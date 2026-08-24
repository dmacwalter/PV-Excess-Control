"""Edge-case tests for per-appliance averaging_window at non-30s controller
intervals.

Background: optimizer.py's optimize() used to hardcode
    controller_interval = 30  # default, used for window->entry count conversion
and never received the real controller interval from the coordinator. At a
60s controller interval (dmacwalter's real config), this made
`entries_needed = int(averaging_window / 30)` select TWICE as many history
entries as the configured window implied, so the effective averaging window
was 2x the configured value.

Fixed by adding a `controller_interval_s` parameter to optimize(), wired
through from the coordinator's real `update_interval`. These tests build
history at a real 60s cadence (rather than the previously-hardcoded-matching
30s cadence used elsewhere) to confirm the fix.
"""
from __future__ import annotations

import dataclasses
from datetime import timedelta

from custom_components.pv_excess_control.models import PowerState

from .test_optimizer import (
    _empty_plan,
    _make_appliance,
    _make_power,
    _make_state,
    _make_tariff,
    _optimizer_for_tests,
    _utcnow,
)


def _history_at_interval(interval_s: float, recent_value: float, older_value: float,
                          n_recent: int, n_older: int) -> list[PowerState]:
    """Build power_history at a given real cadence, oldest-first (as the
    coordinator appends), newest entry last."""
    recent = [
        PowerState(
            pv_production=recent_value + 4140.0, grid_export=recent_value,
            grid_import=0.0, load_power=4140.0, excess_power=recent_value,
            battery_soc=None, battery_power=None, ev_soc=None,
            timestamp=_utcnow() - timedelta(seconds=interval_s * i),
        )
        for i in range(n_recent)
    ]
    older = [
        PowerState(
            pv_production=older_value + 4140.0, grid_export=older_value,
            grid_import=0.0, load_power=4140.0, excess_power=older_value,
            battery_soc=None, battery_power=None, ev_soc=None,
            timestamp=_utcnow() - timedelta(seconds=interval_s * (n_recent + i)),
        )
        for i in range(n_older)
    ]
    return list(reversed(older)) + list(reversed(recent))


def test_averaging_window_at_60s_controller_interval_pulls_double_the_span():
    """At dmacwalter's real 60s controller interval, a configured
    averaging_window=300 (intended: last 5 minutes / 5 entries) should
    average the most recent 5 history entries.
    """
    ev = _make_appliance(
        id="ev", name="EV", priority=1, nominal_power=11000.0, phases=3,
        dynamic_current=True, current_entity="number.wbec",
        min_current=6.0, max_current=16.0, current_step=0.1,
        is_big_consumer=True,
    )
    ev = dataclasses.replace(ev, averaging_window=300.0)  # intent: last 5 min

    state = _make_state(id="ev", is_on=True, current_power=4140.0)  # 6 A
    power = _make_power(excess=3000.0, pv=7140.0)

    # Real 60s cadence. Last 5 entries (true 5-min window) average 1200W.
    # Entries 6-10 back average 200W.
    history = _history_at_interval(
        interval_s=60, recent_value=1200.0, older_value=200.0,
        n_recent=5, n_older=5,
    )

    opt = _optimizer_for_tests(grid_voltage=230, off_threshold=-100, min_good_samples=3)
    result = opt.optimize(
        power_state=power, appliances=[ev], appliance_states=[state],
        plan=_empty_plan(), power_history=history, tariff=_make_tariff(),
        controller_interval_s=60,
    )

    ev_decision = next(d for d in result.decisions if d.appliance_id == "ev")

    # Before the fix (hardcoded 30s constant): entries_needed = int(300/30)
    # = 10, so ALL 10 entries got averaged -> (5*1200+5*200)/10 = 700W budget
    # -> ~7.0A. Now that controller_interval_s=60 is threaded through:
    # entries_needed = int(300/60) = 5, averaging only the most recent 5
    # entries -> 1200W budget -> ~7.7A.
    assert ev_decision.target_current is not None
    correct_available_w = 1200.0 + 4140.0
    correct_amps = correct_available_w / (230 * 3)
    assert abs(ev_decision.target_current - correct_amps) < 0.3, (
        f"Expected ~{correct_amps:.2f}A using the true 5-entry/5-minute "
        f"average at 60s cadence, got {ev_decision.target_current:.2f}A."
    )


def test_averaging_window_entries_needed_scales_with_real_controller_interval():
    """Implementation-level check: with averaging_window=600, entries_needed
    should scale with the REAL controller interval passed in via
    controller_interval_s, not a hardcoded 30s constant. 10 entries at 60s
    cadence, 20 entries at 30s cadence."""
    ev = _make_appliance(
        id="ev", name="EV", priority=1, nominal_power=11000.0, phases=3,
        dynamic_current=True, current_entity="number.wbec",
        min_current=6.0, max_current=16.0, current_step=0.1,
        is_big_consumer=True,
    )
    ev = dataclasses.replace(ev, averaging_window=600.0)
    state = _make_state(id="ev", is_on=True, current_power=4140.0)
    power = _make_power(excess=3000.0, pv=7140.0)

    history = _history_at_interval(
        interval_s=60, recent_value=1200.0, older_value=200.0,
        n_recent=10, n_older=10,
    )

    opt = _optimizer_for_tests(grid_voltage=230, off_threshold=-100, min_good_samples=1)

    # At the real 60s controller interval: entries_needed = 600/60 = 10,
    # averaging only the 10 most-recent (all 1200W) entries -> avg_budget=1200.
    result_60s = opt.optimize(
        power_state=power, appliances=[ev], appliance_states=[state],
        plan=_empty_plan(), power_history=history, tariff=_make_tariff(),
        controller_interval_s=60,
    )
    decision_60s = next(d for d in result_60s.decisions if d.appliance_id == "ev")
    expected_amps_60s = (1200.0 + 4140.0) / (230 * 3)
    assert abs(decision_60s.target_current - expected_amps_60s) < 0.3, (
        f"At 60s controller interval, expected ~{expected_amps_60s:.2f}A "
        f"(10-entry/10-min average of the recent 1200W block), got "
        f"{decision_60s.target_current:.2f}A"
    )

    # At a 30s controller interval with the SAME averaging_window=600s,
    # entries_needed = 600/30 = 20, pulling in all 20 entries.
    result_30s = opt.optimize(
        power_state=power, appliances=[ev], appliance_states=[state],
        plan=_empty_plan(), power_history=history, tariff=_make_tariff(),
        controller_interval_s=30,
    )
    decision_30s = next(d for d in result_30s.decisions if d.appliance_id == "ev")
    expected_amps_30s = (700.0 + 4140.0) / (230 * 3)
    assert abs(decision_30s.target_current - expected_amps_30s) < 0.3, (
        f"At 30s controller interval, expected ~{expected_amps_30s:.2f}A "
        f"(20-entry/10-min average spanning both value blocks), got "
        f"{decision_30s.target_current:.2f}A"
    )

    assert decision_60s.target_current != decision_30s.target_current, (
        "60s and 30s controller intervals produced the same averaged "
        "budget for the same averaging_window -- controller_interval_s "
        "is not being used to scale entries_needed."
    )


def test_averaging_window_entries_needed_uses_ceil_not_floor():
    """Backported from Kolbi/PV-Excess-Control#12: entries_needed must round
    UP (math.ceil), not truncate (int/floor). A 250s averaging_window at a
    60s controller interval needs 5 entries (300s of coverage) to avoid
    under-covering the configured window; int(250/60)=4 (240s) would fall
    short of what was asked for.

    History is built so the 5th-most-recent entry (the one only a ceil'd
    5-entry window includes, and a floor'd 4-entry window would miss) has a
    distinctly different value -- so floor vs ceil produce measurably
    different averaged budgets and the test actually distinguishes them.
    """
    ev = _make_appliance(
        id="ev", name="EV", priority=1, nominal_power=11000.0, phases=3,
        dynamic_current=True, current_entity="number.wbec",
        min_current=6.0, max_current=16.0, current_step=0.1,
        is_big_consumer=True,
    )
    ev = dataclasses.replace(ev, averaging_window=250.0)
    state = _make_state(id="ev", is_on=True, current_power=4140.0)
    power = _make_power(excess=3000.0, pv=7140.0)

    values = [1200.0, 1200.0, 1200.0, 1200.0, -800.0, 200.0, 200.0]
    history = [
        PowerState(
            pv_production=v + 4140.0, grid_export=max(v, 0.0),
            grid_import=max(-v, 0.0), load_power=4140.0, excess_power=v,
            battery_soc=None, battery_power=None, ev_soc=None,
            timestamp=_utcnow() - timedelta(seconds=60 * i),
        )
        for i, v in enumerate(values)
    ]
    history = list(reversed(history))  # oldest first, newest last

    opt = _optimizer_for_tests(grid_voltage=230, off_threshold=-100, min_good_samples=1)
    result = opt.optimize(
        power_state=power, appliances=[ev], appliance_states=[state],
        plan=_empty_plan(), power_history=history, tariff=_make_tariff(),
        controller_interval_s=60,
    )
    decision = next(d for d in result.decisions if d.appliance_id == "ev")

    # ceil(250/60) = 5 entries -> avg of [1200,1200,1200,1200,-800] = 800W.
    # int(250/60) = 4 entries (the bug) -> avg of [1200,1200,1200,1200] = 1200W.
    expected_amps_ceil = (800.0 + 4140.0) / (230 * 3)
    buggy_amps_floor = (1200.0 + 4140.0) / (230 * 3)
    assert abs(decision.target_current - expected_amps_ceil) < 0.3, (
        f"Expected ~{expected_amps_ceil:.2f}A from the correct 5-entry/ceil "
        f"average, got {decision.target_current:.2f}A (which would match "
        f"the buggy 4-entry/floor average of ~{buggy_amps_floor:.2f}A)."
    )

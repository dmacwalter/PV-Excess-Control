"""Tests for battery target protection (feasibility gate).

Reproduces 2026-09-26. Battery target 100% by 15:50. At 15:21 with SoC 90%
the pool (1810 W nominal) was started on grid supplement because the 14C
day rate (0.18) sat under the 0.20 cheap threshold, with only ~1049 W of
averaged excess against 2010 W needed. Once running it was held on through
three "shed imminent" cycles (-681 / -1228 / -1064 W instantaneous) because
its schedule deadline had not passed, so SHED used the pool's averaged
excess instead, and that stayed above the off threshold. The battery
discharged at up to ~1.5 kW while this happened.

0.3.11 answered this with a fixed window before the target time. That was
wrong for 14C: 0.18 is the cheapest grid energy of the day, so running the
pool before the peak is correct even when the energy is routed through the
battery, provided the battery can still be refilled in time. On the day a
grid charge from 15:31 reached 99% by 15:49 (about 7 kW across 90-99%).

0.3.12 engages protection only once the shortfall can no longer be charged
at the assured rate, plus a margin, before the target time. With the rate at
0 the behaviour must be exactly as upstream.
"""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from custom_components.pv_excess_control.const import Action, BatteryStrategy
from custom_components.pv_excess_control.models import (
    ApplianceConfig,
    ApplianceState,
    BatteryTarget,
    Plan,
    PowerState,
    TariffInfo,
)
from custom_components.pv_excess_control.optimizer import Optimizer

CAPACITY_KWH = 22.4
RATE_W = 7000
MARGIN_MIN = 5
# 10% of 22.4 kWh at 7 kW is 19.2 min, plus 5 min margin = 24.2 min.
RECOVERABLE = timedelta(minutes=29)   # 15:21 against the 15:50 target
TOO_LATE = timedelta(minutes=20)


def _cfg(**over):
    base = dict(
        id="pool", name="Pool", entity_id="switch.pool", priority=10, phases=1,
        nominal_power=1810, actual_power_entity="sensor.pool_power",
        dynamic_current=False, current_entity=None, min_current=6, max_current=32,
        ev_soc_entity=None, ev_connected_entity=None, is_big_consumer=False,
        battery_max_discharge_override=None, on_only=False,
        min_daily_runtime=timedelta(hours=3), max_daily_runtime=timedelta(hours=7),
        schedule_deadline=None, allow_grid_supplement=True, max_grid_power=None,
        switch_interval=timedelta(0), averaging_window=None,
        start_after=None, end_before=None,
    )
    base.update(over)
    return ApplianceConfig(**base)


def _state(is_on=False, runtime=timedelta(hours=6)):
    return ApplianceState(
        appliance_id="pool", is_on=is_on, current_power=1330.0 if is_on else 0.0,
        current_amperage=None, runtime_today=runtime, energy_today=0.0,
        last_state_change=None, ev_connected=None, ev_soc=None,
        activations_today=0,
    )


def _ps(excess, soc=90.0):
    return PowerState(
        pv_production=4300.0, grid_export=max(excess, 0.0),
        grid_import=max(-excess, 0.0), load_power=4300.0 - excess,
        excess_power=float(excess), battery_soc=soc, battery_power=0.0,
        ev_soc=None, timestamp=datetime.now(),
    )


def _plan(target_in=TOO_LATE, target_soc=100.0, aware=False):
    now = datetime.now(timezone.utc).astimezone() if aware else datetime.now()
    return Plan(
        created_at=now, horizon=timedelta(hours=12), entries=[],
        confidence=0.0, grid_charge_recommended=False,
        battery_target=BatteryTarget(
            target_soc=target_soc, target_time=now + target_in,
            strategy=BatteryStrategy.BALANCED,
        ),
    )


# 14C day rate under the pool's cheap threshold, as on the day.
TARIFF = TariffInfo(0.18, 0.06, 0.20, 0.20)


def _opt(rate=RATE_W, capacity=CAPACITY_KWH):
    return Optimizer(
        grid_voltage=240, controller_interval=60,
        battery_protect_charge_rate_w=rate,
        battery_protect_margin_minutes=MARGIN_MIN,
        battery_capacity_kwh=capacity,
    )


def _run(cfg, state, history, *, rate=RATE_W, capacity=CAPACITY_KWH, plan=None):
    opt = _opt(rate, capacity)
    return opt.optimize(
        power_state=history[-1], appliances=[cfg], appliance_states=[state],
        plan=plan or _plan(), power_history=history, tariff=TARIFF,
        plan_influence="none",
    ).decisions[0]


class TestGridSupplementStart:
    """The 15:21 start."""

    def test_disabled_keeps_upstream_behaviour(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10, rate=0)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_allowed_while_battery_can_still_recover(self):
        """The 15:21 case: 18c pre-peak, 24 min needed, 29 min left."""
        d = _run(_cfg(), _state(), [_ps(1049)] * 10,
                 plan=_plan(target_in=RECOVERABLE))
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_blocked_once_recovery_time_runs_out(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10)
        assert d.action != Action.ON, d.reason

    def test_allowed_once_target_reached(self):
        d = _run(_cfg(), _state(), [_ps(1049, soc=100.0)] * 10)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_bigger_shortfall_engages_earlier(self):
        """50% short is 96 + 5 min at 7 kW, so 29 min out is already too late."""
        d = _run(_cfg(), _state(), [_ps(1049, soc=50.0)] * 10,
                 plan=_plan(target_in=RECOVERABLE))
        assert d.action != Action.ON, d.reason

    def test_missing_capacity_does_not_block(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10, capacity=None)
        assert d.action == Action.ON

    def test_not_active_after_target_time(self):
        """After the target time the post-deadline gate and ordinary tariff
        logic own the decision."""
        d = _run(_cfg(), _state(), [_ps(1049)] * 10,
                 plan=_plan(target_in=-timedelta(minutes=5)))
        assert d.action == Action.ON

    def test_charge_path_appliance_exempt(self):
        d = _run(_cfg(battery_target_gated=True), _state(), [_ps(1049)] * 10)
        assert d.action == Action.ON

    def test_missing_soc_does_not_block(self):
        d = _run(_cfg(), _state(), [_ps(1049, soc=None)] * 10)
        assert d.action == Action.ON

    def test_timezone_aware_target(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10, plan=_plan(aware=True))
        assert d.action != Action.ON, d.reason

    def test_real_excess_still_starts_it(self):
        """Protection only removes the grid top-up. Genuine surplus above the
        normal on-threshold still starts the appliance."""
        d = _run(_cfg(), _state(), [_ps(2500)] * 10)
        assert d.action == Action.ON
        assert "excess available" in d.reason.lower()


class TestShedWhileRunning:
    """15:24-15:27: shed imminent, never shed."""

    def _deadline_cfg(self):
        return _cfg(
            schedule_deadline=(datetime.now() + timedelta(hours=2)).time(),
            averaging_window=600,
        )

    def _history(self):
        # Nine positive samples then a dip: the averaged figure stays well
        # above the off threshold while the instantaneous one is negative.
        return [_ps(500)] * 9 + [_ps(-681)]

    def test_disabled_reproduces_the_hold(self):
        d = _run(self._deadline_cfg(), _state(is_on=True), self._history(), rate=0)
        assert d.action == Action.ON
        assert "shed imminent" in d.reason

    def test_sheds_on_instantaneous_when_engaged(self):
        d = _run(self._deadline_cfg(), _state(is_on=True), self._history())
        assert d.action == Action.OFF, d.reason

    def test_hold_kept_while_battery_can_still_recover(self):
        d = _run(self._deadline_cfg(), _state(is_on=True), self._history(),
                 plan=_plan(target_in=RECOVERABLE))
        assert d.action == Action.ON

    def test_no_early_shed_once_target_reached(self):
        hist = [_ps(500, soc=100.0)] * 9 + [_ps(-681, soc=100.0)]
        d = _run(self._deadline_cfg(), _state(is_on=True), hist)
        assert d.action == Action.ON


class TestCheapWindowOverride:
    def test_override_amps_suppressed_when_engaged(self):
        opt = _opt()
        opt._current_plan = _plan()
        opt._current_battery_soc = 90.0
        cfg = _cfg(dynamic_current=True, cheap_grid_target_current=16.0)
        assert opt._cheap_window_target_amps(cfg, TARIFF, 1) is None

    def test_override_amps_unchanged_when_disabled(self):
        opt = _opt(rate=0)
        opt._current_plan = _plan()
        opt._current_battery_soc = 90.0
        cfg = _cfg(dynamic_current=True, cheap_grid_target_current=16.0)
        assert opt._cheap_window_target_amps(cfg, TARIFF, 1) == 16.0


class TestTwoStageChargeModel:
    """0.3.13: bulk rate below the taper SoC, assured rate above it."""

    def _opt(self, bulk=9000, taper=90):
        o = Optimizer(
            grid_voltage=240, battery_protect_charge_rate_w=6000,
            battery_protect_margin_minutes=0, battery_capacity_kwh=22.4,
            battery_protect_bulk_rate_w=bulk, battery_protect_taper_soc=taper,
        )
        return o

    def test_from_low_soc_splits_at_taper(self):
        # 40->90% = 11.2 kWh at 9 kW (74.7 min) + 90->100% = 2.24 kWh at 6 kW (22.4 min)
        t = self._opt()._battery_protect_charge_time(40, 100)
        assert t.total_seconds() / 60 == pytest.approx(97.07, abs=0.05)

    def test_above_taper_uses_assured_rate_only(self):
        t = self._opt()._battery_protect_charge_time(95, 100)
        assert t.total_seconds() / 60 == pytest.approx(11.2, abs=0.05)

    def test_target_below_taper_uses_bulk_only(self):
        t = self._opt()._battery_protect_charge_time(40, 80)
        assert t.total_seconds() / 60 == pytest.approx(59.73, abs=0.05)

    def test_no_bulk_rate_is_single_rate(self):
        t = self._opt(bulk=0)._battery_protect_charge_time(40, 100)
        assert t.total_seconds() / 60 == pytest.approx(134.4, abs=0.05)

    def test_bulk_rate_delays_engagement_from_low_soc(self):
        """SoC 40 with 110 min left: single-rate says 134 + 10 min needed
        (engaged), two-stage says 97 + 10 (not yet)."""
        plan = _plan(target_in=timedelta(minutes=110))
        hist = [_ps(1049, soc=40.0)] * 10
        single = Optimizer(grid_voltage=240, controller_interval=60,
                           battery_protect_charge_rate_w=6000,
                           battery_protect_margin_minutes=10, battery_capacity_kwh=22.4)
        two = Optimizer(grid_voltage=240, controller_interval=60,
                        battery_protect_charge_rate_w=6000,
                        battery_protect_margin_minutes=10, battery_capacity_kwh=22.4,
                        battery_protect_bulk_rate_w=9000)
        kw = dict(power_state=hist[-1], appliances=[_cfg()], appliance_states=[_state()],
                  plan=plan, power_history=hist, tariff=TARIFF, plan_influence="none")
        assert single.optimize(**kw).decisions[0].action != Action.ON
        assert two.optimize(**kw).decisions[0].action == Action.ON


def _ps_flow(excess, soc, battery_power, grid_import):
    return replace(_ps(excess, soc=soc), battery_power=battery_power,
                   grid_import=grid_import, grid_export=0.0)


class TestGridChargeExemption:
    """0.3.13: stand aside while the battery is already being grid-charged."""

    def _decide(self, battery_power, grid_import):
        hist = [_ps_flow(1049, 90.0, battery_power, grid_import)] * 10
        return _run(_cfg(), _state(), hist)  # TOO_LATE plan: gate would engage

    def test_charging_while_importing_allows_grid_supplement(self):
        d = self._decide(battery_power=7500, grid_import=4000)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_self_use_discharge_still_blocked(self):
        d = self._decide(battery_power=-1500, grid_import=0)
        assert d.action != Action.ON, d.reason

    def test_charging_from_surplus_not_mistaken_for_grid_charge(self):
        d = self._decide(battery_power=3000, grid_import=0)
        assert d.action != Action.ON, d.reason

    def test_import_without_charging_still_blocked(self):
        d = self._decide(battery_power=0, grid_import=1500)
        assert d.action != Action.ON, d.reason

    def test_below_thresholds_still_blocked(self):
        d = self._decide(battery_power=400, grid_import=150)
        assert d.action != Action.ON, d.reason

    def test_shed_still_on_instantaneous_without_grid_charge(self):
        cfg = _cfg(schedule_deadline=(datetime.now() + timedelta(hours=2)).time(),
                   averaging_window=600)
        hist = [_ps(500)] * 9 + [_ps_flow(-681, 90.0, -700, 0)]
        d = _run(cfg, _state(is_on=True), hist)
        assert d.action == Action.OFF, d.reason

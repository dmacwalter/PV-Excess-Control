"""Tests for the pre-target battery protection window.

Reproduces 2026-09-26. Battery target 100% by 16:00. At 15:21 with SoC 90%
the pool (1810 W nominal) was started on grid supplement because the 14C
day rate (0.18) sat under the 0.20 cheap threshold, with only ~1049 W of
averaged excess against 2010 W needed. Once running it was held on through
three "shed imminent" cycles (-681 / -1228 / -1064 W instantaneous) because
its schedule deadline had not passed, so SHED used the pool's averaged
excess instead, and that stayed above the off threshold. The battery
discharged at up to ~1.5 kW while this happened.

With battery_protect_window_minutes > 0, and SoC below target inside the
window, neither of those paths is available. With the window at 0 the
behaviour must be exactly as before.
"""
from datetime import datetime, timedelta, timezone

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

WINDOW_MIN = 120


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


def _plan(target_in=timedelta(minutes=39), target_soc=100.0, aware=False):
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


def _run(cfg, state, history, *, window=WINDOW_MIN, plan=None):
    opt = Optimizer(
        grid_voltage=240, controller_interval=60,
        battery_protect_window_minutes=window,
    )
    return opt.optimize(
        power_state=history[-1], appliances=[cfg], appliance_states=[state],
        plan=plan or _plan(), power_history=history, tariff=TARIFF,
        plan_influence="none",
    ).decisions[0]


class TestGridSupplementStart:
    """The 15:21 start."""

    def test_window_disabled_keeps_upstream_behaviour(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10, window=0)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_blocked_inside_window_when_below_target(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10)
        assert d.action != Action.ON, d.reason

    def test_allowed_once_target_reached(self):
        d = _run(_cfg(), _state(), [_ps(1049, soc=100.0)] * 10)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_allowed_before_window_opens(self):
        d = _run(_cfg(), _state(), [_ps(1049)] * 10,
                 plan=_plan(target_in=timedelta(hours=4)))
        assert d.action == Action.ON

    def test_not_active_after_target_time(self):
        """The window is [target - w, target); after that the post-deadline
        gate and ordinary tariff logic own the decision."""
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

    def test_window_disabled_reproduces_the_hold(self):
        d = _run(self._deadline_cfg(), _state(is_on=True), self._history(), window=0)
        assert d.action == Action.ON
        assert "shed imminent" in d.reason

    def test_sheds_on_instantaneous_inside_window(self):
        d = _run(self._deadline_cfg(), _state(is_on=True), self._history())
        assert d.action == Action.OFF, d.reason

    def test_no_early_shed_once_target_reached(self):
        hist = [_ps(500, soc=100.0)] * 9 + [_ps(-681, soc=100.0)]
        d = _run(self._deadline_cfg(), _state(is_on=True), hist)
        assert d.action == Action.ON


class TestCheapWindowOverride:
    def test_override_amps_suppressed_inside_window(self):
        opt = Optimizer(grid_voltage=240, battery_protect_window_minutes=WINDOW_MIN)
        opt._current_plan = _plan()
        opt._current_battery_soc = 90.0
        cfg = _cfg(dynamic_current=True, cheap_grid_target_current=16.0)
        assert opt._cheap_window_target_amps(cfg, TARIFF, 1) is None

    def test_override_amps_unchanged_when_disabled(self):
        opt = Optimizer(grid_voltage=240, battery_protect_window_minutes=0)
        opt._current_plan = _plan()
        opt._current_battery_soc = 90.0
        cfg = _cfg(dynamic_current=True, cheap_grid_target_current=16.0)
        assert opt._cheap_window_target_amps(cfg, TARIFF, 1) == 16.0

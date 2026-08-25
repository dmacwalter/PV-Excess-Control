"""Tests for the slack-aware min_daily_runtime shed guard.

The guard was previously absolute: an appliance below its daily runtime total
could never be shed. That forced the requirement to be served as one
contiguous block, since the appliance could not be interrupted until the whole
total was banked.

Observed 2026-08-23: the pool ran unbroken 08:46:35 -> 15:46:38 straight
through a 13.5 kW house peak, with hours of operating window still available
to make the runtime up later. Seen again 2026-08-25 at 10:44, when excess hit
-1344 W and the pool was not even a shed candidate despite roughly four hours
of slack remaining before its 17:20 window end.

A daily total is a total, not a block: shedding is now allowed while enough of
the day remains to catch up, and deadline must-run is the backstop.
"""
from datetime import datetime, time, timedelta

import pytest

from custom_components.pv_excess_control.const import Action
from custom_components.pv_excess_control.models import (
    ApplianceConfig,
    ApplianceState,
    PowerState,
)
from custom_components.pv_excess_control.optimizer import Optimizer


def _cfg(**over):
    base = dict(
        id="pool", name="Pool", entity_id="switch.pool", priority=10, phases=1,
        nominal_power=1810, actual_power_entity="sensor.pool_power",
        dynamic_current=False, current_entity=None, min_current=6, max_current=32,
        ev_soc_entity=None, ev_connected_entity=None, is_big_consumer=False,
        battery_max_discharge_override=None, on_only=False,
        min_daily_runtime=timedelta(hours=3), max_daily_runtime=timedelta(hours=7),
        schedule_deadline=None, allow_grid_supplement=False, max_grid_power=None,
        shed_before_grid_charge=True, switch_interval=timedelta(0),
        averaging_window=600, start_after=time(7, 30), end_before=time(17, 20),
    )
    base.update(over)
    return ApplianceConfig(**base)


def _state(runtime=timedelta(hours=3), is_on=True):
    return ApplianceState(
        appliance_id="pool", is_on=is_on, current_power=1940.0 if is_on else 0.0,
        current_amperage=None, runtime_today=runtime, energy_today=0.0,
        last_state_change=None, ev_connected=None, ev_soc=None,
        activations_today=0,
    )


def _ps(excess):
    return PowerState(
        pv_production=max(excess, 0) + 800, grid_export=max(excess, 0.0),
        grid_import=max(-excess, 0.0), load_power=800.0, excess_power=float(excess),
        battery_soc=80.0, battery_power=0.0, ev_soc=None, timestamp=datetime.now(),
    )


class TestRuntimeSlack:
    """Daily runtime may be served in pieces, so long as it still completes."""

    def _opt(self):
        return Optimizer(grid_voltage=240, controller_interval=60)

    def test_slack_positive_when_day_has_room(self):
        """2h done of 3h, deadline far away -> plenty of slack, may shed."""
        opt = self._opt()
        far = (datetime.now() + timedelta(hours=6)).time()
        slack = opt._runtime_slack_seconds(
            _cfg(schedule_deadline=far), _state(runtime=timedelta(hours=2))
        )
        assert slack is not None and slack > 0

    def test_slack_negative_when_behind(self):
        """1h left to run but only 30min of day remains -> protect it."""
        opt = self._opt()
        soon = (datetime.now() + timedelta(minutes=30)).time()
        slack = opt._runtime_slack_seconds(
            _cfg(schedule_deadline=soon), _state(runtime=timedelta(hours=2))
        )
        assert slack is not None and slack <= 0

    def test_no_protection_once_runtime_met(self):
        opt = self._opt()
        far = (datetime.now() + timedelta(hours=6)).time()
        assert opt._runtime_slack_seconds(
            _cfg(schedule_deadline=far), _state(runtime=timedelta(hours=4))
        ) is None

    def test_falls_back_to_operating_window_end(self):
        """With no schedule_deadline, end_before is the real cut-off."""
        opt = self._opt()
        cfg = _cfg(schedule_deadline=None, end_before=time(23, 59))
        slack = opt._runtime_slack_seconds(cfg, _state(runtime=timedelta(hours=2)))
        assert slack is not None

    def test_none_when_no_deadline_available(self):
        """Neither deadline nor window: slack is unknowable."""
        opt = self._opt()
        cfg = _cfg(schedule_deadline=None, end_before=None)
        assert opt._runtime_slack_seconds(
            cfg, _state(runtime=timedelta(hours=2))
        ) is None

    def test_no_minimum_configured_returns_none(self):
        opt = self._opt()
        assert opt._runtime_slack_seconds(
            _cfg(min_daily_runtime=None), _state()
        ) is None

    def test_ten_percent_buffer_is_applied(self):
        """Slack reserves runtime * 1.1, matching deadline must-run."""
        opt = self._opt()
        now = datetime.now()
        # exactly 66min left, 60min of runtime outstanding -> 60*1.1 = 66 -> zero
        deadline = (now + timedelta(minutes=66)).time()
        cfg = _cfg(schedule_deadline=deadline)
        slack = opt._runtime_slack_seconds(cfg, _state(runtime=timedelta(hours=2)))
        assert slack is not None
        assert abs(slack) < 90  # within a cycle of the buffer boundary


class TestShedIntegration:
    """End-to-end: the guard must actually change SHED's candidate set.

    Reproduces 2026-08-25 10:44:01, when instantaneous excess hit -1344 W and
    the pool (2h15m of a 3h minimum, window open until 17:20) was not even
    considered for shedding.
    """

    def _optimize(self, cfg, state, excess):
        opt = Optimizer(grid_voltage=240, controller_interval=60)
        ps = _ps(excess)
        from custom_components.pv_excess_control.models import Plan, BatteryTarget
        from custom_components.pv_excess_control.const import BatteryStrategy
        from custom_components.pv_excess_control.models import TariffInfo
        plan = Plan(
            created_at=datetime.now(), horizon=timedelta(hours=12), entries=[],
            confidence=0.0, grid_charge_recommended=False,
            battery_target=BatteryTarget(
                target_soc=100.0, target_time=datetime.now() + timedelta(hours=3),
                strategy=list(BatteryStrategy)[0]),
        )
        return opt.optimize(
            power_state=ps, appliances=[cfg], appliance_states=[state],
            plan=plan, power_history=[ps] * 20,
            tariff=TariffInfo(0.18, 0.05, 0.20, 0.20),
            plan_influence="none",
        )

    def test_shed_allowed_with_slack_remaining(self):
        """2h15m of 3h done, window to 17:20 hours away -> sheddable."""
        far = (datetime.now() + timedelta(hours=5)).time()
        cfg = _cfg(schedule_deadline=None, end_before=far, averaging_window=None)
        res = self._optimize(cfg, _state(runtime=timedelta(hours=2, minutes=15)), -1344)
        assert res.decisions[0].action == Action.OFF, (
            f"expected shed with slack available, got {res.decisions[0].reason!r}"
        )

    def test_shed_blocked_when_genuinely_behind(self):
        """Same runtime, but the window closes in 20 minutes -> protected."""
        soon = (datetime.now() + timedelta(minutes=20)).time()
        cfg = _cfg(schedule_deadline=None, end_before=soon, averaging_window=None)
        res = self._optimize(cfg, _state(runtime=timedelta(hours=2, minutes=15)), -1344)
        assert res.decisions[0].action != Action.OFF, (
            f"expected protection when behind, got {res.decisions[0].reason!r}"
        )

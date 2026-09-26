"""0.3.14 fixes to pre-existing behaviour found by randomised simulation:

1. Grid-supplement hold: an appliance started on grid supplement was shed on
   the next check once its own grid draw showed as a deficit, then refused a
   restart for the switch interval, cycling ~10 min on / 10 min off through
   a cheap window.
2. Must-run precedence: a grid-supplement ON is evaluated before must-run and
   did not carry must-run's cooldown bypass, so inside the switch interval it
   was deferred and must-run was never reached.
3. Slack vs switch interval: SHED released an appliance still owed runtime
   with any positive slack, even less than the switch interval it would then
   have to wait before restarting.
4. Cheap window closing: a grid-supplement start in the last switch interval
   of a cheap window committed the appliance into the next, dearer period.
"""
from dataclasses import replace
from datetime import datetime, timedelta

from freezegun import freeze_time

from custom_components.pv_excess_control.const import Action
from custom_components.pv_excess_control.models import TariffInfo, TariffWindow
from custom_components.pv_excess_control.optimizer import Optimizer

from .test_battery_protect_target import _cfg, _plan, _ps, _state

NOW = datetime(2026, 9, 26, 14, 0)  # naive local, frozen


def _tariff(price=0.18, cheap_until=None):
    windows = []
    if cheap_until is not None:
        windows = [
            TariffWindow(NOW.replace(hour=11), cheap_until, 0.18, True),
            TariffWindow(cheap_until, cheap_until + timedelta(hours=5), 0.45, False),
        ]
    return TariffInfo(price, 0.06, 0.20, 0.20, windows)


def _decide(cfg, state, history, tariff=None, **opt_kw):
    opt = Optimizer(grid_voltage=240, controller_interval=60, off_threshold=-100, **opt_kw)
    with freeze_time(NOW):
        return opt.optimize(
            power_state=history[-1], appliances=[cfg], appliance_states=[state],
            plan=_plan(target_in=timedelta(hours=6)), power_history=history,
            tariff=tariff or _tariff(), plan_influence="none",
        ).decisions[0]


RUNNING_DEFICIT = [_ps(-1300)] * 10   # pool's own draw showing as a deficit


class TestGridSupplementHold:
    def test_running_pool_held_on_grid_while_cheap(self):
        d = _decide(_cfg(switch_interval=600), _state(is_on=True), RUNNING_DEFICIT)
        assert d.action == Action.ON
        assert d.reason.startswith("Grid supplement (staying on)")

    def test_not_held_once_tariff_is_dear(self):
        d = _decide(_cfg(), _state(is_on=True), RUNNING_DEFICIT, tariff=_tariff(price=0.45))
        assert d.action == Action.OFF, d.reason

    def test_not_held_without_grid_supplement_allowed(self):
        d = _decide(_cfg(allow_grid_supplement=False), _state(is_on=True), RUNNING_DEFICIT)
        assert d.action == Action.OFF, d.reason

    def test_not_held_when_deficit_exceeds_max_grid_power(self):
        d = _decide(_cfg(max_grid_power=800), _state(is_on=True), RUNNING_DEFICIT)
        assert d.action == Action.OFF, d.reason

    def test_draw_above_nominal_still_held(self):
        st = replace(_state(is_on=True), current_power=1950.0)
        d = _decide(_cfg(nominal_power=1810), st, [_ps(-1950)] * 10)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_not_held_when_battery_protection_engaged(self):
        opt_kw = dict(battery_protect_charge_rate_w=6000, battery_protect_margin_minutes=10,
                      battery_capacity_kwh=22.4)
        opt = Optimizer(grid_voltage=240, controller_interval=60, off_threshold=-100, **opt_kw)
        with freeze_time(NOW):
            d = opt.optimize(
                power_state=RUNNING_DEFICIT[-1], appliances=[_cfg()],
                appliance_states=[_state(is_on=True)], plan=_plan(target_in=timedelta(minutes=20)),
                power_history=RUNNING_DEFICIT, tariff=_tariff(), plan_influence="none",
            ).decisions[0]
        assert d.action == Action.OFF, d.reason

    def test_normal_staying_on_text_when_no_deficit(self):
        d = _decide(_cfg(), _state(is_on=True), [_ps(300)] * 10)
        assert d.action == Action.ON
        assert d.reason.startswith("Staying on")


def _behind_cfg(minutes_to_deadline, **kw):
    return _cfg(schedule_deadline=(NOW + timedelta(minutes=minutes_to_deadline)).time(),
                switch_interval=600, **kw)


class TestMustRunPrecedence:
    def test_grid_supplement_start_carries_bypass_when_must_run_due(self):
        # 20 min owed, 21 min to deadline: must-run due (21 <= 22)
        st = _state(runtime=timedelta(hours=2, minutes=40))
        d = _decide(_behind_cfg(21), st, [_ps(500)] * 10)
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()
        assert d.bypasses_cooldown is True

    def test_no_bypass_when_must_run_not_due(self):
        st = _state(runtime=timedelta(hours=2, minutes=40))
        d = _decide(_behind_cfg(60), st, [_ps(500)] * 10)
        assert d.action == Action.ON
        assert d.bypasses_cooldown is False


class TestSlackKeepsSwitchInterval:
    def _running_behind(self, minutes_to_deadline):
        # 20 min owed; slack = time left - 22 min
        st = replace(_state(is_on=True, runtime=timedelta(hours=2, minutes=40)))
        return _decide(_behind_cfg(minutes_to_deadline), st, [_ps(-1300)] * 10,
                       tariff=_tariff(price=0.45))

    def test_not_shed_with_less_slack_than_switch_interval(self):
        d = self._running_behind(28)   # 6 min slack < 10 min interval
        assert d.action == Action.ON, d.reason

    def test_shed_with_more_slack_than_switch_interval(self):
        d = self._running_behind(40)   # 18 min slack
        assert d.action == Action.OFF, d.reason


class TestCheapWindowClosing:
    def test_start_blocked_in_last_switch_interval(self):
        d = _decide(_cfg(switch_interval=600), _state(), [_ps(500)] * 10,
                    tariff=_tariff(cheap_until=NOW + timedelta(minutes=9)))
        assert d.action != Action.ON, d.reason

    def test_start_allowed_with_a_full_interval_left(self):
        d = _decide(_cfg(switch_interval=600), _state(), [_ps(500)] * 10,
                    tariff=_tariff(cheap_until=NOW + timedelta(minutes=11)))
        assert d.action == Action.ON
        assert "grid supplement" in d.reason.lower()

    def test_start_allowed_when_must_run_due(self):
        st = _state(runtime=timedelta(hours=2, minutes=52))  # 8 min owed
        cfg = _behind_cfg(8)
        d = _decide(cfg, st, [_ps(500)] * 10,
                    tariff=_tariff(cheap_until=NOW + timedelta(minutes=5)))
        assert d.action == Action.ON
        assert d.bypasses_cooldown is True

    def test_consecutive_cheap_windows_merge(self):
        end1 = NOW + timedelta(minutes=5)
        windows = [
            TariffWindow(NOW.replace(hour=11), end1, 0.18, True),
            TariffWindow(end1, end1 + timedelta(hours=1), 0.19, True),
        ]
        d = _decide(_cfg(switch_interval=600), _state(), [_ps(500)] * 10,
                    tariff=TariffInfo(0.18, 0.06, 0.20, 0.20, windows))
        assert d.action == Action.ON

    def test_no_windows_keeps_previous_behaviour(self):
        d = _decide(_cfg(switch_interval=600), _state(), [_ps(500)] * 10, tariff=_tariff())
        assert d.action == Action.ON

    def test_running_appliance_not_affected(self):
        d = _decide(_cfg(switch_interval=600), _state(is_on=True), RUNNING_DEFICIT,
                    tariff=_tariff(cheap_until=NOW + timedelta(minutes=5)))
        assert d.action == Action.ON

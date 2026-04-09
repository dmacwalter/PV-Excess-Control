"""Tests for the status_formatter module."""
from __future__ import annotations

import pytest

from custom_components.pv_excess_control.status_formatter import format_duration


class TestFormatDuration:
    """format_duration renders seconds as compact human-readable strings."""

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "0s"),
            (1, "1s"),
            (45, "45s"),
            (59, "59s"),
            (60, "1min"),
            (90, "1min 30s"),
            (180, "3min"),
            (181, "3min 1s"),
            (599, "9min 59s"),
            (600, "10min"),
            (1800, "30min"),
            (1829, "30min"),   # seconds dropped above the 10-minute boundary
            (3599, "59min"),
            (3600, "1h"),
            (3660, "1h 1min"),
            (7200, "2h"),
            (7230, "2h"),      # 30s rounds to 0min → suppressed
            (7260, "2h 1min"),
        ],
    )
    def test_format_duration(self, seconds: float, expected: str) -> None:
        assert format_duration(seconds) == expected


class TestFormattedStatus:
    """FormattedStatus is a frozen dataclass holding the composed result."""

    def test_all_fields_defaultable(self) -> None:
        from datetime import datetime

        from custom_components.pv_excess_control.status_formatter import FormattedStatus

        fs = FormattedStatus(
            text="example",
            action="on",
            overrides_plan=False,
            cooldown_seconds_remaining=None,
            switch_deferred=False,
            headroom_watts=None,
            plan_action=None,
            plan_window_start=None,
            plan_window_end=None,
        )
        assert fs.text == "example"
        assert fs.action == "on"
        assert fs.overrides_plan is False
        assert fs.cooldown_seconds_remaining is None
        assert fs.switch_deferred is False
        assert fs.headroom_watts is None
        assert fs.plan_action is None
        assert fs.plan_window_start is None
        assert fs.plan_window_end is None

    def test_is_frozen(self) -> None:
        from custom_components.pv_excess_control.status_formatter import FormattedStatus

        fs = FormattedStatus(
            text="x", action="on", overrides_plan=False,
            cooldown_seconds_remaining=None, switch_deferred=False,
            headroom_watts=None, plan_action=None,
            plan_window_start=None, plan_window_end=None,
        )
        with pytest.raises(Exception):
            fs.text = "mutated"  # type: ignore[misc]


from datetime import datetime, timedelta

from custom_components.pv_excess_control.const import Action
from custom_components.pv_excess_control.models import (
    ApplianceConfig,
    ApplianceState,
    BatteryDischargeAction,
    ControlDecision,
)
from custom_components.pv_excess_control.status_formatter import format_status


def _make_config(
    *,
    appliance_id: str = "app1",
    is_big_consumer: bool = False,
) -> ApplianceConfig:
    """Minimal ApplianceConfig fixture — only fields read by the formatter."""
    return ApplianceConfig(
        id=appliance_id,
        name="Test Appliance",
        entity_id="switch.test",
        priority=100,
        phases=1,
        nominal_power=1000.0,
        actual_power_entity=None,
        dynamic_current=False,
        current_entity=None,
        min_current=6.0,
        max_current=16.0,
        ev_soc_entity=None,
        ev_connected_entity=None,
        is_big_consumer=is_big_consumer,
        battery_max_discharge_override=None,
        on_only=False,
        min_daily_runtime=None,
        max_daily_runtime=None,
        schedule_deadline=None,
        switch_interval=300,
        allow_grid_supplement=False,
        max_grid_power=None,
    )


def _make_state(
    *,
    appliance_id: str = "app1",
    is_on: bool = True,
    current_power: float = 1000.0,
    last_state_change: datetime | None = None,
) -> ApplianceState:
    return ApplianceState(
        appliance_id=appliance_id,
        is_on=is_on,
        current_power=current_power,
        current_amperage=None,
        runtime_today=timedelta(0),
        energy_today=0.0,
        last_state_change=last_state_change,
        ev_connected=None,
    )


def _make_decision(
    *,
    appliance_id: str = "app1",
    action: Action = Action.ON,
    reason: str = "Excess available (2100W >= 1800W needed)",
    overrides_plan: bool = False,
) -> ControlDecision:
    return ControlDecision(
        appliance_id=appliance_id,
        action=action,
        target_current=None,
        reason=reason,
        overrides_plan=overrides_plan,
    )


_NO_BATTERY_LIMIT = BatteryDischargeAction(should_limit=False)


class TestFormatStatusCooldown:
    """S1 — switch cooldown suffix."""

    NOW = datetime(2026, 4, 6, 12, 0, 0)

    def test_would_switch_on_within_cooldown_appends_suffix(self) -> None:
        # Decision says ON, appliance currently OFF, last change 10s ago,
        # switch_interval 60s → 50s remaining
        decision = _make_decision(
            action=Action.ON, reason="Excess available (2100W >= 1800W needed)"
        )
        state = _make_state(
            is_on=False,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text == (
            "Excess available (2100W >= 1800W needed) "
            "(switch deferred - 50s cooldown)"
        )
        assert fs.switch_deferred is True
        assert fs.cooldown_seconds_remaining == 50

    def test_would_switch_off_within_cooldown_appends_suffix(self) -> None:
        decision = _make_decision(
            action=Action.OFF, reason="Insufficient excess (1200W < 1800W needed)"
        )
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=43),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text.endswith("(switch deferred - 17s cooldown)")
        assert fs.switch_deferred is True
        assert fs.cooldown_seconds_remaining == 17

    def test_no_switch_needed_no_suffix(self) -> None:
        # Decision says ON, appliance already ON → no switch would happen
        decision = _make_decision(action=Action.ON)
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text
        assert fs.switch_deferred is False
        assert fs.cooldown_seconds_remaining is None

    def test_cooldown_elapsed_no_suffix(self) -> None:
        decision = _make_decision(action=Action.ON)
        state = _make_state(
            is_on=False,
            last_state_change=self.NOW - timedelta(seconds=120),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text
        assert fs.switch_deferred is False
        assert fs.cooldown_seconds_remaining is None

    def test_last_state_change_none_no_suffix_no_crash(self) -> None:
        decision = _make_decision(action=Action.ON)
        state = _make_state(is_on=False, last_state_change=None)
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text
        assert fs.switch_deferred is False

    def test_bypasses_cooldown_flag_suppresses_suffix(self) -> None:
        # Safety OFF decision should never show cooldown suffix even within interval
        decision = ControlDecision(
            appliance_id="app1",
            action=Action.OFF,
            target_current=None,
            reason="Max daily runtime reached (3:00:00 >= 3:00:00)",
            overrides_plan=False,
            bypasses_cooldown=True,
        )
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=5),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text
        assert fs.switch_deferred is False

    def test_idle_action_not_treated_as_switch(self) -> None:
        # IDLE while state is_on=False is not a switch — no suffix
        decision = _make_decision(action=Action.IDLE)
        state = _make_state(
            is_on=False,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text

    def test_set_current_action_not_treated_as_switch(self) -> None:
        # SET_CURRENT is a current adjustment, not an on/off switch
        decision = _make_decision(action=Action.SET_CURRENT)
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "(switch deferred" not in fs.text

    def test_multi_minute_cooldown_uses_format_duration(self) -> None:
        # Longer switch_interval → remaining > 60s → suffix uses
        # format_duration so the user sees "8min 20s" instead of "500s".
        decision = _make_decision(
            action=Action.ON, reason="Excess available (2100W >= 1800W needed)"
        )
        state = _make_state(
            is_on=False,
            last_state_change=self.NOW - timedelta(seconds=100),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=600,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text.endswith("(switch deferred - 8min 20s cooldown)")
        assert fs.switch_deferred is True
        assert fs.cooldown_seconds_remaining == 500


class TestFormatStatusBase:
    """format_status base behavior — no decorations applied."""

    def test_plain_decision_returns_reason_unchanged(self) -> None:
        decision = _make_decision(reason="Staying on (1200W drawn)")
        state = _make_state(is_on=True)
        config = _make_config()
        fs = format_status(
            decision,
            state,
            config,
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=datetime(2026, 4, 6, 12, 0, 0),
        )
        assert fs.text == "Staying on (1200W drawn)"
        assert fs.action == "on"
        assert fs.overrides_plan is False
        assert fs.cooldown_seconds_remaining is None
        assert fs.switch_deferred is False
        assert fs.headroom_watts is None
        assert fs.plan_action is None
        assert fs.plan_window_start is None
        assert fs.plan_window_end is None

    def test_action_value_is_enum_value(self) -> None:
        for action, expected in [
            (Action.ON, "on"),
            (Action.OFF, "off"),
            (Action.SET_CURRENT, "set_current"),
            (Action.IDLE, "idle"),
        ]:
            decision = _make_decision(action=action)
            fs = format_status(
                decision,
                _make_state(),
                _make_config(),
                switch_interval=300,
                battery_action=_NO_BATTERY_LIMIT,
                plan=None,
                now=datetime(2026, 4, 6, 12, 0, 0),
            )
            assert fs.action == expected


class TestFormatStatusBatterySoftLimit:
    """S3 — battery discharge soft-limit suffix."""

    NOW = datetime(2026, 4, 6, 12, 0, 0)

    def test_big_consumer_with_limit_appends_suffix(self) -> None:
        decision = _make_decision(reason="Staying on (2300W drawn)")
        state = _make_state(is_on=True)
        config = _make_config(is_big_consumer=True)
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=1500.0
        )
        fs = format_status(
            decision, state, config,
            switch_interval=300,
            battery_action=battery_action,
            plan=None,
            now=self.NOW,
        )
        assert fs.text == (
            "Staying on (2300W drawn) [battery discharge limited to 1500W]"
        )

    def test_big_consumer_no_limit_no_suffix(self) -> None:
        decision = _make_decision(reason="Staying on (2300W drawn)")
        fs = format_status(
            decision, _make_state(), _make_config(is_big_consumer=True),
            switch_interval=300,
            battery_action=BatteryDischargeAction(should_limit=False),
            plan=None,
            now=self.NOW,
        )
        assert "[battery discharge" not in fs.text

    def test_not_big_consumer_no_suffix(self) -> None:
        decision = _make_decision(reason="Staying on (2300W drawn)")
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=1500.0
        )
        fs = format_status(
            decision, _make_state(), _make_config(is_big_consumer=False),
            switch_interval=300,
            battery_action=battery_action,
            plan=None,
            now=self.NOW,
        )
        assert "[battery discharge" not in fs.text

    def test_reason_already_mentions_soc_protection_no_duplicate(self) -> None:
        decision = _make_decision(
            reason="Battery SoC protection: 28.5% < 30.0% (big consumer shed)",
            action=Action.OFF,
        )
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=0.0
        )
        fs = format_status(
            decision, _make_state(), _make_config(is_big_consumer=True),
            switch_interval=300,
            battery_action=battery_action,
            plan=None,
            now=self.NOW,
        )
        # Count: must appear exactly once (the optimizer's own text)
        assert fs.text.count("Battery SoC protection") == 1
        assert "[battery discharge" not in fs.text

    def test_max_discharge_watts_none_no_suffix(self) -> None:
        # Defensive: should_limit=True but max_discharge_watts=None
        decision = _make_decision(reason="Staying on (2300W drawn)")
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=None
        )
        fs = format_status(
            decision, _make_state(), _make_config(is_big_consumer=True),
            switch_interval=300,
            battery_action=battery_action,
            plan=None,
            now=self.NOW,
        )
        assert "[battery discharge" not in fs.text


from custom_components.pv_excess_control.models import (
    BatteryStrategy,
    BatteryTarget,
    Plan,
    PlanEntry,
    TariffWindow,
)
from custom_components.pv_excess_control.const import PlanReason


def _make_plan(entries: list[PlanEntry]) -> Plan:
    return Plan(
        created_at=datetime(2026, 4, 6, 11, 0, 0),
        horizon=timedelta(hours=8),
        entries=entries,
        battery_target=BatteryTarget(
            target_soc=80.0,
            target_time=datetime(2026, 4, 6, 18, 0, 0),
            strategy=BatteryStrategy.BALANCED,
        ),
        confidence=0.75,
    )


def _make_plan_entry(
    *,
    appliance_id: str = "app1",
    action: Action = Action.OFF,
    window_start: datetime,
    window_end: datetime,
) -> PlanEntry:
    return PlanEntry(
        appliance_id=appliance_id,
        action=action,
        target_current=None,
        window=TariffWindow(
            start=window_start,
            end=window_end,
            price=0.20,
            is_cheap=False,
        ),
        reason=PlanReason.EXCESS_AVAILABLE,
        priority=100,
    )


class TestFormatStatusPlanDeviation:
    """S4 — plan deviation suffix."""

    NOW = datetime(2026, 4, 6, 14, 30, 0)

    def test_overrides_plan_with_matching_entry_appends_detail(self) -> None:
        entry = _make_plan_entry(
            action=Action.OFF,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        decision = _make_decision(
            reason="Deadline must-run: 30min remaining, deadline 15:00 (in 30min)",
            overrides_plan=True,
        )
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert fs.text == (
            "Deadline must-run: 30min remaining, deadline 15:00 (in 30min) "
            "[plan wanted: OFF during 14:00-15:00]"
        )
        assert fs.overrides_plan is True
        assert fs.plan_action == "off"
        assert fs.plan_window_start == datetime(2026, 4, 6, 14, 0, 0)
        assert fs.plan_window_end == datetime(2026, 4, 6, 15, 0, 0)

    def test_overrides_plan_no_matching_entry_falls_back(self) -> None:
        plan = _make_plan([])
        decision = _make_decision(reason="Manual override active", overrides_plan=True)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert fs.text == "Manual override active [overrides plan]"
        assert fs.overrides_plan is True
        assert fs.plan_action is None
        assert fs.plan_window_start is None
        assert fs.plan_window_end is None

    def test_overrides_plan_with_no_plan_falls_back(self) -> None:
        decision = _make_decision(reason="Manual override active", overrides_plan=True)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text == "Manual override active [overrides plan]"

    def test_plan_entry_outside_window_no_match(self) -> None:
        entry = _make_plan_entry(
            action=Action.OFF,
            window_start=datetime(2026, 4, 6, 16, 0, 0),
            window_end=datetime(2026, 4, 6, 17, 0, 0),
        )
        plan = _make_plan([entry])
        decision = _make_decision(
            reason="Excess available (2100W >= 1800W needed)",
            overrides_plan=True,
        )
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert fs.text == (
            "Excess available (2100W >= 1800W needed) [overrides plan]"
        )

    def test_plan_entry_for_different_appliance_no_match(self) -> None:
        entry = _make_plan_entry(
            appliance_id="other",
            action=Action.OFF,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        decision = _make_decision(
            reason="Excess available (2100W >= 1800W needed)",
            overrides_plan=True,
        )
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert fs.text.endswith("[overrides plan]")

    def test_overrides_plan_false_no_suffix(self) -> None:
        decision = _make_decision(reason="Excess available", overrides_plan=False)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert "plan" not in fs.text.lower()
        assert fs.overrides_plan is False

    def test_overrides_plan_but_actions_agree_no_suffix(self) -> None:
        # Manual override sets overrides_plan=True and decision.action=ON.
        # The plan also has an ON entry for the current window. The "override"
        # is functionally a no-op — the formatter should suppress the plan
        # suffix because there is no actual disagreement to surface.
        entry = _make_plan_entry(
            action=Action.ON,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        decision = _make_decision(
            action=Action.ON,
            reason="Manual override active",
            overrides_plan=True,
        )
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert fs.text == "Manual override active"
        assert fs.overrides_plan is True  # optimizer's flag is preserved
        assert fs.plan_action is None
        assert fs.plan_window_start is None
        assert fs.plan_window_end is None

    def test_set_current_plan_action_renders_without_underscore(self) -> None:
        # Action.SET_CURRENT.value is "set_current"; the suffix should
        # render it as "SET CURRENT" rather than "SET_CURRENT" so it
        # reads as a human phrase rather than a code identifier.
        entry = _make_plan_entry(
            action=Action.SET_CURRENT,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        decision = _make_decision(
            action=Action.OFF,  # different from plan → suffix should fire
            reason="Max daily runtime reached",
            overrides_plan=True,
        )
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=plan,
            now=self.NOW,
        )
        assert "[plan wanted: SET CURRENT during 14:00-15:00]" in fs.text
        assert "SET_CURRENT" not in fs.text
        assert fs.plan_action == "set_current"  # raw value for card use


class TestFormatStatusCombined:
    """Combined decorations — order and length guards."""

    NOW = datetime(2026, 4, 6, 14, 30, 0)

    def test_all_three_suffixes_in_order(self) -> None:
        # Cooldown → battery → plan
        decision = _make_decision(
            action=Action.OFF,
            reason="Insufficient excess (1200W < 1800W needed)",
            overrides_plan=True,
        )
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        config = _make_config(is_big_consumer=True)
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=1500.0
        )
        entry = _make_plan_entry(
            action=Action.ON,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        fs = format_status(
            decision, state, config,
            switch_interval=60,
            battery_action=battery_action,
            plan=plan,
            now=self.NOW,
        )
        expected = (
            "Insufficient excess (1200W < 1800W needed) "
            "(switch deferred - 50s cooldown) "
            "[battery discharge limited to 1500W] "
            "[plan wanted: ON during 14:00-15:00]"
        )
        assert fs.text == expected

    def test_long_text_truncated_to_255_chars(self) -> None:
        # Construct a pathological base reason long enough to force truncation
        long_reason = "x" * 300
        decision = _make_decision(reason=long_reason)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert len(fs.text) == 255
        assert fs.text.endswith("...")

    def test_exactly_255_char_reason_not_truncated(self) -> None:
        # Boundary: 255 chars with no suffixes — must pass through unchanged
        reason = "x" * 255
        decision = _make_decision(reason=reason)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text == reason
        assert len(fs.text) == 255

    def test_exactly_254_char_reason_not_truncated(self) -> None:
        # Boundary: just under the limit
        reason = "x" * 254
        decision = _make_decision(reason=reason)
        fs = format_status(
            decision, _make_state(), _make_config(),
            switch_interval=300,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        assert fs.text == reason
        assert len(fs.text) == 254

    def test_long_reason_with_suffix_preserves_suffix_intact(self) -> None:
        # The base reason is too long, but the cooldown suffix must
        # survive whole — only the reason gets truncated.
        long_reason = "x" * 250  # base reason already nearly fills the budget
        decision = _make_decision(
            action=Action.ON,
            reason=long_reason,
        )
        state = _make_state(
            is_on=False,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        fs = format_status(
            decision, state, _make_config(),
            switch_interval=60,
            battery_action=_NO_BATTERY_LIMIT,
            plan=None,
            now=self.NOW,
        )
        cooldown_suffix = " (switch deferred - 50s cooldown)"
        # The full suffix must appear at the end with no truncation
        assert fs.text.endswith(cooldown_suffix)
        # The base reason must have been truncated and end with "..."
        truncated_reason = fs.text[: -len(cooldown_suffix)]
        assert truncated_reason.endswith("...")
        # Total length must respect the cap
        assert len(fs.text) == 255

    def test_partial_suffix_suppression_cooldown_plus_plan_only(self) -> None:
        # Battery suffix is suppressed (is_big_consumer=False), so only
        # cooldown and plan fire — verify they appear in the right order
        # and the battery suffix really is absent.
        decision = _make_decision(
            action=Action.OFF,
            reason="Insufficient excess (1200W < 1800W needed)",
            overrides_plan=True,
        )
        state = _make_state(
            is_on=True,
            last_state_change=self.NOW - timedelta(seconds=10),
        )
        config = _make_config(is_big_consumer=False)  # battery suffix off
        battery_action = BatteryDischargeAction(
            should_limit=True, max_discharge_watts=1500.0
        )
        entry = _make_plan_entry(
            action=Action.ON,
            window_start=datetime(2026, 4, 6, 14, 0, 0),
            window_end=datetime(2026, 4, 6, 15, 0, 0),
        )
        plan = _make_plan([entry])
        fs = format_status(
            decision, state, config,
            switch_interval=60,
            battery_action=battery_action,
            plan=plan,
            now=self.NOW,
        )
        expected = (
            "Insufficient excess (1200W < 1800W needed) "
            "(switch deferred - 50s cooldown) "
            "[plan wanted: ON during 14:00-15:00]"
        )
        assert fs.text == expected
        assert "[battery discharge" not in fs.text

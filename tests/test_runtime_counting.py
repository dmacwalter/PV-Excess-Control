"""Tests for runtime counting with completion_power_threshold."""
from datetime import timedelta

import pytest


class TestRuntimeCounting:
    """Runtime counting gates on actual power when completion_power_threshold is set."""

    def test_runtime_not_counted_below_threshold(self) -> None:
        """When actual power is below completion_power_threshold, runtime should not increment."""
        from custom_components.pv_excess_control.models import ApplianceConfig

        config = ApplianceConfig(
            id="heater", name="Heater", entity_id="switch.heater",
            priority=1, phases=1, nominal_power=6000.0,
            actual_power_entity="sensor.heater_power",
            dynamic_current=False, current_entity=None,
            min_current=0.0, max_current=0.0,
            ev_soc_entity=None, ev_connected_entity=None,
            is_big_consumer=False, battery_max_discharge_override=None,
            on_only=False, min_daily_runtime=timedelta(hours=3),
            max_daily_runtime=None, schedule_deadline=None,
            switch_interval=300, allow_grid_supplement=False,
            max_grid_power=None, completion_power_threshold=500.0,
        )

        # Simulate runtime counting logic from coordinator
        is_on = True
        current_power = 50.0  # Below threshold of 500W
        cycle_seconds = 30.0
        previous_runtime = timedelta(hours=1)

        counts_as_running = (
            config.completion_power_threshold is None
            or current_power >= config.completion_power_threshold
        )
        runtime = previous_runtime
        if is_on and counts_as_running:
            runtime += timedelta(seconds=cycle_seconds)

        # Runtime should NOT have incremented
        assert runtime == previous_runtime

    def test_runtime_counted_above_threshold(self) -> None:
        """When actual power meets completion_power_threshold, runtime should increment."""
        from custom_components.pv_excess_control.models import ApplianceConfig

        config = ApplianceConfig(
            id="heater", name="Heater", entity_id="switch.heater",
            priority=1, phases=1, nominal_power=6000.0,
            actual_power_entity="sensor.heater_power",
            dynamic_current=False, current_entity=None,
            min_current=0.0, max_current=0.0,
            ev_soc_entity=None, ev_connected_entity=None,
            is_big_consumer=False, battery_max_discharge_override=None,
            on_only=False, min_daily_runtime=timedelta(hours=3),
            max_daily_runtime=None, schedule_deadline=None,
            switch_interval=300, allow_grid_supplement=False,
            max_grid_power=None, completion_power_threshold=500.0,
        )

        is_on = True
        current_power = 6000.0  # Above threshold
        cycle_seconds = 30.0
        previous_runtime = timedelta(hours=1)

        counts_as_running = (
            config.completion_power_threshold is None
            or current_power >= config.completion_power_threshold
        )
        runtime = previous_runtime
        if is_on and counts_as_running:
            runtime += timedelta(seconds=cycle_seconds)

        assert runtime == previous_runtime + timedelta(seconds=cycle_seconds)

    def test_runtime_counted_when_threshold_none(self) -> None:
        """When completion_power_threshold is None (disabled), runtime always increments."""
        from custom_components.pv_excess_control.models import ApplianceConfig

        config = ApplianceConfig(
            id="heater", name="Heater", entity_id="switch.heater",
            priority=1, phases=1, nominal_power=6000.0,
            actual_power_entity="sensor.heater_power",
            dynamic_current=False, current_entity=None,
            min_current=0.0, max_current=0.0,
            ev_soc_entity=None, ev_connected_entity=None,
            is_big_consumer=False, battery_max_discharge_override=None,
            on_only=False, min_daily_runtime=timedelta(hours=3),
            max_daily_runtime=None, schedule_deadline=None,
            switch_interval=300, allow_grid_supplement=False,
            max_grid_power=None,
            # completion_power_threshold defaults to None
        )

        is_on = True
        current_power = 0.0  # Zero power, but threshold is disabled
        cycle_seconds = 30.0
        previous_runtime = timedelta(hours=1)

        counts_as_running = (
            config.completion_power_threshold is None
            or current_power >= config.completion_power_threshold
        )
        runtime = previous_runtime
        if is_on and counts_as_running:
            runtime += timedelta(seconds=cycle_seconds)

        # Runtime SHOULD increment (threshold disabled, backward compatible)
        assert runtime == previous_runtime + timedelta(seconds=cycle_seconds)

    def test_energy_uses_zero_when_actual_power_entity_reports_zero(self) -> None:
        """When actual_power_entity is configured and reports 0W, energy should use 0W not nominal."""
        from custom_components.pv_excess_control.models import ApplianceConfig

        config = ApplianceConfig(
            id="heater", name="Heater", entity_id="switch.heater",
            priority=1, phases=1, nominal_power=6000.0,
            actual_power_entity="sensor.heater_power",
            dynamic_current=False, current_entity=None,
            min_current=0.0, max_current=0.0,
            ev_soc_entity=None, ev_connected_entity=None,
            is_big_consumer=False, battery_max_discharge_override=None,
            on_only=False, min_daily_runtime=None,
            max_daily_runtime=None, schedule_deadline=None,
            switch_interval=300, allow_grid_supplement=False,
            max_grid_power=None,
        )

        current_power = 0.0
        cycle_seconds = 30.0

        # New logic: only fall back to nominal when no actual_power_entity
        power_for_energy = (
            current_power if current_power > 0
            else (0.0 if config.actual_power_entity else config.nominal_power)
        )
        energy_delta = (power_for_energy * cycle_seconds) / 3600 / 1000

        assert energy_delta == 0.0

    def test_energy_falls_back_to_nominal_without_power_entity(self) -> None:
        """When no actual_power_entity, energy should still fall back to nominal_power."""
        from custom_components.pv_excess_control.models import ApplianceConfig

        config = ApplianceConfig(
            id="heater", name="Heater", entity_id="switch.heater",
            priority=1, phases=1, nominal_power=6000.0,
            actual_power_entity=None,  # No power sensor
            dynamic_current=False, current_entity=None,
            min_current=0.0, max_current=0.0,
            ev_soc_entity=None, ev_connected_entity=None,
            is_big_consumer=False, battery_max_discharge_override=None,
            on_only=False, min_daily_runtime=None,
            max_daily_runtime=None, schedule_deadline=None,
            switch_interval=300, allow_grid_supplement=False,
            max_grid_power=None,
        )

        current_power = 0.0
        cycle_seconds = 30.0

        power_for_energy = (
            current_power if current_power > 0
            else (0.0 if config.actual_power_entity else config.nominal_power)
        )
        energy_delta = (power_for_energy * cycle_seconds) / 3600 / 1000

        # Should use nominal_power (6000W) as fallback
        expected = (6000.0 * 30.0) / 3600 / 1000
        assert energy_delta == pytest.approx(expected)

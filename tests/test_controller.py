"""Tests for PV Excess Control controller module."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.pv_excess_control.const import (
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_GRID_EXPORT,
    CONF_IMPORT_EXPORT,
    CONF_LOAD_POWER,
    CONF_PV_POWER,
)
from custom_components.pv_excess_control.controller import Controller
from custom_components.pv_excess_control.models import (
    Action,
    ApplianceConfig,
    ApplianceState,
    BatteryDischargeAction,
    ControlDecision,
    PowerState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)


def _make_appliance_config(**kwargs) -> ApplianceConfig:
    """Return a minimal ApplianceConfig with sensible defaults."""
    defaults = dict(
        id="appliance_1",
        name="Washing Machine",
        entity_id="switch.washing_machine",
        priority=100,
        phases=1,
        nominal_power=2000.0,
        actual_power_entity=None,
        dynamic_current=False,
        current_entity=None,
        min_current=0.0,
        max_current=16.0,
        ev_soc_entity=None,
        ev_connected_entity=None,
        is_big_consumer=False,
        battery_max_discharge_override=None,
        on_only=False,
        min_daily_runtime=None,
        max_daily_runtime=None,
        schedule_deadline=None,
        switch_interval=300,
        allow_grid_supplement=False,
        max_grid_power=None,
    )
    defaults.update(kwargs)
    return ApplianceConfig(**defaults)


def _make_state(entity_id: str, state_value: str, attributes: dict | None = None) -> MagicMock:
    """Create a mock HA state object."""
    mock_state = MagicMock()
    mock_state.state = state_value
    mock_state.attributes = attributes or {}
    return mock_state


def _make_hass(states_map: dict[str, MagicMock] | None = None) -> MagicMock:
    """Create a mock HomeAssistant object."""
    hass = MagicMock()
    hass.states = MagicMock()

    if states_map is None:
        states_map = {}

    def get_state(entity_id: str):
        return states_map.get(entity_id)

    hass.states.get = MagicMock(side_effect=get_state)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    return hass


# ---------------------------------------------------------------------------
# TestCollectPowerState
# ---------------------------------------------------------------------------

class TestCollectPowerState:
    def test_collect_power_state(self):
        """Controller reads sensors and builds PowerState."""
        states_map = {
            "sensor.pv_power": _make_state("sensor.pv_power", "5000.0"),
            "sensor.grid_export": _make_state("sensor.grid_export", "1200.0"),
            "sensor.load_power": _make_state("sensor.load_power", "3800.0"),
            "sensor.battery_soc": _make_state("sensor.battery_soc", "80.5"),
            "sensor.battery_power": _make_state("sensor.battery_power", "500.0"),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_GRID_EXPORT: "sensor.grid_export",
            CONF_LOAD_POWER: "sensor.load_power",
            CONF_BATTERY_SOC: "sensor.battery_soc",
            CONF_BATTERY_POWER: "sensor.battery_power",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert isinstance(ps, PowerState)
        assert ps.pv_production == 5000.0
        assert ps.grid_export == 1200.0
        assert ps.grid_import == 0.0
        assert ps.load_power == 3800.0
        assert ps.battery_soc == 80.5
        assert ps.battery_power == 500.0
        # excess = pv - load = 5000 - 3800 = 1200
        assert ps.excess_power == 1200.0

    def test_collect_power_state_combined_sensor(self):
        """Controller handles combined import/export sensor."""
        states_map = {
            "sensor.pv_power": _make_state("sensor.pv_power", "3000.0"),
            "sensor.import_export": _make_state("sensor.import_export", "-500.0"),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_IMPORT_EXPORT: "sensor.import_export",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        # Combined sensor: positive = export, negative = import
        assert ps.grid_export == 0.0
        assert ps.grid_import == 500.0
        # No load sensor, so excess = grid_export - grid_import = 0 - 500 = -500
        assert ps.excess_power == -500.0

    def test_collect_power_state_combined_sensor_exporting(self):
        """Combined sensor positive means exporting."""
        states_map = {
            "sensor.pv_power": _make_state("sensor.pv_power", "5000.0"),
            "sensor.import_export": _make_state("sensor.import_export", "2000.0"),
            "sensor.load_power": _make_state("sensor.load_power", "3000.0"),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_IMPORT_EXPORT: "sensor.import_export",
            CONF_LOAD_POWER: "sensor.load_power",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.grid_export == 2000.0
        assert ps.grid_import == 0.0
        assert ps.excess_power == 2000.0  # pv - load = 5000 - 3000

    def test_collect_power_state_unavailable(self):
        """Unavailable sensors return 0."""
        states_map = {
            "sensor.pv_power": _make_state("sensor.pv_power", "unavailable"),
            "sensor.grid_export": _make_state("sensor.grid_export", "unknown"),
            "sensor.load_power": _make_state("sensor.load_power", ""),
            "sensor.battery_soc": _make_state("sensor.battery_soc", "none"),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_GRID_EXPORT: "sensor.grid_export",
            CONF_LOAD_POWER: "sensor.load_power",
            CONF_BATTERY_SOC: "sensor.battery_soc",
            CONF_BATTERY_POWER: "sensor.battery_power_missing",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.pv_production == 0.0
        assert ps.grid_export == 0.0
        assert ps.load_power == 0.0
        assert ps.battery_soc is None
        assert ps.battery_power is None

    def test_collect_power_state_no_sensors_configured(self):
        """Missing sensor config returns defaults."""
        hass = _make_hass()
        config_data = {}
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.pv_production == 0.0
        assert ps.grid_export == 0.0
        assert ps.grid_import == 0.0
        assert ps.load_power == 0.0
        assert ps.excess_power == 0.0
        assert ps.battery_soc is None
        assert ps.battery_power is None

    def test_collect_power_state_kw_sensors_converted_to_watts(self):
        """Power sensors reporting in kW are converted to watts."""
        states_map = {
            "sensor.pv_power": _make_state(
                "sensor.pv_power", "9.9",
                attributes={"unit_of_measurement": "kW"},
            ),
            "sensor.grid_export": _make_state(
                "sensor.grid_export", "4.8",
                attributes={"unit_of_measurement": "kW"},
            ),
            "sensor.load_power": _make_state(
                "sensor.load_power", "5.1",
                attributes={"unit_of_measurement": "kW"},
            ),
            "sensor.battery_power": _make_state(
                "sensor.battery_power", "0.5",
                attributes={"unit_of_measurement": "kW"},
            ),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_GRID_EXPORT: "sensor.grid_export",
            CONF_LOAD_POWER: "sensor.load_power",
            CONF_BATTERY_POWER: "sensor.battery_power",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.pv_production == pytest.approx(9900.0)
        assert ps.grid_export == pytest.approx(4800.0)
        assert ps.load_power == pytest.approx(5100.0)
        assert ps.battery_power == pytest.approx(500.0)

    def test_collect_power_state_w_sensors_not_double_converted(self):
        """Power sensors already in W are not modified."""
        states_map = {
            "sensor.pv_power": _make_state(
                "sensor.pv_power", "5000.0",
                attributes={"unit_of_measurement": "W"},
            ),
            "sensor.grid_export": _make_state(
                "sensor.grid_export", "1200.0",
                attributes={"unit_of_measurement": "W"},
            ),
        }
        hass = _make_hass(states_map)
        config_data = {
            CONF_PV_POWER: "sensor.pv_power",
            CONF_GRID_EXPORT: "sensor.grid_export",
        }
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.pv_production == 5000.0
        assert ps.grid_export == 1200.0

    def test_collect_power_state_no_unit_attribute_assumes_watts(self):
        """Sensors without unit_of_measurement attribute are treated as watts."""
        states_map = {
            "sensor.pv_power": _make_state("sensor.pv_power", "5000.0"),
        }
        hass = _make_hass(states_map)
        config_data = {CONF_PV_POWER: "sensor.pv_power"}
        controller = Controller(hass, config_data)
        ps = controller.collect_power_state()

        assert ps.pv_production == 5000.0


# ---------------------------------------------------------------------------
# TestCollectApplianceStates
# ---------------------------------------------------------------------------

class TestCollectApplianceStates:
    def test_collect_appliance_states_on(self):
        """Reads on state and actual power from entity."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "on"),
            "sensor.wm_power": _make_state("sensor.wm_power", "1800.0"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            actual_power_entity="sensor.wm_power",
        )]
        runtime_tracker = {"appliance_1": timedelta(hours=1, minutes=30)}
        result = controller.collect_appliance_states(configs, runtime_tracker)

        assert len(result) == 1
        state = result[0]
        assert state.appliance_id == "appliance_1"
        assert state.is_on is True
        assert state.current_power == 1800.0
        assert state.runtime_today == timedelta(hours=1, minutes=30)

    def test_collect_appliance_states_actual_power_kw_converted(self):
        """Appliance actual_power_entity in kW is converted to watts."""
        states_map = {
            "switch.tesla_charge": _make_state("switch.tesla_charge", "on"),
            "sensor.twc_total_power": _make_state(
                "sensor.twc_total_power", "5.07",
                attributes={"unit_of_measurement": "kW"},
            ),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="tesla",
            entity_id="switch.tesla_charge",
            actual_power_entity="sensor.twc_total_power",
        )]
        result = controller.collect_appliance_states(configs, {})

        state = result[0]
        assert state.current_power == pytest.approx(5070.0)

    def test_collect_appliance_states_off(self):
        """Reads off state."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config()]
        result = controller.collect_appliance_states(configs, {})

        assert len(result) == 1
        state = result[0]
        assert state.is_on is False
        assert state.current_power == 0.0
        assert state.runtime_today == timedelta()

    def test_collect_appliance_states_ev_connected(self):
        """Reads EV connected binary sensor."""
        states_map = {
            "switch.ev_charger": _make_state("switch.ev_charger", "on"),
            "binary_sensor.ev_connected": _make_state("binary_sensor.ev_connected", "on"),
            "number.ev_current": _make_state("number.ev_current", "10"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="ev_charger",
            entity_id="switch.ev_charger",
            ev_connected_entity="binary_sensor.ev_connected",
            current_entity="number.ev_current",
            dynamic_current=True,
        )]
        result = controller.collect_appliance_states(configs, {})

        assert result[0].ev_connected is True
        assert result[0].current_amperage == 10.0

    def test_collect_appliance_states_ev_disconnected(self):
        """Reads EV disconnected binary sensor."""
        states_map = {
            "switch.ev_charger": _make_state("switch.ev_charger", "off"),
            "binary_sensor.ev_connected": _make_state("binary_sensor.ev_connected", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="ev_charger",
            entity_id="switch.ev_charger",
            ev_connected_entity="binary_sensor.ev_connected",
        )]
        result = controller.collect_appliance_states(configs, {})

        assert result[0].ev_connected is False

    def test_collect_appliance_states_entity_missing(self):
        """Missing entity returns is_on=False."""
        hass = _make_hass()
        controller = Controller(hass, {})
        configs = [_make_appliance_config(entity_id="switch.nonexistent")]
        result = controller.collect_appliance_states(configs, {})

        assert result[0].is_on is False
        assert result[0].current_power == 0.0


# ---------------------------------------------------------------------------
# TestApplyDecisions
# ---------------------------------------------------------------------------

class TestApplyDecisions:
    @pytest.mark.asyncio
    async def test_apply_switch_on(self):
        """Applies turn_on for switch domain."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config()]
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="Excess available",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        assert applied[0]["appliance_id"] == "appliance_1"
        assert applied[0]["action"] == Action.ON
        hass.services.async_call.assert_any_call(
            "switch", "turn_on", {"entity_id": "switch.washing_machine"}
        )

    @pytest.mark.asyncio
    async def test_apply_switch_off(self):
        """Applies turn_off for switch domain."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config()]
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.OFF,
                target_current=None,
                reason="Insufficient excess",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        assert applied[0]["action"] == Action.OFF
        hass.services.async_call.assert_any_call(
            "switch", "turn_off", {"entity_id": "switch.washing_machine"}
        )

    @pytest.mark.asyncio
    async def test_apply_climate_on(self):
        """Applies turn_on for climate domain."""
        states_map = {
            "climate.heat_pump": _make_state("climate.heat_pump", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="heat_pump",
            entity_id="climate.heat_pump",
        )]
        decisions = [
            ControlDecision(
                appliance_id="heat_pump",
                action=Action.ON,
                target_current=None,
                reason="Excess available",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        hass.services.async_call.assert_any_call(
            "climate", "turn_on", {"entity_id": "climate.heat_pump"}
        )

    @pytest.mark.asyncio
    async def test_apply_set_current(self):
        """Applies set_value for dynamic current."""
        states_map = {
            "switch.ev_charger": _make_state("switch.ev_charger", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="ev_charger",
            entity_id="switch.ev_charger",
            dynamic_current=True,
            current_entity="number.ev_current",
        )]
        decisions = [
            ControlDecision(
                appliance_id="ev_charger",
                action=Action.SET_CURRENT,
                target_current=10.0,
                reason="Dynamic current set to 10A",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        assert applied[0]["action"] == Action.SET_CURRENT
        hass.services.async_call.assert_any_call(
            "number", "set_value",
            {"entity_id": "number.ev_current", "value": 10.0},
        )

    @pytest.mark.asyncio
    async def test_apply_idle_skipped(self):
        """IDLE decisions are not applied."""
        hass = _make_hass()
        controller = Controller(hass, {})
        configs = [_make_appliance_config()]
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.IDLE,
                target_current=None,
                reason="No change needed",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 0
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_unknown_appliance_skipped(self):
        """Decisions for unknown appliance IDs are skipped."""
        hass = _make_hass()
        controller = Controller(hass, {})
        configs = [_make_appliance_config(id="app_1")]
        decisions = [
            ControlDecision(
                appliance_id="unknown_id",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 0

    @pytest.mark.asyncio
    async def test_no_change_when_already_desired_state(self):
        """Won't call service if entity is already in the desired state."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config()]
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="Excess available",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        # Should not apply since already ON
        assert len(applied) == 0
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_input_boolean_on(self):
        """Applies turn_on for input_boolean domain."""
        states_map = {
            "input_boolean.my_toggle": _make_state("input_boolean.my_toggle", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="toggle_1",
            entity_id="input_boolean.my_toggle",
        )]
        decisions = [
            ControlDecision(
                appliance_id="toggle_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        hass.services.async_call.assert_any_call(
            "input_boolean", "turn_on", {"entity_id": "input_boolean.my_toggle"}
        )

    @pytest.mark.asyncio
    async def test_apply_light_off(self):
        """Applies turn_off for light domain."""
        states_map = {
            "light.my_light": _make_state("light.my_light", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="light_1",
            entity_id="light.my_light",
        )]
        decisions = [
            ControlDecision(
                appliance_id="light_1",
                action=Action.OFF,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        hass.services.async_call.assert_any_call(
            "light", "turn_off", {"entity_id": "light.my_light"}
        )

    @pytest.mark.asyncio
    async def test_apply_water_heater_on(self):
        """Applies turn_on for water_heater domain."""
        states_map = {
            "water_heater.boiler": _make_state("water_heater.boiler", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        configs = [_make_appliance_config(
            id="boiler_1",
            entity_id="water_heater.boiler",
        )]
        decisions = [
            ControlDecision(
                appliance_id="boiler_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, configs)

        assert len(applied) == 1
        hass.services.async_call.assert_any_call(
            "water_heater", "turn_on", {"entity_id": "water_heater.boiler"}
        )


# ---------------------------------------------------------------------------
# TestSwitchInterval
# ---------------------------------------------------------------------------

class TestSwitchInterval:
    @pytest.mark.asyncio
    async def test_switch_interval_blocks(self):
        """Won't change state if switch interval hasn't elapsed."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)

        # Simulate a recent state change
        controller._last_state_change["appliance_1"] = datetime.now()

        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, [config])

        assert len(applied) == 0
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_switch_interval_allows_after_elapsed(self):
        """Allows change after switch interval has elapsed."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)

        # Simulate a state change long ago
        controller._last_state_change["appliance_1"] = (
            datetime.now() - timedelta(seconds=600)
        )

        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, [config])

        assert len(applied) == 1

    @pytest.mark.asyncio
    async def test_switch_interval_allows_first_change(self):
        """First change is always allowed (no previous state change)."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)

        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, [config])

        assert len(applied) == 1


# ---------------------------------------------------------------------------
# TestOnOnlyPreventsOff
# ---------------------------------------------------------------------------

class TestOnOnly:
    @pytest.mark.asyncio
    async def test_on_only_prevents_off(self):
        """on_only flag prevents turn_off."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config(on_only=True)
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.OFF,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, [config])

        # Decision is skipped because on_only prevents OFF
        assert len(applied) == 0
        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_only_allows_on(self):
        """on_only flag does not prevent turn_on."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config(on_only=True)
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        applied = await controller.apply_decisions(decisions, [config])

        assert len(applied) == 1


# ---------------------------------------------------------------------------
# TestFiresEvent
# ---------------------------------------------------------------------------

class TestFiresEvent:
    @pytest.mark.asyncio
    async def test_fires_event_on_change(self):
        """Fires HA event when appliance state changes."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config()
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="Excess available",
                overrides_plan=False,
            ),
        ]

        await controller.apply_decisions(decisions, [config])

        hass.bus.async_fire.assert_called_once_with(
            "pv_excess_control.appliance_switched",
            {
                "appliance_id": "appliance_1",
                "appliance_name": "Washing Machine",
                "action": Action.ON,
                "reason": "Excess available",
            },
        )

    @pytest.mark.asyncio
    async def test_no_event_when_no_change(self):
        """No event fired when no state change occurs."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config()
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        await controller.apply_decisions(decisions, [config])

        hass.bus.async_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_last_state_change(self):
        """Records last state change time when decision is applied."""
        states_map = {
            "switch.washing_machine": _make_state("switch.washing_machine", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})
        config = _make_appliance_config()
        decisions = [
            ControlDecision(
                appliance_id="appliance_1",
                action=Action.ON,
                target_current=None,
                reason="test",
                overrides_plan=False,
            ),
        ]

        before = datetime.now()
        await controller.apply_decisions(decisions, [config])
        after = datetime.now()

        last = controller._last_state_change.get("appliance_1")
        assert last is not None
        assert before <= last <= after


# ---------------------------------------------------------------------------
# TestBatteryDischargeLimit
# ---------------------------------------------------------------------------

class TestBatteryDischargeLimit:
    @pytest.mark.asyncio
    async def test_battery_discharge_limit_set(self):
        """Sets battery discharge limit when big consumer active."""
        hass = _make_hass()
        controller = Controller(hass, {})

        action = BatteryDischargeAction(should_limit=True, max_discharge_watts=500.0)
        await controller.apply_battery_discharge_limit(
            action,
            max_discharge_entity="number.battery_max_discharge",
            max_discharge_default=5000.0,
        )

        hass.services.async_call.assert_called_once_with(
            "number", "set_value",
            {"entity_id": "number.battery_max_discharge", "value": 500.0},
        )

    @pytest.mark.asyncio
    async def test_battery_discharge_limit_restore(self):
        """Restores discharge limit when no big consumers."""
        hass = _make_hass()
        controller = Controller(hass, {})

        action = BatteryDischargeAction(should_limit=False)
        await controller.apply_battery_discharge_limit(
            action,
            max_discharge_entity="number.battery_max_discharge",
            max_discharge_default=5000.0,
        )

        hass.services.async_call.assert_called_once_with(
            "number", "set_value",
            {"entity_id": "number.battery_max_discharge", "value": 5000.0},
        )

    @pytest.mark.asyncio
    async def test_battery_discharge_limit_no_entity(self):
        """No service call when no discharge entity configured."""
        hass = _make_hass()
        controller = Controller(hass, {})

        action = BatteryDischargeAction(should_limit=True, max_discharge_watts=500.0)
        await controller.apply_battery_discharge_limit(
            action,
            max_discharge_entity=None,
            max_discharge_default=5000.0,
        )

        hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_battery_discharge_limit_no_default(self):
        """No restore when no default configured and not limiting."""
        hass = _make_hass()
        controller = Controller(hass, {})

        action = BatteryDischargeAction(should_limit=False)
        await controller.apply_battery_discharge_limit(
            action,
            max_discharge_entity="number.battery_max_discharge",
            max_discharge_default=None,
        )

        hass.services.async_call.assert_not_called()


# ---------------------------------------------------------------------------
# TestSensorHelpers
# ---------------------------------------------------------------------------

class TestSensorHelpers:
    def test_read_sensor_valid(self):
        """Reads a valid numeric sensor."""
        states_map = {
            "sensor.power": _make_state("sensor.power", "1234.5"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_sensor("sensor.power") == 1234.5

    def test_read_sensor_unavailable(self):
        """Returns default for unavailable sensor."""
        states_map = {
            "sensor.power": _make_state("sensor.power", "unavailable"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_sensor("sensor.power") == 0.0
        assert controller._read_sensor("sensor.power", default=42.0) == 42.0

    def test_read_sensor_unknown(self):
        """Returns default for unknown sensor."""
        states_map = {
            "sensor.power": _make_state("sensor.power", "unknown"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_sensor("sensor.power") == 0.0

    def test_read_sensor_none_entity(self):
        """Returns default when entity_id is None."""
        hass = _make_hass()
        controller = Controller(hass, {})

        assert controller._read_sensor(None) == 0.0

    def test_read_sensor_missing_entity(self):
        """Returns default when entity does not exist."""
        hass = _make_hass()
        controller = Controller(hass, {})

        assert controller._read_sensor("sensor.nonexistent") == 0.0

    def test_read_sensor_non_numeric(self):
        """Returns default for non-numeric state."""
        states_map = {
            "sensor.power": _make_state("sensor.power", "not_a_number"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_sensor("sensor.power") == 0.0

    def test_read_binary_on(self):
        """Reads binary sensor that is on."""
        states_map = {
            "binary_sensor.connected": _make_state("binary_sensor.connected", "on"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_binary("binary_sensor.connected") is True

    def test_read_binary_off(self):
        """Reads binary sensor that is off."""
        states_map = {
            "binary_sensor.connected": _make_state("binary_sensor.connected", "off"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_binary("binary_sensor.connected") is False

    def test_read_binary_unavailable(self):
        """Returns None for unavailable binary sensor."""
        states_map = {
            "binary_sensor.connected": _make_state("binary_sensor.connected", "unavailable"),
        }
        hass = _make_hass(states_map)
        controller = Controller(hass, {})

        assert controller._read_binary("binary_sensor.connected") is None

    def test_read_binary_none_entity(self):
        """Returns None when entity_id is None."""
        hass = _make_hass()
        controller = Controller(hass, {})

        assert controller._read_binary(None) is None

    def test_read_binary_missing_entity(self):
        """Returns None when entity does not exist."""
        hass = _make_hass()
        controller = Controller(hass, {})

        assert controller._read_binary("binary_sensor.nonexistent") is None


# ---------------------------------------------------------------------------
# TestCanChangeState
# ---------------------------------------------------------------------------

class TestCanChangeState:
    def test_can_change_no_previous(self):
        """Can change state when no previous change recorded."""
        hass = _make_hass()
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)

        assert controller._can_change_state(config) is True

    def test_cannot_change_too_soon(self):
        """Cannot change state when interval hasn't elapsed."""
        hass = _make_hass()
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)
        controller._last_state_change["appliance_1"] = datetime.now()

        assert controller._can_change_state(config) is False

    def test_can_change_after_interval(self):
        """Can change state after interval has elapsed."""
        hass = _make_hass()
        controller = Controller(hass, {})
        config = _make_appliance_config(switch_interval=300)
        controller._last_state_change["appliance_1"] = (
            datetime.now() - timedelta(seconds=600)
        )

        assert controller._can_change_state(config) is True

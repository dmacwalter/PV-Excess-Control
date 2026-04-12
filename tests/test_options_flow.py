"""Tests for PV Excess Control options flow.

Tests verify that:
- The config flow exposes an options flow handler
- Options flow mirrors the main config flow steps
- Options flow pre-populates forms with existing config values
- Validation logic works identically to the main config flow
- Completing the flow creates an options entry
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.pv_excess_control.config_flow import (
    PvExcessControlConfigFlow,
    PvExcessControlOptionsFlow,
)
from custom_components.pv_excess_control.const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_BATTERY_STRATEGY,
    CONF_BATTERY_TARGET_SOC,
    CONF_CONTROLLER_INTERVAL,
    CONF_EXPORT_LIMIT,
    CONF_FEED_IN_TARIFF,
    CONF_FORECAST_PROVIDER,
    CONF_GRID_EXPORT,
    CONF_GRID_VOLTAGE,
    CONF_IMPORT_EXPORT,
    CONF_INVERTER_TYPE,
    CONF_LOAD_POWER,
    CONF_PLANNER_INTERVAL,
    CONF_PRICE_SENSOR,
    CONF_PV_POWER,
    CONF_TARIFF_PROVIDER,
    DEFAULT_CONTROLLER_INTERVAL,
    DEFAULT_GRID_VOLTAGE,
    DEFAULT_PLANNER_INTERVAL,
    DOMAIN,
    BatteryStrategy,
    ForecastProvider,
    InverterType,
    TariffProvider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config_entry(data: dict[str, Any] | None = None) -> MagicMock:
    """Create a mock ConfigEntry with pre-populated data."""
    entry = MagicMock()
    entry.data = data or {
        CONF_INVERTER_TYPE: InverterType.HYBRID,
        CONF_GRID_VOLTAGE: 230,
        CONF_PV_POWER: "sensor.pv_power",
        CONF_GRID_EXPORT: "sensor.grid_export",
        CONF_BATTERY_SOC: "sensor.battery_soc",
        CONF_BATTERY_POWER: "sensor.battery_power",
        CONF_BATTERY_CAPACITY: 10.0,
        CONF_TARIFF_PROVIDER: TariffProvider.NONE,
        CONF_FEED_IN_TARIFF: 0.08,
        CONF_FORECAST_PROVIDER: ForecastProvider.NONE,
        CONF_CONTROLLER_INTERVAL: DEFAULT_CONTROLLER_INTERVAL,
        CONF_PLANNER_INTERVAL: DEFAULT_PLANNER_INTERVAL,
    }
    return entry


def _make_options_flow(entry_data: dict[str, Any] | None = None) -> PvExcessControlOptionsFlow:
    """Create a PvExcessControlOptionsFlow with a mocked config entry."""
    config_entry = _make_config_entry(entry_data)
    flow = PvExcessControlOptionsFlow()
    flow.hass = MagicMock()
    flow.handler = DOMAIN
    flow.flow_id = "test_options_flow_id"
    flow.context = {"source": "options"}
    # Set config_entry via the internal attribute (property is read-only in newer HA)
    # Make config_entry accessible (base class uses it as a property)
    type(flow).config_entry = property(lambda self: config_entry)
    # Initialize data from the mock entry data
    flow.data = dict(config_entry.data)
    return flow


def _schema_has_key(result: dict, key_name: str) -> bool:
    """Check if a form schema contains a specific key."""
    schema = result.get("data_schema")
    if schema is None:
        return False
    for key in schema.schema:
        actual_key = key.schema if isinstance(key, vol.Marker) else key
        if str(actual_key) == key_name:
            return True
    return False


def _get_schema_default(result: dict, key_name: str) -> Any:
    """Extract the default value for a schema key from a form result."""
    schema = result.get("data_schema")
    if schema is None:
        return None
    for key in schema.schema:
        actual_key = key.schema if isinstance(key, vol.Marker) else key
        if str(actual_key) == key_name:
            if hasattr(key, "default") and callable(key.default):
                return key.default()
            return getattr(key, "default", None)
    return None


# ---------------------------------------------------------------------------
# TestOptionsFlowExists
# ---------------------------------------------------------------------------


class TestOptionsFlowExists:
    """Verify that the config flow exposes an options flow handler."""

    def test_options_flow_exists(self):
        """Config flow class has async_get_options_flow static method."""
        assert hasattr(PvExcessControlConfigFlow, "async_get_options_flow")
        assert callable(PvExcessControlConfigFlow.async_get_options_flow)

    def test_options_flow_returns_correct_type(self):
        """async_get_options_flow returns a PvExcessControlOptionsFlow instance."""
        config_entry = _make_config_entry()
        result = PvExcessControlConfigFlow.async_get_options_flow(config_entry)
        assert isinstance(result, PvExcessControlOptionsFlow)

    def test_options_flow_is_options_flow_subclass(self):
        """PvExcessControlOptionsFlow inherits from OptionsFlow."""
        from homeassistant import config_entries
        assert issubclass(PvExcessControlOptionsFlow, config_entries.OptionsFlow)


# ---------------------------------------------------------------------------
# TestOptionsStepUser
# ---------------------------------------------------------------------------


class TestOptionsStepUser:
    """Tests for the options flow user step (inverter setup)."""

    @pytest.mark.asyncio
    async def test_options_step_init_redirects_to_user(self):
        """async_step_init delegates to async_step_user."""
        flow = _make_options_flow()
        result_init = await flow.async_step_init(user_input=None)
        result_user = await _make_options_flow().async_step_user(user_input=None)

        assert result_init["step_id"] == result_user["step_id"]
        assert result_init["type"] == result_user["type"]

    @pytest.mark.asyncio
    async def test_options_step_user_shows_form(self):
        """Options flow starts with inverter setup step."""
        flow = _make_options_flow()
        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert _schema_has_key(result, CONF_INVERTER_TYPE)
        assert _schema_has_key(result, CONF_GRID_VOLTAGE)

    @pytest.mark.asyncio
    async def test_options_preserves_existing_inverter_type(self):
        """Options flow pre-populates inverter_type from current config."""
        flow = _make_options_flow(
            {CONF_INVERTER_TYPE: InverterType.STANDARD, CONF_GRID_VOLTAGE: 120}
        )
        result = await flow.async_step_user(user_input=None)

        # The schema default should reflect the existing config value
        default = _get_schema_default(result, CONF_INVERTER_TYPE)
        assert default == InverterType.STANDARD

    @pytest.mark.asyncio
    async def test_options_preserves_existing_grid_voltage(self):
        """Options flow pre-populates grid_voltage from current config."""
        flow = _make_options_flow(
            {CONF_INVERTER_TYPE: InverterType.HYBRID, CONF_GRID_VOLTAGE: 120}
        )
        result = await flow.async_step_user(user_input=None)

        default = _get_schema_default(result, CONF_GRID_VOLTAGE)
        assert default == 120

    @pytest.mark.asyncio
    async def test_options_step_user_accepts_valid_input(self):
        """Valid inverter input advances to sensors step."""
        flow = _make_options_flow()
        result = await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 230,
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "sensors"
        assert flow.data[CONF_INVERTER_TYPE] == InverterType.STANDARD

    @pytest.mark.asyncio
    async def test_options_step_user_rejects_low_voltage(self):
        """Voltage below 100V is rejected with invalid_voltage error."""
        flow = _make_options_flow()
        result = await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 50,
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"][CONF_GRID_VOLTAGE] == "invalid_voltage"

    @pytest.mark.asyncio
    async def test_options_step_user_rejects_high_voltage(self):
        """Voltage above 500V is rejected with invalid_voltage error."""
        flow = _make_options_flow()
        result = await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 600,
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"][CONF_GRID_VOLTAGE] == "invalid_voltage"

    @pytest.mark.asyncio
    async def test_options_step_user_boundary_voltage_100(self):
        """Voltage of exactly 100V is accepted."""
        flow = _make_options_flow()
        result = await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 100,
            }
        )
        assert result["step_id"] == "sensors"

    @pytest.mark.asyncio
    async def test_options_step_user_boundary_voltage_500(self):
        """Voltage of exactly 500V is accepted."""
        flow = _make_options_flow()
        result = await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 500,
            }
        )
        assert result["step_id"] == "sensors"


# ---------------------------------------------------------------------------
# TestOptionsStepSensors
# ---------------------------------------------------------------------------


class TestOptionsStepSensors:
    """Tests for the options flow sensor mapping step."""

    @pytest.mark.asyncio
    async def test_options_step_sensors_shows_form(self):
        """Sensors step shows form for sensor mapping."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD
        result = await flow.async_step_sensors(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "sensors"
        assert _schema_has_key(result, CONF_PV_POWER)

    @pytest.mark.asyncio
    async def test_options_step_sensors_rejects_no_grid_or_load_sensor(self):
        """Sensors step rejects input with none of grid_export, import_export, or load_power."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD

        result = await flow.async_step_sensors(
            user_input={CONF_PV_POWER: "sensor.pv"}
        )

        assert result["type"] == "form"
        assert result["step_id"] == "sensors"
        assert result["errors"]["base"] == "no_grid_sensor"

    @pytest.mark.asyncio
    async def test_options_step_sensors_accepts_pv_plus_load(self):
        """Sensors step advances when PV + Load Power alone is provided."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD

        result = await flow.async_step_sensors(
            user_input={
                CONF_PV_POWER: "sensor.pv",
                CONF_LOAD_POWER: "sensor.load_power",
            }
        )

        assert result["step_id"] == "energy"

    @pytest.mark.asyncio
    async def test_options_step_sensors_accepts_grid_export(self):
        """Sensors step advances when grid_export is provided."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD

        result = await flow.async_step_sensors(
            user_input={
                CONF_PV_POWER: "sensor.pv",
                CONF_GRID_EXPORT: "sensor.grid_export",
            }
        )

        assert result["step_id"] == "energy"

    @pytest.mark.asyncio
    async def test_options_step_sensors_accepts_import_export(self):
        """Sensors step advances when import_export (combined) sensor is provided."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD

        result = await flow.async_step_sensors(
            user_input={
                CONF_PV_POWER: "sensor.pv",
                CONF_IMPORT_EXPORT: "sensor.grid_combined",
            }
        )

        assert result["step_id"] == "energy"


# ---------------------------------------------------------------------------
# TestOptionsStepEnergy
# ---------------------------------------------------------------------------


class TestOptionsStepEnergy:
    """Tests for the options flow energy pricing step."""

    @pytest.mark.asyncio
    async def test_options_step_energy_shows_form(self):
        """Energy step shows tariff provider and feed-in tariff."""
        flow = _make_options_flow()
        flow.data[CONF_TARIFF_PROVIDER] = TariffProvider.NONE
        result = await flow.async_step_energy(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "energy"
        assert _schema_has_key(result, CONF_TARIFF_PROVIDER)

    @pytest.mark.asyncio
    async def test_options_step_energy_none_provider_advances(self):
        """None tariff provider advances to forecast step."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD
        flow.data[CONF_TARIFF_PROVIDER] = TariffProvider.NONE

        result = await flow.async_step_energy(
            user_input={
                CONF_TARIFF_PROVIDER: TariffProvider.NONE,
                CONF_FEED_IN_TARIFF: 0.08,
            }
        )

        assert result["step_id"] == "forecast"

    @pytest.mark.asyncio
    async def test_options_step_energy_generic_requires_sensor(self):
        """Generic tariff provider requires a price sensor."""
        flow = _make_options_flow()
        flow.data[CONF_TARIFF_PROVIDER] = TariffProvider.GENERIC

        result = await flow.async_step_energy(
            user_input={
                CONF_TARIFF_PROVIDER: TariffProvider.GENERIC,
                CONF_FEED_IN_TARIFF: 0.08,
                # No CONF_PRICE_SENSOR
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "energy"
        assert result["errors"][CONF_PRICE_SENSOR] == "missing_price_sensor"

    @pytest.mark.asyncio
    async def test_options_step_energy_generic_with_sensor_advances(self):
        """Generic tariff provider with sensor advances."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD
        flow.data[CONF_TARIFF_PROVIDER] = TariffProvider.GENERIC

        result = await flow.async_step_energy(
            user_input={
                CONF_TARIFF_PROVIDER: TariffProvider.GENERIC,
                CONF_PRICE_SENSOR: "sensor.price",
                CONF_FEED_IN_TARIFF: 0.08,
            }
        )

        assert result["step_id"] == "forecast"


# ---------------------------------------------------------------------------
# TestOptionsStepForecast
# ---------------------------------------------------------------------------


class TestOptionsStepForecast:
    """Tests for the options flow forecast step."""

    @pytest.mark.asyncio
    async def test_options_step_forecast_shows_form(self):
        """Forecast step shows form."""
        flow = _make_options_flow()
        flow.data[CONF_FORECAST_PROVIDER] = ForecastProvider.NONE
        result = await flow.async_step_forecast(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "forecast"

    @pytest.mark.asyncio
    async def test_options_step_forecast_none_standard_goes_to_settings(self):
        """None forecast provider on standard inverter goes directly to settings."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.STANDARD
        flow.data[CONF_FORECAST_PROVIDER] = ForecastProvider.NONE

        result = await flow.async_step_forecast(
            user_input={CONF_FORECAST_PROVIDER: ForecastProvider.NONE}
        )

        assert result["step_id"] == "settings"

    @pytest.mark.asyncio
    async def test_options_step_forecast_none_hybrid_goes_to_battery(self):
        """None forecast provider on hybrid inverter goes to battery step."""
        flow = _make_options_flow()
        flow.data[CONF_INVERTER_TYPE] = InverterType.HYBRID
        flow.data[CONF_FORECAST_PROVIDER] = ForecastProvider.NONE

        result = await flow.async_step_forecast(
            user_input={CONF_FORECAST_PROVIDER: ForecastProvider.NONE}
        )

        assert result["step_id"] == "battery"

    @pytest.mark.asyncio
    async def test_options_step_forecast_generic_requires_sensor(self):
        """Generic forecast provider requires a forecast sensor."""
        flow = _make_options_flow()
        flow.data[CONF_FORECAST_PROVIDER] = ForecastProvider.GENERIC

        result = await flow.async_step_forecast(
            user_input={
                CONF_FORECAST_PROVIDER: ForecastProvider.GENERIC,
                # No CONF_FORECAST_SENSOR
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "forecast"
        assert "forecast_sensor" in result["errors"]


# ---------------------------------------------------------------------------
# TestOptionsStepBattery
# ---------------------------------------------------------------------------


class TestOptionsStepBattery:
    """Tests for the options flow battery strategy step."""

    @pytest.mark.asyncio
    async def test_options_step_battery_shows_form(self):
        """Battery step shows form with battery strategy fields."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "battery"

    @pytest.mark.asyncio
    async def test_options_step_battery_accepts_valid_soc(self):
        """Valid target SoC advances to settings."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(
            user_input={
                CONF_BATTERY_STRATEGY: BatteryStrategy.BATTERY_FIRST,
                CONF_BATTERY_TARGET_SOC: 80,
            }
        )

        assert result["step_id"] == "settings"

    @pytest.mark.asyncio
    async def test_options_step_battery_rejects_invalid_soc_high(self):
        """SoC above 100 is rejected."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(
            user_input={
                CONF_BATTERY_STRATEGY: BatteryStrategy.BATTERY_FIRST,
                CONF_BATTERY_TARGET_SOC: 110,
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "battery"
        assert result["errors"][CONF_BATTERY_TARGET_SOC] == "invalid_soc"

    @pytest.mark.asyncio
    async def test_options_step_battery_rejects_invalid_soc_negative(self):
        """Negative SoC is rejected."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(
            user_input={
                CONF_BATTERY_STRATEGY: BatteryStrategy.BATTERY_FIRST,
                CONF_BATTERY_TARGET_SOC: -5,
            }
        )

        assert result["type"] == "form"
        assert result["step_id"] == "battery"
        assert result["errors"][CONF_BATTERY_TARGET_SOC] == "invalid_soc"

    @pytest.mark.asyncio
    async def test_options_step_battery_boundary_soc_0(self):
        """SoC of 0 is accepted."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(
            user_input={
                CONF_BATTERY_STRATEGY: BatteryStrategy.APPLIANCE_FIRST,
                CONF_BATTERY_TARGET_SOC: 0,
            }
        )
        assert result["step_id"] == "settings"

    @pytest.mark.asyncio
    async def test_options_step_battery_boundary_soc_100(self):
        """SoC of 100 is accepted."""
        flow = _make_options_flow()
        result = await flow.async_step_battery(
            user_input={
                CONF_BATTERY_STRATEGY: BatteryStrategy.BALANCED,
                CONF_BATTERY_TARGET_SOC: 100,
            }
        )
        assert result["step_id"] == "settings"


# ---------------------------------------------------------------------------
# TestOptionsStepSettings
# ---------------------------------------------------------------------------


class TestOptionsStepSettings:
    """Tests for the options flow settings step (final step)."""

    @pytest.mark.asyncio
    async def test_options_step_settings_shows_form(self):
        """Settings step shows form."""
        flow = _make_options_flow()
        result = await flow.async_step_settings(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "settings"

    @pytest.mark.asyncio
    async def test_options_step_settings_creates_entry(self):
        """Settings step with valid input creates an options entry."""
        flow = _make_options_flow()
        # Populate flow.data with required fields
        flow.data.update({
            CONF_INVERTER_TYPE: InverterType.HYBRID,
            CONF_GRID_VOLTAGE: 230,
            CONF_PV_POWER: "sensor.pv",
            CONF_GRID_EXPORT: "sensor.grid_export",
        })

        result = await flow.async_step_settings(
            user_input={
                CONF_CONTROLLER_INTERVAL: str(DEFAULT_CONTROLLER_INTERVAL),
                CONF_PLANNER_INTERVAL: str(DEFAULT_PLANNER_INTERVAL),
                CONF_EXPORT_LIMIT: None,
            }
        )

        assert result["type"] == "create_entry"

    @pytest.mark.asyncio
    async def test_options_settings_converts_intervals_to_int(self):
        """Settings step converts interval strings to integers in stored data."""
        flow = _make_options_flow()

        await flow.async_step_settings(
            user_input={
                CONF_CONTROLLER_INTERVAL: "30",
                CONF_PLANNER_INTERVAL: "900",
            }
        )

        assert flow.data[CONF_CONTROLLER_INTERVAL] == 30
        assert flow.data[CONF_PLANNER_INTERVAL] == 900


# ---------------------------------------------------------------------------
# TestOptionsPreservesExisting
# ---------------------------------------------------------------------------


class TestOptionsPreservesExisting:
    """Verify options flow pre-populates with current config values."""

    @pytest.mark.asyncio
    async def test_options_flow_initialized_with_entry_data(self):
        """OptionsFlow.data is initialized from config_entry.data."""
        entry_data = {
            CONF_INVERTER_TYPE: InverterType.STANDARD,
            CONF_GRID_VOLTAGE: 120,
            CONF_PV_POWER: "sensor.my_pv",
            CONF_TARIFF_PROVIDER: TariffProvider.TIBBER,
        }
        flow = _make_options_flow(entry_data)

        # flow.data should mirror the entry data at construction time
        assert flow.data[CONF_INVERTER_TYPE] == InverterType.STANDARD
        assert flow.data[CONF_GRID_VOLTAGE] == 120
        assert flow.data[CONF_PV_POWER] == "sensor.my_pv"
        assert flow.data[CONF_TARIFF_PROVIDER] == TariffProvider.TIBBER

    @pytest.mark.asyncio
    async def test_options_uses_existing_inverter_type_as_default(self):
        """The user step schema default for inverter_type matches existing config."""
        flow = _make_options_flow(
            {CONF_INVERTER_TYPE: InverterType.STANDARD, CONF_GRID_VOLTAGE: 230}
        )
        result = await flow.async_step_user(user_input=None)

        # The schema should embed the existing value as the default
        default_inverter = _get_schema_default(result, CONF_INVERTER_TYPE)
        assert default_inverter == InverterType.STANDARD

    @pytest.mark.asyncio
    async def test_options_data_accumulates_across_steps(self):
        """Data from each step is retained in flow.data for subsequent steps."""
        flow = _make_options_flow()
        # Step 1: user
        await flow.async_step_user(
            user_input={
                CONF_INVERTER_TYPE: InverterType.STANDARD,
                CONF_GRID_VOLTAGE: 230,
            }
        )
        assert flow.data[CONF_INVERTER_TYPE] == InverterType.STANDARD

        # Step 2: sensors
        await flow.async_step_sensors(
            user_input={
                CONF_PV_POWER: "sensor.pv",
                CONF_GRID_EXPORT: "sensor.export",
            }
        )
        # Both step 1 and step 2 data should be present
        assert flow.data[CONF_INVERTER_TYPE] == InverterType.STANDARD
        assert flow.data[CONF_PV_POWER] == "sensor.pv"

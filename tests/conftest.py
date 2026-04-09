"""Shared test fixtures for PV Excess Control tests."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.pv_excess_control.models import (
    Action,
    ApplianceConfig,
    ApplianceState,
    BatteryDischargeAction,
    BatteryStrategy,
    BatteryTarget,
    ControlDecision,
    OptimizerResult,
    Plan,
    PowerState,
    TariffInfo,
    TariffWindow,
)


@pytest.fixture
def sample_power_state():
    """A typical power state with solar excess."""
    return PowerState(
        pv_production=4000.0,
        grid_export=1500.0,
        grid_import=0.0,
        load_power=2500.0,
        excess_power=1500.0,
        battery_soc=80.0,
        battery_power=500.0,
        ev_soc=None,
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_appliance_config():
    """A simple switch appliance config."""
    return ApplianceConfig(
        id="test_app",
        name="Test Appliance",
        entity_id="switch.test_app",
        priority=5,
        phases=1,
        nominal_power=1000.0,
        actual_power_entity=None,
        dynamic_current=False,
        current_entity=None,
        min_current=0.0,
        max_current=0.0,
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


@pytest.fixture
def sample_tariff():
    """Standard tariff info."""
    return TariffInfo(
        current_price=0.25,
        feed_in_tariff=0.08,
        cheap_price_threshold=0.10,
        battery_charge_price_threshold=0.05,
    )


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/config/test")
    hass.data = {}
    hass.http = MagicMock()
    hass.http.register_static_path = MagicMock()
    return hass

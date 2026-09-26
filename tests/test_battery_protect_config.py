"""Config path for battery target protection: options flow schema, saved
values, and the coordinator handing them to the optimizer."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.pv_excess_control.const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_PROTECT_BULK_RATE,
    CONF_BATTERY_PROTECT_CHARGE_RATE,
    CONF_BATTERY_PROTECT_MARGIN,
    CONF_BATTERY_PROTECT_TAPER_SOC,
    CONF_BATTERY_STRATEGY,
    CONF_BATTERY_TARGET_SOC,
    BatteryStrategy,
)
from custom_components.pv_excess_control.optimizer import Optimizer

from .test_options_flow import _get_schema_default, _make_config_entry, _make_options_flow

KEYS = {
    CONF_BATTERY_PROTECT_CHARGE_RATE: 0,
    CONF_BATTERY_PROTECT_MARGIN: 5,
    CONF_BATTERY_PROTECT_BULK_RATE: 0,
    CONF_BATTERY_PROTECT_TAPER_SOC: 90,
}


def _schema_keys(result):
    return {str(k.schema if isinstance(k, vol.Marker) else k) for k in result["data_schema"].schema}


@pytest.mark.asyncio
async def test_battery_step_offers_all_protection_fields_with_defaults():
    flow = _make_options_flow()
    result = await flow.async_step_battery(user_input=None)
    assert set(KEYS) <= _schema_keys(result)
    for key, default in KEYS.items():
        assert _get_schema_default(result, key) == default, key
    assert "battery_protect_window_minutes" not in _schema_keys(result)


@pytest.mark.asyncio
async def test_battery_step_shows_saved_values():
    data = dict(_make_config_entry().data)
    data.update({CONF_BATTERY_PROTECT_CHARGE_RATE: 6000, CONF_BATTERY_PROTECT_MARGIN: 10,
                 CONF_BATTERY_PROTECT_BULK_RATE: 9000, CONF_BATTERY_PROTECT_TAPER_SOC: 88})
    flow = _make_options_flow(data)
    result = await flow.async_step_battery(user_input=None)
    assert _get_schema_default(result, CONF_BATTERY_PROTECT_CHARGE_RATE) == 6000
    assert _get_schema_default(result, CONF_BATTERY_PROTECT_MARGIN) == 10
    assert _get_schema_default(result, CONF_BATTERY_PROTECT_BULK_RATE) == 9000
    assert _get_schema_default(result, CONF_BATTERY_PROTECT_TAPER_SOC) == 88


@pytest.mark.asyncio
async def test_battery_step_schema_accepts_and_saves_values():
    flow = _make_options_flow()
    form = await flow.async_step_battery(user_input=None)
    submitted = form["data_schema"]({
        CONF_BATTERY_STRATEGY: BatteryStrategy.BALANCED,
        CONF_BATTERY_TARGET_SOC: 100,
        CONF_BATTERY_PROTECT_CHARGE_RATE: 6000,
        CONF_BATTERY_PROTECT_MARGIN: 10,
        CONF_BATTERY_PROTECT_BULK_RATE: 9000,
        CONF_BATTERY_PROTECT_TAPER_SOC: 90,
    })
    result = await flow.async_step_battery(user_input=submitted)
    assert result["step_id"] == "settings"
    assert flow.data[CONF_BATTERY_PROTECT_CHARGE_RATE] == 6000
    assert flow.data[CONF_BATTERY_PROTECT_MARGIN] == 10
    assert flow.data[CONF_BATTERY_PROTECT_BULK_RATE] == 9000
    assert flow.data[CONF_BATTERY_PROTECT_TAPER_SOC] == 90


@pytest.mark.asyncio
async def test_battery_step_schema_fills_defaults_when_omitted():
    flow = _make_options_flow()
    form = await flow.async_step_battery(user_input=None)
    submitted = form["data_schema"]({
        CONF_BATTERY_STRATEGY: BatteryStrategy.BALANCED, CONF_BATTERY_TARGET_SOC: 100,
    })
    for key, default in KEYS.items():
        assert submitted[key] == default, key


@pytest.mark.asyncio
@pytest.mark.parametrize("key,bad", [
    (CONF_BATTERY_PROTECT_CHARGE_RATE, -1),
    (CONF_BATTERY_PROTECT_MARGIN, 500),
    (CONF_BATTERY_PROTECT_TAPER_SOC, 101),
])
async def test_battery_step_schema_rejects_out_of_range(key, bad):
    flow = _make_options_flow()
    form = await flow.async_step_battery(user_input=None)
    with pytest.raises(vol.Invalid):
        form["data_schema"]({
            CONF_BATTERY_STRATEGY: BatteryStrategy.BALANCED, CONF_BATTERY_TARGET_SOC: 100, key: bad,
        })


def _coordinator_optimizer_kwargs(hass, data):
    """Construct the real coordinator and capture what it passes to Optimizer."""
    from custom_components.pv_excess_control import coordinator as coord_mod

    captured = {}

    class _Capture(Optimizer):
        def __init__(self, *a, **kw):
            captured.update(kw)
            super().__init__(*a, **kw)

    entry = MagicMock()
    entry.entry_id = "cfg_test"
    entry.data = data
    entry.options = {}
    entry.subentries = {}
    with patch.object(coord_mod, "Optimizer", _Capture):
        coord_mod.PvExcessCoordinator(hass, entry)
    return captured


@pytest.mark.asyncio
async def test_coordinator_passes_protection_settings(hass):
    data = dict(_make_config_entry().data)
    data.update({CONF_BATTERY_CAPACITY: 22.4, CONF_BATTERY_PROTECT_CHARGE_RATE: 6000.0,
                 CONF_BATTERY_PROTECT_MARGIN: 10.0, CONF_BATTERY_PROTECT_BULK_RATE: 9000.0,
                 CONF_BATTERY_PROTECT_TAPER_SOC: 90.0})
    kw = _coordinator_optimizer_kwargs(hass, data)
    assert kw["battery_protect_charge_rate_w"] == 6000.0
    assert kw["battery_protect_margin_minutes"] == 10.0
    assert kw["battery_protect_bulk_rate_w"] == 9000.0
    assert kw["battery_protect_taper_soc"] == 90.0
    assert kw["battery_capacity_kwh"] == 22.4


@pytest.mark.asyncio
async def test_coordinator_defaults_when_unset_and_ignores_retired_window(hass):
    data = dict(_make_config_entry().data)
    data["battery_protect_window_minutes"] = 120  # set in 0.3.11, retired in 0.3.12
    kw = _coordinator_optimizer_kwargs(hass, data)
    assert kw["battery_protect_charge_rate_w"] == 0.0
    assert kw["battery_protect_margin_minutes"] == 5.0
    assert kw["battery_protect_bulk_rate_w"] == 0.0
    assert kw["battery_protect_taper_soc"] == 90.0
    assert "battery_protect_window_minutes" not in kw


@pytest.mark.asyncio
async def test_coordinator_zero_margin_is_kept(hass):
    data = dict(_make_config_entry().data)
    data.update({CONF_BATTERY_PROTECT_CHARGE_RATE: 6000, CONF_BATTERY_PROTECT_MARGIN: 0,
                 CONF_BATTERY_PROTECT_TAPER_SOC: 0})
    kw = _coordinator_optimizer_kwargs(hass, data)
    assert kw["battery_protect_margin_minutes"] == 0.0
    assert kw["battery_protect_taper_soc"] == 0.0
    opt = Optimizer(grid_voltage=240, **{k: v for k, v in kw.items() if k.startswith("battery")})
    assert opt._battery_protect_margin == timedelta(0)

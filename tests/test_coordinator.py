"""Tests for PvExcessCoordinator grid-charge state machine.

Uses the same mock-coordinator helper pattern as test_init.py.
"""
from __future__ import annotations

import pytest

from custom_components.pv_excess_control.const import (
    CONF_AUTO_BATTERY_GRID_CHARGE,
    CONF_BATTERY_GRID_CHARGE_POWER_W,
    CONF_BATTERY_TARGET_SOC,
    CONF_BATTERY_STRATEGY,
    CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES,
    CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY,
    CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE,
    CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE,
)


@pytest.mark.asyncio
async def test_grid_charge_engages_when_price_below_threshold_and_soc_below_target(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "Forced charge",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "Stop",
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
        },
        inverter_ctl=mock_inverter_controller,
    )
    coordinator._latest_tariff = mock_tariff_at(current_price=0.01, battery_charge_price_threshold=0.02)
    coordinator._latest_power_state = mock_power_state_with_soc(battery_soc=70.0)

    await coordinator._run_grid_charge_state_machine(
        coordinator._latest_tariff, coordinator._latest_power_state,
    )

    mock_inverter_controller.engage.assert_awaited_once_with(5000.0)
    assert coordinator._grid_charge_engaged is True


@pytest.mark.asyncio
async def test_grid_charge_does_not_re_engage_while_already_engaged(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "Forced charge",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "Stop",
        },
        inverter_ctl=mock_inverter_controller,
    )
    coordinator._latest_tariff = mock_tariff_at(0.01, 0.02)
    coordinator._latest_power_state = mock_power_state_with_soc(70.0)

    await coordinator._run_grid_charge_state_machine(coordinator._latest_tariff, coordinator._latest_power_state)
    await coordinator._run_grid_charge_state_machine(coordinator._latest_tariff, coordinator._latest_power_state)

    assert mock_inverter_controller.engage.await_count == 1


@pytest.mark.asyncio
async def test_grid_charge_no_inverter_configured_no_calls(
    coordinator_factory, mock_tariff_at, mock_power_state_with_soc,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
        },
        inverter_ctl=None,  # not configured
    )
    coordinator._latest_tariff = mock_tariff_at(0.01, 0.02)
    coordinator._latest_power_state = mock_power_state_with_soc(70.0)

    # Must not raise
    await coordinator._run_grid_charge_state_machine(coordinator._latest_tariff, coordinator._latest_power_state)

    assert coordinator._grid_charge_engaged is False


@pytest.mark.asyncio
async def test_grid_charge_disengages_when_price_rises_above_threshold(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc, freeze_time,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )

    with freeze_time() as ft:
        # Engage
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.01, 0.02), mock_power_state_with_soc(70.0),
        )
        ft.tick(seconds=6 * 60)  # past hysteresis
        # Price rises
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.10, 0.02), mock_power_state_with_soc(70.0),
        )

    mock_inverter_controller.disengage.assert_awaited_once()
    assert coordinator._grid_charge_engaged is False


@pytest.mark.asyncio
async def test_grid_charge_disengages_when_soc_reaches_target(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc, freeze_time,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    with freeze_time() as ft:
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.01, 0.02), mock_power_state_with_soc(70.0),
        )
        ft.tick(seconds=6 * 60)
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.01, 0.02), mock_power_state_with_soc(100.0),
        )
    mock_inverter_controller.disengage.assert_awaited_once()


@pytest.mark.asyncio
async def test_grid_charge_hysteresis_holds_disengage_for_min_duration(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc, freeze_time,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    with freeze_time() as ft:
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.01, 0.02), mock_power_state_with_soc(70.0),
        )
        ft.tick(seconds=2 * 60)  # within hysteresis
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.10, 0.02), mock_power_state_with_soc(70.0),
        )
    mock_inverter_controller.disengage.assert_not_awaited()
    assert coordinator._grid_charge_engaged is True


@pytest.mark.asyncio
async def test_grid_charge_force_charge_switch_bypasses_price_gate(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: False,  # auto OFF
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    coordinator.force_charge = True
    coordinator._force_charge_prev = False  # simulate fresh ON edge

    await coordinator._run_grid_charge_state_machine(
        mock_tariff_at(0.50, 0.02),  # very expensive
        mock_power_state_with_soc(70.0),
    )

    mock_inverter_controller.engage.assert_awaited_once_with(5000.0)


@pytest.mark.asyncio
async def test_grid_charge_force_charge_off_bypasses_hysteresis(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc, freeze_time,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: False,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    coordinator.force_charge = True
    coordinator._force_charge_prev = False
    with freeze_time() as ft:
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.50, 0.02), mock_power_state_with_soc(70.0),
        )
        ft.tick(seconds=60)  # well within hysteresis
        # User flips off
        coordinator.force_charge = False
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.50, 0.02), mock_power_state_with_soc(70.0),
        )
    mock_inverter_controller.disengage.assert_awaited_once()
    assert coordinator._grid_charge_engaged is False


@pytest.mark.asyncio
async def test_grid_charge_state_persisted_across_restart_disengages_when_conditions_clear(
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc, freeze_time,
):
    """Persisted engaged=True, fresh restart, conditions cleared → disengage."""
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_GRID_CHARGE_ENGAGE_MIN_DURATION_MINUTES: 5,
            "_grid_charge_engaged": True,  # persisted from prior session
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    # Fresh restart: engage_ts is None, so elapsed = monotonic() - 0 ≈ huge → past hysteresis
    with freeze_time() as ft:
        await coordinator._run_grid_charge_state_machine(
            mock_tariff_at(0.10, 0.02),  # not cheap
            mock_power_state_with_soc(70.0),
        )
    mock_inverter_controller.disengage.assert_awaited_once()
    assert coordinator._grid_charge_engaged is False


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", ["balanced", "battery_first", "appliance_first"])
async def test_grid_charge_independent_of_battery_strategy(
    strategy,
    coordinator_factory, mock_inverter_controller, mock_tariff_at, mock_power_state_with_soc,
):
    coordinator = coordinator_factory(
        config_data={
            CONF_AUTO_BATTERY_GRID_CHARGE: True,
            CONF_BATTERY_GRID_CHARGE_POWER_W: 5000.0,
            CONF_BATTERY_TARGET_SOC: 100,
            CONF_BATTERY_STRATEGY: strategy,
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENTITY: "input_select.cmd",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_ENGAGE_VALUE: "x",
            CONF_INVERTER_FORCE_CHARGE_ENABLE_DISENGAGE_VALUE: "y",
        },
        inverter_ctl=mock_inverter_controller,
    )
    await coordinator._run_grid_charge_state_machine(
        mock_tariff_at(0.01, 0.02), mock_power_state_with_soc(70.0),
    )
    mock_inverter_controller.engage.assert_awaited_once()

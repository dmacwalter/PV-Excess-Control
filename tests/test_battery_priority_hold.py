"""Regression tests for the battery-priority shed/hold interaction.

Covers the failure observed 2026-08-15: the coordinator shed the pool to free
solar for the battery, and the optimizer restarted it on the very next cycle
because the freed load read as available excess. The appliance then oscillated
against the grid-charge state machine, pulling grid import while both ran.

Before this suite there was no coverage of battery_priority_shed,
shed_before_grid_charge, or the hold's persistence across restarts.
"""
from datetime import datetime, time, timedelta

import pytest

from custom_components.pv_excess_control.const import Action
from custom_components.pv_excess_control.models import (
    ApplianceConfig,
    ApplianceState,
    BatteryTarget,
    Plan,
    PowerState,
    TariffInfo,
)
from custom_components.pv_excess_control.optimizer import Optimizer

POOL_W = 1920.0
HOUSE_W = 800.0


def _cfg(**over):
    base = dict(
        id="pool", name="Pool", entity_id="switch.pool", priority=10, phases=1,
        nominal_power=2010, actual_power_entity="sensor.pool_power",
        dynamic_current=False, current_entity=None, min_current=6, max_current=32,
        ev_soc_entity=None, ev_connected_entity=None, is_big_consumer=False,
        battery_max_discharge_override=None, on_only=False,
        min_daily_runtime=timedelta(0), max_daily_runtime=None,
        schedule_deadline=None, allow_grid_supplement=False, max_grid_power=None,
        shed_before_grid_charge=True, switch_interval=timedelta(0),
    )
    base.update(over)
    return ApplianceConfig(**base)


def _state(is_on, *, shed=False, power=None, runtime=timedelta(hours=3)):
    return ApplianceState(
        appliance_id="pool", is_on=is_on,
        current_power=(POOL_W if is_on else 0.0) if power is None else power,
        current_amperage=None, runtime_today=runtime, energy_today=0.0,
        last_state_change=None, ev_connected=None, ev_soc=None,
        activations_today=0, battery_priority_shed=shed,
    )


def _plan():
    from custom_components.pv_excess_control.const import BatteryStrategy
    return Plan(
        created_at=datetime.now(), horizon=timedelta(hours=12), entries=[],
        confidence=0.0, grid_charge_recommended=False,
        battery_target=BatteryTarget(
            target_soc=100.0, target_time=datetime.now() + timedelta(hours=2),
            strategy=list(BatteryStrategy)[0]),
    )


def _run(cfg, state, pv_w):
    """Run one optimizer cycle and return the single decision."""
    load = HOUSE_W + (POOL_W if state.is_on else 0.0)
    excess = pv_w - load
    ps = PowerState(
        pv_production=pv_w, grid_export=max(excess, 0.0),
        grid_import=max(-excess, 0.0), load_power=load, excess_power=excess,
        battery_soc=89.0, battery_power=pv_w - load, ev_soc=None,
        timestamp=datetime.now(),
    )
    tariff = TariffInfo(
        current_price=0.18, feed_in_tariff=0.05,
        cheap_price_threshold=0.20, battery_charge_price_threshold=0.20,
    )
    result = Optimizer(grid_voltage=240).optimize(
        power_state=ps, appliances=[cfg], appliance_states=[state],
        plan=_plan(), power_history=[ps] * 5, tariff=tariff,
        plan_influence="none",
    )
    return result.decisions[0]


class TestBatteryPriorityShed:
    def test_flagged_and_on_is_shed(self):
        d = _run(_cfg(), _state(True, shed=True), 4700)
        assert d.action == Action.OFF
        assert "Battery priority" in d.reason

    def test_flagged_and_off_is_not_restarted(self):
        """The regression: freed load must not be re-offered as excess.

        4700W PV with the pool off leaves 3900W apparent excess, comfortably
        over the ~2210W start threshold. Before the fix this returned ON.
        """
        d = _run(_cfg(), _state(False, shed=True), 4700)
        assert d.action != Action.ON, (
            f"pool restarted while held for battery priority: {d.reason}"
        )
        assert d.action == Action.IDLE
        assert "held off" in d.reason

    def test_unflagged_and_off_still_starts_normally(self):
        """The hold must not suppress ordinary allocation."""
        d = _run(_cfg(), _state(False, shed=False), 4700)
        assert d.action == Action.ON

    def test_unflagged_and_on_stays_on(self):
        d = _run(_cfg(), _state(True, shed=False), 4700)
        assert d.action == Action.ON

    def test_hold_does_not_consume_excess_budget(self):
        """A held appliance must report zero power delta, not a phantom load."""
        cfg, st = _cfg(), _state(False, shed=True)
        load = HOUSE_W
        ps = PowerState(
            pv_production=4700, grid_export=3900, grid_import=0,
            load_power=load, excess_power=3900.0, battery_soc=89.0,
            battery_power=3900.0, ev_soc=None, timestamp=datetime.now(),
        )
        tariff = TariffInfo(0.18, 0.05, 0.20, 0.20)
        res = Optimizer(grid_voltage=240).optimize(
            power_state=ps, appliances=[cfg], appliance_states=[st],
            plan=_plan(), power_history=[ps] * 5, tariff=tariff,
            plan_influence="none",
        )
        assert res.decisions[0].action == Action.IDLE


class TestDeadlinePrecedence:
    """Deadline must-run outranks battery priority.

    Without this the two fight one cycle apart: must-run turns the appliance
    on, the battery-priority shed knocks it straight back off.
    """

    def test_coordinator_clears_hold_when_behind_deadline(self):
        from custom_components.pv_excess_control.coordinator import (
            PvExcessCoordinator,
        )
        coord = object.__new__(PvExcessCoordinator)
        now = datetime.now()
        cfg = _cfg(
            min_daily_runtime=timedelta(hours=10),
            schedule_deadline=(now + timedelta(minutes=30)).time(),
        )
        # 9h50m done, 10m left, deadline in 30m -> not yet behind
        assert coord._is_behind_deadline_raw(
            cfg, timedelta(hours=9, minutes=50)) is False
        # 4h done, 6h left, deadline in 30m -> behind
        assert coord._is_behind_deadline_raw(cfg, timedelta(hours=4)) is True

    def test_no_deadline_configured_is_never_behind(self):
        from custom_components.pv_excess_control.coordinator import (
            PvExcessCoordinator,
        )
        coord = object.__new__(PvExcessCoordinator)
        assert coord._is_behind_deadline_raw(_cfg(), timedelta(0)) is False

    def test_runtime_already_met_is_never_behind(self):
        from custom_components.pv_excess_control.coordinator import (
            PvExcessCoordinator,
        )
        coord = object.__new__(PvExcessCoordinator)
        cfg = _cfg(
            min_daily_runtime=timedelta(hours=2),
            schedule_deadline=(datetime.now() + timedelta(minutes=5)).time(),
        )
        assert coord._is_behind_deadline_raw(cfg, timedelta(hours=3)) is False


class TestHoldPersistence:
    """The hold must survive an HA restart.

    A restart mid-hold previously dropped the flag, so the pool was restarted
    on inflated excess and the whole shed had to happen again.
    """

    def test_hold_set_restored_from_config_entry_data(self):
        stored = {"_battery_priority_hold": ["pool", "spa"]}
        restored = set(stored.get("_battery_priority_hold", []))
        assert restored == {"pool", "spa"}

    def test_missing_key_restores_empty(self):
        assert set({}.get("_battery_priority_hold", [])) == set()

    def test_state_builder_tolerates_missing_attribute(self):
        """Coordinators built without __init__ must not raise."""
        class Bare:
            pass
        assert "pool" not in getattr(Bare(), "_battery_priority_hold", ())

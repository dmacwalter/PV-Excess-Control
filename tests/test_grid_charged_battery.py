"""Battery charged from the grid must not be counted as solar excess.

Every hybrid branch of ``_collect_power_state`` credits the battery's charge
power as excess. That is wrong while the battery is being charged from the
grid at a fixed rate by something other than this integration (Predbat, an
inverter schedule): an appliance switched on then adds its full draw to the
import. See ``PvExcessCoordinator._exclude_grid_charged_battery`` and section
24 of the changelog.
"""

from __future__ import annotations

import pytest

from custom_components.pv_excess_control.const import (
    CONF_BATTERY_POWER,
    CONF_CONTROLLER_INTERVAL,
    CONF_FORECAST_PROVIDER,
    CONF_GRID_EXPORT,
    CONF_GRID_VOLTAGE,
    CONF_IMPORT_EXPORT,
    CONF_LOAD_POWER,
    CONF_PLANNER_INTERVAL,
    CONF_PV_POWER,
    CONF_TARIFF_PROVIDER,
    DEFAULT_CONTROLLER_INTERVAL,
    DEFAULT_GRID_VOLTAGE,
    DEFAULT_PLANNER_INTERVAL,
    GRID_CHARGE_CONFIRM_CYCLES,
    ForecastProvider as ForecastProviderEnum,
    TariffProvider as TariffProviderEnum,
)

from .test_init import MockHass, MockState, _make_config_entry, _make_coordinator

_COMMON = {
    CONF_PV_POWER: "sensor.pv_power",
    CONF_LOAD_POWER: "sensor.load_power",
    CONF_BATTERY_POWER: "sensor.battery_power",  # positive = charging
    CONF_GRID_VOLTAGE: DEFAULT_GRID_VOLTAGE,
    CONF_CONTROLLER_INTERVAL: DEFAULT_CONTROLLER_INTERVAL,
    CONF_PLANNER_INTERVAL: DEFAULT_PLANNER_INTERVAL,
    CONF_TARIFF_PROVIDER: TariffProviderEnum.NONE,
    CONF_FORECAST_PROVIDER: ForecastProviderEnum.NONE,
}

TOPOLOGIES = {
    # Combined meter: positive = export, negative = import.
    "combined": {CONF_IMPORT_EXPORT: "sensor.grid_power"},
    # Export-only meter: import is never measured.
    "export_only": {CONF_GRID_EXPORT: "sensor.grid_export"},
    # No grid sensor at all: excess is pv - load.
    "no_grid": {},
}


def _coordinator(topology: str):
    entry = _make_config_entry(data={**_COMMON, **TOPOLOGIES[topology]})
    hass = MockHass({})
    return _make_coordinator(hass=hass, entry=entry), hass


def _set(hass, *, pv, load, battery, grid):
    """Set a physically consistent snapshot. ``grid`` is + export / - import."""
    assert abs(pv + (-grid if grid < 0 else 0) - load - battery - max(grid, 0)) < 1, (
        "test snapshot violates the energy balance"
    )
    states = {
        "sensor.pv_power": MockState(str(pv)),
        "sensor.load_power": MockState(str(load)),
        "sensor.battery_power": MockState(str(battery)),
        "sensor.grid_power": MockState(str(grid)),
        "sensor.grid_export": MockState(str(max(grid, 0))),
    }
    hass.states._states = states


def _excess(coord):
    return coord._collect_power_state().excess_power


# 2026-10-15 14:33: Predbat charging at 9.6 kW, pool on.
PREDBAT_CHARGE = dict(pv=6211, load=4196, battery=9628, grid=-7613)
# Normal self-consumption: battery soaking up solar, nothing imported.
SOLAR_CHARGE = dict(pv=9000, load=3000, battery=6000, grid=0)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_grid_charge_not_counted_once_confirmed(topology):
    coord, hass = _coordinator(topology)
    _set(hass, **PREDBAT_CHARGE)
    readings = [_excess(coord) for _ in range(GRID_CHARGE_CONFIRM_CYCLES)]

    # First cycle(s): unchanged, still pv - load (= +2015 W).
    assert readings[0] == pytest.approx(2015, abs=1)
    # Once confirmed: the grid balance, i.e. the import.
    assert readings[-1] == pytest.approx(-7613, abs=1)
    # And it stays there while the charge continues.
    assert _excess(coord) == pytest.approx(-7613, abs=1)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_solar_charging_still_counts(topology):
    coord, hass = _coordinator(topology)
    _set(hass, **SOLAR_CHARGE)
    for _ in range(5):
        assert _excess(coord) == pytest.approx(6000, abs=1)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_one_cycle_of_import_is_ignored(topology):
    """An inverter catching up with a cloud edge imports for a few seconds
    while the battery is still charging. One cycle must not change excess."""
    coord, hass = _coordinator(topology)
    _set(hass, **SOLAR_CHARGE)
    _excess(coord)
    # 13 Oct-style cloud edge: PV collapses, battery still charging, import.
    _set(hass, pv=3494, load=8737, battery=2097, grid=-7340)
    # pv - load = 3494 - 8737 = -5243 in every topology (combined: -7340 + 2097).
    assert _excess(coord) == pytest.approx(-5243, abs=1)
    _set(hass, **SOLAR_CHARGE)
    assert _excess(coord) == pytest.approx(6000, abs=1)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_credit_returns_when_grid_charge_ends(topology):
    coord, hass = _coordinator(topology)
    _set(hass, **PREDBAT_CHARGE)
    for _ in range(GRID_CHARGE_CONFIRM_CYCLES + 2):
        _excess(coord)
    # Predbat moves to hold: battery idle, surplus exported.
    _set(hass, pv=6661, load=3026, battery=0, grid=3635)
    assert _excess(coord) == pytest.approx(3635, abs=1)
    # Back to solar charging: credited from the very first cycle.
    _set(hass, **SOLAR_CHARGE)
    assert _excess(coord) == pytest.approx(6000, abs=1)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_discharging_battery_never_triggers(topology):
    coord, hass = _coordinator(topology)
    # Evening: battery covering the house, small import.
    _set(hass, pv=0, load=3000, battery=-2700, grid=-300)
    for _ in range(4):
        assert _excess(coord) == pytest.approx(-3000, abs=1)


@pytest.mark.parametrize("topology", list(TOPOLOGIES))
def test_small_trickle_charge_below_threshold_ignored(topology):
    coord, hass = _coordinator(topology)
    # Battery topping off at 300 W while a kettle pulls 400 W from the grid.
    _set(hass, pv=2000, load=2100, battery=300, grid=-400)
    for _ in range(4):
        assert _excess(coord) == pytest.approx(-100, abs=1)


def test_own_forced_grid_charge_unchanged():
    """The combined-meter branch already drops the credit for this
    integration's own grid charge; the new cap must agree with it."""
    coord, hass = _coordinator("combined")
    coord._grid_charge_engaged = True
    _set(hass, pv=300, load=400, battery=4700, grid=-4800)
    for _ in range(4):
        assert _excess(coord) == pytest.approx(-4800, abs=1)


def test_missing_battery_reading_is_a_no_op():
    coord, hass = _coordinator("combined")
    _set(hass, **PREDBAT_CHARGE)
    hass.states._states["sensor.battery_power"] = MockState("unavailable")
    for _ in range(4):
        ps = coord._collect_power_state()
        # Combined branch without a battery reading: export - import only.
        assert ps.excess_power == pytest.approx(-7613, abs=1)
    assert coord._grid_charged_battery_cycles == 0


# ---------------------------------------------------------------------------
# Through the real optimizer: what the pool does with the corrected reading
# ---------------------------------------------------------------------------

from datetime import timedelta  # noqa: E402

from freezegun import freeze_time  # noqa: E402

from custom_components.pv_excess_control.const import Action  # noqa: E402
from custom_components.pv_excess_control.optimizer import Optimizer  # noqa: E402

from .test_grid_supplement_hold import NOW, _cfg, _plan, _state, _tariff  # noqa: E402


def _pool_decision(cfg, *, confirmed, tariff, cycles=6):
    """Pool running 5 h (past its 3 h minimum) during the 14:33 grid charge.

    ``confirmed=False`` reproduces the pre-0.3.17 reading by taking every
    sample from a fresh coordinator, so the signature never confirms.
    """
    coord, hass = _coordinator("combined")
    _set(hass, **PREDBAT_CHARGE)
    history = []
    for _ in range(cycles):
        if not confirmed:
            coord, hass = _coordinator("combined")
            _set(hass, **PREDBAT_CHARGE)
        history.append(coord._collect_power_state())
    history = [h.__class__(**{**h.__dict__, "timestamp": NOW}) for h in history]
    opt = Optimizer(grid_voltage=240, controller_interval=30, off_threshold=-100)
    with freeze_time(NOW):
        return opt.optimize(
            power_state=history[-1], appliances=[cfg],
            appliance_states=[_state(is_on=True, runtime=timedelta(hours=5))],
            plan=_plan(), power_history=history, tariff=tariff,
            plan_influence="none",
        ).decisions[0]


def test_optimizer_before_confirmation_sees_solar():
    """Pre-0.3.17 reading: the pool looks solar-powered."""
    d = _pool_decision(_cfg(), confirmed=False, tariff=_tariff(price=0.18))
    assert d.action == Action.ON
    assert not d.grid_supplement, d.reason


def test_optimizer_cheap_tariff_holds_pool_as_grid_supplement():
    """0.18 under a 0.20 threshold: kept on, but now as grid supplement."""
    d = _pool_decision(_cfg(), confirmed=True, tariff=_tariff(price=0.18))
    assert d.action == Action.ON, d.reason
    assert d.grid_supplement
    assert d.reason.startswith("Grid supplement (staying on)")


def test_optimizer_without_grid_supplement_sheds_pool():
    d = _pool_decision(
        _cfg(allow_grid_supplement=False), confirmed=True,
        tariff=_tariff(price=0.18),
    )
    assert d.action == Action.OFF, d.reason


def test_optimizer_threshold_below_charge_rate_sheds_pool():
    """Cheap threshold under the grid-charge rate keeps the pool off."""
    from custom_components.pv_excess_control.models import TariffInfo

    d = _pool_decision(
        _cfg(), confirmed=True,
        tariff=TariffInfo(0.18, 0.06, 0.15, 0.15, []),
    )
    assert d.action == Action.OFF, d.reason

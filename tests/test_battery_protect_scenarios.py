"""Whole-afternoon scenario tests for battery target protection.

Each scenario is simulated minute by minute through the real Optimizer (see
battery_protect_sim.py) with protection off and with the recommended
settings (6000 W assured, 10 min margin, 9000 W bulk below 90%). The tests
compare outcomes rather than individual decisions:

  - on days where the battery can reach target anyway, protection must not
    cost the pool runtime or push it into the 0.45 peak;
  - on days where it cannot, protection must leave the battery fuller;
  - it must never make peak-time running from the battery worse. That
    happened in 0.3.12: on an overcast day it blocked the pool's 0.18 slots
    while the battery was already being grid-charged, and must-run later
    forced the pool on in the peak, running from the battery (1.78 kWh vs
    0.70 kWh with protection off).
"""
from datetime import time, timedelta

import pytest

from .battery_protect_sim import (
    OFF,
    RECOMMENDED,
    Scenario,
    simulate,
    with_pool_window_ending,
)


def _collapse(t, pv):
    return pv if t.time() < time(14, 30) else min(pv, 800)


def _ev(t):
    return 7000 if time(13, 30) <= t.time() < time(15, 0) else 0


SUNNY = [
    Scenario("today: Predbat hold, charge 15:31"),
    Scenario("today: just-in-time charge", grid_charge="jit"),
    Scenario("today: no grid charge", grid_charge="none"),
    Scenario("today: Predbat exports 12:15-14:00", grid_charge="export"),
    Scenario("today: +7 kW load 13:30-15:00", extra_load_fn=_ev, grid_charge="jit"),
    Scenario("today: no schedule deadline", deadline=None),
    Scenario("today: PV collapses 14:30, charge 15:31", pv_fn=_collapse, grid_charge="late"),
] + [
    Scenario(f"today: cloud flicker seed {k}", noise=0.35, seed=k) for k in range(1, 4)
]

CLOUDY_JIT = Scenario(
    "cloudy 45%, SoC 55, 1 h run, just-in-time charge",
    pv_scale=0.45, soc0=55, runtime0=timedelta(hours=1), grid_charge="jit",
)
CLOUDY_NO_GRID = Scenario(
    "cloudy 45%, SoC 55, 1 h run, no grid charge",
    pv_scale=0.45, soc0=55, runtime0=timedelta(hours=1), grid_charge="none",
)
OVERCAST = Scenario(
    "overcast 20%, SoC 40, no runtime yet, just-in-time charge",
    pv_scale=0.2, soc0=40, runtime0=timedelta(0), grid_charge="jit",
)
COLLAPSE_NO_GRID = Scenario(
    "PV collapses 14:30, no grid charge", pv_fn=_collapse, grid_charge="none",
)


def _pair(sc):
    return simulate(sc, OFF), simulate(sc, RECOMMENDED)


@pytest.mark.parametrize("sc", SUNNY + [CLOUDY_JIT], ids=lambda s: s.name)
def test_no_cost_when_target_is_reachable(sc):
    off, on = _pair(sc)
    assert on.runtime_end >= off.runtime_end - timedelta(minutes=10), on.log
    assert on.soc_at_target >= off.soc_at_target - 0.5
    assert on.after_target_from_battery_kwh <= off.after_target_from_battery_kwh + 0.05


def test_cloudy_without_grid_charge_leaves_battery_fuller():
    off, on = _pair(CLOUDY_NO_GRID)
    assert on.soc_at_target >= off.soc_at_target + 3, (off.soc_at_target, on.soc_at_target)
    assert on.runtime_end >= timedelta(hours=3)


def test_pv_collapse_without_grid_charge_leaves_battery_fuller():
    off, on = _pair(COLLAPSE_NO_GRID)
    assert on.soc_at_target >= off.soc_at_target
    assert on.pool_from_battery_kwh <= off.pool_from_battery_kwh


def test_overcast_does_not_push_pool_into_peak():
    """Regression for 0.3.12 (1.78 kWh from battery after 15:50 vs 0.70)."""
    off, on = _pair(OVERCAST)
    assert on.after_target_from_battery_kwh <= off.after_target_from_battery_kwh + 0.1, on.log
    assert on.runtime_end >= timedelta(hours=3)


@pytest.mark.parametrize(
    "sc", [OVERCAST, CLOUDY_JIT, CLOUDY_NO_GRID, SUNNY[0], SUNNY[6]], ids=lambda s: s.name,
)
def test_pool_window_ending_at_target_keeps_pool_out_of_peak(sc):
    """With the pool's end time and deadline at 15:50 nothing runs in the
    peak, and the 3 h minimum is still (within a few minutes) met."""
    off, on = _pair(with_pool_window_ending(sc, time(15, 50)))
    for o in (off, on):
        assert o.after_target_minutes == 0, o.log
        assert o.runtime_end >= timedelta(hours=2, minutes=55)


def test_soc_unavailable_behaves_as_if_disabled():
    sc = Scenario("SoC unavailable from 14:00", soc_unavailable_from=time(14, 0))
    off, on = _pair(sc)
    assert on.gate_first is None or on.gate_first.time() < time(14, 0)
    assert on.runtime_end >= off.runtime_end - timedelta(minutes=5)
    assert on.soc_at_target == pytest.approx(off.soc_at_target, abs=0.5)

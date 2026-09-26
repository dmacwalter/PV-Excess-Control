"""Whole-afternoon pool scenarios, simulated minute by minute through the
real optimizer (see scenario_sim.py).

These guard the 0.3.14 fixes to grid supplement and must-run:

  - on grid supplement the pool runs steadily through the 0.18 window
    instead of cycling 10 min on / 10 min off;
  - it gets its 3 h minimum whenever the day allows it;
  - it does not run into the 0.45 peak on battery.

Before those fixes the overcast scenario cycled 36 times, reached exactly
3 h only via must-run, and ran 32 min into the peak from the battery.
"""
import random
from datetime import time, timedelta

import pytest

from .scenario_sim import SEP23, TODAY, Scenario, simulate, with_pool_window_ending

WINDOW_LEFT = timedelta(hours=4, minutes=50)   # 11:00 to 15:50


def _collapse(t, pv):
    return pv if t.time() < time(14, 30) else min(pv, 800)


def _ev(t):
    return 7000 if time(13, 30) <= t.time() < time(15, 0) else 0


OVERCAST = Scenario("overcast 20%, SoC 40, no runtime yet, just-in-time charge",
                    pv_scale=0.2, soc0=40, runtime0=timedelta(0), grid_charge="jit")

NAMED = [
    Scenario("today: Predbat hold, charge 15:31"),
    Scenario("today: just-in-time charge", grid_charge="jit"),
    Scenario("today: no grid charge", grid_charge="none"),
    Scenario("today: Predbat exports 12:15-14:00", grid_charge="export"),
    Scenario("today: +7 kW load 13:30-15:00", extra_load_fn=_ev, grid_charge="jit"),
    Scenario("today: no schedule deadline", deadline=None),
    Scenario("today: PV collapses 14:30", pv_fn=_collapse, grid_charge="late"),
    Scenario("today: SoC unavailable from 14:00", soc_unavailable_from=time(14, 0)),
    Scenario("cloudy 45%, SoC 55, 1 h run, just-in-time", pv_scale=0.45, soc0=55,
             runtime0=timedelta(hours=1), grid_charge="jit"),
    Scenario("cloudy 45%, SoC 55, 1 h run, no grid charge", pv_scale=0.45, soc0=55,
             runtime0=timedelta(hours=1), grid_charge="none"),
    OVERCAST,
    with_pool_window_ending(OVERCAST, time(15, 50)),
] + [
    Scenario(f"23 Sep: {gc}", profile=SEP23, soc0=64,
             runtime0=timedelta(hours=1, minutes=50), grid_charge=gc)
    for gc in ("midday", "none", "jit")
] + [
    Scenario(f"today: cloud flicker seed {k}", noise=0.35, seed=k) for k in range(1, 4)
]


def _check(sc):
    o = simulate(sc)
    need = min(timedelta(hours=3), sc.runtime0 + WINDOW_LEFT)
    assert o.runtime_end >= need - timedelta(minutes=5), o.log
    assert o.switches <= 4, o.log
    assert o.after_target_from_battery_kwh <= 0.1, o.log
    return o


@pytest.mark.parametrize("sc", NAMED, ids=lambda s: s.name)
def test_named_scenarios(sc):
    _check(sc)


def test_overcast_runs_through_cheap_window():
    o = _check(OVERCAST)
    assert o.runtime_end >= timedelta(hours=4, minutes=30), o.log
    assert o.after_target_minutes == 0, o.log
    assert o.soc_at_target >= 99.0, o.log


def test_today_reaches_max_runtime_and_full_battery():
    o = _check(NAMED[0])
    assert o.runtime_end == timedelta(hours=7)
    assert o.soc_at_target >= 99.0


def _draw(rnd, i):
    extra = None
    if rnd.random() < 0.5:
        extra = (rnd.randint(11 * 60, 15 * 60 + 30), rnd.randint(10, 90), rnd.uniform(1, 8))
    collapse = rnd.choice([None, None, rnd.randint(12 * 60, 15 * 60 + 30)])
    dl = rnd.choice(["17:20", "17:20", "15:50", "none"])
    return Scenario(
        name=f"random-{i}",
        profile=rnd.choice([TODAY, SEP23]),
        pv_scale=rnd.choice([rnd.uniform(0.1, 0.4), rnd.uniform(0.4, 0.8), rnd.uniform(0.8, 1.2)]),
        noise=rnd.choice([0, 0.15, 0.35]),
        seed=rnd.randint(1, 10**6),
        soc0=rnd.uniform(15, 100),
        runtime0=timedelta(minutes=rnd.randint(0, 400)),
        grid_charge=rnd.choice(["none", "late", "today", "jit", "export", "midday"]),
        soc_unavailable_from=rnd.choice([None] * 9 + [time(rnd.randint(11, 15), 0)]),
        extra_load_fn=lambda t, e=extra: (
            e[2] * 1000 if e and e[0] <= t.hour * 60 + t.minute < e[0] + e[1] else 0
        ),
        pv_fn=lambda t, pv, c=collapse: (
            pv if c is None or t.hour * 60 + t.minute < c else min(pv, 800)
        ),
        deadline=None if dl == "none" else (time(15, 50) if dl == "15:50" else time(17, 20)),
        end_before=time(15, 50) if dl == "15:50" else time(17, 20),
    )


_rnd = random.Random(20260926)
RANDOM = [_draw(_rnd, i) for i in range(40)]


@pytest.mark.parametrize("sc", RANDOM, ids=lambda s: s.name)
def test_random_scenarios(sc):
    """Same checks on a fixed-seed random sample (PV level, cloud, start SoC,
    runtime done, grid-charge policy, extra loads, PV collapse, SoC dropouts,
    pool deadline, both recorded days). 900 such afternoons (seeds 1-3) were
    run offline while preparing 0.3.15: one marginal case, a pool on solar
    excess until 16:23 drawing just over 0.1 kWh from the battery after
    15:50."""
    _check(sc)

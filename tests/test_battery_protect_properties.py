"""Randomised property test for battery target protection.

A fixed-seed sample of simulated afternoons spanning PV level, cloud noise,
start SoC, runtime already done, grid-charge policy, an extra load block,
PV collapse, SoC dropouts, pool deadline and both recorded profiles. Each is
run with protection off and with the recommended settings, and must satisfy:

  1. no net battery loss by 17:30 (end SoC within 2 points of off), and no
     extra peak-time battery use unless the end SoC shows it is only shifted;
  2. SoC at the 15:50 target no more than 1 point below off;
  3. if off met the 3 h minimum runtime, protection must too (5 min slack);
  4. no more than 6 extra switchings.

The same checks were run offline on 2300 scenarios (seeds 42, 7, 2026)
while developing 0.3.14.
"""
import random
from datetime import time, timedelta

import pytest

from .battery_protect_sim import OFF, RECOMMENDED, SEP23, TODAY, Scenario, simulate

N = 40
SEED = 20260926


def _draw(rnd, i):
    extra = None
    if rnd.random() < 0.5:
        extra = (rnd.randint(11 * 60, 15 * 60 + 30), rnd.randint(10, 90), rnd.uniform(1, 8))
    collapse = rnd.choice([None, None, rnd.randint(12 * 60, 15 * 60 + 30)])
    dl = rnd.choice(["17:20", "17:20", "15:50", "none"])
    return Scenario(
        name=f"prop-{i}",
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


_rnd = random.Random(SEED)
SCENARIOS = [_draw(_rnd, i) for i in range(N)]


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: s.name)
def test_protection_properties(sc):
    off, on = simulate(sc, OFF), simulate(sc, RECOMMENDED)
    assert on.soc_end >= off.soc_end - 2.0, (off.soc_end, on.soc_end, on.log)
    if on.after_target_from_battery_kwh > off.after_target_from_battery_kwh + 0.15:
        assert on.soc_end >= off.soc_end - 1.0, on.log
    assert on.soc_at_target >= off.soc_at_target - 1.0
    three = timedelta(hours=3)
    if off.runtime_end >= three:
        assert on.runtime_end >= three - timedelta(minutes=5), (off.runtime_end, on.runtime_end, on.log)
    assert on.switches <= off.switches + 6

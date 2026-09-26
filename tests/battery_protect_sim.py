"""Closed-loop, minute-by-minute simulation used by
test_battery_protect_scenarios.py.

Drives the real Optimizer against a model of one installation (GoodWe
hybrid, 22.4 kWh battery, Ergon 14C tariff, pool pump/heater) so that the
battery target protection can be judged on outcomes over a whole afternoon,
not just single decisions.

Inputs are 5-minute means from Home Assistant statistics for 2026-09-26,
06:00-15:55 local: PV, whole-house load, and the pool's own draw (subtracted
from house load to give the base load). Scenarios scale or reshape these.

Modelled:
  - self-consumption battery: 9.6 kW discharge, charge limited to 9.6 kW
    below 90% and tapering 8.5 kW -> 5 kW across 90-99% (fitted to a grid
    charge on the day, 90->99% in ~17 min), 2.5 kW for the last percent
  - 5.4 kW export cap, surplus beyond it curtailed
  - external grid charging (Predbat or an automation), as a policy:
      none   - no grid charging
      late   - forced charge 15:31-15:50, as happened on the day
      today  - Predbat hold 12:16-14:15 (surplus exported, battery only
               covers deficit), then forced charge 15:31-15:50
      jit    - forced charge from the point where 7 kW + 3 min would only
               just finish by the target time, then held until the target
               time or 100% (as the charge on 2026-09-26 was held)
      export - Predbat force-exports 2.5 kW 12:15-14:00, then jit
      midday - forced charge 12:00-13:00 (as Predbat did on 2026-09-23)
  - tariff as the price sensor reports it, price_windows included: 0.25
    before 11:00, 0.18 to 15:50, 0.45 to 21:00; feed-in 0.06; cheap
    threshold 0.20
  - integration view: excess = export - import + battery charge power,
    SoC read as an integer %, 30 samples of history at 60 s
  - controller: 600 s switch interval, bypassed only for must-run

Not modelled: the curtailment-hold automation, Predbat re-planning, inverter
pass-through limits, heater cycling within a 5-minute slot.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from custom_components.pv_excess_control.const import Action, BatteryStrategy
from custom_components.pv_excess_control.models import (
    ApplianceConfig,
    ApplianceState,
    BatteryTarget,
    Plan,
    PowerState,
    TariffInfo,
    TariffWindow,
)
from custom_components.pv_excess_control.optimizer import Optimizer

TZ = ZoneInfo("Australia/Brisbane")
DAY = datetime(2026, 9, 26, tzinfo=TZ)
CAPACITY_KWH = 22.4
TARGET_TIME = DAY.replace(hour=15, minute=50)

# fmt: off
PV = [3,78,176,281,434,573,708,801,876,937,1061,1135,1242,1445,1859,1902,2045,2024,2120,1821,
1852,2546,2453,2144,3100,4555,4306,4382,4700,5269,6330,7198,4767,5131,7062,6408,6972,6708,7739,7316,
8066,9722,10030,9791,9390,9887,10201,10292,9479,10138,10035,8429,8970,8083,11415,10199,8192,9557,3980,9357,
10508,10548,10619,9577,9439,12866,9112,13101,11697,12922,12974,12782,13107,13012,13195,9540,9635,9396,9630,9615,
9655,9643,9686,9689,9637,9012,9055,9054,9055,9503,9102,9092,8415,8468,7968,6565,5630,5181,4877,4905,
5043,5193,4797,4383,4249,3982,3779,3737,3840,4089,4305,4576,4690,4356,4010,3889,3351,3497,4264,3603]
HOUSE = [477,410,398,411,508,689,674,628,536,4400,3128,1845,1690,1763,1246,618,752,870,669,857,
899,732,719,818,814,1831,2308,3148,3208,3364,3012,3045,3050,3038,2960,3019,3135,3128,3125,3079,
3175,3110,3111,3056,2928,3170,3973,4003,3997,3982,3992,4013,4119,4692,7754,7758,7769,7774,7558,5774,
5773,7011,8346,9690,9594,9896,9762,9507,8664,9915,9899,9916,9931,9931,7823,4127,4252,4283,4478,4236,
4270,4262,4303,4308,4254,3625,3672,3674,3672,4117,3708,3713,3725,3797,3782,3781,3701,3600,3555,3261,
3129,3105,2976,2979,2919,3023,2986,4764,6440,6751,3596,3720,3867,4638,3032,2546,2938,2436,2099,1906]
POOL = [0]*26 + [1259,1787,1874,1897,1900,1900,1900,1920,1923,1923,1903,1899,1919,1923,1923,1923,1923,1923,1923,1923,
1942,1947,1947,1929,1941,1929,1941,1930,1941,1947,1947,1947,1557,0,0,670,495,1180,1781,1955,
1971,1971,1971,1986,1980,1971,1971,1971,1971,1971,1971,1971,1971,1957,1961,1971,1971,1971,1971,1625,
1328,1328,1328,1328,1328,1328,1328,1340,1340,1340,1352,1285,1209,1209,1209,1167,1114,1073,1019,1019,
979,947,637,0,0,0,664,1329,362,0,540,36,0,0]
# fmt: on


def _slot(t: datetime) -> int:
    i = int((t - DAY.replace(hour=6)).total_seconds() // 300)
    return max(0, min(119, i))


def price(t: datetime) -> float:
    hm = t.time()
    if hm < time(11, 0):
        return 0.25
    if hm < time(15, 50):
        return 0.18
    if hm < time(21, 0):
        return 0.45
    return 0.25


def _windows() -> list[TariffWindow]:
    """The price sensor's price_windows attribute, as on 2026-09-26."""
    spans = [((0, 0), (11, 0), 0.25), ((11, 0), (15, 50), 0.18),
             ((15, 50), (21, 0), 0.45), ((21, 0), (23, 59), 0.25)]
    return [
        TariffWindow(DAY.replace(hour=a[0], minute=a[1]), DAY.replace(hour=b[0], minute=b[1]),
                     p, p <= 0.20)
        for a, b, p in spans
    ]


WINDOWS = _windows()


def max_charge_w(soc: float) -> float:
    if soc < 90:
        return 9600
    if soc < 99:
        return 8500 - (soc - 90) * (3500 / 9)
    if soc < 100:
        return 2500
    return 0


@dataclass(frozen=True)
class Profile:
    """5-minute means from 06:00 (120 slots): PV, whole-house load, pool draw."""
    name: str
    pv: list
    house: list
    pool: list


TODAY = Profile("2026-09-26", PV, HOUSE, POOL)


# 2026-09-23: broken cloud, Predbat grid charge 12:00-13:00, SoC 96% at 15:50.
# fmt: off
PV_0923 = [0,23,102,169,218,238,372,474,518,535,563,639,684,697,740,784,832,861,909,993,
1643,1780,1948,2908,3062,3106,2999,3276,4470,4656,5101,4197,5223,2354,3086,4801,5666,5559,5265,5101,
7404,4123,3428,3223,3703,4834,4815,4227,3685,2520,2340,2716,3241,3141,2594,2810,3356,3250,2973,3269,
2564,1937,2803,4268,4003,6199,7151,6640,5490,5962,5674,7824,3790,3204,7442,6273,5751,6640,7344,7876,
6330,6021,2987,1175,2164,2953,3199,3453,3596,3828,4112,4575,5214,6096,7382,3124,2066,2799,2951,3370,
3759,3830,3457,3245,3653,4761,3783,4153,6763,7639,6330,5363,3573,2878,3153,2432,2850,3051,2956,3062]
HOUSE_0923 = [430,312,384,412,390,432,565,666,618,1847,793,693,1053,1100,693,731,1202,1367,1377,822,
707,875,822,950,1547,2313,2858,2894,3099,2962,2925,5052,5201,1835,1272,2042,2529,3168,3106,3171,
3233,3215,3268,3117,3473,3552,3507,3374,3613,2947,1552,1331,1115,2007,4960,4510,4874,4499,4877,4503,
4822,4434,4714,4745,4500,4612,5129,4855,2479,2565,2607,2627,2600,2574,2758,2653,2695,2691,2689,2777,
2768,2802,2676,1966,527,577,1760,2279,2698,3244,3203,3059,2940,3048,3105,2814,2870,1280,2792,4466,
4312,2101,1385,2129,2615,2933,2854,2886,3108,3061,2917,3009,2815,2806,2824,2788,2788,2770,760,534]
POOL_0923 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,461,733,1438,1885,1908,1925,1931,1949,1591,0,0,629,957,1640,1699,1934,
1967,1948,1944,1929,1948,1948,1952,1972,1972,1610,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,461,589,1286,1782,1948,1972,1948,1971,1971,1948,1970,1948,1970,1971,
1971,1971,1971,1215,0,0,666,538,1380,1890,1948,1968,1991,1975,1971,1991,1995,452,0,0,
0,0,448,528,1284,1844,1965,1988,1977,1971,1971,1971,1971,1988,1995,1978,2003,2018,55,0]
# fmt: on
SEP23 = Profile("2026-09-23", PV_0923, HOUSE_0923, POOL_0923)


@dataclass
class Scenario:
    name: str
    profile: Profile = TODAY
    start: time = time(11, 0)
    end: time = time(17, 30)
    soc0: float = 76.0
    runtime0: timedelta = timedelta(hours=2, minutes=49)
    pv_scale: float = 1.0
    pv_fn: object = None
    extra_load_fn: object = None
    grid_charge: str = "today"
    soc_unavailable_from: time | None = None
    noise: float = 0.0
    seed: int = 1
    deadline: time | None = time(17, 20)
    end_before: time = time(17, 20)


@dataclass
class Settings:
    label: str
    rate_w: float = 0
    margin: float = 0
    bulk_w: float = 0
    taper: float = 90


OFF = Settings("off")
RECOMMENDED = Settings("6000/10 bulk 9000", 6000, 10, 9000)


@dataclass
class Outcome:
    soc_at_target: float = 0.0
    runtime_end: timedelta = timedelta()
    pool_from_battery_kwh: float = 0.0
    after_target_minutes: int = 0
    after_target_from_battery_kwh: float = 0.0
    grid_supplement_starts: int = 0
    gate_first: datetime | None = None
    switches: int = 0
    soc_end: float = 0.0
    log: list = field(default_factory=list)


def pool_config(sc: Scenario) -> ApplianceConfig:
    return ApplianceConfig(
        id="pool", name="Pool", entity_id="switch.pool_pump_heater", priority=10, phases=1,
        nominal_power=1810, actual_power_entity="sensor.pool_system_power_kw",
        dynamic_current=False, current_entity=None, min_current=6, max_current=32,
        ev_soc_entity=None, ev_connected_entity=None, is_big_consumer=False,
        battery_max_discharge_override=None, on_only=False,
        min_daily_runtime=timedelta(hours=3), max_daily_runtime=timedelta(hours=7),
        schedule_deadline=sc.deadline, switch_interval=600,
        allow_grid_supplement=True, max_grid_power=None, cheap_price_threshold=0.20,
        start_after=time(7, 30), end_before=sc.end_before, averaging_window=600,
        shed_before_grid_charge=True,
    )


def _pool_draw(t: datetime) -> float:
    return 1930.0 if t.time() < time(13, 0) else 1320.0


def _battery_flow(sc, t, soc, pv, load, charging) -> float:
    """Battery power, + charging / - discharging."""
    if charging:
        return max_charge_w(soc)
    if sc.grid_charge == "export" and time(12, 15) <= t.time() < time(14, 0):
        return -2500.0 if soc > 60 else 0.0
    if sc.grid_charge == "today" and time(12, 16) <= t.time() < time(14, 15):
        return min(pv - load, 0.0)
    flow = min(pv - load, max_charge_w(soc))
    return max(flow, -9600.0 if soc > 10 else 0.0)


def _charging(sc, t, soc) -> bool:
    if soc >= 100 or t >= TARGET_TIME:
        return False
    if sc.grid_charge in ("late", "today"):
        return time(15, 31) <= t.time() < time(15, 50)
    if sc.grid_charge == "midday":
        return time(12, 0) <= t.time() < time(13, 0)
    if sc.grid_charge in ("jit", "export"):
        mins_left = (TARGET_TIME - t).total_seconds() / 60
        short_kwh = (100 - soc) / 100 * CAPACITY_KWH
        return short_kwh / 7.0 * 60 + 3 >= mins_left
    return False


def simulate(sc: Scenario, st: Settings) -> Outcome:
    rnd = random.Random(sc.seed)
    opt = Optimizer(
        grid_voltage=240, timezone_str="Australia/Brisbane", off_threshold=-100,
        controller_interval=60,
        battery_protect_charge_rate_w=st.rate_w,
        battery_protect_margin_minutes=st.margin,
        battery_capacity_kwh=CAPACITY_KWH,
        battery_protect_bulk_rate_w=st.bulk_w,
        battery_protect_taper_soc=st.taper,
    )
    cfg = pool_config(sc)
    plan = Plan(
        created_at=DAY, horizon=timedelta(hours=24), entries=[], confidence=0.7,
        grid_charge_recommended=False,
        battery_target=BatteryTarget(100.0, TARGET_TIME, BatteryStrategy.BALANCED),
    )
    t = DAY.replace(hour=sc.start.hour, minute=sc.start.minute)
    end = DAY.replace(hour=sc.end.hour, minute=sc.end.minute)
    soc, runtime, on = sc.soc0, sc.runtime0, False
    last_change = t - timedelta(hours=1)
    history: list[PowerState] = []
    out = Outcome()
    charging = False

    with freeze_time(t) as clock:
        while t < end:
            clock.move_to(t)
            s = _slot(t)
            pv = sc.profile.pv[s] * sc.pv_scale
            if t.time() >= time(16, 0):  # data ends 16:00; fade to zero by 17:45
                pv *= max(0.0, 1 - (t - DAY.replace(hour=16)).total_seconds() / 6300)
            if sc.pv_fn:
                pv = sc.pv_fn(t, pv)
            if sc.noise:
                pv = max(0.0, pv * (1 + rnd.uniform(-sc.noise, sc.noise)))
            base_load = max(300.0, sc.profile.house[s] - sc.profile.pool[s])
            if sc.extra_load_fn:
                base_load += sc.extra_load_fn(t)
            if sc.grid_charge in ("jit", "export"):
                # latch: once started, hold until target time or full
                charging = (charging or _charging(sc, t, soc)) and soc < 100 and t < TARGET_TIME
            else:
                charging = _charging(sc, t, soc)

            pool_w = _pool_draw(t) if on else 0.0
            load = base_load + pool_w
            batt = _battery_flow(sc, t, soc, pv, load, charging)
            grid = max(load + batt - pv, -5400.0)
            export, imp = max(-grid, 0.0), max(grid, 0.0)
            soc_read = None if (
                sc.soc_unavailable_from and t.time() >= sc.soc_unavailable_from
            ) else round(soc)
            ps = PowerState(
                pv_production=pv, grid_export=export, grid_import=imp, load_power=load,
                excess_power=export - imp + batt, battery_soc=soc_read, battery_power=batt,
                ev_soc=None, timestamp=t,
            )
            history = (history + [ps])[-30:]
            state = ApplianceState(
                appliance_id="pool", is_on=on, current_power=pool_w, current_amperage=None,
                runtime_today=runtime, energy_today=0.0, last_state_change=last_change,
                ev_connected=None, ev_soc=None, activations_today=0,
            )
            result = opt.optimize(
                power_state=ps, appliances=[cfg], appliance_states=[state], plan=plan,
                power_history=history, tariff=TariffInfo(price(t), 0.06, 0.20, 0.20, WINDOWS),
                plan_influence="light",
            )
            if opt._battery_protection_active(cfg) and out.gate_first is None:
                out.gate_first = t
            if result.decisions:
                d = result.decisions[0]
                want_on = d.action in (Action.ON, Action.SET_CURRENT)
                can_switch = (t - last_change).total_seconds() >= 600 or d.bypasses_cooldown
                if want_on != on and can_switch:
                    on, last_change = want_on, t
                    out.switches += 1
                    if on and "grid supplement" in d.reason.lower():
                        out.grid_supplement_starts += 1
                    out.log.append(f"{t:%H:%M} SoC {soc:5.1f} {'ON ' if on else 'OFF'} {d.reason}")

            pool_w = _pool_draw(t) if on else 0.0
            if on:
                runtime += timedelta(minutes=1)
                from_pv = min(pool_w, max(pv - base_load, 0.0))
                rest_kwh = (pool_w - from_pv) / 60000
                if not charging:
                    out.pool_from_battery_kwh += rest_kwh
                    if t >= TARGET_TIME:
                        out.after_target_from_battery_kwh += rest_kwh
                if t >= TARGET_TIME:
                    out.after_target_minutes += 1
            batt = _battery_flow(sc, t, soc, pv, base_load + pool_w, charging)
            soc = min(100.0, max(0.0, soc + batt / 60000 / CAPACITY_KWH * 100))
            if t == TARGET_TIME:
                out.soc_at_target = soc
            t += timedelta(minutes=1)
    out.runtime_end = runtime
    out.soc_end = soc
    return out


def with_pool_window_ending(sc: Scenario, at: time) -> Scenario:
    return replace(sc, deadline=at, end_before=at)

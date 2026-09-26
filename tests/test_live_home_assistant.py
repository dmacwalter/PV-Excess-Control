"""End-to-end tests in a real Home Assistant instance.

Everything else in this suite drives the optimizer or a mocked coordinator.
These load the integration the way Home Assistant does: a config entry with
an appliance subentry, platforms forwarded, the coordinator on its update
timer. Sensors are fed minute by minute from the scenario simulator
(scenario_sim.py), and the integration switches a stand-in pool, whose power
and state feed back into the sensors.

The configuration mirrors one real installation: GoodWe hybrid, 22.4 kWh
battery, Ergon 14C price sensor with price_windows, and a pool of 1810 W
nominal needing 3-7 h a day with grid supplement allowed.

Set PVEC_TRACE_DIR to write a minute-by-minute JSON trace per scenario
(switch calls, every integration entity state, analytics). Diffing traces
from two versions is a quick way to confirm a refactor changed nothing.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.pv_excess_control.const import DOMAIN

from . import scenario_sim as S

pytestmark = pytest.mark.skipif(
    "subentries_data" not in MockConfigEntry.__init__.__code__.co_varnames,
    reason="Home Assistant test harness too old for config subentries",
)

ENTRY_DATA = {
    "inverter_type": "hybrid", "grid_voltage": 240,
    "pv_power": "sensor.pv", "import_export_power": "sensor.grid", "load_power": "sensor.load",
    "battery_soc": "sensor.soc", "battery_power": "sensor.batt", "battery_capacity": 22.4,
    "tariff_provider": "generic", "price_sensor": "sensor.price", "feed_in_tariff": 0.06,
    "cheap_price_threshold": 0.20, "battery_charge_price_threshold": 0.20,
    "forecast_provider": "none", "battery_strategy": "balanced",
    "battery_target_soc": 100, "battery_target_time": "15:50",
    "controller_interval": 60, "planner_interval": 900, "off_threshold": -100,
}
POOL = {
    "appliance_name": "Pool", "appliance_entity": "input_boolean.pool", "appliance_priority": 10,
    "nominal_power": 1810.0, "actual_power_entity": "sensor.pool_power", "phases": 1,
    "dynamic_current": False, "min_daily_runtime": 180, "max_daily_runtime": 420,
    "schedule_deadline": "17:20", "start_after": "07:30", "end_before": "17:20",
    "switch_interval": 600, "allow_grid_supplement": True, "cheap_price_threshold": 0.20,
    "averaging_window": 600, "shed_before_grid_charge": True, "on_only": False,
    "is_big_consumer": False,
}
STATUS = "sensor.pv_excess_control_pool_status"


async def _run_day(hass: HomeAssistant, freezer, sc: S.Scenario, name: str, until=(16, 30)):
    """Set the integration up and run it from 11:00 to ``until``, one cycle a
    minute. Returns (switch calls, per-minute trace, analytics, entry)."""
    rnd = random.Random(sc.seed)
    await hass.config.async_set_time_zone("Australia/Brisbane")
    t = S.DAY.replace(hour=11, minute=0)
    freezer.move_to(t.astimezone(timezone.utc))

    pool_on = {"v": False}
    calls: list[tuple[str, str]] = []

    async def _switch(call: ServiceCall) -> None:
        calls.append((datetime.now(S.TZ).strftime("%H:%M"), call.service))
        pool_on["v"] = call.service == "turn_on"
        hass.states.async_set("input_boolean.pool", "on" if pool_on["v"] else "off")

    async def _notify(call: ServiceCall) -> None:
        pass

    # A real install always has these; a bare test instance does not.
    hass.services.async_register("input_boolean", "turn_on", _switch)
    hass.services.async_register("input_boolean", "turn_off", _switch)
    hass.services.async_register("persistent_notification", "create", _notify)

    state = {"soc": sc.soc0, "charging": False}
    windows = [dict(start=w.start.isoformat(), end=w.end.isoformat(), price=w.price)
               for w in S.WINDOWS]

    def feed(t: datetime) -> None:
        slot = S._slot(t)
        pv = sc.profile.pv[slot] * sc.pv_scale
        if sc.noise:
            pv = max(0.0, pv * (1 + rnd.uniform(-sc.noise, sc.noise)))
        base = max(300.0, sc.profile.house[slot] - sc.profile.pool[slot])
        soc = state["soc"]
        if sc.grid_charge in ("jit", "export"):
            state["charging"] = ((state["charging"] or S._charging(sc, t, soc))
                                 and soc < 100 and t < S.TARGET_TIME)
        else:
            state["charging"] = S._charging(sc, t, soc)
        pool_w = S._pool_draw(t) if pool_on["v"] else 0.0
        load = base + pool_w
        batt = S._battery_flow(sc, t, soc, pv, load, state["charging"])
        grid = min(pv - load - batt, 5400.0)  # + export / - import
        for eid, val, unit, extra in (
            ("sensor.pv", pv, "W", {}),
            ("sensor.load", load, "W", {}),
            ("sensor.grid", grid, "W", {}),
            ("sensor.batt", batt, "W", {}),
            ("sensor.soc", round(soc), "%", {}),
            ("sensor.pool_power", pool_w / 1000, "kW", {}),
            ("sensor.price", S.price(t), "AUD/kWh", {"price_windows": windows}),
        ):
            hass.states.async_set(eid, str(round(val, 3)), {"unit_of_measurement": unit, **extra})
        state["soc"] = min(100.0, max(0.0, soc + batt / 60000 / S.CAPACITY_KWH * 100))

    hass.states.async_set("input_boolean.pool", "off")
    feed(t)
    entry = MockConfigEntry(
        domain=DOMAIN, title="PV Excess Control", data=ENTRY_DATA,
        subentries_data=[{"data": POOL, "subentry_type": "appliance", "title": "Pool",
                          "unique_id": None}],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    trace = []
    end = S.DAY.replace(hour=until[0], minute=until[1])
    while t < end:
        t += timedelta(minutes=1)
        feed(t)
        freezer.move_to(t.astimezone(timezone.utc))
        async_fire_time_changed(hass, t.astimezone(timezone.utc))
        await hass.async_block_till_done()
        trace.append({
            "t": t.strftime("%H:%M"), "pool_on": pool_on["v"], "soc": round(state["soc"], 2),
            "states": {s.entity_id: s.state for s in hass.states.async_all()
                       if DOMAIN in s.entity_id},
        })

    a = hass.data[DOMAIN][entry.entry_id].analytics
    analytics = {k: getattr(a, k) for k in dir(a)
                 if not k.startswith("_") and isinstance(getattr(a, k), (int, float))}
    if os.environ.get("PVEC_TRACE_DIR"):
        os.makedirs(os.environ["PVEC_TRACE_DIR"], exist_ok=True)
        with open(os.path.join(os.environ["PVEC_TRACE_DIR"], f"{name}.json"), "w") as fh:
            json.dump({"calls": calls, "trace": trace, "analytics": analytics}, fh, indent=0)
    return calls, trace, analytics, entry


def _at(trace, hhmm):
    return next(x for x in trace if x["t"] == hhmm)


async def test_setup_creates_entities_and_unloads(hass, freezer, enable_custom_integrations):
    _, trace, _, entry = await _run_day(hass, freezer, S.Scenario("today"), "setup", until=(11, 5))
    states = trace[-1]["states"]
    for eid in (STATUS, "sensor.pv_excess_control_excess_power",
                "sensor.pv_excess_control_pool_runtime_today",
                "switch.pv_excess_control_control_enabled",
                "switch.pv_excess_control_pool_enabled",
                "number.pv_excess_control_pool_min_daily_runtime"):
        assert eid in states, eid
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_sunny_day_runs_pool_steadily_on_solar(hass, freezer, enable_custom_integrations):
    calls, trace, analytics, _ = await _run_day(hass, freezer, S.Scenario("today"), "today")
    # Runtime counting starts at setup (11:00) here, so the 7 h maximum is not
    # reached by 16:30: one start after the 60 s startup grace, then steady.
    assert calls == [("11:02", "turn_on")]
    assert float(trace[-1]["states"]["sensor.pv_excess_control_pool_runtime_today"]) >= 5.4
    assert analytics["solar_consumed_kwh"] > 0
    assert analytics["self_consumption_ratio"] > 0


async def test_overcast_day_holds_pool_on_grid_until_peak(hass, freezer, enable_custom_integrations):
    sc = S.Scenario("overcast", pv_scale=0.2, soc0=40, runtime0=timedelta(0), grid_charge="jit")
    calls, trace, analytics, _ = await _run_day(hass, freezer, sc, "overcast_jit")
    # One start, held through the 0.18 window, one stop when it closes at 15:50.
    assert calls == [("11:02", "turn_on"), ("15:50", "turn_off")]
    assert _at(trace, "14:00")["states"][STATUS].startswith("Grid supplement (staying on)")
    assert not any(x["pool_on"] for x in trace if x["t"] > "15:50")
    assert analytics["savings_today"] > 0             # grid-supplement energy costed


async def test_cloud_flicker_does_not_cycle(hass, freezer, enable_custom_integrations):
    calls, trace, _, _ = await _run_day(hass, freezer, S.Scenario("flicker", noise=0.35, seed=3),
                                        "flicker")
    assert len(calls) <= 4, calls
    assert float(trace[-1]["states"]["sensor.pv_excess_control_pool_runtime_today"]) >= 3.0

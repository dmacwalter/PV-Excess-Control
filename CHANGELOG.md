# Changelog — dmacwalter fork of PV Excess Control

All changes documented here are **additions to** the upstream project by
[Henrik Wasserfuhr / InventoCasa](https://github.com/InventoCasa/PV-Excess-Control),
which is the origin of essentially all of this integration's code: the
architecture, planner, optimizer, tariff and forecast providers, config flow,
dashboards, documentation and test suite are all his work. This fork adds a
small number of battery-SoC-aware safety gates and external-controller options
on top of that engine.

**Every change below is additive and opt-in.** With all new options left at
their defaults (`False` / empty), behaviour is identical to upstream. These
changes are intended to be offered back upstream.

---

## Overview

| Area | Upstream behaviour | This fork |
|---|---|---|
| PREEMPT phase | Turns on any IDLE appliance once enough wattage is freed by shedding lower-priority ones — no SoC awareness | Skips appliances flagged `battery_target_gated` once the battery has met the plan's target SoC |
| Grid supplement (3 paths) | Activates on cheap tariff + power budget alone | Same, plus respects `battery_target_gated` |
| Externally-managed loads (evcc etc.) | Counted as consumption; this integration yields to them | Optional add-back so this integration's appliances take priority instead — with an optional override to reverse it |
| Cheap-window target current field | Pre-fills with `max_current` even when unset | Genuinely empty until deliberately set |
| Forced grid charge vs. shedding | No way to guarantee a specific appliance sheds first | `shed_before_grid_charge` flag + one-cycle deferral |
| Battery power during grid charge | Can be double-counted as "excess" | Grid-charge false-positive fix |
| SHED near appliance deadlines | Reacts to instantaneous excess only | Deadline-aware shed protection via per-appliance averaged excess |
| Appliance running post-deadline | No battery-state check | Blocked unless battery met its target |

---

## Changes

### 1. Battery target gate (`battery_target_gated`)

**Problem.** PREEMPT is a pure power-budget feasibility check. If shedding a
lower-priority appliance frees enough PV budget on paper, PREEMPT turns the
higher-priority IDLE appliance on. That is correct for a load that draws only
what the surplus supports — but not for a switch that *commands an inverter to
charge*. Such a switch isn't wattage-limited: it tells the inverter to charge,
and the inverter pulls whatever it needs, including from the grid.

Observed in production (GoodWe hybrid + 22.4 kWh battery):

```
14:40:22  Pool heater shed — "insufficient excess (priority 10)"
14:41:21  switch.goodwe_fast_charging_switch → ON
14:42:21  status: "Preemption: started after shedding lower-priority appliances"
```

Battery SoC was 98 % at 14:38 and had been climbing on solar alone all day
(87 % at 12:08 → 98 % at 14:38). Grid power was imported into an effectively
full battery. The switch only stopped when SoC hit 100 %.

This is not the documented grid-charging path
(`docs/features/battery-management.md`), which correctly gates on *"the battery
cannot reach its target using solar alone"* and on the price threshold. PREEMPT
bypasses that reasoning entirely — it never even tags its decisions as grid
supplement, because from its point of view it is allocating solar.

**Fix.**
- New `ApplianceConfig.battery_target_gated: bool` (default `False`).
- New `Optimizer._battery_target_reached()` comparing `power_state.battery_soc`
  against `plan.battery_target.target_soc`. Returns `False` (does not block)
  when the plan, target or SoC reading is missing — it only ever blocks on
  positive confirmation, never on absent data.
- Applied at all four places such an appliance can be switched on outside the
  normal solar-excess path:
  1. Opportunity-cost grid supplement (`_allocate_appliance`)
  2. Standard-appliance grid supplement (`_allocate_standard`)
  3. Dynamic-current grid supplement (`_allocate_dynamic_current`)
  4. **PREEMPT** (`_preempt`) — the actual trigger in the incident above

**Files:** `models.py`, `const.py`, `config_flow.py`, `coordinator.py`,
`optimizer.py`, `strings.json`, `translations/en.json`

**UI:** *"Block Fast-Charge Preemption Once Battery Full"* on the appliance
config page.

---

### 2. Externally-managed load add-back

**Problem.** A large load controlled by *another* system — evcc, an OEM wallbox
app — still appears in the grid meter reading. From this integration's point of
view the solar surplus has vanished, so it sheds its own appliances and the
external controller takes everything. When both systems are surplus-following,
they compete for the same watts and whichever samples first wins.

This was previously solved outside the integration with a template sensor that
added EV charger power back onto the grid reading before feeding it in. That
works, but bakes a `* 1000` kW→W assumption into a Jinja template and is
invisible to anyone else running the integration.

**Fix.** Three optional fields on the **Sensor Mapping** page:

| Config key | UI label |
|---|---|
| `external_load_power` | Externally-Managed Load Power Sensor |
| `external_load_priority_entity` | External Load Priority Mode Entity |
| `external_load_priority_state` | Priority Mode State Value |

When `external_load_power` is set, that load's live draw is added back onto the
computed excess after all topology branches, so the optimizer sees the surplus
that *would* exist if the external load weren't drawing. Its own appliances
allocate against that figure first; the external controller then backs off to
whatever remains (evcc does this via `residualPower` / aux meters).

**Both configurations are valid and supported:**

- **Sensor set** → this integration's appliances take priority over the
  external load.
- **Sensor empty** → the external load takes priority. This is upstream
  behaviour and remains the default.

The priority-mode pair temporarily reverses whichever choice was made. While
`external_load_priority_entity` matches `external_load_priority_state`, the
add-back is skipped — so an explicit "charge now" request is honoured: the
optimizer sees the genuinely reduced surplus and sheds its own appliances out
of the way like any other load, rather than protecting them against a charge
the user deliberately asked for. For evcc the entity is the charge-mode select
and the value is `now` (the raw mode value behind the Fast Charge button — the
entity reports the raw value, not the UI label).

**Implementation notes:**
- Power is read via `_parse_sensor_float(power=True)`, which normalises W / kW /
  MW from each sensor's own `unit_of_measurement` — no hardcoded unit
  assumption.
- The add-back is skipped when `excess_power is None`. A sensor outage must
  propagate as `None` so the optimizer's safety-only path engages; adding to
  `None` would fabricate a trustworthy-looking number from missing data.
- State matching is case-insensitive and whitespace-trimmed on both sides.
- If the priority entity is missing or unavailable, the add-back **is** applied
  — same as if no override were configured.
- Config-flow validation rejects setting the priority fields without the load
  sensor, or one half of the pair without the other.

**Files:** `const.py`, `coordinator.py`, `config_flow.py`, `strings.json`,
`translations/en.json`

---

### 3. Cheap-window target current pre-fill fix

`config_flow.py` set `suggested_value` for `cheap_grid_target_current` to
`d.get(CONF_MAX_CURRENT, 16.0)` when the field had never been set. HA renders
`suggested_value` as a pre-filled number, so every dynamic-current appliance
appeared deliberately configured for a cheap-window target at max current.

That is not cosmetic: `_cheap_window_target_amps()` treats "field has a value"
as "the user wants cheap-window grid-supplement targeting at that amperage", so
appliances with `allow_grid_supplement` could silently opt into cheap-tariff
grid charging at max current.

Now reads `d.get(CONF_CHEAP_GRID_TARGET_CURRENT)` with no fallback.

> **Note:** this only prevents *new* pre-fills. Configs saved while the old
> pre-fill was showing may already have the value persisted — audit existing
> appliances for accidental carryovers.

---

### 4. `shed_before_grid_charge`

Flags an appliance to always be shed before the forced-grid-charge state
machine engages — regardless of whether `min_daily_runtime` is met, and
regardless of whether shedding it alone is projected to close the gap.
Engagement is deferred one cycle so the freed power has a chance to register in
`battery_power` first, avoiding a race where grid charge engages against stale
readings.

### 5. Grid-charge false-positive fix

Prevents battery power being credited back as "excess" while the battery is
being charged *from the grid*. Upstream's hybrid-branch adjustment adds
`battery_power` to recover solar going into the battery, which is correct in
normal self-consumption but double-counts during forced grid charge —
potentially masking a large grid draw as surplus for any downstream consumer
reading the same figure.

### 6. Deadline-aware shed protection

In `_shed`, appliances with both a `schedule_deadline` and an
`averaging_window` are judged against their own averaged excess rather than the
shared instantaneous budget, until the deadline passes. SHED reads instantaneous
excess by design, but that urgency isn't warranted while there is no deadline
pressure — this stops a brief dip from shedding an appliance that had time to
ride it out. Falls through to normal instant-based shedding once the deadline
passes or the averaged figure also looks bad.

### 7. Post-deadline battery lock

`_check_post_deadline_battery`: once both the appliance's `schedule_deadline`
and the battery's target time have passed, the appliance is blocked unless the
battery has met its target SoC — stopping a deadline-constrained appliance
(e.g. a pool) from draining the battery during peak tariff after the solar
window has closed.

---

## Testing status

- All modified modules compile cleanly.
- The external-load add-back decision table was verified in isolation across
  ten cases: PV mode, priority mode, case and whitespace variants, unavailable
  priority entity, unavailable power sensor, zero draw, `None` excess, feature
  unconfigured, and incomplete override config.
- **Not run:** the upstream `pytest` suite, which requires the `homeassistant`
  package. Config-flow wiring is verified by compilation and inspection only —
  walk the config flow once after installing to confirm the new fields render
  as expected.

---

## Suggested upstream PR description

> ### Add battery-SoC-aware gating for inverter-commanded charge switches
>
> Adds an opt-in `battery_target_gated` flag for appliances that command an
> inverter to charge (e.g. a GoodWe "fast charge" switch) rather than being
> wattage-limited to actual solar excess.
>
> **Problem:** PREEMPT and the grid-supplement paths are pure power-budget
> checks with no battery SoC awareness. In production this let PREEMPT free
> wattage by shedding a lower-priority appliance and use it to justify enabling
> a battery fast-charge switch — with the battery already at 98 % SoC and
> climbing on solar alone, resulting in grid import into a nearly-full battery.
> This bypasses the documented grid-charging logic, which correctly gates on
> "cannot reach target using solar alone" plus a price threshold.
>
> **Fix:** flagged appliances are excluded from PREEMPT and all three
> grid-supplement paths once `battery_soc >= plan.battery_target.target_soc`.
> Default `False`, fully backward compatible. The gate never blocks on missing
> data (no plan / no target / no SoC reading → not blocked).
>
> Also included: a UI fix where the "cheap window target current" field's
> suggested value defaulted to `max_current`, making every dynamic-current
> appliance look deliberately configured for max-current grid draw.

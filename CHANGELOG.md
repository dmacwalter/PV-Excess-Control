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
| Forced grid charge vs. shedding | No way to guarantee a specific appliance sheds first | `shed_before_grid_charge` flag + hold until the charge cycle resolves (0.3.2) |
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

> **Superseded in 0.3.2.** The one-cycle deferral alone was not sufficient —
> see section 8. The shed intent is now held until the charge cycle resolves.

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

### 8. Battery-priority shed hold (0.3.2)

**Problem.** The `shed_before_grid_charge` deferral (section 4) shed the
appliance and waited one cycle before engaging grid charge, so the freed power
could register. But `battery_priority_shed` was set in exactly one place and
read in exactly one place, and **both required `is_on`**.
`_get_appliance_states` rebuilds every `ApplianceState` each cycle without that
field, so it defaulted to `False` on the cycle after a shed — and could not be
re-set, because the setter requires the appliance to still be on.

During the deferral cycle the optimizer therefore saw an ordinary OFF appliance
plus excess that existed *only because that appliance had just been shed*, and
restarted it via ALLOCATE. Observed in production as
`Excess available (3822W >= 2010W needed)` one cycle after
`Battery priority: min runtime met, freeing solar for battery`, followed by the
appliance and the grid-charge state machine oscillating against each other —
each spurious engagement costing a guaranteed 5 minutes of grid import via
`grid_charge_engage_min_duration_minutes`.

**Fix.**

- `_battery_priority_hold: set[str]` tracks appliances currently held OFF, and
  is persisted to `config_entry.data` via the runtime-state-key bypass (the
  same no-reload pattern as `_grid_charge_engaged`). A restart mid-hold
  previously dropped the intent and restarted the appliance on inflated excess.
- `_get_appliance_states` carries `battery_priority_shed` forward from that set
  instead of defaulting it to `False`.
- The optimizer's battery-priority branch now handles the OFF case as well,
  returning `IDLE` rather than falling through to ALLOCATE.
- The hold releases on target SoC reached, past target time, or price no longer
  cheap — deliberately **not** on "solar now covers target", which is circular:
  solar only covers it because the appliance is being held off.
- `_is_behind_deadline_raw()` mirrors the optimizer's deadline must-run test.
  Appliances behind their runtime deadline are neither shed nor held, so
  runtime commitments still win. Without this the two fight one cycle apart —
  must-run turns the appliance on, the shed knocks it straight back off.

**Note on scope.** This fixes the oscillation *after* a shed decision. It does
not change when the shed fires: `_solar_can_fill_battery` remains a reactive
per-cycle judgement, and `_balanced_strategy` in the planner is still
deadline-unaware (a flat 50/50 split of each slot's excess that never reads
`target_time`). Making the planner anticipate the battery deadline is a
separate design change.

---

### 9. Per-appliance averaging window used the wrong controller cadence (0.3.4)

**Problem.** `Optimizer.optimize()` converted a per-appliance
`averaging_window` (seconds) into a count of `power_history` entries with
`entries_needed = int(averaging_window / controller_interval)`, but
`controller_interval` was hardcoded to `30` and never received the real
value from the coordinator's configured `controller_interval` (which
defaults to 30s but is user-configurable — e.g. 60s in production here).

At a 60s controller cadence this silently doubled the effective averaging
window for any appliance with a custom `averaging_window` set: a configured
5-minute window actually averaged the last 10 minutes of history. The one
existing test for this path built its fixture history at 30s spacing, which
happened to match the hardcoded constant, so it passed without exercising
the real cadence.

**Fix.** `optimize()` now accepts `controller_interval_s` (default `30`,
preserving prior behaviour for any caller that doesn't pass it), and the
coordinator passes its real `self.update_interval.total_seconds()` on every
call.

**Testing status.**

- Full suite: 903 passed (901 pre-existing + 2 new), 0 failed.
- Along the way, fixed three stale test-fixture gaps unrelated to production
  code (hand-built coordinator mocks in `test_init.py` / `test_coordinator.py`
  missing fields added to `__init__` after the fixtures were written; one
  setup test leaking a real HA timer onto the event loop). None were
  production defects — the real `__init__` path was correct throughout.
- New: `tests/test_averaging_window_edge_cases.py` — two tests exercising a
  real 60s controller cadence (rather than the previously-hardcoded-matching
  30s), including a regression guard asserting the same `averaging_window`
  yields a different, correctly-scaled result at 30s vs 60s.

---

### 10. Backported fixes from Kolbi/PV-Excess-Control (0.3.5)

While comparing against [Kolbi's independent fork](https://github.com/Kolbi/PV-Excess-Control),
found they'd separately landed a fix for the same averaging-window bug as
section 9 (their PR #12, merged five days before this fork's 0.3.4), plus an
unrelated EV-budget fix. Backported both, with two refinements over the
0.3.4 fix along the way:

**a) `math.ceil()` instead of `int()` when converting `averaging_window` to
an entry count.** `int()` truncates: a 250s window at a 60s controller
interval gave 4 entries (240s of actual coverage), falling short of what was
configured. `math.ceil()` gives 5 entries (300s), never under-covering the
requested window.

**b) `power_history` retention now scales with the real controller interval
too.** The buffer was capped at a flat `MAX_HISTORY_SIZE = 60` entries
(~30 min at a 30-60s interval) independent of `averaging_window`. The 0.3.4
fix corrected the *conversion* from window to entry count, but a
sufficiently long `averaging_window` at a fast controller interval could
still be silently capped by this second, separate constant before the
conversion ever got a chance to matter. Replaced with
`_history_size_for_interval()`, which sizes the buffer to always cover the
new `MAX_AVERAGING_WINDOW` constant (1800s) at whatever interval is
configured.

**c) EV-connected budget fix (unrelated to averaging windows).** A
dynamic-current appliance with `override_active=True` and OFF unconditionally
reserved `max_current * grid_voltage * phases` worth of budget for
lower-priority appliances to work around -- even when its
`ev_connected_entity` explicitly reported the vehicle disconnected. No
vehicle plugged in means no load can actually be created, so this starved
other appliances of budget for a charger with nothing attached. Fixed to
reserve `0.0` in that specific case; the override command itself is
unchanged (still sent, in case a vehicle connects mid-cycle).

The `Optimizer` constructor now takes `controller_interval` directly
(matching Kolbi's cleaner design) instead of the 0.3.4 per-call
`controller_interval_s` parameter, which is retained only as an optional
override for any caller not yet updated to construct the optimizer with the
real interval.

**Testing status.**

- Full suite: 905 passed (903 pre-existing + 2 new), 0 failed.
- New: `test_averaging_window_entries_needed_uses_ceil_not_floor` --
  constructs history where a floor'd 4-entry window and a ceil'd 5-entry
  window give measurably different averages, confirming the fix actually
  takes effect rather than being masked by coincidentally-equal values.
- New: `test_manual_override_off_ev_disconnected_reserves_no_power` --
  verified to fail against the pre-fix code (a lower-priority pool appliance
  gets starved of budget by a disconnected EV's phantom 3680W reservation)
  before confirming it passes against the fix.

---

### 11. Local brand icon (0.3.6)

**Problem.** The integration's tile in Settings → Devices & Services showed
"icon not available" — the logo added in 0.3.4 only lived in the GitHub
README, which HA's frontend has no way to read. HA icons come either from
the centralized `home-assistant/brands` repo (requires a separate PR there)
or, since HA 2026.3, from a `brand/` folder shipped inside the integration
itself.

**Fix.** Added `custom_components/pv_excess_control/brand/` with
`icon.png` (256×256), `icon@2x.png` (512×512), `logo.png`, and
`logo@2x.png`, generated from the existing `logo.png`/`logo.svg` (transparent
background, circular badge fully contained in-frame — already correctly
composed for icon use). Local brand images take priority over the CDN
automatically; no manifest or config changes needed. Requires HA 2026.3+ to
take effect — on older HA the folder is silently ignored and the tile falls
back to its previous "icon not available" state, so this is a safe no-op on
older installs rather than a hard requirement bump.

---

---

### 12. Trim microsecond precision from the max-daily-runtime status message (0.3.7)

**Problem.** The "Max daily runtime reached" status/log message
interpolated `state.runtime_today` and `appliance.max_daily_runtime`
(both `timedelta`) directly into an f-string, which renders as
`str(timedelta)` -- e.g. `"7:00:13.042882 >= 7:00:00"`. The
microsecond suffix comes from HA's controller-cycle timing jitter and
carries no useful information for a person reading the pool pump's
status history.

**Fix.** Round both values to the nearest second before formatting:
`timedelta(seconds=round(td.total_seconds()))`. Message now reads
`"7:00:13 >= 7:00:00"`.

**Testing status.** Full suite: 906 passed (905 pre-existing + 1 new),
0 failed. New test asserts no `"."` appears in the rendered reason
string.

---

## Testing status

- **0.3.2:** the upstream `pytest` suite now runs — 888 passed. The 13
  remaining failures and 1 error are pre-existing and byte-identical before and
  after the change (the test environment resolves to HA 2025.1.4 while the
  integration targets 2026.x); no regressions introduced.
- **0.3.2:** 11 new tests in `tests/test_battery_priority_hold.py`, of which 5
  fail against unpatched source. These are the first tests to cover
  `battery_priority_shed`, `shed_before_grid_charge`, or the hold's persistence
  across restarts — `grep` for any of them previously returned nothing.
- **0.3.2:** the interaction was additionally exercised by driving the real
  `Optimizer` through a simulation harness across ten edge cases plus
  adversarial restart, starvation, cloud-flicker and engage-floor scenarios.
  Headline results (before -> after): observed incident 3 -> 1 toggles;
  marginal excess 13 -> 0; cloud flicker 15 -> 1 with grid import 0.107 -> 0.000
  kWh; unreachable battery target 179 -> 1; restart mid-hold 2 -> 0. A
  genuinely-needed grid charge still engages on the identical cycle.
  Caveat: the harness modelled the real-time path of `_solar_can_fill_battery`,
  not the Solcast forecast path that triggers it in production, so trigger
  thresholds there will differ. The interaction is downstream of that decision.
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

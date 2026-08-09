# PV Excess Control — Fork Changes vs. InventoCasa Upstream

This fork (`dmacwalter/PV-Excess-Control`) extends the upstream `optimizer.py` /
`coordinator.py` decision engine with battery-SoC-aware safety gates that the
upstream project does not have. Upstream's real-time controller (ALLOCATE,
PREEMPT, SHED) is purely a power-budget feasibility engine — it has no
concept of "is the battery already where it needs to be" outside the
separate 24h planner. These changes close that gap for the parts of the
system that can pull grid power.

## Summary

| Area | Upstream behaviour | This fork |
|---|---|---|
| PREEMPT phase | Turns on any IDLE appliance once enough wattage is freed by shedding lower-priority appliances — no SoC check | Skips battery-charge-control appliances (flagged `battery_target_gated`) once the battery has met the plan's target SoC |
| Grid supplement (all 3 paths) | Activates purely on cheap tariff + power budget | Same, but also respects `battery_target_gated` |
| Cheap-window target current field | UI pre-fills with `max_current` even when unset, making every appliance look "configured" for max-current grid draw | Field genuinely defaults to empty until deliberately set |
| Forced grid charge vs. appliance shedding | No mechanism to guarantee a specific appliance is shed first | `shed_before_grid_charge` flag + one-cycle deferral |
| Battery charging while grid-charging | Can double-count grid-sourced battery power as "excess" | Grid-charge false-positive fix prevents this |
| SHED phase near appliance deadlines | Reacts only to instantaneous excess — a brief dip can shed something that had time to recover | Deadline-aware shed protection: appliances with a `schedule_deadline` are judged on their own averaged excess until the deadline passes |
| Appliance running post-deadline | No check against battery state | Blocked from running past `schedule_deadline` once the battery's target time has also passed, unless the battery has met its target — stops e.g. the pool draining the battery during peak tariff after the solar window closes |

## Detail

### 1. Battery target SoC gate (`battery_target_gated`)

**Problem:** PREEMPT is a pure power-budget check. If shedding a
lower-priority appliance (e.g. the pool heater) frees enough wattage on
paper, PREEMPT will turn on a higher-priority IDLE appliance — even if
that appliance is actually an inverter "fast charge" switch that commands
AC/grid current directly rather than being wattage-modulated. Observed in
production: pool heater shed at 14:40 → fast-charge switch turned on at
14:41 → battery was already at 98% SoC and climbing on solar alone. Grid
power was imported into an effectively full battery.

**Fix:**
- New `ApplianceConfig.battery_target_gated: bool` field (`const.py`,
  `models.py`, `config_flow.py`, `coordinator.py`).
- New `Optimizer._battery_target_reached()` helper compares
  `power_state.battery_soc` against `plan.battery_target.target_soc`.
- Gate applied at all three places an appliance can be turned on from
  outside the normal solar-excess-only path:
  1. Opportunity-cost grid supplement (`_allocate_appliance`)
  2. Standard-appliance grid supplement (`_allocate_standard`)
  3. Dynamic-current grid supplement (`_allocate_dynamic_current`)
  4. PREEMPT (`_preempt`) — the actual trigger in the production incident

Appliances without the flag set are unaffected (default `False`,
backward compatible with existing configs).

### 2. Cheap-window target current UI bug

**Problem:** `config_flow.py`'s `suggested_value` for
`cheap_grid_target_current` fell back to `d.get(CONF_MAX_CURRENT, 16.0)`
when the field had never been set, rather than falling back to nothing.
HA renders a `suggested_value` as a pre-filled number, so every
dynamic-current appliance appeared to have a deliberately configured
cheap-window target at max current — silently opting appliances into
cheap-tariff grid-supplement targeting that nobody chose.

**Fix:** `suggested_value` now reads `d.get(CONF_CHEAP_GRID_TARGET_CURRENT)`
with no fallback, so the field is genuinely empty until a value is set.

> Note: this only stops new pre-fills. Existing appliance configs that
> were saved while the field showed a pre-filled max-current value may
> already have that value persisted — worth auditing existing appliances
> for accidental carryovers.

### 3. `shed_before_grid_charge`

Flags an appliance (e.g. the pool pump/heater) to always be shed before
the forced-grid-charge state machine is allowed to engage — regardless of
whether `min_daily_runtime` has been met or whether shedding it alone is
projected to close the gap. Engagement is deferred one cycle so the freed
power has a chance to actually register in `battery_power` before the
grid-charge decision is finalised, avoiding a race where grid charge
engages against stale power readings.

### 4. Grid-charge false-positive fix

Prevents the coordinator from double-crediting battery power as "excess"
during an active grid-charge cycle, which upstream can misinterpret as
available solar surplus.

### 5. Deadline-aware shed protection

In `_shed`, appliances with a `schedule_deadline` and a configured
`averaging_window` are judged against their own per-appliance averaged
excess rather than the shared instantaneous budget, as long as the
deadline hasn't passed. Stops a transient instantaneous dip from
shedding an appliance that still has time to ride it out before its
deadline. Falls through to normal instant-based shedding once the
deadline passes or the averaged figure also looks bad.

### 6. Post-deadline battery lock

`_check_post_deadline_battery`: once an appliance's `schedule_deadline`
*and* the battery's target time have both passed, the appliance is
blocked from running unless the battery has met its target SoC. Stops a
deadline-constrained appliance (e.g. the pool) from draining the battery
during peak tariff once the solar charging window has closed.

---

## Suggested PR description (for upstream contribution)

> ### Add battery-SoC-aware gating for grid-drawing appliances
>
> This PR adds an opt-in `battery_target_gated` flag for appliances that
> pull AC/grid current when activated (e.g. an inverter's built-in "fast
> charge" switch), rather than being wattage-modulated like a normal load.
>
> **Problem:** the real-time PREEMPT and grid-supplement paths are pure
> power-budget checks with no battery SoC awareness. In production, this
> let PREEMPT free wattage by shedding a lower-priority appliance and use
> it to justify enabling a battery fast-charge switch — even though the
> battery was already at 98% SoC and climbing on solar alone, resulting in
> unnecessary grid import into a nearly-full battery.
>
> **Fix:** appliances flagged `battery_target_gated` are now excluded from
> PREEMPT and all three grid-supplement code paths once
> `battery_soc >= plan.battery_target.target_soc`. Default `False`,
> fully backward compatible.
>
> Also includes a minor UI fix: the "cheap window target current" field's
> suggested value no longer defaults to `max_current`, which was making
> every appliance look pre-configured for max-current grid draw.

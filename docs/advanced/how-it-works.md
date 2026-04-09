# How It Works

PV Excess Control uses a two-layer architecture to combine real-time responsiveness with intelligent forward planning.

---

## The Two Layers

### Layer 1: Real-Time Controller (every 30 s)

The **Controller** runs on a short interval and reacts to current conditions:

1. Reads all sensor values from Home Assistant
2. Builds a `PowerState` snapshot (production, grid, battery, load)
3. Reads all appliance states
4. Calls the **Optimizer** with this data
5. Applies the resulting `ControlDecisions` by calling HA services

### Layer 2: Forward-Looking Planner (every 15 min)

The **Planner** runs less frequently and builds a 24-hour schedule:

1. Fetches solar forecast data
2. Fetches tariff windows for the next 24 hours
3. Builds a timeline of expected excess power, slot by slot
4. Allocates battery charging across the timeline
5. Schedules appliances in optimal windows
6. Produces a `Plan` that the Controller consults every cycle

---

## The Optimizer -- Four Phases

Each Controller cycle runs the Optimizer through four phases:

### Phase 1: ASSESS
- Averages excess power over recent history to smooth sensor noise
- Applies **hysteresis**: requires excess > `ON_THRESHOLD` (default 200 W) to turn on, and excess < `OFF_THRESHOLD` (default -50 W) to turn off
- Checks if each appliance is within its min/max runtime constraints
- Checks switch interval (don't switch more often than configured)

### Phase 2: ALLOCATE
- Sorts appliances by priority (1 = highest)
- For each appliance (highest priority first): allocates available excess
- For dynamic current appliances: calculates the optimal current
- Checks the plan for scheduled on/off times and reason codes
- Applies opportunity cost to borderline decisions (factors in feed-in tariff revenue)
- Can activate appliances during cheap tariff windows even without solar excess

### Phase 3: SHED
- If total power draw exceeds available excess, reduces current on dynamic appliances
- If still over-budget, turns off lowest-priority appliances first

### Phase 4: BATTERY DISCHARGE PROTECTION
- If any "big consumer" appliance is running, checks if the battery discharge should be limited
- Issues a `BatteryDischargeAction` to cap the battery output

---

## Plan Influence

The **Plan Influence** setting controls how much the planner's 24-hour schedule affects the optimizer's real-time decisions. Configure it in Settings -> PV Excess Control -> Global Settings.

### None (Pure Reactive)
The optimizer completely ignores the plan. Decisions are based only on current excess power and tariff. Use this if you don't have a forecast provider configured or prefer pure reactive control.

### Light (Default)
When the plan schedules an appliance to be ON in the current time slot, the optimizer **lowers the activation threshold**. Normally an appliance needs `nominal_power + 200W` of excess to turn on. With `light` mode and a plan match, it only needs `nominal_power` (the 200W buffer is removed). The plan never forces an appliance ON without any excess -- it just makes the optimizer more willing.

**Best for:** Most users. Gets the benefit of forecast data (Solcast, tariff schedules) without the risk of unexpected grid consumption.

### Plan Follows (Schedule-Driven)
The optimizer actively follows the plan. If the plan schedules an appliance ON based on forecast or cheap tariff windows, it activates even without full solar excess. The optimizer overrides only when actual conditions deviate significantly from the forecast.

**Best for:** Users with reliable forecast data (Solcast with good accuracy) and tariff providers, who want maximum automation.

---

## The Pure-Logic Principle

The **Optimizer** is completely decoupled from Home Assistant:

```
PowerState + ApplianceConfigs + ApplianceStates + Plan + TariffInfo
    |
Optimizer
    |
OptimizerResult (list of ControlDecisions)
```

This means:
- The optimizer can be unit-tested without any HA mocking
- The same optimizer logic runs in tests and production
- Logic bugs are caught at the unit test level, not during runtime

---

## Data Flow Summary

```
HA Sensors
    |
    v
Controller.build_power_state()
    |
    |--> Optimizer.optimize()
    |         |
    |         |-- Phase 1: ASSESS
    |         |-- Phase 2: ALLOCATE
    |         |-- Phase 3: SHED
    |         |-- Phase 4: BATTERY PROTECTION
    |              |
    |              v
    |         OptimizerResult
    |
    |--> Controller.apply_decisions()
              |
              v
         HA Services (switch, number)
```

---

## Plan vs. Real-Time

The Controller always runs real-time control. The Plan is a *guide*, not a hard constraint. If real conditions deviate from the plan:

- Real excess < planned: the Controller sheds appliances immediately
- Real excess > planned: the Controller allocates extra power by priority
- Sensor unavailable: the Controller uses safe defaults (all appliances off)

Plan entries with reason `MANUAL_OVERRIDE` always win over real-time decisions.

---

## Coordinator

A `DataUpdateCoordinator` manages both the Controller and Planner intervals, entity updates, and integration lifecycle (setup, unload, options changes).

---

## Reading the status sensor

Every configured appliance has a `sensor.pv_excess_control_<appliance>_status`
entity. Its state is a short human-readable sentence explaining the
optimizer's most recent decision for that appliance. When the situation
warrants it, the sentence is followed by one or more suffix decorations.

### Anatomy of a status string

```
<base reason> [ (switch deferred - Ns cooldown) ] [ [battery discharge limited to NW] ] [ [plan wanted: ...] ]
```

- **Base reason** — what the optimizer decided and why, e.g.
  `Excess available (2100W >= 1800W needed)` or
  `Staying on at 10.0A (6900W drawn) - shed at -100W (current: +720W)`.
- **Cooldown suffix** — appears when the optimizer wanted to switch the
  appliance on/off but the configured switch interval has not yet
  elapsed. The appliance will switch automatically once the cooldown
  finishes (unless the decision changes before then). Safety-OFF
  decisions (max daily runtime, time window, EV-disconnect, EV SoC
  target, battery SoC protection) bypass the cooldown and never show
  this suffix.
- **Battery discharge suffix** — appears when battery SoC protection
  is currently limiting the configured big-consumer discharge rate.
  The base reason is not a battery protection message in this case;
  the suffix is added so you can see why headroom is reduced.
- **Plan deviation suffix** — appears when the optimizer made a
  different decision than the planner scheduled for this time window,
  e.g. because a deadline must-run forced the appliance on.
- **"Startup grace period"** — replaces the entire string for the
  first 2 minutes after a reload. The optimizer does not make
  decisions during this window; the sensor shows the remaining time.
- **"(shed imminent)"** — appears on the end of the `Staying on`
  reason when the current remaining excess has crossed the shed
  threshold. SHED will normally take over on the next cycle.

### Using the attributes

For Lovelace cards and automations, prefer reading the sensor's
attributes rather than parsing the state string. See
`docs/dashboard/custom-dashboards.md` for the full attribute reference
and examples.

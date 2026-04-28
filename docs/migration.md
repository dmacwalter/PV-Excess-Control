# Migration from Blueprint

This guide maps the original PV Excess Control blueprint inputs to the new integration's configuration flow fields.

---

## Why Migrate?

The original PV Excess Control was a Home Assistant blueprint — an automation template configured via a single YAML form. The new integration:

- Has a proper UI config flow (no YAML required)
- Supports multiple appliances as sub-entries
- Provides analytics and long-term statistics
- Supports forward planning and tariff optimization
- Has configurable thresholds, time windows, and per-appliance tuning

---

## Field Mapping

### Inverter Setup

| Blueprint Input | New Integration Field | Location |
|-----------------|----------------------|----------|
| _(not in blueprint)_ | Inverter Type | Inverter Setup step |
| _(not in blueprint)_ | Grid Voltage (V) | Inverter Setup step |

The blueprint assumed a standard inverter. The new integration asks you to specify **Standard** or **Hybrid** (battery-connected) to optimize excess power calculation.

### Core Power Sensors

| Blueprint Input | New Integration Field | Location |
|-----------------|----------------------|----------|
| `pv_power_sensor` | PV Production Power Sensor | Sensor Mapping step |
| `grid_export_sensor` | Grid Export Power Sensor | Sensor Mapping step |
| _(not in blueprint)_ | Combined Import/Export Power Sensor | Sensor Mapping step |
| `load_power_sensor` | Load Power Sensor | Sensor Mapping step |
| `battery_soc_sensor` | Battery State of Charge Sensor | Sensor Mapping step |
| _(not in blueprint)_ | Combined Battery Power Sensor | Sensor Mapping step |
| _(not in blueprint)_ | Battery Charge Power Sensor | Sensor Mapping step |
| _(not in blueprint)_ | Battery Discharge Power Sensor | Sensor Mapping step |
| _(not in blueprint)_ | Battery Capacity (kWh) | Sensor Mapping step |

> **Note:** All power sensors accept both W and kW — the integration reads the sensor's `unit_of_measurement` and converts automatically.

### Appliance Settings (per appliance)

The blueprint controlled a single appliance. In the new integration, each appliance is a separate sub-entry with three configuration steps: Basic, Dynamic Current, and Constraints.

#### Basic Settings

| Blueprint Input | New Appliance Field | Notes |
|-----------------|---------------------|-------|
| `appliance_switch` | Appliance Entity | |
| `appliance_power` | Nominal Power (W) | |
| `appliance_priority` | Priority (1-1000) | Same scale: 1 = highest priority |
| _(not in blueprint)_ | Appliance Name | Friendly name for the appliance |
| _(not in blueprint)_ | Actual Power Sensor | Optional real-time power tracking (W or kW) |
| _(not in blueprint)_ | Number of Phases | Used for amps-to-watts conversion |

#### Dynamic Current (EV Chargers)

| Blueprint Input | New Appliance Field | Notes |
|-----------------|---------------------|-------|
| `ev_charger_mode` | Dynamic Current | Enable for variable-amp control |
| `min_charge_current` | Min Current (A) | |
| `max_charge_current` | Max Current (A) | |
| _(not in blueprint)_ | Current Step Size (A) | Resolution of amp adjustments (default 0.1 A) |
| `ev_soc_sensor` | EV SoC Sensor | |
| `ev_connected_sensor` | EV Connected Sensor | |
| _(not in blueprint)_ | EV Target SoC | Stop charging at this SoC % |

#### Constraints & Grid Settings

| Blueprint Input | New Appliance Field | Notes |
|-----------------|---------------------|-------|
| `turn_off_delay` | Switch Interval (s) | Renamed, in seconds (default 300 s) |
| `on_only_mode` | On Only | |
| `min_daily_runtime` | Min Daily Runtime (min) | Now in minutes |
| `required_by_time` | Schedule Deadline | |
| _(not in blueprint)_ | Max Daily Runtime (min) | Hard stop after this many minutes |
| _(not in blueprint)_ | Max Daily Activations | Limit on/off cycles per day |
| _(not in blueprint)_ | Activation Buffer (W) | Per-appliance ON threshold (default 200 W standard, 50 W dynamic) |
| _(not in blueprint)_ | Start After | Earliest time of day to operate |
| _(not in blueprint)_ | End Before | Latest time of day to operate |
| _(not in blueprint)_ | Averaging Window (s) | Per-appliance excess smoothing window |
| _(not in blueprint)_ | Allow Grid Supplement | Use cheap grid power to supplement |
| _(not in blueprint)_ | Max Grid Power (W) | Limit on grid draw during supplementation |
| _(not in blueprint)_ | Cheap Price Threshold | Per-appliance price threshold (falls back to global) |
| _(not in blueprint)_ | Big Consumer | Enable battery discharge protection |
| _(not in blueprint)_ | Battery Discharge Override (W) | Max discharge when this appliance is active |
| _(not in blueprint)_ | Protect From Preemption | Prevent shedding by higher-priority appliances |
| _(not in blueprint)_ | Requires Appliance | Dependency — another appliance must be running first |
| _(not in blueprint)_ | Run Only as Helper | Only runs when a dependent appliance needs it |

### Global Settings

| Blueprint Input | New Integration Field | Notes |
|-----------------|-----------------------|-------|
| `update_interval` | Controller Update Interval | Renamed (default 30 s) |
| `excess_threshold` | _(removed)_ | Replaced by per-appliance Activation Buffer |
| `off_threshold` | Shed Threshold (W) | Now configurable in Global Settings (default -50 W) |
| _(not in blueprint)_ | Planner Update Interval | How often the planner recalculates (default 900 s) |
| _(not in blueprint)_ | Export Limit (W) | For feed-in capped systems |
| _(not in blueprint)_ | Plan Influence Mode | None / Light / Plan Follows |
| _(not in blueprint)_ | Enable Priority Preemption | Shed lower-priority to start higher-priority |
| _(not in blueprint)_ | Notification Service | HA notification target |

---

## Settings Not in the Blueprint (New Features)

These features did not exist in the blueprint and are new to the integration:

- **Tariff integration** (Tibber, Nordpool, Awattar, Octopus, generic) — see [Energy Pricing](configuration/energy-pricing.md)
- **Solar forecast** (Solcast, Forecast.Solar, generic) — see [Solar Forecast](configuration/solar-forecast.md)
- **Battery strategy** (Battery First / Appliance First / Balanced) with target SoC, target time, and grid charging control
- **Minimum Battery SoC** — sheds all non-essential appliances and blocks discharge when SoC drops below threshold
- **Export limit** — for feed-in capped systems
- **Plan influence** — 24-hour planner that uses forecast and tariff data to schedule appliances (None / Light / Plan Follows)
- **Priority preemption** — shed lower-priority appliances to start higher-priority ones when excess is insufficient
- **Grid supplementation** — per-appliance option to use cheap grid power, with configurable price threshold and max grid draw
- **Time windows** — per-appliance Start After / End Before constraints
- **Appliance dependencies** — chain appliances so one requires another to be running first
- **Helper-only mode** — appliance only runs when a dependent needs it (e.g., circulation pump for heat pump)
- **Big consumer protection** — limit battery discharge when high-power appliances are active
- **Per-appliance tuning** — activation buffer (ON threshold), averaging window, cheap price threshold
- **Max daily activations** — limit on/off cycles for sensitive equipment
- **Configurable shed threshold** — adjust the global OFF threshold (default -50 W)
- **Weather pre-planning** — automatic, no configuration required
- **Analytics** — automatic tracking, visible in device page
- **Dashboard examples** — see [Dashboard Examples](dashboard-examples.md)

---

## Step-by-Step Migration

### 1. Install the Integration

Follow [Installation](installation.md). Do not remove the blueprint automation yet.

### 2. Run the Setup Wizard

Go to Settings → Devices & Services → Add Integration → PV Excess Control.

The setup wizard has six steps:
1. **Inverter Setup** — inverter type and grid voltage
2. **Sensor Mapping** — map your power and battery sensors
3. **Energy Pricing** — tariff provider and price thresholds
4. **Solar Forecast** — forecast provider for planning
5. **Battery Strategy** — charging strategy and protection settings
6. **Global Settings** — intervals, thresholds, preemption, notifications

Map the same sensors you had in the blueprint inputs.

### 3. Add Each Appliance

For each appliance controlled by the blueprint (or by separate blueprint instances), add a sub-entry with the mapped fields above.

### 4. Test in Parallel

Run both the blueprint automations and the new integration for a few days. Compare switching behaviour. The new integration should make equivalent decisions.

### 5. Disable Blueprint Automations

Once satisfied, disable the blueprint automations in Settings → Automations.

### 6. Remove Blueprint (Optional)

If you had multiple blueprint instances, remove them from Settings → Automations after verifying the integration controls all appliances.

---

## Common Migration Issues

**Integration turns appliances on/off at different times than blueprint**
The new integration uses a configurable poll cycle (default 30 s) and hysteresis. The default activation buffer is 200 W (50 W for dynamic current appliances) and the default shed threshold is -50 W. Both are configurable: the activation buffer per-appliance in the Constraints step, and the shed threshold in Global Settings. The blueprint may have used different trigger conditions.

**Multiple blueprint instances for different appliances**
Each blueprint instance becomes one appliance sub-entry. The integration handles all appliances in a single coordinated optimizer, so priorities now interact — set priorities carefully.

**Blueprint had per-appliance excess thresholds**
The new integration supports per-appliance **Activation Buffer** (ON threshold) in each appliance's Constraints step. Set this to match the excess threshold you had in the blueprint. Additionally, you can set a per-appliance **Averaging Window** to control how quickly the appliance reacts to excess changes.

**Combined Import/Export sensor sign convention flipped**
The original blueprint documented the combined Import/Export sensor as *positive = import, negative = export* (matching how utility meters typically display grid power). The new integration uses the opposite convention: **positive = export, negative = import**. This keeps the sign of the combined sensor consistent with how the integration reasons about excess internally (positive number means surplus). If you reuse the same sensor and the excess calculations look inverted, either create a template sensor that negates the value, or switch to the separate **Grid Export Power** field instead (which only takes positive export watts).

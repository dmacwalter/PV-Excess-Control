# Migration from Blueprint

This guide maps the original PV Excess Control blueprint inputs to the new integration's configuration flow fields.

---

## Why Migrate?

The original PV Excess Control was a Home Assistant blueprint — an automation template configured via a single YAML form. The new integration:

- Has a proper UI config flow (no YAML required)
- Supports multiple appliances as sub-entries
- Has a dedicated dashboard card
- Provides analytics and long-term statistics
- Supports forward planning and tariff optimization

---

## Field Mapping

### Core Power Sensors

| Blueprint Input | New Integration Field | Location |
|-----------------|----------------------|----------|
| `pv_power_sensor` | PV Power | Sensor Mapping step |
| `grid_export_sensor` | Grid Export Power | Sensor Mapping step |
| `load_power_sensor` | Load Power | Sensor Mapping step |
| `battery_soc_sensor` | Battery SoC | Sensor Mapping step |

### Appliance Settings (per appliance in blueprint)

The blueprint controlled a single appliance. In the new integration, each appliance is a separate sub-entry.

| Blueprint Input | New Appliance Field | Notes |
|-----------------|---------------------|-------|
| `appliance_switch` | Switch Entity | |
| `appliance_power` | Nominal Power | |
| `appliance_priority` | Priority | Same 1-1000 scale |
| `min_excess_for_on` | — | Now handled by global ON threshold (200 W default) |
| `turn_off_delay` | Switch Interval | Renamed, in seconds |
| `on_only_mode` | On Only | |
| `min_daily_runtime` | Min Daily Runtime | Now in minutes |
| `required_by_time` | Schedule Deadline | |

### EV Charger Settings

| Blueprint Input | New Appliance Field | Notes |
|-----------------|---------------------|-------|
| `ev_charger_mode` | Dynamic Current | Enable to use variable amps |
| `min_charge_current` | Min Current | |
| `max_charge_current` | Max Current | |
| `ev_soc_sensor` | EV SoC Sensor | |
| `ev_connected_sensor` | EV Connected Sensor | |

### Global Settings

| Blueprint Input | New Integration Field | Notes |
|-----------------|-----------------------|-------|
| `update_interval` | Controller Interval | Renamed |
| `excess_threshold` | ON Threshold | Hardcoded default: 200 W (not user-configurable) |
| `off_threshold` | OFF Threshold | Hardcoded default: -50 W (not user-configurable) |

---

## Settings Not in the Blueprint (New Features)

These features did not exist in the blueprint and are new to the integration:

- **Tariff integration** (Tibber, Nordpool, Awattar, Octopus, generic) — see [Energy Pricing](configuration/energy-pricing.md)
- **Solar forecast** (Solcast, Forecast.Solar) — see [Solar Forecast](configuration/solar-forecast.md)
- **Battery strategy** (Battery First / Appliance First / Balanced)
- **Export limit** — for feed-in capped systems
- **Weather pre-planning** — automatic, no configuration required
- **Analytics** — automatic tracking, visible in device page

---

## Step-by-Step Migration

### 1. Install the Integration

Follow [Installation](installation.md). Do not remove the blueprint automation yet.

### 2. Run the Setup Wizard

Go to Settings → Devices & Services → Add Integration → PV Excess Control.

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
The new integration uses a 30-second poll cycle and hysteresis (ON threshold: 200 W, OFF threshold: -50 W). The blueprint may have used different trigger conditions. These thresholds are hardcoded defaults and cannot be changed via the UI.

**Multiple blueprint instances for different appliances**
Each blueprint instance becomes one appliance sub-entry. The integration handles all appliances in a single coordinated optimizer, so priorities now interact — set priorities carefully.

**Blueprint had per-appliance excess thresholds**
The new integration uses a global ON threshold with per-appliance priority to differentiate. An appliance with a high minimum excess in the blueprint should get a higher priority number (lower priority) so it only activates when there is substantial excess.

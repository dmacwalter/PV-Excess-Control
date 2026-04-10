# Entity Reference

This page documents all entities exposed by PV Excess Control and their attributes. Use this as a reference when building your dashboard. For complete, ready-to-use YAML examples, see the [Dashboard Examples](../dashboard-examples.md).

---

## Key Entities

### System-Level Entities

| Entity | Description |
|--------|-------------|
| `sensor.pv_excess_control_excess_power` | Current excess power (W) |
| `sensor.pv_excess_control_plan_confidence` | Plan confidence score |
| `binary_sensor.pv_excess_control_excess_available` | Whether excess power is available |
| `switch.pv_excess_control_control_enabled` | Master on/off for the integration |
| `switch.pv_excess_control_force_charge` | Force battery grid charging |
| `select.pv_excess_control_battery_strategy` | Battery strategy selector |

### Per-Appliance Entities

For an appliance named "Water Heater" (slug: `water_heater`):

| Entity | Description |
|--------|-------------|
| `sensor.pv_excess_control_water_heater_power` | Current power draw (W) |
| `sensor.pv_excess_control_water_heater_runtime_today` | Runtime today |
| `sensor.pv_excess_control_water_heater_energy_today` | Energy consumed today (kWh) |
| `sensor.pv_excess_control_water_heater_activations_today` | Number of times turned on today |
| `sensor.pv_excess_control_water_heater_status` | Current appliance status |
| `switch.pv_excess_control_water_heater_enabled` | Enable/disable this appliance |
| `switch.pv_excess_control_water_heater_override` | Manual override toggle |
| `binary_sensor.pv_excess_control_water_heater_active` | Whether the appliance is currently running |
| `number.pv_excess_control_water_heater_priority` | Priority setting (1-1000) |

---

## Example: Power Flow Gauge

```yaml
type: gauge
entity: sensor.pv_excess_control_excess_power
name: Available Excess
unit: W
min: -3000
max: 10000
segments:
  - from: -3000
    color: red
  - from: 0
    color: yellow
  - from: 500
    color: green
```

---

## Example: Appliance Status Grid

```yaml
type: grid
columns: 2
cards:
  - type: entities
    title: Water Heater
    entities:
      - entity: switch.pv_excess_control_water_heater_enabled
      - entity: sensor.pv_excess_control_water_heater_power
        name: Current Power
      - entity: sensor.pv_excess_control_water_heater_runtime_today
        name: Runtime Today
      - entity: switch.pv_excess_control_water_heater_override
        name: Manual Override

  - type: entities
    title: Heat Pump
    entities:
      - entity: switch.pv_excess_control_heat_pump_enabled
      - entity: sensor.pv_excess_control_heat_pump_power
        name: Current Power
      - entity: sensor.pv_excess_control_heat_pump_runtime_today
        name: Runtime Today
      - entity: switch.pv_excess_control_heat_pump_override
        name: Manual Override
```

---

## Status sensor attributes

The `sensor.pv_excess_control_<appliance>_status` entity exposes a set of
structured attributes that make it easy to build richer Lovelace cards
without parsing the state string. The state string is meant to be a
human-readable summary; the attributes give you machine-readable values.

| Attribute | Type | Meaning |
|---|---|---|
| `action` | string | Machine-readable decision: `on`, `off`, `set_current`, or `idle`. |
| `overrides_plan` | bool | `true` when the current decision deviates from the planner's schedule. |
| `cooldown_seconds_remaining` | int or `null` | Seconds until the next switch is allowed. `null` when no cooldown applies. |
| `switch_deferred` | bool | `true` when the switch interval prevented applying a state change this cycle. |
| `headroom_watts` | float or `null` | Watts of headroom before SHED, for already-running appliances. `null` otherwise. |
| `plan_action` | string or `null` | Planner's scheduled action for the current time window. `null` if no plan or no matching entry. |
| `plan_window_start` | ISO datetime or `null` | Start of the matching planner window. |
| `plan_window_end` | ISO datetime or `null` | End of the matching planner window. |

### Example: cooldown countdown badge

```yaml
type: custom:mushroom-template-card
primary: "{{ state_attr('sensor.pv_excess_control_water_heater_status', 'switch_deferred') }}"
secondary: >-
  {% set s = state_attr('sensor.pv_excess_control_water_heater_status', 'cooldown_seconds_remaining') %}
  {% if s %}Next switch allowed in {{ s }}s{% else %}Ready{% endif %}
icon: mdi:timer-sand
```

### Example: plan deviation indicator

```yaml
type: conditional
conditions:
  - entity: sensor.pv_excess_control_water_heater_status
    attribute: overrides_plan
    state: true
card:
  type: markdown
  content: >-
    Overriding plan. Plan wanted
    **{{ state_attr('sensor.pv_excess_control_water_heater_status', 'plan_action') | upper }}**
    during
    {{ state_attr('sensor.pv_excess_control_water_heater_status', 'plan_window_start')[11:16] }}
    –
    {{ state_attr('sensor.pv_excess_control_water_heater_status', 'plan_window_end')[11:16] }}
```

### Example: headroom gauge

```yaml
type: gauge
entity: sensor.pv_excess_control_water_heater_status
attribute: headroom_watts
name: Shed headroom
unit: W
min: 0
max: 2000
severity:
  green: 500
  yellow: 200
  red: 0
```

---

## Example: System Status Overview

```yaml
type: entities
title: PV Excess Control
entities:
  - entity: sensor.pv_excess_control_excess_power
    name: Excess Power
  - entity: binary_sensor.pv_excess_control_excess_available
    name: Excess Available
  - entity: switch.pv_excess_control_control_enabled
    name: Control Enabled
  - entity: select.pv_excess_control_battery_strategy
    name: Battery Strategy
  - entity: sensor.pv_excess_control_plan_confidence
    name: Plan Confidence
```

---

## Example: Appliance Activity History

Using the History Graph card:

```yaml
type: history-graph
title: Appliance Activity
entities:
  - entity: binary_sensor.pv_excess_control_water_heater_active
    name: Water Heater
  - entity: binary_sensor.pv_excess_control_heat_pump_active
    name: Heat Pump
hours_to_show: 24
```

---

## Integration with Energy Dashboard

Add the integration's energy sensors to the Home Assistant Energy Dashboard for long-term tracking:

1. Settings -> Dashboards -> Energy -> Configure
2. Under **Individual Devices**, add:
   - `sensor.pv_excess_control_water_heater_energy_today`
   - `sensor.pv_excess_control_heat_pump_energy_today`
   - (etc. for each appliance)
3. Under **Solar Panels**, ensure your PV power sensor is already listed

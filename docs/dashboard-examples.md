# Dashboard Examples

PV Excess Control does not ship with a built-in dashboard card. Instead, you build your own using popular community cards — giving you full control over layout, styling and functionality.

This page provides ready-to-use YAML examples for a complete solar excess dashboard. Each section is independent — copy what you need and adapt the entity IDs to your setup.

> **All examples use a fictional 3-appliance setup:** EV Charger, Heat Pump, and Dishwasher. Replace the entity IDs with your own. Lines marked `# <- CHANGE` need your entity IDs.

---

## 1. Prerequisites

Install the following community cards via **HACS → Frontend** before using these examples.

| Card | HACS Frontend Name | GitHub |
|------|--------------------|--------|
| Mushroom Cards | `mushroom` | [piitaya/lovelace-mushroom](https://github.com/piitaya/lovelace-mushroom) |
| ApexCharts Card | `apexcharts-card` | [RomRider/apexcharts-card](https://github.com/RomRider/apexcharts-card) |
| Mini Graph Card | `mini-graph-card` | [kalkih/mini-graph-card](https://github.com/kalkih/mini-graph-card) |
| Power Flow Card Plus | `power-flow-card-plus` | [flixlix/power-flow-card-plus](https://github.com/flixlix/power-flow-card-plus) |

After installing each card, **reload your browser** (Ctrl+Shift+R / Cmd+Shift+R) for the cards to be recognized.

---

## 2. System Overview

### Master Controls (Mushroom Chips Row)

A chips row giving quick access to the master controls and a live excess indicator.

```yaml
type: custom:mushroom-chips-card
chips:
  # Master enable/disable
  - type: entity
    entity: switch.pv_excess_control_control_enabled
    icon_color: green
  # Force battery charge
  - type: entity
    entity: switch.pv_excess_control_force_charge
    icon_color: amber
  # Battery strategy selector
  - type: entity
    entity: select.pv_excess_control_battery_strategy
  # Conditional chip — only visible when excess power is available
  - type: conditional
    conditions:
      - entity: binary_sensor.pv_excess_control_excess_available
        state: "on"
    chip:
      type: template
      icon: mdi:solar-power
      icon_color: green
      content: >-
        {{ states('sensor.pv_excess_control_excess_power') | int }} W excess
```

### Excess Power Gauge

Color-coded gauge showing current excess power: red when negative (importing), yellow for low surplus, green for healthy surplus.

```yaml
type: gauge
entity: sensor.pv_excess_control_excess_power
name: PV Excess Power
unit: W
min: -3000
max: 10000
needle: true
segments:
  - from: -3000
    color: "var(--error-color)"
  - from: 0
    color: "var(--warning-color)"
  - from: 500
    color: "var(--success-color)"
```

---

## 3. Power Flow

### Option A: Power Flow Card Plus

Full animated power flow diagram. Replace the sensor entity IDs with your inverter's sensors.

```yaml
type: custom:power-flow-card-plus
entities:
  grid:
    entity: sensor.fronius_grid_export    # <- CHANGE
    secondary_info:
      entity: sensor.fronius_grid_import  # <- CHANGE
  solar:
    entity: sensor.fronius_pv_power       # <- CHANGE
  battery:
    entity: sensor.fronius_battery_power  # <- CHANGE
    state_of_charge: sensor.fronius_battery_soc  # <- CHANGE
  home:
    entity: sensor.fronius_load_power     # <- CHANGE
  individual:
    - entity: sensor.pv_excess_control_ev_charger_power
      name: EV Charger
      icon: mdi:ev-station
    - entity: sensor.pv_excess_control_heat_pump_power
      name: Heat Pump
      icon: mdi:heat-pump
    - entity: sensor.pv_excess_control_dishwasher_power
      name: Dishwasher
      icon: mdi:dishwasher
kw_decimals: 1
min_flow_rate: 0.75
max_flow_rate: 6
```

### Option B: Simple Mushroom Horizontal Stack

A lightweight alternative for setups without battery, or when you prefer a minimal layout.

```yaml
type: horizontal-stack
cards:
  - type: custom:mushroom-template-card
    primary: Solar
    secondary: "{{ states('sensor.fronius_pv_power') | int }} W"  # <- CHANGE
    icon: mdi:solar-power-variant
    icon_color: >-
      {% if states('sensor.fronius_pv_power') | int > 100 %}amber{% else %}disabled{% endif %}
  - type: custom:mushroom-template-card
    primary: Excess
    secondary: "{{ states('sensor.pv_excess_control_excess_power') | int }} W"
    icon: mdi:transmission-tower-export
    icon_color: >-
      {% set v = states('sensor.pv_excess_control_excess_power') | int %}
      {% if v > 500 %}green{% elif v > 0 %}amber{% else %}red{% endif %}
  - type: custom:mushroom-template-card
    primary: Battery
    secondary: "{{ states('sensor.fronius_battery_soc') | int }}%"  # <- CHANGE
    icon: mdi:battery
    icon_color: >-
      {% set s = states('sensor.fronius_battery_soc') | int %}
      {% if s > 70 %}green{% elif s > 30 %}amber{% else %}red{% endif %}
  - type: custom:mushroom-template-card
    primary: Grid
    secondary: "{{ states('sensor.fronius_grid_import') | int }} W"  # <- CHANGE
    icon: mdi:transmission-tower-import
    icon_color: >-
      {% if states('sensor.fronius_grid_import') | int > 100 %}red{% else %}disabled{% endif %}
```

---

## 4. Appliance Control Cards

### EV Charger

Dynamic current appliance with cooldown timer badge and plan override indicator.

```yaml
type: vertical-stack
cards:
  # Main card
  - type: custom:mushroom-template-card
    primary: EV Charger
    secondary: "{{ states('sensor.pv_excess_control_ev_charger_status') }}"
    icon: mdi:ev-station
    icon_color: >-
      {% if is_state('binary_sensor.pv_excess_control_ev_charger_active', 'on') %}
        cyan
      {% else %}
        disabled
      {% endif %}
    badge_icon: >-
      {% if state_attr('sensor.pv_excess_control_ev_charger_status', 'overrides_plan') %}
        mdi:calendar-alert
      {% endif %}
    badge_color: amber
    tap_action:
      action: more-info
      entity: sensor.pv_excess_control_ev_charger_status
  # Runtime / Power / Energy grid
  - type: grid
    columns: 3
    square: false
    cards:
      - type: custom:mushroom-template-card
        primary: Power
        secondary: "{{ states('sensor.pv_excess_control_ev_charger_power') | int }} W"
        icon: mdi:lightning-bolt
        icon_color: cyan
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Runtime
        secondary: >-
          {% set h = states('sensor.pv_excess_control_ev_charger_runtime_today') | float %}
          {% set hh = h | int %}
          {% set mm = ((h - hh) * 60) | int %}
          {{ hh }}h {{ mm }}m
        icon: mdi:clock-outline
        icon_color: teal
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Energy
        secondary: "{{ states('sensor.pv_excess_control_ev_charger_energy_today') | float | round(2) }} kWh"
        icon: mdi:flash
        icon_color: teal
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
  # Controls row
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: switch.pv_excess_control_ev_charger_enabled
        icon_color: green
      - type: entity
        entity: switch.pv_excess_control_ev_charger_override
        icon_color: amber
      - type: conditional
        conditions:
          - entity: sensor.pv_excess_control_ev_charger_status
            attribute: cooldown_seconds_remaining
            state_not: null
        chip:
          type: template
          icon: mdi:timer-sand
          icon_color: orange
          content: >-
            {% set s = state_attr('sensor.pv_excess_control_ev_charger_status', 'cooldown_seconds_remaining') %}
            {% if s %}{{ s }}s{% else %}Ready{% endif %}
```

### Heat Pump

Standard on/off appliance with deep-orange active color.

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: Heat Pump
    secondary: "{{ states('sensor.pv_excess_control_heat_pump_status') }}"
    icon: mdi:heat-pump
    icon_color: >-
      {% if is_state('binary_sensor.pv_excess_control_heat_pump_active', 'on') %}
        deep-orange
      {% else %}
        disabled
      {% endif %}
    badge_icon: >-
      {% if state_attr('sensor.pv_excess_control_heat_pump_status', 'overrides_plan') %}
        mdi:calendar-alert
      {% endif %}
    badge_color: amber
    tap_action:
      action: more-info
      entity: sensor.pv_excess_control_heat_pump_status
  - type: grid
    columns: 3
    square: false
    cards:
      - type: custom:mushroom-template-card
        primary: Power
        secondary: "{{ states('sensor.pv_excess_control_heat_pump_power') | int }} W"
        icon: mdi:lightning-bolt
        icon_color: deep-orange
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Runtime
        secondary: >-
          {% set h = states('sensor.pv_excess_control_heat_pump_runtime_today') | float %}
          {% set hh = h | int %}
          {% set mm = ((h - hh) * 60) | int %}
          {{ hh }}h {{ mm }}m
        icon: mdi:clock-outline
        icon_color: orange
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Energy
        secondary: "{{ states('sensor.pv_excess_control_heat_pump_energy_today') | float | round(2) }} kWh"
        icon: mdi:flash
        icon_color: orange
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: switch.pv_excess_control_heat_pump_enabled
        icon_color: green
      - type: entity
        entity: switch.pv_excess_control_heat_pump_override
        icon_color: amber
      - type: conditional
        conditions:
          - entity: sensor.pv_excess_control_heat_pump_status
            attribute: cooldown_seconds_remaining
            state_not: null
        chip:
          type: template
          icon: mdi:timer-sand
          icon_color: orange
          content: >-
            {% set s = state_attr('sensor.pv_excess_control_heat_pump_status', 'cooldown_seconds_remaining') %}
            {% if s %}{{ s }}s{% else %}Ready{% endif %}
```

### Dishwasher

Simple on/off appliance. Cooldown chip is omitted here since dishwashers typically finish a full cycle and rarely benefit from mid-cycle monitoring. Add it back if you have a long `switch_interval`.

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-template-card
    primary: Dishwasher
    secondary: "{{ states('sensor.pv_excess_control_dishwasher_status') }}"
    icon: mdi:dishwasher
    icon_color: >-
      {% if is_state('binary_sensor.pv_excess_control_dishwasher_active', 'on') %}
        blue
      {% else %}
        disabled
      {% endif %}
    badge_icon: >-
      {% if state_attr('sensor.pv_excess_control_dishwasher_status', 'overrides_plan') %}
        mdi:calendar-alert
      {% endif %}
    badge_color: amber
    tap_action:
      action: more-info
      entity: sensor.pv_excess_control_dishwasher_status
  - type: grid
    columns: 3
    square: false
    cards:
      - type: custom:mushroom-template-card
        primary: Power
        secondary: "{{ states('sensor.pv_excess_control_dishwasher_power') | int }} W"
        icon: mdi:lightning-bolt
        icon_color: blue
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Runtime
        secondary: >-
          {% set h = states('sensor.pv_excess_control_dishwasher_runtime_today') | float %}
          {% set hh = h | int %}
          {% set mm = ((h - hh) * 60) | int %}
          {{ hh }}h {{ mm }}m
        icon: mdi:clock-outline
        icon_color: blue
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
      - type: custom:mushroom-template-card
        primary: Energy
        secondary: "{{ states('sensor.pv_excess_control_dishwasher_energy_today') | float | round(2) }} kWh"
        icon: mdi:flash
        icon_color: blue
        card_mod:
          style: |
            ha-card { --ha-card-border-width: 0; }
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: switch.pv_excess_control_dishwasher_enabled
        icon_color: green
      - type: entity
        entity: switch.pv_excess_control_dishwasher_override
        icon_color: amber
```

---

## 5. Solar Forecast Chart

Requires the [Solcast integration](https://github.com/BJReplay/ha-solcast-solar) installed and configured. The `data_generator` reads the `detailedForecast` attribute directly.

> **Adapter note:** If you use Forecast.Solar or another provider, adjust the sensor entity and attribute name in `data_generator`. Forecast.Solar typically exposes `watts` under a similar structure — check the attribute in Developer Tools → States.

```yaml
type: custom:apexcharts-card
header:
  title: Solar Forecast
  show: true
  show_states: true
  colorize_states: true
graph_span: 2d
span:
  start: day
series:
  # Today's forecast — filled area
  - entity: sensor.solcast_pv_forecast_forecast_today    # <- CHANGE
    name: Today
    color: "var(--warning-color)"
    type: area
    curve: smooth
    opacity: 0.3
    unit: W
    data_generator: |
      const attr = entity.attributes.detailedForecast
        || entity.attributes.forecasts
        || entity.attributes.detailedHourly;
      if (!attr) return [];
      return attr.map(item => [
        new Date(item.period_start || item.datetime).getTime(),
        Math.round((item.pv_estimate || item.watts || 0) * 1000)
      ]);
  # Tomorrow's forecast — line only
  - entity: sensor.solcast_pv_forecast_forecast_tomorrow  # <- CHANGE
    name: Tomorrow
    color: "var(--info-color)"
    type: line
    curve: smooth
    opacity: 0.8
    unit: W
    data_generator: |
      const attr = entity.attributes.detailedForecast
        || entity.attributes.forecasts
        || entity.attributes.detailedHourly;
      if (!attr) return [];
      return attr.map(item => [
        new Date(item.period_start || item.datetime).getTime(),
        Math.round((item.pv_estimate || item.watts || 0) * 1000)
      ]);
yaxis:
  - min: 0
    apex_config:
      forceNiceScale: true
apex_config:
  chart:
    height: 200
  xaxis:
    type: datetime
    labels:
      datetimeUTC: false
```

---

## 6. Plan Timeline

Visualizes the planner's scheduled actions as range bars. Plan entries are read from the `plan_entries` attribute on `sensor.pv_excess_control_plan_confidence`.

> **Note:** This is a simplified visualization. ApexCharts range bars require a start/end pair; entries without a `window_start`/`window_end` (e.g. reason-only entries) are skipped by the `data_generator`. Plan confidence is shown in the card header.

```yaml
type: custom:apexcharts-card
header:
  title: >-
    Plan Timeline — confidence:
    {{ states('sensor.pv_excess_control_plan_confidence') }}%
  show: true
graph_span: 24h
span:
  start: day
series:
  - entity: sensor.pv_excess_control_plan_confidence
    name: EV Charger
    type: rangeBar
    color: cyan
    data_generator: |
      const entries = entity.attributes.plan_entries || [];
      return entries
        .filter(e =>
          e.appliance_id === 'ev_charger' &&
          e.window_start && e.window_end &&
          (e.action === 'on' || e.action === 'set_current')
        )
        .map(e => ({
          x: e.appliance_id,
          y: [
            new Date(e.window_start).getTime(),
            new Date(e.window_end).getTime()
          ],
          meta: e.reason
        }));
  - entity: sensor.pv_excess_control_plan_confidence
    name: Heat Pump
    type: rangeBar
    color: deep-orange
    data_generator: |
      const entries = entity.attributes.plan_entries || [];
      return entries
        .filter(e =>
          e.appliance_id === 'heat_pump' &&
          e.window_start && e.window_end &&
          (e.action === 'on' || e.action === 'set_current')
        )
        .map(e => ({
          x: e.appliance_id,
          y: [
            new Date(e.window_start).getTime(),
            new Date(e.window_end).getTime()
          ],
          meta: e.reason
        }));
  - entity: sensor.pv_excess_control_plan_confidence
    name: Dishwasher
    type: rangeBar
    color: blue
    data_generator: |
      const entries = entity.attributes.plan_entries || [];
      return entries
        .filter(e =>
          e.appliance_id === 'dishwasher' &&
          e.window_start && e.window_end &&
          (e.action === 'on' || e.action === 'set_current')
        )
        .map(e => ({
          x: e.appliance_id,
          y: [
            new Date(e.window_start).getTime(),
            new Date(e.window_end).getTime()
          ],
          meta: e.reason
        }));
apex_config:
  chart:
    type: rangeBar
    height: 160
  plotOptions:
    bar:
      horizontal: true
      barHeight: 50%
  xaxis:
    type: datetime
    labels:
      datetimeUTC: false
  tooltip:
    custom: |
      function({ seriesIndex, dataPointIndex, w }) {
        const data = w.config.series[seriesIndex].data[dataPointIndex];
        const start = new Date(data.y[0]).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        const end = new Date(data.y[1]).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
        const reason = (data.meta || '').replace(/_/g, ' ');
        return '<div style="padding:4px 8px">' + start + '–' + end + '<br/>' + reason + '</div>';
      }
```

---

## 7. Energy & Savings

### Daily Energy Sparklines (Mini Graph)

Compact sparkline history for each appliance's energy consumption today.

```yaml
type: grid
columns: 3
square: false
cards:
  - type: custom:mini-graph-card
    name: EV Charger
    icon: mdi:ev-station
    entities:
      - entity: sensor.pv_excess_control_ev_charger_energy_today
        name: Energy
        color: cyan
    hours_to_show: 24
    points_per_hour: 2
    line_width: 2
    hour24: true
    show:
      graph: line
      fill: true
      icon: true
      name: true
      state: true
  - type: custom:mini-graph-card
    name: Heat Pump
    icon: mdi:heat-pump
    entities:
      - entity: sensor.pv_excess_control_heat_pump_energy_today
        name: Energy
        color: "var(--warning-color)"
    hours_to_show: 24
    points_per_hour: 2
    line_width: 2
    hour24: true
    show:
      graph: line
      fill: true
      icon: true
      name: true
      state: true
  - type: custom:mini-graph-card
    name: Dishwasher
    icon: mdi:dishwasher
    entities:
      - entity: sensor.pv_excess_control_dishwasher_energy_today
        name: Energy
        color: "var(--info-color)"
    hours_to_show: 24
    points_per_hour: 2
    line_width: 2
    hour24: true
    show:
      graph: line
      fill: true
      icon: true
      name: true
      state: true
```

### Daily Summary

Entities card with per-appliance totals and activation counts.

```yaml
type: entities
title: Today's Summary
show_header_toggle: false
entities:
  - type: section
    label: EV Charger
  - entity: sensor.pv_excess_control_ev_charger_energy_today
    name: Energy consumed
  - entity: sensor.pv_excess_control_ev_charger_runtime_today
    name: Runtime
  - entity: sensor.pv_excess_control_ev_charger_activations_today
    name: Activations
  - type: section
    label: Heat Pump
  - entity: sensor.pv_excess_control_heat_pump_energy_today
    name: Energy consumed
  - entity: sensor.pv_excess_control_heat_pump_runtime_today
    name: Runtime
  - entity: sensor.pv_excess_control_heat_pump_activations_today
    name: Activations
  - type: section
    label: Dishwasher
  - entity: sensor.pv_excess_control_dishwasher_energy_today
    name: Energy consumed
  - entity: sensor.pv_excess_control_dishwasher_runtime_today
    name: Runtime
  - entity: sensor.pv_excess_control_dishwasher_activations_today
    name: Activations
```

---

## 8. Activity History

### History Graph — Appliance Active States

Built-in history graph showing when each appliance was running over the last 24 hours.

```yaml
type: history-graph
title: Appliance Activity (24 h)
hours_to_show: 24
entities:
  - entity: binary_sensor.pv_excess_control_ev_charger_active
    name: EV Charger
  - entity: binary_sensor.pv_excess_control_heat_pump_active
    name: Heat Pump
  - entity: binary_sensor.pv_excess_control_dishwasher_active
    name: Dishwasher
```

### Activity + Excess Power Overlay (Mini Graph)

Combines excess power history with appliance active states in a single sparkline view.

```yaml
type: custom:mini-graph-card
name: Activity vs Excess Power
icon: mdi:solar-power
hours_to_show: 24
points_per_hour: 2
hour24: true
line_width: 2
show:
  graph: line
  fill: false
  legend: true
  state: false
entities:
  - entity: sensor.pv_excess_control_excess_power
    name: Excess Power
    color: "var(--warning-color)"
    y_axis: left
  - entity: binary_sensor.pv_excess_control_ev_charger_active
    name: EV Charger
    color: cyan
    y_axis: right
  - entity: binary_sensor.pv_excess_control_heat_pump_active
    name: Heat Pump
    color: "var(--error-color)"
    y_axis: right
  - entity: binary_sensor.pv_excess_control_dishwasher_active
    name: Dishwasher
    color: "var(--info-color)"
    y_axis: right
```

---

## 9. Full Dashboard

A single vertical-stack combining all sections into one cohesive view. Paste this into a new Lovelace view in **raw configuration editor** mode.

```yaml
type: vertical-stack
cards:
  # ── Master controls ───────────────────────────────────────────────────────
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: switch.pv_excess_control_control_enabled
        icon_color: green
      - type: entity
        entity: switch.pv_excess_control_force_charge
        icon_color: amber
      - type: entity
        entity: select.pv_excess_control_battery_strategy
      - type: conditional
        conditions:
          - entity: binary_sensor.pv_excess_control_excess_available
            state: "on"
        chip:
          type: template
          icon: mdi:solar-power
          icon_color: green
          content: >-
            {{ states('sensor.pv_excess_control_excess_power') | int }} W excess

  # ── Power flow ────────────────────────────────────────────────────────────
  - type: custom:power-flow-card-plus
    entities:
      grid:
        entity: sensor.fronius_grid_export         # <- CHANGE
        secondary_info:
          entity: sensor.fronius_grid_import       # <- CHANGE
      solar:
        entity: sensor.fronius_pv_power            # <- CHANGE
      battery:
        entity: sensor.fronius_battery_power       # <- CHANGE
        state_of_charge: sensor.fronius_battery_soc  # <- CHANGE
      home:
        entity: sensor.fronius_load_power          # <- CHANGE
      individual:
        - entity: sensor.pv_excess_control_ev_charger_power
          name: EV Charger
          icon: mdi:ev-station
        - entity: sensor.pv_excess_control_heat_pump_power
          name: Heat Pump
          icon: mdi:heat-pump
        - entity: sensor.pv_excess_control_dishwasher_power
          name: Dishwasher
          icon: mdi:dishwasher
    kw_decimals: 1
    min_flow_rate: 0.75
    max_flow_rate: 6

  # ── Appliance cards ───────────────────────────────────────────────────────
  - type: vertical-stack
    cards:
      - type: custom:mushroom-template-card
        primary: EV Charger
        secondary: "{{ states('sensor.pv_excess_control_ev_charger_status') }}"
        icon: mdi:ev-station
        icon_color: >-
          {% if is_state('binary_sensor.pv_excess_control_ev_charger_active', 'on') %}cyan{% else %}disabled{% endif %}
        badge_icon: >-
          {% if state_attr('sensor.pv_excess_control_ev_charger_status', 'overrides_plan') %}mdi:calendar-alert{% endif %}
        badge_color: amber
      - type: custom:mushroom-chips-card
        chips:
          - type: entity
            entity: switch.pv_excess_control_ev_charger_enabled
            icon_color: green
          - type: entity
            entity: switch.pv_excess_control_ev_charger_override
            icon_color: amber
          - type: conditional
            conditions:
              - entity: sensor.pv_excess_control_ev_charger_status
                attribute: cooldown_seconds_remaining
                state_not: null
            chip:
              type: template
              icon: mdi:timer-sand
              icon_color: orange
              content: >-
                {% set s = state_attr('sensor.pv_excess_control_ev_charger_status', 'cooldown_seconds_remaining') %}
                {% if s %}{{ s }}s{% endif %}

  - type: vertical-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Heat Pump
        secondary: "{{ states('sensor.pv_excess_control_heat_pump_status') }}"
        icon: mdi:heat-pump
        icon_color: >-
          {% if is_state('binary_sensor.pv_excess_control_heat_pump_active', 'on') %}deep-orange{% else %}disabled{% endif %}
        badge_icon: >-
          {% if state_attr('sensor.pv_excess_control_heat_pump_status', 'overrides_plan') %}mdi:calendar-alert{% endif %}
        badge_color: amber
      - type: custom:mushroom-chips-card
        chips:
          - type: entity
            entity: switch.pv_excess_control_heat_pump_enabled
            icon_color: green
          - type: entity
            entity: switch.pv_excess_control_heat_pump_override
            icon_color: amber
          - type: conditional
            conditions:
              - entity: sensor.pv_excess_control_heat_pump_status
                attribute: cooldown_seconds_remaining
                state_not: null
            chip:
              type: template
              icon: mdi:timer-sand
              icon_color: orange
              content: >-
                {% set s = state_attr('sensor.pv_excess_control_heat_pump_status', 'cooldown_seconds_remaining') %}
                {% if s %}{{ s }}s{% endif %}

  - type: vertical-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Dishwasher
        secondary: "{{ states('sensor.pv_excess_control_dishwasher_status') }}"
        icon: mdi:dishwasher
        icon_color: >-
          {% if is_state('binary_sensor.pv_excess_control_dishwasher_active', 'on') %}blue{% else %}disabled{% endif %}
        badge_icon: >-
          {% if state_attr('sensor.pv_excess_control_dishwasher_status', 'overrides_plan') %}mdi:calendar-alert{% endif %}
        badge_color: amber
      - type: custom:mushroom-chips-card
        chips:
          - type: entity
            entity: switch.pv_excess_control_dishwasher_enabled
            icon_color: green
          - type: entity
            entity: switch.pv_excess_control_dishwasher_override
            icon_color: amber

  # ── Solar forecast ────────────────────────────────────────────────────────
  - type: custom:apexcharts-card
    header:
      title: Solar Forecast
      show: true
    graph_span: 2d
    span:
      start: day
    series:
      - entity: sensor.solcast_pv_forecast_forecast_today    # <- CHANGE
        name: Today
        color: "var(--warning-color)"
        type: area
        curve: smooth
        opacity: 0.3
        unit: W
        data_generator: |
          const attr = entity.attributes.detailedForecast
            || entity.attributes.forecasts
            || entity.attributes.detailedHourly;
          if (!attr) return [];
          return attr.map(item => [
            new Date(item.period_start || item.datetime).getTime(),
            Math.round((item.pv_estimate || item.watts || 0) * 1000)
          ]);
      - entity: sensor.solcast_pv_forecast_forecast_tomorrow  # <- CHANGE
        name: Tomorrow
        color: "var(--info-color)"
        type: line
        curve: smooth
        unit: W
        data_generator: |
          const attr = entity.attributes.detailedForecast
            || entity.attributes.forecasts
            || entity.attributes.detailedHourly;
          if (!attr) return [];
          return attr.map(item => [
            new Date(item.period_start || item.datetime).getTime(),
            Math.round((item.pv_estimate || item.watts || 0) * 1000)
          ]);
    yaxis:
      - min: 0
        apex_config:
          forceNiceScale: true
    apex_config:
      chart:
        height: 200
      xaxis:
        type: datetime
        labels:
          datetimeUTC: false

  # ── Activity history ──────────────────────────────────────────────────────
  - type: history-graph
    title: Appliance Activity (24 h)
    hours_to_show: 24
    entities:
      - entity: binary_sensor.pv_excess_control_ev_charger_active
        name: EV Charger
      - entity: binary_sensor.pv_excess_control_heat_pump_active
        name: Heat Pump
      - entity: binary_sensor.pv_excess_control_dishwasher_active
        name: Dishwasher

  # ── Daily summary ─────────────────────────────────────────────────────────
  - type: entities
    title: Today's Summary
    show_header_toggle: false
    entities:
      - type: section
        label: EV Charger
      - entity: sensor.pv_excess_control_ev_charger_energy_today
        name: Energy consumed
      - entity: sensor.pv_excess_control_ev_charger_runtime_today
        name: Runtime
      - entity: sensor.pv_excess_control_ev_charger_activations_today
        name: Activations
      - type: section
        label: Heat Pump
      - entity: sensor.pv_excess_control_heat_pump_energy_today
        name: Energy consumed
      - entity: sensor.pv_excess_control_heat_pump_runtime_today
        name: Runtime
      - entity: sensor.pv_excess_control_heat_pump_activations_today
        name: Activations
      - type: section
        label: Dishwasher
      - entity: sensor.pv_excess_control_dishwasher_energy_today
        name: Energy consumed
      - entity: sensor.pv_excess_control_dishwasher_runtime_today
        name: Runtime
      - entity: sensor.pv_excess_control_dishwasher_activations_today
        name: Activations
```

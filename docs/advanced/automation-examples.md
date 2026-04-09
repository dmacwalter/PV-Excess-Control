# Automation Examples

These examples show how to use PV Excess Control entities in Home Assistant automations to extend the integration's behaviour.

---

## Notify When EV Finishes Charging

```yaml
alias: "EV Charging Complete"
trigger:
  - platform: numeric_state
    entity_id: sensor.my_car_battery_level
    above: 90
condition:
  - condition: state
    entity_id: binary_sensor.pv_excess_control_ev_charger_active
    state: "on"
action:
  - service: notify.mobile_app_phone
    data:
      message: "EV is above 90% — charging paused"
mode: single
```

---

## Prevent Heat Pump from Running at Night

Use the override switch to disable an appliance during specific hours:

```yaml
alias: "Block Heat Pump at Night"
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.pv_excess_control_heat_pump_override
  - delay: "08:00:00"
  - service: switch.turn_off
    target:
      entity_id: switch.pv_excess_control_heat_pump_override
mode: single
```

---

## Run Dishwasher Only When SoC is Above 50%

Use a condition on the integration's optimizer by setting the dishwasher's priority low -- but if you want a hard rule, create two automations:

```yaml
alias: "Block Dishwasher — Low Battery"
trigger:
  - platform: numeric_state
    entity_id: sensor.battery_soc
    below: 50
action:
  - service: switch.turn_on
    target:
      entity_id: switch.pv_excess_control_dishwasher_override
mode: single
```

```yaml
alias: "Unblock Dishwasher — Battery Recovered"
trigger:
  - platform: numeric_state
    entity_id: sensor.battery_soc
    above: 60
action:
  - service: switch.turn_off
    target:
      entity_id: switch.pv_excess_control_dishwasher_override
mode: single
```

---

## Force Charge Battery Before a Storm

Trigger on a weather integration forecast:

```yaml
alias: "Storm Pre-Charge"
trigger:
  - platform: state
    entity_id: sensor.weather_forecast_condition
    to: "lightning-rainy"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.pv_excess_control_force_charge
  - service: notify.mobile_app_phone
    data:
      message: "Storm forecast — grid battery charging enabled"
mode: single
```

---

## Daily Energy Report via Telegram

Use per-appliance sensors for energy reporting:

```yaml
alias: "Daily PV Report"
trigger:
  - platform: time
    at: "19:00:00"
action:
  - service: notify.telegram_bot
    data:
      message: >
        PV Report for {{ now().strftime('%d %b') }}:
        Excess Power: {{ states('sensor.pv_excess_control_excess_power') }} W
        EV Energy: {{ states('sensor.pv_excess_control_ev_charger_energy_today') }} kWh
        Heat Pump Energy: {{ states('sensor.pv_excess_control_heat_pump_energy_today') }} kWh
mode: single
```

---

## Apartment Balcony Solar: Maximize Self-Consumption

For small systems where you want any appliance to run when solar is available, create two automations:

```yaml
alias: "Balcony Solar — Enable Appliances"
trigger:
  - platform: numeric_state
    entity_id: sensor.pv_excess_control_excess_power
    above: 100
action:
  - service: switch.turn_off
    target:
      entity_id:
        - switch.pv_excess_control_washing_machine_override
        - switch.pv_excess_control_dishwasher_override
mode: single
```

```yaml
alias: "Balcony Solar — Disable Appliances"
trigger:
  - platform: numeric_state
    entity_id: sensor.pv_excess_control_excess_power
    below: 0
  - platform: time
    at: "19:00:00"
action:
  - service: switch.turn_on
    target:
      entity_id:
        - switch.pv_excess_control_washing_machine_override
        - switch.pv_excess_control_dishwasher_override
mode: single
```

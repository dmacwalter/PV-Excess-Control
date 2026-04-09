# EV Charging

PV Excess Control provides first-class EV charging support with dynamic current control, SoC awareness, deadline scheduling, and connection detection.

---

## Features

- **Dynamic current** -- Continuously adjusts amps to consume exactly available solar excess
- **SoC awareness** -- Stops charging when EV reaches the configured target SoC
- **Connection detection** -- Pauses charging logic when the car is not plugged in
- **Deadline scheduling** -- Ensures the car is charged to a target by a specific time
- **Cheap tariff fallback** -- Charges during off-peak hours if solar is insufficient

---

## Configuration

Add your EV charger as an appliance with these settings:

```
Name: EV Charger
Switch Entity: switch.wallbox_charging    # or input_boolean controlling the charger
Priority: 10                               # low number = high priority
Nominal Power: 7400 W                     # 32A x 1-phase x 230V or similar
Phases: 3

Dynamic Current: Yes
  Current Entity: number.wallbox_current
  Min Current: 6 A
  Max Current: 16 A

EV SoC Sensor: sensor.my_car_battery_level     # 0-100 %
EV Connected Sensor: binary_sensor.wallbox_car_connected
EV Target SoC: 80                              # stop charging at 80%

Schedule Deadline: 07:00
Min Daily Runtime: 90 min
```

---

## How SoC Is Used

The EV SoC sensor works with the **EV Target SoC** configuration field to control charging:

- **EV Target SoC** -- A user-configured percentage (e.g., 80%). When the EV's SoC reaches or exceeds this target, charging stops. The appliance is excluded from allocation in the optimizer.
- **Disconnected** -- The appliance is skipped entirely for the current cycle when the EV is not plugged in.

Configure the target SoC per appliance when adding or editing the EV charger in the integration's settings. This allows you to set different targets for different EVs if you have multiple chargers.

---

## Deadline Scheduling

When a **Schedule Deadline** is set (e.g. `07:00`), the planner guarantees the EV reaches its **Min Daily Runtime** by that time.

The planner:
1. Calculates how much runtime remains to meet the minimum
2. Finds the cheapest available hours (solar excess or cheap tariff) before the deadline
3. Schedules charging in those hours

This means overnight cheap-rate charging happens automatically without separate automations.

---

## Multiple EVs

Add a separate appliance for each EV charger. Assign different priorities:

```
EV Charger 1 (daily driver):  Priority 5
EV Charger 2 (weekend car):   Priority 30
```

The optimizer fills higher-priority chargers first and uses remaining excess for lower-priority ones.

---

## Integration with Common Charger Brands

### go-eCharger
```
Switch Entity:   switch.go_echarger_charging
Current Entity:  number.go_echarger_max_current
```

### Wallbox Pulsar Plus
```
Switch Entity:   switch.wallbox_charging
Current Entity:  number.wallbox_max_charging_current
Connected Sensor: binary_sensor.wallbox_status_description  # check state values
```

### OCPP Charger
```
Switch Entity:   switch.ocpp_charge_point
Current Entity:  number.ocpp_charge_limit_amps
```

---

## Common Issues

**Car charges even when disconnected**
Ensure the **EV Connected Sensor** is mapped correctly and returns `on` only when connected. Check the sensor state in Developer Tools -> States.

**Charging stops too early**
If Min Daily Runtime is not set, the planner has no guarantee to maintain. Set a runtime that matches typical daily driving needs.

**Charging current too low**
If excess is consistently below the minimum current threshold (6 A x 3 phases x 230 V = 4140 W), consider enabling **Allow Grid Supplement** with a small allowance (e.g. 500 W) to bridge the gap.

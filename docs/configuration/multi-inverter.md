# Multi-Inverter Setup

If you have more than one inverter (e.g. two roof sections with separate inverters, or a separate battery inverter), you can aggregate their sensors before connecting them to PV Excess Control.

---

## Approach: Aggregate with Template Sensors

Create template sensors that sum the outputs of all your inverters:

```yaml
# configuration.yaml
template:
  - sensor:
      - name: "Total PV Power"
        unit_of_measurement: W
        device_class: power
        state: >
          {{ (states('sensor.inverter1_pv_power') | float(0)) +
             (states('sensor.inverter2_pv_power') | float(0)) }}

      - name: "Total Grid Power"
        unit_of_measurement: W
        device_class: power
        state: >
          {{ (states('sensor.inverter1_grid_power') | float(0)) +
             (states('sensor.inverter2_grid_power') | float(0)) }}
```

Then use `sensor.total_pv_power` and `sensor.total_grid_power` in the PV Excess Control sensor mapping.

---

## AC-Coupled Battery (e.g. Powerwall)

Some systems have a separate AC-coupled battery inverter. Map:

- **PV Power** → your solar inverter's PV output
- **Battery SoC / Battery Power** → the battery inverter's sensors
- **Import/Export** → the grid meter sensor (at the meter, after all inverters)

---

## Example: Two String Inverters + Fronius Symo

```yaml
template:
  - sensor:
      - name: "Combined PV Power"
        unit_of_measurement: W
        state: >
          {{ (states('sensor.fronius_string1_power') | float(0)) +
             (states('sensor.fronius_string2_power') | float(0)) }}
```

In PV Excess Control sensor mapping:
- PV Power: `sensor.combined_pv_power`
- Import/Export: `sensor.fronius_smart_meter_power`

---

## Multiple PV Excess Control Instances

For completely separate systems (e.g. a main house and a guest house), add multiple PV Excess Control integration entries. Each instance manages its own set of appliances independently.

---

## Common Issues

**Negative excess when system is producing**
Check that the sign convention is consistent across your aggregated sensors. If inverter 1 exports positive and inverter 2 exports negative, the sum will cancel out. Fix with a per-sensor inversion.

**Battery SoC jumps around**
If you have multiple batteries, average the SoC values:

```yaml
state: >
  {{ ((states('sensor.battery1_soc') | float(0)) +
      (states('sensor.battery2_soc') | float(0))) / 2 }}
```

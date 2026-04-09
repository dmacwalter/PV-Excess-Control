# Analytics

PV Excess Control tracks energy consumption, runtime, savings, and self-consumption ratios for all managed appliances.

---

## What Is Tracked

### Per Appliance
- **Energy today** (kWh) -- Solar and grid energy consumed today
- **Runtime today** -- Total on-time today

### System-Wide
- **Self-consumption ratio** (%) -- tracked internally by the coordinator
- **Savings today** -- tracked internally by the coordinator

---

## How Savings Are Calculated

For each cycle where an appliance is running:

```
savings = power_kw x cycle_duration_h x net_savings_per_kwh

net_savings_per_kwh = import_price - feed_in_tariff
```

If the appliance is running on cheap grid tariff (not solar), the savings calculation reflects the difference between the cheap rate and the normal import price.

Energy sources are tracked per-appliance:
- `solar` -- Running on solar excess
- `cheap_tariff` -- Running on cheap grid power
- `grid` -- Running on normal grid power

---

## Entities Created

### Per-Appliance Sensors

For an appliance named "Water Heater" (slug: `water_heater`):

| Entity | Description |
|--------|-------------|
| `sensor.pv_excess_control_water_heater_power` | Current power draw of this appliance (W) |
| `sensor.pv_excess_control_water_heater_energy_today` | Energy consumed by this appliance today (kWh) |
| `sensor.pv_excess_control_water_heater_runtime_today` | Runtime of this appliance today |
| `sensor.pv_excess_control_water_heater_activations_today` | Number of times turned on today |
| `sensor.pv_excess_control_water_heater_status` | Optimizer's current decision and the reasoning behind it (see the Dashboard guide for attribute reference) |

### System-Level

System-wide analytics (self-consumption ratio, total savings) are tracked internally by the coordinator and are available via the daily summary notification. They are not exposed as separate sensor entities.

---

## Long-Term Statistics

Per-appliance energy sensors integrate with Home Assistant's long-term statistics. Use the **Energy Dashboard** to track historical data:

1. Go to **Settings -> Dashboards -> Energy**
2. Add `sensor.pv_excess_control_water_heater_energy_today` as an "Individual Device" source
3. View daily, weekly, and monthly energy breakdowns

---

## Resetting Daily Statistics

Statistics reset automatically at midnight. The reset time follows your Home Assistant timezone setting.

There is no manual reset service. Daily statistics are managed entirely by the integration's internal midnight reset.

---

## Apartment with Balcony Solar Example

For small systems (balcony PV, 600-800 W), analytics help validate whether the integration is worth the effort:

Typical day:
- Solar produced: 2.1 kWh
- Self-consumed by appliances: 1.8 kWh (86 % self-consumption)
- Exported: 0.3 kWh
- Savings: EUR 0.43

Monthly savings: ~EUR 13, annual ~EUR 155 -- easily justifying the setup.

---

## Common Issues

**Savings appear too low**
Check that the tariff prices in the energy pricing config are correct. Savings are calculated from the configured import price and feed-in tariff -- if these are wrong, savings will be wrong.

**Self-consumption ratio above 100 %**
This can happen if the PV power sensor is reading lower than actual production (e.g. after-inverter losses excluded). Verify the PV power sensor measures the full DC or AC output.

**Energy sensors not appearing in Energy Dashboard**
Ensure the sensor has `device_class: energy` and `state_class: total`. These are set automatically by the integration, but custom template sensors wrapping them may strip these attributes.

# Initial Setup

This page walks you through the PV Excess Control setup wizard step by step.

---

## Step 1 — Inverter Type

Choose the type of inverter in your system:

| Option | When to use |
|--------|-------------|
| **Standard** | PV + grid only, no battery storage |
| **Hybrid** | PV + battery storage (battery steps appear later) |

Also set **Grid Voltage** (default: 230 V). This is used to convert between amps and watts for dynamic current control.

---

## Step 2 — Sensor Mapping

Map your Home Assistant entities to the integration's required inputs.

See [Sensor Mapping](sensor-mapping.md) for a full description of each field and which inverter brands expose which entities.

**Standard inverter minimum requirement:** either `PV Power` or `Grid Export Power`.

**Hybrid inverter additional requirements:** `Battery SoC`, `Battery Power`, and `Battery Capacity`.

---

## Step 3 — Energy Pricing

Choose how the integration gets electricity prices. This enables the tariff-aware optimizer and cheap-tariff charging.

- **None** — No tariff integration; optimization is solar-excess only
- **Tibber / Awattar / Nordpool / Octopus Energy** — Automatic price retrieval via the respective HA integration
- **Generic sensor** — Point to any HA sensor that exposes a current price in €/kWh (or your local currency)

Set the **Cheap Price Threshold** (e.g. `0.10` €/kWh). Appliances can be configured to run during cheap windows even without solar.

See [Energy Pricing](energy-pricing.md) for details.

---

## Step 4 — Solar Forecast

Choose how the integration gets solar production forecasts. This enables the 24-hour planner and weather pre-planning.

- **None** — Planner uses historical averages only
- **Solcast** — Requires the [Solcast HA integration](https://github.com/BJReplay/ha-solcast-solar)
- **Forecast.Solar** — Requires the built-in Forecast.Solar integration
- **Generic sensor** — Any sensor that provides remaining-today kWh

See [Solar Forecast](solar-forecast.md) for details.

---

## Step 5 — Battery Strategy (Hybrid Only)

Configure how the battery is managed alongside appliances:

| Strategy | Behavior |
|----------|----------|
| **Battery First** | Fills the battery before turning on appliances |
| **Appliance First** | Runs appliances before charging the battery |
| **Balanced** | Splits excess proportionally between battery and appliances |

Additional battery settings:

| Field | Description |
|-------|-------------|
| **Target SoC** | Desired charge level to reach by target time (e.g. 80%) |
| **Target Time** | Time by which the battery should reach target SoC (e.g. 07:00) |
| **Allow Grid Charging** | Allow charging the battery from the grid during cheap tariff periods |
| **Battery Max Discharge Entity** | Entity to control maximum battery discharge power |
| **Battery Max Discharge Default** | Default maximum discharge power when no override is active (W) |
| **Min Battery SoC** | When battery SoC drops below this threshold, all non-essential appliances are shed and battery discharge is blocked. Leave empty to disable. |

See [Battery Management](../features/battery-management.md) for details.

---

## Step 6 — Global Settings

| Field | Default | Description |
|-------|---------|-------------|
| Controller Interval | 30 s | How often the real-time optimizer runs |
| Planner Interval | 900 s | How often the 24-hour planner recalculates |
| Plan Influence | Light | How the planner affects decisions: **None** (pure reactive), **Light** (lower thresholds when plan says ON), **Plan follows** (schedule-driven). See [How It Works](../advanced/how-it-works.md#plan-influence) |
| Enable Preemption | Off | When enabled, the optimizer can shed lower-priority appliances to start higher-priority ones that lack sufficient excess power |
| Export Limit | — | Maximum grid export in watts (for feed-in capped systems) |
| Notification Service | — | HA notify service name (e.g. `notify.mobile_app_phone`) |
| Notify Appliance On | Off | Send a notification when an appliance is turned on |
| Notify Appliance Off | Off | Send a notification when an appliance is turned off |
| Notify Daily Summary | Off | Send a daily summary at midnight with energy stats |

---

## Adding Appliances

After the main integration is configured, add each appliance:

1. Go to **Settings → Devices & Services → PV Excess Control**
2. Click **Add sub-entry**
3. Follow the [Adding Appliances](adding-appliances.md) guide

---

## Real-World Example: House with EV and Heat Pump

A typical setup might look like:

```
Inverter type: Hybrid
Grid voltage: 230 V

Sensors:
  PV Power:        sensor.solis_pv_power
  Import/Export:   sensor.solis_grid_power   (positive = export, negative = import)
  Battery SoC:     sensor.solis_battery_soc
  Battery Power:   sensor.solis_battery_power
  Battery Capacity: 10 (kWh)

Tariff provider: Tibber
Cheap threshold: 0.10 €/kWh

Forecast: Solcast
  Forecast sensor: sensor.solcast_forecast_remaining_today

Battery strategy: Balanced
  Target SoC: 80%
  Target time: 07:00
```

Appliances added:
- EV Charger (priority 10, dynamic current, EV SoC sensor)
- Heat Pump (priority 20, 2000 W, on-only mode)
- Dishwasher (priority 50, 1800 W, min runtime 1h)
- Pool Pump (priority 100, 800 W, max runtime 4h/day)

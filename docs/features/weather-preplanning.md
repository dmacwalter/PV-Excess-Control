# Weather Pre-Planning

Weather pre-planning uses tomorrow's solar forecast to make smarter decisions today — running appliances on cheap grid power when tomorrow's forecast is poor, rather than waiting for solar that won't arrive.

---

## How It Works

Every time the planner runs (every 15 minutes), it checks `tomorrow_total_kwh` from the forecast provider:

1. **If tomorrow looks sunny**: The planner defers appliances to use tomorrow's solar excess
2. **If tomorrow looks cloudy**: The planner schedules appliances today during cheap tariff hours instead of waiting

The threshold for "cloudy" is calculated relative to typical production for the season. If tomorrow's forecast is significantly below average, pre-planning activates.

---

## Requirements

- A forecast provider configured with **tomorrow's total kWh** support
  - Solcast provides this via `sensor.solcast_pv_forecast_forecast_tomorrow`
  - Forecast.Solar provides this via `sensor.energy_production_tomorrow`
- A tariff provider configured (so the planner knows which hours are cheap today)
- At least one appliance with a **Schedule Deadline** or **Min Daily Runtime**

---

## Configuration

No additional configuration is required beyond the standard forecast and tariff setup. The planner automatically uses tomorrow's forecast data when available.

To verify pre-planning is active, check the plan entries in the integration's diagnostics — entries with reason `weather_preplanning` indicate this feature is active.

---

## Example Scenario

**Situation**: Thursday evening, 20:00. Tomorrow (Friday) forecast is 2 kWh (cloudy, typical is 18 kWh). Tonight has cheap tariff from 00:00–06:00.

**Without pre-planning**: EV charging is deferred to Friday's solar hours. Friday is cloudy, so the car charges slowly and may miss the deadline.

**With pre-planning**: The planner schedules EV charging tonight during the cheap 00:00–04:00 window. The car is fully charged before Friday.

---

## Appliance Priority in Pre-Planning

Pre-planning respects appliance priority. If total cheap hours are limited:
1. Highest-priority appliances with deadlines are scheduled first
2. Lower-priority appliances fill remaining cheap hours
3. Appliances without deadlines are not included in pre-planning

---

## Common Issues

**Pre-planning runs even on sunny days**
Check the `tomorrow_total_kwh` value from your forecast sensor. If the forecast is inaccurate (always reporting low), pre-planning will trigger unnecessarily. Verify your forecast provider's accuracy by comparing next-day forecasts with actual production.

**Pre-planning doesn't activate on cloudy forecasts**
Ensure `tomorrow_total_kwh` is exposed by your forecast provider. Not all generic sensors provide this value. Solcast and Forecast.Solar support it natively.

**Appliances run overnight unexpectedly**
This is expected behaviour when pre-planning activates. If you want to prevent overnight operation for a specific appliance, set its **Switch Interval** high or add a Home Assistant automation to block the switch entity during night hours.

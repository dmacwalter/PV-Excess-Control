# Solar Forecast

A solar forecast allows the 24-hour planner to schedule appliances intelligently based on expected production, not just current conditions.

---

## Supported Providers

| Provider | HA Integration |
|----------|---------------|
| **None** | No forecast; planner uses fixed averages |
| **Solcast** | [ha-solcast-solar](https://github.com/BJReplay/ha-solcast-solar) |
| **Forecast.Solar** | [Built-in HA integration](https://www.home-assistant.io/integrations/forecast_solar/) |
| **Generic sensor** | Any sensor exposing remaining-today kWh |

---

## What the Planner Does with Forecast Data

When forecast data is available, the 24-hour planner:

1. **Builds a timeline** of expected solar production per hour
2. **Reserves hours** with high production for high-priority appliances
3. **Schedules deadlines** — ensures EV charging completes before 7 am using the cheapest available hours (solar + cheap tariff)
4. **Weather pre-planning** — if tomorrow is expected to be cloudy, it may run appliances today during cheap tariff rather than waiting for solar that won't come
5. **Confidence scoring** — plans carry a confidence level (0–1) based on forecast certainty

---

## Solcast Setup

1. Install the [ha-solcast-solar](https://github.com/BJReplay/ha-solcast-solar) integration
2. Configure your roof segments (azimuth, tilt, peak power)
3. In PV Excess Control, select **Solcast** and set:

| Field | Example Value |
|-------|--------------|
| Forecast sensor | `sensor.solcast_pv_forecast_forecast_remaining_today` |
| Tomorrow forecast sensor | `sensor.solcast_pv_forecast_forecast_tomorrow` (optional) |

The integration automatically extracts hourly breakdown data from Solcast's attributes.

The **Tomorrow Forecast Sensor** enables weather pre-planning: if tomorrow's forecast is significantly lower than today, the planner can shift appliance schedules to take advantage of today's surplus solar.

---

## Forecast.Solar Setup

1. Go to **Settings → Devices & Services → Add Integration → Forecast.Solar**
2. Enter your roof parameters
3. In PV Excess Control, select **Forecast.Solar** and set:

| Field | Example Value |
|-------|--------------|
| Forecast sensor | `sensor.energy_production_today_remaining` |
| Tomorrow forecast sensor | (optional — Forecast.Solar provides this via its own tomorrow sensor) |

---

## Generic Sensor Setup

If you use a different forecast service, create a sensor that provides remaining production for today in kWh:

```yaml
template:
  - sensor:
      - name: "Solar Forecast Remaining"
        unit_of_measurement: kWh
        state: "{{ states('sensor.my_forecast_api_remaining') | float(0) }}"
```

Select **Generic sensor** and point to your template sensor. The planner will use this value for basic planning but cannot produce per-hour breakdowns.

---

## Planning Without Forecast

If you select **None**, the planner still runs but uses simulated averages based on a typical solar day profile. Deadline scheduling and weather pre-planning are disabled. Real-time control still works fully.

---

## Common Issues

**Planner confidence is always low**
This is normal when no forecast is configured. Add a forecast provider to improve planning quality.

**Solcast sensor shows "unavailable" early morning**
Solcast updates on a schedule. The integration tolerates unavailable forecast data and falls back gracefully.

**Forecast seems too optimistic or pessimistic**
Check your roof configuration in the Solcast or Forecast.Solar integration (azimuth, tilt, shading, peak power). Inaccurate parameters cause inaccurate forecasts.

# Notifications

PV Excess Control can send Home Assistant notifications for key events. Each event type can be enabled or disabled independently.

---

## Setup

During initial setup (or in Options), set a **Notification Service**:

```
notify.mobile_app_my_phone
notify.telegram
notify.pushover
```

This must be a valid HA notify service. The integration calls it using the standard `notify` domain.

---

## Event Types

The following notification toggles are configurable via the integration's Settings step:

| Toggle | Config Field | Default | When it fires |
|--------|-------------|---------|--------------|
| **Appliance On** | `notify_appliance_on` | Off | Every time an appliance is switched on |
| **Appliance Off** | `notify_appliance_off` | Off | Every time an appliance is switched off |
| **Daily Summary** | `notify_daily_summary` | Off | Once daily at midnight (00:00) with energy stats and savings |

---

## Configuring Notification Toggles

Notification toggles are configured via the integration's options flow:

1. Go to **Settings -> Integrations -> PV Excess Control**
2. Click **Configure**
3. Navigate to the **Settings** step
4. Enable or disable individual notification types

There are no separate switch entities for notification toggles. All notification preferences are managed through the integration's configuration UI.

---

## Daily Summary

When enabled, the daily summary (sent at midnight, 00:00) includes:

- Total solar production (kWh)
- Self-consumption ratio (%)
- Total energy consumed by managed appliances (kWh)
- Estimated savings vs. grid
- Per-appliance runtime summary

Example notification:

```
PV Excess Control — Daily Summary
Solar produced: 18.4 kWh | Self-consumed: 72%
Appliance energy: 9.2 kWh | Savings: €2.16

  EV Charger:   5.4 kWh  |  74 min  |  €1.26
  Heat Pump:    2.1 kWh  |  105 min |  €0.49
  Dishwasher:   1.7 kWh  |  60 min  |  €0.40
```

---

## Sensor Unavailable Warnings

When a mapped sensor (PV power, grid export, battery SoC) becomes unavailable, the integration sends a warning notification. This helps catch inverter connectivity issues before they silently degrade optimization.

---

## Common Issues

**No notifications received**
Verify the notify service name is correct by testing it in Developer Tools -> Services -> notify.X with a test message.

**Too many appliance on/off notifications**
Leave Appliance On/Off disabled (the default) and only enable them for specific troubleshooting. For general awareness, the Daily Summary is less noisy.

**Notification service not listed**
The integration accepts any string as the notify service name -- it does not validate the service exists at setup time. If notifications aren't arriving, check the service name spelling.

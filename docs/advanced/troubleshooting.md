# Troubleshooting

---

## Diagnostics

### Check the Logs

Enable debug logging for the integration:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.pv_excess_control: debug
```

After restarting, the log will show every optimizer cycle, including excess calculation, allocation decisions, and plan entries.

---

## Common Problems

### Appliances Never Turn On

**Check 1: Is excess being calculated correctly?**

In Developer Tools → States, find `sensor.pv_excess_control_excess_power`. If it is 0 or negative when solar is producing, the sensor mapping is wrong.

Common causes:
- Wrong sign convention on grid sensor (see [Sensor Mapping](../configuration/sensor-mapping.md))
- PV power sensor is unavailable — integration defaults to 0
- Load power sensor included when it should not be (if using Import/Export, load power is implicit)

**Check 2: Is excess below the ON threshold?**

The ON threshold is a hardcoded default of 200 W. If excess is 150 W, the threshold prevents turn-on. The appliance needs at least 200 W of sustained excess to activate.

**Check 3: Are switch interval constraints blocking it?**

An appliance that was recently turned off will not turn on again until the switch interval expires. Check the appliance's last state change time in the device page.

---

### Appliances Switch Too Frequently

**Problem**: Appliance turns on/off repeatedly every few minutes.

**Fixes**:
1. Increase **Switch Interval** to 300–600 s for the appliance
2. The ON threshold (200 W) and OFF threshold (-50 W) provide built-in hysteresis to prevent flip-flopping
3. If the appliance is still switching too frequently, check that the switch interval has not been set too low

---

### EV Not Charging

**Check 1: Is the car connected?**
Verify `binary_sensor.X_car_connected` shows `on` in Developer Tools.

**Check 2: Is the switch entity controllable?**
Go to Developer Tools → Services → `switch.turn_on` with the switch entity ID. Does it work?

**Check 3: Is the charger in a state that accepts current changes?**
Some EVSEs only accept current changes while actively charging. If the switch is on but current changes are ignored, check the charger's state machine.

---

### Battery Not Charging / Always Discharging

**Check 1: Is the Battery Power sensor sign correct?**
The integration expects positive values for charging and negative for discharging (or vice versa — check your inverter). Verify in Developer Tools.

**Check 2: Is Allow Grid Charging enabled?**
Without this setting, grid charging cannot happen even during cheap hours.

**Check 3: Is Battery Charge Price Threshold set correctly?**
If the threshold is 0 or very low, cheap-rate grid charging will never activate.

---

### Savings Are Always Zero

Savings require a non-zero feed-in tariff and import price to be configured. If both are 0, net savings per kWh is 0.

Set realistic values in Options → Energy Pricing.

---

### Card Not Appearing

1. Clear browser cache (hard refresh: Ctrl+Shift+R)
2. Restart Home Assistant fully (not just reload)
3. Check browser console for JavaScript errors

---

### Integration Fails to Load

Check `home-assistant.log` for:

```
ERROR (MainThread) [homeassistant.loader] ...
```

Common causes:
- Home Assistant version below 2025.8
- Missing dependency in `manifest.json` (check version against the integration's requirements)
- Syntax error in custom template sensors that the integration reads

---

## Getting Help

If the above does not resolve your issue:

1. Enable debug logging and reproduce the problem
2. Download diagnostics
3. Open an issue at [GitHub Issues](https://github.com/InventoCasa/PV-Excess-Control/issues) with:
   - Home Assistant version
   - Integration version
   - Relevant log lines
   - Diagnostics file

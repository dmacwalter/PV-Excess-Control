# Dynamic Current Control

Dynamic current control lets the integration continuously adjust the charging amps of an EV charger or wallbox to precisely match the available solar excess — no on/off switching required.

---

## How It Works

Instead of switching the charger on and off, the optimizer:

1. Calculates available excess power each cycle (every 30 s by default)
2. Converts watts to amps: `amps = watts / (phases × grid_voltage)`
3. Clamps to the appliance's configured min/max current range
4. Writes the new current value to the number entity

This delivers smooth, continuous charging that follows the solar curve.

**Example:** 3 kW excess on a 3-phase 230 V charger → `3000 / (3 × 230)` = 4.35 A → clamped to min 6 A

If excess falls below what the minimum current requires, the charger is turned off (or held on if "On Only" is set).

---

## Configuration

Enable **Dynamic Current** on the appliance:

| Field | Example | Description |
|-------|---------|-------------|
| Current Entity | `number.wallbox_charging_current` | Writable number entity |
| Min Current | `6` | EVSE minimum (usually 6 A) |
| Max Current | `16` or `32` | EVSE or circuit maximum |
| Current Step | `1.0` | Resolution of current adjustments (default: 0.1 A). Set to 1.0 for chargers that only accept whole-amp values. |
| Phases | `3` | 1 or 3 phase |

---

## Compatible Hardware

Any EV charger or wallbox that exposes a writable `number` entity for charging current in Home Assistant:

- **go-eCharger** via go-e API integration
- **Wallbox Pulsar** via Wallbox integration
- **KEBA** via KEBA integration
- **ABB Terra** via Modbus
- **OpenEVSE** via OpenEVSE integration
- **charger.io** via API
- **Any OCPP-compatible charger** via the OCPP integration

The charger must support IEC 61851 pilot signal current control (almost all modern EVSEs do).

---

## Minimum Excess for Dynamic Charging

The minimum power needed to charge at minimum current:

| Min Current | 1-phase | 3-phase |
|-------------|---------|---------|
| 6 A | 1380 W | 4140 W |
| 8 A | 1840 W | 5520 W |
| 10 A | 2300 W | 6900 W |

If your solar production is typically below these thresholds, consider:
- Setting **Allow Grid Supplement** with a small **Max Grid Power** to bridge the gap
- Using the **Schedule Deadline** feature to charge during cheap overnight hours instead

---

## Interaction with Planning

The planner sets a target current range for each planning slot. The real-time controller adjusts within that range every 30 seconds based on actual conditions.

---

## Common Issues

**Current jumps between min and 0 frequently**
Increase the **On Threshold** (global setting) so the charger only starts when there is clearly sufficient excess. Or enable **Allow Grid Supplement** with a small allowance.

**Charger ignores current changes**
Some chargers only accept current changes while actively charging. Ensure the charger is in an "active" state before the current entity accepts values.

**Current entity not writable**
The `number` entity must be writable. Some integrations expose a read-only sensor instead. Check in Developer Tools → States — if it shows "number" domain and you can set its value via the UI, it will work.

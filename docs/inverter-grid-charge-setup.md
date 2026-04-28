# Inverter Forced Grid-Charge Setup

This guide explains how to wire PV Excess Control to command your inverter
to charge the home battery from the grid during cheap tariff windows.

## What this feature does

When enabled, the integration writes to up to three Home Assistant entities
exposed by your inverter (or your inverter's HACS integration) to engage
forced grid charging at a configurable wattage. It re-evaluates each
control cycle (default 30 s) and disengages when:

- the current price rises above your `battery_charge_price_threshold`, or
- the battery state of charge reaches your `battery_target_soc`.

The integration tracks whether *it* engaged the inverter, so a manual UI
change between cycles is silently re-asserted only if conditions still
match. The state survives Home Assistant restarts.

## Generic configuration model

Three optional triplets:

| Triplet     | Required? | Examples                                              |
|-------------|-----------|-------------------------------------------------------|
| Enable cmd  | yes       | `input_select.set_sg_battery_forced_charge_discharge_cmd` + `"Forced charge"` / `"Stop (default)"` |
| Mode        | optional  | `input_select.set_sg_ems_mode` + `"Forced mode"` / `"Self-consumption mode (default)"` |
| Power       | optional  | `input_number.set_sg_forced_charge_discharge_power`  |

Engage order: mode → power → enable.
Disengage order: enable (stop) → mode (revert). Power is left untouched on
disengage to preserve a user-set value.

Supported entity domains for **mode** and **enable**: `input_select`,
`select`, `switch`, `input_boolean`. For switch/input_boolean, set the
engage/disengage values to `"on"`/`"off"` (case-insensitive; `"true"`,
`"1"`, `"yes"` also count as on).

Supported entity domains for **power**: `input_number`, `number`.

## Worked examples

### Sungrow SHx with mkaiser Modbus integration

| Field | Value |
|---|---|
| Enable entity | `input_select.set_sg_battery_forced_charge_discharge_cmd` |
| Engage value | `Forced charge` |
| Disengage value | `Stop (default)` |
| Mode entity | `input_select.set_sg_ems_mode` |
| Mode engage value | `Forced mode` |
| Mode disengage value | `Self-consumption mode (default)` |
| Power entity | `input_number.set_sg_forced_charge_discharge_power` |
| Forced grid-charge power | up to 5000 W (inverter cap on SH5RT-V112 / SH10RT-V112) |

Tip: ensure `input_number.set_sg_max_soc` is at or above `battery_target_soc`
in the integration; otherwise the inverter stops accepting forced charge
before the integration's gate trips.

### Single-switch inverter

Some integrations expose a simple toggle entity. Wire only the enable triplet:

| Field | Value |
|---|---|
| Enable entity | `switch.battery_force_charge` |
| Engage value | `on` |
| Disengage value | `off` |

No mode, no power. Power is controlled by whatever the switch represents.

### Solis (HACS Solis Modbus) — placeholder, contributions welcome

Likely shape (untested by the maintainer; please open an issue with your
working values):

| Field | Value |
|---|---|
| Enable entity | `select.solis_storage_mode` |
| Engage value | `Force Charge` |
| Disengage value | `Self-Use` |

### Deye / SunSynk — placeholder, contributions welcome

| Field | Value |
|---|---|
| Enable entity | `select.sunsynk_priority_mode` |
| Engage value | `Battery First` |
| Disengage value | `Load First` |
| Power entity | `number.sunsynk_grid_charge_power` |

### Generic Modbus via input_number + automation

If your inverter has only direct Modbus registers, create three
`input_number`/`input_boolean` helpers in HA, point this integration at
them, then write a Home Assistant automation that mirrors the helpers to
your `modbus.write_register` calls.

## Common pitfalls

- **Inverter SoC ceiling:** The inverter's own max-SoC limit must be at
  least `battery_target_soc`, otherwise the inverter refuses forced charge
  before the integration's gate trips.
- **Inverter power range:** `battery_grid_charge_power_w` must be within
  the inverter's accepted range (e.g. Sungrow 0–5000W).
- **mkaiser helper-vs-Modbus distinction:** The mkaiser integration writes
  Modbus only via its bundled automations. Always point this integration
  at the `input_select` / `input_number` *helpers*, never directly at
  Modbus.
- **Test your wiring before relying on it:** Flip the manual `force_charge`
  switch in HA. Watch the inverter's mode change in the UI and verify
  grid import rises. Flip it off, watch it revert.
- **Notification channel:** Engage/disengage notifications use the existing
  `notify_force_charge` toggle in the integration's notification settings.

## Disabling

Set `auto_battery_grid_charge: false` and don't flip the manual
`force_charge` switch. The integration will not write to your inverter.

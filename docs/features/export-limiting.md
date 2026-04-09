# Export Limiting

Some grid operators impose a cap on how much power you can export (feed-in limit). Export limiting ensures that when your solar production hits the cap, excess power is redirected to appliances rather than being curtailed.

---

## What It Does

When **Export Limit** is set (in watts), the integration:

1. Monitors current grid export
2. Calculates "would-be-curtailed" power: `curtailed = export - export_limit`
3. Treats curtailed power as additional available excess for appliances
4. Activates appliances (starting from the highest priority) to absorb the curtailed power

This is particularly useful if your inverter curtails output at the export limit — you can instead direct that power into a hot water heater, battery, or EV charger.

---

## Configuration

Set the **Export Limit** in the global settings during initial setup, or update it in the integration options:

```
Export Limit: 5000 W   # Maximum watts allowed to export
```

Leave blank or set to 0 to disable export limiting.

---

## How It Interacts with the Optimizer

The `EXPORT_LIMIT` plan reason marks appliance decisions made specifically to absorb curtailed power. These decisions have lower priority than explicit schedule deadlines but higher priority than idle decisions.

The optimizer's Phase 2 (ALLOCATE) adds curtailed power to the excess pool, making it available to appliances just like solar excess.

---

## Example Scenario

System: 10 kW PV, 4 kW export limit, hot water heater (3 kW), pool pump (1 kW)

At 13:00 with 9 kW production and 2 kW load:
- Excess without export limit: 7 kW
- Export limit allows: 4 kW → curtailed: 3 kW
- Effective excess for appliances: 7 kW (3 kW curtailed + 4 kW would-be export available)
- Result: hot water heater ON (3 kW), pool pump ON (1 kW), still exporting 3 kW

---

## Regulatory Compliance

Export limiting is not a replacement for hardware-level curtailment if your grid operator requires it. The integration operates at the software/switch level and cannot guarantee hardware compliance. For regulatory requirements, ensure your inverter's built-in export limit is also configured.

---

## Common Issues

**Appliances activate even without excess**
If the export limit is set but the inverter is not actually curtailing, the optimizer may activate appliances based on the limit value alone. Verify your export sensor reflects real-time export power.

**Export limit not respected during peaks**
The integration can only switch appliances that are configured. If no appliances are available to absorb curtailed power (all already on, or none configured), curtailment will occur. Add more controllable loads if you frequently hit the cap.

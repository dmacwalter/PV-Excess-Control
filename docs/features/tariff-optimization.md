# Tariff Optimization

The tariff optimizer runs appliances during the cheapest electricity hours, even without solar — and factors in feed-in tariff revenue when deciding whether to export or self-consume.

---

## How It Works

The optimizer has two tariff-aware modes:

### 1. Opportunity Cost
When solar excess is available and multiple appliances compete for it, the optimizer factors in the **opportunity cost** of using power vs. exporting it:

```
net_savings_per_kwh = import_price - feed_in_tariff
```

If net savings are high (e.g. 0.30 import - 0.07 export = 0.23 €/kWh), the optimizer aggressively self-consumes. If the feed-in tariff is high relative to import prices, low-priority appliances may be skipped in favour of exporting.

### 2. Cheap Tariff Windows
When the current price is below the **Cheap Price Threshold**, the planner can schedule appliances using grid power. This is useful for:

- Overnight EV charging at off-peak rates
- Running the dishwasher or washing machine during cheap hours
- Pre-heating hot water before the morning peak

---

## Configuring Appliances for Cheap Windows

By default, appliances only run on solar excess. To allow grid-powered cheap-tariff runs, ensure the appliance has:

- A **Schedule Deadline** set (so the planner knows when it must be done)
- A **Min Daily Runtime** (so the planner knows how much runtime is needed)

The planner will then automatically schedule the appliance in the cheapest available window before the deadline.

---

## Tariff Providers

See [Energy Pricing](../configuration/energy-pricing.md) for setup instructions for each provider.

### Tibber Example

```
Tariff Provider: Tibber
Cheap Price Threshold: 0.10 €/kWh
Battery Charge Price Threshold: 0.08 €/kWh
Feed-In Tariff: 0.082 €/kWh
```

The integration uses Tibber's hourly prices to plan the next 24 hours.

### Nordpool Example

```
Tariff Provider: Nordpool
Cheap Price Threshold: 0.05 €/kWh
Feed-In Tariff: 0.05 €/kWh
```

---

## Planning Timeline

Every 15 minutes, the planner:

1. Fetches current and upcoming tariff prices (next 24 hours)
2. Identifies cheap windows (price ≤ cheap threshold)
3. For each appliance with a deadline:
   - Calculates remaining runtime needed
   - Finds the cheapest slots before the deadline
   - Schedules the appliance for those slots
4. For appliances without deadlines:
   - Marks cheap windows as "available for grid charging"
   - Real-time controller activates them when cheap hours are active

---

## Viewing the Plan

The dashboard card shows the planned schedule as a timeline. Each appliance entry shows:

- Planned on/off times
- Reason (solar excess, cheap tariff, deadline, etc.)
- Expected cost/saving for each run

---

## Common Issues

**Appliances run during expensive hours unexpectedly**
Check that the cheap price threshold is set correctly. If the threshold is too high (e.g. 0.25 when average price is 0.20), almost all hours qualify as "cheap" and the optimizer runs appliances freely.

**No cheap tariff scheduling happens**
The planner needs both a tariff provider and appliances with deadlines. Without deadlines, there is no constraint to schedule around.

**Feed-in tariff affects scheduling unexpectedly**
If your feed-in tariff is higher than expected (e.g. an old guaranteed rate), the optimizer may prefer to export rather than run low-priority appliances. This is correct behaviour. Adjust the feed-in tariff value if it has changed.

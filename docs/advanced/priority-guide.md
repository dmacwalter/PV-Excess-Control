# Priority Guide

Priority is the central mechanism for deciding which appliances run first when solar excess is limited.

---

## The Priority Scale

| Priority | Use for |
|----------|---------|
| 1–10 | Must-run: EV with deadline, medical devices, critical loads |
| 11–30 | High-value: EV without deadline, heat pump, hot water |
| 31–60 | Medium: dishwasher, washing machine, dryer |
| 61–100 | Low: pool pump, garden irrigation, secondary loads |
| 101–500 | Background: plug-in heaters, miscellaneous |
| 501–1000 | Lowest: anything that should only run with strong excess |

---

## How Priority Affects Decisions

### Allocation (turning on)
When excess power becomes available, the optimizer fills appliances from **lowest priority number** (highest priority) first:

1. EV Charger (priority 10) turns on and gets as many watts as it needs
2. Remaining excess goes to Heat Pump (priority 20)
3. Remaining excess goes to Dishwasher (priority 50)
4. And so on, until excess is exhausted

### Shedding (turning off)
When excess drops and appliances must be shed, the optimizer sheds from **highest priority number** (lowest priority) first:

1. Pool Pump (priority 100) is turned off first
2. If still insufficient, Dishwasher (priority 50) is turned off
3. And so on, preserving the highest-priority appliances

### Dynamic Current Adjustment
For EV chargers with dynamic current, current is reduced before shedding:

1. EV Charger current is reduced from 16 A → 12 A → 8 A → 6 A
2. If still insufficient at minimum current, the charger is turned off

---

## Real-World Example: House with EV, Heat Pump, Dishwasher, Pool

| Appliance | Priority | Power |
|-----------|----------|-------|
| EV Charger | 10 | up to 11 kW |
| Heat Pump | 20 | 2 kW |
| Dishwasher | 50 | 1.8 kW |
| Pool Pump | 100 | 0.8 kW |

**At 6 kW excess:**
- EV Charger: ON at ~6A (3-phase, consuming ~4 kW)
- Heat Pump: ON (2 kW)
- Dishwasher: OFF — not enough remaining excess
- Pool Pump: OFF

**At 9 kW excess:**
- EV Charger: ON at ~10A (consuming ~7 kW)
- Heat Pump: ON (2 kW)
- Dishwasher: OFF — just below threshold
- Pool Pump: OFF

**At 12 kW excess:**
- EV Charger: ON at ~14A (consuming ~10 kW)
- Heat Pump: ON (2 kW)
- Dishwasher: OFF (only 0 W remaining — use ON_THRESHOLD = 200 W)
- Pool Pump: OFF

**At 15 kW excess:**
- EV Charger: ON at 16A (11 kW max)
- Heat Pump: ON (2 kW)
- Dishwasher: ON (1.8 kW)
- Pool Pump: ON (0.8 kW)
- Still 0.4 kW exported

---

## Adjusting Priorities

Think of priority as answering: *"When excess is limited and I have to choose, which appliance matters most?"*

**EV should be higher priority than pool pump** — you need the car charged, but the pool can wait.

**Dishwasher may be higher priority than heat pump** — if the dishwasher runs in the morning during solar peak, it costs nothing. The heat pump is always on when needed regardless.

Avoid setting too many appliances to the same priority — it makes the allocation unpredictable. Spread priorities apart.

---

## Priority vs. Deadline

Priority governs real-time allocation. Deadlines govern planning:

- **High priority + no deadline**: Runs first with available excess, but no guarantee of runtime
- **Low priority + deadline**: May run overnight on cheap tariff to meet the deadline
- **High priority + deadline**: Gets the best of both — first choice of solar, plus guaranteed runtime

---

## Changing Priority

Update appliance priority through the integration options:

Settings → Devices & Services → PV Excess Control → Configure sub-entry → Change Priority

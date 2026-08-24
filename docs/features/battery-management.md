# Battery Management

PV Excess Control integrates with hybrid inverter systems to make battery-aware optimization decisions.

---

## Strategies

Three strategies control how the battery is treated relative to appliances:

### Battery First
The battery is charged to the target SoC before any appliances are turned on. Best for maximizing self-sufficiency -- the battery is always ready for the evening.

### Appliance First
Appliances run using solar excess before any power goes to the battery. Best for time-sensitive tasks (EV charging deadline, dishwasher cycle) where you want maximum runtime during solar hours.

### Balanced
Excess solar is split proportionally between battery charging and appliances. The split is calculated so that both reach their targets at the same time.

---

## Target SoC and Target Time

Set a **Target SoC** (e.g. 80 %) and **Target Time** (e.g. 07:00) to tell the planner when the battery needs to be ready.

The planner uses the forecast to calculate:
1. How much energy is needed to reach the target (`capacity x (target_soc - current_soc) / 100`)
2. Which hours have sufficient solar excess to charge
3. Whether grid charging is needed to meet the deadline

---

## Grid Charging

If **Allow Grid Charging** is enabled and the battery cannot reach its target using solar alone, the planner will schedule grid charging during the cheapest available hours before the deadline.

Example: EV and battery both need charging by 7 am. Cheapest grid hours are 01:00-04:00. The planner schedules battery charging from 02:00-04:00 to minimize cost.

Grid charging only activates when the tariff is below the **Battery Charge Price Threshold**.

### Shed Before Grid Charge

Per-appliance flag: **Shed Before Grid Charge**. When enabled, this appliance is always turned off before forced grid charge is allowed to engage — regardless of its own minimum daily runtime commitment.

Without this, forced grid charge could engage while a lower-priority appliance is still consuming the solar that would otherwise go toward the battery target, forcing more (and more expensive) grid import than necessary. Enable it on appliances you're happy to briefly interrupt in favour of hitting the battery's charge deadline (e.g. a pool pump), and leave it off for appliances with a hard runtime commitment you don't want grid charging to override.

### Battery Target Gated

Per-appliance flag: **Block Fast-Charge Preemption Once Battery Full**.

This is for appliances that command an inverter to charge directly (e.g. a "fast charge" switch) rather than being wattage-limited to actual solar excess. Normally, if shedding a lower-priority appliance frees up enough PV budget on paper, preemption switches this kind of appliance on — but because it isn't itself wattage-limited, it may then pull whatever it needs from the grid, not just the solar that was freed.

Enabling this flag blocks that preemption once the battery has already reached its target SoC, so a full battery won't trigger unnecessary grid import just because shedding something else freed up nominal capacity on paper. It also blocks the separate cheap-tariff grid-supplement paths for the same reason.

Leave this off for normal wattage-modulated appliances (pool pumps, standard EV chargers) — it's specifically for switches that aren't self-limiting.

---

## Battery Discharge Protection

Mark high-power appliances (heat pump, EV charger, tumble dryer) as **Big Consumer** to enable discharge protection.

When a big consumer is running and the battery SoC is below a safety threshold, the integration can limit the battery discharge rate. This prevents the battery from draining too fast and triggering grid import spikes.

Configure **Battery Discharge Override** per appliance (e.g. 500 W) to set the limit.

---

## Minimum Battery SoC Protection

The `min_battery_soc` threshold (configured in the battery settings) protects the battery from excessive discharge. When the battery SoC drops below this threshold, the optimizer will shed appliances to reduce load and prevent further battery drain.

This works in conjunction with Battery Discharge Protection: while discharge protection limits the discharge rate for big consumers, the min SoC threshold triggers active shedding of appliances when the battery level is critically low.

---

## Common Issues

**Battery charges during expensive hours**
Ensure the **Battery Charge Price Threshold** is set correctly and is lower than your normal import price.

**Battery never reaches target SoC**
Check that the battery capacity is set correctly and that the battery SoC sensor is reporting accurate values. Also verify the battery power sensor is positive when charging.

**Grid charging not activating**
"Allow Grid Charging" must be enabled. The tariff provider must be configured so the integration knows when prices are cheap.

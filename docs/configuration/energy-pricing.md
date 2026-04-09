# Energy Pricing

The tariff integration enables the optimizer to run appliances during cheap electricity windows and factor in feed-in tariff revenue when deciding whether to export or consume solar power.

---

## Supported Providers

| Provider | HA Integration Required |
|----------|------------------------|
| **None** | — Solar excess control only |
| **Tibber** | [Tibber integration](https://www.home-assistant.io/integrations/tibber/) |
| **Awattar** | [Awattar integration](https://github.com/mampfes/hacs_awattar) |
| **Nordpool** | [Nordpool integration](https://github.com/custom-components/nordpool) |
| **Octopus Energy** | [Octopus Energy integration](https://github.com/BottlecapDave/HomeAssistant-OctopusEnergy) |
| **Generic sensor** | Any sensor exposing a numeric price in your local currency per kWh |

---

## Configuration Fields

| Field | Description |
|-------|-------------|
| **Cheap Price Threshold** | Prices at or below this value trigger "cheap tariff" mode (e.g. `0.10` €/kWh) |
| **Battery Charge Price Threshold** | Prices at or below this value allow grid charging of the battery (e.g. `0.08` €/kWh) |
| **Feed-In Tariff** | Fixed revenue per kWh exported to grid (e.g. `0.07` €/kWh) |
| **Feed-In Tariff Sensor** | Alternative: a sensor that provides a dynamic feed-in tariff |

---

## How Tariff Data Is Used

### Cheap Tariff Charging
When the current price is below the **Cheap Price Threshold**, the optimizer can run appliances even without solar excess. This is useful for running the dishwasher or topping up the EV battery at off-peak rates overnight.

Each appliance can be configured to participate in cheap tariff windows or not.

### Opportunity Cost
The integration calculates the net value of using solar power vs. exporting it:

```
net_savings_per_kwh = current_import_price - feed_in_tariff
```

If `net_savings_per_kwh` is high (e.g. buying at 0.30, selling at 0.07 → 0.23 €/kWh savings), the optimizer aggressively self-consumes solar.

If feed-in tariff is high (e.g. guaranteed 0.20 €/kWh export), the optimizer may prefer to export over running low-priority appliances.

### Planning
The 24-hour planner uses future tariff windows to schedule appliances optimally:
- Identifies the cheapest hours for must-run tasks (EV charging deadline)
- Reserves solar excess hours for high-priority appliances
- Avoids running appliances during expensive peak periods

---

## Generic Sensor Setup

If you use a pricing API not in the list above, create a sensor in HA that exposes the current price:

```yaml
# configuration.yaml (example using a REST sensor)
sensor:
  - platform: rest
    name: "Electricity Price"
    resource: "https://api.yourprovider.com/current_price"
    value_template: "{{ value_json.price }}"
    unit_of_measurement: "EUR/kWh"
    scan_interval: 3600
```

Then select **Generic sensor** in the tariff provider step and point to `sensor.electricity_price`.

---

## Common Issues

**"Cheap" mode never activates**
Check that the threshold is set correctly and that the price sensor is returning numeric values. View the current price in Developer Tools → States.

**Appliances run during expensive hours**
By default, appliances only run on cheap tariff if explicitly configured. Check that the appliance has "Allow Grid Supplement" or "Cheap Tariff" options enabled.

**Feed-in tariff has no effect**
The feed-in tariff only influences the optimizer's decision-making when excess is available and multiple appliances compete for it. It does not block appliances from running.

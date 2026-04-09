# Dashboard Card Setup

PV Excess Control ships with a custom Lovelace card that provides a unified view of your solar system, appliance status, schedule, and savings.

---

## Installing the Card

### If installed via HACS
HACS registers the card resource automatically. After installing and restarting Home Assistant, the card should be available in the card picker.

### If installed manually
You need to register the card as a Lovelace resource:

1. Go to **Settings → Dashboards → Resources** (top-right three-dot menu)
2. Click **Add Resource**
3. URL: `/hacsfiles/pv_excess_control/pv-excess-card.js`
4. Type: **JavaScript Module**
5. Click **Create**
6. Refresh your browser (Ctrl+F5)

### Adding the card to a dashboard

1. Edit a Lovelace dashboard
2. Click **Add Card**
3. Scroll to the bottom under **Custom cards** and select **PV Excess Control**
4. The card auto-discovers all configured appliances

---

## Card Configuration

The card works with minimal configuration. The full YAML:

```yaml
type: custom:pv-excess-control-card
title: Solar Control           # optional header
show_forecast: true            # show forecast chart (default: true)
show_timeline: true            # show 24h plan timeline (default: true)
show_savings: true             # show savings summary (default: true)
show_appliances: true          # show appliance list (default: true)
appliance_order:               # optional: override display order
  - ev_charger
  - heat_pump
  - dishwasher
```

---

## Card Sections

### Power Flow
Real-time power flow visualization showing:
- Solar production (W)
- Grid import/export (W)
- Battery charge/discharge (W, hybrid only)
- Total household load (W)
- Net excess available (W)

### Appliance List
For each managed appliance:
- Current state (on/off)
- Current power draw (W)
- Runtime today
- Savings today
- Manual override toggle
- Current setting (for dynamic current appliances)

### 24-Hour Timeline
A visual schedule showing:
- Planned on/off windows for each appliance
- Solar forecast curve
- Tariff price overlay (cheap hours highlighted)
- Current time indicator

### Savings Summary
- Total savings today
- Self-consumption ratio
- Total solar produced today

---

## Manual Override

Each appliance in the card has a **Manual Override** toggle:

- **Override ON**: Forces the appliance on, regardless of optimizer decisions
- **Override OFF**: Forces the appliance off, regardless of optimizer decisions
- **Auto**: Returns control to the optimizer

Overrides are time-limited by default (the integration will return to auto after a configurable period). You can also set a permanent override from the appliance device page.

---

## Mobile Layout

The card is responsive and works on mobile. On narrow screens:
- Timeline is hidden by default (set `show_timeline: false` for mobile panels)
- Power flow shows a compact single-column layout

For a mobile-optimized view:

```yaml
type: custom:pv-excess-control-card
show_forecast: false
show_timeline: false
show_savings: true
show_appliances: true
```

---

## Common Issues

**Card shows "Custom element doesn't exist"**
The card resource is not registered. If installed via HACS, try restarting HA and clearing your browser cache. If installed manually, add the resource as described in the "Installing the Card" section above.

**Card displays but appliances are missing**
Ensure appliances have been added as sub-entries. Go to Settings → Devices & Services → PV Excess Control and check for listed sub-entries.

**Timeline is empty**
The timeline requires a forecast provider to be configured. Without forecast data, the timeline shows only current state.

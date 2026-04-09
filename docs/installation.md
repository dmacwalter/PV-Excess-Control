# Installation

## Requirements

- Home Assistant **2025.8** or newer
- A solar inverter with at least one power sensor in Home Assistant (PV production or grid power)
- [HACS](https://hacs.xyz/) for the recommended installation path

---

## Install via HACS (Recommended)

1. In your Home Assistant sidebar, open **HACS**.
2. Click the three-dot overflow menu (top right) and choose **Custom repositories**.
3. Paste `https://github.com/InventoCasa/PV-Excess-Control` and set the category to **Integration**, then click **Add**.
4. In the HACS integration list, search for **PV Excess Control** and click **Download**.
5. When prompted, choose the latest version and confirm.
6. **Restart Home Assistant** (Developer Tools → Restart, or via Settings → System → Restart).
7. After the restart, go to **Settings → Devices & Services → Add Integration**, search for **PV Excess Control**, and follow the setup wizard.

---

## Manual Installation

1. Download the latest release ZIP from the [GitHub releases page](https://github.com/InventoCasa/PV-Excess-Control/releases).
2. Extract the archive and copy the `custom_components/pv_excess_control` folder into your Home Assistant `config/custom_components/` directory.

   Your directory structure should look like:
   ```
   config/
   └── custom_components/
       └── pv_excess_control/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```

3. **Restart Home Assistant**.
4. Go to **Settings → Devices & Services → Add Integration**, search for **PV Excess Control**, and follow the setup wizard.

---

## After Installation

The setup wizard walks you through six steps:

1. **Inverter type** — Standard (no battery) or Hybrid (with battery)
2. **Sensor mapping** — Map your inverter's power sensors
3. **Energy pricing** — Choose a tariff provider (optional)
4. **Solar forecast** — Choose a forecast provider (optional)
5. **Battery strategy** — Only shown for Hybrid inverters
6. **Global settings** — Export limit, poll intervals, notification service

After the main integration is set up, add each appliance you want to control via the sub-device UI (click **Add sub-entry** on the integration card).

See [Initial Setup](configuration/initial-setup.md) for a step-by-step walkthrough of the wizard.

---

## Updating

### Via HACS
HACS will notify you when a new version is available. Click **Update** and restart Home Assistant.

### Manual
Overwrite the `custom_components/pv_excess_control` folder with the new version, then restart Home Assistant.

---

## Common Issues

**Integration not found after install**
Make sure Home Assistant was fully restarted (not just reloaded). Check `home-assistant.log` for import errors.

**"Integration is not compatible" error**
Verify that your Home Assistant version is 2025.8 or newer (Settings → About).

**Config flow fails at sensor mapping**
The sensors must already exist in Home Assistant before running the wizard. Check that your inverter integration is loaded and the entities are visible in Developer Tools → States.

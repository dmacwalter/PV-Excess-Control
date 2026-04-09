"""Select platform for PV Excess Control."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BatteryStrategy, CONF_BATTERY_STRATEGY, DOMAIN, MANUFACTURER
from .coordinator import PvExcessCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PV Excess Control select entities."""
    coordinator: PvExcessCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SelectEntity] = [
        BatteryStrategySelect(coordinator),
    ]

    async_add_entities(entities)


class BatteryStrategySelect(CoordinatorEntity[PvExcessCoordinator], SelectEntity):
    """Select entity for battery charging strategy."""

    _attr_has_entity_name = True
    _attr_name = "Battery Strategy"
    _attr_icon = "mdi:battery-sync"
    _attr_options = ["battery_first", "appliance_first", "balanced"]

    def __init__(self, coordinator: PvExcessCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_battery_strategy"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            name="PV Excess Control",
            manufacturer=MANUFACTURER,
        )

    @property
    def current_option(self) -> str:
        val = self.coordinator.battery_strategy
        if val not in self._attr_options:
            return self._attr_options[-1]  # default to "balanced"
        return val

    async def async_select_option(self, option: str) -> None:
        self.coordinator.battery_strategy = option
        try:
            new_data = dict(self.coordinator.config_entry.data)
            new_data[CONF_BATTERY_STRATEGY] = option
            self.hass.config_entries.async_update_entry(
                self.coordinator.config_entry, data=new_data
            )
        except Exception as err:
            _LOGGER.warning("Could not persist battery strategy change: %s", err)
        self.async_write_ha_state()

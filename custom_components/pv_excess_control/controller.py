"""Controller for PV Excess Control.

Bridges Home Assistant state with the optimizer:
- Collects sensor states and builds PowerState
- Collects appliance states from HA entities
- Applies ControlDecisions by calling HA services
- Handles safety checks (switch interval, on_only)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .const import (
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_GRID_EXPORT,
    CONF_IMPORT_EXPORT,
    CONF_LOAD_POWER,
    CONF_PV_POWER,
)
from .models import (
    Action,
    ApplianceConfig,
    ApplianceState,
    BatteryDischargeAction,
    ControlDecision,
    PowerState,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_UNAVAILABLE_STATES = {"unavailable", "unknown", "none", ""}

# Multipliers to normalise power values to watts.
_POWER_UNIT_MULTIPLIERS: dict[str, float] = {
    "w": 1.0,
    "kw": 1000.0,
    "mw": 1_000_000.0,
}


def _normalise_power(value: float, unit: str | None) -> float:
    """Convert a power reading to watts based on its unit_of_measurement."""
    if unit is None:
        return value
    return value * _POWER_UNIT_MULTIPLIERS.get(unit.lower().strip(), 1.0)


class Controller:
    """Bridges Home Assistant state with the optimizer."""

    def __init__(self, hass: HomeAssistant, config_data: dict) -> None:
        self.hass = hass
        self.config_data = config_data
        self._last_state_change: dict[str, datetime] = {}  # appliance_id -> last change time

    # ------------------------------------------------------------------
    # Sensor reading helpers
    # ------------------------------------------------------------------

    def _read_sensor(
        self, entity_id: str | None, default: float = 0.0, *, power: bool = False,
    ) -> float:
        """Read a numeric sensor value, returning default if unavailable.

        When *power* is True the value is normalised to watts using the
        sensor's ``unit_of_measurement`` attribute (kW → W, MW → W).
        """
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _UNAVAILABLE_STATES:
            return default
        try:
            val = float(state.state)
        except (ValueError, TypeError):
            return default
        if power:
            val = _normalise_power(val, state.attributes.get("unit_of_measurement"))
        return val

    def _read_sensor_optional(
        self, entity_id: str | None, *, power: bool = False,
    ) -> float | None:
        """Read a numeric sensor value, returning None if unavailable.

        When *power* is True the value is normalised to watts using the
        sensor's ``unit_of_measurement`` attribute (kW → W, MW → W).
        """
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _UNAVAILABLE_STATES:
            return None
        try:
            val = float(state.state)
        except (ValueError, TypeError):
            return None
        if power:
            val = _normalise_power(val, state.attributes.get("unit_of_measurement"))
        return val

    def _read_binary(self, entity_id: str | None) -> bool | None:
        """Read a binary sensor, returns True/False/None."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            return None
        return state.state == "on"

    # ------------------------------------------------------------------
    # Power state collection
    # ------------------------------------------------------------------

    def collect_power_state(self) -> PowerState:
        """Read sensor entities and build PowerState."""
        data = self.config_data

        pv_production = self._read_sensor(data.get(CONF_PV_POWER), power=True)

        # Grid export/import: either separate entity or combined
        grid_export = 0.0
        grid_import = 0.0
        import_export_entity = data.get(CONF_IMPORT_EXPORT)
        grid_export_entity = data.get(CONF_GRID_EXPORT)

        if import_export_entity:
            # Combined sensor: positive = export, negative = import
            combined = self._read_sensor(import_export_entity, power=True)
            grid_export = max(combined, 0.0)
            grid_import = abs(min(combined, 0.0))
        elif grid_export_entity:
            grid_export = self._read_sensor(grid_export_entity, power=True)

        load_power = self._read_sensor(data.get(CONF_LOAD_POWER), power=True)

        battery_soc = self._read_sensor_optional(data.get(CONF_BATTERY_SOC))
        battery_power = self._read_sensor_optional(
            data.get(CONF_BATTERY_POWER), power=True,
        )

        # Calculate excess: PV production minus load; if no load sensor, use grid export
        if load_power > 0:
            excess_power = pv_production - load_power
        else:
            excess_power = grid_export - grid_import

        return PowerState(
            pv_production=pv_production,
            grid_export=grid_export,
            grid_import=grid_import,
            load_power=load_power,
            excess_power=excess_power,
            battery_soc=battery_soc,
            battery_power=battery_power,
            ev_soc=None,
            timestamp=datetime.now(),
        )

    # ------------------------------------------------------------------
    # Appliance state collection
    # ------------------------------------------------------------------

    def collect_appliance_states(
        self,
        appliance_configs: list[ApplianceConfig],
        runtime_tracker: dict[str, timedelta],
    ) -> list[ApplianceState]:
        """Read current state of each managed appliance."""
        states: list[ApplianceState] = []

        for config in appliance_configs:
            entity_state = self.hass.states.get(config.entity_id)
            is_on = False
            if entity_state is not None:
                is_on = entity_state.state in ("on", "true", "True", "1")

            # Read actual power if available
            current_power = 0.0
            if config.actual_power_entity:
                current_power = self._read_sensor(
                    config.actual_power_entity, power=True,
                )

            # Read current amperage if available
            current_amperage: float | None = None
            if config.current_entity:
                current_amperage = self._read_sensor_optional(config.current_entity)

            # EV connected status
            ev_connected: bool | None = None
            if config.ev_connected_entity:
                ev_connected = self._read_binary(config.ev_connected_entity)

            # Runtime from tracker
            runtime_today = runtime_tracker.get(config.id, timedelta())

            state = ApplianceState(
                appliance_id=config.id,
                is_on=is_on,
                current_power=current_power,
                current_amperage=current_amperage,
                runtime_today=runtime_today,
                energy_today=0.0,
                last_state_change=None,
                ev_connected=ev_connected,
            )
            states.append(state)

        return states

    # ------------------------------------------------------------------
    # Apply decisions
    # ------------------------------------------------------------------

    async def apply_decisions(
        self,
        decisions: list[ControlDecision],
        appliance_configs: list[ApplianceConfig],
    ) -> list[dict]:
        """Apply control decisions by calling HA services."""
        applied: list[dict] = []

        for decision in decisions:
            if decision.action == Action.IDLE:
                continue

            config = self._find_config(decision.appliance_id, appliance_configs)
            if not config:
                continue

            # Check switch interval
            if not self._can_change_state(config):
                last = self._last_state_change.get(config.id)
                elapsed = (datetime.now() - last).total_seconds() if last else 0
                remaining = max(config.switch_interval - elapsed, 0)
                _LOGGER.debug(
                    "Skip %s: switch interval (%ds remaining)",
                    config.name, int(remaining),
                )
                continue

            # Check if state actually needs to change
            current_state = self.hass.states.get(config.entity_id)
            if not self._needs_change(decision, current_state, config):
                entity_state = getattr(current_state, "state", None) if current_state else None
                is_on = entity_state in ("on", "true", "True", "1") if entity_state else False
                _LOGGER.debug(
                    "Skip %s: already %s",
                    config.name, "on" if is_on else "off",
                )
                continue

            # Apply the decision
            entity_id = config.entity_id
            domain = entity_id.split(".")[0] if "." in entity_id else "switch"
            _LOGGER.info(
                "Calling %s.%s for %s (%s)",
                domain,
                "turn_on" if decision.action == Action.ON else (
                    "turn_off" if decision.action == Action.OFF else "set_value"
                ),
                config.name,
                entity_id,
            )
            await self._apply_single(decision, config)
            self._last_state_change[config.id] = datetime.now()
            applied.append({"appliance_id": config.id, "action": decision.action})

            # Fire event
            self.hass.bus.async_fire(
                "pv_excess_control.appliance_switched",
                {
                    "appliance_id": config.id,
                    "appliance_name": config.name,
                    "action": decision.action,
                    "reason": decision.reason,
                },
            )

        return applied

    async def apply_battery_discharge_limit(
        self,
        action: BatteryDischargeAction,
        max_discharge_entity: str | None,
        max_discharge_default: float | None,
    ) -> None:
        """Set or restore battery discharge limit."""
        if not max_discharge_entity:
            return

        if action.should_limit and action.max_discharge_watts is not None:
            _LOGGER.debug(
                "Battery discharge limit: %s -> %.0fW",
                max_discharge_entity, action.max_discharge_watts,
            )
            await self.hass.services.async_call(
                "number",
                "set_value",
                {
                    "entity_id": max_discharge_entity,
                    "value": action.max_discharge_watts,
                },
            )
        elif max_discharge_default is not None:
            _LOGGER.debug(
                "Battery discharge limit: %s -> %.0fW (restoring default)",
                max_discharge_entity, max_discharge_default,
            )
            await self.hass.services.async_call(
                "number",
                "set_value",
                {
                    "entity_id": max_discharge_entity,
                    "value": max_discharge_default,
                },
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_config(
        self, appliance_id: str, configs: list[ApplianceConfig]
    ) -> ApplianceConfig | None:
        """Find an appliance config by its ID."""
        for config in configs:
            if config.id == appliance_id:
                return config
        return None

    def _can_change_state(self, config: ApplianceConfig) -> bool:
        """Check if enough time has passed since last state change."""
        last = self._last_state_change.get(config.id)
        if last is None:
            return True
        elapsed = (datetime.now() - last).total_seconds()
        return elapsed >= config.switch_interval

    def _needs_change(
        self,
        decision: ControlDecision,
        current_state: object | None,
        config: ApplianceConfig,
    ) -> bool:
        """Check if the decision would actually change the appliance state."""
        if current_state is None:
            # Entity not found - allow the change attempt
            return True

        entity_state = getattr(current_state, "state", None)

        if decision.action == Action.ON:
            # Already on - no change needed
            if entity_state in ("on", "true", "True", "1"):
                return False
        elif decision.action == Action.OFF:
            # Already off - no change needed
            if entity_state in ("off", "false", "False", "0"):
                return False
            # on_only prevents turning off
            if config.on_only:
                return False
        elif decision.action == Action.SET_CURRENT:
            # Dynamic current - always apply (target value may have changed)
            return True

        return True

    async def _apply_single(
        self, decision: ControlDecision, config: ApplianceConfig
    ) -> None:
        """Apply a single decision to an appliance."""
        entity_id = config.entity_id
        domain = entity_id.split(".")[0]

        if decision.action == Action.ON:
            await self._turn_on(domain, entity_id)
        elif decision.action == Action.OFF:
            # Respect on_only flag (double safety check)
            if config.on_only:
                return
            await self._turn_off(domain, entity_id)
        elif decision.action == Action.SET_CURRENT:
            if config.current_entity and decision.target_current is not None:
                current_domain = config.current_entity.split(".")[0]
                await self.hass.services.async_call(
                    current_domain,
                    "set_value",
                    {
                        "entity_id": config.current_entity,
                        "value": decision.target_current,
                    },
                )

    async def _turn_on(self, domain: str, entity_id: str) -> None:
        """Turn on an entity based on its domain."""
        service_map = {
            "switch": ("switch", "turn_on"),
            "climate": ("climate", "turn_on"),
            "light": ("light", "turn_on"),
            "water_heater": ("water_heater", "turn_on"),
            "input_boolean": ("input_boolean", "turn_on"),
        }
        if domain in service_map:
            svc_domain, svc_name = service_map[domain]
            await self.hass.services.async_call(
                svc_domain, svc_name, {"entity_id": entity_id}
            )

    async def _turn_off(self, domain: str, entity_id: str) -> None:
        """Turn off an entity based on its domain."""
        service_map = {
            "switch": ("switch", "turn_off"),
            "climate": ("climate", "turn_off"),
            "light": ("light", "turn_off"),
            "water_heater": ("water_heater", "turn_off"),
            "input_boolean": ("input_boolean", "turn_off"),
        }
        if domain in service_map:
            svc_domain, svc_name = service_map[domain]
            await self.hass.services.async_call(
                svc_domain, svc_name, {"entity_id": entity_id}
            )

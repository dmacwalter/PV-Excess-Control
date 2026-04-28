"""Generic inverter forced grid-charge controller.

Drives an inverter's forced grid-charge behaviour via Home Assistant
entities. Supports single-switch, two-step (mode + command) and
three-step (mode + command + power) inverter protocols. Inverter-agnostic.

Engage order: mode → power → command.
Disengage order: command → mode (power entity is left untouched to
preserve a user-set value).
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .models import InverterGridChargeConfig

_LOGGER = logging.getLogger(__name__)

SUPPORTED_ENABLE_DOMAINS = frozenset({"input_select", "select", "switch", "input_boolean"})
SUPPORTED_POWER_DOMAINS = frozenset({"input_number", "number"})

_TRUTHY_STRINGS = frozenset({"on", "true", "1", "yes"})


class InverterGridChargeController:
    """Drives an inverter's forced grid-charge entities."""

    def __init__(self, hass: HomeAssistant, config: InverterGridChargeConfig) -> None:
        self._hass = hass
        self._config = config
        self._validate_domains()

    def _validate_domains(self) -> None:
        enable_domain = self._domain(self._config.enable_entity_id)
        if enable_domain not in SUPPORTED_ENABLE_DOMAINS:
            raise ValueError(
                f"enable_entity '{self._config.enable_entity_id}' has unsupported domain '{enable_domain}'. "
                f"Supported domains: {sorted(SUPPORTED_ENABLE_DOMAINS)}"
            )
        if self._config.mode_entity_id is not None:
            mode_domain = self._domain(self._config.mode_entity_id)
            if mode_domain not in SUPPORTED_ENABLE_DOMAINS:
                raise ValueError(
                    f"mode_entity '{self._config.mode_entity_id}' has unsupported domain '{mode_domain}'."
                )
        if self._config.power_entity_id is not None:
            power_domain = self._domain(self._config.power_entity_id)
            if power_domain not in SUPPORTED_POWER_DOMAINS:
                raise ValueError(
                    f"power_entity '{self._config.power_entity_id}' has unsupported domain '{power_domain}'."
                )

    async def engage(self, power_w: float) -> None:
        """Command the inverter into forced grid-charge."""
        if self._config.mode_entity_id is not None:
            await self._write(self._config.mode_entity_id, self._config.mode_engage_value)
        if self._config.power_entity_id is not None:
            await self._write(self._config.power_entity_id, float(power_w))
        await self._write(self._config.enable_entity_id, self._config.enable_engage_value)

    async def disengage(self) -> None:
        """Revert to self-consumption / stop forced charge."""
        await self._write(self._config.enable_entity_id, self._config.enable_disengage_value)
        if self._config.mode_entity_id is not None:
            await self._write(self._config.mode_entity_id, self._config.mode_disengage_value)
        # Intentionally do not touch power_entity on disengage.

    async def _write(self, entity_id: str, value) -> None:
        domain = self._domain(entity_id)
        if domain in {"input_select", "select"}:
            await self._hass.services.async_call(
                domain, "select_option",
                {"entity_id": entity_id, "option": str(value)},
                blocking=False,
            )
        elif domain in {"input_number", "number"}:
            await self._hass.services.async_call(
                domain, "set_value",
                {"entity_id": entity_id, "value": float(value)},
                blocking=False,
            )
        elif domain in {"switch", "input_boolean"}:
            service = "turn_on" if str(value).strip().lower() in _TRUTHY_STRINGS else "turn_off"
            await self._hass.services.async_call(
                domain, service,
                {"entity_id": entity_id},
                blocking=False,
            )
        else:
            raise ValueError(f"Unsupported entity domain for inverter grid charge: {domain}")

    @staticmethod
    def _domain(entity_id: str) -> str:
        return entity_id.split(".", 1)[0]

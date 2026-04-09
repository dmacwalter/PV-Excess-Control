"""Sensor combiner helpers for multi-inverter/battery setups."""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


class SensorCombiner:
    """Combines multiple sensor values into one."""

    @staticmethod
    def sum_values(
        values: list[float | None],
        labels: list[str] | None = None,
    ) -> float:
        """Sum multiple sensor values. Skips None values with warning."""
        total = 0.0
        for i, val in enumerate(values):
            if val is None:
                label = labels[i] if labels and i < len(labels) else f"sensor_{i}"
                _LOGGER.warning("Sensor %s unavailable, skipping in sum", label)
                continue
            total += val
        return total

    @staticmethod
    def weighted_average(
        values: list[float | None],
        weights: list[float],
        labels: list[str] | None = None,
    ) -> float:
        """Weighted average. For combining battery SoC with different capacities."""
        if len(values) != len(weights):
            raise ValueError("values and weights must have same length")
        total_weight = 0.0
        weighted_sum = 0.0
        for i, (val, weight) in enumerate(zip(values, weights)):
            if val is None:
                label = labels[i] if labels and i < len(labels) else f"sensor_{i}"
                _LOGGER.warning("Sensor %s unavailable, skipping in average", label)
                continue
            weighted_sum += val * weight
            total_weight += weight
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight


def read_multiple_sensors(
    hass,
    entity_ids: list[str],
) -> tuple[list[float | None], list[str]]:
    """Read multiple sensor values from HA. Returns (values, labels)."""
    values: list[float | None] = []
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", "none", ""):
            values.append(None)
        else:
            try:
                values.append(float(state.state))
            except (ValueError, TypeError):
                values.append(None)
    return values, entity_ids

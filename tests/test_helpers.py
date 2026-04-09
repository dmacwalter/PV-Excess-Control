"""Tests for sensor combiner helpers (Task 18)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.pv_excess_control.helpers import (
    SensorCombiner,
    read_multiple_sensors,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass(states: dict[str, str | None]) -> MagicMock:
    """Build a minimal mock hass whose states.get() returns stub state objects."""
    hass = MagicMock()

    def _get(entity_id):
        if entity_id not in states:
            return None
        state_val = states[entity_id]
        mock_state = MagicMock()
        mock_state.state = state_val if state_val is not None else "unknown"
        return mock_state

    hass.states.get.side_effect = _get
    return hass


# ---------------------------------------------------------------------------
# TestSumCombiner
# ---------------------------------------------------------------------------

class TestSumCombiner:
    def test_sum_all_values(self):
        """Sum of [1000, 2000, 3000] = 6000."""
        assert SensorCombiner.sum_values([1000.0, 2000.0, 3000.0]) == 6000.0

    def test_sum_with_none_skipped(self):
        """None values are skipped: [1000, None, 3000] = 4000."""
        assert SensorCombiner.sum_values([1000.0, None, 3000.0]) == 4000.0

    def test_sum_all_none(self):
        """All None = 0."""
        assert SensorCombiner.sum_values([None, None]) == 0.0

    def test_sum_empty(self):
        """Empty list = 0."""
        assert SensorCombiner.sum_values([]) == 0.0

    def test_sum_single(self):
        """Single value = that value."""
        assert SensorCombiner.sum_values([42.0]) == 42.0

    def test_sum_with_labels(self):
        """Labels are accepted without error."""
        result = SensorCombiner.sum_values(
            [500.0, None, 1500.0],
            labels=["inv1", "inv2", "inv3"],
        )
        assert result == 2000.0

    def test_sum_negative_values(self):
        """Negative values (e.g. export power) sum correctly."""
        assert SensorCombiner.sum_values([-500.0, -300.0]) == pytest.approx(-800.0)


# ---------------------------------------------------------------------------
# TestWeightedAverage
# ---------------------------------------------------------------------------

class TestWeightedAverage:
    def test_weighted_average_batteries(self):
        """Weighted average for two batteries: 80% at 5kWh + 60% at 10kWh."""
        result = SensorCombiner.weighted_average([80.0, 60.0], [5.0, 10.0])
        # (80*5 + 60*10) / (5+10) = (400+600)/15 = 66.67
        assert abs(result - 66.67) < 0.01

    def test_weighted_average_with_none(self):
        """None values excluded from average."""
        result = SensorCombiner.weighted_average([80.0, None], [5.0, 10.0])
        # Only first sensor: 80.0
        assert result == 80.0

    def test_weighted_average_all_none(self):
        """All None = 0."""
        assert SensorCombiner.weighted_average([None, None], [5.0, 10.0]) == 0.0

    def test_weighted_average_equal_weights(self):
        """Equal weights = simple average."""
        result = SensorCombiner.weighted_average([80.0, 60.0], [1.0, 1.0])
        assert result == 70.0

    def test_mismatched_lengths_raises(self):
        """Mismatched values/weights raises ValueError."""
        with pytest.raises(ValueError):
            SensorCombiner.weighted_average([80.0], [5.0, 10.0])

    def test_weighted_average_with_labels(self):
        """Labels are accepted and used in warnings without error."""
        result = SensorCombiner.weighted_average(
            [90.0, None, 50.0],
            [10.0, 5.0, 10.0],
            labels=["bat_a", "bat_b", "bat_c"],
        )
        # (90*10 + 50*10) / (10+10) = 1400/20 = 70.0
        assert result == pytest.approx(70.0)

    def test_zero_weight_sensor_excluded(self):
        """A sensor with weight 0 contributes nothing to the average."""
        result = SensorCombiner.weighted_average([100.0, 50.0], [0.0, 10.0])
        assert result == pytest.approx(50.0)

    def test_single_sensor(self):
        """Single sensor returns its own value."""
        result = SensorCombiner.weighted_average([75.0], [8.0])
        assert result == pytest.approx(75.0)


# ---------------------------------------------------------------------------
# TestReadMultipleSensors
# ---------------------------------------------------------------------------

class TestReadMultipleSensors:
    def test_reads_values(self):
        """Reads float values from mock HA states."""
        hass = _make_hass({
            "sensor.inv1_power": "1500.5",
            "sensor.inv2_power": "2000.0",
        })
        values, labels = read_multiple_sensors(
            hass,
            ["sensor.inv1_power", "sensor.inv2_power"],
        )
        assert values == [pytest.approx(1500.5), pytest.approx(2000.0)]
        assert labels == ["sensor.inv1_power", "sensor.inv2_power"]

    def test_unavailable_returns_none(self):
        """Unavailable sensors return None."""
        hass = _make_hass({
            "sensor.inv1_power": "unavailable",
            "sensor.inv2_power": "1000.0",
        })
        values, labels = read_multiple_sensors(
            hass,
            ["sensor.inv1_power", "sensor.inv2_power"],
        )
        assert values[0] is None
        assert values[1] == pytest.approx(1000.0)

    def test_unknown_state_returns_none(self):
        """'unknown' sensor state returns None."""
        hass = _make_hass({"sensor.bat_soc": "unknown"})
        values, _ = read_multiple_sensors(hass, ["sensor.bat_soc"])
        assert values[0] is None

    def test_missing_entity_returns_none(self):
        """Entity not found in HA states returns None."""
        hass = _make_hass({})
        values, _ = read_multiple_sensors(hass, ["sensor.nonexistent"])
        assert values[0] is None

    def test_non_numeric_state_returns_none(self):
        """Non-numeric state string returns None instead of raising."""
        hass = _make_hass({"sensor.bad": "not_a_number"})
        values, _ = read_multiple_sensors(hass, ["sensor.bad"])
        assert values[0] is None

    def test_empty_entity_list(self):
        """Empty entity list returns empty values and labels."""
        hass = _make_hass({})
        values, labels = read_multiple_sensors(hass, [])
        assert values == []
        assert labels == []

    def test_labels_are_entity_ids(self):
        """Labels returned are the original entity IDs."""
        hass = _make_hass({"sensor.a": "100.0"})
        _, labels = read_multiple_sensors(hass, ["sensor.a"])
        assert labels == ["sensor.a"]

    def test_integration_sum_of_read_sensors(self):
        """read_multiple_sensors output can be fed directly into sum_values."""
        hass = _make_hass({
            "sensor.inv1": "1000.0",
            "sensor.inv2": "unavailable",
            "sensor.inv3": "2000.0",
        })
        values, labels = read_multiple_sensors(
            hass,
            ["sensor.inv1", "sensor.inv2", "sensor.inv3"],
        )
        total = SensorCombiner.sum_values(values, labels)
        assert total == pytest.approx(3000.0)

"""Forecast provider abstraction for PV Excess Control.

Supports Solcast, Forecast.Solar, and generic sensor providers.
Designed to be HA-agnostic: accepts raw state dicts, not HA objects.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from .models import ForecastData, HourlyForecast

_LOGGER = logging.getLogger(__name__)


def _parse_float(value: Any) -> float | None:
    """Parse a value to float, returning None on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_float(state: str) -> float:
    """Parse a sensor state string to float, returning 0.0 if not possible."""
    result = _parse_float(state)
    return result if result is not None else 0.0


class ForecastProvider(ABC):
    """Base class for forecast providers."""

    @abstractmethod
    def get_forecast(
        self,
        states: dict[str, dict],  # entity_id -> {"state": value, "attributes": {}}
    ) -> ForecastData:
        """Extract forecast data from HA entity states."""


class GenericForecastProvider(ForecastProvider):
    """Reads remaining daily kWh from any sensor. No hourly breakdown."""

    def __init__(self, forecast_entity: str) -> None:
        self.forecast_entity = forecast_entity

    def get_forecast(self, states: dict[str, dict]) -> ForecastData:
        entity_state = states.get(self.forecast_entity)
        if entity_state is None:
            _LOGGER.warning("ForecastProvider: entity %s state is unavailable/unknown", self.forecast_entity)
            return ForecastData(remaining_today_kwh=0.0)

        raw_state = entity_state.get("state", "unavailable")
        remaining = _safe_float(raw_state)
        _LOGGER.debug(
            "GenericForecast: entity=%s raw_state=%s -> remaining=%.2f kWh",
            self.forecast_entity, raw_state, remaining,
        )
        return ForecastData(remaining_today_kwh=remaining)


class SolcastProvider(ForecastProvider):
    """Reads Solcast forecast data.

    Solcast attributes contain a ``forecasts`` list of 30-minute slots:
        [{"period_start": "<iso>", "pv_estimate": <kW>}, ...]

    Slots are grouped by calendar hour and merged into HourlyForecast entries.
    Optionally reads ``forecast_tomorrow`` total kWh.
    """

    def __init__(self, forecast_entity: str) -> None:
        self.forecast_entity = forecast_entity

    def get_forecast(self, states: dict[str, dict]) -> ForecastData:
        entity_state = states.get(self.forecast_entity)
        if entity_state is None:
            _LOGGER.warning("ForecastProvider: entity %s state is unavailable/unknown", self.forecast_entity)
            return ForecastData(remaining_today_kwh=0.0)

        state_val = entity_state.get("state", "unavailable")
        remaining = _safe_float(state_val)

        attributes: dict = entity_state.get("attributes", {})
        # Solcast exposes forecast data under different attribute names
        # depending on the integration version: "forecasts", "detailedForecast",
        # or "detailedHourly". Try each in order of preference.
        forecasts_raw: list[dict] | None = (
            attributes.get("forecasts")
            or attributes.get("detailedForecast")
            or attributes.get("detailedHourly")
        )
        if not forecasts_raw:
            _LOGGER.debug(
                "Solcast: no forecast attribute found (tried forecasts, detailedForecast, detailedHourly), available keys: %s",
                list(attributes.keys()),
            )
        tomorrow_raw = attributes.get("forecast_tomorrow")
        try:
            tomorrow_kwh: float | None = float(tomorrow_raw) if tomorrow_raw is not None else None
        except (ValueError, TypeError):
            _LOGGER.warning("Solcast: forecast_tomorrow not numeric: %r", tomorrow_raw)
            tomorrow_kwh = None

        hourly_breakdown = self._parse_forecasts(forecasts_raw or [])

        _LOGGER.debug(
            "Solcast: entity=%s remaining=%.2f kWh hourly_slots=%d tomorrow=%.2f kWh",
            self.forecast_entity, remaining, len(hourly_breakdown), tomorrow_kwh or 0,
        )
        return ForecastData(
            remaining_today_kwh=remaining,
            hourly_breakdown=hourly_breakdown,
            tomorrow_total_kwh=tomorrow_kwh if tomorrow_kwh is not None else None,
        )

    def _parse_forecasts(self, forecasts_raw: list[dict]) -> list[HourlyForecast]:
        """Merge 30-min Solcast slots into per-hour HourlyForecast entries."""
        if not forecasts_raw:
            return []

        # Group slots by (date, hour) - accumulate kWh contributions
        # Each slot covers 30 minutes: kWh = kW * 0.5
        hour_kwh: dict[tuple, float] = {}
        hour_kw_sum: dict[tuple, float] = {}
        hour_count: dict[tuple, int] = {}
        hour_start: dict[tuple, datetime] = {}

        for slot in forecasts_raw:
            period_start_raw = slot.get("period_start")
            pv_estimate_kw = slot.get("pv_estimate", 0.0)

            if period_start_raw is None:
                continue

            dt = _parse_iso(period_start_raw)
            if dt is None:
                continue

            # Truncate to the calendar hour
            hour_key = (dt.year, dt.month, dt.day, dt.hour,
                        dt.tzinfo.utcoffset(dt) if dt.tzinfo else None)
            hour_dt = dt.replace(minute=0, second=0, microsecond=0)

            if hour_key not in hour_start:
                hour_start[hour_key] = hour_dt
                hour_kwh[hour_key] = 0.0
                hour_kw_sum[hour_key] = 0.0
                hour_count[hour_key] = 0

            # 30-min slot: kWh = kW * 0.5
            hour_kwh[hour_key] += pv_estimate_kw * 0.5
            hour_kw_sum[hour_key] += pv_estimate_kw
            hour_count[hour_key] += 1

        result: list[HourlyForecast] = []
        for hour_key in sorted(hour_start.keys(), key=lambda k: hour_start[k]):
            start_dt = hour_start[hour_key]
            end_dt = start_dt + timedelta(hours=1)
            kwh = hour_kwh[hour_key]
            # Average watts = average kW * 1000
            avg_kw = hour_kw_sum[hour_key] / hour_count[hour_key]
            result.append(HourlyForecast(
                start=start_dt,
                end=end_dt,
                expected_kwh=kwh,
                expected_watts=avg_kw * 1000.0,
            ))

        return result


class ForecastSolarProvider(ForecastProvider):
    """Reads Forecast.Solar data.

    Forecast.Solar attributes contain a ``watts`` dict:
        {"<iso_timestamp>": <watts>, ...}

    Each entry represents an hour.  The timestamp is the start of the hour.
    """

    def __init__(self, forecast_entity: str) -> None:
        self.forecast_entity = forecast_entity

    def get_forecast(self, states: dict[str, dict]) -> ForecastData:
        entity_state = states.get(self.forecast_entity)
        if entity_state is None:
            _LOGGER.warning("ForecastProvider: entity %s state is unavailable/unknown", self.forecast_entity)
            return ForecastData(remaining_today_kwh=0.0)

        state_val = entity_state.get("state", "unavailable")
        remaining = _safe_float(state_val)

        attributes: dict = entity_state.get("attributes", {})
        watts_dict: dict[str, int | float] | None = attributes.get("watts")

        hourly_breakdown = self._parse_watts(watts_dict or {})

        # Parse tomorrow's total from wh_days attribute if available.
        # Keys may be datetime objects (HA forecast_solar) or ISO strings.
        tomorrow_total_kwh = None
        wh_days = attributes.get("wh_days", {})
        if wh_days:
            from datetime import date, timedelta as td
            tomorrow_date = date.today() + td(days=1)
            for key, wh_value in wh_days.items():
                try:
                    if hasattr(key, 'date'):
                        key_date = key.date()
                    else:
                        key_date = date.fromisoformat(str(key))
                    if key_date == tomorrow_date:
                        tomorrow_total_kwh = float(wh_value) / 1000.0
                        break
                except (ValueError, TypeError, AttributeError):
                    continue

        _LOGGER.debug(
            "ForecastSolar: entity=%s remaining=%.2f kWh watts_entries=%d tomorrow=%.2f kWh",
            self.forecast_entity, remaining, len(watts_dict) if watts_dict else 0,
            tomorrow_total_kwh or 0,
        )
        return ForecastData(
            remaining_today_kwh=remaining,
            hourly_breakdown=hourly_breakdown,
            tomorrow_total_kwh=tomorrow_total_kwh,
        )

    def _parse_watts(self, watts_dict: dict[str, int | float]) -> list[HourlyForecast]:
        """Convert Forecast.Solar watts dict to HourlyForecast list."""
        if not watts_dict:
            return []

        result: list[HourlyForecast] = []
        for timestamp_str, watts_value in watts_dict.items():
            dt = _parse_iso(timestamp_str)
            if dt is None:
                continue

            watts = float(watts_value)
            kwh = watts / 1000.0  # average watts over 1 hour -> kWh

            result.append(HourlyForecast(
                start=dt,
                end=dt + timedelta(hours=1),
                expected_kwh=kwh,
                expected_watts=watts,
            ))

        # Sort chronologically
        result.sort(key=lambda hf: hf.start)
        return result


def _parse_iso(value) -> datetime | None:
    """Parse an ISO 8601 datetime string or pass through a datetime object.

    HA stores sensor attributes as native Python types internally,
    so period_start may be a datetime object (not a string).
    """
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def create_forecast_provider(provider_type: str, forecast_entity: str) -> ForecastProvider:
    """Create a forecast provider by type string.

    Args:
        provider_type: One of "generic", "solcast", "forecast_solar".
        forecast_entity: The HA entity_id to read forecast data from.

    Returns:
        An appropriate ForecastProvider instance.

    Raises:
        ValueError: If provider_type is not recognised.
    """
    if provider_type == "none":
        # "none" means no forecast configured; return a generic provider
        # that will simply return empty ForecastData.
        return GenericForecastProvider(forecast_entity or "")

    mapping: dict[str, type[ForecastProvider]] = {
        "generic": GenericForecastProvider,
        "solcast": SolcastProvider,
        "forecast_solar": ForecastSolarProvider,
    }
    provider_cls = mapping.get(provider_type)
    if provider_cls is None:
        raise ValueError(
            f"Unknown forecast provider type: {provider_type!r}. "
            f"Supported types: {list(mapping.keys())}"
        )
    return provider_cls(forecast_entity)

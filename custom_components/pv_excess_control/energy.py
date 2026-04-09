"""Energy / tariff provider module for PV Excess Control.

HA-agnostic: providers accept state dicts (entity_id -> {state, attributes})
rather than HA objects, making them straightforwardly unit-testable.
"""
from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from custom_components.pv_excess_control.const import TariffProvider as TariffProviderEnum
from custom_components.pv_excess_control.models import TariffInfo, TariffWindow

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNAVAILABLE_STATES = {"unavailable", "unknown", "none", ""}


def _parse_price(raw: str) -> float | None:
    """Parse a price string to float, returning None on failure."""
    if raw.lower() in _UNAVAILABLE_STATES:
        return None
    try:
        val = float(raw)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except (ValueError, TypeError):
        return None


def _parse_dt(value: str | datetime) -> datetime:
    """Parse an ISO-format datetime string or pass through a datetime object."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _make_window(start: datetime, end: datetime, price: float, threshold: float) -> TariffWindow:
    """Create a TariffWindow with is_cheap derived from price <= threshold."""
    return TariffWindow(start=start, end=end, price=price, is_cheap=price <= threshold)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TariffProvider(ABC):
    """Base class for tariff providers."""

    @abstractmethod
    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        """Extract tariff information from HA entity states.

        Args:
            states: Mapping of entity_id -> {"state": value, "attributes": {...}}
            cheap_price_threshold: Price below which energy is considered cheap (same unit as price)
            battery_charge_price_threshold: Price below which battery should charge from grid
            feed_in_tariff: Feed-in tariff rate (same unit as price)

        Returns:
            TariffInfo populated with current price and upcoming windows.
        """


# ---------------------------------------------------------------------------
# GenericTariffProvider
# ---------------------------------------------------------------------------

class GenericTariffProvider(TariffProvider):
    """Reads current price from any HA sensor.

    The sensor state must be a numeric price value.  Optionally the attributes
    may contain a ``price_windows`` list of dicts with keys:
        - ``start`` (ISO datetime string)
        - ``end``   (ISO datetime string)
        - ``price`` (float)
    """

    def __init__(self, price_entity: str) -> None:
        self.price_entity = price_entity

    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        entity = states.get(self.price_entity)
        if entity is None:
            if self.price_entity:
                _LOGGER.warning("TariffProvider: entity %s not found in states, using fallback price inf", self.price_entity)
            return TariffInfo(
                current_price=float("inf"),
                feed_in_tariff=feed_in_tariff,
                cheap_price_threshold=cheap_price_threshold,
                battery_charge_price_threshold=battery_charge_price_threshold,
            )

        raw_state = str(entity.get("state", ""))
        parsed_price = _parse_price(raw_state)
        if parsed_price is None:
            _LOGGER.warning("TariffProvider: entity %s state is unavailable/unknown ('%s'), using fallback price inf", self.price_entity, raw_state)
            current_price = float("inf")
        else:
            current_price = parsed_price
        attributes: dict = entity.get("attributes", {}) or {}

        windows: list[TariffWindow] = []
        raw_windows = attributes.get("price_windows", [])
        for entry in raw_windows:
            try:
                start = _parse_dt(entry["start"])
                end = _parse_dt(entry["end"])
                price = float(entry["price"])
                windows.append(_make_window(start, end, price, cheap_price_threshold))
            except (KeyError, ValueError, TypeError):
                # Skip malformed entries
                pass

        _LOGGER.debug(
            "GenericTariff: entity=%s raw_state=%s -> price=%s windows=%d",
            self.price_entity, raw_state, current_price, len(windows),
        )
        return TariffInfo(
            current_price=current_price,
            feed_in_tariff=feed_in_tariff,
            cheap_price_threshold=cheap_price_threshold,
            battery_charge_price_threshold=battery_charge_price_threshold,
            windows=windows,
        )


# ---------------------------------------------------------------------------
# TibberProvider
# ---------------------------------------------------------------------------

class TibberProvider(TariffProvider):
    """Reads Tibber price data.

    Tibber sensors expose today's and tomorrow's prices in attributes with
    each hour represented as ``{"startsAt": "<ISO>", "total": <float>}``.
    Each window is assumed to last exactly one hour.
    """

    def __init__(self, price_entity: str) -> None:
        self.price_entity = price_entity

    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        entity = states.get(self.price_entity)
        if entity is None:
            _LOGGER.warning("TariffProvider: entity %s not found in states, using fallback price inf", self.price_entity)
            return TariffInfo(
                current_price=float("inf"),
                feed_in_tariff=feed_in_tariff,
                cheap_price_threshold=cheap_price_threshold,
                battery_charge_price_threshold=battery_charge_price_threshold,
            )

        raw_state = str(entity.get("state", ""))
        parsed_price = _parse_price(raw_state)
        if parsed_price is None:
            _LOGGER.warning("TariffProvider: entity %s state is unavailable/unknown ('%s'), using fallback price inf", self.price_entity, raw_state)
            current_price = float("inf")
        else:
            current_price = parsed_price
        attributes: dict = entity.get("attributes", {}) or {}

        today_windows: list[TariffWindow] = []
        tomorrow_windows: list[TariffWindow] = []
        for entry in attributes.get("today", []):
            try:
                start = _parse_dt(entry["startsAt"])
                end = start + timedelta(hours=1)
                price = float(entry["total"])
                today_windows.append(_make_window(start, end, price, cheap_price_threshold))
            except (KeyError, ValueError, TypeError):
                pass
        for entry in attributes.get("tomorrow", []):
            try:
                start = _parse_dt(entry["startsAt"])
                end = start + timedelta(hours=1)
                price = float(entry["total"])
                tomorrow_windows.append(_make_window(start, end, price, cheap_price_threshold))
            except (KeyError, ValueError, TypeError):
                pass

        windows = today_windows + tomorrow_windows
        _LOGGER.debug(
            "Tibber: entity=%s price=%.4f windows_today=%d windows_tomorrow=%d",
            self.price_entity, current_price, len(today_windows), len(tomorrow_windows),
        )
        return TariffInfo(
            current_price=current_price,
            feed_in_tariff=feed_in_tariff,
            cheap_price_threshold=cheap_price_threshold,
            battery_charge_price_threshold=battery_charge_price_threshold,
            windows=windows,
        )


# ---------------------------------------------------------------------------
# AwattarProvider
# ---------------------------------------------------------------------------

class AwattarProvider(TariffProvider):
    """Reads aWATTar spot prices.

    aWATTar sensors expose prices in cents per kWh. The current sensor state
    is also in cents.  This provider converts all values to the same currency
    unit as the threshold (assumed EUR/kWh) by dividing by 100.

    Attributes contain a ``prices`` list of:
        ``{"start_time": "<ISO>", "end_time": "<ISO>", "price_ct_per_kwh": <float>}``
    """

    def __init__(self, price_entity: str) -> None:
        self.price_entity = price_entity

    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        entity = states.get(self.price_entity)
        if entity is None:
            _LOGGER.warning("TariffProvider: entity %s not found in states, using fallback price inf", self.price_entity)
            return TariffInfo(
                current_price=float("inf"),
                feed_in_tariff=feed_in_tariff,
                cheap_price_threshold=cheap_price_threshold,
                battery_charge_price_threshold=battery_charge_price_threshold,
            )

        raw_state = str(entity.get("state", ""))
        parsed_price = _parse_price(raw_state)
        if parsed_price is None:
            _LOGGER.warning("TariffProvider: entity %s state is unavailable/unknown ('%s'), using fallback price inf", self.price_entity, raw_state)
            current_price = float("inf")
        else:
            # State is in cents; convert to EUR
            current_price = parsed_price / 100.0

        attributes: dict = entity.get("attributes", {}) or {}

        windows: list[TariffWindow] = []
        for entry in attributes.get("prices", []):
            try:
                start = _parse_dt(entry["start_time"])
                end = _parse_dt(entry["end_time"])
                price_eur = float(entry["price_ct_per_kwh"]) / 100.0
                windows.append(_make_window(start, end, price_eur, cheap_price_threshold))
            except (KeyError, ValueError, TypeError):
                pass

        _LOGGER.debug(
            "Awattar: entity=%s raw_state=%s -> price=%.4f windows=%d",
            self.price_entity, raw_state, current_price, len(windows),
        )
        return TariffInfo(
            current_price=current_price,
            feed_in_tariff=feed_in_tariff,
            cheap_price_threshold=cheap_price_threshold,
            battery_charge_price_threshold=battery_charge_price_threshold,
            windows=windows,
        )


# ---------------------------------------------------------------------------
# NordpoolProvider
# ---------------------------------------------------------------------------

class NordpoolProvider(TariffProvider):
    """Reads Nordpool spot prices.

    Nordpool sensors expose hourly prices as plain lists (one float per hour
    starting at midnight local time).

    Attributes:
        ``today``    - list of 24 floats (hourly prices for today)
        ``tomorrow`` - list of 24 floats (may be empty until afternoon)

    The provider builds TariffWindow objects anchored to midnight UTC today
    (since we have no timezone metadata in tests - a real implementation
    could use the sensor's ``timezone`` attribute if present).  For windows
    we use :func:`datetime.now(timezone.utc)` floored to midnight as the
    base so tests using timezone-aware datetimes still work.
    """

    def __init__(self, price_entity: str, timezone_str: str | None = None) -> None:
        self.price_entity = price_entity
        self._tz = ZoneInfo(timezone_str) if timezone_str else None

    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        entity = states.get(self.price_entity)
        if entity is None:
            _LOGGER.warning("TariffProvider: entity %s not found in states, using fallback price inf", self.price_entity)
            return TariffInfo(
                current_price=float("inf"),
                feed_in_tariff=feed_in_tariff,
                cheap_price_threshold=cheap_price_threshold,
                battery_charge_price_threshold=battery_charge_price_threshold,
            )

        raw_state = str(entity.get("state", ""))
        parsed_price = _parse_price(raw_state)
        if parsed_price is None:
            _LOGGER.warning("TariffProvider: entity %s state is unavailable/unknown ('%s'), using fallback price inf", self.price_entity, raw_state)
            current_price = float("inf")
        else:
            current_price = parsed_price
        attributes: dict = entity.get("attributes", {}) or {}

        windows: list[TariffWindow] = []

        # Base timestamp: midnight local time today using configured timezone
        if self._tz is not None:
            now_local = datetime.now(self._tz)
        else:
            now_local = datetime.now().astimezone()
        midnight_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_tomorrow = midnight_today + timedelta(days=1)

        for day_prices, midnight in (
            (attributes.get("today", []), midnight_today),
            (attributes.get("tomorrow", []), midnight_tomorrow),
        ):
            for hour_idx, price in enumerate(day_prices):
                try:
                    start = midnight + timedelta(hours=hour_idx)
                    end = start + timedelta(hours=1)
                    windows.append(_make_window(start, end, float(price), cheap_price_threshold))
                except (ValueError, TypeError):
                    pass

        _LOGGER.debug(
            "Nordpool: entity=%s raw_state=%s -> price=%.4f windows=%d",
            self.price_entity, raw_state, current_price, len(windows),
        )
        return TariffInfo(
            current_price=current_price,
            feed_in_tariff=feed_in_tariff,
            cheap_price_threshold=cheap_price_threshold,
            battery_charge_price_threshold=battery_charge_price_threshold,
            windows=windows,
        )


# ---------------------------------------------------------------------------
# OctopusProvider
# ---------------------------------------------------------------------------

class OctopusProvider(TariffProvider):
    """Reads Octopus Energy tariff data.

    Octopus sensors expose tariff rates in attributes as a ``rates`` list of:
        ``{"start": "<ISO>", "end": "<ISO>", "value_inc_vat": <float>}``
    """

    def __init__(self, price_entity: str) -> None:
        self.price_entity = price_entity

    def get_tariff_info(
        self,
        states: dict[str, dict],
        cheap_price_threshold: float,
        battery_charge_price_threshold: float,
        feed_in_tariff: float,
    ) -> TariffInfo:
        entity = states.get(self.price_entity)
        if entity is None:
            _LOGGER.warning("TariffProvider: entity %s not found in states, using fallback price inf", self.price_entity)
            return TariffInfo(
                current_price=float("inf"),
                feed_in_tariff=feed_in_tariff,
                cheap_price_threshold=cheap_price_threshold,
                battery_charge_price_threshold=battery_charge_price_threshold,
            )

        raw_state = str(entity.get("state", ""))
        parsed_price = _parse_price(raw_state)
        if parsed_price is None:
            _LOGGER.warning("TariffProvider: entity %s state is unavailable/unknown ('%s'), using fallback price inf", self.price_entity, raw_state)
            current_price = float("inf")
        else:
            current_price = parsed_price
        attributes: dict = entity.get("attributes", {}) or {}

        windows: list[TariffWindow] = []
        rates = attributes.get("rates", attributes.get("applicable_rates", []))
        if not rates:
            _LOGGER.debug(
                "Octopus: no 'rates' attribute found, available keys: %s",
                list(attributes.keys()),
            )
        for entry in rates:
            try:
                start = _parse_dt(entry["start"])
                end = _parse_dt(entry["end"])
                price = float(entry["value_inc_vat"])
                windows.append(_make_window(start, end, price, cheap_price_threshold))
            except (KeyError, ValueError, TypeError):
                pass

        _LOGGER.debug(
            "Octopus: entity=%s raw_state=%s -> price=%.4f windows=%d",
            self.price_entity, raw_state, current_price, len(windows),
        )
        return TariffInfo(
            current_price=current_price,
            feed_in_tariff=feed_in_tariff,
            cheap_price_threshold=cheap_price_threshold,
            battery_charge_price_threshold=battery_charge_price_threshold,
            windows=windows,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tariff_provider(
    provider_type: str,
    price_entity: str,
    timezone_str: str | None = None,
) -> TariffProvider:
    """Create a tariff provider by type string.

    Args:
        provider_type: One of the :class:`~const.TariffProvider` enum values.
        price_entity: HA entity_id for the price sensor.
        timezone_str: IANA timezone name (e.g. ``Europe/Berlin``).  Only used
            by :class:`NordpoolProvider` to anchor tariff windows to the correct
            local midnight.

    Returns:
        An instantiated :class:`TariffProvider`.

    Raises:
        ValueError: If ``provider_type`` is not a known provider.
    """
    mapping: dict[str, type[TariffProvider]] = {
        TariffProviderEnum.NONE: GenericTariffProvider,
        TariffProviderEnum.GENERIC: GenericTariffProvider,
        TariffProviderEnum.TIBBER: TibberProvider,
        TariffProviderEnum.AWATTAR: AwattarProvider,
        TariffProviderEnum.NORDPOOL: NordpoolProvider,
        TariffProviderEnum.OCTOPUS: OctopusProvider,
    }

    cls = mapping.get(provider_type)
    if cls is None:
        known = ", ".join(str(k) for k in mapping)
        raise ValueError(
            f"Unknown tariff provider type {provider_type!r}. Known types: {known}"
        )
    if cls is NordpoolProvider:
        return cls(price_entity, timezone_str=timezone_str)
    return cls(price_entity)

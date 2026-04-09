"""Tests for the energy module (tariff providers). TDD."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.pv_excess_control.energy import (
    AwattarProvider,
    GenericTariffProvider,
    NordpoolProvider,
    OctopusProvider,
    TariffProvider,
    TibberProvider,
    create_tariff_provider,
)
from custom_components.pv_excess_control.const import TariffProvider as TariffProviderEnum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)


def _hour_later(dt: datetime) -> datetime:
    return dt + timedelta(hours=1)


# ---------------------------------------------------------------------------
# TestGenericProvider
# ---------------------------------------------------------------------------

class TestGenericProvider:
    def test_reads_current_price_from_state(self):
        """GenericTariffProvider reads price from sensor state."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "0.25", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == 0.25
        assert info.feed_in_tariff == 0.08
        assert info.cheap_price_threshold == 0.10

    def test_battery_charge_price_threshold_stored(self):
        """battery_charge_price_threshold is stored in TariffInfo."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "0.25", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.battery_charge_price_threshold == 0.05

    def test_unavailable_sensor_returns_inf(self):
        """If sensor is unavailable, return inf price to prevent false cheap triggers."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "unavailable", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == float("inf")

    def test_unknown_sensor_state_returns_inf(self):
        """If sensor state is 'unknown', return inf price to prevent false cheap triggers."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "unknown", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == float("inf")

    def test_missing_sensor_returns_inf(self):
        """If sensor doesn't exist in states dict, return inf price."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == float("inf")

    def test_no_price_windows_when_no_attributes(self):
        """With empty attributes, windows list is empty."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "0.30", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert info.windows == []

    def test_reads_price_windows_from_attributes(self):
        """GenericTariffProvider reads price_windows from attributes if present."""
        provider = GenericTariffProvider("sensor.energy_price")
        now = _utcnow()
        later = _hour_later(now)
        states = {
            "sensor.energy_price": {
                "state": "0.30",
                "attributes": {
                    "price_windows": [
                        {"start": now.isoformat(), "end": later.isoformat(), "price": 0.30},
                        {"start": later.isoformat(), "end": _hour_later(later).isoformat(), "price": 0.10},
                    ]
                },
            }
        }
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert len(info.windows) == 2
        assert info.windows[0].price == pytest.approx(0.30)
        assert info.windows[1].price == pytest.approx(0.10)
        assert info.windows[1].is_cheap is True   # 0.10 < threshold 0.20
        assert info.windows[0].is_cheap is False  # 0.30 > threshold 0.20

    def test_is_abstract_base(self):
        """TariffProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TariffProvider()  # type: ignore[abstract]

    def test_integer_state_parsed(self):
        """State '1' (no decimal point) is parsed correctly."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "1", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == pytest.approx(1.0)

    def test_negative_price_parsed(self):
        """Negative prices (e.g. during surplus) are handled."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "-0.05", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == pytest.approx(-0.05)

    def test_non_parseable_state_returns_inf(self):
        """A garbage state string returns inf price (not crash)."""
        provider = GenericTariffProvider("sensor.energy_price")
        states = {"sensor.energy_price": {"state": "not_a_number", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)
        assert info.current_price == float("inf")


# ---------------------------------------------------------------------------
# TestTibberProvider
# ---------------------------------------------------------------------------

class TestTibberProvider:
    def test_reads_price_and_windows(self):
        """TibberProvider reads current price and today/tomorrow windows."""
        provider = TibberProvider("sensor.tibber_price")
        now = _utcnow()
        later = _hour_later(now)
        states = {
            "sensor.tibber_price": {
                "state": "0.15",
                "attributes": {
                    "today": [
                        {"startsAt": now.isoformat(), "total": 0.15},
                        {"startsAt": later.isoformat(), "total": 0.25},
                    ],
                    "tomorrow": [],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert info.current_price == 0.15
        assert len(info.windows) >= 1

    def test_today_windows_is_cheap_flag(self):
        """Windows from Tibber are correctly labelled cheap/not-cheap."""
        provider = TibberProvider("sensor.tibber_price")
        now = _utcnow()
        states = {
            "sensor.tibber_price": {
                "state": "0.15",
                "attributes": {
                    "today": [
                        {"startsAt": now.isoformat(), "total": 0.10},
                        {"startsAt": _hour_later(now).isoformat(), "total": 0.30},
                    ],
                    "tomorrow": [],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        cheap_windows = [w for w in info.windows if w.is_cheap]
        expensive_windows = [w for w in info.windows if not w.is_cheap]
        assert len(cheap_windows) >= 1
        assert len(expensive_windows) >= 1

    def test_tomorrow_windows_included(self):
        """TibberProvider includes tomorrow's windows."""
        provider = TibberProvider("sensor.tibber_price")
        now = _utcnow()
        states = {
            "sensor.tibber_price": {
                "state": "0.15",
                "attributes": {
                    "today": [
                        {"startsAt": now.isoformat(), "total": 0.15},
                    ],
                    "tomorrow": [
                        {"startsAt": _hour_later(now).isoformat(), "total": 0.12},
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert len(info.windows) == 2

    def test_missing_tomorrow_is_ok(self):
        """If tomorrow key is missing from attributes, no crash."""
        provider = TibberProvider("sensor.tibber_price")
        now = _utcnow()
        states = {
            "sensor.tibber_price": {
                "state": "0.15",
                "attributes": {
                    "today": [
                        {"startsAt": now.isoformat(), "total": 0.15},
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert info.current_price == 0.15
        assert len(info.windows) >= 1

    def test_unavailable_returns_inf(self):
        """Tibber sensor unavailable returns inf price."""
        provider = TibberProvider("sensor.tibber_price")
        states = {"sensor.tibber_price": {"state": "unavailable", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert info.current_price == float("inf")

    def test_missing_sensor_returns_inf(self):
        """Missing Tibber sensor returns inf price."""
        provider = TibberProvider("sensor.tibber_price")
        states = {}
        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)
        assert info.current_price == float("inf")


# ---------------------------------------------------------------------------
# TestAwattarProvider
# ---------------------------------------------------------------------------

class TestAwattarProvider:
    def test_reads_prices_in_cents(self):
        """AwattarProvider converts cents to euros."""
        provider = AwattarProvider("sensor.awattar")
        now = _utcnow()
        states = {
            "sensor.awattar": {
                "state": "5.5",  # cents
                "attributes": {
                    "prices": [
                        {
                            "start_time": now.isoformat(),
                            "end_time": _hour_later(now).isoformat(),
                            "price_ct_per_kwh": 5.5,
                        },
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == pytest.approx(0.055)  # converted from cents

    def test_price_window_is_cheap_correctly_classified(self):
        """Awattar window prices are correctly classified as cheap/expensive."""
        provider = AwattarProvider("sensor.awattar")
        now = _utcnow()
        states = {
            "sensor.awattar": {
                "state": "5.5",
                "attributes": {
                    "prices": [
                        {
                            "start_time": now.isoformat(),
                            "end_time": _hour_later(now).isoformat(),
                            "price_ct_per_kwh": 5.5,  # 0.055 EUR - cheap vs 0.10 threshold
                        },
                        {
                            "start_time": _hour_later(now).isoformat(),
                            "end_time": _hour_later(_hour_later(now)).isoformat(),
                            "price_ct_per_kwh": 20.0,  # 0.20 EUR - expensive vs 0.10 threshold
                        },
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.windows[0].is_cheap is True
        assert info.windows[1].is_cheap is False

    def test_no_prices_attribute_gives_empty_windows(self):
        """If no prices attribute, windows is empty but price still read."""
        provider = AwattarProvider("sensor.awattar")
        states = {
            "sensor.awattar": {
                "state": "8.0",
                "attributes": {},
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == pytest.approx(0.08)  # cents to EUR
        assert info.windows == []

    def test_unavailable_returns_inf(self):
        """Unavailable Awattar sensor returns inf."""
        provider = AwattarProvider("sensor.awattar")
        states = {"sensor.awattar": {"state": "unavailable", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == float("inf")

    def test_missing_sensor_returns_inf(self):
        """Missing Awattar sensor returns inf."""
        provider = AwattarProvider("sensor.awattar")
        states = {}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == float("inf")


# ---------------------------------------------------------------------------
# TestNordpoolProvider
# ---------------------------------------------------------------------------

class TestNordpoolProvider:
    def test_reads_prices(self):
        """NordpoolProvider reads current and hourly prices."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.08",
                "attributes": {
                    "today": [0.05, 0.06, 0.08, 0.12] + [0.10] * 20,
                    "tomorrow": [],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == 0.08

    def test_today_windows_built_from_prices(self):
        """NordpoolProvider builds hourly windows from today's price list."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.08",
                "attributes": {
                    "today": [0.05, 0.06, 0.08, 0.12],
                    "tomorrow": [],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert len(info.windows) == 4

    def test_cheap_flag_set_correctly(self):
        """Nordpool windows are correctly labelled cheap/expensive."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.08",
                "attributes": {
                    "today": [0.05, 0.15],  # 0.05 cheap, 0.15 expensive vs 0.10
                    "tomorrow": [],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.windows[0].is_cheap is True   # 0.05 < 0.10
        assert info.windows[1].is_cheap is False  # 0.15 > 0.10

    def test_tomorrow_windows_included(self):
        """Nordpool tomorrow prices produce additional windows."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.08",
                "attributes": {
                    "today": [0.05, 0.06],
                    "tomorrow": [0.04, 0.07],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert len(info.windows) == 4

    def test_missing_today_gives_empty_windows(self):
        """If today attribute is missing, windows is empty."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.08",
                "attributes": {},
            },
        }
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == 0.08
        assert info.windows == []

    def test_unavailable_returns_inf(self):
        """Unavailable Nordpool sensor returns inf."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {"sensor.nordpool": {"state": "unavailable", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == float("inf")

    def test_missing_sensor_returns_inf(self):
        """Missing Nordpool sensor returns inf."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {}
        info = provider.get_tariff_info(states, 0.10, 0.05, 0.0)
        assert info.current_price == float("inf")


# ---------------------------------------------------------------------------
# TestOctopusProvider
# ---------------------------------------------------------------------------

class TestOctopusProvider:
    def test_reads_rates(self):
        """OctopusProvider reads tariff rates."""
        provider = OctopusProvider("sensor.octopus")
        now = _utcnow()
        states = {
            "sensor.octopus": {
                "state": "0.20",
                "attributes": {
                    "rates": [
                        {
                            "start": now.isoformat(),
                            "end": _hour_later(now).isoformat(),
                            "value_inc_vat": 0.20,
                        },
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.15, 0.05, 0.0)
        assert info.current_price == 0.20

    def test_windows_built_from_rates(self):
        """OctopusProvider builds windows from rates attribute."""
        provider = OctopusProvider("sensor.octopus")
        now = _utcnow()
        states = {
            "sensor.octopus": {
                "state": "0.20",
                "attributes": {
                    "rates": [
                        {"start": now.isoformat(), "end": _hour_later(now).isoformat(), "value_inc_vat": 0.20},
                        {"start": _hour_later(now).isoformat(), "end": _hour_later(_hour_later(now)).isoformat(), "value_inc_vat": 0.08},
                    ],
                },
            },
        }
        info = provider.get_tariff_info(states, 0.15, 0.05, 0.0)
        assert len(info.windows) == 2
        assert info.windows[0].is_cheap is False  # 0.20 > 0.15
        assert info.windows[1].is_cheap is True   # 0.08 < 0.15

    def test_no_rates_gives_empty_windows(self):
        """If no rates attribute, windows is empty."""
        provider = OctopusProvider("sensor.octopus")
        states = {
            "sensor.octopus": {
                "state": "0.20",
                "attributes": {},
            },
        }
        info = provider.get_tariff_info(states, 0.15, 0.05, 0.0)
        assert info.current_price == 0.20
        assert info.windows == []

    def test_unavailable_returns_inf(self):
        """Unavailable Octopus sensor returns inf."""
        provider = OctopusProvider("sensor.octopus")
        states = {"sensor.octopus": {"state": "unavailable", "attributes": {}}}
        info = provider.get_tariff_info(states, 0.15, 0.05, 0.0)
        assert info.current_price == float("inf")

    def test_missing_sensor_returns_inf(self):
        """Missing Octopus sensor returns inf."""
        provider = OctopusProvider("sensor.octopus")
        states = {}
        info = provider.get_tariff_info(states, 0.15, 0.05, 0.0)
        assert info.current_price == float("inf")


# ---------------------------------------------------------------------------
# TestCreateTariffProvider (factory)
# ---------------------------------------------------------------------------

class TestCreateTariffProvider:
    def test_create_generic(self):
        from custom_components.pv_excess_control.energy import GenericTariffProvider
        p = create_tariff_provider(TariffProviderEnum.GENERIC, "sensor.price")
        assert isinstance(p, GenericTariffProvider)

    def test_create_tibber(self):
        p = create_tariff_provider(TariffProviderEnum.TIBBER, "sensor.tibber_price")
        assert isinstance(p, TibberProvider)

    def test_create_awattar(self):
        p = create_tariff_provider(TariffProviderEnum.AWATTAR, "sensor.awattar")
        assert isinstance(p, AwattarProvider)

    def test_create_nordpool(self):
        p = create_tariff_provider(TariffProviderEnum.NORDPOOL, "sensor.nordpool")
        assert isinstance(p, NordpoolProvider)

    def test_create_octopus(self):
        p = create_tariff_provider(TariffProviderEnum.OCTOPUS, "sensor.octopus")
        assert isinstance(p, OctopusProvider)

    def test_create_none_returns_generic(self):
        """NONE provider type falls back to GenericTariffProvider."""
        p = create_tariff_provider(TariffProviderEnum.NONE, "sensor.price")
        assert isinstance(p, GenericTariffProvider)

    def test_unknown_type_raises(self):
        """Unknown provider type raises ValueError."""
        with pytest.raises(ValueError):
            create_tariff_provider("does_not_exist", "sensor.price")  # type: ignore[arg-type]

    def test_entity_id_stored_on_provider(self):
        """Factory passes entity_id through to provider."""
        p = create_tariff_provider(TariffProviderEnum.TIBBER, "sensor.my_tibber")
        assert p.price_entity == "sensor.my_tibber"

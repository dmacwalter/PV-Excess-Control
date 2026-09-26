"""Tests for coverage gaps in PV Excess Control modules.

Covers edge cases not already tested in module-specific test files:
1. Planner: empty forecast but tariff windows present
2. Energy providers: malformed / partial attributes
3. Controller: unknown entity domain in apply_decisions
4. Notifications: rate limit boundary (exactly at the limit)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.pv_excess_control.const import (
    NotificationEvent,
)
from custom_components.pv_excess_control.energy import (
    AwattarProvider,
    GenericTariffProvider,
    NordpoolProvider,
    OctopusProvider,
    TibberProvider,
    create_tariff_provider,
)
from custom_components.pv_excess_control.models import (
    Action,
    ApplianceConfig,
    BatteryConfig,
    BatteryStrategy,
    ControlDecision,
    ForecastData,
    HourlyForecast,
    Plan,
    TariffInfo,
    TariffWindow,
)
from custom_components.pv_excess_control.notifications import NotificationManager
from custom_components.pv_excess_control.planner import Planner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt(hour: int, minute: int = 0) -> datetime:
    """Create a UTC datetime on 2026-03-23 at the given hour:minute."""
    return datetime(2026, 3, 23, hour, minute, 0, tzinfo=timezone.utc)


def _make_tariff_window(start_hour: int, end_hour: int, price: float, is_cheap: bool = False) -> TariffWindow:
    return TariffWindow(
        start=_dt(start_hour),
        end=_dt(end_hour),
        price=price,
        is_cheap=is_cheap,
    )


def _make_appliance_config(**kwargs) -> ApplianceConfig:
    defaults = dict(
        id="appliance_1",
        name="Test Appliance",
        entity_id="switch.test",
        priority=100,
        phases=1,
        nominal_power=1000.0,
        actual_power_entity=None,
        dynamic_current=False,
        current_entity=None,
        min_current=0.0,
        max_current=16.0,
        ev_soc_entity=None,
        ev_connected_entity=None,
        is_big_consumer=False,
        battery_max_discharge_override=None,
        on_only=False,
        min_daily_runtime=None,
        max_daily_runtime=None,
        schedule_deadline=None,
        switch_interval=0,  # No delay so tests don't need to wait
        allow_grid_supplement=False,
        max_grid_power=None,
    )
    defaults.update(kwargs)
    return ApplianceConfig(**defaults)


def _make_state(state_value: str, attributes: dict | None = None) -> MagicMock:
    mock_state = MagicMock()
    mock_state.state = state_value
    mock_state.attributes = attributes or {}
    return mock_state


def _make_hass(states_map: dict | None = None) -> MagicMock:
    hass = MagicMock()
    hass.states = MagicMock()
    hass.states.get = MagicMock(side_effect=lambda eid: (states_map or {}).get(eid))
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    return hass


def _make_notification_manager(settings: dict | None = None) -> tuple[MagicMock, NotificationManager]:
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    manager = NotificationManager(hass, notification_settings=settings)
    return hass, manager


# ===========================================================================
# 1. Planner edge cases
# ===========================================================================


class TestPlannerEdgeCases:
    """Edge cases for Planner.build_timeline() and create_plan()."""

    def test_empty_forecast_with_tariff_windows(self):
        """When forecast is empty but tariffs are present, slots are produced with 0 solar."""
        planner = Planner()
        # ForecastData with no hourly breakdown
        forecast = ForecastData(remaining_today_kwh=0.0, hourly_breakdown=[])
        tariffs = [
            _make_tariff_window(10, 11, 0.20),
            _make_tariff_window(11, 12, 0.25),
        ]

        slots = planner.build_timeline(forecast, tariffs, base_load_watts=500.0)

        # Slots are created (one per tariff window), but with 0 solar
        assert len(slots) >= 1
        for slot in slots:
            assert slot.expected_solar_watts == 0.0
            assert slot.expected_excess_watts == 0.0

    def test_empty_forecast_create_plan_no_crash(self):
        """create_plan does not crash when forecast has no hourly breakdown."""
        planner = Planner()
        forecast = ForecastData(remaining_today_kwh=0.0)
        tariff = TariffInfo(
            current_price=0.25,
            feed_in_tariff=0.08,
            cheap_price_threshold=0.10,
            battery_charge_price_threshold=0.05,
            windows=[
                _make_tariff_window(10, 11, 0.20),
                _make_tariff_window(11, 12, 0.25),
            ],
        )
        plan = planner.create_plan(
            forecast=forecast,
            tariff=tariff,
            appliances=[],
            battery_config=None,
            current_soc=None,
            export_limit=None,
        )

        assert isinstance(plan, Plan)
        # No appliances means no entries
        assert plan.entries == []

    def test_empty_tariff_windows_empty_timeline(self):
        """When tariff has no windows, build_timeline returns empty list."""
        planner = Planner()
        forecast = ForecastData(
            remaining_today_kwh=5.0,
            hourly_breakdown=[
                HourlyForecast(
                    start=_dt(10), end=_dt(11), expected_kwh=1.0, expected_watts=1000.0
                )
            ],
        )
        tariff = TariffInfo(
            current_price=0.25,
            feed_in_tariff=0.08,
            cheap_price_threshold=0.10,
            battery_charge_price_threshold=0.05,
            windows=[],  # No windows
        )

        plan = planner.create_plan(
            forecast=forecast,
            tariff=tariff,
            appliances=[],
            battery_config=None,
            current_soc=None,
            export_limit=None,
        )

        assert isinstance(plan, Plan)
        assert plan.entries == []

    def test_full_battery_needs_no_charging(self):
        """Battery at 100% SoC produces no charging need."""
        from datetime import time

        planner = Planner()
        forecast = ForecastData(
            remaining_today_kwh=5.0,
            hourly_breakdown=[
                HourlyForecast(
                    start=_dt(10), end=_dt(11), expected_kwh=3.0, expected_watts=3000.0
                )
            ],
        )
        battery = BatteryConfig(
            capacity_kwh=10.0,
            max_discharge_entity=None,
            max_discharge_default=None,
            target_soc=80.0,
            target_time=time(7, 0),
            strategy=BatteryStrategy.BATTERY_FIRST,
            allow_grid_charging=False,
        )
        tariff = TariffInfo(
            current_price=0.25,
            feed_in_tariff=0.08,
            cheap_price_threshold=0.10,
            battery_charge_price_threshold=0.05,
            windows=[_make_tariff_window(10, 11, 0.20)],
        )

        # current_soc=100 >= target_soc=80, so no charging needed
        allocation = planner.calculate_battery_strategy(
            planner.build_timeline(forecast, tariff.windows),
            battery,
            current_soc=100.0,
        )

        assert allocation.charging_needed_kwh == 0.0
        assert allocation.slots_reserved == []

    def test_planner_confidence_neutral_when_nothing_scheduled(self):
        """Plan confidence is 0.5 (neutral) when no appliances are scheduled."""
        planner = Planner()
        forecast = ForecastData(remaining_today_kwh=0.0, hourly_breakdown=[])
        tariff = TariffInfo(
            current_price=0.25,
            feed_in_tariff=0.08,
            cheap_price_threshold=0.10,
            battery_charge_price_threshold=0.05,
            windows=[],
        )

        plan = planner.create_plan(
            forecast=forecast,
            tariff=tariff,
            appliances=[],
            battery_config=None,
            current_soc=None,
            export_limit=None,
        )

        # Per planner._calculate_confidence: "Neutral confidence when nothing is scheduled"
        assert plan.confidence == pytest.approx(0.5)


# ===========================================================================
# 2. Energy provider edge cases
# ===========================================================================


class TestEnergyProviderEdgeCases:
    """Edge cases for tariff providers with malformed attributes."""

    def test_generic_malformed_price_windows_skipped(self):
        """Malformed price_windows entries are silently skipped."""
        provider = GenericTariffProvider("sensor.price")
        states = {
            "sensor.price": {
                "state": "0.25",
                "attributes": {
                    "price_windows": [
                        {"start": "bad_date", "end": "also_bad", "price": 0.25},  # invalid dates
                        {"start": "2026-03-23T10:00:00+00:00", "end": "2026-03-23T11:00:00+00:00"},  # missing price
                        None,  # None entry
                    ]
                },
            }
        }

        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)

        # Should not crash; malformed entries are silently dropped
        assert info.current_price == pytest.approx(0.25)
        assert info.windows == []

    def test_generic_attributes_is_none(self):
        """Provider handles None attributes gracefully."""
        provider = GenericTariffProvider("sensor.price")
        states = {
            "sensor.price": {
                "state": "0.20",
                "attributes": None,  # None instead of dict
            }
        }

        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)

        assert info.current_price == pytest.approx(0.20)
        assert info.windows == []

    def test_tibber_malformed_entries_skipped(self):
        """Tibber entries with missing keys are silently skipped."""
        provider = TibberProvider("sensor.tibber")
        now = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc)
        states = {
            "sensor.tibber": {
                "state": "0.15",
                "attributes": {
                    "today": [
                        {"total": 0.15},  # missing "startsAt"
                        {"startsAt": now.isoformat(), "total": "not_a_number"},  # bad total
                        {"startsAt": now.isoformat(), "total": 0.12},  # valid
                    ],
                    "tomorrow": [],
                },
            }
        }

        info = provider.get_tariff_info(states, 0.20, 0.05, 0.08)

        # Only the valid entry should be parsed
        assert info.current_price == pytest.approx(0.15)
        assert len(info.windows) == 1

    def test_awattar_malformed_prices_skipped(self):
        """Awattar entries with missing keys are silently skipped."""
        provider = AwattarProvider("sensor.awattar")
        now = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc)
        states = {
            "sensor.awattar": {
                "state": "5.5",
                "attributes": {
                    "prices": [
                        {"price_ct_per_kwh": 5.5},  # missing start/end times
                        {"start_time": now.isoformat(), "end_time": "bad"},  # bad end time
                        {
                            "start_time": now.isoformat(),
                            "end_time": (now + timedelta(hours=1)).isoformat(),
                            "price_ct_per_kwh": 6.0,
                        },  # valid
                    ]
                },
            }
        }

        info = provider.get_tariff_info(states, 0.10, 0.05, 0.08)

        assert info.current_price == pytest.approx(0.055)  # 5.5 cents / 100
        assert len(info.windows) == 1
        assert info.windows[0].price == pytest.approx(0.06)

    def test_nordpool_non_numeric_prices_skipped(self):
        """NordPool entries with non-numeric prices are silently skipped."""
        provider = NordpoolProvider("sensor.nordpool")
        states = {
            "sensor.nordpool": {
                "state": "0.22",
                "attributes": {
                    "today": [0.22, "bad_price", None, 0.28],
                    "tomorrow": [],
                },
            }
        }

        info = provider.get_tariff_info(states, 0.25, 0.05, 0.08)

        # Only the 2 numeric entries (0.22 and 0.28) should produce windows
        assert info.current_price == pytest.approx(0.22)
        assert len(info.windows) == 2

    def test_octopus_malformed_rates_skipped(self):
        """Octopus entries with missing keys are silently skipped."""
        provider = OctopusProvider("sensor.octopus")
        now = datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc)
        states = {
            "sensor.octopus": {
                "state": "0.30",
                "attributes": {
                    "rates": [
                        {"value_inc_vat": 0.30},  # missing start/end
                        {"start": now.isoformat(), "end": "garbage", "value_inc_vat": 0.28},  # bad end
                        {
                            "start": now.isoformat(),
                            "end": (now + timedelta(minutes=30)).isoformat(),
                            "value_inc_vat": 0.25,
                        },  # valid
                    ]
                },
            }
        }

        info = provider.get_tariff_info(states, 0.35, 0.05, 0.08)

        assert info.current_price == pytest.approx(0.30)
        assert len(info.windows) == 1

    def test_create_tariff_provider_unknown_raises(self):
        """create_tariff_provider raises ValueError for unknown provider types."""
        with pytest.raises(ValueError, match="Unknown tariff provider type"):
            create_tariff_provider("totally_unknown_provider", "sensor.price")


# ===========================================================================
# 3. Controller edge cases
# ===========================================================================


class TestApplyDecisionsEdgeCases:
    """Edge cases on the live apply path (coordinator._apply_decisions).

    These replace tests of controller.Controller, an unused duplicate of this
    path that was removed in 0.3.16.
    """

    def _run(self, entity_id, action, *, bypass=False, recent_change=False):
        import asyncio
        from custom_components.pv_excess_control.models import (
            BatteryDischargeAction, OptimizerResult,
        )
        from .test_init import MockState, _make_config_entry, _make_coordinator

        sub = MagicMock()
        sub.data = {
            "appliance_name": "Thing", "appliance_entity": entity_id,
            "appliance_priority": 500, "nominal_power": 200.0, "phases": 1,
            "dynamic_current": False, "switch_interval": 300, "on_only": False,
            "allow_grid_supplement": False, "is_big_consumer": False,
        }
        start = "off" if action == Action.ON else "on"
        coord = _make_coordinator(states={entity_id: MockState(start)},
                                  entry=_make_config_entry(subentries={"sub_1": sub}))
        coord._get_appliance_configs()
        if recent_change:
            coord._last_state_change["sub_1"] = datetime.now() - timedelta(seconds=10)
        result = OptimizerResult(
            decisions=[ControlDecision(appliance_id="sub_1", action=action, target_current=None,
                                       reason="test", overrides_plan=False,
                                       bypasses_cooldown=bypass)],
            battery_discharge_action=BatteryDischargeAction(should_limit=False,
                                                            max_discharge_watts=None),
        )
        asyncio.get_event_loop().run_until_complete(coord._apply_decisions(result))
        return coord.hass.services.calls

    def test_service_domain_follows_entity_domain(self):
        for entity_id in ("light.pool_lamp", "water_heater.hws", "input_boolean.flag"):
            calls = self._run(entity_id, Action.ON)
            assert [(c[0], c[1]) for c in calls] == [(entity_id.split(".")[0], "turn_on")]

    def test_turn_off_uses_entity_domain(self):
        calls = self._run("climate.study", Action.OFF)
        assert [(c[0], c[1]) for c in calls] == [("climate", "turn_off")]

    def test_switch_interval_blocks_change(self):
        assert self._run("switch.thing", Action.ON, recent_change=True) == []

    def test_bypass_flag_overrides_switch_interval(self):
        calls = self._run("switch.thing", Action.OFF, bypass=True, recent_change=True)
        assert [(c[0], c[1]) for c in calls] == [("switch", "turn_off")]


class TestNotificationEdgeCases:
    """Edge cases for the NotificationManager rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_boundary_exactly_at_limit(self):
        """Notification sent exactly at the rate limit boundary (300s) is still blocked."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_notification_manager(settings)

        # Set last sent to exactly 300 seconds ago (equal to, not greater than)
        exactly_at_limit = datetime.now() - timedelta(seconds=300)
        manager._last_sent[NotificationEvent.FORCE_CHARGE] = exactly_at_limit

        result = await manager.async_notify(NotificationEvent.FORCE_CHARGE, "Test")

        # Exactly at the limit: 300 < 300 is False, so NOT rate-limited -> should send
        # Per the code: `total_seconds() < self._rate_limit_seconds` means < 300
        # At exactly 300 seconds elapsed, it is NOT rate-limited
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_just_before_expiry(self):
        """Notification 1 second before rate limit expiry is blocked."""
        settings = {NotificationEvent.APPLIANCE_ON: True}
        hass, manager = _make_notification_manager(settings)

        # 299 seconds ago = still within 300s rate limit
        manager._last_sent[NotificationEvent.APPLIANCE_ON] = (
            datetime.now() - timedelta(seconds=299)
        )

        result = await manager.async_notify(NotificationEvent.APPLIANCE_ON, "test")

        assert result is False
        hass.services.async_call.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rate_limit_just_after_expiry(self):
        """Notification 1 second after rate limit expiry is allowed."""
        settings = {NotificationEvent.APPLIANCE_ON: True}
        hass, manager = _make_notification_manager(settings)

        # 301 seconds ago = past the 300s rate limit
        manager._last_sent[NotificationEvent.APPLIANCE_ON] = (
            datetime.now() - timedelta(seconds=301)
        )

        result = await manager.async_notify(NotificationEvent.APPLIANCE_ON, "test")

        assert result is True
        hass.services.async_call.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_different_events_have_independent_rate_limits(self):
        """Rate limiting is per-event-type, not global."""
        settings = {
            NotificationEvent.APPLIANCE_ON: True,
            NotificationEvent.APPLIANCE_OFF: True,
        }
        hass, manager = _make_notification_manager(settings)

        # Send APPLIANCE_ON (sets its rate limit)
        await manager.async_notify(NotificationEvent.APPLIANCE_ON, "Appliance on")

        # APPLIANCE_OFF should not be rate-limited by the APPLIANCE_ON send
        result = await manager.async_notify(NotificationEvent.APPLIANCE_OFF, "Appliance off")

        assert result is True
        assert hass.services.async_call.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(self):
        """After rate limit window expires, the same event can be sent again."""
        settings = {NotificationEvent.SENSOR_UNAVAILABLE: True}
        hass, manager = _make_notification_manager(settings)

        # First send
        first = await manager.async_notify(NotificationEvent.SENSOR_UNAVAILABLE, "msg 1")
        assert first is True

        # Immediately after: rate-limited
        second = await manager.async_notify(NotificationEvent.SENSOR_UNAVAILABLE, "msg 2")
        assert second is False

        # Simulate window expiry
        manager._last_sent[NotificationEvent.SENSOR_UNAVAILABLE] = (
            datetime.now() - timedelta(seconds=301)
        )

        # Should now be allowed
        third = await manager.async_notify(NotificationEvent.SENSOR_UNAVAILABLE, "msg 3")
        assert third is True
        assert hass.services.async_call.await_count == 2  # first + third

    @pytest.mark.asyncio
    async def test_no_rate_limit_entry_allows_send(self):
        """First-time event (no prior entry in _last_sent) is not rate-limited."""
        settings = {NotificationEvent.DAILY_SUMMARY: True}
        hass, manager = _make_notification_manager(settings)

        assert NotificationEvent.DAILY_SUMMARY not in manager._last_sent

        result = await manager.async_notify(NotificationEvent.DAILY_SUMMARY, "Daily summary")

        assert result is True
        assert NotificationEvent.DAILY_SUMMARY in manager._last_sent

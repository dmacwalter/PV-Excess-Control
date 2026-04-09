"""Tests for PV Excess Control notification manager."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.pv_excess_control.const import (
    DEFAULT_NOTIFICATION_SETTINGS,
    NotificationEvent,
)
from custom_components.pv_excess_control.notifications import NotificationManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hass() -> MagicMock:
    """Create a minimal mock HomeAssistant object."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


def _make_manager(
    settings: dict[str, bool] | None = None,
    service: str | None = None,
) -> tuple[MagicMock, NotificationManager]:
    hass = _make_hass()
    manager = NotificationManager(hass, notification_settings=settings, notification_service=service)
    return hass, manager


# ---------------------------------------------------------------------------
# TestNotificationManager
# ---------------------------------------------------------------------------

class TestNotificationManager:
    async def test_enabled_event_sends(self):
        """Enabled events send notifications."""
        settings = {NotificationEvent.SENSOR_UNAVAILABLE: True}
        hass, manager = _make_manager(settings=settings)

        result = await manager.async_notify(NotificationEvent.SENSOR_UNAVAILABLE, "Test message")

        assert result is True
        hass.services.async_call.assert_awaited_once()

    async def test_disabled_event_skips(self):
        """Disabled events are not sent."""
        settings = {NotificationEvent.APPLIANCE_ON: False}
        hass, manager = _make_manager(settings=settings)

        result = await manager.async_notify(NotificationEvent.APPLIANCE_ON, "Appliance on")

        assert result is False
        hass.services.async_call.assert_not_awaited()

    async def test_unknown_event_skips(self):
        """Events not in settings default to disabled."""
        hass, manager = _make_manager(settings={})

        result = await manager.async_notify("unknown_event", "Some message")

        assert result is False
        hass.services.async_call.assert_not_awaited()

    async def test_rate_limiting(self):
        """Same event not repeated within rate limit window."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_manager(settings=settings)

        first = await manager.async_notify(NotificationEvent.FORCE_CHARGE, "First")
        second = await manager.async_notify(NotificationEvent.FORCE_CHARGE, "Second")

        assert first is True
        assert second is False
        assert hass.services.async_call.await_count == 1

    async def test_rate_limiting_allows_after_window(self):
        """Event is sent again after the rate limit window expires."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_manager(settings=settings)

        past_time = datetime.now() - timedelta(seconds=301)
        manager._last_sent[NotificationEvent.FORCE_CHARGE] = past_time

        result = await manager.async_notify(NotificationEvent.FORCE_CHARGE, "After window")

        assert result is True
        hass.services.async_call.assert_awaited_once()

    async def test_custom_service(self):
        """Custom notification service used when configured."""
        settings = {NotificationEvent.OVERRIDE_ACTIVATED: True}
        hass, manager = _make_manager(settings=settings, service="notify.mobile_app_phone")

        await manager.async_notify(NotificationEvent.OVERRIDE_ACTIVATED, "Override active")

        hass.services.async_call.assert_awaited_once_with(
            "notify",
            "mobile_app_phone",
            {"message": "Override active", "title": "PV Excess Control"},
        )

    async def test_custom_service_with_subdomain(self):
        """Custom service with dots in name is split at first dot."""
        settings = {NotificationEvent.OVERRIDE_ACTIVATED: True}
        hass, manager = _make_manager(settings=settings, service="notify.group.all_devices")

        await manager.async_notify(NotificationEvent.OVERRIDE_ACTIVATED, "msg")

        hass.services.async_call.assert_awaited_once_with(
            "notify",
            "group.all_devices",
            {"message": "msg", "title": "PV Excess Control"},
        )

    async def test_default_persistent_notification(self):
        """Falls back to persistent_notification when no service configured."""
        settings = {NotificationEvent.SENSOR_UNAVAILABLE: True}
        hass, manager = _make_manager(settings=settings, service=None)

        await manager.async_notify(NotificationEvent.SENSOR_UNAVAILABLE, "Sensor gone")

        hass.services.async_call.assert_awaited_once_with(
            "persistent_notification",
            "create",
            {
                "message": "Sensor gone",
                "title": "PV Excess Control",
                "notification_id": f"pv_excess_{NotificationEvent.SENSOR_UNAVAILABLE}",
            },
        )

    async def test_custom_title(self):
        """Custom title is forwarded to the service call."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_manager(settings=settings)

        await manager.async_notify(NotificationEvent.FORCE_CHARGE, "msg", title="My Title")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["title"] == "My Title"

    async def test_last_sent_updated_after_send(self):
        """_last_sent is updated with the current time after a successful send."""
        settings = {NotificationEvent.DAILY_SUMMARY: True}
        hass, manager = _make_manager(settings=settings)

        before = datetime.now()
        await manager.async_notify(NotificationEvent.DAILY_SUMMARY, "msg")
        after = datetime.now()

        ts = manager._last_sent[NotificationEvent.DAILY_SUMMARY]
        assert before <= ts <= after

    # ------------------------------------------------------------------
    # Convenience methods - message format
    # ------------------------------------------------------------------

    async def test_appliance_on_message(self):
        """Correct message format for appliance on."""
        settings = {NotificationEvent.APPLIANCE_ON: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_appliance_on("EV Charger", "excess solar", 1800.0)

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "EV Charger started: excess solar (1800W)"

    async def test_appliance_off_message(self):
        """Correct message format for appliance off."""
        settings = {NotificationEvent.APPLIANCE_OFF: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_appliance_off("Hot Water Heater", "insufficient excess")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Hot Water Heater stopped: insufficient excess"

    async def test_override_message_without_until(self):
        """Override notification message without an end time."""
        settings = {NotificationEvent.OVERRIDE_ACTIVATED: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_override("Pool Pump")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Pool Pump override active"

    async def test_override_message_with_until(self):
        """Override notification message includes end time when provided."""
        settings = {NotificationEvent.OVERRIDE_ACTIVATED: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_override("Pool Pump", until="18:00")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Pool Pump override active until 18:00"

    async def test_force_charge_started_message(self):
        """Force charge started message."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_force_charge(active=True)

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Battery force charge started"

    async def test_force_charge_stopped_message(self):
        """Force charge stopped message."""
        settings = {NotificationEvent.FORCE_CHARGE: True}
        hass, manager = _make_manager(settings=settings)
        # Allow second send by clearing last_sent
        manager._rate_limit_seconds = 0

        await manager.notify_force_charge(active=False)

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Battery force charge stopped"

    async def test_sensor_unavailable_message(self):
        """Correct message format for sensor unavailable."""
        settings = {NotificationEvent.SENSOR_UNAVAILABLE: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_sensor_unavailable("sensor.pv_power")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "sensor.pv_power unavailable - control paused"

    async def test_daily_summary_message(self):
        """Correct message format for daily summary."""
        settings = {NotificationEvent.DAILY_SUMMARY: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_daily_summary(ratio=82.0, savings=3.40, solar_kwh=18.2)

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Today: 82% self-consumption, saved 3.40, 18.2 kWh solar"

    async def test_forecast_warning_message(self):
        """Correct message format for forecast warning."""
        settings = {NotificationEvent.FORECAST_WARNING: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_forecast_warning(tomorrow_kwh=4.2, actions="Pre-heating scheduled.")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "Tomorrow: low solar (4.2 kWh). Pre-heating scheduled."

    async def test_plan_deviation_message(self):
        """Correct message format for plan deviation."""
        settings = {NotificationEvent.PLAN_DEVIATION: True}
        hass, manager = _make_manager(settings=settings)

        await manager.notify_plan_deviation("EV Charger", "actual solar 40% below forecast")

        service_data = hass.services.async_call.call_args.args[2]
        assert service_data["message"] == "EV Charger deviated from plan: actual solar 40% below forecast"

    async def test_all_event_types_have_methods(self):
        """All NotificationEvent types have convenience methods."""
        expected_methods = {
            NotificationEvent.APPLIANCE_ON: "notify_appliance_on",
            NotificationEvent.APPLIANCE_OFF: "notify_appliance_off",
            NotificationEvent.OVERRIDE_ACTIVATED: "notify_override",
            NotificationEvent.FORCE_CHARGE: "notify_force_charge",
            NotificationEvent.SENSOR_UNAVAILABLE: "notify_sensor_unavailable",
            NotificationEvent.DAILY_SUMMARY: "notify_daily_summary",
            NotificationEvent.FORECAST_WARNING: "notify_forecast_warning",
            NotificationEvent.PLAN_DEVIATION: "notify_plan_deviation",
        }
        _, manager = _make_manager()
        for event, method_name in expected_methods.items():
            assert hasattr(manager, method_name), (
                f"NotificationManager missing method '{method_name}' for event '{event}'"
            )

    async def test_default_settings_applied_when_none_passed(self):
        """DEFAULT_NOTIFICATION_SETTINGS used when notification_settings is None."""
        hass, manager = _make_manager(settings=None)

        assert manager.settings == DEFAULT_NOTIFICATION_SETTINGS

    async def test_default_settings_events_enabled(self):
        """Events enabled by default (override, force_charge, sensor_unavailable) are active."""
        hass, manager = _make_manager(settings=None)

        for event in (
            NotificationEvent.OVERRIDE_ACTIVATED,
            NotificationEvent.FORCE_CHARGE,
            NotificationEvent.SENSOR_UNAVAILABLE,
        ):
            assert manager.settings[event] is True, f"{event} should be enabled by default"

    async def test_default_settings_events_disabled(self):
        """Events disabled by default are inactive."""
        hass, manager = _make_manager(settings=None)

        for event in (
            NotificationEvent.APPLIANCE_ON,
            NotificationEvent.APPLIANCE_OFF,
            NotificationEvent.DAILY_SUMMARY,
            NotificationEvent.FORECAST_WARNING,
            NotificationEvent.PLAN_DEVIATION,
        ):
            assert manager.settings[event] is False, f"{event} should be disabled by default"

    async def test_returns_false_when_disabled(self):
        """Convenience methods return False when event is disabled."""
        settings = {e: False for e in NotificationEvent}
        hass, manager = _make_manager(settings=settings)

        assert await manager.notify_appliance_on("X", "reason", 1000) is False
        assert await manager.notify_appliance_off("X", "reason") is False
        assert await manager.notify_override("X") is False
        assert await manager.notify_force_charge(True) is False
        assert await manager.notify_sensor_unavailable("s") is False
        assert await manager.notify_daily_summary(80, 2.5, 10.0) is False
        assert await manager.notify_forecast_warning(5.0, "act") is False
        assert await manager.notify_plan_deviation("X", "details") is False

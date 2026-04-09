"""Tests for the analytics tracker module."""

from datetime import timedelta

import pytest

from custom_components.pv_excess_control.analytics import (
    AnalyticsTracker,
    ApplianceStats,
)


class TestAnalyticsTracker:
    def test_record_solar_savings(self):
        """Solar-powered cycle: savings = energy * (import_price - feed_in)."""
        tracker = AnalyticsTracker(feed_in_tariff=0.08, normal_import_price=0.25)
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.25)
        # 1kWh * (0.25 - 0.08) = 0.17
        assert abs(tracker.savings_today - 0.17) < 0.001

    def test_record_cheap_tariff_savings(self):
        """Cheap tariff cycle: savings = energy * (normal - cheap)."""
        tracker = AnalyticsTracker(normal_import_price=0.25)
        tracker.record_cycle("app1", 2000, 1800, "cheap_tariff", 0.05)
        # 1kWh * (0.25 - 0.05) = 0.20
        assert abs(tracker.savings_today - 0.20) < 0.001

    def test_no_feed_in_defaults_zero(self):
        """Without feed-in tariff, full import price counts as savings."""
        tracker = AnalyticsTracker(feed_in_tariff=0.0)
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.30)
        assert abs(tracker.savings_today - 0.30) < 0.001

    def test_self_consumption_ratio(self):
        """Ratio = solar consumed / solar produced * 100."""
        tracker = AnalyticsTracker()
        tracker.record_solar_production(5000, 3600)  # 5kWh
        tracker.record_cycle("app1", 3000, 3600, "solar", 0.25)  # 3kWh consumed
        # 3/5 = 60%
        assert abs(tracker.self_consumption_ratio - 60.0) < 0.1

    def test_per_appliance_stats(self):
        """Track per-appliance energy and runtime."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("ev", 3000, 7200, "solar", 0.25)  # 6kWh, 2h
        stats = tracker.get_appliance_stats("ev")
        assert abs(stats.energy_today_kwh - 6.0) < 0.001
        assert stats.runtime_today == timedelta(hours=2)

    def test_daily_reset(self):
        """Reset clears all daily counters."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.25)
        tracker.reset_daily()
        assert tracker.savings_today == 0.0
        assert tracker.self_consumption_ratio == 0.0

    def test_negative_savings_clamped(self):
        """Negative savings (feed_in > import) clamped to 0."""
        tracker = AnalyticsTracker(feed_in_tariff=0.50)
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.10)
        assert tracker.savings_today == 0.0

    def test_grid_source_no_savings(self):
        """Grid-powered cycle produces no savings."""
        tracker = AnalyticsTracker(normal_import_price=0.25)
        tracker.record_cycle("app1", 1000, 3600, "grid", 0.25)
        assert tracker.savings_today == 0.0

    def test_solar_consumed_kwh_accumulates(self):
        """Solar consumed kWh accumulates across multiple solar cycles."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("app1", 2000, 3600, "solar", 0.25)  # 2kWh
        tracker.record_cycle("app2", 1000, 3600, "solar", 0.25)  # 1kWh
        assert abs(tracker.solar_consumed_kwh - 3.0) < 0.001

    def test_grid_source_does_not_count_as_solar_consumed(self):
        """Grid-powered cycle does not add to solar consumed kWh."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("app1", 1000, 3600, "grid", 0.25)
        assert tracker.solar_consumed_kwh == 0.0

    def test_cheap_tariff_does_not_count_as_solar_consumed(self):
        """Cheap tariff cycle does not add to solar consumed kWh."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("app1", 1000, 3600, "cheap_tariff", 0.05)
        assert tracker.solar_consumed_kwh == 0.0

    def test_record_grid_export(self):
        """Grid export kWh is tracked separately."""
        tracker = AnalyticsTracker()
        tracker.record_grid_export(3000, 3600)  # 3kWh
        assert abs(tracker.grid_export_kwh - 3.0) < 0.001

    def test_self_consumption_ratio_zero_production(self):
        """Self-consumption ratio is 0 when no solar has been produced."""
        tracker = AnalyticsTracker()
        assert tracker.self_consumption_ratio == 0.0

    def test_self_consumption_ratio_capped_at_100(self):
        """Self-consumption ratio cannot exceed 100%."""
        tracker = AnalyticsTracker()
        tracker.record_solar_production(1000, 3600)  # 1kWh produced
        # Record more consumed than produced (e.g. battery discharge scenario)
        tracker.record_cycle("app1", 2000, 3600, "solar", 0.25)  # 2kWh consumed
        assert tracker.self_consumption_ratio == 100.0

    def test_multiple_appliances_independent_stats(self):
        """Each appliance accumulates its own independent statistics."""
        tracker = AnalyticsTracker(feed_in_tariff=0.0, normal_import_price=0.25)
        tracker.record_cycle("ev", 7000, 3600, "solar", 0.25)   # 7kWh
        tracker.record_cycle("heatpump", 2000, 1800, "solar", 0.25)  # 1kWh

        ev_stats = tracker.get_appliance_stats("ev")
        hp_stats = tracker.get_appliance_stats("heatpump")

        assert abs(ev_stats.energy_today_kwh - 7.0) < 0.001
        assert abs(hp_stats.energy_today_kwh - 1.0) < 0.001
        assert ev_stats.runtime_today == timedelta(hours=1)
        assert hp_stats.runtime_today == timedelta(minutes=30)

    def test_get_appliance_stats_unknown_appliance(self):
        """Requesting stats for an unknown appliance returns default ApplianceStats."""
        tracker = AnalyticsTracker()
        stats = tracker.get_appliance_stats("nonexistent")
        assert isinstance(stats, ApplianceStats)
        assert stats.energy_today_kwh == 0.0
        assert stats.savings_today == 0.0
        assert stats.runtime_today == timedelta(0)

    def test_reset_daily_clears_appliance_stats(self):
        """Daily reset clears per-appliance stats."""
        tracker = AnalyticsTracker()
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.25)
        tracker.reset_daily()
        stats = tracker.get_appliance_stats("app1")
        assert stats.energy_today_kwh == 0.0
        assert stats.runtime_today == timedelta(0)

    def test_reset_daily_clears_grid_export(self):
        """Daily reset clears grid export counter."""
        tracker = AnalyticsTracker()
        tracker.record_grid_export(2000, 3600)
        tracker.reset_daily()
        assert tracker.grid_export_kwh == 0.0

    def test_appliance_savings_accumulate(self):
        """Per-appliance savings accumulate across multiple cycles."""
        tracker = AnalyticsTracker(feed_in_tariff=0.0, normal_import_price=0.25)
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.25)  # 0.25 savings
        tracker.record_cycle("app1", 1000, 3600, "solar", 0.25)  # 0.25 savings
        stats = tracker.get_appliance_stats("app1")
        assert abs(stats.savings_today - 0.50) < 0.001

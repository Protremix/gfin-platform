"""Tests for Analytics — Module 30."""

import pytest

from services.analytics import (
    AnalyticsMetric,
    AnalyticsService,
    TimePeriod,
    TrendAnalysis,
    TrendDirection,
)


@pytest.fixture
def service():
    return AnalyticsService()


class TestAnalyticsMetric:
    def test_creation(self):
        m = AnalyticsMetric(name="fraud_count", value=42, unit="count")
        assert m.value == 42


class TestTrendAnalysis:
    def test_calculate_empty(self):
        t = TrendAnalysis(metric_name="test", period="DAILY")
        t.calculate()
        assert t.average == 0

    def test_calculate_upward(self):
        t = TrendAnalysis(metric_name="test", period="DAILY", data_points=[10, 15, 20, 25])
        t.calculate()
        assert t.direction == TrendDirection.UP.value
        assert t.average == 17.5
        assert t.minimum == 10
        assert t.maximum == 25
        assert t.change_percent == 150.0

    def test_calculate_downward(self):
        t = TrendAnalysis(metric_name="test", period="DAILY", data_points=[100, 80, 60])
        t.calculate()
        assert t.direction == TrendDirection.DOWN.value

    def test_calculate_stable(self):
        t = TrendAnalysis(metric_name="test", period="DAILY", data_points=[100, 101, 100])
        t.calculate()
        assert t.direction == TrendDirection.STABLE.value


class TestAnalyticsService:
    def test_record_metric(self, service):
        m = service.record_metric("fraud_count", 42, "count")
        assert m.name == "fraud_count"
        assert service.metric_count == 1

    def test_get_metrics(self, service):
        service.record_metric("a", 1)
        service.record_metric("b", 2)
        service.record_metric("a", 3)
        assert len(service.get_metrics()) == 3
        assert len(service.get_metrics(name="a")) == 2

    def test_get_metrics_by_period(self, service):
        service.record_metric("a", 1, period=TimePeriod.DAILY.value)
        service.record_metric("a", 2, period=TimePeriod.HOURLY.value)
        assert len(service.get_metrics(period=TimePeriod.DAILY.value)) == 1

    def test_analyze_trend(self, service):
        service.record_metric("fraud_count", 10)
        service.record_metric("fraud_count", 15)
        service.record_metric("fraud_count", 20)
        trend = service.analyze_trend("fraud_count")
        assert trend.direction == TrendDirection.UP.value
        assert trend.average == 15.0

    def test_analyze_trend_empty(self, service):
        trend = service.analyze_trend("nonexistent")
        assert trend.average == 0


class TestFraudStats:
    def test_record_fraud_stat(self, service):
        s = service.record_fraud_stat("phishing", count=5, total_value=1000)
        assert s.id.startswith("FS-")
        assert service.fraud_stat_count == 1

    def test_get_fraud_stat(self, service):
        s = service.record_fraud_stat("phishing")
        assert service.get_fraud_stat(s.id) is not None
        assert service.get_fraud_stat("nonexistent") is None

    def test_list_fraud_stats(self, service):
        service.record_fraud_stat("phishing")
        service.record_fraud_stat("ransomware")
        assert len(service.list_fraud_stats()) == 2
        assert len(service.list_fraud_stats(category="phishing")) == 1

    def test_fraud_summary_by_category(self, service):
        service.record_fraud_stat("phishing", count=5, total_value=1000)
        service.record_fraud_stat("phishing", count=3, total_value=500)
        service.record_fraud_stat("ransomware", count=2, total_value=5000)
        summary = service.get_fraud_summary_by_category()
        assert "phishing" in summary
        assert summary["phishing"]["count"] == 8
        assert summary["phishing"]["total_value"] == 1500

    def test_fraud_summary_empty(self, service):
        assert service.get_fraud_summary_by_category() == {}


class TestGeoData:
    def test_record_geo_data(self, service):
        dp = service.record_geo_data("Germany", count=5)
        assert dp.country == "Germany"
        assert service.geo_data_count == 1

    def test_record_geo_data_merge(self, service):
        service.record_geo_data("Germany", count=5, city="Berlin")
        service.record_geo_data("Germany", count=3, city="Berlin")
        assert service.geo_data_count == 1
        assert service.get_geo_data()[0].count == 8

    def test_get_geo_data(self, service):
        service.record_geo_data("Germany")
        service.record_geo_data("France")
        assert len(service.get_geo_data()) == 2
        assert len(service.get_geo_data(country="Germany")) == 1

    def test_get_top_countries(self, service):
        service.record_geo_data("Germany", count=10)
        service.record_geo_data("France", count=5)
        service.record_geo_data("Spain", count=15)
        top = service.get_top_countries(limit=2)
        assert len(top) == 2
        assert top[0].country == "Spain"
        assert top[0].count == 15

    def test_get_top_countries_empty(self, service):
        top = service.get_top_countries()
        assert len(top) == 0


class TestDashboard:
    def test_dashboard(self, service):
        service.record_metric("queries", 100)
        service.record_fraud_stat("phishing", count=5, total_value=1000)
        service.record_geo_data("Germany", count=10)
        dash = service.get_dashboard()
        assert dash["total_metrics"] == 1
        assert dash["total_fraud_count"] == 5
        assert dash["total_fraud_value"] == 1000
        assert "phishing" in dash["fraud_by_category"]
        assert len(dash["top_countries"]) >= 1

    def test_dashboard_empty(self, service):
        dash = service.get_dashboard()
        assert dash["total_metrics"] == 0
        assert dash["total_fraud_count"] == 0

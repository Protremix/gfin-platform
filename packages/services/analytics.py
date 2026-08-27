"""GFIN Analytics — Module 30.

Analytics and reporting: trend analysis, fraud statistics,
geographic distribution, and operational metrics dashboards.

Layer A: In-memory analytics framework
Layer B: Real OLAP/warehouse integration (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TimePeriod(StrEnum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class TrendDirection(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class AnalyticsMetric(BaseModel):
    """A single analytics metric."""

    name: str
    value: float = 0.0
    unit: str = ""
    period: str = TimePeriod.DAILY.value
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dimensions: dict[str, str] = Field(default_factory=dict)


class TrendAnalysis(BaseModel):
    """Trend analysis result."""

    metric_name: str
    period: str
    data_points: list[float] = Field(default_factory=list)
    direction: str = TrendDirection.STABLE.value
    change_percent: float = 0.0
    average: float = 0.0
    minimum: float = 0.0
    maximum: float = 0.0

    def calculate(self) -> None:
        if not self.data_points:
            return
        self.average = sum(self.data_points) / len(self.data_points)
        self.minimum = min(self.data_points)
        self.maximum = max(self.data_points)
        if len(self.data_points) >= 2:
            first = self.data_points[0]
            last = self.data_points[-1]
            if first > 0:
                self.change_percent = round(((last - first) / first) * 100, 2)
            if self.change_percent > 5:
                self.direction = TrendDirection.UP.value
            elif self.change_percent < -5:
                self.direction = TrendDirection.DOWN.value
            else:
                self.direction = TrendDirection.STABLE.value


class GeographicDataPoint(BaseModel):
    """A geographic data point."""

    country: str
    region: str = ""
    city: str = ""
    count: int = 0
    latitude: float = 0.0
    longitude: float = 0.0


class FraudStatistic(BaseModel):
    """A fraud statistic record."""

    id: str
    category: str
    subcategory: str = ""
    count: int = 0
    total_value: float = 0.0
    period: str = TimePeriod.DAILY.value
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsService:
    """Service for analytics and reporting.

    Per Master Spec: search analytics, fraud statistics, operational metrics.
    """

    def __init__(self) -> None:
        self._metrics: list[AnalyticsMetric] = []
        self._fraud_stats: dict[str, FraudStatistic] = {}
        self._geo_data: list[GeographicDataPoint] = []
        self._stat_counter = 0

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        period: str = TimePeriod.DAILY.value,
        dimensions: dict[str, str] | None = None,
    ) -> AnalyticsMetric:
        """Record an analytics metric."""
        metric = AnalyticsMetric(
            name=name,
            value=value,
            unit=unit,
            period=period,
            dimensions=dimensions or {},
        )
        self._metrics.append(metric)
        return metric

    def get_metrics(
        self,
        name: str | None = None,
        period: str | None = None,
    ) -> list[AnalyticsMetric]:
        metrics = list(self._metrics)
        if name:
            metrics = [m for m in metrics if m.name == name]
        if period:
            metrics = [m for m in metrics if m.period == period]
        return metrics

    def analyze_trend(
        self,
        metric_name: str,
        period: str = TimePeriod.DAILY.value,
    ) -> TrendAnalysis:
        """Analyze trend for a specific metric."""
        metrics = [m for m in self._metrics if m.name == metric_name and m.period == period]
        data_points = [m.value for m in metrics]
        trend = TrendAnalysis(
            metric_name=metric_name,
            period=period,
            data_points=data_points,
        )
        trend.calculate()
        return trend

    def record_fraud_stat(
        self,
        category: str,
        count: int = 1,
        total_value: float = 0.0,
        subcategory: str = "",
        period: str = TimePeriod.DAILY.value,
    ) -> FraudStatistic:
        """Record a fraud statistic."""
        self._stat_counter += 1
        stat = FraudStatistic(
            id=f"FS-{self._stat_counter:06d}",
            category=category,
            subcategory=subcategory,
            count=count,
            total_value=total_value,
            period=period,
        )
        self._fraud_stats[stat.id] = stat
        return stat

    def get_fraud_stat(self, stat_id: str) -> FraudStatistic | None:
        return self._fraud_stats.get(stat_id)

    def list_fraud_stats(
        self,
        category: str | None = None,
        period: str | None = None,
    ) -> list[FraudStatistic]:
        stats = list(self._fraud_stats.values())
        if category:
            stats = [s for s in stats if s.category == category]
        if period:
            stats = [s for s in stats if s.period == period]
        return stats

    def get_fraud_summary_by_category(self) -> dict[str, dict[str, Any]]:
        """Get fraud statistics summarized by category."""
        summary: dict[str, dict[str, Any]] = {}
        for stat in self._fraud_stats.values():
            cat = stat.category
            if cat not in summary:
                summary[cat] = {"count": 0, "total_value": 0.0, "records": 0}
            summary[cat]["count"] += stat.count
            summary[cat]["total_value"] += stat.total_value
            summary[cat]["records"] += 1
        return summary

    def record_geo_data(
        self,
        country: str,
        count: int = 1,
        region: str = "",
        city: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> GeographicDataPoint:
        """Record a geographic data point."""
        # Merge with existing if same location
        for dp in self._geo_data:
            if dp.country == country and dp.region == region and dp.city == city:
                dp.count += count
                return dp

        point = GeographicDataPoint(
            country=country,
            region=region,
            city=city,
            count=count,
            latitude=latitude,
            longitude=longitude,
        )
        self._geo_data.append(point)
        return point

    def get_geo_data(self, country: str | None = None) -> list[GeographicDataPoint]:
        if country:
            return [d for d in self._geo_data if d.country == country]
        return list(self._geo_data)

    def get_top_countries(self, limit: int = 10) -> list[GeographicDataPoint]:
        """Get top countries by fraud count."""
        by_country: dict[str, int] = {}
        for d in self._geo_data:
            by_country[d.country] = by_country.get(d.country, 0) + d.count
        sorted_countries = sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [GeographicDataPoint(country=c, count=n) for c, n in sorted_countries]

    def get_dashboard(self) -> dict[str, Any]:
        """Get a full analytics dashboard."""
        fraud_summary = self.get_fraud_summary_by_category()
        top_countries = self.get_top_countries(5)
        total_fraud_count = sum(s.count for s in self._fraud_stats.values())
        total_fraud_value = sum(s.total_value for s in self._fraud_stats.values())

        return {
            "total_metrics": len(self._metrics),
            "total_fraud_stats": len(self._fraud_stats),
            "total_fraud_count": total_fraud_count,
            "total_fraud_value": total_fraud_value,
            "fraud_by_category": fraud_summary,
            "top_countries": [{"country": c.country, "count": c.count} for c in top_countries],
            "geo_data_points": len(self._geo_data),
        }

    @property
    def metric_count(self) -> int:
        return len(self._metrics)

    @property
    def fraud_stat_count(self) -> int:
        return len(self._fraud_stats)

    @property
    def geo_data_count(self) -> int:
        return len(self._geo_data)

"""GFIN Observability — Module 34.

Metrics collection, health checks, distributed tracing, and system monitoring.
Per Master Spec: OpenTelemetry/Prometheus/Grafana.

Layer A: In-memory metrics, health, traces
Layer B: OpenTelemetry, Prometheus export, Grafana dashboards (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ───


class MetricType(StrEnum):
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


# ─── Models ───


class Metric(BaseModel):
    """A named metric with value, type, labels, timestamp."""

    name: str
    metric_type: str
    value: float = 0.0
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    description: str = ""


class HealthCheck(BaseModel):
    """System health check result."""

    component: str
    status: str = HealthStatus.HEALTHY.value
    latency_ms: float = 0.0
    message: str = ""
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraceSpan(BaseModel):
    """Distributed tracing span."""

    span_id: str
    trace_id: str
    operation: str
    parent_span_id: str = ""
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    duration_ms: float = 0.0
    attributes: dict[str, Any] = Field(default_factory=dict)
    status: str = "OK"

    def finish(self) -> None:
        self.end_time = datetime.now(UTC)
        if self.start_time and self.end_time:
            delta = (self.end_time - self.start_time).total_seconds() * 1000
            self.duration_ms = round(delta, 2)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


class SystemMetrics(BaseModel):
    """Aggregate system metrics snapshot."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_metrics: int = 0
    healthy_components: int = 0
    degraded_components: int = 0
    unhealthy_components: int = 0
    active_traces: int = 0
    counters: dict[str, float] = Field(default_factory=dict)
    gauges: dict[str, float] = Field(default_factory=dict)


# ─── Observability Service ───


class ObservabilityService:
    """Service for metrics collection, health checks, and tracing.

    Per Master Spec: OpenTelemetry/Prometheus/Grafana.
    """

    def __init__(self) -> None:
        self._metrics: list[Metric] = []
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._health_checks: dict[str, HealthCheck] = {}
        self._spans: dict[str, TraceSpan] = {}
        self._active_traces: dict[str, TraceSpan] = {}
        self._span_counter = 0

    def increment_counter(
        self, name: str, value: float = 1, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a counter metric."""
        self._counters[name] = self._counters.get(name, 0) + value
        self._metrics.append(
            Metric(
                name=name,
                metric_type=MetricType.COUNTER.value,
                value=value,
                labels=labels or {},
            )
        )

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        self._gauges[name] = value
        self._metrics.append(
            Metric(
                name=name,
                metric_type=MetricType.GAUGE.value,
                value=value,
                labels=labels or {},
            )
        )

    def record_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """Record a histogram observation."""
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
        self._metrics.append(
            Metric(
                name=name,
                metric_type=MetricType.HISTOGRAM.value,
                value=value,
                labels=labels or {},
            )
        )

    def get_counter(self, name: str) -> float:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0)

    def get_histogram(self, name: str) -> list[float]:
        return self._histograms.get(name, [])

    def record_health_check(
        self,
        component: str,
        status: str,
        latency_ms: float = 0,
        message: str = "",
    ) -> HealthCheck:
        """Record a health check for a component."""
        check = HealthCheck(
            component=component,
            status=status,
            latency_ms=latency_ms,
            message=message,
        )
        self._health_checks[component] = check
        return check

    def get_health_check(self, component: str) -> HealthCheck | None:
        return self._health_checks.get(component)

    def get_all_health_checks(self) -> list[HealthCheck]:
        return list(self._health_checks.values())

    def get_system_health(self) -> str:
        """Get overall system health status."""
        checks = list(self._health_checks.values())
        if not checks:
            return HealthStatus.HEALTHY.value
        if any(c.status == HealthStatus.UNHEALTHY.value for c in checks):
            return HealthStatus.UNHEALTHY.value
        if any(c.status == HealthStatus.DEGRADED.value for c in checks):
            return HealthStatus.DEGRADED.value
        return HealthStatus.HEALTHY.value

    def start_span(self, trace_id: str, operation: str, parent_span_id: str = "") -> TraceSpan:
        """Start a new trace span."""
        self._span_counter += 1
        span = TraceSpan(
            span_id=f"SPAN-{self._span_counter:06d}",
            trace_id=trace_id,
            operation=operation,
            parent_span_id=parent_span_id,
        )
        self._active_traces[span.span_id] = span
        self._spans[span.span_id] = span
        return span

    def finish_span(self, span_id: str, status: str = "OK") -> TraceSpan | None:
        """Finish a trace span."""
        span = self._active_traces.pop(span_id, None)
        if span is None:
            return None
        span.status = status
        span.finish()
        return span

    def get_span(self, span_id: str) -> TraceSpan | None:
        return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        """Get all spans for a trace."""
        return [s for s in self._spans.values() if s.trace_id == trace_id]

    def get_system_metrics(self) -> SystemMetrics:
        """Get a snapshot of system metrics."""
        checks = list(self._health_checks.values())
        return SystemMetrics(
            total_metrics=len(self._metrics),
            healthy_components=sum(1 for c in checks if c.status == HealthStatus.HEALTHY.value),
            degraded_components=sum(1 for c in checks if c.status == HealthStatus.DEGRADED.value),
            unhealthy_components=sum(1 for c in checks if c.status == HealthStatus.UNHEALTHY.value),
            active_traces=len(self._active_traces),
            counters=dict(self._counters),
            gauges=dict(self._gauges),
        )

    def get_metrics(self, name: str | None = None, metric_type: str | None = None) -> list[Metric]:
        """Get metrics with optional filters."""
        metrics = list(self._metrics)
        if name:
            metrics = [m for m in metrics if m.name == name]
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        return metrics

    @property
    def metric_count(self) -> int:
        return len(self._metrics)

    @property
    def span_count(self) -> int:
        return len(self._spans)

    @property
    def active_trace_count(self) -> int:
        return len(self._active_traces)

    @property
    def component_count(self) -> int:
        return len(self._health_checks)

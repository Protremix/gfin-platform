"""Tests for Observability — Module 34."""

import pytest

from services.observability import (
    HealthCheck,
    HealthStatus,
    Metric,
    MetricType,
    ObservabilityService,
    TraceSpan,
)


@pytest.fixture
def service():
    return ObservabilityService()


# ─── Metric Tests ───


class TestMetric:
    def test_creation(self):
        m = Metric(name="requests", metric_type=MetricType.COUNTER.value, value=1)
        assert m.value == 1
        assert m.timestamp is not None


# ─── HealthCheck Tests ───


class TestHealthCheck:
    def test_creation(self):
        hc = HealthCheck(component="api", status=HealthStatus.HEALTHY.value)
        assert hc.status == HealthStatus.HEALTHY.value
        assert hc.latency_ms == 0


# ─── TraceSpan Tests ───


class TestTraceSpan:
    def test_creation(self):
        span = TraceSpan(span_id="S1", trace_id="T1", operation="search")
        assert span.end_time is None
        assert span.duration_ms == 0

    def test_finish(self):
        span = TraceSpan(span_id="S1", trace_id="T1", operation="search")
        span.finish()
        assert span.end_time is not None
        assert span.duration_ms >= 0

    def test_set_attribute(self):
        span = TraceSpan(span_id="S1", trace_id="T1", operation="search")
        span.set_attribute("entity_count", 5)
        assert span.attributes["entity_count"] == 5


# ─── ObservabilityService Tests ───


class TestObservabilityService:
    def test_increment_counter(self, service):
        service.increment_counter("requests")
        service.increment_counter("requests", 5)
        assert service.get_counter("requests") == 6

    def test_set_gauge(self, service):
        service.set_gauge("temperature", 42.5)
        assert service.get_gauge("temperature") == 42.5
        service.set_gauge("temperature", 30)
        assert service.get_gauge("temperature") == 30

    def test_record_histogram(self, service):
        service.record_histogram("latency", 10)
        service.record_histogram("latency", 20)
        service.record_histogram("latency", 30)
        hist = service.get_histogram("latency")
        assert len(hist) == 3
        assert hist == [10, 20, 30]

    def test_get_counter_nonexistent(self, service):
        assert service.get_counter("nonexistent") == 0

    def test_get_gauge_nonexistent(self, service):
        assert service.get_gauge("nonexistent") == 0

    def test_get_histogram_nonexistent(self, service):
        assert service.get_histogram("nonexistent") == []

    def test_metric_count(self, service):
        service.increment_counter("a")
        service.set_gauge("b", 1)
        service.record_histogram("c", 1)
        assert service.metric_count == 3

    def test_get_metrics_filtered(self, service):
        service.increment_counter("a")
        service.set_gauge("b", 1)
        counters = service.get_metrics(metric_type=MetricType.COUNTER.value)
        assert len(counters) == 1
        assert counters[0].name == "a"

    def test_get_metrics_by_name(self, service):
        service.increment_counter("x", 1)
        service.increment_counter("x", 2)
        metrics = service.get_metrics(name="x")
        assert len(metrics) == 2


class TestHealthChecks:
    def test_record_health_check(self, service):
        service.record_health_check("api", HealthStatus.HEALTHY.value, 5.0)
        hc = service.get_health_check("api")
        assert hc is not None
        assert hc.status == HealthStatus.HEALTHY.value

    def test_get_health_check_nonexistent(self, service):
        assert service.get_health_check("nonexistent") is None

    def test_get_all_health_checks(self, service):
        service.record_health_check("api", HealthStatus.HEALTHY.value)
        service.record_health_check("db", HealthStatus.DEGRADED.value)
        checks = service.get_all_health_checks()
        assert len(checks) == 2

    def test_system_health_healthy(self, service):
        service.record_health_check("api", HealthStatus.HEALTHY.value)
        service.record_health_check("db", HealthStatus.HEALTHY.value)
        assert service.get_system_health() == HealthStatus.HEALTHY.value

    def test_system_health_degraded(self, service):
        service.record_health_check("api", HealthStatus.HEALTHY.value)
        service.record_health_check("db", HealthStatus.DEGRADED.value)
        assert service.get_system_health() == HealthStatus.DEGRADED.value

    def test_system_health_unhealthy(self, service):
        service.record_health_check("api", HealthStatus.UNHEALTHY.value)
        assert service.get_system_health() == HealthStatus.UNHEALTHY.value

    def test_system_health_empty(self, service):
        assert service.get_system_health() == HealthStatus.HEALTHY.value

    def test_component_count(self, service):
        service.record_health_check("api", HealthStatus.HEALTHY.value)
        service.record_health_check("db", HealthStatus.HEALTHY.value)
        assert service.component_count == 2


class TestTracing:
    def test_start_span(self, service):
        span = service.start_span("TRACE-001", "search_entity")
        assert span.span_id.startswith("SPAN-")
        assert span.operation == "search_entity"
        assert service.active_trace_count == 1

    def test_finish_span(self, service):
        span = service.start_span("TRACE-001", "search")
        finished = service.finish_span(span.span_id)
        assert finished is not None
        assert finished.end_time is not None
        assert finished.duration_ms >= 0
        assert service.active_trace_count == 0

    def test_finish_nonexistent_span(self, service):
        assert service.finish_span("nonexistent") is None

    def test_get_span(self, service):
        span = service.start_span("T1", "op")
        assert service.get_span(span.span_id) is not None
        assert service.get_span("nonexistent") is None

    def test_get_trace(self, service):
        s1 = service.start_span("T1", "op1")
        s2 = service.start_span("T1", "op2", parent_span_id=s1.span_id)
        service.finish_span(s1.span_id)
        service.finish_span(s2.span_id)
        trace = service.get_trace("T1")
        assert len(trace) == 2

    def test_span_with_parent(self, service):
        parent = service.start_span("T1", "parent")
        child = service.start_span("T1", "child", parent_span_id=parent.span_id)
        assert child.parent_span_id == parent.span_id

    def test_span_attributes(self, service):
        span = service.start_span("T1", "search")
        span.set_attribute("entity_count", 42)
        service.finish_span(span.span_id)
        stored = service.get_span(span.span_id)
        assert stored.attributes["entity_count"] == 42

    def test_span_count(self, service):
        service.start_span("T1", "op")
        assert service.span_count == 1


class TestSystemMetrics:
    def test_get_system_metrics(self, service):
        service.increment_counter("requests", 10)
        service.set_gauge("queue_size", 5)
        service.record_health_check("api", HealthStatus.HEALTHY.value)
        service.record_health_check("db", HealthStatus.DEGRADED.value)
        service.start_span("T1", "op")

        metrics = service.get_system_metrics()
        assert metrics.total_metrics == 2
        assert metrics.healthy_components == 1
        assert metrics.degraded_components == 1
        assert metrics.unhealthy_components == 0
        assert metrics.active_traces == 1
        assert "requests" in metrics.counters
        assert "queue_size" in metrics.gauges

    def test_system_metrics_empty(self, service):
        metrics = service.get_system_metrics()
        assert metrics.total_metrics == 0
        assert metrics.healthy_components == 0

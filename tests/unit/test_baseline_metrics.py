"""Tests for baseline performance metrics."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from observability.baseline_metrics import BaselineMetrics


class TestBaselineMetrics:
    """Test baseline performance metrics recording."""

    def test_create_baseline_metrics(self):
        """BaselineMetrics should create with all operations."""
        bm = BaselineMetrics()
        assert len(bm.OPERATIONS) == 8

    def test_record_latency(self):
        """Recording latency should store it."""
        bm = BaselineMetrics()
        bm.record("entity_create", 0.05)
        metrics = bm.get_metrics("entity_create")
        assert metrics is not None
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] == 0.05

    def test_record_multiple(self):
        """Recording multiple latencies should store all."""
        bm = BaselineMetrics()
        for i in range(100):
            bm.record("entity_query", 0.001 * (i + 1))
        metrics = bm.get_metrics("entity_query")
        assert len(metrics.latencies) == 100

    def test_percentiles(self):
        """Percentiles should be correctly calculated."""
        bm = BaselineMetrics()
        for i in range(100):
            bm.record("entity_create", 0.001 * (i + 1))
        metrics = bm.get_metrics("entity_create")
        assert metrics.p50 > 0
        assert metrics.p95 >= metrics.p50
        assert metrics.p99 >= metrics.p95

    def test_p50_is_median(self):
        """p50 should approximate the median."""
        bm = BaselineMetrics()
        for _i in range(100):
            bm.record("entity_query", 0.01)
        metrics = bm.get_metrics("entity_query")
        assert abs(metrics.p50 - 0.01) < 0.001

    def test_p95_less_than_max(self):
        """p95 should be less than or equal to max."""
        bm = BaselineMetrics()
        for i in range(100):
            bm.record("entity_create", 0.001 * (i + 1))
        metrics = bm.get_metrics("entity_create")
        assert metrics.p95 <= metrics.max_latency

    def test_min_max_mean(self):
        """Min, max, mean should be correct."""
        bm = BaselineMetrics()
        for v in [0.01, 0.02, 0.03, 0.04, 0.05]:
            bm.record("entity_create", v)
        metrics = bm.get_metrics("entity_create")
        assert metrics.min_latency == 0.01
        assert metrics.max_latency == 0.05
        assert abs(metrics.mean_latency - 0.03) < 0.001

    def test_slo_check_pass(self):
        """SLO check should pass when p95 is within target."""
        bm = BaselineMetrics()
        for _ in range(100):
            bm.record("cache_get", 0.001)  # 1ms, SLO is 5ms
        passes, p95, target = bm.check_slo("cache_get")
        assert passes
        assert p95 <= target

    def test_slo_check_fail(self):
        """SLO check should fail when p95 exceeds target."""
        bm = BaselineMetrics()
        for _ in range(100):
            bm.record("cache_get", 0.01)  # 10ms, SLO is 5ms
        passes, p95, target = bm.check_slo("cache_get")
        assert not passes
        assert p95 > target

    def test_check_all_slos(self):
        """check_all_slos should return results for all operations."""
        bm = BaselineMetrics()
        results = bm.check_all_slos()
        assert len(results) == 8
        for op in bm.OPERATIONS:
            assert op in results
            assert "passes" in results[op]
            assert "p95_ms" in results[op]
            assert "target_ms" in results[op]

    def test_export_json(self):
        """Export to JSON should be serializable."""
        bm = BaselineMetrics()
        bm.record("entity_create", 0.05)
        bm.record("entity_query", 0.02)
        data = bm.export_json()
        assert "entity_create" in data
        assert "entity_query" in data
        assert "latency_ms" in data["entity_create"]

    def test_export_slo_report(self):
        """Export SLO report should include all operations."""
        bm = BaselineMetrics()
        bm.record("entity_create", 0.05)
        report = bm.export_slo_report()
        assert "slo_results" in report
        assert "total_operations" in report
        assert report["total_operations"] == 8

    def test_time_operation_context_manager(self):
        """Time operation context manager should record latency."""
        bm = BaselineMetrics()
        with bm.time_operation("entity_create"):
            time.sleep(0.01)
        metrics = bm.get_metrics("entity_create")
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] > 0

    def test_empty_metrics_zero_percentiles(self):
        """Empty metrics should return 0 for percentiles."""
        bm = BaselineMetrics()
        metrics = bm.get_metrics("entity_create")
        assert metrics.p50 == 0.0
        assert metrics.p95 == 0.0
        assert metrics.p99 == 0.0

    def test_throughput_recording(self):
        """Throughput should be recorded and averaged."""
        bm = BaselineMetrics()
        bm.record("entity_create", 0.01, throughput=1000)
        bm.record("entity_create", 0.01, throughput=2000)
        metrics = bm.get_metrics("entity_create")
        assert metrics.mean_throughput == 1500

    def test_memory_recording(self):
        """Memory usage should be recorded and averaged."""
        bm = BaselineMetrics()
        bm.record("entity_create", 0.01, memory_mb=100)
        bm.record("entity_create", 0.01, memory_mb=200)
        metrics = bm.get_metrics("entity_create")
        assert metrics.mean_memory == 150

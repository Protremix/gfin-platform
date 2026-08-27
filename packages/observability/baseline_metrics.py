"""Baseline performance metrics for GFIN operations.

Per Luna Directive — Focus Area 3: Record baseline latency, throughput,
memory, and queue behavior.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OperationMetrics:
    """Metrics for a single operation type."""

    name: str
    latencies: list[float] = field(default_factory=list)
    throughput_samples: list[float] = field(default_factory=list)
    memory_samples: list[float] = field(default_factory=list)

    def record_latency(self, seconds: float) -> None:
        self.latencies.append(seconds)

    def record_throughput(self, ops_per_sec: float) -> None:
        self.throughput_samples.append(ops_per_sec)

    def record_memory(self, mb: float) -> None:
        self.memory_samples.append(mb)

    def percentile(self, p: float) -> float:
        """Calculate the p-th percentile (p=50 for p50, p=95 for p95)."""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * p / 100)
        if idx >= len(sorted_lat):
            idx = len(sorted_lat) - 1
        return sorted_lat[idx]

    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0.0

    @property
    def mean_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def p50(self) -> float:
        return self.percentile(50)

    @property
    def p95(self) -> float:
        return self.percentile(95)

    @property
    def p99(self) -> float:
        return self.percentile(99)

    @property
    def mean_throughput(self) -> float:
        return statistics.mean(self.throughput_samples) if self.throughput_samples else 0.0

    @property
    def mean_memory(self) -> float:
        return statistics.mean(self.memory_samples) if self.memory_samples else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "samples": len(self.latencies),
            "latency_ms": {
                "min": self.min_latency * 1000,
                "max": self.max_latency * 1000,
                "mean": self.mean_latency * 1000,
                "p50": self.p50 * 1000,
                "p95": self.p95 * 1000,
                "p99": self.p99 * 1000,
            },
            "throughput_ops_sec": self.mean_throughput,
            "memory_mb": self.mean_memory,
        }


class BaselineMetrics:
    """Records and stores performance baselines for GFIN operations."""

    OPERATIONS = [
        "entity_create",
        "entity_query",
        "graph_traverse",
        "search_query",
        "evidence_store",
        "event_publish",
        "cache_get",
        "cache_set",
    ]

    # SLO targets in milliseconds
    SLO_TARGETS_MS = {
        "entity_create": 100,
        "entity_query": 50,
        "graph_traverse": 200,
        "search_query": 100,
        "evidence_store": 150,
        "event_publish": 10,
        "cache_get": 5,
        "cache_set": 5,
    }

    def __init__(self) -> None:
        self._metrics: dict[str, OperationMetrics] = {
            op: OperationMetrics(name=op) for op in self.OPERATIONS
        }

    def record(self, operation: str, latency_seconds: float, throughput: float = 0, memory_mb: float = 0) -> None:
        """Record a performance measurement."""
        if operation not in self._metrics:
            self._metrics[operation] = OperationMetrics(name=operation)
        self._metrics[operation].record_latency(latency_seconds)
        if throughput > 0:
            self._metrics[operation].record_throughput(throughput)
        if memory_mb > 0:
            self._metrics[operation].record_memory(memory_mb)

    def time_operation(self, operation: str):
        """Context manager to time an operation."""
        class Timer:
            def __init__(self, metrics, op):
                self.metrics = metrics
                self.op = op
                self.start = 0.0

            def __enter__(self):
                self.start = time.perf_counter()
                return self

            def __exit__(self, *args):
                elapsed = time.perf_counter() - self.start
                self.metrics.record(self.op, elapsed)

        return Timer(self, operation)

    def get_metrics(self, operation: str) -> OperationMetrics | None:
        """Get metrics for a specific operation."""
        return self._metrics.get(operation)

    def check_slo(self, operation: str) -> tuple[bool, float, float]:
        """Check if operation meets its SLO. Returns (passes, p95_ms, target_ms)."""
        metrics = self._metrics.get(operation)
        if metrics is None or not metrics.latencies:
            return False, 0.0, self.SLO_TARGETS_MS.get(operation, 0)

        p95_ms = metrics.p95 * 1000
        target_ms = self.SLO_TARGETS_MS.get(operation, 0)
        return p95_ms <= target_ms, p95_ms, target_ms

    def check_all_slos(self) -> dict[str, dict[str, Any]]:
        """Check SLOs for all operations. Returns per-operation pass/fail."""
        results: dict[str, dict[str, Any]] = {}
        for op in self.OPERATIONS:
            passes, p95, target = self.check_slo(op)
            results[op] = {
                "passes": passes,
                "p95_ms": p95,
                "target_ms": target,
                "samples": len(self._metrics[op].latencies) if self._metrics.get(op) else 0,
            }
        return results

    def export_json(self) -> dict[str, Any]:
        """Export all metrics to a JSON-serializable dict."""
        return {
            op: metrics.to_dict()
            for op, metrics in self._metrics.items()
            if metrics.latencies
        }

    def export_slo_report(self) -> dict[str, Any]:
        """Export SLO compliance report."""
        return {
            "timestamp": time.time(),
            "slo_results": self.check_all_slos(),
            "total_operations": len(self.OPERATIONS),
            "operations_with_data": sum(1 for m in self._metrics.values() if m.latencies),
        }

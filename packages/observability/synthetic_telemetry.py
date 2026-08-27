"""Synthetic telemetry generator for GFIN monitoring.

Per Luna Directive — Focus Area 3: Generate synthetic metrics for testing.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

METRIC_NAMES = [
    "gfin_http_request_duration_seconds",
    "gfin_event_bus_published_total",
    "gfin_entity_count",
    "gfin_search_query_duration_seconds",
    "gfin_evidence_vault_items",
    "gfin_cache_hit_rate",
    "gfin_graph_query_duration_seconds",
    "gfin_ai_gateway_tokens_used",
    "gfin_kafka_consumer_lag",
    "gfin_error_rate",
]

METRIC_LABELS = {
    "gfin_http_request_duration_seconds": {"method": "GET", "status": "200", "endpoint": "/api/entities"},
    "gfin_event_bus_published_total": {"topic": "entity_events", "source": "api"},
    "gfin_entity_count": {"entity_type": "EMAIL"},
    "gfin_search_query_duration_seconds": {"index": "entities"},
    "gfin_evidence_vault_items": {"classification": "COMMUNITY"},
    "gfin_cache_hit_rate": {"service": "entity_service"},
    "gfin_graph_query_duration_seconds": {"query_type": "path"},
    "gfin_ai_gateway_tokens_used": {"model": "gpt-5.6-luna", "task": "reasoning"},
    "gfin_kafka_consumer_lag": {"topic": "entity_events", "consumer_group": "entity-processor"},
    "gfin_error_rate": {"service": "api", "severity": "warning"},
}


class SyntheticTelemetryGenerator:
    """Generates synthetic Prometheus-format metrics for testing."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)  # noqa: S311

    def generate_metric_line(self, metric_name: str, value: float, timestamp: int) -> str:
        """Generate a single Prometheus-format metric line."""
        labels = METRIC_LABELS.get(metric_name, {})
        label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        if label_str:
            return f"{metric_name}{{{label_str}}} {value} {timestamp}"
        return f"{metric_name} {value} {timestamp}"

    def generate_metric_series(self, metric_name: str, duration_hours: int = 24, interval_seconds: int = 60) -> list[str]:
        """Generate a time series for a single metric."""
        lines: list[str] = []
        now = datetime.now(UTC)
        points = int(duration_hours * 3600 / interval_seconds)

        for i in range(points):
            ts = int((now - timedelta(seconds=(points - i) * interval_seconds)).timestamp())
            value = self._generate_value(metric_name, i, points)
            lines.append(self.generate_metric_line(metric_name, value, ts))

        return lines

    def _generate_value(self, metric_name: str, i: int, total: int) -> float:
        """Generate a realistic value for the given metric."""
        progress = i / total if total > 0 else 0
        noise = self._rng.gauss(0, 0.1)

        if "duration" in metric_name:
            return max(0.001, 0.05 + 0.02 * progress + abs(noise) * 0.01)
        elif "count" in metric_name or "items" in metric_name or "tokens" in metric_name:
            return max(0, 1000 * (1 + progress) + noise * 100)
        elif "rate" in metric_name:
            return max(0, min(1, 0.85 + noise * 0.05))
        elif "lag" in metric_name:
            return max(0, 50 + noise * 10)
        elif "error" in metric_name:
            return max(0, abs(noise) * 0.01)
        else:
            return max(0, 100 + noise * 10)

    def generate_all_metrics(self, duration_hours: int = 24, interval_seconds: int = 60) -> dict[str, list[str]]:
        """Generate all metrics for the specified duration."""
        return {
            name: self.generate_metric_series(name, duration_hours, interval_seconds)
            for name in METRIC_NAMES
        }

    def generate_summary(self, duration_hours: int = 24) -> dict[str, dict[str, float]]:
        """Generate a summary of min/max/mean for each metric."""
        summary: dict[str, dict[str, float]] = {}
        for name in METRIC_NAMES:
            series = self.generate_metric_series(name, duration_hours, interval_seconds=60)
            values = [float(line.split()[-2]) for line in series]
            if values:
                summary[name] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "count": len(values),
                }
        return summary

    @staticmethod
    def get_metric_names() -> list[str]:
        """Return all defined metric names."""
        return list(METRIC_NAMES)

    @staticmethod
    def validate_metric_line(line: str) -> bool:
        """Validate that a metric line is in proper Prometheus format."""
        parts = line.rsplit(" ", 2)
        if len(parts) < 3:
            return False
        metric_part = parts[0]
        try:
            float(parts[1])
            int(parts[2])
        except (ValueError, IndexError):
            return False
        # Check metric name starts with valid char
        return metric_part.split("{")[0].replace("_", "").replace(":", "").isalnum()

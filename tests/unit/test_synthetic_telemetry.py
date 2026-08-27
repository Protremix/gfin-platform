"""Tests for synthetic telemetry generator."""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from observability.synthetic_telemetry import METRIC_NAMES, SyntheticTelemetryGenerator


class TestSyntheticTelemetry:
    """Test synthetic telemetry generation."""

    def test_generator_creates_instance(self):
        """Generator should create successfully."""
        gen = SyntheticTelemetryGenerator()
        assert gen is not None

    def test_all_10_metrics_defined(self):
        """All 10 metric names should be defined."""
        assert len(METRIC_NAMES) == 10

    def test_metric_names_are_valid(self):
        """Metric names should follow Prometheus naming convention."""
        for name in METRIC_NAMES:
            assert name.startswith("gfin_")
            assert "_" in name

    def test_generate_single_metric_line(self):
        """A single metric line should be valid Prometheus format."""
        gen = SyntheticTelemetryGenerator()
        line = gen.generate_metric_line("gfin_entity_count", 1000, 1700000000)
        assert SyntheticTelemetryGenerator.validate_metric_line(line)

    def test_metric_line_has_labels(self):
        """Metric line should include labels."""
        gen = SyntheticTelemetryGenerator()
        line = gen.generate_metric_line("gfin_entity_count", 1000, 1700000000)
        assert "{" in line
        assert "}" in line

    def test_metric_line_has_value_and_timestamp(self):
        """Metric line should have value and timestamp."""
        gen = SyntheticTelemetryGenerator()
        line = gen.generate_metric_line("gfin_entity_count", 1000, 1700000000)
        parts = line.rsplit(" ", 2)
        assert float(parts[1]) == 1000
        assert int(parts[2]) == 1700000000

    def test_generate_time_series(self):
        """Time series should generate correct number of points."""
        gen = SyntheticTelemetryGenerator()
        series = gen.generate_metric_series("gfin_entity_count", duration_hours=1, interval_seconds=60)
        assert len(series) == 60  # 1 hour / 60 seconds = 60 points

    def test_generate_24h_series(self):
        """24-hour series should generate 1440 points at 1-minute intervals."""
        gen = SyntheticTelemetryGenerator()
        series = gen.generate_metric_series("gfin_entity_count", duration_hours=24, interval_seconds=60)
        assert len(series) == 1440

    def test_generate_all_metrics(self):
        """Generate all metrics should return all 10 metrics."""
        gen = SyntheticTelemetryGenerator()
        all_metrics = gen.generate_all_metrics(duration_hours=1, interval_seconds=300)
        assert len(all_metrics) == 10
        for name in METRIC_NAMES:
            assert name in all_metrics
            assert len(all_metrics[name]) > 0

    def test_all_lines_valid_format(self):
        """All generated lines should be valid Prometheus format."""
        gen = SyntheticTelemetryGenerator()
        all_metrics = gen.generate_all_metrics(duration_hours=1, interval_seconds=300)
        for _name, lines in all_metrics.items():
            for line in lines:
                assert SyntheticTelemetryGenerator.validate_metric_line(line), f"Invalid line: {line}"

    def test_generate_summary(self):
        """Summary should include min, max, mean for each metric."""
        gen = SyntheticTelemetryGenerator()
        summary = gen.generate_summary(duration_hours=1)
        assert len(summary) == 10
        for _name, stats in summary.items():
            assert "min" in stats
            assert "max" in stats
            assert "mean" in stats
            assert stats["min"] <= stats["mean"] <= stats["max"]

    def test_values_are_positive(self):
        """Generated values should be positive."""
        gen = SyntheticTelemetryGenerator()
        series = gen.generate_metric_series("gfin_entity_count", duration_hours=1)
        for line in series:
            value = float(line.rsplit(" ", 2)[1])
            assert value >= 0

    def test_get_metric_names(self):
        """get_metric_names should return all metric names."""
        names = SyntheticTelemetryGenerator.get_metric_names()
        assert len(names) == 10
        assert "gfin_entity_count" in names
        assert "gfin_error_rate" in names

    def test_validate_invalid_line(self):
        """Invalid metric line should fail validation."""
        assert not SyntheticTelemetryGenerator.validate_metric_line("invalid")
        assert not SyntheticTelemetryGenerator.validate_metric_line("")

    def test_deterministic_with_seed(self):
        """Same seed should produce same output."""
        gen1 = SyntheticTelemetryGenerator(seed=42)
        gen2 = SyntheticTelemetryGenerator(seed=42)
        series1 = gen1.generate_metric_series("gfin_entity_count", duration_hours=1, interval_seconds=60)
        series2 = gen2.generate_metric_series("gfin_entity_count", duration_hours=1, interval_seconds=60)
        assert series1 == series2

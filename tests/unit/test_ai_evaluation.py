"""Tests for AI Evaluation — Module 37."""

import pytest

from services.ai_evaluation import (
    AIEvaluationService,
    EvalMetric,
    EvalMetricType,
    EvalResult,
    EvalStatus,
)


@pytest.fixture
def service():
    return AIEvaluationService()


# ─── EvalMetric Tests ───


class TestEvalMetric:
    def test_check_pass_meets_target(self):
        m = EvalMetric(metric_type=EvalMetricType.ACCURACY.value, value=0.95, target=0.90)
        m.check_pass()
        assert m.passed is True

    def test_check_pass_below_target(self):
        m = EvalMetric(metric_type=EvalMetricType.ACCURACY.value, value=0.80, target=0.90)
        m.check_pass()
        assert m.passed is False

    def test_no_target(self):
        m = EvalMetric(metric_type=EvalMetricType.LATENCY_MS.value, value=100)
        m.check_pass()
        assert m.passed is None


# ─── EvalResult Tests ───


class TestEvalResult:
    def test_add_metric(self):
        r = EvalResult(id="R1", model_id="gpt-5", task_type="fraud_classification")
        r.add_metric(EvalMetric(metric_type=EvalMetricType.ACCURACY.value, value=0.95, target=0.90))
        assert len(r.metrics) == 1
        assert r.metrics[0].passed is True

    def test_all_passed_true(self):
        r = EvalResult(id="R1", model_id="m1", task_type="t1")
        r.add_metric(EvalMetric(metric_type="A", value=0.95, target=0.90))
        r.add_metric(EvalMetric(metric_type="B", value=0.88, target=0.85))
        assert r.all_passed is True

    def test_all_passed_false(self):
        r = EvalResult(id="R1", model_id="m1", task_type="t1")
        r.add_metric(EvalMetric(metric_type="A", value=0.95, target=0.90))
        r.add_metric(EvalMetric(metric_type="B", value=0.80, target=0.85))
        assert r.all_passed is False

    def test_all_passed_empty(self):
        r = EvalResult(id="R1", model_id="m1", task_type="t1")
        assert r.all_passed is True

    def test_start_and_complete(self):
        r = EvalResult(id="R1", model_id="m1", task_type="t1")
        r.start()
        assert r.status == EvalStatus.RUNNING.value
        r.complete()
        assert r.status == EvalStatus.COMPLETED.value
        assert r.completed_at is not None


# ─── AIEvaluationService Tests ───


class TestAIEvaluationService:
    def test_create_evaluation(self, service):
        r = service.create_evaluation("gpt-5", "fraud_classification")
        assert r.id.startswith("EVAL-")
        assert service.result_count == 1

    def test_run_evaluation(self, service):
        r = service.run_evaluation(
            "gpt-5",
            "fraud_classification",
            [
                {"metric_type": EvalMetricType.ACCURACY.value, "value": 0.95, "target": 0.90},
                {"metric_type": EvalMetricType.PRECISION.value, "value": 0.92, "target": 0.85},
            ],
        )
        assert r.status == EvalStatus.COMPLETED.value
        assert len(r.metrics) == 2
        assert r.all_passed is True

    def test_run_evaluation_failed(self, service):
        r = service.run_evaluation(
            "gpt-5",
            "fraud_classification",
            [
                {"metric_type": EvalMetricType.ACCURACY.value, "value": 0.80, "target": 0.90},
            ],
        )
        assert r.all_passed is False

    def test_get_result(self, service):
        r = service.create_evaluation("m1", "t1")
        assert service.get_result(r.id) is not None
        assert service.get_result("nonexistent") is None

    def test_list_results(self, service):
        service.create_evaluation("m1", "t1")
        service.create_evaluation("m2", "t1")
        service.create_evaluation("m1", "t2")
        assert len(service.list_results()) == 3
        assert len(service.list_results(model_id="m1")) == 2
        assert len(service.list_results(task_type="t1")) == 2

    def test_list_results_by_status(self, service):
        service.run_evaluation("m1", "t1", [{"metric_type": "A", "value": 0.9, "target": 0.8}])
        service.create_evaluation("m2", "t1")
        completed = service.list_results(status=EvalStatus.COMPLETED.value)
        pending = service.list_results(status=EvalStatus.PENDING.value)
        assert len(completed) == 1
        assert len(pending) == 1


# ─── Model Comparison Tests ───


class TestModelComparison:
    def test_compare_models(self, service):
        cmp = service.compare_models(
            "model-a",
            "model-b",
            "fraud_classification",
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.95, "target": 0.90}],
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.85, "target": 0.90}],
        )
        assert cmp.winner == "model-a"

    def test_compare_models_tie(self, service):
        cmp = service.compare_models(
            "model-a",
            "model-b",
            "fraud_classification",
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.95, "target": 0.90}],
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.95, "target": 0.90}],
        )
        assert cmp.winner == "TIE"

    def test_compare_models_b_wins(self, service):
        cmp = service.compare_models(
            "model-a",
            "model-b",
            "fraud_classification",
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.85, "target": 0.90}],
            [{"metric_type": EvalMetricType.ACCURACY.value, "value": 0.95, "target": 0.90}],
        )
        assert cmp.winner == "model-b"

    def test_get_comparison(self, service):
        cmp = service.compare_models(
            "a",
            "b",
            "t1",
            [{"metric_type": "A", "value": 0.9, "target": 0.8}],
            [{"metric_type": "A", "value": 0.85, "target": 0.8}],
        )
        assert service.get_comparison(cmp.id) is not None
        assert service.get_comparison("nonexistent") is None

    def test_list_comparisons(self, service):
        service.compare_models(
            "a",
            "b",
            "t1",
            [{"metric_type": "A", "value": 0.9, "target": 0.8}],
            [{"metric_type": "A", "value": 0.85, "target": 0.8}],
        )
        assert len(service.list_comparisons()) == 1


# ─── Summary Tests ───


class TestEvaluationSummary:
    def test_summary(self, service):
        service.run_evaluation(
            "m1", "fraud_classification", [{"metric_type": "A", "value": 0.95, "target": 0.90}]
        )
        service.run_evaluation(
            "m2", "entity_extraction", [{"metric_type": "A", "value": 0.80, "target": 0.90}]
        )
        summary = service.get_evaluation_summary()
        assert summary["total_evaluations"] == 2
        assert summary["completed"] == 2
        assert summary["all_passed"] == 1
        assert "fraud_classification" in summary["by_task_type"]
        assert "entity_extraction" in summary["by_task_type"]

    def test_summary_empty(self, service):
        summary = service.get_evaluation_summary()
        assert summary["total_evaluations"] == 0

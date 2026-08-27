"""GFIN AI Evaluation — Module 37.

AI model evaluation framework: benchmarks, quality metrics, model comparison,
and evaluation reporting. Per Directive: AI model selection per task type
(D-PENDING-03) requires evaluation.

Layer A: In-memory evaluation framework
Layer B: Automated CI/CD evaluation pipeline (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvalMetricType(StrEnum):
    ACCURACY = "ACCURACY"
    PRECISION = "PRECISION"
    RECALL = "RECALL"
    F1_SCORE = "F1_SCORE"
    LATENCY_MS = "LATENCY_MS"
    HALLUCINATION_RATE = "HALLUCINATION_RATE"
    FALSE_POSITIVE_RATE = "FALSE_POSITIVE_RATE"


class EvalStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvalMetric(BaseModel):
    """A single evaluation metric."""

    metric_type: str
    value: float
    target: float | None = None
    passed: bool | None = None
    description: str = ""

    def check_pass(self) -> None:
        if self.target is not None:
            self.passed = self.value >= self.target


class EvalResult(BaseModel):
    """Result of an AI model evaluation."""

    id: str
    model_id: str
    task_type: str
    status: str = EvalStatus.PENDING.value
    metrics: list[EvalMetric] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""

    def add_metric(self, metric: EvalMetric) -> None:
        metric.check_pass()
        self.metrics.append(metric)

    @property
    def all_passed(self) -> bool:
        if not self.metrics:
            return True
        return all(m.passed for m in self.metrics if m.passed is not None)

    def start(self) -> None:
        self.status = EvalStatus.RUNNING.value
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        self.status = EvalStatus.COMPLETED.value
        self.completed_at = datetime.now(UTC)


class ModelComparison(BaseModel):
    """Comparison between two models on the same task."""

    id: str
    model_a: str
    model_b: str
    task_type: str
    result_a: EvalResult | None = None
    result_b: EvalResult | None = None
    winner: str = ""

    def determine_winner(self) -> str:
        """Determine which model performed better overall."""
        if self.result_a is None or self.result_b is None:
            return ""
        passed_a = self.result_a.all_passed
        passed_b = self.result_b.all_passed
        if passed_a and not passed_b:
            self.winner = self.model_a
        elif passed_b and not passed_a:
            self.winner = self.model_b
        elif passed_a and passed_b:
            # Both passed — compare metrics
            score_a = sum(m.value for m in self.result_a.metrics if m.target is not None)
            score_b = sum(m.value for m in self.result_b.metrics if m.target is not None)
            if score_a > score_b:
                self.winner = self.model_a
            elif score_b > score_a:
                self.winner = self.model_b
            else:
                self.winner = "TIE"
        else:
            self.winner = "TIE"
        return self.winner


class AIEvaluationService:
    """Service for AI model evaluation and comparison.

    Per D-PENDING-03: AI model selection per task type requires evaluation.
    """

    def __init__(self) -> None:
        self._results: dict[str, EvalResult] = {}
        self._comparisons: dict[str, ModelComparison] = {}
        self._result_counter = 0
        self._comparison_counter = 0

    def create_evaluation(self, model_id: str, task_type: str, notes: str = "") -> EvalResult:
        self._result_counter += 1
        result = EvalResult(
            id=f"EVAL-{self._result_counter:06d}",
            model_id=model_id,
            task_type=task_type,
            notes=notes,
        )
        self._results[result.id] = result
        return result

    def run_evaluation(
        self,
        model_id: str,
        task_type: str,
        metrics: list[dict[str, Any]],
    ) -> EvalResult:
        """Run an evaluation with provided metrics."""
        result = self.create_evaluation(model_id, task_type)
        result.start()

        for m in metrics:
            metric = EvalMetric(
                metric_type=m.get("metric_type", EvalMetricType.ACCURACY.value),
                value=m.get("value", 0),
                target=m.get("target"),
                description=m.get("description", ""),
            )
            result.add_metric(metric)

        result.complete()
        return result

    def get_result(self, result_id: str) -> EvalResult | None:
        return self._results.get(result_id)

    def list_results(
        self,
        model_id: str | None = None,
        task_type: str | None = None,
        status: str | None = None,
    ) -> list[EvalResult]:
        results = list(self._results.values())
        if model_id:
            results = [r for r in results if r.model_id == model_id]
        if task_type:
            results = [r for r in results if r.task_type == task_type]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def compare_models(
        self,
        model_a: str,
        model_b: str,
        task_type: str,
        metrics_a: list[dict[str, Any]],
        metrics_b: list[dict[str, Any]],
    ) -> ModelComparison:
        """Compare two models on the same task."""
        result_a = self.run_evaluation(model_a, task_type, metrics_a)
        result_b = self.run_evaluation(model_b, task_type, metrics_b)

        self._comparison_counter += 1
        comparison = ModelComparison(
            id=f"CMP-{self._comparison_counter:06d}",
            model_a=model_a,
            model_b=model_b,
            task_type=task_type,
            result_a=result_a,
            result_b=result_b,
        )
        comparison.determine_winner()
        self._comparisons[comparison.id] = comparison
        return comparison

    def get_comparison(self, comparison_id: str) -> ModelComparison | None:
        return self._comparisons.get(comparison_id)

    def list_comparisons(self) -> list[ModelComparison]:
        return list(self._comparisons.values())

    def get_evaluation_summary(self) -> dict[str, Any]:
        """Get summary of all evaluations."""
        results = list(self._results.values())
        return {
            "total_evaluations": len(results),
            "completed": sum(1 for r in results if r.status == EvalStatus.COMPLETED.value),
            "all_passed": sum(1 for r in results if r.all_passed),
            "by_task_type": self._count_by_task_type(),
        }

    def _count_by_task_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._results.values():
            counts[r.task_type] = counts.get(r.task_type, 0) + 1
        return counts

    @property
    def result_count(self) -> int:
        return len(self._results)

    @property
    def comparison_count(self) -> int:
        return len(self._comparisons)

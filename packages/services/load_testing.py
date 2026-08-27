"""GFIN Load Testing — Module 38.

Load test framework: test scenarios, throughput measurement, performance
benchmarks, and scalability validation. Per Architecture Review: RTO/RPO
must be validated under load.

Layer A: In-memory load test simulation
Layer B: k6/JMeter integration, real load generation (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class LoadTestStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class LoadTestScenario(BaseModel):
    """A load test scenario."""

    id: str
    name: str
    target_rps: int = 100
    duration_seconds: int = 60
    concurrent_users: int = 10
    description: str = ""
    status: str = LoadTestStatus.PENDING.value

    @property
    def total_requests(self) -> int:
        return self.target_rps * self.duration_seconds


class LoadTestResult(BaseModel):
    """Result of a load test."""

    id: str
    scenario_id: str
    status: str = LoadTestStatus.PENDING.value
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    actual_rps: float = 0.0
    error_rate: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""

    def start(self) -> None:
        self.status = LoadTestStatus.RUNNING.value
        self.started_at = datetime.now(UTC)

    def complete(self, passed: bool) -> None:
        self.status = LoadTestStatus.PASSED.value if passed else LoadTestStatus.FAILED.value
        self.completed_at = datetime.now(UTC)
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    @property
    def passed_threshold(self) -> bool:
        return self.error_rate < 0.01 and self.p95_latency_ms < 500


class LoadTestService:
    """Service for running and tracking load tests.

    Per Architecture Review: performance must be validated under load.
    """

    def __init__(self) -> None:
        self._scenarios: dict[str, LoadTestScenario] = {}
        self._results: dict[str, LoadTestResult] = {}
        self._scenario_counter = 0
        self._result_counter = 0

    def create_scenario(
        self,
        name: str,
        target_rps: int = 100,
        duration_seconds: int = 60,
        concurrent_users: int = 10,
        description: str = "",
    ) -> LoadTestScenario:
        self._scenario_counter += 1
        scenario = LoadTestScenario(
            id=f"LT-{self._scenario_counter:06d}",
            name=name,
            target_rps=target_rps,
            duration_seconds=duration_seconds,
            concurrent_users=concurrent_users,
            description=description,
        )
        self._scenarios[scenario.id] = scenario
        return scenario

    def get_scenario(self, scenario_id: str) -> LoadTestScenario | None:
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> list[LoadTestScenario]:
        return list(self._scenarios.values())

    def run_test(
        self,
        scenario_id: str,
        successful: int = 0,
        failed: int = 0,
        avg_latency: float = 0,
        p95_latency: float = 0,
        p99_latency: float = 0,
        max_latency: float = 0,
    ) -> LoadTestResult | None:
        """Simulate running a load test with provided metrics."""
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return None

        self._result_counter += 1
        result = LoadTestResult(
            id=f"LTR-{self._result_counter:06d}",
            scenario_id=scenario_id,
            total_requests=successful + failed,
            successful_requests=successful,
            failed_requests=failed,
            avg_latency_ms=avg_latency,
            p50_latency_ms=avg_latency * 0.5,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max_latency,
            actual_rps=(successful + failed) / scenario.duration_seconds
            if scenario.duration_seconds > 0
            else 0,
        )

        result.start()
        if result.total_requests > 0:
            result.error_rate = result.failed_requests / result.total_requests
        passed = result.passed_threshold
        result.complete(passed)
        self._results[result.id] = result
        return result

    def get_result(self, result_id: str) -> LoadTestResult | None:
        return self._results.get(result_id)

    def list_results(
        self, scenario_id: str | None = None, status: str | None = None
    ) -> list[LoadTestResult]:
        results = list(self._results.values())
        if scenario_id:
            results = [r for r in results if r.scenario_id == scenario_id]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_summary(self) -> dict[str, Any]:
        results = list(self._results.values())
        return {
            "total_scenarios": len(self._scenarios),
            "total_runs": len(results),
            "passed": sum(1 for r in results if r.status == LoadTestStatus.PASSED.value),
            "failed": sum(1 for r in results if r.status == LoadTestStatus.FAILED.value),
            "avg_error_rate": sum(r.error_rate for r in results) / len(results) if results else 0,
            "avg_p95_latency": sum(r.p95_latency_ms for r in results) / len(results)
            if results
            else 0,
        }

    @property
    def scenario_count(self) -> int:
        return len(self._scenarios)

    @property
    def result_count(self) -> int:
        return len(self._results)

"""Tests for Load Testing — Module 38."""

import pytest

from services.load_testing import (
    LoadTestResult,
    LoadTestScenario,
    LoadTestService,
    LoadTestStatus,
)


@pytest.fixture
def service():
    return LoadTestService()


class TestLoadTestScenario:
    def test_total_requests(self):
        s = LoadTestScenario(id="S1", name="Test", target_rps=100, duration_seconds=60)
        assert s.total_requests == 6000


class TestLoadTestResult:
    def test_success_rate(self):
        r = LoadTestResult(id="R1", scenario_id="S1", total_requests=100, successful_requests=95)
        assert r.success_rate == 0.95

    def test_success_rate_zero(self):
        r = LoadTestResult(id="R1", scenario_id="S1")
        assert r.success_rate == 0.0

    def test_complete_calculates_error_rate(self):
        r = LoadTestResult(id="R1", scenario_id="S1", total_requests=100, failed_requests=5)
        r.complete(passed=True)
        assert r.error_rate == 0.05

    def test_passed_threshold_good(self):
        r = LoadTestResult(
            id="R1", scenario_id="S1", total_requests=100, failed_requests=0, p95_latency_ms=200
        )
        r.complete(passed=True)
        assert r.passed_threshold is True

    def test_passed_threshold_bad_latency(self):
        r = LoadTestResult(
            id="R1", scenario_id="S1", total_requests=100, failed_requests=0, p95_latency_ms=600
        )
        r.complete(passed=True)
        assert r.passed_threshold is False

    def test_passed_threshold_bad_error_rate(self):
        r = LoadTestResult(
            id="R1", scenario_id="S1", total_requests=100, failed_requests=10, p95_latency_ms=200
        )
        r.complete(passed=True)
        assert r.passed_threshold is False


class TestLoadTestService:
    def test_create_scenario(self, service):
        s = service.create_scenario("High Load", target_rps=500)
        assert s.id.startswith("LT-")
        assert service.scenario_count == 1

    def test_get_scenario(self, service):
        s = service.create_scenario("Test")
        assert service.get_scenario(s.id) is not None
        assert service.get_scenario("nonexistent") is None

    def test_list_scenarios(self, service):
        service.create_scenario("A")
        service.create_scenario("B")
        assert len(service.list_scenarios()) == 2

    def test_run_test_passed(self, service):
        s = service.create_scenario("Test", duration_seconds=10)
        result = service.run_test(s.id, successful=1000, failed=0, avg_latency=50, p95_latency=100)
        assert result is not None
        assert result.status == LoadTestStatus.PASSED.value
        assert result.actual_rps == 100.0

    def test_run_test_failed(self, service):
        s = service.create_scenario("Test")
        result = service.run_test(s.id, successful=900, failed=100, p95_latency=600)
        assert result.status == LoadTestStatus.FAILED.value

    def test_run_test_nonexistent(self, service):
        assert service.run_test("nonexistent") is None

    def test_get_result(self, service):
        s = service.create_scenario("Test")
        r = service.run_test(s.id, successful=100)
        assert service.get_result(r.id) is not None
        assert service.get_result("nonexistent") is None

    def test_list_results(self, service):
        s = service.create_scenario("Test")
        service.run_test(s.id, successful=100)
        service.run_test(s.id, successful=200)
        assert len(service.list_results()) == 2
        assert len(service.list_results(scenario_id=s.id)) == 2

    def test_list_results_by_status(self, service):
        s = service.create_scenario("Test")
        service.run_test(s.id, successful=100, p95_latency=100)
        service.run_test(s.id, successful=50, failed=50, p95_latency=600)
        passed = service.list_results(status=LoadTestStatus.PASSED.value)
        failed = service.list_results(status=LoadTestStatus.FAILED.value)
        assert len(passed) == 1
        assert len(failed) == 1

    def test_summary(self, service):
        s = service.create_scenario("Test")
        service.run_test(s.id, successful=100, p95_latency=100)
        service.run_test(s.id, successful=90, failed=10, p95_latency=300)
        summary = service.get_summary()
        assert summary["total_scenarios"] == 1
        assert summary["total_runs"] == 2
        assert summary["passed"] == 1

    def test_summary_empty(self, service):
        summary = service.get_summary()
        assert summary["total_scenarios"] == 0

    def test_result_count(self, service):
        s = service.create_scenario("Test")
        service.run_test(s.id, successful=100)
        assert service.result_count == 1

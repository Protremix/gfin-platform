"""Unit tests for AI Investigation Copilot service."""

from datetime import datetime

from services.investigation_copilot import (
    InvestigationCopilot,
    InvestigationResult,
    InvestigationStep,
    MockTool,
    create_default_mock_registry,
)


class TestInvestigationSeedTypes:
    def test_investigate_phone_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("phone", "+15550199")
        assert res.authorized is True
        assert res.seed_type == "phone"
        assert res.seed_value == "+15550199"
        assert len(res.steps) == 12

    def test_investigate_email_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("email", "fraud@example.com")
        assert res.authorized is True
        assert res.seed_type == "email"
        assert res.seed_value == "fraud@example.com"
        assert len(res.steps) == 12

    def test_investigate_domain_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "phishing-scam.com")
        assert res.authorized is True
        assert res.seed_type == "domain"
        assert res.seed_value == "phishing-scam.com"
        assert len(res.steps) == 12

    def test_investigate_url_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("url", "https://phishing-scam.com/login")
        assert res.authorized is True
        assert res.seed_type == "url"
        assert res.seed_value == "https://phishing-scam.com/login"
        assert len(res.steps) == 12

    def test_investigate_wallet_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("wallet", "0x71C7656EC7ab88b098defB751B7401B5f6d8976F")
        assert res.authorized is True
        assert res.seed_type == "wallet"
        assert res.seed_value == "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
        assert len(res.steps) == 12

    def test_investigate_ip_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("ip", "192.0.2.1")
        assert res.authorized is True
        assert res.seed_type == "ip"
        assert res.seed_value == "192.0.2.1"
        assert len(res.steps) == 12

    def test_investigate_case_seed(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("case", "CASE-2026-001")
        assert res.authorized is True
        assert res.seed_type == "case"
        assert res.seed_value == "CASE-2026-001"
        assert len(res.steps) == 12


class TestWorkflowAndStepTracking:
    def test_full_workflow_execution_12_steps(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "example-fraud.com")
        assert len(res.steps) == 12
        step_numbers = [s.step_number for s in res.steps]
        assert step_numbers == list(range(1, 13))

    def test_step_status_tracking(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "example-fraud.com")
        statuses = {s.status for s in res.steps}
        assert statuses.issubset({"COMPLETED", "SKIPPED", "FAILED"})
        step = InvestigationStep(step_number=1, action="norm", tool_name="normalize_domain", input_data={})
        assert step.status == "PENDING"

    def test_evidence_chain_construction(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("phone", "+15550199")
        assert len(res.evidence_chain) > 0
        first_ev = res.evidence_chain[0]
        assert "evidence_id" in first_ev
        assert "tool_name" in first_ev
        assert "data" in first_ev

    def test_summary_generation_with_evidence_links(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("email", "bad@actor.com")
        assert "Summary" in res.summary
        assert "Evidence:" in res.summary
        assert "Source:" in res.summary
        assert "Timestamp:" in res.summary
        assert "Confidence:" in res.summary

    def test_unverified_claims_marking(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "bad-site.org")
        assert len(res.unverified_claims) > 0
        for claim in res.unverified_claims:
            assert "[UNVERIFIED]" in claim
        assert "[UNVERIFIED]" in res.summary

    def test_gap_identification(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "bad-site.org")
        assert isinstance(res.gaps_identified, list)

    def test_next_steps_recommendation(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "bad-site.org")
        assert len(res.next_steps_recommended) > 0
        assert any("subscriber" in s.lower() or "law enforcement" in s.lower() for s in res.next_steps_recommended)


class TestSecurityAndAuthorization:
    def test_unauthorized_tool_rejected(self):
        tools = create_default_mock_registry()
        tools["search_entities"] = MockTool("search_entities", lambda inp: {"status": "success"}, required_role="SUPERVISOR")
        user = {"user_id": "u1", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["*"]}
        copilot = InvestigationCopilot(tool_registry=tools, user_context=user)
        res = copilot.investigate("domain", "test.com")
        step2 = next(s for s in res.steps if s.step_number == 2)
        assert step2.status == "FAILED"
        assert "Unauthorized" in str(step2.output_data)

    def test_tool_not_in_allowlist_rejected(self):
        tools = create_default_mock_registry()
        del tools["search_entities"]
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "test.com")
        step2 = next(s for s in res.steps if s.step_number == 2)
        assert step2.status == "FAILED"
        assert "not found" in str(step2.output_data) or "Unauthorized" in str(step2.output_data)

    def test_input_validation_invalid_seed_type(self):
        copilot = InvestigationCopilot()
        assert copilot._validate_input("invalid_seed", "val") is False
        res = copilot.investigate("invalid_seed", "val")
        assert res.authorized is False
        assert len(res.steps) == 0

    def test_input_validation_empty_seed_value(self):
        copilot = InvestigationCopilot()
        assert copilot._validate_input("phone", "") is False
        assert copilot._validate_input("phone", "   ") is False
        res = copilot.investigate("phone", "")
        assert res.authorized is False

    def test_output_validation_malformed_output(self):
        tools = create_default_mock_registry()
        tools["normalize_domain"] = MockTool("normalize_domain", lambda inp: {"status": "error", "message": "Corrupted"})
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "test.com")
        step1 = res.steps[0]
        assert step1.status == "FAILED"

    def test_rate_limiting_too_many_requests(self):
        user = {"user_id": "rate_user", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["*"]}
        copilot = InvestigationCopilot(user_context=user)
        copilot.rate_limit_max = 2
        r1 = copilot.investigate("domain", "site1.com")
        assert r1.authorized is True
        r2 = copilot.investigate("domain", "site2.com")
        assert r2.authorized is True
        r3 = copilot.investigate("domain", "site3.com")
        assert r3.authorized is False
        assert "Rate limit" in r3.summary

    def test_case_scope_enforcement_out_of_scope(self):
        user = {"user_id": "scoped_user", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["CASE-101"]}
        copilot = InvestigationCopilot(user_context=user)
        res = copilot.investigate("case", "CASE-999")
        assert res.authorized is False or any(s.status == "FAILED" for s in res.steps)

    def test_case_scope_enforcement_in_scope(self):
        user = {"user_id": "scoped_user", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["CASE-101"]}
        copilot = InvestigationCopilot(user_context=user)
        res = copilot.investigate("case", "CASE-101")
        assert res.authorized is True

    def test_case_scope_wildcard(self):
        user = {"user_id": "wildcard_user", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["*"]}
        copilot = InvestigationCopilot(user_context=user)
        res = copilot.investigate("case", "ANY-CASE-123")
        assert res.authorized is True

    def test_classification_enforcement_confidential_stripped(self):
        tools = create_default_mock_registry()
        tools["normalize_domain"] = MockTool(
            "normalize_domain",
            lambda inp: {"status": "success", "public_info": "ok", "confidential_intel": "secret_sauce"}
        )
        user = {"user_id": "u1", "role": "INVESTIGATOR", "clearance": "RESTRICTED", "case_scope": ["*"]}
        copilot = InvestigationCopilot(tool_registry=tools, user_context=user)
        res = copilot.investigate("domain", "test.com")
        step1_out = res.steps[0].output_data
        assert "confidential_intel" not in step1_out
        assert "public_info" in step1_out

    def test_classification_enforcement_secret_stripped(self):
        tools = create_default_mock_registry()
        tools["normalize_domain"] = MockTool(
            "normalize_domain",
            lambda inp: {"status": "success", "public_info": "ok", "secret_notes": "classified"}
        )
        user = {"user_id": "u1", "role": "INVESTIGATOR", "clearance": "CONFIDENTIAL", "case_scope": ["*"]}
        copilot = InvestigationCopilot(tool_registry=tools, user_context=user)
        res = copilot.investigate("domain", "test.com")
        step1_out = res.steps[0].output_data
        assert "secret_notes" not in step1_out
        assert "public_info" in step1_out

    def test_classification_enforcement_top_secret_allowed(self):
        tools = create_default_mock_registry()
        tools["normalize_domain"] = MockTool(
            "normalize_domain",
            lambda inp: {"status": "success", "public_info": "ok", "secret_notes": "classified"}
        )
        user = {"user_id": "u1", "role": "ADMIN", "clearance": "TOP_SECRET", "case_scope": ["*"]}
        copilot = InvestigationCopilot(tool_registry=tools, user_context=user)
        res = copilot.investigate("domain", "test.com")
        step1_out = res.steps[0].output_data
        assert "secret_notes" in step1_out


class TestAuditAndLogging:
    def test_audit_trail_action_logged(self):
        copilot = InvestigationCopilot()
        copilot.investigate("domain", "audit-test.com")
        assert len(copilot.audit_log) > 0
        actions = [a["action"] for a in copilot.audit_log]
        assert "step_started" in actions
        assert "step_completed" in actions
        assert "investigation_completed" in actions

    def test_audit_trail_unauthorized_attempts_logged(self):
        user = {"user_id": "unauth_user", "role": "INVESTIGATOR", "clearance": "UNCLASSIFIED", "case_scope": ["CASE-101"]}
        tools = create_default_mock_registry()
        tools["normalize_domain"] = MockTool("normalize_domain", lambda inp: {"status": "success"}, required_clearance="SECRET")
        copilot = InvestigationCopilot(tool_registry=tools, user_context=user)
        copilot.investigate("domain", "test.com")
        actions = [a["action"] for a in copilot.audit_log]
        assert "unauthorized_clearance" in actions or "step_failed_unauthorized" in actions

    def test_execute_step_audit_logging(self):
        copilot = InvestigationCopilot()
        step = InvestigationStep(step_number=1, action="normalize", tool_name="normalize_domain", input_data={"seed_type": "domain", "seed_value": "test.com"})
        copilot._execute_step(step)
        assert len(copilot.audit_log) >= 2
        actions = [a["action"] for a in copilot.audit_log]
        assert "step_started" in actions
        assert "step_completed" in actions


class TestMockToolsAndResults:
    def test_mock_tool_execution_realistic_data(self):
        registry = create_default_mock_registry()
        norm_phone = registry["normalize_phone"].execute({"seed_value": "+15550199"})
        assert norm_phone["status"] == "success"
        assert norm_phone["country"] == "US"
        assert norm_phone["carrier"] == "Mock Mobile"

        enrich_infra = registry["enrich_infrastructure"].execute({"seed_value": "192.0.2.1"})
        assert enrich_infra["status"] == "success"
        assert "ip" in enrich_infra["infrastructure"]

    def test_investigation_result_structure_validation(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("phone", "+15550199")
        assert isinstance(res, InvestigationResult)
        assert isinstance(res.investigation_id, str)
        assert res.investigation_id.startswith("INV-")
        assert isinstance(res.confidence, float)
        assert isinstance(res.created_at, datetime)

    def test_confidence_scoring(self):
        copilot = InvestigationCopilot()
        res = copilot.investigate("domain", "test.com")
        assert 0.0 <= res.confidence <= 1.0

        tools = create_default_mock_registry()
        tools["search_entities"] = MockTool("search_entities", lambda inp: {"status": "error"})
        copilot2 = InvestigationCopilot(tool_registry=tools)
        res2 = copilot2.investigate("domain", "test.com")
        assert res2.confidence < res.confidence

    def test_multiple_investigations_concurrent(self):
        copilot1 = InvestigationCopilot(user_context={"user_id": "u1", "role": "INVESTIGATOR", "case_scope": ["*"]})
        copilot2 = InvestigationCopilot(user_context={"user_id": "u2", "role": "INVESTIGATOR", "case_scope": ["*"]})
        res1 = copilot1.investigate("domain", "dom1.com")
        res2 = copilot2.investigate("domain", "dom2.com")
        assert res1.investigation_id != res2.investigation_id
        assert res1.user_id == "u1"
        assert res2.user_id == "u2"

    def test_edge_case_no_results(self):
        tools = create_default_mock_registry()
        tools["search_entities"] = MockTool("search_entities", lambda inp: {"status": "success", "entities": [], "matches": 0})
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "empty-results.com")
        assert res.authorized is True
        assert res.steps[1].status == "COMPLETED"

    def test_edge_case_partial_results(self):
        tools = create_default_mock_registry()
        tools["search_history"] = MockTool("search_history", lambda inp: {"status": "error", "error": "History service unavailable"})
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "partial-test.com")
        assert res.authorized is True
        assert any(s.status == "FAILED" for s in res.steps)
        assert any(s.status == "COMPLETED" for s in res.steps)

    def test_edge_case_all_tools_fail(self):
        tools = {}
        for k in create_default_mock_registry():
            tools[k] = MockTool(k, lambda inp: {"status": "error", "error": "Tool system offline"})
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "fail-all.com")
        assert res.authorized is True
        assert all(s.status == "FAILED" or s.status == "SKIPPED" for s in res.steps)
        assert res.confidence < 0.5

    def test_error_handling_tool_exception(self):
        tools = create_default_mock_registry()
        def bad_tool(inp):
            raise RuntimeError("Database connection crashed")
        tools["search_entities"] = MockTool("search_entities", bad_tool)
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("domain", "crash.com")
        step2 = next(s for s in res.steps if s.step_number == 2)
        assert step2.status == "FAILED"
        assert "Database connection crashed" in str(step2.output_data)

    def test_error_handling_timeout(self):
        tools = create_default_mock_registry()
        def timeout_tool(inp):
            raise TimeoutError("Tool call timed out after 30s")
        tools["enrich_infrastructure"] = MockTool("enrich_infrastructure", timeout_tool)
        copilot = InvestigationCopilot(tool_registry=tools)
        res = copilot.investigate("ip", "192.0.2.1")
        step3 = next(s for s in res.steps if s.step_number == 3)
        assert step3.status == "FAILED"
        assert "timed out" in str(step3.output_data)

    def test_custom_tool_registry(self):
        custom_tools = {
            "normalize_domain": MockTool("normalize_domain", lambda inp: {"status": "success"}),
        }
        copilot = InvestigationCopilot(tool_registry=custom_tools)
        assert "normalize_domain" in copilot.tools
        assert "search_entities" not in copilot.tools

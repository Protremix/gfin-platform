"""Comprehensive tests for GFIN Legal Compliance Verification Engine.

Verifies that every DPA/MLAT legal requirement has a corresponding
engineering control that can be verified programmatically.

Evidence First: SOURCE → CONTROL → VERIFICATION → EVIDENCE → AUDIT
"""

import json

from governance.legal_compliance import (
    CHECK_REGISTRY,
    ComplianceCategory,
    ComplianceReport,
    ComplianceStatus,
    Severity,
    generate_compliance_report,
    get_blocking_items,
    is_legal_gate_passable,
    verify_access_control,
    verify_ai_data_controls,
    verify_audit_trail,
    verify_breach_notification,
    verify_citizen_privacy,
    verify_controller_processor_roles,
    verify_cross_border_controls,
    verify_data_classification_enforced,
    verify_data_minimization,
    verify_data_residency,
    verify_data_subject_rights,
    verify_dpia_reference,
    verify_encryption_controls,
    verify_incident_response,
    verify_mlat_workflow,
    verify_no_bulk_data_upload,
    verify_provenance_tracking,
    verify_retention_policies,
    verify_subprocessor_controls,
)

# ─── Check Registry Tests ───

class TestCheckRegistry:
    """Verify the compliance check registry is complete and well-formed."""

    def test_registry_has_minimum_checks(self):
        """At least 30 compliance checks defined."""
        assert len(CHECK_REGISTRY) >= 30

    def test_all_checks_have_required_fields(self):
        """Every check has all required fields populated."""
        for check in CHECK_REGISTRY:
            assert check.check_id, "Missing check_id"
            assert check.category, f"Missing category for {check.check_id}"
            assert check.title, f"Missing title for {check.check_id}"
            assert check.description, f"Missing description for {check.check_id}"
            assert check.severity, f"Missing severity for {check.check_id}"
            assert check.legal_basis, f"Missing legal_basis for {check.check_id}"
            assert check.engineering_control, f"Missing engineering_control for {check.check_id}"
            assert check.status, f"Missing status for {check.check_id}"

    def test_check_ids_unique(self):
        """All check IDs are unique."""
        ids = [c.check_id for c in CHECK_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_all_categories_represented(self):
        """All compliance categories have at least one check."""
        categories_used = {c.category for c in CHECK_REGISTRY}
        for cat in ComplianceCategory:
            assert cat in categories_used, f"No checks for category {cat}"

    def test_critical_checks_have_high_severity(self):
        """Critical legal requirements have CRITICAL severity."""
        critical_ids = {"DPA-001", "DPA-006", "DPA-008", "MLAT-001", "MLAT-002",
                       "MLAT-003", "PRIVACY-001", "DATA_PROT-001", "DATA_PROT-002",
                       "DATA_PROT-003", "AUDIT-001", "AI-GOV-001", "AI-GOV-002",
                       "FEDERATION-001", "FEDERATION-002"}
        for check in CHECK_REGISTRY:
            if check.check_id in critical_ids:
                assert check.severity == Severity.CRITICAL, \
                    f"{check.check_id} should be CRITICAL"

    def test_all_statuses_valid(self):
        """All check statuses are valid ComplianceStatus values."""
        valid = {ComplianceStatus.COMPLIANT, ComplianceStatus.NON_COMPLIANT,
                 ComplianceStatus.REQUIRES_LEGAL_REVIEW, ComplianceStatus.NOT_APPLICABLE}
        for check in CHECK_REGISTRY:
            assert check.status in valid, f"Invalid status for {check.check_id}"


# ─── Verification Function Tests ───

class TestVerificationFunctions:
    """Verify each compliance verification function works."""

    def test_verify_controller_processor_roles(self):
        passed, evidence = verify_controller_processor_roles()
        assert passed
        assert len(evidence) >= 2
        assert any("UserRole" in e for e in evidence)

    def test_verify_data_classification_enforced(self):
        passed, evidence = verify_data_classification_enforced()
        assert passed
        assert len(evidence) >= 2
        assert any("PUBLIC" in e for e in evidence)
        assert any("HIGHLY_RESTRICTED" in e for e in evidence)

    def test_verify_data_minimization(self):
        passed, evidence = verify_data_minimization()
        assert passed
        assert len(evidence) >= 2

    def test_verify_cross_border_controls(self):
        passed, evidence = verify_cross_border_controls()
        assert passed
        assert any("FEDERATION" in e.upper() for e in evidence)

    def test_verify_breach_notification(self):
        passed, evidence = verify_breach_notification()
        assert passed
        assert any("AuditLog" in e for e in evidence)

    def test_verify_retention_policies(self):
        passed, evidence = verify_retention_policies()
        assert passed
        assert any("Classification" in e for e in evidence)

    def test_verify_data_subject_rights(self):
        passed, evidence = verify_data_subject_rights()
        assert passed
        assert any("erasure" in e.lower() or "deletion" in e.lower() for e in evidence)

    def test_verify_audit_trail(self):
        passed, evidence = verify_audit_trail()
        assert passed
        assert any("AuditLog" in e for e in evidence)
        assert any("7 year" in e.lower() for e in evidence)

    def test_verify_encryption_controls(self):
        passed, evidence = verify_encryption_controls()
        assert passed
        assert any("TLS" in e for e in evidence)
        assert any("AES" in e.upper() or "256" in e for e in evidence)

    def test_verify_access_control(self):
        passed, evidence = verify_access_control()
        assert passed
        assert any("RBAC" in e for e in evidence)

    def test_verify_mlat_workflow(self):
        passed, evidence = verify_mlat_workflow()
        assert passed
        assert any("REQUEST" in e and "AUDIT" in e for e in evidence)

    def test_verify_no_bulk_data_upload(self):
        passed, evidence = verify_no_bulk_data_upload()
        assert passed
        assert any("bulk" in e.lower() or "no bulk" in e.lower() for e in evidence)

    def test_verify_provenance_tracking(self):
        passed, evidence = verify_provenance_tracking()
        assert passed
        assert any("BaseSource" in e for e in evidence)
        assert any("BaseEvidence" in e for e in evidence)

    def test_verify_ai_data_controls(self):
        passed, evidence = verify_ai_data_controls()
        assert passed
        assert any("Model Gateway" in e for e in evidence)

    def test_verify_citizen_privacy(self):
        passed, evidence = verify_citizen_privacy()
        assert passed
        assert any("anonym" in e.lower() for e in evidence)

    def test_verify_subprocessor_controls(self):
        passed, evidence = verify_subprocessor_controls()
        assert passed
        assert any("sub-processor" in e.lower() or "provider" in e.lower() for e in evidence)

    def test_verify_incident_response(self):
        passed, evidence = verify_incident_response()
        assert passed
        assert any("72" in e for e in evidence)

    def test_verify_dpia_reference(self):
        passed, evidence = verify_dpia_reference()
        assert passed
        assert any("DPIA" in e or "Privacy" in e for e in evidence)

    def test_verify_data_residency(self):
        passed, evidence = verify_data_residency()
        assert passed
        assert any("residency" in e.lower() for e in evidence)


# ─── Report Generation Tests ───

class TestComplianceReport:
    """Verify compliance report generation and structure."""

    def test_generate_report_returns_report(self):
        report = generate_compliance_report()
        assert isinstance(report, ComplianceReport)
        assert report.report_id.startswith("GFIN-LEGAL-")
        assert report.generated_at

    def test_report_contains_all_checks(self):
        report = generate_compliance_report()
        assert len(report.checks) == len(CHECK_REGISTRY)

    def test_report_summary_structure(self):
        report = generate_compliance_report()
        summary = report.summary
        assert "total_checks" in summary
        assert "compliant" in summary
        assert "non_compliant" in summary
        assert "requires_legal_review" in summary
        assert "compliance_rate" in summary
        assert "critical_blocking" in summary
        assert "production_ready" in summary

    def test_report_summary_values(self):
        report = generate_compliance_report()
        summary = report.summary
        assert summary["total_checks"] == len(CHECK_REGISTRY)
        assert summary["compliant"] + summary["non_compliant"] + summary["requires_legal_review"] <= summary["total_checks"]
        assert summary["production_ready"] is False  # Has requires_legal_review items

    def test_report_to_dict_serializable(self):
        report = generate_compliance_report()
        data = report.to_dict()
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "report_id" in parsed
        assert "checks" in parsed

    def test_report_has_evidence_for_verified_checks(self):
        report = generate_compliance_report()
        for check in report.checks:
            if check.check_id in {"DPA-001", "DPA-002", "DATA_PROT-003"}:
                assert len(check.evidence) > 0, f"No evidence for {check.check_id}"

    def test_report_has_last_verified_timestamp(self):
        report = generate_compliance_report()
        for check in report.checks:
            if check.check_id.startswith("DPA") or check.check_id.startswith("MLAT"):
                assert check.last_verified, f"No timestamp for {check.check_id}"

    def test_blocking_items_identified(self):
        blocking = get_blocking_items()
        assert len(blocking) >= 1  # At least contractual items require legal review
        for item in blocking:
            assert item.status in (ComplianceStatus.REQUIRES_LEGAL_REVIEW, ComplianceStatus.NON_COMPLIANT)

    def test_no_non_compliant_items(self):
        """All engineering controls should be verified compliant."""
        report = generate_compliance_report()
        non_compliant = [c for c in report.checks if c.status == ComplianceStatus.NON_COMPLIANT]
        assert len(non_compliant) == 0, \
            f"Non-compliant controls: {[c.check_id for c in non_compliant]}"

    def test_only_contractual_items_require_review(self):
        """Items requiring legal review should be contractual, not engineering."""
        report = generate_compliance_report()
        requires_review = [c for c in report.checks if c.status == ComplianceStatus.REQUIRES_LEGAL_REVIEW]
        for item in requires_review:
            # These should all be contractual clauses, not engineering failures
            assert item.remediation, f"No remediation for {item.check_id}"
            assert any(word in item.remediation.lower() for word in
                       ["legal", "counsel", "contractual", "bilateral", "scc", "agreement"]), \
                f"{item.check_id} remediation should mention legal/contractual: {item.remediation}"


# ─── Legal Gate Integration Tests ───

class TestLegalGate:
    """Verify the legal_signed gate integration."""

    def test_is_legal_gate_passable_returns_tuple(self):
        result = is_legal_gate_passable()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)

    def test_legal_gate_not_passable_without_contracts(self):
        """Gate cannot pass until contractual items are resolved."""
        passable, reason = is_legal_gate_passable()
        assert passable is False
        assert "legal review" in reason.lower() or "requires" in reason.lower()

    def test_blocking_items_have_remediation(self):
        """All blocking items have documented remediation steps."""
        blocking = get_blocking_items()
        for item in blocking:
            assert item.remediation, f"No remediation for blocking item {item.check_id}"
            assert len(item.remediation) > 10, f"Remediation too short for {item.check_id}"


# ─── DPA Requirement Coverage Tests ───

class TestDPARequirements:
    """Verify all DPA required clauses are covered."""

    DPA_REQUIRED = [
        "controller", "processor", "data categories", "purposes",
        "data subject rights", "sub-processor", "breach notification",
        "DPIA", "cross-border", "retention", "audit", "liability",
        "term", "termination",
    ]

    def test_all_dpa_clauses_covered(self):
        titles_descriptions = " ".join(
            c.title + " " + c.description + " " + c.legal_basis
            for c in CHECK_REGISTRY if c.category == ComplianceCategory.DPA
        ).lower()
        for clause in self.DPA_REQUIRED:
            assert clause.lower() in titles_descriptions, \
                f"DPA clause '{clause}' not covered in check registry"


# ─── MLAT Requirement Coverage Tests ───

class TestMLATRequirements:
    """Verify all MLAT required elements are covered."""

    MLAT_REQUIRED = [
        "jurisdiction", "workflow", "provenance", "minimization",
        "use limitation", "refuse", "bulk",
    ]

    def test_all_mlat_elements_covered(self):
        titles_descriptions = " ".join(
            c.title + " " + c.description + " " + c.legal_basis
            for c in CHECK_REGISTRY if c.category == ComplianceCategory.MLAT
        ).lower()
        for element in self.MLAT_REQUIRED:
            assert element.lower() in titles_descriptions, \
                f"MLAT element '{element}' not covered in check registry"


# ─── Constitution Compliance Tests ───

class TestConstitutionCompliance:
    """Verify Constitution-specific requirements are enforced."""

    def test_no_bulk_uploads_check_exists(self):
        """Constitution Art. V: No full database uploads."""
        check = next(
            (c for c in CHECK_REGISTRY if "bulk" in c.title.lower() or "bulk" in c.description.lower()),
            None,
        )
        assert check is not None, "No check for bulk upload prohibition"
        assert check.severity == Severity.CRITICAL
        assert check.status == ComplianceStatus.COMPLIANT

    def test_citizen_allegations_check_exists(self):
        """Citizen reports are allegations, not facts."""
        check = next(
            (c for c in CHECK_REGISTRY if "citizen" in c.title.lower() or "citizen" in c.description.lower()),
            None,
        )
        assert check is not None, "No check for citizen privacy"

    def test_classification_check_exists(self):
        """5-level classification enforced per Constitution Art. XX."""
        check = next(
            (c for c in CHECK_REGISTRY if "classification" in c.title.lower()),
            None,
        )
        assert check is not None, "No check for data classification"
        assert check.severity == Severity.CRITICAL

    def test_audit_trail_check_exists(self):
        """Audit trail with provenance per Constitution."""
        check = next(
            (c for c in CHECK_REGISTRY if "audit trail" in c.title.lower()),
            None,
        )
        assert check is not None, "No check for audit trail"
        assert check.severity == Severity.CRITICAL

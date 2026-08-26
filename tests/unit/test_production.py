"""Tests for Production — Module 40."""

import pytest

from services.production import (
    ProductionChecklist,
    ProductionService,
    ReadinessCheck,
    ReadinessLevel,
)


@pytest.fixture
def service():
    return ProductionService()


class TestReadinessCheck:
    def test_verify(self):
        c = ReadinessCheck(id="RC-0001", category="SECURITY", description="TLS configured")
        c.verify("Done")
        assert c.verified is True
        assert c.verified_at is not None
        assert c.notes == "Done"


class TestProductionChecklist:
    def test_readiness_not_ready(self):
        cl = ProductionChecklist(id="PC-1", name="Test")
        cl.checks.append(ReadinessCheck(id="C1", category="SEC", description="Req", required=True))
        assert cl.readiness_level == ReadinessLevel.NOT_READY.value

    def test_readiness_partially_ready(self):
        cl = ProductionChecklist(id="PC-1", name="Test")
        c1 = ReadinessCheck(id="C1", category="SEC", description="Req", required=True)
        c2 = ReadinessCheck(id="C2", category="SEC", description="Optional", required=False)
        c1.verify()
        cl.checks.extend([c1, c2])
        assert cl.readiness_level == ReadinessLevel.PARTIALLY_READY.value

    def test_readiness_ready(self):
        cl = ProductionChecklist(id="PC-1", name="Test")
        c1 = ReadinessCheck(id="C1", category="SEC", description="Req")
        c1.verify()
        cl.checks.append(c1)
        assert cl.readiness_level == ReadinessLevel.READY.value

    def test_verified_count(self):
        cl = ProductionChecklist(id="PC-1", name="Test")
        c1 = ReadinessCheck(id="C1", category="SEC", description="A")
        c2 = ReadinessCheck(id="C2", category="SEC", description="B")
        c1.verify()
        cl.checks.extend([c1, c2])
        assert cl.verified_count == 1
        assert cl.total_checks == 2

    def test_required_unverified(self):
        cl = ProductionChecklist(id="PC-1", name="Test")
        c1 = ReadinessCheck(id="C1", category="SEC", description="A", required=True)
        c2 = ReadinessCheck(id="C2", category="SEC", description="B", required=False)
        c1.verify()
        cl.checks.extend([c1, c2])
        assert cl.required_unverified == 0


class TestProductionService:
    def test_default_checklist_exists(self, service):
        cl = service.get_checklist()
        assert cl is not None
        assert cl.total_checks >= 26

    def test_list_checklists(self, service):
        assert len(service.list_checklists()) == 1

    def test_verify_check(self, service):
        cl = service.get_checklist()
        check_id = cl.checks[0].id
        assert service.verify_check(cl.id, check_id, "Done") is True
        assert cl.checks[0].verified is True

    def test_verify_nonexistent_check(self, service):
        cl = service.get_checklist()
        assert service.verify_check(cl.id, "nonexistent") is False

    def test_verify_nonexistent_checklist(self, service):
        assert service.verify_check("nonexistent", "C1") is False

    def test_get_readiness_level_initial(self, service):
        assert service.get_readiness_level() == ReadinessLevel.NOT_READY.value

    def test_readiness_summary(self, service):
        summary = service.get_readiness_summary()
        assert summary["readiness_level"] == ReadinessLevel.NOT_READY.value
        assert summary["total_checks"] >= 26
        assert summary["verified"] == 0
        assert "INFRASTRUCTURE" in summary["by_category"]

    def test_readiness_after_verification(self, service):
        cl = service.get_checklist()
        # Verify all required checks
        for check in cl.checks:
            if check.required:
                service.verify_check(cl.id, check.id)
        summary = service.get_readiness_summary()
        assert summary["required_unverified"] == 0


class TestInfrastructureRequirements:
    def test_default_requirements_exist(self, service):
        reqs = service.list_requirements()
        assert len(reqs) >= 12

    def test_list_provisioned(self, service):
        service.list_requirements()[0].provisioned = True
        provisioned = service.list_requirements(provisioned=True)
        assert len(provisioned) == 1

    def test_provision_requirement(self, service):
        reqs = service.list_requirements()
        assert service.provision_requirement(reqs[0].id, "Done") is True
        assert reqs[0].provisioned is True

    def test_provision_nonexistent(self, service):
        assert service.provision_requirement("nonexistent") is False

    def test_requirements_summary(self, service):
        summary = service.get_requirements_summary()
        assert summary["total"] >= 12
        assert summary["provisioned"] == 0
        assert summary["pending"] >= 12

    def test_all_unprovisioned_initially(self, service):
        reqs = service.list_requirements()
        for r in reqs:
            assert r.status == "REQUIRES_EXTERNAL_INFRASTRUCTURE"
            assert r.provisioned is False


class TestGoLive:
    def test_not_ready_initially(self, service):
        assert service.is_production_ready() is False

    def test_mark_go_live_not_ready(self, service):
        result = service.mark_go_live()
        assert "NOT READY" in result

    def test_mark_go_live_after_all_verified(self, service):
        cl = service.get_checklist()
        for check in cl.checks:
            if check.required:
                service.verify_check(cl.id, check.id)
        for req in service.list_requirements():
            service.provision_requirement(req.id)
        result = service.mark_go_live()
        assert "READY FOR GO-LIVE" in result

    def test_is_production_ready_after_all(self, service):
        cl = service.get_checklist()
        for check in cl.checks:
            if check.required:
                service.verify_check(cl.id, check.id)
        for req in service.list_requirements():
            service.provision_requirement(req.id)
        assert service.is_production_ready() is True

    def test_not_ready_with_unprovisioned(self, service):
        cl = service.get_checklist()
        for check in cl.checks:
            if check.required:
                service.verify_check(cl.id, check.id)
        # Don't provision infrastructure
        assert service.is_production_ready() is False

    def test_not_ready_with_unverified(self, service):
        for req in service.list_requirements():
            service.provision_requirement(req.id)
        # Don't verify checks
        assert service.is_production_ready() is False

    def test_checklist_count(self, service):
        assert service.checklist_count == 1

    def test_requirement_count(self, service):
        assert service.requirement_count >= 12

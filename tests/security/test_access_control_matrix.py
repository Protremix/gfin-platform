"""Tests for access control matrix."""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from security.access_control_matrix import AccessControlMatrix


class TestAccessControlMatrix:
    """Test access control matrix."""

    def test_all_roles_defined(self):
        """All 7 roles should be defined."""
        acm = AccessControlMatrix()
        roles = acm.get_all_roles()
        assert len(roles) == 7
        assert "citizen" in roles
        assert "admin" in roles
        assert "system" in roles

    def test_all_resources_defined(self):
        """All 9 resources should be defined."""
        acm = AccessControlMatrix()
        resources = acm.get_all_resources()
        assert len(resources) == 9

    def test_all_actions_defined(self):
        """All 8 actions should be defined."""
        acm = AccessControlMatrix()
        actions = acm.get_all_actions()
        assert len(actions) == 8

    def test_citizen_can_read_entity(self):
        """Citizen should be able to read entities."""
        acm = AccessControlMatrix()
        assert acm.check_access("citizen", "entity", "read") is True

    def test_citizen_cannot_delete_entity(self):
        """Citizen should not be able to delete entities."""
        acm = AccessControlMatrix()
        assert acm.check_access("citizen", "entity", "delete") is False

    def test_citizen_cannot_access_user_management(self):
        """Citizen should not have user management permissions."""
        acm = AccessControlMatrix()
        assert acm.check_access("citizen", "user_management", "read") is False
        assert acm.check_access("citizen", "user_management", "create") is False

    def test_analyst_can_create_entity(self):
        """Analyst should be able to create entities."""
        acm = AccessControlMatrix()
        assert acm.check_access("analyst", "entity", "create") is True

    def test_analyst_cannot_approve_report(self):
        """Analyst should not be able to approve reports."""
        acm = AccessControlMatrix()
        assert acm.check_access("analyst", "report", "approve") is False

    def test_analyst_cannot_access_federation(self):
        """Analyst should not have federation permissions."""
        acm = AccessControlMatrix()
        assert acm.check_access("analyst", "federation_request", "read") is False

    def test_supervisor_can_approve(self):
        """Supervisor should be able to approve reports and alerts."""
        acm = AccessControlMatrix()
        assert acm.check_access("supervisor", "report", "approve") is True
        assert acm.check_access("supervisor", "alert", "approve") is True

    def test_admin_has_all_entity_actions(self):
        """Admin should have extensive entity permissions."""
        acm = AccessControlMatrix()
        for action in ["read", "create", "update", "delete", "export", "classify"]:
            assert acm.check_access("admin", "entity", action) is True, f"Admin should have entity:{action}"

    def test_admin_can_manage_users(self):
        """Admin should be able to manage users."""
        acm = AccessControlMatrix()
        assert acm.check_access("admin", "user_management", "create") is True
        assert acm.check_access("admin", "user_management", "delete") is True

    def test_federation_partner_read_only(self):
        """Federation partner should have read-only on most resources."""
        acm = AccessControlMatrix()
        assert acm.check_access("federation_partner", "entity", "read") is True
        assert acm.check_access("federation_partner", "entity", "delete") is False
        assert acm.check_access("federation_partner", "evidence", "read") is True
        assert acm.check_access("federation_partner", "evidence", "delete") is False

    def test_federation_partner_can_share_reports(self):
        """Federation partner should be able to share reports."""
        acm = AccessControlMatrix()
        assert acm.check_access("federation_partner", "report", "share") is True

    def test_system_has_full_access(self):
        """System role should have all actions on all resources."""
        acm = AccessControlMatrix()
        for resource in acm.get_all_resources():
            for action in acm.get_all_actions():
                assert acm.check_access("system", resource, action) is True, \
                    f"System should have {resource}:{action}"

    def test_get_permissions_returns_dict(self):
        """get_permissions should return dict of resource -> actions."""
        acm = AccessControlMatrix()
        perms = acm.get_permissions("analyst")
        assert "entity" in perms
        assert "read" in perms["entity"]

    def test_export_json(self):
        """Export to JSON should be serializable."""
        acm = AccessControlMatrix()
        data = acm.export_json()
        assert "citizen" in data
        assert "admin" in data
        assert isinstance(data["citizen"], dict)

    def test_get_denied_actions(self):
        """get_denied_actions should return actions not allowed."""
        acm = AccessControlMatrix()
        denied = acm.get_denied_actions("citizen", "entity")
        assert "delete" in denied
        assert "create" in denied
        assert "read" not in denied

    def test_unknown_role_denied(self):
        """Unknown role should be denied all access."""
        acm = AccessControlMatrix()
        assert acm.check_access("unknown_role", "entity", "read") is False

    def test_unknown_resource_denied(self):
        """Unknown resource should be denied."""
        acm = AccessControlMatrix()
        assert acm.check_access("admin", "unknown_resource", "read") is False

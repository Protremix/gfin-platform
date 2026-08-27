"""Access control matrix for GFIN.

Per Luna Directive — Focus Area 4: Role -> permission mappings.
"""

from __future__ import annotations

from typing import Any

# Role definitions
ROLES = [
    "citizen",
    "analyst",
    "senior_analyst",
    "supervisor",
    "admin",
    "federation_partner",
    "system",
]

# Resource definitions
RESOURCES = [
    "entity",
    "evidence",
    "campaign",
    "report",
    "alert",
    "audit_log",
    "federation_request",
    "system_config",
    "user_management",
]

# Action definitions
ACTIONS = ["read", "create", "update", "delete", "export", "share", "classify", "approve"]

# Access control matrix: role -> resource -> set of allowed actions
ACCESS_MATRIX: dict[str, dict[str, set[str]]] = {
    "citizen": {
        "entity": {"read"},
        "report": {"create", "read"},
        "evidence": set(),
        "campaign": set(),
        "alert": set(),
        "audit_log": set(),
        "federation_request": set(),
        "system_config": set(),
        "user_management": set(),
    },
    "analyst": {
        "entity": {"read", "create", "update"},
        "evidence": {"read", "create"},
        "campaign": {"read", "create"},
        "report": {"read", "create", "update"},
        "alert": {"read"},
        "audit_log": set(),
        "federation_request": set(),
        "system_config": set(),
        "user_management": set(),
    },
    "senior_analyst": {
        "entity": {"read", "create", "update", "delete"},
        "evidence": {"read", "create", "export"},
        "campaign": {"read", "create", "update"},
        "report": {"read", "create", "update", "delete"},
        "alert": {"read", "classify"},
        "audit_log": {"read"},
        "federation_request": set(),
        "system_config": set(),
        "user_management": set(),
    },
    "supervisor": {
        "entity": {"read", "create", "update", "delete"},
        "evidence": {"read", "create", "export", "share"},
        "campaign": {"read", "create", "update", "delete"},
        "report": {"read", "create", "update", "delete", "approve"},
        "alert": {"read", "classify", "approve"},
        "audit_log": {"read"},
        "federation_request": {"read", "approve"},
        "system_config": {"read"},
        "user_management": set(),
    },
    "admin": {
        "entity": {"read", "create", "update", "delete", "export", "classify"},
        "evidence": {"read", "create", "update", "delete", "export", "share", "classify"},
        "campaign": {"read", "create", "update", "delete", "export"},
        "report": {"read", "create", "update", "delete", "export", "share", "classify", "approve"},
        "alert": {"read", "classify", "approve"},
        "audit_log": {"read", "export"},
        "federation_request": {"read", "create", "update", "approve", "share"},
        "system_config": {"read", "create", "update", "delete"},
        "user_management": {"read", "create", "update", "delete"},
    },
    "federation_partner": {
        "entity": {"read"},
        "evidence": {"read"},
        "campaign": {"read"},
        "report": {"read", "share"},
        "alert": set(),
        "audit_log": set(),
        "federation_request": {"read", "create", "share"},
        "system_config": set(),
        "user_management": set(),
    },
    "system": {
        # System has all permissions
        resource: {"read", "create", "update", "delete", "export", "share", "classify", "approve"}
        for resource in RESOURCES
    },
}


class AccessControlMatrix:
    """Access control matrix for GFIN role-based access control."""

    def __init__(self) -> None:
        self._matrix = ACCESS_MATRIX

    def check_access(self, role: str, resource: str, action: str) -> bool:
        """Check if a role can perform an action on a resource."""
        role_perms = self._matrix.get(role, {})
        allowed_actions = role_perms.get(resource, set())
        return action in allowed_actions

    def get_permissions(self, role: str) -> dict[str, list[str]]:
        """Get all permissions for a role."""
        role_perms = self._matrix.get(role, {})
        return {resource: sorted(actions) for resource, actions in role_perms.items() if actions}

    def get_all_roles(self) -> list[str]:
        """Get all defined roles."""
        return list(self._matrix.keys())

    def get_all_resources(self) -> list[str]:
        """Get all defined resources."""
        return RESOURCES

    def get_all_actions(self) -> list[str]:
        """Get all defined actions."""
        return ACTIONS

    def export_json(self) -> dict[str, Any]:
        """Export the full matrix as JSON-serializable dict."""
        return {
            role: {resource: sorted(actions) for resource, actions in perms.items() if actions}
            for role, perms in self._matrix.items()
        }

    def get_denied_actions(self, role: str, resource: str) -> list[str]:
        """Get actions that are denied for a role on a resource."""
        allowed = self._matrix.get(role, {}).get(resource, set())
        return sorted([a for a in ACTIONS if a not in allowed])

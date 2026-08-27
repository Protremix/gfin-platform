"""Versioned schema registry for GFIN.

Per Luna Directive — Focus Area 1: Freeze versioned schemas.
Each schema gets a version string and backward compatibility checks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SchemaVersion(BaseModel):
    """Versioned schema definition."""

    name: str
    version: str
    fields: dict[str, str]  # field_name -> type
    required_fields: list[str]
    optional_fields: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deprecated: bool = False
    successor_version: str | None = None


class MigrationResult(BaseModel):
    """Result of a schema migration."""

    from_version: str
    to_version: str
    migrated_fields: list[str]
    added_fields: list[str]
    removed_fields: list[str]
    success: bool
    errors: list[str] = []


# Frozen schema registry
SCHEMA_REGISTRY: dict[str, dict[str, SchemaVersion]] = {
    "entity": {
        "1.0": SchemaVersion(
            name="entity",
            version="1.0",
            fields={
                "id": "str",
                "entity_type": "str",
                "normalized_value": "str",
                "raw_values": "list[str]",
                "confidence": "float",
                "provenance": "str",
                "first_seen": "datetime",
                "last_seen": "datetime",
            },
            required_fields=["id", "entity_type", "normalized_value"],
            optional_fields=["raw_values", "confidence", "provenance"],
        ),
        "1.1": SchemaVersion(
            name="entity",
            version="1.1",
            fields={
                "id": "str",
                "entity_type": "str",
                "normalized_value": "str",
                "raw_values": "list[str]",
                "confidence": "float",
                "provenance": "str",
                "first_seen": "datetime",
                "last_seen": "datetime",
                "classification": "str",
                "organization_id": "str",
            },
            required_fields=["id", "entity_type", "normalized_value"],
            optional_fields=["raw_values", "confidence", "provenance", "classification", "organization_id"],
            successor_version=None,
        ),
    },
    "event": {
        "1.0": SchemaVersion(
            name="event",
            version="1.0",
            fields={
                "event_id": "str",
                "topic": "str",
                "event_type": "str",
                "source": "str",
                "payload": "dict",
                "version": "int",
                "timestamp": "datetime",
                "correlation_id": "str",
            },
            required_fields=["event_id", "topic", "event_type", "source", "payload", "version"],
            optional_fields=["timestamp", "correlation_id"],
        ),
    },
    "graph_node": {
        "1.0": SchemaVersion(
            name="graph_node",
            version="1.0",
            fields={
                "entity_id": "str",
                "entity_type": "str",
                "label": "str",
                "properties": "dict",
            },
            required_fields=["entity_id", "entity_type", "label"],
            optional_fields=["properties"],
        ),
    },
    "graph_edge": {
        "1.0": SchemaVersion(
            name="graph_edge",
            version="1.0",
            fields={
                "relationship_id": "str",
                "from_entity_id": "str",
                "to_entity_id": "str",
                "relationship_type": "str",
                "confidence": "float",
                "source_id": "str",
                "timestamp": "datetime",
                "properties": "dict",
            },
            required_fields=["relationship_id", "from_entity_id", "to_entity_id", "relationship_type"],
            optional_fields=["confidence", "source_id", "timestamp", "properties"],
        ),
    },
    "search_query": {
        "1.0": SchemaVersion(
            name="search_query",
            version="1.0",
            fields={
                "query": "str",
                "limit": "int",
                "offset": "int",
                "filters": "dict",
                "sort_by": "str",
                "sort_order": "str",
            },
            required_fields=["query"],
            optional_fields=["limit", "offset", "filters", "sort_by", "sort_order"],
        ),
    },
    "evidence": {
        "1.0": SchemaVersion(
            name="evidence",
            version="1.0",
            fields={
                "evidence_id": "str",
                "source_id": "str",
                "content_type": "str",
                "content_hash": "str",
                "classification": "str",
                "collected_at": "datetime",
            },
            required_fields=["evidence_id", "source_id", "content_type", "content_hash"],
            optional_fields=["classification", "collected_at"],
        ),
    },
    "api_request": {
        "1.0": SchemaVersion(
            name="api_request",
            version="1.0",
            fields={
                "method": "str",
                "path": "str",
                "headers": "dict",
                "body": "dict",
                "query_params": "dict",
                "correlation_id": "str",
            },
            required_fields=["method", "path"],
            optional_fields=["headers", "body", "query_params", "correlation_id"],
        ),
    },
}


def get_schema(name: str, version: str) -> SchemaVersion | None:
    """Get a specific schema version."""
    versions = SCHEMA_REGISTRY.get(name, {})
    return versions.get(version)


def get_latest_version(name: str) -> str | None:
    """Get the latest non-deprecated version of a schema."""
    versions = SCHEMA_REGISTRY.get(name, {})
    latest = None
    for v in versions.values():
        if not v.deprecated:
            if latest is None or v.version > latest.version:
                latest = v
    return latest.version if latest else None


def check_backward_compatibility(name: str, from_version: str, to_version: str) -> tuple[bool, list[str]]:
    """Check if migrating from one version to another is backward compatible.

    Returns (is_compatible, list_of_issues).
    """
    old = get_schema(name, from_version)
    new = get_schema(name, to_version)

    if old is None or new is None:
        return False, [f"Schema {name} version not found"]

    issues: list[str] = []

    # Check that all required fields in old version are still present in new
    for field in old.required_fields:
        if field not in new.fields:
            issues.append(f"Required field '{field}' removed in {to_version}")

    # Check that no required fields were added (would break old data)
    for field in new.required_fields:
        if field not in old.fields:
            issues.append(f"New required field '{field}' added in {to_version} — old data missing this field")

    return len(issues) == 0, issues


def migrate_entity(data: dict[str, Any], from_version: str, to_version: str) -> MigrationResult:
    """Migrate entity data from one schema version to another."""
    migrated = dict(data)
    migrated_fields: list[str] = []
    added_fields: list[str] = []
    removed_fields: list[str] = []
    errors: list[str] = []

    old = get_schema("entity", from_version)
    new = get_schema("entity", to_version)

    if old is None or new is None:
        return MigrationResult(
            from_version=from_version,
            to_version=to_version,
            migrated_fields=[],
            added_fields=[],
            removed_fields=[],
            success=False,
            errors=["Schema version not found"],
        )

    # Add new optional fields with defaults
    for field in new.optional_fields:
        if field not in migrated:
            migrated[field] = None
            added_fields.append(field)

    # Check required fields exist
    for field in new.required_fields:
        if field not in migrated:
            errors.append(f"Missing required field: {field}")

    # Mark migrated fields
    for field in old.fields:
        if field in new.fields and field in data:
            migrated_fields.append(field)

    success = len(errors) == 0

    if success:
        # In a real system, we'd persist the migrated data
        pass

    return MigrationResult(
        from_version=from_version,
        to_version=to_version,
        migrated_fields=migrated_fields,
        added_fields=added_fields,
        removed_fields=removed_fields,
        success=success,
        errors=errors,
    )

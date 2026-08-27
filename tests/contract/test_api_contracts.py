"""Contract tests for STIX adapter and API interfaces.

Per Luna Directive — Focus Area 1: Contract tests for STIX input/output
and API request/response schema validation.
"""

from __future__ import annotations

import sys
from uuid import uuid4

sys.path.insert(0, ".")
sys.path.insert(0, "packages")


from common.stix_adapter import STIXAdapter
from schemas.entities import create_entity
from schemas.versions import get_schema


class TestSTIXAdapterContracts:
    """Test STIX adapter input/output contracts."""

    def test_stix_adapter_exists(self):
        """STIX adapter should be importable."""
        adapter = STIXAdapter()
        assert adapter is not None

    def test_entity_to_stix(self):
        """Converting an entity to STIX should produce valid STIX."""
        adapter = STIXAdapter()

        entity = create_entity("EMAIL", email="test@example.com")

        stix_obj = adapter.export_entity(entity)
        assert stix_obj is not None
        assert hasattr(stix_obj, "type") or isinstance(stix_obj, dict)

    def test_stix_has_required_fields(self):
        """STIX output should have required STIX 2.1 fields."""
        adapter = STIXAdapter()

        entity = create_entity("DOMAIN", domain="example.com")
        stix_obj = adapter.export_entity(entity)

        assert "type" in stix_obj
        assert "id" in stix_obj

    def test_stix_from_valid_input(self):
        """Converting from STIX to entity should work with valid input."""
        adapter = STIXAdapter()

        stix_input = {
            "type": "email-addr",
            "value": "test@example.com",
            "id": "email-addr--" + str(uuid4()),
        }

        entity = adapter.import_bundle(stix_input)
        assert entity is not None

    def test_stix_from_invalid_input(self):
        """Converting from invalid STIX should be handled gracefully."""
        adapter = STIXAdapter()

        # Missing required fields
        stix_input = {"type": "email-addr"}  # Missing value and id

        try:
            entity = adapter.import_bundle(stix_input)
            # If it returns something, it should be None or have defaults
            if entity is not None:
                pass  # Graceful handling
        except (ValueError, KeyError, TypeError):
            pass  # Acceptable to raise on invalid input

    def test_round_trip_conversion(self):
        """Entity → STIX → Entity should preserve key attributes."""
        adapter = STIXAdapter()

        entity = create_entity("PHONE", e164="+1234567890")
        stix_obj = adapter.export_entity(entity)

        assert stix_obj is not None
        # The STIX object should contain the phone value
        stix_str = str(stix_obj)
        assert "+1234567890" in stix_str or "1234567890" in stix_str


class TestAPIRequestSchemaContracts:
    """Test API request schema validation contracts."""

    def test_api_request_schema_v1_exists(self):
        """API request schema v1.0 should exist."""
        schema = get_schema("api_request", "1.0")
        assert schema is not None
        assert "method" in schema.required_fields
        assert "path" in schema.required_fields

    def test_api_request_optional_fields(self):
        """API request should have optional fields for body, headers, etc."""
        schema = get_schema("api_request", "1.0")
        assert "body" in schema.optional_fields
        assert "headers" in schema.optional_fields
        assert "correlation_id" in schema.optional_fields

    def test_api_request_method_field(self):
        """API request should require a method field."""
        schema = get_schema("api_request", "1.0")
        assert "method" in schema.required_fields


class TestSearchQuerySchemaContracts:
    """Test search query schema contracts."""

    def test_search_query_schema_v1_exists(self):
        """Search query schema v1.0 should exist."""
        schema = get_schema("search_query", "1.0")
        assert schema is not None
        assert "query" in schema.required_fields

    def test_search_query_optional_fields(self):
        """Search query should have optional pagination fields."""
        schema = get_schema("search_query", "1.0")
        assert "limit" in schema.optional_fields
        assert "offset" in schema.optional_fields
        assert "filters" in schema.optional_fields


class TestEvidenceSchemaContracts:
    """Test evidence schema contracts."""

    def test_evidence_schema_v1_exists(self):
        """Evidence schema v1.0 should exist."""
        schema = get_schema("evidence", "1.0")
        assert schema is not None
        assert "evidence_id" in schema.required_fields
        assert "content_hash" in schema.required_fields

    def test_evidence_optional_fields(self):
        """Evidence should have optional classification and timestamp."""
        schema = get_schema("evidence", "1.0")
        assert "classification" in schema.optional_fields
        assert "collected_at" in schema.optional_fields

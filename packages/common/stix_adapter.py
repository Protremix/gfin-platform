# GFIN STIX 2.x Import/Export Adapter
#
# Per Constitution Article XV: Provider independence through interoperability standards.
# Per Master Spec §25: STIX/TAXII support for cross-organization intelligence sharing.
#
# STIX is an INTEROPERABILITY FORMAT, not the GFIN canonical data model.
# This adapter converts between GFIN canonical entities and STIX 2.x objects.
#
# License: stix2 library is BSD-3-Clause (OASIS official)
# Repository: https://github.com/oasis-open/cti-python-stix2

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from stix2 import (
    URL as STIXURL,
)
from stix2 import (
    Bundle,
    DomainName,
    EmailAddress,
    Identity,
    IPv4Address,
    Report,
)
from stix2 import (
    Campaign as STIXCampaign,
)
from stix2 import (
    Location as STIXLocation,
)
from stix2 import (
    Relationship as STIXRelationship,
)

from schemas.base import BaseEntity, BaseRelationship, BaseReport
from schemas.enums import EntityType

# Custom STIX properties for GFIN-specific fields (STIX 2.x allows x_* custom properties)
GFIN_CLASSIFICATION = "x_gfin_classification"
GFIN_JURISDICTION = "x_gfin_jurisdiction"
GFIN_SOURCE_ID = "x_gfin_source_id"
GFIN_SOURCE_TYPE = "x_gfin_source_type"
GFIN_ORG_ID = "x_gfin_organization_id"
GFIN_TRIAGE_PRIORITY = "x_gfin_triage_priority"
GFIN_SCORE = "x_gfin_score"


def _extract_custom_props(entity: BaseEntity) -> dict[str, Any]:
    """Extract GFIN-specific custom properties from a BaseEntity."""
    props: dict[str, Any] = {}

    # Classification is a nested Classification model
    cls = getattr(entity, "classification", None)
    if cls is not None:
        if hasattr(cls, "classification"):
            props[GFIN_CLASSIFICATION] = cls.classification.value if hasattr(cls.classification, "value") else str(cls.classification)
        else:
            if hasattr(cls, "value"):
                props[GFIN_CLASSIFICATION] = cls.value
            else:
                props[GFIN_CLASSIFICATION] = str(cls)

        if hasattr(cls, "jurisdiction") and cls.jurisdiction:
            props[GFIN_JURISDICTION] = cls.jurisdiction

    org_id = getattr(entity, "organization_id", None)
    if org_id:
        props[GFIN_ORG_ID] = org_id

    return props


class STIXAdapter:
    """Adapter for converting between GFIN canonical entities and STIX 2.x objects.

    Layer A: In-memory conversion (this implementation)
    Layer B: Persistent STIX storage and TAXII server (REQUIRES EXTERNAL INFRASTRUCTURE)
    """

    def __init__(self) -> None:
        self._export_count = 0
        self._import_count = 0
        self._errors: list[str] = []

    # ─── Export: GFIN → STIX ───

    def export_entity(self, entity: BaseEntity) -> Any:
        """Convert a single GFIN entity to a STIX 2.x object."""
        custom = _extract_custom_props(entity)
        entity_type = str(getattr(entity, "entity_type", "") or "")
        value = getattr(entity, "normalized_value", "") or ""

        if entity_type == EntityType.EMAIL.value:
            return EmailAddress(
                id=f"email-addr--{uuid.uuid5(uuid.NAMESPACE_DNS, value)}",
                value=value,
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.DOMAIN.value:
            return DomainName(
                id=f"domain-name--{uuid.uuid5(uuid.NAMESPACE_DNS, value)}",
                value=value,
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.IP.value:
            return IPv4Address(
                id=f"ipv4-addr--{uuid.uuid5(uuid.NAMESPACE_DNS, value)}",
                value=value,
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.URL.value:
            return STIXURL(
                id=f"url--{uuid.uuid5(uuid.NAMESPACE_URL, value)}",
                value=value,
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.PERSON.value:
            return Identity(
                id=f"identity--{uuid.uuid4()}",
                name=value or "Unknown",
                identity_class="individual",
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.ORGANIZATION.value:
            return Identity(
                id=f"identity--{uuid.uuid4()}",
                name=value or "Unknown",
                identity_class="organization",
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.CAMPAIGN.value:
            return STIXCampaign(
                id=f"campaign--{uuid.uuid4()}",
                name=value or "GFIN Campaign",
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        elif entity_type == EntityType.COUNTRY.value:
            cls = getattr(entity, "classification", None)
            country = cls.jurisdiction if cls and hasattr(cls, "jurisdiction") else ""
            return STIXLocation(
                id=f"location--{uuid.uuid4()}",
                name=value or "Unknown",
                country=country or "",
                allow_custom=True,
                **{k: v for k, v in custom.items() if v},
            )
        else:
            return {
                "type": "x-gfin-entity",
                "id": f"x-gfin-entity--{uuid.uuid4()}",
                "entity_type": entity_type,
                "value": value,
                **{k: v for k, v in custom.items() if v},
            }

    def export_relationship(self, rel: BaseRelationship) -> STIXRelationship:
        """Convert a GFIN relationship to a STIX 2.x Relationship."""
        return STIXRelationship(
            id=f"relationship--{uuid.uuid4()}",
            relationship_type=str(rel.relationship_type).lower().replace("_", "-"),
            source_ref=f"gfin--{rel.source_entity_id}" if hasattr(rel, "source_entity_id") else "",
            target_ref=f"gfin--{rel.target_entity_id}" if hasattr(rel, "target_entity_id") else "",
            created=datetime.now(UTC),
            modified=datetime.now(UTC),
            allow_custom=True,
        )

    def export_entities(
        self,
        entities: list[BaseEntity],
        relationships: list[BaseRelationship] | None = None,
    ) -> Bundle:
        """Export a collection of GFIN entities and relationships to a STIX bundle."""
        objects: list[Any] = []
        for entity in entities:
            try:
                obj = self.export_entity(entity)
                if obj:
                    objects.append(obj)
                self._export_count += 1
            except Exception as e:
                self._errors.append(f"Export error for entity: {e}")

        if relationships:
            for rel in relationships:
                try:
                    obj = self.export_relationship(rel)
                    objects.append(obj)
                    self._export_count += 1
                except Exception as e:
                    self._errors.append(f"Export error for relationship: {e}")

        return Bundle(objects=objects, allow_custom=True)

    def export_report(self, report: BaseReport) -> Report:
        """Export a GFIN report to a STIX 2.x Report."""
        custom: dict[str, Any] = {GFIN_CLASSIFICATION: "PUBLIC"}
        return Report(
            id=f"report--{uuid.uuid4()}",
            name=getattr(report, "title", "GFIN Report"),
            description=getattr(report, "description", ""),
            labels=[getattr(report, "category", "fraud")],
            published=datetime.now(UTC),
            object_refs=[],
            allow_custom=True,
            **custom,
        )

    # ─── Import: STIX → GFIN ───

    def import_bundle(self, bundle: Bundle) -> dict[str, list[dict[str, Any]]]:
        """Import a STIX 2.x bundle and convert to GFIN canonical format."""
        result: dict[str, list[dict[str, Any]]] = {
            "entities": [],
            "relationships": [],
            "reports": [],
            "observations": [],
            "errors": [],
        }

        # Empty bundles may not have .objects attribute
        objects = getattr(bundle, "objects", None) or []

        for obj in objects:
            try:
                stix_type = getattr(obj, "type", "")

                if stix_type == "email-addr":
                    result["entities"].append(self._import_email(obj))
                elif stix_type == "domain-name":
                    result["entities"].append(self._import_domain(obj))
                elif stix_type == "ipv4-addr":
                    result["entities"].append(self._import_ipv4(obj))
                elif stix_type == "url":
                    result["entities"].append(self._import_url(obj))
                elif stix_type == "identity":
                    result["entities"].append(self._import_identity(obj))
                elif stix_type == "report":
                    result["reports"].append(self._import_report(obj))
                elif stix_type == "relationship":
                    result["relationships"].append(self._import_relationship(obj))
                else:
                    result["observations"].append({
                        "source_type": "STIX",
                        "stix_type": stix_type,
                        "raw": str(obj),
                        "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
                    })

                self._import_count += 1
            except Exception as e:
                result["errors"].append({"error": f"Import error: {e}"})
                self._errors.append(str(e))

        return result

    # ─── Import helpers ───

    def _import_email(self, obj: EmailAddress) -> dict[str, Any]:
        return {
            "entity_type": EntityType.EMAIL.value,
            "entity_value": obj.value,
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "jurisdiction": getattr(obj, GFIN_JURISDICTION, None),
            "source_type": "STIX",
        }

    def _import_domain(self, obj: DomainName) -> dict[str, Any]:
        return {
            "entity_type": EntityType.DOMAIN.value,
            "entity_value": obj.value,
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "jurisdiction": getattr(obj, GFIN_JURISDICTION, None),
            "source_type": "STIX",
        }

    def _import_ipv4(self, obj: IPv4Address) -> dict[str, Any]:
        return {
            "entity_type": EntityType.IP.value,
            "entity_value": obj.value,
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "jurisdiction": getattr(obj, GFIN_JURISDICTION, None),
            "source_type": "STIX",
        }

    def _import_url(self, obj: STIXURL) -> dict[str, Any]:
        return {
            "entity_type": EntityType.URL.value,
            "entity_value": obj.value,
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "jurisdiction": getattr(obj, GFIN_JURISDICTION, None),
            "source_type": "STIX",
        }

    def _import_identity(self, obj: Identity) -> dict[str, Any]:
        if obj.identity_class == "organization":
            etype = EntityType.ORGANIZATION.value
        elif obj.identity_class == "individual":
            etype = EntityType.PERSON.value
        else:
            etype = "UNKNOWN"
        return {
            "entity_type": etype,
            "entity_value": obj.name,
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "jurisdiction": getattr(obj, GFIN_JURISDICTION, None),
            "source_type": "STIX",
        }

    def _import_report(self, obj: Report) -> dict[str, Any]:
        return {
            "title": obj.name,
            "description": obj.description or "",
            "category": obj.labels[0] if obj.labels else "fraud",
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "source_type": "STIX",
        }

    def _import_relationship(self, obj: STIXRelationship) -> dict[str, Any]:
        return {
            "relationship_type": obj.relationship_type.upper().replace("-", "_"),
            "source_entity_id": obj.source_ref.replace("gfin--", ""),
            "target_entity_id": obj.target_ref.replace("gfin--", ""),
            "classification": getattr(obj, GFIN_CLASSIFICATION, "PUBLIC"),
            "source_type": "STIX",
        }

    # ─── Stats ───

    def stats(self) -> dict[str, int]:
        return {
            "exported": self._export_count,
            "imported": self._import_count,
            "errors": len(self._errors),
        }

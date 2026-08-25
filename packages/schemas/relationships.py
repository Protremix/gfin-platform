# GFIN Concrete Relationship Models
#
# Per Master Spec §6: 20+ relationship types with provenance.
# Each relationship connects two entities with a typed connection.

from __future__ import annotations

from pydantic import field_validator, model_validator

from schemas.base import BaseRelationship
from schemas.enums import RelationshipType


class Relationship(BaseRelationship):
    """A typed, provenance-bearing connection between two entities.

    Extends BaseRelationship with relationship-type-specific validation.
    """

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        valid = {r.value for r in RelationshipType}
        if v not in valid:
            raise ValueError(f"Relationship type must be one of {valid}")
        return v

    @model_validator(mode="after")
    def validate_self_relationship(self):
        """A relationship must not connect an entity to itself."""
        if self.from_entity_id == self.to_entity_id:
            raise ValueError(
                f"Self-relationship not allowed: {self.from_entity_id} -> {self.to_entity_id}"
            )
        return self


# ─── Typed Relationship Factories ───


class OwnsRelationship(Relationship):
    """Entity A owns entity B (e.g., person owns phone)."""

    relationship_type: str = RelationshipType.OWNS.value


class UsesRelationship(Relationship):
    """Entity A uses entity B (e.g., person uses email)."""

    relationship_type: str = RelationshipType.USES.value


class HostedOnRelationship(Relationship):
    """Entity A is hosted on entity B (e.g., website hosted on IP)."""

    relationship_type: str = RelationshipType.HOSTED_ON.value


class ResolvesToRelationship(Relationship):
    """Entity A resolves to entity B (e.g., domain resolves to IP)."""

    relationship_type: str = RelationshipType.RESOLVES_TO.value


class RedirectsToRelationship(Relationship):
    """Entity A redirects to entity B (e.g., URL redirects to URL)."""

    relationship_type: str = RelationshipType.REDIRECTS_TO.value


class RegisteredWithRelationship(Relationship):
    """Entity A is registered with entity B (e.g., domain registered with registrar)."""

    relationship_type: str = RelationshipType.REGISTERED_WITH.value


class SharesCertificateRelationship(Relationship):
    """Entity A shares a certificate with entity B."""

    relationship_type: str = RelationshipType.SHARES_CERTIFICATE.value


class SharesInfrastructureRelationship(Relationship):
    """Entity A shares infrastructure with entity B."""

    relationship_type: str = RelationshipType.SHARES_INFRASTRUCTURE.value


class ReferencesRelationship(Relationship):
    """Entity A references entity B (e.g., URL references domain)."""

    relationship_type: str = RelationshipType.REFERENCES.value


class ContactedRelationship(Relationship):
    """Entity A contacted entity B (e.g., phone contacted email)."""

    relationship_type: str = RelationshipType.CONTACTED.value


class ReportedByRelationship(Relationship):
    """Entity A was reported by entity B (e.g., URL reported by person)."""

    relationship_type: str = RelationshipType.REPORTED_BY.value


class RelatedToRelationship(Relationship):
    """Entity A is related to entity B (generic)."""

    relationship_type: str = RelationshipType.RELATED_TO.value


class MatchesRelationship(Relationship):
    """Entity A matches entity B (cross-border match)."""

    relationship_type: str = RelationshipType.MATCHES.value


class PartOfCampaignRelationship(Relationship):
    """Entity A is part of campaign B."""

    relationship_type: str = RelationshipType.PART_OF_CAMPAIGN.value


class ObservedInCaseRelationship(Relationship):
    """Entity A was observed in case B."""

    relationship_type: str = RelationshipType.OBSERVED_IN_CASE.value


class ObservedInCountryRelationship(Relationship):
    """Entity A was observed in country B."""

    relationship_type: str = RelationshipType.OBSERVED_IN_COUNTRY.value


class PaymentToRelationship(Relationship):
    """Entity A made payment to entity B."""

    relationship_type: str = RelationshipType.PAYMENT_TO.value


class SimilarToRelationship(Relationship):
    """Entity A is similar to entity B (fuzzy match)."""

    relationship_type: str = RelationshipType.SIMILAR_TO.value


class MonitoredByRelationship(Relationship):
    """Entity A is monitored by entity B (e.g., entity monitored by alert rule)."""

    relationship_type: str = RelationshipType.MONITORED_BY.value


# ─── Relationship Factory ───

RELATIONSHIP_TYPE_TO_CLASS: dict[str, type[Relationship]] = {
    RelationshipType.OWNS.value: OwnsRelationship,
    RelationshipType.USES.value: UsesRelationship,
    RelationshipType.HOSTED_ON.value: HostedOnRelationship,
    RelationshipType.RESOLVES_TO.value: ResolvesToRelationship,
    RelationshipType.REDIRECTS_TO.value: RedirectsToRelationship,
    RelationshipType.REGISTERED_WITH.value: RegisteredWithRelationship,
    RelationshipType.SHARES_CERTIFICATE.value: SharesCertificateRelationship,
    RelationshipType.SHARES_INFRASTRUCTURE.value: SharesInfrastructureRelationship,
    RelationshipType.REFERENCES.value: ReferencesRelationship,
    RelationshipType.CONTACTED.value: ContactedRelationship,
    RelationshipType.REPORTED_BY.value: ReportedByRelationship,
    RelationshipType.RELATED_TO.value: RelatedToRelationship,
    RelationshipType.MATCHES.value: MatchesRelationship,
    RelationshipType.PART_OF_CAMPAIGN.value: PartOfCampaignRelationship,
    RelationshipType.OBSERVED_IN_CASE.value: ObservedInCaseRelationship,
    RelationshipType.OBSERVED_IN_COUNTRY.value: ObservedInCountryRelationship,
    RelationshipType.PAYMENT_TO.value: PaymentToRelationship,
    RelationshipType.SIMILAR_TO.value: SimilarToRelationship,
    RelationshipType.MONITORED_BY.value: MonitoredByRelationship,
}


def create_relationship(rel_type: str, **kwargs) -> Relationship:
    """Factory function to create a relationship of the given type."""
    cls = RELATIONSHIP_TYPE_TO_CLASS.get(rel_type)
    if cls is None:
        raise ValueError(f"Unknown relationship type: {rel_type}")
    return cls(**kwargs)

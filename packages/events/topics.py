# GFIN Event Topics
#
# Per Master Spec §9: Initial event topics for the event bus.
# All events must be versioned.

from __future__ import annotations

from enum import StrEnum


class EventTopic(StrEnum):
    """Kafka/event bus topics per Master Spec §9."""

    ENTITY_CREATED = "entity.created"
    ENTITY_UPDATED = "entity.updated"
    OBSERVATION_CREATED = "observation.created"
    RELATIONSHIP_CREATED = "relationship.created"
    EVIDENCE_CREATED = "evidence.created"
    REPORT_CREATED = "report.created"
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_UPDATED = "campaign.updated"
    INFRASTRUCTURE_CHANGED = "infrastructure.changed"
    RISK_CHANGED = "risk.changed"
    ALERT_CREATED = "alert.created"
    POLICE_MATCH = "police.match"
    POLICE_REQUEST = "police.request"
    AUDIT_EVENT = "audit.event"

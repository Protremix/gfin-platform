# GFIN Extended Base Models
#
# Per Master Spec §5: Additional core data model types:
# Case, Campaign, Alert, Organization, Country/Jurisdiction, User, Access Policy

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from schemas.base import (
    AuditMetadata,
    Classification,
    Provenance,
    Timestamp,
    utc_now,
)
from schemas.enums import (
    AlertPriority,
    DataClassification,
    RiskLevel,
    UserRole,
)


class BaseCase(BaseModel):
    """An investigation case — groups related entities, observations, reports.

    CASE ≠ ENTITY. A case is an investigation context.
    It groups evidence and entities under jurisdictional authority.
    """

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8].upper())
    case_number: str = ""
    case_status: str = "OPEN"  # OPEN, UNDER_INVESTIGATION, CLOSED, ARCHIVED
    jurisdiction: str | None = None  # ISO 3166-1 alpha-2
    lead_investigator_id: str | None = None
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    related_entity_ids: list[str] = Field(default_factory=list)
    related_report_ids: list[str] = Field(default_factory=list)
    classification: Classification = Field(default_factory=lambda: Classification(
        classification=DataClassification.RESTRICTED
    ))

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseCampaign(BaseModel):
    """A fraud campaign — correlated set of potentially related fraud activity.

    CAMPAIGN ≠ ENTITY. A campaign groups entities showing coordinated activity.
    """

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8].upper())
    name: str = ""
    campaign_status: str = "ACTIVE"  # ACTIVE, DORMANT, DISMANTLED
    severity: str = "MEDIUM"  # RiskLevel value
    start_date: Timestamp | None = None
    end_date: Timestamp | None = None
    affected_countries: list[str] = Field(default_factory=list)
    fraud_type: str = ""
    entity_count: int = 0
    related_entity_ids: list[str] = Field(default_factory=list)
    classification: Classification = Field(default_factory=Classification)

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseAlert(BaseModel):
    """An alert — triggered by monitoring or detection rules.

    ALERT ≠ ENTITY. An alert is a notification of a detected event.
    """

    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8].upper())
    alert_type: str = ""
    priority: str = "P3"  # AlertPriority value
    alert_status: str = "NEW"  # NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    triggered_by: str = ""  # rule_id, monitoring_id, ai_analysis_id
    entity_ids: list[str] = Field(default_factory=list)
    description: str = ""
    classification: Classification = Field(default_factory=Classification)

    # Multi-tenant
    organization_id: str | None = None

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseOrganization(BaseModel):
    """An organization — law enforcement agency, NGO, or partner.

    Supports multi-tenant isolation. Every entity, observation, report
    can be scoped to an organization.
    """

    id: str = Field(default_factory=lambda: f"ORG-{__import__('uuid').uuid4().hex[:8].upper()}")
    name: str = ""
    org_type: str = ""  # law_enforcement, ngo, government, private, international
    country: str | None = None  # ISO 3166-1 alpha-2
    jurisdiction: str | None = None
    parent_organization_id: str | None = None  # For hierarchical orgs
    classification: Classification = Field(default_factory=Classification)

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class BaseCountry(BaseModel):
    """A country/jurisdiction — for geographic tracking and jurisdiction isolation.

    Supports jurisdiction-aware access control.
    """

    id: str = Field(default_factory=lambda: f"CTRY-{__import__('uuid').uuid4().hex[:8].upper()}")
    iso_code: str = ""  # ISO 3166-1 alpha-2
    name: str = ""
    region: str | None = None  # continent/region
    is_eu_member: bool = False
    data_protection_law: str | None = None  # GDPR, UK-GDPR, etc.

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    model_config = {"use_enum_values": True}

    @field_validator("iso_code")
    @classmethod
    def validate_iso_code(cls, v: str) -> str:
        if not v:
            raise ValueError("Country ISO code is required")
        v = v.upper().strip()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country ISO code must be 2 letters")
        return v


class BaseUser(BaseModel):
    """A GFIN user — authenticated individual with a role.

    User ≠ Entity. A user is an authenticated platform participant.
    Roles determine access via RBAC + ABAC.
    """

    id: str = Field(default_factory=lambda: f"USR-{__import__('uuid').uuid4().hex[:8].upper()}")
    email: str = ""
    full_name: str = ""
    role: str = UserRole.CITIZEN.value
    organization_id: str | None = None
    jurisdiction: str | None = None  # ISO 3166-1 alpha-2
    is_active: bool = True
    mfa_enabled: bool = False

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    model_config = {"use_enum_values": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v:
            v = v.lower().strip()
        return v


class BaseAccessPolicy(BaseModel):
    """An access policy — defines who can access what data under what conditions.

    Supports ABAC evaluation: role + classification + jurisdiction + organization.
    """

    id: str = Field(default_factory=lambda: f"POL-{__import__('uuid').uuid4().hex[:8].upper()}")
    name: str = ""
    description: str = ""
    required_roles: list[str] = Field(default_factory=list)
    required_classifications: list[str] = Field(default_factory=list)  # DataClassification values
    required_jurisdictions: list[str] = Field(default_factory=list)
    required_organizations: list[str] = Field(default_factory=list)
    deny_by_default: bool = True
    is_active: bool = True

    # Lifecycle
    audit: AuditMetadata = Field(default_factory=AuditMetadata)

    model_config = {"use_enum_values": True}

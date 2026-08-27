# GFIN Schema Enums

from __future__ import annotations

from enum import StrEnum


class DataClassification(StrEnum):
    """Data classification levels per Constitution Article XX."""

    PUBLIC = "PUBLIC"
    COMMUNITY = "COMMUNITY"
    RESTRICTED = "RESTRICTED"
    LAW_ENFORCEMENT = "LAW_ENFORCEMENT"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


class EntityType(StrEnum):
    """Core entity types per Master Spec §5."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    DOMAIN = "DOMAIN"
    URL = "URL"
    IP = "IP"
    ASN = "ASN"
    NETWORK = "NETWORK"
    DNS_RECORD = "DNS_RECORD"
    CERTIFICATE = "CERTIFICATE"
    WEBSITE = "WEBSITE"
    TELEGRAM_IDENTIFIER = "TELEGRAM_IDENTIFIER"
    SOCIAL_ACCOUNT = "SOCIAL_ACCOUNT"
    CRYPTO_WALLET = "CRYPTO_WALLET"
    TRANSACTION = "TRANSACTION"
    PAYMENT_IDENTIFIER = "PAYMENT_IDENTIFIER"
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    REPORT = "REPORT"
    CASE = "CASE"
    CAMPAIGN = "CAMPAIGN"
    INFRASTRUCTURE_CLUSTER = "INFRASTRUCTURE_CLUSTER"
    FRAUD_PATTERN = "FRAUD_PATTERN"
    ALERT = "ALERT"
    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    SOURCE = "SOURCE"
    COUNTRY = "COUNTRY"


class RelationshipType(StrEnum):
    """Relationship types per Master Spec §6."""

    OWNS = "OWNS"
    USES = "USES"
    HOSTED_ON = "HOSTED_ON"
    RESOLVES_TO = "RESOLVES_TO"
    REDIRECTS_TO = "REDIRECTS_TO"
    REGISTERED_WITH = "REGISTERED_WITH"
    SHARES_CERTIFICATE = "SHARES_CERTIFICATE"
    SHARES_INFRASTRUCTURE = "SHARES_INFRASTRUCTURE"
    REFERENCES = "REFERENCES"
    CONTACTED = "CONTACTED"
    REPORTED_BY = "REPORTED_BY"
    RELATED_TO = "RELATED_TO"
    MATCHES = "MATCHES"
    PART_OF_CAMPAIGN = "PART_OF_CAMPAIGN"
    OBSERVED_IN_CASE = "OBSERVED_IN_CASE"
    OBSERVED_IN_COUNTRY = "OBSERVED_IN_COUNTRY"
    PAYMENT_TO = "PAYMENT_TO"
    SIMILAR_TO = "SIMILAR_TO"
    MONITORED_BY = "MONITORED_BY"


class ReportStatus(StrEnum):
    """Report states per Master Spec §18."""

    UNVERIFIED = "UNVERIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CORROBORATED = "CORROBORATED"
    DISPUTED = "DISPUTED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    VERIFIED = "VERIFIED"
    OFFICIALLY_ESTABLISHED = "OFFICIALLY_ESTABLISHED"


class RiskLevel(StrEnum):
    """Risk levels per Master Spec §21."""

    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertPriority(StrEnum):
    """Alert priorities per Master Spec §24."""

    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_MEDIUM = "P2"
    P3_INFORMATIONAL = "P3"


class ModuleStatus(StrEnum):
    """Module states per Constitution Article XLI."""

    NOT_STARTED = "NOT_STARTED"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    TESTING = "TESTING"
    BLOCKED = "BLOCKED"
    ACCEPTED = "ACCEPTED"
    DEPRECATED = "DEPRECATED"


class UserRole(StrEnum):
    """User roles per Master Spec §3."""

    CITIZEN = "CITIZEN"
    INVESTIGATOR = "INVESTIGATOR"
    ANALYST = "ANALYST"
    ADMINISTRATOR = "ADMINISTRATOR"


class Confidence(StrEnum):
    """Confidence levels for observations and claims."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class SourceReliability(StrEnum):
    """Source reliability assessment per Source Policy."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

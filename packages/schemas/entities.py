# GFIN Concrete Entity Models
#
# Per Master Spec §5 and §7:
# Each entity type has type-specific fields, validation, and normalization.
# An entity is a normalized, resolved object. An observation is a single sighting.
#
# All entities extend BaseEntity and inherit provenance, classification, and
# confidence tracking. Each concrete model adds type-specific validation.

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from pydantic import field_validator, model_validator

from schemas.base import BaseEntity, BaseObservation, utc_now
from schemas.enums import EntityType


# ─── Person ───

class PersonEntity(BaseEntity):
    """A person entity — name and aliases.

    Classification: RESTRICTED by default (personal data).
    Per Constitution: citizen reports are allegations until corroborated.
    """

    entity_type: EntityType = EntityType.PERSON
    full_name: str = ""
    aliases: list[str] = []
    date_of_birth: datetime | None = None  # RESTRICTED
    nationality: str | None = None  # ISO 3166-1 alpha-2

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Person full_name is required")
        return v.strip()

    @field_validator("nationality")
    @classmethod
    def validate_nationality(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r'^[A-Z]{2}$', v):
            raise ValueError("Nationality must be ISO 3166-1 alpha-2 code")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.full_name.lower().strip()
        if self.full_name and self.full_name not in self.raw_values:
            self.raw_values.append(self.full_name)
        for alias in self.aliases:
            if alias and alias not in self.raw_values:
                self.raw_values.append(alias)
        return self


# ─── Organization ───

class OrganizationEntity(BaseEntity):
    """An organization entity."""

    entity_type: EntityType = EntityType.ORGANIZATION
    name: str = ""
    registration_number: str | None = None
    registration_country: str | None = None  # ISO 3166-1 alpha-2
    organization_type: str | None = None  # e.g., "company", "nonprofit", "government"

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Organization name is required")
        return v.strip()

    @field_validator("registration_country")
    @classmethod
    def validate_country(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r'^[A-Z]{2}$', v):
            raise ValueError("Registration country must be ISO 3166-1 alpha-2")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.name.lower().strip()
        if self.name and self.name not in self.raw_values:
            self.raw_values.append(self.name)
        return self


# ─── Phone ───

class PhoneEntity(BaseEntity):
    """A phone number entity — E.164 normalized."""

    entity_type: EntityType = EntityType.PHONE
    e164: str = ""  # +34612345678
    country_code: str | None = None  # +34
    country: str | None = None  # ES
    carrier: str | None = None
    line_type: str | None = None  # mobile, landline, voip

    @field_validator("e164")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        if not v:
            raise ValueError("Phone e164 is required")
        # Normalize: remove all non-digit except leading +
        normalized = re.sub(r'[^\d+]', '', v)
        if not normalized.startswith('+'):
            normalized = '+' + normalized
        if not re.match(r'^\+\d{6,15}$', normalized):
            raise ValueError(f"Phone must be valid E.164 format (got {normalized})")
        return normalized

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.e164
        if self.e164 and self.e164 not in self.raw_values:
            self.raw_values.append(self.e164)
        # Extract country code from E.164 (simplified — first 1-3 digits after +)
        if not self.country_code and self.e164:
            self.country_code = self.e164[:3]  # +XX (approximate)
        return self


# ─── Email ───

class EmailEntity(BaseEntity):
    """An email address entity."""

    entity_type: EntityType = EntityType.EMAIL
    email: str = ""
    local_part: str = ""
    domain_part: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v:
            raise ValueError("Email is required")
        v = v.lower().strip()
        if not re.match(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$', v):
            raise ValueError(f"Invalid email format: {v}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.email
        if self.email:
            parts = self.email.split('@', 1)
            self.local_part = parts[0]
            self.domain_part = parts[1] if len(parts) > 1 else ""
            if self.email not in self.raw_values:
                self.raw_values.append(self.email)
        return self


# ─── Domain ───

class DomainEntity(BaseEntity):
    """A domain name entity."""

    entity_type: EntityType = EntityType.DOMAIN
    domain: str = ""
    tld: str = ""
    registrar: str | None = None
    registration_date: datetime | None = None
    expiry_date: datetime | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v:
            raise ValueError("Domain is required")
        v = v.lower().strip()
        if len(v) > 253:
            raise ValueError("Domain exceeds 253 chars")
        if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$', v):
            raise ValueError(f"Invalid domain format: {v}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.domain
        if self.domain:
            parts = self.domain.rsplit('.', 1)
            self.tld = parts[1] if len(parts) > 1 else ""
            if self.domain not in self.raw_values:
                self.raw_values.append(self.domain)
        return self


# ─── URL ───

class URLEntity(BaseEntity):
    """A URL entity."""

    entity_type: EntityType = EntityType.URL
    url: str = ""
    scheme: str = ""
    domain: str = ""
    path: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v:
            raise ValueError("URL is required")
        if not re.match(r'^https?://', v, re.IGNORECASE):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL exceeds 2048 chars")
        return v.strip()

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.url
        if self.url:
            parsed = urlparse(self.url)
            self.scheme = parsed.scheme or ""
            self.domain = parsed.hostname or ""
            self.path = parsed.path or ""
            if self.url not in self.raw_values:
                self.raw_values.append(self.url)
        return self


# ─── IP Address ───

class IPEntity(BaseEntity):
    """An IP address entity — IPv4 or IPv6."""

    entity_type: EntityType = EntityType.IP
    ip: str = ""
    ip_version: int = 4  # 4 or 6
    asn: str | None = None
    country: str | None = None  # ISO 3166-1 alpha-2
    isp: str | None = None
    is_tor_exit: bool = False
    is_vpn: bool = False

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not v:
            raise ValueError("IP address is required")
        try:
            addr = ipaddress.ip_address(v)
            return str(addr)  # Normalized form
        except ValueError:
            raise ValueError(f"Invalid IP address: {v}")

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.ip
        if self.ip:
            self.ip_version = 6 if ':' in self.ip else 4
            if self.ip not in self.raw_values:
                self.raw_values.append(self.ip)
        return self


# ─── ASN ───

class ASNEntity(BaseEntity):
    """An Autonomous System Number entity."""

    entity_type: EntityType = EntityType.ASN
    asn_number: int = 0
    holder_name: str = ""
    country: str | None = None
    network_prefixes: list[str] = []

    @field_validator("asn_number")
    @classmethod
    def validate_asn(cls, v: int) -> int:
        if v < 1 or v > 4294967295:
            raise ValueError(f"ASN must be 1-4294967295 (got {v})")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"AS{self.asn_number}"
        if not self.holder_name:
            self.holder_name = f"AS{self.asn_number}"
        return self


# ─── Network ───

class NetworkEntity(BaseEntity):
    """A network/CIDR entity."""

    entity_type: EntityType = EntityType.NETWORK
    cidr: str = ""
    network_type: str | None = None  # datacenter, residential, mobile
    country: str | None = None

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        if not v:
            raise ValueError("CIDR is required")
        try:
            net = ipaddress.ip_network(v, strict=False)
            return str(net)
        except ValueError:
            raise ValueError(f"Invalid CIDR: {v}")

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.cidr
        if self.cidr and self.cidr not in self.raw_values:
            self.raw_values.append(self.cidr)
        return self


# ─── DNS Record ───

class DNSRecordEntity(BaseEntity):
    """A DNS record entity."""

    entity_type: EntityType = EntityType.DNS_RECORD
    record_type: str = "A"  # A, AAAA, MX, TXT, NS, CNAME, etc.
    record_value: str = ""
    ttl: int | None = None
    domain: str = ""

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, v: str) -> str:
        v = v.upper().strip()
        valid = {"A", "AAAA", "MX", "TXT", "NS", "CNAME", "PTR", "SOA", "SRV", "CAA"}
        if v not in valid:
            raise ValueError(f"DNS record type must be one of {valid}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v:
            raise ValueError("DNS record domain is required")
        return v.lower().strip()

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"{self.domain}|{self.record_type}|{self.record_value}"
        return self


# ─── Certificate ───

class CertificateEntity(BaseEntity):
    """An SSL/TLS certificate entity."""

    entity_type: EntityType = EntityType.CERTIFICATE
    serial_number: str = ""
    issuer: str = ""
    subject: str = ""
    fingerprint_sha256: str = ""
    not_before: datetime | None = None
    not_after: datetime | None = None

    @field_validator("fingerprint_sha256")
    @classmethod
    def validate_fingerprint(cls, v: str) -> str:
        if v and not re.match(r'^[a-fA-F0-9:]{64,69}$', v):
            raise ValueError("Certificate fingerprint must be SHA-256 hex")
        return v.lower() if v else v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.fingerprint_sha256 or self.serial_number
        return self


# ─── Website ───

class WebsiteEntity(BaseEntity):
    """A website entity — content snapshot of a URL."""

    entity_type: EntityType = EntityType.WEBSITE
    title: str = ""
    content_hash: str = ""
    technologies: list[str] = []
    status_code: int | None = None
    redirect_chain: list[str] = []

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.content_hash or self.id
        return self


# ─── Telegram ───

class TelegramIdentifierEntity(BaseEntity):
    """A Telegram identifier entity — username, phone, or user ID."""

    entity_type: EntityType = EntityType.TELEGRAM_IDENTIFIER
    telegram_type: str = "username"  # username, phone, user_id
    username: str | None = None
    phone: str | None = None
    user_id: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().lstrip('@')
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', v):
                raise ValueError("Telegram username must be 5-32 chars, alphanumeric + underscore")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            if self.username:
                self.normalized_value = f"tg:@{self.username.lower()}"
            elif self.phone:
                self.normalized_value = f"tg:{self.phone}"
            elif self.user_id:
                self.normalized_value = f"tg:id:{self.user_id}"
            else:
                self.normalized_value = self.id
        return self


# ─── Social Account ───

class SocialAccountEntity(BaseEntity):
    """A social media account entity."""

    entity_type: EntityType = EntityType.SOCIAL_ACCOUNT
    platform: str = ""  # facebook, twitter, instagram, linkedin, etc.
    username: str = ""
    user_id: str | None = None
    profile_url: str | None = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if not v:
            raise ValueError("Social platform is required")
        return v.lower().strip()

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"{self.platform}:{self.username.lower()}"
        return self


# ─── Crypto Wallet ───

class CryptoWalletEntity(BaseEntity):
    """A cryptocurrency wallet address entity."""

    entity_type: EntityType = EntityType.CRYPTO_WALLET
    blockchain: str = "bitcoin"  # bitcoin, ethereum, tron, etc.
    address: str = ""
    address_type: str | None = None  # legacy, segwit, bech32, contract, etc.
    balance: float | None = None
    first_transaction: datetime | None = None
    last_transaction: datetime | None = None
    transaction_count: int = 0

    @field_validator("blockchain")
    @classmethod
    def validate_blockchain(cls, v: str) -> str:
        if not v:
            raise ValueError("Blockchain type is required")
        return v.lower().strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v:
            raise ValueError("Wallet address is required")
        return v.strip()

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"{self.blockchain}:{self.address}"
        return self


# ─── Transaction ───

class TransactionEntity(BaseEntity):
    """A blockchain transaction entity."""

    entity_type: EntityType = EntityType.TRANSACTION
    blockchain: str = ""
    tx_hash: str = ""
    from_address: str = ""
    to_address: str = ""
    amount: float = 0.0
    token: str | None = None
    timestamp: datetime | None = None
    block_number: int | None = None

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"{self.blockchain}:{self.tx_hash}"
        return self


# ─── Payment Identifier ───

class PaymentIdentifierEntity(BaseEntity):
    """A payment identifier entity — IBAN, PayPal, etc."""

    entity_type: EntityType = EntityType.PAYMENT_IDENTIFIER
    payment_type: str = ""  # iban, paypal, wise, western_union, etc.
    identifier: str = ""
    processor: str | None = None

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        if not v:
            raise ValueError("Payment type is required")
        return v.lower().strip()

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = f"{self.payment_type}:{self.identifier.lower()}"
        return self


# ─── Document ───

class DocumentEntity(BaseEntity):
    """A document entity."""

    entity_type: EntityType = EntityType.DOCUMENT
    doc_type: str = ""  # pdf, html, text, screenshot
    title: str | None = None
    content_hash: str = ""
    file_size: int | None = None
    language: str | None = None

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.content_hash or self.id
        return self


# ─── Image ───

class ImageEntity(BaseEntity):
    """An image entity."""

    entity_type: EntityType = EntityType.IMAGE
    content_hash: str = ""
    width: int | None = None
    height: int | None = None
    format: str | None = None  # png, jpg, webp
    file_size: int | None = None

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.content_hash or self.id
        return self


# ─── Report ───

class ReportEntity(BaseEntity):
    """A fraud report entity — citizen submission."""

    entity_type: EntityType = EntityType.REPORT
    status: str = "UNVERIFIED"  # ReportStatus enum value
    category: str = ""  # phishing, investment_fraud, romance_scam, etc.
    description: str = ""
    reporter_id: str | None = None
    country: str | None = None
    language: str | None = None
    risk_level: str = "UNKNOWN"
    related_entity_ids: list[str] = []

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        from schemas.enums import ReportStatus
        valid = {s.value for s in ReportStatus}
        if v not in valid:
            raise ValueError(f"Report status must be one of {valid}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.id
        return self


# ─── Case ───

class CaseEntity(BaseEntity):
    """An investigation case entity."""

    entity_type: EntityType = EntityType.CASE
    case_number: str = ""
    case_status: str = "OPEN"  # OPEN, UNDER_INVESTIGATION, CLOSED, ARCHIVED
    jurisdiction: str | None = None
    lead_investigator_id: str | None = None
    priority: str = "MEDIUM"
    related_entity_ids: list[str] = []
    related_report_ids: list[str] = []

    @field_validator("case_status")
    @classmethod
    def validate_case_status(cls, v: str) -> str:
        valid = {"OPEN", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED"}
        if v not in valid:
            raise ValueError(f"Case status must be one of {valid}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.case_number or self.id
        return self


# ─── Campaign ───

class CampaignEntity(BaseEntity):
    """A fraud campaign entity — grouped fraudulent activity."""

    entity_type: EntityType = EntityType.CAMPAIGN
    name: str = ""
    campaign_status: str = "ACTIVE"  # ACTIVE, DORMANT, DISMANTLED
    severity: str = "MEDIUM"
    start_date: datetime | None = None
    end_date: datetime | None = None
    affected_countries: list[str] = []
    fraud_type: str = ""
    entity_count: int = 0

    @field_validator("campaign_status")
    @classmethod
    def validate_campaign_status(cls, v: str) -> str:
        valid = {"ACTIVE", "DORMANT", "DISMANTLED"}
        if v not in valid:
            raise ValueError(f"Campaign status must be one of {valid}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.name.lower().strip() or self.id
        return self


# ─── Infrastructure Cluster ───

class InfrastructureClusterEntity(BaseEntity):
    """A cluster of related infrastructure entities."""

    entity_type: EntityType = EntityType.INFRASTRUCTURE_CLUSTER
    cluster_name: str = ""
    cluster_type: str = ""  # phishing_kit, scam_network, malspam
    member_entity_ids: list[str] = []
    shared_indicators: list[str] = []

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.cluster_name.lower().strip() or self.id
        return self


# ─── Fraud Pattern ───

class FraudPatternEntity(BaseEntity):
    """A fraud pattern entity — recurring indicators and tactics."""

    entity_type: EntityType = EntityType.FRAUD_PATTERN
    pattern_type: str = ""
    description: str = ""
    indicators: list[str] = []
    ttp_refs: list[str] = []  # MITRE ATT&CK style references

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.pattern_type.lower().strip() or self.id
        return self


# ─── Alert ───

class AlertEntity(BaseEntity):
    """An alert entity — triggered by monitoring or detection."""

    entity_type: EntityType = EntityType.ALERT
    alert_type: str = ""
    priority: str = "P3"  # AlertPriority value
    alert_status: str = "NEW"  # NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    triggered_by: str = ""  # rule_id, monitoring_id, ai_analysis_id
    entity_ids: list[str] = []
    description: str = ""

    @field_validator("alert_status")
    @classmethod
    def validate_alert_status(cls, v: str) -> str:
        valid = {"NEW", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"}
        if v not in valid:
            raise ValueError(f"Alert status must be one of {valid}")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.id
        return self


# ─── Country ───

class CountryEntity(BaseEntity):
    """A country entity — for geographic tracking."""

    entity_type: EntityType = EntityType.COUNTRY
    iso_code: str = ""  # ISO 3166-1 alpha-2
    name: str = ""
    region: str | None = None  # continent/region
    is_eu_member: bool = False

    @field_validator("iso_code")
    @classmethod
    def validate_iso_code(cls, v: str) -> str:
        if not v:
            raise ValueError("Country ISO code is required")
        v = v.upper().strip()
        if not re.match(r'^[A-Z]{2}$', v):
            raise ValueError("Country ISO code must be 2 letters")
        return v

    @model_validator(mode='after')
    def set_defaults(self):
        if not self.normalized_value:
            self.normalized_value = self.iso_code
        return self


# ─── Entity Factory ───

ENTITY_TYPE_TO_CLASS: dict[str, type[BaseEntity]] = {
    EntityType.PERSON.value: PersonEntity,
    EntityType.ORGANIZATION.value: OrganizationEntity,
    EntityType.PHONE.value: PhoneEntity,
    EntityType.EMAIL.value: EmailEntity,
    EntityType.DOMAIN.value: DomainEntity,
    EntityType.URL.value: URLEntity,
    EntityType.IP.value: IPEntity,
    EntityType.ASN.value: ASNEntity,
    EntityType.NETWORK.value: NetworkEntity,
    EntityType.DNS_RECORD.value: DNSRecordEntity,
    EntityType.CERTIFICATE.value: CertificateEntity,
    EntityType.WEBSITE.value: WebsiteEntity,
    EntityType.TELEGRAM_IDENTIFIER.value: TelegramIdentifierEntity,
    EntityType.SOCIAL_ACCOUNT.value: SocialAccountEntity,
    EntityType.CRYPTO_WALLET.value: CryptoWalletEntity,
    EntityType.TRANSACTION.value: TransactionEntity,
    EntityType.PAYMENT_IDENTIFIER.value: PaymentIdentifierEntity,
    EntityType.DOCUMENT.value: DocumentEntity,
    EntityType.IMAGE.value: ImageEntity,
    EntityType.REPORT.value: ReportEntity,
    EntityType.CASE.value: CaseEntity,
    EntityType.CAMPAIGN.value: CampaignEntity,
    EntityType.INFRASTRUCTURE_CLUSTER.value: InfrastructureClusterEntity,
    EntityType.FRAUD_PATTERN.value: FraudPatternEntity,
    EntityType.ALERT.value: AlertEntity,
    EntityType.COUNTRY.value: CountryEntity,
}


def create_entity(entity_type: str, **kwargs) -> BaseEntity:
    """Factory function to create an entity of the given type."""
    cls = ENTITY_TYPE_TO_CLASS.get(entity_type)
    if cls is None:
        raise ValueError(f"Unknown entity type: {entity_type}")
    return cls(**kwargs)

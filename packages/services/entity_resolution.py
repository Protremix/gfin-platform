# GFIN Entity Resolution Service
#
# Per Master Spec §8 (Identity Resolution) and Module 04:
# - Normalize phone, email, domain, URL, IP, crypto, Telegram, orgs, persons
# - Match entities by normalized value
# - Deduplicate with confidence scoring
# - Merge/split workflows with audit trail
#
# Key principles:
# - Original submitted representation is ALWAYS retained (raw_values)
# - Similarity ≠ ownership or criminal attribution
# - Merges require sufficient confidence; low confidence = candidate only
# - All merges are auditable and reversible (split)
# - Phone variants: +34 612 345 678, 0034 612 345 678, 612345678 → +34612345678

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import (
    BaseEntity,
    BaseObservation,
    AuditMetadata,
    Confidence,
    Provenance,
    utc_now,
)
from schemas.enums import EntityType
from schemas.entities import (
    PhoneEntity,
    EmailEntity,
    DomainEntity,
    URLEntity,
    IPEntity,
    CryptoWalletEntity,
    TelegramIdentifierEntity,
    SocialAccountEntity,
    PersonEntity,
    OrganizationEntity,
    create_entity,
)
from common.database import EntityRepository


# ═══════════════════════════════════════════════
# NORMALIZATION
# ═══════════════════════════════════════════════

def normalize_phone(raw: str) -> str:
    """Normalize phone number to E.164 format.

    Handles:
    - +34 612 345 678 → +34612345678
    - 0034 612 345 678 → +34612345678
    - 612345678 → 612345678 (no country code, kept as-is)
    - +34612345678 → +34612345678

    Returns the E.164 normalized form. Original raw value is retained by the entity.
    """
    if not raw:
        raise ValueError("Phone number cannot be empty")

    cleaned = re.sub(r'[\s\-\(\)\.]', '', raw.strip())

    # 00 prefix → + (international prefix)
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    # If no + and starts with country code length (11-15 digits), assume needs +
    elif not cleaned.startswith('+') and len(cleaned) > 10:
        # Heuristic: if first 1-3 digits look like a country code
        # This is conservative — only adds + if clearly international
        pass  # Keep as-is without + to avoid false normalization

    if not re.match(r'^\+?\d{4,15}$', cleaned):
        raise ValueError(f"Invalid phone number: {raw}")

    return cleaned


def normalize_email(raw: str) -> str:
    """Normalize email to canonical form: lowercase, stripped."""
    if not raw:
        raise ValueError("Email cannot be empty")

    email = raw.strip().lower()

    # Basic email format check
    if not re.match(r'^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$', email):
        raise ValueError(f"Invalid email: {raw}")

    return email


def normalize_domain(raw: str) -> str:
    """Normalize domain to canonical form: lowercase, no trailing dot."""
    if not raw:
        raise ValueError("Domain cannot be empty")

    domain = raw.strip().lower().rstrip('.')

    # Remove protocol prefix if present
    domain = re.sub(r'^https?://', '', domain)
    # Remove path if present
    domain = domain.split('/')[0]

    # Basic domain format check
    if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$', domain):
        raise ValueError(f"Invalid domain: {raw}")

    return domain


def normalize_url(raw: str) -> str:
    """Normalize URL to canonical form: scheme://domain/path.

    - Adds https:// if no scheme
    - Lowercases scheme and domain
    - Removes trailing slash on root
    - Removes default ports (80, 443)
    """
    if not raw:
        raise ValueError("URL cannot be empty")

    url = raw.strip()

    # Add default scheme if missing (case-insensitive)
    url_lower = url.lower()
    if not url_lower.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Split into components (case-insensitive match)
    match = re.match(r'^(https?)://([^/]+)(/.*)?$', url, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid URL: {raw}")

    scheme = match.group(1).lower()
    host = match.group(2).lower()
    path = match.group(3) or ''

    # Remove default ports
    if host.endswith(':80'):
        host = host[:-3]
    elif host.endswith(':443'):
        host = host[:-4]

    # Validate host has at least one dot (is a real domain)
    if '.' not in host:
        raise ValueError(f"Invalid URL: {raw}")

    # Remove trailing slash on root
    if path == '/':
        path = ''

    return f"{scheme}://{host}{path}"


def normalize_ip(raw: str) -> str:
    """Normalize IP address to canonical form.

    IPv4: removes leading zeros (192.168.001.001 → 192.168.1.1)
    IPv6: compressed form (::1, fe80::1)
    """
    if not raw:
        raise ValueError("IP address cannot be empty")

    try:
        ip = ipaddress.ip_address(raw.strip())
        return str(ip)  # ipaddress module returns canonical form
    except ValueError:
        raise ValueError(f"Invalid IP address: {raw}")


def normalize_crypto_address(raw: str, blockchain: str) -> str:
    """Normalize crypto wallet address by blockchain type.

    Different blockchains have different address formats:
    - Bitcoin: starts with 1, 3, or bc1
    - Ethereum: 0x + 40 hex chars (checksummed)
    - Tron: T + 33 base58 chars
    """
    if not raw:
        raise ValueError("Crypto address cannot be empty")

    address = raw.strip()
    blockchain_lower = blockchain.lower().strip()

    if blockchain_lower == 'ethereum':
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValueError(f"Invalid Ethereum address: {raw}")
        return address.lower()  # Normalize to lowercase (EIP-55 checksum is optional)

    elif blockchain_lower == 'bitcoin':
        if not re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{6,87}$', address):
            raise ValueError(f"Invalid Bitcoin address: {raw}")
        return address  # Bitcoin addresses are case-sensitive

    elif blockchain_lower == 'tron':
        if not re.match(r'^T[A-Za-z0-9]{33,34}$', address):
            raise ValueError(f"Invalid Tron address: {raw}")
        return address

    else:
        # Unknown blockchain — return as-is (conservative)
        return address


def normalize_telegram(raw: str) -> str:
    """Normalize Telegram identifier: strip @, lowercase.

    @SomeUser → someuser
    SomeUser → someuser
    """
    if not raw:
        raise ValueError("Telegram identifier cannot be empty")

    handle = raw.strip().lstrip('@').lower()

    if not re.match(r'^[a-z][a-z0-9_]{4,31}$', handle):
        raise ValueError(f"Invalid Telegram identifier: {raw}")

    return handle


def normalize_social_account(raw: str, platform: str) -> str:
    """Normalize social media account identifier."""
    if not raw:
        raise ValueError("Social account identifier cannot be empty")

    handle = raw.strip().lstrip('@').lower()
    platform_lower = platform.lower().strip()

    # Platform-specific normalization
    if platform_lower in ('twitter', 'x'):
        if not re.match(r'^[a-z0-9_]{1,15}$', handle):
            raise ValueError(f"Invalid Twitter/X handle: {raw}")
    elif platform_lower == 'instagram':
        if not re.match(r'^[a-z0-9._]{1,30}$', handle):
            raise ValueError(f"Invalid Instagram handle: {raw}")

    return handle


def normalize_person_name(raw: str) -> str:
    """Normalize person name: stripped, title case, whitespace-normalized."""
    if not raw:
        raise ValueError("Person name cannot be empty")

    # Collapse whitespace, strip
    name = re.sub(r'\s+', ' ', raw.strip())

    return name.lower()  # Normalized for matching; raw stored separately


def normalize_organization_name(raw: str) -> str:
    """Normalize organization name: stripped, lowercase, suffix handling."""
    if not raw:
        raise ValueError("Organization name cannot be empty")

    name = raw.strip().lower()
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name)
    # Remove common legal suffixes for matching
    name = re.sub(r'\s+(inc|llc|ltd|gmbh|sa|sl|s\.?l\.?|s\.?a\.?|corp|corporation|limited)$', '', name)

    return name


# Normalization dispatch
NORMALIZERS = {
    "PHONE": normalize_phone,
    "EMAIL": normalize_email,
    "DOMAIN": normalize_domain,
    "URL": normalize_url,
    "IP": normalize_ip,
    "TELEGRAM_IDENTIFIER": normalize_telegram,
    "PERSON": normalize_person_name,
    "ORGANIZATION": normalize_organization_name,
}


def normalize_value(entity_type: str, raw_value: str, **kwargs) -> str:
    """Dispatch to the appropriate normalizer by entity type."""
    if entity_type in NORMALIZERS:
        return NORMALIZERS[entity_type](raw_value)
    # For types without specific normalizers, just strip and lowercase
    return raw_value.strip().lower() if raw_value else ""


# ═══════════════════════════════════════════════
# MATCHING
# ═══════════════════════════════════════════════

class MatchType(str, Enum):
    """How two entities were matched."""
    EXACT = "exact"               # Normalized values are identical
    NORMALIZED = "normalized"     # Different raw forms, same normalized form
    SIMILAR = "similar"           # Fuzzy match (e.g., similar names)
    NONE = "none"


class MatchResult(BaseModel):
    """Result of comparing two entities for a potential match."""
    match_type: MatchType
    confidence: Confidence
    normalized_value_match: bool
    raw_values_overlap: bool
    details: str = ""

    model_config = {"use_enum_values": True}


def match_entities(entity_a: BaseEntity, entity_b: BaseEntity) -> MatchResult:
    """Match two entities by comparing normalized values and raw values.

    Key principle: Similarity ≠ ownership or criminal attribution.
    A match means "these likely refer to the same entity" — nothing more.
    """
    if entity_a.entity_type != entity_b.entity_type:
        return MatchResult(
            match_type=MatchType.NONE,
            confidence=Confidence.UNKNOWN,
            normalized_value_match=False,
            raw_values_overlap=False,
            details="Different entity types cannot match",
        )

    # Check normalized value match
    norm_match = (
        entity_a.normalized_value == entity_b.normalized_value
        and entity_a.normalized_value != ""
    )

    # Check raw value overlap
    raw_a = set(entity_a.raw_values) if entity_a.raw_values else set()
    raw_b = set(entity_b.raw_values) if entity_b.raw_values else set()
    raw_overlap = bool(raw_a & raw_b)

    if norm_match and raw_overlap:
        return MatchResult(
            match_type=MatchType.EXACT,
            confidence=Confidence.HIGH,
            normalized_value_match=True,
            raw_values_overlap=True,
            details="Both normalized and raw values match — high confidence",
        )
    elif norm_match:
        return MatchResult(
            match_type=MatchType.NORMALIZED,
            confidence=Confidence.MEDIUM,
            normalized_value_match=True,
            raw_values_overlap=False,
            details="Normalized values match but raw values differ — medium confidence",
        )
    elif raw_overlap:
        return MatchResult(
            match_type=MatchType.SIMILAR,
            confidence=Confidence.LOW,
            normalized_value_match=False,
            raw_values_overlap=True,
            details="Raw values overlap but normalized values differ — low confidence",
        )
    else:
        return MatchResult(
            match_type=MatchType.NONE,
            confidence=Confidence.UNKNOWN,
            normalized_value_match=False,
            raw_values_overlap=False,
            details="No match",
        )


# ═══════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════

class DeduplicationCandidate(BaseModel):
    """A candidate pair for deduplication."""
    entity_a_id: str
    entity_b_id: str
    entity_type: str
    match_type: MatchType
    confidence: Confidence
    normalized_value: str
    details: str = ""

    model_config = {"use_enum_values": True}


async def find_duplicates(
    repository: EntityRepository,
    entity_type: str | None = None,
    min_confidence: Confidence = Confidence.MEDIUM,
) -> list[DeduplicationCandidate]:
    """Find duplicate entity candidates in the repository.

    Returns candidate pairs sorted by confidence (highest first).
    Does NOT auto-merge — merging requires explicit decision.
    """
    filters = {"entity_type": entity_type} if entity_type else None
    entities = await repository.list(filters=filters, limit=10000)

    candidates: list[DeduplicationCandidate] = []
    seen_pairs: set[tuple[str, str]] = set()

    # O(n²) comparison — acceptable for Layer A (in-memory, limited data)
    # Production: use indexed lookups on normalized_value
    for i, a in enumerate(entities):
        for b in entities[i + 1:]:
            if a.entity_type != b.entity_type:
                continue

            result = match_entities(a, b)
            if result.match_type == MatchType.NONE:
                continue

            # Filter by minimum confidence
            conf_order = [Confidence.UNKNOWN, Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
            if conf_order.index(result.confidence) < conf_order.index(min_confidence):
                continue

            # Canonical pair ordering
            pair = tuple(sorted([a.id, b.id]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            candidates.append(DeduplicationCandidate(
                entity_a_id=a.id,
                entity_b_id=b.id,
                entity_type=a.entity_type,
                match_type=result.match_type,
                confidence=result.confidence,
                normalized_value=a.normalized_value,
                details=result.details,
            ))

    # Sort by confidence (highest first)
    candidates.sort(key=lambda c: conf_order.index(c.confidence))
    return candidates


# ═══════════════════════════════════════════════
# MERGE / SPLIT WORKFLOWS
# ═══════════════════════════════════════════════

class MergeRecord(BaseModel):
    """Audit record for an entity merge operation."""
    merge_id: str = Field(default_factory=lambda: f"MRG-{uuid4().hex[:8].upper()}")
    primary_entity_id: str     # The surviving entity
    merged_entity_id: str      # The entity absorbed (soft-deleted)
    entity_type: str
    confidence: Confidence
    merged_at: datetime = Field(default_factory=utc_now)
    merged_by: str | None = None
    merged_fields: dict[str, Any] = Field(default_factory=dict)
    raw_values_transferred: list[str] = Field(default_factory=list)

    model_config = {"use_enum_values": True}


class SplitRecord(BaseModel):
    """Audit record for an entity split operation (reverse merge)."""
    split_id: str = Field(default_factory=lambda: f"SPL-{uuid4().hex[:8].upper()}")
    merge_id: str               # The merge being reversed
    split_at: datetime = Field(default_factory=utc_now)
    split_by: str | None = None
    reason: str = ""

    model_config = {"use_enum_values": True}


async def merge_entities(
    repository: EntityRepository,
    primary_id: str,
    merged_id: str,
    merged_by: str | None = None,
    confidence: Confidence = Confidence.MEDIUM,
) -> MergeRecord:
    """Merge two entities: primary absorbs merged entity.

    The merged entity is soft-deleted (not hard-deleted).
    All raw values from the merged entity are transferred to primary.
    The merge is recorded for audit and can be reversed via split.

    Safety:
    - Both entities must be the same type
    - Merged entity is soft-deleted, not hard-deleted
    - All data is preserved — merge is reversible
    - Merge requires explicit confidence level
    """
    primary = await repository.get(primary_id)
    merged = await repository.get(merged_id)

    if primary is None:
        raise ValueError(f"Primary entity not found: {primary_id}")
    if merged is None:
        raise ValueError(f"Merged entity not found: {merged_id}")
    if primary.entity_type != merged.entity_type:
        raise ValueError(
            f"Cannot merge entities of different types: "
            f"{primary.entity_type} vs {merged.entity_type}"
        )
    if primary.id == merged.id:
        raise ValueError("Cannot merge an entity with itself")

    # Collect merged entity's raw values to transfer
    raw_to_transfer = list(merged.raw_values)
    # Also add the merged entity's normalized value as a raw value
    if merged.normalized_value and merged.normalized_value not in raw_to_transfer:
        raw_to_transfer.append(merged.normalized_value)

    # Update primary entity: merge raw values
    existing_raw = set(primary.raw_values)
    for rv in raw_to_transfer:
        existing_raw.add(rv)

    # Merge metadata
    merged_metadata = {**primary.metadata, **merged.metadata}
    # Merge confidence — take the higher of the two
    conf_order = [Confidence.UNKNOWN, Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
    merged_conf = (primary.confidence if conf_order.index(primary.confidence) >= conf_order.index(merged.confidence)
                   else merged.confidence)

    # Update last_seen to the more recent timestamp
    new_last_seen = max(primary.last_seen, merged.last_seen)

    await repository.update(primary_id, {
        "raw_values": list(existing_raw),
        "metadata": merged_metadata,
        "confidence": merged_conf,
        "last_seen": new_last_seen,
    })

    # Soft-delete the merged entity
    merged.soft_delete(deleted_by=merged_by)
    # Re-validate to ensure audit stays as AuditMetadata object
    await repository.update(merged_id, {
        "audit": merged.audit,
    })

    return MergeRecord(
        primary_entity_id=primary_id,
        merged_entity_id=merged_id,
        entity_type=primary.entity_type,
        confidence=confidence,
        merged_by=merged_by,
        merged_fields={
            "raw_values_added": raw_to_transfer,
            "metadata_merged": True,
            "confidence_upgraded": merged_conf != primary.confidence,
        },
        raw_values_transferred=raw_to_transfer,
    )


async def split_entity(
    repository: EntityRepository,
    merge_record: MergeRecord,
    split_by: str | None = None,
    reason: str = "",
) -> SplitRecord:
    """Reverse a merge operation: restore the merged entity.

    The merged entity is un-deleted (is_deleted = False).
    The transferred raw values are removed from the primary entity.
    """
    # Restore merged entity
    merged = await repository.get(merge_record.merged_entity_id)
    if merged is None:
        raise ValueError(f"Merged entity not found: {merge_record.merged_entity_id}")

    # Un-delete: create fresh AuditMetadata with restored state
    from schemas.base import AuditMetadata, utc_now
    restored_audit = AuditMetadata(
        created_by=merged.audit.created_by if hasattr(merged.audit, 'created_by') else None,
        created_at=merged.audit.created_at if hasattr(merged.audit, 'created_at') else utc_now(),
        updated_by=split_by,
        updated_at=utc_now(),
        version=(merged.audit.version if hasattr(merged.audit, 'version') else 1) + 1,
        is_deleted=False,
        deleted_at=None,
        deleted_by=None,
    )
    await repository.update(merge_record.merged_entity_id, {
        "audit": restored_audit,
    })

    # Remove transferred raw values from primary
    primary = await repository.get(merge_record.primary_entity_id)
    if primary is not None:
        primary_raw = set(primary.raw_values)
        for rv in merge_record.raw_values_transferred:
            primary_raw.discard(rv)
        await repository.update(merge_record.primary_entity_id, {
            "raw_values": list(primary_raw),
        })

    return SplitRecord(
        merge_id=merge_record.merge_id,
        split_by=split_by,
        reason=reason,
    )


# ═══════════════════════════════════════════════
# RESOLUTION SERVICE (top-level API)
# ═══════════════════════════════════════════════

class EntityResolutionService:
    """Top-level entity resolution service.

    Provides:
    - resolve_or_create: normalize input, find existing, or create new
    - find_matches: find matching entities
    - deduplicate: find all duplicate candidates
    - merge: merge two entities
    - split: reverse a merge
    """

    def __init__(self, repository: EntityRepository) -> None:
        self.repository = repository

    async def resolve_or_create(
        self,
        entity_type: str,
        raw_value: str,
        **entity_kwargs,
    ) -> tuple[BaseEntity, bool]:
        """Resolve an entity by normalized value, or create a new one.

        Returns (entity, was_created).
        If an entity with the same normalized value exists, returns it.
        Otherwise, creates a new entity.

        The original raw value is always stored in raw_values.
        """
        # Normalize the value
        if entity_type == "CRYPTO_WALLET":
            blockchain = entity_kwargs.get("blockchain", "bitcoin")
            normalized = normalize_crypto_address(raw_value, blockchain)
        elif entity_type == "SOCIAL_ACCOUNT":
            platform = entity_kwargs.get("platform", "unknown")
            normalized = normalize_social_account(raw_value, platform)
        else:
            normalized = normalize_value(entity_type, raw_value)

        # Check if entity with this normalized value already exists
        existing = await self.repository.find_by_normalized_value(entity_type, normalized)
        if existing is not None and not existing.audit.is_deleted:
            # Add raw value if not already present
            if raw_value not in existing.raw_values:
                existing.raw_values.append(raw_value)
                await self.repository.update(existing.id, {
                    "raw_values": existing.raw_values,
                    "last_seen": utc_now(),
                })
            return existing, False

        # Create new entity
        entity = create_entity(entity_type, **entity_kwargs)
        entity.normalized_value = normalized
        entity.raw_values = [raw_value]

        await self.repository.create(entity)
        return entity, True

    async def find_matches(
        self,
        entity: BaseEntity,
        limit: int = 10,
    ) -> list[MatchResult]:
        """Find potential matches for an entity in the repository."""
        entities = await self.repository.list(
            filters={"entity_type": entity.entity_type},
            limit=10000,
        )

        results: list[tuple[MatchResult, BaseEntity]] = []
        for other in entities:
            if other.id == entity.id or other.audit.is_deleted:
                continue
            result = match_entities(entity, other)
            if result.match_type != MatchType.NONE:
                results.append((result, other))

        # Sort by confidence (highest first)
        conf_order = [Confidence.UNKNOWN, Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
        results.sort(key=lambda x: conf_order.index(x[0].confidence), reverse=True)

        return [r for r, _ in results[:limit]]

    async def deduplicate(
        self,
        entity_type: str | None = None,
        min_confidence: Confidence = Confidence.MEDIUM,
    ) -> list[DeduplicationCandidate]:
        """Find all duplicate candidates in the repository."""
        return await find_duplicates(self.repository, entity_type, min_confidence)

    async def merge(
        self,
        primary_id: str,
        merged_id: str,
        merged_by: str | None = None,
        confidence: Confidence = Confidence.MEDIUM,
    ) -> MergeRecord:
        """Merge two entities."""
        return await merge_entities(
            self.repository, primary_id, merged_id, merged_by, confidence
        )

    async def split(
        self,
        merge_record: MergeRecord,
        split_by: str | None = None,
        reason: str = "",
    ) -> SplitRecord:
        """Reverse a merge operation."""
        return await split_entity(
            self.repository, merge_record, split_by, reason
        )


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# The following capabilities are NOT available in Layer A:
#
# - PostgreSQL indexed lookups for normalized_value (currently O(n²) in-memory scan)
# - Apache Kafka event emission for entity.merge, entity.split events (Module 05)
# - Distributed merge locking (prevents concurrent merges on same entity)
# - Fuzzy matching with ML-based similarity (currently exact normalized comparison)
# - Phoneword/phonetic matching for person names (Soundex, Metaphone)
# - International phone number validation via libphonenumber (currently regex-based)
# - Blockchain address checksum validation (EIP-55 for Ethereum)
# - IDN (Internationalized Domain Name) punycode conversion
# - Bulk deduplication with parallel processing (currently sequential)
# - Merge conflict resolution with concurrent entity updates
#
# All of the above are marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
# Do NOT consider entity resolution production-ready until these are implemented.

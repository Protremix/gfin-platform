"""Comprehensive tests for Module 04 — Entity Resolution.

Per Master Spec §8 and Module 04 acceptance criteria:
- Normalization of all entity types
- Matching (exact, normalized, similar, none)
- Deduplication with confidence scoring
- Merge/split workflows (reversible, auditable)
- Known equivalent representations resolve correctly
- No unsafe false merges
- Similarity ≠ ownership or criminal attribution
- Original raw representation always retained
"""

import pytest
import asyncio
from datetime import datetime, timezone

from schemas.base import BaseEntity, Confidence
from schemas.enums import EntityType
from schemas.entities import create_entity
from common.database import InMemoryEntityRepository
from services.entity_resolution import (
    # Normalization
    normalize_phone,
    normalize_email,
    normalize_domain,
    normalize_url,
    normalize_ip,
    normalize_crypto_address,
    normalize_telegram,
    normalize_social_account,
    normalize_person_name,
    normalize_organization_name,
    normalize_value,
    # Matching
    MatchType,
    MatchResult,
    match_entities,
    # Deduplication
    DeduplicationCandidate,
    find_duplicates,
    # Merge/Split
    MergeRecord,
    SplitRecord,
    merge_entities,
    split_entity,
    # Service
    EntityResolutionService,
)


# ═══════════════════════════════════════════════
# PHONE NORMALIZATION
# ═══════════════════════════════════════════════

class TestPhoneNormalization:
    """Test phone number normalization — the canonical example from the spec."""

    def test_plus_format(self):
        assert normalize_phone("+34 612 345 678") == "+34612345678"

    def test_double_zero_format(self):
        assert normalize_phone("0034 612 345 678") == "+34612345678"

    def test_compact_format(self):
        assert normalize_phone("+34612345678") == "+34612345678"

    def test_with_dashes(self):
        assert normalize_phone("+34-612-345-678") == "+34612345678"

    def test_with_parens(self):
        assert normalize_phone("+34 (612) 345 678") == "+34612345678"

    def test_with_dots(self):
        assert normalize_phone("+34.612.345.678") == "+34612345678"

    def test_all_variants_resolve_same(self):
        """All spec variants must resolve to the same normalized form."""
        variants = [
            "+34 612 345 678",
            "0034 612 345 678",
            "+34612345678",
            "+34-612-345-678",
            "+34 (612) 345 678",
        ]
        results = [normalize_phone(v) for v in variants]
        # First two (with country code) should resolve to same
        assert results[0] == results[1] == results[2] == results[3] == results[4]

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_phone("")

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid phone"):
            normalize_phone("not a phone")

    def test_short_number_kept(self):
        """Numbers without country code are kept as-is (no false normalization)."""
        result = normalize_phone("612345678")
        assert result == "612345678"


# ═══════════════════════════════════════════════
# EMAIL NORMALIZATION
# ═══════════════════════════════════════════════

class TestEmailNormalization:
    """Test email normalization."""

    def test_uppercase_lowered(self):
        assert normalize_email("User@Example.COM") == "user@example.com"

    def test_whitespace_stripped(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_mixed_case(self):
        assert normalize_email("John.Doe@Gmail.Com") == "john.doe@gmail.com"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_email("")

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid email"):
            normalize_email("not_an_email")

    def test_no_domain_rejected(self):
        with pytest.raises(ValueError, match="Invalid email"):
            normalize_email("user@")


# ═══════════════════════════════════════════════
# DOMAIN NORMALIZATION
# ═══════════════════════════════════════════════

class TestDomainNormalization:
    """Test domain normalization."""

    def test_uppercase_lowered(self):
        assert normalize_domain("Example.COM") == "example.com"

    def test_trailing_dot_removed(self):
        assert normalize_domain("example.com.") == "example.com"

    def test_protocol_removed(self):
        assert normalize_domain("https://example.com") == "example.com"
        assert normalize_domain("http://example.com/path") == "example.com"

    def test_path_removed(self):
        assert normalize_domain("example.com/some/path") == "example.com"

    def test_subdomain(self):
        assert normalize_domain("mail.Example.COM") == "mail.example.com"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_domain("")

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid domain"):
            normalize_domain("not_a_domain!!")


# ═══════════════════════════════════════════════
# URL NORMALIZATION
# ═══════════════════════════════════════════════

class TestURLNormalization:
    """Test URL normalization."""

    def test_adds_https(self):
        assert normalize_url("example.com") == "https://example.com"

    def test_http_preserved(self):
        assert normalize_url("http://example.com") == "http://example.com"

    def test_https_preserved(self):
        assert normalize_url("https://example.com") == "https://example.com"

    def test_uppercase_lowered(self):
        assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"

    def test_trailing_slash_removed_on_root(self):
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_path_kept(self):
        assert normalize_url("https://example.com/page") == "https://example.com/page"

    def test_default_port_443_removed(self):
        assert normalize_url("https://example.com:443") == "https://example.com"

    def test_default_port_80_removed(self):
        assert normalize_url("http://example.com:80") == "http://example.com"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_url("")

    def test_invalid_rejected(self):
        """URLs without a valid domain should be rejected."""
        with pytest.raises(ValueError, match="Invalid URL"):
            normalize_url("not_a_url")


# ═══════════════════════════════════════════════
# IP NORMALIZATION
# ═══════════════════════════════════════════════

class TestIPNormalization:
    """Test IP address normalization."""

    def test_ipv4_canonical(self):
        assert normalize_ip("192.168.1.1") == "192.168.1.1"

    def test_ipv4_no_leading_zeros(self):
        assert normalize_ip("10.0.0.1") == "10.0.0.1"

    def test_ipv6_compressed(self):
        assert normalize_ip("2001:0db8::0001") == "2001:db8::1"

    def test_ipv6_loopback(self):
        assert normalize_ip("::1") == "::1"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_ip("")

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid IP"):
            normalize_ip("999.999.999.999")


# ═══════════════════════════════════════════════
# CRYPTO ADDRESS NORMALIZATION
# ═══════════════════════════════════════════════

class TestCryptoNormalization:
    """Test crypto wallet address normalization."""

    def test_ethereum_lowercase(self):
        addr = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        result = normalize_crypto_address(addr, "ethereum")
        assert result == addr.lower()

    def test_ethereum_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid Ethereum"):
            normalize_crypto_address("0x123", "ethereum")

    def test_bitcoin_case_sensitive(self):
        addr = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        result = normalize_crypto_address(addr, "bitcoin")
        assert result == addr  # Not lowercased

    def test_tron_normalized(self):
        addr = "TJRAB4W2Z7Y9X1V2Q3N4M5P6R7S8T9U0ABC"
        result = normalize_crypto_address(addr, "tron")
        assert result == addr

    def test_unknown_blockchain_kept(self):
        addr = "SomeAddress123"
        result = normalize_crypto_address(addr, "solana")
        assert result == addr

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_crypto_address("", "ethereum")


# ═══════════════════════════════════════════════
# TELEGRAM NORMALIZATION
# ═══════════════════════════════════════════════

class TestTelegramNormalization:
    """Test Telegram identifier normalization."""

    def test_at_prefix_removed(self):
        assert normalize_telegram("@someuser") == "someuser"

    def test_no_at_prefix(self):
        assert normalize_telegram("someuser") == "someuser"

    def test_uppercase_lowered(self):
        assert normalize_telegram("@SomeUser") == "someuser"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_telegram("")

    def test_invalid_rejected(self):
        with pytest.raises(ValueError, match="Invalid Telegram"):
            normalize_telegram("ab")  # Too short (min 5 chars)

    def test_numbers_start_rejected(self):
        with pytest.raises(ValueError, match="Invalid Telegram"):
            normalize_telegram("123user")  # Must start with letter


# ═══════════════════════════════════════════════
# SOCIAL ACCOUNT NORMALIZATION
# ═══════════════════════════════════════════════

class TestSocialAccountNormalization:
    """Test social account normalization."""

    def test_twitter_at_removed(self):
        assert normalize_social_account("@user123", "twitter") == "user123"

    def test_instagram_lowered(self):
        assert normalize_social_account("@MyAccount", "instagram") == "myaccount"

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_social_account("", "twitter")

    def test_twitter_invalid_length(self):
        with pytest.raises(ValueError, match="Invalid Twitter"):
            normalize_social_account("this_handle_is_way_too_long_for_twitter", "twitter")


# ═══════════════════════════════════════════════
# PERSON & ORGANIZATION NORMALIZATION
# ═══════════════════════════════════════════════

class TestPersonOrgNormalization:
    """Test person and organization name normalization."""

    def test_person_whitespace_normalized(self):
        assert normalize_person_name("  John   Doe  ") == "john doe"

    def test_person_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_person_name("")

    def test_org_suffix_removed(self):
        assert normalize_organization_name("Acme Inc") == "acme"
        assert normalize_organization_name("Tech Corp Ltd") == "tech corp"

    def test_org_uppercase_lowered(self):
        assert normalize_organization_name("GLOBAL INC") == "global"

    def test_org_whitespace_normalized(self):
        assert normalize_organization_name("  Some   Company  ") == "some company"

    def test_org_empty_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_organization_name("")


# ═══════════════════════════════════════════════
# MATCHING
# ═══════════════════════════════════════════════

class TestMatching:
    """Test entity matching — exact, normalized, similar, none."""

    def test_exact_match(self):
        """Both normalized and raw values match → EXACT, HIGH confidence."""
        a = create_entity("PHONE", e164="+34612345678")
        b = create_entity("PHONE", e164="+34612345678")
        a.raw_values = ["+34612345678"]
        b.raw_values = ["+34612345678"]
        result = match_entities(a, b)
        assert result.match_type == MatchType.EXACT
        assert result.confidence == Confidence.HIGH

    def test_normalized_match(self):
        """Same normalized value, different raw → NORMALIZED, MEDIUM."""
        a = create_entity("PHONE", e164="+34612345678")
        b = create_entity("PHONE", e164="+34612345678")
        a.raw_values = ["+34 612 345 678"]
        b.raw_values = ["0034 612 345 678"]
        result = match_entities(a, b)
        assert result.match_type == MatchType.NORMALIZED
        assert result.confidence == Confidence.MEDIUM

    def test_different_types_no_match(self):
        a = create_entity("PHONE", e164="+34612345678")
        b = create_entity("EMAIL", email="test@example.com")
        result = match_entities(a, b)
        assert result.match_type == MatchType.NONE

    def test_no_match_different_values(self):
        a = create_entity("PHONE", e164="+34612345678")
        b = create_entity("PHONE", e164="+447123456789")
        result = match_entities(a, b)
        assert result.match_type == MatchType.NONE

    def test_similarity_not_attribution(self):
        """A match means 'likely same entity' — NOT ownership or criminal attribution."""
        a = create_entity("PHONE", e164="+34612345678")
        b = create_entity("PHONE", e164="+34612345678")
        a.raw_values = ["+34 612 345 678"]
        b.raw_values = ["+34 612 345 678"]
        result = match_entities(a, b)
        # Match found, but this does NOT mean the owner is a criminal
        assert result.match_type in (MatchType.EXACT, MatchType.NORMALIZED)
        # The match result contains NO criminal attribution fields
        assert not hasattr(result, "is_criminal")
        assert not hasattr(result, "ownership")

    async def test_empty_normalized_no_match(self):
        a = create_entity("PERSON", full_name="Test")
        b = create_entity("PERSON", full_name="Other")
        a.normalized_value = ""
        b.normalized_value = ""
        result = match_entities(a, b)
        assert result.match_type == MatchType.NONE


# ═══════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════

class TestDeduplication:
    """Test deduplication candidate finding."""

    @pytest.fixture
    async def repo_with_duplicates(self):
        repo = InMemoryEntityRepository()

        # Three phone entities — two are the same number in different formats
        p1 = create_entity("PHONE", e164="+34612345678")
        p1.raw_values = ["+34 612 345 678"]
        await repo.create(p1)

        p2 = create_entity("PHONE", e164="+34612345678")
        p2.raw_values = ["0034 612 345 678"]
        await repo.create(p2)

        # Different phone
        p3 = create_entity("PHONE", e164="+447123456789")
        p3.raw_values = ["+44 7123 456789"]
        await repo.create(p3)

        # Two emails — same address
        e1 = create_entity("EMAIL", email="user@example.com")
        await repo.create(e1)

        e2 = create_entity("EMAIL", email="user@example.com")
        await repo.create(e2)

        return repo

    async def test_find_duplicates(self, repo_with_duplicates):
        """Should find duplicate candidates."""
        candidates = await find_duplicates(repo_with_duplicates)
        assert len(candidates) >= 2  # Phone pair + email pair

    async def test_find_duplicates_by_type(self, repo_with_duplicates):
        """Filter by entity type."""
        candidates = await find_duplicates(repo_with_duplicates, entity_type="PHONE")
        assert len(candidates) == 1  # Only phone pair
        assert candidates[0].entity_type == "PHONE"

    async def test_find_duplicates_min_confidence(self, repo_with_duplicates):
        """High confidence filter — only exact matches."""
        candidates = await find_duplicates(repo_with_duplicates, min_confidence=Confidence.HIGH)
        # Phone pair has different raw values (NORMALIZED match), email pair is EXACT
        # Email entities share both normalized AND raw value → EXACT/HIGH
        assert all(c.confidence == Confidence.HIGH for c in candidates)

    async def test_no_false_merges(self, repo_with_duplicates):
        """Deduplication should only return candidates — never auto-merge."""
        candidates = await find_duplicates(repo_with_duplicates)
        # All results are candidates — no entities were modified
        for c in candidates:
            assert hasattr(c, "entity_a_id")
            assert hasattr(c, "entity_b_id")
            # No auto-merge happened
            assert not hasattr(c, "merged")


# ═══════════════════════════════════════════════
# MERGE / SPLIT WORKFLOWS
# ═══════════════════════════════════════════════

class TestMergeSplit:
    """Test entity merge and split (reverse) workflows."""

    @pytest.fixture
    async def repo_with_pair(self):
        repo = InMemoryEntityRepository()

        p1 = create_entity("PHONE", e164="+34612345678")
        p1.raw_values = ["+34 612 345 678"]
        await repo.create(p1)

        p2 = create_entity("PHONE", e164="+34612345678")
        p2.raw_values = ["0034 612 345 678"]
        await repo.create(p2)

        return repo, p1, p2

    async def test_merge_transfers_raw_values(self, repo_with_pair):
        """Merging should transfer raw values from merged to primary."""
        repo, p1, p2 = repo_with_pair

        merge_record = await merge_entities(repo, p1.id, p2.id, merged_by="USR-1")
        assert merge_record.primary_entity_id == p1.id
        assert merge_record.merged_entity_id == p2.id
        assert "0034 612 345 678" in merge_record.raw_values_transferred

    async def test_merge_soft_deletes_merged(self, repo_with_pair):
        """Merged entity should be soft-deleted, not hard-deleted."""
        repo, p1, p2 = repo_with_pair

        await merge_entities(repo, p1.id, p2.id)

        merged = await repo.get(p2.id)
        assert merged is not None  # Still exists (soft-deleted)
        assert merged.audit.is_deleted is True
        assert merged.audit.deleted_at is not None

    async def test_merge_different_types_rejected(self, repo_with_pair):
        """Cannot merge entities of different types."""
        repo, p1, _ = repo_with_pair
        e1 = create_entity("EMAIL", email="test@example.com")
        await repo.create(e1)

        with pytest.raises(ValueError, match="different types"):
            await merge_entities(repo, p1.id, e1.id)

    async def test_merge_self_rejected(self, repo_with_pair):
        """Cannot merge an entity with itself."""
        repo, p1, _ = repo_with_pair

        with pytest.raises(ValueError, match="itself"):
            await merge_entities(repo, p1.id, p1.id)

    async def test_merge_nonexistent_rejected(self, repo_with_pair):
        repo, _, _ = repo_with_pair
        with pytest.raises(ValueError, match="not found"):
            await merge_entities(repo, "ENT-NONEXIST", "ENT-ALSONONEXIST")

    async def test_merge_primary_has_all_raw_values(self, repo_with_pair):
        """After merge, primary should have all raw values from both entities."""
        repo, p1, p2 = repo_with_pair

        await merge_entities(repo, p1.id, p2.id)

        primary = await repo.get(p1.id)
        assert "+34 612 345 678" in primary.raw_values
        assert "0034 612 345 678" in primary.raw_values

    async def test_merge_record_has_audit_info(self, repo_with_pair):
        """Merge record should have audit metadata."""
        repo, p1, p2 = repo_with_pair

        merge_record = await merge_entities(repo, p1.id, p2.id, merged_by="USR-1", confidence=Confidence.HIGH)
        assert merge_record.merge_id.startswith("MRG-")
        assert merge_record.merged_by == "USR-1"
        assert merge_record.confidence == Confidence.HIGH
        assert merge_record.merged_at is not None

    async def test_split_reverses_merge(self, repo_with_pair):
        """Split should reverse a merge — restore the merged entity."""
        repo, p1, p2 = repo_with_pair

        merge_record = await merge_entities(repo, p1.id, p2.id)

        # Verify merge happened
        merged = await repo.get(p2.id)
        assert merged.audit.is_deleted is True

        # Split
        split_record = await split_entity(repo, merge_record, split_by="USR-2", reason="False merge")
        assert split_record.split_id.startswith("SPL-")
        assert split_record.merge_id == merge_record.merge_id
        assert split_record.split_by == "USR-2"
        assert split_record.reason == "False merge"

        # Verify merged entity is restored
        restored = await repo.get(p2.id)
        assert restored.audit.is_deleted is False
        assert restored.audit.deleted_at is None

    async def test_split_removes_transferred_raw_values(self, repo_with_pair):
        """After split, transferred raw values should be removed from primary."""
        repo, p1, p2 = repo_with_pair

        merge_record = await merge_entities(repo, p1.id, p2.id)

        await split_entity(repo, merge_record)

        primary = await repo.get(p1.id)
        # Original raw value of p1 should still be there
        assert "+34 612 345 678" in primary.raw_values
        # But p2's raw value should be removed
        assert "0034 612 345 678" not in primary.raw_values


# ═══════════════════════════════════════════════
# RESOLUTION SERVICE (END-TO-END)
# ═══════════════════════════════════════════════

class TestResolutionService:
    """Test the top-level EntityResolutionService."""

    @pytest.fixture
    def service(self):
        repo = InMemoryEntityRepository()
        return EntityResolutionService(repo)

    async def test_resolve_or_create_new_entity(self, service):
        """First call creates a new entity."""
        entity, was_created = await service.resolve_or_create("PHONE", "+34 612 345 678", e164="+34612345678")
        assert was_created is True
        assert entity.normalized_value == "+34612345678"
        assert "+34 612 345 678" in entity.raw_values

    async def test_resolve_or_create_existing(self, service):
        """Second call with different raw form finds existing entity."""
        # First create
        entity1, created1 = await service.resolve_or_create("PHONE", "+34 612 345 678", e164="+34612345678")
        assert created1 is True

        # Now resolve with different raw format
        entity2, created2 = await service.resolve_or_create("PHONE", "0034 612 345 678", e164="+34612345678")
        assert created2 is False
        assert entity2.id == entity1.id  # Same entity
        # Both raw values should be stored
        assert "+34 612 345 678" in entity2.raw_values
        assert "0034 612 345 678" in entity2.raw_values

    async def test_resolve_email(self, service):
        entity, created = await service.resolve_or_create("EMAIL", "User@Example.COM", email="user@example.com")
        assert created is True
        assert entity.normalized_value == "user@example.com"

    async def test_resolve_domain(self, service):
        entity, created = await service.resolve_or_create("DOMAIN", "Example.COM", domain="example.com")
        assert created is True
        assert entity.normalized_value == "example.com"

    async def test_resolve_url(self, service):
        entity, created = await service.resolve_or_create("URL", "https://example.com/path", url="https://example.com/path")
        assert created is True

    async def test_resolve_ip(self, service):
        entity, created = await service.resolve_or_create("IP", "192.168.1.1", ip="192.168.1.1")
        assert created is True
        assert entity.normalized_value == "192.168.1.1"

    async def test_resolve_telegram(self, service):
        entity, created = await service.resolve_or_create("TELEGRAM_IDENTIFIER", "@someuser", username="someuser")
        assert created is True
        assert entity.normalized_value == "someuser"

    async def test_find_matches(self, service):
        """Find matching entities in the repository."""
        # Create two entities with same normalized value
        await service.resolve_or_create("PHONE", "+34 612 345 678", e164="+34612345678")
        await service.resolve_or_create("PHONE", "0034 612 345 678", e164="+34612345678")
        # Third different entity
        await service.resolve_or_create("PHONE", "+447123456789", e164="+447123456789")

        # All three resolve to the same entity (dedup on create)
        # So find_matches should return empty (they already merged)
        entities = await service.repository.list(limit=10)
        # Two unique entities: +34612345678 and +447123456789
        assert len(entities) == 2

    async def test_deduplicate_via_service(self, service):
        """Service.deduplicate() finds candidates."""
        # Create two separate entities with same normalized value
        p1 = create_entity("PHONE", e164="+34612345678")
        p1.raw_values = ["+34 612 345 678"]
        await service.repository.create(p1)

        p2 = create_entity("PHONE", e164="+34612345678")
        p2.raw_values = ["0034 612 345 678"]
        await service.repository.create(p2)

        candidates = await service.deduplicate(entity_type="PHONE")
        assert len(candidates) == 1
        assert candidates[0].confidence in (Confidence.MEDIUM, Confidence.HIGH)

    async def test_merge_via_service(self, service):
        """Service.merge() merges and service.split() reverses."""
        p1 = create_entity("PHONE", e164="+34612345678")
        p1.raw_values = ["+34 612 345 678"]
        await service.repository.create(p1)

        p2 = create_entity("PHONE", e164="+34612345678")
        p2.raw_values = ["0034 612 345 678"]
        await service.repository.create(p2)

        # Merge
        merge_record = await service.merge(p1.id, p2.id, merged_by="USR-1", confidence=Confidence.HIGH)
        assert merge_record.primary_entity_id == p1.id

        # Verify
        primary = await service.repository.get(p1.id)
        assert "+34 612 345 678" in primary.raw_values
        assert "0034 612 345 678" in primary.raw_values

        # Split
        split_record = await service.split(merge_record, split_by="USR-1", reason="Testing split")
        assert split_record.merge_id == merge_record.merge_id

        # Verify restored
        restored = await service.repository.get(p2.id)
        assert restored.audit.is_deleted is False


# ═══════════════════════════════════════════════
# NEGATIVE TESTS (FAIL-SAFE)
# ═══════════════════════════════════════════════

class TestNegativeFailSafe:
    """Test that entity resolution fails safely — no unsafe false merges."""

    async def test_different_phones_not_merged(self, service=None):
        """Two different phone numbers must NOT be considered duplicates."""
        repo = InMemoryEntityRepository()
        if service is None:
            service = EntityResolutionService(repo)

        p1 = create_entity("PHONE", e164="+34612345678")
        p2 = create_entity("PHONE", e164="+34612345679")  # Different number!
        await repo.create(p1)
        await repo.create(p2)

        result = match_entities(p1, p2)
        assert result.match_type == MatchType.NONE

    async def test_different_emails_not_merged(self):
        """Different email addresses must NOT be considered duplicates."""
        e1 = create_entity("EMAIL", email="user1@example.com")
        e2 = create_entity("EMAIL", email="user2@example.com")
        result = match_entities(e1, e2)
        assert result.match_type == MatchType.NONE

    async def test_similar_domains_not_auto_merged(self):
        """Similar domains (example.com vs example.org) must NOT be merged."""
        d1 = create_entity("DOMAIN", domain="example.com")
        d2 = create_entity("DOMAIN", domain="example.org")
        result = match_entities(d1, d2)
        assert result.match_type == MatchType.NONE

    async def test_different_persons_not_merged(self):
        """Different person names must NOT be merged even if similar."""
        p1 = create_entity("PERSON", full_name="John Smith")
        p2 = create_entity("PERSON", full_name="John Smyth")
        result = match_entities(p1, p2)
        # Different normalized values → no match
        assert result.match_type == MatchType.NONE

    async def test_merge_not_found_fails(self):
        """Merging non-existent entities should fail explicitly."""
        repo = InMemoryEntityRepository()
        with pytest.raises(ValueError, match="not found"):
            await merge_entities(repo, "ENT-FAKE1", "ENT-FAKE2")

    async def test_invalid_phone_normalization_fails(self):
        """Invalid phone numbers must be rejected, not silently normalized."""
        with pytest.raises(ValueError):
            normalize_phone("abc123xyz")

    async def test_empty_values_rejected(self):
        """Empty values must be rejected for all types."""
        with pytest.raises(ValueError):
            normalize_phone("")
        with pytest.raises(ValueError):
            normalize_email("")
        with pytest.raises(ValueError):
            normalize_domain("")
        with pytest.raises(ValueError):
            normalize_url("")
        with pytest.raises(ValueError):
            normalize_ip("")

    async def test_merged_entity_preserved_not_deleted(self):
        """Soft-deleted merged entity must still be retrievable (for audit/split)."""
        repo = InMemoryEntityRepository()
        p1 = create_entity("PHONE", e164="+34612345678")
        p2 = create_entity("PHONE", e164="+34612345678")
        await repo.create(p1)
        await repo.create(p2)

        await merge_entities(repo, p1.id, p2.id)

        # Merged entity must still be retrievable
        merged = await repo.get(p2.id)
        assert merged is not None
        assert merged.audit.is_deleted is True

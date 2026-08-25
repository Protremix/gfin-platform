"""Comprehensive tests for Module 08 — Web Discovery Engine.

Per Master Spec §12 (Web Discovery Engine):
Functions: receive seed, schedule crawl, fetch permitted content, extract text,
extract links, extract entities, extract metadata, create observations,
preserve provenance, discover additional seeds, submit new jobs.
Requirements: queue-based processing, concurrency controls, rate limits,
retries, dead-letter queues, deduplication, content hashing, crawl policies,
robots/terms compliance, no bypass of auth/access controls.
"""

import asyncio

import pytest

from schemas.base import utc_now
from services.web_discovery import (
    ContentExtractor,
    CrawlPolicy,
    CrawlPolicyChecker,
    CrawlPriority,
    CrawlStatus,
    FetchResult,
    MockFetcher,
    RateLimiter,
    WebDiscoveryEngine,
)

# ─── Fixtures ───


@pytest.fixture
def fetcher():
    f = MockFetcher()
    f.register_page(
        "https://evil.com",
        '<html><head><title>Phishing Site</title><meta name="description" content="Scam page"></head>'
        '<body><a href="/login">Login</a><a href="https://good.com">Good</a>'
        "<p>Contact: scam@evil.com</p><p>Call: +34612345678</p></body></html>",
    )
    f.register_page(
        "https://evil.com/login",
        "<html><head><title>Login</title></head><body>Login form</body></html>",
    )
    f.register_page(
        "https://good.com",
        "<html><head><title>Good Site</title></head><body>Legitimate</body></html>",
    )
    return f


@pytest.fixture
def engine(fetcher):
    e = WebDiscoveryEngine(fetcher=fetcher, max_workers=1)
    e._policy_checker.register_policy(CrawlPolicy(policy_id="default", request_delay_ms=0))
    return e


# ═══════════════════════════════════════════════
# SEED SUBMISSION AND JOB QUEUE
# ═══════════════════════════════════════════════


class TestSeedSubmission:
    def test_submit_seed(self, engine):
        job = engine.submit_seed("https://evil.com")
        assert job.job_id.startswith("CRL-")
        assert job.seed_url == "https://evil.com"
        assert job.status == CrawlStatus.QUEUED
        assert job.depth == 0

    def test_submit_seed_with_priority(self, engine):
        job = engine.submit_seed("https://evil.com", priority=CrawlPriority.URGENT)
        assert int(job.priority) == int(CrawlPriority.URGENT)

    def test_submit_duplicate_seed_skipped(self, engine):
        engine.submit_seed("https://evil.com")
        engine._processed_urls.add(engine.normalize_url("https://evil.com"))
        job2 = engine.submit_seed("https://evil.com")
        assert job2.status == CrawlStatus.SKIPPED

    def test_get_job(self, engine):
        job = engine.submit_seed("https://evil.com")
        retrieved = engine.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_job_nonexistent(self, engine):
        assert engine.get_job("NONEXIST") is None


# ═══════════════════════════════════════════════
# CRAWL POLICY ENFORCEMENT
# ═══════════════════════════════════════════════


class TestCrawlPolicy:
    def test_scheme_allowed(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allowed_schemes=["https"]))
        result = checker.check("https://example.com", depth=0)
        assert result.allowed

    def test_scheme_blocked(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allowed_schemes=["https"]))
        result = checker.check("http://example.com", depth=0)
        assert not result.allowed
        assert "Scheme" in result.reason

    def test_domain_allowed_list(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allowed_domains=["example.com"]))
        result = checker.check("https://example.com", depth=0)
        assert result.allowed

    def test_domain_not_in_allowed(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allowed_domains=["example.com"]))
        result = checker.check("https://evil.com", depth=0)
        assert not result.allowed

    def test_domain_blocked(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(blocked_domains=["evil.com"]))
        result = checker.check("https://evil.com", depth=0)
        assert not result.allowed
        assert "blocked" in result.reason

    def test_depth_exceeded(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(max_depth=2))
        result = checker.check("https://example.com", depth=3)
        assert not result.allowed
        assert "Depth" in result.reason

    def test_robots_disallowed(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(respect_robots=True))
        checker.set_robots_allowed("evil.com", False)
        result = checker.check("https://evil.com", depth=0)
        assert not result.allowed
        assert "Robots" in result.reason

    def test_robots_allowed(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(respect_robots=True))
        checker.set_robots_allowed("evil.com", True)
        result = checker.check("https://evil.com", depth=0)
        assert result.allowed

    def test_auth_bypass_never_allowed(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allow_auth_bypass=True))
        result = checker.check("https://example.com", depth=0)
        assert not result.allowed
        assert "Auth bypass" in result.reason

    def test_tos_blocked_domain(self):
        """Terms of Service compliance should block crawling."""
        checker = CrawlPolicyChecker()
        checker.register_policy(
            CrawlPolicy(respect_terms_of_service=True, blocked_by_tos=["evil.com"])
        )
        result = checker.check("https://evil.com", depth=0)
        assert not result.allowed
        assert "Terms of Service" in result.reason

    def test_tos_allowed_domain(self):
        """Domains not in ToS block list should be allowed."""
        checker = CrawlPolicyChecker()
        checker.register_policy(
            CrawlPolicy(respect_terms_of_service=True, blocked_by_tos=["blocked.com"])
        )
        result = checker.check("https://evil.com", depth=0)
        assert result.allowed

    def test_set_tos_blocked(self):
        """set_tos_blocked should add domain to blocked list."""
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(respect_terms_of_service=True))
        checker.set_tos_blocked("evil.com")
        result = checker.check("https://evil.com", depth=0)
        assert not result.allowed

    def test_content_size_limit(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(max_content_size_bytes=100))
        result = checker.check_content("text/html", 200)
        assert not result.allowed

    def test_content_type_limit(self):
        checker = CrawlPolicyChecker()
        checker.register_policy(CrawlPolicy(allowed_content_types=["text/html"]))
        result = checker.check_content("application/pdf", 100)
        assert not result.allowed


# ═══════════════════════════════════════════════
# MOCK FETCHER
# ═══════════════════════════════════════════════


class TestMockFetcher:
    def test_registered_fixture(self, fetcher):
        result = asyncio.run(fetcher.fetch("https://evil.com"))
        assert result.status_code == 200
        assert b"Phishing Site" in result.content

    def test_no_fixture_returns_404(self, fetcher):
        result = asyncio.run(fetcher.fetch("https://unknown.com"))
        assert result.status_code == 404
        assert result.error is not None

    def test_fetch_count(self, fetcher):
        asyncio.run(fetcher.fetch("https://evil.com"))
        asyncio.run(fetcher.fetch("https://good.com"))
        assert fetcher.fetch_count == 2


# ═══════════════════════════════════════════════
# CONTENT EXTRACTION
# ═══════════════════════════════════════════════


class TestContentExtractor:
    def test_extract_title(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com",
            content=b"<html><title>Test Title</title><body>Content</body></html>",
        )
        extracted = extractor.extract(result, base_url="https://example.com")
        assert extracted.title == "Test Title"

    def test_extract_text(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com", content=b"<html><body><p>Hello World</p></body></html>"
        )
        extracted = extractor.extract(result)
        assert "Hello World" in extracted.text

    def test_extract_links(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com",
            content=b'<html><body><a href="/page1">Link1</a><a href="https://other.com">Link2</a></body></html>',
        )
        extracted = extractor.extract(result, base_url="https://example.com")
        assert "https://example.com/page1" in extracted.links
        assert "https://other.com" in extracted.links

    def test_extract_email(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com", content=b"<html><body>scam@evil.com</body></html>"
        )
        extracted = extractor.extract(result)
        emails = [e for e in extracted.entities if e["type"] == "EMAIL"]
        assert len(emails) == 1
        assert emails[0]["value"] == "scam@evil.com"

    def test_extract_phone(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com", content=b"<html><body>+34612345678</body></html>"
        )
        extracted = extractor.extract(result)
        phones = [e for e in extracted.entities if e["type"] == "PHONE"]
        assert len(phones) == 1

    def test_extract_ip(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com", content=b"<html><body>192.168.1.1</body></html>"
        )
        extracted = extractor.extract(result)
        ips = [e for e in extracted.entities if e["type"] == "IP"]
        assert len(ips) == 1
        assert ips[0]["value"] == "192.168.1.1"

    def test_extract_metadata(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com",
            content=b'<html><head><meta name="description" content="Test page"></head></html>',
        )
        extracted = extractor.extract(result)
        assert extracted.metadata.get("description") == "Test page"

    def test_extract_url_entities(self):
        extractor = ContentExtractor()
        result = FetchResult(
            url="https://example.com", content=b"<html><body>https://link.com/page</body></html>"
        )
        extracted = extractor.extract(result)
        urls = [e for e in extracted.entities if e["type"] == "URL"]
        assert len(urls) >= 1

    def test_empty_content(self):
        extractor = ContentExtractor()
        result = FetchResult(url="https://example.com", content=b"")
        extracted = extractor.extract(result)
        assert extracted.text == ""
        assert extracted.links == []


# ═══════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════


class TestDeduplication:
    def test_url_normalization(self, engine):
        norm1 = engine.normalize_url("https://EVIL.COM/")
        norm2 = engine.normalize_url("https://evil.com")
        assert norm1 == norm2

    def test_duplicate_url_skipped(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        engine._queue.clear()
        job2 = engine.submit_seed("https://evil.com")
        assert job2.status == CrawlStatus.SKIPPED

    def test_duplicate_content_hash(self, fetcher):
        fetcher.register_page("https://dup1.com", "<html><body>Same content</body></html>")
        fetcher.register_page("https://dup2.com", "<html><body>Same content</body></html>")
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        engine.submit_seed("https://dup1.com")
        engine.submit_seed("https://dup2.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_deduped"] >= 1


# ═══════════════════════════════════════════════
# RETRIES AND DEAD-LETTER QUEUE
# ═══════════════════════════════════════════════


class TestRetriesAndDLQ:
    def test_retry_on_failure(self, fetcher):
        fetcher.register_page("https://fail.com", "", status_code=500)
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        job = engine.submit_seed("https://fail.com", max_depth=0)
        job.max_retries = 2
        asyncio.run(engine.process_one())
        assert job.retry_count == 1
        assert job.status == CrawlStatus.QUEUED

    def test_dead_letter_after_max_retries(self, fetcher):
        fetcher.register_page("https://fail.com", "", status_code=500)
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        job = engine.submit_seed("https://fail.com", max_depth=0)
        job.max_retries = 2
        for _ in range(5):
            asyncio.run(engine.process_one())
            if job.status == CrawlStatus.QUEUED:
                job.next_attempt_at = utc_now()
        assert job.status == CrawlStatus.DEAD_LETTER
        dlq = engine.get_dead_letter_queue()
        assert len(dlq) >= 1

    def test_retry_exponential_backoff(self, fetcher):
        fetcher.register_page("https://fail.com", "", status_code=500)
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        job = engine.submit_seed("https://fail.com", max_depth=0)
        original_time = job.next_attempt_at
        asyncio.run(engine.process_one())
        assert job.next_attempt_at > original_time


# ═══════════════════════════════════════════════
# RATE LIMITING
# ═══════════════════════════════════════════════


class TestRateLimiting:
    def test_rate_limiter_allows_first(self):
        limiter = RateLimiter()
        allowed, _ = limiter.check("SRC-001", 1000)
        assert allowed

    def test_rate_limiter_blocks_second(self):
        limiter = RateLimiter()
        limiter.record("SRC-001", 5000)
        allowed, next_time = limiter.check("SRC-001", 5000)
        assert not allowed
        assert next_time is not None

    def test_rate_limiter_allows_after_delay(self):
        limiter = RateLimiter()
        limiter.record("SRC-001", 0)
        allowed, _ = limiter.check("SRC-001", 0)
        assert allowed


# ═══════════════════════════════════════════════
# OBSERVATION CREATION
# ═══════════════════════════════════════════════


class TestObservationCreation:
    def test_observation_created(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_observations"] >= 1

    def test_observation_has_provenance(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        for job in engine._jobs.values():
            if job.status == CrawlStatus.COMPLETED:
                assert job.observation_id is not None
                assert job.content_hash is not None
                break


# ═══════════════════════════════════════════════
# SEED DISCOVERY
# ═══════════════════════════════════════════════


class TestSeedDiscovery:
    def test_discover_links(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_discovered"] >= 1

    def test_discovered_seeds_queued(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        job_urls = [j.seed_url for j in engine._jobs.values()]
        assert any("login" in url for url in job_urls)

    def test_discovery_respects_max_depth(self, fetcher):
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0, max_depth=0))
        engine.submit_seed("https://evil.com", max_depth=0)
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_discovered"] == 0


# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════


class TestMetrics:
    def test_empty_metrics(self, engine):
        metrics = engine.get_metrics()
        assert metrics["total_crawled"] == 0
        assert metrics["queue_length"] == 0
        assert metrics["dlq_length"] == 0

    def test_metrics_after_crawl(self, engine):
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_crawled"] >= 1
        assert metrics["total_observations"] >= 1


# ═══════════════════════════════════════════════
# NEGATIVE / FAIL-SAFE
# ═══════════════════════════════════════════════


class TestNegativeFailSafe:
    def test_no_fixture_returns_404(self, fetcher):
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        engine.submit_seed("https://unknown.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_failed"] >= 1
        assert metrics["total_crawled"] == 0

    def test_empty_queue(self, engine):
        result = asyncio.run(engine.process_one())
        assert result is None

    def test_process_all_empty(self, engine):
        results = asyncio.run(engine.process_all())
        assert results == []

    def test_policy_blocked_url(self, fetcher):
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(
            CrawlPolicy(request_delay_ms=0, blocked_domains=["evil.com"])
        )
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_policy_blocked"] >= 1


# ═══════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════


class TestIntegration:
    def test_full_crawl_workflow(self, fetcher):
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0, max_depth=2))
        engine.submit_seed("https://evil.com", max_depth=2)
        asyncio.run(engine.process_all())
        engine._rate_limiter = RateLimiter()
        asyncio.run(engine.process_all())
        metrics = engine.get_metrics()
        assert metrics["total_crawled"] >= 2
        assert metrics["total_discovered"] >= 1
        assert metrics["total_observations"] >= 2

    def test_evidence_integration(self, fetcher):
        from services.evidence_vault import EvidenceVault

        vault = EvidenceVault()
        engine = WebDiscoveryEngine(fetcher=fetcher, evidence_vault=vault)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        engine.submit_seed("https://evil.com")
        asyncio.run(engine.process_all())
        for job in engine._jobs.values():
            if job.status == CrawlStatus.COMPLETED:
                assert job.evidence_id is not None
                break

    def test_priority_ordering(self, fetcher):
        engine = WebDiscoveryEngine(fetcher=fetcher)
        engine._policy_checker.register_policy(CrawlPolicy(request_delay_ms=0))
        engine.submit_seed("https://good.com", priority=CrawlPriority.LOW)
        engine.submit_seed("https://evil.com", priority=CrawlPriority.URGENT)
        job = asyncio.run(engine.process_one())
        assert job is not None
        assert job.seed_url == "https://evil.com"

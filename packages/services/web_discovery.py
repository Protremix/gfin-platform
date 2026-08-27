# GFIN Web Discovery Engine — Module 08
#
# Per Master Spec §12 (Web Discovery Engine):
# Functions: receive seed, schedule crawl, fetch permitted content, extract text,
# extract links, extract entities, extract metadata, create observations,
# preserve provenance, discover additional seeds, submit new jobs.
# Requirements: queue-based processing, concurrency controls, source-specific
# rate limits, retries, dead-letter queues, deduplication, content hashing,
# crawl policies, robots/terms compliance, no bypass of auth/access controls.
#
# Per GPT Luna guidance:
# - Layer A: In-memory job queue, scheduler, mock fetcher, discovery pipeline
# - Layer B: Distributed crawlers, Kafka queue, persistent scheduler (REQUIRES EXTERNAL INFRASTRUCTURE)
# - Use deterministic mock fetcher (no real HTTP by default)
# - Use Module 06 Evidence Vault for content hashing/custody
# - Use Module 05 Event Bus for observation.created events
# - Crawl policy enforcement before fetch (robots, schemes, depth, size limits)

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from enum import Enum, StrEnum
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import BaseObservation, Provenance, utc_now

# ═══════════════════════════════════════════════
# CRAWL JOB MODEL
# ═══════════════════════════════════════════════


class CrawlStatus(StrEnum):
    """Status of a crawl job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    SKIPPED = "skipped"  # Deduplicated or policy-blocked


class CrawlPriority(int, Enum):
    """Priority levels for crawl jobs."""

    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class CrawlJob(BaseModel):
    """A single crawl job in the discovery queue.

    Per Luna: seed URL, parent job, crawl policy, priority, depth,
    source identity, retry count, status.
    """

    job_id: str = Field(default_factory=lambda: f"CRL-{uuid4().hex[:8].upper()}")
    seed_url: str
    parent_job_id: str | None = None  # Links to parent that discovered this seed
    crawl_policy_id: str = "default"
    priority: CrawlPriority = CrawlPriority.NORMAL
    depth: int = 0  # 0 = seed, increments for discovered links
    max_depth: int = 3
    source_id: str = ""  # BaseSource.id
    status: CrawlStatus = CrawlStatus.QUEUED
    retry_count: int = 0
    max_retries: int = 3
    next_attempt_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    content_hash: str | None = None
    observation_id: str | None = None
    evidence_id: str | None = None
    discovered_urls: list[str] = Field(default_factory=list)
    extracted_entities: list[dict[str, Any]] = Field(default_factory=list)
    extracted_metadata: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime = Field(default_factory=utc_now)  # For insertion-order tiebreaking

    model_config = {"use_enum_values": True}


class CrawlPolicy(BaseModel):
    """Policy governing what and how to crawl.

    Per Luna: robots/terms checks, allowed schemes and domains,
    maximum depth, content-type limits, size limits.
    """

    policy_id: str = "default"
    allowed_schemes: list[str] = Field(default_factory=lambda: ["http", "https"])
    allowed_domains: list[str] = Field(default_factory=list)  # Empty = all allowed
    blocked_domains: list[str] = Field(default_factory=list)
    max_depth: int = 3
    max_content_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_content_types: list[str] = Field(
        default_factory=lambda: [
            "text/html",
            "application/xhtml+xml",
            "text/plain",
            "application/json",
        ]
    )
    respect_robots: bool = True
    follow_redirects: bool = True
    max_redirects: int = 5
    request_delay_ms: int = 1000  # Per-source rate limit
    max_concurrent_per_source: int = 1
    # Explicit: no bypass of auth/access controls
    allow_auth_bypass: bool = False  # ALWAYS False
    respect_terms_of_service: bool = True  # Check ToS before crawling
    blocked_by_tos: list[str] = Field(default_factory=list)  # Domains blocked by ToS

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# MOCK FETCHER (Layer A — no real HTTP)
# ═══════════════════════════════════════════════


class FetchResult(BaseModel):
    """Result of fetching a URL."""

    url: str
    status_code: int = 200
    headers: dict[str, str] = Field(default_factory=dict)
    content: bytes = b""
    content_type: str = "text/html"
    final_url: str = ""  # After redirects
    error: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class MockFetcher:
    """Deterministic mock fetcher for Layer A.

    Uses registered fixtures to simulate HTTP responses.
    Does NOT make real HTTP requests.
    """

    def __init__(self) -> None:
        self._fixtures: dict[str, FetchResult] = {}
        self._fetch_count = 0

    def register_fixture(self, url: str, result: FetchResult) -> None:
        """Register a fixture for a URL."""
        self._fixtures[url] = result

    def register_page(
        self,
        url: str,
        content: str,
        content_type: str = "text/html",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Convenience method to register a page."""
        self._fixtures[url] = FetchResult(
            url=url,
            status_code=status_code,
            headers=headers or {"Content-Type": content_type},
            content=content.encode(),
            content_type=content_type,
            final_url=url,
        )

    async def fetch(self, url: str) -> FetchResult:
        """Fetch a URL using registered fixtures.

        Returns a 404 FetchResult if no fixture is registered.
        """
        self._fetch_count += 1

        if url in self._fixtures:
            return self._fixtures[url]

        # No fixture — return 404
        return FetchResult(
            url=url,
            status_code=404,
            headers={},
            content=b"",
            content_type="",
            error="No fixture registered",
        )

    @property
    def fetch_count(self) -> int:
        return self._fetch_count


# ═══════════════════════════════════════════════
# CONTENT EXTRACTOR
# ═══════════════════════════════════════════════


class ExtractedContent(BaseModel):
    """Content extracted from a fetched page."""

    text: str = ""
    links: list[str] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    title: str = ""

    model_config = {"use_enum_values": True}


class ContentExtractor:
    """Extracts text, links, entities, and metadata from fetched content.

    Layer A: Simple regex-based extraction.
    Layer B: NLP-powered extraction, ML entity recognition.
    """

    # Regex patterns for entity extraction
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_PATTERN = re.compile(r"\+\d{6,15}")
    URL_PATTERN = re.compile(r'https?://[^\s<>"\']+')
    IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

    def extract(self, fetch_result: FetchResult, base_url: str = "") -> ExtractedContent:
        """Extract content from a fetch result."""
        content_str = fetch_result.content.decode("utf-8", errors="ignore")

        # Extract title
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>", content_str, re.IGNORECASE | re.DOTALL
        )
        title = title_match.group(1).strip() if title_match else ""

        # Extract text (remove HTML tags)
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", content_str, flags=re.IGNORECASE | re.DOTALL
        )
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        # Extract links (href attributes)
        link_matches = re.findall(r'href=["\']([^"\']+)["\']', content_str, re.IGNORECASE)
        links = []
        for link in link_matches:
            if base_url:
                absolute = urljoin(base_url, link)
                links.append(absolute)
            else:
                links.append(link)

        # Extract entities
        entities = []

        for email in self.EMAIL_PATTERN.findall(content_str):
            entities.append({"type": "EMAIL", "value": email})

        for phone in self.PHONE_PATTERN.findall(content_str):
            entities.append({"type": "PHONE", "value": phone})

        for url in self.URL_PATTERN.findall(content_str):
            entities.append({"type": "URL", "value": url})

        for ip in self.IP_PATTERN.findall(content_str):
            # Basic validation
            parts = ip.split(".")
            if all(0 <= int(p) <= 255 for p in parts):
                entities.append({"type": "IP", "value": ip})

        # Extract metadata
        metadata = {}
        meta_matches = re.findall(
            r'<meta\s+(?:name|property)=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\']',
            content_str,
            re.IGNORECASE,
        )
        for name, value in meta_matches:
            metadata[name] = value

        return ExtractedContent(
            text=text,
            links=links,
            entities=entities,
            metadata=metadata,
            title=title,
        )


# ═══════════════════════════════════════════════
# CRAWL POLICY CHECKER
# ═══════════════════════════════════════════════


class PolicyCheckResult(BaseModel):
    """Result of a crawl policy check."""

    allowed: bool
    reason: str

    model_config = {"use_enum_values": True}


class CrawlPolicyChecker:
    """Enforces crawl policies before fetching.

    Per Luna: robots/terms checks, allowed schemes and domains,
    max depth, content-type limits, size limits, no auth bypass.
    """

    def __init__(self) -> None:
        self._policies: dict[str, CrawlPolicy] = {}
        self._robots_cache: dict[str, bool] = {}  # domain → allowed (simplified)

    def register_policy(self, policy: CrawlPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def set_robots_allowed(self, domain: str, allowed: bool) -> None:
        """Set robots.txt allowance for a domain (Layer A: manual)."""
        self._robots_cache[domain] = allowed

    def set_tos_blocked(self, domain: str) -> None:
        """Mark a domain as blocked by Terms of Service (Layer A: manual)."""
        policy = self._policies.get("default", CrawlPolicy())
        if domain not in policy.blocked_by_tos:
            policy.blocked_by_tos.append(domain)
            self._policies[policy.policy_id] = policy

    def check(self, url: str, depth: int, policy_id: str = "default") -> PolicyCheckResult:
        """Check if a URL can be crawled under the given policy."""
        policy = self._policies.get(policy_id, CrawlPolicy())
        parsed = urlparse(url)

        # 1. Scheme check
        if parsed.scheme not in policy.allowed_schemes:
            return PolicyCheckResult(allowed=False, reason=f"Scheme not allowed: {parsed.scheme}")

        # 2. Domain check
        domain = parsed.hostname or ""
        if policy.allowed_domains and domain not in policy.allowed_domains:
            return PolicyCheckResult(allowed=False, reason=f"Domain not in allowed list: {domain}")

        if domain in policy.blocked_domains:
            return PolicyCheckResult(allowed=False, reason=f"Domain blocked: {domain}")

        # 3. Depth check
        if depth > policy.max_depth:
            return PolicyCheckResult(
                allowed=False, reason=f"Depth {depth} exceeds max {policy.max_depth}"
            )

        # 4. Robots check
        if policy.respect_robots and domain in self._robots_cache:
            if not self._robots_cache[domain]:
                return PolicyCheckResult(allowed=False, reason=f"Robots.txt disallows: {domain}")

        # 5. No auth bypass
        if policy.allow_auth_bypass:
            return PolicyCheckResult(allowed=False, reason="Auth bypass is NEVER allowed")

        # 6. Terms of Service compliance
        if policy.respect_terms_of_service and domain in policy.blocked_by_tos:
            return PolicyCheckResult(
                allowed=False, reason=f"Terms of Service disallow crawling: {domain}"
            )

        return PolicyCheckResult(allowed=True, reason="Policy check passed")

    def check_content(
        self, content_type: str, content_size: int, policy_id: str = "default"
    ) -> PolicyCheckResult:
        """Check if fetched content meets policy limits."""
        policy = self._policies.get(policy_id, CrawlPolicy())

        if content_size > policy.max_content_size_bytes:
            return PolicyCheckResult(
                allowed=False,
                reason=f"Content size {content_size} exceeds limit {policy.max_content_size_bytes}",
            )

        if policy.allowed_content_types and content_type not in policy.allowed_content_types:
            return PolicyCheckResult(
                allowed=False, reason=f"Content type not allowed: {content_type}"
            )

        return PolicyCheckResult(allowed=True, reason="Content policy passed")


# ═══════════════════════════════════════════════
# RATE LIMITER (per-source)
# ═══════════════════════════════════════════════


class RateLimiter:
    """Per-source rate limiter.

    Layer A: In-memory next-permitted-request tracking.
    Layer B: Distributed rate limiting (Redis-based).
    """

    def __init__(self) -> None:
        self._next_allowed: dict[str, datetime] = {}  # source_id → next allowed time

    def check(self, source_id: str, delay_ms: int) -> tuple[bool, datetime | None]:
        """Check if a request is allowed for this source.

        Returns (allowed, next_allowed_time).
        """
        now = utc_now()
        next_allowed = self._next_allowed.get(source_id)

        if next_allowed and now < next_allowed:
            return False, next_allowed

        return True, None

    def record(self, source_id: str, delay_ms: int) -> None:
        """Record a request for rate limiting."""
        self._next_allowed[source_id] = utc_now() + timedelta(milliseconds=delay_ms)


# ═══════════════════════════════════════════════
# WEB DISCOVERY ENGINE
# ═══════════════════════════════════════════════


class WebDiscoveryEngine:
    """Web discovery engine — distributed crawling system (Layer A: in-memory).

    Per Master Spec §12:
    - receive seed, schedule crawl, fetch permitted content
    - extract text, links, entities, metadata
    - create observations, preserve provenance
    - discover additional seeds, submit new jobs

    Per Luna:
    - In-memory job queue with priority scheduling
    - Deterministic mock fetcher (no real HTTP)
    - Crawl policy enforcement before fetch
    - Deduplication via normalized URL keys + content hashes
    - Retries with exponential backoff + DLQ
    - Per-source rate limiting
    - Bounded worker concurrency (configurable)
    """

    def __init__(
        self,
        fetcher: MockFetcher | None = None,
        policy_checker: CrawlPolicyChecker | None = None,
        evidence_vault: Any = None,
        event_bus: Any = None,
        max_workers: int = 1,
    ) -> None:
        self._fetcher = fetcher or MockFetcher()
        self._policy_checker = policy_checker or CrawlPolicyChecker()
        self._policy_checker.register_policy(CrawlPolicy())  # Default policy
        self._evidence_vault = evidence_vault
        self._event_bus = event_bus
        self._max_workers = max_workers
        self._extractor = ContentExtractor()
        self._rate_limiter = RateLimiter()

        # Job storage
        self._jobs: dict[str, CrawlJob] = {}
        self._queue: list[CrawlJob] = []  # Sorted by priority, then next_attempt_at
        self._dead_letter_queue: list[CrawlJob] = []

        # Deduplication
        self._processed_urls: set[str] = set()  # Normalized URLs already processed
        self._content_hashes: set[str] = set()  # Content hashes already seen

        # Metrics
        self._total_crawled = 0
        self._total_failed = 0
        self._total_discovered = 0
        self._total_observations = 0
        self._total_deduped = 0
        self._total_policy_blocked = 0

    def normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Lowercase scheme and host, remove fragment, strip trailing slash
        normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def submit_seed(
        self,
        url: str,
        source_id: str = "SRC-WEB",
        policy_id: str = "default",
        priority: CrawlPriority = CrawlPriority.NORMAL,
        max_depth: int = 3,
    ) -> CrawlJob:
        """Submit a seed URL for crawling.

        Per spec: receive seed, submit new jobs.
        """
        norm_url = self.normalize_url(url)

        # Deduplication — don't re-crawl already processed URLs
        if norm_url in self._processed_urls:
            job = CrawlJob(
                seed_url=url,
                source_id=source_id,
                crawl_policy_id=policy_id,
                priority=priority,
                max_depth=max_depth,
                status=CrawlStatus.SKIPPED,
                error_message="URL already processed (deduplication)",
            )
            self._jobs[job.job_id] = job
            self._total_deduped += 1
            return job

        job = CrawlJob(
            seed_url=url,
            source_id=source_id,
            crawl_policy_id=policy_id,
            priority=priority,
            max_depth=max_depth,
            depth=0,
        )
        self._jobs[job.job_id] = job
        self._enqueue(job)
        return job

    def _enqueue(self, job: CrawlJob) -> None:
        """Add a job to the priority queue."""
        self._queue.append(job)
        # Sort by priority (lower = higher priority), then next_attempt_at, then queued_at
        self._queue.sort(
            key=lambda j: (
                j.priority if isinstance(j.priority, int) else int(j.priority),
                j.next_attempt_at,
                j.queued_at,
            )
        )

    async def process_one(self) -> CrawlJob | None:
        """Process the next job in the queue.

        Returns the processed job, or None if queue is empty.
        """
        # Find next runnable job
        now = utc_now()
        runnable = None
        runnable_idx = -1

        for i, job in enumerate(self._queue):
            if job.status not in (CrawlStatus.QUEUED.value, CrawlStatus.QUEUED):
                continue
            next_attempt = job.next_attempt_at
            if isinstance(next_attempt, str):
                next_attempt = datetime.fromisoformat(next_attempt)
            if next_attempt <= now:
                # Check rate limit
                delay = self._get_policy_delay(job.crawl_policy_id)
                allowed, _ = self._rate_limiter.check(job.source_id, delay)
                if allowed:
                    runnable = job
                    runnable_idx = i
                    break

        if runnable is None:
            return None

        # Remove from queue
        self._queue.pop(runnable_idx)

        # Process
        await self._process_job(runnable)
        return runnable

    async def process_all(self) -> list[CrawlJob]:
        """Process all runnable jobs in the queue."""
        results = []
        while True:
            job = await self.process_one()
            if job is None:
                break
            results.append(job)
        return results

    def _get_policy_delay(self, policy_id: str) -> int:
        """Get rate limit delay from policy."""
        policy = self._policy_checker._policies.get(policy_id, CrawlPolicy())
        return policy.request_delay_ms

    async def _process_job(self, job: CrawlJob) -> None:
        """Process a single crawl job."""
        job.status = CrawlStatus.RUNNING
        job.started_at = utc_now()

        # Record rate limit
        delay = self._get_policy_delay(job.crawl_policy_id)
        self._rate_limiter.record(job.source_id, delay)

        # 1. Policy check
        policy_result = self._policy_checker.check(job.seed_url, job.depth, job.crawl_policy_id)
        if not policy_result.allowed:
            job.status = CrawlStatus.FAILED
            job.error_message = f"Policy blocked: {policy_result.reason}"
            self._total_policy_blocked += 1
            self._handle_failure(job)
            return

        # 2. Fetch
        fetch_result = await self._fetcher.fetch(job.seed_url)

        if fetch_result.error or fetch_result.status_code >= 400:
            job.status = CrawlStatus.FAILED
            job.error_message = fetch_result.error or f"HTTP {fetch_result.status_code}"
            self._handle_failure(job)
            return

        # 3. Content policy check
        content_size = len(fetch_result.content)
        content_check = self._policy_checker.check_content(
            fetch_result.content_type, content_size, job.crawl_policy_id
        )
        if not content_check.allowed:
            job.status = CrawlStatus.FAILED
            job.error_message = f"Content policy: {content_check.reason}"
            self._handle_failure(job)
            return

        # 4. Content hash + deduplication
        content_hash = hashlib.sha256(fetch_result.content).hexdigest()
        job.content_hash = content_hash

        if content_hash in self._content_hashes:
            job.status = CrawlStatus.SKIPPED
            job.error_message = "Duplicate content (same hash)"
            self._total_deduped += 1
            self._processed_urls.add(self.normalize_url(job.seed_url))
            job.completed_at = utc_now()
            return

        self._content_hashes.add(content_hash)
        self._processed_urls.add(self.normalize_url(job.seed_url))

        # 5. Extract content
        extracted = self._extractor.extract(fetch_result, base_url=job.seed_url)

        job.discovered_urls = extracted.links
        job.extracted_entities = extracted.entities
        job.extracted_metadata = extracted.metadata

        # 6. Create observation
        observation = BaseObservation(
            entity_id=job.seed_url,  # URL as entity reference
            source_id=job.source_id,
            source_type="web_crawler",
            raw_value=job.seed_url,
            provenance=Provenance(
                source_id=job.source_id,
                source_type="web_crawler",
                acquisition_method="crawl",
                retrieval_timestamp=utc_now(),
                reference=job.seed_url,
            ),
            metadata={
                "content_hash": content_hash,
                "title": extracted.title,
                "content_type": fetch_result.content_type,
                "text_length": len(extracted.text),
                "links_count": len(extracted.links),
                "entities_count": len(extracted.entities),
            },
        )
        job.observation_id = observation.id
        self._total_observations += 1

        # 7. Evidence preservation (if vault is available)
        if self._evidence_vault:
            from schemas.base import BaseEvidence, Classification
            from schemas.enums import DataClassification

            evidence = BaseEvidence(
                source_id=job.source_id,
                source_reference=job.seed_url,
                retrieval_timestamp=utc_now(),
                content_hash=content_hash,
                content_type=fetch_result.content_type,
                classification=Classification(classification=DataClassification.PUBLIC),
            )
            try:
                stored = self._evidence_vault.create(
                    evidence, fetch_result.content, actor="web_discovery"
                )
                job.evidence_id = stored.evidence.id
            except Exception:
                pass  # Evidence vault not critical for Layer A crawl

        # 8. Discover additional seeds
        for link in extracted.links:
            norm_link = self.normalize_url(link)
            if norm_link not in self._processed_urls:
                # Check policy for discovered URL
                link_check = self._policy_checker.check(link, job.depth + 1, job.crawl_policy_id)
                if link_check.allowed and job.depth + 1 <= job.max_depth:
                    new_job = CrawlJob(
                        seed_url=link,
                        parent_job_id=job.job_id,
                        source_id=job.source_id,
                        crawl_policy_id=job.crawl_policy_id,
                        priority=job.priority,
                        depth=job.depth + 1,
                        max_depth=job.max_depth,
                    )
                    self._jobs[new_job.job_id] = new_job
                    self._enqueue(new_job)
                    self._total_discovered += 1

        # 9. Complete
        job.status = CrawlStatus.COMPLETED
        job.completed_at = utc_now()
        self._total_crawled += 1

    def _handle_failure(self, job: CrawlJob) -> None:
        """Handle a failed crawl job — retry or DLQ."""
        self._total_failed += 1
        max_retries = job.max_retries
        if job.retry_count < max_retries:
            job.retry_count += 1
            # Exponential backoff: 2^retry_count seconds
            backoff = timedelta(seconds=2**job.retry_count)
            job.next_attempt_at = utc_now() + backoff
            job.status = CrawlStatus.QUEUED
            self._enqueue(job)
        else:
            job.status = CrawlStatus.DEAD_LETTER
            job.completed_at = utc_now()
            self._dead_letter_queue.append(job)

    def get_job(self, job_id: str) -> CrawlJob | None:
        return self._jobs.get(job_id)

    def get_dead_letter_queue(self) -> list[CrawlJob]:
        return list(self._dead_letter_queue)

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_jobs": len(self._jobs),
            "queue_length": len(self._queue),
            "total_crawled": self._total_crawled,
            "total_failed": self._total_failed,
            "total_discovered": self._total_discovered,
            "total_observations": self._total_observations,
            "total_deduped": self._total_deduped,
            "total_policy_blocked": self._total_policy_blocked,
            "dlq_length": len(self._dead_letter_queue),
            "processed_urls": len(self._processed_urls),
            "unique_content_hashes": len(self._content_hashes),
        }


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# The following capabilities are NOT available in Layer A:
#
# - Distributed crawl workers across multiple nodes
# - Kafka-backed durable job queue
# - Persistent scheduler state across restarts
# - Distributed rate-limit coordination
# - Real HTTP fetching with TLS, proxy rotation, user agent management
# - Production robots.txt parsing and caching
# - Distributed deduplication (Redis-backed)
# - Scalable content storage (S3-backed)
# - Headless browser rendering (JavaScript execution)
# - CAPTCHA solving (NOT ALLOWED per Constitution — no auth bypass)
# - Distributed retry/DLQ storage
# - Crawl monitoring and alerting
# - Bandwidth throttling and QoS
# - Geo-distributed crawling
# - Content delivery network integration
# - Large-scale link graph analysis
# - Production entity extraction (NLP/ML models)
#
# All of the above are marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION
# Do NOT consider the web discovery engine production-ready until these are implemented.

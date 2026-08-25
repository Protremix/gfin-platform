# GFIN Infrastructure Intelligence — Module 09
#
# Per Master Spec §13 (Infrastructure Intelligence):
# For domains, collect: A/AAAA/MX/NS/CNAME/TXT records, DNS history, IP history,
# ASN, network info, provider info, TLS certs, CT observations, redirect chains,
# tech fingerprints, related domains, historical infrastructure.
#
# Interpretation rules: IP != owner, ASN != criminal, CDN != origin,
# Shared hosting != common ownership. Never infer criminal ownership from
# single technical correlation.
#
# Per GPT Luna:
# - Layer A: In-memory mock DNS/ASN/cert data with fixtures, observations, interpretation rules
# - Layer B: Live DNS, RDAP/WHOIS, CT logs, production fingerprinting (REQUIRES EXTERNAL INFRASTRUCTURE)
# - Mock data marked synthetic=true with fixture provenance
# - Enforce interpretation rules in schema (typed relationships) and operationally (validation)

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import utc_now, Provenance


# ═══════════════════════════════════════════════
# DNS RECORD OBSERVATION
# ═══════════════════════════════════════════════

class DNSRecordType(str, Enum):
    A = "A"
    AAAA = "AAAA"
    MX = "MX"
    NS = "NS"
    CNAME = "CNAME"
    TXT = "TXT"
    SOA = "SOA"
    PTR = "PTR"
    SRV = "SRV"
    CAA = "CAA"


class DNSObservation(BaseModel):
    """A DNS observation about a domain.

    OBSERVATION ≠ ENTITY. This records what was observed at a point in time.
    Per Luna: TTL, first-seen/last-seen, resolver context, record status.
    """
    observation_id: str = Field(default_factory=lambda: f"DNS-{uuid4().hex[:8].upper()}")
    domain: str
    record_type: DNSRecordType
    value: str  # The DNS record value
    ttl: int | None = None
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    resolver: str = "mock-resolver"  # Which resolver observed this
    is_synthetic: bool = True  # Layer A: always True (mock data)
    source_id: str = "SRC-INFRA-MOCK"
    provenance: Provenance | None = None
    confidence: float = 1.0  # Confidence in the observation itself

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# IP / ASN / NETWORK
# ═══════════════════════════════════════════════

class IPInfo(BaseModel):
    """Information about an IP address.

    Per Luna: Mock ASN, network, provider fields independently from ownership claims.
    IP != owner (interpretation rule).
    """
    ip_address: str
    ip_version: str = "IPv4"  # IPv4 or IPv6
    asn: str = ""  # AS number (e.g., "AS12345")
    asn_organization: str = ""  # ASN operator name
    network_name: str = ""  # Network/block name
    network_cidr: str = ""  # CIDR notation
    provider: str = ""  # Hosting provider
    is_cdn: bool = False  # Is this a CDN IP?
    is_hosting_provider: bool = False
    is_synthetic: bool = True
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    source_id: str = "SRC-INFRA-MOCK"

    model_config = {"use_enum_values": True}


class ASNInfo(BaseModel):
    """Autonomous System information.

    Per Luna: ASN != criminal (interpretation rule).
    """
    asn: str  # e.g., "AS12345"
    organization: str = ""
    country: str = ""
    network_prefixes: list[str] = Field(default_factory=list)
    is_synthetic: bool = True
    source_id: str = "SRC-INFRA-MOCK"

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# CERTIFICATE INTELLIGENCE
# ═══════════════════════════════════════════════

class CertificateObservation(BaseModel):
    """TLS certificate observation.

    Per spec: TLS certificates, Certificate Transparency observations.
    """
    observation_id: str = Field(default_factory=lambda: f"CRT-{uuid4().hex[:8].upper()}")
    domain: str
    fingerprint: str = ""  # SHA-256 fingerprint
    issuer: str = ""
    subject: str = ""
    serial_number: str = ""
    not_before: datetime | None = None
    not_after: datetime | None = None
    is_expired: bool = False
    is_self_signed: bool = False
    san_domains: list[str] = Field(default_factory=list)  # Subject Alternative Names
    ct_log_entries: list[dict[str, Any]] = Field(default_factory=list)  # CT log observations
    is_synthetic: bool = True
    first_seen: datetime = Field(default_factory=utc_now)
    last_seen: datetime = Field(default_factory=utc_now)
    source_id: str = "SRC-INFRA-MOCK"

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# REDIRECT CHAIN
# ═══════════════════════════════════════════════

class RedirectHop(BaseModel):
    """A single hop in a redirect chain."""
    url: str
    status_code: int = 301
    location: str = ""  # Where it redirects to
    timestamp: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


class RedirectChainObservation(BaseModel):
    """A redirect chain observed from a URL.

    Per spec: redirect chains.
    """
    observation_id: str = Field(default_factory=lambda: f"RDR-{uuid4().hex[:8].upper()}")
    start_url: str
    final_url: str
    hops: list[RedirectHop] = Field(default_factory=list)
    total_hops: int = 0
    is_synthetic: bool = True
    timestamp: datetime = Field(default_factory=utc_now)
    source_id: str = "SRC-INFRA-MOCK"

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# TECHNOLOGY FINGERPRINT
# ═══════════════════════════════════════════════

class TechnologyFingerprint(BaseModel):
    """A technology fingerprint observation.

    Per spec: technology fingerprints.
    """
    observation_id: str = Field(default_factory=lambda: f"TECH-{uuid4().hex[:8].upper()}")
    domain: str
    technologies: list[dict[str, str]] = Field(default_factory=list)  # [{name, version, category}]
    server_header: str = ""
    powered_by: str = ""
    is_synthetic: bool = True
    timestamp: datetime = Field(default_factory=utc_now)
    source_id: str = "SRC-INFRA-MOCK"

    model_config = {"use_enum_values": True}


# ═══════════════════════════════════════════════
# INFRASTRUCTURE RELATIONSHIP (with interpretation rules)
# ═══════════════════════════════════════════════

class InfraRelationType(str, Enum):
    """Typed infrastructure relationships.

    Per Luna: Model IP, ASN, CDN, origin, hosting, ownership as DISTINCT typed relationships.
    Prohibit automatic OWNS, OPERATES, CRIMINAL_ASSOCIATION from technical observations alone.
    """
    RESOLVES_TO = "resolves_to"  # Domain → IP (DNS resolution)
    ANNOUNCED_BY = "announced_by"  # IP → ASN (BGP announcement)
    HOSTED_ON = "hosted_on"  # Domain → IP (hosting)
    USES_CDN = "uses_cdn"  # Domain → CDN provider
    CERTIFICATE_FOR = "certificate_for"  # Certificate → Domain
    REDIRECTS_TO = "redirects_to"  # URL → URL
    RELATED_DOMAIN = "related_domain"  # Domain → Domain
    # Attribution edges — require evidence + analyst justification
    OWNS = "owns"  # Entity → Entity (requires evidence)
    OPERATES = "operates"  # Entity → Entity (requires evidence)
    CRIMINAL_ASSOCIATION = "criminal_association"  # Entity → Entity (requires evidence + corroboration)


class InfraRelationship(BaseModel):
    """A relationship between infrastructure entities.

    Per Luna: require evidence IDs, provenance, confidence, and analyst
    justification for attribution edges.
    """
    relationship_id: str = Field(default_factory=lambda: f"IR-{uuid4().hex[:8].upper()}")
    from_entity: str  # Entity ID or domain/IP
    to_entity: str
    relationship_type: InfraRelationType
    evidence_id: str | None = None  # Required for attribution edges
    provenance: Provenance | None = None
    confidence: float = 1.0
    analyst_justification: str = ""  # Required for attribution edges
    is_synthetic: bool = True
    timestamp: datetime = Field(default_factory=utc_now)

    model_config = {"use_enum_values": True}


# Attribution edges that require evidence + justification
ATTRIBUTION_EDGES = {
    InfraRelationType.OWNS.value,
    InfraRelationType.OPERATES.value,
    InfraRelationType.CRIMINAL_ASSOCIATION.value,
}


# ═══════════════════════════════════════════════
# INTERPRETATION RULE ENFORCEMENT
# ═══════════════════════════════════════════════

class InterpretationRuleResult(BaseModel):
    """Result of an interpretation rule check."""
    rule_name: str
    passed: bool
    message: str
    qualifying_language: str = ""  # Required display language

    model_config = {"use_enum_values": True}


def check_interpretation_rules(
    relationship_type: str,
    evidence_id: str | None = None,
    analyst_justification: str = "",
    has_multiple_correlations: bool = False,
) -> list[InterpretationRuleResult]:
    """Check infrastructure interpretation rules.

    Per Luna: enforce operationally — require evidence, justification,
    qualifying language, and return INSUFFICIENT_DATA when attribution evidence is absent.

    Rules:
    1. IP != owner: A 'resolves_to' relationship does not imply ownership
    2. ASN != criminal: An 'announced_by' relationship does not imply criminal association
    3. CDN != origin server: A 'uses_cdn' relationship does not identify the origin
    4. Shared hosting != common ownership: Co-hosting does not imply common ownership
    5. No criminal ownership from single correlation
    """
    results = []

    # Rule 1: IP != owner
    if relationship_type == InfraRelationType.RESOLVES_TO.value:
        results.append(InterpretationRuleResult(
            rule_name="IP != owner",
            passed=True,
            message="DNS resolution does not imply ownership",
            qualifying_language="resolves to",
        ))

    # Rule 2: ASN != criminal
    if relationship_type == InfraRelationType.ANNOUNCED_BY.value:
        results.append(InterpretationRuleResult(
            rule_name="ASN != criminal",
            passed=True,
            message="ASN announcement does not imply criminal association",
            qualifying_language="announced by",
        ))

    # Rule 3: CDN != origin
    if relationship_type == InfraRelationType.USES_CDN.value:
        results.append(InterpretationRuleResult(
            rule_name="CDN != origin server",
            passed=True,
            message="CDN usage does not identify the origin server",
            qualifying_language="uses CDN",
        ))

    # Rule 4: Shared hosting != common ownership
    if relationship_type == InfraRelationType.HOSTED_ON.value:
        results.append(InterpretationRuleResult(
            rule_name="Shared hosting != common ownership",
            passed=True,
            message="Co-hosting does not imply common ownership",
            qualifying_language="hosted on",
        ))

    # Attribution edge checks
    if relationship_type in ATTRIBUTION_EDGES:
        # Rule 5: No criminal ownership from single correlation
        if relationship_type == InfraRelationType.CRIMINAL_ASSOCIATION.value:
            if not has_multiple_correlations:
                results.append(InterpretationRuleResult(
                    rule_name="No criminal ownership from single correlation",
                    passed=False,
                    message="INSUFFICIENT_DATA: Criminal association requires multiple corroborating correlations",
                ))
            else:
                results.append(InterpretationRuleResult(
                    rule_name="No criminal ownership from single correlation",
                    passed=True,
                    message="Multiple correlations present — criminal association may be considered with analyst review",
                ))

        # Evidence required for attribution
        if not evidence_id:
            results.append(InterpretationRuleResult(
                rule_name="Attribution requires evidence",
                passed=False,
                message="INSUFFICIENT_DATA: Attribution edge requires evidence reference",
            ))

        # Analyst justification required for attribution
        if not analyst_justification:
            results.append(InterpretationRuleResult(
                rule_name="Attribution requires justification",
                passed=False,
                message="INSUFFICIENT_DATA: Attribution edge requires analyst justification",
            ))

    return results


def validate_attribution(
    relationship_type: str,
    evidence_id: str | None = None,
    analyst_justification: str = "",
    has_multiple_correlations: bool = False,
) -> tuple[bool, str]:
    """Validate whether an attribution edge can be created.

    Returns (is_valid, reason).
    """
    if relationship_type not in ATTRIBUTION_EDGES:
        return True, "Non-attribution edge — no special validation required"

    rules = check_interpretation_rules(
        relationship_type, evidence_id, analyst_justification, has_multiple_correlations
    )

    for rule in rules:
        if not rule.passed:
            return False, rule.message

    return True, "Attribution validated — evidence and justification provided"


# ═══════════════════════════════════════════════
# INFRASTRUCTURE INTELLIGENCE SERVICE
# ═══════════════════════════════════════════════

class InfrastructureIntelligenceService:
    """Infrastructure intelligence service — Layer A (in-memory).

    Per Master Spec §13: Collect and correlate infrastructure observations
    for domains, IPs, ASNs, certificates, and related infrastructure.

    Per Luna:
    - Use deterministic fixtures, mark synthetic=true, include fixture provenance
    - Enforce interpretation rules in schema and operationally
    - Integrate with Event Bus, Evidence Vault, Search Platform
    """

    def __init__(self) -> None:
        # DNS observations by domain
        self._dns_observations: dict[str, list[DNSObservation]] = {}
        # IP info by IP address
        self._ip_info: dict[str, IPInfo] = {}
        # ASN info by AS number
        self._asn_info: dict[str, ASNInfo] = {}
        # Certificate observations by domain
        self._cert_observations: dict[str, list[CertificateObservation]] = {}
        # Redirect chains by start URL
        self._redirect_chains: dict[str, RedirectChainObservation] = {}
        # Technology fingerprints by domain
        self._tech_fingerprints: dict[str, TechnologyFingerprint] = {}
        # Infrastructure relationships
        self._relationships: list[InfraRelationship] = []
        # DNS history by domain (chronological)
        self._dns_history: dict[str, list[DNSObservation]] = {}
        # IP history by domain
        self._ip_history: dict[str, list[str]] = {}

    def register_dns_record(
        self, domain: str, record_type: DNSRecordType, value: str,
        ttl: int = 3600, resolver: str = "mock-resolver",
    ) -> DNSObservation:
        """Register a DNS observation (mock fixture)."""
        obs = DNSObservation(
            domain=domain.lower(),
            record_type=record_type,
            value=value,
            ttl=ttl,
            resolver=resolver,
            is_synthetic=True,
            provenance=Provenance(
                source_id="SRC-INFRA-MOCK",
                source_type="dns_fixture",
                acquisition_method="mock_lookup",
                retrieval_timestamp=utc_now(),
                reference=f"mock://{domain}/{record_type.value}",
            ),
        )
        if domain.lower() not in self._dns_observations:
            self._dns_observations[domain.lower()] = []
        self._dns_observations[domain.lower()].append(obs)

        # Track DNS history
        if domain.lower() not in self._dns_history:
            self._dns_history[domain.lower()] = []
        self._dns_history[domain.lower()].append(obs)

        return obs

    def register_ip_info(self, ip_address: str, **kwargs) -> IPInfo:
        """Register IP address information (mock fixture)."""
        info = IPInfo(ip_address=ip_address, is_synthetic=True, **kwargs)
        self._ip_info[ip_address] = info
        return info

    def register_asn_info(self, asn: str, **kwargs) -> ASNInfo:
        """Register ASN information (mock fixture)."""
        info = ASNInfo(asn=asn, is_synthetic=True, **kwargs)
        self._asn_info[asn] = info
        return info

    def register_certificate(self, domain: str, **kwargs) -> CertificateObservation:
        """Register a TLS certificate observation (mock fixture)."""
        cert = CertificateObservation(domain=domain.lower(), is_synthetic=True, **kwargs)
        if domain.lower() not in self._cert_observations:
            self._cert_observations[domain.lower()] = []
        self._cert_observations[domain.lower()].append(cert)
        return cert

    def register_redirect_chain(self, start_url: str, hops: list[dict], final_url: str = "") -> RedirectChainObservation:
        """Register a redirect chain observation."""
        hop_objects = [RedirectHop(**h) for h in hops]
        if not final_url and hop_objects:
            final_url = hop_objects[-1].location or hop_objects[-1].url
        chain = RedirectChainObservation(
            start_url=start_url,
            final_url=final_url,
            hops=hop_objects,
            total_hops=len(hop_objects),
            is_synthetic=True,
        )
        self._redirect_chains[start_url] = chain
        return chain

    def register_tech_fingerprint(self, domain: str, **kwargs) -> TechnologyFingerprint:
        """Register a technology fingerprint observation."""
        fp = TechnologyFingerprint(domain=domain.lower(), is_synthetic=True, **kwargs)
        self._tech_fingerprints[domain.lower()] = fp
        return fp

    def add_relationship(
        self, from_entity: str, to_entity: str,
        relationship_type: InfraRelationType,
        evidence_id: str | None = None,
        analyst_justification: str = "",
        confidence: float = 1.0,
        has_multiple_correlations: bool = False,
    ) -> tuple[InfraRelationship | None, str]:
        """Add an infrastructure relationship.

        Per Luna: enforce interpretation rules operationally.
        Attribution edges require evidence + justification.
        Returns (relationship, reason) — relationship is None if validation fails.
        """
        rel_type = relationship_type.value if hasattr(relationship_type, 'value') else str(relationship_type)

        # Validate attribution
        is_valid, reason = validate_attribution(
            rel_type, evidence_id, analyst_justification, has_multiple_correlations
        )

        if not is_valid:
            return None, reason

        rel = InfraRelationship(
            from_entity=from_entity,
            to_entity=to_entity,
            relationship_type=relationship_type,
            evidence_id=evidence_id,
            analyst_justification=analyst_justification,
            confidence=confidence,
            is_synthetic=True,
        )
        self._relationships.append(rel)
        return rel, "Relationship created"

    def get_dns_records(self, domain: str, record_type: str | None = None) -> list[DNSObservation]:
        """Get DNS observations for a domain."""
        records = self._dns_observations.get(domain.lower(), [])
        if record_type:
            return [r for r in records if r.record_type == record_type or (hasattr(r.record_type, 'value') and r.record_type.value == record_type)]
        return list(records)

    def get_dns_history(self, domain: str) -> list[DNSObservation]:
        """Get DNS history for a domain."""
        return list(self._dns_history.get(domain.lower(), []))

    def get_ip_info(self, ip_address: str) -> IPInfo | None:
        return self._ip_info.get(ip_address)

    def get_asn_info(self, asn: str) -> ASNInfo | None:
        return self._asn_info.get(asn)

    def get_certificates(self, domain: str) -> list[CertificateObservation]:
        return list(self._cert_observations.get(domain.lower(), []))

    def get_redirect_chain(self, url: str) -> RedirectChainObservation | None:
        return self._redirect_chains.get(url)

    def get_tech_fingerprint(self, domain: str) -> TechnologyFingerprint | None:
        return self._tech_fingerprints.get(domain.lower())

    def get_relationships(
        self, entity: str | None = None, relationship_type: str | None = None
    ) -> list[InfraRelationship]:
        """Get relationships, optionally filtered."""
        results = self._relationships
        if entity:
            results = [r for r in results if r.from_entity == entity or r.to_entity == entity]
        if relationship_type:
            results = [r for r in results if r.relationship_type == relationship_type or (hasattr(r.relationship_type, 'value') and r.relationship_type.value == relationship_type)]
        return list(results)

    def get_domain_profile(self, domain: str) -> dict[str, Any]:
        """Get a complete infrastructure profile for a domain.

        Aggregates: DNS records, IP info, certificates, redirects, tech fingerprints,
        relationships, history.
        """
        domain = domain.lower()
        profile = {
            "domain": domain,
            "dns_records": {},
            "ip_addresses": [],
            "ip_info": [],
            "asn_info": [],
            "certificates": [],
            "redirect_chains": [],
            "tech_fingerprint": None,
            "relationships": [],
            "dns_history_count": 0,
            "is_synthetic": True,
        }

        # DNS records grouped by type
        dns_obs = self._dns_observations.get(domain, [])
        for obs in dns_obs:
            rt = obs.record_type if isinstance(obs.record_type, str) else obs.record_type.value
            if rt not in profile["dns_records"]:
                profile["dns_records"][rt] = []
            profile["dns_records"][rt].append(obs.value)

        # IP addresses from A/AAAA records
        for obs in dns_obs:
            rt = obs.record_type if isinstance(obs.record_type, str) else obs.record_type.value
            if rt in ("A", "AAAA"):
                profile["ip_addresses"].append(obs.value)
                ip_info = self._ip_info.get(obs.value)
                if ip_info:
                    profile["ip_info"].append(ip_info)
                    if ip_info.asn and ip_info.asn not in [a.get("asn") for a in profile["asn_info"]]:
                        asn = self._asn_info.get(ip_info.asn)
                        if asn:
                            profile["asn_info"].append(asn)

        # Certificates
        profile["certificates"] = self.get_certificates(domain)

        # Redirect chains starting from this domain
        for url, chain in self._redirect_chains.items():
            if domain in url:
                profile["redirect_chains"].append(chain)

        # Tech fingerprint
        profile["tech_fingerprint"] = self.get_tech_fingerprint(domain)

        # Relationships
        profile["relationships"] = self.get_relationships(entity=domain)

        # DNS history count
        profile["dns_history_count"] = len(self.get_dns_history(domain))

        return profile

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_domains_tracked": len(self._dns_observations),
            "total_dns_observations": sum(len(v) for v in self._dns_observations.values()),
            "total_ip_addresses": len(self._ip_info),
            "total_asns": len(self._asn_info),
            "total_certificates": sum(len(v) for v in self._cert_observations.values()),
            "total_redirect_chains": len(self._redirect_chains),
            "total_tech_fingerprints": len(self._tech_fingerprints),
            "total_relationships": len(self._relationships),
            "attribution_edges": len([r for r in self._relationships if r.relationship_type in ATTRIBUTION_EDGES or (hasattr(r.relationship_type, 'value') and r.relationship_type.value in ATTRIBUTION_EDGES)]),
        }


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# The following are NOT available in Layer A:
#
# - Live DNS resolution (dig/nslookup against authoritative servers)
# - Authoritative DNS history (SecurityTrails, PassiveDNS)
# - IP history (BGP data, IP assignment history)
# - RDAP/WHOIS lookups (registrar data)
# - ASN and provider enrichment (BGP, MaxMind, IPinfo)
# - Live TLS certificate retrieval
# - Certificate Transparency log querying (crt.sh, Censys)
# - Live redirect execution (HTTP client following redirects)
# - Production technology fingerprinting (Wappalyzer, BuiltWith)
# - Production infrastructure correlation engine
# - Real-time infrastructure change monitoring
# - Distributed infrastructure scanning
# - GeoIP enrichment
# - Passive DNS correlation across providers
#
# All marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION

# GFIN Domain Intelligence — Modules 10/11/12
#
# Per Master Spec:
# §14 (Domain Intelligence): domain profile with RDAP, registrar, creation date,
#   nameservers, status, DNS, historical observations, certificates, related domains,
#   infrastructure clusters, fraud reports, campaigns, first/last seen.
#   Non-public info via official/legal mechanisms only.
# §15 (Certificate Intelligence): CT logs, certificates, SANs, domain relationships,
#   certificate timelines, related infrastructure, newly observed domains.
# §16 (IP/ASN Intelligence): current/historical IP, prefix, ASN, network, provider,
#   country, routing metadata, abuse contact, related domains.
#   Public/licensed/permitted sources only.
#
# Per GPT Luna: Build as extensions of Module 09 InfrastructureIntelligenceService.
# Domain Intelligence as aggregation/profile layer, Certificate + IP/ASN as extensions.

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from schemas.base import utc_now, Provenance
from services.infrastructure_intelligence import (
    InfrastructureIntelligenceService,
    DNSRecordType, DNSObservation,
    IPInfo, ASNInfo,
    CertificateObservation,
    InfraRelationship, InfraRelationType,
)


# ═══════════════════════════════════════════════
# DOMAIN PROFILE (§14)
# ═══════════════════════════════════════════════

class RDAPInfo(BaseModel):
    """RDAP/WHOIS registration information.

    Per spec: RDAP information, registrar, creation date, nameservers, status.
    Per spec: Non-public registration info via official/legal mechanisms only.

    Layer A: Mock data marked synthetic. Layer B: Live RDAP/WHOIS (REQUIRES EXTERNAL INFRASTRUCTURE).
    """
    domain: str
    registrar: str = ""
    creation_date: datetime | None = None
    expiration_date: datetime | None = None
    updated_date: datetime | None = None
    nameservers: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)  # e.g., ["clientTransferProhibited"]
    registrant_country: str = ""
    is_public_data: bool = True  # True = public RDAP, False = non-public (legal mechanism required)
    is_synthetic: bool = True
    source_id: str = "SRC-RDAP-MOCK"
    legal_basis: str = ""  # Required if is_public_data=False

    model_config = {"use_enum_values": True}


class DomainProfile(BaseModel):
    """Complete domain intelligence profile.

    Per §14: domain, RDAP, registrar, creation date, nameservers, status,
    DNS, historical observations, certificates, related domains, infrastructure
    clusters, fraud reports, campaigns, first/last seen.
    """
    domain: str
    rdap_info: RDAPInfo | None = None
    dns_records: dict[str, list[str]] = Field(default_factory=dict)  # type → values
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    historical_dns_count: int = 0
    certificates: list[CertificateObservation] = Field(default_factory=list)
    related_domains: list[str] = Field(default_factory=list)
    infrastructure_clusters: list[dict[str, Any]] = Field(default_factory=list)
    fraud_report_ids: list[str] = Field(default_factory=list)
    campaign_ids: list[str] = Field(default_factory=list)
    ip_addresses: list[str] = Field(default_factory=list)
    ip_info: list[IPInfo] = Field(default_factory=list)
    asn_info: list[ASNInfo] = Field(default_factory=list)
    relationships: list[InfraRelationship] = Field(default_factory=list)
    is_synthetic: bool = True

    model_config = {"use_enum_values": True}


class DomainIntelligenceService:
    """Domain intelligence service — Layer A.

    Builds on Module 09 InfrastructureIntelligenceService.
    Per Luna: Domain Intelligence as aggregation/profile layer.
    """

    def __init__(self, infra_service: InfrastructureIntelligenceService | None = None) -> None:
        self._infra = infra_service or InfrastructureIntelligenceService()
        self._rdap_info: dict[str, RDAPInfo] = {}
        self._domain_first_seen: dict[str, datetime] = {}
        self._domain_last_seen: dict[str, datetime] = {}
        self._related_domains: dict[str, list[str]] = {}
        self._infra_clusters: dict[str, list[dict[str, Any]]] = {}
        self._fraud_reports: dict[str, list[str]] = {}  # domain → [report_ids]
        self._campaign_links: dict[str, list[str]] = {}  # domain → [campaign_ids]

    def register_rdap_info(
        self, domain: str, registrar: str = "", creation_date: datetime | None = None,
        nameservers: list[str] | None = None, status: list[str] | None = None,
        is_public_data: bool = True, legal_basis: str = "",
    ) -> RDAPInfo:
        """Register RDAP/WHOIS info (mock fixture).

        Per spec: Non-public registration info via official/legal mechanisms only.
        """
        if not is_public_data and not legal_basis:
            raise ValueError("Non-public RDAP data requires legal_basis (official/legal mechanism)")

        info = RDAPInfo(
            domain=domain.lower(),
            registrar=registrar,
            creation_date=creation_date,
            nameservers=nameservers or [],
            status=status or [],
            is_public_data=is_public_data,
            legal_basis=legal_basis,
            is_synthetic=True,
        )
        self._rdap_info[domain.lower()] = info

        # Track first/last seen
        now = utc_now()
        d = domain.lower()
        if d not in self._domain_first_seen or (creation_date and creation_date < self._domain_first_seen[d]):
            self._domain_first_seen[d] = creation_date or now
        self._domain_last_seen[d] = now

        return info

    def add_related_domain(self, domain: str, related: str, bidirectional: bool = True) -> None:
        """Link two domains as related."""
        d = domain.lower()
        r = related.lower()
        if d not in self._related_domains:
            self._related_domains[d] = []
        if r not in self._related_domains[d]:
            self._related_domains[d].append(r)
        if bidirectional:
            if r not in self._related_domains:
                self._related_domains[r] = []
            if d not in self._related_domains[r]:
                self._related_domains[r].append(d)

    def add_infrastructure_cluster(self, domain: str, cluster: dict[str, Any]) -> None:
        """Associate an infrastructure cluster with a domain."""
        d = domain.lower()
        if d not in self._infra_clusters:
            self._infra_clusters[d] = []
        self._infra_clusters[d].append(cluster)

    def link_fraud_report(self, domain: str, report_id: str) -> None:
        """Link a fraud report to a domain."""
        d = domain.lower()
        if d not in self._fraud_reports:
            self._fraud_reports[d] = []
        self._fraud_reports[d].append(report_id)

    def link_campaign(self, domain: str, campaign_id: str) -> None:
        """Link a campaign to a domain."""
        d = domain.lower()
        if d not in self._campaign_links:
            self._campaign_links[d] = []
        self._campaign_links[d].append(campaign_id)

    def get_domain_profile(self, domain: str) -> DomainProfile:
        """Get a complete domain intelligence profile.

        Aggregates: RDAP, DNS, IP, ASN, certificates, related domains,
        infrastructure clusters, fraud reports, campaigns, first/last seen.
        """
        d = domain.lower()
        infra_profile = self._infra.get_domain_profile(d)

        return DomainProfile(
            domain=d,
            rdap_info=self._rdap_info.get(d),
            dns_records=infra_profile.get("dns_records", {}),
            first_seen=self._domain_first_seen.get(d),
            last_seen=self._domain_last_seen.get(d) or infra_profile.get("last_seen"),
            historical_dns_count=infra_profile.get("dns_history_count", 0),
            certificates=infra_profile.get("certificates", []),
            related_domains=self._related_domains.get(d, []),
            infrastructure_clusters=self._infra_clusters.get(d, []),
            fraud_report_ids=self._fraud_reports.get(d, []),
            campaign_ids=self._campaign_links.get(d, []),
            ip_addresses=infra_profile.get("ip_addresses", []),
            ip_info=infra_profile.get("ip_info", []),
            asn_info=infra_profile.get("asn_info", []),
            relationships=infra_profile.get("relationships", []),
            is_synthetic=True,
        )

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_domains": len(self._rdap_info),
            "total_related_domain_links": sum(len(v) for v in self._related_domains.values()),
            "total_infra_clusters": sum(len(v) for v in self._infra_clusters.values()),
            "total_fraud_report_links": sum(len(v) for v in self._fraud_reports.values()),
            "total_campaign_links": sum(len(v) for v in self._campaign_links.values()),
        }


# ═══════════════════════════════════════════════
# CERTIFICATE INTELLIGENCE (§15)
# ═══════════════════════════════════════════════

class CertificateIntelligenceService:
    """Certificate intelligence service — Layer A.

    Per §15: CT logs, certificates, SANs, domain relationships,
    certificate timelines, related infrastructure, newly observed domains.
    """

    def __init__(self, infra_service: InfrastructureIntelligenceService | None = None) -> None:
        self._infra = infra_service or InfrastructureIntelligenceService()
        self._cert_timeline: dict[str, list[CertificateObservation]] = {}  # domain → chronological certs
        self._newly_observed_domains: list[dict[str, Any]] = []
        self._san_index: dict[str, list[str]] = {}  # SAN domain → [certificate domains]

    def register_certificate(
        self, domain: str, issuer: str = "", subject: str = "",
        san_domains: list[str] | None = None,
        fingerprint: str = "",
        not_before: datetime | None = None,
        not_after: datetime | None = None,
        is_self_signed: bool = False,
    ) -> CertificateObservation:
        """Register a certificate observation and update intelligence."""
        cert = self._infra.register_certificate(
            domain,
            issuer=issuer,
            subject=subject,
            san_domains=san_domains or [],
            fingerprint=fingerprint,
            not_before=not_before,
            not_after=not_after,
            is_self_signed=is_self_signed,
        )

        d = domain.lower()
        if d not in self._cert_timeline:
            self._cert_timeline[d] = []
        self._cert_timeline[d].append(cert)

        # Index SANs
        for san in san_domains or []:
            san_lower = san.lower()
            
            # Check if newly observed BEFORE adding to index
            is_new = san_lower != d and not self._is_known_domain(san_lower)
            
            if san_lower not in self._san_index:
                self._san_index[san_lower] = []
            if d not in self._san_index[san_lower]:
                self._san_index[san_lower].append(d)

            # Track newly observed domains
            if is_new:
                self._newly_observed_domains.append({
                    "domain": san_lower,
                    "discovered_via": "certificate_san",
                    "certificate_domain": d,
                    "fingerprint": fingerprint,
                    "timestamp": utc_now(),
                })

        return cert

    def _is_known_domain(self, domain: str) -> bool:
        """Check if a domain is already known."""
        return (domain in self._cert_timeline or
                domain in self._san_index)

    def get_certificate_timeline(self, domain: str) -> list[CertificateObservation]:
        """Get chronological certificate timeline for a domain."""
        return sorted(
            self._cert_timeline.get(domain.lower(), []),
            key=lambda c: c.first_seen,
        )

    def get_domains_by_san(self, san_domain: str) -> list[str]:
        """Find which certificate domains share a SAN."""
        return list(self._san_index.get(san_domain.lower(), []))

    def get_newly_observed_domains(self, since: datetime | None = None) -> list[dict[str, Any]]:
        """Get newly observed domains from certificate SANs."""
        if since is None:
            return list(self._newly_observed_domains)
        return [d for d in self._newly_observed_domains if d["timestamp"] >= since]

    def get_certificate_relationships(self, domain: str) -> list[dict[str, Any]]:
        """Get certificate-based domain relationships for a domain."""
        relationships = []
        d = domain.lower()

        # Find domains sharing SANs with this domain
        for san, cert_domains in self._san_index.items():
            if d in cert_domains:
                for other in cert_domains:
                    if other != d:
                        relationships.append({
                            "domain": d,
                            "related_domain": other,
                            "shared_san": san,
                            "relationship_type": "shared_certificate_san",
                        })

        return relationships

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_certificates": sum(len(v) for v in self._cert_timeline.values()),
            "total_domains_with_certs": len(self._cert_timeline),
            "total_san_entries": len(self._san_index),
            "total_newly_observed": len(self._newly_observed_domains),
        }


# ═══════════════════════════════════════════════
# IP / ASN INTELLIGENCE (§16)
# ═══════════════════════════════════════════════

class IPASNIntelligenceService:
    """IP/ASN intelligence service — Layer A.

    Per §16: current/historical IP, prefix, ASN, network, provider,
    country, routing metadata, abuse contact, related domains.
    Public/licensed/permitted sources only.
    """

    def __init__(self, infra_service: InfrastructureIntelligenceService | None = None) -> None:
        self._infra = infra_service or InfrastructureIntelligenceService()
        self._ip_history: dict[str, list[IPInfo]] = {}  # IP → historical snapshots
        self._domain_ip_history: dict[str, list[str]] = {}  # domain → [IPs over time]
        self._abuse_contacts: dict[str, str] = {}  # ASN → abuse contact
        self._related_domains_by_ip: dict[str, list[str]] = {}  # IP → [domains]

    def register_ip_info(
        self, ip_address: str, asn: str = "", provider: str = "",
        country: str = "", network_name: str = "", network_cidr: str = "",
        is_cdn: bool = False, is_hosting_provider: bool = False,
        source_licensed: bool = True, source_type: str = "public",
    ) -> IPInfo:
        """Register IP info.

        Per spec: Use public, licensed, or otherwise permitted data sources only.
        """
        if not source_licensed:
            raise ValueError("IP/ASN data requires source_licensed=True (public/licensed/permitted only)")

        info = self._infra.register_ip_info(
            ip_address,
            asn=asn,
            provider=provider,
            country=country,
            network_name=network_name,
            network_cidr=network_cidr,
            is_cdn=is_cdn,
            is_hosting_provider=is_hosting_provider,
        )

        # Track history
        if ip_address not in self._ip_history:
            self._ip_history[ip_address] = []
        self._ip_history[ip_address].append(info)

        return info

    def register_asn_info(
        self, asn: str, organization: str = "", country: str = "",
        network_prefixes: list[str] | None = None,
        abuse_contact: str = "",
    ) -> ASNInfo:
        """Register ASN info with abuse contact."""
        info = self._infra.register_asn_info(
            asn,
            organization=organization,
            country=country,
            network_prefixes=network_prefixes or [],
        )

        if abuse_contact:
            self._abuse_contacts[asn] = abuse_contact

        return info

    def link_domain_ip(self, domain: str, ip_address: str) -> None:
        """Track which domains resolve to which IPs over time."""
        d = domain.lower()
        if d not in self._domain_ip_history:
            self._domain_ip_history[d] = []
        if ip_address not in self._domain_ip_history[d]:
            self._domain_ip_history[d].append(ip_address)

        if ip_address not in self._related_domains_by_ip:
            self._related_domains_by_ip[ip_address] = []
        if d not in self._related_domains_by_ip[ip_address]:
            self._related_domains_by_ip[ip_address].append(d)

    def get_ip_history(self, ip_address: str) -> list[IPInfo]:
        """Get historical snapshots for an IP address."""
        return list(self._ip_history.get(ip_address, []))

    def get_domain_ip_history(self, domain: str) -> list[str]:
        """Get IP history for a domain (all IPs it has resolved to)."""
        return list(self._domain_ip_history.get(domain.lower(), []))

    def get_related_domains_by_ip(self, ip_address: str) -> list[str]:
        """Get all domains that have resolved to an IP."""
        return list(self._related_domains_by_ip.get(ip_address, []))

    def get_abuse_contact(self, asn: str) -> str | None:
        """Get abuse contact for an ASN."""
        return self._abuse_contacts.get(asn)

    def get_ip_profile(self, ip_address: str) -> dict[str, Any]:
        """Get complete IP intelligence profile."""
        info = self._infra.get_ip_info(ip_address)
        history = self.get_ip_history(ip_address)
        related_domains = self.get_related_domains_by_ip(ip_address)
        abuse = None
        if info and info.asn:
            abuse = self.get_abuse_contact(info.asn)
        asn_info = None
        if info and info.asn:
            asn_info = self._infra.get_asn_info(info.asn)

        return {
            "ip_address": ip_address,
            "current_info": info,
            "history_count": len(history),
            "related_domains": related_domains,
            "asn_info": asn_info,
            "abuse_contact": abuse,
            "is_synthetic": True,
        }

    def get_asn_profile(self, asn: str) -> dict[str, Any]:
        """Get complete ASN intelligence profile."""
        info = self._infra.get_asn_info(asn)
        return {
            "asn": asn,
            "info": info,
            "abuse_contact": self.get_abuse_contact(asn),
            "is_synthetic": True,
        }

    def get_metrics(self) -> dict[str, Any]:
        return {
            "total_ips_tracked": len(self._ip_history),
            "total_domain_ip_links": sum(len(v) for v in self._domain_ip_history.values()),
            "total_asns": len(self._abuse_contacts),
            "total_ip_domain_links": sum(len(v) for v in self._related_domains_by_ip.values()),
        }


# ═══════════════════════════════════════════════
# PRODUCTION CAPABILITIES — REQUIRES EXTERNAL INFRASTRUCTURE
# ═══════════════════════════════════════════════
#
# Domain Intelligence (§14):
# - Live RDAP/WHOIS API integration
# - Non-public registration data via legal mechanisms
# - Real-time domain registration monitoring
# - Historical WHOIS data providers (DomainTools, WhoisXML)
#
# Certificate Intelligence (§15):
# - Live Certificate Transparency log querying (crt.sh, Censys)
# - Real-time certificate monitoring
# - CT log stream processing
#
# IP/ASN Intelligence (§16):
# - Live BGP/routing data
# - MaxMind/IPinfo GeoIP databases
# - Abuse contact databases (Spamhaus, RIR data)
# - Real-time IP/ASN change monitoring
# - Prefix/ASN correlation at scale
#
# All marked: REQUIRES EXTERNAL INFRASTRUCTURE / PRODUCTION VALIDATION

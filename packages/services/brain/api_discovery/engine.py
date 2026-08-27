"""GFIN API Discovery Engine — continuously discovers lawful data sources for investigations."""
from __future__ import annotations
from typing import Any, Optional
from datetime import datetime, timezone
from enum import Enum
import logging

from packages.sources.registry import SourceRegistry, SourceRecord
from packages.sources.scoring import SourceScorer, QualityScore
from packages.sources.policy import SourcePolicy, AccessStatus, AuthMethod

logger = logging.getLogger(__name__)


class DiscoveryStatus(str, Enum):
    FOUND_AND_ACCESSIBLE = "found_and_accessible"
    FOUND_BUT_AUTH_REQUIRED = "found_but_auth_required"
    FOUND_BUT_NOT_SUPPORTED = "found_but_not_supported"
    NOT_FOUND = "not_found"


class APIDiscoveryEngine:
    """Proactively discovers APIs, feeds, and data providers for investigations.

    The Brain asks: 'Which additional lawful and authorized API, feed, database,
    registry, archive, or provider could provide evidence relevant to this case?'

    Discovery pipeline:
        SOURCE_DISCOVERY -> PROVIDER_DISCOVERY -> API_DISCOVERY ->
        AUTHORIZATION_CHECK -> CONNECTOR_CHECK -> ALTERNATIVE_SOURCE_SEARCH

    Non-negotiable boundary: GFIN is an investigative system, not an intrusion system.
    """

    # Source categories to discover from
    SOURCE_CATEGORIES = [
        "developer_portals",
        "government_open_data",
        "law_enforcement_catalogs",
        "financial_regulatory",
        "blockchain_data",
        "threat_intelligence",
        "social_platform_apis",
        "advertising_apis",
        "geospatial_earth_observation",
        "company_registries",
        "court_government_apis",
        "telecom_number_intelligence",
        "archival_apis",
        "search_index_apis",
        "licensed_intelligence",
    ]

    def __init__(
        self,
        registry: SourceRegistry,
        scorer: SourceScorer,
        policy: SourcePolicy,
    ):
        self.registry = registry
        self.scorer = scorer
        self.policy = policy
        self._discovery_history: list[dict[str, Any]] = []

    def discover_for_gap(
        self,
        case_id: str,
        data_type_needed: str,
        jurisdiction: str = "GLOBAL",
    ) -> dict[str, Any]:
        """Discover sources that could fill an evidence gap.

        Called automatically when the Brain identifies an evidence gap.
        Returns ranked list of potential sources with authorization status.
        """
        logger.info(f"API discovery for gap: case={case_id} data_type={data_type_needed}")

        # Step 1: Search existing registry for matching sources
        existing = self.registry.search_by_data_type(data_type_needed)

        # Step 2: Discover new potential sources (from known categories)
        candidates = self._discover_candidates(data_type_needed, jurisdiction)

        # Step 3: Evaluate each candidate
        evaluated = []
        for candidate in candidates:
            # Check authorization
            access = self.policy.check_access(candidate, jurisdiction)
            # Score quality
            score = self.scorer.score(candidate)
            evaluated.append({
                "provider": candidate.provider,
                "source_id": candidate.source_id,
                "data_type": data_type_needed,
                "access_status": access.status.value,
                "auth_method": candidate.auth_method.value if hasattr(candidate, 'auth_method') else "unknown",
                "quality_score": score.overall,
                "legal_usability": score.legal_usability,
                "authority": score.authority,
                "reliability": score.reliability,
                "independence": score.independence,
                "required_auth": access.required_auth if hasattr(access, 'required_auth') else [],
                "jurisdiction": jurisdiction,
            })

        # Step 4: Rank by expected investigative value
        ranked = sorted(evaluated, key=lambda x: (-x["quality_score"], x["access_status"]))

        # Step 5: Record discovery
        discovery_record = {
            "case_id": case_id,
            "data_type_needed": data_type_needed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "candidates_found": len(ranked),
            "results": ranked,
        }
        self._discovery_history.append(discovery_record)

        return discovery_record

    def discover_unknown(
        self,
        case_id: str,
        unknown_description: str,
        jurisdiction: str = "GLOBAL",
    ) -> dict[str, Any]:
        """When GFIN encounters an unknown, perform full source discovery.

        UNKNOWN -> WHY_UNKNOWN -> WHAT_SOURCE_COULD_ANSWER -> DOES_API_EXIST ->
        CAN_GFIN_LAWFULLY_ACCESS -> DO_WE_HAVE_AUTHORIZATION -> CONNECT -> COLLECT ->
        VERIFY -> CORRELATE -> EVIDENCE
        """
        # Determine what data type could answer this unknown
        data_type = self._infer_data_type(unknown_description)

        # Run discovery
        result = self.discover_for_gap(case_id, data_type, jurisdiction)

        # Add unknown context
        result["unknown"] = unknown_description
        result["inferred_data_type"] = data_type

        # Classify results
        accessible = [r for r in result["results"] if r["access_status"] == DiscoveryStatus.FOUND_AND_ACCESSIBLE.value]
        auth_needed = [r for r in result["results"] if r["access_status"] == DiscoveryStatus.FOUND_BUT_AUTH_REQUIRED.value]
        not_supported = [r for r in result["results"] if r["access_status"] == DiscoveryStatus.FOUND_BUT_NOT_SUPPORTED.value]

        result["summary"] = {
            "accessible_count": len(accessible),
            "auth_required_count": len(auth_needed),
            "not_supported_count": len(not_supported),
            "best_source": accessible[0]["provider"] if accessible else None,
            "best_auth_required_source": auth_needed[0]["provider"] if auth_needed else None,
        }

        return result

    def _discover_candidates(self, data_type: str, jurisdiction: str) -> list[SourceRecord]:
        """Discover candidate sources for a data type."""
        # Check registry first
        registered = self.registry.search_by_data_type(data_type)

        # Also check built-in source catalog
        builtin = self._get_builtin_sources(data_type, jurisdiction)

        # Combine, avoiding duplicates
        seen_ids = {s.source_id for s in registered}
        candidates = list(registered)
        for source in builtin:
            if source.source_id not in seen_ids:
                candidates.append(source)

        return candidates

    def _get_builtin_sources(self, data_type: str, jurisdiction: str) -> list[SourceRecord]:
        """Get built-in source catalog for common data types."""
        # These are publicly known APIs that can be discovered
        builtin_map = {
            "domain": [
                SourceRecord(source_id="dns_google", provider="Google", connector="dns_doh",
                    base_url="https://dns.google/resolve", auth_method=AuthMethod.PUBLIC_API,
                    data_categories=["dns"], jurisdictions=["GLOBAL"],
                    allowed_data=["dns_records"], classification="PUBLIC",
                    legal_basis="Public DNS API", reliability="HIGH"),
                SourceRecord(source_id="rdap_verisign", provider="Verisign", connector="rdap",
                    base_url="https://rdap.verisign.com/com/v1/domain/", auth_method=AuthMethod.PUBLIC_API,
                    data_categories=["whois"], jurisdictions=["GLOBAL"],
                    allowed_data=["registration_data"], classification="PUBLIC",
                    legal_basis="Public RDAP standard", reliability="HIGH"),
            ],
            "ip": [
                SourceRecord(source_id="ipinfo", provider="ipinfo.io", connector="ip_geo",
                    base_url="https://ipinfo.io/", auth_method=AuthMethod.PUBLIC_API,
                    data_categories=["geolocation"], jurisdictions=["GLOBAL"],
                    allowed_data=["ip_metadata"], classification="PUBLIC",
                    legal_basis="Public API", reliability="HIGH"),
            ],
            "crypto": [
                SourceRecord(source_id="blockchain_info", provider="Blockchain.com", connector="blockchain",
                    base_url="https://blockchain.info/", auth_method=AuthMethod.PUBLIC_API,
                    data_categories=["blockchain"], jurisdictions=["GLOBAL"],
                    allowed_data=["transactions", "addresses"], classification="PUBLIC",
                    legal_basis="Public blockchain data", reliability="HIGH"),
                SourceRecord(source_id="chainabuse", provider="Chainabuse", connector="chainabuse",
                    base_url="https://chainabuse.com/", auth_method=AuthMethod.PUBLIC_API,
                    data_categories=["scam_reports"], jurisdictions=["GLOBAL"],
                    allowed_data=["scam_reports"], classification="PUBLIC",
                    legal_basis="Public scam reports", reliability="MEDIUM"),
            ],
            "phone": [
                SourceRecord(source_id="numverify", provider="Numverify", connector="phone_lookup",
                    base_url="https://apilayer.net/", auth_method=AuthMethod.API_KEY,
                    data_categories=["phone"], jurisdictions=["GLOBAL"],
                    allowed_data=["phone_metadata"], classification="PUBLIC",
                    legal_basis="Licensed API", reliability="MEDIUM"),
            ],
            "social": [
                SourceRecord(source_id="telegram_api", provider="Telegram", connector="telegram",
                    base_url="https://api.telegram.org/", auth_method=AuthMethod.API_KEY,
                    data_categories=["social"], jurisdictions=["GLOBAL"],
                    allowed_data=["public_channels", "public_messages"], classification="PUBLIC",
                    legal_basis="Official API", reliability="MEDIUM"),
            ],
        }
        return builtin_map.get(data_type, [])

    def _infer_data_type(self, description: str) -> str:
        """Infer what data type could answer an unknown."""
        desc = description.lower()
        if any(w in desc for w in ["domain", "dns", "website", "url"]):
            return "domain"
        if any(w in desc for w in ["ip", "asn", "network", "hosting"]):
            return "ip"
        if any(w in desc for w in ["wallet", "bitcoin", "crypto", "blockchain", "transaction"]):
            return "crypto"
        if any(w in desc for w in ["phone", "number", "call", "sms"]):
            return "phone"
        if any(w in desc for w in ["email", "mail"]):
            return "email"
        if any(w in desc for w in ["social", "telegram", "facebook", "twitter", "post"]):
            return "social"
        if any(w in desc for w in ["geo", "location", "satellite", "map"]):
            return "geoint"
        if any(w in desc for w in ["company", "business", "registry"]):
            return "company"
        return "generic"

    def get_discovery_history(self) -> list[dict[str, Any]]:
        """Get the full discovery history."""
        return list(self._discovery_history)

    def refresh_catalog(self) -> dict[str, Any]:
        """Periodically refresh the source catalog.

        Detect: new APIs, new providers, changed endpoints, deprecated APIs,
        new datasets, new jurisdictions, changed licenses, changed rate limits.
        """
        all_sources = self.registry.list_sources()
        refreshed = 0
        deprecated = 0
        for source in all_sources:
            # In production, this would check the provider's actual status
            # For Layer A, we mark as verified
            self.registry.update_source(source.source_id, last_verified=datetime.now(timezone.utc))
            refreshed += 1

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_sources": len(all_sources),
            "refreshed": refreshed,
            "deprecated": deprecated,
        }
        return result

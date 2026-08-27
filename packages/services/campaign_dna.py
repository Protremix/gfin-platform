"""GFIN Campaign DNA Engine — Module for Campaign Feature Extraction & DNA Matching.

Identifies recurring characteristics of fraud campaigns and generates CampaignSignatures
from extracted campaign features. Evaluates pattern similarity across campaigns without
treating similarity as ground-truth proof (Constitution §22).

All outputs are marked UNVERIFIED by default.
No external dependencies beyond standard library.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

DEFAULT_LIMITATIONS = [
    "DNA similarity indicates pattern resemblance, not definitive common ownership or causality.",
    "Ground truth human analyst verification is required before final attribution.",
    "Shared public infrastructure (e.g. CDNs, shared hosting, public registrars) may cause false similarity."
]


@dataclass
class CampaignSignature:
    """Dataclass representing a fraud campaign's structural DNA signature."""

    id: str
    campaign_id: str
    features: dict[str, Any] = field(default_factory=dict)
    feature_hash: str = ""
    similarity_threshold: float = 0.7
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    confidence: float = 0.0
    verification_status: str = "UNVERIFIED"
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_LIMITATIONS))

    def to_dict(self) -> dict[str, Any]:
        """Convert signature to dictionary format."""
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "features": self.features,
            "feature_hash": self.feature_hash,
            "similarity_threshold": self.similarity_threshold,
            "created_at": self.created_at,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "limitations": self.limitations,
        }


class CampaignDNAEngine:
    """Engine for extracting DNA features, generating signatures, and comparing campaign DNA."""

    FEATURE_CATEGORIES = [
        "language",
        "phrasing",
        "website_structure",
        "domain_patterns",
        "phone_patterns",
        "email_patterns",
        "hosting_patterns",
        "certificate_reuse",
        "dns_patterns",
        "payment_destinations",
        "wallet_relationships",
        "timing",
        "infrastructure",
        "geography",
        "victim_reports",
    ]

    def _get_val(self, obj: Any, keys: list[str], default: Any = None) -> Any:
        """Helper to safely extract a field from dict or object across key aliases."""
        if obj is None:
            return default
        for key in keys:
            if isinstance(obj, dict):
                if key in obj and obj[key] is not None:
                    return obj[key]
            else:
                if hasattr(obj, key) and getattr(obj, key) is not None:
                    return getattr(obj, key)
        return default

    def extract_features(self, campaign: Any) -> dict[str, Any]:
        """Extract all 15 feature categories from a campaign object or dictionary."""
        extracted: dict[str, Any] = {}

        # If campaign already has a nested 'features' dict, start with it
        existing_features = self._get_val(campaign, ["features"], {})
        if not isinstance(existing_features, dict):
            existing_features = {}

        # 1. language
        lang_val = self._get_val(campaign, ["language", "languages", "lang"], existing_features.get("language", []))
        if isinstance(lang_val, str):
            extracted["language"] = [lang_val.strip().lower()] if lang_val.strip() else []
        elif isinstance(lang_val, (list, set, tuple)):
            extracted["language"] = sorted({str(x).strip().lower() for x in lang_val if x})
        else:
            extracted["language"] = []

        # 2. phrasing
        phrase_val = self._get_val(campaign, ["phrasing", "phrases", "slogans", "text_snippets"], existing_features.get("phrasing", []))
        if isinstance(phrase_val, str):
            extracted["phrasing"] = [phrase_val.strip()] if phrase_val.strip() else []
        elif isinstance(phrase_val, (list, set, tuple)):
            extracted["phrasing"] = sorted({str(x).strip() for x in phrase_val if x})
        else:
            extracted["phrasing"] = []

        # 3. website_structure
        web_val = self._get_val(campaign, ["website_structure", "site_structure", "dom_patterns", "template"], existing_features.get("website_structure", []))
        if isinstance(web_val, str):
            extracted["website_structure"] = [web_val.strip()] if web_val.strip() else []
        elif isinstance(web_val, (list, set, tuple)):
            extracted["website_structure"] = sorted({str(x).strip() for x in web_val if x})
        elif isinstance(web_val, dict):
            extracted["website_structure"] = [f"{k}:{v}" for k, v in sorted(web_val.items())]
        else:
            extracted["website_structure"] = []

        # 4. domain_patterns
        dom_val = self._get_val(campaign, ["domain_patterns", "domains", "domain_list"], existing_features.get("domain_patterns", []))
        if isinstance(dom_val, str):
            extracted["domain_patterns"] = [dom_val.strip().lower()] if dom_val.strip() else []
        elif isinstance(dom_val, (list, set, tuple)):
            extracted["domain_patterns"] = sorted({str(x).strip().lower() for x in dom_val if x})
        else:
            extracted["domain_patterns"] = []

        # 5. phone_patterns
        phone_val = self._get_val(campaign, ["phone_patterns", "phones", "phone_numbers"], existing_features.get("phone_patterns", []))
        if isinstance(phone_val, str):
            extracted["phone_patterns"] = [phone_val.strip()] if phone_val.strip() else []
        elif isinstance(phone_val, (list, set, tuple)):
            extracted["phone_patterns"] = sorted({str(x).strip() for x in phone_val if x})
        else:
            extracted["phone_patterns"] = []

        # 6. email_patterns
        email_val = self._get_val(campaign, ["email_patterns", "emails", "email_addresses"], existing_features.get("email_patterns", []))
        if isinstance(email_val, str):
            extracted["email_patterns"] = [email_val.strip().lower()] if email_val.strip() else []
        elif isinstance(email_val, (list, set, tuple)):
            extracted["email_patterns"] = sorted({str(x).strip().lower() for x in email_val if x})
        else:
            extracted["email_patterns"] = []

        # 7. hosting_patterns
        host_val = self._get_val(campaign, ["hosting_patterns", "hosting", "hosters", "asn_list"], existing_features.get("hosting_patterns", []))
        if isinstance(host_val, str):
            extracted["hosting_patterns"] = [host_val.strip()] if host_val.strip() else []
        elif isinstance(host_val, (list, set, tuple)):
            extracted["hosting_patterns"] = sorted({str(x).strip() for x in host_val if x})
        else:
            extracted["hosting_patterns"] = []

        # 8. certificate_reuse
        cert_val = self._get_val(campaign, ["certificate_reuse", "certificates", "certs", "ssl_certs"], existing_features.get("certificate_reuse", []))
        if isinstance(cert_val, str):
            extracted["certificate_reuse"] = [cert_val.strip()] if cert_val.strip() else []
        elif isinstance(cert_val, (list, set, tuple)):
            extracted["certificate_reuse"] = sorted({str(x).strip() for x in cert_val if x})
        else:
            extracted["certificate_reuse"] = []

        # 9. dns_patterns
        dns_val = self._get_val(campaign, ["dns_patterns", "dns", "nameservers"], existing_features.get("dns_patterns", []))
        if isinstance(dns_val, str):
            extracted["dns_patterns"] = [dns_val.strip().lower()] if dns_val.strip() else []
        elif isinstance(dns_val, (list, set, tuple)):
            extracted["dns_patterns"] = sorted({str(x).strip().lower() for x in dns_val if x})
        else:
            extracted["dns_patterns"] = []

        # 10. payment_destinations
        pay_val = self._get_val(campaign, ["payment_destinations", "payments", "ibans", "bank_accounts"], existing_features.get("payment_destinations", []))
        if isinstance(pay_val, str):
            extracted["payment_destinations"] = [pay_val.strip()] if pay_val.strip() else []
        elif isinstance(pay_val, (list, set, tuple)):
            extracted["payment_destinations"] = sorted({str(x).strip() for x in pay_val if x})
        else:
            extracted["payment_destinations"] = []

        # 11. wallet_relationships
        wallet_val = self._get_val(campaign, ["wallet_relationships", "wallets", "crypto_addresses"], existing_features.get("wallet_relationships", []))
        if isinstance(wallet_val, str):
            extracted["wallet_relationships"] = [wallet_val.strip()] if wallet_val.strip() else []
        elif isinstance(wallet_val, (list, set, tuple)):
            extracted["wallet_relationships"] = sorted({str(x).strip() for x in wallet_val if x})
        else:
            extracted["wallet_relationships"] = []

        # 12. timing
        time_val = self._get_val(campaign, ["timing", "timestamps", "cadence"], existing_features.get("timing", []))
        if isinstance(time_val, str):
            extracted["timing"] = [time_val.strip()] if time_val.strip() else []
        elif isinstance(time_val, (list, set, tuple)):
            extracted["timing"] = sorted({str(x).strip() for x in time_val if x})
        elif isinstance(time_val, dict):
            extracted["timing"] = [f"{k}:{v}" for k, v in sorted(time_val.items())]
        else:
            extracted["timing"] = []

        # 13. infrastructure
        infra_val = self._get_val(campaign, ["infrastructure", "ips", "ip_addresses", "servers"], existing_features.get("infrastructure", []))
        if isinstance(infra_val, str):
            extracted["infrastructure"] = [infra_val.strip()] if infra_val.strip() else []
        elif isinstance(infra_val, (list, set, tuple)):
            extracted["infrastructure"] = sorted({str(x).strip() for x in infra_val if x})
        else:
            extracted["infrastructure"] = []

        # 14. geography
        geo_val = self._get_val(campaign, ["geography", "countries", "regions", "target_countries"], existing_features.get("geography", []))
        if isinstance(geo_val, str):
            extracted["geography"] = [geo_val.strip().upper()] if geo_val.strip() else []
        elif isinstance(geo_val, (list, set, tuple)):
            extracted["geography"] = sorted({str(x).strip().upper() for x in geo_val if x})
        else:
            extracted["geography"] = []

        # 15. victim_reports
        rep_val = self._get_val(campaign, ["victim_reports", "reports", "report_ids"], existing_features.get("victim_reports", []))
        if isinstance(rep_val, str):
            extracted["victim_reports"] = [rep_val.strip()] if rep_val.strip() else []
        elif isinstance(rep_val, (list, set, tuple)):
            extracted["victim_reports"] = sorted({str(x).strip() for x in rep_val if x})
        elif isinstance(rep_val, (int, float)):
            extracted["victim_reports"] = [f"count:{rep_val}"]
        else:
            extracted["victim_reports"] = []

        return extracted

    def generate_signature(self, campaign: Any, similarity_threshold: float = 0.7) -> CampaignSignature:
        """Create a CampaignSignature from extracted campaign features."""
        campaign_id = str(self._get_val(campaign, ["campaign_id", "id", "name"], "unknown_campaign"))
        features = self.extract_features(campaign)

        # Canonical JSON string for hash stability
        canonical_json = json.dumps(features, sort_keys=True)
        feature_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # Calculate confidence score based on feature density
        non_empty_count = sum(1 for v in features.values() if v)
        confidence = round(min(1.0, non_empty_count / len(self.FEATURE_CATEGORIES)), 4)

        sig_id = f"sig_{feature_hash[:16]}"
        created_at = datetime.now(UTC).isoformat()

        return CampaignSignature(
            id=sig_id,
            campaign_id=campaign_id,
            features=features,
            feature_hash=feature_hash,
            similarity_threshold=similarity_threshold,
            created_at=created_at,
            confidence=confidence,
            verification_status="UNVERIFIED",
            limitations=list(DEFAULT_LIMITATIONS),
        )

    def _jaccard_similarity(self, set_a: set, set_b: set) -> float:
        """Compute Jaccard index between two sets."""
        if not set_a and not set_b:
            return 0.0
        union_size = len(set_a.union(set_b))
        if union_size == 0:
            return 0.0
        intersection_size = len(set_a.intersection(set_b))
        return intersection_size / union_size

    def compute_similarity(
        self,
        sig_a: CampaignSignature | dict,
        sig_b: CampaignSignature | dict
    ) -> float:
        """Compare two signatures and return a similarity score between 0.0 and 1.0."""
        feat_a = sig_a.features if isinstance(sig_a, CampaignSignature) else (sig_a.get("features", {}) if isinstance(sig_a, dict) else {})
        feat_b = sig_b.features if isinstance(sig_b, CampaignSignature) else (sig_b.get("features", {}) if isinstance(sig_b, dict) else {})

        # Hash fast path
        hash_a = getattr(sig_a, "feature_hash", "") if isinstance(sig_a, CampaignSignature) else sig_a.get("feature_hash", "")
        hash_b = getattr(sig_b, "feature_hash", "") if isinstance(sig_b, CampaignSignature) else sig_b.get("feature_hash", "")
        if hash_a and hash_b and hash_a == hash_b:
            return 1.0

        cat_scores: list[float] = []
        active_categories = 0

        for cat in self.FEATURE_CATEGORIES:
            val_a = feat_a.get(cat, [])
            val_b = feat_b.get(cat, [])

            set_a = set(val_a) if isinstance(val_a, list) else ({str(val_a)} if val_a else set())
            set_b = set(val_b) if isinstance(val_b, list) else ({str(val_b)} if val_b else set())

            if not set_a and not set_b:
                continue

            active_categories += 1
            cat_sim = self._jaccard_similarity(set_a, set_b)
            cat_scores.append(cat_sim)

        if active_categories == 0:
            return 0.0

        avg_score = sum(cat_scores) / active_categories
        return round(float(avg_score), 4)

    def find_similar_campaigns(
        self,
        campaign_id: str,
        all_campaigns: list | dict,
        threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Find campaigns with DNA similarity greater than or equal to threshold."""
        # Convert all_campaigns into a lookup map of id -> signature
        sig_map: dict[str, CampaignSignature] = {}

        if isinstance(all_campaigns, dict):
            items = list(all_campaigns.items())
        else:
            items = [(self._get_val(c, ["campaign_id", "id"], str(idx)), c) for idx, c in enumerate(all_campaigns)]

        for key, item in items:
            if isinstance(item, CampaignSignature):
                sig_map[item.campaign_id] = item
            elif isinstance(item, dict) and "features" in item and "feature_hash" in item:
                sig_map[item.get("campaign_id", key)] = CampaignSignature(
                    id=item.get("id", f"sig_{key}"),
                    campaign_id=item.get("campaign_id", key),
                    features=item.get("features", {}),
                    feature_hash=item.get("feature_hash", ""),
                    similarity_threshold=item.get("similarity_threshold", threshold),
                    created_at=item.get("created_at", ""),
                    confidence=item.get("confidence", 0.0),
                    verification_status=item.get("verification_status", "UNVERIFIED"),
                )
            else:
                sig = self.generate_signature(item, similarity_threshold=threshold)
                sig_map[sig.campaign_id] = sig

        target_sig = sig_map.get(campaign_id)
        if not target_sig:
            return []

        results = []
        for cid, other_sig in sig_map.items():
            if cid == campaign_id:
                continue
            sim = self.compute_similarity(target_sig, other_sig)
            if sim >= threshold:
                explanation = self.explain_similarity(target_sig, other_sig)
                results.append({
                    "campaign_id": cid,
                    "similarity": sim,
                    "signature": other_sig,
                    "matching_features": explanation["matching_features"],
                    "differing_features": explanation["differing_features"],
                    "confidence": explanation["confidence"],
                    "limitations": explanation["limitations"],
                    "verification_status": "UNVERIFIED",
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def explain_similarity(
        self,
        sig_a: CampaignSignature | dict,
        sig_b: CampaignSignature | dict
    ) -> dict[str, Any]:
        """Return structured explanation of similarity between two campaign signatures."""
        sim = self.compute_similarity(sig_a, sig_b)

        feat_a = sig_a.features if isinstance(sig_a, CampaignSignature) else (sig_a.get("features", {}) if isinstance(sig_a, dict) else {})
        feat_b = sig_b.features if isinstance(sig_b, CampaignSignature) else (sig_b.get("features", {}) if isinstance(sig_b, dict) else {})

        matching_features: dict[str, list[Any]] = {}
        differing_features: dict[str, dict[str, list[Any]]] = {}
        features_breakdown: dict[str, float] = {}
        evidence: dict[str, Any] = {"matches": [], "differences": []}

        for cat in self.FEATURE_CATEGORIES:
            val_a = set(feat_a.get(cat, [])) if isinstance(feat_a.get(cat), list) else ({feat_a[cat]} if feat_a.get(cat) else set())
            val_b = set(feat_b.get(cat, [])) if isinstance(feat_b.get(cat), list) else ({feat_b[cat]} if feat_b.get(cat) else set())

            if not val_a and not val_b:
                continue

            intersection = sorted(val_a.intersection(val_b))
            diff_a = sorted(val_a.difference(val_b))
            diff_b = sorted(val_b.difference(val_a))

            cat_sim = self._jaccard_similarity(val_a, val_b)
            features_breakdown[cat] = round(cat_sim, 4)

            if intersection:
                matching_features[cat] = intersection
                evidence["matches"].append({"category": cat, "shared_elements": intersection})
            if diff_a or diff_b:
                differing_features[cat] = {"sig_a_only": diff_a, "sig_b_only": diff_b}
                evidence["differences"].append({"category": cat, "sig_a_only": diff_a, "sig_b_only": diff_b})

        conf_a = getattr(sig_a, "confidence", 0.5) if isinstance(sig_a, CampaignSignature) else sig_a.get("confidence", 0.5)
        conf_b = getattr(sig_b, "confidence", 0.5) if isinstance(sig_b, CampaignSignature) else sig_b.get("confidence", 0.5)
        combined_confidence = round(min(1.0, float((conf_a + conf_b) / 2.0) * (0.5 + 0.5 * sim)), 4)

        explanation = {
            "similarity": sim,
            "matching_features": matching_features,
            "differing_features": differing_features,
            "confidence": combined_confidence,
            "limitations": list(DEFAULT_LIMITATIONS),
            "verification_status": "UNVERIFIED",
            "evidence": evidence,
            "features": features_breakdown,
            # Uppercase aliases for directive requirements
            "SIMILARITY": sim,
            "EVIDENCE": evidence,
            "FEATURES": features_breakdown,
            "CONFIDENCE": combined_confidence,
            "LIMITATIONS": list(DEFAULT_LIMITATIONS),
        }

        return explanation

"""GFIN Fraud Pattern Engine — Module for Fraud Network Detection.

Detects combinations of fraud indicators across entities that form potential fraud networks.
Evaluates shared infrastructure, content similarity, payment correlations, contact reuse,
and multi-dimensional infrastructure clusters.

All outputs are probabilistic and marked UNVERIFIED pending ground-truth analyst verification.
No external dependencies beyond standard library.
"""

import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

DEFAULT_PATTERN_LIMITATIONS = [
    "Fraud pattern detection is probabilistic and derived from correlated observables.",
    "Shared infrastructure (IP, hosting, registrar) or contacts do not prove joint control.",
    "Outputs are marked UNVERIFIED until validated by ground-truth evidence."
]


@dataclass
class FraudPattern:
    """Dataclass representing a detected fraud pattern or correlation."""

    id: str
    pattern_type: str
    entities: list[Any] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    limitations: list[str] = field(default_factory=lambda: list(DEFAULT_PATTERN_LIMITATIONS))
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    verification_status: str = "UNVERIFIED"
    features: dict[str, Any] = field(default_factory=dict)
    similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern to dictionary format."""
        return {
            "id": self.id,
            "pattern_type": self.pattern_type,
            "entities": self.entities,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "limitations": self.limitations,
            "detected_at": self.detected_at,
            "verification_status": self.verification_status,
            "features": self.features,
            "similarity": self.similarity,
        }


class PatternEngine:
    """Engine for detecting fraud patterns, correlations, and potential fraud networks across entities."""

    def _get_val(self, obj: Any, keys: list[str], default: Any = None) -> Any:
        """Safely extract field value from dict or dataclass/object across alias keys."""
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

    def _get_entity_id(self, entity: Any) -> str:
        """Get identifier for an entity."""
        return str(self._get_val(entity, ["id", "entity_id", "domain", "name", "url"], f"entity_{id(entity)}"))

    def _extract_list(self, entity: Any, keys: list[str]) -> list[str]:
        """Extract a list of clean normalized string indicators from an entity."""
        val = self._get_val(entity, keys, [])
        if isinstance(val, str):
            return [val.strip()] if val.strip() else []
        elif isinstance(val, (list, set, tuple)):
            return sorted({str(x).strip() for x in val if x})
        return []

    def detect_shared_infrastructure(self, entities: list[Any]) -> list[FraudPattern]:
        """Detect multiple domains/entities sharing IP, ASN, SSL certificate, or DNS."""
        if not entities or len(entities) < 2:
            return []

        # Maps indicator_type:value -> list of entity_ids
        shared_map: dict[str, list[str]] = defaultdict(list)

        for entity in entities:
            eid = self._get_entity_id(entity)
            ips = self._extract_list(entity, ["ip", "ips", "ip_address", "ip_addresses"])
            asns = self._extract_list(entity, ["asn", "asns", "asn_number"])
            certs = self._extract_list(entity, ["cert", "certs", "ssl_cert", "certificate", "cert_hash"])
            dns = self._extract_list(entity, ["dns", "nameserver", "nameservers", "ns"])

            for ip in ips:
                shared_map[f"ip:{ip}"].append(eid)
            for asn in asns:
                shared_map[f"asn:{asn}"].append(eid)
            for cert in certs:
                shared_map[f"cert:{cert}"].append(eid)
            for ns in dns:
                shared_map[f"dns:{ns}"].append(eid)

        patterns: list[FraudPattern] = []
        for key, eids in shared_map.items():
            unique_eids = sorted(set(eids))
            if len(unique_eids) > 1:
                kind, val = key.split(":", 1)
                pat_id = f"pat_infra_{hashlib.sha256(key.encode()).hexdigest()[:10]}"
                confidence = 0.85 if kind in ("ip", "cert") else 0.60
                pattern = FraudPattern(
                    id=pat_id,
                    pattern_type="SHARED_INFRASTRUCTURE",
                    entities=unique_eids,
                    evidence={
                        "indicator_type": kind,
                        "shared_value": val,
                        "entity_count": len(unique_eids),
                        "shared_entities": unique_eids,
                    },
                    confidence=confidence,
                    limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                    verification_status="UNVERIFIED",
                    features={"indicator_type": kind, "shared_value": val},
                    similarity=round(len(unique_eids) / len(entities), 4),
                )
                patterns.append(pattern)

        return patterns

    def detect_similar_content(self, entities: list[Any]) -> list[FraudPattern]:
        """Detect similar website text, HTML structure, or page template across entities."""
        if not entities or len(entities) < 2:
            return []

        shared_map: dict[str, list[str]] = defaultdict(list)
        entity_texts: dict[str, str] = {}

        for entity in entities:
            eid = self._get_entity_id(entity)
            tmpl = self._extract_list(entity, ["template", "template_id", "html_hash", "structure_hash"])
            text = self._get_val(entity, ["content", "text", "body_text", "website_text"], "")

            for t in tmpl:
                shared_map[f"template:{t}"].append(eid)

            if isinstance(text, str) and len(text.strip()) > 20:
                entity_texts[eid] = text.strip().lower()

        patterns: list[FraudPattern] = []

        # Template match patterns
        for key, eids in shared_map.items():
            unique_eids = sorted(set(eids))
            if len(unique_eids) > 1:
                _, val = key.split(":", 1)
                pat_id = f"pat_content_{hashlib.sha256(key.encode()).hexdigest()[:10]}"
                patterns.append(
                    FraudPattern(
                        id=pat_id,
                        pattern_type="SIMILAR_CONTENT",
                        entities=unique_eids,
                        evidence={"match_type": "template_hash", "shared_template": val, "shared_entities": unique_eids},
                        confidence=0.80,
                        limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                        verification_status="UNVERIFIED",
                        features={"match_type": "template_hash", "template": val},
                        similarity=round(len(unique_eids) / len(entities), 4),
                    )
                )

        # Pairwise text similarity
        eids_with_text = list(entity_texts.keys())
        for i in range(len(eids_with_text)):
            for j in range(i + 1, len(eids_with_text)):
                eid1, eid2 = eids_with_text[i], eids_with_text[j]
                t1, t2 = set(entity_texts[eid1].split()), set(entity_texts[eid2].split())
                if not t1 or not t2:
                    continue
                jaccard = len(t1.intersection(t2)) / len(t1.union(t2))
                if jaccard >= 0.5:
                    pat_id = f"pat_text_{hashlib.sha256(f'{eid1}:{eid2}'.encode()).hexdigest()[:10]}"
                    patterns.append(
                        FraudPattern(
                            id=pat_id,
                            pattern_type="SIMILAR_CONTENT",
                            entities=[eid1, eid2],
                            evidence={
                                "match_type": "text_jaccard",
                                "jaccard_similarity": round(jaccard, 4),
                                "shared_entities": [eid1, eid2],
                            },
                            confidence=round(0.70 + 0.25 * jaccard, 4),
                            limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                            verification_status="UNVERIFIED",
                            features={"text_similarity": round(jaccard, 4)},
                            similarity=round(jaccard, 4),
                        )
                    )

        return patterns

    def detect_payment_correlation(self, entities: list[Any]) -> list[FraudPattern]:
        """Detect same payment destination or crypto wallet across entities."""
        if not entities or len(entities) < 2:
            return []

        shared_map: dict[str, list[str]] = defaultdict(list)

        for entity in entities:
            eid = self._get_entity_id(entity)
            ibans = self._extract_list(entity, ["iban", "ibans", "bank_account", "bank_accounts", "payment_destinations"])
            wallets = self._extract_list(entity, ["wallet", "wallets", "crypto_address", "crypto_addresses"])

            for iban in ibans:
                shared_map[f"iban:{iban}"].append(eid)
            for wallet in wallets:
                shared_map[f"wallet:{wallet}"].append(eid)

        patterns: list[FraudPattern] = []
        for key, eids in shared_map.items():
            unique_eids = sorted(set(eids))
            if len(unique_eids) > 1:
                kind, val = key.split(":", 1)
                pat_id = f"pat_pay_{hashlib.sha256(key.encode()).hexdigest()[:10]}"
                patterns.append(
                    FraudPattern(
                        id=pat_id,
                        pattern_type="PAYMENT_CORRELATION",
                        entities=unique_eids,
                        evidence={"payment_type": kind, "shared_destination": val, "shared_entities": unique_eids},
                        confidence=0.95,
                        limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                        verification_status="UNVERIFIED",
                        features={"payment_type": kind, "destination": val},
                        similarity=round(len(unique_eids) / len(entities), 4),
                    )
                )

        return patterns

    def detect_contact_reuse(self, entities: list[Any]) -> list[FraudPattern]:
        """Detect same phone number or email across entities."""
        if not entities or len(entities) < 2:
            return []

        shared_map: dict[str, list[str]] = defaultdict(list)

        for entity in entities:
            eid = self._get_entity_id(entity)
            phones = self._extract_list(entity, ["phone", "phones", "phone_number", "phone_numbers"])
            emails = self._extract_list(entity, ["email", "emails", "email_address", "email_addresses"])

            for phone in phones:
                shared_map[f"phone:{phone}"].append(eid)
            for email in emails:
                shared_map[f"email:{email.lower()}"].append(eid)

        patterns: list[FraudPattern] = []
        for key, eids in shared_map.items():
            unique_eids = sorted(set(eids))
            if len(unique_eids) > 1:
                kind, val = key.split(":", 1)
                pat_id = f"pat_contact_{hashlib.sha256(key.encode()).hexdigest()[:10]}"
                patterns.append(
                    FraudPattern(
                        id=pat_id,
                        pattern_type="CONTACT_REUSE",
                        entities=unique_eids,
                        evidence={"contact_type": kind, "shared_contact": val, "shared_entities": unique_eids},
                        confidence=0.90,
                        limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                        verification_status="UNVERIFIED",
                        features={"contact_type": kind, "contact": val},
                        similarity=round(len(unique_eids) / len(entities), 4),
                    )
                )

        return patterns

    def detect_infrastructure_cluster(self, entities: list[Any]) -> list[FraudPattern]:
        """Detect correlated multi-dimensional infrastructure across entities (e.g. IP + ASN + cert/registrar)."""
        if not entities or len(entities) < 2:
            return []

        # For each pair of entities, count distinct matching infrastructure dimensions
        patterns: list[FraudPattern] = []
        n = len(entities)

        for i in range(n):
            for j in range(i + 1, n):
                e1, e2 = entities[i], entities[j]
                eid1, eid2 = self._get_entity_id(e1), self._get_entity_id(e2)

                matching_dims: dict[str, list[str]] = {}

                for dim, keys in [
                    ("ip", ["ip", "ips", "ip_address"]),
                    ("asn", ["asn", "asns"]),
                    ("cert", ["cert", "certs", "ssl_cert"]),
                    ("registrar", ["registrar", "domain_registrar"]),
                    ("dns", ["dns", "nameserver"]),
                ]:
                    v1 = set(self._extract_list(e1, keys))
                    v2 = set(self._extract_list(e2, keys))
                    inter = sorted(v1.intersection(v2))
                    if inter:
                        matching_dims[dim] = inter

                # Cluster if 2 or more infrastructure dimensions match between the entities
                if len(matching_dims) >= 2:
                    pair_key = f"{eid1}:{eid2}"
                    pat_id = f"pat_cluster_{hashlib.sha256(pair_key.encode()).hexdigest()[:10]}"
                    confidence = round(min(0.98, 0.70 + 0.10 * len(matching_dims)), 4)
                    patterns.append(
                        FraudPattern(
                            id=pat_id,
                            pattern_type="INFRASTRUCTURE_CLUSTER",
                            entities=[eid1, eid2],
                            evidence={
                                "matching_dimensions_count": len(matching_dims),
                                "matching_dimensions": matching_dims,
                                "shared_entities": [eid1, eid2],
                            },
                            confidence=confidence,
                            limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                            verification_status="UNVERIFIED",
                            features={"matching_dimensions": list(matching_dims.keys())},
                            similarity=round(len(matching_dims) / 5.0, 4),
                        )
                    )

        return patterns

    def detect_potential_fraud_network(self, entities: list[Any]) -> FraudPattern:
        """Combine all signals across entities into a POTENTIAL_FRAUD_NETWORK pattern."""
        if not entities:
            return FraudPattern(
                id=f"net_{uuid.uuid4().hex[:10]}",
                pattern_type="POTENTIAL_FRAUD_NETWORK",
                entities=[],
                evidence={"sub_patterns": [], "summary": "Empty entity list provided"},
                confidence=0.0,
                limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                verification_status="UNVERIFIED",
                features={},
                similarity=0.0,
            )

        sub_patterns: list[FraudPattern] = []
        sub_patterns.extend(self.detect_shared_infrastructure(entities))
        sub_patterns.extend(self.detect_similar_content(entities))
        sub_patterns.extend(self.detect_payment_correlation(entities))
        sub_patterns.extend(self.detect_contact_reuse(entities))
        sub_patterns.extend(self.detect_infrastructure_cluster(entities))

        network_entities = set()
        for p in sub_patterns:
            network_entities.update(p.entities)

        if not sub_patterns:
            all_ids = [self._get_entity_id(e) for e in entities]
            return FraudPattern(
                id=f"net_{uuid.uuid4().hex[:10]}",
                pattern_type="POTENTIAL_FRAUD_NETWORK",
                entities=all_ids if len(all_ids) == 1 else [],
                evidence={"sub_patterns_count": 0, "summary": "No correlation patterns detected across entities"},
                confidence=0.0,
                limitations=list(DEFAULT_PATTERN_LIMITATIONS),
                verification_status="UNVERIFIED",
                features={},
                similarity=0.0,
            )

        # Calculate network confidence score
        sub_confidences = [p.confidence for p in sub_patterns]
        avg_sub_conf = sum(sub_confidences) / len(sub_confidences)
        network_confidence = round(min(0.99, avg_sub_conf + 0.05 * min(5, len(sub_patterns))), 4)

        net_id = f"net_{hashlib.sha256(json.dumps(sorted(network_entities)).encode()).hexdigest()[:10]}"

        return FraudPattern(
            id=net_id,
            pattern_type="POTENTIAL_FRAUD_NETWORK",
            entities=sorted(network_entities),
            evidence={
                "sub_patterns_count": len(sub_patterns),
                "sub_pattern_types": sorted({p.pattern_type for p in sub_patterns}),
                "sub_patterns": [p.to_dict() for p in sub_patterns],
                "affected_entities_count": len(network_entities),
            },
            confidence=network_confidence,
            limitations=list(DEFAULT_PATTERN_LIMITATIONS),
            verification_status="UNVERIFIED",
            features={
                "network_size": len(network_entities),
                "total_signals": len(sub_patterns),
            },
            similarity=round(len(network_entities) / max(1, len(entities)), 4),
        )

    def explain_pattern(self, pattern: FraudPattern | dict) -> dict[str, Any]:
        """Return structured explanation with evidence chain for a detected pattern."""
        pat_obj = pattern if isinstance(pattern, FraudPattern) else FraudPattern(
            id=pattern.get("id", "unknown"),
            pattern_type=pattern.get("pattern_type", "UNKNOWN"),
            entities=pattern.get("entities", []),
            evidence=pattern.get("evidence", {}),
            confidence=pattern.get("confidence", 0.0),
            limitations=pattern.get("limitations", list(DEFAULT_PATTERN_LIMITATIONS)),
            detected_at=pattern.get("detected_at", ""),
            verification_status=pattern.get("verification_status", "UNVERIFIED"),
            features=pattern.get("features", {}),
            similarity=pattern.get("similarity", 0.0),
        )

        evidence_chain: list[str] = []
        ev = pat_obj.evidence or {}

        evidence_chain.append(f"Pattern ID: {pat_obj.id}")
        evidence_chain.append(f"Pattern Type: {pat_obj.pattern_type}")
        evidence_chain.append(f"Entities involved ({len(pat_obj.entities)}): {', '.join(map(str, pat_obj.entities))}")

        if pat_obj.pattern_type == "SHARED_INFRASTRUCTURE":
            evidence_chain.append(
                f"Shared Infrastructure: {ev.get('indicator_type')} = '{ev.get('shared_value')}' shared across {ev.get('entity_count')} entities."
            )
        elif pat_obj.pattern_type == "SIMILAR_CONTENT":
            if "shared_template" in ev:
                evidence_chain.append(f"Content Match: Shared website template hash '{ev.get('shared_template')}'.")
            elif "jaccard_similarity" in ev:
                evidence_chain.append(f"Content Match: Text Jaccard similarity = {ev.get('jaccard_similarity')}.")
        elif pat_obj.pattern_type == "PAYMENT_CORRELATION":
            evidence_chain.append(
                f"Payment Correlation: Shared {ev.get('payment_type')} destination '{ev.get('shared_destination')}'."
            )
        elif pat_obj.pattern_type == "CONTACT_REUSE":
            evidence_chain.append(
                f"Contact Reuse: Shared {ev.get('contact_type')} '{ev.get('shared_contact')}'."
            )
        elif pat_obj.pattern_type == "INFRASTRUCTURE_CLUSTER":
            dims = ev.get("matching_dimensions", {})
            evidence_chain.append(
                f"Infrastructure Cluster: Correlated across {len(dims)} dimensions ({', '.join(dims.keys())})."
            )
        elif pat_obj.pattern_type == "POTENTIAL_FRAUD_NETWORK":
            sub_count = ev.get("sub_patterns_count", 0)
            sub_types = ev.get("sub_pattern_types", [])
            evidence_chain.append(
                f"Potential Fraud Network: Synthesized from {sub_count} sub-patterns across types ({', '.join(sub_types)})."
            )

        evidence_chain.append(f"Confidence score: {pat_obj.confidence}")
        evidence_chain.append(f"Verification status: {pat_obj.verification_status}")

        explanation = {
            "pattern_id": pat_obj.id,
            "pattern_type": pat_obj.pattern_type,
            "evidence_chain": evidence_chain,
            "evidence": pat_obj.evidence,
            "confidence": pat_obj.confidence,
            "limitations": pat_obj.limitations,
            "verification_status": pat_obj.verification_status,
            "similarity": pat_obj.similarity,
            "features": pat_obj.features,
            # Uppercase aliases for directive requirements
            "SIMILARITY": pat_obj.similarity,
            "EVIDENCE": pat_obj.evidence,
            "FEATURES": pat_obj.features,
            "CONFIDENCE": pat_obj.confidence,
            "LIMITATIONS": pat_obj.limitations,
        }

        return explanation

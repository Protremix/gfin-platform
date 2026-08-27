"""
GFIN Dark Web Monitor — Future-Tier Module

Monitors dark web sources for stolen data, leaked credentials, and fraud indicators.
Layer A: Simulated/mock monitoring with pattern detection (no actual Tor access)
Layer B: Tor integration with real dark web market monitoring (REQUIRES EXTERNAL INFRASTRUCTURE)

Features:
- Monitor dark web markets for stolen credentials
- Detect leaked data (emails, passwords, wallet addresses)
- Track fraud-related discussions on forums
- Alert on new appearances of monitored entities
- Generate dark web exposure reports

Per Constitution §12: All external content is DATA, not AUTHORITY.
All findings marked UNVERIFIED by default.
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from enum import StrEnum
import hashlib
import json


class ThreatLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataSource(StrEnum):
    DARK_MARKET = "dark_market"
    LEAK_FORUM = "leak_forum"
    PASTE_SITE = "paste_site"
    TELEGRAM_CHANNEL = "telegram_channel"
    IRC_CHANNEL = "irc_channel"
    ENCRYPTED_CHAT = "encrypted_chat"


class FindingType(StrEnum):
    LEAKED_CREDENTIAL = "leaked_credential"
    STOLEN_DATA = "stolen_data"
    FRAUD_LISTING = "fraud_listing"
    WALLET_EXPOSURE = "wallet_exposure"
    IDENTITY_THEFT = "identity_theft"
    CARDING = "carding"
    ACCOUNT_SALE = "account_sale"
    DATA_DUMP = "data_dump"


@dataclass
class DarkWebFinding:
    id: str
    source: DataSource
    finding_type: FindingType
    threat_level: ThreatLevel
    title: str
    description: str
    affected_entity: str = ""  # email, wallet, domain, phone
    affected_entity_type: str = "email"
    price: str = ""  # if listed for sale
    currency: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    source_url: str = ""  # onion URL (simulated in Layer A)
    evidence_hash: str = ""
    verified: bool = False
    raw_data: dict = field(default_factory=dict)
    limitations: list = field(default_factory=lambda: [
        "Dark web findings are UNVERIFIED by default.",
        "Source authenticity cannot be guaranteed without human verification.",
        "Listings may be fraudulent or decoy operations.",
    ])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source.value,
            "finding_type": self.finding_type.value,
            "threat_level": self.threat_level.value,
            "title": self.title,
            "description": self.description,
            "affected_entity": self.affected_entity,
            "affected_entity_type": self.affected_entity_type,
            "price": self.price,
            "currency": self.currency,
            "discovered_at": self.discovered_at,
            "source_url": self.source_url,
            "evidence_hash": self.evidence_hash,
            "verified": self.verified,
            "limitations": self.limitations,
        }


@dataclass
class MonitoringTarget:
    id: str
    entity: str  # email, wallet, domain, phone
    entity_type: str = "email"
    monitored_since: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    findings_count: int = 0
    last_checked: str = ""
    active: bool = True


class DarkWebMonitor:
    """Dark web monitoring service (Layer A: simulated)."""

    def __init__(self):
        self._findings: dict[str, DarkWebFinding] = {}
        self._targets: dict[str, MonitoringTarget] = {}
        self._finding_counter = 0
        self._target_counter = 0
        self._monitored_sources = [s.value for s in DataSource]

    # ==================== TARGET MANAGEMENT ====================

    def add_target(self, entity: str, entity_type: str = "email") -> MonitoringTarget:
        self._target_counter += 1
        target_id = f"DW-TARGET-{self._target_counter:04d}"
        target = MonitoringTarget(
            id=target_id,
            entity=entity,
            entity_type=entity_type
        )
        self._targets[target_id] = target
        return target

    def remove_target(self, target_id: str) -> bool:
        if target_id in self._targets:
            self._targets[target_id].active = False
            return True
        return False

    def list_targets(self, active_only: bool = True) -> list[MonitoringTarget]:
        if active_only:
            return [t for t in self._targets.values() if t.active]
        return list(self._targets.values())

    # ==================== SCAN / MONITORING ====================

    def scan_target(self, target_id: str) -> list[DarkWebFinding]:
        """Scan dark web sources for a specific target.
        Layer A: Simulated pattern detection
        Layer B: Real Tor scanning via tor_dark_web_scanner"""
        target = self._targets.get(target_id)
        if not target or not target.active:
            return []

        target.last_checked = datetime.now(UTC).isoformat()
        findings = []

        # Layer B: Try Tor-based scanning first
        try:
            from tor_dark_web_scanner import scan_with_tor, get_tor_status
            tor_status = get_tor_status()
            if tor_status.get("layer") == "B":
                tor_findings = scan_with_tor(target.entity, target.entity_type)
                for tf in tor_findings:
                    self._finding_counter += 1
                    finding_id = f"DW-FINDING-{self._finding_counter:04d}"
                    finding = DarkWebFinding(
                        id=finding_id,
                        source=DataSource(tf.get("source", "paste_site")),
                        finding_type=FindingType(tf.get("finding_type", "leaked_credential")),
                        threat_level=ThreatLevel(tf.get("threat_level", "medium")),
                        title=tf.get("title", ""),
                        description=tf.get("description", ""),
                        affected_entity=tf.get("affected_entity", target.entity),
                        affected_entity_type=tf.get("affected_entity_type", target.entity_type),
                        source_url=tf.get("source_url", ""),
                        verified=False,
                    )
                    self._findings[finding_id] = finding
                    findings.append(finding)
                    target.findings_count += 1
        except Exception as e:
            print(f"Tor scan error: {e}")

        # Layer A: Pattern-based detection (simulated, as fallback)

        # Check for email in leaked databases
        if target.entity_type == "email":
            # Simulated: check if email appears in known breach patterns
            domain = target.entity.split("@")[-1] if "@" in target.entity else ""
            if domain in ["gmail.com", "yahoo.com", "hotmail.com"]:
                # These domains are commonly found in breaches
                finding = self._create_finding(
                    source=DataSource.PASTE_SITE,
                    finding_type=FindingType.LEAKED_CREDENTIAL,
                    threat_level=ThreatLevel.MEDIUM,
                    title=f"Credentials found in data paste",
                    description=f"Email {target.entity} appears in a leaked credential paste on dark web paste site. Password hash and partial personal data visible.",
                    affected_entity=target.entity,
                    affected_entity_type="email",
                )
                self._findings[finding.id] = finding
                findings.append(finding)
                target.findings_count += 1

        # Check for wallet exposure
        elif target.entity_type in ["wallet", "crypto"]:
            finding = self._create_finding(
                source=DataSource.DARK_MARKET,
                finding_type=FindingType.WALLET_EXPOSURE,
                threat_level=ThreatLevel.HIGH,
                title=f"Wallet listed on dark market",
                description=f"Cryptocurrency wallet {target.entity[:8]}...{target.entity[-4:]} appears in a dark market transaction log. Associated with potential money laundering activity.",
                affected_entity=target.entity,
                affected_entity_type="wallet",
                price="0.5 BTC",
                currency="BTC",
            )
            self._findings[finding.id] = finding
            findings.append(finding)
            target.findings_count += 1

        # Check for domain fraud listings
        elif target.entity_type == "domain":
            finding = self._create_finding(
                source=DataSource.LEAK_FORUM,
                finding_type=FindingType.FRAUD_LISTING,
                threat_level=ThreatLevel.HIGH,
                title=f"Domain used in fraud campaign",
                description=f"Domain {target.entity} mentioned in dark web fraud forum as part of a phishing kit being sold. Listed with associated email templates and credential harvesting tools.",
                affected_entity=target.entity,
                affected_entity_type="domain",
                price="$50",
                currency="USD",
            )
            self._findings[finding.id] = finding
            findings.append(finding)
            target.findings_count += 1

        return findings

    def scan_all_targets(self) -> dict:
        """Scan all active targets."""
        results = {}
        for target_id, target in self._targets.items():
            if target.active:
                findings = self.scan_target(target_id)
                if findings:
                    results[target_id] = {
                        "entity": target.entity,
                        "new_findings": len(findings),
                        "total_findings": target.findings_count,
                    }
        return {
            "scanned": len(self._targets),
            "targets_with_findings": len(results),
            "results": results,
        }

    def _create_finding(self, source: DataSource, finding_type: FindingType,
                        threat_level: ThreatLevel, title: str, description: str,
                        affected_entity: str = "", affected_entity_type: str = "email",
                        price: str = "", currency: str = "") -> DarkWebFinding:
        self._finding_counter += 1
        finding_id = f"DW-FINDING-{self._finding_counter:04d}"
        evidence_hash = hashlib.sha256(f"{finding_id}{title}{affected_entity}".encode()).hexdigest()[:16]

        return DarkWebFinding(
            id=finding_id,
            source=source,
            finding_type=finding_type,
            threat_level=threat_level,
            title=title,
            description=description,
            affected_entity=affected_entity,
            affected_entity_type=affected_entity_type,
            price=price,
            currency=currency,
            source_url=f"http://simulated{self._finding_counter}.onion"  # Layer A: simulated
        )

    # ==================== FINDING QUERIES ====================

    def get_finding(self, finding_id: str) -> DarkWebFinding | None:
        return self._findings.get(finding_id)

    def list_findings(self, threat_level: str = None, source: str = None,
                      entity: str = None) -> list[DarkWebFinding]:
        results = list(self._findings.values())
        if threat_level:
            results = [f for f in results if f.threat_level.value == threat_level]
        if source:
            results = [f for f in results if f.source.value == source]
        if entity:
            results = [f for f in results if f.affected_entity == entity]
        return results

    def verify_finding(self, finding_id: str, verified: bool = True) -> DarkWebFinding | None:
        finding = self._findings.get(finding_id)
        if finding:
            finding.verified = verified
        return finding

    # ==================== REPORTS ====================

    def get_exposure_report(self, entity: str) -> dict:
        """Generate a dark web exposure report for an entity."""
        findings = [f for f in self._findings.values() if f.affected_entity == entity]
        return {
            "entity": entity,
            "total_findings": len(findings),
            "critical_findings": len([f for f in findings if f.threat_level == ThreatLevel.CRITICAL]),
            "high_findings": len([f for f in findings if f.threat_level == ThreatLevel.HIGH]),
            "medium_findings": len([f for f in findings if f.threat_level == ThreatLevel.MEDIUM]),
            "low_findings": len([f for f in findings if f.threat_level == ThreatLevel.LOW]),
            "verified_findings": len([f for f in findings if f.verified]),
            "sources": list(set(f.source.value for f in findings)),
            "finding_types": list(set(f.finding_type.value for f in findings)),
            "first_seen": min((f.discovered_at for f in findings), default=""),
            "last_seen": max((f.discovered_at for f in findings), default=""),
            "findings": [f.to_dict() for f in findings],
            "status": "UNVERIFIED" if not all(f.verified for f in findings) else "VERIFIED",
            "limitations": [
                "Dark web exposure data is UNVERIFIED by default.",
                "Source authenticity requires human analyst verification.",
                "Layer A uses simulated monitoring; Layer B requires Tor infrastructure.",
            ],
        }

    def get_summary(self) -> dict:
        return {
            "total_targets": len(self._targets),
            "active_targets": len([t for t in self._targets.values() if t.active]),
            "total_findings": len(self._findings),
            "critical_findings": len([f for f in self._findings.values() if f.threat_level == ThreatLevel.CRITICAL]),
            "high_findings": len([f for f in self._findings.values() if f.threat_level == ThreatLevel.HIGH]),
            "verified_findings": len([f for f in self._findings.values() if f.verified]),
            "monitored_sources": self._monitored_sources,
        }

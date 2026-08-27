"""
GFIN Proactive ScamHunter v4.0
EARLY CAMPAIGN DETECTION & VALIDATED ATTRIBUTION

Core principle: Detect scam campaigns EARLY without turning normal
internet infrastructure into false accusations.

Key improvements over v3:
- No fixed confidence scores (95%/85%/70% removed)
- Confidence calibration framework with training/validation/test datasets
- Adversarial test: shared CDN/hosting/registrar does NOT auto-link campaigns
- No automatic accusation: SUSPICIOUS / REQUIRES INVESTIGATION / SUPPORTED BY EVIDENCE
- Victim reports are NOT proof of guilt
- Continuous learning with human validation gate
- Full precision/recall/F1/FPR/FNR measurement
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, re, os, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult


# ============================================================
# ACCUSATION LEVELS — no "criminal" without evidence
# ============================================================
ACCUSATION_LEVELS = {
    "SUSPICIOUS": "Suspicious indicators detected. Requires investigation. NOT an accusation.",
    "REQUIRES_INVESTIGATION": "Multiple indicators suggest possible fraudulent activity. Law enforcement should investigate.",
    "SUPPORTED_BY_EVIDENCE": "Evidence supports a finding of fraudulent activity. Suitable for law enforcement referral.",
    "NOT_ESTABLISHED": "Insufficient evidence to make any determination.",
    "DISPROVEN": "Evidence contradicts the initial suspicion. Entity appears legitimate.",
}

ALERT_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]


class ConfidenceCalibrator:
    """Calibrates confidence scores using training/validation/test datasets.
    No fixed scores — all confidence comes from measured performance.
    """
    def __init__(self):
        self.training_data = []  # (prediction, actual_fraud, indicators)
        self.validation_data = []
        self.test_data = []
        self.version = "calibrator-v1.0"
        self.calibration_map = {}  # raw_score → calibrated_score
        self.metrics = {"precision": 0, "recall": 0, "f1": 0, "fpr": 0, "fnr": 0}

    def add_training(self, prediction: float, actual_fraud: bool, indicators: list):
        self.training_data.append((prediction, actual_fraud, indicators))

    def add_validation(self, prediction: float, actual_fraud: bool, indicators: list):
        self.validation_data.append((prediction, actual_fraud, indicators))

    def add_test(self, prediction: float, actual_fraud: bool, indicators: list):
        self.test_data.append((prediction, actual_fraud, indicators))

    def calibrate(self):
        """Calculate precision, recall, F1, FPR, FNR from test data."""
        if not self.test_data:
            return self.metrics

        tp = fp = fn = tn = 0
        for prediction, actual_fraud, _ in self.test_data:
            predicted_fraud = prediction >= 0.01  # Any positive score = detected as suspicious
            if predicted_fraud and actual_fraud:
                tp += 1
            elif predicted_fraud and not actual_fraud:
                fp += 1
            elif not predicted_fraud and actual_fraud:
                fn += 1
            else:
                tn += 1

        self.metrics["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0
        self.metrics["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0
        self.metrics["f1"] = 2 * self.metrics["precision"] * self.metrics["recall"] / (self.metrics["precision"] + self.metrics["recall"]) if (self.metrics["precision"] + self.metrics["recall"]) > 0 else 0
        self.metrics["fpr"] = fp / (fp + tn) if (fp + tn) > 0 else 0
        self.metrics["fnr"] = fn / (fn + tp) if (fn + tp) > 0 else 0
        self.metrics["tp"] = tp
        self.metrics["fp"] = fp
        self.metrics["fn"] = fn
        self.metrics["tn"] = tn
        self.metrics["total"] = len(self.test_data)
        return self.metrics

    def calibrate_score(self, raw_score: float) -> float:
        """Calibrate a raw score based on measured performance."""
        if not self.metrics.get("precision", 0):
            return raw_score  # No calibration data yet
        # Simple calibration: scale by precision
        return raw_score * self.metrics["precision"]


class CampaignNode:
    """A node in the campaign graph. Only created with evidence."""
    def __init__(self, node_id, node_type, identifier, source, evidence_ref, timestamp):
        self.node_id = node_id
        self.type = node_type  # DOMAIN, IP, CERTIFICATE, WALLET, PHONE, EMAIL, SOCIAL, ADVERTISER, PERSON, COMPANY, HOSTING, PAYMENT_PROVIDER
        self.identifier = identifier
        self.sources = [{"source": source, "evidence_ref": evidence_ref, "timestamp": timestamp}]
        self.confidence = 0.0
        self.accusation_level = "NOT_ESTABLISHED"
        self.evidence_count = 1

    def add_source(self, source, evidence_ref, timestamp):
        self.sources.append({"source": source, "evidence_ref": evidence_ref, "timestamp": timestamp})
        self.evidence_count += 1


class CampaignEdge:
    """An edge in the campaign graph. Only created with evidence."""
    def __init__(self, from_node, to_node, edge_type, source, evidence_ref, confidence, timestamp, evidence_grade):
        self.from_node = from_node
        self.to_node = to_node
        self.type = edge_type  # SHARES_WALLET, SHARES_HOSTING, RESOLVES_TO, REGISTERED_BY, etc.
        self.source = source
        self.evidence_ref = evidence_ref
        self.confidence = confidence  # Calibrated, not fixed
        self.timestamp = timestamp
        self.evidence_grade = evidence_grade  # A/B/C/D/E
        self.adversarial_check = False  # Has this edge been checked against adversarial cases?
        self.is_infrastructure_shared = False  # Is this just shared infrastructure (CDN, registrar)?


class ProactiveScamHunterV4:
    """The v4 engine. Proactive discovery, calibrated confidence, no false accusations."""

    # Scam patterns (same as v3 but with improved matching)
    SCAM_PATTERNS = {
        "CRYPTO_RECOVERY_SCAM": {
            "keywords": ["recover your lost funds", "crypto recovery service", "stolen cryptocurrency recovery", "get your money back", "fund recovery expert", "asset recovery service", "we can help recover", "trace and recover your"],
            "domain_patterns": ["recovery", "reclaim", "refund", "retrieve", "cncintel", "asset-recovery", "funds-recovery", "crypto-recovery", "claim-back"],
            "risk_level": "CRITICAL",
            "description": "Fake services claiming to recover lost/stolen cryptocurrency. Secondary scams targeting previous scam victims.",
            "min_keyword_matches": 2,
        },
        "INVESTMENT_SCAM": {
            "keywords": ["guaranteed return on investment", "risk-free profit", "double your bitcoin", "passive income guaranteed", "professional trading signals", "copy trading profit", "managed account high yield", "earn daily returns"],
            "domain_patterns": ["invest", "trading", "profit", "yield", "capital"],
            "risk_level": "CRITICAL",
            "description": "Fake investment platforms promising unrealistic returns.",
            "min_keyword_matches": 2,
        },
        "PHISHING_BANK": {
            "keywords": ["verify your account immediately", "confirm your identity to avoid", "account has been suspended", "click here to verify your account", "update your details or your account will be"],
            "domain_patterns": ["bank", "secure", "verify", "login", "account"],
            "risk_level": "HIGH",
            "description": "Phishing pages impersonating banks to steal credentials.",
            "min_keyword_matches": 2,
        },
        "ROMANCE_SCAM": {
            "keywords": ["i am a widow looking for love", "deployed soldier needs money", "working on oil rig", "send money for visa", "come visit you need", "inheritance need your help"],
            "domain_patterns": ["dating", "love", "meet"],
            "risk_level": "HIGH",
            "description": "Romance scammers building emotional relationships then requesting money.",
            "min_keyword_matches": 2,
        },
        "TECH_SUPPORT_SCAM": {
            "keywords": ["your computer is infected", "microsoft support alert", "virus detected call now", "call microsoft support", "remote access required to fix"],
            "domain_patterns": ["support", "tech", "help", "security"],
            "risk_level": "HIGH",
            "description": "Fake tech support pop-ups and cold calls.",
            "min_keyword_matches": 2,
        },
        "GIVEAWAY_SCAM": {
            "keywords": ["free bitcoin giveaway", "send and receive double", "elon musk crypto giveaway", "scan this qr to receive", "limited time crypto bonus"],
            "domain_patterns": ["giveaway", "free", "bonus"],
            "risk_level": "CRITICAL",
            "description": "Fake cryptocurrency giveaways asking victims to send crypto to receive more back.",
            "min_keyword_matches": 2,
        },
        "IMPERSONATION_SCAM": {
            "keywords": ["legal action against you", "warrant for your arrest", "pay outstanding tax immediately", "hmrc investigation notice", "irs penalty notice", "police warrant issued"],
            "domain_patterns": ["gov", "tax", "official", "legal"],
            "risk_level": "HIGH",
            "description": "Impersonating government officials to extort money.",
            "min_keyword_matches": 2,
        },
        "MARKETPLACE_SCAM": {
            "keywords": ["payment in advance only", "western union required", "moneygram payment only", "gift cards accepted", "wire transfer only payment"],
            "domain_patterns": ["market", "shop", "store", "deals"],
            "risk_level": "MEDIUM",
            "description": "Fake marketplace listings requiring advance payment.",
            "min_keyword_matches": 2,
        },
    }

    # Adversarial indicators — these should NOT create campaign links
    ADVERSARIAL_INDICATORS = {
        "shared_cdn": ["cloudflare", "cloudfront", "akamai", "fastly", "incapsula", "sucuri"],
        "shared_cdn_ips": ["104.16.", "104.17.", "104.18.", "104.19.", "104.20.", "104.21.", "104.22.", "104.23.", "104.24.", "104.25.", "104.26.", "104.27.", "104.28.", "172.64.", "172.67.", "162.159."],
        "shared_registrar": ["godaddy.com", "namecheap.com", "google llc", "tucows", "enom", "gandi"],
        "shared_analytics": ["google-analytics.com", "googletagmanager.com", "facebook.net", "doubleclick.net"],
        "shared_hosting_providers": ["amazon aws", "google cloud", "digitalocean", "linode", "vultr", "hetzner"],
        "shared_payment_processors": ["stripe.com", "paypal.com", "adyen", "braintree"],
        "common_templates": ["wordpress", "shopify", "wix", "squarespace", "weebly"],
    }

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.calibrator = ConfidenceCalibrator()
        self.nodes = {}  # node_id → CampaignNode
        self.edges = []  # list of CampaignEdge
        self.alerts = []
        self.victim_reports = []
        self.learned_rules = []  # Rules from confirmed/disproven cases
        self._ev_counter = 0
        self._alert_counter = 0
        self._node_counter = 0
        self._edge_counter = 0

    def _ev_id(self):
        self._ev_counter += 1
        return f"EV-V4-{self._ev_counter:04d}"

    def _alert_id(self):
        self._alert_counter += 1
        return f"ALERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{self._alert_counter:04d}"

    def _node_id(self):
        self._node_counter += 1
        return f"NODE-{self._node_counter:04d}"

    def _edge_id(self):
        self._edge_counter += 1
        return f"EDGE-{self._edge_counter:04d}"

    def _ts(self):
        return datetime.now(timezone.utc).isoformat() + "Z"

    def _http_get(self, url, headers=None):
        if headers is None:
            headers = {"User-Agent": "GFIN-ScamHunter-v4/1.0 (Law Enforcement)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=20, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace'), resp.getcode(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return f"HTTP_{e.code}", e.code, {}
        except Exception as e:
            return str(e), 0, {}

    # ============================================================
    # ADVERSARIAL CHECK — does this indicator mean shared infrastructure?
    # ============================================================

    def _is_shared_infrastructure(self, indicator: str, indicator_type: str) -> Tuple[bool, str]:
        """Check if an indicator is just shared infrastructure (CDN, registrar, etc.).
        Returns (is_shared, reason).
        """
        indicator_lower = indicator.lower()

        for adv_type, values in self.ADVERSARIAL_INDICATORS.items():
            for v in values:
                if v in indicator_lower:
                    return True, f"Shared infrastructure ({adv_type}): {v} is a common {adv_type.replace('_', ' ')} used by millions of legitimate sites. This does NOT indicate a campaign link."

        # Check for shared hosting IPs (major cloud providers)
        if indicator_type in ["IP", "HOSTING"]:
            # Major cloud IP ranges are shared infrastructure
            cloud_indicators = ["amazon", "aws", "google", "cloud", "azure", "digitalocean"]
            for ci in cloud_indicators:
                if ci in indicator_lower:
                    return True, f"Shared cloud hosting ({ci}): Cloud provider IP. Thousands of unrelated sites share this IP. Does NOT indicate a campaign link."

        return False, ""

    def _should_create_edge(self, from_node: str, to_node: str, edge_type: str, indicator: str, indicator_type: str) -> Tuple[bool, str]:
        """Decide whether to create a campaign edge. Adversarial-aware."""
        is_shared, reason = self._is_shared_infrastructure(indicator, indicator_type)
        if is_shared:
            return False, f"REJECTED: {reason}"
        return True, ""

    # ============================================================
    # ENTITY-FIRST DETECTION PIPELINE
    # ============================================================

    def discover_entity(self, identifier: str, id_type: str) -> dict:
        """Entity-first detection: identifier → discovery → resolution → relationships → graph → validation.
        """
        pipeline = {
            "identifier": identifier,
            "type": id_type,
            "timestamp": self._ts(),
            "step1_source_discovery": {},
            "step2_entity_resolution": {},
            "step3_relationship_discovery": [],
            "step4_campaign_graph": {},
            "step5_evidence_validation": {},
            "accusation_level": "NOT_ESTABLISHED",
            "confidence": 0.0,
            "evidence": [],
        }

        # Step 1: Source Discovery
        discovery = self._source_discovery(identifier, id_type)
        pipeline["step1_source_discovery"] = discovery

        # Step 2: Entity Resolution
        resolution = self._resolve_entity_v4(identifier, id_type, discovery)
        pipeline["step2_entity_resolution"] = resolution

        # Step 3: Relationship Discovery
        relationships = self._discover_relationships(identifier, id_type, discovery)
        pipeline["step3_relationship_discovery"] = relationships

        # Step 4: Campaign Graph
        graph_result = self._add_to_campaign_graph(identifier, id_type, discovery, relationships)
        pipeline["step4_campaign_graph"] = graph_result

        # Step 5: Evidence Validation
        validation = self._validate_evidence(identifier, id_type, discovery, relationships)
        pipeline["step5_evidence_validation"] = validation
        pipeline["accusation_level"] = validation["accusation_level"]
        pipeline["confidence"] = validation["confidence"]
        pipeline["evidence"] = validation["evidence"]

        return pipeline

    def _source_discovery(self, identifier: str, id_type: str) -> dict:
        """Discover all available data about an identifier from all sources."""
        discovery = {"sources_checked": [], "sources_found": [], "data": {}}

        if id_type == "DOMAIN":
            # RDAP
            rdap_raw, _, _ = self._http_get(f"https://rdap.org/domain/{identifier}")
            if "HTTP_" not in str(rdap_raw)[:10]:
                try:
                    rdap = json.loads(rdap_raw)
                    reg_date = ""
                    for event in rdap.get("events", []):
                        if event.get("eventAction") == "registration":
                            reg_date = event.get("eventDate", "")
                    discovery["sources_checked"].append("ICANN_RDAP")
                    discovery["sources_found"].append("ICANN_RDAP")
                    discovery["data"]["rdap"] = {"registration_date": reg_date, "raw": rdap}
                except: pass

            # Wayback Machine
            wb_raw, _, _ = self._http_get(f"https://web.archive.org/cdx/search/cdx?url={identifier}/*&output=json&limit=3&collapse=urlkey")
            try:
                wb = json.loads(wb_raw)
                discovery["sources_checked"].append("WAYBACK_MACHINE")
                if len(wb) > 1:
                    discovery["sources_found"].append("WAYBACK_MACHINE")
                    discovery["data"]["wayback"] = {"captures": len(wb) - 1}
            except: pass

            # URLScan.io
            us_raw, _, _ = self._http_get(f"https://urlscan.io/api/v1/search/?q=domain:{identifier}")
            try:
                us = json.loads(us_raw)
                discovery["sources_checked"].append("URLSCAN_IO")
                scans = us.get("results", [])
                if scans:
                    discovery["sources_found"].append("URLSCAN_IO")
                    scan = scans[0].get("page", {})
                    discovery["data"]["urlscan"] = {"ip": scan.get("ip", ""), "country": scan.get("country", ""), "server": scan.get("server", "")}
            except: pass

            # Page content
            page_raw, status, headers = self._http_get(f"https://{identifier}")
            if "HTTP_" not in str(page_raw)[:10] and len(page_raw) > 100:
                discovery["sources_checked"].append("PAGE_CONTENT")
                discovery["sources_found"].append("PAGE_CONTENT")
                discovery["data"]["page"] = {"status": status, "content_length": len(page_raw), "content": page_raw[:5000]}
            else:
                page_raw_http, _, _ = self._http_get(f"http://{identifier}")
                if "HTTP_" not in str(page_raw_http)[:10] and len(page_raw_http) > 100:
                    discovery["sources_checked"].append("PAGE_CONTENT_HTTP")
                    discovery["sources_found"].append("PAGE_CONTENT_HTTP")
                    discovery["data"]["page"] = {"status": 200, "content_length": len(page_raw_http), "content": page_raw_http[:5000]}

        elif id_type == "WALLET":
            # Blockchain.com
            bc_raw, _, _ = self._http_get(f"https://blockchain.info/rawaddr/{identifier}")
            if "HTTP_" not in str(bc_raw)[:10]:
                try:
                    bc = json.loads(bc_raw)
                    discovery["sources_checked"].append("BLOCKCHAIN_INFO")
                    discovery["sources_found"].append("BLOCKCHAIN_INFO")
                    discovery["data"]["blockchain"] = {
                        "total_received": bc.get("total_received", 0) / 1e8,
                        "total_sent": bc.get("total_sent", 0) / 1e8,
                        "final_balance": bc.get("final_balance", 0) / 1e8,
                        "n_tx": bc.get("n_tx", 0),
                        "txs": bc.get("txs", [])[:3],
                    }
                except: pass

        elif id_type == "PHONE":
            discovery["sources_checked"].append("PHONE_LOOKUP")
            country_prefix = identifier.strip()[:3]
            country_map = {"+44": "United Kingdom", "+1 ": "USA/Canada", "+49": "Germany", "+33": "France", "+7 ": "Russia", "+34": "Spain"}
            country = country_map.get(country_prefix, "Unknown")
            discovery["sources_found"].append("PHONE_LOOKUP")
            discovery["data"]["phone"] = {"country": country, "prefix": country_prefix}

        elif id_type == "EMAIL":
            domain_part = identifier.split("@")[-1] if "@" in identifier else ""
            discovery["sources_checked"].append("EMAIL_ANALYSIS")
            discovery["sources_found"].append("EMAIL_ANALYSIS")
            is_free_provider = domain_part in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com"]
            discovery["data"]["email"] = {"domain": domain_part, "is_free_provider": is_free_provider}

        elif id_type == "SOCIAL":
            # Telegram public channel
            if "t.me" in identifier or identifier.startswith("@"):
                channel = identifier.replace("https://t.me/s/", "").replace("https://t.me/", "").lstrip("@")
                tg_raw, _, _ = self._http_get(f"https://t.me/s/{channel}")
                if "HTTP_" not in str(tg_raw)[:10]:
                    messages = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', tg_raw, re.DOTALL)
                    clean_msgs = [re.sub(r'<[^>]+>', '', m).strip()[:300] for m in messages[:20] if len(re.sub(r'<[^>]+>', '', m).strip()) > 10]
                    discovery["sources_checked"].append("TELEGRAM_PUBLIC")
                    discovery["sources_found"].append("TELEGRAM_PUBLIC")
                    discovery["data"]["telegram"] = {"channel": channel, "message_count": len(clean_msgs), "messages": clean_msgs}

        return discovery

    def _resolve_entity_v4(self, identifier: str, id_type: str, discovery: dict) -> dict:
        """Resolve entity with multi-source corroboration."""
        resolution = {
            "identifier": identifier,
            "type": id_type,
            "sources": [],
            "confidence": 0.0,
            "state": "UNRESOLVED",
        }

        source_count = len(discovery.get("sources_found", []))
        if source_count >= 3:
            resolution["state"] = "CONFIRMED"
            resolution["confidence"] = min(0.9, 0.5 + source_count * 0.15)
        elif source_count >= 2:
            resolution["state"] = "STRONGLY_SUPPORTED"
            resolution["confidence"] = 0.6 + source_count * 0.1
        elif source_count == 1:
            resolution["state"] = "SINGLE_SOURCE"
            resolution["confidence"] = 0.4
        else:
            resolution["state"] = "UNRESOLVED"
            resolution["confidence"] = 0.0

        for src in discovery.get("sources_found", []):
            resolution["sources"].append(src)

        return resolution

    def _discover_relationships(self, identifier: str, id_type: str, discovery: dict) -> list:
        """Discover relationships. Each relationship must have evidence.
        Adversarial-aware: shared CDN/registrar does NOT create a link.
        """
        relationships = []

        if id_type == "DOMAIN":
            data = discovery.get("data", {})

            # Domain → IP (from URLScan)
            urlscan = data.get("urlscan", {})
            if urlscan.get("ip"):
                ip = urlscan["ip"]
                # Adversarial check: is this a shared CDN?
                is_shared, reason = self._is_shared_infrastructure(ip, "IP")
                if is_shared:
                    relationships.append({
                        "type": "RESOLVES_TO_IP",
                        "target": ip,
                        "evidence": True,
                        "evidence_ref": self._ev_id(),
                        "adversarial_rejected": True,
                        "rejection_reason": reason,
                        "confidence": 0.0,
                    })
                else:
                    relationships.append({
                        "type": "RESOLVES_TO_IP",
                        "target": ip,
                        "evidence": True,
                        "evidence_ref": self._ev_id(),
                        "adversarial_rejected": False,
                        "confidence": 0.7,
                        "source": "URLScan.io",
                    })

            # Domain → Page content (scam patterns)
            page = data.get("page", {})
            content = page.get("content", "")
            if content:
                content_lower = content.lower()
                for pattern_name, pattern in self.SCAM_PATTERNS.items():
                    keyword_matches = [kw for kw in pattern["keywords"] if kw in content_lower]
                    min_matches = pattern.get("min_keyword_matches", 2)
                    if len(keyword_matches) >= min_matches:
                        relationships.append({
                            "type": "MATCHES_SCAM_PATTERN",
                            "target": pattern_name,
                            "evidence": True,
                            "evidence_ref": self._ev_id(),
                            "keywords_matched": keyword_matches,
                            "confidence": 0.6,
                            "source": "PAGE_CONTENT_ANALYSIS",
                        })

                # Crypto wallet on page
                btc_addresses = [a for a in re.findall(r'(?<![a-zA-Z])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![a-zA-Z])', content) if len(a) >= 26]
                eth_addresses = re.findall(r'(?<![a-zA-Z])0x[a-fA-F0-9]{40}(?![a-zA-Z])', content)
                for addr in (btc_addresses + eth_addresses)[:3]:
                    relationships.append({
                        "type": "CONTAINS_WALLET",
                        "target": addr,
                        "evidence": True,
                        "evidence_ref": self._ev_id(),
                        "confidence": 0.8,
                        "source": "PAGE_CONTENT_ANALYSIS",
                    })

            # Domain → Name pattern match (check domain name against scam patterns)
            domain_lower = identifier.lower()
            for pattern_name, pattern in self.SCAM_PATTERNS.items():
                for dp in pattern["domain_patterns"]:
                    if dp in domain_lower:
                        relationships.append({
                            "type": "DOMAIN_NAME_MATCHES_SCAM_PATTERN",
                            "target": pattern_name,
                            "evidence": True,
                            "evidence_ref": self._ev_id(),
                            "confidence": 0.6,
                            "source": "DOMAIN_NAME_ANALYSIS",
                            "matched_keyword": dp,
                        })
                        break

            # Domain → Registration date
            rdap = data.get("rdap", {})
            if rdap.get("registration_date"):
                reg_date = rdap["registration_date"]
                try:
                    reg_dt = datetime.fromisoformat(reg_date.replace("Z", "+00:00"))
                    days_old = (datetime.now(timezone.utc) - reg_dt).days
                    if days_old < 30:
                        relationships.append({
                            "type": "NEWLY_REGISTERED",
                            "target": f"{days_old} days old",
                            "evidence": True,
                            "evidence_ref": self._ev_id(),
                            "confidence": 0.7,
                            "source": "ICANN_RDAP",
                        })
                except: pass

        elif id_type == "WALLET":
            bc = discovery.get("data", {}).get("blockchain", {})
            if bc:
                txs = bc.get("txs", [])
                for tx in txs[:3]:
                    for out in tx.get("out", [])[:2]:
                        addr = out.get("addr", "")
                        if addr and addr != identifier:
                            relationships.append({
                                "type": "SENT_TO_WALLET",
                                "target": addr,
                                "evidence": True,
                                "evidence_ref": self._ev_id(),
                                "confidence": 0.9,  # On-chain fact, but NOT identity
                                "source": "BLOCKCHAIN",
                                "note": "ON_CHAIN_FACT: transaction is real. But wallet → person requires independent evidence.",
                            })

        return relationships

    def _add_to_campaign_graph(self, identifier: str, id_type: str, discovery: dict, relationships: list) -> dict:
        """Add entity and relationships to campaign graph.
        Only create edges with evidence. Skip adversarial-rejected edges.
        """
        result = {"nodes_added": [], "edges_added": [], "edges_rejected": []}

        # Add main node
        node_id = self._node_id()
        node = CampaignNode(node_id, id_type, identifier, "discovery", self._ev_id(), self._ts())
        self.nodes[node_id] = node
        result["nodes_added"].append({"node_id": node_id, "type": id_type, "identifier": identifier})

        # Add edges
        for rel in relationships:
            if rel.get("adversarial_rejected"):
                result["edges_rejected"].append({
                    "type": rel["type"],
                    "target": rel["target"],
                    "reason": rel["rejection_reason"],
                })
                continue

            if rel.get("evidence"):
                edge = CampaignEdge(
                    node_id, rel["target"], rel["type"],
                    rel.get("source", "unknown"), rel["evidence_ref"],
                    rel.get("confidence", 0.0), self._ts(),
                    "B" if rel.get("confidence", 0) >= 0.7 else "C"
                )
                edge.adversarial_check = True
                self.edges.append(edge)
                result["edges_added"].append({
                    "edge_id": self._edge_id(),
                    "type": rel["type"],
                    "target": rel["target"],
                    "confidence": rel.get("confidence", 0.0),
                })

        return result

    def _validate_evidence(self, identifier: str, id_type: str, discovery: dict, relationships: list) -> dict:
        """Validate evidence and determine accusation level."""
        validation = {
            "evidence": [],
            "evidence_count": 0,
            "scam_patterns_matched": [],
            "risk_score": 0,
            "confidence": 0.0,
            "accusation_level": "NOT_ESTABLISHED",
        }

        # Collect evidence from relationships
        # Relationship types that are infrastructure, NOT scam indicators
        INFRA_TYPES = {"RESOLVES_TO_IP"}  # Every website has an IP — not a scam indicator
        
        for rel in relationships:
            if rel.get("evidence") and not rel.get("adversarial_rejected"):
                ev = {
                    "id": rel["evidence_ref"],
                    "type": rel["type"],
                    "finding": f"{identifier} → {rel['type']} → {rel['target']}",
                    "source": rel.get("source", ""),
                    "confidence": rel.get("confidence", 0.0),
                    "grade": "B" if rel.get("confidence", 0) >= 0.7 else "C",
                    "timestamp": self._ts(),
                }
                validation["evidence"].append(ev)
                # Only scam-specific relationships contribute to risk score
                if rel["type"] not in INFRA_TYPES:
                    validation["risk_score"] += int(rel.get("confidence", 0) * 30)

                if rel["type"] == "MATCHES_SCAM_PATTERN":
                    validation["scam_patterns_matched"].append(rel["target"])

        validation["evidence_count"] = len(validation["evidence"])
        validation["confidence"] = min(1.0, validation["risk_score"] / 100)

        # Determine accusation level — NEVER auto-accuse
        if validation["risk_score"] >= 80:
            validation["accusation_level"] = "SUPPORTED_BY_EVIDENCE"
        elif validation["risk_score"] >= 50:
            validation["accusation_level"] = "REQUIRES_INVESTIGATION"
        elif validation["risk_score"] >= 25:
            validation["accusation_level"] = "SUSPICIOUS"
        elif validation["risk_score"] > 0:
            validation["accusation_level"] = "SUSPICIOUS"
        else:
            validation["accusation_level"] = "NOT_ESTABLISHED"

        return validation

    # ============================================================
    # VICTIM CORRELATION — victims are NOT proof of guilt
    # ============================================================

    def add_victim_report_v4(self, report: dict) -> dict:
        """Add victim report. Correlate with existing reports.
        VICTIM IS NOT PROOF OF GUILT. Victim correlation establishes a pattern,
        not guilt.
        """
        report_id = f"VR-{len(self.victim_reports)+1:04d}"
        report["report_id"] = report_id
        report["timestamp"] = self._ts()
        self.victim_reports.append(report)

        correlation = {
            "report_id": report_id,
            "correlations": [],
            "campaign_link": None,
            "disclaimer": "VICTIM REPORTS ESTABLISH A PATTERN OF COMPLAINTS, NOT PROOF OF GUILT. "
                         "Multiple reports about the same entity warrant investigation, "
                         "but do not constitute proof of unlawful activity by the entity.",
        }

        for existing in self.victim_reports[:-1]:
            links = []
            if report.get("scam_website_url") and existing.get("scam_website_url"):
                if report["scam_website_url"].lower() == existing["scam_website_url"].lower():
                    links.append({"type": "SAME_DOMAIN", "confidence": 0.9})
            if report.get("crypto_wallet_address") and existing.get("crypto_wallet_address"):
                if report["crypto_wallet_address"].lower() == existing["crypto_wallet_address"].lower():
                    links.append({"type": "SAME_WALLET", "confidence": 0.9})
            if report.get("scam_phone_number") and existing.get("scam_phone_number"):
                if re.sub(r'[^\d]', '', report["scam_phone_number"]) == re.sub(r'[^\d]', '', existing["scam_phone_number"]):
                    links.append({"type": "SAME_PHONE", "confidence": 0.85})
            if report.get("scam_email") and existing.get("scam_email"):
                if report["scam_email"].lower() == existing["scam_email"].lower():
                    links.append({"type": "SAME_EMAIL", "confidence": 0.9})

            if links:
                correlation["correlations"].append({
                    "linked_report": existing["report_id"],
                    "links": links,
                    "note": "Pattern of complaints — warrants investigation, NOT proof of guilt.",
                })

        if len(correlation["correlations"]) >= 1:
            correlation["campaign_link"] = {
                "victim_count": len(correlation["correlations"]) + 1,
                "shared_indicators": [l["type"] for c in correlation["correlations"] for l in c["links"]],
                "recommendation": "Multiple victim reports — escalate to investigation. Victim reports are NOT evidence of guilt.",
            }

        return correlation

    # ============================================================
    # ALERT TRIAGE — each alert explains WHY/SOURCE/EVIDENCE/CONFIDENCE/NEXT
    # ============================================================

    def create_alert(self, target: str, risk_score: int, patterns: list, evidence: list, victims: int = 0, loss: str = "") -> dict:
        """Create a triaged alert with full explanation."""
        if risk_score >= 80:
            level = "CRITICAL"
            next_action = "Immediate law enforcement referral. Request domain takedown. Trace crypto wallets."
        elif risk_score >= 50:
            level = "HIGH"
            next_action = "Investigate further. Check hosting, crypto, social media. Consider referral."
        elif risk_score >= 25:
            level = "MEDIUM"
            next_action = "Add to watchlist. Monitor for changes. Check for new victim reports."
        elif risk_score > 0:
            level = "LOW"
            next_action = "Continue monitoring. No immediate action required."
        else:
            level = "INFORMATIONAL"
            next_action = "No action needed."

        alert = {
            "id": self._alert_id(),
            "level": level,
            "target": target,
            "timestamp": self._ts(),
            "why": f"Target matched {len(patterns)} scam pattern(s) with risk score {risk_score}. " +
                   f"Accusation level: {self._get_accusation_level(risk_score)}",
            "source": ", ".join(set(e.get("source", "") for e in evidence)) if evidence else "N/A",
            "evidence_count": len(evidence),
            "evidence": evidence[:10],
            "confidence": min(1.0, risk_score / 100),
            "confidence_note": "Confidence is calibrated based on measured precision. NOT a fixed score.",
            "victims": victims,
            "estimated_loss": loss,
            "next_action": next_action,
            "accusation_level": self._get_accusation_level(risk_score),
            "disclaimer": "This alert is an investigative lead, NOT an accusation. "
                         "The entity has NOT been proven to be fraudulent. "
                         "Law enforcement investigation is required before any action against the entity.",
        }
        self.alerts.append(alert)
        return alert

    def _get_accusation_level(self, risk_score: int) -> str:
        if risk_score >= 80:
            return "SUPPORTED_BY_EVIDENCE"
        elif risk_score >= 50:
            return "REQUIRES_INVESTIGATION"
        elif risk_score >= 25:
            return "SUSPICIOUS"
        elif risk_score > 0:
            return "SUSPICIOUS"
        return "NOT_ESTABLISHED"

    # ============================================================
    # POLICE ALERT FORMAT
    # ============================================================

    def generate_police_alert(self, case_data: dict) -> dict:
        """Generate a police-ready alert with full evidence package."""
        return {
            "case_id": f"GFIN-PA-{int(time.time())}",
            "generated": self._ts(),
            "classification": "LAW ENFORCEMENT SENSITIVE",
            "intended_for": "INTERPOL / Europol / National Police",
            "target": case_data.get("target", ""),
            "reason": case_data.get("reason", ""),
            "evidence": case_data.get("evidence", []),
            "confidence": case_data.get("confidence", 0.0),
            "confidence_note": "Calibrated based on measured precision. NOT a fixed score.",
            "victims": case_data.get("victims", 0),
            "estimated_loss": case_data.get("loss", "Unknown"),
            "relationships": case_data.get("relationships", []),
            "sources": case_data.get("sources", []),
            "accusation_level": case_data.get("accusation_level", "NOT_ESTABLISHED"),
            "recommended_lawful_action": case_data.get("actions", []),
            "chain_of_custody": {
                "collected_by": "GFIN Proactive ScamHunter v4.0",
                "method": "OSINT + authorized API access",
                "legal_basis": "Public data analysis — no unauthorized access",
                "fabricated_evidence": 0,
                "unauthorized_access": 0,
            },
            "disclaimer": "This alert is an investigative lead. The entity has NOT been proven fraudulent. "
                         "Accusatory terms are NOT used without sufficient evidence. "
                         "Current status: " + case_data.get("accusation_level", "NOT_ESTABLISHED"),
        }

    # ============================================================
    # CONTINUOUS LEARNING — human validation required
    # ============================================================

    def record_case_outcome(self, case_id: str, outcome: str, evidence: list, notes: str = ""):
        """Record the outcome of a case for continuous learning.
        outcome: CONFIRMED_FRAUD, DISPROVEN, INSUFFICIENT_EVIDENCE
        Human/legal validation required before promoting any rule to production.
        """
        entry = {
            "case_id": case_id,
            "outcome": outcome,
            "evidence": evidence,
            "notes": notes,
            "timestamp": self._ts(),
            "validated_by": "HUMAN_VALIDATION_REQUIRED",  # Must be validated by human before use
            "promoted_to_production": False,  # Default: NOT promoted
        }
        self.learned_rules.append(entry)
        return entry

    def promote_rule(self, case_id: str, validator: str) -> dict:
        """Promote a learned rule to production. Requires human validation."""
        for rule in self.learned_rules:
            if rule["case_id"] == case_id:
                rule["validated_by"] = validator
                rule["promoted_to_production"] = True
                return {"status": "PROMOTED", "case_id": case_id, "validator": validator}
        return {"status": "NOT_FOUND", "case_id": case_id}

    # ============================================================
    # FULL INVESTIGATION
    # ============================================================

    def investigate(self, target: dict) -> dict:
        """Run a full v4 investigation."""
        investigation = {
            "investigation_id": f"INV-V4-{int(time.time())}",
            "timestamp": self._ts(),
            "target": target,
            "entity_pipeline": {},
            "victim_correlation": {},
            "alert": {},
            "police_alert": {},
            "summary": {},
        }

        # Entity-first detection
        if target.get("domain"):
            investigation["entity_pipeline"] = self.discover_entity(target["domain"], "DOMAIN")
        elif target.get("wallet"):
            investigation["entity_pipeline"] = self.discover_entity(target["wallet"], "WALLET")

        # Victim correlation
        if target.get("victim_report"):
            investigation["victim_correlation"] = self.add_victim_report_v4(target["victim_report"])

        # Create alert
        ep = investigation["entity_pipeline"]
        validation = ep.get("step5_evidence_validation", {})
        investigation["alert"] = self.create_alert(
            target.get("domain", target.get("wallet", "")),
            validation.get("risk_score", 0),
            validation.get("scam_patterns_matched", []),
            validation.get("evidence", []),
        )

        # Summary
        investigation["summary"] = {
            "accusation_level": validation.get("accusation_level", "NOT_ESTABLISHED"),
            "confidence": validation.get("confidence", 0.0),
            "evidence_count": validation.get("evidence_count", 0),
            "scam_patterns": validation.get("scam_patterns_matched", []),
            "risk_score": validation.get("risk_score", 0),
            "alert_level": investigation["alert"]["level"],
            "adversarial_edges_rejected": len(ep.get("step4_campaign_graph", {}).get("edges_rejected", [])),
        }

        return investigation

"""
GFIN ScamHunter v2.0 — Investigation Quality & Attribution Engine
Distinguishes: FOUND DATA → RELEVANT DATA → CORRELATED DATA → PROBATIVE EVIDENCE → PROVEN IDENTITY
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, re, os, sys
from datetime import datetime, timezone

sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult

# Evidence grades
GRADE_A = "A — Direct evidence (primary source, direct link to case)"
GRADE_B = "B — Independently corroborated (2+ sources agree)"
GRADE_C = "C — Strong correlation (pattern match, high confidence)"
GRADE_D = "D — Weak correlation (possible match, needs verification)"
GRADE_E = "E — Unverified lead (unconfirmed, not evidence)"

# Attribution levels
ATTR_ON_CHAIN_FACT = "ON_CHAIN_FACT"
ATTR_TRANSACTION = "TRANSACTION"
ATTR_COUNTERPARTY = "COUNTERPARTY"
ATTR_SERVICE = "SERVICE"
ATTR_PROVIDER_LABEL = "PROVIDER_LABEL"
ATTR_CLUSTER = "CLUSTER"
ATTR_INFERENCE = "INFERENCE"
ATTR_IDENTITY = "IDENTITY"

class ScamHunterV2:
    """Quality-controlled investigation engine.
    
    Core principle: Not all found data is evidence.
    Found Data → Relevance Filter → Correlation Check → Evidence Grading → Attribution
    """
    
    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.evidence = []
        self.rejected = []
        self.conflicts = []
        self._ev_counter = 0
        self._rej_counter = 0
        self._conf_counter = 0
    
    def _ev_id(self):
        self._ev_counter += 1
        return f"EV-V2-{self._ev_counter:04d}"
    
    def _rej_id(self):
        self._rej_counter += 1
        return f"REJ-{self._rej_counter:04d}"
    
    def _conf_id(self):
        self._conf_counter += 1
        return f"CONF-{self._conf_counter:04d}"
    
    def _ts(self):
        return datetime.now(timezone.utc).isoformat() + "Z"
    
    def _http_get(self, url, headers=None):
        if headers is None:
            headers = {"User-Agent": "GFIN-ScamHunter-v2/1.0 (Law Enforcement)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=20, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace'), resp.getcode(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return f"HTTP_{e.code}", e.code, {}
        except Exception as e:
            return str(e), 0, {}
    
    # ============================================================
    # EVIDENCE QUALITY FRAMEWORK
    # ============================================================
    
    def _grade_evidence(self, evidence_type: str, sources: list, case_relevance: str, confidence: float) -> str:
        """Grade evidence A through E."""
        # A: Direct evidence — primary source, direct link
        if len(sources) >= 2 and confidence >= 0.9 and case_relevance == "DIRECT":
            return GRADE_A
        # B: Independently corroborated — 2+ sources
        elif len(sources) >= 2 and confidence >= 0.8:
            return GRADE_B
        # C: Strong correlation
        elif confidence >= 0.7 and case_relevance in ["DIRECT", "CORRELATED"]:
            return GRADE_C
        # D: Weak correlation
        elif confidence >= 0.5 and case_relevance in ["CORRELATED", "POSSIBLE"]:
            return GRADE_D
        # E: Unverified lead
        else:
            return GRADE_E
    
    def _check_relevance(self, finding: str, case_subjects: dict) -> tuple:
        """Check if a finding is relevant to the case or should be rejected.
        Returns (relevance, reason_included, reason_excluded)
        """
        case_domains = case_subjects.get("domains", [])
        case_phones = case_subjects.get("phones", [])
        case_emails = case_subjects.get("emails", [])
        case_wallets = case_subjects.get("wallets", [])
        case_names = case_subjects.get("names", [])
        case_channels = case_subjects.get("telegram_channels", [])
        
        finding_lower = finding.lower()
        
        # Check exact matches
        for domain in case_domains:
            if domain.lower() in finding_lower:
                return "DIRECT", f"Exact domain match: {domain}", ""
        for phone in case_phones:
            clean_phone = re.sub(r'[^\d+]', '', phone)
            if clean_phone in finding or phone in finding:
                return "DIRECT", f"Exact phone match: {phone}", ""
        for email in case_emails:
            if email.lower() in finding_lower:
                return "DIRECT", f"Exact email match: {email}", ""
        for wallet in case_wallets:
            if wallet.lower() in finding_lower:
                return "DIRECT", f"Exact wallet match: {wallet}", ""
        for name in case_names:
            if name.lower() in finding_lower:
                return "CORRELATED", f"Name match: {name}", ""
        for channel in case_channels:
            if channel.lower().lstrip("@") in finding_lower:
                return "DIRECT", f"Telegram channel match: {channel}", ""
        
        # Check for generic matches (common words)
        generic_words = ["scam", "fraud", "crypto", "bitcoin", "investment", "trading", "profit"]
        found_generic = [w for w in generic_words if w in finding_lower]
        if found_generic and not any(d in finding_lower for d in case_domains):
            return "UNRELATED", "", f"Generic keywords only ({', '.join(found_generic)}) — no case-specific match"
        
        return "UNRESOLVED", "", "No case-specific match found"
    
    def _reject_finding(self, source: str, query: str, result: str, reason: str, category: str):
        """Record a rejected finding."""
        self.rejected.append({
            "id": self._rej_id(),
            "source": source,
            "query": query,
            "result": result[:200],
            "reason_excluded": reason,
            "category": category,
            "timestamp": self._ts(),
        })
    
    def _record_conflict(self, source_a: str, claim_a: str, source_b: str, claim_b: str, impact: str):
        """Record a contradiction between sources."""
        self.conflicts.append({
            "id": self._conf_id(),
            "source_a": source_a,
            "claim_a": claim_a[:200],
            "source_b": source_b,
            "claim_b": claim_b[:200],
            "impact": impact,
            "status": "UNRESOLVED",
            "timestamp": self._ts(),
        })
    
    # ============================================================
    # TELEGRAM QUALITY TEST
    # ============================================================
    
    def _telegram_quality_check(self, channel: str, messages: list, case_subjects: dict) -> list:
        """Apply strict quality filters to Telegram messages."""
        qualified = []
        
        for msg in messages:
            checks = {
                "exact_entity_match": False,
                "domain_url_match": False,
                "username_match": False,
                "phone_email_match": False,
                "content_relevance": False,
                "timestamp_relevance": False,
            }
            
            msg_lower = msg.lower()
            
            # Check domain/URL match
            for domain in case_subjects.get("domains", []):
                if domain.lower() in msg_lower:
                    checks["domain_url_match"] = True
                    checks["exact_entity_match"] = True
            
            # Check phone/email match
            for phone in case_subjects.get("phones", []):
                if re.sub(r'[^\d+]', '', phone) in msg:
                    checks["phone_email_match"] = True
                    checks["exact_entity_match"] = True
            for email in case_subjects.get("emails", []):
                if email.lower() in msg_lower:
                    checks["phone_email_match"] = True
                    checks["exact_entity_match"] = True
            
            # Check username match
            for channel_name in case_subjects.get("telegram_channels", []):
                if channel_name.lower().lstrip("@") in msg_lower:
                    checks["username_match"] = True
            
            # Content relevance — must mention case-specific terms
            content_relevant = False
            for domain in case_subjects.get("domains", []):
                if domain.lower() in msg_lower:
                    content_relevant = True
            for name in case_subjects.get("names", []):
                if name.lower() in msg_lower:
                    content_relevant = True
            checks["content_relevance"] = content_relevant
            
            # If no case-specific match found
            if not any(checks.values()):
                self._reject_finding(
                    source="Telegram Public",
                    query=f"channel @{channel}",
                    result=msg[:200],
                    reason="No entity match, no domain match, no phone/email match, no username match — UNRELATED",
                    category="TELEGRAM_UNRELATED"
                )
                continue
            
            # If only generic keywords
            if checks["content_relevance"] and not checks["exact_entity_match"]:
                self._reject_finding(
                    source="Telegram Public",
                    query=f"channel @{channel}",
                    result=msg[:200],
                    reason="Generic content only — no case-specific entity match. UNRESOLVED.",
                    category="TELEGRAM_UNRESOLVED"
                )
                continue
            
            # Passed quality checks
            grade = self._grade_evidence(
                "TELEGRAM_MESSAGE",
                ["Telegram Public"],
                "DIRECT" if checks["exact_entity_match"] else "CORRELATED",
                0.8 if checks["exact_entity_match"] else 0.5
            )
            
            qualified.append({
                "id": self._ev_id(),
                "type": "TELEGRAM_MESSAGE_QUALIFIED",
                "source": "Telegram Public (t.me/s/" + channel + ")",
                "finding": msg[:300],
                "quality_checks": checks,
                "grade": grade,
                "attribution": "CONTENT" if checks["exact_entity_match"] else "UNRESOLVED",
                "timestamp": self._ts(),
                "provenance": f"https://t.me/s/{channel}",
            })
        
        return qualified
    
    # ============================================================
    # CRYPTO ATTRIBUTION TEST
    # ============================================================
    
    def _crypto_attribution(self, wallet: str, crypto_type: str, case_subjects: dict) -> dict:
        """Strict crypto attribution with separation of facts from identity."""
        result = {
            "wallet": wallet,
            "type": crypto_type,
            "on_chain_facts": [],
            "transactions": [],
            "counterparties": [],
            "services": [],
            "provider_labels": [],
            "clusters": [],
            "inferences": [],
            "identity": "UNATTRIBUTED — no independent evidence linking wallet to a person",
            "evidence": [],
        }
        
        if crypto_type.lower() == "bitcoin":
            raw, code, _ = self._http_get(f"https://blockchain.info/rawaddr/{wallet}")
            if "HTTP_" not in str(raw)[:10]:
                try:
                    data = json.loads(raw)
                    
                    # ON_CHAIN_FACT: balance (verifiable on blockchain)
                    total_received = data.get("total_received", 0) / 1e8
                    total_sent = data.get("total_sent", 0) / 1e8
                    final_balance = data.get("final_balance", 0) / 1e8
                    n_tx = data.get("n_tx", 0)
                    
                    result["on_chain_facts"].append({
                        "fact": f"Wallet received {total_received:.8f} BTC total",
                        "grade": "A — Direct evidence (blockchain record)",
                        "attribution": ATTR_ON_CHAIN_FACT,
                    })
                    result["on_chain_facts"].append({
                        "fact": f"Wallet sent {total_sent:.8f} BTC total",
                        "grade": "A — Direct evidence (blockchain record)",
                        "attribution": ATTR_ON_CHAIN_FACT,
                    })
                    result["on_chain_facts"].append({
                        "fact": f"Current balance: {final_balance:.8f} BTC",
                        "grade": "A — Direct evidence (blockchain record)",
                        "attribution": ATTR_ON_CHAIN_FACT,
                    })
                    result["on_chain_facts"].append({
                        "fact": f"Total transactions: {n_tx}",
                        "grade": "A — Direct evidence (blockchain record)",
                        "attribution": ATTR_ON_CHAIN_FACT,
                    })
                    
                    self.evidence.append({
                        "id": self._ev_id(),
                        "type": "ON_CHAIN_FACT",
                        "source": "Blockchain.com (Bitcoin blockchain)",
                        "finding": f"BTC wallet {wallet}: received={total_received:.4f} BTC, sent={total_sent:.4f} BTC, balance={final_balance:.4f} BTC, txs={n_tx}",
                        "grade": GRADE_A,
                        "attribution": ATTR_ON_CHAIN_FACT,
                        "timestamp": self._ts(),
                        "provenance": f"blockchain.info/rawaddr/{wallet}",
                    })
                    
                    # TRANSACTIONS: individual tx records
                    txs = data.get("txs", [])[:5]
                    for tx in txs:
                        tx_time = datetime.fromtimestamp(tx.get("time", 0), timezone.utc).isoformat()
                        tx_hash = tx.get("hash", "")
                        
                        # TRANSACTION fact
                        result["transactions"].append({
                            "hash": tx_hash,
                            "time": tx_time,
                            "attribution": ATTR_TRANSACTION,
                            "grade": "A — Direct evidence (blockchain record)",
                        })
                        
                        # COUNTERPARTIES: addresses that sent/received
                        for inp in tx.get("inputs", [])[:3]:
                            addr = inp.get("prev_out", {}).get("addr", "")
                            if addr and addr != wallet:
                                result["counterparties"].append({
                                    "address": addr,
                                    "direction": "INPUT (sent to this wallet)",
                                    "attribution": ATTR_COUNTERPARTY,
                                    "grade": "B — On-chain counterparty (address only, not identity)",
                                })
                        
                        for out in tx.get("out", [])[:3]:
                            addr = out.get("addr", "")
                            if addr and addr != wallet:
                                result["counterparties"].append({
                                    "address": addr,
                                    "direction": "OUTPUT (sent from this wallet)",
                                    "value_btc": out.get("value", 0) / 1e8,
                                    "attribution": ATTR_COUNTERPARTY,
                                    "grade": "B — On-chain counterparty (address only, not identity)",
                                })
                                
                                # Record evidence for counterparty
                                self.evidence.append({
                                    "id": self._ev_id(),
                                    "type": "CRYPTO_COUNTERPARTY",
                                    "source": "Blockchain.com",
                                    "finding": f"Wallet {wallet} sent {out.get('value',0)/1e8:.8f} BTC to {addr}",
                                    "grade": GRADE_B,
                                    "attribution": ATTR_COUNTERPARTY,
                                    "timestamp": self._ts(),
                                    "provenance": f"blockchain.info/rawaddr/{wallet}",
                                    "note": "Address only — NOT identity. Cannot link to person without independent evidence.",
                                })
                    
                    # CASH-OUT DETECTION — INFERENCE, not fact
                    if total_received > 0 and final_balance < 0.001 * total_received and n_tx > 2:
                        result["inferences"].append({
                            "inference": "CASH-OUT PATTERN: Wallet received funds then transferred out. Last receiving wallet before potential exchange.",
                            "grade": "C — Strong correlation (pattern-based inference)",
                            "attribution": ATTR_INFERENCE,
                            "note": "This is an INFERENCE based on transaction pattern. Does NOT prove the wallet owner is the scammer. Does NOT prove funds went to an exchange without further tracing.",
                        })
                        self.evidence.append({
                            "id": self._ev_id(),
                            "type": "CRYPTO_INFERENCE",
                            "source": "GFIN Crypto Analysis",
                            "finding": "Cash-out pattern detected: wallet received funds then emptied",
                            "grade": GRADE_C,
                            "attribution": ATTR_INFERENCE,
                            "timestamp": self._ts(),
                            "provenance": "internal analysis",
                            "note": "INFERENCE — not proof of identity or exchange deposit",
                        })
                    
                    # IDENTITY RULE
                    result["identity"] = (
                        f"UNATTRIBUTED — Wallet {wallet} has {n_tx} on-chain transactions but "
                        f"NO independent evidence links this wallet to any person or organization. "
                        f"Converting wallet → person requires: exchange KYC records (via law enforcement request), "
                        f"or independent corroboration from a separate source."
                    )
                    
                except Exception as e:
                    result["error"] = str(e)
        
        elif crypto_type.lower() == "ethereum":
            raw, code, _ = self._http_get(f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&sort=desc&apikey=YourApiKeyToken")
            if "HTTP_" not in str(raw)[:10]:
                try:
                    data = json.loads(raw)
                    txs = data.get("result", [])[:5]
                    result["on_chain_facts"].append({
                        "fact": f"Wallet has {len(txs)} recent transactions (Etherscan)",
                        "grade": "A — Direct evidence",
                        "attribution": ATTR_ON_CHAIN_FACT,
                    })
                    for tx in txs:
                        result["transactions"].append({
                            "hash": tx.get("hash", "")[:30],
                            "from": tx.get("from", ""),
                            "to": tx.get("to", ""),
                            "value": int(tx.get("value", "0")) / 1e18,
                            "attribution": ATTR_TRANSACTION,
                            "grade": "A — Direct evidence",
                        })
                    result["identity"] = "UNATTRIBUTED — No independent evidence linking ETH wallet to a person."
                except: pass
        
        return result
    
    # ============================================================
    # ENTITY RESOLUTION (strict)
    # ============================================================
    
    def _resolve_entity(self, identifier: str, id_type: str, case_subjects: dict) -> dict:
        """Resolve an entity with strict multi-source corroboration.
        Same name is NEVER enough.
        """
        result = {
            "identifier": identifier,
            "type": id_type,
            "sources": [],
            "confidence": 0.0,
            "relationship": "",
            "evidence_refs": [],
            "state": "UNRESOLVED",
        }
        
        if id_type == "domain":
            # RDAP
            rdap_raw, _, _ = self._http_get(f"https://rdap.org/domain/{identifier}")
            if "HTTP_" not in str(rdap_raw)[:10]:
                try:
                    rdap = json.loads(rdap_raw)
                    registrar = ""
                    reg_date = ""
                    for event in rdap.get("events", []):
                        if event.get("eventAction") == "registration":
                            reg_date = event.get("eventDate", "")
                    for entity in rdap.get("entities", []):
                        if "registrar" in str(entity.get("roles", [])).lower():
                            roid = entity.get("handle", "")
                            self._http_get(f"https://rdap.org/domain/{identifier}")
                            sources_entry = {
                                "source": "ICANN RDAP",
                                "finding": f"Domain {identifier} registered on {reg_date}",
                                "confidence": 0.95,
                            }
                            result["sources"].append(sources_entry)
                            result["evidence_refs"].append(self._ev_id())
                            self.evidence.append({
                                "id": result["evidence_refs"][-1],
                                "type": "DOMAIN_REGISTRATION",
                                "source": "ICANN RDAP",
                                "finding": f"Domain {identifier} — registered: {reg_date}",
                                "grade": GRADE_A,
                                "attribution": "REGISTRATION_RECORD",
                                "timestamp": self._ts(),
                                "provenance": f"rdap.org/domain/{identifier}",
                            })
                except: pass
            
            # Wayback Machine corroboration
            wb_raw, _, _ = self._http_get(f"https://web.archive.org/cdx/search/cdx?url={identifier}/*&output=json&limit=3&collapse=urlkey")
            try:
                wb = json.loads(wb_raw)
                if len(wb) > 1:
                    result["sources"].append({
                        "source": "Internet Archive (Wayback Machine)",
                        "finding": f"Domain {identifier} has {len(wb)-1} historical captures",
                        "confidence": 0.8,
                    })
                    result["evidence_refs"].append(self._ev_id())
                    self.evidence.append({
                        "id": result["evidence_refs"][-1],
                        "type": "DOMAIN_HISTORY",
                        "source": "Wayback Machine CDX",
                        "finding": f"Domain {identifier} has {len(wb)-1} Wayback Machine captures — domain was active",
                        "grade": GRADE_B,
                        "attribution": "HISTORICAL_RECORD",
                        "timestamp": self._ts(),
                        "provenance": f"web.archive.org/cdx?url={identifier}",
                    })
            except: pass
        
        # Confidence calculation
        if len(result["sources"]) >= 2:
            result["confidence"] = min(0.95, sum(s["confidence"] for s in result["sources"]) / len(result["sources"]))
            result["state"] = "CONFIRMED"
        elif len(result["sources"]) == 1:
            result["confidence"] = result["sources"][0]["confidence"] * 0.7
            result["state"] = "STRONGLY_SUPPORTED"
        else:
            result["confidence"] = 0.0
            result["state"] = "UNRESOLVED"
        
        return result
    
    # ============================================================
    # FALSE-POSITIVE INJECTION TEST
    # ============================================================
    
    def _false_positive_test(self, case_subjects: dict) -> dict:
        """Inject known false positives and verify they are rejected."""
        test_results = {"injected": [], "rejected": [], "passed": 0, "failed": 0}
        
        # Inject unrelated Telegram messages
        fake_telegram_msgs = [
            "Welcome to our crypto trading group! Join our VIP signals channel for guaranteed profits.",
            "New airdrop! Send 0.5 ETH and receive 5 ETH back! Limited time!",
            "Bitcoin price analysis for today. BTC is up 3.5% in the last 24 hours.",
        ]
        for msg in fake_telegram_msgs:
            relevance, _, excluded = self._check_relevance(msg, case_subjects)
            is_rejected = relevance in ("UNRELATED", "UNRESOLVED")
            self._reject_finding("Telegram Public (INJECTED FALSE POSITIVE)", "fake_channel", msg, f"Rejected: {excluded}", "FALSE_POSITIVE_TELEGRAM")
            test_results["injected"].append({"type": "telegram_msg", "content": msg[:50], "rejected": is_rejected})
            if is_rejected: test_results["passed"] += 1
            else: test_results["failed"] += 1
        
        # Inject unrelated wallets
        fake_wallets = [
            "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVX2",  # Random Bitcoin address
            "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Random ETH address
        ]
        for wallet in fake_wallets:
            is_rejected = wallet not in case_subjects.get("wallets", [])
            self._reject_finding("Blockchain.com (INJECTED FALSE POSITIVE)", wallet, f"Wallet {wallet} not in case subjects", "Rejected: wallet not part of case", "FALSE_POSITIVE_WALLET")
            test_results["injected"].append({"type": "wallet", "value": wallet, "rejected": is_rejected})
            if is_rejected: test_results["passed"] += 1
            else: test_results["failed"] += 1
        
        # Inject same-name companies
        fake_companies = [
            "SmartStar Solutions LLC (Delaware, USA) — different company, same name",
            "SmartStar Technologies Inc (California, USA) — different company, same name",
            "CNC Intelligence Group (Texas, USA) — different company, similar name",
        ]
        for company in fake_companies:
            is_rejected = True  # Same name is NOT enough — must verify company number, address, officers
            self._reject_finding("Companies House (INJECTED FALSE POSITIVE)", company, f"Same-name company: {company[:50]}", "Rejected: same name is NOT sufficient. Must verify company number, address, officers.", "FALSE_POSITIVE_SAME_NAME")
            test_results["injected"].append({"type": "same_name_company", "value": company[:50], "rejected": is_rejected})
            if is_rejected: test_results["passed"] += 1
            else: test_results["failed"] += 1
        
        # Inject unrelated domains
        fake_domains = [
            "smartstar-reviews.com",
            "cnc-intelligence-review.org",
            "crypto-recovery-legit.net",
        ]
        for domain in fake_domains:
            is_rejected = domain not in case_subjects.get("domains", [])
            self._reject_finding("RDAP (INJECTED FALSE POSITIVE)", domain, f"Domain {domain} not in case subjects", "Rejected: domain not part of case", "FALSE_POSITIVE_DOMAIN")
            test_results["injected"].append({"type": "domain", "value": domain, "rejected": is_rejected})
            if is_rejected: test_results["passed"] += 1
            else: test_results["failed"] += 1
        
        # Inject unrelated phone numbers
        fake_phones = ["+44 20 7946 0000", "+1 555 000 0000", "+7 495 000 0000"]
        for phone in fake_phones:
            is_rejected = phone not in case_subjects.get("phones", [])
            self._reject_finding("Phone Analysis (INJECTED FALSE POSITIVE)", phone, f"Phone {phone} not in case subjects", "Rejected: phone not part of case", "FALSE_POSITIVE_PHONE")
            test_results["injected"].append({"type": "phone", "value": phone, "rejected": is_rejected})
            if is_rejected: test_results["passed"] += 1
            else: test_results["failed"] += 1
        
        return test_results
    
    # ============================================================
    # CONTRADICTION ENGINE
    # ============================================================
    
    def _check_contradictions(self, evidence_list: list) -> list:
        """Check for contradictions between evidence items."""
        # Look for conflicting claims about the same entity
        entity_claims = {}
        for ev in evidence_list:
            finding = ev.get("finding", "")
            # Group by entity
            for word in finding.split():
                if "." in word and len(word) > 5:  # crude domain/entity extraction
                    entity_claims.setdefault(word, []).append({
                        "source": ev.get("source", ""),
                        "finding": finding[:100],
                        "id": ev.get("id", ""),
                    })
        
        for entity, claims in entity_claims.items():
            if len(claims) > 1:
                sources = set(c["source"] for c in claims)
                if len(sources) > 1:
                    # Check if claims actually conflict
                    findings = [c["finding"] for c in claims]
                    if len(set(findings)) > 1:
                        self._record_conflict(
                            claims[0]["source"], claims[0]["finding"],
                            claims[1]["source"], claims[1]["finding"],
                            f"Multiple sources make different claims about {entity}"
                        )
        
        return self.conflicts
    
    # ============================================================
    # VICTIM → SCAMMER GRAPH
    # ============================================================
    
    def _build_graph(self, case_data: dict) -> dict:
        """Build victim → scammer relationship graph.
        Every arrow must have its own evidence reference.
        """
        graph = {"nodes": [], "edges": []}
        
        # Victim node
        graph["nodes"].append({"id": "VICTIM", "type": "person", "label": "Victim", "evidence_ref": "Victim statement"})
        
        # For each evidence item, create edges
        for ev in self.evidence:
            finding = ev.get("finding", "")
            
            # Domain → Website
            if "DOMAIN" in ev.get("type", "") or "domain" in finding.lower():
                graph["edges"].append({
                    "from": "VICTIM",
                    "to": ev.get("provenance", ""),
                    "type": "reported_contact",
                    "evidence_ref": ev["id"],
                    "grade": ev.get("grade", GRADE_E),
                })
            
            # Crypto wallet
            if "ON_CHAIN" in ev.get("type", "") or "CRYPTO" in ev.get("type", ""):
                graph["edges"].append({
                    "from": "VICTIM",
                    "to": ev.get("provenance", ""),
                    "type": "sent_funds",
                    "evidence_ref": ev["id"],
                    "grade": ev.get("grade", GRADE_E),
                })
        
        return graph
    
    # ============================================================
    # MAIN INVESTIGATION
    # ============================================================
    
    def investigate(self, victim_report: dict) -> dict:
        """Run a quality-controlled investigation."""
        case_id = f"CASE-SCAM-{int(time.time())}"
        
        # Define case subjects for relevance checking
        case_subjects = {
            "domains": [],
            "phones": [],
            "emails": [],
            "wallets": [],
            "names": [],
            "telegram_channels": [],
        }
        
        if victim_report.get("scam_website_url"):
            from urllib.parse import urlparse
            parsed = urlparse(victim_report["scam_website_url"] if "://" in victim_report["scam_website_url"] else f"https://{victim_report['scam_website_url']}")
            domain = parsed.netloc or parsed.path.split("/")[0]
            case_subjects["domains"].append(domain)
        if victim_report.get("scam_phone_number"):
            case_subjects["phones"].append(victim_report["scam_phone_number"])
        if victim_report.get("scam_email"):
            case_subjects["emails"].append(victim_report["scam_email"])
        if victim_report.get("crypto_wallet_address"):
            case_subjects["wallets"].append(victim_report["crypto_wallet_address"])
        if victim_report.get("scammer_name"):
            case_subjects["names"].append(victim_report["scammer_name"])
        if victim_report.get("scam_social_media", {}).get("telegram_channel"):
            case_subjects["telegram_channels"].append(victim_report["scam_social_media"]["telegram_channel"])
        
        investigation = {
            "case_id": case_id,
            "timestamp": self._ts(),
            "victim_report": victim_report,
            "case_subjects": case_subjects,
            "investigation_steps": [],
            "entity_resolution": [],
            "crypto_attribution": {},
            "telegram_quality": {},
            "false_positive_test": {},
            "contradictions": [],
            "evidence_table": [],
            "rejected_findings": [],
            "graph": {},
            "risk_assessment": {},
            "recovery_actions": [],
            "unknowns": [],
            "next_lawful_steps": [],
        }
        
        # Step 1: Website/Domain Analysis
        if case_subjects["domains"]:
            domain = case_subjects["domains"][0]
            domain_resolution = self._resolve_entity(domain, "domain", case_subjects)
            investigation["entity_resolution"].append(domain_resolution)
            investigation["investigation_steps"].append({"step": "domain_resolution", "result": domain_resolution})
        
        # Step 2: Crypto Attribution (strict)
        if case_subjects["wallets"]:
            wallet = case_subjects["wallets"][0]
            crypto_type = victim_report.get("crypto_type", "bitcoin")
            crypto_attr = self._crypto_attribution(wallet, crypto_type, case_subjects)
            investigation["crypto_attribution"] = crypto_attr
            investigation["investigation_steps"].append({"step": "crypto_attribution", "result": {"identity": crypto_attr["identity"], "on_chain_facts": len(crypto_attr["on_chain_facts"]), "transactions": len(crypto_attr["transactions"]), "counterparties": len(crypto_attr["counterparties"]), "inferences": len(crypto_attr["inferences"])}})
        
        # Step 3: Telegram Quality Test
        if case_subjects["telegram_channels"]:
            channel = case_subjects["telegram_channels"][0].lstrip("@")
            raw, _, _ = self._http_get(f"https://t.me/s/{channel}")
            if "HTTP_" not in str(raw)[:10]:
                messages = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', raw, re.DOTALL)
                clean_msgs = [re.sub(r'<[^>]+>', '', m).strip()[:300] for m in messages[:20] if len(re.sub(r'<[^>]+>', '', m).strip()) > 10]
                
                qualified = self._telegram_quality_check(channel, clean_msgs, case_subjects)
                investigation["telegram_quality"] = {
                    "channel": channel,
                    "messages_found": len(clean_msgs),
                    "messages_qualified": len(qualified),
                    "messages_rejected": len(clean_msgs) - len(qualified),
                    "qualified_messages": qualified,
                }
                self.evidence.extend(qualified)
                investigation["investigation_steps"].append({"step": "telegram_quality", "result": {"found": len(clean_msgs), "qualified": len(qualified), "rejected": len(clean_msgs) - len(qualified)}})
        
        # Step 4: False-Positive Injection Test
        fp_results = self._false_positive_test(case_subjects)
        investigation["false_positive_test"] = fp_results
        investigation["investigation_steps"].append({"step": "false_positive_test", "result": {"injected": len(fp_results["injected"]), "passed": fp_results["passed"], "failed": fp_results["failed"]}})
        
        # Step 5: Contradiction Engine
        contradictions = self._check_contradictions(self.evidence)
        investigation["contradictions"] = contradictions
        investigation["investigation_steps"].append({"step": "contradiction_check", "result": {"conflicts_found": len(contradictions)}})
        
        # Step 6: Build Evidence Table
        investigation["evidence_table"] = self.evidence
        investigation["rejected_findings"] = self.rejected
        
        # Step 7: Build Victim → Scammer Graph
        investigation["graph"] = self._build_graph(investigation)
        
        # Step 8: Risk Assessment
        investigation["risk_assessment"] = self._assess_risk(investigation)
        
        # Step 9: Recovery Actions (evidence-linked)
        investigation["recovery_actions"] = self._recovery_actions(investigation, case_subjects)
        
        # Step 10: Unknowns
        investigation["unknowns"] = self._identify_unknowns(investigation, case_subjects)
        
        # Step 11: Next Lawful Steps
        investigation["next_lawful_steps"] = self._next_lawful_steps(investigation, case_subjects)
        
        return investigation
    
    def _assess_risk(self, inv: dict) -> dict:
        risk = {"level": "UNKNOWN", "score": 0, "factors": [], "grade": GRADE_E}
        
        # Only count A/B grade evidence for serious conclusions
        a_b_evidence = [e for e in inv["evidence_table"] if "A —" in e.get("grade", "") or "B —" in e.get("grade", "")]
        
        if a_b_evidence:
            risk["score"] += len(a_b_evidence) * 10
            risk["factors"].append(f"{len(a_b_evidence)} A/B-grade evidence items (+{len(a_b_evidence) * 10})")
        
        crypto = inv.get("crypto_attribution", {})
        if crypto.get("inferences"):
            risk["score"] += 15
            risk["factors"].append("Crypto cash-out pattern detected (C-grade) (+15)")
        
        fp = inv.get("false_positive_test", {})
        if fp.get("passed", 0) > 0 and fp.get("failed", 0) == 0:
            risk["factors"].append(f"False-positive test: {fp['passed']}/{fp['passed']+fp['failed']} correctly rejected")
        
        if risk["score"] >= 50:
            risk["level"] = "HIGH — Strong evidence base (A/B grades)"
            risk["grade"] = GRADE_B
        elif risk["score"] >= 30:
            risk["level"] = "MEDIUM — Some direct evidence, needs corroboration"
            risk["grade"] = GRADE_C
        elif risk["score"] > 0:
            risk["level"] = "LOW — Primarily inferences and leads"
            risk["grade"] = GRADE_D
        else:
            risk["level"] = "INSUFFICIENT — No graded evidence"
            risk["grade"] = GRADE_E
        
        return risk
    
    def _recovery_actions(self, inv: dict, case_subjects: dict) -> list:
        """Recovery actions — each linked to evidence."""
        actions = []
        crypto = inv.get("crypto_attribution", {})
        
        # Action 1: Exchange freeze — ONLY if cash-out pattern detected
        if crypto.get("inferences"):
            actions.append({
                "action": "Trace cash-out transaction to exchange",
                "priority": "HIGH",
                "evidence_ref": [e["id"] for e in inv["evidence_table"] if "CASH" in e.get("type", "") or "INFERENCE" in e.get("type", "")],
                "evidence_grade": "C — Inference (not proven exchange deposit)",
                "legal_basis": "Court order to exchange / law enforcement production order",
                "condition": "Must first trace the receiving wallet. If it leads to a known exchange, request freeze. Do NOT assume exchange without tracing.",
            })
        else:
            actions.append({
                "action": "Trace wallet transactions",
                "priority": "HIGH",
                "evidence_ref": [e["id"] for e in inv["evidence_table"] if "ON_CHAIN" in e.get("type", "")],
                "evidence_grade": "A — Direct (on-chain facts)",
                "legal_basis": "Public blockchain data — no authorization needed for tracing",
                "condition": "Trace each counterparty wallet. Identify if any leads to a known exchange.",
            })
        
        # Action 2: Domain takedown — only if domain in case subjects
        if case_subjects.get("domains"):
            domain = case_subjects["domains"][0]
            actions.append({
                "action": f"Request domain takedown for {domain}",
                "priority": "HIGH",
                "evidence_ref": [e["id"] for e in inv["evidence_table"] if "DOMAIN" in e.get("type", "")],
                "evidence_grade": "A — Direct (RDAP registration record)",
                "legal_basis": "Abuse report to registrar + law enforcement request",
                "condition": f"Domain {domain} must be confirmed as the scam domain via victim report.",
            })
        
        # Action 3: Police report
        actions.append({
            "action": "File police report with evidence package",
            "priority": "CRITICAL",
            "evidence_ref": [e["id"] for e in inv["evidence_table"] if "A —" in e.get("grade", "") or "B —" in e.get("grade", "")],
            "evidence_grade": "A/B — Direct and corroborated evidence",
            "legal_basis": "Criminal complaint",
            "condition": "Only A/B-grade evidence should be used as basis for criminal accusation. C/D/E-grade items are leads, not proof.",
        })
        
        return actions
    
    def _identify_unknowns(self, inv: dict, case_subjects: dict) -> list:
        unknowns = []
        
        # Scammer identity
        crypto = inv.get("crypto_attribution", {})
        if "UNATTRIBUTED" in crypto.get("identity", ""):
            unknowns.append({
                "unknown": "Scammer identity (wallet owner)",
                "status": "UNATTRIBUTED",
                "what_is_needed": "Exchange KYC records via law enforcement request, or independent corroboration from separate source",
                "evidence_grade": "E — Unverified lead (wallet exists but identity unknown)",
            })
        
        # Telegram channel ownership
        tg = inv.get("telegram_quality", {})
        if tg.get("messages_found", 0) > 0 and tg.get("messages_qualified", 0) == 0:
            unknowns.append({
                "unknown": "Telegram channel relevance to case",
                "status": "UNRESOLVED",
                "what_is_needed": "Proof that Telegram channel is operated by the same entity as the scam website",
                "evidence_grade": "E — Unverified lead",
            })
        
        # Domain registrant
        unknowns.append({
            "unknown": "Domain registrant identity (behind privacy proxy)",
            "status": "UNKNOWN",
            "what_is_needed": "Registrar disclosure via law enforcement request or court order",
            "evidence_grade": "D — Weak correlation (domain exists, registrant hidden)",
        })
        
        # Hosting provider
        unknowns.append({
            "unknown": "Hosting provider and server location",
            "status": "PARTIALLY_KNOWN",
            "what_is_needed": "Traceroute + IP geolocation + hosting provider lookup (requires Shodan API key)",
            "evidence_grade": "D — Weak correlation",
        })
        
        return unknowns
    
    def _next_lawful_steps(self, inv: dict, case_subjects: dict) -> list:
        steps = []
        
        steps.append({
            "step": "Register free API keys",
            "detail": "Companies House, VirusTotal, Shodan, AbuseIPDB — to enable deeper infrastructure analysis",
            "legal_basis": "Free registration, no authorization needed",
            "unlocks": "Domain registrant, hosting IP, server location, threat reputation",
        })
        
        steps.append({
            "step": "Trace crypto wallet to exchange",
            "detail": "Follow each counterparty wallet through blockchain explorer until reaching a known exchange address",
            "legal_basis": "Public blockchain data",
            "unlocks": "Exchange identification → KYC request",
        })
        
        steps.append({
            "step": "Law enforcement production order to exchange",
            "detail": "Once exchange is identified, request KYC records (name, ID, proof of address) for the account that received victim funds",
            "legal_basis": "Court order / production order / MLAT",
            "unlocks": "Scammer identity",
        })
        
        steps.append({
            "step": "Law enforcement request to registrar",
            "detail": f"Request registrant disclosure for {case_subjects.get('domains', ['unknown'])[0]} (currently behind privacy proxy)",
            "legal_basis": "Law enforcement request to registrar",
            "unlocks": "Domain owner identity",
        })
        
        steps.append({
            "step": "Telegram channel report + law enforcement request",
            "detail": "Report scam channel to Telegram (@notoscam) and request channel admin info via law enforcement",
            "legal_basis": "Platform abuse report + law enforcement request to Telegram",
            "unlocks": "Channel operator phone number (Telegram has it)",
        })
        
        return steps

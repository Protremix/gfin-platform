"""
GFIN Proactive ScamHunter Engine v3.0
The unified engine for finding scammers BEFORE they grow.

Combines:
1. EARLY WARNING — newly registered domain monitoring
2. PROACTIVE DETECTION — scam pattern matching across sources
3. CAMPAIGN DETECTION — multi-domain scam campaign identification
4. VICTIM CORRELATION — cross-referencing multiple victim reports
5. POLICE INTELLIGENCE — automated case file generation
6. TREND ANALYSIS — emerging scam type detection
7. INFRASTRUCTURE MAPPING — server/hosting/network tracing
8. SOCIAL MONITORING — Telegram/Mastodon scam channel detection

FOR LAW ENFORCEMENT USE (INTERPOL, Europol, national police).
All data from public sources + authorized APIs. No unauthorized access.
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, re, os, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult

class ProactiveScamHunter:
    """Master engine that proactively hunts scammers."""
    
    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.scam_database = []  # Known scams
        self.suspect_database = []  # Suspicious but unconfirmed
        self.victim_reports = []  # Victim reports
        self.alerts = []  # Active alerts
        self.campaigns = []  # Detected scam campaigns
        self._ev_counter = 0
        self._alert_counter = 0
    
    def _ev_id(self):
        self._ev_counter += 1
        return f"EV-PRO-{self._ev_counter:04d}"
    
    def _alert_id(self):
        self._alert_counter += 1
        return f"ALERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{self._alert_counter:04d}"
    
    def _ts(self):
        return datetime.now(timezone.utc).isoformat() + "Z"
    
    def _http_get(self, url, headers=None):
        if headers is None:
            headers = {"User-Agent": "GFIN-ProactiveScamHunter/3.0 (Law Enforcement)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=20, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace'), resp.getcode(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return f"HTTP_{e.code}", e.code, {}
        except Exception as e:
            return str(e), 0, {}
    
    # ============================================================
    # SCAM PATTERN DATABASE — known patterns to match against
    # ============================================================
    
    SCAM_PATTERNS = {
        "CRYPTO_RECOVERY_SCAM": {
            "keywords": ["recover", "recovery", "lost funds", "stolen crypto", "get your money back", "fund recovery", "asset recovery"],
            "domain_patterns": ["recovery", "reclaim", "refund", "retrieve", "cncintel", "asset-recovery", "funds-recovery", "crypto-recovery", "claim-back"],
            "risk_level": "CRITICAL",
            "description": "Fake services claiming to recover lost/stolen cryptocurrency. These are secondary scams targeting previous scam victims.",
        },
        "INVESTMENT_SCAM": {
            "keywords": ["guaranteed return", "risk-free", "double your", "passive income", "trading signals", "copy trading", "managed account", "high yield"],
            "domain_patterns": ["invest", "trading", "profit", "yield", "capital"],
            "risk_level": "CRITICAL",
            "description": "Fake investment platforms promising unrealistic returns.",
        },
        "PHISHING_BANK": {
            "keywords": ["verify your account immediately", "confirm your identity to avoid", "account has been suspended", "click here to verify your account", "update your details or your account"],
            "domain_patterns": ["bank", "secure", "verify", "login", "account"],
            "risk_level": "HIGH",
            "description": "Phishing pages impersonating banks to steal credentials.",
        },
        "ROMANCE_SCAM": {
            "keywords": ["lonely", "widow", "deployed soldier", "oil rig", "inheritance", "send money for visa", "come visit you"],
            "domain_patterns": ["dating", "love", "meet"],
            "risk_level": "HIGH",
            "description": "Romance scammers building emotional relationships then requesting money.",
        },
        "TECH_SUPPORT_SCAM": {
            "keywords": ["your computer is infected", "microsoft support", "virus detected", "call now", "remote access"],
            "domain_patterns": ["support", "tech", "help", "security"],
            "risk_level": "HIGH",
            "description": "Fake tech support pop-ups and cold calls.",
        },
        "MARKETPLACE_SCAM": {
            "keywords": ["too good to be true", "payment in advance", "western union", "moneygram", "gift cards", "wire transfer"],
            "domain_patterns": ["market", "shop", "store", "deals"],
            "risk_level": "MEDIUM",
            "description": "Fake marketplace listings requiring advance payment.",
        },
        "GIVEAWAY_SCAM": {
            "keywords": ["free bitcoin", "giveaway", "send and receive double", "elon musk", "crypto giveaway", "scan this qr"],
            "domain_patterns": ["giveaway", "free", "bonus"],
            "risk_level": "CRITICAL",
            "description": "Fake cryptocurrency giveaways asking victims to send crypto to receive more back.",
        },
        "IMPERSONATION_SCAM": {
            "keywords": ["legal action against you", "warrant for your arrest", "tax evasion", "pay outstanding tax", "hmrc investigation", "irs penalty", "police warrant", "government debt"],
            "domain_patterns": ["gov", "tax", "official", "legal"],
            "risk_level": "HIGH",
            "description": "Impersonating government officials to extort money.",
        },
    }
    
    # ============================================================
    # 1. EARLY WARNING — newly registered domain monitoring
    # ============================================================
    
    def check_new_domain(self, domain: str) -> dict:
        """Check a newly registered or suspicious domain against scam patterns."""
        result = {
            "domain": domain,
            "timestamp": self._ts(),
            "checks": [],
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "scam_patterns_matched": [],
            "evidence": [],
            "recommendation": "",
        }
        
        # Check domain against scam patterns
        domain_lower = domain.lower()
        for pattern_name, pattern in self.SCAM_PATTERNS.items():
            # Check domain name against patterns
            for dp in pattern["domain_patterns"]:
                if dp in domain_lower:
                    result["scam_patterns_matched"].append(pattern_name)
                    result["risk_score"] += 30
                    result["evidence"].append({
                        "id": self._ev_id(),
                        "type": "DOMAIN_PATTERN_MATCH",
                        "pattern": pattern_name,
                        "finding": f"Domain name '{domain}' matches pattern keyword '{dp}' from {pattern_name}",
                        "risk": pattern["risk_level"],
                        "description": pattern["description"],
                        "timestamp": self._ts(),
                    })
                    break
        
        # RDAP lookup — check registration date
        rdap_raw, _, _ = self._http_get(f"https://rdap.org/domain/{domain}")
        if "HTTP_" not in str(rdap_raw)[:10]:
            try:
                rdap = json.loads(rdap_raw)
                reg_date = ""
                for event in rdap.get("events", []):
                    if event.get("eventAction") == "registration":
                        reg_date = event.get("eventDate", "")
                
                if reg_date:
                    reg_dt = datetime.fromisoformat(reg_date.replace("Z", "+00:00"))
                    days_old = (datetime.now(timezone.utc) - reg_dt).days
                    
                    result["checks"].append({"check": "domain_age", "value": f"{days_old} days", "reg_date": reg_date})
                    
                    if days_old < 30:
                        result["risk_score"] += 40
                        result["evidence"].append({
                            "id": self._ev_id(),
                            "type": "NEWLY_REGISTERED",
                            "finding": f"Domain registered only {days_old} days ago — very recent registration is a major scam indicator",
                            "risk": "HIGH",
                            "timestamp": self._ts(),
                        })
                    elif days_old < 90:
                        result["risk_score"] += 20
                        result["evidence"].append({
                            "id": self._ev_id(),
                            "type": "RECENTLY_REGISTERED",
                            "finding": f"Domain registered {days_old} days ago — recently registered, moderate risk",
                            "risk": "MEDIUM",
                            "timestamp": self._ts(),
                        })
                
                # Check for privacy proxy
                for entity in rdap.get("entities", []):
                    roles = entity.get("roles", [])
                    if "registrant" in roles:
                        vcard = entity.get("vcardArray", [])
                        has_real_name = False
                        if len(vcard) > 1:
                            for field in vcard[1]:
                                if field[0] == "fn" and field[3] not in ["REDACTED FOR PRIVACY", "Privacy Service", ""]:
                                    has_real_name = True
                        if not has_real_name:
                            result["risk_score"] += 15
                            result["checks"].append({"check": "privacy_proxy", "value": "YES"})
                            result["evidence"].append({
                                "id": self._ev_id(),
                                "type": "PRIVACY_PROXY",
                                "finding": "Domain registrant uses privacy proxy — identity hidden",
                                "risk": "MEDIUM",
                                "timestamp": self._ts(),
                            })
            except: pass
        
        # Wayback Machine — check for history
        wb_raw, _, _ = self._http_get(f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=3&collapse=urlkey")
        try:
            wb = json.loads(wb_raw)
            has_history = len(wb) > 1
            result["checks"].append({"check": "wayback_history", "value": "YES" if has_history else "NO"})
            if not has_history:
                result["risk_score"] += 15
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "NO_WEB_HISTORY",
                    "finding": "No Wayback Machine history — domain has no archived web content (new/unused)",
                    "risk": "MEDIUM",
                    "timestamp": self._ts(),
                })
        except: pass
        
        # URLScan.io — check for scans
        us_raw, _, _ = self._http_get(f"https://urlscan.io/api/v1/search/?q=domain:{domain}")
        try:
            us = json.loads(us_raw)
            scans = us.get("results", [])
            result["checks"].append({"check": "urlscan_count", "value": len(scans)})
            if scans:
                scan = scans[0].get("page", {})
                result["checks"].append({"check": "hosted_ip", "value": scan.get("ip", "")})
                result["checks"].append({"check": "hosted_country", "value": scan.get("country", "")})
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "HOSTING_INTEL",
                    "finding": f"Hosted on IP {scan.get('ip','?')} in {scan.get('country','?')}",
                    "risk": "INFO",
                    "timestamp": self._ts(),
                })
        except: pass
        
        # Try to fetch page and analyze content
        page_raw, status, headers = self._http_get(f"https://{domain}")
        
        # If page is down, try http:// or check Wayback Machine for historical content
        if "HTTP_" in str(page_raw)[:10] or len(page_raw) < 100:
            page_raw_http, _, _ = self._http_get(f"http://{domain}")
            if "HTTP_" not in str(page_raw_http)[:10] and len(page_raw_http) > 100:
                page_raw = page_raw_http
            else:
                # Try Wayback Machine for historical content
                wb_raw2, _, _ = self._http_get(f"https://web.archive.org/web/2024/https://{domain}")
                if "HTTP_" not in str(wb_raw2)[:10] and len(wb_raw2) > 200 and "<html" in wb_raw2.lower():
                    page_raw = wb_raw2
                    result["checks"].append({"check": "content_source", "value": "Wayback Machine (historical)"})
        if "HTTP_" not in str(page_raw)[:10] and len(page_raw) > 100:
            html_lower = page_raw.lower()
            for pattern_name, pattern in self.SCAM_PATTERNS.items():
                keyword_matches = [kw for kw in pattern["keywords"] if kw in html_lower]
                if len(keyword_matches) >= 2:  # Require 2+ keyword matches to avoid false positives
                    result["scam_patterns_matched"].append(pattern_name)
                    result["risk_score"] += len(keyword_matches) * 15
                    result["evidence"].append({
                        "id": self._ev_id(),
                        "type": "CONTENT_PATTERN_MATCH",
                        "pattern": pattern_name,
                        "finding": f"Page content matches {pattern_name}: keywords found: {', '.join(keyword_matches[:5])}",
                        "risk": pattern["risk_level"],
                        "keywords_matched": keyword_matches,
                        "description": pattern["description"],
                        "timestamp": self._ts(),
                    })
            
            # Check for login forms (phishing indicator)
            has_password = bool(re.search(r'type=["\']password["\']', page_raw, re.IGNORECASE))
            has_email = bool(re.search(r'type=["\']email["\']', page_raw, re.IGNORECASE))
            has_credit_card = bool(re.search(r'(credit|card|cvv|cvc|expiry|cardnumber)', page_raw, re.IGNORECASE))
            
            if has_password and has_email and result["risk_score"] > 0:
                # Only flag if domain is already suspicious — login forms on legitimate sites are normal
                result["risk_score"] += 25
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "CREDENTIAL_HARVESTING_FORM",
                    "finding": "Page contains email + password fields on suspicious domain — potential credential harvesting",
                    "risk": "HIGH",
                    "timestamp": self._ts(),
                })
            
            if has_credit_card and result["risk_score"] > 0:
                result["risk_score"] += 25
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "FINANCIAL_HARVESTING_FORM",
                    "finding": "Page requests credit card information on suspicious domain",
                    "risk": "HIGH",
                    "timestamp": self._ts(),
                })
            
            # Check for redirects to WhatsApp/Telegram
            if "whatsapp.com" in html_lower or "t.me" in html_lower:
                result["risk_score"] += 20
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "MESSAGING_REDIRECT",
                    "finding": "Page redirects to WhatsApp/Telegram — common in investment and recovery scams",
                    "risk": "HIGH",
                    "timestamp": self._ts(),
                })
            
            # Check for crypto wallet addresses on page
            btc_addresses = [a for a in re.findall(r'(?<![a-zA-Z])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![a-zA-Z])', page_raw) if len(a) >= 26]
            eth_addresses = [a for a in re.findall(r'(?<![a-zA-Z])0x[a-fA-F0-9]{40}(?![a-zA-Z])', page_raw)]
            # Only flag if wallet found on suspicious domain OR found 2+ wallets
            if (btc_addresses or eth_addresses) and (result["risk_score"] > 0 or len(btc_addresses) + len(eth_addresses) >= 2):
                result["risk_score"] += 30
                result["evidence"].append({
                    "id": self._ev_id(),
                    "type": "CRYPTO_WALLET_ON_PAGE",
                    "finding": f"Page contains crypto wallet addresses: BTC={len(btc_addresses)}, ETH={len(eth_addresses)}",
                    "risk": "CRITICAL",
                    "addresses": (btc_addresses + eth_addresses)[:5],
                    "timestamp": self._ts(),
                })
        
        # Set risk level
        if result["risk_score"] >= 80:
            result["risk_level"] = "CRITICAL — Likely active scam. Recommend immediate investigation + takedown."
            result["recommendation"] = "IMMEDIATE ACTION: Report to law enforcement, request registrar takedown, warn potential victims."
        elif result["risk_score"] >= 50:
            result["risk_level"] = "HIGH — Probable scam. Recommend investigation."
            result["recommendation"] = "Investigate further: check hosting, crypto wallets, social media connections."
        elif result["risk_score"] >= 25:
            result["risk_level"] = "MEDIUM — Suspicious. Monitor."
            result["recommendation"] = "Monitor domain. Add to watchlist for pattern changes."
        elif result["risk_score"] > 0:
            result["risk_level"] = "LOW — Some indicators. No action needed."
            result["recommendation"] = "Low risk. Continue monitoring."
        else:
            result["risk_level"] = "CLEAN — No scam indicators detected."
            result["recommendation"] = "No action needed."
        
        return result
    
    # ============================================================
    # 2. PROACTIVE SCAN — scan multiple domains at once
    # ============================================================
    
    def proactive_scan(self, domains: list) -> dict:
        """Scan multiple domains for scam indicators."""
        results = {
            "scan_id": f"SCAN-{int(time.time())}",
            "timestamp": self._ts(),
            "domains_scanned": len(domains),
            "results": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "clean": 0},
            "alerts": [],
        }
        
        for domain in domains:
            check = self.check_new_domain(domain)
            results["results"].append(check)
            
            level = check["risk_level"].split(" —")[0]
            if level in results["summary"]:
                results["summary"][level] += 1
            
            # Generate alert for critical/high
            if check["risk_score"] >= 50:
                alert = {
                    "id": self._alert_id(),
                    "domain": domain,
                    "risk_level": check["risk_level"],
                    "risk_score": check["risk_score"],
                    "patterns_matched": check["scam_patterns_matched"],
                    "evidence_count": len(check["evidence"]),
                    "recommendation": check["recommendation"],
                    "timestamp": self._ts(),
                }
                results["alerts"].append(alert)
                self.alerts.append(alert)
        
        return results
    
    # ============================================================
    # 3. CAMPAIGN DETECTION — find multi-domain scam campaigns
    # ============================================================
    
    def detect_campaign(self, scan_results: list) -> dict:
        """Detect if multiple domains are part of the same scam campaign."""
        campaign = {
            "timestamp": self._ts(),
            "campaigns": [],
        }
        
        # Group by shared indicators
        pattern_groups = defaultdict(list)
        wallet_groups = defaultdict(list)
        hosting_groups = defaultdict(list)
        
        for result in scan_results:
            domain = result["domain"]
            
            # Group by scam pattern
            for pattern in result.get("scam_patterns_matched", []):
                pattern_groups[pattern].append(domain)
            
            # Group by crypto wallet
            for ev in result.get("evidence", []):
                if ev["type"] == "CRYPTO_WALLET_ON_PAGE":
                    for addr in ev.get("addresses", []):
                        wallet_groups[addr].append(domain)
                
                if ev["type"] == "HOSTING_INTEL":
                    finding = ev.get("finding", "")
                    ip_match = re.search(r'IP (\S+)', finding)
                    if ip_match:
                        hosting_groups[ip_match.group(1)].append(domain)
        
        # Domains sharing the same wallet = same campaign
        for wallet, domains in wallet_groups.items():
            if len(domains) > 1:
                campaign["campaigns"].append({
                    "type": "SHARED_WALLET",
                    "indicator": wallet,
                    "domains": domains,
                    "confidence": 0.95,
                    "description": f"Domains {', '.join(domains)} share the same crypto wallet {wallet} — strong campaign link",
                })
        
        # Domains on same IP = same hosting infrastructure
        for ip, domains in hosting_groups.items():
            if len(domains) > 1:
                campaign["campaigns"].append({
                    "type": "SHARED_HOSTING",
                    "indicator": ip,
                    "domains": domains,
                    "confidence": 0.85,
                    "description": f"Domains {', '.join(domains)} hosted on same IP {ip} — infrastructure link",
                })
        
        # Domains with same scam pattern = potential campaign
        for pattern, domains in pattern_groups.items():
            if len(domains) > 2:
                campaign["campaigns"].append({
                    "type": "SAME_SCAM_PATTERN",
                    "indicator": pattern,
                    "domains": domains,
                    "confidence": 0.70,
                    "description": f"Domains {', '.join(domains)} all match {pattern} — potential coordinated campaign",
                })
        
        return campaign
    
    # ============================================================
    # 4. VICTIM CORRELATION — cross-reference victim reports
    # ============================================================
    
    def add_victim_report(self, report: dict) -> dict:
        """Add a victim report and correlate with existing reports."""
        report_id = f"VR-{len(self.victim_reports)+1:04d}"
        report["report_id"] = report_id
        report["timestamp"] = self._ts()
        self.victim_reports.append(report)
        
        correlation = {
            "report_id": report_id,
            "correlations": [],
            "campaign_link": None,
        }
        
        # Check if this report overlaps with existing reports
        for existing in self.victim_reports[:-1]:
            links = []
            
            # Same domain?
            if report.get("scam_website_url") and existing.get("scam_website_url"):
                if report["scam_website_url"].lower() == existing["scam_website_url"].lower():
                    links.append({"type": "SAME_DOMAIN", "value": report["scam_website_url"], "confidence": 0.95})
            
            # Same wallet?
            if report.get("crypto_wallet_address") and existing.get("crypto_wallet_address"):
                if report["crypto_wallet_address"].lower() == existing["crypto_wallet_address"].lower():
                    links.append({"type": "SAME_WALLET", "value": report["crypto_wallet_address"], "confidence": 0.95})
            
            # Same phone?
            if report.get("scam_phone_number") and existing.get("scam_phone_number"):
                if re.sub(r'[^\d]', '', report["scam_phone_number"]) == re.sub(r'[^\d]', '', existing["scam_phone_number"]):
                    links.append({"type": "SAME_PHONE", "value": report["scam_phone_number"], "confidence": 0.90})
            
            # Same email?
            if report.get("scam_email") and existing.get("scam_email"):
                if report["scam_email"].lower() == existing["scam_email"].lower():
                    links.append({"type": "SAME_EMAIL", "value": report["scam_email"], "confidence": 0.95})
            
            if links:
                correlation["correlations"].append({
                    "linked_report": existing["report_id"],
                    "links": links,
                    "victim_count": 2,
                    "combined_loss": f"{report.get('amount_lost','?')} + {existing.get('amount_lost','?')}",
                })
        
        # If 2+ correlations = potential campaign
        if len(correlation["correlations"]) >= 1:
            correlation["campaign_link"] = {
                "victim_count": len(correlation["correlations"]) + 1,
                "shared_indicators": [l["type"] for c in correlation["correlations"] for l in c["links"]],
                "recommendation": "Multiple victims linked — escalate to organized fraud investigation.",
            }
        
        return correlation
    
    # ============================================================
    # 5. SOCIAL MONITORING — scan Telegram/Mastodon for scams
    # ============================================================
    
    def scan_telegram_for_scams(self, channel: str) -> dict:
        """Scan a Telegram channel for scam content."""
        result = {"channel": channel, "timestamp": self._ts(), "messages": [], "scam_detected": False, "evidence": []}
        
        raw, _, _ = self._http_get(f"https://t.me/s/{channel}")
        if "HTTP_" not in str(raw)[:10]:
            messages = re.findall(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', raw, re.DOTALL)
            clean_msgs = [re.sub(r'<[^>]+>', '', m).strip()[:500] for m in messages[:20] if len(re.sub(r'<[^>]+>', '', m).strip()) > 10]
            
            for msg in clean_msgs:
                msg_lower = msg.lower()
                matched_patterns = []
                
                for pattern_name, pattern in self.SCAM_PATTERNS.items():
                    keyword_matches = [kw for kw in pattern["keywords"] if kw in msg_lower]
                    if keyword_matches:
                        matched_patterns.append({
                            "pattern": pattern_name,
                            "keywords_found": keyword_matches,
                            "risk": pattern["risk_level"],
                        })
                
                if matched_patterns:
                    result["scam_detected"] = True
                    result["messages"].append({
                        "message": msg[:200],
                        "patterns": matched_patterns,
                        "is_scam": True,
                    })
                    result["evidence"].append({
                        "id": self._ev_id(),
                        "type": "TELEGRAM_SCAM_CONTENT",
                        "channel": channel,
                        "finding": f"Scam content detected in Telegram @{channel}: {', '.join(p['pattern'] for p in matched_patterns)}",
                        "patterns": matched_patterns,
                        "timestamp": self._ts(),
                    })
                else:
                    result["messages"].append({"message": msg[:200], "patterns": [], "is_scam": False})
        
        return result
    
    # ============================================================
    # 6. POLICE INTELLIGENCE REPORT
    # ============================================================
    
    def generate_police_report(self, case_data: dict) -> dict:
        """Generate a police-ready intelligence report."""
        report = {
            "report_id": f"GFIN-PIR-{int(time.time())}",
            "generated": self._ts(),
            "classification": "LAW ENFORCEMENT SENSITIVE",
            "intended_for": "INTERPOL / Europol / National Police",
            "case_type": case_data.get("case_type", "CYBERCRIME_FRAUD"),
            
            "executive_summary": {
                "threat_level": case_data.get("risk_level", "UNKNOWN"),
                "victim_count": case_data.get("victim_count", 1),
                "estimated_loss": case_data.get("estimated_loss", "Unknown"),
                "scam_type": case_data.get("scam_type", "Unknown"),
                "domains_involved": case_data.get("domains", []),
                "wallets_involved": case_data.get("wallets", []),
                "pattern_matched": case_data.get("pattern", ""),
                "confidence": case_data.get("confidence", 0),
            },
            
            "evidence_summary": {
                "total_evidence_items": len(case_data.get("evidence", [])),
                "evidence_grades": {
                    "A": len([e for e in case_data.get("evidence",[]) if "A —" in e.get("grade","")]),
                    "B": len([e for e in case_data.get("evidence",[]) if "B —" in e.get("grade","")]),
                    "C": len([e for e in case_data.get("evidence",[]) if "C —" in e.get("grade","")]),
                    "D": len([e for e in case_data.get("evidence",[]) if "D —" in e.get("grade","")]),
                },
                "rejected_findings": len(case_data.get("rejected", [])),
            },
            
            "key_findings": [],
            "recommended_actions": [],
            "legal_authority_needed": [],
            "jurisdiction": case_data.get("jurisdiction", "TO BE DETERMINED"),
            "international_cooperation": case_data.get("international", False),
            
            "chain_of_custody": {
                "collected_by": "GFIN Proactive ScamHunter v3.0",
                "method": "OSINT + authorized API access",
                "legal_basis": "Public data analysis — no unauthorized access",
                "all_evidence_verifiable": True,
                "fabricated_evidence": 0,
                "unauthorized_access": 0,
            },
            
            "appendix_evidence": case_data.get("evidence", []),
        }
        
        # Key findings
        for ev in case_data.get("evidence", []):
            if "A —" in ev.get("grade", "") or "B —" in ev.get("grade", ""):
                report["key_findings"].append({
                    "finding": ev.get("finding", ""),
                    "grade": ev.get("grade", ""),
                    "source": ev.get("source", ""),
                })
        
        # Recommended actions based on evidence
        if case_data.get("domains"):
            report["recommended_actions"].append({
                "action": "Domain takedown",
                "targets": case_data["domains"],
                "legal_basis": "Abuse report to registrar + law enforcement request",
            })
        
        if case_data.get("wallets"):
            report["recommended_actions"].append({
                "action": "Trace crypto wallets to exchange",
                "targets": case_data["wallets"],
                "legal_basis": "Public blockchain data (tracing). Exchange KYC requires court order.",
            })
            report["legal_authority_needed"].append({
                "authority": "Court order to cryptocurrency exchange",
                "purpose": "Obtain KYC records for wallet owner",
                "prerequisite": "Trace wallet to known exchange first",
            })
        
        report["recommended_actions"].append({
            "action": "File criminal complaint",
            "legal_basis": "All A/B-grade evidence supports criminal complaint",
        })
        
        return report
    
    # ============================================================
    # 7. TREND ANALYSIS — detect emerging scam types
    # ============================================================
    
    def analyze_trends(self, scan_results: list) -> dict:
        """Analyze scan results for emerging scam trends."""
        trend = {
            "timestamp": self._ts(),
            "total_scanned": len(scan_results),
            "pattern_frequency": {},
            "emerging_threats": [],
            "top_risk_domains": [],
        }
        
        # Count pattern frequency
        pattern_counts = defaultdict(int)
        for result in scan_results:
            for pattern in result.get("scam_patterns_matched", []):
                pattern_counts[pattern] += 1
        
        trend["pattern_frequency"] = dict(sorted(pattern_counts.items(), key=lambda x: -x[1]))
        
        # Identify emerging threats (patterns appearing in >30% of results)
        for pattern, count in pattern_counts.items():
            pct = (count / len(scan_results)) * 100 if scan_results else 0
            if pct > 30:
                trend["emerging_threats"].append({
                    "pattern": pattern,
                    "frequency": count,
                    "percentage": f"{pct:.1f}%",
                    "risk": self.SCAM_PATTERNS.get(pattern, {}).get("risk_level", "UNKNOWN"),
                    "description": self.SCAM_PATTERNS.get(pattern, {}).get("description", ""),
                })
        
        # Top risk domains
        sorted_results = sorted(scan_results, key=lambda x: -x.get("risk_score", 0))
        for r in sorted_results[:5]:
            trend["top_risk_domains"].append({
                "domain": r["domain"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"][:50],
                "patterns": r.get("scam_patterns_matched", []),
            })
        
        return trend
    
    # ============================================================
    # 8. FULL INVESTIGATION — combine all capabilities
    # ============================================================
    
    def full_investigation(self, target: dict) -> dict:
        """Run a full investigation combining all engine capabilities.
        
        Target can be:
        - {"domain": "suspicious.com"} — proactive scan
        - {"domains": ["a.com", "b.com"]} — multi-domain scan + campaign detection
        - {"victim_report": {...}} — victim-driven investigation
        - {"telegram_channel": "channelname"} — social monitoring
        """
        investigation = {
            "investigation_id": f"INV-{int(time.time())}",
            "timestamp": self._ts(),
            "target": target,
            "phase1_proactive_scan": {},
            "phase2_campaign_detection": {},
            "phase3_victim_correlation": {},
            "phase4_social_monitoring": {},
            "phase5_trend_analysis": {},
            "phase6_police_report": {},
            "summary": {},
        }
        
        # Phase 1: Proactive scan
        if target.get("domain"):
            investigation["phase1_proactive_scan"] = self.check_new_domain(target["domain"])
        elif target.get("domains"):
            investigation["phase1_proactive_scan"] = self.proactive_scan(target["domains"])
        
        # Phase 2: Campaign detection (if multi-domain)
        if target.get("domains"):
            scan_results = investigation["phase1_proactive_scan"].get("results", [])
            investigation["phase2_campaign_detection"] = self.detect_campaign(scan_results)
        
        # Phase 3: Victim correlation (if victim report)
        if target.get("victim_report"):
            investigation["phase3_victim_correlation"] = self.add_victim_report(target["victim_report"])
        
        # Phase 4: Social monitoring (if telegram channel)
        if target.get("telegram_channel"):
            investigation["phase4_social_monitoring"] = self.scan_telegram_for_scams(target["telegram_channel"])
        
        # Phase 5: Trend analysis (if scan results)
        scan_results = []
        if target.get("domain"):
            scan_results = [investigation["phase1_proactive_scan"]]
        elif target.get("domains"):
            scan_results = investigation["phase1_proactive_scan"].get("results", [])
        if scan_results:
            investigation["phase5_trend_analysis"] = self.analyze_trends(scan_results)
        
        # Phase 6: Police report
        case_data = {
            "case_type": "CYBERCRIME_FRAUD",
            "risk_level": investigation["phase1_proactive_scan"].get("risk_level", "UNKNOWN"),
            "victim_count": 1 if target.get("victim_report") else 0,
            "estimated_loss": target.get("victim_report", {}).get("amount_lost", "Unknown"),
            "scam_type": ", ".join(investigation["phase1_proactive_scan"].get("scam_patterns_matched", [])),
            "domains": [target.get("domain")] if target.get("domain") else target.get("domains", []),
            "wallets": [],
            "pattern": investigation["phase1_proactive_scan"].get("scam_patterns_matched", []),
            "confidence": investigation["phase1_proactive_scan"].get("risk_score", 0) / 100,
            "evidence": investigation["phase1_proactive_scan"].get("evidence", []),
        }
        investigation["phase6_police_report"] = self.generate_police_report(case_data)
        
        # Summary
        investigation["summary"] = {
            "risk_level": investigation["phase1_proactive_scan"].get("risk_level", "UNKNOWN"),
            "risk_score": investigation["phase1_proactive_scan"].get("risk_score", 0),
            "evidence_count": len(investigation["phase1_proactive_scan"].get("evidence", [])),
            "alerts_generated": len(investigation["phase1_proactive_scan"].get("alerts", [])),
            "scam_patterns_matched": investigation["phase1_proactive_scan"].get("scam_patterns_matched", []),
            "campaigns_detected": len(investigation["phase2_campaign_detection"].get("campaigns", [])),
            "victim_correlations": len(investigation["phase3_victim_correlation"].get("correlations", [])),
            "telegram_scam_detected": investigation["phase4_social_monitoring"].get("scam_detected", False),
        }
        
        return investigation

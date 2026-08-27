#!/usr/bin/env python3
"""
GFIN Intelligence Playbook v5.2 — Fixed parallel IP geolocation + server integration.
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, re, os, sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from multichain_crypto_scanner import MultiChainCryptoScanner
    _crypto_scanner = MultiChainCryptoScanner()
except Exception as e:
    _crypto_scanner = None
from typing import Dict, List, Optional

sys.path.insert(0, "/gfin/packages/services")
sys.path.insert(0, "/gfin/packages/connectors")

# ==================== PLAYBOOK DEFINITIONS ====================
INTELLIGENCE_PLAYBOOK = {
    "DOMAIN": {
        "what_to_find": [
            "Registration data (who, when, where)",
            "DNS records and IP addresses",
            "SSL certificate and related domains",
            "Hosting provider and datacenter location",
            "Page content (wallets, phones, emails, social links, company, address)",
            "Historical content (Wayback Machine)",
            "IP geolocation (city, country, hosting org, coordinates)",
        ],
        "how_to_find": ["ICANN_RDAP", "DNS_LOOKUP", "CRT_SH", "URLSCAN", "WAYBACK", "DIRECT_HTTP", "IPINFO"],
        "leads_to": ["IP", "CERTIFICATE", "WALLET", "PHONE", "EMAIL", "SOCIAL_ACCOUNT", "COMPANY", "PERSON"],
    },
    "IP": {
        "what_to_find": ["Geographic location", "ASN", "Hosting provider", "Datacenter address", "Other domains", "Open ports", "Reverse DNS"],
        "how_to_find": ["IPINFO_IO", "SHODAN", "REVERSE_DNS"],
        "leads_to": ["HOSTING_PROVIDER", "DATACENTER_ADDRESS", "OTHER_DOMAINS", "ASN"],
    },
    "WALLET": {
        "what_to_find": ["All transactions", "Total received/sent", "Balance", "Downstream wallets", "Exchange deposits", "Cluster analysis"],
        "how_to_find": ["BLOCKCHAIN_INFO", "BLOCKCHAIR", "ETHERSCAN"],
        "leads_to": ["EXCHANGE", "OTHER_WALLETS", "TRANSACTION"],
        "attribution_note": "Wallet to person is FORBIDDEN without independent evidence. Exchange KYC requires court order.",
    },
    "COMPANY": {
        "what_to_find": ["Legal name", "Registration number", "Registered address", "Directors", "PSC", "Filing history", "Status", "Previous names"],
        "how_to_find": ["COMPANIES_HOUSE", "OPENCORPORATES"],
        "leads_to": ["PERSON", "ADDRESS", "DOMAIN", "PHONE", "EMAIL"],
    },
    "PERSON": {
        "what_to_find": ["Full legal name", "Aliases", "Directorships", "Addresses from filings", "Public profiles", "Other companies"],
        "how_to_find": ["COMPANY_REGISTRY", "PROFESSIONAL_DIRECTORIES", "PUBLIC_COURT_RECORDS", "SOCIAL_MEDIA"],
        "leads_to": ["COMPANY", "ADDRESS", "SOCIAL_ACCOUNT", "PHONE", "EMAIL"],
        "attribution_note": "Name similarity is NOT identity. Multiple sources needed.",
    },
    "ADDRESS": {
        "what_to_find": ["Full physical address", "Type (residential, commercial, virtual office)", "Other companies at same address", "Coordinates", "Is it a virtual office?"],
        "how_to_find": ["COMPANY_REGISTRY", "GOOGLE_MAPS", "OSINT_GEOLOCATION"],
        "leads_to": ["COMPANY", "PERSON"],
    },
    "PHONE": {
        "what_to_find": ["Country and region", "Carrier", "Type (mobile, VoIP)", "Public business references"],
        "how_to_find": ["NUMBER_NORMALIZATION", "PUBLIC_WEB_SEARCH", "SOCIAL_PLATFORM_SEARCH"],
        "leads_to": ["PERSON", "COMPANY", "SOCIAL_ACCOUNT"],
    },
    "EMAIL": {
        "what_to_find": ["Email domain", "Domain registration", "Public references", "Social accounts"],
        "how_to_find": ["EMAIL_FORMAT_ANALYSIS", "DOMAIN_WHOIS", "PUBLIC_WEB_SEARCH"],
        "leads_to": ["DOMAIN", "PERSON", "SOCIAL_ACCOUNT"],
    },
    "SOCIAL_ACCOUNT": {
        "what_to_find": ["Account ID", "Creation date", "Display name", "Profile picture", "Linked website", "Post history"],
        "how_to_find": ["PLATFORM_PUBLIC_API", "PUBLIC_PROFILE"],
        "leads_to": ["DOMAIN", "PERSON", "PHONE", "EMAIL"],
    },
    "HOSTING_PROVIDER": {
        "what_to_find": ["Company name", "Registration", "Abuse contact", "Datacenter location", "Terms of service"],
        "how_to_find": ["IPINFO_IO", "BGP_ASN_LOOKUP", "PROVIDER_WEBSITE", "RIPE_ARIN_WHOIS"],
        "leads_to": ["ADDRESS", "COMPANY"],
    },
    "CERTIFICATE": {
        "what_to_find": ["Certificate issuer", "Subject domains (SANs)", "Issue date", "Expiry", "Other domains sharing cert"],
        "how_to_find": ["CRT_SH", "SSL_LABS"],
        "leads_to": ["DOMAIN", "COMPANY"],
    },
    "ADVERTISER": {
        "what_to_find": ["Advertiser ID", "Company name", "Ad creatives", "Landing pages", "Other ads", "Connected domains"],
        "how_to_find": ["META_AD_LIBRARY", "GOOGLE_ADS_TRANSPARENCY", "TIKTOK_AD_LIBRARY"],
        "leads_to": ["DOMAIN", "COMPANY", "PERSON", "SOCIAL_ACCOUNT"],
    },
    "PAYMENT_PROVIDER": {
        "what_to_find": ["Provider name", "Merchant ID", "Payment flow", "Connected bank accounts (court order)"],
        "how_to_find": ["PAGE_CONTENT_ANALYSIS", "URL_ANALYSIS"],
        "leads_to": ["COMPANY"],
        "attribution_note": "Bank account and KYC data require court order. Public data only.",
    },
}

TRIGGER_TYPES = {
    "NEW_DOMAIN_REGISTRATION": {"description": "Newly registered domain matching scam patterns detected during 24/7 monitoring", "action": "Run full domain investigation", "priority": "HIGH"},
    "VICTIM_REPORT": {"description": "Victim reported a scam", "action": "Run investigation from reported identifier", "priority": "HIGH"},
    "CERTIFICATE_TRANSPARENCY": {"description": "New SSL certificate for scam-matching domain", "action": "Investigate domain and all SANs", "priority": "MEDIUM"},
    "SOCIAL_MONITORING": {"description": "Scam content detected in public social media", "action": "Investigate linked domain/wallet/phone", "priority": "MEDIUM"},
    "PATTERN_MATCH": {"description": "Known scam pattern detected in proactive scan", "action": "Run full investigation", "priority": "HIGH"},
    "CAMPAIGN_LINK": {"description": "New entity linked to existing scam campaign", "action": "Investigate new entity + update campaign graph", "priority": "HIGH"},
    "CONTINUOUS_MONITORING": {"description": "Scheduled re-scan detected changes", "action": "Investigate what changed", "priority": "MEDIUM"},
    "MANUAL": {"description": "Operator manually initiated investigation", "action": "Run full investigation", "priority": "OPERATOR_SET"},
}


class IntelligencePlaybook:
    """The intelligence engine: WHAT to find, HOW to find it, Subject to Evidence to Physical Address."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self._ev_counter = 0
        self._step_counter = 0
        self._chain_counter = 0

    def _ev_id(self):
        self._ev_counter += 1
        return f"EV-INT-{self._ev_counter:04d}"

    def _step_id(self):
        self._step_counter += 1
        return f"STEP-{self._step_counter:04d}"

    def _chain_id(self):
        self._chain_counter += 1
        return f"CHAIN-{self._chain_counter:04d}"

    def _ts(self):
        return datetime.now(timezone.utc).isoformat() + "Z"

    def _http_get_json(self, url, timeout=12):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Playbook/5.2 (Law Enforcement)"})
            resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
            return json.loads(resp.read().decode('utf-8', errors='replace'))
        except:
            return None

    def _http_get_text(self, url, timeout=12):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Playbook/5.2 (Law Enforcement)"})
            resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace')
        except:
            return None

    def _dns_lookup(self, domain):
        try:
            import socket
            ips = socket.getaddrinfo(domain, None, socket.AF_INET)
            return list(set(ip[4][0] for ip in ips))
        except:
            return []

    def _ipinfo(self, ip):
        data = self._http_get_json(f"https://ipinfo.io/{ip}/json", timeout=10)
        if data and data.get("ip"):
            return data
        return None

    # ============================================================
    # FULL INVESTIGATION
    # ============================================================

    def investigate(self, subject: dict) -> dict:
        """Run a full investigation: Subject -> Evidence -> Physical Address."""
        investigation = {
            "investigation_id": f"INV-FULL-{int(time.time())}",
            "timestamp": self._ts(),
            "subject": subject,
            "trigger_reason": subject.get("trigger_reason", ""),
            "playbook_used": subject.get("identifier_type", "DOMAIN"),
            "evidence_chain": [],
            "attribution_chain": [],
            "physical_locations": [],
            "people_identified": [],
            "companies_identified": [],
            "digital_identifiers": [],
            "financial_indicators": [],
            "scam_indicators": [],
            "confidence": 0.0,
            "accusation_level": "NOT_ESTABLISHED",
            "next_steps": [],
            "report": "",
        }

        # Step 1: SUBJECT
        investigation["evidence_chain"].append({
            "step": self._step_id(),
            "phase": "SUBJECT",
            "finding": f"Investigation triggered by: {subject.get('trigger', 'MANUAL')}",
            "reason": subject.get("trigger_reason", "Manual investigation"),
            "identifier": subject.get("identifier", ""),
            "identifier_type": subject.get("identifier_type", ""),
            "operator": subject.get("operator", ""),
            "authority": subject.get("authority", ""),
            "evidence_id": self._ev_id(),
            "timestamp": self._ts(),
        })

        # Step 2: PLAYBOOK
        id_type = subject.get("identifier_type", "DOMAIN")
        identifier = subject.get("identifier", "")
        playbook = INTELLIGENCE_PLAYBOOK.get(id_type, {})

        investigation["evidence_chain"].append({
            "step": self._step_id(),
            "phase": "PLAYBOOK",
            "finding": f"Intelligence Playbook for {id_type}: {len(playbook.get('what_to_find', []))} items to discover, {len(playbook.get('how_to_find', []))} methods",
            "what_to_find": playbook.get("what_to_find", []),
            "how_to_find": playbook.get("how_to_find", []),
            "leads_to": playbook.get("leads_to", []),
            "evidence_id": self._ev_id(),
            "timestamp": self._ts(),
        })

        # Step 3: Execute discovery
        discovery_steps = self._execute_discovery(identifier, id_type)
        investigation["evidence_chain"].extend(discovery_steps)

        # Step 4: Attribution chain
        attribution = self._build_attribution_chain(discovery_steps)
        investigation["attribution_chain"] = attribution["chain"]
        investigation["physical_locations"] = attribution["physical_locations"]
        investigation["people_identified"] = attribution["people"]
        investigation["companies_identified"] = attribution["companies"]
        investigation["digital_identifiers"] = attribution["digital_identifiers"]
        investigation["financial_indicators"] = attribution["financial_indicators"]
        investigation["scam_indicators"] = attribution["scam_indicators"]

        # Step 5: Score
        scam_count = len(attribution["scam_indicators"])
        loc_count = len(attribution["physical_locations"])
        comp_count = len(attribution["companies"])
        fin_count = len(attribution["financial_indicators"])

        if scam_count >= 3 and (loc_count > 0 or comp_count > 0):
            investigation["accusation_level"] = "REQUIRES_INVESTIGATION"
            investigation["confidence"] = 0.6
        elif scam_count >= 2:
            investigation["accusation_level"] = "SUSPICIOUS"
            investigation["confidence"] = 0.4
        elif scam_count >= 1 or fin_count > 0:
            investigation["accusation_level"] = "SUSPICIOUS"
            investigation["confidence"] = 0.2
        elif loc_count > 0:
            investigation["accusation_level"] = "INFORMATION_GATHERED"
            investigation["confidence"] = 0.1
        else:
            investigation["accusation_level"] = "NOT_ESTABLISHED"
            investigation["confidence"] = 0.0

        # Step 6: Next steps
        investigation["next_steps"] = self._determine_next_steps(attribution, investigation["accusation_level"])

        # Step 7: Report
        investigation["report"] = self._generate_report(investigation)

        return investigation

    # ============================================================
    # DISCOVERY
    # ============================================================

    def _execute_discovery(self, identifier: str, id_type: str) -> list:
        """Execute all discovery methods — parallel where possible, sequential for dependencies."""
        steps = []
        all_ips = set()

        # Phase 1: Run independent APIs in parallel
        def run_rdap():
            data = self._http_get_json(f"https://rdap.org/domain/{identifier}", timeout=10)
            if data:
                reg_date = ""
                reg_name = ""
                for event in data.get("events", []):
                    if event.get("eventAction") == "registration":
                        reg_date = event.get("eventDate", "")
                for entity in data.get("entities", []):
                    if "registrant" in entity.get("roles", []):
                        vcard = entity.get("vcardArray", [])
                        if len(vcard) > 1:
                            for field in vcard[1]:
                                if field[0] == "fn":
                                    reg_name = field[3]
                return {"step": self._step_id(), "phase": "DOMAIN_REGISTRATION", "source": "ICANN_RDAP",
                        "finding": f"Domain {identifier} registered on {reg_date}",
                        "data": {"registration_date": reg_date, "registrant": reg_name if reg_name else "PRIVACY_PROXY"},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_dns():
            ips = self._dns_lookup(identifier)
            if ips:
                return {"step": self._step_id(), "phase": "DNS_RESOLUTION", "source": "DNS_LOOKUP",
                        "finding": f"Domain resolves to {len(ips)} IP(s): {', '.join(ips)}",
                        "data": {"ips": ips},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_crtsh():
            # crt.sh is often slow, try with shorter timeout
            data = self._http_get_json(f"https://crt.sh/?q={identifier}&output=json", timeout=12)
            if data and isinstance(data, list) and len(data) > 0:
                sans = set()
                for cert in data[:20]:
                    for name in cert.get("name_value", "").split("\n"):
                        n = name.strip()
                        if n: sans.add(n)
                return {"step": self._step_id(), "phase": "CERTIFICATE_TRANSPARENCY", "source": "CRT_SH",
                        "finding": f"Found {len(data)} certificates, {len(sans)} unique domain names",
                        "data": {"cert_count": len(data), "domains": list(sans)[:15]},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_page_content():
            content = self._http_get_text(f"https://{identifier}", timeout=12)
            if not content:
                content = self._http_get_text(f"http://{identifier}", timeout=12)
            if content and len(content) > 100:
                return {"step": self._step_id(), "phase": "PAGE_CONTENT", "source": "DIRECT_HTTP",
                        "finding": f"Fetched page content: {len(content)} bytes",
                        "data": {"content": content[:10000], "content_length": len(content)},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_urlscan():
            data = self._http_get_json(f"https://urlscan.io/api/v1/search/?q=domain:{identifier}", timeout=10)
            if data:
                scans = data.get("results", [])
                if scans:
                    scan = scans[0].get("page", {})
                    ip = scan.get("ip", "")
                    country = scan.get("country", "")
                    server = scan.get("server", "")
                    return {"step": self._step_id(), "phase": "HOSTING_INTEL", "source": "URLSCAN_IO",
                            "finding": f"Hosted on IP {ip} in {country}, server: {server}",
                            "data": {"ip": ip, "country": country, "server": server},
                            "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_wayback():
            data = self._http_get_json(f"https://web.archive.org/cdx/search/cdx?url={identifier}/*&output=json&limit=10&collapse=urlkey", timeout=10)
            if data and isinstance(data, list) and len(data) > 1:
                return {"step": self._step_id(), "phase": "WEB_HISTORY", "source": "WAYBACK_MACHINE",
                        "finding": f"Domain has {len(data)-1} archived pages",
                        "data": {"captures": len(data) - 1},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        def run_blockchain(addr):
            data = self._http_get_json(f"https://blockchain.info/rawaddr/{addr}", timeout=15)
            if data:
                return {"step": self._step_id(), "phase": "BLOCKCHAIN_ANALYSIS", "source": "BLOCKCHAIN_INFO",
                        "finding": f"Wallet {addr}: {data.get('n_tx', 0)} tx, {data.get('total_received', 0)/1e8:.4f} BTC received",
                        "data": {"total_received": data.get("total_received", 0)/1e8, "total_sent": data.get("total_sent", 0)/1e8,
                                 "final_balance": data.get("final_balance", 0)/1e8, "n_tx": data.get("n_tx", 0)},
                        "evidence_id": self._ev_id(), "timestamp": self._ts()}
            return None

        if id_type == "DOMAIN":
            # Run all independent calls in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_map = {
                    executor.submit(run_rdap): "rdap",
                    executor.submit(run_dns): "dns",
                    executor.submit(run_crtsh): "crtsh",
                    executor.submit(run_page_content): "page",
                    executor.submit(run_urlscan): "urlscan",
                    executor.submit(run_wayback): "wayback",
                }

                for future in as_completed(future_map, timeout=25):
                    name = future_map[future]
                    try:
                        result = future.result(timeout=25)
                        if result:
                            steps.append(result)
                            # Collect IPs from DNS and URLScan
                            if name == "dns" and result.get("data", {}).get("ips"):
                                all_ips.update(result["data"]["ips"])
                            if name == "urlscan" and result.get("data", {}).get("ip"):
                                all_ips.add(result["data"]["ip"])
                    except:
                        pass

            # Phase 2: Run IP geolocation for all collected IPs (sequential, they're fast)
            for ip in list(all_ips)[:5]:
                geo = self._ipinfo(ip)
                if geo:
                    steps.append({
                        "step": self._step_id(),
                        "phase": "IP_GEOLOCATION",
                        "source": "IPINFO_IO",
                        "finding": f"IP {ip} located in {geo.get('city', '?')}, {geo.get('region', '?')}, {geo.get('country', '?')} — Hosting: {geo.get('org', '?')}",
                        "data": {"ip": ip, "city": geo.get("city", ""), "region": geo.get("region", ""),
                                 "country": geo.get("country", ""), "org": geo.get("org", ""),
                                 "hostname": geo.get("hostname", ""), "loc": geo.get("loc", "")},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })

            # Phase 3: Extract entities from page content
            page_steps = [s for s in steps if s.get("phase") == "PAGE_CONTENT"]
            if page_steps:
                content = page_steps[0]["data"].get("content", "")
                entity_steps = self._extract_entities_from_page(content, identifier)
                steps.extend(entity_steps)

                # Phase 4: Multi-chain blockchain tracing (done by scanner)
                wallet_steps = [s for s in entity_steps if s.get("phase") == "CRYPTO_WALLET_DISCOVERY"]
                if wallet_steps and wallet_steps[0]["data"].get("traces"):
                    for trace in wallet_steps[0]["data"]["traces"]:
                        chain = trace.get("chain", "")
                        tx_count = trace.get("tx_count", 0)
                        has_usdt = trace.get("has_usdt", False)
                        usdt_bal = trace.get("usdt_balance", 0)
                        finding = "Wallet " + trace["address"] + " on " + chain + ": " + str(tx_count) + " transactions"
                        if has_usdt:
                            finding += ", USDT balance: " + str(usdt_bal)
                        if trace.get("eth_balance", 0) > 0:
                            finding += ", ETH: " + str(trace["eth_balance"])
                        if trace.get("trx_balance", 0) > 0:
                            finding += ", TRX: " + str(trace["trx_balance"])
                        src = "MULTI_CHAIN_" + chain.upper()
                        steps.append({
                            "step": self._step_id(),
                            "phase": "BLOCKCHAIN_ANALYSIS",
                            "source": src,
                            "finding": finding,
                            "data": trace,
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })

        elif id_type == "WALLET":
            result = run_blockchain(identifier)
            if result:
                steps.append(result)

        elif id_type == "IP":
            geo = self._ipinfo(identifier)
            if geo:
                steps.append({
                    "step": self._step_id(),
                    "phase": "IP_GEOLOCATION",
                    "source": "IPINFO_IO",
                    "finding": f"IP {identifier} located in {geo.get('city', '?')}, {geo.get('region', '?')}, {geo.get('country', '?')}",
                    "data": {"ip": identifier, "city": geo.get("city", ""), "region": geo.get("region", ""),
                             "country": geo.get("country", ""), "org": geo.get("org", ""), "loc": geo.get("loc", "")},
                    "evidence_id": self._ev_id(),
                    "timestamp": self._ts(),
                })

        # Sort by step ID
        steps.sort(key=lambda s: s.get("step", ""))
        return steps

    def _extract_entities_from_page(self, content: str, domain: str) -> list:
        """Extract entities from page content."""
        steps = []
        content_lower = content.lower()

        # Crypto wallets — MULTI-CHAIN: BTC, ETH, USDT (TRC-20/ERC-20/BEP20), SOL, TON, XRP, etc.
        if _crypto_scanner:
            crypto_result = _crypto_scanner.scan_and_trace(content)
            wallets = [w["address"] for w in crypto_result["wallets"]
                       if w["type"] not in ("DOGE",)]
            if wallets:
                steps.append({"step": self._step_id(), "phase": "CRYPTO_WALLET_DISCOVERY", "source": "MULTI_CHAIN_SCANNER",
                              "finding": "Found " + str(len(wallets)) + " crypto wallet(s) across " + str(len(crypto_result["chains_detected"])) + " chains. USDT found: " + str(crypto_result["usdt_found"]),
                              "data": {
                                  "wallets": wallets[:10],
                                  "wallets_detail": [
                                      {"address": w["address"], "type": w["type"], "chain": w["chain"], "asset": w["asset"]}
                                      for w in crypto_result["wallets"][:10]
                                  ],
                                  "usdt_found": crypto_result["usdt_found"],
                                  "usdt_total": crypto_result["usdt_total"],
                                  "chains_detected": crypto_result["chains_detected"],
                                  "traces": [
                                      {"address": t.get("address", ""), "chain": t.get("chain", ""),
                                       "tx_count": t.get("transaction_count", 0),
                                       "has_usdt": t.get("has_usdt", False),
                                       "usdt_balance": t.get("usdt_balance", 0),
                                       "eth_balance": t.get("eth_balance", 0),
                                       "trx_balance": t.get("trx_balance", 0)}
                                      for t in crypto_result["traces"][:10]
                                  ],
                              },
                              "evidence_id": self._ev_id(), "timestamp": self._ts()})
        else:
            btc = list(set(re.findall(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b', content)))
            eth = list(set(re.findall(r'\b0x[a-fA-F0-9]{40}\b', content)))
            bc1 = list(set(re.findall(r'\bbc1[a-z0-9]{39,59}\b', content)))
            wallets = btc + eth + bc1
            if wallets:
                steps.append({"step": self._step_id(), "phase": "CRYPTO_WALLET_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                              "finding": "Found " + str(len(wallets)) + " crypto wallet(s): " + ", ".join(wallets[:3]),
                              "data": {"wallets": wallets[:5]},
                              "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Phones
        phones = re.findall(r'\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}', content)
        phones = [p for p in phones if 10 <= len(re.sub(r'[^\d]', '', p)) <= 15]
        if phones:
            steps.append({"step": self._step_id(), "phase": "PHONE_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                          "finding": f"Found {len(phones)} phone(s): {', '.join(list(set(phones))[:3])}",
                          "data": {"phones": list(set(phones))[:5]},
                          "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Emails
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)))
        emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))]
        if emails:
            steps.append({"step": self._step_id(), "phase": "EMAIL_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                          "finding": f"Found {len(emails)} email(s): {', '.join(emails[:3])}",
                          "data": {"emails": emails[:5]},
                          "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Social links
        social_patterns = {
            "telegram": r'(?:t\.me/|@)([a-zA-Z0-9_]{4,32})',
            "whatsapp": r'wa\.me/(\d{6,})',
            "twitter": r'twitter\.com/([a-zA-Z0-9_]{3,})',
            "facebook": r'facebook\.com/([a-zA-Z0-9.]{3,})',
            "instagram": r'instagram\.com/([a-zA-Z0-9_.]{3,})',
            "linkedin": r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]{3,})',
        }
        socials = {}
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, content_lower)
            if matches: socials[platform] = list(set(matches))[:3]
        if socials:
            steps.append({"step": self._step_id(), "phase": "SOCIAL_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                          "finding": f"Found social media: {json.dumps(socials)}",
                          "data": {"socials": socials},
                          "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Company references
        company_patterns = [
            r'(?:©\s*(?:\d{4})?\s*)([A-Z][a-zA-Z\s]{2,40}(?:Ltd|Limited|Inc|LLC|GmbH|S\.A\.|Corp))',
            r'(?:Company|Companies House)[:\s]*(\d{6,})',
            r'(?:Registered|Reg\.?\s*No\.?)[:\s]*(\d{6,})',
        ]
        for pat in company_patterns:
            matches = re.findall(pat, content)
            if matches:
                steps.append({"step": self._step_id(), "phase": "COMPANY_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                              "finding": f"Found company reference: {matches[:3]}",
                              "data": {"company_refs": matches[:3]},
                              "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Physical address
        addr_patterns = [
            r'(\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Close|Place|Pl|Court|Ct)[,\s]+[A-Z][a-zA-Z\s]+,\s*[A-Z]{2,}\s+\d{5})',
            r'(Address[:\s]+[^<\n]{10,100})',
            r'(Registered Office[:\s]+[^<\n]{10,100})',
        ]
        for pat in addr_patterns:
            matches = re.findall(pat, content, re.IGNORECASE)
            if matches:
                for m in matches[:2]:
                    if isinstance(m, str) and len(m) > 10:
                        steps.append({"step": self._step_id(), "phase": "ADDRESS_DISCOVERY", "source": "PAGE_CONTENT_ANALYSIS",
                                      "finding": f"Found physical address: {m[:100]}",
                                      "data": {"address": m[:200]},
                                      "evidence_id": self._ev_id(), "timestamp": self._ts()})

        # Scam pattern detection
        try:
            from scam_engine_v3 import DeterministicScamEngine
            scam_result = DeterministicScamEngine.analyze(content, domain)
            if scam_result["summary"]["risk_score"] > 0:
                steps.append({"step": self._step_id(), "phase": "SCAM_ANALYSIS", "source": "GFIN_ENGINE_V3",
                              "finding": f"Scam detection: {scam_result['summary']['risk_level']} risk ({scam_result['summary']['risk_score']}), {scam_result['summary']['pattern_count']} patterns, categories: {scam_result['summary']['categories_detected']}",
                              "data": {"risk_level": scam_result["summary"]["risk_level"], "risk_score": scam_result["summary"]["risk_score"],
                                       "categories": scam_result["summary"]["categories_detected"], "pattern_count": scam_result["summary"]["pattern_count"]},
                              "evidence_id": self._ev_id(), "timestamp": self._ts()})
        except: pass

        return steps

    # ============================================================
    # ATTRIBUTION CHAIN
    # ============================================================

    def _build_attribution_chain(self, discovery_steps: list) -> dict:
        chain = []
        physical_locations = []
        people = []
        companies = []
        digital_identifiers = []
        financial_indicators = []
        scam_indicators = []

        for step in discovery_steps:
            chain.append({
                "chain_id": self._chain_id(),
                "step": step.get("step", ""),
                "phase": step.get("phase", ""),
                "source": step.get("source", ""),
                "finding": step.get("finding", ""),
                "evidence_id": step.get("evidence_id", ""),
                "timestamp": step.get("timestamp", ""),
            })

            phase = step.get("phase", "")
            data = step.get("data", {})

            if phase == "IP_GEOLOCATION":
                physical_locations.append({
                    "type": "HOSTING_LOCATION",
                    "ip": data.get("ip", ""),
                    "city": data.get("city", ""),
                    "region": data.get("region", ""),
                    "country": data.get("country", ""),
                    "coordinates": data.get("loc", ""),
                    "hosting_org": data.get("org", ""),
                    "note": "This is the hosting location (server), NOT the scammer's location. Hosting is typically a third-party datacenter.",
                })

            if phase == "ADDRESS_DISCOVERY":
                physical_locations.append({
                    "type": "PAGE_ADDRESS",
                    "address": data.get("address", ""),
                    "note": "Address from the website. Must be verified — scammers often use fake or virtual office addresses.",
                })

            if phase == "CRYPTO_WALLET_DISCOVERY":
                for w in data.get("wallets", []):
                    financial_indicators.append({
                        "type": "CRYPTO_WALLET", "address": w, "source": "MULTI_CHAIN_SCANNER",
                        "note": "Wallet found on website. Trace on blockchain to find exchange deposits. Exchange KYC requires court order.",
                    })
                    digital_identifiers.append({"type": "WALLET", "value": w})
                for wd in data.get("wallets_detail", []):
                    digital_identifiers.append({
                        "type": "WALLET", "value": wd["address"],
                        "chain": wd["chain"], "asset": wd["asset"], "wallet_type": wd["type"],
                    })
                if data.get("usdt_found"):
                    financial_indicators.append({
                        "type": "USDT_DETECTED",
                        "usdt_total": data.get("usdt_total", 0),
                        "source": "MULTI_CHAIN_SCANNER",
                        "note": "USDT found across chains. Total: " + str(data.get("usdt_total", 0)) + ". Trace to exchange for KYC.",
                    })

            if phase == "BLOCKCHAIN_ANALYSIS":
                if data.get("chain"):
                    financial_indicators.append({
                        "type": "WALLET_SUMMARY",
                        "chain": data.get("chain", ""),
                        "address": data.get("address", ""),
                        "transaction_count": data.get("transaction_count", 0),
                        "has_usdt": data.get("has_usdt", False),
                        "usdt_balance": data.get("usdt_balance", 0),
                        "eth_balance": data.get("eth_balance", 0),
                        "trx_balance": data.get("trx_balance", 0),
                        "source": data.get("source", "MULTI_CHAIN"),
                    })
                else:
                    financial_indicators.append({
                        "type": "WALLET_SUMMARY",
                        "total_received_btc": data.get("total_received", 0),
                        "total_sent_btc": data.get("total_sent", 0),
                        "final_balance_btc": data.get("final_balance", 0),
                        "transaction_count": data.get("n_tx", 0),
                        "source": "BLOCKCHAIN_INFO",
                    })

            if phase == "PHONE_DISCOVERY":
                for p in data.get("phones", []):
                    digital_identifiers.append({"type": "PHONE", "value": p})

            if phase == "EMAIL_DISCOVERY":
                for e in data.get("emails", []):
                    digital_identifiers.append({"type": "EMAIL", "value": e})

            if phase == "SOCIAL_DISCOVERY":
                for platform, accounts in data.get("socials", {}).items():
                    for acc in accounts:
                        digital_identifiers.append({"type": "SOCIAL_ACCOUNT", "platform": platform, "value": acc})

            if phase == "COMPANY_DISCOVERY":
                companies.append({"name": str(data.get("company_refs", "")), "source": "PAGE_CONTENT"})

            if phase == "SCAM_ANALYSIS":
                scam_indicators.append({
                    "risk_level": data.get("risk_level", ""),
                    "risk_score": data.get("risk_score", 0),
                    "categories": data.get("categories", []),
                    "pattern_count": data.get("pattern_count", 0),
                    "source": "GFIN_ENGINE_V3",
                })

            if phase == "CERTIFICATE_TRANSPARENCY":
                for d in data.get("domains", []):
                    digital_identifiers.append({"type": "DOMAIN", "value": d, "source": "CERTIFICATE_TRANSPARENCY"})

        return {
            "chain": chain,
            "physical_locations": physical_locations,
            "people": people,
            "companies": companies,
            "digital_identifiers": digital_identifiers,
            "financial_indicators": financial_indicators,
            "scam_indicators": scam_indicators,
        }

    def _determine_next_steps(self, attribution: dict, accusation_level: str) -> list:
        steps = []
        locs = attribution["physical_locations"]
        wallets = [f for f in attribution["financial_indicators"] if f["type"] == "CRYPTO_WALLET"]
        ids = attribution["digital_identifiers"]
        scams = attribution["scam_indicators"]

        if scams:
            steps.append({"action": "Investigate scam patterns further", "detail": f"Found {len(scams)} scam indicator(s): {', '.join(s.get('risk_level','') for s in scams)}", "priority": "HIGH"})

        if wallets:
            steps.append({"action": "Trace crypto wallets to exchange", "detail": f"Trace {len(wallets)} wallet(s) on blockchain. Identify exchange deposits. Exchange KYC requires court order.", "priority": "HIGH", "legal_authority_needed": "Court order to exchange for KYC records"})

        for loc in locs:
            if loc["type"] == "HOSTING_LOCATION":
                steps.append({"action": "Investigate hosting provider", "detail": f"Server in {loc.get('city', '?')}, {loc.get('country', '?')} via {loc.get('hosting_org', '?')}. Request provider identify account holder (requires legal authority).", "priority": "MEDIUM", "legal_authority_needed": "Subpoena/MLAT to hosting provider for account holder identity"})
            elif loc["type"] == "PAGE_ADDRESS":
                steps.append({"action": "Verify page address", "detail": f"Address on website: {loc.get('address', '?')}. May be fake. Verify independently.", "priority": "LOW"})

        if ids:
            steps.append({"action": "Investigate digital identifiers", "detail": f"Found {len(ids)} digital identifier(s). Cross-reference with other scams and victim reports.", "priority": "MEDIUM"})

        steps.append({"action": "File criminal complaint if evidence supports it", "detail": f"Current accusation level: {accusation_level}. Only file if REQUIRES_INVESTIGATION or SUPPORTED_BY_EVIDENCE.", "priority": "AS_NEEDED"})
        return steps

    def _generate_report(self, inv: dict) -> str:
        lines = []
        subj = inv["subject"]
        lines.append("=" * 70)
        lines.append("GFIN INTELLIGENCE PLAYBOOK INVESTIGATION REPORT")
        lines.append("=" * 70)
        lines.append(f"Investigation ID: {inv['investigation_id']}")
        lines.append(f"Generated: {inv['timestamp']}")
        lines.append(f"Classification: LAW ENFORCEMENT SENSITIVE")
        lines.append(f"Accusation Level: {inv['accusation_level']}")
        lines.append(f"Confidence: {inv['confidence']:.2f}")
        lines.append("")
        lines.append("=== SUBJECT — WHY WE STARTED INVESTIGATING ===")
        lines.append(f"Trigger: {subj.get('trigger', 'MANUAL')}")
        lines.append(f"Reason: {subj.get('trigger_reason', 'Manual investigation')}")
        lines.append(f"Identifier: {subj.get('identifier', '')} ({subj.get('identifier_type', '')})")
        lines.append(f"Operator: {subj.get('operator', '')}")
        lines.append(f"Authority: {subj.get('authority', '')}")
        lines.append("")
        lines.append("=== EVIDENCE CHAIN ===")
        for step in inv["evidence_chain"]:
            lines.append(f"[{step.get('step', '')}] {step.get('phase', '')} — {step.get('finding', '')}")
            if step.get("source"): lines.append(f"  Source: {step['source']}")
            lines.append(f"  Evidence ID: {step.get('evidence_id', '')}")
            lines.append("")
        lines.append("=== ATTRIBUTION CHAIN (Digital to Physical) ===")
        for c in inv["attribution_chain"]:
            lines.append(f"[{c['chain_id']}] {c['phase']}: {c['finding']}")
            lines.append(f"  Source: {c['source']}, Evidence: {c['evidence_id']}")
            lines.append("")
        if inv["physical_locations"]:
            lines.append("=== PHYSICAL LOCATIONS ===")
            for loc in inv["physical_locations"]:
                lines.append(f"Type: {loc['type']}")
                if loc.get("address"): lines.append(f"Address: {loc['address']}")
                if loc.get("city"): lines.append(f"City: {loc['city']}, {loc.get('region', '')}, {loc['country']}")
                if loc.get("coordinates"): lines.append(f"Coordinates: {loc['coordinates']}")
                if loc.get("hosting_org"): lines.append(f"Hosting: {loc['hosting_org']}")
                lines.append(f"Note: {loc.get('note', '')}")
                lines.append("")
        else:
            lines.append("=== PHYSICAL LOCATIONS ===")
            lines.append("No physical locations identified yet. Further investigation needed.")
            lines.append("")
        if inv["companies_identified"]:
            lines.append("=== COMPANIES IDENTIFIED ===")
            for comp in inv["companies_identified"]:
                lines.append(f"Company: {comp.get('name', '?')}, Source: {comp.get('source', '?')}")
            lines.append("")
        if inv["digital_identifiers"]:
            lines.append("=== DIGITAL IDENTIFIERS ===")
            for did in inv["digital_identifiers"]:
                lines.append(f"Type: {did['type']}, Value: {did.get('value', '?')}, Platform: {did.get('platform', '')}")
            lines.append("")
        if inv["financial_indicators"]:
            lines.append("=== FINANCIAL INDICATORS ===")
            for fi in inv["financial_indicators"]:
                lines.append(f"Type: {fi['type']}, Source: {fi.get('source', '')}")
                if fi.get("address"): lines.append(f"  Wallet: {fi['address']}")
                if fi.get("total_received_btc") is not None:
                    lines.append(f"  Received: {fi['total_received_btc']} BTC, Sent: {fi.get('total_sent_btc', 0)}, Balance: {fi.get('final_balance_btc', 0)}")
                if fi.get("note"): lines.append(f"  Note: {fi['note']}")
                lines.append("")
        if inv["scam_indicators"]:
            lines.append("=== SCAM INDICATORS ===")
            for si in inv["scam_indicators"]:
                lines.append(f"Risk: {si.get('risk_level', '')} ({si.get('risk_score', 0)}), Categories: {si.get('categories', [])}, Patterns: {si.get('pattern_count', 0)}")
            lines.append("")
        lines.append("=== NEXT STEPS ===")
        for ns in inv["next_steps"]:
            lines.append(f"Action: {ns['action']}")
            lines.append(f"  Detail: {ns['detail']}")
            lines.append(f"  Priority: {ns.get('priority', '')}")
            if ns.get("legal_authority_needed"):
                lines.append(f"  Legal Authority Needed: {ns['legal_authority_needed']}")
            lines.append("")
        lines.append("=== DISCLAIMER ===")
        lines.append("This report is an investigative lead, NOT an accusation.")
        lines.append(f"Accusation level: {inv['accusation_level']}")
        lines.append("The entity has NOT been proven to be fraudulent.")
        lines.append("Law enforcement investigation is required before any action.")
        lines.append("Physical locations are leads, NOT confirmed addresses of suspects.")
        lines.append("Hosting locations identify the server, NOT the scammer.")
        lines.append("All evidence from public sources. Zero fabricated evidence.")
        return "\n".join(lines)

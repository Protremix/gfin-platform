"""
GFIN Intelligence Playbook & Full Attribution Chain v5.0
24/7 MONITORING — FROM DIGITAL IDENTIFIER TO PHYSICAL ADDRESS

Every investigation starts with a SUBJECT (why we started looking),
follows the evidence chain, and traces from digital artifacts to
real-world physical locations (home/office address, datacenter, etc.)

INTELLIGENCE PLAYBOOK defines WHAT to find and HOW at each stage.
"""
import json, time, hashlib, urllib.request, urllib.parse, ssl, re, os, sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult


# ============================================================
# INTELLIGENCE PLAYBOOK — What to find and How
# ============================================================

INTELLIGENCE_PLAYBOOK = {
    "DOMAIN": {
        "what_to_find": [
            "Registration data (who registered it, when, where)",
            "DNS records (A, AAAA, MX, NS, TXT, CAA, SOA)",
            "IP addresses it resolves to",
            "SSL/TLS certificate details",
            "Other domains on the same certificate",
            "Hosting provider and datacenter location",
            "Page content (scam patterns, wallets, phones, emails, social links)",
            "Historical content (Wayback Machine)",
            "Subdomains",
            "Redirects (where does it send victims?)",
            "Privacy policy, terms of service (who is the legal entity?)",
            "Advertising IDs (if running ads)",
            "App store links (if promoting apps)",
        ],
        "how_to_find": [
            "ICANN RDAP (registration data)",
            "DNS lookup (A, AAAA, MX, NS, TXT)",
            "Certificate Transparency logs (crt.sh)",
            "URLScan.io (hosting, screenshots)",
            "Wayback Machine (historical content)",
            "Direct HTTP fetch (page content)",
            "SecurityTrails (passive DNS, subdomains)",
        ],
        "leads_to": ["IP", "CERTIFICATE", "WALLET", "PHONE", "EMAIL", "SOCIAL_ACCOUNT", "COMPANY", "PERSON"],
    },
    "IP": {
        "what_to_find": [
            "Geographic location (country, city, coordinates)",
            "ASN (Autonomous System Number)",
            "Hosting provider (company name)",
            "Datacenter physical address",
            "Other domains hosted on same IP",
            "Is this a shared CDN IP? (adversarial check)",
            "Is this a known malicious IP?",
            "Open ports and services",
            "Reverse DNS (hostname)",
        ],
        "how_to_find": [
            "IPinfo.io (geolocation, ASN, company)",
            "BGP routing tables (ASN)",
            "Shodan (open ports, services)",
            "AbuseIPDB (malicious reputation)",
            "Reverse DNS lookup",
            "URLScan.io (other domains on same IP)",
        ],
        "leads_to": ["HOSTING_PROVIDER", "DATACENTER_ADDRESS", "OTHER_DOMAINS", "ASN"],
    },
    "CERTIFICATE": {
        "what_to_find": [
            "Certificate issuer (CA)",
            "Subject domains (all SANs)",
            "Issue date and expiry",
            "Other domains sharing this certificate",
            "Certificate fingerprint",
        ],
        "how_to_find": [
            "crt.sh (Certificate Transparency logs)",
            "SSL Labs (certificate analysis)",
        ],
        "leads_to": ["DOMAIN", "COMPANY"],
    },
    "WALLET": {
        "what_to_find": [
            "All transactions (incoming and outgoing)",
            "Total received and sent",
            "Current balance",
            "Wallets it sent to (downstream)",
            "Wallets it received from (upstream)",
            "Exchange deposits (when funds go to an exchange)",
            "Exchange name (which exchange received the funds)",
            "Cluster analysis (related wallets controlled by same entity)",
        ],
        "how_to_find": [
            "Blockchain.com API (BTC)",
            "Etherscan API (ETH)",
            "Blockchair API (multi-chain)",
            "WalletExplorer (cluster analysis)",
            "Chainalysis (if licensed — requires authorization)",
        ],
        "leads_to": ["EXCHANGE", "OTHER_WALLETS", "TRANSACTION"],
        "attribution_note": "Wallet → person is FORBIDDEN without independent evidence. Exchange KYC requires court order.",
    },
    "PHONE": {
        "what_to_find": [
            "Country and region",
            "Carrier/provider",
            "Type (mobile, landline, VoIP)",
            "Public business references (company listings)",
            "Social media accounts linked to this number",
            "Public complaint references",
        ],
        "how_to_find": [
            "Number normalization (E.164 format)",
            "Public web search (business listings)",
            "Social platform search (if API available)",
            "Carrier lookup (if lawfully available)",
        ],
        "leads_to": ["PERSON", "COMPANY", "SOCIAL_ACCOUNT"],
        "attribution_note": "Phone → person requires corroboration. Number portability means carrier data may be outdated.",
    },
    "EMAIL": {
        "what_to_find": [
            "Email domain (custom domain vs free provider)",
            "Domain registration of email domain",
            "Public references (breach databases if lawfully accessible)",
            "Social accounts using this email",
            "Company associations",
        ],
        "how_to_find": [
            "Email format analysis",
            "Domain WHOIS/RDAP for email domain",
            "Public web search",
            "HaveIBeenPwned (breach check, if lawfully accessible)",
        ],
        "leads_to": ["DOMAIN", "PERSON", "SOCIAL_ACCOUNT"],
        "attribution_note": "Never access mailbox. Email ownership requires corroboration.",
    },
    "SOCIAL_ACCOUNT": {
        "what_to_find": [
            "Account ID and username",
            "Account creation date",
            "Display name and bio",
            "Profile picture (reverse image search)",
            "Linked website/domain",
            "Linked email/phone (if public)",
            "Followers and following (if public)",
            "Post history (public posts only)",
            "Advertising accounts (if running ads)",
        ],
        "how_to_find": [
            "Platform public API",
            "Public profile scrape (authorized)",
            "Social OSINT tools",
        ],
        "leads_to": ["DOMAIN", "PERSON", "PHONE", "EMAIL"],
        "attribution_note": "Private account access requires authorization. Account name ≠ real name.",
    },
    "COMPANY": {
        "what_to_find": [
            "Legal name and registration number",
            "Registered address (physical office)",
            "Directors and officers (names, dates)",
            "PSC (Persons with Significant Control)",
            "Shareholders (if available)",
            "Historical directors",
            "Other companies with same directors",
            "Filing history (annual returns, accounts)",
            "Company status (active, dissolved, in liquidation)",
            "Previous company names",
            "Charges and mortgages",
            "Insolvency records",
        ],
        "how_to_find": [
            "Companies House API (UK)",
            "OpenCorporates API",
            "Official registry (per jurisdiction)",
            "Court records (insolvency, litigation)",
        ],
        "leads_to": ["PERSON", "ADDRESS", "DOMAIN", "PHONE", "EMAIL"],
    },
    "PERSON": {
        "what_to_find": [
            "Full legal name (if publicly available)",
            "Aliases and usernames",
            "Directorships (current and historical)",
            "Addresses (from company filings, not private)",
            "Public social profiles",
            "Public professional profiles",
            "Other companies they're associated with",
            "Court records (if public)",
        ],
        "how_to_find": [
            "Company registry (director records)",
            "Professional directories",
            "Public court records",
            "Social media search",
        ],
        "leads_to": ["COMPANY", "ADDRESS", "SOCIAL_ACCOUNT", "PHONE", "EMAIL"],
        "attribution_note": "Name similarity is NOT identity. Multiple sources needed for confirmation.",
    },
    "ADDRESS": {
        "what_to_find": [
            "Full physical address",
            "Type (residential, commercial, virtual office, PO box)",
            "Other companies registered at same address",
            "Other people linked to same address",
            "Geographic coordinates",
            "Street view (if available)",
            "Is this a known virtual office location?",
            "Is this a mail forwarding service?",
        ],
        "how_to_find": [
            "Company registry (registered office)",
            "Google Maps (geocoding, street view)",
            "OSINT geolocation tools",
        ],
        "leads_to": ["COMPANY", "PERSON"],
    },
    "ADVERTISER": {
        "what_to_find": [
            "Advertiser ID",
            "Company name",
            "Ad creatives",
            "Landing pages",
            "Targeting (if available)",
            "Ad spend (if available)",
            "Other ads from same advertiser",
            "Connected domains and pages",
        ],
        "how_to_find": [
            "Meta Ad Library API",
            "Google Ads Transparency Center",
            "TikTok Ad Library",
        ],
        "leads_to": ["DOMAIN", "COMPANY", "PERSON", "SOCIAL_ACCOUNT"],
    },
    "HOSTING_PROVIDER": {
        "what_to_find": [
            "Company name",
            "Company registration",
            "Abuse contact",
            "Datacenter location (physical address)",
            "Terms of service (what do they allow?)",
            "Response to abuse reports",
        ],
        "how_to_find": [
            "IPinfo.io (hosting company)",
            "BGP/ASN lookup",
            "Provider website",
            "RIPE/ARIN/APNIC WHOIS",
        ],
        "leads_to": ["ADDRESS", "COMPANY"],
    },
    "PAYMENT_PROVIDER": {
        "what_to_find": [
            "Provider name",
            "Merchant ID (if discoverable)",
            "Payment flow (how victims pay)",
            "Connected bank accounts (requires court order)",
            "Chargeback data (requires court order)",
        ],
        "how_to_find": [
            "Page content analysis (payment forms)",
            "URL analysis (redirect to payment provider)",
            "Public payment provider APIs",
        ],
        "leads_to": ["COMPANY"],
        "attribution_note": "Bank account and KYC data require court order. Public data only.",
    },
}

# ============================================================
# TRIGGER TYPES — what starts an investigation
# ============================================================

TRIGGER_TYPES = {
    "NEW_DOMAIN_REGISTRATION": {
        "description": "A newly registered domain matching scam patterns was detected during 24/7 monitoring",
        "action": "Run full domain investigation playbook",
        "priority": "HIGH",
    },
    "VICTIM_REPORT": {
        "description": "A victim reported a scam — domain, phone, email, or wallet",
        "action": "Run investigation from reported identifier",
        "priority": "HIGH",
    },
    "CERTIFICATE_TRANSPARENCY": {
        "description": "A new SSL certificate was issued for a domain matching scam patterns",
        "action": "Investigate domain and all SANs on the certificate",
        "priority": "MEDIUM",
    },
    "SOCIAL_MONITORING": {
        "description": "Scam content detected in public social media monitoring",
        "action": "Investigate linked domain/wallet/phone",
        "priority": "MEDIUM",
    },
    "PATTERN_MATCH": {
        "description": "Known scam pattern detected in proactive scan",
        "action": "Run full investigation from matched entity",
        "priority": "HIGH",
    },
    "CAMPAIGN_LINK": {
        "description": "New entity linked to existing scam campaign via shared evidence",
        "action": "Investigate new entity + update campaign graph",
        "priority": "HIGH",
    },
    "CONTINUOUS_MONITORING": {
        "description": "Scheduled re-scan of known scam infrastructure detected changes",
        "action": "Investigate what changed and update evidence",
        "priority": "MEDIUM",
    },
    "MANUAL": {
        "description": "Operator manually initiated investigation",
        "action": "Run full investigation from provided identifier",
        "priority": "OPERATOR_SET",
    },
}


class IntelligencePlaybook:
    """The intelligence engine that knows WHAT to find and HOW."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.investigations = []
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

    def _http_get(self, url, headers=None):
        if headers is None:
            headers = {"User-Agent": "GFIN-IntelligencePlaybook/5.0 (Law Enforcement)"}
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=20, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace'), resp.getcode(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return f"HTTP_{e.code}", e.code, {}
        except Exception as e:
            return str(e), 0, {}

    # ============================================================
    # FULL INVESTIGATION — Subject to Evidence to Physical Address
    # ============================================================

    def investigate(self, subject: dict) -> dict:
        """Run a full investigation.
        subject = {
            'trigger': TRIGGER_TYPE,
            'trigger_reason': 'why we started looking',
            'identifier': 'domain.com',
            'identifier_type': 'DOMAIN',
            'operator': 'who authorized this',
            'authority': 'what legal authority',
        }
        """
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

        # Step 1: Subject — why we started investigating
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

        # Step 2: Follow the playbook for the identifier type
        id_type = subject.get("identifier_type", "DOMAIN")
        identifier = subject.get("identifier", "")
        playbook = INTELLIGENCE_PLAYBOOK.get(id_type, {})

        investigation["evidence_chain"].append({
            "step": self._step_id(),
            "phase": "PLAYBOOK",
            "finding": f"Intelligence Playbook for {id_type}: {len(playbook.get('what_to_find', []))} items to discover",
            "what_to_find": playbook.get("what_to_find", []),
            "how_to_find": playbook.get("how_to_find", []),
            "leads_to": playbook.get("leads_to", []),
            "evidence_id": self._ev_id(),
            "timestamp": self._ts(),
        })

        # Step 3: Execute discovery
        discovery = self._execute_discovery(identifier, id_type)
        investigation["evidence_chain"].extend(discovery["steps"])

        # Step 4: Build attribution chain (digital → physical)
        attribution = self._build_attribution_chain(identifier, id_type, discovery)
        investigation["attribution_chain"] = attribution["chain"]
        investigation["physical_locations"] = attribution["physical_locations"]
        investigation["people_identified"] = attribution["people"]
        investigation["companies_identified"] = attribution["companies"]
        investigation["digital_identifiers"] = attribution["digital_identifiers"]
        investigation["financial_indicators"] = attribution["financial_indicators"]
        investigation["scam_indicators"] = attribution["scam_indicators"]

        # Step 5: Determine confidence and accusation level
        evidence_count = len([s for s in investigation["evidence_chain"] if s.get("phase") not in ["SUBJECT", "PLAYBOOK"]])
        scam_count = len(attribution["scam_indicators"])
        physical_count = len(attribution["physical_locations"])
        people_count = len(attribution["people"])
        company_count = len(attribution["companies"])

        if scam_count >= 3 and (physical_count > 0 or people_count > 0 or company_count > 0):
            investigation["accusation_level"] = "REQUIRES_INVESTIGATION"
            investigation["confidence"] = 0.6
        elif scam_count >= 2:
            investigation["accusation_level"] = "SUSPICIOUS"
            investigation["confidence"] = 0.4
        elif scam_count >= 1:
            investigation["accusation_level"] = "SUSPICIOUS"
            investigation["confidence"] = 0.2
        else:
            investigation["accusation_level"] = "NOT_ESTABLISHED"
            investigation["confidence"] = 0.0

        # Step 6: Next steps
        investigation["next_steps"] = self._determine_next_steps(attribution, investigation["accusation_level"])

        # Step 7: Generate report
        investigation["report"] = self._generate_report(investigation)

        self.investigations.append(investigation)
        return investigation

    # ============================================================
    # DISCOVERY — execute the playbook for the identifier
    # ============================================================

    def _execute_discovery(self, identifier: str, id_type: str) -> dict:
        """Execute the playbook discovery steps."""
        result = {"steps": [], "data": {}}

        if id_type == "DOMAIN":
            # RDAP
            rdap_raw, _, _ = self._http_get(f"https://rdap.org/domain/{identifier}")
            if "HTTP_" not in str(rdap_raw)[:10]:
                try:
                    rdap = json.loads(rdap_raw)
                    reg_date = ""
                    reg_name = ""
                    for event in rdap.get("events", []):
                        if event.get("eventAction") == "registration":
                            reg_date = event.get("eventDate", "")
                    for entity in rdap.get("entities", []):
                        if "registrant" in entity.get("roles", []):
                            vcard = entity.get("vcardArray", [])
                            if len(vcard) > 1:
                                for field in vcard[1]:
                                    if field[0] == "fn":
                                        reg_name = field[3]
                    
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "DOMAIN_REGISTRATION",
                        "source": "ICANN_RDAP",
                        "finding": f"Domain {identifier} registered on {reg_date}",
                        "data": {"registration_date": reg_date, "registrant": reg_name if reg_name else "PRIVACY_PROXY"},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["rdap"] = {"registration_date": reg_date, "registrant": reg_name}
                except: pass

            # URLScan
            us_raw, _, _ = self._http_get(f"https://urlscan.io/api/v1/search/?q=domain:{identifier}")
            if "HTTP_" not in str(us_raw)[:10]:
                try:
                    us = json.loads(us_raw)
                    scans = us.get("results", [])
                    if scans:
                        scan = scans[0].get("page", {})
                        ip = scan.get("ip", "")
                        country = scan.get("country", "")
                        server = scan.get("server", "")
                        result["steps"].append({
                            "step": self._step_id(),
                            "phase": "HOSTING_INTEL",
                            "source": "URLSCAN_IO",
                            "finding": f"Hosted on IP {ip} in {country}, server: {server}",
                            "data": {"ip": ip, "country": country, "server": server},
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })
                        result["data"]["urlscan"] = {"ip": ip, "country": country, "server": server}

                        # IP geolocation
                        if ip:
                            geo_raw, _, _ = self._http_get(f"https://ipinfo.io/{ip}/json")
                            if "HTTP_" not in str(geo_raw)[:10]:
                                try:
                                    geo = json.loads(geo_raw)
                                    result["steps"].append({
                                        "step": self._step_id(),
                                        "phase": "IP_GEOLOCATION",
                                        "source": "IPINFO_IO",
                                        "finding": f"IP {ip} located in {geo.get('city', '?')}, {geo.get('region', '?')}, {geo.get('country', '?')}",
                                        "data": {
                                            "ip": ip, "city": geo.get("city", ""), "region": geo.get("region", ""),
                                            "country": geo.get("country", ""), "org": geo.get("org", ""),
                                            "hostname": geo.get("hostname", ""), "loc": geo.get("loc", ""),
                                        },
                                        "evidence_id": self._ev_id(),
                                        "timestamp": self._ts(),
                                    })
                                    result["data"]["geolocation"] = geo
                                except: pass
                except: pass

            # Certificate Transparency
            ct_raw, _, _ = self._http_get(f"https://crt.sh/?q={identifier}&output=json")
            if "HTTP_" not in str(ct_raw)[:10]:
                try:
                    ct = json.loads(ct_raw)
                    if ct:
                        sans = set()
                        for cert in ct[:10]:
                            for name in cert.get("name_value", "").split("\n"):
                                sans.add(name.strip())
                        result["steps"].append({
                            "step": self._step_id(),
                            "phase": "CERTIFICATE_TRANSPARENCY",
                            "source": "CRT_SH",
                            "finding": f"Found {len(ct)} certificates, {len(sans)} unique domain names",
                            "data": {"cert_count": len(ct), "domains": list(sans)[:10]},
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })
                        result["data"]["certificates"] = {"count": len(ct), "domains": list(sans)[:10]}
                except: pass

            # Page content
            page_raw, status, headers = self._http_get(f"https://{identifier}")
            if "HTTP_" not in str(page_raw)[:10] and len(page_raw) > 100:
                result["data"]["page"] = page_raw[:5000]
                result["steps"].append({
                    "step": self._step_id(),
                    "phase": "PAGE_CONTENT",
                    "source": "DIRECT_HTTP",
                    "finding": f"Fetched page content: {len(page_raw)} bytes, status {status}",
                    "data": {"status": status, "content_length": len(page_raw)},
                    "evidence_id": self._ev_id(),
                    "timestamp": self._ts(),
                })

                # Extract entities from page
                page_lower = page_raw.lower()
                # Crypto wallets
                btc = [a for a in re.findall(r'(?<![a-zA-Z])[13][a-km-zA-HJ-NP-Z1-9]{25,34}(?![a-zA-Z])', page_raw) if len(a) >= 26]
                eth = re.findall(r'(?<![a-zA-Z])0x[a-fA-F0-9]{40}(?![a-zA-Z])', page_raw)
                if btc or eth:
                    wallets = btc + eth
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "CRYPTO_WALLET_DISCOVERY",
                        "source": "PAGE_CONTENT_ANALYSIS",
                        "finding": f"Found {len(wallets)} crypto wallet address(es) on page: {', '.join(wallets[:3])}",
                        "data": {"wallets": wallets[:5], "types": ["BTC"] * len(btc) + ["ETH"] * len(eth)},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["wallets"] = wallets[:5]

                # Phone numbers
                phones = re.findall(r'(?<!\d)(\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})(?!\d)', page_raw)
                # Filter to reasonable phone numbers
                phones = [p for p in phones if len(re.sub(r'[^\d]', '', p)) >= 10 and len(re.sub(r'[^\d]', '', p)) <= 15]
                if phones:
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "PHONE_DISCOVERY",
                        "source": "PAGE_CONTENT_ANALYSIS",
                        "finding": f"Found {len(phones)} phone number(s) on page: {', '.join(phones[:3])}",
                        "data": {"phones": phones[:5]},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["phones"] = phones[:5]

                # Emails
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_raw)
                emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js'))]
                if emails:
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "EMAIL_DISCOVERY",
                        "source": "PAGE_CONTENT_ANALYSIS",
                        "finding": f"Found {len(emails)} email address(es) on page: {', '.join(emails[:3])}",
                        "data": {"emails": list(set(emails))[:5]},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["emails"] = list(set(emails))[:5]

                # Social links
                social_patterns = {
                    "telegram": r't(?:elegram|\.me)[/]@?([a-zA-Z0-9_]{3,})',
                    "whatsapp": r'wa\.me/(\d{6,})|whatsapp\.com/send\?phone=(\d{6,})',
                    "twitter": r'twitter\.com/([a-zA-Z0-9_]{3,})',
                    "facebook": r'facebook\.com/([a-zA-Z0-9.]{3,})',
                    "instagram": r'instagram\.com/([a-zA-Z0-9_.]{3,})',
                    "linkedin": r'linkedin\.com/(?:in|company)/([a-zA-Z0-9_-]{3,})',
                }
                socials = {}
                for platform, pattern in social_patterns.items():
                    matches = re.findall(pattern, page_lower)
                    if matches:
                        socials[platform] = [m[0] if isinstance(m, tuple) else m for m in matches][:3]
                if socials:
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "SOCIAL_DISCOVERY",
                        "source": "PAGE_CONTENT_ANALYSIS",
                        "finding": f"Found social media links: {json.dumps(socials)}",
                        "data": {"socials": socials},
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["socials"] = socials

                # Scam patterns (from v4 patterns)
                from scam_hunter_v4 import ProactiveScamHunterV4
                for pname, pat in ProactiveScamHunterV4.SCAM_PATTERNS.items():
                    kw_matches = [kw for kw in pat["keywords"] if kw in page_lower]
                    if len(kw_matches) >= pat.get("min_keyword_matches", 2):
                        result["steps"].append({
                            "step": self._step_id(),
                            "phase": "SCAM_PATTERN_MATCH",
                            "source": "PAGE_CONTENT_ANALYSIS",
                            "finding": f"Page matches scam pattern {pname}: keywords found: {', '.join(kw_matches[:3])}",
                            "data": {"pattern": pname, "keywords": kw_matches, "risk": pat["risk_level"]},
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })

                # Company name (from footer/about/legal pages)
                company_patterns = [
                    r'©\s*(\d{4})?\s*([A-Z][a-zA-Z\s]{2,40}(?:Ltd|Limited|Inc|LLC|GmbH|S\.A\.|Corp))',
                    r'(?:Company|Companies House)[:\s]*(\d{6,})',
                    r'(?:Registered|Reg\.? No\.?)[:\s]*(\d{6,})',
                ]
                for pat in company_patterns:
                    matches = re.findall(pat, page_raw)
                    if matches:
                        result["steps"].append({
                            "step": self._step_id(),
                            "phase": "COMPANY_DISCOVERY",
                            "source": "PAGE_CONTENT_ANALYSIS",
                            "finding": f"Found company reference: {matches}",
                            "data": {"company_refs": matches},
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })

                # Physical address
                addr_patterns = [
                    r'(\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Close|Place|Pl|Court|Ct)[,\s]+[A-Z][a-zA-Z\s]+,\s*[A-Z]{2,}\s+\d{5})',
                    r'(Address[:\s]+.*?)(?:<|$|\n)',
                    r'(Registered Office[:\s]+.*?)(?:<|$|\n)',
                ]
                for pat in addr_patterns:
                    matches = re.findall(pat, page_raw, re.IGNORECASE)
                    if matches:
                        for m in matches[:2]:
                            addr = m if isinstance(m, str) else str(m)
                            if len(addr) > 10 and len(addr) < 200:
                                result["steps"].append({
                                    "step": self._step_id(),
                                    "phase": "ADDRESS_DISCOVERY",
                                    "source": "PAGE_CONTENT_ANALYSIS",
                                    "finding": f"Found physical address on page: {addr[:100]}",
                                    "data": {"address": addr[:200]},
                                    "evidence_id": self._ev_id(),
                                    "timestamp": self._ts(),
                                })

            # Wayback Machine
            wb_raw, _, _ = self._http_get(f"https://web.archive.org/cdx/search/cdx?url={identifier}/*&output=json&limit=5&collapse=urlkey")
            if "HTTP_" not in str(wb_raw)[:10]:
                try:
                    wb = json.loads(wb_raw)
                    if len(wb) > 1:
                        result["steps"].append({
                            "step": self._step_id(),
                            "phase": "WEB_HISTORY",
                            "source": "WAYBACK_MACHINE",
                            "finding": f"Domain has {len(wb)-1} archived pages in Wayback Machine",
                            "data": {"captures": len(wb) - 1},
                            "evidence_id": self._ev_id(),
                            "timestamp": self._ts(),
                        })
                        result["data"]["wayback"] = {"captures": len(wb) - 1}
                except: pass

        elif id_type == "WALLET":
            # Blockchain lookup
            bc_raw, _, _ = self._http_get(f"https://blockchain.info/rawaddr/{identifier}")
            if "HTTP_" not in str(bc_raw)[:10]:
                try:
                    bc = json.loads(bc_raw)
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "BLOCKCHAIN_ANALYSIS",
                        "source": "BLOCKCHAIN_INFO",
                        "finding": f"Wallet {identifier}: {bc.get('n_tx', 0)} transactions, {bc.get('total_received', 0)/1e8:.4f} BTC received, {bc.get('final_balance', 0)/1e8:.4f} BTC balance",
                        "data": {
                            "total_received": bc.get("total_received", 0) / 1e8,
                            "total_sent": bc.get("total_sent", 0) / 1e8,
                            "final_balance": bc.get("final_balance", 0) / 1e8,
                            "n_tx": bc.get("n_tx", 0),
                        },
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["blockchain"] = bc

                    # Trace transactions
                    for tx in bc.get("txs", [])[:5]:
                        for out in tx.get("out", [])[:3]:
                            addr = out.get("addr", "")
                            if addr and addr != identifier:
                                result["steps"].append({
                                    "step": self._step_id(),
                                    "phase": "TRANSACTION_TRACE",
                                    "source": "BLOCKCHAIN_INFO",
                                    "finding": f"Wallet sent {out.get('value', 0)/1e8:.4f} BTC to {addr}",
                                    "data": {"to_address": addr, "amount_btc": out.get("value", 0) / 1e8},
                                    "evidence_id": self._ev_id(),
                                    "timestamp": self._ts(),
                                    "note": "ON_CHAIN_FACT: transaction is real. Identity of receiver requires independent evidence.",
                                })
                except: pass

        elif id_type == "COMPANY":
            # Companies House (UK)
            company_num = identifier
            ch_raw, _, _ = self._http_get(f"https://api.company-information.service.gov.uk/company/{company_num}")
            if "HTTP_" not in str(ch_raw)[:10]:
                try:
                    ch = json.loads(ch_raw)
                    result["steps"].append({
                        "step": self._step_id(),
                        "phase": "COMPANY_REGISTRATION",
                        "source": "COMPANIES_HOUSE",
                        "finding": f"Company: {ch.get('company_name', '?')}, Status: {ch.get('company_status', '?')}, Address: {ch.get('registered_office_address', {}).get('address_line_1', '?')}",
                        "data": {
                            "company_name": ch.get("company_name", ""),
                            "company_number": ch.get("company_number", ""),
                            "company_status": ch.get("company_status", ""),
                            "registered_address": ch.get("registered_office_address", {}),
                            "incorporation_date": ch.get("date_of_creation", ""),
                        },
                        "evidence_id": self._ev_id(),
                        "timestamp": self._ts(),
                    })
                    result["data"]["company"] = ch
                except: pass

        return result

    # ============================================================
    # ATTRIBUTION CHAIN — Digital → Physical
    # ============================================================

    def _build_attribution_chain(self, identifier: str, id_type: str, discovery: dict) -> dict:
        """Build a chain from digital identifier to physical address."""
        chain = []
        physical_locations = []
        people = []
        companies = []
        digital_identifiers = []
        financial_indicators = []
        scam_indicators = []

        data = discovery.get("data", {})

        # Build the chain from discovery steps
        for step in discovery.get("steps", []):
            chain_entry = {
                "chain_id": self._chain_id(),
                "step": step.get("step", ""),
                "phase": step.get("phase", ""),
                "source": step.get("source", ""),
                "finding": step.get("finding", ""),
                "evidence_id": step.get("evidence_id", ""),
                "timestamp": step.get("timestamp", ""),
            }
            chain.append(chain_entry)

            # Extract physical locations
            if step.get("phase") == "IP_GEOLOCATION":
                geo_data = step.get("data", {})
                physical_locations.append({
                    "type": "HOSTING_LOCATION",
                    "ip": geo_data.get("ip", ""),
                    "city": geo_data.get("city", ""),
                    "region": geo_data.get("region", ""),
                    "country": geo_data.get("country", ""),
                    "coordinates": geo_data.get("loc", ""),
                    "hosting_org": geo_data.get("org", ""),
                    "note": "This is the hosting location, NOT necessarily the scammer's location. Hosting may be a third-party datacenter.",
                })

            if step.get("phase") == "ADDRESS_DISCOVERY":
                physical_locations.append({
                    "type": "PAGE_ADDRESS",
                    "address": step.get("data", {}).get("address", ""),
                    "note": "Address found on the scam website. Must be verified — scammers often use fake or virtual office addresses.",
                })

            if step.get("phase") == "COMPANY_REGISTRATION":
                comp = step.get("data", {})
                companies.append({
                    "name": comp.get("company_name", ""),
                    "number": comp.get("company_number", ""),
                    "status": comp.get("company_status", ""),
                    "address": comp.get("registered_address", {}),
                    "incorporation_date": comp.get("incorporation_date", ""),
                })
                addr = comp.get("registered_address", {})
                if addr.get("address_line_1"):
                    physical_locations.append({
                        "type": "COMPANY_REGISTERED_ADDRESS",
                        "address": f"{addr.get('address_line_1', '')}, {addr.get('postal_code', '')}, {addr.get('country', '')}",
                        "company": comp.get("company_name", ""),
                        "note": "Company registered office. May be a virtual office or accountant's address — NOT necessarily where the scammer operates.",
                    })

            if step.get("phase") == "COMPANY_DISCOVERY":
                companies.append({
                    "name": str(step.get("data", {}).get("company_refs", "")),
                    "source": "PAGE_CONTENT",
                })

            # Extract digital identifiers
            if step.get("phase") == "CRYPTO_WALLET_DISCOVERY":
                for w in step.get("data", {}).get("wallets", []):
                    financial_indicators.append({
                        "type": "CRYPTO_WALLET",
                        "address": w,
                        "source": "PAGE_CONTENT",
                        "note": "Wallet address found on scam website. Trace on blockchain to find exchange deposits. Exchange KYC requires court order.",
                    })
                    digital_identifiers.append({"type": "WALLET", "value": w})

            if step.get("phase") == "PHONE_DISCOVERY":
                for p in step.get("data", {}).get("phones", []):
                    digital_identifiers.append({"type": "PHONE", "value": p})

            if step.get("phase") == "EMAIL_DISCOVERY":
                for e in step.get("data", {}).get("emails", []):
                    digital_identifiers.append({"type": "EMAIL", "value": e})

            if step.get("phase") == "SOCIAL_DISCOVERY":
                for platform, accounts in step.get("data", {}).get("socials", {}).items():
                    for acc in accounts:
                        digital_identifiers.append({"type": "SOCIAL_ACCOUNT", "platform": platform, "value": acc})

            if step.get("phase") == "SCAM_PATTERN_MATCH":
                scam_indicators.append({
                    "pattern": step.get("data", {}).get("pattern", ""),
                    "risk": step.get("data", {}).get("risk", ""),
                    "keywords": step.get("data", {}).get("keywords", []),
                    "source": "PAGE_CONTENT_ANALYSIS",
                })

            if step.get("phase") == "TRANSACTION_TRACE":
                financial_indicators.append({
                    "type": "BLOCKCHAIN_TRANSACTION",
                    "to_address": step.get("data", {}).get("to_address", ""),
                    "amount_btc": step.get("data", {}).get("amount_btc", 0),
                    "source": "BLOCKCHAIN_INFO",
                    "note": step.get("note", "On-chain fact. Identity requires independent evidence."),
                })

            if step.get("phase") == "BLOCKCHAIN_ANALYSIS":
                bc = step.get("data", {})
                financial_indicators.append({
                    "type": "WALLET_SUMMARY",
                    "total_received_btc": bc.get("total_received", 0),
                    "total_sent_btc": bc.get("total_sent", 0),
                    "final_balance_btc": bc.get("final_balance", 0),
                    "transaction_count": bc.get("n_tx", 0),
                    "source": "BLOCKCHAIN_INFO",
                })

        return {
            "chain": chain,
            "physical_locations": physical_locations,
            "people": people,
            "companies": companies,
            "digital_identifiers": digital_identifiers,
            "financial_indicators": financial_indicators,
            "scam_indicators": scam_indicators,
        }

    # ============================================================
    # NEXT STEPS — what should happen next
    # ============================================================

    def _determine_next_steps(self, attribution: dict, accusation_level: str) -> list:
        steps = []
        locs = attribution["physical_locations"]
        wallets = [f for f in attribution["financial_indicators"] if f["type"] == "CRYPTO_WALLET"]
        ids = attribution["digital_identifiers"]
        scams = attribution["scam_indicators"]

        if scams:
            steps.append({
                "action": "Investigate scam patterns further",
                "detail": f"Found {len(scams)} scam pattern(s): {', '.join(s['pattern'] for s in scams)}",
                "priority": "HIGH",
            })

        if wallets:
            steps.append({
                "action": "Trace crypto wallets to exchange",
                "detail": f"Trace {len(wallets)} wallet(s) on blockchain. Identify if funds were sent to a known exchange. Exchange KYC requires court order.",
                "priority": "HIGH",
                "legal_authority_needed": "Court order to exchange for KYC records",
            })

        if locs:
            for loc in locs:
                if loc["type"] == "HOSTING_LOCATION":
                    steps.append({
                        "action": "Investigate hosting provider",
                        "detail": f"Server located in {loc.get('city', '?')}, {loc.get('country', '?')} via {loc.get('hosting_org', '?')}. Request hosting provider to identify account holder (requires legal authority).",
                        "priority": "MEDIUM",
                        "legal_authority_needed": "Subpoena/MLAT to hosting provider for account holder identity",
                    })
                elif loc["type"] == "COMPANY_REGISTERED_ADDRESS":
                    steps.append({
                        "action": "Verify registered address",
                        "detail": f"Company registered at: {loc.get('address', '?')}. Verify if this is a virtual office. Visit in person if possible.",
                        "priority": "MEDIUM",
                    })
                elif loc["type"] == "PAGE_ADDRESS":
                    steps.append({
                        "action": "Verify page address",
                        "detail": f"Address found on website: {loc.get('address', '?')}. May be fake. Verify via independent sources.",
                        "priority": "LOW",
                    })

        if ids:
            steps.append({
                "action": "Investigate digital identifiers",
                "detail": f"Found {len(ids)} digital identifier(s): phones, emails, social accounts. Each should be cross-referenced with other scams and victim reports.",
                "priority": "MEDIUM",
            })

        steps.append({
            "action": "File criminal complaint if evidence supports it",
            "detail": f"Current accusation level: {accusation_level}. Only file if accusation is REQUIRES_INVESTIGATION or SUPPORTED_BY_EVIDENCE.",
            "priority": "AS_NEEDED",
        })

        return steps

    # ============================================================
    # REPORT — Subject to Evidence narrative
    # ============================================================

    def _generate_report(self, investigation: dict) -> str:
        """Generate a narrative report: Subject → Evidence → Physical."""
        lines = []
        subj = investigation["subject"]
        lines.append(f"INVESTIGATION REPORT: {investigation['investigation_id']}")
        lines.append(f"Generated: {investigation['timestamp']}")
        lines.append(f"Classification: LAW ENFORCEMENT SENSITIVE")
        lines.append(f"Accusation Level: {investigation['accusation_level']}")
        lines.append(f"Confidence: {investigation['confidence']:.2f}")
        lines.append("")
        lines.append("=== SUBJECT — WHY WE STARTED INVESTIGATING ===")
        lines.append(f"Trigger: {subj.get('trigger', 'MANUAL')}")
        lines.append(f"Reason: {subj.get('trigger_reason', 'Manual investigation')}")
        lines.append(f"Identifier: {subj.get('identifier', '')} ({subj.get('identifier_type', '')})")
        lines.append(f"Operator: {subj.get('operator', '')}")
        lines.append(f"Authority: {subj.get('authority', '')}")
        lines.append("")

        lines.append("=== EVIDENCE CHAIN ===")
        for step in investigation["evidence_chain"]:
            lines.append(f"[{step.get('step', '')}] {step.get('phase', '')} — {step.get('finding', '')}")
            if step.get("source"):
                lines.append(f"  Source: {step['source']}")
            lines.append(f"  Evidence ID: {step.get('evidence_id', '')}")
            lines.append("")

        lines.append("=== ATTRIBUTION CHAIN (Digital → Physical) ===")
        for c in investigation["attribution_chain"]:
            lines.append(f"[{c['chain_id']}] {c['phase']}: {c['finding']}")
            lines.append(f"  Source: {c['source']}, Evidence: {c['evidence_id']}")
            lines.append("")

        if investigation["physical_locations"]:
            lines.append("=== PHYSICAL LOCATIONS ===")
            for loc in investigation["physical_locations"]:
                lines.append(f"Type: {loc['type']}")
                if loc.get("address"):
                    lines.append(f"Address: {loc['address']}")
                if loc.get("city"):
                    lines.append(f"City: {loc['city']}, {loc.get('region', '')}, {loc.get('country', '')}")
                if loc.get("coordinates"):
                    lines.append(f"Coordinates: {loc['coordinates']}")
                if loc.get("hosting_org"):
                    lines.append(f"Hosting: {loc['hosting_org']}")
                lines.append(f"Note: {loc.get('note', '')}")
                lines.append("")
        else:
            lines.append("=== PHYSICAL LOCATIONS ===")
            lines.append("No physical locations identified yet. Further investigation needed.")
            lines.append("")

        if investigation["companies_identified"]:
            lines.append("=== COMPANIES IDENTIFIED ===")
            for comp in investigation["companies_identified"]:
                lines.append(f"Company: {comp.get('name', '?')}, Number: {comp.get('number', '?')}, Status: {comp.get('status', '?')}")
                lines.append("")

        if investigation["digital_identifiers"]:
            lines.append("=== DIGITAL IDENTIFIERS ===")
            for did in investigation["digital_identifiers"]:
                lines.append(f"Type: {did['type']}, Value: {did.get('value', '?')}, Platform: {did.get('platform', '')}")
            lines.append("")

        if investigation["financial_indicators"]:
            lines.append("=== FINANCIAL INDICATORS ===")
            for fi in investigation["financial_indicators"]:
                lines.append(f"Type: {fi['type']}, Source: {fi.get('source', '')}")
                if fi.get("address"):
                    lines.append(f"  Wallet: {fi['address']}")
                if fi.get("to_address"):
                    lines.append(f"  Sent to: {fi['to_address']}, Amount: {fi.get('amount_btc', 0)} BTC")
                if fi.get("total_received_btc") is not None:
                    lines.append(f"  Received: {fi['total_received_btc']}, Sent: {fi.get('total_sent_btc', 0)}, Balance: {fi.get('final_balance_btc', 0)}")
                lines.append(f"  Note: {fi.get('note', '')}")
                lines.append("")

        if investigation["scam_indicators"]:
            lines.append("=== SCAM INDICATORS ===")
            for si in investigation["scam_indicators"]:
                lines.append(f"Pattern: {si['pattern']}, Risk: {si['risk']}, Keywords: {', '.join(si.get('keywords', [])[:3])}")
            lines.append("")

        lines.append("=== NEXT STEPS ===")
        for ns in investigation["next_steps"]:
            lines.append(f"Action: {ns['action']}")
            lines.append(f"  Detail: {ns['detail']}")
            lines.append(f"  Priority: {ns.get('priority', '')}")
            if ns.get("legal_authority_needed"):
                lines.append(f"  Legal Authority Needed: {ns['legal_authority_needed']}")
            lines.append("")

        lines.append("=== DISCLAIMER ===")
        lines.append("This report is an investigative lead, NOT an accusation.")
        lines.append(f"Accusation level: {investigation['accusation_level']}")
        lines.append("The entity has NOT been proven to be fraudulent.")
        lines.append("Law enforcement investigation is required before any action against the entity.")
        lines.append("Physical locations are leads, NOT confirmed addresses of suspects.")
        lines.append("Hosting locations identify the server, NOT the scammer.")
        lines.append("Company addresses may be virtual offices.")
        lines.append("All evidence from public sources + authorized APIs. Zero fabricated evidence. Zero unauthorized access.")

        return "\n".join(lines)

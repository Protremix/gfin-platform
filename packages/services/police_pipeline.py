#!/usr/bin/env python3
"""
GFIN Police Investigation Pipeline v2.0
Works like a real detective - not a web scraper.

For each case, the pipeline:
1. Identifies VICTIM, SUSPECT, INFRASTRUCTURE entities (people table)
2. Runs OSINT collection (WHOIS, DNS, URLScan, page content)
3. Extracts actionable intelligence from Telegram messages
4. Builds evidence chain: Victim -> Website -> Registration -> Hosting -> Contact -> Identity
5. Determines legal pathway: what is PUBLIC vs what needs a WARRANT
6. Creates structured investigation steps with real findings
7. Populates scam_websites database
"""
import sys
import json
import re
import hashlib
import urllib.request
import ssl
from datetime import datetime, timezone

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

CDN_PROVIDERS = {
    "cloudflare": {"name": "Cloudflare, Inc.", "legal": "subpoena via 1285 S Delaware St, San Francisco, CA", "jurisdiction": "US"},
    "amazon": {"name": "Amazon Web Services", "legal": "subpoena via AWS Legal, Seattle, WA", "jurisdiction": "US"},
    "google": {"name": "Google LLC", "legal": "subpoena via Google Legal, Mountain View, CA", "jurisdiction": "US"},
    "microsoft": {"name": "Microsoft Corporation", "legal": "subpoena via Microsoft Legal, Redmond, WA", "jurisdiction": "US"},
    "fastly": {"name": "Fastly, Inc.", "legal": "subpoena via Fastly Legal, San Francisco, CA", "jurisdiction": "US"},
    "ddos-guard": {"name": "DDoS-Guard Ltd.", "legal": "MLAT via Russia (non-US jurisdiction)", "jurisdiction": "RU"},
    "ovh": {"name": "OVHcloud", "legal": "MLAT via France", "jurisdiction": "FR"},
    "hetzner": {"name": "Hetzner Online GmbH", "legal": "MLAT via Germany", "jurisdiction": "DE"},
    "namecheap": {"name": "NameCheap, Inc.", "legal": "subpoena via NameCheap Legal, Los Angeles, CA", "jurisdiction": "US"},
    "godaddy": {"name": "GoDaddy.com, LLC", "legal": "subpoena via GoDaddy Legal, Scottsdale, AZ", "jurisdiction": "US"},
}

LEGAL_CLASSIFICATIONS = {
    "INVESTMENT_FRAUD": {"crime": "Investment Fraud / Wire Fraud", "element": "False promises of investment returns", "statute": "18 USC 1343 (Wire Fraud)"},
    "RECOVERY_SCAM": {"crime": "Advance Fee Fraud", "element": "Charging upfront fees for fake recovery services", "statute": "18 USC 1343 (Wire Fraud)"},
    "IMPERSONATION": {"crime": "Criminal Impersonation / Identity Fraud", "element": "Impersonating legitimate entity", "statute": "18 USC 913 (Impersonator)"},
    "PHISHING": {"crime": "Phishing / Computer Fraud", "element": "Deceptive collection of credentials", "statute": "18 USC 1030 (CFAA)"},
    "ADVANCE_FEE": {"crime": "Advance Fee Fraud", "element": "Charging upfront fees for promised services", "statute": "18 USC 1343 (Wire Fraud)"},
}

TRAFFICKING_INDICATORS = [
    "retention", "conversion", "recovery agent", "hiring", "relocation",
    "work permit", "visa", "accommodation", "flight ticket", "office",
    "call center", "forex jobs", "crypto jobs", "languages required"
]


class PoliceInvestigationPipeline:

    def __init__(self, db_conn):
        self.conn = db_conn
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def investigate_case(self, case_id):
        cur = self.conn.cursor()
        cur.execute("SELECT target, priority, confidence, trigger FROM cases WHERE case_id = %s", (case_id,))
        row = cur.fetchone()
        if not row:
            return {"error": "Case not found"}
        target, priority, confidence, trigger = row
        domain = target.strip()
        cur.close()

        result = {"case_id": case_id, "domain": domain, "priority": priority, "steps_completed": []}

        # STEP 1: Entity Identification
        result["steps_completed"].append("ENTITY_IDENTIFICATION")
        entities = self._identify_entities(case_id, domain)
        result["entities_identified"] = entities

        # STEP 2: OSINT Collection
        result["steps_completed"].append("OSINT_COLLECTION")
        osint = self._collect_osint(domain)
        result["osint"] = osint

        # STEP 3: Telegram Intelligence Analysis
        result["steps_completed"].append("TELEGRAM_ANALYSIS")
        telegram_intel = self._analyze_telegram_intelligence(case_id, domain)
        result["telegram_intel"] = telegram_intel

        # STEP 4: People Identification
        result["steps_completed"].append("PEOPLE_IDENTIFICATION")
        people_created = self._create_people_entries(case_id, domain, osint, telegram_intel, trigger)
        result["people_created"] = people_created

        # STEP 5: Evidence Chain
        result["steps_completed"].append("EVIDENCE_CHAIN")
        chain = self._build_evidence_chain(case_id, domain, osint, telegram_intel)
        result["evidence_chain"] = chain

        # STEP 6: Legal Pathway
        result["steps_completed"].append("LEGAL_PATHWAY")
        legal = self._determine_legal_pathway(domain, osint, telegram_intel, trigger)
        result["legal_pathway"] = legal

        # STEP 7: Investigation Steps
        result["steps_completed"].append("INVESTIGATION_STEPS")
        steps = self._create_investigation_steps(case_id, domain, osint, legal)
        result["investigation_steps"] = steps

        # STEP 8: Scam Website Entry
        result["steps_completed"].append("SCAM_WEBSITE_ENTRY")
        self._create_scam_website_entry(domain, case_id, osint, telegram_intel)

        return result

    def _identify_entities(self, case_id, domain):
        cur = self.conn.cursor()
        entities = {"domains": [], "phones": [], "emails": [], "wallets": [], "usernames": [], "groups": []}
        cur.execute("""
            SELECT domains::text, phones::text, usernames::text, group_name, is_victim, scam_type
            FROM telegram_intelligence
            WHERE domains::text ILIKE %s OR message_text ILIKE %s
        """, ("%" + domain + "%", "%" + domain + "%"))
        for row in cur.fetchall():
            domains_raw, phones_raw, usernames_raw, group_name, is_victim, scam_type = row
            for field, raw in [("domains", domains_raw), ("phones", phones_raw), ("usernames", usernames_raw)]:
                try:
                    vals = json.loads(raw) if isinstance(raw, str) else (raw or [])
                    for v in vals:
                        if v and v not in entities[field]:
                            entities[field].append(v)
                except:
                    pass
            if group_name and group_name not in entities["groups"]:
                entities["groups"].append(group_name)
        cur.close()
        return entities

    def _collect_osint(self, domain):
        osint = {"domain": domain, "rdap": {}, "urlscan": {}, "page": {}}

        # RDAP
        try:
            url = "https://rdap.org/domain/" + domain
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=self.ctx)
            data = json.loads(resp.read())
            osint["rdap"] = {
                "registrar": self._extract_rdap_registrar(data),
                "registration_date": self._extract_rdap_date(data, "registration"),
                "expiration_date": self._extract_rdap_date(data, "expiration"),
                "status": data.get("status", []),
            }
        except Exception as e:
            osint["rdap"] = {"error": str(e)}

        # URLScan
        try:
            url = "https://urlscan.io/api/v1/search/?q=domain:" + domain
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=self.ctx)
            data = json.loads(resp.read())
            results = data.get("results", [])
            if results:
                latest = results[0]
                page = latest.get("page", {})
                osint["urlscan"] = {
                    "ip": page.get("ip", ""),
                    "server": page.get("server", ""),
                    "country": page.get("country", ""),
                    "status_code": page.get("status", 0),
                    "title": page.get("title", ""),
                }
        except Exception as e:
            osint["urlscan"] = {"error": str(e)}

        # Page content
        try:
            url = "https://" + domain
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"}, method="GET")
            resp = urllib.request.urlopen(req, timeout=10, context=self.ctx)
            content = resp.read().decode("utf-8", errors="ignore")
            osint["page"] = {
                "status": resp.status,
                "content_length": len(content),
                "title": self._extract_html_title(content),
                "emails": list(set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)))[:5],
                "phones": list(set(re.findall(r'\+\d{10,15}', content)))[:5],
                "social_links": self._extract_social_links(content),
                "payment_indicators": self._extract_payment_indicators(content),
                "business_name": self._extract_business_name(content),
            }
        except Exception as e:
            osint["page"] = {"error": str(e), "status": 0}

        return osint

    def _extract_rdap_registrar(self, data):
        for ent in data.get("entities", []):
            if ent.get("roles") and "registrar" in ent.get("roles", []):
                va = ent.get("vcardArray", [])
                if len(va) > 1:
                    for item in va[1]:
                        if item and item[0] == "fn":
                            return item[3]
        return "Unknown"

    def _extract_rdap_date(self, data, date_type):
        for event in data.get("events", []):
            if date_type in event.get("eventAction", "").lower():
                return event.get("eventDate", "")
        return ""

    def _extract_html_title(self, content):
        match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_social_links(self, content):
        socials = []
        patterns = {
            "telegram": r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)',
            "whatsapp": r'(?:https?://)?wa\.me/(\d+)',
            "instagram": r'(?:https?://)?instagram\.com/([a-zA-Z0-9_.]+)',
            "facebook": r'(?:https?://)?facebook\.com/([a-zA-Z0-9.]+)',
            "twitter": r'(?:https?://)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
            "linkedin": r'(?:https?://)?linkedin\.com/(?:company|in)/([a-zA-Z0-9-]+)',
        }
        for platform, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for m in matches[:2]:
                socials.append({"platform": platform, "handle": m})
        return socials

    def _extract_payment_indicators(self, content):
        indicators = []
        content_lower = content.lower()
        methods = ["stripe", "paypal", "visa", "mastercard", "bitcoin", "crypto", "usdt",
                   "ethereum", "wire transfer", "bank transfer", "western union", "moneygram",
                   "skrill", "perfect money", "payeer", "bitpay", "coinpayments"]
        for pm in methods:
            if pm in content_lower:
                indicators.append(pm)
        return indicators

    def _extract_business_name(self, content):
        patterns = [
            r'<meta[^>]*property="og:site_name"[^>]*content="([^"]+)"',
            r'<meta[^>]*name="author"[^>]*content="([^"]+)"',
        ]
        for p in patterns:
            match = re.search(p, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _analyze_telegram_intelligence(self, case_id, domain):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT group_name, is_victim, scam_type, risk_level, usernames::text,
                   LEFT(message_text, 500) as text_preview
            FROM telegram_intelligence
            WHERE domains::text ILIKE %s OR message_text ILIKE %s
            ORDER BY is_victim DESC LIMIT 20
        """, ("%" + domain + "%", "%" + domain + "%"))
        rows = cur.fetchall()
        cur.close()

        analysis = {
            "total_mentions": len(rows),
            "victim_reports": sum(1 for r in rows if r[1]),
            "groups": list(set(r[0] for r in rows if r[0])),
            "scam_types": list(set(r[2] for r in rows if r[2])),
            "usernames": [],
            "recruitment_detected": False,
            "key_excerpts": [],
        }

        all_text = ""
        for group, is_victim, scam_type, risk_level, usernames_raw, text in rows:
            all_text += (text or "").lower() + " "
            try:
                unames = json.loads(usernames_raw) if isinstance(usernames_raw, str) else (usernames_raw or [])
                for u in unames:
                    if u and u not in analysis["usernames"]:
                        analysis["usernames"].append(u)
            except:
                pass
            if is_victim and text:
                analysis["key_excerpts"].append({"group": group, "text": text[:200]})

        for indicator in TRAFFICKING_INDICATORS:
            if indicator in all_text:
                analysis["recruitment_detected"] = True
                break

        return analysis

    def _create_people_entries(self, case_id, domain, osint, telegram_intel, trigger):
        cur = self.conn.cursor()
        count = 0
        cur.execute("DELETE FROM people WHERE case_id = %s AND source != 'MANUAL'", (case_id,))

        # VICTIM
        if telegram_intel.get("victim_reports", 0) > 0:
            victim_name = "Telegram victim reporters ({})".format(telegram_intel["victim_reports"])
            victim_detail = "Victims reported in Telegram groups. Identities not verified. Requires direct contact for statements."
            cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'VICTIM', %s, 'PSEUDONYMOUS', %s, false, 'TELEGRAM_INTELLIGENCE', 'POSSIBLE', NOW())", (case_id, victim_name, victim_detail))
            count += 1

        # SUSPECT - website operator
        page = osint.get("page", {})
        business_name = page.get("business_name", "")
        suspect_name = business_name if business_name else "Unknown operator of " + domain
        suspect_details = "Website operator of {}. ".format(domain)
        if page.get("emails"):
            suspect_details += "Contact email: {}. ".format(", ".join(page["emails"][:2]))
        if page.get("phones"):
            suspect_details += "Contact phone: {}. ".format(", ".join(page["phones"][:2]))
        if page.get("social_links"):
            socials = ["{} (@{})".format(s["platform"], s["handle"]) for s in page["social_links"][:3]]
            suspect_details += "Social media: {}. ".format(", ".join(socials))
        suspect_details += "Real identity requires legal process."
        cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'SUSPECT', %s, %s, %s, false, 'OSINT_ANALYSIS', 'UNRESOLVED', NOW())", (case_id, suspect_name, "ORGANIZATION" if business_name else "UNKNOWN", suspect_details))
        count += 1

        # SUSPECT - Telegram recruiters
        if telegram_intel.get("usernames"):
            for username in telegram_intel["usernames"][:3]:
                if username.lower() in ("admin", "support", "info", "bot", "system"):
                    continue
                uname = "@" + username
                udetail = "Telegram user active in groups: {}. Promotes domain {}. Real identity requires legal process to Telegram.".format(", ".join(telegram_intel.get("groups", [])), domain)
                cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'SUSPECT', %s, 'PSEUDONYMOUS', %s, false, 'TELEGRAM_INTELLIGENCE', 'POSSIBLE', NOW()) ON CONFLICT DO NOTHING", (case_id, uname, udetail))
                count += 1

        # INFRASTRUCTURE - Registrar
        rdap = osint.get("rdap", {})
        registrar = rdap.get("registrar", "Unknown")
        if registrar and registrar != "Unknown":
            legal_info = CDN_PROVIDERS.get(registrar.lower(), {})
            registrar_detail = "Domain registrar for {}. Registered on {}. Can provide registrant data via {}.".format(domain, rdap.get("registration_date", "unknown"), legal_info.get("legal", "subpoena"))
            cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'INFRASTRUCTURE', %s, 'REGISTRAR', %s, true, 'ICANN_RDAP', 'CONFIRMED', NOW()) ON CONFLICT DO NOTHING", (case_id, registrar, registrar_detail))
            count += 1

        # INFRASTRUCTURE - Hosting
        urlscan = osint.get("urlscan", {})
        server = urlscan.get("server", "").lower()
        if server:
            for provider_key, provider_info in CDN_PROVIDERS.items():
                if provider_key in server:
                    hosting_detail = "Hosting/CDN provider for {}. IP: {}. Country: {}. Can provide server logs via {}.".format(domain, urlscan.get("ip", "?"), urlscan.get("country", "?"), provider_info["legal"])
                    cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'INFRASTRUCTURE', %s, 'HOSTING', %s, true, 'URLSCAN', 'CONFIRMED', NOW()) ON CONFLICT DO NOTHING", (case_id, provider_info["name"], hosting_detail))
                    count += 1
                    break

        # INFRASTRUCTURE - Telegram platform
        if telegram_intel.get("usernames"):
            cur.execute("INSERT INTO people (case_id, role, name, entity_type, details, is_verified, source, confidence, created_date) VALUES (%s, 'INFRASTRUCTURE', 'Telegram (Meta/FBI Legal)', 'PLATFORM', 'Telegram can provide account data via legal process.', true, 'TELEGRAM_API', 'CONFIRMED', NOW()) ON CONFLICT DO NOTHING", (case_id,))
            count += 1

        self.conn.commit()
        cur.close()
        return count

    def _build_evidence_chain(self, case_id, domain, osint, telegram_intel):
        chain = []
        if telegram_intel.get("total_mentions", 0) > 0:
            chain.append({"step": 1, "from": "Telegram Intel ({} mentions, {} victims)".format(telegram_intel["total_mentions"], telegram_intel["victim_reports"]), "to": domain, "link": "Domain mentioned in {} Telegram groups".format(len(telegram_intel["groups"])), "evidence_type": "INTELLIGENCE", "strength": "MEDIUM" if telegram_intel["victim_reports"] == 0 else "STRONG"})

        rdap = osint.get("rdap", {})
        if rdap.get("registrar"):
            chain.append({"step": 2, "from": domain, "to": rdap["registrar"], "link": "Registered on {} via {}".format(rdap.get("registration_date", "unknown"), rdap["registrar"]), "evidence_type": "INFRASTRUCTURE", "strength": "CONFIRMED"})

        urlscan = osint.get("urlscan", {})
        if urlscan.get("ip"):
            chain.append({"step": 3, "from": domain, "to": "{} ({})".format(urlscan.get("server", "Unknown"), urlscan.get("ip", "")), "link": "Hosted at {} in {}".format(urlscan.get("ip", "?"), urlscan.get("country", "?")), "evidence_type": "INFRASTRUCTURE", "strength": "CONFIRMED"})

        page = osint.get("page", {})
        contacts = []
        if page.get("emails"):
            contacts.append("emails: " + ", ".join(page["emails"][:2]))
        if page.get("phones"):
            contacts.append("phones: " + ", ".join(page["phones"][:2]))
        if page.get("social_links"):
            socials = ["{}(@{})".format(s["platform"], s["handle"]) for s in page["social_links"][:3]]
            contacts.append("socials: " + ", ".join(socials))
        if contacts:
            chain.append({"step": 4, "from": domain, "to": "Contact Information", "link": "; ".join(contacts), "evidence_type": "IDENTITY_LEAD", "strength": "POSSIBLE"})

        if telegram_intel.get("usernames"):
            chain.append({"step": 5, "from": "Telegram accounts ({})".format(", ".join(telegram_intel["usernames"][:3])), "to": "Real Identity (REQUIRES LEGAL PROCESS)", "link": "Telegram can provide phone, IP, and registration data via legal request", "evidence_type": "IDENTITY_LEAD", "strength": "REQUIRES_WARRANT"})

        return chain

    def _determine_legal_pathway(self, domain, osint, telegram_intel, trigger):
        rdap = osint.get("rdap", {})
        urlscan = osint.get("urlscan", {})
        page = osint.get("page", {})

        public = []
        if rdap.get("registrar"):
            public.append("Registrar name (RDAP)")
        if rdap.get("registration_date"):
            public.append("Registration date (RDAP)")
        if urlscan.get("ip"):
            public.append("Hosting IP (URLScan)")
        if urlscan.get("server"):
            public.append("Server technology (URLScan)")
        if page.get("emails"):
            public.append("Contact emails (page content)")
        if page.get("phones"):
            public.append("Contact phones (page content)")
        if page.get("social_links"):
            public.append("Social media accounts (page content)")
        if telegram_intel.get("usernames"):
            public.append("Telegram usernames (public messages)")
        if telegram_intel.get("groups"):
            public.append("Telegram group names (public)")
        public.append("Scam type classification (GFIN analysis)")
        public.append("Victim reports count (Telegram intelligence)")

        requires_legal = []
        if rdap.get("registrar"):
            requires_legal.append("Registrant name, email, address, phone (subpoena to {})".format(rdap["registrar"]))
        if urlscan.get("server"):
            for key, info in CDN_PROVIDERS.items():
                if key in urlscan.get("server", "").lower():
                    requires_legal.append("Server logs, customer records ({})".format(info["legal"]))
                    break
        if telegram_intel.get("usernames"):
            requires_legal.append("Telegram account data: phone, IP, registration date (legal request to Telegram)")
        requires_legal.append("Banking/financial records (subpoena to financial institutions)")
        if page.get("payment_indicators"):
            requires_legal.append("Payment processor records (subpoena to {})".format(", ".join(page["payment_indicators"])))

        scam_types = telegram_intel.get("scam_types", [])
        primary_type = scam_types[0] if scam_types else "UNKNOWN"
        legal_class = LEGAL_CLASSIFICATIONS.get(primary_type, {"crime": "Unknown", "element": "Unknown", "statute": "Unknown"})

        is_recruitment = telegram_intel.get("recruitment_detected", False)

        pathway = {
            "public_evidence": public,
            "requires_legal_process": requires_legal,
            "primary_crime": legal_class["crime"],
            "legal_elements": legal_class["element"],
            "applicable_statute": legal_class["statute"],
            "is_recruitment_case": is_recruitment,
            "recommended_actions": self._recommend_legal_actions(domain, osint, telegram_intel, is_recruitment),
        }

        if is_recruitment:
            pathway["additional_crime"] = "Human Trafficking / Forced Labor"
            pathway["additional_statute"] = "Palermo Protocol / National anti-trafficking laws"
            pathway["trafficking_indicators"] = "Recruitment ads for retention/conversion/recovery agents with relocation offers"

        return pathway

    def _recommend_legal_actions(self, domain, osint, telegram_intel, is_recruitment):
        actions = []
        rdap = osint.get("rdap", {})
        urlscan = osint.get("urlscan", {})

        actions.append("Preserve evidence: screenshot website, save page content, record Telegram messages")
        actions.append("Document victim reports and attempt to contact victims for formal statements")

        if rdap.get("registrar"):
            actions.append("Send preservation request to {} (registrar) for registrant data".format(rdap["registrar"]))

        if urlscan.get("server"):
            for key, info in CDN_PROVIDERS.items():
                if key in urlscan.get("server", "").lower():
                    actions.append("Send preservation request to {} for server logs".format(info["name"]))
                    break

        if telegram_intel.get("usernames"):
            actions.append("Submit legal request to Telegram for account data on: {}".format(", ".join(telegram_intel["usernames"][:3])))

        if is_recruitment:
            actions.append("FLAG: Human trafficking indicators detected - coordinate with anti-trafficking unit")
            actions.append("Cross-reference with known trafficking cases in database")

        actions.append("Check if domain has been reported to other law enforcement or consumer protection agencies")
        return actions

    def _create_investigation_steps(self, case_id, domain, osint, legal):
        cur = self.conn.cursor()
        count = 0
        cur.execute("DELETE FROM investigation_steps WHERE case_id = %s AND officer_id IS NULL", (case_id,))

        steps = [
            {"step_name": "1. Complaint Intake & Victim Identification", "phase": "INTAKE", "result": {"target": domain, "scam_types": legal.get("primary_crime", "Unknown")}, "status": "COMPLETED"},
            {"step_name": "2. OSINT Collection (Public Data)", "phase": "OSINT", "result": {"rdap": osint.get("rdap", {}), "urlscan": osint.get("urlscan", {}), "page_analysis": {"status": osint.get("page", {}).get("status", 0), "emails": osint.get("page", {}).get("emails", []), "phones": osint.get("page", {}).get("phones", []), "social_links": osint.get("page", {}).get("social_links", [])}}, "status": "COMPLETED"},
            {"step_name": "3. Entity Identification (People, Organizations, Infrastructure)", "phase": "ENTITY", "result": {"registrar": osint.get("rdap", {}).get("registrar", "Unknown"), "hosting": osint.get("urlscan", {}).get("server", "Unknown"), "contacts_found": bool(osint.get("page", {}).get("emails") or osint.get("page", {}).get("phones"))}, "status": "COMPLETED"},
            {"step_name": "4. Evidence Chain Construction", "phase": "EVIDENCE", "result": {"chain_built": True, "public_evidence": len(legal.get("public_evidence", []))}, "status": "COMPLETED"},
            {"step_name": "5. Legal Pathway Assessment", "phase": "LEGAL", "result": {"primary_crime": legal.get("primary_crime"), "statute": legal.get("applicable_statute"), "public_evidence": len(legal.get("public_evidence", [])), "requires_legal_process": len(legal.get("requires_legal_process", [])), "recommended_actions": legal.get("recommended_actions", []), "is_recruitment": legal.get("is_recruitment_case", False)}, "status": "COMPLETED"},
            {"step_name": "6. Financial Tracing (Pending - requires wallet/transaction data)", "phase": "FINANCIAL", "result": {"status": "No wallets identified yet. Requires victim to provide transaction details."}, "status": "PENDING"},
            {"step_name": "7. Legal Process Preparation (Pending - requires officer review)", "phase": "LEGAL_PROCESS", "result": {"status": "Prepare preservation requests and subpoenas based on identified infrastructure providers."}, "status": "PENDING"},
        ]

        for i, step in enumerate(steps):
            cur.execute("INSERT INTO investigation_steps (case_id, phase, step_name, step_type, status, result, order_num, created_date) VALUES (%s, %s, %s, 'AUTO', %s, %s, %s, NOW()) ON CONFLICT DO NOTHING", (case_id, step["phase"], step["step_name"], step["status"], json.dumps(step["result"]), i + 1))
            count += 1

        self.conn.commit()
        cur.close()
        return count

    def _create_scam_website_entry(self, domain, case_id, osint, telegram_intel):
        cur = self.conn.cursor()
        page = osint.get("page", {})
        phones = page.get("phones", [])
        scam_types = telegram_intel.get("scam_types", [])
        scam_type = scam_types[0] if scam_types else "Unknown"

        if telegram_intel.get("victim_reports", 0) > 0:
            risk = "CRITICAL"
        elif telegram_intel.get("total_mentions", 0) > 5:
            risk = "HIGH"
        elif telegram_intel.get("total_mentions", 0) > 0:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        cur.execute("""INSERT INTO scam_websites (domain, scam_type, risk_level, report_count, sources, evidence_hashes, wallet_addresses, phone_numbers, countries_affected, total_loss_reported, is_verified, created_date, updated_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, NOW(), NOW())
            ON CONFLICT (domain) DO UPDATE SET risk_level = EXCLUDED.risk_level, report_count = EXCLUDED.report_count, phone_numbers = EXCLUDED.phone_numbers, updated_date = NOW()""",
            (domain, scam_type, risk, telegram_intel.get("total_mentions", 0),
             ["telegram_intelligence", "osint_analysis"],
             [case_id],
             [], phones, telegram_intel.get("groups", []), 0))
        self.conn.commit()
        cur.close()


def run_police_pipeline():
    db = psycopg2.connect(**DB_CONFIG)
    sep = "=" * 60
    print(sep)
    print("GFIN POLICE INVESTIGATION PIPELINE v2.0")
    print("Working like a detective - not a web scraper")
    print(sep)

    cur = db.cursor()
    cur.execute("SELECT case_id FROM cases ORDER BY case_id")
    case_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    print("Cases to investigate: {}".format(len(case_ids)))

    pipeline = PoliceInvestigationPipeline(db)
    total_people = 0
    total_steps = 0
    total_links = 0

    for case_id in case_ids:
        print("\n" + "-" * 40)
        print("INVESTIGATING: " + case_id)
        result = pipeline.investigate_case(case_id)

        people = result.get("people_created", 0)
        steps = result.get("investigation_steps", 0)
        chain = len(result.get("evidence_chain", []))
        legal = result.get("legal_pathway", {})

        print("  People identified: {}".format(people))
        print("  Investigation steps: {}".format(steps))
        print("  Evidence chain links: {}".format(chain))
        print("  Primary crime: {}".format(legal.get("primary_crime", "Unknown")))
        print("  Statute: {}".format(legal.get("applicable_statute", "Unknown")))
        print("  Public evidence items: {}".format(len(legal.get("public_evidence", []))))
        print("  Requires legal process: {}".format(len(legal.get("requires_legal_process", []))))
        if legal.get("is_recruitment_case"):
            print("  ** TRAFFICKING INDICATORS DETECTED **")
        if legal.get("recommended_actions"):
            print("  Recommended actions: {}".format(len(legal["recommended_actions"])))

        total_people += people
        total_steps += steps
        total_links += chain

    print("\n" + sep)
    print("POLICE INVESTIGATION PIPELINE COMPLETE")
    print(sep)

    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM people")
    print("People identified: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT role, COUNT(*) FROM people GROUP BY role ORDER BY count DESC")
    for role, count in cur.fetchall():
        print("  {}: {}".format(role, count))
    cur.execute("SELECT COUNT(*) FROM investigation_steps")
    print("Investigation steps: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM scam_websites")
    print("Scam websites: {}".format(cur.fetchone()[0]))
    cur.close()
    db.close()


if __name__ == "__main__":
    run_police_pipeline()

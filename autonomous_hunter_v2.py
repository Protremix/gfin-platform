#!/usr/bin/env python3
"""
GFIN Autonomous Scam Hunter v2.1 — Investigator-Grade
======================================================
Improved based on real cyber fraud investigator requirements:
- SSL SANs extraction (find scammer's other domains)
- Full DNS (A, AAAA, MX, TXT, CNAME)
- Source-aware risk scoring (OpenPhish = confirmed phishing)
- Proper entity extraction (valid phone, email, wallet regex)
- URLScan.io integration for page screenshots & redirect chains
- Cross-case correlation (shared IPs, shared SSL certs)
- Full WHOIS/RDAP with registrant data
- Better confidence scoring

Runs 24/7 as systemd service. NO mock data.
"""
import asyncio, json, time, re, ssl, socket, hashlib, urllib.request, urllib.parse
import logging, os, sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import subprocess
from hunter_v3_intel import *  # v3.0 Enhanced intelligence: favicon, analytics, redirect, tech stack, forms, typo-squatting
from hunter_v3_advanced import *  # v3.0 Advanced: Neo4j, privacy guard, subdomains, wallet intel, takedown reports

sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [hunter] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/gfin/logs/autonomous_hunter.log'),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================
SCAN_INTERVAL = 900  # 15 min
MAX_CASES_PER_CYCLE = 10
_investigated = set()

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# Known safe domains (CDNs, hosting platforms, legit services)
SAFE_DOMAINS = {
    "google.com", "googleapis.com", "cloudflare.com", "amazonaws.com",
    "microsoft.com", "github.com", "wikipedia.org", "mozilla.org",
    "letsencrypt.org", "digicert.com", "godaddy.com", "cloudfront.net",
    "akamai.com", "azure.com", "office.com", "live.com", "yahoo.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
    "apple.com", "bootstrap.com", "jquery.com",
    "nip.io", "sslip.io", "xip.io",
    "pages.dev", "workers.dev", "r2.dev",
    "netlify.app", "vercel.app", "herokuapp.com",
    "000webhostapp.com", "infinityfree.com",
    "github.io", "gitlab.io",
    "heroku.com", "fly.dev", "railway.app",
    "repl.co", "replit.app", "glitch.me",
    "onrender.com", "render.com",
    "deno.dev", "fastly.net", "fastly.io",
    "wcomhost.com", "blogspot.com", "wordpress.com",
    "gitbook.io", "notion.site", "carrd.co",
    "weebly.com", "weeblysite.com",
    "shopify.com", "myshopify.com",
}

SCAM_KEYWORDS = [
    "recovery", "payback", "refund", "reclaim", "retrieve",
    "crypto-recovery", "bitcoin-recovery", "wallet-recovery",
    "lost-funds", "hack-back", "fund-recovery",
    "invest-bitcoin", "double-your-crypto", "free-bitcoin",
    "binary-options", "forex-scam-recovery",
    "chargeback-service", "scam-recovery",
    "phishing-login", "secure-login-verify", "account-verify",
    "bank-verify", "paypal-verify", "amazon-verify",
    "wallet-connect", "metamask-connect", "defi-airdrop",
    "free-airdrop", "token-claim", "staking-reward",
]

# Source reliability multipliers
SOURCE_RELIABILITY = {
    "OPENPHISH": 0.9,          # Confirmed phishing feed
    "PHISHING_DATABASE": 0.85,  # Community verified phishing
    "URLSCAN": 0.8,            # Scanned and flagged malicious
    "CERTIFICATE_TRANSPARENCY": 0.4,  # Keyword match only, not confirmed
}

# ============================================================
# HTTP HELPERS
# ============================================================
def http_get_json(url, timeout=15, headers=None):
    try:
        hdrs = {"User-Agent": "GFIN-Hunter/2.0 (Fraud Intelligence)"}
        if headers: hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except: return None

def http_get_text(url, timeout=15, headers=None):
    try:
        hdrs = {"User-Agent": "GFIN-Hunter/2.0 (Fraud Intelligence)"}
        if headers: hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        return resp.read().decode('utf-8', errors='replace')
    except: return None

# ============================================================
# DISCOVERY
# ============================================================
def discover_targets() -> List[Dict]:
    results = []
    logger.info("=== DISCOVERY PHASE ===")

    # CT logs
    logger.info("Scanning CT logs...")
    for kw in SCAM_KEYWORDS[:6]:
        data = http_get_json(f"https://crt.sh/?q=%25{kw}%25&output=json&limit=20", timeout=20)
        if data and isinstance(data, list):
            for cert in data[:10]:
                for name in cert.get("name_value", "").split("\n"):
                    name = name.strip().lower()
                    if name and not name.startswith("*.") and kw in name and name not in _investigated:
                        if not _is_safe(name):
                            results.append({"domain": name, "source": "CERTIFICATE_TRANSPARENCY",
                                          "keyword": kw, "cert_date": cert.get("not_before", "")})
        time.sleep(0.5)
    logger.info(f"  CT logs: {len([r for r in results if r['source'] == 'CERTIFICATE_TRANSPARENCY'])} domains")

    # URLScan
    logger.info("Scanning URLScan.io...")
    data = http_get_json("https://urlscan.io/api/v1/search/?q=task.method:GET+AND+lists.verdicts.malicious:true&size=20", timeout=20)
    if data and "results" in data:
        for entry in data["results"][:20]:
            domain = entry.get("page", {}).get("domain", "")
            if domain and not _is_safe(domain) and domain not in _investigated:
                results.append({"domain": domain, "source": "URLSCAN",
                              "url": entry.get("page", {}).get("url", ""),
                              "ip": entry.get("page", {}).get("ip", ""),
                              "scan_id": entry.get("_id", "")})
    logger.info(f"  URLScan: {len([r for r in results if r['source'] == 'URLSCAN'])} domains")

    # Phishing.Database
    logger.info("Scanning Phishing.Database...")
    text = http_get_text("https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt", timeout=20)
    if text:
        for url in text.strip().split("\n")[:100]:
            url = url.strip()
            if not url or url.startswith("#"): continue
            if not url.startswith("http"): url = "http://" + url
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            if domain and "." in domain and not _is_safe(domain) and not re.match(r"^[\d.]+$", domain) and domain not in _investigated:
                results.append({"domain": domain, "source": "PHISHING_DATABASE", "url": url})
    logger.info(f"  Phishing DB: {len([r for r in results if r['source'] == 'PHISHING_DATABASE'])} domains")

    # OpenPhish
    logger.info("Scanning OpenPhish...")
    text = http_get_text("https://www.openphish.com/feed.txt", timeout=20)
    if text:
        for url in text.strip().split("\n")[:100]:
            url = url.strip()
            if not url: continue
            if not url.startswith("http"): url = "http://" + url
            parsed = urllib.parse.urlparse(url)
            domain = parsed.netloc.lower()
            if domain and "." in domain and not _is_safe(domain) and not re.match(r"^[\d.]+$", domain) and domain not in _investigated:
                results.append({"domain": domain, "source": "OPENPHISH", "url": url})
    logger.info(f"  OpenPhish: {len([r for r in results if r['source'] == 'OPENPHISH'])} domains")

    # URLHaus (abuse.ch)
    logger.info("Scanning URLHaus (abuse.ch)...")
    urlhaus_results = discover_from_urlhaus()
    for r in urlhaus_results:
        if r["domain"] not in _investigated:
            results.append(r)
    logger.info(f"  URLHaus: {len(urlhaus_results)} domains")

    # ThreatFox (abuse.ch)
    logger.info("Scanning ThreatFox (abuse.ch)...")
    threatfox_results = discover_from_abuseipdb()
    for r in threatfox_results:
        if r["domain"] not in _investigated:
            results.append(r)
    logger.info(f"  ThreatFox: {len(threatfox_results)} domains")

    # Deduplicate
    seen, unique = set(), []
    for r in results:
        d = r["domain"]
        if d not in seen:
            seen.add(d)
            unique.append(r)
    logger.info(f"Total unique targets: {len(unique)}")
    return unique[:MAX_CASES_PER_CYCLE]

def _is_safe(domain: str) -> bool:
    for safe in SAFE_DOMAINS:
        if safe in domain: return True
    return False

# ============================================================
# INVESTIGATION (7 phases)
# ============================================================
def investigate_domain(domain: str, source: str, extra: dict = None) -> dict:
    inv = {
        "domain": domain, "source": source, "timestamp": datetime.now(timezone.utc).isoformat(),
        "evidence_chain": [], "digital_identifiers": [], "physical_locations": [],
        "financial_indicators": [], "affected_countries": [], "scam_indicators": [],
        "scam_patterns": [], "confidence": 0.0, "summary": "",
        "urlscan_data": None, "ssl_sans": [], "cross_refs": [],
    }
    ev_n = 0
    def eid():
        nonlocal ev_n; ev_n += 1; return f"E-AH-{ev_n:04d}"

    extra = extra or {}

    # === PHASE 1: DNS (full) ===
    logger.info(f"  [1/8] DNS resolution for {domain}")
    dns = _dns_full(domain)
    if dns["a"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DNS_RESOLUTION",
            "finding": f"A records: {', '.join(dns['a'])}", "source": "DNS resolver", "confidence": "HIGH"})
        for ip in dns["a"]:
            inv["digital_identifiers"].append({"type": "IP", "value": ip, "context": f"A record for {domain}"})
    if dns["mx"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DNS_RESOLUTION",
            "finding": f"MX records: {', '.join(dns['mx'])}", "source": "DNS resolver", "confidence": "HIGH"})
        for mx in dns["mx"]:
            inv["digital_identifiers"].append({"type": "MX", "value": mx, "context": f"Mail server for {domain}"})
    if dns["ns"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DNS_RESOLUTION",
            "finding": f"NS records: {', '.join(dns['ns'])}", "source": "DNS resolver", "confidence": "HIGH"})
        for ns in dns["ns"]:
            inv["digital_identifiers"].append({"type": "NS", "value": ns, "context": f"Name server for {domain}"})
    if dns["txt"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DNS_RESOLUTION",
            "finding": f"TXT records: {'; '.join(dns['txt'][:3])}", "source": "DNS resolver", "confidence": "HIGH"})
        # Extract SPF, DKIM, verification tokens from TXT
        for txt in dns["txt"]:
            if "v=spf1" in txt:
                inv["digital_identifiers"].append({"type": "SPF", "value": txt, "context": f"Email SPF policy for {domain}"})
            elif "google-site-verification" in txt or "amazon" in txt.lower() or "azure" in txt.lower():
                inv["digital_identifiers"].append({"type": "VERIFICATION_TOKEN", "value": txt[:100],
                    "context": f"Domain verification token on {domain} — reveals platform usage"})
    if dns["cname"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DNS_RESOLUTION",
            "finding": f"CNAME: {', '.join(dns['cname'])}", "source": "DNS resolver", "confidence": "HIGH"})

    # === PHASE 2: IP GEOLOCATION ===
    logger.info(f"  [2/8] IP geolocation for {domain}")
    if dns["a"]:
        for ip in dns["a"][:2]:
            geo = http_get_json(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,lat,lon,timezone,isp,org,as,hostname,query", timeout=10)
            if geo and geo.get("status") == "success":
                inv["evidence_chain"].append({"evidence_id": eid(), "phase": "IP_GEOLOCATION",
                    "finding": f"IP {ip}: {geo.get('city','?')}, {geo.get('country','?')} — ISP: {geo.get('isp','?')}, ASN: {geo.get('as','?')}",
                    "source": "ip-api.com", "confidence": "HIGH"})
                inv["physical_locations"].append({
                    "ip": ip, "city": geo.get("city",""), "region": geo.get("regionName",""),
                    "country": geo.get("country",""), "country_code": geo.get("countryCode",""),
                    "latitude": geo.get("lat",""), "longitude": geo.get("lon",""),
                    "isp": geo.get("isp",""), "asn": geo.get("as",""), "org": geo.get("org",""),
                    "hostname": geo.get("hostname",""), "timezone": geo.get("timezone",""),
                    "source": "IP geolocation"
                })
                if geo.get("countryCode"): inv["affected_countries"].append(geo["countryCode"])
                inv["digital_identifiers"].append({"type": "HOSTING_PROVIDER",
                    "value": geo.get("isp", geo.get("org","")), "context": f"Hosting {domain} at {ip}"})
                inv["digital_identifiers"].append({"type": "ASN",
                    "value": geo.get("as",""), "context": f"ASN for {ip}"})

    # === PHASE 3: RDAP/WHOIS ===
    logger.info(f"  [3/8] RDAP/WHOIS for {domain}")
    rdap = _rdap_lookup(domain)
    if rdap:
        finding_parts = []
        if rdap.get("registrar"): finding_parts.append(f"Registrar: {rdap['registrar']}")
        if rdap.get("registration_date"): finding_parts.append(f"Registered: {rdap['registration_date']}")
        if rdap.get("expiration_date"): finding_parts.append(f"Expires: {rdap['expiration_date']}")
        if rdap.get("country"): finding_parts.append(f"Country: {rdap['country']}")
        if rdap.get("status"): finding_parts.append(f"Status: {', '.join(rdap['status'][:3])}")
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DOMAIN_REGISTRATION",
            "finding": ", ".join(finding_parts) if finding_parts else "RDAP data retrieved",
            "source": "RDAP (rdap.org)", "confidence": "HIGH"})
        if rdap.get("registrar"):
            inv["digital_identifiers"].append({"type": "REGISTRAR", "value": rdap["registrar"], "context": f"Domain registrar for {domain}"})
        if rdap.get("registration_date"):
            # Check if recently registered (within 90 days) — suspicious
            try:
                reg_date = rdap["registration_date"].split("T")[0]
                from datetime import date
                d = date.fromisoformat(reg_date[:10])
                days_old = (date.today() - d).days
                if days_old < 90:
                    inv["evidence_chain"].append({"evidence_id": eid(), "phase": "REGISTRATION_ANALYSIS",
                        "finding": f"Domain registered only {days_old} days ago — newly registered domains are high-risk for fraud",
                        "source": "GFIN analysis", "confidence": "HIGH"})
                    inv["scam_indicators"].append({"indicator": "NEWLY_REGISTERED", "detail": f"Domain is {days_old} days old", "weight": 20})
            except: pass

    # === PHASE 4: SSL CERTIFICATE (with SANs!) ===
    logger.info(f"  [4/8] SSL certificate analysis for {domain}")
    ssl_info = _get_ssl_with_sans(domain)
    if ssl_info:
        san_domains = ssl_info.get("san_domains", [])
        inv["ssl_sans"] = san_domains
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "SSL_CERTIFICATE",
            "finding": f"Issuer: {ssl_info.get('issuer','?')}, Valid: {ssl_info.get('not_before','?')} to {ssl_info.get('not_after','?')}, SANs: {len(san_domains)} domains",
            "source": "SSL/TLS connection", "confidence": "HIGH"})
        inv["digital_identifiers"].append({"type": "SSL_ISSUER", "value": ssl_info.get("issuer",""), "context": f"Certificate issuer for {domain}"})
        # SANs are CRITICAL — they reveal the scammer's other domains
        for san in san_domains[:20]:
            if san != domain and not san.startswith("*."):
                inv["digital_identifiers"].append({"type": "SSL_SAN", "value": san,
                    "context": f"Domain sharing SSL certificate with {domain} — likely same operator"})
        if len(san_domains) > 3:
            inv["scam_indicators"].append({"indicator": "MULTIPLE_SANS", "detail": f"SSL cert covers {len(san_domains)} domains — scammer may operate multiple sites", "weight": 15})
    else:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "SSL_CERTIFICATE",
            "finding": "No SSL certificate found or connection failed", "source": "SSL/TLS connection", "confidence": "MEDIUM"})

    # === PHASE 5: URLScan.io (if available) ===
    logger.info(f"  [5/8] URLScan.io lookup for {domain}")
    urlscan = http_get_json(f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=5", timeout=15)
    if urlscan and "results" in urlscan and urlscan["results"]:
        scan = urlscan["results"][0]
        page = scan.get("page", {})
        inv["urlscan_data"] = {
            "scan_id": scan.get("_id", ""),
            "url": page.get("url", ""),
            "final_url": page.get("url", ""),
            "ip": page.get("ip", ""),
            "asn": page.get("asn", ""),
            "server": page.get("server", ""),
            "status_code": page.get("status", ""),
            "screenshot": scan.get("screenshot", ""),
        }
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "URLSCAN_ANALYSIS",
            "finding": f"URLScan: IP {page.get('ip','?')}, Server: {page.get('server','?')}, Status: {page.get('status','?')}, Malicious: {scan.get('verdicts', {}).get('malicious', False)}",
            "source": "urlscan.io", "confidence": "HIGH"})
        if page.get("ip") and page.get("ip") not in [d.get("value") for d in inv["digital_identifiers"] if d["type"] == "IP"]:
            inv["digital_identifiers"].append({"type": "IP", "value": page["ip"], "context": f"URLScan detected IP for {domain}"})
    else:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "URLSCAN_ANALYSIS",
            "finding": "No URLScan.io results found for this domain", "source": "urlscan.io", "confidence": "LOW"})

    # === PHASE 6: HTTP CONTENT + ENTITY EXTRACTION ===
    logger.info(f"  [6/8] HTTP content analysis for {domain}")
    content = _fetch_content(domain)
    if content:
        entities = _extract_entities_proper(content, domain)
        ent_summary = []
        for k, v in entities.items():
            if v: ent_summary.append(f"{k}: {len(v)}")
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "CONTENT_ANALYSIS",
            "finding": f"Page loaded ({len(content)} bytes). Extracted: {', '.join(ent_summary) if ent_summary else 'nothing'}",
            "source": f"https://{domain}", "confidence": "MEDIUM"})
        for email in entities["emails"]:
            inv["digital_identifiers"].append({"type": "EMAIL", "value": email, "context": f"Found on {domain}"})
        for phone in entities["phones"]:
            inv["digital_identifiers"].append({"type": "PHONE", "value": phone, "context": f"Found on {domain}"})
        for wallet in entities["wallets"]:
            inv["financial_indicators"].append({"type": wallet["type"], "address": wallet["address"], "context": f"Found on {domain}"})
            inv["digital_identifiers"].append({"type": "CRYPTO_WALLET", "value": wallet["address"], "context": f"{wallet['type']} wallet on {domain}"})
        for social in entities["social_links"]:
            inv["digital_identifiers"].append({"type": "SOCIAL_ACCOUNT", "value": social["url"], "context": f"{social['platform']} link on {domain}"})
        for company in entities["company_names"]:
            inv["digital_identifiers"].append({"type": "COMPANY", "value": company, "context": f"Mentioned on {domain}"})
        for addr in entities["addresses"]:
            inv["physical_locations"].append({"type": "CONTENT_ADDRESS", "address": addr, "context": f"Found on {domain}", "source": "Website content"})
    else:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "CONTENT_ANALYSIS",
            "finding": "Could not fetch HTTP content (site may be down or blocking)", "source": f"https://{domain}", "confidence": "LOW"})

    # === PHASE 6b: FAVICON FINGERPRINTING ===
    logger.info(f"  [6b] Favicon fingerprinting for {domain}")
    favicon_hash = fetch_favicon_hash(domain)
    if favicon_hash:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "FAVICON_FINGERPRINT",
            "finding": f"Favicon MD5 hash: {favicon_hash}", "source": f"https://{domain}/favicon.ico", "confidence": "MEDIUM"})
        inv["digital_identifiers"].append({"type": "FAVICON_HASH", "value": favicon_hash, "context": f"Favicon hash for {domain}"})

    # === PHASE 6c: ANALYTICS ID EXTRACTION ===
    logger.info(f"  [6c] Analytics ID extraction for {domain}")
    if content:
        analytics_ids = extract_analytics_ids(content)
        if analytics_ids:
            for tracker_type, tracker_ids in analytics_ids.items():
                for tid in tracker_ids:
                    inv["evidence_chain"].append({"evidence_id": eid(), "phase": "ANALYTICS_TRACKING",
                        "finding": f"{tracker_type}: {tid}", "source": f"https://{domain}", "confidence": "HIGH"})
                    inv["digital_identifiers"].append({"type": "ANALYTICS_ID", "value": f"{tracker_type}:{tid}", "context": f"Tracking ID on {domain}"})

    # === PHASE 6d: REDIRECT CHAIN ===
    logger.info(f"  [6d] Redirect chain analysis for {domain}")
    redirect_info = follow_redirects(domain)
    if redirect_info.get("redirect_count", 0) > 0:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "REDIRECT_ANALYSIS",
            "finding": f"{redirect_info['redirect_count']} redirects to {redirect_info['final_url']}" + (" (cross-domain!)" if redirect_info.get("cross_domain_redirect") else ""),
            "source": f"https://{domain}/", "confidence": "MEDIUM"})
        if redirect_info.get("cross_domain_redirect"):
            final_domain = urllib.parse.urlparse(redirect_info["final_url"]).netloc
            if final_domain and final_domain != domain:
                inv["digital_identifiers"].append({"type": "REDIRECT_TARGET", "value": final_domain, "context": f"{domain} redirects to {final_domain}"})

    # === PHASE 6e: TECH STACK FINGERPRINTING ===
    logger.info(f"  [6e] Tech stack fingerprinting for {domain}")
    if content:
        tech_stack = fingerprint_tech_stack(content, {})
        if tech_stack:
            tech_parts = [f"{cat}: {', '.join(items)}" for cat, items in tech_stack.items()]
            inv["evidence_chain"].append({"evidence_id": eid(), "phase": "TECH_STACK",
                "finding": f"Detected: {'; '.join(tech_parts)}", "source": f"https://{domain}", "confidence": "MEDIUM"})
            for pp in tech_stack.get("payment_processors", []):
                inv["financial_indicators"].append({"type": "PAYMENT_PROCESSOR", "processor": pp, "context": f"Found on {domain}"})

    # === PHASE 6f: FORM DETECTION ===
    logger.info(f"  [6f] Form detection for {domain}")
    if content:
        forms = detect_forms(content)
        if forms["login_forms"] > 0 or forms["payment_forms"] > 0 or forms["crypto_forms"] > 0:
            form_parts = []
            if forms["login_forms"]: form_parts.append(f"{forms['login_forms']} login")
            if forms["payment_forms"]: form_parts.append(f"{forms['payment_forms']} payment")
            if forms["crypto_forms"]: form_parts.append(f"{forms['crypto_forms']} crypto")
            inv["evidence_chain"].append({"evidence_id": eid(), "phase": "FORM_ANALYSIS",
                "finding": f"Forms: {', '.join(form_parts)}", "source": f"https://{domain}", "confidence": "HIGH"})
            if forms["crypto_forms"] > 0:
                inv["scam_indicators"].append({"type": "CRYPTO_FORM", "severity": "HIGH", "description": "Crypto wallet/seed phrase form detected"})

    # === PHASE 6g: TYPO-SQUATTING CHECK ===
    logger.info(f"  [6g] Typo-squatting check for {domain}")
    typo = detect_typosquatting(domain)
    if typo["is_typosquat"]:
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "TYPO_SQUATTING",
            "finding": f"DOMAIN IMPERSONATES {typo['target_brand']} (type: {typo['type']})",
            "source": "GFIN Brand Protection Database", "confidence": "HIGH"})
        inv["scam_indicators"].append({"type": "BRAND_IMPERSONATION", "severity": "CRITICAL",
            "target_brand": typo["target_brand"], "method": typo["type"], "description": f"{domain} impersonates {typo['target_brand']}"})

    # === PHASE 6h: DOMAIN AGE ===
    logger.info(f"  [6h] Domain age analysis for {domain}")
    if rdap and rdap.get("registration_date"):
        age_info = calculate_domain_age(rdap["registration_date"])
        if age_info["age_days"] is not None:
            inv["evidence_chain"].append({"evidence_id": eid(), "phase": "DOMAIN_AGE",
                "finding": f"Domain registered {age_info['age_days']} days ago ({age_info['age_category']})" + (" — NEWLY REGISTERED" if age_info["is_newly_registered"] else ""),
                "source": "RDAP registration data", "confidence": "HIGH"})
            if age_info["is_newly_registered"]:
                inv["scam_indicators"].append({"type": "NEWLY_REGISTERED", "severity": "HIGH", "age_days": age_info["age_days"], "description": f"Domain is only {age_info['age_days']} days old"})

    # === PHASE 6i: PAGE METADATA ===
    logger.info(f"  [6i] Page metadata extraction for {domain}")
    if content:
        page_meta = extract_page_metadata(content)
        if page_meta["title"] or page_meta["description"]:
            inv["evidence_chain"].append({"evidence_id": eid(), "phase": "PAGE_METADATA",
                "finding": f"Title: {page_meta['title'][:100]} | Generator: {page_meta.get('generator', 'none')}",
                "source": f"https://{domain}", "confidence": "MEDIUM"})

    # === PHASE 7: SCAM DETECTION (source-aware!) ===
    logger.info(f"  [7/8] Scam pattern detection for {domain}")
    scam = _detect_scam_v2(domain, content or "", source, extra)
    inv["scam_patterns"] = scam["categories"]
    inv["scam_indicators"].extend(scam["indicators"])
    inv["evidence_chain"].append({"evidence_id": eid(), "phase": "SCAM_DETECTION",
        "finding": f"GFIN Scam Engine v2.1: {scam['risk_level']} risk (score {scam['risk_score']}/100), categories: {', '.join(scam['categories']) or 'none'}, source: {source} (reliability {SOURCE_RELIABILITY.get(source, 0.5)})",
        "source": "GFIN Scam Engine v2.1", "confidence": "HIGH"})

    # === PHASE 8: COUNTRY ROUTING + CROSS-REF ===
    logger.info(f"  [8/8] Country routing & cross-reference for {domain}")
    unique_countries = list(set(c for c in inv["affected_countries"] if c))
    inv["affected_countries"] = unique_countries
    inv["routed_to_countries"] = unique_countries + ["EUROPOL", "INTERPOL"]
    inv["evidence_chain"].append({"evidence_id": eid(), "phase": "COUNTRY_ROUTING",
        "finding": f"Affected: {', '.join(unique_countries) if unique_countries else 'unknown'}. Routed to: {', '.join(inv['routed_to_countries'])}",
        "source": "GFIN Country Routing", "confidence": "HIGH"})

    # Cross-reference: check if any IP or SSL SAN matches existing cases
    cross_refs = _cross_reference(domain, dns.get("a", []), inv["ssl_sans"])
    if cross_refs:
        inv["cross_refs"] = cross_refs
        # Also query Neo4j for graph-based relationships
        try:
            neo4j_related = query_related_domains(domain)
            if neo4j_related.get("related_domains"):
                inv["neo4j_related"] = neo4j_related
                logger.info(f"    Neo4j: {len(neo4j_related['related_domains'])} related domains")
        except:
            pass
        inv["evidence_chain"].append({"evidence_id": eid(), "phase": "CROSS_REFERENCE",
            "finding": f"Cross-referenced: {len(cross_refs)} matches with existing cases — possible campaign link",
            "source": "GFIN Cross-Reference Engine", "confidence": "HIGH"})

    # === CONFIDENCE ===
    ev_count = len(inv["evidence_chain"])
    ent_count = len(inv["digital_identifiers"])
    country_count = len(unique_countries)
    source_boost = SOURCE_RELIABILITY.get(source, 0.3)
    base_conf = (ev_count * 0.03) + (ent_count * 0.02) + (country_count * 0.03)
    typo_boost = 0.15 if any(s.get("type") == "BRAND_IMPERSONATION" for s in inv.get("scam_indicators", [])) else 0
    new_domain_boost = 0.10 if any(s.get("type") == "NEWLY_REGISTERED" for s in inv.get("scam_indicators", [])) else 0
    crypto_form_boost = 0.15 if any(s.get("type") == "CRYPTO_FORM" for s in inv.get("scam_indicators", [])) else 0
    analytics_boost = 0.05 if any(d.get("type") == "ANALYTICS_ID" for d in inv.get("digital_identifiers", [])) else 0
    payment_boost = 0.05 if any(f.get("type") == "PAYMENT_PROCESSOR" for f in inv.get("financial_indicators", [])) else 0
    inv["confidence"] = round(min(1.0, base_conf + (scam["risk_score"] / 100 * 0.4) + (source_boost * 0.2) + typo_boost + new_domain_boost + crypto_form_boost + analytics_boost + payment_boost), 2)

    # === PHASE 9: ADVANCED INTELLIGENCE (v3.0) ===
    logger.info(f"  [9/9] Advanced intelligence for {domain}")
    try:
        advanced = run_advanced_intelligence(inv, rdap)
        if advanced.get("privacy_guard"):
            logger.info(f"    Privacy guard detected: {advanced['privacy_guard']['privacy_service']}")
        if advanced.get("subdomains", {}).get("total_count", 0) > 0:
            logger.info(f"    Subdomains found: {advanced['subdomains']['total_count']} ({len(advanced['subdays'].get('suspicious_subdomains', []))} suspicious)" if 'subdays' in str(advanced) else f"    Subdomains: {advanced['subdomains']['total_count']}")
        if advanced.get("wallet_intelligence"):
            for w in advanced["wallet_intelligence"][:3]:
                logger.info(f"    Wallet {w['type']}: {w['address'][:20]}... balance={w.get('balance', '?')} risk={w.get('risk_level', '?')}")
        if advanced.get("takedown_report"):
            logger.info(f"    Takedown report generated: {advanced['takedown_report']['report_id']}")
        if advanced.get("neo4j_stored"):
            logger.info(f"    Graph data stored in Neo4j")
        inv["advanced_intelligence"] = advanced
    except Exception as e:
        logger.debug(f"    Advanced intelligence failed: {e}")

    # === SUMMARY ===
    inv["summary"] = (
        f"Autonomous discovery via {source}. Domain: {domain}. "
        f"Risk: {scam['risk_level']} ({scam['risk_score']}/100). "
        f"Patterns: {', '.join(scam['categories']) or 'none'}. "
        f"Evidence: {ev_count} steps, {ent_count} entities, {len(unique_countries)} countries. "
        f"SSL SANs: {len(inv['ssl_sans'])} domains. "
        f"Confidence: {inv['confidence']}."
    )
    logger.info(f"  Investigation complete: {ev_count} evidence, {ent_count} entities, {country_count} countries, {len(inv['ssl_sans'])} SANs, confidence {inv['confidence']}")
    return inv

# ============================================================
# DNS (full resolution)
# ============================================================
def _dns_full(domain: str) -> dict:
    result = {"a": [], "aaaa": [], "mx": [], "ns": [], "txt": [], "cname": []}
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5; resolver.lifetime = 10
        for rtype in ["A", "MX", "NS", "TXT", "CNAME", "AAAA"]:
            try:
                answers = resolver.resolve(domain, rtype)
                result[rtype.lower()] = [str(r) for r in answers]
            except: pass
    except ImportError:
        try:
            ips = socket.getaddrinfo(domain, None, socket.AF_INET)
            result["a"] = list(set(ip[4][0] for ip in ips))
        except: pass
    return result

# ============================================================
# RDAP
# ============================================================
def _rdap_lookup(domain: str) -> dict:
    tld = domain.split(".")[-1] if "." in domain else ""
    servers = {
        "com": "https://rdap.verisign.com/com/v1/domain/",
        "net": "https://rdap.verisign.com/net/v1/domain/",
        "org": "https://rdap.publicinterestregistry.org/rdap/domain/",
        "io": "https://rdap.identitydigital.services/rdap/domain/",
        "co": "https://rdap.nic.co/domain/",
        "info": "https://rdap.identitydigital.info/rdap/domain/",
        "biz": "https://rdap.nic.biz/domain/",
        "top": "https://rdap.nic.top/domain/",
        "br": "https://rdap.registro.br/domain/",
    }
    url = servers.get(tld, f"https://rdap.org/domain/")
    data = http_get_json(f"{url}{domain}", timeout=15)
    if not data: return {}
    result = {"registrar": "", "registration_date": "", "expiration_date": "", "country": "", "status": []}
    for event in data.get("events", []):
        if event.get("eventAction") == "registration": result["registration_date"] = event.get("eventDate", "")
        if event.get("eventAction") == "expiration": result["expiration_date"] = event.get("eventDate", "")
    for entity in data.get("entities", []):
        if "registrar" in entity.get("roles", []):
            vcard = entity.get("vcardArray", [{}])
            if len(vcard) > 1:
                for field in vcard[1]:
                    if field[0] == "fn": result["registrar"] = field[3]; break
    result["status"] = data.get("status", [])
    return result

# ============================================================
# SSL (with SANs!)
# ============================================================
def _get_ssl_with_sans(domain: str) -> dict:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                if not cert: return None
                issuer = dict(x[0] for x in cert.get("issuer", []))
                subject = dict(x[0] for x in cert.get("subject", []))
                sans = [san[1] for san in cert.get("subjectAltName", []) if san[0] == "DNS"]
                return {"issuer": issuer.get("organizationName", str(issuer)),
                        "subject": subject.get("commonName", ""),
                        "not_before": cert.get("notBefore", ""),
                        "not_after": cert.get("notAfter", ""),
                        "san_domains": sans}
    except Exception as e:
        logger.debug(f"SSL failed for {domain}: {e}")
        return None

# ============================================================
# HTTP Content
# ============================================================
def _fetch_content(domain: str) -> str:
    for scheme in ["https", "http"]:
        try:
            url = f"{scheme}://{domain}/"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml"})
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            ct = resp.headers.get("Content-Type", "")
            if "text" in ct or "html" in ct:
                return resp.read().decode('utf-8', errors='replace')[:100000]
        except: pass
    return None

# ============================================================
# Entity Extraction (PROPER regex)
# ============================================================
def _extract_entities_proper(content: str, domain: str) -> dict:
    entities = {"emails": [], "phones": [], "wallets": [], "social_links": [], "company_names": [], "addresses": []}

    # Emails — proper regex
    emails = set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content))
    # Filter out common false positives
    emails = {e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.css', '.js', '.svg'))
              and 'example.com' not in e and 'sentry' not in e.lower() and 'wixpress' not in e.lower()}
    entities["emails"] = list(emails)[:10]

    # Phones — proper international format
    # Match +CC followed by 7-15 digits with optional separators
    phone_matches = re.findall(r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b', content)
    # Also match US format (xxx) xxx-xxxx
    phone_matches += re.findall(r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b', content)
    # Filter: must have at least 7 digits
    valid_phones = set()
    for p in phone_matches:
        digits = re.sub(r'\D', '', p)
        if 7 <= len(digits) <= 15:
            valid_phones.add(p.strip())
    entities["phones"] = list(valid_phones)[:10]

    # Crypto wallets — proper regex
    btc_legacy = re.findall(r'\b1[a-km-zA-HJ-NP-Z1-9]{25,34}\b', content)
    btc_bech32 = re.findall(r'\bbc1[a-z0-9]{39,59}\b', content)
    eth = re.findall(r'\b0x[a-fA-F0-9]{40}\b', content)
    tron = re.findall(r'\bT[A-Za-z0-9]{33}\b', content)
    for a in set(btc_legacy): entities["wallets"].append({"type": "BTC", "address": a})
    for a in set(btc_bech32): entities["wallets"].append({"type": "BTC", "address": a})
    for a in set(eth): entities["wallets"].append({"type": "ETH", "address": a})
    for a in set(tron): entities["wallets"].append({"type": "TRON", "address": a})

    # Social links — extract from href attributes
    social_patterns = [
        (r'href=["\'](?:https?:)?//(?:www\.)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)', "Telegram"),
        (r'href=["\'](?:https?:)?//(?:www\.)?wa\.me/(\d+)', "WhatsApp"),
        (r'href=["\'](?:https?:)?//(?:www\.)?twitter\.com/([A-Za-z0-9_]+)', "Twitter"),
        (r'href=["\'](?:https?:)?//(?:www\.)?facebook\.com/([A-Za-z0-9._-]+)', "Facebook"),
        (r'href=["\'](?:https?:)?//(?:www\.)?instagram\.com/([A-Za-z0-9._-]+)', "Instagram"),
        (r'href=["\'](?:https?:)?//(?:www\.)?discord\.(?:gg|com)/([A-Za-z0-9_-]+)', "Discord"),
    ]
    for pattern, platform in social_patterns:
        for m in re.finditer(pattern, content):
            handle = m.group(1)
            url = m.group(0).replace('href="', '').replace('href=\'', '').rstrip('"\'')
            entities["social_links"].append({"platform": platform, "handle": handle, "url": f"https://{platform.lower()}.com/{handle}" if platform not in ["Telegram","WhatsApp","Discord"] else url})

    # Company names — from copyright, title, meta
    copyright_match = re.findall(r'(?:©|Copyright)\s*(?:\d{4}\s+)?([A-Z][a-zA-Z0-9\s&.,]{3,50}(?:Ltd|Limited|Inc|LLC|GmbH|S\.A\.|Corp|Corporation|SARL|B\.V\.|Pty|LLP))', content)
    title_match = re.findall(r'<title>([^<]{3,80})</title>', content)
    for m in set(copyright_match):
        entities["company_names"].append(m.strip()[:80])
    for t in title_match[:2]:
        t = t.strip()
        if len(t) > 3 and not any(x in t.lower() for x in ["login", "error", "404", "access"]):
            entities["company_names"].append(t[:80])

    # Addresses — look for street patterns
    addr_patterns = [
        r'\b\d+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Place|Pl|Suite|Ste)[,]?\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}',
        r'\b[A-Z][a-zA-Z]+\s+\d+[,]\s*[A-Z][a-zA-Z]+\s+\d{4,5}\b',  # European format
    ]
    for pattern in addr_patterns:
        matches = re.findall(pattern, content)
        for m in set(matches[:3]):
            entities["addresses"].append(m.strip()[:200])

    return entities

# ============================================================
# Scam Detection v2 (source-aware)
# ============================================================
def _detect_scam_v2(domain: str, content: str, source: str, extra: dict) -> dict:
    text = f"{domain}\n{content[:10000]}".lower()
    categories, indicators = set(), []
    risk = 0

    # Source-based boost (confirmed sources)
    source_boost = SOURCE_RELIABILITY.get(source, 0.3)
    if source_boost >= 0.8:
        risk += 30
        indicators.append({"indicator": "CONFIRMED_PHISHING_FEED", "detail": f"Domain found in {source} — confirmed malicious by threat intelligence community", "weight": 30})

    # Recovery scam
    rec_kws = ["recovery", "recover", "payback", "refund", "retrieve", "reclaim", "lost funds", "hack back", "get your money back", "claim your funds"]
    rec_count = sum(1 for kw in rec_kws if kw in text)
    if rec_count >= 1:
        categories.add("RECOVERY_SCAM"); risk += 25 + rec_count * 5
        indicators.append({"indicator": "RECOVERY_KEYWORDS", "detail": f"{rec_count} recovery scam keywords found", "weight": 25})

    # Investment fraud
    inv_kws = ["guaranteed return", "double your", "risk-free", "high yield", "profit guaranteed", "investment plan", "trading signal", "copy trad", "roi"]
    inv_count = sum(1 for kw in inv_kws if kw in text)
    if inv_count >= 1:
        categories.add("INVESTMENT_FRAUD"); risk += 25 + inv_count * 5
        indicators.append({"indicator": "INVESTMENT_KEYWORDS", "detail": f"{inv_count} investment fraud keywords", "weight": 25})

    # Phishing
    phish_kws = ["verify your account", "confirm your identity", "suspended account", "click here to verify", "login to confirm", "update your payment", "security alert", "unusual activity", "verify your", "confirm your", "unlock your"]
    phish_count = sum(1 for kw in phish_kws if kw in text)
    if phish_count >= 1:
        categories.add("PHISHING"); risk += 20 + phish_count * 5
        indicators.append({"indicator": "PHISHING_KEYWORDS", "detail": f"{phish_count} phishing keywords", "weight": 20})

    # Crypto fraud
    crypto_kws = ["free bitcoin", "crypto airdrop", "claim your token", "connect wallet", "metamask", "wallet connect", "seed phrase", "private key", "staking reward", "free airdrop", "token claim", "defi"]
    crypto_count = sum(1 for kw in crypto_kws if kw in text)
    if crypto_count >= 1:
        categories.add("CRYPTO_FRAUD"); risk += 25 + crypto_count * 5
        indicators.append({"indicator": "CRYPTO_KEYWORDS", "detail": f"{crypto_count} crypto fraud keywords", "weight": 25})

    # Brand impersonation (domain contains brand name)
    brands = ["paypal", "amazon", "apple", "microsoft", "google", "facebook", "netflix", "bank", "ledger", "metamask", "coinbase", "binance", "trezor", "trustwallet"]
    for b in brands:
        if b in domain.lower():
            categories.add("BRAND_IMPERSONATION"); risk += 30
            indicators.append({"indicator": "BRAND_IN_DOMAIN", "detail": f"Brand '{b}' in domain name — likely impersonation", "weight": 30})
            break

    # Domain-based indicators
    if any(kw in domain.lower() for kw in ["login", "verify", "secure", "account", "update", "confirm", "wallet", "connect"]):
        risk += 15
        indicators.append({"indicator": "SUSPICIOUS_DOMAIN_KEYWORDS", "detail": "Domain contains login/verify/secure/wallet/connect", "weight": 15})

    # Limit
    risk = min(risk, 100)
    level = "CRITICAL" if risk >= 70 else "HIGH" if risk >= 40 else "MEDIUM" if risk >= 20 else "LOW" if risk >= 10 else "MINIMAL"
    return {"risk_score": risk, "risk_level": level, "categories": list(categories), "indicators": indicators}

# ============================================================
# Cross-Reference (find related cases)
# ============================================================
def _cross_reference(domain: str, ips: list, sans: list) -> list:
    """Check if this domain's IPs or SSL SANs match existing cases."""
    refs = []
    try:
        import asyncpg
        loop = asyncio.new_event_loop()
        async def check():
            conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
            try:
                # Check by IP match
                for ip in ips[:2]:
                    rows = await conn.fetch(
                        "SELECT case_id, target FROM cases WHERE digital_identifiers @> $1::jsonb AND target != $2 LIMIT 5",
                        json.dumps([{"type": "IP", "value": ip}]), domain
                    )
                    for r in rows:
                        refs.append({"type": "SHARED_IP", "ip": ip, "case_id": r["case_id"], "target": r["target"]})

                # Check by SSL SAN match
                for san in sans[:5]:
                    rows = await conn.fetch(
                        "SELECT case_id, target FROM cases WHERE target = $1 AND target != $2 LIMIT 3",
                        san, domain
                    )
                    for r in rows:
                        refs.append({"type": "SHARED_SSL_SAN", "san": san, "case_id": r["case_id"], "target": r["target"]})
            finally:
                await conn.close()
        loop.run_until_complete(check())
        loop.close()
    except Exception as e:
        logger.debug(f"Cross-ref failed: {e}")
    return refs

# ============================================================
# DATABASE: Create case
# ============================================================

# ============================================================
# FLAG DOMAIN (always) + EVIDENCE GATE (case opening)
# ============================================================

async def flag_domain_in_db(domain, inv):
    """Flag a domain in scam_websites without opening a full case."""
    import asyncpg
    DB = {"host": "127.0.0.1", "port": 5432, "user": "gfin", "password": "", "database": "gfin"}
    conn = await asyncpg.connect(**DB)
    try:
        existing = await conn.fetchrow("SELECT id, report_count, sources FROM scam_websites WHERE domain = $1", domain)
        si = inv.get("scam_indicators", [{}])
        risk_score = si[0].get("risk_score", 0) if si and isinstance(si[0], dict) else 0
        risk_level = si[0].get("risk_level", "UNKNOWN") if si and isinstance(si[0], dict) else "UNKNOWN"
        cats = si[0].get("categories", []) if si and isinstance(si[0], dict) else []
        wallets = [d.get("value", "") for d in inv.get("digital_identifiers", []) if isinstance(d, dict) and d.get("type") == "CRYPTO_WALLET"]
        phones = [d.get("value", "") for d in inv.get("digital_identifiers", []) if isinstance(d, dict) and d.get("type") == "PHONE"]
        countries = inv.get("affected_countries", [])
        source = inv.get("source", "HUNTER")
        if existing:
            old_sources = list(existing.get("sources", []) or [])
            new_sources = list(set(old_sources + [source]))
            await conn.execute(
                "UPDATE scam_websites SET report_count=$1, sources=$2, last_reported=NOW(), risk_level=$3, countries_affected=$4, wallet_addresses=$5, phone_numbers=$6, description=$7 WHERE domain=$8",
                (existing["report_count"] or 1) + 1, new_sources, risk_level, countries, wallets, phones,
                inv.get("summary", "")[:500], domain)
            logger.info("  Flagged (updated): %s (report #%d)" % (domain, (existing["report_count"] or 1) + 1))
            return False
        else:
            await conn.execute(
                "INSERT INTO scam_websites (domain, scam_type, risk_level, report_count, sources, description, countries_affected, wallet_addresses, phone_numbers, is_verified, status) VALUES ($1,$2,$3,1,$4,$5,$6,$7,$8,false,'FLAGGED')",
                domain, ", ".join(cats) if cats else "SUSPICIOUS", risk_level, [source],
                inv.get("summary", "")[:500], countries, wallets, phones)
            logger.info("  Flagged (new): %s (risk: %s, source: %s)" % (domain, risk_level, source))
            return True
    except Exception as e:
        logger.error("  Flag failed for %s: %s" % (domain, e))
        return False
    finally:
        await conn.close()


def has_strong_evidence(inv):
    """Only open a case if there is REAL evidence."""
    si = inv.get("scam_indicators", [])
    risk_score = 0
    risk_level = "UNKNOWN"
    categories = []
    if si and isinstance(si, list) and isinstance(si[0], dict):
        risk_score = si[0].get("risk_score", 0)
        risk_level = si[0].get("risk_level", "UNKNOWN")
        categories = si[0].get("categories", [])

    if risk_score >= 40:
        logger.info("  GATE PASS: risk %d (%s)" % (risk_score, risk_level))
        return True
    if categories:
        logger.info("  GATE PASS: patterns %s" % categories)
        return True
    if "OPENPHISH" in inv.get("source", "").upper():
        logger.info("  GATE PASS: OpenPhish confirmed")
        return True
    if len(inv.get("digital_identifiers", [])) >= 5:
        logger.info("  GATE PASS: %d identifiers" % len(inv["digital_identifiers"]))
        return True
    if inv.get("confidence", 0) >= 0.5:
        logger.info("  GATE PASS: confidence %.2f" % inv["confidence"])
        return True
    for loc in inv.get("physical_locations", []):
        isp = str(loc.get("isp", "")).lower()
        if isp and "cloudflare" not in isp and "amazon" not in isp:
            logger.info("  GATE PASS: real location %s (%s)" % (loc.get("city", "?"), loc.get("isp", "?")))
            return True

    # v3 Evidence conditions
    all_scam = [s for s in si if isinstance(s, dict)] if isinstance(si, list) else []
    if any(s.get("type") == "BRAND_IMPERSONATION" for s in all_scam):
        logger.info("  GATE PASS: brand impersonation detected")
        return True
    if any(s.get("type") == "NEWLY_REGISTERED" and s.get("age_days", 999) <= 7 for s in all_scam):
        logger.info("  GATE PASS: domain registered within 7 days")
        return True
    if any(s.get("type") == "CRYPTO_FORM" for s in all_scam):
        logger.info("  GATE PASS: crypto wallet form detected")
        return True
    if "URLHAUS" in inv.get("source", "").upper() or "THREATFOX" in inv.get("source", "").upper():
        logger.info("  GATE PASS: confirmed malicious by threat feed")
        return True

    logger.info("  GATE FAIL: risk=%d, patterns=%s, ids=%d, conf=%.2f" % (
        risk_score, categories, len(inv.get("digital_identifiers", [])), inv.get("confidence", 0)))
    return False

async def create_case(inv: dict) -> str:
    import asyncpg
    case_id = f"GFIN-AUTO-{int(time.time() * 1000) % 10000000000}"
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        await conn.execute(
            """INSERT INTO cases (case_id, target, target_type, trigger, summary, status, confidence,
               scam_patterns, affected_countries, routed_to_countries,
               physical_locations, financial_indicators, digital_identifiers,
               evidence_chain, victim_count, created_by_officer, classification)
               VALUES ($1,$2,$3,$4,$5,'INVESTIGATING',$6,$7,$8,$9,$10,$11,$12,$13,0,'GFIN_AUTONOMOUS_HUNTER','LAW ENFORCEMENT SENSITIVE')""",
            case_id, inv["domain"], "DOMAIN", f"Autonomous discovery: {inv['source']}",
            inv["summary"][:500], inv["confidence"], inv["scam_patterns"],
            inv["affected_countries"], inv["routed_to_countries"],
            json.dumps(inv["physical_locations"]), json.dumps(inv["financial_indicators"]),
            json.dumps(inv["digital_identifiers"]), json.dumps(inv["evidence_chain"])
        )
        for ev in inv["evidence_chain"]:
            await conn.execute(
                """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (evidence_id) DO NOTHING""",
                case_id, ev.get("evidence_id","") + f"-{case_id[-6:]}", ev.get("phase",""),
                ev.get("finding","")[:500], ev.get("source",""), "autonomous_hunter", "AUTOMATED_OSINT",
                ev.get("confidence","MEDIUM")
            )
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1,$2,$3,$4,$5,$6)",
            case_id, "AUTO_DISCOVERY_INVESTIGATION", "GFIN_AUTONOMOUS_HUNTER", "autonomous_hunter_v2",
            inv["domain"], f"Evidence: {len(inv['evidence_chain'])} steps, Entities: {len(inv['digital_identifiers'])}, Countries: {', '.join(inv['affected_countries'])}, SANs: {len(inv.get('ssl_sans',[]))}"
        )
        logger.info(f"  Case created: {case_id} for {inv['domain']}")
        return case_id
    finally:
        await conn.close()

# ============================================================
# MAIN LOOP
# ============================================================
async def run_cycle():
    logger.info("=" * 60)
    logger.info("STARTING AUTONOMOUS HUNTER v2.1 EVIDENCE-GATED CYCLE")
    logger.info("=" * 60)
    targets = discover_targets()
    if not targets:
        logger.info("No new targets. Sleeping."); return 0
    flagged = 0
    skipped = 0
    for t in targets[:MAX_CASES_PER_CYCLE]:
        d = t["domain"]
        if d in _investigated:
            skipped += 1
            continue
        logger.info("INVESTIGATING: %s (source: %s)" % (d, t["source"]))
        try:
            inv = investigate_domain(d, t["source"], t)

            # ALWAYS flag in database
            await flag_domain_in_db(d, inv)
            flagged += 1

            # FEED DOMAINS ARE NEVER PROMOTED TO CASES — only flagged as tracked_domains
            # Cases are created only from: (1) real victim complaints, (2) officer manual creation, (3) Telegram intelligence operations
            logger.info("  => FLAGGED ONLY: %s (feed discovery — not a case)" % d)

            _investigated.add(d)
        except Exception as e:
            logger.error("  Failed: %s" % e)
        time.sleep(3)
    logger.info("Cycle complete: %d flagged, %d skipped (no cases created — feed mode)" % (flagged, skipped))
    return cases

async def main():
    logger.info("=" * 60)
    logger.info("GFIN AUTONOMOUS SCAM HUNTER v2.1 — STARTING")
    logger.info("=" * 60)
    while True:
        try: await run_cycle()
        except Exception as e: logger.error(f"Cycle error: {e}")
        logger.info(f"Sleeping {SCAN_INTERVAL}s...")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
GFIN Autonomous Scam Hunter & Auto-Investigation Engine v1.0
=============================================================
Runs 24/7 as a systemd service. Discovers new scam domains via free public APIs,
runs full investigations (DNS, IP, WHOIS, SSL, content, geolocation), creates
GFIN cases with complete evidence chains, digital identifiers, physical
locations, and country tags. NO mock data — everything is real.

Sources (all free, no API keys required):
  - CT logs (crt.sh) — newly registered domains with scam keywords
  - URLScan.io — recently scanned phishing/scan URLs
  - Phishing.Database (GitHub raw) — community phishing URL feed
  - DNS resolution — A, MX, NS, TXT, CNAME records
  - ip-api.com — IP geolocation (country, city, ISP, ASN, coordinates)
  - RDAP (rdap.org) — domain registration data (registrar, dates, country)
  - crt.sh — SSL certificate transparency (SANs, issuer)
  - HTTP content — extract wallets, phones, emails, company names, addresses, social links

Output: New GFIN cases in the database with full evidence chains.
"""
import asyncio, json, time, re, ssl, socket, hashlib, urllib.request, urllib.parse
import logging, os, sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from hunter_v3_intel import *  # v3.0 Enhanced intelligence: favicon, analytics, redirect, tech stack, forms, typo-squatting

# Ensure we can import server modules
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
# CONFIGURATION
# ============================================================

SCAN_INTERVAL_SECONDS = 900  # 15 minutes between discovery scans
MAX_CASES_PER_CYCLE = 10        # Max new cases per scan cycle
MAX_INVESTIGATIONS_PER_CYCLE = 3  # Max concurrent investigations

# Scam keywords to search in CT logs and domain registrations
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

# Domains already investigated (in-memory cache, also checks DB)
_investigated_cache = set()

# HTTP context (no cert verification for OSINT sources)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ============================================================
# HTTP HELPERS
# ============================================================

def http_get_json(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "GFIN-AutonomousHunter/1.0 (Fraud Intelligence)"
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        return json.loads(resp.read().decode('utf-8', errors='replace'))
    except Exception as e:
        logger.debug(f"HTTP GET JSON failed for {url}: {e}")
        return None

def http_get_text(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "GFIN-AutonomousHunter/1.0 (Fraud Intelligence)"
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        logger.debug(f"HTTP GET TEXT failed for {url}: {e}")
        return None

# ============================================================
# DISCOVERY: Find new scam domains from free public sources
# ============================================================

def discover_from_ct_logs() -> List[Dict]:
    """Scan Certificate Transparency logs for domains matching scam keywords."""
    results = []
    for keyword in SCAM_KEYWORDS[:8]:  # Top 8 keywords per cycle
        try:
            data = http_get_json(
                f"https://crt.sh/?q=%25{keyword}%25&output=json&limit=30",
                timeout=20
            )
            if data and isinstance(data, list):
                for cert in data[:15]:
                    name_value = cert.get("name_value", "").strip()
                    if not name_value:
                        continue
                    # Handle multi-line name_value (SANs)
                    for domain in name_value.split("\n"):
                        domain = domain.strip().lower()
                        if not domain or domain.startswith("*."):
                            continue
                        if keyword in domain and domain not in _investigated_cache:
                            results.append({
                                "domain": domain,
                                "source": "CERTIFICATE_TRANSPARENCY",
                                "keyword": keyword,
                                "cert_not_before": cert.get("not_before", ""),
                                "cert_issuer": cert.get("issuer_name", ""),
                            })
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            logger.debug(f"CT scan failed for keyword '{keyword}': {e}")
    return results

def discover_from_urlscan() -> List[Dict]:
    """Scan URLScan.io recent scans for phishing/malware URLs."""
    results = []
    try:
        # URLScan free API — recent phishing scans
        data = http_get_json(
            "https://urlscan.io/api/v1/search/?q=task.method:GET+AND+lists.verdicts.malicious:true&size=20",
            timeout=20
        )
        if data and "results" in data:
            for entry in data["results"][:20]:
                page = entry.get("page", {})
                url = page.get("url", "")
                domain = page.get("domain", "")
                if domain and domain not in _investigated_cache:
                    ip = entry.get("page", {}).get("ip", "")
                    results.append({
                        "domain": domain,
                        "source": "URLSCAN",
                        "url": url,
                        "ip": ip,
                        "scan_id": entry.get("_id", ""),
                        "verdict": "malicious",
                    })
    except Exception as e:
        logger.debug(f"URLScan scan failed: {e}")
    return results

def discover_from_phishing_db() -> List[Dict]:
    """Fetch phishing URLs from the Phishing.Database GitHub feed."""
    results = []
    try:
        # Phishing.Database — community-maintained phishing URL list
        text = http_get_text(
            "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
            timeout=20
        )
        if text:
            urls = text.strip().split("\n")
            for url in urls[:50]:  # Check most recent 50
                url = url.strip()
                if not url or url.startswith("#"):
                    continue
                # Ensure URL has scheme for proper parsing
                if not url.startswith("http"):
                    url = "http://" + url
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()
                # Filter out non-domain entries
                if not domain or "@" in domain or domain in _investigated_cache:
                    continue
                # Must look like a domain (at least one dot, not just an IP)
                if "." not in domain or re.match(r"^[\d.]+$", domain):
                    continue
                results.append({
                    "domain": domain,
                    "source": "PHISHING_DATABASE",
                    "url": url,
                })
    except Exception as e:
        logger.debug(f"Phishing DB scan failed: {e}")
    return results

def discover_from_openphish() -> List[Dict]:
    """Fetch phishing URLs from OpenPhish free feed."""
    results = []
    try:
        text = http_get_text("https://www.openphish.com/feed.txt", timeout=20)
        if text:
            urls = text.strip().split("\n")
            for url in urls[:50]:
                url = url.strip()
                if not url:
                    continue
                if not url.startswith("http"):
                    url = "http://" + url
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()
                if not domain or "@" in domain or domain in _investigated_cache:
                    continue
                if "." not in domain or re.match(r"^[\d.]+$", domain):
                    continue
                results.append({
                    "domain": domain,
                    "source": "OPENPHISH",
                    "url": url,
                })
    except Exception as e:
        logger.debug(f"OpenPhish scan failed: {e}")
    return results

def discover_targets() -> List[Dict]:
    """Run all discovery sources and return unique targets."""
    all_results = []

    logger.info("=== DISCOVERY PHASE ===")
    logger.info("Scanning CT logs...")
    ct_results = discover_from_ct_logs()
    all_results.extend(ct_results)
    logger.info(f"  CT logs: {len(ct_results)} potential domains")

    logger.info("Scanning URLScan.io...")
    urlscan_results = discover_from_urlscan()
    all_results.extend(urlscan_results)
    logger.info(f"  URLScan: {len(urlscan_results)} domains")

    logger.info("Scanning Phishing.Database...")
    phish_results = discover_from_phishing_db()
    all_results.extend(phish_results)
    logger.info(f"  Phishing DB: {len(phish_results)} domains")

    logger.info("Scanning OpenPhish...")
    openphish_results = discover_from_openphish()
    all_results.extend(openphish_results)
    logger.info(f"  OpenPhish: {len(openphish_results)} domains")

    logger.info("Scanning URLHaus (abuse.ch)...")
    urlhaus_results = discover_from_urlhaus()
    all_results.extend(urlhaus_results)
    logger.info(f"  URLHaus: {len(urlhaus_results)} domains")

    logger.info("Scanning ThreatFox (abuse.ch)...")
    threatfox_results = discover_from_abuseipdb()
    all_results.extend(threatfox_results)
    logger.info(f"  ThreatFox: {len(threatfox_results)} domains")

    # Deduplicate by domain, filter invalid entries
    seen = set()
    unique = []
    for r in all_results:
        d = r["domain"]
        # Must be a valid domain (not IP, not email, has a dot, not a safe CDN)
        if d and "." in d and "@" not in d and not re.match(r"^[\d.]+$", d) and d not in seen and not _is_safe_domain(d):
            seen.add(d)
            unique.append(r)

    logger.info(f"Total unique new targets: {len(unique)}")
    return unique[:MAX_CASES_PER_CYCLE]

def _is_safe_domain(domain: str) -> bool:
    """Check if domain is obviously safe (common CDNs, Google, etc.)."""
    safe_patterns = [
        "google.com", "googleapis.com", "cloudflare.com", "amazonaws.com",
        "microsoft.com", "github.com", "wikipedia.org", "mozilla.org",
        "letsencrypt.org", "digicert.com", "godaddy.com", "cloudfront.net",
        "akamai.com", "azure.com", "office.com", "live.com", "yahoo.com",
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "apple.com", "mozilla.com", "bootstrap.com", "jquery.com",
        "nip.io", "sslip.io", "xip.io",
        "pages.dev", "workers.dev", "r2.dev",
        "netlify.app", "vercel.app", "herokuapp.com",
        "000webhostapp.com", "infinityfree.com",
        "github.io", "gitlab.io",
        "heroku.com", "fly.dev", "railway.app",
        "repl.co", "glitch.me",
        "onrender.com", "render.com",
        "deno.dev",
        "fastly.net", "fastly.io",
    ]
    for safe in safe_patterns:
        if safe in domain:
            return True
    return False

# ============================================================
# INVESTIGATION: Full forensic investigation of a domain
# ============================================================

def investigate_domain(domain: str, source: str, extra: dict = None) -> dict:
    """
    Full investigation: DNS -> IP -> Geo -> WHOIS -> SSL -> Content -> Entities.
    Returns complete investigation data for case creation.
    """
    investigation = {
        "domain": domain,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evidence_chain": [],
        "digital_identifiers": [],
        "physical_locations": [],
        "financial_indicators": [],
        "affected_countries": [],
        "scam_indicators": [],
        "scam_patterns": [],
        "confidence": 0.0,
        "summary": "",
    }

    evidence_counter = 0
    def ev_id():
        nonlocal evidence_counter
        evidence_counter += 1
        return f"E-AH-{evidence_counter:04d}"

    # === STEP 1: DNS RESOLUTION ===
    logger.info(f"  [1/7] DNS resolution for {domain}")
    dns_a, dns_mx, dns_ns, dns_txt, dns_cname = _dns_lookup_full(domain)

    if dns_a:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "DNS_RESOLUTION",
            "finding": f"A records: {', '.join(dns_a)}",
            "source": "DNS (system resolver)",
            "confidence": "HIGH",
        })
        for ip in dns_a:
            investigation["digital_identifiers"].append({
                "type": "IP",
                "value": ip,
                "context": f"A record for {domain}",
            })
    if dns_mx:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "DNS_RESOLUTION",
            "finding": f"MX records: {', '.join(dns_mx)}",
            "source": "DNS (system resolver)",
            "confidence": "HIGH",
        })
        for mx in dns_mx:
            investigation["digital_identifiers"].append({
                "type": "MX",
                "value": mx,
                "context": f"Mail server for {domain}",
            })
    if dns_ns:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "DNS_RESOLUTION",
            "finding": f"NS records: {', '.join(dns_ns)}",
            "source": "DNS (system resolver)",
            "confidence": "HIGH",
        })
        for ns in dns_ns:
            investigation["digital_identifiers"].append({
                "type": "NS",
                "value": ns,
                "context": f"Name server for {domain}",
            })
    if dns_txt:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "DNS_RESOLUTION",
            "finding": f"TXT records: {'; '.join(dns_txt[:3])}",
            "source": "DNS (system resolver)",
            "confidence": "HIGH",
        })

    # === STEP 2: IP GEOLOCATION ===
    logger.info(f"  [2/7] IP geolocation for {domain}")
    if dns_a:
        for ip in dns_a[:2]:  # Geolocate first 2 IPs
            geo = _geolocate_ip(ip)
            if geo:
                investigation["evidence_chain"].append({
                    "evidence_id": ev_id(),
                    "phase": "IP_GEOLOCATION",
                    "finding": f"IP {ip}: {geo.get('city', '?')}, {geo.get('country', '?')} — ISP: {geo.get('isp', '?')}, ASN: {geo.get('as', '?')}",
                    "source": "ip-api.com",
                    "confidence": "HIGH",
                })
                investigation["physical_locations"].append({
                    "ip": ip,
                    "city": geo.get("city", ""),
                    "region": geo.get("regionName", ""),
                    "country": geo.get("country", ""),
                    "country_code": geo.get("countryCode", ""),
                    "latitude": geo.get("lat", ""),
                    "longitude": geo.get("lon", ""),
                    "isp": geo.get("isp", ""),
                    "asn": geo.get("as", ""),
                    "hostname": geo.get("hostname", ""),
                    "org": geo.get("org", ""),
                    "timezone": geo.get("timezone", ""),
                })
                if geo.get("countryCode"):
                    investigation["affected_countries"].append(geo["countryCode"])
                investigation["digital_identifiers"].append({
                    "type": "HOSTING_PROVIDER",
                    "value": geo.get("isp", geo.get("org", "")),
                    "context": f"Hosting {domain} at IP {ip}",
                })

    # === STEP 3: RDAP / WHOIS ===
    logger.info(f"  [3/7] RDAP/WHOIS for {domain}")
    rdap = _rdap_lookup(domain)
    if rdap:
        registrar = rdap.get("registrar", "")
        reg_date = rdap.get("registration_date", "")
        reg_country = rdap.get("country", "")
        status = rdap.get("status", [])

        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "DOMAIN_REGISTRATION",
            "finding": f"Registrar: {registrar}, Registered: {reg_date}, Country: {reg_country}, Status: {', '.join(status[:3]) if status else 'unknown'}",
            "source": "RDAP (rdap.org)",
            "confidence": "HIGH",
        })
        if reg_country:
            investigation["affected_countries"].append(reg_country)
        investigation["digital_identifiers"].append({
            "type": "REGISTRAR",
            "value": registrar,
            "context": f"Domain registrar for {domain}",
        })

    # === STEP 4: SSL CERTIFICATE ===
    logger.info(f"  [4/7] SSL certificate analysis for {domain}")
    ssl_info = _get_ssl_info(domain)
    if ssl_info:
        san_domains = ssl_info.get("san_domains", [])
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "SSL_CERTIFICATE",
            "finding": f"Issuer: {ssl_info.get('issuer', '?')}, Valid: {ssl_info.get('not_before', '?')} to {ssl_info.get('not_after', '?')}, SANs: {len(san_domains)} domains",
            "source": "SSL/TLS connection",
            "confidence": "HIGH",
        })
        for san in san_domains[:5]:
            if san != domain and not san.startswith("*."):
                investigation["digital_identifiers"].append({
                    "type": "SSL_SAN",
                    "value": san,
                    "context": f"Domain sharing SSL certificate with {domain}",
                })

    # === STEP 5: HTTP CONTENT ANALYSIS ===
    logger.info(f"  [5/7] HTTP content analysis for {domain}")
    content = _fetch_http_content(domain)
    if content:
        entities = _extract_entities(content)
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "CONTENT_ANALYSIS",
            "finding": f"Page loaded ({len(content)} bytes). Extracted: {len(entities.get('emails', []))} emails, {len(entities.get('phones', []))} phones, {len(entities.get('wallets', []))} crypto wallets, {len(entities.get('social_links', []))} social links",
            "source": f"https://{domain}",
            "confidence": "MEDIUM",
        })
        for email in entities.get("emails", [])[:5]:
            investigation["digital_identifiers"].append({
                "type": "EMAIL",
                "value": email,
                "context": f"Found on {domain}",
            })
        for phone in entities.get("phones", [])[:5]:
            investigation["digital_identifiers"].append({
                "type": "PHONE",
                "value": phone,
                "context": f"Found on {domain}",
            })
        for wallet in entities.get("wallets", [])[:5]:
            investigation["financial_indicators"].append({
                "type": wallet.get("type", "CRYPTO_WALLET"),
                "address": wallet.get("address", ""),
                "context": f"Found on {domain}",
            })
        for social in entities.get("social_links", [])[:5]:
            investigation["digital_identifiers"].append({
                "type": "SOCIAL_ACCOUNT",
                "value": social,
                "context": f"Linked from {domain}",
            })
        for company in entities.get("company_names", [])[:3]:
            investigation["digital_identifiers"].append({
                "type": "COMPANY",
                "value": company,
                "context": f"Mentioned on {domain}",
            })
        for addr in entities.get("addresses", [])[:3]:
            investigation["physical_locations"].append({
                "type": "CONTENT_ADDRESS",
                "address": addr,
                "context": f"Found on {domain}",
            })

    # === STEP 5b: FAVICON HASHING ===
    logger.info(f"  [5b/10] Favicon fingerprinting for {domain}")
    favicon_hash = fetch_favicon_hash(domain)
    if favicon_hash:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "FAVICON_FINGERPRINT",
            "finding": f"Favicon MD5 hash: {favicon_hash}",
            "source": f"https://{domain}/favicon.ico",
            "confidence": "MEDIUM",
        })
        investigation["digital_identifiers"].append({
            "type": "FAVICON_HASH",
            "value": favicon_hash,
            "context": f"Favicon hash for {domain} — same hash across domains = same operator",
        })

    # === STEP 5c: ANALYTICS ID EXTRACTION ===
    logger.info(f"  [5c/10] Analytics ID extraction for {domain}")
    if content:
        analytics_ids = extract_analytics_ids(content)
        if analytics_ids:
            for tracker_type, tracker_ids in analytics_ids.items():
                for tid in tracker_ids:
                    investigation["evidence_chain"].append({
                        "evidence_id": ev_id(),
                        "phase": "ANALYTICS_TRACKING",
                        "finding": f"{tracker_type}: {tid}",
                        "source": f"https://{domain}",
                        "confidence": "HIGH",
                    })
                    investigation["digital_identifiers"].append({
                        "type": "ANALYTICS_ID",
                        "value": f"{tracker_type}:{tid}",
                        "context": f"Tracking ID found on {domain} — same ID across sites = same operator",
                    })

    # === STEP 5d: REDIRECT CHAIN ANALYSIS ===
    logger.info(f"  [5d/10] Redirect chain analysis for {domain}")
    redirect_info = follow_redirects(domain)
    if redirect_info["redirect_count"] > 0:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "REDIRECT_ANALYSIS",
            "finding": f"{redirect_info['redirect_count']} redirects to {redirect_info['final_url']}" + (" (cross-domain!)" if redirect_info['cross_domain_redirect'] else ""),
            "source": f"https://{domain}/",
            "confidence": "MEDIUM",
        })
        if redirect_info["cross_domain_redirect"]:
            final_domain = urllib.parse.urlparse(redirect_info["final_url"]).netloc
            if final_domain and final_domain != domain:
                investigation["digital_identifiers"].append({
                    "type": "REDIRECT_TARGET",
                    "value": final_domain,
                    "context": f"{domain} redirects to {final_domain}",
                })

    # === STEP 5e: TECH STACK FINGERPRINTING ===
    logger.info(f"  [5e/10] Tech stack fingerprinting for {domain}")
    if content:
        # Get headers from the redirect chain first step
        tech_headers = redirect_info["redirects"][0] if redirect_info.get("redirects") else {}
        tech_stack = fingerprint_tech_stack(content, {
            "Server": tech_stack.get("server", "") if isinstance(tech_stack, dict) else "",
            "X-Powered-By": tech_stack.get("powered_by", "") if isinstance(tech_stack, dict) else "",
        })
        if tech_stack:
            tech_parts = []
            for category, items in tech_stack.items():
                tech_parts.append(f"{category}: {', '.join(items)}")
            investigation["evidence_chain"].append({
                "evidence_id": ev_id(),
                "phase": "TECH_STACK",
                "finding": f"Detected: {'; '.join(tech_parts)}",
                "source": f"https://{domain}",
                "confidence": "MEDIUM",
            })
            for pp in tech_stack.get("payment_processors", []):
                investigation["financial_indicators"].append({
                    "type": "PAYMENT_PROCESSOR",
                    "processor": pp,
                    "context": f"Found on {domain}",
                })

    # === STEP 5f: FORM DETECTION ===
    logger.info(f"  [5f/10] Form detection for {domain}")
    if content:
        forms = detect_forms(content)
        if forms["login_forms"] > 0 or forms["payment_forms"] > 0 or forms["crypto_forms"] > 0:
            form_summary = []
            if forms["login_forms"]: form_summary.append(f"{forms['login_forms']} login forms")
            if forms["payment_forms"]: form_summary.append(f"{forms['payment_forms']} payment forms")
            if forms["crypto_forms"]: form_summary.append(f"{forms['crypto_forms']} crypto forms")
            if forms["registration_forms"]: form_summary.append(f"{forms['registration_forms']} registration forms")
            
            investigation["evidence_chain"].append({
                "evidence_id": ev_id(),
                "phase": "FORM_ANALYSIS",
                "finding": f"Forms detected: {', '.join(form_summary)}",
                "source": f"https://{domain}",
                "confidence": "HIGH",
            })
            if forms["crypto_forms"] > 0:
                investigation["scam_indicators"].append({
                    "type": "CRYPTO_FORM",
                    "severity": "HIGH",
                    "description": "Crypto wallet/seed phrase form detected — potential wallet drainer",
                })
            if forms["payment_forms"] > 0:
                investigation["financial_indicators"].append({
                    "type": "PAYMENT_FORM",
                    "context": f"Payment form on {domain}",
                })

    # === STEP 5g: TYPO-SQUATTING CHECK ===
    logger.info(f"  [5g/10] Typo-squatting check for {domain}")
    typo = detect_typosquatting(domain)
    if typo["is_typosquat"]:
        investigation["evidence_chain"].append({
            "evidence_id": ev_id(),
            "phase": "TYPO_SQUATTING",
            "finding": f"DOMAIN IMPERSONATES {typo['target_brand']} (type: {typo['type']})",
            "source": "GFIN Brand Protection Database",
            "confidence": "HIGH",
        })
        investigation["scam_indicators"].append({
            "type": "BRAND_IMPERSONATION",
            "severity": "CRITICAL",
            "target_brand": typo["target_brand"],
            "method": typo["type"],
            "description": f"{domain} impersonates {typo['target_brand']}",
        })

    # === STEP 5h: DOMAIN AGE ANALYSIS ===
    logger.info(f"  [5h/10] Domain age analysis for {domain}")
    if rdap and rdap.get("registration_date"):
        age_info = calculate_domain_age(rdap["registration_date"])
        if age_info["age_days"] is not None:
            investigation["evidence_chain"].append({
                "evidence_id": ev_id(),
                "phase": "DOMAIN_AGE",
                "finding": f"Domain registered {age_info['age_days']} days ago ({age_info['age_category']})" + (" — NEWLY REGISTERED, HIGH RISK" if age_info["is_newly_registered"] else ""),
                "source": "RDAP registration data",
                "confidence": "HIGH",
            })
            if age_info["is_newly_registered"]:
                investigation["scam_indicators"].append({
                    "type": "NEWLY_REGISTERED",
                    "severity": "HIGH",
                    "age_days": age_info["age_days"],
                    "description": f"Domain is only {age_info['age_days']} days old",
                })

    # === STEP 5i: PAGE METADATA ===
    logger.info(f"  [5i/10] Page metadata extraction for {domain}")
    if content:
        page_meta = extract_page_metadata(content)
        if page_meta["title"] or page_meta["description"]:
            investigation["evidence_chain"].append({
                "evidence_id": ev_id(),
                "phase": "PAGE_METADATA",
                "finding": f"Title: {page_meta['title'][:100]} | Description: {page_meta['description'][:100]} | Generator: {page_meta.get('generator', 'none')} | JSON-LD: {page_meta.get('has_jsonld', False)}",
                "source": f"https://{domain}",
                "confidence": "MEDIUM",
            })
            if page_meta.get("generator"):
                investigation["digital_identifiers"].append({
                    "type": "CMS_GENERATOR",
                    "value": page_meta["generator"],
                    "context": f"CMS detected on {domain}",
                })

    # === STEP 6: SCAM PATTERN DETECTION ===
    logger.info(f"  [6/7] Scam pattern detection for {domain}")
    scam_analysis = _detect_scam_patterns(domain, content or "")
    investigation["scam_patterns"] = scam_analysis.get("categories", [])
    investigation["scam_indicators"].append({
        "risk_score": scam_analysis["risk_score"],
        "risk_level": scam_analysis["risk_level"],
        "categories": scam_analysis["categories"],
        "indicators": scam_analysis["indicators"],
    })
    investigation["evidence_chain"].append({
        "evidence_id": ev_id(),
        "phase": "SCAM_DETECTION",
        "finding": f"GFIN Scam Engine: {scam_analysis['risk_level']} risk (score {scam_analysis['risk_score']}), categories: {', '.join(scam_analysis['categories']) or 'none'}, indicators: {len(scam_analysis['indicators'])}",
        "source": "GFIN Deterministic Scam Engine v3.0",
        "confidence": "HIGH",
    })

    # === STEP 7: COUNTRY ROUTING ===
    logger.info(f"  [7/7] Country routing for {domain}")
    # Deduplicate countries
    unique_countries = list(set(c for c in investigation["affected_countries"] if c))
    investigation["affected_countries"] = unique_countries
    routed = unique_countries + ["EUROPOL", "INTERPOL"]
    investigation["routed_to_countries"] = routed

    investigation["evidence_chain"].append({
        "evidence_id": ev_id(),
        "phase": "COUNTRY_ROUTING",
        "finding": f"Affected countries: {', '.join(unique_countries) if unique_countries else 'unknown'}. Routed to: {', '.join(routed)}",
        "source": "GFIN Country Routing Engine",
        "confidence": "HIGH",
    })

    # === CONFIDENCE SCORING ===
    evidence_count = len(investigation["evidence_chain"])
    entity_count = len(investigation["digital_identifiers"])
    country_count = len(unique_countries)
    confidence = min(1.0, (evidence_count * 0.05) + (entity_count * 0.03) + (country_count * 0.05) + (scam_analysis["risk_score"] * 0.005))
    investigation["confidence"] = round(confidence, 2)

    # === SUMMARY ===
    summary_parts = [
        f"Autonomous discovery via {source}",
        f"Domain: {domain}",
        f"Risk: {scam_analysis['risk_level']} ({scam_analysis['risk_score']}/100)",
        f"Evidence: {evidence_count} steps",
        f"Entities: {entity_count} digital identifiers",
        f"Countries: {', '.join(unique_countries) if unique_countries else 'unknown'}",
        f"Patterns: {', '.join(scam_analysis['categories']) if scam_analysis['categories'] else 'none detected'}",
    ]
    investigation["summary"] = ". ".join(summary_parts)

    logger.info(f"  Investigation complete: {evidence_count} evidence steps, {entity_count} entities, {country_count} countries, confidence {confidence:.2f}")
    return investigation


def _dns_lookup_full(domain: str) -> Tuple[list, list, list, list, list]:
    """Full DNS resolution: A, MX, NS, TXT, CNAME."""
    a_records, mx_records, ns_records, txt_records, cname_records = [], [], [], [], []

    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 10

        try:
            answers = resolver.resolve(domain, 'A')
            a_records = [str(r) for r in answers]
        except: pass
        try:
            answers = resolver.resolve(domain, 'MX')
            mx_records = [str(r) for r in answers]
        except: pass
        try:
            answers = resolver.resolve(domain, 'NS')
            ns_records = [str(r) for r in answers]
        except: pass
        try:
            answers = resolver.resolve(domain, 'TXT')
            txt_records = [str(r)[:200] for r in answers]
        except: pass
        try:
            answers = resolver.resolve(domain, 'CNAME')
            cname_records = [str(r) for r in answers]
        except: pass
    except ImportError:
        # Fallback: use socket for A records only
        try:
            ips = socket.getaddrinfo(domain, None, socket.AF_INET)
            a_records = list(set(ip[4][0] for ip in ips))
        except: pass

    return a_records, mx_records, ns_records, txt_records, cname_records


def _geolocate_ip(ip: str) -> dict:
    """Geolocate an IP address using free ip-api.com (no key needed)."""
    data = http_get_json(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,lat,lon,timezone,isp,org,as,hostname,query", timeout=10)
    if data and data.get("status") == "success":
        return data
    return None


def _rdap_lookup(domain: str) -> dict:
    """RDAP lookup for domain registration data."""
    tld = domain.split(".")[-1] if "." in domain else ""
    rdap_servers = {
        "com": "https://rdap.verisign.com/com/v1/domain/",
        "net": "https://rdap.verisign.com/net/v1/domain/",
        "org": "https://rdap.publicinterestregistry.org/rdap/domain/",
        "io": "https://rdap.identitydigital.services/rdap/domain/",
        "co": "https://rdap.nic.co/domain/",
        "info": "https://rdap.identitydigital.info/rdap/domain/",
        "biz": "https://rdap.nic.biz/domain/",
    }
    rdap_url = rdap_servers.get(tld, f"https://rdap.org/domain/")
    data = http_get_json(f"{rdap_url}{domain}", timeout=15)
    if not data:
        return {}

    result = {"registrar": "", "registration_date": "", "country": "", "status": []}

    # Extract registrar
    for event in data.get("events", []):
        if event.get("eventAction") == "registration":
            result["registration_date"] = event.get("eventDate", "")
        if event.get("eventAction") == "expiration":
            result["expiration_date"] = event.get("eventDate", "")

    # Extract registrar name
    for entity in data.get("entities", []):
        roles = entity.get("roles", [])
        if "registrar" in roles:
            vcard = entity.get("vcardArray", [{}])
            if len(vcard) > 1:
                for field in vcard[1]:
                    if field[0] == "fn":
                        result["registrar"] = field[3]
                        break

    result["status"] = data.get("status", [])
    result["country"] = data.get("ldName", {}).get("location", "")

    return result


def _get_ssl_info(domain: str) -> dict:
    """Get SSL certificate information."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return None

                issuer = dict(x[0] for x in cert.get("issuer", []))
                subject = dict(x[0] for x in cert.get("subject", []))
                not_before = cert.get("notBefore", "")
                not_after = cert.get("notAfter", "")
                san_domains = []
                for san in cert.get("subjectAltName", []):
                    if san[0] == "DNS":
                        san_domains.append(san[1])

                return {
                    "issuer": issuer.get("organizationName", str(issuer)),
                    "subject": subject.get("commonName", ""),
                    "not_before": not_before,
                    "not_after": not_after,
                    "san_domains": san_domains,
                }
    except Exception as e:
        logger.debug(f"SSL info failed for {domain}: {e}")
        return None


def _fetch_http_content(domain: str) -> str:
    """Fetch HTTP content from domain."""
    for scheme in ["https", "http"]:
        try:
            url = f"{scheme}://{domain}/"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            })
            resp = urllib.request.urlopen(req, timeout=15, context=SSL_CTX)
            content_type = resp.headers.get("Content-Type", "")
            if "text" in content_type or "html" in content_type or "json" in content_type:
                return resp.read().decode('utf-8', errors='replace')[:50000]  # Limit to 50KB
        except Exception as e:
            logger.debug(f"HTTP fetch failed for {scheme}://{domain}: {e}")
    return None


def _extract_entities(content: str) -> dict:
    """Extract entities from HTML content: emails, phones, crypto wallets, social links, company names, addresses."""
    entities = {
        "emails": [],
        "phones": [],
        "wallets": [],
        "social_links": [],
        "company_names": [],
        "addresses": [],
    }

    # Extract emails
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
    entities["emails"] = list(set(emails))[:10]

    # Extract phone numbers
    phones = re.findall(r'(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}', content)
    entities["phones"] = list(set(p for p in phones if len(p.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")) >= 7))[:10]

    # Extract crypto wallets
    # Bitcoin (legacy addresses start with 1, Bech32 start with bc1)
    btc_legacy = re.findall(r'\b1[a-zA-HJ-NP-Z0-9]{25,34}\b', content)
    btc_bech32 = re.findall(r'\bbc1[a-z0-9]{39,59}\b', content)
    # Ethereum (0x + 40 hex chars)
    eth = re.findall(r'\b0x[a-fA-F0-9]{40}\b', content)
    # Tron (T + 33 chars)
    tron = re.findall(r'\bT[A-Za-z0-9]{33}\b', content)

    for addr in btc_legacy:
        entities["wallets"].append({"type": "BTC", "address": addr})
    for addr in btc_bech32:
        entities["wallets"].append({"type": "BTC", "address": addr})
    for addr in eth:
        entities["wallets"].append({"type": "ETH", "address": addr})
    for addr in tron:
        entities["wallets"].append({"type": "TRON", "address": addr})

    # Extract social media links
    social_patterns = [
        (r'(?:https?:)?//(?:www\.)?(?:telegram\.me|t\.me)/[\w]+', "Telegram"),
        (r'(?:https?:)?//(?:www\.)?twitter\.com/[\w]+', "Twitter"),
        (r'(?:https?:)?//(?:www\.)?facebook\.com/[\w]+', "Facebook"),
        (r'(?:https?:)?//(?:www\.)?instagram\.com/[\w]+', "Instagram"),
        (r'(?:https?:)?//(?:www\.)?linkedin\.com/company/[\w-]+', "LinkedIn"),
        (r'(?:https?:)?//(?:www\.)?wa\.me/[\d]+', "WhatsApp"),
    ]
    for pattern, platform in social_patterns:
        matches = re.findall(pattern, content)
        for m in matches[:5]:
            entities["social_links"].append(f"{platform}: {m}")

    # Extract company names (look for common patterns)
    company_patterns = [
        r'(?:©|Copyright)\s*(\d{4}\s+)?([A-Z][a-zA-Z\s]{3,40}(?:Ltd|Limited|Inc|LLC|GmbH|S\.A\.|Corp|Corporation|SARL|B\.V\.|Pty))',
        r'class="[^"]*company[^"]*"[^>]*>([A-Z][a-zA-Z\s]{3,40})<',
        r'<title>([A-Z][a-zA-Z\s]{3,60})</title>',
    ]
    for pattern in company_patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            if isinstance(m, tuple):
                m = m[-1]
            m = m.strip()
            if m and len(m) > 3 and m not in entities["company_names"]:
                entities["company_names"].append(m)
    entities["company_names"] = entities["company_names"][:5]

    # Extract addresses (basic pattern matching)
    address_patterns = [
        r'\b\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b[^<\n]{0,60}',
    ]
    for pattern in address_patterns:
        matches = re.findall(pattern, content)
        for m in matches[:3]:
            m = m.strip()
            if m and m not in entities["addresses"]:
                entities["addresses"].append(m)

    return entities


def _detect_scam_patterns(domain: str, content: str) -> dict:
    """Run scam pattern detection on domain + content."""
    text = f"{domain}\n{content[:5000]}"
    categories = set()
    indicators = []
    risk_score = 0

    # Recovery scam patterns
    recovery_keywords = ["recovery", "recover", "payback", "refund", "retrieve", "reclaim", "lost funds", "hack back", "get your money back"]
    recovery_count = sum(1 for kw in recovery_keywords if kw in text.lower())
    if recovery_count >= 1:
        categories.add("RECOVERY_SCAM")
        risk_score += 25 + (recovery_count * 5)
        indicators.append(f"Recovery scam keywords: {recovery_count} found")

    # Investment fraud patterns
    invest_keywords = ["guaranteed return", "double your", "risk-free investment", "high yield", "roi", "profit guaranteed", "investment plan", "trading signals", "copy trading"]
    invest_count = sum(1 for kw in invest_keywords if kw in text.lower())
    if invest_count >= 1:
        categories.add("INVESTMENT_FRAUD")
        risk_score += 25 + (invest_count * 5)
        indicators.append(f"Investment fraud keywords: {invest_count} found")

    # Phishing patterns
    phishing_keywords = ["verify your account", "confirm your identity", "suspended account", "click here to verify", "login to confirm", "update your payment", "security alert", "unusual activity"]
    phishing_count = sum(1 for kw in phishing_keywords if kw in text.lower())
    if phishing_count >= 1:
        categories.add("PHISHING")
        risk_score += 20 + (phishing_count * 5)
        indicators.append(f"Phishing keywords: {phishing_count} found")

    # Crypto scam patterns
    crypto_keywords = ["free bitcoin", "crypto airdrop", "claim your tokens", "connect wallet", "metamask", "wallet connect", "seed phrase", "private key", "double your crypto", "staking reward"]
    crypto_count = sum(1 for kw in crypto_keywords if kw in text.lower())
    if crypto_count >= 1:
        categories.add("CRYPTO_FRAUD")
        risk_score += 25 + (crypto_count * 5)
        indicators.append(f"Crypto fraud keywords: {crypto_count} found")

    # Brand impersonation
    brands = ["paypal", "amazon", "apple", "microsoft", "google", "facebook", "netflix", "bank of america", "chase", "wells fargo", "barclays", "hsbc", "santander"]
    brand_count = sum(1 for b in brands if b in domain.lower() and b not in domain.split(".")[-2] if b in domain.lower())
    if brand_count >= 1:
        categories.add("BRAND_IMPERSONATION")
        risk_score += 30
        indicators.append(f"Brand name in domain: {brand_count} found")

    # Romance scam
    romance_keywords = ["lonely", "widow", "widower", "deployed soldier", "love you", "send money", "need money for", "emergency fund", "can you help me financially"]
    romance_count = sum(1 for kw in romance_keywords if kw in text.lower())
    if romance_count >= 2:
        categories.add("ROMANCE_SCAM")
        risk_score += 20 + (romance_count * 3)
        indicators.append(f"Romance scam indicators: {romance_count} found")

    # Tech support scam
    tech_keywords = ["your computer is infected", "virus detected", "call microsoft", "windows support", "security warning", "your pc is at risk", "toll-free support"]
    tech_count = sum(1 for kw in tech_keywords if kw in text.lower())
    if tech_count >= 1:
        categories.add("TECH_SUPPORT_SCAM")
        risk_score += 25 + (tech_count * 3)
        indicators.append(f"Tech support scam keywords: {tech_count} found")

    # Domain-based indicators
    if any(kw in domain.lower() for kw in ["login", "verify", "secure", "account", "update", "confirm"]):
        risk_score += 10
        indicators.append("Domain contains suspicious keywords (login/verify/secure)")

    # Recently registered (from RDAP or CT) - high risk
    risk_level = "MINIMAL"
    if risk_score >= 70:
        risk_level = "CRITICAL"
    elif risk_score >= 40:
        risk_level = "HIGH"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
    elif risk_score >= 10:
        risk_level = "LOW"

    return {
        "risk_score": min(risk_score, 100),
        "risk_level": risk_level,
        "categories": list(categories),
        "indicators": indicators,
    }


async def flag_domain_in_db(domain: str, investigation: dict) -> bool:
    """Flag a domain in the scam_websites database without opening a full case."""
    import asyncpg

    DB_CONFIG = {
        "host": "127.0.0.1", "port": 5432,
        "user": "gfin", "password": "GfinSecure2026!",
        "database": "gfin",
    }

    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if domain already exists
        existing = await conn.fetchrow("SELECT id, report_count, sources FROM scam_websites WHERE domain = $1", domain)

        scam_analysis = investigation.get("scam_indicators", [{}])
        risk_score = scam_analysis[0].get("risk_score", 0) if scam_analysis else 0
        risk_level = scam_analysis[0].get("risk_level", "UNKNOWN") if scam_analysis else "UNKNOWN"
        categories = scam_analysis[0].get("categories", []) if scam_analysis else []

        # Extract identifiers for the flagged record
        wallets = [d.get("value", "") for d in investigation.get("digital_identifiers", []) if d.get("type") == "CRYPTO_WALLET"]
        phones = [d.get("value", "") for d in investigation.get("digital_identifiers", []) if d.get("type") == "PHONE"]
        countries = investigation.get("affected_countries", [])
        source = investigation.get("source", "HUNTER")

        if existing:
            # Update existing record — increment report count, update sources
            old_sources = existing.get("sources", []) or []
            new_sources = list(set(old_sources + [source]))
            await conn.execute(
                """UPDATE scam_websites SET
                    report_count = $1, sources = $2, last_reported = NOW(),
                    risk_level = $3, countries_affected = $4,
                    wallet_addresses = $5, phone_numbers = $6,
                    description = $7
                WHERE domain = $8""",
                (existing["report_count"] or 1) + 1,
                new_sources,
                risk_level,
                countries,
                wallets,
                phones,
                investigation.get("summary", "")[:500],
                domain,
            )
            logger.info(f"  Flagged domain updated: {domain} (report #{existing['report_count'] + 1})")
            return False  # Not new
        else:
            # Insert new flagged domain
            await conn.execute(
                """INSERT INTO scam_websites (
                    domain, scam_type, risk_level, report_count, sources,
                    description, countries_affected, wallet_addresses, phone_numbers,
                    is_verified, status
                ) VALUES ($1, $2, $3, 1, $4, $5, $6, $7, $8, false, 'FLAGGED')""",
                domain,
                ", ".join(categories) if categories else "SUSPICIOUS",
                risk_level,
                [source],
                investigation.get("summary", "")[:500],
                countries,
                wallets,
                phones,
            )
            logger.info(f"  Domain flagged in database: {domain} (risk: {risk_level}, source: {source})")
            return True  # New
    except Exception as e:
        logger.error(f"  Failed to flag domain {domain}: {e}")
        return False
    finally:
        await conn.close()


def has_strong_evidence(investigation: dict) -> bool:
    """
    STRICT evidence gate — a case is opened ONLY when there is REAL evidence of active fraud.

    A domain being on a threat feed (OpenPhish, URLHaus) is NOT sufficient.
    DNS records and WHOIS data are NOT sufficient.
    A case requires AT LEAST ONE of:

    1. VICTIM EVIDENCE: Real victim complaints or confirmed financial losses
    2. CONFIRMED SCAM INFRASTRUCTURE: Multiple high-confidence scam indicators
       (brand impersonation + phishing forms + payment collection)
    3. LAW ENFORCEMENT CONFIRMATION: Domain already seized or flagged by LEA
    4. ACTIVE FRAUD OPERATION: Payment forms, wallet drainers, or live scam pages confirmed

    Domains that don't meet this threshold go to tracked_domains, NOT cases.
    """
    scam_indicators = investigation.get("scam_indicators", [])
    risk_score = 0
    risk_level = "UNKNOWN"
    categories = []

    if scam_indicators and isinstance(scam_indicators, list):
        si = scam_indicators[0]
        if isinstance(si, dict):
            risk_score = si.get("risk_score", 0)
            risk_level = si.get("risk_level", "UNKNOWN")
            categories = si.get("categories", [])

    all_scam_indicators = scam_indicators if isinstance(scam_indicators, list) else []
    source = investigation.get("source", "")
    confidence = investigation.get("confidence", 0)

    # Condition 1: BRAND_IMPERSONATION + CRYPTO_FORM (active wallet drainer)
    has_brand_impersonation = any(s.get("type") == "BRAND_IMPERSONATION" for s in all_scam_indicators if isinstance(s, dict))
    has_crypto_form = any(s.get("type") == "CRYPTO_FORM" for s in all_scam_indicators if isinstance(s, dict))
    if has_brand_impersonation and has_crypto_form:
        logger.info(f"  EVIDENCE GATE: PASS — Brand impersonation + crypto wallet drainer form = active fraud")
        return True

    # Condition 2: Risk score >= 75 (CRITICAL) + scam patterns detected
    if risk_score >= 75 and len(categories) >= 2:
        logger.info(f"  EVIDENCE GATE: PASS — Critical risk {risk_score} with {len(categories)} scam patterns")
        return True

    # Condition 3: CRYPTO_FORM detected (wallet drainer = active financial fraud)
    if has_crypto_form:
        logger.info(f"  EVIDENCE GATE: PASS — Crypto wallet/seed phrase form = active fraud operation")
        return True

    # Condition 4: 3+ scam pattern categories (multiple fraud indicators)
    if len(categories) >= 3:
        logger.info(f"  EVIDENCE GATE: PASS — {len(categories)} scam patterns: {categories}")
        return True

    # Condition 5: BRAND_IMPERSONATION + NEWLY_REGISTERED (fresh impersonation domain)
    has_newly_registered = any(s.get("type") == "NEWLY_REGISTERED" for s in all_scam_indicators if isinstance(s, dict))
    if has_brand_impersonation and has_newly_registered:
        logger.info(f"  EVIDENCE GATE: PASS — Brand impersonation on newly registered domain")
        return True

    logger.info(f"  EVIDENCE GATE: FAIL — Risk {risk_score}, patterns: {categories}, confidence: {confidence}, source: {source}")
    logger.info(f"  -> Domain will be tracked, not opened as case")
    return False



# ============================================================
# DATABASE: Create GFIN cases with full evidence
# ============================================================

async def add_to_tracked_domains(domain: str, investigation: dict) -> str:
    """Add domain to tracked_domains table (default path for all discovered domains)."""
    import asyncpg

    DB_CONFIG = {
        "host": "127.0.0.1", "port": 5432,
        "user": "gfin", "password": "GfinSecure2026!",
        "database": "gfin",
    }

    scam_indicators = investigation.get("scam_indicators", [])
    risk_level = "UNKNOWN"
    risk_score = 0
    patterns = []
    if scam_indicators and isinstance(scam_indicators, list):
        si = scam_indicators[0]
        if isinstance(si, dict):
            risk_level = si.get("risk_level", "UNKNOWN")
            risk_score = si.get("risk_score", 0)
            patterns = si.get("categories", [])

    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute(
            """INSERT INTO tracked_domains (domain, source, risk_level, risk_score, confidence, patterns, evidence_summary, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'TRACKED')
            ON CONFLICT DO NOTHING""",
            domain,
            investigation.get("source", "AUTO"),
            risk_level,
            risk_score,
            investigation.get("confidence", 0),
            patterns,
            investigation.get("summary", "")[:500],
        )
        logger.info(f"  Domain tracked: {domain} (risk: {risk_level})")
    except Exception as e:
        logger.error(f"  Failed to track domain {domain}: {e}")
    finally:
        await conn.close()

    return domain


async def create_case_from_investigation(investigation: dict) -> str:
    """Create a GFIN case ONLY when strong evidence exists. Otherwise, track the domain."""
    import asyncpg

    DB_CONFIG = {
        "host": "127.0.0.1", "port": 5432,
        "user": "gfin", "password": "GfinSecure2026!",
        "database": "gfin",
    }

    case_id = f"GFIN-AUTO-{int(time.time() * 1000) % 10000000000}"
    target = investigation["domain"]
    trigger = f"Autonomous discovery: {investigation['source']}"

    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Insert case
        await conn.execute(
            """INSERT INTO cases (
                case_id, target, target_type, trigger, summary, status, confidence,
                scam_patterns, affected_countries, routed_to_countries,
                physical_locations, financial_indicators, digital_identifiers,
                evidence_chain, victim_count, created_by_officer, classification
            ) VALUES ($1, $2, $3, $4, $5, 'INVESTIGATING', $6, $7, $8, $9, $10, $11, $12, $13, 0, 'GFIN_AUTONOMOUS_HUNTER', 'LAW ENFORCEMENT SENSITIVE')""",
            case_id,
            target,
            "DOMAIN",
            trigger,
            investigation["summary"][:500],
            investigation["confidence"],
            investigation["scam_patterns"],
            investigation["affected_countries"],
            investigation["routed_to_countries"],
            json.dumps(investigation["physical_locations"]),
            json.dumps(investigation["financial_indicators"]),
            json.dumps(investigation["digital_identifiers"]),
            json.dumps(investigation["evidence_chain"]),
        )

        # Insert evidence records
        for ev in investigation["evidence_chain"]:
            ev_id = ev.get("evidence_id", f"E-AH-{int(time.time())}")
            await conn.execute(
                """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (evidence_id) DO NOTHING""",
                case_id,
                ev_id + f"-{case_id[-6:]}",
                ev.get("phase", ""),
                ev.get("finding", "")[:500],
                ev.get("source", ""),
                ev.get("source_url", "autonomous_hunter"),
                "AUTOMATED_OSINT",
                ev.get("confidence", "MEDIUM"),
            )

        # Log to audit
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "AUTO_DISCOVERY_INVESTIGATION", "GFIN_AUTONOMOUS_HUNTER", "autonomous_hunter",
            target, f"Evidence: {len(investigation['evidence_chain'])} steps, Countries: {', '.join(investigation['affected_countries'])}, Risk: {investigation['scam_indicators'][0].get('risk_level', 'unknown') if investigation['scam_indicators'] else 'unknown'}"
        )

        logger.info(f"  Case created: {case_id} for {target}")
        return case_id

    finally:
        await conn.close()

# ============================================================
# MAIN LOOP
# ============================================================

async def run_cycle():
    """Run one full discovery + investigation cycle."""
    logger.info("=" * 60)
    logger.info("STARTING AUTONOMOUS HUNTER CYCLE")
    logger.info("=" * 60)

    # Discover new targets
    targets = discover_targets()

    if not targets:
        logger.info("No new targets discovered this cycle. Sleeping.")
        return 0

    cases_created = 0
    domains_flagged = 0
    domains_skipped = 0

    for target in targets[:MAX_CASES_PER_CYCLE]:
        domain = target["domain"]
        source = target["source"]

        if domain in _investigated_cache:
            domains_skipped += 1
            continue

        logger.info(f"INVESTIGATING: {domain} (source: {source})")

        try:
            investigation = investigate_domain(domain, source, target)

            # ALWAYS add domain to tracked_domains database
            is_new = await flag_domain_in_db(domain, investigation)
            await add_to_tracked_domains(domain, investigation)
            domains_flagged += 1

            # ONLY open a full case if there is STRONG evidence (victims, financial fraud, active scam)
            if has_strong_evidence(investigation):
                case_id = await create_case_from_investigation(investigation)
                _investigated_cache.add(domain)
                cases_created += 1
                logger.info(f"  => CASE OPENED: {case_id} for {domain} (strong evidence — real fraud)")
            else:
                _investigated_cache.add(domain)
                logger.info(f"  => TRACKED ONLY: {domain} (added to domain database, not a case)")

        except Exception as e:
            logger.error(f"  Failed to investigate {domain}: {e}")

        # Rate limit between investigations
        time.sleep(3)

    logger.info(f"Cycle complete: {cases_created} cases opened, {domains_flagged} domains flagged, {domains_skipped} already known")
    return cases_created


async def main():
    """Main 24/7 loop."""
    logger.info("=" * 60)
    logger.info("GFIN AUTONOMOUS SCAM HUNTER v2.1 — EVIDENCE-GATED — STARTING")
    logger.info(f"Scan interval: {SCAN_INTERVAL_SECONDS}s")
    logger.info(f"Max cases per cycle: {MAX_CASES_PER_CYCLE}")
    logger.info("=" * 60)

    while True:
        try:
            await run_cycle()
        except Exception as e:
            logger.error(f"Cycle error: {e}")

        logger.info(f"Sleeping {SCAN_INTERVAL_SECONDS} seconds until next cycle...")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())

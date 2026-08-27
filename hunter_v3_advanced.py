#!/usr/bin/env python3
"""
GFIN Hunter v3.0 — Module 2: Advanced Cyber Intelligence
Adds: Neo4j graph storage, WHOIS privacy guard detection, subdomain enumeration,
wallet intelligence, automated takedown report generation.
"""

import re, json, ssl, hashlib, urllib.request, urllib.parse, socket, logging
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ============================================================
# 1. NEO4J GRAPH STORAGE — Infrastructure correlation graph
# ============================================================
def store_investigation_in_neo4j(investigation: dict, case_id: str = None) -> bool:
    """Store investigation entities and relationships in Neo4j graph database."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "gfin_temp_password"))
        
        domain = investigation.get("domain", "")
        if not domain:
            return False
        
        with driver.session() as session:
            # Create domain node
            session.run(
                "MERGE (d:Domain {name: $domain}) "
                "SET d.last_seen = $timestamp, d.case_id = $case_id, "
                "d.risk_level = $risk, d.confidence = $conf, d.source = $source",
                domain=domain,
                timestamp=datetime.now(timezone.utc).isoformat(),
                case_id=case_id or "",
                risk=investigation.get("scam_indicators", [{}])[0].get("risk_level", "UNKNOWN") if investigation.get("scam_indicators") else "UNKNOWN",
                conf=investigation.get("confidence", 0),
                source=investigation.get("source", ""),
            )
            
            # Link IPs
            for identifier in investigation.get("digital_identifiers", []):
                if identifier.get("type") == "IP":
                    ip = identifier.get("value", "")
                    if ip:
                        session.run(
                            "MERGE (i:IP {address: $ip}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:RESOLVES_TO]->(i)",
                            ip=ip, domain=domain,
                        )
                elif identifier.get("type") == "MX":
                    mx = identifier.get("value", "")
                    if mx:
                        session.run(
                            "MERGE (m:MailServer {name: $mx}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:USES_MAIL]->(m)",
                            mx=mx, domain=domain,
                        )
                elif identifier.get("type") == "NS":
                    ns = identifier.get("value", "")
                    if ns:
                        session.run(
                            "MERGE (n:NameServer {name: $ns}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:USES_NS]->(n)",
                            ns=ns, domain=domain,
                        )
                elif identifier.get("type") == "REGISTRAR":
                    reg = identifier.get("value", "")
                    if reg:
                        session.run(
                            "MERGE (r:Registrar {name: $reg}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:REGISTERED_WITH]->(r)",
                            reg=reg, domain=domain,
                        )
                elif identifier.get("type") == "SSL_SAN":
                    san = identifier.get("value", "")
                    if san:
                        session.run(
                            "MERGE (s:Domain {name: $san}) "
                            "MERGE (d1:Domain {name: $domain}) "
                            "MERGE (d1)-[:SHARES_SSL_CERT]->(s)",
                            san=san, domain=domain,
                        )
                elif identifier.get("type") == "FAVICON_HASH":
                    fav = identifier.get("value", "")
                    if fav:
                        session.run(
                            "MERGE (f:Favicon {hash: $fav}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:HAS_FAVICON]->(f)",
                            fav=fav, domain=domain,
                        )
                elif identifier.get("type") == "ANALYTICS_ID":
                    aid = identifier.get("value", "")
                    if aid:
                        session.run(
                            "MERGE (a:AnalyticsID {id: $aid}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:USES_ANALYTICS]->(a)",
                            aid=aid, domain=domain,
                        )
                elif identifier.get("type") == "EMAIL":
                    email = identifier.get("value", "")
                    if email:
                        session.run(
                            "MERGE (e:Email {address: $email}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:HAS_EMAIL]->(e)",
                            email=email, domain=domain,
                        )
                elif identifier.get("type") == "PHONE":
                    phone = identifier.get("value", "")
                    if phone:
                        session.run(
                            "MERGE (p:Phone {number: $phone}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:HAS_PHONE]->(p)",
                            phone=phone, domain=domain,
                        )
                elif identifier.get("type") == "SOCIAL_ACCOUNT":
                    social = identifier.get("value", "")
                    if social:
                        session.run(
                            "MERGE (s:SocialAccount {name: $social}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:LINKS_TO]->(s)",
                            social=social, domain=domain,
                        )
            
            # Link hosting provider
            for loc in investigation.get("physical_locations", []):
                isp = loc.get("isp", "")
                if isp:
                    session.run(
                        "MERGE (h:HostingProvider {name: $isp}) "
                        "SET h.country = $country, h.asn = $asn "
                        "MERGE (d:Domain {name: $domain}) "
                        "MERGE (d)-[:HOSTED_BY]->(h)",
                        isp=isp, country=loc.get("country", ""), asn=loc.get("asn", ""), domain=domain,
                    )
            
            # Link crypto wallets
            for fin in investigation.get("financial_indicators", []):
                if fin.get("type") == "CRYPTO_WALLET" or "address" in fin:
                    wallet = fin.get("address", fin.get("value", ""))
                    wallet_type = fin.get("type", fin.get("wallet_type", "CRYPTO"))
                    if wallet:
                        session.run(
                            "MERGE (w:Wallet {address: $wallet}) SET w.type = $wtype "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:ACCEPTS_WALLET]->(w)",
                            wallet=wallet, wtype=wallet_type, domain=domain,
                        )
            
            # Link payment processors
            for fin in investigation.get("financial_indicators", []):
                if fin.get("type") == "PAYMENT_PROCESSOR":
                    pp = fin.get("processor", "")
                    if pp:
                        session.run(
                            "MERGE (p:PaymentProcessor {name: $pp}) "
                            "MERGE (d:Domain {name: $domain}) "
                            "MERGE (d)-[:USES_PAYMENT]->(p)",
                            pp=pp, domain=domain,
                        )
            
            # Link scam patterns
            for pattern in investigation.get("scam_patterns", []):
                if pattern:
                    session.run(
                        "MERGE (s:ScamPattern {name: $pattern}) "
                        "MERGE (d:Domain {name: $domain}) "
                        "MERGE (d)-[:MATCHES_PATTERN]->(s)",
                        pattern=pattern, domain=domain,
                    )
            
            # Link countries
            for country in investigation.get("affected_countries", []):
                if country:
                    session.run(
                        "MERGE (c:Country {code: $country}) "
                        "MERGE (d:Domain {name: $domain}) "
                        "MERGE (d)-[:AFFECTS_COUNTRY]->(c)",
                        country=country, domain=domain,
                    )
        
        driver.close()
        logger.info(f"  [NEO4J] Stored graph data for {domain}")
        return True
    except ImportError:
        logger.debug("  [NEO4J] neo4j driver not installed")
        return False
    except Exception as e:
        logger.debug(f"  [NEO4J] Storage failed: {e}")
        return False

def query_related_domains(domain: str, depth: int = 2) -> dict:
    """Find all domains connected to this domain through shared infrastructure."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "gfin_temp_password"))
        
        with driver.session() as session:
            # Find domains sharing IPs, NS, SSL, favicon, analytics, hosting
            result = session.run("""
                MATCH (d:Domain {name: $domain})-[r]->(n)
                MATCH (other:Domain)-[r2]->(n)
                WHERE other.name <> $domain
                RETURN DISTINCT other.name as domain, 
                       collect(DISTINCT labels(n)[0]) as shared_types,
                       collect(DISTINCT coalesce(n.address, n.name, n.hash, n.id)) as shared_values
                LIMIT 50
            """, domain=domain)
            
            related = []
            for record in result:
                related.append({
                    "domain": record["domain"],
                    "shared_infrastructure": record["shared_types"],
                    "shared_values": record["shared_values"],
                })
            
            # Count total graph size for this domain
            count_result = session.run("""
                MATCH (d:Domain {name: $domain})--(n)
                RETURN count(DISTINCT n) as total_nodes,
                       count(DISTINCT labels(n)[0]) as node_types
            """, domain=domain)
            count = count_result.single()
            
            driver.close()
            return {
                "domain": domain,
                "related_domains": related,
                "total_graph_nodes": count["total_nodes"] if count else 0,
                "node_types": count["node_types"] if count else 0,
            }
    except Exception as e:
        logger.debug(f"  [NEO4J] Query failed: {e}")
        return {"domain": domain, "related_domains": [], "total_graph_nodes": 0}

# ============================================================
# 2. WHOIS PRIVACY GUARD DETECTION
# ============================================================
PRIVACY_SERVICES = [
    "withheld for privacy", "privacy guard", "whoisguard", "domains by proxy",
    "privacy protect", "perfect privacy", "whois privacy", "domain privacy",
    "privacy service", "redacted for privacy", "statutory masking enabled",
    "data protected", "contact privacy", "privacy administrator",
    "super privacy", "whois identity shield", "domain privacy service",
    "privacy please", "whois privacy protection", "na whois privacy",
    "thewhois privacy", "id shield", "privacykeep", "safe whois",
]

def detect_privacy_guard(rdap_data: dict, content: str = None) -> dict:
    """Detect if domain uses WHOIS privacy protection service."""
    result = {
        "uses_privacy_guard": False,
        "privacy_service": "",
        "indicators": [],
    }
    
    # Check RDAP data for privacy keywords
    rdap_text = json.dumps(rdap_data).lower() if rdap_data else ""
    
    for service in PRIVACY_SERVICES:
        if service in rdap_text:
            result["uses_privacy_guard"] = True
            result["privacy_service"] = service.title()
            result["indicators"].append(f"Found '{service}' in RDAP data")
    
    # Check registrant name/entity
    for entity in rdap_data.get("entities", []) if rdap_data else []:
        vcard = entity.get("vcardArray", [])
        if len(vcard) > 1:
            for field in vcard[1]:
                if field[0] in ["fn", "org", "role"]:
                    value = str(field[-1]).lower() if len(field) > 1 else str(field).lower()
                    for service in PRIVACY_SERVICES:
                        if service in value:
                            result["uses_privacy_guard"] = True
                            result["privacy_service"] = service.title()
                            result["indicators"].append(f"Registrant name: '{field[-1]}'")
    
    # Check for missing registrant info (another privacy indicator)
    if rdap_data and not rdap_data.get("entities"):
        result["indicators"].append("No registrant entities in RDAP — possible privacy")
    
    return result

# ============================================================
# 3. SUBDOMAIN ENUMERATION — Find hidden scam pages
# ============================================================
SUSPICIOUS_SUBDOMAIN_PREFIXES = [
    "login", "secure", "wallet", "verify", "account", "auth", "signin",
    "register", "pay", "payment", "app", "portal", "connect", "confirm",
    "recover", "restore", "unlock", "claim", "swap", "bridge", "stake",
    "airdrop", "mint", "free", "bonus", "reward", "gift",
]

def enumerate_subdomains(domain: str) -> dict:
    """Find subdomains via Certificate Transparency logs (crt.sh)."""
    result = {
        "subdomains": [],
        "suspicious_subdomains": [],
        "total_count": 0,
    }
    
    try:
        # Query crt.sh for all certificates for this domain
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)",
        })
        resp = urllib.request.urlopen(req, timeout=15, context=SSL_CTX)
        data = json.loads(resp.read().decode('utf-8', errors='replace'))
        
        # Extract unique subdomains from certificate SANs
        subdomains = set()
        for entry in data[:200]:  # Limit to most recent 200 certs
            name_value = entry.get("name_value", "")
            for name in name_value.split("\n"):
                name = name.strip().lower()
                if name and name.endswith(domain) and name != domain and not name.startswith("*"):
                    subdomains.add(name)
        
        result["subdomains"] = sorted(subdomains)[:50]
        result["total_count"] = len(subdomains)
        
        # Flag suspicious subdomains
        for sub in result["subdomains"]:
            for prefix in SUSPICIOUS_SUBDOMAIN_PREFIXES:
                if sub.startswith(prefix + ".") or sub.startswith(prefix + "-"):
                    result["suspicious_subdomains"].append({
                        "subdomain": sub,
                        "prefix": prefix,
                        "risk": "HIGH — common scam subdomain pattern",
                    })
                    break
        
    except Exception as e:
        logger.debug(f"  [SUBDOMAIN] Enumeration failed for {domain}: {e}")
    
    return result

# ============================================================
# 4. WALLET INTELLIGENCE — Check crypto wallets against blockchain APIs
# ============================================================
def check_wallet_intelligence(address: str, wallet_type: str) -> dict:
    """Check a crypto wallet against blockchain APIs for balance, tx count, and risk."""
    result = {
        "address": address,
        "type": wallet_type,
        "balance": None,
        "tx_count": None,
        "first_seen": None,
        "last_active": None,
        "is_known_scam": False,
        "total_received": None,
        "risk_level": "UNKNOWN",
    }
    
    try:
        if wallet_type == "BTC":
            # blockchain.info API (free, no key)
            url = f"https://blockchain.info/rawaddr/{address}?limit=5"
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Scanner/1.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            data = json.loads(resp.read().decode())
            result["balance"] = data.get("final_balance", 0) / 1e8  # Satoshis to BTC
            result["tx_count"] = data.get("n_tx", 0)
            result["total_received"] = data.get("total_received", 0) / 1e8
            if data.get("txs"):
                txs = data["txs"]
                result["first_seen"] = datetime.fromtimestamp(txs[-1].get("time", 0), tz=timezone.utc).isoformat() if txs else None
                result["last_active"] = datetime.fromtimestamp(txs[0].get("time", 0), tz=timezone.utc).isoformat() if txs else None
            result["risk_level"] = "HIGH" if result["total_received"] and result["total_received"] > 1 else "LOW" if result["tx_count"] and result["tx_count"] < 3 else "MEDIUM"
        
        elif wallet_type in ("ETH", "EVM"):
            # Blockscout free API (no key needed)
            url = f"https://eth.blockscout.com/api?module=account&action=balance&address={address}"
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Scanner/1.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            data = json.loads(resp.read().decode())
            if data.get("status") == "1":
                result["balance"] = int(data.get("result", "0")) / 1e18
            
            # Get tx count
            url2 = f"https://eth.blockscout.com/api?module=account&action=txlist&address={address}&page=1&offset=5&sort=desc"
            req2 = urllib.request.Request(url2, headers={"User-Agent": "GFIN-Scanner/1.0"})
            resp2 = urllib.request.urlopen(req2, timeout=10, context=SSL_CTX)
            data2 = json.loads(resp2.read().decode())
            if data2.get("status") == "1" and data2.get("result"):
                result["tx_count"] = len(data2["result"])
                if data2["result"]:
                    ts = int(data2["result"][0].get("timeStamp", 0))
                    result["last_active"] = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            result["risk_level"] = "HIGH" if result["balance"] and result["balance"] > 0.1 else "MEDIUM"
        
        elif wallet_type == "TRON":
            # Tronscan free API
            url = f"https://apilist.tronscanapi.com/api/account/tokens?address={address}"
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Scanner/1.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            data = json.loads(resp.read().decode())
            tokens = data.get("data", [])
            result["balance"] = sum(float(t.get("balance", 0)) / 1e6 for t in tokens if t.get("tokenType") == "TRC20")
            result["tx_count"] = data.get("total", 0) if isinstance(data.get("total"), int) else None
            result["risk_level"] = "HIGH" if result["balance"] and result["balance"] > 100 else "MEDIUM"
        
    except Exception as e:
        logger.debug(f"  [WALLET] Intelligence check failed for {address}: {e}")
        result["risk_level"] = "UNKNOWN"
    
    return result

def check_all_wallets(investigation: dict) -> List[dict]:
    """Check all crypto wallets found in an investigation."""
    results = []
    for fin in investigation.get("financial_indicators", []):
        if fin.get("type") == "CRYPTO_WALLET" or "address" in fin:
            address = fin.get("address", "")
            wallet_type = fin.get("type", fin.get("wallet_type", "BTC"))
            if address and wallet_type in ("BTC", "ETH", "EVM", "TRON"):
                intel = check_wallet_intelligence(address, wallet_type)
                results.append(intel)
    return results

# ============================================================
# 5. AUTOMATED TAKEDOWN REPORT GENERATION
# ============================================================
def generate_takedown_report(investigation: dict) -> dict:
    """Generate professional abuse/takedown reports for hosting, registrar, and CDN."""
    domain = investigation.get("domain", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Extract key data
    ips = [d["value"] for d in investigation.get("digital_identifiers", []) if d.get("type") == "IP"]
    hosting_providers = set()
    for loc in investigation.get("physical_locations", []):
        if loc.get("isp"):
            hosting_providers.add(loc["isp"])
    
    registrars = [d["value"] for d in investigation.get("digital_identifiers", []) if d.get("type") == "REGISTRAR"]
    nameservers = [d["value"] for d in investigation.get("digital_identifiers", []) if d.get("type") == "NS"]
    ssl_sans = [d["value"] for d in investigation.get("digital_identifiers", []) if d.get("type") == "SSL_SAN"]
    wallets = [f.get("address", "") for f in investigation.get("financial_indicators", []) if "address" in f]
    payment_processors = [f.get("processor", "") for f in investigation.get("financial_indicators", []) if f.get("type") == "PAYMENT_PROCESSOR"]
    
    scam_patterns = investigation.get("scam_patterns", [])
    scam_indicators = investigation.get("scam_indicators", [])
    risk_level = scam_indicators[0].get("risk_level", "UNKNOWN") if scam_indicators and isinstance(scam_indicators[0], dict) else "UNKNOWN"
    risk_score = scam_indicators[0].get("risk_score", 0) if scam_indicators and isinstance(scam_indicators[0], dict) else 0
    
    countries = investigation.get("affected_countries", [])
    evidence_chain = investigation.get("evidence_chain", [])
    
    # Detect CDN
    cdn = None
    for loc in investigation.get("physical_locations", []):
        isp = str(loc.get("isp", "")).lower()
        if "cloudflare" in isp:
            cdn = "Cloudflare"
            break
        if "cloudfront" in isp:
            cdn = "AWS CloudFront"
            break
    
    # === HOSTING PROVIDER ABUSE REPORT ===
    hosting_report = f"""ABUSE REPORT — FRAUDULENT WEBSITE TAKEDOWN REQUEST
============================================================

Report ID: GFIN-TD-{int(datetime.now().timestamp())}
Date: {timestamp}
Source: Global Fraud Intelligence Network (GFIN) — Autonomous Hunter v3.0

DOMAIN: {domain}
IP ADDRESSES: {', '.join(ips) if ips else 'Not resolved'}
HOSTING PROVIDER: {', '.join(hosting_providers) if hosting_providers else 'Unknown'}
NAMESERVERS: {', '.join(nameservers) if nameservers else 'Unknown'}

CLASSIFICATION: {risk_level} RISK (score: {risk_score}/100)
SCAM CATEGORIES: {', '.join(scam_patterns) if scam_patterns else 'Suspicious activity detected'}

EVIDENCE SUMMARY:
{chr(10).join(f'  [{e.get("phase", "?")}] {e.get("finding", "")}' for e in evidence_chain[:10])}

AFFECTED COUNTRIES: {', '.join(countries) if countries else 'Multiple'}

CRYPTO WALLETS FOUND: {', '.join(wallets) if wallets else 'None detected'}
PAYMENT PROCESSORS: {', '.join(payment_processors) if payment_processors else 'None detected'}

REQUESTED ACTION:
1. Immediately suspend hosting for domain {domain}
2. Preserve server logs for law enforcement investigation
3. Report any associated accounts to GFIN

This report was generated autonomously by the GFIN Hunter v3.0 system
based on evidence-based analysis. All findings are verifiable through
the evidence chain above. This is a good-faith report filed under
applicable abuse reporting frameworks.

GFIN Reference: gfin-system.com
"""
    
    # === REGISTRAR ABUSE REPORT ===
    registrar_report = f"""DOMAIN REGISTRAR ABUSE REPORT — FRAUDULENT DOMAIN USAGE
=====================================================

Report ID: GFIN-DR-{int(datetime.now().timestamp())}
Date: {timestamp}
Source: Global Fraud Intelligence Network (GFIN)

DOMAIN: {domain}
REGISTRAR: {', '.join(registrars) if registrars else 'Unknown'}

CLASSIFICATION: {risk_level} RISK
SCAM CATEGORIES: {', '.join(scam_patterns) if scam_patterns else 'Suspicious'}
BRAND IMPERSONATION: {', '.join(s.get('target_brand', '') for s in scam_indicators if isinstance(s, dict) and s.get('type') == 'BRAND_IMPERSONATION') or 'None detected'}

DOMAIN AGE: {', '.join(f'{s.get("age_days", "?")} days' for s in scam_indicators if isinstance(s, dict) and s.get('type') == 'NEWLY_REGISTERED') or 'Unknown'}

SSL CERTIFICATE SANs (related domains): {', '.join(ssl_sans[:10]) if ssl_sans else 'None'}

REQUESTED ACTION:
1. Suspend or transfer domain {domain}
2. Provide registrant contact information to law enforcement upon request
3. Flag associated accounts for fraudulent activity

Evidence chain available upon request.
GFIN Reference: gfin-system.com
"""
    
    # === CDN ABUSE REPORT (if Cloudflare or similar) ===
    cdn_report = None
    if cdn:
        cdn_report = f"""CDN ABUSE REPORT — FRAUDULENT CONTENT BEHIND CDN
==================================================

Report ID: GFIN-CDN-{int(datetime.now().timestamp())}
Date: {timestamp}
Source: Global Fraud Intelligence Network (GFIN)

DOMAIN: {domain}
CDN PROVIDER: {cdn}
ORIGIN IP: {', '.join(ips) if ips else 'Unknown'}

CLASSIFICATION: {risk_level} RISK
SCAM CATEGORIES: {', '.join(scam_patterns) if scam_patterns else 'Suspicious'}

This domain is serving fraudulent content through {cdn}.
The origin server should be investigated and the domain
should be blocked at the CDN level.

REQUESTED ACTION:
1. Block domain {domain} at CDN edge
2. Provide origin server IP and access logs to law enforcement
3. Disable any CDN features protecting the origin (DDoS protection, etc.)

GFIN Reference: gfin-system.com
"""
    
    return {
        "report_id": f"GFIN-TD-{int(datetime.now().timestamp())}",
        "domain": domain,
        "timestamp": timestamp,
        "hosting_report": hosting_report,
        "registrar_report": registrar_report,
        "cdn_report": cdn_report,
        "cdn_provider": cdn,
        "hosting_provider": list(hosting_providers),
        "registrar": registrars,
        "classification": risk_level,
        "scam_categories": scam_patterns,
        "target_recipients": {
            "hosting": list(hosting_providers),
            "registrar": registrars,
            "cdn": [cdn] if cdn else [],
        },
    }

# ============================================================
# INTEGRATION: Run all advanced modules on an investigation
# ============================================================
def run_advanced_intelligence(investigation: dict, rdap_data: dict = None) -> dict:
    """Run all advanced intelligence modules on an investigation result."""
    domain = investigation.get("domain", "")
    advanced = {
        "privacy_guard": None,
        "subdomains": None,
        "wallet_intelligence": [],
        "takedown_report": None,
        "neo4j_stored": False,
    }
    
    # 1. Privacy guard detection
    privacy = detect_privacy_guard(rdap_data or {})
    if privacy["uses_privacy_guard"]:
        advanced["privacy_guard"] = privacy if privacy and privacy.get("uses_privacy_guard") else None
        investigation["evidence_chain"].append({
            "evidence_id": f"E-ADV-{len(investigation.get('evidence_chain', []))+1:04d}",
            "phase": "PRIVACY_GUARD",
            "finding": f"WHOIS privacy protection detected: {privacy['privacy_service']}",
            "source": "RDAP analysis",
            "confidence": "MEDIUM",
        })
        investigation["scam_indicators"].append({
            "type": "PRIVACY_GUARD",
            "severity": "MEDIUM",
            "description": f"Domain uses WHOIS privacy: {privacy['privacy_service']}",
        })
    
    # 2. Subdomain enumeration
    subdomain_info = enumerate_subdomains(domain)
    if subdomain_info["total_count"] > 0:
        advanced["subdomains"] = subdomain_info if subdomain_info else {"total_count": 0, "subdomains": [], "suspicious_subdomains": []}
        investigation["evidence_chain"].append({
            "evidence_id": f"E-ADV-{len(investigation.get('evidence_chain', []))+1:04d}",
            "phase": "SUBDOMAIN_ENUMERATION",
            "finding": f"Found {subdomain_info['total_count']} subdomains, {len(subdomain_info['suspicious_subdomains'])} suspicious (login/secure/wallet patterns)",
            "source": "crt.sh Certificate Transparency",
            "confidence": "HIGH",
        })
        for sub in subdomain_info["suspicious_subdomains"][:5]:
            investigation["digital_identifiers"].append({
                "type": "SUSPICIOUS_SUBDOMAIN",
                "value": sub["subdomain"],
                "context": sub["risk"],
            })
    
    # 3. Wallet intelligence (check all found wallets)
    wallets = check_all_wallets(investigation)
    if wallets:
        advanced["wallet_intelligence"] = wallets
        for w in wallets:
            if w.get("balance") is not None:
                investigation["evidence_chain"].append({
                    "evidence_id": f"E-ADV-{len(investigation.get('evidence_chain', []))+1:04d}",
                    "phase": "WALLET_INTELLIGENCE",
                    "finding": f"{w['type']} wallet {w['address']}: balance={w['balance']}, txs={w['tx_count']}, risk={w['risk_level']}",
                    "source": f"Blockchain API ({w['type']})",
                    "confidence": "HIGH",
                })
    
    # 4. Generate takedown report (for cases that pass the evidence gate)
    if investigation.get("confidence", 0) >= 0.3 or any(s.get("type") == "BRAND_IMPERSONATION" for s in investigation.get("scam_indicators", []) if isinstance(s, dict)):
        report = generate_takedown_report(investigation)
        advanced["takedown_report"] = report
        investigation["evidence_chain"].append({
            "evidence_id": f"E-ADV-{len(investigation.get('evidence_chain', []))+1:04d}",
            "phase": "TAKEDOWN_REPORT",
            "finding": f"Generated takedown report: hosting={', '.join(report.get('hosting_provider', ['?']))}, registrar={', '.join(report.get('registrar', ['?']))}, cdn={report.get('cdn_provider', 'none')}",
            "source": "GFIN Takedown Report Generator",
            "confidence": "HIGH",
        })
    
    # 5. Store in Neo4j
    advanced["neo4j_stored"] = store_investigation_in_neo4j(investigation)
    
    return advanced

print("GFIN Hunter v3.0 Advanced Intelligence Module loaded")
print("Features: Neo4j graph storage, WHOIS privacy guard, subdomain enumeration,")
print("wallet intelligence (BTC/ETH/TRON blockchain APIs), takedown report generation")

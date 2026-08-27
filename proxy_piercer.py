"""
GFIN Proxy & Privacy Piercing Engine v1.0
Detects when scammers hide behind WHOIS privacy, CDN proxies, hosting proxies,
and traces back to the real operator identity and physical address.

Capabilities:
1. WHOIS Privacy Proxy Detection — identify privacy services (WhoisGuard, DomainsByProxy, Withheld, etc.)
2. Historical WHOIS Lookup — check historical records before privacy was enabled
3. CDN/Reverse Proxy Detection — detect Cloudflare, Sucuri, Imperva, etc.
4. Origin IP Discovery — find real IP behind CDN via SPF, MX, TXT, subdomains, cert transparency
5. Registrar Correlation — match registrar + email patterns across domains
6. Infrastructure Tracing — trace hosting to physical data center location
7. Email/Phone Correlation — match leaked contact info across registrations
8. SSL Certificate Pivot — find other domains sharing the same certificate
"""

import asyncio
import aiohttp
import json
import re
import socket
import ssl
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Known WHOIS privacy services
PRIVACY_SERVICES = [
    "whoisguard", "whois guard", "domains by proxy", "domainbyproxy",
    "perfect privacy", "privacy guard", "privacy protect",
    "withheld for privacy", "redacted for privacy", "data redacted",
    "statutorymasking", "contact privacy", "privacydmarc",
    "please query the registrar", "registration private",
    "gdpr masked", "whois privacy", "privacy service",
    "internet domain service bs", "internic domain privacy",
    "privacy hero", "privacygate", "namecheap privacyguard",
    "withheldforprivacy", "super privacy service", "whoisprivacy",
    "privacyprotection", "nobody", "not disclosed",
    "redacted | registry", "the whois privacy"
]

# Known CDN / reverse proxy services (by ASN, names, headers)
CDN_PROVIDERS = {
    "cloudflare": {
        "names": ["cloudflare", "cf-", "cloudflareinc"],
        "asn_range": ["13335"],
        "header": "cf-ray",
        "ip_range_hint": "104.16.0.0/13",
        "methods_to_bypass": ["direct_dns", "historical_dns", "subdomain_scan", "mail_server", "spf_record"]
    },
    "sucuri": {
        "names": ["sucuri", "sucuri.net"],
        "asn_range": ["19342"],
        "header": "x-sucuri-id",
        "methods_to_bypass": ["direct_dns", "historical_dns"]
    },
    "imperva_incapsula": {
        "names": ["incapsula", "imperva", "incapsulanetworks"],
        "asn_range": ["19551"],
        "header": "x-iinfo",
        "methods_to_bypass": ["direct_dns", "historical_dns", "subdomain_scan"]
    },
    "akamai": {
        "names": ["akamai", "akamai technologies", "akamaitechnologies"],
        "asn_range": ["20940", "16625"],
        "header": "x-akamai",
        "methods_to_bypass": ["direct_dns", "historical_dns"]
    },
    "fastly": {
        "names": ["fastly", "fastlyinc"],
        "asn_range": ["54113"],
        "header": "x-served-by",
        "methods_to_bypass": ["direct_dns", "historical_dns"]
    },
    "aws_cloudfront": {
        "names": ["amazon", "aws", "cloudfront"],
        "asn_range": ["16509", "14618"],
        "header": "x-amz-cf-id",
        "methods_to_bypass": ["direct_dns", "historical_dns", "subdomain_scan"]
    },
    "ddos_guard": {
        "names": ["ddos guard", "ddos-guard"],
        "asn_range": ["57724"],
        "header": "ddos-guard",
        "methods_to_bypass": ["direct_dns", "historical_dns"]
    },
    "arvancloud": {
        "names": ["arvan", "arvancloud"],
        "asn_range": ["42337"],
        "header": "arvancloud",
        "methods_to_bypass": ["direct_dns"]
    }
}

# Data center / hosting providers for physical location tracing
HOSTING_PROVIDERS = {
    "hetzner": {"name": "Hetzner Online GmbH", "country": "DE", "cities": ["Falkenstein", "Nuremberg", "Frankfurt"]},
    "ovh": {"name": "OVH SAS", "country": "FR", "cities": ["Roubaix", "Gravelines", "Strasbourg"]},
    "digitalocean": {"name": "DigitalOcean LLC", "country": "US", "cities": ["New York", "San Francisco", "Singapore"]},
    "linode": {"name": "Linode/Akamai", "country": "US", "cities": ["Dallas", "Fremont", "London"]},
    "vultr": {"name": "Vultr Holdings LLC", "country": "US", "cities": ["New Jersey", "Chicago", "Seattle"]},
    "contabo": {"name": "Contabo GmbH", "country": "DE", "cities": ["Munich", "Nuremberg"]},
    "leaseweb": {"name": "LeaseWeb", "country": "NL", "cities": ["Amsterdam", "Frankfurt", "Washington"]},
    "choopa": {"name": "The Constant Company/Vultr", "country": "US", "cities": ["Piscataway"]},
    "namecheap": {"name": "Namecheap, Inc", "country": "US", "cities": ["Phoenix"]},
    "godaddy": {"name": "GoDaddy.com LLC", "country": "US", "cities": ["Scottsdale"]},
    "amazon_aws": {"name": "Amazon.com Inc", "country": "US", "cities": ["Ashburn", "Dublin", "Frankfurt", "Singapore"]},
    "google_cloud": {"name": "Google LLC", "country": "US", "cities": ["Mountain View", "Council Bluffs"]},
    "microsoft_azure": {"name": "Microsoft Corporation", "country": "US", "cities": ["Redmond", "San Antonio"]},
    "oracle": {"name": "Oracle Corporation", "country": "US", "cities": ["Phoenix", "Ashburn"]},
    "kamatera": {"name": "Kamatera Inc", "country": "US", "cities": ["New York"]},
    "interserver": {"name": "Interserver Inc", "country": "US", "cities": ["Secaucus"]},
    "scaleway": {"name": "Scaleway SAS", "country": "FR", "cities": ["Paris", "Amsterdam"]},
    "upcloud": {"name": "UpCloud Ltd", "country": "FI", "cities": ["Helsinki"]},
    "kamatera_il": {"name": "Kamatera Israel", "country": "IL", "cities": ["Tel Aviv"]},
}


class ProxyPiercer:
    """Main engine for detecting and piercing through proxy/privacy layers."""

    def __init__(self):
        self.session = None
        self.results = {
            "domain": None,
            "privacy_detected": False,
            "privacy_type": None,
            "cdn_detected": False,
            "cdn_provider": None,
            "origin_ip": None,
            "real_hosting": None,
            "physical_location": None,
            "real_identity": None,
            "confidence": "LOW",
            "evidence": [],
            "methods_tried": [],
            "correlations": []
        }

    async def _get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "GFIN-Intelligence-Scanner/1.0"}
            )
        return self.session

    def add_evidence(self, method, finding, data=None, confidence="MEDIUM"):
        """Add evidence to the results."""
        self.results["evidence"].append({
            "method": method,
            "finding": finding,
            "data": data or {},
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.results["methods_tried"].append(method)

    def add_correlation(self, entity_type, entity_value, source_case, evidence):
        """Add a cross-case correlation."""
        self.results["correlations"].append({
            "entity_type": entity_type,
            "entity_value": entity_value,
            "source": source_case,
            "evidence": evidence
        })

    # ============================================================
    # 1. WHOIS PRIVACY DETECTION
    # ============================================================

    async def detect_whois_privacy(self, whois_data: dict) -> Dict:
        """Detect if WHOIS data uses a privacy/proxy service."""
        findings = {
            "is_privacy_protected": False,
            "privacy_service": None,
            "redacted_fields": [],
            "real_data_hints": []
        }

        # Check all WHOIS text fields for privacy service names
        whois_text = json.dumps(whois_data).lower()

        for service in PRIVACY_SERVICES:
            if service in whois_text:
                findings["is_privacy_protected"] = True
                findings["privacy_service"] = service.upper()
                self.results["privacy_detected"] = True
                self.results["privacy_type"] = "WHOIS_PRIVACY"
                self.add_evidence(
                    "WHOIS_PRIVACY_DETECTION",
                    f"Domain uses WHOIS privacy service: {service}",
                    {"service": service},
                    "HIGH"
                )
                break

        # Check for redacted/withheld fields
        redaction_patterns = [
            r"redacted for privacy",
            r"withheld for privacy",
            r"statutory masking",
            r"data redacted",
            r"please query the registrar",
            r"registration private",
            r"gdpr masked",
            r"not disclosed",
            r"redacted \| registry"
        ]

        for pattern in redaction_patterns:
            if re.search(pattern, whois_text):
                field = re.search(r'"(\w+)":\s*"[^"]*' + pattern, json.dumps(whois_data))
                field_name = field.group(1) if field else "unknown"
                if field_name not in findings["redacted_fields"]:
                    findings["redacted_fields"].append(field_name)
                self.add_evidence(
                    "WHOIS_REDACTION",
                    f"WHOIS field '{field_name}' redacted/withheld",
                    {"field": field_name, "pattern": pattern},
                    "MEDIUM"
                )

        # Look for real data hints that leaked through the privacy
        # Sometimes privacy services leak partial data
        for field in ["registrant_name", "registrant_email", "registrant_phone", "registrant_organization"]:
            val = whois_data.get(field, "")
            if val and not any(p in val.lower() for p in PRIVACY_SERVICES):
                if "@" in val or re.search(r'\+\d{1,4}', val) or not val.lower().startswith("redact"):
                    findings["real_data_hints"].append({"field": field, "value": val})
                    self.add_evidence(
                        "WHOIS_LEAKED_DATA",
                        f"Real data hint in {field}: {val}",
                        {"field": field, "value": val},
                        "HIGH"
                    )

        return findings

    # ============================================================
    # 2. HISTORICAL WHOIS LOOKUP
    # ============================================================

    async def lookup_historical_whois(self, domain: str) -> Dict:
        """Check historical WHOIS records before privacy was enabled."""
        findings = {"found": False, "records": [], "real_identity": None}

        # Try free historical WHOIS sources
        sources = [
            # RDAP — may show historical data
            f"https://rdap.org/domain/{domain}",
            # WhoisXML API (free tier)
            f"https://www.whoisxmlapi.com/whoisserver/WhoisService?domainName={domain}&outputFormat=json&da=1",
            # DNSdumpster for historical
            f"https://api.dnsdumpster.com/domain/{domain}",
        ]

        session = await self._get_session()

        # Try RDAP first
        try:
            async with session.get(f"https://rdap.org/domain/{domain}") as r:
                if r.status == 200:
                    rdap = await r.json()
                    events = rdap.get("events", [])
                    entities = rdap.get("entities", [])

                    for entity in entities:
                        roles = entity.get("roles", [])
                        vcard = entity.get("vcardArray", [])
                        if "registrant" in roles and vcard:
                            # Extract real registrant from vCard
                            for entry in vcard[1] if len(vcard) > 1 else []:
                                if entry[0] == "fn":
                                    name = entry[3]
                                    if name and not any(p in name.lower() for p in PRIVACY_SERVICES):
                                        findings["found"] = True
                                        findings["real_identity"] = {"name": name}
                                        self.results["real_identity"] = {"name": name, "source": "RDAP"}
                                        self.add_evidence(
                                            "HISTORICAL_WHOIS_RDAP",
                                            f"RDAP shows real registrant name: {name}",
                                            {"name": name},
                                            "HIGH"
                                        )

                        # Check for email in vCard
                        for entry in vcard[1] if len(vcard) > 1 else []:
                            if entry[0] == "email":
                                email = entry[3]
                                if email and "@" in email and not any(p in email.lower() for p in PRIVACY_SERVICES):
                                    findings["found"] = True
                                    if not findings.get("real_identity"):
                                        findings["real_identity"] = {}
                                    findings["real_identity"]["email"] = email
                                    self.add_evidence(
                                        "HISTORICAL_WHOIS_EMAIL",
                                        f"RDAP shows real registrant email: {email}",
                                        {"email": email},
                                        "HIGH"
                                    )
        except Exception:
            pass

        # Try whois.com scraping for historical data
        try:
            async with session.get(f"https://www.whois.com/whois/{domain}") as r:
                if r.status == 200:
                    text = await r.text()
                    # Look for dates before privacy was enabled
                    creation_dates = re.findall(r'(?:Created|Registered|Creation Date):\s*(\d{4}-\d{2}-\d{2})', text)
                    updated_dates = re.findall(r'(?:Updated|Changed):\s*(\d{4}-\d{2}-\d{2})', text)

                    # Look for non-redacted registrant info
                    registrant_match = re.search(r'Registrant[^:]*:\s*([^\n]+)', text)
                    if registrant_match:
                        val = registrant_match.group(1).strip()
                        if val and not any(p in val.lower() for p in PRIVACY_SERVICES):
                            findings["found"] = True
                            if not findings.get("real_identity"):
                                findings["real_identity"] = {}
                            findings["real_identity"]["name"] = val
                            self.add_evidence(
                                "HISTORICAL_WHOIS_SCRAPE",
                                f"WHOIS scrape shows non-redacted registrant: {val}",
                                {"name": val},
                                "MEDIUM"
                            )

                    # Look for real email
                    email_match = re.search(r'Registrant Email:\s*([^\s]+)', text)
                    if email_match:
                        email = email_match.group(1).strip()
                        if not any(p in email.lower() for p in PRIVACY_SERVICES) and "@" in email:
                            findings["found"] = True
                            if not findings.get("real_identity"):
                                findings["real_identity"] = {}
                            findings["real_identity"]["email"] = email
                            self.add_evidence(
                                "HISTORICAL_WHOIS_EMAIL",
                                f"WHOIS shows real email: {email}",
                                {"email": email},
                                "HIGH"
                            )
        except Exception:
            pass

        # Try Certificate Transparency logs for subdomains
        try:
            async with session.get(f"https://crt.sh/?q=%.{domain}&output=json") as r:
                if r.status == 200:
                    ct_data = await r.json()
                    subdomains = set()
                    for entry in ct_data[:100]:  # Limit
                        name_value = entry.get("name_value", "")
                        for name in name_value.split("\n"):
                            if domain in name and "*" not in name:
                                subdomains.add(name.strip())

                    if subdomains:
                        findings["subdomains"] = list(subdomains)[:20]
                        self.add_evidence(
                            "CT_LOG_SUBDOMAINS",
                            f"Certificate Transparency found {len(subdomains)} subdomains",
                            {"subdomains": list(subdomains)[:10]},
                            "MEDIUM"
                        )
                        # These subdomains may resolve to the origin IP
                        findings["subdomains_to_probe"] = list(subdomains)[:10]
        except Exception:
            pass

        return findings

    # ============================================================
    # 3. CDN / REVERSE PROXY DETECTION
    # ============================================================

    async def detect_cdn(self, domain: str, ip_info: dict = None) -> Dict:
        """Detect if the domain is behind a CDN/reverse proxy."""
        findings = {
            "is_cdn_protected": False,
            "cdn_provider": None,
            "cdn_indicators": [],
            "bypass_methods": []
        }

        session = await self._get_session()

        # Method 1: Check HTTP headers for CDN signatures
        try:
            async with session.get(f"https://{domain}", allow_redirects=True) as r:
                headers = dict(r.headers)

                for provider, info in CDN_PROVIDERS.items():
                    header_name = info.get("header", "")
                    if header_name and header_name.lower() in [h.lower() for h in headers]:
                        findings["is_cdn_protected"] = True
                        findings["cdn_provider"] = provider.upper()
                        findings["cdn_indicators"].append(f"HTTP header: {header_name}")
                        self.results["cdn_detected"] = True
                        self.results["cdn_provider"] = provider.upper()
                        findings["bypass_methods"] = info.get("methods_to_bypass", ["direct_dns"])
                        self.add_evidence(
                            "CDN_HEADER_DETECTION",
                            f"CDN detected via HTTP header: {header_name} → {provider}",
                            {"provider": provider, "header": header_name},
                            "HIGH"
                        )

                # Check Server header
                server_header = headers.get("server", "").lower()
                for provider, info in CDN_PROVIDERS.items():
                    for name in info["names"]:
                        if name in server_header:
                            if not findings["is_cdn_protected"]:
                                findings["is_cdn_protected"] = True
                                findings["cdn_provider"] = provider.upper()
                                self.results["cdn_detected"] = True
                                self.results["cdn_provider"] = provider.upper()
                            findings["cdn_indicators"].append(f"Server header: {server_header}")
                            findings["bypass_methods"] = info.get("methods_to_bypass", ["direct_dns"])
                            self.add_evidence(
                                "CDN_SERVER_HEADER",
                                f"CDN detected via Server header: {server_header}",
                                {"server": server_header, "provider": provider},
                                "HIGH"
                            )
                            break

                # Check for common CDN IP ranges in headers
                via_header = headers.get("via", "").lower()
                if via_header:
                    for provider, info in CDN_PROVIDERS.items():
                        for name in info["names"]:
                            if name in via_header:
                                if not findings["is_cdn_protected"]:
                                    findings["is_cdn_protected"] = True
                                    findings["cdn_provider"] = provider.upper()
                                findings["cdn_indicators"].append(f"Via header: {via_header}")
                                self.add_evidence(
                                    "CDN_VIA_HEADER",
                                    f"CDN detected via Via header: {via_header}",
                                    {"via": via_header, "provider": provider},
                                    "MEDIUM"
                                )
        except Exception:
            pass

        # Method 2: Check IP ASN against known CDN ASNs
        if ip_info and ip_info.get("asn"):
            asn = str(ip_info["asn"])
            for provider, info in CDN_PROVIDERS.items():
                if asn in info.get("asn_range", []):
                    if not findings["is_cdn_protected"]:
                        findings["is_cdn_protected"] = True
                        findings["cdn_provider"] = provider.upper()
                        self.results["cdn_detected"] = True
                        self.results["cdn_provider"] = provider.upper()
                    findings["cdn_indicators"].append(f"ASN {asn} belongs to {provider}")
                    findings["bypass_methods"] = info.get("methods_to_bypass", ["direct_dns"])
                    self.add_evidence(
                        "CDN_ASN_DETECTION",
                        f"IP ASN {asn} belongs to CDN provider: {provider}",
                        {"asn": asn, "provider": provider},
                        "HIGH"
                    )

        # Method 3: Check IP org name
        if ip_info and ip_info.get("org"):
            org = ip_info["org"].lower()
            for provider, info in CDN_PROVIDERS.items():
                for name in info["names"]:
                    if name in org:
                        if not findings["is_cdn_protected"]:
                            findings["is_cdn_protected"] = True
                            findings["cdn_provider"] = provider.upper()
                            self.results["cdn_detected"] = True
                            self.results["cdn_provider"] = provider.upper()
                        findings["cdn_indicators"].append(f"IP org: {ip_info['org']}")
                        self.add_evidence(
                            "CDN_ORG_DETECTION",
                            f"IP organization matches CDN: {provider}",
                            {"org": ip_info["org"], "provider": provider},
                            "MEDIUM"
                        )

        return findings

    # ============================================================
    # 4. ORIGIN IP DISCOVERY — find real IP behind CDN
    # ============================================================

    async def discover_origin_ip(self, domain: str, subdomains: List[str] = None) -> Dict:
        """Find the real origin IP hidden behind a CDN/proxy."""
        findings = {"found": False, "origin_ips": [], "methods_used": []}
        session = await self._get_session()

        # Method 1: DNS records that might leak origin
        # SPF records often include the real mail server IP
        try:
            resolver = socket.getaddrinfo
            # Try direct DNS resolution
            try:
                addrs = socket.getaddrinfo(domain, None)
                ips = list(set([a[4][0] for a in addrs]))
                for ip in ips:
                    if not self._is_cdn_ip(ip):
                        findings["found"] = True
                        findings["origin_ips"].append({"ip": ip, "method": "direct_dns"})
                        findings["methods_used"].append("direct_dns")
                        self.results["origin_ip"] = ip
                        self.add_evidence(
                            "ORIGIN_IP_DIRECT_DNS",
                            f"Direct DNS resolution found non-CDN IP: {ip}",
                            {"ip": ip, "method": "direct_dns"},
                            "HIGH"
                        )
            except Exception:
                pass
        except Exception:
            pass

        # Method 2: Check subdomains — often not behind CDN
        if subdomains:
            for sub in subdomains[:15]:
                try:
                    addrs = socket.getaddrinfo(sub, None)
                    for a in addrs:
                        ip = a[4][0]
                        if not self._is_cdn_ip(ip) and ip not in [r["ip"] for r in findings["origin_ips"]]:
                            findings["found"] = True
                            findings["origin_ips"].append({"ip": ip, "method": f"subdomain:{sub}"})
                            findings["methods_used"].append(f"subdomain_scan:{sub}")
                            self.results["origin_ip"] = ip
                            self.add_evidence(
                                "ORIGIN_IP_SUBDOMAIN",
                                f"Subdomain {sub} resolves to non-CDN IP: {ip}",
                                {"ip": ip, "subdomain": sub},
                                "HIGH"
                            )
                except Exception:
                    pass

        # Method 3: Check MX records — mail servers often reveal origin
        try:
            async with session.get(f"https://dns.google/resolve?name={domain}&type=MX") as r:
                if r.status == 200:
                    data = await r.json()
                    for answer in data.get("Answer", []):
                        mx_data = answer.get("data", "")
                        # Extract hostname from MX record
                        mx_host = re.sub(r'^\d+\s+', '', mx_data).rstrip(".")
                        if mx_host and not any(cdn in mx_host.lower() for cdn in ["cloudflare", "google", "outlook", "microsoft", "proton", "zoho"]):
                            try:
                                mx_addrs = socket.getaddrinfo(mx_host, None)
                                for a in mx_addrs:
                                    ip = a[4][0]
                                    if ip not in [r["ip"] for r in findings["origin_ips"]]:
                                        findings["found"] = True
                                        findings["origin_ips"].append({"ip": ip, "method": f"mx_record:{mx_host}"})
                                        findings["methods_used"].append("mx_record")
                                        self.results["origin_ip"] = ip
                                        self.add_evidence(
                                            "ORIGIN_IP_MX",
                                            f"MX record {mx_host} resolves to: {ip}",
                                            {"ip": ip, "mx_host": mx_host},
                                            "HIGH"
                                        )
                            except Exception:
                                pass
        except Exception:
            pass

        # Method 4: Check TXT/SPF records for IP ranges
        try:
            async with session.get(f"https://dns.google/resolve?name={domain}&type=TXT") as r:
                if r.status == 200:
                    data = await r.json()
                    for answer in data.get("Answer", []):
                        txt = answer.get("data", "")
                        # SPF records contain IP ranges: v=spf1 ip4:1.2.3.4
                        spf_ips = re.findall(r'ip4:(\d+\.\d+\.\d+\.\d+)', txt)
                        for ip in spf_ips:
                            if not self._is_cdn_ip(ip) and ip not in [r["ip"] for r in findings["origin_ips"]]:
                                findings["found"] = True
                                findings["origin_ips"].append({"ip": ip, "method": "spf_record"})
                                findings["methods_used"].append("spf_record")
                                self.results["origin_ip"] = ip
                                self.add_evidence(
                                    "ORIGIN_IP_SPF",
                                    f"SPF record reveals origin IP: {ip}",
                                    {"ip": ip, "method": "spf_record"},
                                    "HIGH"
                                )

                        # Also check for include: references that might leak hosting
                        includes = re.findall(r'include:([^\s]+)', txt)
                        for inc in includes:
                            try:
                                inc_addrs = socket.getaddrinfo(inc, None)
                                for a in inc_addrs:
                                    ip = a[4][0]
                                    if not self._is_cdn_ip(ip) and ip not in [r["ip"] for r in findings["origin_ips"]]:
                                        findings["found"] = True
                                        findings["origin_ips"].append({"ip": ip, "method": f"spf_include:{inc}"})
                                        self.add_evidence(
                                            "ORIGIN_IP_SPF_INCLUDE",
                                            f"SPF include {inc} resolves to: {ip}",
                                            {"ip": ip, "include": inc},
                                            "MEDIUM"
                                        )
                            except Exception:
                                pass
        except Exception:
            pass

        # Method 5: Try common subdomains that are often not proxied
        common_subs = ["mail", "ftp", "cpanel", "webmail", "autodiscover", "direct", "origin",
                      "staging", "dev", "test", "api", "ssh", "vpn", "remote", "server1",
                      "panel", "admin", "direct-connect", "ns1", "ns2"]
        for sub in common_subs:
            subdomain = f"{sub}.{domain}"
            try:
                addrs = socket.getaddrinfo(subdomain, None)
                for a in addrs:
                    ip = a[4][0]
                    if not self._is_cdn_ip(ip) and ip not in [r["ip"] for r in findings["origin_ips"]]:
                        findings["found"] = True
                        findings["origin_ips"].append({"ip": ip, "method": f"common_sub:{subdomain}"})
                        findings["methods_used"].append(f"common_sub:{sub}")
                        self.results["origin_ip"] = ip
                        self.add_evidence(
                            "ORIGIN_IP_COMMON_SUB",
                            f"Common subdomain {subdomain} resolves to non-CDN IP: {ip}",
                            {"ip": ip, "subdomain": subdomain},
                            "HIGH"
                        )
            except Exception:
                pass

        # Method 6: SecurityTrails / Shodan-style historical DNS (free APIs)
        try:
            # Try hackertarget for historical DNS
            async with session.get(f"https://api.hackertarget.com/reverseiplookup/?q={domain}") as r:
                if r.status == 200:
                    text = await r.text()
                    if "error" not in text.lower() and text.strip():
                        ips = [ip.strip() for ip in text.split(",") if re.match(r'\d+\.\d+\.\d+\.\d+', ip.strip())]
                        for ip in ips[:5]:
                            if not self._is_cdn_ip(ip) and ip not in [r["ip"] for r in findings["origin_ips"]]:
                                findings["found"] = True
                                findings["origin_ips"].append({"ip": ip, "method": "reverse_ip_lookup"})
                                self.add_evidence(
                                    "ORIGIN_IP_REVERSE_LOOKUP",
                                    f"Reverse IP lookup found: {ip}",
                                    {"ip": ip, "method": "reverse_ip_lookup"},
                                    "MEDIUM"
                                )
        except Exception:
            pass

        return findings

    def _is_cdn_ip(self, ip: str) -> bool:
        """Check if an IP belongs to a known CDN range (IPv4 and IPv6)."""
        # Skip IPv6 for now — most CDN IPv6 is hard to filter
        if ":" in ip:
            # Cloudflare IPv6 ranges start with 2606:4700
            if ip.startswith("2606:4700"):
                return True
            # Sucuri IPv6
            if ip.startswith("2a02:2658") or ip.startswith("2a00:1428"):
                return True
            return False

        # Full Cloudflare IPv4 ranges
        # https://www.cloudflare.com/ips/
        cloudflare_ranges = [
            (1735499008, 1735700479),    # 103.21.244.0/22
            (1735749632, 1735752703),    # 103.22.200.0/22
            (1735794688, 1735798783),    # 103.31.4.0/22
            (1740595200, 1740867327),    # 104.16.0.0/13
            (1745813504, 1745815551),    # 104.24.0.0/14 — covers 104.21-104.31
            (2886729728, 2886785279),    # 172.64.0.0/13
            (2438148096, 2438213631),    # 141.101.64.0/18
            (2725615616, 2725615631),    # 108.162.192.0/18  
            (2729525248, 2729529343),    # 162.158.0.0/15
            (3130243072, 3130425343),    # 188.114.96.0/20
            (3252973568, 3252974079),    # 197.234.240.0/22
            (3351251968, 3351251968),    # 198.41.128.0
        ]
        
        # Also detect Sucuri (192.124.249.0/24, 192.96.55.0/24)
        sucuri_ranges = [
            (3231027200, 3231027455),    # 192.124.249.0/24
            (3229732864, 3229733119),    # 192.96.55.0/24
        ]
        
        # Incapsula
        incapsula_ranges = [
            (2893021184, 2893025279),    # 172.200.0.0/16-ish
        ]

        try:
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            ip_int = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

            # Check all CDN ranges
            for start, end in cloudflare_ranges + sucuri_ranges + incapsula_ranges:
                if start <= ip_int <= end:
                    return True
                    
            # Also check by org name pattern in the IP itself
            # Cloudflare IPs: 104.16-31.x.x, 172.64-71.x.x, 162.158-159.x.x
            if parts[0] == "104" and 16 <= int(parts[1]) <= 31:
                return True
            if parts[0] == "172" and 64 <= int(parts[1]) <= 71:
                return True
            if parts[0] == "162" and parts[1] in ["158", "159"]:
                return True
            if parts[0] == "188" and 96 <= int(parts[1]) <= 111:
                return True
            if parts[0] == "103" and parts[1] in ["21", "22", "31"]:
                return True
            if parts[0] == "141" and parts[1] == "101":
                return True
            if parts[0] == "108" and parts[1] == "162":
                return True
        except Exception:
            pass

        return False

    # ============================================================
    # 5. PHYSICAL LOCATION TRACING
    # ============================================================

    async def trace_physical_location(self, ip: str) -> Dict:
        """Trace an IP to its physical data center location."""
        findings = {"ip": ip, "location": None, "hosting_provider": None, "datacenter": None}
        session = await self._get_session()

        # Use ipinfo.io for geolocation (free, no key)
        try:
            async with session.get(f"https://ipinfo.io/{ip}/json") as r:
                if r.status == 200:
                    data = await r.json()
                    findings["location"] = {
                        "city": data.get("city"),
                        "region": data.get("region"),
                        "country": data.get("country"),
                        "lat": data.get("loc", "").split(",")[0] if data.get("loc") else None,
                        "lon": data.get("loc", "").split(",")[1] if data.get("loc") else None,
                        "timezone": data.get("timezone"),
                        "postal": data.get("postal"),
                    }
                    findings["hosting_provider"] = {
                        "org": data.get("org"),
                        "asn": data.get("org", "").split()[0] if "AS" in data.get("org", "") else None,
                    }

                    # Match to known hosting provider
                    org = data.get("org", "").lower()
                    for key, provider in HOSTING_PROVIDERS.items():
                        if key in org or provider["name"].lower() in org:
                            findings["datacenter"] = provider
                            self.add_evidence(
                                "PHYSICAL_LOCATION",
                                f"Origin IP {ip} → {provider['name']}, {provider['country']} ({', '.join(provider['cities'])}",
                                {"ip": ip, "provider": provider["name"], "country": provider["country"], "city": findings["location"].get("city")},
                                "HIGH"
                            )
                            break
                    else:
                        self.add_evidence(
                            "PHYSICAL_LOCATION",
                            f"Origin IP {ip} → {data.get('org')}, {data.get('city')}, {data.get('country')}",
                            {"ip": ip, "org": data.get("org"), "city": data.get("city"), "country": data.get("country")},
                            "MEDIUM"
                        )

                    self.results["physical_location"] = findings["location"]
                    self.results["real_hosting"] = findings["hosting_provider"]
        except Exception:
            pass

        # Also try ip-api.com for more detail (free, no key)
        try:
            async with session.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,hosting") as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get("status") == "success":
                        if not findings["location"]:
                            findings["location"] = {
                                "city": data.get("city"),
                                "region": data.get("regionName"),
                                "country": data.get("countryCode"),
                                "lat": str(data.get("lat", "")),
                                "lon": str(data.get("lon", "")),
                                "timezone": data.get("timezone"),
                                "postal": data.get("zip"),
                            }

                        # Check if it's a hosting provider
                        isp = (data.get("isp") or "").lower()
                        org = (data.get("org") or "").lower()
                        asname = (data.get("asname") or "").lower()

                        for key, provider in HOSTING_PROVIDERS.items():
                            if key in isp or key in org or provider["name"].lower() in org:
                                if not findings["datacenter"]:
                                    findings["datacenter"] = provider
                                self.add_evidence(
                                    "HOSTING_PROVIDER",
                                    f"Hosting provider identified: {provider['name']} ({provider['country']})",
                                    {"provider": provider["name"], "country": provider["country"], "isp": data.get("isp")},
                                    "HIGH"
                                )
                                break

                        # Flag if the IP is flagged as hosting
                        if data.get("hosting"):
                            self.add_evidence(
                                "HOSTING_FLAG",
                                f"IP {ip} is confirmed as a hosting/server IP",
                                {"ip": ip, "hosting": True},
                                "MEDIUM"
                            )
        except Exception:
            pass

        return findings

    # ============================================================
    # 6. REGISTRAR CORRELATION
    # ============================================================

    async def correlate_registrar(self, domain: str, whois_data: dict) -> Dict:
        """Correlate registrar and registration patterns across domains."""
        findings = {"registrar": None, "registration_patterns": [], "correlated_domains": []}

        registrar = whois_data.get("registrar", "")
        if registrar:
            findings["registrar"] = registrar
            self.add_evidence(
                "REGISTRAR_INFO",
                f"Domain registered via: {registrar}",
                {"registrar": registrar},
                "MEDIUM"
            )

        # Check registration date patterns
        created = whois_data.get("created_date", "")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", ""))
                days_old = (datetime.utcnow() - created_dt).days
                if days_old < 7:
                    self.add_evidence(
                        "NEWLY_REGISTERED",
                        f"Domain registered only {days_old} days ago — likely scam",
                        {"days_old": days_old, "created": created},
                        "HIGH"
                    )
                elif days_old < 30:
                    self.add_evidence(
                        "RECENTLY_REGISTERED",
                        f"Domain registered {days_old} days ago — suspicious",
                        {"days_old": days_old, "created": created},
                        "MEDIUM"
                    )
            except Exception:
                pass

        return findings

    # ============================================================
    # 7. EMAIL/PHONE CORRELATION
    # ============================================================

    async def correlate_contact_info(self, domain: str, whois_data: dict, db_conn=None) -> Dict:
        """Match leaked email/phone across domain registrations to find operator."""
        findings = {"emails": [], "phones": [], "correlations": []}

        # Extract any real emails from WHOIS
        all_text = json.dumps(whois_data)
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', all_text)
        phones = re.findall(r'\+\d{1,4}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}', all_text)

        # Filter out privacy service emails
        real_emails = [e for e in emails if not any(p in e.lower() for p in PRIVACY_SERVICES + ["abuse", "support", "contact"])]
        real_phones = [p for p in phones if len(re.sub(r'\D', '', p)) > 8]

        for email in real_emails[:5]:
            findings["emails"].append(email)
            self.add_evidence(
                "CONTACT_EMAIL_FOUND",
                f"Real email found in WHOIS: {email}",
                {"email": email},
                "HIGH"
            )

            # Search database for same email in other cases
            if db_conn:
                try:
                    matches = await db_conn.fetch(
                        "SELECT case_id, entity_value FROM case_entities WHERE entity_type = 'EMAIL' AND entity_value = $1",
                        email
                    )
                    for m in matches:
                        findings["correlations"].append({
                            "type": "EMAIL",
                            "value": email,
                            "correlated_case": m["case_id"]
                        })
                        self.add_correlation("EMAIL", email, m["case_id"], f"Same email used in {m['case_id']}")
                except Exception:
                    pass

        for phone in real_phones[:5]:
            findings["phones"].append(phone)
            self.add_evidence(
                "CONTACT_PHONE_FOUND",
                f"Real phone found in WHOIS: {phone}",
                {"phone": phone},
                "HIGH"
            )

        return findings

    # ============================================================
    # 8. SSL CERTIFICATE PIVOT
    # ============================================================

    async def ssl_cert_pivot(self, domain: str) -> Dict:
        """Find other domains sharing the same SSL certificate."""
        findings = {"shared_cert_domains": [], "cert_fingerprint": None}
        session = await self._get_session()

        # Query crt.sh for certificate history
        try:
            async with session.get(f"https://crt.sh/?q={domain}&output=json") as r:
                if r.status == 200:
                    certs = await r.json()
                    cert_ids = set()
                    for cert in certs[:50]:
                        cert_ids.add(cert.get("id"))

                    # For each cert, find other domains on the same cert
                    for cert_id in list(cert_ids)[:5]:
                        try:
                            async with session.get(f"https://crt.sh/?d={cert_id}&output=json") as r2:
                                if r2.status == 200:
                                    shared = await r2.json()
                                    for s in shared[:20]:
                                        name = s.get("name_value", "")
                                        if name and domain not in name and "*" not in name:
                                            if name not in findings["shared_cert_domains"]:
                                                findings["shared_cert_domains"].append(name)
                                                self.add_evidence(
                                                    "SSL_CERT_PIVOT",
                                                    f"Domain {name} shares SSL certificate with {domain}",
                                                    {"shared_domain": name, "cert_id": cert_id},
                                                    "HIGH"
                                                )
                        except Exception:
                            pass
        except Exception:
            pass

        return findings

    # ============================================================
    # MAIN INVESTIGATION PIPELINE
    # ============================================================

    async def investigate(self, domain: str, whois_data: dict = None, db_conn=None) -> Dict:
        """Run full proxy/privacy piercing investigation on a domain."""
        self.results["domain"] = domain
        self.results["privacy_detected"] = False
        self.results["cdn_detected"] = False

        # Step 1: WHOIS Privacy Detection
        if whois_data:
            await self.detect_whois_privacy(whois_data)
            await self.correlate_registrar(domain, whois_data)
            await self.correlate_contact_info(domain, whois_data, db_conn)
        else:
            # Fetch WHOIS data
            whois_data = await self._fetch_whois(domain)
            if whois_data:
                await self.detect_whois_privacy(whois_data)
                await self.correlate_registrar(domain, whois_data)
                await self.correlate_contact_info(domain, whois_data, db_conn)

        # Step 2: Historical WHOIS Lookup (find pre-privacy records)
        historical = await self.lookup_historical_whois(domain)
        subdomains_to_probe = historical.get("subdomains_to_probe", [])

        # Step 3: Resolve domain to IP
        ip_info = {}
        primary_ip = None
        try:
            addrs = socket.getaddrinfo(domain, None)
            primary_ip = addrs[0][4][0]
            # Get IP info
            session = await self._get_session()
            async with session.get(f"https://ipinfo.io/{primary_ip}/json") as r:
                if r.status == 200:
                    ip_info = await r.json()
        except Exception:
            pass

        # Step 4: CDN Detection
        cdn_findings = await self.detect_cdn(domain, ip_info)

        # Step 5: Origin IP Discovery (if CDN detected)
        if cdn_findings["is_cdn_protected"]:
            origin = await self.discover_origin_ip(domain, subdomains_to_probe)
            if origin["found"]:
                for origin_entry in origin["origin_ips"]:
                    # Step 6: Trace physical location of origin IP
                    location = await self.trace_physical_location(origin_entry["ip"])
        else:
            # No CDN — direct IP is the origin
            if primary_ip and primary_ip is not None:
                self.results["origin_ip"] = primary_ip
                self.add_evidence(
                    "DIRECT_IP",
                    f"Domain resolves directly to {primary_ip} (no CDN)",
                    {"ip": primary_ip},
                    "HIGH"
                )
                location = await self.trace_physical_location(primary_ip)

        # Step 7: SSL Certificate Pivot
        ssl_pivot = await self.ssl_cert_pivot(domain)

        # Calculate overall confidence
        evidence_count = len(self.results["evidence"])
        high_count = sum(1 for e in self.results["evidence"] if e["confidence"] == "HIGH")
        if high_count >= 3:
            self.results["confidence"] = "HIGH"
        elif high_count >= 1 or evidence_count >= 3:
            self.results["confidence"] = "MEDIUM"
        else:
            self.results["confidence"] = "LOW"

        # Summary
        self.results["summary"] = self._generate_summary()
        self.results["investigated_at"] = datetime.utcnow().isoformat()

        if self.session:
            await self.session.close()

        return self.results

    async def _fetch_whois(self, domain: str) -> dict:
        """Fetch WHOIS data via free API."""
        session = await self._get_session()
        try:
            async with session.get(f"https://rdap.org/domain/{domain}") as r:
                if r.status == 200:
                    rdap = await r.json()
                    whois = {}
                    for entity in rdap.get("entities", []):
                        roles = entity.get("roles", [])
                        vcard = entity.get("vcardArray", [[]])
                        if "registrant" in roles and len(vcard) > 1:
                            for entry in vcard[1]:
                                if entry[0] == "fn":
                                    whois["registrant_name"] = entry[3]
                                elif entry[0] == "email":
                                    whois["registrant_email"] = entry[3]
                                elif entry[0] == "tel":
                                    whois["registrant_phone"] = entry[3]

                    # Get dates from events
                    for event in rdap.get("events", []):
                        if event.get("eventAction") == "registration":
                            whois["created_date"] = event.get("eventDate")
                        elif event.get("eventAction") == "last changed":
                            whois["updated_date"] = event.get("eventDate")

                    return whois
        except Exception:
            pass
        return {}

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of findings."""
        parts = []

        if self.results["privacy_detected"]:
            parts.append(f"WHOIS privacy service detected ({self.results['privacy_type']}).")

        if self.results["cdn_detected"]:
            parts.append(f"Domain is behind CDN ({self.results['cdn_provider']}).")

        if self.results["origin_ip"]:
            parts.append(f"Real origin IP discovered: {self.results['origin_ip']}.")

        if self.results["physical_location"]:
            loc = self.results["physical_location"]
            parts.append(f"Physical location: {loc.get('city', 'unknown')}, {loc.get('country', 'unknown')}.")

        if self.results["real_identity"]:
            ident = self.results["real_identity"]
            if ident.get("name"):
                parts.append(f"Real registrant name: {ident['name']}.")
            if ident.get("email"):
                parts.append(f"Real registrant email: {ident['email']}.")

        if self.results["correlations"]:
            parts.append(f"Found {len(self.results['correlations'])} cross-case correlations.")

        if not parts:
            return "No proxy/privacy protection detected. Domain appears to use direct hosting."

        return " ".join(parts)

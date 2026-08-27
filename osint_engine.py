"""
GFIN OSINT Engine Integration v1.0
Wraps GitHub open-source intelligence tools into unified API endpoints:
- SpiderFoot (200+ OSINT modules)
- DNSTwist (typo-squatting detection)
- Shodan (internet-connected device search)
- WAFW00F (WAF detection)
- DNSRecon (DNS enumeration)
- python-whois (WHOIS lookup)
- ProxyPiercer (proxy/privacy piercing)
"""

import asyncio
import subprocess
import json
import time
import re
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================
# OSINT ENGINE WRAPPERS
# ============================================================

async def run_spiderfoot_scan(target: str, modules: List[str] = None, timeout: int = 120) -> Dict:
    """Run SpiderFoot scan on a target domain/IP/email."""
    results = {
        "engine": "SpiderFoot",
        "target": target,
        "modules_used": [],
        "findings": [],
        "summary": {},
        "errors": []
    }

    try:
        # SpiderFoot CLI: sf.py -m <modules> -t <target> -s
        sf_path = "/opt/spiderfoot/sf.py"
        
        # Default to most useful modules for fraud investigation
        if not modules:
            modules = [
                "sfp_whois",              # WHOIS records
                "sfp_dnsresolve",         # DNS resolution
                "sfp_subdomains",         # Subdomain enumeration
                "sfp_ipinfo",            # IP geolocation
                "sfp_sslcert",           # SSL certificate analysis
                "sfp_hackertarget",      # HackerTarget API
                "sfp_whatweb",           # Web technology fingerprinting
                "sfp_blocklist",         # Check against blocklists
                "sfp_abuseipdb",         # AbuseIPDB check (free)
                "sfp_bitcoinabuse",       # Bitcoin abuse check (free)
                "sfp_archiveorg",         # Wayback Machine
                "sfp_bing",              # Bing search
                "sfp_dnsbrute",          # DNS brute force
                "sfp_emailformat",       # Email format validation
                "sfp_honeypot",          # Honeypot detection
                "sfp_rir",               # RIR (regional internet registry)
                "sfp_securitytrails",    # SecurityTrails (free tier)
            ]

        results["modules_used"] = modules
        module_str = ",".join(modules)
        
        # Run SpiderFoot scan
        cmd = [
            sys.executable, sf_path,
            "-m", module_str,
            "-t", target,
            "-s",  # Use SQLite for output
            "-q",  # Quiet mode
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/opt/spiderfoot"
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            
            if err and "warning" not in err.lower():
                results["errors"].append(err[:500])

            # Parse SpiderFoot output
            # SpiderFoot outputs scan results in a table format
            lines = output.strip().split("\n")
            for line in lines:
                if "|" in line and not line.startswith("=") and not line.startswith("-"):
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        results["findings"].append({
                            "module": parts[0],
                            "type": parts[1],
                            "data": "|".join(parts[2:])[:500]
                        })

        except asyncio.TimeoutError:
            proc.kill()
            results["errors"].append(f"SpiderFoot scan timed out after {timeout}s")
            
    except Exception as e:
        results["errors"].append(str(e))

    results["summary"] = {
        "total_findings": len(results["findings"]),
        "modules_run": len(results["modules_used"]),
        "errors": len(results["errors"])
    }

    return results


async def run_dnstwist_scan(domain: str, timeout: int = 30) -> Dict:
    """Run DNSTwist to find typo-squatting and lookalike domains."""
    results = {
        "engine": "DNSTwist",
        "target": domain,
        "findings": [],
        "summary": {},
        "errors": []
    }

    try:
        cmd = [sys.executable, "-m", "dnstwist", "-r", "-f", "json", domain]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            
            if err:
                results["errors"].append(err[:500])

            # Parse JSON output
            try:
                data = json.loads(output)
                for entry in data:
                    if entry.get("domain") != domain:  # Skip the original domain
                        results["findings"].append({
                            "domain": entry.get("domain"),
                            "dns_a": entry.get("dns_a", []),
                            "dns_mx": entry.get("dns_mx", []),
                            "fuzzer": entry.get("fuzzer", ""),
                            "ssdeep": entry.get("ssdeep", "")
                        })
            except json.JSONDecodeError:
                # Try line by line
                for line in output.strip().split("\n"):
                    try:
                        entry = json.loads(line)
                        if entry.get("domain") != domain:
                            results["findings"].append(entry)
                    except:
                        pass

        except asyncio.TimeoutError:
            proc.kill()
            results["errors"].append(f"DNSTwist timed out after {timeout}s")

    except Exception as e:
        results["errors"].append(str(e))

    results["summary"] = {
        "total_lookalikes": len(results["findings"]),
        "with_dns_records": sum(1 for f in results["findings"] if f.get("dns_a")),
        "errors": len(results["errors"])
    }

    return results


async def run_shodan_lookup(ip: str) -> Dict:
    """Look up an IP address in Shodan (free tier — no API key needed for basic info)."""
    results = {
        "engine": "Shodan",
        "target": ip,
        "findings": {},
        "errors": []
    }

    try:
        import shodan
        
        # Free API — no key needed for host lookup via REST
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Use Shodan's free REST API
            async with session.get(f"https://api.shodan.io/shodan/host/{ip}") as r:
                if r.status == 200:
                    data = await r.json()
                    results["findings"] = {
                        "ip": data.get("ip_str"),
                        "org": data.get("org"),
                        "isp": data.get("isp"),
                        "asn": data.get("asn"),
                        "hostnames": data.get("hostnames", []),
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "city": data.get("city"),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "os": data.get("os"),
                        "ports": data.get("ports", []),
                        "services": [
                            {"port": s.get("port"), "service": s.get("transport"), 
                             "product": s.get("product"), "version": s.get("version"),
                             "banner": (s.get("data", "") or "")[:200]}
                            for s in data.get("data", [])
                        ],
                        "vulns": data.get("vulns", []),
                        "tags": data.get("tags", []),
                        "last_update": data.get("last_update")
                    }
                elif r.status == 404:
                    results["findings"] = {"ip": ip, "note": "No Shodan data available for this IP"}
                elif r.status == 401:
                    results["findings"] = {"ip": ip, "note": "Shodan API key required for detailed results. Basic info available via free tier with API key."}
                    # Try ipinfo.io as fallback (always free)
                    async with session.get(f"https://ipinfo.io/{ip}/json") as r2:
                        if r2.status == 200:
                            data = await r2.json()
                            results["findings"] = {
                                "ip": ip,
                                "fallback": "ipinfo.io",
                                "org": data.get("org"),
                                "city": data.get("city"),
                                "country": data.get("country"),
                                "region": data.get("region"),
                                "location": data.get("loc"),
                                "timezone": data.get("timezone")
                            }
                else:
                    results["errors"].append(f"Shodan API returned {r.status}")
                    
    except Exception as e:
        results["errors"].append(str(e))

    return results


async def run_wafw00f_check(domain: str) -> Dict:
    """Check if a website is protected by a WAF (Web Application Firewall)."""
    results = {
        "engine": "WAFW00F",
        "target": domain,
        "findings": {},
        "errors": []
    }

    try:
        cmd = ["wafw00f", f"https://{domain}"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stdout.decode("utf-8", errors="replace")
            
            # Parse WAFW00F output
            waf_match = re.search(r'is behind\s+(.+)', output)
            if waf_match:
                waf_name = waf_match.group(1).strip()
                results["findings"] = {
                    "waf_detected": True,
                    "waf_name": waf_name,
                    "raw_output": output[:500]
                }
            else:
                if "no WAF" in output.lower() or "not behind" in output.lower():
                    results["findings"] = {"waf_detected": False, "note": "No WAF detected"}
                else:
                    results["findings"] = {"waf_detected": False, "raw_output": output[:500]}

        except asyncio.TimeoutError:
            proc.kill()
            results["errors"].append("WAFW00F timed out")

    except Exception as e:
        results["errors"].append(str(e))

    return results


async def run_dnsrecon(domain: str) -> Dict:
    """Run DNS enumeration on a domain."""
    results = {
        "engine": "DNSRecon",
        "target": domain,
        "findings": {"records": [], "subdomains": []},
        "errors": []
    }

    try:
        cmd = ["dnsrecon", "-d", domain, "-t", "std,brt", "--lifetime", "5"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            output = stdout.decode("utf-8", errors="replace")
            
            for line in output.strip().split("\n"):
                if "\t" in line:
                    parts = [p.strip() for p in line.split("\t")]
                    if len(parts) >= 3:
                        record = {
                            "type": parts[0],
                            "host": parts[1],
                            "value": parts[2] if len(parts) > 2 else "",
                        }
                        results["findings"]["records"].append(record)
                        if parts[0] == "A" and parts[1] != domain:
                            results["findings"]["subdomains"].append({
                                "subdomain": parts[1],
                                "ip": parts[2]
                            })

        except asyncio.TimeoutError:
            proc.kill()
            results["errors"].append("DNSRecon timed out (60s)")

    except Exception as e:
        results["errors"].append(str(e))

    results["summary"] = {
        "total_records": len(results["findings"]["records"]),
        "subdomains_found": len(results["findings"]["subdomains"])
    }

    return results


async def run_whois_lookup(domain: str) -> Dict:
    """Full WHOIS lookup using python-whois."""
    results = {
        "engine": "python-whois",
        "target": domain,
        "findings": {},
        "errors": []
    }

    try:
        import whois
        w = whois.whois(domain)
        results["findings"] = {
            "domain": w.domain,
            "registrar": w.registrar,
            "registrant_name": w.name,
            "registrant_email": w.email if isinstance(w.email, str) else (w.email[0] if w.email else None),
            "registrant_org": w.org,
            "creation_date": str(w.creation_date) if w.creation_date else None,
            "expiration_date": str(w.expiration_date) if w.expiration_date else None,
            "updated_date": str(w.updated_date) if w.updated_date else None,
            "name_servers": w.name_servers if w.name_servers else [],
            "status": w.status if w.status else [],
            "country": w.country,
            "state": w.state,
            "city": w.city,
            "address": w.address,
            "phone": w.phone,
            "dnssec": w.dnssec,
        }
        
        # Check for privacy protection
        all_text = json.dumps(results["findings"]).lower()
        privacy_keywords = ["privacy", "redacted", "withheld", "whoisguard", "domains by proxy", "proxy"]
        results["findings"]["privacy_protected"] = any(kw in all_text for kw in privacy_keywords)
        
    except Exception as e:
        results["errors"].append(str(e))

    return results


# ============================================================
# UNIFIED FULL OSINT SCAN
# ============================================================

async def run_full_osint_scan(target: str, target_type: str = "domain") -> Dict:
    """Run all OSINT engines against a target and merge results."""
    scan_id = f"OSINT-{int(time.time())}"
    results = {
        "scan_id": scan_id,
        "target": target,
        "target_type": target_type,
        "started_at": datetime.utcnow().isoformat(),
        "engines": {},
        "correlations": [],
        "confidence": "LOW",
        "summary": ""
    }

    # Run all engines in parallel
    tasks = {}
    
    if target_type == "domain":
        tasks["whois"] = run_whois_lookup(target)
        tasks["dnstwist"] = run_dnstwist_scan(target)
        tasks["wafw00f"] = run_wafw00f_check(target)
        tasks["dnsrecon"] = run_dnsrecon(target)
        tasks["spiderfoot"] = run_spiderfoot_scan(target, timeout=90)
        
    elif target_type == "ip":
        tasks["shodan"] = run_shodan_lookup(target)
        tasks["spiderfoot"] = run_spiderfoot_scan(target, timeout=90)

    # Execute all in parallel
    engine_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    for (name, _), result in zip(tasks.items(), engine_results):
        if isinstance(result, Exception):
            results["engines"][name] = {"error": str(result)}
        else:
            results["engines"][name] = result

    # Generate correlations
    correlations = []
    
    # Correlation: If DNSTwist found lookalike domains with same IP as target
    dnstwist_data = results["engines"].get("dnstwist", {})
    if dnstwist_data.get("findings"):
        for finding in dnstwist_data["findings"][:5]:
            if finding.get("dns_a"):
                correlations.append({
                    "type": "TYPOSQUAT_LIVE",
                    "description": f"Lookalike domain {finding['domain']} resolves to {finding.get('dns_a', ['?'])[0]}",
                    "severity": "HIGH"
                })
    
    # Correlation: If WAF detected, note it
    wafw00f_data = results["engines"].get("wafw00f", {})
    if wafw00f_data.get("findings", {}).get("waf_detected"):
        correlations.append({
            "type": "WAF_PROTECTED",
            "description": f"Site behind WAF: {wafw00f_data['findings'].get('waf_name', 'unknown')}",
            "severity": "MEDIUM"
        })
    
    # Correlation: If WHOIS shows privacy protection
    whois_data = results["engines"].get("whois", {})
    if whois_data.get("findings", {}).get("privacy_protected"):
        correlations.append({
            "type": "PRIVACY_PROTECTED",
            "description": "Domain uses WHOIS privacy protection — registrant identity hidden",
            "severity": "MEDIUM"
        })
    
    # Correlation: DNS records showing CDN
    dnsrecon_data = results["engines"].get("dnsrecon", {})
    for record in dnsrecon_data.get("findings", {}).get("records", []):
        if record.get("value") and any(cdn in record["value"].lower() for cdn in ["cloudflare", "akamai", "incapsula", "sucuri"]):
            correlations.append({
                "type": "CDN_DETECTED",
                "description": f"DNS shows CDN: {record['value']}",
                "severity": "MEDIUM"
            })
    
    results["correlations"] = correlations
    
    # Calculate confidence
    engine_count = len([e for e in results["engines"].values() if not e.get("error")])
    finding_count = sum(len(e.get("findings", [])) if isinstance(e.get("findings"), list) else (1 if e.get("findings") else 0) for e in results["engines"].values())
    correlation_count = len(correlations)
    
    if correlation_count >= 3 and finding_count >= 10:
        results["confidence"] = "HIGH"
    elif correlation_count >= 1 or finding_count >= 5:
        results["confidence"] = "MEDIUM"
    else:
        results["confidence"] = "LOW"
    
    # Generate summary
    summary_parts = [f"Ran {engine_count} OSINT engines against {target}."]
    if dnstwist_data.get("summary", {}).get("total_lookalikes"):
        summary_parts.append(f"Found {dnstwist_data['summary']['total_lookalikes']} typo-squatting domains.")
    if wafw00f_data.get("findings", {}).get("waf_detected"):
        summary_parts.append(f"Site protected by WAF: {wafw00f_data['findings'].get('waf_name', 'unknown')}.")
    if whois_data.get("findings", {}).get("privacy_protected"):
        summary_parts.append("Domain uses WHOIS privacy protection.")
    if dnsrecon_data.get("summary", {}).get("subdomains_found"):
        summary_parts.append(f"Found {dnsrecon_data['summary']['subdomains_found']} subdomains.")
    if correlations:
        summary_parts.append(f"Generated {len(correlations)} intelligence correlations.")
    
    results["summary"] = " ".join(summary_parts)
    results["completed_at"] = datetime.utcnow().isoformat()
    
    return results


# ============================================================
# AVAILABLE ENGINES LIST
# ============================================================

AVAILABLE_ENGINES = [
    {
        "name": "SpiderFoot",
        "version": "4.0.0",
        "modules": 200,
        "description": "Full OSINT automation with 200+ modules — WHOIS, DNS, subdomains, SSL, blocklists, Bitcoin abuse, Wayback Machine, and more",
        "github": "https://github.com/smicallef/spiderfoot",
        "license": "MIT",
        "requires_api_key": False,
        "endpoint": "/api/osint/spiderfoot"
    },
    {
        "name": "DNSTwist",
        "version": "latest",
        "modules": 15,
        "description": "Detects typo-squatting, lookalike domains, homoglyphs, and phishing domain variants with DNS resolution",
        "github": "https://github.com/elceef/dnstwist",
        "license": "Apache-2.0",
        "requires_api_key": False,
        "endpoint": "/api/osint/dnstwist"
    },
    {
        "name": "Shodan",
        "version": "latest",
        "modules": 1,
        "description": "Search engine for internet-connected devices — ports, services, vulnerabilities, banners, geolocation",
        "github": "https://github.com/shodan-io/python-shodan",
        "license": "MIT",
        "requires_api_key": False,
        "endpoint": "/api/osint/shodan"
    },
    {
        "name": "WAFW00F",
        "version": "latest",
        "modules": 1,
        "description": "Identifies Web Application Firewalls — detects if scammers hide behind Cloudflare, Sucuri, Imperva, etc.",
        "github": "https://github.com/EnableSecurity/wafw00f",
        "license": "BSD-3-Clause",
        "requires_api_key": False,
        "endpoint": "/api/osint/wafw00f"
    },
    {
        "name": "DNSRecon",
        "version": "latest",
        "modules": 1,
        "description": "DNS enumeration — records, subdomain brute force, zone transfers, SRV records, reverse lookups",
        "github": "https://github.com/darkoperator/dnsrecon",
        "license": "GPL-2.0",
        "requires_api_key": False,
        "endpoint": "/api/osint/dnsrecon"
    },
    {
        "name": "python-whois",
        "version": "latest",
        "modules": 1,
        "description": "Full WHOIS record extraction — registrant, registrar, dates, nameservers, privacy detection",
        "github": "https://github.com/richardpenman/whois",
        "license": "WTFPL",
        "requires_api_key": False,
        "endpoint": "/api/osint/whois"
    },
    {
        "name": "ProxyPiercer",
        "version": "1.0",
        "modules": 8,
        "description": "GFIN-built: Pierces WHOIS privacy, CDN proxies, finds origin IP, traces physical location, SSL pivot",
        "github": "GFIN Internal",
        "license": "GFIN Proprietary",
        "requires_api_key": False,
        "endpoint": "/api/osint/proxy-pierce"
    }
]

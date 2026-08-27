"""
GFIN Dark Web Monitor — Layer B Tor Integration Patch

Uses curl --socks5-hostname for reliable .onion resolution through Tor.
All findings marked UNVERIFIED by default per Constitution §12.
"""
import subprocess
import json
import hashlib
from datetime import datetime, UTC

TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050
TOR_ENABLED = True


def _tor_curl(url, timeout=30):
    """Fetch a URL through Tor using curl --socks5-hostname."""
    cmd = [
        "curl", "-s",
        "--socks5-hostname", f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
        "--max-time", str(timeout),
        "-H", "User-Agent: GFIN-Monitor/1.0",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    return result.stdout if result.returncode == 0 else None


def _check_tor_available():
    """Check if Tor SOCKS proxy is available."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--socks5-hostname", f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
             "--max-time", "15", "https://check.torproject.org/api/ip"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and "IsTor" in result.stdout:
            return True
    except Exception:
        pass
    return False


def get_tor_exit_ip():
    """Get the current Tor exit IP."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--socks5-hostname", f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
             "--max-time", "15", "https://check.torproject.org/api/ip"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            return json.loads(result.stdout).get("IP", "unknown")
    except Exception:
        pass
    return "unknown"


# Dark web sources for passive monitoring
# These are well-known .onion services. URLs change frequently.
DARK_WEB_SOURCES = {
    "paste_sites": [
        "http://strongerw2ieewjpdqvu4iq4jvyfwcmo5pzpey3l4c2y3pbsuqq6kvktyd.onion",
    ],
    "search_engines": [
        "http://juhanurmihxlp77nkq76byazc4y5sflaz2sqi3v3k6qj2c5qck3awzyd.onion",  # Ahmia
    ],
    "breach_checkers": [
        # Known breach databases (passive monitoring only)
    ],
}


def scan_with_tor(entity, entity_type="email"):
    """
    Scan dark web sources using Tor SOCKS proxy (Layer B).
    Passive monitoring only — reads public pages, no interaction.
    """
    findings = []

    if not _check_tor_available():
        print("Tor proxy not available, falling back to Layer A simulation")
        return findings

    exit_ip = get_tor_exit_ip()

    # Scan paste sites
    for site_url in DARK_WEB_SOURCES["paste_sites"]:
        try:
            content = _tor_curl(f"{site_url}/search?q={entity}", timeout=30)
            if content and entity.lower() in content.lower():
                findings.append({
                    "source": "paste_site",
                    "finding_type": "leaked_credential",
                    "threat_level": "high",
                    "title": "Entity found on dark web paste site",
                    "description": f"Entity '{entity}' found in search results on dark web paste site. Content may include leaked credentials or personal data.",
                    "affected_entity": entity,
                    "affected_entity_type": entity_type,
                    "source_url": site_url,
                    "verified": False,
                    "scan_method": "tor_socks5_curl",
                    "tor_exit_ip": exit_ip,
                    "limitations": [
                        "Finding is UNVERIFIED — requires human analyst verification.",
                        "Source may be compromised, decoy, or contain outdated data.",
                        "Tor-based scanning confirms source accessibility, not data accuracy.",
                    ],
                })
            else:
                findings.append({
                    "source": "paste_site",
                    "finding_type": "scan_attempt",
                    "threat_level": "low",
                    "title": "Paste site scanned — no match",
                    "description": f"Scanned {site_url} for '{entity}'. No matches found in search results.",
                    "affected_entity": entity,
                    "affected_entity_type": entity_type,
                    "source_url": site_url,
                    "verified": False,
                    "scan_method": "tor_socks5_curl",
                    "tor_exit_ip": exit_ip,
                    "result": "no_match",
                })
        except subprocess.TimeoutExpired:
            findings.append({
                "source": "paste_site",
                "finding_type": "scan_attempt",
                "threat_level": "low",
                "title": "Scan attempted — source timeout",
                "description": f"Scanning {site_url} for '{entity}' timed out. Source may be down or slow.",
                "affected_entity": entity,
                "affected_entity_type": entity_type,
                "source_url": site_url,
                "verified": False,
                "scan_method": "tor_socks5_curl",
                "tor_exit_ip": exit_ip,
                "error": "timeout",
            })
        except Exception as e:
            findings.append({
                "source": "paste_site",
                "finding_type": "scan_attempt",
                "threat_level": "low",
                "title": "Scan attempted — source unreachable",
                "description": f"Attempted to scan {site_url} for '{entity}'. Source was unreachable.",
                "affected_entity": entity,
                "affected_entity_type": entity_type,
                "source_url": site_url,
                "verified": False,
                "scan_method": "tor_socks5_curl",
                "tor_exit_ip": exit_ip,
                "error": str(e),
            })

    # Scan dark web search engines (Ahmia)
    for engine_url in DARK_WEB_SOURCES["search_engines"]:
        try:
            search_url = f"{engine_url}/search?q={entity}"
            content = _tor_curl(search_url, timeout=30)
            if content and entity.lower() in content.lower():
                findings.append({
                    "source": "leak_forum",
                    "finding_type": "data_dump",
                    "threat_level": "high",
                    "title": "Entity found in dark web search results",
                    "description": f"Entity '{entity}' found in dark web search engine results. May appear in leaked databases or fraud listings.",
                    "affected_entity": entity,
                    "affected_entity_type": entity_type,
                    "source_url": search_url,
                    "verified": False,
                    "scan_method": "tor_socks5_curl_ahmia",
                    "tor_exit_ip": exit_ip,
                    "limitations": [
                        "Search results are UNVERIFIED — requires human analyst verification.",
                        "Dark web search indices may be incomplete or contain stale data.",
                    ],
                })
        except Exception as e:
            print(f"Search engine scan error: {e}")

    return findings


def get_tor_status():
    """Get Tor proxy status for monitoring."""
    available = _check_tor_available()
    exit_ip = get_tor_exit_ip() if available else "unavailable"
    return {
        "tor_enabled": TOR_ENABLED,
        "socks_proxy": f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
        "proxy_available": available,
        "exit_ip": exit_ip,
        "layer": "B" if available else "A",
        "sources_configured": sum(len(v) for v in DARK_WEB_SOURCES.values()),
        "source_categories": list(DARK_WEB_SOURCES.keys()),
        "note": "Layer B (real Tor scanning) active" if available else "Layer A (simulated) — Tor proxy not available",
    }

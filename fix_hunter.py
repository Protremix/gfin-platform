import re

# Read the current file
with open("/gfin/autonomous_hunter.py", "r") as f:
    content = f.read()

# Fix 1: Better URL parsing in phishing DB discovery
old_phish = """    try:
        # Phishing.Database — community-maintained phishing URL list
        text = http_get_text(
            "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
            timeout=20
        )
        if text:
            urls = text.strip().split("\\n")
            for url in urls[:50]:  # Check most recent 50
                url = url.strip()
                if not url or url.startswith("#"):
                    continue
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()
                if domain and domain not in _investigated_cache:
                    results.append({
                        "domain": domain,
                        "source": "PHISHING_DATABASE",
                        "url": url,
                    })"""

new_phish = """    try:
        # Phishing.Database — community-maintained phishing URL list
        text = http_get_text(
            "https://raw.githubusercontent.com/mitchellkrogza/Phishing.Database/master/phishing-links-ACTIVE.txt",
            timeout=20
        )
        if text:
            urls = text.strip().split("\\n")
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
                if "." not in domain or re.match(r"^[\\d.]+$", domain):
                    continue
                results.append({
                    "domain": domain,
                    "source": "PHISHING_DATABASE",
                    "url": url,
                })"""

content = content.replace(old_phish, new_phish)

# Fix 2: Better URL parsing in OpenPhish
old_openphish = """    try:
        text = http_get_text("https://www.openphish.com/feed.txt", timeout=20)
        if text:
            urls = text.strip().split("\\n")
            for url in urls[:50]:
                url = url.strip()
                if not url:
                    continue
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()
                if domain and domain not in _investigated_cache:
                    results.append({
                        "domain": domain,
                        "source": "OPENPHISH",
                        "url": url,
                    })"""

new_openphish = """    try:
        text = http_get_text("https://www.openphish.com/feed.txt", timeout=20)
        if text:
            urls = text.strip().split("\\n")
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
                if "." not in domain or re.match(r"^[\\d.]+$", domain):
                    continue
                results.append({
                    "domain": domain,
                    "source": "OPENPHISH",
                    "url": url,
                })"""

content = content.replace(old_openphish, new_openphish)

# Fix 3: Add timeout to HTTP content fetch
old_fetch = """def _fetch_http_content(domain: str) -> str:
    \"\"\"Fetch HTTP content from domain.\"\"\"
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
                return resp.read().decode("utf-8", errors="replace")[:50000]  # Limit to 50KB
        except Exception as e:
            logger.debug(f"HTTP fetch failed for {scheme}://{domain}: {e}")
    return None"""

new_fetch = """def _fetch_http_content(domain: str) -> str:
    \"\"\"Fetch HTTP content from domain.\"\"\"
    for scheme in ["https", "http"]:
        try:
            url = f"{scheme}://{domain}/"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            })
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            content_type = resp.headers.get("Content-Type", "")
            if "text" in content_type or "html" in content_type or "json" in content_type:
                return resp.read().decode("utf-8", errors="replace")[:50000]
        except Exception as e:
            logger.debug(f"HTTP fetch failed for {scheme}://{domain}: {e}")
    return None"""

content = content.replace(old_fetch, new_fetch)

# Fix 4: Add _is_valid_domain check in discover_targets
old_dedup = """    # Deduplicate by domain
    seen = set()
    unique = []
    for r in all_results:
        d = r["domain"]
        if d not in seen and not _is_safe_domain(d):
            seen.add(d)
            unique.append(r)"""

new_dedup = """    # Deduplicate by domain, filter invalid entries
    seen = set()
    unique = []
    for r in all_results:
        d = r["domain"]
        # Must be a valid domain (not IP, not email, has a dot, not a safe CDN)
        if d and "." in d and "@" not in d and not re.match(r"^[\\d.]+$", d) and d not in seen and not _is_safe_domain(d):
            seen.add(d)
            unique.append(r)"""

content = content.replace(old_dedup, new_dedup)

# Fix 5: Faster scan interval (15 min instead of 30) and more cases per cycle
content = content.replace("SCAN_INTERVAL_SECONDS = 1800  # 30 minutes between discovery scans", "SCAN_INTERVAL_SECONDS = 900  # 15 minutes between discovery scans")
content = content.replace("MAX_CASES_PER_CYCLE = 5", "MAX_CASES_PER_CYCLE = 10")

with open("/gfin/autonomous_hunter.py", "w") as f:
    f.write(content)

print("Fixed autonomous_hunter.py")

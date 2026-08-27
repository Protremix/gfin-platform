#!/usr/bin/env python3
"""
GFIN Hunter v3.0 — Enhanced Cyber Intelligence Module
Adds: Favicon hashing, Analytics ID tracking, redirect chains, tech stack fingerprinting,
registration age, typo-squatting detection, form detection, more threat feeds.
"""

import re, hashlib, json, ssl, urllib.request, urllib.parse, socket, struct, logging
from datetime import datetime, timezone
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# ============================================================
# 1. FAVICON HASHING — Correlate sites by same operator
# ============================================================
def fetch_favicon_hash(domain: str) -> str:
    """Fetch favicon and compute MD5 hash. Same hash = same operator."""
    for favicon_path in ["/favicon.ico", "/favicon.png", "/favicons/favicon.ico"]:
        for scheme in ["https", "http"]:
            try:
                url = f"{scheme}://{domain}{favicon_path}"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)",
                })
                resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
                data = resp.read()
                if len(data) > 100:  # Ignore tiny/empty responses
                    return hashlib.md5(data).hexdigest()
            except:
                pass
    # Try parsing HTML for favicon link
    try:
        url = f"https://{domain}/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)"})
        resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
        html = resp.read().decode('utf-8', errors='replace')[:20000]
        match = re.search(r'<link[^>]*rel=["\'](?:shortcut )?icon["\'][^>]*href=["\']([^"\']+)["\']', html, re.I)
        if match:
            favicon_url = match.group(1)
            if not favicon_url.startswith("http"):
                favicon_url = f"https://{domain}" + favicon_url if favicon_url.startswith("/") else f"https://{domain}/{favicon_url}"
            req2 = urllib.request.Request(favicon_url, headers={"User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)"})
            resp2 = urllib.request.urlopen(req2, timeout=10, context=SSL_CTX)
            data = resp2.read()
            if len(data) > 100:
                return hashlib.md5(data).hexdigest()
    except:
        pass
    return None

# ============================================================
# 2. ANALYTICS ID EXTRACTION — Track operators across sites
# ============================================================
def extract_analytics_ids(html: str) -> dict:
    """Extract tracking IDs from HTML. These are unique per operator."""
    ids = {
        "google_analytics": [],
        "google_adsense": [],
        "yandex_metrica": [],
        "facebook_pixel": [],
        "hotjar": [],
        "clarity": [],
        "gtm_container": [],
    }

    # Google Analytics (UA-XXXXXX-X or G-XXXXXXX)
    for m in re.findall(r'(?:UA-\d{4,10}-\d{1,4}|G-[A-Z0-9]{6,12})', html):
        ids["google_analytics"].append(m)
    
    # Google AdSense (ca-pub-XXXXXXXXX)
    for m in re.findall(r'ca-pub-(\d{10,20})', html):
        ids["google_adsense"].append("ca-pub-" + m)
    
    # Yandex.Metrica (ym(XXXXXX, 
    for m in re.findall(r'ym\((\d{6,12})', html):
        ids["yandex_metrica"].append(m)
    
    # Facebook Pixel (fbq('init', 'XXXXXXXXX')
    for m in re.findall(r"fbq\('init',\s*'(\d{8,20})", html):
        ids["facebook_pixel"].append(m)
    
    # Hotjar (hjid=XXXXXX)
    for m in re.findall(r'hjid["\']?\s*[:=]\s*["\']?(\d{4,10})', html):
        ids["hotjar"].append(m)
    
    # Microsoft Clarity (clarity ID)
    for m in re.findall(r'clarity\(["\']\w+["\'],\s*["\'](\w+)["\']', html):
        ids["clarity"].append(m)
    
    # Google Tag Manager container (GTM-XXXXXXX)
    for m in re.findall(r'GTM-[A-Z0-9]{5,10}', html):
        ids["gtm_container"].append(m)
    
    # Deduplicate
    for k in ids:
        ids[k] = list(set(ids[k]))
    
    # Remove empty
    return {k: v for k, v in ids.items() if v}

# ============================================================
# 3. REDIRECT CHAIN FOLLOWING — Find the real landing page
# ============================================================
def follow_redirects(domain: str, max_redirects: int = 5) -> dict:
    """Follow HTTP redirect chains. Scammers redirect to hide the real scam page."""
    chain = []
    current_url = f"https://{domain}/"
    
    for i in range(max_redirects):
        try:
            req = urllib.request.Request(current_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GFIN-Scanner/1.0)",
            })
            resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
            final_url = resp.geturl()
            status = resp.getcode()
            headers = dict(resp.headers)
            
            chain.append({
                "step": i + 1,
                "url": current_url,
                "status": status,
                "final_url": final_url,
                "server": headers.get("Server", ""),
                "content_type": headers.get("Content-Type", ""),
                "content_length": headers.get("Content-Length", ""),
                "powered_by": headers.get("X-Powered-By", ""),
                "cache": headers.get("Cache-Control", ""),
                "cf_ray": headers.get("CF-Ray", ""),  # Cloudflare
            })
            
            if final_url == current_url:
                break
            current_url = final_url
        except urllib.error.HTTPError as e:
            chain.append({
                "step": i + 1,
                "url": current_url,
                "status": e.code,
                "error": str(e),
            })
            break
        except Exception as e:
            chain.append({
                "step": i + 1,
                "url": current_url,
                "error": str(e),
            })
            break
    
    return {
        "redirects": chain,
        "final_url": chain[-1]["url"] if chain else current_url,
        "redirect_count": len(chain) - 1 if len(chain) > 1 else 0,
        "cross_domain_redirect": any(
            c.get("final_url") and domain not in c.get("final_url", "")
            for c in chain[1:]
        ) if len(chain) > 1 else False,
    }

# ============================================================
# 4. TECH STACK FINGERPRINTING — What's running the site
# ============================================================
def fingerprint_tech_stack(html: str, headers: dict = None) -> dict:
    """Detect CMS, frameworks, JS libraries, payment processors."""
    stack = {
        "cms": [],
        "frameworks": [],
        "js_libraries": [],
        "payment_processors": [],
        "cdn": [],
        "hosting": [],
        "security": [],
    }
    headers = headers or {}
    header_str = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
    text = html[:30000].lower() if html else ""

    # CMS detection
    cms_signatures = {
        "WordPress": [r'wp-content/', r'wp-includes/', r'wp-json/', r'/wp-login.php'],
        "Joomla": [r'/components/com_', r'joomla!', r'index.php\?option=com_'],
        "Drupal": [r'drupal.js', r'sites/all/', r'sites/default/'],
        "Shopify": [r'cdn.shopify.com', r'shopify.theme', r'window.Shopify'],
        "Wix": [r'wix.com', r'wixsite', r'static.parastorage.com'],
        "Squarespace": [r'squarespace', r'static1.squarespace.com'],
        "Magento": [r'mage/cookies', r'magento', r'skin/frontend/'],
        "Ghost": [r'ghost-url', r'content/images/'],
        "Webflow": [r'webflow', r'wf-'],
        "Tilda": [r'tilda', r'tildacdn'],
    }
    for cms, patterns in cms_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I):
                stack["cms"].append(cms)
                break

    # Frameworks
    fw_signatures = {
        "React": [r'react.js', r'reactjs', r'_next/data/', r'__next'],
        "Vue.js": [r'vue.js', r'vuejs', r'__vue__'],
        "Angular": [r'angular', r'ng-app', r'ng-version'],
        "Next.js": [r'__next', r'_next/static/'],
        "Nuxt.js": [r'_nuxt/', r'__nuxt'],
        "Laravel": [r'laravel', r'csrf-token.*laravel'],
        "Django": [r'csrfmiddlewaretoken', r'django'],
        "Flask": [r'flask'],
        "Express": [r'x-powered-by.*express'],
        "Rails": [r'csrf-token.*rails', r'turbolinks'],
    }
    for fw, patterns in fw_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I) or re.search(p, header_str):
                stack["frameworks"].append(fw)
                break

    # JS libraries
    js_signatures = {
        "jQuery": [r'jquery', r'jquery.min.js'],
        "Bootstrap": [r'bootstrap', r'bootstrap.min'],
        "TailwindCSS": [r'tailwind', r'tailwindcss'],
        "Bulma": [r'bulma'],
        "Font Awesome": [r'font-awesome', r'fontawesome'],
        "Stripe.js": [r'stripe.js', r'stripe.com/v3'],
        "Google Tag Manager": [r'googletagmanager', r'gtm.js'],
    }
    for lib, patterns in js_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I):
                stack["js_libraries"].append(lib)
                break

    # Payment processors (critical for scam detection)
    payment_signatures = {
        "Stripe": [r'stripe.js', r'stripe.com', r'stripe_checkout', r'pk_live_', r'pk_test_'],
        "PayPal": [r'paypal.com', r'paypal-button', r'paypal-sdk'],
        "Coinbase Commerce": [r'coinbase.com/commerce', r'CommerceButton'],
        "CoinPayments": [r'coinpayments.net', r'coinpayments'],
        "Binance Pay": [r'binance.com', r'binance-pay'],
        "Razorpay": [r'razorpay.com', r'razorpay'],
        "Skrill": [r'skrill.com', r'skrill'],
        "Western Union": [r'westernunion.com'],
        "MoneyGram": [r'moneygram.com'],
        "BitPay": [r'bitpay.com', r'bitpay'],
        "NOWPayments": [r'nowpayments.io', r'nowpayments'],
    }
    for pp, patterns in payment_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I):
                stack["payment_processors"].append(pp)
                break

    # CDN detection
    cdn_signatures = {
        "Cloudflare": [r'cloudflare', r'cf-ray', r'__cf_bm'],
        "CloudFront": [r'cloudfront.net', r'x-amz-cf-id'],
        "Akamai": [r'akamai', r'akamaized.net', r'edgekey.net'],
        "Fastly": [r'fastly', r'fastly.net'],
        "jsDelivr": [r'jsdelivr.net'],
        "unpkg": [r'unpkg.com'],
    }
    for cdn, patterns in cdn_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I) or re.search(p, header_str):
                stack["cdn"].append(cdn)
                break

    # Security products
    sec_signatures = {
        "Cloudflare WAF": [r'cf-ray', r'__cf_bm'],
        "reCAPTCHA": [r'recaptcha', r'grecaptcha'],
        "hCaptcha": [r'hcaptcha'],
        "Cloudflare Turnstile": [r'cf-turnstile', r'challenges.cloudflare.com'],
        "hCaptcha Enterprise": [r'hcaptcha.com'],
    }
    for sec, patterns in sec_signatures.items():
        for p in patterns:
            if re.search(p, text, re.I) or re.search(p, header_str):
                stack["security"].append(sec)
                break

    # Deduplicate
    for k in stack:
        stack[k] = list(set(stack[k]))
    
    return {k: v for k, v in stack.items() if v}

# ============================================================
# 5. FORM DETECTION — Find login, payment, crypto forms
# ============================================================
def detect_forms(html: str) -> dict:
    """Detect forms on the page — login, payment, registration, crypto wallet forms."""
    forms = {
        "login_forms": 0,
        "registration_forms": 0,
        "payment_forms": 0,
        "crypto_forms": 0,
        "newsletter_forms": 0,
        "contact_forms": 0,
        "form_details": [],
    }
    if not html:
        return forms

    # Find all <form> tags
    form_pattern = re.findall(r'<form[^>]*>(.*?)</form>', html, re.S | re.I)
    for form_html in form_pattern:
        form_lower = form_html.lower()
        form_info = {"action": "", "method": "", "fields": [], "type": "unknown"}
        
        # Extract form action
        action_match = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', html, re.I)
        if action_match:
            form_info["action"] = action_match.group(1)
        
        # Determine form type
        if any(kw in form_lower for kw in ["password", "passwd", "login", "signin", "log in", "sign in"]):
            forms["login_forms"] += 1
            form_info["type"] = "login"
        elif any(kw in form_lower for kw in ["credit card", "card number", "cvv", "expiry", "payment", "billing", "checkout"]):
            forms["payment_forms"] += 1
            form_info["type"] = "payment"
        elif any(kw in form_lower for kw in ["wallet", "bitcoin", "ethereum", "usdt", "crypto", "seed phrase", "private key", "mnemonic"]):
            forms["crypto_forms"] += 1
            form_info["type"] = "crypto"
        elif any(kw in form_lower for kw in ["register", "signup", "sign up", "create account", "join"]):
            forms["registration_forms"] += 1
            form_info["type"] = "registration"
        elif any(kw in form_lower for kw in ["newsletter", "subscribe"]):
            forms["newsletter_forms"] += 1
            form_info["type"] = "newsletter"
        elif any(kw in form_lower for kw in ["contact", "message", "email us"]):
            forms["contact_forms"] += 1
            form_info["type"] = "contact"
        
        # Extract input fields
        inputs = re.findall(r'<input[^>]*(?:name|type|placeholder)=["\']([^"\']*)["\']', form_html, re.I)
        form_info["fields"] = inputs[:10]
        forms["form_details"].append(form_info)
    
    return forms

# ============================================================
# 6. REGISTRATION AGE — How old is this domain?
# ============================================================
def calculate_domain_age(registration_date: str) -> dict:
    """Calculate domain age from registration date string."""
    if not registration_date:
        return {"age_days": None, "age_category": "unknown", "is_newly_registered": False}
    
    try:
        # Parse various date formats
        reg_date = None
        for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
            try:
                reg_date = datetime.strptime(registration_date[:19], fmt[:19] if "%f" not in fmt else fmt)
                break
            except:
                pass
        
        if not reg_date:
            # Try ISO format
            reg_date = datetime.fromisoformat(registration_date.replace("Z", "+00:00"))
        
        now = datetime.now(timezone.utc)
        if reg_date.tzinfo is None:
            reg_date = reg_date.replace(tzinfo=timezone.utc)
        
        age_days = (now - reg_date).days
        age_category = "mature"
        is_new = False
        
        if age_days <= 7:
            age_category = "brand_new"
            is_new = True
        elif age_days <= 30:
            age_category = "very_new"
            is_new = True
        elif age_days <= 90:
            age_category = "new"
            is_new = True
        elif age_days <= 365:
            age_category = "young"
        
        return {
            "age_days": age_days,
            "age_category": age_category,
            "is_newly_registered": is_new,
            "registration_date": registration_date,
        }
    except:
        return {"age_days": None, "age_category": "unknown", "is_newly_registered": False}

# ============================================================
# 7. TYPO-SQUATTING DETECTION — Is this a fake brand domain?
# ============================================================
PROTECTED_BRANDS = [
    "paypal", "google", "apple", "microsoft", "amazon", "facebook", "instagram",
    "netflix", "spotify", "twitter", "linkedin", "wellsfargo", "chase",
    "bankofamerica", "citibank", "hsbc", "barclays", "santander", "binance",
    "coinbase", "metamask", "trustwallet", "ledger", "trezor", "kraken",
    "bittrex", "huobi", "okx", "bybit", "kucoin", "gate", "crypto.com",
    "revolut", "wise", "n26", "discord", "telegram", "whatsapp", "snapchat",
    "tiktok", "youtube", "twitch", "steam", "epicgames", "playstation",
    "xbox", "nintendo", "uber", "airbnb", "booking", "expedia",
    "fedex", "dhl", "ups", "usps", "royalmail", "amex", "visa",
    "mastercard", "westernunion", "moneygram", "skrill",
]

def detect_typosquatting(domain: str) -> dict:
    """Check if domain is a typosquat of a legitimate brand."""
    domain_lower = domain.lower()
    # Extract the main part (before TLD)
    parts = domain_lower.split(".")
    if len(parts) < 2:
        return {"is_typosquat": False, "target_brand": None, "type": None}
    
    name = parts[0]  # e.g., "paypa1" from "paypa1.com"
    
    for brand in PROTECTED_BRANDS:
        # Exact match (brand in domain but with different TLD)
        if name == brand:
            continue  # Could be the real brand
        
        # Homoglyph substitution (0->o, 1->l, 3->e, etc.)
        homoglyphs = {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "$": "s", "@": "a"}
        normalized = name
        for old, new in homoglyphs.items():
            normalized = normalized.replace(old, new)
        
        if normalized == brand or brand in normalized:
            return {"is_typosquat": True, "target_brand": brand, "type": "homoglyph"}
        
        # Character substitution (1 char difference)
        if len(name) == len(brand):
            diffs = sum(1 for a, b in zip(name, brand) if a != b)
            if diffs == 1:
                return {"is_typosquat": True, "target_brand": brand, "type": "character_substitution"}
        
        # Character omission (missing 1 char)
        if len(name) == len(brand) - 1:
            for i in range(len(brand)):
                test = brand[:i] + brand[i+1:]
                if test == name:
                    return {"is_typosquat": True, "target_brand": brand, "type": "character_omission"}
        
        # Character insertion (extra char)
        if len(name) == len(brand) + 1:
            for i in range(len(name)):
                test = name[:i] + name[i+1:]
                if test == brand:
                    return {"is_typosquat": True, "target_brand": brand, "type": "character_insertion"}
        
        # Brand with prefix/suffix
        if name.startswith(brand + "-") or name.startswith(brand + ".") or \
           name.endswith("-" + brand) or name.endswith("." + brand) or \
           name.startswith("my" + brand) or name.startswith("the" + brand) or \
           name.startswith("secure" + brand) or name.startswith("login" + brand) or \
           name.startswith("verify" + brand) or name.startswith("wallet" + brand) or \
           name.startswith("support" + brand) or name.startswith("official" + brand):
            return {"is_typosquat": True, "target_brand": brand, "type": "prefix_suffix"}
    
    return {"is_typosquat": False, "target_brand": None, "type": None}

# ============================================================
# 8. HTTP SECURITY HEADERS ANALYSIS
# ============================================================
def analyze_security_headers(headers: dict) -> dict:
    """Analyze HTTP security headers. Missing headers = less professional = higher risk."""
    headers = headers or {}
    analysis = {
        "has_hsts": False,
        "has_csp": False,
        "has_xframe": False,
        "has_xcontent": False,
        "has_referrer_policy": False,
        "has_permissions_policy": False,
        "security_score": 0,
        "missing_headers": [],
    }
    
    h = {k.lower(): v for k, v in headers.items()}
    
    if h.get("strict-transport-security"):
        analysis["has_hsts"] = True
        analysis["security_score"] += 1
    else:
        analysis["missing_headers"].append("HSTS")
    
    if h.get("content-security-policy"):
        analysis["has_csp"] = True
        analysis["security_score"] += 1
    else:
        analysis["missing_headers"].append("CSP")
    
    if h.get("x-frame-options"):
        analysis["has_xframe"] = True
        analysis["security_score"] += 1
    else:
        analysis["missing_headers"].append("X-Frame-Options")
    
    if h.get("x-content-type-options"):
        analysis["has_xcontent"] = True
        analysis["security_score"] += 1
    else:
        analysis["missing_headers"].append("X-Content-Type-Options")
    
    if h.get("referrer-policy"):
        analysis["has_referrer_policy"] = True
        analysis["security_score"] += 1
    else:
        analysis["missing_headers"].append("Referrer-Policy")
    
    if h.get("permissions-policy"):
        analysis["has_permissions_policy"] = True
        analysis["security_score"] += 1
    
    return analysis

# ============================================================
# 9. ADDITIONAL THREAT FEEDS
# ============================================================
def discover_from_urlhaus() -> List[Dict]:
    """Fetch malicious URLs from URLHaus (abuse.ch)."""
    results = []
    try:
        data = urllib.request.urlopen(
            "https://urlhaus.abuse.ch/downloads/csv_recent/",
            timeout=20, context=SSL_CTX
        ).read().decode('utf-8', errors='replace')
        
        lines = data.strip().split("\n")
        for line in lines[1:51]:  # Skip header, take first 50
            if line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                url = parts[2].strip('"')
                if url.startswith("http"):
                    parsed = urllib.parse.urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain and "." in domain and not re.match(r"^[\d.]+$", domain):
                        results.append({
                            "domain": domain,
                            "source": "URLHAUS",
                            "url": url,
                            "threat_type": parts[3].strip('"') if len(parts) > 3 else "malware",
                        })
    except Exception as e:
        logger.debug(f"URLHaus scan failed: {e}")
    return results

def discover_from_abuseipdb() -> List[Dict]:
    """Check IP reputation via AbuseIPDB community feed (no API key needed for basic check)."""
    results = []
    try:
        # Use the abuse.ch ThreatFox feed as alternative (no API key)
        data = urllib.request.urlopen(
            "https://threatfox-api.abuse.ch/api/v1/",
            timeout=20, context=SSL_CTX
        ).read().decode('utf-8', errors='replace')
        parsed = json.loads(data)
        if parsed.get("query_status") == "ok":
            for item in parsed.get("data", [])[:30]:
                ioc_value = item.get("ioc_value", "")
                ioc_type = item.get("ioc_type", "")
                if ioc_type == "domain":
                    domain = ioc_value.lower()
                    if domain and "." in domain:
                        results.append({
                            "domain": domain,
                            "source": "THREATFOX",
                            "threat_type": item.get("malware", "unknown"),
                            "confidence": item.get("confidence_level", 50),
                        })
    except Exception as e:
        logger.debug(f"ThreatFox scan failed: {e}")
    return results

# ============================================================
# 10. PAGE TITLE & META ANALYSIS
# ============================================================
def extract_page_metadata(html: str) -> dict:
    """Extract page title, meta description, OpenGraph tags, structured data."""
    meta = {
        "title": "",
        "description": "",
        "og_title": "",
        "og_description": "",
        "og_image": "",
        "keywords": "",
        "generator": "",
        "viewport": "",
        "has_jsonld": False,
        "jsonld_types": [],
        "language": "",
    }
    if not html:
        return meta

    # Title
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    if title_match:
        meta["title"] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()[:200]

    # Meta description
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if desc_match:
        meta["description"] = desc_match.group(1)[:300]

    # Meta keywords
    kw_match = re.search(r'<meta[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if kw_match:
        meta["keywords"] = kw_match.group(1)[:300]

    # Meta generator
    gen_match = re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if gen_match:
        meta["generator"] = gen_match.group(1)

    # OpenGraph
    og_title = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if og_title:
        meta["og_title"] = og_title.group(1)
    og_desc = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if og_desc:
        meta["og_description"] = og_desc.group(1)
    og_image = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if og_image:
        meta["og_image"] = og_image.group(1)

    # JSON-LD structured data
    jsonld_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I)
    if jsonld_matches:
        meta["has_jsonld"] = True
        for jld in jsonld_matches:
            try:
                jld_data = json.loads(jld.strip())
                if isinstance(jld_data, dict) and "@type" in jld_data:
                    meta["jsonld_types"].append(jld_data["@type"])
                elif isinstance(jld_data, list):
                    for item in jld_data:
                        if isinstance(item, dict) and "@type" in item:
                            meta["jsonld_types"].append(item["@type"])
            except:
                pass

    # Language
    lang_match = re.search(r'<html[^>]*lang=["\']([^"\']*)["\']', html, re.I)
    if lang_match:
        meta["language"] = lang_match.group(1)

    return meta

print("GFIN Hunter v3.0 Enhanced Intelligence Module loaded")
print("Features: favicon hashing, analytics ID extraction, redirect chains,")
print("tech stack fingerprinting, form detection, domain age, typo-squatting,")
print("security headers, page metadata, URLHaus + ThreatFox feeds")

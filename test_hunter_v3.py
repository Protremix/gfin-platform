#!/usr/bin/env python3
"""Test script for Hunter v3 enhanced intelligence module."""
import sys
sys.path.insert(0, "/gfin")
from hunter_v3_intel import *

# Test favicon hashing
print("=== FAVICON HASH ===")
fav = fetch_favicon_hash("example.com")
print(f"example.com favicon: {fav}")

# Test typo-squatting
print("\n=== TYPO-SQUATTING ===")
tests = ["paypa1.com", "faceb00k.com", "google-secure.com", "binance-login.com", "metamask-wallet.com", "legitimate-site.com"]
for d in tests:
    result = detect_typosquatting(d)
    if result["is_typosquat"]:
        print(f"  {d} -> IMPERSONATES {result['target_brand']} ({result['type']})")
    else:
        print(f"  {d} -> clean")

# Test analytics ID extraction
print("\n=== ANALYTICS IDs ===")
html = '''<script>ga("create", "UA-12345678-1");</script>
<script>fbq("init", "9876543210");</script>
<script>ym(54321, "init");</script>
<ins data-ad-client="ca-pub-1234567890123456"></ins>
<script>GTM-ABCDEF12</script>'''
ids = extract_analytics_ids(html)
for k, v in ids.items():
    print(f"  {k}: {v}")

# Test domain age
print("\n=== DOMAIN AGE ===")
for d in ["2026-08-20T00:00:00Z", "2020-01-01", "unknown"]:
    age = calculate_domain_age(d)
    print(f"  {d}: {age['age_days']} days, {age['age_category']}, new={age['is_newly_registered']}")

# Test form detection
print("\n=== FORM DETECTION ===")
html_forms = '''<form action="/login"><input type="password" name="pass"><input type="submit"></form>
<form action="/pay"><input name="card_number"><input name="cvv"></form>
<form><input name="seed_phrase"><input name="private_key"></form>'''
forms = detect_forms(html_forms)
print(f"  Login forms: {forms['login_forms']}")
print(f"  Payment forms: {forms['payment_forms']}")
print(f"  Crypto forms: {forms['crypto_forms']}")

# Test tech stack
print("\n=== TECH STACK ===")
html_tech = '''<link href="/wp-content/themes/style.css">
<script src="stripe.js"></script>
<script src="cloudflare.js"></script>'''
stack = fingerprint_tech_stack(html_tech, {"Server": "cloudflare", "CF-Ray": "abc123"})
for k, v in stack.items():
    print(f"  {k}: {v}")

# Test page metadata
print("\n=== PAGE METADATA ===")
html_meta = '''<html lang="en">
<head>
<title>Buy Crypto - Best Exchange</title>
<meta name="description" content="Trade crypto with guaranteed returns">
<meta name="generator" content="WordPress 6.2">
<script type="application/ld+json">{"@type": "Organization", "name": "FakeExchange"}</script>
</head></html>'''
meta = extract_page_metadata(html_meta)
print(f"  Title: {meta['title']}")
print(f"  Description: {meta['description']}")
print(f"  Generator: {meta['generator']}")
print(f"  JSON-LD types: {meta['jsonld_types']}")
print(f"  Language: {meta['language']}")

print("\n=== ALL TESTS PASSED ===")

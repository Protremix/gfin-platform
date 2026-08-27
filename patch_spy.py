#!/usr/bin/env python3
"""Patch telegram_spy.py to fix domain extraction."""
import re

with open("/gfin/telegram_spy.py", "r") as f:
    content = f.read()

# Backup
with open("/gfin/telegram_spy.py.bak", "w") as f:
    f.write(content)

# 1. Replace DOMAIN_PATTERN
old_pattern_line = 'DOMAIN_PATTERN = r\'\\b(?:https?://)?(?:www\\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\\.[a-zA-Z]{2,}(?:\\.[a-zA-Z]{2,})?)\\b\''

new_pattern_block = '''DOMAIN_PATTERN = re.compile(
    r'(?<![\\w\\-])(?:https?://)?(?:www\\.)?'
    r'([a-zA-Z][a-zA-Z0-9](?:[a-zA-Z0-9\\-]{0,61}[a-zA-Z0-9])?'
    r'\\.(?:[a-zA-Z]{2,63}))'
    r'(?:\\.[a-zA-Z]{2,63})?'
    r'(?![\\w\\-])',
    re.IGNORECASE
)

# Valid TLDs
VALID_TLDS = {
    "com", "net", "org", "io", "co", "me", "info", "biz", "xyz", "online",
    "site", "club", "top", "live", "store", "shop", "app", "dev", "tech",
    "ai", "cloud", "world", "money", "finance", "trade", "invest", "bank",
    "cash", "fund", "pro", "plus", "one", "first", "group", "global", "zone",
    "today", "now", "win", "vip", "gold", "link", "click", "fun",
    "website", "page", "space", "press", "news", "media", "digital", "crypto",
    "chain", "token", "coin", "wallet", "exchange", "market", "fx",
    "network", "systems", "solutions", "services", "agency", "capital",
    "ventures", "partners", "holdings", "ltd", "inc",
    "us", "uk", "de", "fr", "es", "it", "nl", "eu", "ru", "cn", "jp",
    "au", "ca", "br", "in", "ch", "at", "be", "se", "no", "dk", "fi",
    "pl", "cz", "sk", "hu", "ro", "bg", "gr", "pt", "ie", "lt", "lv",
    "ee", "si", "hr", "lu", "mt", "cy", "is", "tr", "ae", "sa", "il",
    "kr", "tw", "hk", "sg", "my", "th", "id", "ph", "vn", "nz",
    "za", "ng", "ke", "eg", "ma", "gh",
    "mx", "ar", "cl", "co", "pe", "ve", "ec", "uy", "py", "bo", "cr",
    "do", "gt", "sv", "hn", "ni", "pa",
    "cc", "tk", "ml", "ga", "cf", "gq", "ws", "to", "ms", "gs", "fm",
    "st", "tv", "gg", "am", "sh", "pr", "su",
    "icu", "cyou", "cam", "fit", "rest", "casa", "life",
    "name", "buzz", "fans", "sbs", "quest", "realty",
    "work", "best", "host", "wiki", "design", "studio",
}'''

content = content.replace(old_pattern_line, new_pattern_block)
print(f"Domain pattern replaced: {'DOMAIN_PATTERN' in content and 'VALID_TLDS' in content}")

# 2. Replace SAFE_DOMAINS
old_safe_start = 'SAFE_DOMAINS = {'
old_safe_end = '    "gfin-system.com",\n}'
# Find and replace the block
safe_match = re.search(r'SAFE_DOMAINS = \{[^}]+\}', content)
if safe_match:
    old_safe = safe_match.group(0)
    new_safe = '''SAFE_DOMAINS = {
    "telegram.org", "t.me", "youtube.com", "youtu.be", "google.com",
    "github.com", "wikipedia.org", "reddit.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "whatsapp.com", "linkedin.com",
    "tiktok.com", "snapchat.com", "pinterest.com", "medium.com",
    "discord.com", "discord.gg", "twitch.tv",
    "paypal.com", "stripe.com", "wise.com", "revolut.com",
    "amazon.com", "ebay.com", "apple.com", "microsoft.com",
    "netflix.com", "spotify.com",
    "binance.com", "coinbase.com", "kraken.com", "bybit.com",
    "crypto.com", "okx.com", "kucoin.com", "gate.io", "bitfinex.com",
    "huobi.com", "mexc.com", "poloniex.com", "gemini.com",
    "ethereum.org", "bitcoin.org", "ripple.com",
    "blockchain.com", "blockchair.com", "blockscout.com",
    "etherscan.io", "bscscan.com", "polygonscan.com", "tronscan.org",
    "solscan.io", "mempool.space", "ordiscan.com",
    "wa.link", "pm.me", "id.me", "bit.ly", "tinyurl.com",
    "imgur.com", "pastebin.com",
    "gfin-system.com", "statista.com", "reuters.com", "bloomberg.com",
    "forbes.com", "ft.com", "wsj.com", "bbc.com", "cnn.com",
    "shopify.com", "authorize.net", "square.com", "flutterwave.com",
    "payoneer.com", "sumup.com", "neex.com",
}'''
    content = content.replace(old_safe, new_safe)
    print("Safe domains replaced")

# 3. Replace extract_domains function
old_extract_match = re.search(r'def extract_domains\(text\):.*?\n    return domains', content, re.DOTALL)
if old_extract_match:
    old_extract = old_extract_match.group(0)
    new_extract = '''def extract_domains(text):
    """Extract domains with strict TLD validation — filters out garbage."""
    if not text:
        return []
    domains = []
    for match in DOMAIN_PATTERN.finditer(text):
        full_domain = match.group(1).lower()
        # Extract TLD
        parts = full_domain.rsplit(".", 1)
        if len(parts) < 2:
            continue
        tld = parts[1]
        # Must be a valid TLD
        if tld not in VALID_TLDS:
            continue
        # Skip safe domains
        if full_domain in SAFE_DOMAINS:
            continue
        # Skip if parent domain is safe
        parent_parts = full_domain.split(".")
        skip = False
        for i in range(len(parent_parts)):
            parent = ".".join(parent_parts[i:])
            if parent in SAFE_DOMAINS:
                skip = True
                break
        if skip:
            continue
        # Skip image/file extensions
        if full_domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".webp", ".css", ".js")):
            continue
        # Skip if starts with digit
        if full_domain[0].isdigit():
            continue
        # Skip very short domains
        if len(full_domain) < 5:
            continue
        # Skip false positive patterns
        if full_domain.endswith(".the") or full_domain.endswith(".all") or full_domain.endswith(".send"):
            continue
        if full_domain not in domains:
            domains.append(full_domain)
    return domains'''
    content = content.replace(old_extract, new_extract)
    print("extract_domains replaced")

with open("/gfin/telegram_spy.py", "w") as f:
    f.write(content)

print("✅ Patch complete")

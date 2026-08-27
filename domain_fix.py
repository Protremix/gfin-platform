#!/usr/bin/env python3
"""
GFIN Domain Extraction Fix — replaces the loose regex pattern with strict TLD validation.
This file provides the fixed extract_domains function and DOMAIN_PATTERN.
"""
import re

# Valid TLDs — only real top-level domains, no country names or random words
VALID_TLDS = {
    # Generic
    'com', 'net', 'org', 'io', 'co', 'me', 'info', 'biz', 'xyz', 'online',
    'site', 'club', 'top', 'live', 'store', 'shop', 'app', 'dev', 'tech',
    'ai', 'cloud', 'world', 'money', 'finance', 'trade', 'invest', 'bank',
    'cash', 'fund', 'pro', 'plus', 'one', 'first', 'group', 'global', 'zone',
    'today', 'now', 'win', 'vip', 'gold', 'vip', 'link', 'click', 'fun',
    'website', 'page', 'space', 'press', 'news', 'media', 'digital', 'crypto',
    'chain', 'token', 'coin', 'wallet', 'exchange', 'market', 'fx', 'trade',
    'network', 'systems', 'solutions', 'services', 'agency', 'capital',
    'ventures', 'partners', 'holdings', 'group', 'ltd', 'inc',
    # Country code (common)
    'us', 'uk', 'de', 'fr', 'es', 'it', 'nl', 'eu', 'ru', 'cn', 'jp',
    'au', 'ca', 'br', 'in', 'ch', 'at', 'be', 'se', 'no', 'dk', 'fi',
    'pl', 'cz', 'sk', 'hu', 'ro', 'bg', 'gr', 'pt', 'ie', 'lt', 'lv',
    'ee', 'si', 'hr', 'lu', 'mt', 'cy', 'is', 'tr', 'ae', 'sa', 'il',
    'kr', 'tw', 'hk', 'sg', 'my', 'th', 'id', 'ph', 'vn', 'nz',
    'za', 'ng', 'ke', 'eg', 'ma', 'gh', 'ng',
    'mx', 'ar', 'cl', 'co', 'pe', 've', 'ec', 'uy', 'py', 'bo', 'cr',
    'do', 'gt', 'sv', 'hn', 'ni', 'pa',
    # ccTLD commonly abused
    'cc', 'tk', 'ml', 'ga', 'cf', 'gq', 'ws', 'to', 'ms', 'gs', 'fm',
    'st', 'tv', 'gg', 'am', 'sh', 'pr', 'su',
    # New gTLDs commonly used
    'icu', 'cyou', 'cam', 'fit', 'monet', 'rest', 'casa', 'life',
    'name', 'buzz', 'fans', 'sbs', 'auty', 'autos', 'quest', 'realty',
    'men', 'work', 'best', 'host', 'wiki', 'design', 'studio',
}

# Safe/legitimate domains that should NOT be flagged as scam
SAFE_DOMAINS = {
    # Social media
    "telegram.org", "t.me", "youtube.com", "youtu.be", "google.com",
    "github.com", "wikipedia.org", "reddit.com", "twitter.com", "x.com",
    "facebook.com", "instagram.com", "whatsapp.com", "linkedin.com",
    "tiktok.com", "snapchat.com", "pinterest.com", "medium.com",
    "discord.com", "discord.gg", "twitch.tv",
    # Legit financial
    "paypal.com", "stripe.com", "wise.com", "revolut.com",
    "amazon.com", "ebay.com", "apple.com", "microsoft.com",
    "netflix.com", "spotify.com",
    # Legit crypto exchanges
    "binance.com", "coinbase.com", "kraken.com", "bybit.com",
    "crypto.com", "okx.com", "kucoin.com", "gate.io", "bitfinex.com",
    "huobi.com", "mexc.com", "poloniex.com", "gemini.com",
    # Legit crypto/blockchain
    "ethereum.org", "bitcoin.org", "ripple.com",
    "blockchain.com", "blockchair.com", "blockscout.com",
    "etherscan.io", "bscscan.com", "polygonscan.com", "tronscan.org",
    "solscan.io", "mempool.space", "ordiscan.com",
    # Legit tools
    "wa.link", "pm.me", "id.me", "bit.ly", "tinyurl.com",
    "imgur.com", "pastebin.com", "drive.google.com",
    # GFIN
    "gfin-system.com",
    # Common legit
    "statista.com", "reuters.com", "bloomberg.com", "forbes.com",
    "ft.com", "wsj.com", "bbc.com", "cnn.com",
    "shopify.com", "authorize.net", "square.com", "flutterwave.com",
    "payoneer.com", "sumup.com", "wise.com", "visor.com",
    "neex.com",  # legitimate broker
}

# Strict domain pattern: requires valid TLD from our list
# Domain must have at least 2 chars before TLD, can't start with digit+dot
DOMAIN_PATTERN = re.compile(
    r'\b(?:https?://)?(?:www\.)?'
    r'([a-zA-Z][a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
    r'\.(?:[a-zA-Z]{2,63}))'
    r'(?:\.[a-zA-Z]{2,63})?'
    r'\b',
    re.IGNORECASE
)

def extract_domains_strict(text):
    """
    Extract domains from text with strict TLD validation.
    Filters out:
    - Country names used as TLDs (serbia, greece, albania, etc.)
    - Person names (erica.chan)
    - Common words (minutes.the, services.all)
    - Legitimate services (crypto.com, youtube.com, etc.)
    - Numbered prefixes (1.serbia, 2.greece)
    """
    if not text:
        return []

    domains = []
    for match in DOMAIN_PATTERN.finditer(text):
        full_domain = match.group(1).lower()

        # Extract the TLD (last part after the last dot)
        parts = full_domain.rsplit('.', 1)
        if len(parts) < 2:
            continue
        tld = parts[1]

        # Must be a valid TLD
        if tld not in VALID_TLDS:
            continue

        # For two-part TLDs like co.uk, check the full domain
        # If domain ends with known two-part TLD, extract the base domain
        full_parts = full_domain.split('.')
        if len(full_parts) >= 3:
            # Check for two-part TLDs (co.uk, com.au, etc.)
            if full_parts[-2] in ('co', 'com', 'org', 'net', 'gov', 'edu') and full_parts[-1] in VALID_TLDS:
                # Two-part TLD: the domain is the part before
                base_domain = '.'.join(full_parts[:-2])
                if len(base_domain) < 2:
                    continue
                full_domain = base_domain + '.' + '.'.join(full_parts[-2:])
            else:
                # Regular domain with subdomain
                pass

        # Skip safe domains
        if full_domain in SAFE_DOMAINS:
            continue

        # Skip if any parent domain is safe (e.g., drive.google.com -> google.com is safe)
        parent_parts = full_domain.split('.')
        for i in range(len(parent_parts)):
            parent = '.'.join(parent_parts[i:])
            if parent in SAFE_DOMAINS:
                full_domain = None
                break
        if full_domain is None:
            continue

        # Skip image/file extensions
        if full_domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".webp", ".css", ".js")):
            continue

        # Skip if domain starts with a digit (like 1.serbia — already filtered by TLD check)
        if full_domain[0].isdigit():
            continue

        # Skip very short domain names (less than 4 chars total)
        if len(full_domain) < 5:
            continue

        # Skip known false positive patterns
        false_positive_patterns = [
            r'^\d+\.',           # Starts with number+dot (1.serbia)
            r'\.the$',           # Ends with .the (minutes.the)
            r'\.all$',           # Ends with .all (services.all)
            r'\.send$',          # Ends with .send (usdt.send)
            r'\.if$',            # Ends with .if (usdt.if) — but .if is not a valid TLD anyway
            r'^[a-z]{1,3}\.com$', # Very short domain (abc.com) — could be legit, but flag
        ]
        skip = False
        for pattern in false_positive_patterns:
            if re.match(pattern, full_domain):
                skip = True
                break
        if skip:
            continue

        if full_domain not in domains:
            domains.append(full_domain)

    return domains


if __name__ == "__main__":
    # Test with problematic messages
    test_cases = [
        "1.serbia 2.greece 3.albania 4.ecuador 5.dominican 6.ukraine",
        "Contact us at teamforcetechnologies.com for more info",
        "Send USDT to usdt.send or visit usdt.if",
        "Visit crypto.com for trading",
        "Check authorize.net for payments",
        "minutes.the meeting lasted 2 hours",
        "services.all are available",
        "erica.chan is the new manager",
        "Visit scam-site.com or fake-broker.net to invest",
        "wa.link contact me on WhatsApp",
        "pm.me for private messages",
        "Visit neex.com for trading",
        "Buy from shop.example-store.com today",
    ]

    for text in test_cases:
        result = extract_domains_strict(text)
        print(f"  Input: {text[:60]}...")
        print(f"  Output: {result}")
        print()

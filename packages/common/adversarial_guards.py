"""
GFIN Adversarial Data Guards v1.0
6 guards against false correlations and misleading data in evidence pipeline.

Guards:
1. guard_false_relationship — CDN/shared hosting does NOT indicate ownership
2. guard_wallet_attribution — exchange vs personal wallet classification
3. guard_generic_username — reject generic usernames as identity
4. guard_stale_record — flag old domains for re-verification
5. guard_conflicting_records — detect contradiction between sources
6. guard_provider_label_vs_identity — separate provider labels from identity
"""

CDN_IP_PREFIXES = {"104.21.", "172.67.", "13.32.", "13.33.", "151.139.", "23.235.", "43.249."}
SHARED_HOSTING_PROVIDERS = {"cloudflare", "amazon aws", "google llc", "microsoft azure", "fastly", "akamai", "godaddy", "bluehost", "hostgator", "digitalocean", "linode", "vultr", "hetzner", "ovh"}
KNOWN_EXCHANGE_PREFIXES = {"0x742d35", "0xC098B2a0", "0x28C6c06298", "0x21a31EEd", "0xDFd5", "0x5D44", "0xe626"}
GENERIC_USERNAMES = {"admin", "administrator", "root", "support", "info", "contact", "help", "service", "team", "staff", "moderator", "mod", "bot", "system", "noreply", "no-reply", "notifications", "official", "news", "updates", "announce", "sales", "marketing", "hr", "billing", "account", "security", "trust", "safety", "welcome", "hello", "test", "demo", "example", "sample", "user", "guest", "unknown", "anonymous", "anon", "deleted", "removed"}
PROVIDER_LABELS = {"binance", "coinbase", "kraken", "okx", "bybit", "kucoin", "bitfinex", "gate.io", "huobi", "gemini", "crypto.com", "blockchain.com", "trezor", "ledger", "metamask", "exchange", "hot wallet", "cold wallet", "trading platform", "payment processor", "payment gateway", "merchant"}

def guard_false_relationship(shared_ip):
    for prefix in CDN_IP_PREFIXES:
        if shared_ip.startswith(prefix):
            return {"decision": "REJECT", "reason": f"Shared IP {shared_ip} is CDN. Does NOT indicate ownership.", "confidence": 0.95}
    return {"decision": "UNRESOLVED", "reason": "Requires WHOIS/ASN lookup", "confidence": 0.3}

def guard_wallet_attribution(wallet_address):
    addr_lower = wallet_address.lower()
    for prefix in KNOWN_EXCHANGE_PREFIXES:
        if addr_lower.startswith(prefix.lower()):
            return {"decision": "COUNTERPARTY", "reason": "Exchange hot wallet", "classification": "EXCHANGE_WALLET", "confidence": 0.8}
    return {"decision": "IDENTITY_CANDIDATE", "reason": "No exchange match", "classification": "PERSONAL_WALLET", "confidence": 0.5}

def guard_generic_username(username):
    u = username.lower().lstrip("@")
    if u in GENERIC_USERNAMES: return {"decision": "REJECT", "reason": "Generic username", "confidence": 0.95}
    if len(u) < 3: return {"decision": "REJECT", "reason": "Too short", "confidence": 0.9}
    if u.isdigit(): return {"decision": "REJECT", "reason": "Numeric only", "confidence": 0.8}
    return {"decision": "ACCEPT", "reason": "Specific enough", "confidence": 0.7}

def guard_stale_record(domain_age_days, last_scam_date=None):
    if domain_age_days > 365: return {"decision": "LOW_CONFIDENCE_LEAD", "reason": "Old domain, may have changed ownership", "confidence": 0.3, "action": "RE_VERIFY"}
    if domain_age_days <= 7: return {"decision": "HIGH_CONFIDENCE_LEAD", "reason": "Newly registered", "confidence": 0.8}
    return {"decision": "MEDIUM_CONFIDENCE_LEAD", "reason": "Moderate age", "confidence": 0.5}

def guard_conflicting_records(domain, reports):
    scam = [r for r in reports if r.get("classification") == "scam"]
    legit = [r for r in reports if r.get("classification") == "legitimate"]
    if scam and legit: return {"decision": "CONFLICT", "reason": f"Contradiction: {len(scam)} scam vs {len(legit)} legit", "confidence": 0.0, "action": "LOG_CONTRADICTION"}
    if scam: return {"decision": "CONSISTENT_SCAM", "confidence": 0.7}
    return {"decision": "CONSISTENT_CLEAN", "confidence": 0.5}

def guard_provider_label_vs_identity(label):
    l = label.lower()
    for p in PROVIDER_LABELS:
        if p in l: return {"decision": "PROVIDER_LABEL", "reason": f"Provider: {p}", "confidence": 0.9}
    return {"decision": "IDENTITY_CANDIDATE", "reason": "Not a provider", "confidence": 0.6}

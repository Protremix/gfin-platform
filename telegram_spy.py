#!/usr/bin/env python3
"""
GFIN Telegram User Spy v2.0
Operates as a REAL Telegram USER (not a bot) — joins groups,
reads ALL messages, extracts intelligence, detects scams & victims.

Uses Telethon MTProto client API with api_id + api_hash.
Session is saved after first login — runs autonomously after that.
"""
import os, sys, re, json, time, logging, hashlib, asyncio
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.tl.types import (
    Channel, Chat, User,
    ChannelParticipantsSearch,
)
import urllib.request

# === MIDAS Real-time Graph Anomaly Detection ===
try:
    from gfin_midas import midas_pipeline
    MIDAS_AVAILABLE = True
except Exception as e:
    print(f"MIDAS import warning: {e}")
    MIDAS_AVAILABLE = False
import urllib.parse, urllib.parse, ssl

# ============================================================
# CONFIGURATION
# ============================================================
API_ID = int(os.environ.get("TELEGRAM_API_ID", "0"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_NAME = "/gfin/gfin_user_session"
GFIN_API = "http://127.0.0.1:8000"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [spy] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/gfin/logs/telegram_spy.log"),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================
# INTELLIGENCE EXTRACTION PATTERNS
# ============================================================

WALLET_PATTERNS = {
    "BTC": r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
    "BTC_BECH32": r'\bbc1[a-z0-9]{39,59}\b',
    "ETH": r'\b0x[a-fA-F0-9]{40}\b',
    "TRON": r'\bT[A-Za-z0-9]{33}\b',
    "SOLANA": r'\b[1-9A-HJ-NP-Za-km-z]{43,44}\b',
    "XRP": r'\br[A-Za-z0-9]{24,34}\b',
    "TON": r'\b(EQA|EQB|EQC|EQD|EQE|EQF|EQG|EQH|EQI|EQJ|EQK|EQL|EQM|EQN|EQO|EQP|EQQ|EQR|EQS|EQT|EQU|EQV|EQW|EQX|EQY|EQZ)[A-Za-z0-9_-]{46}\b',
    "LTC": r'\b[LM][ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz1-9]{25,33}\b',
    "DOGE": r'\bD[ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz1-9]{33}\b',
}

DOMAIN_PATTERN = re.compile(
    r'(?<![\w\-])(?:https?://)?(?:www\.)?'
    r'([a-zA-Z][a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
    r'\.(?:[a-zA-Z]{2,63}))'
    r'(?:\.[a-zA-Z]{2,63})?'
    r'(?![\w\-])',
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
}
PHONE_PATTERN = r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}'
IP_PATTERN = r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
USERNAME_MENTION = r'@([A-Za-z0-9_]{5,32})'

# Known safe domains (don't flag these)
SAFE_DOMAINS = {
    "telegram.org", "t.me", "telegram.me", "youtube.com", "youtu.be", "google.com",
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
}

VICTIM_PATTERNS = [
    r"(i\s+was\s+scammed|got\s+scammed|been\s+scammed)",
    r"(i\s+lost\s+(my|all|everything|\$?\d)|lost\s+money|lost\s+funds)",
    r"(they\s+took\s+my\s+(money|crypto|funds)|stole\s+my)",
    r"(how\s+(do|can)\s+i\s+(recover|get\s+back|retrieve))",
    r"(i\s+sent\s+(btc|eth|crypto|bitcoin|usdt))",
    r"(fake\s+(website|exchange|platform|trader|investment))",
    r"(pig\s+butcher)",
    r"(recovery\s+(service|agent|expert|hacker))",
    r"(can\s+anyone\s+help\s+(me|us))",
    r"(anyone\s+(know|heard\s+of)\s+this\s+(site|domain|platform))",
    r"(got\s+ripped\s+off|was\s+robbed)",
    r"(they\s+(blocked|disabled)\s+my\s+account)",
    r"(withdrawal\s+(blocked|frozen|cancelled))",
    r"(can.?t\s+withdraw|cannot\s+withdraw)",
]

SCAM_INDICATORS = [
    "guaranteed profit", "double your", "invest and earn", "trading signals",
    "recovery service", "recovery agent", "get your money back",
    "hack back", "reclaim your funds", "fund recovery expert",
    "giveaway", "free bitcoin", "send 1 eth get 2",
    "airdrop", "claim your reward", "connect wallet",
    "private key", "seed phrase", "mnemonic",
    "pig butchering", "romance scam", "dating scam",
    "double your bitcoin", "multiply your crypto",
]

SCAM_TYPE_MAP = {
    "RECOVERY_SCAM": ["recover", "get your money back", "recovery service", "recovery agent", "fund recovery", "hack back", "reclaim"],
    "ROMANCE_SCAM": ["romance", "dating scam", "love scam", "catfish", "sugar daddy", "sugar mommy"],
    "INVESTMENT_FRAUD": ["investment", "trading", "forex", "binary options", "guaranteed return", "trading signals", "arbitrage"],
    "PHISHING": ["verify your", "confirm your", "suspended account", "click here to", "login to secure"],
    "IMPERSONATION": ["official representative", "support team", "customer service", "verify identity"],
    "CRYPTO_FRAUD": ["airdrop", "connect wallet", "private key", "seed phrase", "giveaway", "free bitcoin"],
    "ADVANCE_FEE": ["advance payment", "processing fee", "clearance fee", "unlock fee", "transfer fee"],
}

# ============================================================
# DATABASE
# ============================================================
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db():
    return psycopg2.connect(
        host="127.0.0.1",
        database="gfin",
        user="gfin",
        password="",
        port=5432,
    )

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_intelligence (
            id SERIAL PRIMARY KEY,
            message_id BIGINT,
            group_id BIGINT,
            group_name TEXT,
            sender_id BIGINT,
            sender_name TEXT,
            sender_username TEXT,
            message_text TEXT,
            wallets JSONB DEFAULT '[]',
            domains JSONB DEFAULT '[]',
            phones JSONB DEFAULT '[]',
            ips JSONB DEFAULT '[]',
            usernames JSONB DEFAULT '[]',
            is_victim BOOLEAN DEFAULT FALSE,
            victim_patterns JSONB DEFAULT '[]',
            scam_type TEXT,
            scam_indicators JSONB DEFAULT '[]',
            risk_level TEXT DEFAULT 'LOW',
            processed BOOLEAN DEFAULT FALSE,
            investigated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_groups (
            id SERIAL PRIMARY KEY,
            group_id BIGINT UNIQUE,
            group_name TEXT,
            group_username TEXT,
            member_count INTEGER DEFAULT 0,
            is_monitored BOOLEAN DEFAULT TRUE,
            first_seen TIMESTAMP DEFAULT NOW(),
            last_activity TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_wallets (
            id SERIAL PRIMARY KEY,
            wallet_address TEXT UNIQUE,
            wallet_type TEXT,
            first_seen_group TEXT,
            first_seen_sender TEXT,
            mention_count INTEGER DEFAULT 1,
            last_seen TIMESTAMP DEFAULT NOW(),
            investigated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_domains (
            id SERIAL PRIMARY KEY,
            domain TEXT UNIQUE,
            first_seen_group TEXT,
            first_seen_sender TEXT,
            mention_count INTEGER DEFAULT 1,
            investigated BOOLEAN DEFAULT FALSE,
            scam_detected BOOLEAN DEFAULT FALSE,
            risk_level TEXT DEFAULT 'UNKNOWN',
            created_at TIMESTAMP DEFAULT NOW(),
            last_seen TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database tables initialized")

# ============================================================
# INTELLIGENCE EXTRACTION
# ============================================================

def extract_wallets(text):
    wallets = []
    for wtype, pattern in WALLET_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            addr = match.group(0)
            # Validate
            if wtype == "ETH" and not addr.startswith("0x"):
                continue
            if wtype == "BTC" and not (addr.startswith("1") or addr.startswith("3")):
                continue
            if wtype == "TRON" and not addr.startswith("T"):
                continue
            if wtype == "XRP" and not addr.startswith("r"):
                continue
            # Base58 validation (no 0, O, I, l in non-hex addresses)
            _BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            if wtype not in ("ETH", "BTC_BECH32"):
                if not all(c in _BASE58 for c in addr):
                    continue
            # Reject if contains common words (false positive guard)
            if wtype in ("DOGE", "LTC") and any(w in addr.lower() for w in ["number", "trunk", "call", "center", "phone", "support"]):
                continue
            wallets.append({"type": wtype, "address": addr})
    # Deduplicate
    seen = set()
    unique = []
    for w in wallets:
        key = f"{w['type']}:{w['address']}"
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique

def extract_domains(text):
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
    return domains

def extract_phones(text):
    return list(set(re.findall(PHONE_PATTERN, text)))

def extract_ips(text):
    return list(set(re.findall(IP_PATTERN, text)))

def extract_usernames(text):
    return list(set(re.findall(USERNAME_MENTION, text)))

def detect_victim(text):
    text_lower = text.lower()
    matched = []
    for pattern in VICTIM_PATTERNS:
        if re.search(pattern, text_lower):
            matched.append(pattern)
    return len(matched) > 0, matched

def detect_scam(text):
    text_lower = text.lower()
    indicators = []
    for indicator in SCAM_INDICATORS:
        if indicator in text_lower:
            indicators.append(indicator)
    
    scam_type = None
    for stype, keywords in SCAM_TYPE_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                scam_type = stype
                break
        if scam_type:
            break
    
    return scam_type, indicators

def calculate_risk(wallets, domains, is_victim, scam_indicators, scam_type):
    score = 0
    if wallets:
        score += 30
    if domains:
        score += 25
    if scam_indicators:
        score += min(20 * len(scam_indicators), 40)
    if scam_type:
        score += 20
    if is_victim:
        return "VICTIM"
    if score >= 60:
        return "CRITICAL"
    elif score >= 40:
        return "HIGH"
    elif score >= 20:
        return "MEDIUM"
    return "LOW"

# ============================================================
# GFIN API INTEGRATION
# ============================================================

def investigate_domain(domain, group_name="", sender_name=""):
    """Send domain to GFIN Hunter Playbook for full investigation.
    Calls /api/playbook/investigate which traces:
    Subject -> WHOIS -> DNS -> SSL -> Hosting -> Content -> IP Geolocation -> Physical Address
    """
    try:
        trigger_reason = f"Domain detected in Telegram group '{group_name}' by {sender_name}"
        params = urllib.parse.urlencode({
            "identifier": domain,
            "identifier_type": "DOMAIN",
            "trigger": "TELEGRAM_INTEL",
            "trigger_reason": trigger_reason,
            "operator": "GFIN_SPY",
        })
        url = f"{GFIN_API}/api/playbook/investigate?{params}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = urllib.request.urlopen(url, timeout=45, context=ctx)
        result = json.loads(resp.read())
        
        # Store investigation results in telegram_domains table
        if result:
            summary = result.get("summary", {})
            confidence = result.get("confidence", 0)
            accusation = result.get("accusation_level", "UNKNOWN")
            locations = result.get("physical_locations", [])
            evidence_count = summary.get("evidence_steps", 0)
            
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE telegram_domains 
                SET investigated = TRUE,
                    scam_detected = %s,
                    risk_level = %s
                WHERE domain = %s
            """, (
                confidence > 0.5,
                "CRITICAL" if confidence > 0.7 else "HIGH" if confidence > 0.4 else "MEDIUM" if confidence > 0.2 else "LOW",
                domain
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"  HUNTER: {domain} -> confidence={confidence}, accusation={accusation}, "
                       f"evidence_steps={evidence_count}, locations={len(locations)}")
            
            # Periodic MIDAS stats
        if MIDAS_AVAILABLE and not hasattr(process_message, '_msg_count'):
            process_message._msg_count = 0
        if MIDAS_AVAILABLE:
            process_message._msg_count += 1
            if process_message._msg_count % 100 == 0:
                stats = midas_pipeline.midas.get_stats()
                logger.info(f"  📊 MIDAS: {stats['edges_processed']} edges, {stats['anomalies_detected']} anomalies, {stats['recent_anomalies']} recent")
        
        # Log physical locations if found
            for loc in locations[:3]:
                city = loc.get("city", "?")
                country = loc.get("country", "?")
                org = loc.get("hosting_org", loc.get("organization", ""))
                logger.info(f"    LOCATION: {city}, {country} ({org})")
        
        return result
    except Exception as e:
        logger.debug(f"Investigate domain {domain}: {e}")
        return None

def check_domain_scam(domain):
    """Check if domain is a known scam site."""
    try:
        url = f"{GFIN_API}/api/scam-sites/check/{domain}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = urllib.request.urlopen(url, timeout=10, context=ctx)
        return json.loads(resp.read())
    except:
        return None

# ============================================================
# STORE INTELLIGENCE
# ============================================================

def store_intel(msg_data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO telegram_intelligence
        (message_id, group_id, group_name, sender_id, sender_name, sender_username,
         message_text, wallets, domains, phones, ips, usernames,
         is_victim, victim_patterns, scam_type, scam_indicators, risk_level)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        msg_data["message_id"], msg_data["group_id"], msg_data["group_name"],
        msg_data["sender_id"], msg_data["sender_name"], msg_data["sender_username"],
        msg_data["message_text"][:5000],
        json.dumps(msg_data["wallets"]),
        json.dumps(msg_data["domains"]),
        json.dumps(msg_data["phones"]),
        json.dumps(msg_data["ips"]),
        json.dumps(msg_data["usernames"]),
        msg_data["is_victim"],
        json.dumps(msg_data["victim_patterns"]),
        msg_data["scam_type"],
        json.dumps(msg_data["scam_indicators"]),
        msg_data["risk_level"],
    ))
    
    # Store wallets
    for w in msg_data["wallets"]:
        cur.execute("""
            INSERT INTO telegram_wallets (wallet_address, wallet_type, first_seen_group, first_seen_sender)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (wallet_address) DO UPDATE SET
                mention_count = telegram_wallets.mention_count + 1,
                last_seen = NOW()
        """, (w["address"], w["type"], msg_data["group_name"], msg_data["sender_name"]))
    
    # Store domains
    for d in msg_data["domains"]:
        cur.execute("""
            INSERT INTO telegram_domains (domain, first_seen_group, first_seen_sender)
            VALUES (%s, %s, %s)
            ON CONFLICT (domain) DO UPDATE SET
                mention_count = telegram_domains.mention_count + 1,
                last_seen = NOW()
        """, (d, msg_data["group_name"], msg_data["sender_name"]))
    
    conn.commit()
    conn.close()

def register_group(group_id, group_name, group_username, member_count=0):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO telegram_groups (group_id, group_name, group_username, member_count, last_activity)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (group_id) DO UPDATE SET
            group_name = EXCLUDED.group_name,
            member_count = EXCLUDED.member_count,
            last_activity = NOW()
    """, (group_id, group_name, group_username, member_count))
    conn.commit()
    conn.close()

# ============================================================
# TELETHON CLIENT
# ============================================================

client = None

async def init_client():
    global client
    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH,
        device_model="GFIN Spy Client",
        system_version="2.0",
        app_version="GFIN Intel v2.0",
        lang_code="en",
        system_lang_code="en",
    )
    await client.start()
    me = await client.get_me()
    logger.info(f"Logged in as: {me.first_name} (@{me.username}) [ID: {me.id}]")
    logger.info(f"Phone: {me.phone}")
    return me

async def process_message(event):
    """Process every message in every group the user is a member of."""
    try:
        # Skip if no text
        text = event.raw_text or ""
        if not text or len(text) < 3:
            return
        
        # Get chat info
        chat = await event.get_chat()
        sender = await event.get_sender()
        
        # Determine group/chat name
        group_name = ""
        group_username = None
        if hasattr(chat, "title"):
            group_name = chat.title
            if hasattr(chat, "username") and chat.username:
                group_username = chat.username
        elif hasattr(chat, "first_name"):
            group_name = f"DM:{chat.first_name}"
        else:
            group_name = str(chat.id) if hasattr(chat, "id") else "Unknown"
        
        group_id = chat.id if hasattr(chat, "id") else 0
        
        # Skip channels (we want groups)
        # But still process if it's a group or supergroup
        
        # Get sender info
        sender_name = ""
        sender_username = ""
        sender_id = 0
        if sender:
            if hasattr(sender, "first_name"):
                sender_name = (sender.first_name or "") + " " + (sender.last_name or "")
            elif hasattr(sender, "title"):
                sender_name = sender.title
            sender_name = sender_name.strip()
            if hasattr(sender, "username") and sender.username:
                sender_username = sender.username
            sender_id = sender.id if hasattr(sender, "id") else 0
        
        # Skip our own messages
        if sender_id == (await client.get_me()).id:
            return
        
        # ============================================================
        # EXTRACT INTELLIGENCE
        # ============================================================
        wallets = extract_wallets(text)
        domains = extract_domains(text)
        phones = extract_phones(text)
        ips = extract_ips(text)
        usernames = extract_usernames(text)
        is_victim, victim_patterns = detect_victim(text)
        scam_type, scam_indicators = detect_scam(text)
        risk_level = calculate_risk(wallets, domains, is_victim, scam_indicators, scam_type)
        
        # Skip if nothing interesting
        if not wallets and not domains and not is_victim and not scam_indicators and not phones:
            return
        
        # Register the group
        register_group(group_id, group_name, group_username)
        
        
        # Money Laundering Detection
        try:
            laundering_result = detect_money_laundering(text)
            if laundering_result["is_laundering"]:
                laundering_alert = create_laundering_alert(
                    source="telegram_spy",
                    group_name=group_title,
                    group_username=group_username,
                    message_text=text,
                    detected=laundering_result
                )
                # Save to laundering alerts file
                import json

                alerts_file = "/gfin/laundering_alerts.json"
                try:
                    with open(alerts_file, "r") as af:
                        alerts = json.load(af)
                except:
                    alerts = []
                alerts.append(laundering_alert)
                with open(alerts_file, "w") as af:
                    json.dump(alerts, af, indent=2)
                
                print(f"  [LAUNDERING ALERT] {laudering_result['risk_level']} - {group_title} - Score: {laudering_result['risk_score']}")
                print(f"  Patterns: {laudering_result['detected_patterns']}")
                
                # Also store in intelligence database
                try:
                    import urllib.request
                    data = json.dumps({
                        "text": text,
                        "group_name": group_title,
                        "group_username": group_username,
                        "source": "telegram_spy"
                    }).encode()
                    req = urllib.request.Request(
                        "http://127.0.0.1:8000/api/laundering/analyze-message",
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=5)
                except:
                    pass
        except Exception as e:
            print(f"  Laundering detection error: {e}")

        # Store intelligence
        msg_data = {
            "message_id": event.id,
            "group_id": group_id,
            "group_name": group_name,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "sender_username": sender_username,
            "message_text": text,
            "wallets": wallets,
            "domains": domains,
            "phones": phones,
            "ips": ips,
            "usernames": usernames,
            "is_victim": is_victim,
            "victim_patterns": victim_patterns,
            "scam_type": scam_type,
            "scam_indicators": scam_indicators,
            "risk_level": risk_level,
        }
        store_intel(msg_data)
        
        # === STREAM THROUGH MIDAS FOR REAL-TIME ANOMALY DETECTION ===
        if MIDAS_AVAILABLE:
            try:
                sender_node = sender_username or sender_name or f"user_{sender_id}"
                anomalies = []
                # Process locally AND send to server API (dual: local + shared)
                def midas_add(src, dst):
                    result = midas_pipeline.midas.add_edge(src, dst)
                    try:
                        req = urllib.request.Request(
                            f"{GFIN_API}/api/midas/internal/edge",
                            data=json.dumps({"src": src, "dst": dst}).encode(),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        urllib.request.urlopen(req, timeout=2)
                    except:
                        pass
                    return result
                for w in wallets:
                    result = midas_add(sender_node, f"WALLET:{w['address']}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Wallet {w['address'][:15]}... score={result['combined_score']:.1f}")
                for d in domains:
                    result = midas_add(sender_node, f"DOMAIN:{d}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Domain {d} score={result['combined_score']:.1f}")
                for p in phones:
                    result = midas_add(sender_node, f"PHONE:{p}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Phone {p} score={result['combined_score']:.1f}")
                for ip in ips:
                    result = midas_add(sender_node, f"IP:{ip}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"IP {ip} score={result['combined_score']:.1f}")
                for u in usernames:
                    result = midas_add(sender_node, f"USER:{u}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"User @{u} score={result['combined_score']:.1f}")
                midas_add(f"GROUP:{group_name}", sender_node)
                if scam_type:
                    midas_add(f"GROUP:{group_name}", f"SCAM:{scam_type}")
                if anomalies:
                    logger.warning(f"  MIDAS ANOMALY: {'; '.join(anomalies)}")
            except Exception as e:
                logger.debug(f"  MIDAS processing error: {e}")
        
        # Log
        intel_items = []
        if wallets:
            intel_items.append(f"{len(wallets)} wallets")
        if domains:
            intel_items.append(f"{len(domains)} domains")
        if phones:
            intel_items.append(f"{len(phones)} phones")
        if is_victim:
            intel_items.append("VICTIM")
        if scam_type:
            intel_items.append(f"scam={scam_type}")
        
        logger.info(
            f"[{group_name}] {sender_name}: risk={risk_level}, "
            f"{', '.join(intel_items) if intel_items else 'low risk'}"
        )
        
        # ============================================================
        # AUTO-INVESTIGATE NEW DOMAINS
        # ============================================================
        for domain in domains:
            # Check if already investigated
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT investigated, scam_detected, risk_level FROM telegram_domains WHERE domain = %s", (domain,))
            existing = cur.fetchone()
            conn.close()
            
            if existing and existing[0]:  # already investigated
                if existing[1]:  # scam detected
                    logger.info(f"  KNOWN SCAM: {domain} (risk={existing[2]})")
                continue
            
            # Check if already known scam
            known = check_domain_scam(domain)
            if known and known.get("is_scam"):
                logger.info(f"  KNOWN SCAM: {domain} (risk={known.get('risk_level', '?')})")
                # Mark as investigated
                conn = get_db()
                cur = conn.cursor()
                cur.execute("UPDATE telegram_domains SET investigated = TRUE, scam_detected = TRUE, risk_level = 'CRITICAL' WHERE domain = %s", (domain,))
                conn.commit()
                conn.close()
                continue
            
            # Auto-investigate new domain via Hunter Playbook
            logger.info(f"  HUNTER INVESTIGATING: {domain} (from {group_name} by {sender_name})")
            result = investigate_domain(domain, group_name, sender_name)
            if result:
                confidence = result.get("confidence", 0)
                accusation = result.get("accusation_level", "")
                if confidence > 0.5 or accusation in ("SUSPICIOUS", "LIKELY_FRAUD", "FRAUDULENT"):
                    logger.info(f"  ⚠️ FLAGGED: {domain} confidence={confidence} accusation={accusation}")
                else:
                    logger.info(f"  ✓ CLEAN: {domain} confidence={confidence}")
        
        # ============================================================
        # VICTIM RESPONSE
        # ============================================================
        if is_victim:
            try:
                help_text = (
                    "🛡️ **GFIN Fraud Intelligence**\n\n"
                    "I detected you may have been affected by a scam. "
                    "You can report it to GFIN — the Global Fraud Intelligence Network.\n\n"
                    "📱 **Report here:** https://gfin-system.com/victim\n"
                    "🔍 **Check a domain:** https://gfin-system.com/scam-sites\n\n"
                    "GFIN works with law enforcement worldwide to track and shut down fraud operations."
                )
                await event.reply(help_text, link_preview=False)
                logger.info(f"  Sent victim help to {sender_name}")
            except Exception as e:
                logger.debug(f"  Could not reply: {e}")
        
        # ============================================================
        # KNOWN WALLET ALERT
        # ============================================================
        for w in wallets:
            # Could check wallet against blockchain APIs here
            logger.info(f"  WALLET: {w['type']} {w['address'][:20]}...")
        
    except Exception as e:
        logger.error(f"Process message error: {e}")

async def scan_history(group_entity, limit=100):
    """Scan recent message history of a group."""
    title = group_entity.title if hasattr(group_entity, 'title') else str(group_entity.id)
    logger.info(f"Scanning history of {title}...")
    count = 0
    intel_count = 0
    midas_edges = 0
    async for message in client.iter_messages(group_entity, limit=limit):
        if not message.text:
            continue
        count += 1
        text = message.text
        
        wallets = extract_wallets(text)
        domains = extract_domains(text)
        phones = extract_phones(text)
        ips = extract_ips(text)
        usernames = extract_usernames(text)
        is_victim, victim_patterns = detect_victim(text)
        scam_type, scam_indicators = detect_scam(text)
        risk_level = calculate_risk(wallets, domains, is_victim, scam_indicators, scam_type)
        
        if wallets or domains or is_victim or scam_indicators or phones:
            intel_count += 1
            sender = await message.get_sender()
            sender_name = (sender.first_name + " " + (sender.last_name or "")) if sender and hasattr(sender, "first_name") else "Unknown"
            sender_username = sender.username if sender and hasattr(sender, "username") else ""
            sender_id = sender.id if sender and hasattr(sender, "id") else 0
            
            if wallets:
                logger.info(f"  [HISTORY] {sender_name}: {len(wallets)} wallets")
            if domains:
                logger.info(f"  [HISTORY] {sender_name}: domains={domains[:3]}")
            if is_victim:
                logger.info(f"  [HISTORY] {sender_name}: VICTIM detected")
            if scam_type:
                logger.info(f"  [HISTORY] {sender_name}: scam={scam_type}")
            
            # Store intelligence in DB
            msg_data = {
                "message_id": message.id,
                "group_id": group_entity.id if hasattr(group_entity, 'id') else 0,
                "group_name": title,
                "sender_id": sender_id,
                "sender_name": sender_name.strip(),
                "sender_username": sender_username or "",
                "message_text": text[:5000],
                "wallets": wallets,
                "domains": domains,
                "phones": phones,
                "ips": ips,
                "usernames": usernames,
                "is_victim": is_victim,
                "victim_patterns": victim_patterns,
                "scam_type": scam_type,
                "scam_indicators": scam_indicators,
                "risk_level": risk_level,
            }
            store_intel(msg_data)
            
            # Stream through MIDAS (local + server API)
            if MIDAS_AVAILABLE:
                try:
                    snode = sender_username or sender_name.strip() or f"user_{sender_id}"
                    def hist_midas_add(src, dst):
                        midas_pipeline.midas.add_edge(src, dst)
                        try:
                            req = urllib.request.Request(
                                f"{GFIN_API}/api/midas/internal/edge",
                                data=json.dumps({"src": src, "dst": dst}).encode(),
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            )
                            urllib.request.urlopen(req, timeout=1)
                        except:
                            pass
                    for w in wallets:
                        hist_midas_add(snode, f"WALLET:{w['address']}")
                        midas_edges += 1
                    for d in domains:
                        hist_midas_add(snode, f"DOMAIN:{d}")
                        midas_edges += 1
                    for p in phones:
                        hist_midas_add(snode, f"PHONE:{p}")
                    for ip in ips:
                        hist_midas_add(snode, f"IP:{ip}")
                    for u in usernames:
                        hist_midas_add(snode, f"USER:{u}")
                    hist_midas_add(f"GROUP:{title}", snode)
                    if scam_type:
                        hist_midas_add(f"GROUP:{title}", f"SCAM:{scam_type}")
                except Exception as e:
                    pass
    
    logger.info(f"  Scanned {count} messages, {intel_count} with intelligence, {midas_edges} MIDAS edges")

async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("GFIN TELEGRAM USER SPY v2.0 - STARTING")
    logger.info("=" * 60)
    
    if not API_ID or not API_HASH:
        logger.error("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH environment variables")
        logger.error("Set them in /gfin/.env.telegram")
        sys.exit(1)
    
    init_db()
    
    # Initialize and authenticate
    me = await init_client()
    
    # List all groups/chats the user is a member of
    logger.info("=" * 60)
    logger.info("CONNECTED GROUPS & CHATS")
    logger.info("=" * 60)
    
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if hasattr(entity, "title") or hasattr(entity, "first_name"):
            name = dialog.title or dialog.name
            is_group = hasattr(entity, "title") and not hasattr(entity, "first_name")
            logger.info(f"  {'[GROUP]' if is_group else '[CHAT]'} {name} (ID: {dialog.id})")
            
            if is_group:
                # Register the group
                group_username = entity.username if hasattr(entity, "username") else None
                register_group(dialog.id, name, group_username, 0)
                
                # Scan recent history
                await scan_history(entity, limit=500)
    
    logger.info("=" * 60)
    logger.info("LIVE MONITORING STARTED")
    logger.info("=" * 60)
    logger.info("Listening for new messages in all groups...")
    
    # Register handler for ALL new messages
    @client.on(events.NewMessage())
    async def handler(event):
        await process_message(event)
    
    # Run forever
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

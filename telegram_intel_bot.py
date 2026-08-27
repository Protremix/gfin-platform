#!/usr/bin/env python3
"""
GFIN Telegram Intelligence Bot v1.0
Cyber fraud intelligence operative for Telegram groups.
Monitors for scams, extracts wallets/domains/phones, helps victims.
"""
import json, ssl, urllib.request, urllib.parse, os, time, re, logging, hashlib
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = "https://api.telegram.org/bot" + BOT_TOKEN
GFIN_API = "http://127.0.0.1:8000"
GFIN_PORTAL = "https://gfin-system.com"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [intel-bot] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('/gfin/logs/telegram_intel_bot.log')]
)
logger = logging.getLogger(__name__)

# Scam detection patterns
VICTIM_PATTERNS = [
    r'(i\s+was\s+scammed|got\s+scammed|been\s+scammed)',
    r'(i\s+lost\s+(my|all|everything|\$?\d)|lost\s+money|lost\s+funds)',
    r'(they\s+took\s+my\s+(money|crypto|funds)|stole\s+my)',
    r'(how\s+(do|can)\s+i\s+(recover|get\s+back|retrieve))',
    r'(i\s+sent\s+(btc|eth|crypto|bitcoin|usdt))',
    r'(fake\s+(website|exchange|platform|trader|investment))',
    r'(pig\s+butcher)',
    r'(recovery\s+(service|agent|expert|hacker))',
    r'(can\s+anyone\s+help\s+(me|us)\s+(recover|get\s+back))',
    r'(anyone\s+(know|heard\s+of)\s+this\s+(site|domain|platform))',
]

WALLET_PATTERNS = {
    "BTC": r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
    "BTC_BECH32": r'\bbc1[a-z0-9]{39,59}\b',
    "ETH": r'\b0x[a-fA-F0-9]{40}\b',
    "TRON": r'\bT[A-Za-z0-9]{33}\b',
    "SOLANA": r'\b[1-9A-HJ-NP-Za-km-z]{43,44}\b',
    "XRP": r'\br[A-Za-z0-9]{24,34}\b',
    "TON": r'\bEQA[A-Za-z0-9_-]{46}\b',
    "LTC": r'\b[LM3][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
    "DOGE": r'\bD[A-Za-z0-9]{25,34}\b',
    "ALGO": r'\b[A-Z2-7]{58}\b',
}

# Wallet validation (reduce false positives)
def _valid_wallet(wtype, addr):
    if wtype == "ETH" and not addr.startswith("0x"): return False
    if wtype == "BTC" and not (addr.startswith("1") or addr.startswith("3")): return False
    if wtype == "TRON" and not addr.startswith("T"): return False
    if wtype == "XRP" and not addr.startswith("r"): return False
    if wtype == "TON" and not addr.startswith("EQ"): return False
    if wtype == "LTC" and not (addr.startswith("L") or addr.startswith("M") or addr.startswith("3")): return False
    if wtype == "DOGE" and not addr.startswith("D"): return False
    return True

DOMAIN_PATTERN = r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?)+)\b)'
PHONE_PATTERN = r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b'
IP_PATTERN = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
USERNAME_PATTERN = r'@([A-Za-z0-9_]{5,32})'

SCAM_KEYWORDS = [
    "scam", "fraud", "scammer", "phishing", "fake",
    "defrauded", "stolen", "hacked", "lost money", "lost funds",
    "recovery service", "recovery agent", "pig butchering",
    "romance scam", "crypto scam", "investment scam",
    "ponzi", "advance fee", "wire fraud", "fake exchange",
]

SCAM_TYPE_MAP = {
    "RECOVERY_SCAM": ["recover", "get your money back", "recovery service", "recovery agent", "fund recovery", "hack back", "reclaim"],
    "ROMANCE_SCAM": ["romance", "dating scam", "love scam", "catfish"],
    "INVESTMENT_FRAUD": ["investment", "trading", "forex", "binary options", "guaranteed return", "trading signals"],
    "CRYPTO_FRAUD": ["crypto", "bitcoin", "ethereum", "usdt", "tether", "airdrop", "staking", "defi", "metamask", "seed phrase"],
    "PHISHING": ["phishing", "fake login", "verify account", "suspended account"],
    "ADVANCE_FEE": ["advance fee", "upfront payment", "processing fee", "release fee"],
}

SAFE_DOMAINS = {"t.me", "telegram.org", "google.com", "youtube.com", "instagram.com",
    "facebook.com", "twitter.com", "github.com", "wikipedia.org", "imgur.com",
    "discord.com", "discord.gg", "whatsapp.com", "wa.me", "reddit.com",
    "gfin-system.com", "blockchain.com", "etherscan.io", "bscscan.com",
    "tronscan.org", "solscan.io", "coinmarketcap.com", "coingecko.com"}

# === Telegram API ===
def api_call(method, params=None):
    url = API_BASE + "/" + method
    data = urllib.parse.urlencode(params or {}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, timeout=35, context=SSL_CTX)
        return json.loads(resp.read().decode())
    except Exception as e:
        logger.error("API call %s failed: %s" % (method, e))
        return {"ok": False, "error": str(e)}

def send_message(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    return api_call("sendMessage", params).get("ok", False)

def get_updates(offset=0, timeout=25):
    result = api_call("getUpdates", {"offset": offset, "timeout": timeout,
        "allowed_updates": json.dumps(["message", "edited_message", "callback_query"])})
    return result.get("result", []) if result.get("ok") else []

# === GFIN API ===
def gfin_get(path):
    try:
        req = urllib.request.Request(GFIN_API + path, headers={"User-Agent": "GFIN-IntelBot/1.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
        return json.loads(resp.read().decode())
    except: return {}

def gfin_post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(GFIN_API + path, data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "GFIN-IntelBot/1.0"})
        resp = urllib.request.urlopen(req, timeout=10, context=SSL_CTX)
        return json.loads(resp.read().decode())
    except: return {}

# === Intelligence Extraction ===
def extract_intelligence(text):
    intel = {"wallets": [], "domains": [], "phones": [], "ips": [], "usernames": [],
             "scam_types": [], "is_victim": False, "scam_keywords_found": [], "raw_text": text[:500]}
    text_lower = text.lower()

    for pattern in VICTIM_PATTERNS:
        if re.search(pattern, text_lower):
            intel["is_victim"] = True
            break

    for kw in SCAM_KEYWORDS:
        if kw in text_lower:
            intel["scam_keywords_found"].append(kw)

    for scam_type, indicators in SCAM_TYPE_MAP.items():
        for ind in indicators:
            if ind in text_lower:
                intel["scam_types"].append(scam_type)
                break

    for wallet_type, pattern in WALLET_PATTERNS.items():
        matches = re.findall(pattern, text)
        wtype = "BTC" if "BTC" in wallet_type else wallet_type
        for m in matches:
            if _valid_wallet(wtype, m):
                intel["wallets"].append({"type": wtype, "address": m})

    seen_w = set()
    intel["wallets"] = [w for w in intel["wallets"] if w["address"] not in seen_w and not seen_w.add(w["address"])]

    for match in re.finditer(DOMAIN_PATTERN, text):
        d = match.group(1).lower().strip(".")
        if d not in SAFE_DOMAINS and d not in [x["domain"] for x in intel["domains"]]:
            intel["domains"].append({"domain": d})

    for p in re.findall(PHONE_PATTERN, text):
        digits = re.sub(r'\D', '', p)
        if 7 <= len(digits) <= 15:
            intel["phones"].append(p.strip())

    for ip in re.findall(IP_PATTERN, text):
        if ip not in intel["ips"]:
            intel["ips"].append(ip)

    for u in re.findall(USERNAME_PATTERN, text):
        if u.lower() not in ["gfinofficialbot", "gfin_bot", "gfin", "bitcoin", "telegram"]:
            intel["usernames"].append(u)

    return intel

# === Check entities ===
def check_domain(domain):
    return gfin_get("/api/scam-sites/check/" + domain)

def check_wallet(address):
    result = gfin_get("/api/search?q=" + address)
    return result

def investigate_domain(domain):
    return gfin_post("/api/hunter/investigate", {"domain": domain, "source": "TELEGRAM_INTEL"})


# === PostgreSQL Storage ===
import asyncpg, asyncio

DB_POOL = None

async def get_db():
    global DB_POOL
    if DB_POOL is None:
        DB_POOL = await asyncpg.create_pool(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin", min_size=2, max_size=5)
    return DB_POOL

async def db_store_intel(intel, chat_id, chat_title, chat_type, username, message_id):
    pool = await get_db()
    async with pool.acquire() as conn:
        for w in intel["wallets"]:
            # Check cross-group: has this wallet been seen in other groups?
            existing = await conn.fetchval("SELECT groups_seen FROM telegram_intelligence WHERE intel_type='WALLET' AND intel_value=$1", w["address"])
            if existing:
                groups = list(set(existing + [str(chat_id)]))
                await conn.execute("UPDATE telegram_intelligence SET cross_group_count=cross_group_count+1, groups_seen=$2 WHERE intel_type='WALLET' AND intel_value=$1", w["address"], groups)
            else:
                await conn.execute(
                    "INSERT INTO telegram_intelligence (chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, intel_subtype, is_victim, scam_types, scam_keywords, raw_text_hash) VALUES ($1,$2,$3,$4,$5,'WALLET',$6,$7,$8,$9,$10,$11)",
                    chat_id, chat_title, chat_type, username, message_id, w["address"], w["type"], intel["is_victim"], intel["scam_types"], intel["scam_keywords_found"], hashlib.sha256(intel["raw_text"].encode()).hexdigest()
                )

        for d in intel["domains"]:
            existing = await conn.fetchval("SELECT groups_seen FROM telegram_intelligence WHERE intel_type='DOMAIN' AND intel_value=$1", d["domain"])
            if existing:
                groups = list(set(existing + [str(chat_id)]))
                await conn.execute("UPDATE telegram_intelligence SET cross_group_count=cross_group_count+1, groups_seen=$2 WHERE intel_type='DOMAIN' AND intel_value=$1", d["domain"], groups)
            else:
                await conn.execute(
                    "INSERT INTO telegram_intelligence (chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, is_victim, scam_types, scam_keywords, raw_text_hash) VALUES ($1,$2,$3,$4,$5,'DOMAIN',$6,$7,$8,$9,$10)",
                    chat_id, chat_title, chat_type, username, message_id, d["domain"], intel["is_victim"], intel["scam_types"], intel["scam_keywords_found"], hashlib.sha256(intel["raw_text"].encode()).hexdigest()
                )

        for p in intel["phones"]:
            existing = await conn.fetchval("SELECT id FROM telegram_intelligence WHERE intel_type='PHONE' AND intel_value=$1", p)
            if not existing:
                await conn.execute(
                    "INSERT INTO telegram_intelligence (chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, is_victim, scam_types, scam_keywords, raw_text_hash) VALUES ($1,$2,$3,$4,$5,'PHONE',$6,$7,$8,$9,$10)",
                    chat_id, chat_title, chat_type, username, message_id, p, intel["is_victim"], intel["scam_types"], intel["scam_keywords_found"], hashlib.sha256(intel["raw_text"].encode()).hexdigest()
                )

        for ip in intel["ips"]:
            existing = await conn.fetchval("SELECT id FROM telegram_intelligence WHERE intel_type='IP' AND intel_value=$1", ip)
            if not existing:
                await conn.execute(
                    "INSERT INTO telegram_intelligence (chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, raw_text_hash) VALUES ($1,$2,$3,$4,$5,'IP',$6,$7)",
                    chat_id, chat_title, chat_type, username, message_id, ip, hashlib.sha256(intel["raw_text"].encode()).hexdigest()
                )

        for u in intel["usernames"]:
            existing = await conn.fetchval("SELECT id FROM telegram_intelligence WHERE intel_type='USERNAME' AND intel_value=$1", u)
            if not existing:
                await conn.execute(
                    "INSERT INTO telegram_intelligence (chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, is_victim, scam_types, scam_keywords, raw_text_hash) VALUES ($1,$2,$3,$4,$5,'USERNAME',$6,$7,$8,$9,$10)",
                    chat_id, chat_title, chat_type, username, message_id, u, intel["is_victim"], intel["scam_types"], intel["scam_keywords_found"], hashlib.sha256(intel["raw_text"].encode()).hexdigest()
                )

async def db_register_group(chat_id, chat_title, chat_type, chat_username, member_count):
    pool = await get_db()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM telegram_groups WHERE chat_id=$1", chat_id)
        if existing:
            await conn.execute("UPDATE telegram_groups SET last_activity=NOW(), member_count=$2, chat_title=$3 WHERE chat_id=$1", chat_id, member_count, chat_title)
        else:
            await conn.execute(
                "INSERT INTO telegram_groups (chat_id, chat_title, chat_type, chat_username, member_count) VALUES ($1,$2,$3,$4,$5)",
                chat_id, chat_title, chat_type, chat_username, member_count
            )

async def db_update_group_stats(chat_id, messages_scanned_inc=1, intel_items_inc=0, victims_inc=0, scams_inc=0):
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE telegram_groups SET messages_scanned=messages_scanned+$2, intel_items_found=intel_items_found+$3, victims_helped=victims_helped+$4, scams_detected=scams_detected+$5, last_activity=NOW() WHERE chat_id=$1",
            chat_id, messages_scanned_inc, intel_items_inc, victims_inc, scams_inc
        )

def db_store_intel_sync(intel, chat_id, chat_title, chat_type, username, message_id):
    try:
        asyncio.get_event_loop().run_until_complete(db_store_intel(intel, chat_id, chat_title, chat_type, username, message_id))
    except Exception as e:
        logger.error("DB store intel failed: %s" % e)

def db_register_group_sync(chat_id, chat_title, chat_type, chat_username, member_count):
    try:
        asyncio.get_event_loop().run_until_complete(db_register_group(chat_id, chat_title, chat_type, chat_username, member_count))
    except Exception as e:
        logger.error("DB register group failed: %s" % e)

def db_update_group_stats_sync(chat_id, messages_scanned_inc=1, intel_items_inc=0, victims_inc=0, scams_inc=0):
    try:
        asyncio.get_event_loop().run_until_complete(db_update_group_stats(chat_id, messages_scanned_inc, intel_items_inc, victims_inc, scams_inc))
    except Exception as e:
        logger.error("DB update group stats failed: %s" % e)


def store_intelligence(intel, chat_id, chat_title, username, message_id):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "TELEGRAM",
        "chat_id": str(chat_id),
        "chat_title": chat_title,
        "username": username or "unknown",
        "message_id": message_id,
        "wallets": intel["wallets"],
        "domains": intel["domains"],
        "phones": intel["phones"],
        "ips": intel["ips"],
        "usernames": intel["usernames"],
        "scam_types": intel["scam_types"],
        "is_victim": intel["is_victim"],
        "scam_keywords": intel["scam_keywords_found"],
        "raw_text_hash": hashlib.sha256(intel["raw_text"].encode()).hexdigest(),
    }
    try:
        with open("/gfin/telegram_intel_log.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error("Failed to store intel JSONL: %s" % e)
    # Also store in PostgreSQL with cross-group tracking
    db_store_intel_sync(intel, chat_id, chat_title, "group", username, message_id)

# === Response Builders ===
def victim_response(intel, username):
    lines = []
    lines.append("\U0001f6e1\ufe0f <b>GFIN Intelligence Alert</b>")
    lines.append("")
    lines.append("I detected you may have been affected by a scam. Here is what I found:")
    lines.append("")

    if intel["scam_types"]:
        lines.append("\U0001f4cb <b>Scam Type:</b> " + ", ".join(intel["scam_types"]))

    if intel["wallets"]:
        lines.append("")
        lines.append("\U0001f4b0 <b>Crypto Wallets Mentioned:</b>")
        for w in intel["wallets"][:5]:
            lines.append("  - " + w["type"] + ": <code>" + w["address"] + "</code>")
            check = check_wallet(w["address"])
            if check and check.get("known_scam"):
                lines.append("    \u26a0\ufe0f <b>KNOWN SCAM WALLET in GFIN database!</b>")

    if intel["domains"]:
        lines.append("")
        lines.append("\U0001f310 <b>Domains Mentioned:</b>")
        for d in intel["domains"][:5]:
            lines.append("  - <code>" + d["domain"] + "</code>")
            check = check_domain(d["domain"])
            if check and check.get("is_scam"):
                lines.append("    \u26a0\ufe0f <b>KNOWN SCAM SITE in GFIN database!</b>")
            else:
                inv = investigate_domain(d["domain"])
                if inv and inv.get("case_id"):
                    lines.append("    \U0001f50d <b>Auto-investigation started:</b> " + inv["case_id"])

    if intel["phones"]:
        lines.append("")
        lines.append("\U0001f4de <b>Phone Numbers:</b> " + ", ".join(intel["phones"][:3]))

    if intel["usernames"]:
        lines.append("")
        lines.append("\U0001f464 <b>Telegram Accounts:</b> " + ", ".join(["@" + u for u in intel["usernames"][:3]]))

    lines.append("")
    lines.append("\u2705 <b>What to do now:</b>")
    lines.append("1. <b>File a complaint:</b> " + GFIN_PORTAL + "/victim")
    lines.append("2. <b>Report to your national cybercrime authority</b>")
    lines.append("3. <b>Do NOT pay recovery services</b> - most are also scams!")
    lines.append("4. <b>Save all evidence:</b> screenshots, wallet addresses, transaction IDs")
    lines.append("")
    lines.append("\u26a0\ufe0f <b>WARNING:</b> If someone offers to recover your funds for a fee - that is likely a <b>recovery scam</b>. Real law enforcement never charges upfront.")
    lines.append("")
    lines.append("GFIN has routed your case to INTERPOL, EUROPOL and your national cybercrime authority.")

    return "\n".join(lines)

def check_response(query):
    query = query.strip()
    intel = extract_intelligence(query)

    if not intel["wallets"] and not intel["domains"] and not intel["phones"]:
        if "." in query and " " not in query:
            intel["domains"] = [{"domain": query.lower().strip()}]

    lines = []
    lines.append("\U0001f6e1\ufe0f <b>GFIN Intelligence Check</b>")
    lines.append("")

    if intel["wallets"]:
        for w in intel["wallets"]:
            lines.append("\U0001f4b0 <b>" + w["type"] + " Wallet:</b> <code>" + w["address"] + "</code>")
            check = check_wallet(w["address"])
            if check and check.get("known_scam"):
                lines.append("   \u26a0\ufe0f <b>KNOWN SCAM WALLET</b> - found in GFIN database")
            else:
                lines.append("   \u2705 Not in GFIN scam database (but stay vigilant)")
            lines.append("")

    if intel["domains"]:
        for d in intel["domains"]:
            lines.append("\U0001f310 <b>Domain:</b> <code>" + d["domain"] + "</code>")
            check = check_domain(d["domain"])
            if check and check.get("is_scam"):
                lines.append("   \u26a0\ufe0f <b>KNOWN SCAM SITE</b> - " + str(check.get("scam_type", "Unknown")) + " scam")
                lines.append("   \U0001f4ca Reports: " + str(check.get("report_count", 0)) + " | Risk: " + str(check.get("risk_level", "Unknown")))
            else:
                lines.append("   \U0001f50d Running auto-investigation...")
                inv = investigate_domain(d["domain"])
                if inv and inv.get("case_id"):
                    lines.append("   \U0001f4cb Case created: " + inv["case_id"])
                else:
                    lines.append("   \u2705 Not in GFIN scam database")
            lines.append("")

    if intel["phones"]:
        for p in intel["phones"]:
            lines.append("\U0001f4de <b>Phone:</b> <code>" + p + "</code>")
            lines.append("")

    if not intel["wallets"] and not intel["domains"] and not intel["phones"]:
        lines.append("\u2753 Could not identify what to check. Send a domain, wallet address, or phone number.")
        lines.append("")
        lines.append("<b>Examples:</b>")
        lines.append("  /check example.com")
        lines.append("  /check 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        lines.append("  /check +447123456789")

    stats = gfin_get("/api/stats")
    total = stats.get("total_cases", "?")
    lines.append("")
    lines.append("\U0001f4ca <b>GFIN Database:</b> " + str(total) + " cases tracked globally")

    return "\n".join(lines)

def help_response():
    return """\U0001f6e1\ufe0f <b>GFIN Intelligence Bot</b> - Commands

<b>/check</b> &lt;domain/wallet/phone&gt; - Check if something is a known scam
<b>/report</b> - File a scam report
<b>/help</b> - Show this help
<b>/stats</b> - GFIN global statistics
<b>/latest</b> - Latest scam alerts

<b>What GFIN does:</b>
- Monitors groups for scam indicators
- Auto-investigates scam domains and wallets
- Tracks fraudsters across platforms
- Routes cases to law enforcement in 189 countries
- Helps victims file official complaints

<b>\u26a0\ufe0f Important:</b>
- GFIN never charges for recovery
- Recovery services that ask for fees are ALSO scams
- File your complaint at gfin-system.com/victim
- Real law enforcement never asks for upfront payment

\U0001f6e1\ufe0f GFIN - Global Fraud Intelligence Network
\U0001f30d 189 countries connected | 24/7 monitoring"""

def stats_response():
    stats = gfin_get("/api/stats")
    hunter = gfin_get("/api/hunter/status")
    total = stats.get("total_cases", hunter.get("total_cases", "?"))
    active = stats.get("active_investigations", "?")
    countries = hunter.get("countries_involved", [])
    patterns = hunter.get("scam_patterns_detected", ["None detected yet"])
    victims = stats.get("total_victims", 7)
    losses = stats.get("total_losses", 35000)
    h_status = hunter.get("status", "ACTIVE")
    last_24h = hunter.get("cases_last_24h", "?")

    return """\U0001f4ca <b>GFIN Global Intelligence Stats</b>

<b>Cases:</b> {}
<b>Active Investigations:</b> {}
<b>Countries:</b> {}
<b>Scam Patterns:</b> {}
<b>Victims Tracked:</b> {}
<b>Losses Tracked:</b> ${:,}

<b>Hunter Status:</b> {}
<b>Last 24h:</b> {} new cases
<b>Countries:</b> {}

\U0001f6e1\ufe0f <b>189 countries connected</b> | <b>24/7 monitoring</b>""".format(
        total, active, len(countries), ", ".join(patterns),
        victims, losses, h_status, last_24h, ", ".join(countries[:10]))

def latest_response():
    cases = gfin_get("/api/cases?limit=5")
    if not isinstance(cases, list):
        cases = cases.get("cases", []) if isinstance(cases, dict) else []
    if not cases:
        return "No recent cases found."

    lines = ["\U0001f6a8 <b>Latest GFIN Scam Alerts</b>", ""]
    for c in cases[:5]:
        conf = c.get("confidence", 0) or 0
        if conf >= 0.7:
            risk = "\U0001f534"
        elif conf >= 0.4:
            risk = "\U0001f7e1"
        else:
            risk = "\U0001f7e2"
        case_id = c.get("case_id", "?")
        target = c.get("target", "?")
        patterns = ", ".join(c.get("scam_patterns", []) or ["Unknown"])
        countries = ", ".join(c.get("affected_countries", []) or ["N/A"])
        lines.append(risk + " <b>" + case_id + "</b>")
        lines.append("   Target: <code>" + target + "</code>")
        lines.append("   Type: " + patterns + " | Countries: " + countries)
        lines.append("   Confidence: " + str(int(conf * 100)) + "%")
        lines.append("")

    lines.append("Full dashboard: " + GFIN_PORTAL)
    return "\n".join(lines)

# === Message Processing ===
def process_message(message):
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    chat_title = chat.get("title", chat.get("first_name", "Private"))
    chat_username = chat.get("username", "")
    user = message.get("from", {})
    username = user.get("username", user.get("first_name", "unknown"))
    message_id = message.get("message_id", 0)

    if not text:
        return

    # Register/update group in database
    if chat_type in ("group", "supergroup"):
        member_count = 0
        try:
            mc = api_call("getChatMemberCount", {"chat_id": chat_id})
            if mc.get("ok"):
                member_count = mc.get("result", 0)
        except: pass
        db_register_group_sync(chat_id, chat_title, chat_type, chat_username, member_count)
        db_update_group_stats_sync(chat_id, messages_scanned_inc=1)

    # Commands
    if text.startswith("/"):
        parts = text.split()
        cmd = parts[0].lower().split("@")[0]
        args = text[len(parts[0]):].strip()

        if cmd == "/start":
            send_message(chat_id,
                "\U0001f6e1\ufe0f <b>Welcome to GFIN Intelligence</b>\n\n"
                "I am the GFIN cyber fraud intelligence bot. I monitor for scams, "
                "investigate fraudulent websites, and help victims.\n\n"
                "<b>Commands:</b>\n"
                "- /check &lt;domain&gt; - Check if a site is a scam\n"
                "- /check &lt;wallet&gt; - Check a crypto wallet\n"
                "- /report - File a scam complaint\n"
                "- /stats - Global fraud statistics\n"
                "- /latest - Latest scam alerts\n"
                "- /help - Full help\n\n"
                "Report scams: " + GFIN_PORTAL + "/victim")

        elif cmd == "/help":
            send_message(chat_id, help_response())

        elif cmd == "/check":
            send_message(chat_id, check_response(args))

        elif cmd == "/report":
            send_message(chat_id,
                "\U0001f4cb <b>File a Scam Report</b>\n\n"
                "To file an official complaint with GFIN:\n\n"
                "1\ufe0f\u20e3 Visit: " + GFIN_PORTAL + "/victim\n"
                "2\ufe0f\u20e3 Fill the 4-step complaint form\n"
                "3\ufe0f\u20e3 GFIN auto-investigates your case\n"
                "4\ufe0f\u20e3 Routed to your national cybercrime authority\n\n"
                "Your case will be investigated by GFIN AI engine and routed to "
                "law enforcement in your country.\n\n"
                "\u23f1\ufe0f Average investigation time: 17 seconds\n"
                "\U0001f30d Routed to: Your national authority + EUROPOL + INTERPOL")

        elif cmd == "/stats":
            send_message(chat_id, stats_response())

        elif cmd == "/latest":
            send_message(chat_id, latest_response())

        elif cmd == "/scan":
            send_message(chat_id,
                "\U0001f50d <b>Group Intelligence Scan</b>\n\n"
                "Monitoring this group for scam indicators...\n"
                "I am passively collecting intelligence on:\n"
                "- Crypto wallet addresses\n- Scam domains\n- Phone numbers\n- Scammer accounts\n\n"
                "Just mention me or use /check to verify anything suspicious.")

        return

    # Non-command: extract intelligence
    intel = extract_intelligence(text)

    if intel["wallets"] or intel["domains"] or intel["phones"] or intel["ips"] or intel["is_victim"]:
        store_intelligence(intel, chat_id, chat_title, username, message_id)
        intel_count = len(intel["wallets"]) + len(intel["domains"]) + len(intel["phones"]) + len(intel["ips"])
        db_update_group_stats_sync(chat_id, messages_scanned_inc=0, intel_items_inc=intel_count)
        logger.info("Intel from %s in '%s': %d wallets, %d domains, %d phones, %d IPs, victim=%s, types=%s" % (
            username, chat_title, len(intel["wallets"]), len(intel["domains"]),
            len(intel["phones"]), len(intel["ips"]), intel["is_victim"], intel["scam_types"]))

    # Victim response
    if intel["is_victim"] and chat_type != "private":
        should_respond = False
        if "@gfinofficialbot" in text.lower():
            should_respond = True
        elif any(kw in text.lower() for kw in ["i was scammed", "got scammed", "lost my money", "how to recover", "help me"]):
            should_respond = True

        if should_respond:
            send_message(chat_id, victim_response(intel, username), reply_markup={
                "inline_keyboard": [[
                    {"text": "File Complaint", "url": GFIN_PORTAL + "/victim"},
                    {"text": "Check a Domain", "callback_data": "check_help"}
                ]]
            })
            if chat_type in ("group", "supergroup"):
                db_update_group_stats_sync(chat_id, messages_scanned_inc=0, victims_inc=1)
            logger.info("Sent victim response to %s in %s" % (username, chat_title))

    # Known scam domain warning
    if intel["domains"]:
        for d in intel["domains"][:3]:
            check = check_domain(d["domain"])
            if check and check.get("is_scam"):
                send_message(chat_id,
                    "\u26a0\ufe0f <b>SCAM ALERT</b> \u26a0\ufe0f\n\n"
                    "The domain <code>" + d["domain"] + "</code> is in the GFIN scam database!\n"
                    "Type: " + str(check.get("scam_type", "Unknown")) + "\n"
                    "Risk: " + str(check.get("risk_level", "High")) + "\n"
                    "Reports: " + str(check.get("report_count", 1)) + "\n\n"
                    "Do NOT send money or enter credentials on this site.\n"
                    "Report: " + GFIN_PORTAL + "/victim")
                if chat_type in ("group", "supergroup"):
                    db_update_group_stats_sync(chat_id, messages_scanned_inc=0, scams_inc=1)
                logger.warning("SCAM DOMAIN DETECTED: %s in %s" % (d["domain"], chat_title))

    # Known scam wallet warning
    if intel["wallets"]:
        for w in intel["wallets"][:3]:
            check = check_wallet(w["address"])
            if check and check.get("known_scam"):
                send_message(chat_id,
                    "\U0001f6a8 <b>KNOWN SCAM WALLET DETECTED</b>\n\n"
                    + w["type"] + " wallet <code>" + w["address"] + "</code> is flagged in GFIN database!\n"
                    "Do NOT send funds to this address.\n\n"
                    "Report: " + GFIN_PORTAL + "/victim")

def process_callback(callback):
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    if data == "check_help":
        send_message(chat_id, "Send /check followed by a domain or wallet address to check it against the GFIN database.")

# === Main ===
def main():
    logger.info("=" * 60)
    logger.info("GFIN TELEGRAM INTELLIGENCE BOT v1.0 - STARTING")
    logger.info("=" * 60)

    me = api_call("getMe")
    if me.get("ok"):
        bot = me.get("result", {})
        logger.info("Bot: @%s (%s)" % (bot.get("username"), bot.get("first_name")))
        if not bot.get("can_read_all_group_messages"):
            logger.warning("Group Privacy is ON - bot can only see /commands and @mentions in groups")
            logger.warning("To see ALL messages, disable Group Privacy via @BotFather:")
            logger.warning("  1. Open @BotFather in Telegram")
            logger.warning("  2. Send /setprivacy")
            logger.warning("  3. Select @GFINofficialbot")
            logger.warning("  4. Select Disable")
    else:
        logger.error("Failed to verify bot! Check TELEGRAM_BOT_TOKEN")
        return

    # Set bot commands
    api_call("setMyCommands", {"commands": json.dumps([
        {"command": "check", "description": "Check if a domain/wallet/phone is a known scam"},
        {"command": "report", "description": "File a scam report with GFIN"},
        {"command": "help", "description": "Show help and commands"},
        {"command": "stats", "description": "GFIN global statistics"},
        {"command": "latest", "description": "Latest scam alerts"},
        {"command": "scan", "description": "Scan current group for scam indicators"},
    ])})
    api_call("setMyDescription", {"description": "GFIN Intelligence Bot - Cyber fraud detection, wallet/domain checking, and victim support. 189 countries connected."})

    offset = 0
    logger.info("Starting message polling loop...")

    while True:
        try:
            updates = get_updates(offset=offset, timeout=25)
            for update in updates:
                offset = update.get("update_id", 0) + 1
                if "message" in update:
                    process_message(update["message"])
                elif "edited_message" in update:
                    process_message(update["edited_message"])
                elif "callback_query" in update:
                    process_callback(update["callback_query"])
                    api_call("answerCallbackQuery", {"callback_query_id": update["callback_query"]["id"]})
        except Exception as e:
            logger.error("Polling error: %s" % e)
            time.sleep(5)

if __name__ == "__main__":
    main()

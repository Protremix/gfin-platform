#!/usr/bin/env python3
"""
GFIN Telegram Intelligence Bot v2.0 — Enhanced Spy System
Upgrades: PostgreSQL storage, more wallet types, cross-group tracking, group management.
This patch updates the existing telegram_intel_bot.py.
"""

import re

# Read the current bot
with open("/gfin/telegram_intel_bot.py", "r") as f:
    bot = f.read()

# 1. Add more wallet patterns
old_wallets = '''WALLET_PATTERNS = {
    "BTC": r'\\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\\b',
    "BTC_BECH32": r'\\bbc1[a-z0-9]{39,59}\\b',
    "ETH": r'\\b0x[a-fA-F0-9]{40}\\b',
    "TRON": r'\\bT[A-Za-z0-9]{33}\\b',
    "SOLANA": r'\\b[1-9A-HJ-NP-Za-km-z]{43,44}\\b',
}'''

new_wallets = '''WALLET_PATTERNS = {
    "BTC": r'\\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\\b',
    "BTC_BECH32": r'\\bbc1[a-z0-9]{39,59}\\b',
    "ETH": r'\\b0x[a-fA-F0-9]{40}\\b',
    "TRON": r'\\bT[A-Za-z0-9]{33}\\b',
    "SOLANA": r'\\b[1-9A-HJ-NP-Za-km-z]{43,44}\\b',
    "XRP": r'\\br[A-Za-z0-9]{24,34}\\b',
    "TON": r'\\bEQA[A-Za-z0-9_-]{46}\\b',
    "LTC": r'\\b[LM3][a-km-zA-HJ-NP-Z1-9]{25,34}\\b',
    "DOGE": r'\\bD[A-Za-z0-9]{25,34}\\b',
    "ALGO": r'\\b[A-Z2-7]{58}\\b',
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
    return True'''

bot = bot.replace(old_wallets, new_wallets)

# 2. Add asyncpg import and DB functions after the GFIN API section
db_code = '''
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

'''

# Insert after gfin_post function
insert_after = "def store_intelligence(intel, chat_id, chat_title, username, message_id):"
bot = bot.replace(insert_after, db_code + "\n" + insert_after)

# 3. Update store_intelligence to also store in DB
old_store = '''def store_intelligence(intel, chat_id, chat_title, username, message_id):
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
            f.write(json.dumps(entry) + "\\n")
    except Exception as e:
        logger.error("Failed to store intel: %s" % e)'''

new_store = '''def store_intelligence(intel, chat_id, chat_title, username, message_id):
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
            f.write(json.dumps(entry) + "\\n")
    except Exception as e:
        logger.error("Failed to store intel JSONL: %s" % e)
    # Also store in PostgreSQL with cross-group tracking
    db_store_intel_sync(intel, chat_id, chat_title, "group", username, message_id)'''

bot = bot.replace(old_store, new_store)

# 4. Update process_message to register groups and update stats
old_process_start = '''def process_message(message):
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    chat_title = chat.get("title", chat.get("first_name", "Private"))
    user = message.get("from", {})
    username = user.get("username", user.get("first_name", "unknown"))
    message_id = message.get("message_id", 0)

    if not text:
        return'''

new_process_start = '''def process_message(message):
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
        db_update_group_stats_sync(chat_id, messages_scanned_inc=1)'''

bot = bot.replace(old_process_start, new_process_start)

# 5. Update the intel storage section to also update group stats
old_intel_store = '''    if intel["wallets"] or intel["domains"] or intel["phones"] or intel["is_victim"]:
        store_intelligence(intel, chat_id, chat_title, username, message_id)
        logger.info("Intel from %s in '%s': %d wallets, %d domains, %d phones, victim=%s, types=%s" % (
            username, chat_title, len(intel["wallets"]), len(intel["domains"]),
            len(intel["phones"]), intel["is_victim"], intel["scam_types"]))'''

new_intel_store = '''    if intel["wallets"] or intel["domains"] or intel["phones"] or intel["ips"] or intel["is_victim"]:
        store_intelligence(intel, chat_id, chat_title, username, message_id)
        intel_count = len(intel["wallets"]) + len(intel["domains"]) + len(intel["phones"]) + len(intel["ips"])
        db_update_group_stats_sync(chat_id, messages_scanned_inc=0, intel_items_inc=intel_count)
        logger.info("Intel from %s in '%s': %d wallets, %d domains, %d phones, %d IPs, victim=%s, types=%s" % (
            username, chat_title, len(intel["wallets"]), len(intel["domains"]),
            len(intel["phones"]), len(intel["ips"]), intel["is_victim"], intel["scam_types"]))'''

bot = bot.replace(old_intel_store, new_intel_store)

# 6. Update victim response to increment victim counter
old_victim_respond = '''        if should_respond:
            send_message(chat_id, victim_response(intel, username), reply_markup={
                "inline_keyboard": [[
                    {"text": "File Complaint", "url": GFIN_PORTAL + "/victim"},
                    {"text": "Check a Domain", "callback_data": "check_help"}
                ]]
            })
            logger.info("Sent victim response to %s in %s" % (username, chat_title))'''

new_victim_respond = '''        if should_respond:
            send_message(chat_id, victim_response(intel, username), reply_markup={
                "inline_keyboard": [[
                    {"text": "File Complaint", "url": GFIN_PORTAL + "/victim"},
                    {"text": "Check a Domain", "callback_data": "check_help"}
                ]]
            })
            if chat_type in ("group", "supergroup"):
                db_update_group_stats_sync(chat_id, messages_scanned_inc=0, victims_inc=1)
            logger.info("Sent victim response to %s in %s" % (username, chat_title))'''

bot = bot.replace(old_victim_respond, new_victim_respond)

# 7. Update scam detection to increment scam counter
old_scam_detect = '''                logger.warning("SCAM DOMAIN DETECTED: %s in %s" % (d["domain"], chat_title))'''
new_scam_detect = '''                if chat_type in ("group", "supergroup"):
                    db_update_group_stats_sync(chat_id, messages_scanned_inc=0, scams_inc=1)
                logger.warning("SCAM DOMAIN DETECTED: %s in %s" % (d["domain"], chat_title))'''
bot = bot.replace(old_scam_detect, new_scam_detect)

# 8. Add wallet validation to extraction
old_wallet_extract = '''    for wallet_type, pattern in WALLET_PATTERNS.items():
        matches = re.findall(pattern, text)
        wtype = "BTC" if "BTC" in wallet_type else wallet_type
        for m in matches:
            if len(m) >= 26 or wallet_type == "ETH":
                intel["wallets"].append({"type": wtype, "address": m})'''

new_wallet_extract = '''    for wallet_type, pattern in WALLET_PATTERNS.items():
        matches = re.findall(pattern, text)
        wtype = "BTC" if "BTC" in wallet_type else wallet_type
        for m in matches:
            if _valid_wallet(wtype, m):
                intel["wallets"].append({"type": wtype, "address": m})'''

if old_wallet_extract in bot:
    bot = bot.replace(old_wallet_extract, new_wallet_extract)
    print("Wallet validation added")
else:
    print("WARNING: Could not find wallet extraction to update")

with open("/gfin/telegram_intel_bot.py", "w") as f:
    f.write(bot)
print("Bot updated to v2.0")

#!/usr/bin/env python3
"""Re-scan group history and store intel in DB."""
import os, asyncio, sys, re, json
sys.path.insert(0, "/gfin")

API_ID = 33592112
API_HASH = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()
SESSION = "/gfin/gfin_user_session"

from telethon import TelegramClient
import psycopg2

client = TelegramClient(SESSION, API_ID, API_HASH)

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
}
DOMAIN_PATTERN = r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b'
PHONE_PATTERN = r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}'
IP_PATTERN = r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
SAFE_DOMAINS = {"telegram.org","t.me","youtube.com","google.com","github.com","wikipedia.org","reddit.com","twitter.com","x.com","facebook.com","instagram.com","whatsapp.com","paypal.com","amazon.com","ebay.com","apple.com","microsoft.com","netflix.com","spotify.com","binance.com","coinbase.com","kraken.com","bybit.com","ethereum.org","bitcoin.org","ripple.com","gfin-system.com"}

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
    "guaranteed profit","double your","invest and earn","trading signals",
    "recovery service","recovery agent","get your money back","hack back",
    "reclaim your funds","fund recovery expert","giveaway","free bitcoin",
    "send 1 eth get 2","airdrop","claim your reward","connect wallet",
    "private key","seed phrase","mnemonic","pig butchering","romance scam",
    "dating scam","double your bitcoin","multiply your crypto",
]

SCAM_TYPE_MAP = {
    "RECOVERY_SCAM": ["recover","get your money back","recovery service","recovery agent","fund recovery","hack back","reclaim"],
    "ROMANCE_SCAM": ["romance","dating scam","love scam","catfish","sugar daddy","sugar mommy"],
    "INVESTMENT_FRAUD": ["investment","trading","forex","binary options","guaranteed return","trading signals","arbitrage"],
    "PHISHING": ["verify your","confirm your","suspended account","click here to","login to secure"],
    "IMPERSONATION": ["official representative","support team","customer service","verify identity"],
    "CRYPTO_FRAUD": ["airdrop","connect wallet","private key","seed phrase","giveaway","free bitcoin"],
    "ADVANCE_FEE": ["advance payment","processing fee","clearance fee","unlock fee","transfer fee"],
}

def extract_wallets(text):
    wallets = []
    for wtype, pattern in WALLET_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            addr = match.group(0)
            if wtype == "ETH" and not addr.startswith("0x"): continue
            if wtype == "BTC" and not (addr.startswith("1") or addr.startswith("3")): continue
            if wtype == "TRON" and not addr.startswith("T"): continue
            if wtype == "XRP" and not addr.startswith("r"): continue
            if wtype == "TON" and not addr.startswith("EQ"): continue
            wallets.append({"type": wtype, "address": addr})
    seen = set()
    unique = []
    for w in wallets:
        key = f"{w['type']}:{w['address']}"
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique

def extract_domains(text):
    domains = []
    for match in re.finditer(DOMAIN_PATTERN, text, re.IGNORECASE):
        domain = match.group(1).lower()
        if domain in SAFE_DOMAINS: continue
        if domain.endswith((".png",".jpg",".jpeg",".gif",".svg",".pdf",".webp")): continue
        if domain not in domains:
            domains.append(domain)
    return domains

def extract_phones(text):
    return list(set(re.findall(PHONE_PATTERN, text)))

def extract_ips(text):
    return list(set(re.findall(IP_PATTERN, text)))

def detect_victim(text):
    text_lower = text.lower()
    matched = []
    for pattern in VICTIM_PATTERNS:
        if re.search(pattern, text_lower):
            matched.append(pattern)
    return len(matched) > 0, matched

def detect_scam(text):
    text_lower = text.lower()
    indicators = [i for i in SCAM_INDICATORS if i in text_lower]
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
    if is_victim:
        return "VICTIM"
    score = 0
    if wallets: score += 30
    if domains: score += 25
    if scam_indicators: score += min(20 * len(scam_indicators), 40)
    if scam_type: score += 20
    if score >= 60: return "CRITICAL"
    elif score >= 40: return "HIGH"
    elif score >= 20: return "MEDIUM"
    return "LOW"

def get_db():
    return psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!", port=5432)

async def scan_and_store():
    await client.connect()
    me = await client.get_me()
    print(f"Logged in as {me.first_name} (ID: {me.id})")
    
    conn = get_db()
    cur = conn.cursor()
    
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if not hasattr(entity, "title"):
            continue
        
        group_name = dialog.title
        group_id = dialog.id
        print(f"\n=== Scanning {group_name} ===")
        
        count = 0
        intel_count = 0
        
        async for message in client.iter_messages(entity, limit=1000):
            if not message or not message.text:
                continue
            text = message.text
            count += 1
            
            wallets = extract_wallets(text)
            domains = extract_domains(text)
            phones = extract_phones(text)
            ips = extract_ips(text)
            is_victim, victim_patterns = detect_victim(text)
            scam_type, scam_indicators = detect_scam(text)
            risk_level = calculate_risk(wallets, domains, is_victim, scam_indicators, scam_type)
            
            if not wallets and not domains and not is_victim and not scam_indicators and not phones:
                continue
            
            intel_count += 1
            
            sender = await message.get_sender()
            sender_name = ""
            sender_username = ""
            sender_id = 0
            if sender:
                if hasattr(sender, "first_name"):
                    sender_name = ((sender.first_name or "") + " " + (sender.last_name or "")).strip()
                elif hasattr(sender, "title"):
                    sender_name = sender.title
                if hasattr(sender, "username") and sender.username:
                    sender_username = sender.username
                if hasattr(sender, "id"):
                    sender_id = sender.id
            
            try:
                cur.execute("""
                    INSERT INTO telegram_intelligence
                    (message_id, group_id, group_name, sender_id, sender_name, sender_username,
                     message_text, wallets, domains, phones, ips, usernames,
                     is_victim, victim_patterns, scam_type, scam_indicators, risk_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    message.id, group_id, group_name, sender_id, sender_name, sender_username,
                    text[:5000],
                    json.dumps(wallets), json.dumps(domains), json.dumps(phones),
                    json.dumps(ips), json.dumps([]),
                    is_victim, json.dumps(victim_patterns), scam_type,
                    json.dumps(scam_indicators), risk_level,
                ))
                
                for w in wallets:
                    cur.execute("""
                        INSERT INTO telegram_wallets (wallet_address, wallet_type, first_seen_group, first_seen_sender)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (wallet_address) DO UPDATE SET
                            mention_count = telegram_wallets.mention_count + 1,
                            last_seen = NOW()
                    """, (w["address"], w["type"], group_name, sender_name))
                
                for d in domains:
                    cur.execute("""
                        INSERT INTO telegram_domains (domain, first_seen_group, first_seen_sender)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (domain) DO UPDATE SET
                            mention_count = telegram_domains.mention_count + 1,
                            last_seen = NOW()
                    """, (d, group_name, sender_name))
            except Exception as e:
                pass
            
            if wallets or is_victim or scam_type:
                items = []
                if wallets: items.append(f"{len(wallets)} wallets")
                if is_victim: items.append("VICTIM")
                if scam_type: items.append(f"scam={scam_type}")
                if domains: items.append(f"domains={domains[:3]}")
                print(f"  [{sender_name}] risk={risk_level}: {', '.join(items)}")
        
        conn.commit()
        print(f"  Scanned {count} messages, {intel_count} with intelligence")
    
    conn.close()
    await client.disconnect()

asyncio.run(scan_and_store())

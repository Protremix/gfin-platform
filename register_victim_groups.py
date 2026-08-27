import asyncio, os, json, re
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import Channel

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

# All victim groups we've joined
VICTIM_GROUPS = [
    "@scammers_unmasked_with_tee",
    "@ultgg",
    "@fxscammersexposed",
    "@cpmscammer",
    "@ScammersExposedForex",
    "@exposeddddd",
    "@Ghanausdt_exchange",
    "@Malta_buy_usdt",
    "@Colombia_buy_usdt",
    "@Brazil_exchange_usdt0",
    "@Romania_buy_usdt",
    "@Luxembourgexchangeusdt",
    "@rocket21scam",
    "@ScammedbyGothixAI",
]

async def register_groups():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTH")
        return
    
    groups_data = []
    for username in VICTIM_GROUPS:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            group_id = entity.id
            is_channel = isinstance(entity, Channel)
            
            group_type = "victim_community"
            # Classify group type
            title_lower = title.lower()
            if "defrauded" in title_lower or "buy usdt" in title_lower:
                group_type = "money_laundering_infrastructure"
            elif "exposed" in title_lower or "unmasked" in title_lower or "scammers of" in title_lower:
                group_type = "scam_exposure_community"
            elif "scammed" in title_lower or "got scammed" in title_lower or "was scammed" in title_lower:
                group_type = "victim_support_group"
            elif "forex" in title_lower or "crypto" in title_lower:
                group_type = "forex_crypto_scam_community"
            
            info = {
                "id": group_id,
                "title": title,
                "username": username,
                "members": members,
                "type": "channel" if is_channel else "group",
                "category": group_type,
                "monitoring_purpose": "victim_intelligence"
            }
            groups_data.append(info)
            print("Registered:", title, "|", username, "|", group_type, "|", members, "members")
        except Exception as e:
            print("Error:", username, type(e).__name__)
    
    # Save to file for the spy to load
    with open("/gfin/victim_groups.json", "w") as f:
        json.dump(groups_data, f, indent=2)
    
    print("\nSaved", len(groups_data), "victim groups to /gfin/victim_groups.json")
    
    # Also register via GFIN API
    import urllib.request
    for g in groups_data:
        try:
            data = json.dumps({
                "group_id": str(g["id"]),
                "group_name": g["title"],
                "username": g["username"],
                "member_count": g["members"],
                "group_type": g["category"],
                "monitoring_purpose": "victim_intelligence",
                "is_victim_group": True
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:8000/api/telegram/groups",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=5)
            print("API registered:", g["username"], "-", resp.status)
        except Exception as e:
            print("API error:", g["username"], "-", str(e)[:50])
    
    # Now extract intelligence from recent messages
    print("\n=== EXTRACTING VICTIM INTELLIGENCE ===")
    
    intel_items = []
    for username in VICTIM_GROUPS:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            
            async for msg in client.iter_messages(entity, limit=30):
                if not msg or not msg.text:
                    continue
                
                text = msg.text
                date = msg.date.isoformat() if msg.date else ""
                sender = ""
                if msg.sender:
                    sender = getattr(msg.sender, "first_name", "") or getattr(msg.sender, "title", "") or "?"
                    sender_username = getattr(msg.sender, "username", "") or ""
                
                # Extract wallets
                wallets = []
                # BTC
                wallets += re.findall(r'\b[bc1q][a-z0-9]{20,40}\b', text, re.I)
                # ETH
                wallets += re.findall(r'\b0x[a-fA-F0-9]{40}\b', text)
                # TRON
                wallets += re.findall(r'\bT[A-Za-z0-9]{33}\b', text)
                
                # Extract domains
                domains = re.findall(r'(?:https?://)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)', text)
                
                # Extract usernames
                usernames = re.findall(r'@([a-zA-Z0-9_]{3,})', text)
                
                # Scam indicators
                scam_indicators = []
                scam_keywords = ["scammed", "defrauded", "fraud", "stole", "stolen", "lost money",
                                "fake", "ponzi", "pyramid", "investment scam", "phishing",
                                "flash usdt", "flash btc", "recovery", "refund",
                                "money laundering", "exchange", "wash", "defraud"]
                for kw in scam_keywords:
                    if kw in text.lower():
                        scam_indicators.append(kw)
                
                # Phone numbers
                phones = re.findall(r'\+?\d{10,15}', text)
                
                if wallets or domains or scam_indicators or phones:
                    intel = {
                        "group": title,
                        "group_username": username,
                        "date": date,
                        "sender": sender,
                        "sender_username": sender_username,
                        "text": text[:500],
                        "wallets": wallets[:5],
                        "domains": domains[:5],
                        "usernames": usernames[:5],
                        "phones": phones[:3],
                        "scam_indicators": scam_indicators,
                        "category": "victim_intel" if any(kw in scam_indicators for kw in ["scammed", "defrauded", "lost money"]) else "scam_infrastructure"
                    }
                    intel_items.append(intel)
                    if wallets or domains:
                        print("INTEL:", username, "| wallets:", wallets[:3], "| domains:", domains[:3], "| indicators:", scam_indicators[:3])
                    
        except Exception as e:
            print("Scan error:", username, type(e).__name__)
    
    print("\n=== TOTAL INTELLIGENCE ITEMS:", len(intel_items), "===")
    
    # Save intelligence
    with open("/gfin/victim_intelligence.json", "w") as f:
        json.dump(intel_items, f, indent=2)
    
    print("Saved to /gfin/victim_intelligence.json")
    
    # Print summary
    all_wallets = set()
    all_domains = set()
    all_usernames = set()
    all_phones = set()
    victim_reports = 0
    laundering_indicators = 0
    
    for item in intel_items:
        all_wallets.update(item["wallets"])
        all_domains.update(item["domains"])
        all_usernames.update(item["usernames"])
        all_phones.update(item["phones"])
        if "scammed" in item["scam_indicators"] or "defrauded" in item["scam_indicators"] or "lost money" in item["scam_indicators"]:
            victim_reports += 1
        if "exchange" in item["scam_indicators"] or "wash" in item["scam_indicators"]:
            laundering_indicators += 1
    
    print("\n=== VICTIM INTELLIGENCE SUMMARY ===")
    print("Unique wallets found:", len(all_wallets))
    print("Unique domains found:", len(all_domains))
    print("Usernames mentioned:", len(all_usernames))
    print("Phone numbers:", len(all_phones))
    print("Victim reports:", victim_reports)
    print("Laundering indicators:", laundering_indicators)
    
    await client.disconnect()

asyncio.run(register_groups())

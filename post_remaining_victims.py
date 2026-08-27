import asyncio, os
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import Channel
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatWriteForbiddenError

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

MESSAGE = """🛡️ **GFIN — Global Fraud Intelligence Network**

If you've been scammed, defrauded, or lost money to fraud — you're not alone, and there IS something you can do about it.

**GFIN is a global fraud intelligence platform** that:
• Files official cybercrime complaints routed directly to national police
• Tracks scammers across borders (wallets, domains, phone numbers, identities)
• Monitors scam networks 24/7 across Telegram and the internet
• Routes your case to the correct law enforcement agency in your country

**Filing a complaint is free and takes 2 minutes:**
👉 https://gfin-system.com/victim

Your complaint is treated as evidence. Every report helps build cases against fraud networks and protects future victims.

What GFIN does with your report:
✅ Auto-investigates the scammer's wallet, domain, and infrastructure
✅ Routes to your country's cybercrime agency + INTERPOL
✅ Adds the scammer to our global intelligence database
✅ Alerts other victims about the same scammer

**You don't need proof to file a complaint** — your testimony matters. Screenshots, wallet addresses, domains, phone numbers, and usernames all help, but even without them, your report is valuable.

🌐 File your complaint: https://gfin-system.com/victim
ℹ️ Learn more: https://gfin-system.com

Stay safe. Report fraud. Help stop scammers. 🛡️"""

# Remaining groups to join and post in
REMAINING = [
    "@metahackk",
    "@wewerescammed",
    "@worth40k",
    "@exposingscammerio",
    "@scamkillerss",
    "@flash_crypto_scammers_expose",
    "@scammers_alert_exposed",
    "@cyber1111restore",
]

async def join_and_post():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    
    me = await client.get_me()
    print("Connected as:", me.first_name)
    
    # Check current dialogs to see what we're already in
    dialogs = await client.get_dialogs()
    current_usernames = set()
    for d in dialogs:
        if hasattr(d.entity, 'username') and d.entity.username:
            current_usernames.add("@" + d.entity.username)
    
    posted = 0
    joined_and_posted = 0
    
    for username in REMAINING:
        if username not in current_usernames:
            # Try to join first
            try:
                entity = await client.get_entity(username)
                title = getattr(entity, "title", username)
                if isinstance(entity, Channel):
                    await client(functions.channels.JoinChannelRequest(entity))
                print("JOINED:", title, "-", username)
                await asyncio.sleep(15)
            except FloodWaitError as e:
                print("FLOOD WAIT:", username, "-", e.seconds, "seconds — stopping")
                break
            except Exception as e:
                err = str(e)
                if "Already" in err or "Participant" in err:
                    print("ALREADY IN:", username)
                else:
                    print("JOIN FAIL:", username, "-", type(e).__name__, err[:60])
                    continue
        else:
            print("ALREADY IN:", username)
        
        # Now try to post
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            is_channel = isinstance(entity, Channel)
            
            if is_channel and not entity.megagroup:
                print("  READ-ONLY CHANNEL:", title, "(skipping)")
                continue
            
            await client.send_message(entity, MESSAGE, link_preview=True)
            print("  POSTED to:", title)
            posted += 1
            joined_and_posted += 1
            await asyncio.sleep(10)
            
        except ChatWriteForbiddenError:
            print("  CANNOT WRITE:", title, "(no permission)")
        except FloodWaitError as e:
            print("  FLOOD WAIT:", title, "-", e.seconds, "seconds")
            break
        except Exception as e:
            err = str(e)
            if "SlowMode" in err:
                print("  SLOW MODE:", title, "— need to wait")
            else:
                print("  ERROR:", title, "-", type(e).__name__, err[:60])
    
    print("\n=== POSTED in", posted, "additional groups ===")
    print("=== TOTAL victim groups reached:", 3 + posted, "===")
    
    # Now also try to message individual victims we found in the scans
    # Victims who mentioned being scammed in the groups
    print("\n=== MESSAGING INDIVIDUAL VICTIMS ===")
    
    # Read the intelligence file to find victims
    import json
    try:
        with open("/gfin/victim_intelligence.json") as f:
            intel = json.load(f)
    except:
        intel = []
    
    # Find messages where someone reported being scammed
    victim_senders = set()
    for item in intel:
        indicators = item.get("scam_indicators", [])
        if any(kw in indicators for kw in ["scammed", "defrauded", "lost money", "stole", "stolen"]):
            sender_username = item.get("sender_username", "")
            if sender_username and sender_username not in ["cpmscammer", "scammers_unmasked_with_tee"]:
                victim_senders.add(sender_username)
    
    print("Found", len(victim_senders), "individual victim senders")
    for s in victim_senders:
        print("  @"+s)
    
    dm_sent = 0
    for username in victim_senders:
        try:
            entity = await client.get_entity(username)
            name = getattr(entity, "first_name", "") or username
            print("  Messaging:", name, "(@"+username+")")
            
            dm = """Hi """ + name + """ 👋

I saw your message about being scammed in a Telegram group. I'm reaching out from GFIN — the Global Fraud Intelligence Network.

We help fraud victims file official complaints that get routed directly to national cybercrime police. It's free and takes 2 minutes:

👉 https://gfin-system.com/victim

Your report helps:
• Police track the scammer across borders
• Warn other potential victims
• Build international cases against fraud networks

You don't need to have all the evidence — even a description of what happened helps. Wallet addresses, scammer usernames, domains, and screenshots are all useful but optional.

Stay safe, and don't hesitate to file a report. Every complaint matters. 🛡️

🌐 https://gfin-system.com"""
            
            await client.send_message(entity, dm, link_preview=True)
            print("  -> SENT to @" + username)
            dm_sent += 1
            await asyncio.sleep(15)
            
        except FloodWaitError as e:
            print("  FLOOD WAIT — stopping DMs")
            break
        except Exception as e:
            print("  ERROR:", username, "-", type(e).__name__, str(e)[:60])
    
    print("\n=== DMs SENT:", dm_sent, "===")
    
    await client.disconnect()

asyncio.run(join_and_post())

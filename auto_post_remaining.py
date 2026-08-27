import asyncio, os, time
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import Channel
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, SlowModeWaitError

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

MESSAGE = """\U0001F6E1\uFE0F **GFIN \u2014 Global Fraud Intelligence Network**

If you've been scammed, defrauded, or lost money to fraud \u2014 you're not alone, and there IS something you can do about it.

**GFIN is a global fraud intelligence platform** that:
\u2022 Files official cybercrime complaints routed directly to national police
\u2022 Tracks scammers across borders (wallets, domains, phone numbers, identities)
\u2022 Monitors scam networks 24/7 across Telegram and the internet
\u2022 Routes your case to the correct law enforcement agency in your country

**Filing a complaint is free and takes 2 minutes:**
\U0001F449 https://gfin-system.com/victim

Your complaint is treated as evidence. Every report helps build cases against fraud networks and protects future victims.

What GFIN does with your report:
\u2705 Auto-investigates the scammer's wallet, domain, and infrastructure
\u2705 Routes to your country's cybercrime agency + INTERPOL
\u2705 Adds the scammer to our global intelligence database
\u2705 Alerts other victims about the same scammer

**You don't need proof to file a complaint** \u2014 your testimony matters. Screenshots, wallet addresses, domains, phone numbers, and usernames all help, but even without them, your report is valuable.

\U0001F310 File your complaint: https://gfin-system.com/victim
\u2139\uFE0F Learn more: https://gfin-system.com

Stay safe. Report fraud. Help stop scammers. \U0001F6E1\uFE0F"""

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

async def main():
    # Wait for flood limit to clear (10 minutes = 600 seconds from last attempt)
    print("Waiting 600 seconds for flood limit to clear...", flush=True)
    await asyncio.sleep(600)
    print("Starting join + post sequence...", flush=True)
    
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED", flush=True)
        return
    
    me = await client.get_me()
    print("Connected as: " + str(me.first_name), flush=True)
    
    # Check which groups we're already in
    dialogs = await client.get_dialogs()
    current_usernames = set()
    for d in dialogs:
        if hasattr(d.entity, 'username') and d.entity.username:
            current_usernames.add("@" + d.entity.username)
    
    posted = 0
    joined = 0
    
    for username in REMAINING:
        if username not in current_usernames:
            try:
                entity = await client.get_entity(username)
                title = getattr(entity, "title", username)
                if isinstance(entity, Channel):
                    await client(functions.channels.JoinChannelRequest(entity))
                print("JOINED: " + str(title) + " (" + username + ")", flush=True)
                joined += 1
                await asyncio.sleep(25)
            except FloodWaitError as e:
                print("FLOOD: " + username + " - " + str(e.seconds) + "s, waiting...", flush=True)
                await asyncio.sleep(e.seconds + 10)
                try:
                    entity = await client.get_entity(username)
                    if isinstance(entity, Channel):
                        await client(functions.channels.JoinChannelRequest(entity))
                    print("JOINED (retry): " + username, flush=True)
                    joined += 1
                    await asyncio.sleep(25)
                except Exception as e2:
                    print("RETRY FAIL: " + username + " - " + type(e2).__name__, flush=True)
                    continue
            except Exception as e:
                err = str(e)
                if "Already" in err or "Participant" in err:
                    print("ALREADY IN: " + username, flush=True)
                else:
                    print("JOIN FAIL: " + username + " - " + type(e).__name__, flush=True)
                    continue
        else:
            print("ALREADY IN: " + username, flush=True)
        
        # Try to post
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            is_channel = isinstance(entity, Channel)
            
            if is_channel and not entity.megagroup:
                print("  READ-ONLY CHANNEL: " + str(title) + " (skip)", flush=True)
                continue
            
            await client.send_message(entity, MESSAGE, link_preview=True)
            print("  POSTED to: " + str(title), flush=True)
            posted += 1
            await asyncio.sleep(15)
            
        except ChatWriteForbiddenError:
            print("  CANNOT WRITE: " + str(title), flush=True)
        except SlowModeWaitError as e:
            print("  SLOW MODE: " + str(title) + " - wait " + str(e.seconds) + "s", flush=True)
        except Exception as e:
            print("  ERROR: " + str(title) + " - " + type(e).__name__ + ": " + str(e)[:60], flush=True)
    
    print("\n=== JOINED: " + str(joined) + " | POSTED: " + str(posted) + " ===", flush=True)
    print("=== TOTAL victim groups reached: " + str(3 + posted) + " ===", flush=True)
    
    await client.disconnect()

asyncio.run(main())

import asyncio, os
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

# Only post in victim support groups — NOT money laundering or scammer channels
VICTIM_GROUPS = [
    "@ultgg",                    # We got scammed (the aftermath) — 1.1K, active chat
    "@rocket21scam",             # Rocket21 scam victims
    "@ScammedbyGothixAI",        # Gothix AI scammed users
    "@scammers_unmasked_with_tee",  # SCAMMERS Unmasked — 10K, but may be channel
]

# Also try scam exposure groups where victims share stories
EXPOSURE_GROUPS = [
    "@fxscammersexposed",        # Forex Scammers Exposed
    "@cpmscammer",               # SCAMMERS EXPOSED
    "@ScammersExposedForex",     # Scammers Exposed
    "@exposeddddd",              # SCAMMERS OF TG!
]

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

async def post_messages():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    
    me = await client.get_me()
    print("Connected as:", me.first_name)
    
    all_groups = VICTIM_GROUPS + EXPOSURE_GROUPS
    
    for username in all_groups:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            is_channel = isinstance(entity, Channel)
            
            # Check if we can post (is it a group or a broadcast channel?)
            can_post = True
            if is_channel and not entity.megagroup:
                # Broadcast channel — only admins can post
                can_post = False
                print("CHANNEL (read-only):", title, "-", username, "(skipping — only admins can post)")
                continue
            
            if is_channel and entity.megagroup:
                print("MEGA GROUP:", title, "-", username, "(can post)")
            elif not is_channel:
                print("GROUP:", title, "-", username, "(can post)")
            
            # Send the message
            await client.send_message(entity, MESSAGE, link_preview=True)
            print("  -> POSTED SUCCESSFULLY to", title)
            
            # Wait between posts to avoid rate limiting
            await asyncio.sleep(10)
            
        except Exception as e:
            err = str(e)
            if "SlowModeWait" in err:
                print("  -> SLOW MODE ACTIVE:", username, "— need to wait before posting")
            elif "ChatWriteForbidden" in err or "Banned" in err:
                print("  -> CANNOT POST:", username, "— no permission (banned or read-only)")
            elif "FloodWait" in err:
                print("  -> FLOOD WAIT:", username, "— rate limited")
            else:
                print("  -> ERROR:", username, "-", type(e).__name__, err[:80])
    
    print("\n=== POSTING COMPLETE ===")
    await client.disconnect()

asyncio.run(post_messages())

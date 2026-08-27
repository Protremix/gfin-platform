import asyncio, os, json, sys
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import Channel
from telethon.errors import FloodWaitError, ChannelPrivateError

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

REMAINING = [
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
    "@metahackk",
    "@ScammedbyGothixAI",
    "@rocket21scam",
    "@wewerescammed",
    "@worth40k",
    "@exposingscammerio",
    "@scamkillerss",
    "@flash_crypto_scammers_expose",
    "@scammers_alert_exposed",
    "@cyber1111restore",
]

async def main():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED", flush=True)
        return
    
    me = await client.get_me()
    print("Connected as: " + str(me.first_name), flush=True)
    
    # Check which groups we're already in
    print("\n--- CURRENT GROUPS ---", flush=True)
    dialogs = await client.get_dialogs()
    current_groups = set()
    for d in dialogs:
        if d.is_channel or d.is_group:
            uname = d.entity.username if hasattr(d.entity, 'username') and d.entity.username else ""
            current_groups.add(uname)
            print("  IN: " + str(d.name) + " | @" + str(uname), flush=True)
    
    # Join remaining groups
    print("\n--- JOINING ---", flush=True)
    joined = 0
    for username in REMAINING:
        if username in current_groups:
            print("ALREADY IN: " + username, flush=True)
            joined += 1
            continue
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            if isinstance(entity, Channel):
                await client(functions.channels.JoinChannelRequest(entity))
            print("JOINED: " + str(title) + " | " + username + " | " + str(members) + " members", flush=True)
            joined += 1
            await asyncio.sleep(20)
        except FloodWaitError as e:
            print("FLOOD: " + username + " - wait " + str(e.seconds) + "s", flush=True)
            await asyncio.sleep(min(e.seconds + 5, 60))
            try:
                entity = await client.get_entity(username)
                title = getattr(entity, "title", username)
                if isinstance(entity, Channel):
                    await client(functions.channels.JoinChannelRequest(entity))
                members = getattr(entity, "participants_count", 0) or 0
                print("JOINED (retry): " + str(title) + " | " + username + " | " + str(members), flush=True)
                joined += 1
                await asyncio.sleep(20)
            except Exception as e2:
                print("RETRY FAIL: " + username + " - " + type(e2).__name__, flush=True)
        except ChannelPrivateError:
            print("PRIVATE: " + username, flush=True)
        except Exception as e:
            err = str(e)
            if "Already" in err or "Participant" in err:
                print("ALREADY IN: " + username, flush=True)
                joined += 1
            else:
                print("FAIL: " + username + " - " + type(e).__name__ + ": " + err[:60], flush=True)
    
    print("\n=== JOINED " + str(joined) + " groups ===", flush=True)
    
    # Scan ALL victim groups for messages
    print("\n=== SCANNING VICTIM MESSAGES ===", flush=True)
    all_groups = ["@scammers_unmasked_with_tee", "@ultgg"] + REMAINING
    
    for username in all_groups:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            print("\n" + "="*50, flush=True)
            print("GROUP: " + str(title) + " (" + username + ") - " + str(members) + " members", flush=True)
            print("="*50, flush=True)
            
            count = 0
            async for msg in client.iter_messages(entity, limit=10):
                if msg and msg.text:
                    sender = ""
                    if msg.sender:
                        sender = getattr(msg.sender, "first_name", "") or getattr(msg.sender, "title", "") or "?"
                    date = msg.date.strftime("%m-%d %H:%M") if msg.date else "?"
                    text = msg.text[:250].replace("\n", " | ")
                    print("  [" + date + "] [" + sender + "] " + text, flush=True)
                    count += 1
            if count == 0:
                print("  (no messages)", flush=True)
        except Exception as e:
            print("  ERR: " + type(e).__name__ + ": " + str(e)[:50], flush=True)
    
    print("\n=== SCAN COMPLETE ===", flush=True)
    await client.disconnect()

asyncio.run(main())

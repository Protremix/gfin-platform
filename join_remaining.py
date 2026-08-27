import asyncio, os, time
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
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

async def join_remaining():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    
    print("Waiting 310 seconds for flood wait to expire...")
    await asyncio.sleep(310)
    print("Starting to join remaining groups with 15s delays...")
    print("=" * 80)
    
    joined = []
    for username in REMAINING:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            
            from telethon.tl.types import Channel
            if isinstance(entity, Channel):
                await client(functions.channels.JoinChannelRequest(entity))
            
            print("JOINED:", title, "|", username, "|", members, "members")
            joined.append({"username": username, "title": title, "members": members})
            await asyncio.sleep(15)
            
        except FloodWaitError as e:
            wait = e.seconds
            print("FLOOD WAIT:", username, "- need to wait", wait, "seconds")
            print("Waiting", wait + 5, "seconds...")
            await asyncio.sleep(wait + 5)
            # Retry
            try:
                entity = await client.get_entity(username)
                title = getattr(entity, "title", username)
                members = getattr(entity, "participants_count", 0) or 0
                from telethon.tl.types import Channel
                if isinstance(entity, Channel):
                    await client(functions.channels.JoinChannelRequest(entity))
                print("JOINED (retry):", title, "|", username, "|", members, "members")
                joined.append({"username": username, "title": title, "members": members})
                await asyncio.sleep(15)
            except Exception as e2:
                print("RETRY FAILED:", username, "-", type(e2).__name__)
        except ChannelPrivateError:
            print("PRIVATE:", username)
        except Exception as e:
            err = str(e)
            if "Already" in err or "Participant" in err:
                print("ALREADY MEMBER:", username)
                joined.append({"username": username, "title": username, "members": 0})
            else:
                print("FAILED:", username, "-", type(e).__name__, err[:60])
    
    print("\n" + "=" * 80)
    print("TOTAL JOINED:", len(joined))
    
    # Now scan messages from ALL victim groups for victim content
    print("\n" + "=" * 80)
    print("SCANNING VICTIM MESSAGES FROM ALL JOINED GROUPS")
    print("=" * 80)
    
    all_joined = ["@scammers_unmasked_with_tee", "@ultgg"] + [j["username"] for j in joined]
    
    for username in all_joined:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            print(f"\n{'='*40}")
            print(f"GROUP: {title} ({username}) — {members} members")
            print(f"{'='*40}")
            
            msg_count = 0
            async for msg in client.iter_messages(entity, limit=10):
                if msg and msg.text:
                    sender = ""
                    if msg.sender:
                        sender = getattr(msg.sender, "first_name", "") or getattr(msg.sender, "title", "") or "?"
                    text = msg.text[:250].replace("\n", " | ")
                    date = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "?"
                    print(f"  [{date}] [{sender}] {text}")
                    msg_count += 1
            if msg_count == 0:
                print("  (no recent text messages)")
                
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {str(e)[:60]}")
    
    await client.disconnect()

asyncio.run(join_remaining())

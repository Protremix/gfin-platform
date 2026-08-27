import asyncio, os, json
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
        print("NOT AUTHORIZED")
        return
    
    me = await client.get_me()
    print("Connected as:", me.first_name)
    
    # First check which groups we already have
    print("\n--- CURRENT DIALOGS ---")
    dialogs = await client.get_dialogs()
    for d in dialogs:
        if d.is_channel or d.is_group:
            uname = d.entity.username if hasattr(d.entity, 'username') and d.entity.username else "private"
            members = d.entity.participants_count if hasattr(d.entity, 'participants_count') else 0
            print("  ALREADY IN:", d.name, "| @"+str(uname), "|", members)
    
    # Join remaining one by one
    print("\n--- JOINING REMAINING ---")
    joined = 0
    for username in REMAINING:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            
            if isinstance(entity, Channel):
                await client(functions.channels.JoinChannelRequest(entity))
            
            print("JOINED:", title, "|", username, "|", members)
            joined += 1
            await asyncio.sleep(20)
            
        except FloodWaitError as e:
            print("FLOOD WAIT:", username, "- need", e.seconds, "seconds")
            print("Waiting", e.seconds + 10, "...")
            await asyncio.sleep(e.seconds + 10)
            try:
                entity = await client.get_entity(username)
                title = getattr(entity, "title", username)
                if isinstance(entity, Channel):
                    await client(functions.channels.JoinChannelRequest(entity))
                members = getattr(entity, "participants_count", 0) or 0
                print("JOINED (retry):", title, "|", username, "|", members)
                joined += 1
                await asyncio.sleep(20)
            except Exception as e2:
                print("RETRY FAILED:", username, type(e2).__name__)
        except ChannelPrivateError:
            print("PRIVATE:", username)
        except Exception as e:
            err = str(e)
            if "Already" in err or "Participant" in err:
                print("ALREADY MEMBER:", username)
                joined += 1
            else:
                print("FAILED:", username, "-", type(e).__name__, err[:60])
    
    print("\n=== JOINED", joined, "groups ===")
    
    # Now scan ALL victim groups for recent messages
    print("\n=== SCANNING VICTIM MESSAGES ===")
    
    all_groups = ["@scammers_unmasked_with_tee", "@ultgg"] + REMAINING
    victim_data = []
    
    for username in all_groups:
        try:
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0) or 0
            print("\n" + "="*50)
            print("GROUP:", title, "("+username+") -", members, "members")
            print("="*50)
            
            count = 0
            async for msg in client.iter_messages(entity, limit=15):
                if msg and msg.text:
                    sender = ""
                    if msg.sender:
                        sender = getattr(msg.sender, "first_name", "") or getattr(msg.sender, "title", "") or "?"
                    date = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "?"
                    text = msg.text[:300].replace("\n", " | ")
                    print("  ["+date+"] ["+sender+"] "+text)
                    count += 1
            if count == 0:
                print("  (no recent text messages)")
                
        except Exception as e:
            print("  Error:", type(e).__name__, str(e)[:60])
    
    await client.disconnect()

asyncio.run(main())

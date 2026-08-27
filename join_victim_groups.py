import asyncio, os, json
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions
from telethon.tl.types import Channel, Chat, User
from telethon.errors import ChannelPrivateError, UserBannedInChannelError, ChatAdminRequiredError

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

# Groups to join — victim communities, scam exposure, fraud reporting
GROUPS_TO_JOIN = [
    # High-value victim communities
    "@scammers_unmasked_with_tee",  # 10,123 members
    "@ultgg",                         # 1,181 — "We got scammed (the aftermath)"
    "@fxscammersexposed",            # 721 — Forex scammers exposed
    "@cpmscammer",                   # 520
    "@ScammersExposedForex",         # 318
    "@exposeddddd",                  # 313 — "SCAMMERS OF TG!"
    
    # Country-specific defrauded groups (valuable for routing)
    "@Ghanausdt_exchange",           # 299 — Ghana defrauded
    "@Malta_buy_usdt",               # 234 — Malta defrauded
    "@Colombia_buy_usdt",            # 194 — Colombia defrauded
    "@Brazil_exchange_usdt0",        # 191 — Brazil defrauded
    "@Romania_buy_usdt",             # 188 — Romania defrauded
    "@Luxembourgexchangeusdt",       # 163 — Luxembourg defrauded
    
    # Direct victim groups
    "@metahackk",                    # 46 — "GOT SCAMMED"
    "@ScammedbyGothixAI",            # 37
    "@rocket21scam",                 # 17
    "@wewerescammed",                # 15 — "I was scammed"
    "@worth40k",                     # 7 — "how I got scammed worth 40k+"
    
    # Scam exposure / reporting
    "@exposingscammerio",            # 197
    "@scamkillerss",                 # 33
    "@flash_crypto_scammers_expose", # 28
    "@scammers_alert_exposed",       # 5
    
    # CAUTION: Likely recovery scam (monitor but don't promote)
    "@cyber1111restore",             # 32 — "I got scammed 100% recovery" — RECOVERY SCAM SUSPECTED
]

async def join_and_collect():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    
    me = await client.get_me()
    print("Connected as:", me.first_name, "(ID:", me.id, ")")
    print("Joining", len(GROUPS_TO_JOIN), "victim/scam-exposure groups...")
    print("=" * 80)
    
    joined = []
    failed = []
    
    for username in GROUPS_TO_JOIN:
        try:
            # Resolve the entity
            entity = await client.get_entity(username)
            title = getattr(entity, "title", username)
            members = getattr(entity, "participants_count", 0)
            
            # Try to join
            if isinstance(entity, Channel):
                await client(functions.channels.JoinChannelRequest(entity))
            else:
                await client(functions.messages.ImportChatInviteRequest(username.replace("@", "")))
            
            print("JOINED:", title, "|", username, "|", members, "members")
            joined.append({"username": username, "title": title, "members": members})
            
            # Wait a moment between joins to avoid rate limiting
            await asyncio.sleep(3)
            
        except ChannelPrivateError:
            print("PRIVATE:", username, "(channel is private)")
            failed.append({"username": username, "reason": "private"})
        except UserBannedInChannelError:
            print("BANNED:", username, "(banned from this channel)")
            failed.append({"username": username, "reason": "banned"})
        except ChatAdminRequiredError:
            print("ADMIN REQUIRED:", username)
            failed.append({"username": username, "reason": "admin_required"})
        except Exception as e:
            err_type = type(e).__name__
            # Maybe already joined
            if "Already" in str(e) or "UserAlreadyParticipant" in str(e):
                print("ALREADY MEMBER:", username)
                joined.append({"username": username, "title": username, "members": 0, "already": True})
            else:
                print("FAILED:", username, "-", err_type, str(e)[:80])
                failed.append({"username": username, "reason": err_type})
            await asyncio.sleep(2)
    
    print("\n" + "=" * 80)
    print("JOINED:", len(joined), "| FAILED:", len(failed))
    
    # Now fetch recent messages from joined groups to see victim content
    print("\n" + "=" * 80)
    print("SCANNING RECENT MESSAGES FROM VICTIM GROUPS")
    print("=" * 80)
    
    for j in joined[:10]:  # Scan top 10
        username = j["username"]
        try:
            entity = await client.get_entity(username)
            print(f"\n--- {j['title']} ({username}) ---")
            count = 0
            async for msg in client.iter_messages(entity, limit=5):
                if msg and msg.text:
                    sender = ""
                    if msg.sender:
                        sender = getattr(msg.sender, "first_name", "") or getattr(msg.sender, "title", "") or "?"
                    text = msg.text[:200].replace("\n", " | ")
                    print(f"  [{sender}] {text}")
                    count += 1
            if count == 0:
                print("  (no recent text messages)")
        except Exception as e:
            print(f"  Error reading: {type(e).__name__}: {str(e)[:60]}")
    
    await client.disconnect()
    
    return joined, failed

result = asyncio.run(join_and_collect())

import asyncio, os
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = "7a667ef2a73525df9e4d2c25a5153ab3"
from telethon import TelegramClient
from telethon.tl import functions

SESSION = "/gfin/gfin_user_session"
API_ID = 33592112
API_HASH = "7a667ef2a73525df9e4d2c25a5153ab3"

async def search_victim_groups():
    client = TelegramClient(SESSION, API_ID, API_HASH, device_model="GFIN Spy Client", system_version="2.0")
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT AUTHORIZED")
        return
    me = await client.get_me()
    print("Connected as:", me.first_name, "(ID:", me.id, ")")
    
    search_terms = [
        "scam victim", "fraud victim", "scam warning", "scam report",
        "anti scam", "scammers exposed", "scam alert", "got scammed",
        "scam help", "crypto scam victim", "investment fraud victim",
        "scam recovery", "scam survivor", "defrauded", "scam support",
        "fraud help", "scam exposed", "scammer exposed", "report scam",
        "expose scammer", "scam alert group", "fraud warning",
        "I was scammed", "lost money scam", "scam victim help",
        "scam victim support", "online fraud victim",
    ]
    
    all_results = {}
    for term in search_terms:
        try:
            results = await client(functions.contacts.SearchRequest(q=term, limit=15))
            for chat in results.chats:
                title = getattr(chat, "title", "") or ""
                username = getattr(chat, "username", "") or ""
                members = getattr(chat, "participants_count", 0) or 0
                key = username or str(chat.id)
                if key not in all_results:
                    all_results[key] = {"title": title, "username": username, "members": members, "found_by": term}
        except Exception as e:
            pass
    
    print("\nFound", len(all_results), "unique groups/channels")
    print("=" * 80)
    for key, info in sorted(all_results.items(), key=lambda x: x[1]["members"], reverse=True):
        uname = info["username"] or "no-username"
        line = str(info["members"]).rjust(6) + " | " + info["title"][:40].ljust(40) + " | @" + uname.ljust(25) + " | found: " + info["found_by"]
        print(line)
    
    await client.disconnect()

asyncio.run(search_victim_groups())

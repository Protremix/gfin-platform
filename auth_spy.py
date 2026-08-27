import os, asyncio, sys
sys.path.insert(0, "/gfin")
os.environ["TELEGRAM_API_ID"] = "33592112"
os.environ["TELEGRAM_API_HASH"] = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()

from telethon import TelegramClient

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION = "/gfin/gfin_user_session"

client = TelegramClient(SESSION, API_ID, API_HASH)

async def login():
    await client.start(
        phone="+44 7446378384",
        max_retries=1
    )
    me = await client.get_me()
    print(f"AUTH_SUCCESS: {me.first_name} (@{me.username}) ID={me.id} phone={me.phone}")
    await client.disconnect()

asyncio.run(login())

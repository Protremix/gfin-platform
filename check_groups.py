import os, asyncio

API_ID = 33592112
API_HASH = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()
SESSION = "/gfin/gfin_user_session"

from telethon import TelegramClient

client = TelegramClient(SESSION, API_ID, API_HASH)

async def list_groups():
    await client.connect()
    print("=== CURRENT GROUPS ===")
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        name = dialog.title or dialog.name
        if hasattr(entity, "title"):
            members = entity.participants_count if hasattr(entity, "participants_count") else "?"
            username = f"@{entity.username}" if hasattr(entity, "username") and entity.username else "no username"
            print(f"  [GROUP] {name} ({username}) - {members} members (ID: {dialog.id})")
        elif hasattr(entity, "first_name"):
            print(f"  [CHAT] {name} (ID: {dialog.id})")
    await client.disconnect()

asyncio.run(list_groups())

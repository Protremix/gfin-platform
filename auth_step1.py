import os, asyncio, sys, json

API_ID = 33592112
API_HASH = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()
SESSION = "/gfin/gfin_user_session"

from telethon import TelegramClient

client = TelegramClient(SESSION, API_ID, API_HASH)

async def send_code():
    await client.connect()
    result = await client.send_code_request("+44 7446378384")
    print(f"PHONE_CODE_HASH={result.phone_code_hash}")
    with open("/gfin/auth_state.json", "w") as f:
        json.dump({"phone_code_hash": result.phone_code_hash, "phone": "+447446378384"}, f)
    print("CODE_SENT")
    await client.disconnect()

asyncio.run(send_code())

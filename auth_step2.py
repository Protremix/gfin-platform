import os, asyncio, sys, json

API_ID = 33592112
API_HASH = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()
SESSION = "/gfin/gfin_user_session"

from telethon import TelegramClient

client = TelegramClient(SESSION, API_ID, API_HASH)

async def login():
    await client.connect()
    
    with open("/gfin/auth_state.json") as f:
        state = json.load(f)
    
    phone_code_hash = state["phone_code_hash"]
    phone = state["phone"]
    
    try:
        result = await client.sign_in(
            phone=phone,
            code="89987",
            phone_code_hash=phone_code_hash
        )
        me = await client.get_me()
        print(f"AUTH_SUCCESS: {me.first_name} (@{me.username}) ID={me.id} phone={me.phone}")
    except Exception as e:
        print(f"AUTH_ERROR: {e}")
        # Check if 2FA is needed
        if "password" in str(e).lower() or "SessionPasswordNeeded" in str(e):
            print("2FA_NEEDED")
        elif "code" in str(e).lower() and "invalid" in str(e).lower():
            print("INVALID_CODE")
        elif "flood" in str(e).lower():
            print("FLOOD_WAIT")
    
    await client.disconnect()

asyncio.run(login())

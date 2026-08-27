import os, asyncio, sys

API_ID = 33592112
API_HASH = os.popen("grep TELEGRAM_API_HASH /gfin/.env.telegram | cut -d= -f2").read().strip()
SESSION = "/gfin/gfin_user_session"

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import FloodWaitError, InviteHashExpiredError, UserAlreadyParticipantError, ChannelPrivateError

client = TelegramClient(SESSION, API_ID, API_HASH)

async def join_group(link):
    await client.connect()
    
    # Parse the link
    if "t.me/+" in link or "t.me/joinchat" in link:
        # Private group invite link
        hash_part = link.split("/")[-1].lstrip("+")
        print(f"Private invite: {hash_part}")
        try:
            result = await client(ImportChatInviteRequest(hash_part))
            chat = result.chats[0] if result.chats else result.chat
            title = chat.title if hasattr(chat, "title") else str(chat.id)
            print(f"JOINED: {title}")
        except UserAlreadyParticipantError:
            print("ALREADY_MEMBER")
        except InviteHashExpiredError:
            print("EXPIRED_LINK")
        except ChannelPrivateError:
            print("PRIVATE_CHANNEL_BANNED")
        except FloodWaitError as e:
            print(f"FLOOD_WAIT: {e.seconds}s")
        except Exception as e:
            print(f"ERROR: {e}")
    else:
        # Public channel/group
        username = link.split("/")[-1].lstrip("@")
        print(f"Public group: @{username}")
        try:
            result = await client(JoinChannelRequest(username))
            chat = result.chats[0] if result.chats else result.chat
            title = chat.title if hasattr(chat, "title") else str(chat.id)
            member_count = chat.participants_count if hasattr(chat, "participants_count") else 0
            print(f"JOINED: {title} ({member_count} members)")
        except FloodWaitError as e:
            print(f"FLOOD_WAIT: {e.seconds}s")
        except Exception as e:
            print(f"ERROR: {e}")
    
    await client.disconnect()

link = sys.argv[1] if len(sys.argv) > 1 else "https://t.me/forexjobworld"
asyncio.run(join_group(link))

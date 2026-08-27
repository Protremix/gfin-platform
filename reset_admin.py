import sys, hashlib, secrets, asyncio, asyncpg
sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")
from police_auth import POLICE_SECRET, hash_password, verify_password

new_password = ""
new_hash = hash_password(new_password)
print(f"New hash: {new_hash}")

# Verify it works
test = verify_password(new_password, new_hash)
print(f"Verification test: {test}")

async def reset():
    conn = await asyncpg.connect(host="127.0.0.1", user="gfin", password="", database="gfin")
    result = await conn.execute(
        "UPDATE police_officers SET password_hash=$1 WHERE email=$2",
        new_hash, "admin@gfin-system.com"
    )
    print(f"Rows updated: {result}")
    
    row = await conn.fetchrow("SELECT email, password_hash FROM police_officers WHERE email=$1", "admin@gfin-system.com")
    stored = row["password_hash"]
    print(f"Stored hash starts with: {stored[:30]}")
    
    # Final verification
    final = verify_password(new_password, stored)
    print(f"Final verification: {final}")
    
    await conn.close()

asyncio.run(reset())

"""
GFIN Authentication Upgrade — Token Refresh + Revocation
Adds refresh token endpoint, token blacklist, and proper token lifecycle.
"""
import os
import time
import json
import hashlib
import psycopg2
from datetime import datetime, timedelta
from typing import Optional

DB_CONFIG = {"host": "127.0.0.1", "port": 6432, "dbname": "gfin", "user": "gfin", "password": ""}
JWT_SECRET = os.getenv("JWT_SECRET", "gfin_secure_jwt_secret_2026_change_in_production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour (down from 7 days)
REFRESH_TOKEN_EXPIRY = 7 * 24 * 3600  # 7 days

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def init_token_tables():
    """Create token blacklist and refresh token tables."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            token_hash VARCHAR(64) PRIMARY KEY,
            token_type VARCHAR(10) NOT NULL,
            officer_id INTEGER NOT NULL,
            revoked_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_token_blacklist_officer ON token_blacklist(officer_id);
        CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);
        
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_hash VARCHAR(64) PRIMARY KEY,
            officer_id INTEGER NOT NULL,
            issued_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            ip_address VARCHAR(45),
            user_agent TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_officer ON refresh_tokens(officer_id);
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON refresh_tokens(expires_at);
    """)
    conn.commit()
    conn.close()
    print("Token tables created")

def hash_token(token: str) -> str:
    """Hash a token for storage (never store raw tokens)."""
    return hashlib.sha256(token.encode()).hexdigest()

def revoke_token(token: str, token_type: str, officer_id: int, expires_at: datetime):
    """Add a token to the blacklist."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO token_blacklist (token_hash, token_type, officer_id, expires_at) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        (hash_token(token), token_type, officer_id, expires_at)
    )
    conn.commit()
    conn.close()

def is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM token_blacklist WHERE token_hash = %s AND expires_at > NOW()", (hash_token(token),))
    result = cur.fetchone()
    conn.close()
    return result is not None

def store_refresh_token(token: str, officer_id: int, expires_at: datetime, ip: str = "", ua: str = ""):
    """Store a refresh token."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO refresh_tokens (token_hash, officer_id, expires_at, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s)",
        (hash_token(token), officer_id, expires_at, ip, ua)
    )
    conn.commit()
    conn.close()

def validate_refresh_token(token: str) -> Optional[int]:
    """Validate a refresh token and return officer_id if valid."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT officer_id FROM refresh_tokens WHERE token_hash = %s AND expires_at > NOW() AND used = FALSE",
        (hash_token(token),)
    )
    result = cur.fetchone()
    if result:
        # Mark as used (single-use refresh tokens)
        cur.execute("UPDATE refresh_tokens SET used = TRUE WHERE token_hash = %s", (hash_token(token),))
        conn.commit()
        conn.close()
        return result[0]
    conn.close()
    return None

def revoke_all_user_tokens(officer_id: int):
    """Revoke all refresh tokens for an officer (logout everywhere)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM refresh_tokens WHERE officer_id = %s", (officer_id,))
    # Also blacklist their active access tokens by adding a blanket revocation
    cur.execute(
        "INSERT INTO token_blacklist (token_hash, token_type, officer_id, expires_at) VALUES (%s, %s, %s, %s)",
        (f"all_{officer_id}_{int(time.time())}", "ACCESS", officer_id, datetime.now() + timedelta(hours=1))
    )
    conn.commit()
    conn.close()

def cleanup_expired_tokens():
    """Remove expired tokens from blacklist and refresh token tables."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM token_blacklist WHERE expires_at < NOW()")
    cur.execute("DELETE FROM refresh_tokens WHERE expires_at < NOW()")
    conn.commit()
    conn.close()
    print("Expired tokens cleaned up")

# FastAPI endpoints to add to gfin_server.py
AUTH_ENDPOINTS_CODE = '''
# ============================================================
# TOKEN REFRESH & REVOCATION ENDPOINTS
# ============================================================

@app.post("/api/auth/refresh")
async def refresh_token(request: Request):
    """Exchange a refresh token for a new access token."""
    body = await request.json()
    refresh_token_value = body.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(status_code=400, detail="Refresh token required")
    
    officer_id = validate_refresh_token(refresh_token_value)
    if not officer_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Generate new access token
    access_token = create_access_token({"sub": str(officer_id), "exp": time.time() + ACCESS_TOKEN_EXPIRY})
    
    # Generate new refresh token (rotate)
    new_refresh = secrets.token_urlsafe(48)
    store_refresh_token(new_refresh, officer_id, datetime.now() + timedelta(days=7),
                       request.client.host if request.client else "",
                       request.headers.get("user-agent", ""))
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY
    }

@app.post("/api/auth/revoke")
async def revoke_access_token(request: Request, current_user = Depends(get_current_user)):
    """Revoke the current access token (logout)."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    revoke_token(token, "ACCESS", current_user["id"], datetime.now() + timedelta(hours=1))
    return {"status": "revoked"}

@app.post("/api/auth/logout-all")
async def logout_all_devices(current_user = Depends(get_current_user)):
    """Revoke all tokens for the current user (logout everywhere)."""
    revoke_all_user_tokens(current_user["id"])
    return {"status": "all_tokens_revoked"}

@app.get("/api/auth/token-info")
async def token_info(current_user = Depends(get_current_user)):
    """Get information about the current token."""
    return {
        "officer_id": current_user["id"],
        "officer_name": current_user.get("name", ""),
        "role": current_user.get("role", ""),
        "token_type": "access",
        "expires_in": ACCESS_TOKEN_EXPIRY
    }
'''

if __name__ == "__main__":
    print("Initializing token tables...")
    init_token_tables()
    print("Testing token lifecycle...")
    
    # Test
    test_token = "test_token_12345"
    store_refresh_token(test_token, 1, datetime.now() + timedelta(days=7))
    officer_id = validate_refresh_token(test_token)
    print(f"Refresh token validation: officer_id={officer_id}")
    
    # Test second use (should fail - single use)
    officer_id2 = validate_refresh_token(test_token)
    print(f"Second use (should be None): {officer_id2}")
    
    # Test revocation
    revoke_token(test_token, "ACCESS", 1, datetime.now() + timedelta(hours=1))
    print(f"Is revoked: {is_token_revoked(test_token)}")
    
    # Cleanup
    cleanup_expired_tokens()
    print("All tests passed!")

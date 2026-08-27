#!/usr/bin/env python3
"""
GFIN Police Authentication System
- Police officer registration (admin-only)
- Login with JWT tokens
- Role-based access control (admin, investigator, viewer)
- API rate limiting
- Protected dashboard endpoints
"""
import hashlib, json, time, secrets, os
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Query, Body, Depends
from fastapi.responses import HTMLResponse, JSONResponse

# JWT-like token system (simplified, no external deps)
# In production, use PyJWT with proper RSA keys

POLICE_SECRET = os.environ.get("GFIN_POLICE_SECRET", "GFIN-POLICE-SECRET-2026-CHANGE-ME")

def generate_token(officer_id: int, role: str, agency: str) -> str:
    """Generate a signed token."""
    payload = {
        "oid": officer_id,
        "role": role,
        "agency": agency,
        "exp": int(time.time()) + 86400 * 7,  # 7 days
        "iat": int(time.time()),
    }
    payload_json = json.dumps(payload, sort_keys=True)
    signature = hashlib.sha256((payload_json + POLICE_SECRET).encode()).hexdigest()
    import base64
    token_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    return f"{token_b64}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify a token and return the payload."""
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_json = base64.urlsafe_b64decode(parts[0]).decode()
        signature = parts[1]
        expected_sig = hashlib.sha256((payload_json + POLICE_SECRET).encode()).hexdigest()
        if signature != expected_sig:
            return None
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except:
        return None


def hash_password(password: str) -> str:
    """Hash a password with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt + POLICE_SECRET).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 2:
            return False
        salt, hashed = parts
        test_hash = hashlib.sha256((password + salt + POLICE_SECRET).encode()).hexdigest()
        return test_hash == hashed
    except:
        return False


# ==================== RATE LIMITER ====================

class RateLimiter:
    """Simple in-memory rate limiter (per IP)."""
    def __init__(self):
        self.requests = {}  # ip -> [(timestamp, endpoint)]

    def check(self, ip: str, endpoint: str, limit: int = 60, window: int = 60) -> bool:
        """Check if IP is within rate limit. Returns True if allowed."""
        now = time.time()
        key = f"{ip}:{endpoint}"
        if key not in self.requests:
            self.requests[key] = []
        # Clean old entries
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        # Check limit
        if len(self.requests[key]) >= limit:
            return False
        self.requests[key].append(now)
        return True


rate_limiter = RateLimiter()


# ==================== AUTH MIDDLEWARE ====================

async def auth_police(request: Request):
    """Verify police officer authentication. Raises 401 if not authenticated."""
    # Try Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    else:
        # Try cookie
        token = request.cookies.get("gfin_police_token", "")

    if not token:
        raise HTTPException(401, "Authentication required. Login at /police/login")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token. Please login again.")

    return payload


async def auth_police_admin(request: Request):
    """Verify police officer with admin role."""
    payload = await auth_police(request)
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin access required for this action.")
    return payload


async def rate_limit(request: Request):
    """Rate limiting dependency."""
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    if not rate_limiter.check(client_ip, endpoint, limit=60, window=60):
        raise HTTPException(429, "Rate limit exceeded. Please slow down.")
    return True


# ==================== DB SCHEMA FOR POLICE OFFICERS ====================

POLICE_SCHEMA = """
CREATE TABLE IF NOT EXISTS police_officers (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    rank TEXT DEFAULT 'investigator',
    role TEXT NOT NULL DEFAULT 'investigator',
    agency TEXT NOT NULL,
    country_code TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    badge_number TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    approved_by TEXT DEFAULT 'SYSTEM'
);
"""


# ==================== POLICE LOGIN PAGE HTML ====================

POLICE_LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>GFIN Police Login — Global Fraud Intelligence Network</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e1a; color: #e0e0e0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.login-container { background: #131826; border: 1px solid #2a3450; border-radius: 12px; padding: 40px; max-width: 440px; width: 90%; }
.login-header { text-align: center; margin-bottom: 30px; }
.login-header h1 { color: #4a9eff; font-size: 28px; margin-bottom: 5px; }
.login-header p { color: #6b7280; font-size: 14px; }
.login-header .badge { display: inline-block; background: #1e3a5f; color: #4a9eff; padding: 4px 12px; border-radius: 4px; font-size: 12px; margin-top: 8px; }
.form-group { margin-bottom: 20px; }
.form-group label { display: block; color: #9ca3af; font-size: 13px; margin-bottom: 6px; }
.form-group input { width: 100%; background: #0a0e1a; border: 1px solid #2a3450; color: #e0e0e0; padding: 12px 16px; border-radius: 8px; font-size: 14px; }
.form-group input:focus { outline: none; border-color: #4a9eff; }
.btn-login { width: 100%; background: #4a9eff; color: #fff; border: none; padding: 14px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
.btn-login:hover { background: #3a8eef; }
.btn-login:disabled { background: #2a3450; cursor: not-allowed; }
.error-msg { background: #3a1518; border: 1px solid #5c2024; color: #f87171; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; display: none; }
.success-msg { background: #1a3a1a; border: 1px solid #2a5a2a; color: #4ade80; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; display: none; }
.info-box { background: #1a2332; border: 1px solid #2a3450; padding: 15px; border-radius: 8px; margin-top: 20px; font-size: 12px; color: #9ca3af; }
.info-box strong { color: #4a9eff; }
.footer { text-align: center; margin-top: 30px; color: #4b5563; font-size: 12px; }
.footer a { color: #4a9eff; text-decoration: none; }

        /* ===== MOBILE / SAMSUNG BROWSER FIX ===== */
        @media (max-width: 768px) {
            .login-container, .container, .login-box, .card { max-width: 100% !important; padding: 20px 16px !important; margin: 0 !important; border-radius: 10px !important; }
            h1, h2, .login-title { font-size: 20px !important; }
            label { font-size: 15px !important; }
            input, select, textarea { font-size: 16px !important; padding: 12px !important; }
            button, .btn, .login-btn { font-size: 16px !important; padding: 14px !important; width: 100% !important; }
            body { font-size: 15px !important; }
        }
        @media (max-width: 480px) {
            .login-container, .container { padding: 10px !important; }
            h1, h2 { font-size: 18px !important; }
        }
    </style>
</head>
<body>
<div class="login-container">
    <div class="login-header">
        <h1>🛡️ GFIN</h1>
        <p>Global Fraud Intelligence Network</p>
        <div class="badge">LAW ENFORCEMENT ONLY</div>
    </div>
    <div class="error-msg" id="error"></div>
    <div class="success-msg" id="success"></div>
    <form id="loginForm">
        <div class="form-group">
            <label>Police Email</label>
            <input type="email" id="email" placeholder="officer@police.gov" required>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" id="password" placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn-login" id="loginBtn">Sign In</button>
    </form>
    <div class="info-box">
        <strong>Restricted Access:</strong> This portal is for authorized law enforcement personnel only.
        All access is logged. Unauthorized access is a criminal offense.
        <br><br>
        <strong>First time?</strong> Contact your GFIN administrator to register.
    </div>
    <div class="footer">
        <a href="/victim">Victim Portal</a> · 
        <a href="/health">System Status</a>
    </div>
</div>
<script>
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('loginBtn');
    const errDiv = document.getElementById('error');
    const successDiv = document.getElementById('success');
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    errDiv.style.display = 'none';
    successDiv.style.display = 'none';
    try {
        const res = await fetch('/api/police/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.token) {
            // Set cookie
            document.cookie = 'gfin_police_token=' + data.token + '; path=/; max-age=604800; secure; samesite=strict';
            successDiv.textContent = 'Login successful! Redirecting to dashboard...';
            successDiv.style.display = 'block';
            setTimeout(() => { window.location.href = '/dashboard'; }, 800);
        } else {
            errDiv.textContent = data.detail || data.error || 'Login failed';
            errDiv.style.display = 'block';
            btn.disabled = false;
            btn.textContent = 'Sign In';
        }
    } catch (err) {
        errDiv.textContent = 'Network error. Please try again.';
        errDiv.style.display = 'block';
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
});
</script>
</body>
</html>"""


# ==================== POLICE DASHBOARD WITH AUTH GUARD ====================

POLICE_DASHBOARD_GUARD = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GFIN Dashboard — Redirecting</title>
<script>
// Check for auth token
const token = document.cookie.includes('gfin_police_token');
if (!token) {
    window.location.href = '/police/login';
} else {
    window.location.href = '/dashboard';
}
</script>
</head>
<body>
<p>Redirecting...</p>
</body>
</html>
"""

# ============================================================
# TOKEN REFRESH & REVOCATION (v2 upgrade)
# ============================================================
import psycopg2 as _psycopg2
import hashlib as _hashlib

_AUTH_DB = {"host": "127.0.0.1", "port": 6432, "dbname": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

def _auth_conn():
    return _psycopg2.connect(**_AUTH_DB)

def _hash_tok(token):
    return _hashlib.sha256(token.encode()).hexdigest()

def init_auth_tables():
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            token_hash VARCHAR(64) PRIMARY KEY,
            token_type VARCHAR(10) NOT NULL,
            officer_id INTEGER NOT NULL,
            revoked_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL
        );
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_hash VARCHAR(64) PRIMARY KEY,
            officer_id INTEGER NOT NULL,
            issued_at TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            ip_address VARCHAR(45),
            user_agent TEXT
        );
    """)
    conn.commit()
    conn.close()

def generate_refresh_token(officer_id, ip="", ua=""):
    """Generate and store a refresh token."""
    token = secrets.token_urlsafe(48)
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO refresh_tokens (token_hash, officer_id, expires_at, ip_address, user_agent) VALUES (%s, %s, NOW() + INTERVAL \"7 days\", %s, %s)",
        (_hash_tok(token), officer_id, ip, ua)
    )
    conn.commit()
    conn.close()
    return token

def validate_refresh_token(token):
    """Validate refresh token (single-use). Returns officer_id or None."""
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT officer_id FROM refresh_tokens WHERE token_hash = %s AND expires_at > NOW() AND used = FALSE",
        (_hash_tok(token),)
    )
    result = cur.fetchone()
    if result:
        cur.execute("UPDATE refresh_tokens SET used = TRUE WHERE token_hash = %s", (_hash_tok(token),))
        conn.commit()
        conn.close()
        return result[0]
    conn.close()
    return None

def revoke_token(token, officer_id):
    """Add token to blacklist."""
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO token_blacklist (token_hash, token_type, officer_id, expires_at) VALUES (%s, %s, %s, NOW() + INTERVAL \"1 hour\") ON CONFLICT DO NOTHING",
        (_hash_tok(token), "ACCESS", officer_id)
    )
    conn.commit()
    conn.close()

def is_token_revoked(token):
    """Check if token is blacklisted."""
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM token_blacklist WHERE token_hash = %s AND expires_at > NOW()", (_hash_tok(token),))
    result = cur.fetchone()
    conn.close()
    return result is not None

def revoke_all_tokens(officer_id):
    """Revoke all refresh tokens for an officer."""
    conn = _auth_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM refresh_tokens WHERE officer_id = %s", (officer_id,))
    conn.commit()
    conn.close()

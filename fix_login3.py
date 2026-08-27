#!/usr/bin/env python3
"""Fix police login: robust cookie + redirect + server-side URL decode."""

# 1. Fix login page
login = open("/gfin/police_login_gov.html").read()

old_code = """                if (resp.ok && data.token) {
                    // Store token as cookie so /dashboard can read it
                    document.cookie = 'gfin_police_token=' + data.token + '; path=/; max-age=604800; SameSite=Lax';
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting to dashboard...';
                    setTimeout(() => window.location.href = '/dashboard', 800);
                } else {"""

new_code = """                if (resp.ok && data.token) {
                    // Store token as cookie so /dashboard can read it
                    document.cookie = 'gfin_police_token=' + data.token + '; path=/; max-age=604800; SameSite=Lax; Secure';
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting...';
                    window.location.href = '/dashboard';
                } else {"""

login = login.replace(old_code, new_code)
open("/gfin/police_login_gov.html", "w").write(login)
print("Login page: redirect to /dashboard immediately (no setTimeout)")

# 2. Fix server to URL-decode cookie token (in case browser encodes it)
server = open("/gfin/gfin_server.py").read()

old_dashboard = '''@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias(request: Request):
    """Police dashboard — checks for auth, redirects if not logged in."""
    if _police_auth:
        token = request.cookies.get("gfin_police_token", "")
        if not token:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
        payload = verify_token(token)
        if not payload:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')'''

new_dashboard = '''@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias(request: Request):
    """Police dashboard — checks for auth, redirects if not logged in."""
    if _police_auth:
        from urllib.parse import unquote
        token = unquote(request.cookies.get("gfin_police_token", ""))
        if not token:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
        payload = verify_token(token)
        if not payload:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')'''

server = server.replace(old_dashboard, new_dashboard)
open("/gfin/gfin_server.py", "w").write(server)
print("Server: URL-decode cookie token before verification")

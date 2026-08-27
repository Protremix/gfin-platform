#!/usr/bin/env python3
"""Fix police login: store token as cookie before redirecting to dashboard."""

content = open("/gfin/police_login_gov.html").read()

# The current code redirects without setting the cookie
old_redirect = """                if (resp.ok && data.token) {
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting to dashboard...';
                    setTimeout(() => window.location.href = '/dashboard', 1000);
                } else {"""

new_redirect = """                if (resp.ok && data.token) {
                    // Store token as cookie so /dashboard can read it
                    document.cookie = 'gfin_police_token=' + data.token + '; path=/; max-age=604800; SameSite=Lax';
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting to dashboard...';
                    setTimeout(() => window.location.href = '/dashboard', 800);
                } else {"""

content = content.replace(old_redirect, new_redirect)

open("/gfin/police_login_gov.html", "w").write(content)
print("Fixed: token now stored as cookie before redirect")

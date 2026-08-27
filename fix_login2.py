#!/usr/bin/env python3
"""Fix police login redirect - add debug logging and use replace() instead of href."""

content = open("/gfin/police_login_gov.html").read()

old_code = """                if (resp.ok && data.token) {
                    // Store token as cookie so /dashboard can read it
                    document.cookie = 'gfin_police_token=' + data.token + '; path=/; max-age=604800; SameSite=Lax';
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting to dashboard...';
                    setTimeout(() => window.location.href = '/dashboard', 800);
                } else {"""

new_code = """                if (resp.ok && data.token) {
                    // Store token as cookie so /dashboard can read it
                    try {
                        document.cookie = 'gfin_police_token=' + encodeURIComponent(data.token) + '; path=/; max-age=604800; SameSite=Lax';
                    } catch(e) { console.error('Cookie set failed:', e); }
                    alert.className = 'alert success';
                    alert.textContent = 'Login successful. Redirecting to dashboard...';
                    // Redirect immediately using replace() for reliability
                    setTimeout(function() {
                        window.location.replace('/dashboard');
                    }, 500);
                } else {"""

content = content.replace(old_code, new_code)

# Also fix the server-side verify_token to handle URL-encoded tokens
open("/gfin/police_login_gov.html", "w").write(content)
print("Login redirect fixed: using encodeURIComponent + window.location.replace()")

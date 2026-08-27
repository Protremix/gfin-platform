#!/usr/bin/env python3
"""Fix script to add dynamic hosting platform filtering to autonomous_hunter.py"""
import re

with open("/gfin/autonomous_hunter.py", 'r') as f:
    content = f.read()

old_safe = '''    safe_patterns = [
        "google.com", "googleapis.com", "cloudflare.com", "amazonaws.com",
        "microsoft.com", "github.com", "wikipedia.org", "mozilla.org",
        "letsencrypt.org", "digicert.com", "godaddy.com", "cloudfront.net",
        "akamai.com", "azure.com", "office.com", "live.com", "yahoo.com",
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "apple.com", "mozilla.com", "bootstrap.com", "jquery.com",
    ]'''

new_safe = '''    safe_patterns = [
        "google.com", "googleapis.com", "cloudflare.com", "amazonaws.com",
        "microsoft.com", "github.com", "wikipedia.org", "mozilla.org",
        "letsencrypt.org", "digicert.com", "godaddy.com", "cloudfront.net",
        "akamai.com", "azure.com", "office.com", "live.com", "yahoo.com",
        "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
        "apple.com", "mozilla.com", "bootstrap.com", "jquery.com",
        "nip.io", "sslip.io", "xip.io",
        "pages.dev", "workers.dev", "r2.dev",
        "netlify.app", "vercel.app", "herokuapp.com",
        "000webhostapp.com", "infinityfree.com",
        "github.io", "gitlab.io",
        "heroku.com", "fly.dev", "railway.app",
        "repl.co", "glitch.me",
        "onrender.com", "render.com",
        "deno.dev",
        "fastly.net", "fastly.io",
    ]'''

content = content.replace(old_safe, new_safe)

with open("/gfin/autonomous_hunter.py", 'w') as f:
    f.write(content)
print("Added dynamic hosting platform filtering")

import re

with open("/gfin/telegram_spy.py", "r") as f:
    spy = f.read()

# Find the SAFE_DOMAINS closing and add more entries
old_safe = '"gfin-system.com"\n}'
new_safe = '''"gfin-system.com",
    # False positive patterns from Telegram text
    "usdt.send", "usdt.if", "authorize.net", "erica.chan", "services.all",
    "pm.me", "wa.link", "2fbitcoinmagazine.com", "youtu.be",
    "crypto.com",
}'''

spy = spy.replace(old_safe, new_safe, 1)

# Add filter for numbered country domains
old_extract = '''    if domain in SAFE_DOMAINS:
            continue
        if domain.endswith((".png",".jpg",".jpeg",".gif",".svg",".pdf",".webp")):
            continue'''

new_extract = '''    if domain in SAFE_DOMAINS:
            continue
        if domain.endswith((".png",".jpg",".jpeg",".gif",".svg",".pdf",".webp")):
            continue
        # Skip numbered patterns like 1.serbia, 2.greece (not real domains)
        if re.match(r'^\d+\.', domain):
            continue'''

spy = spy.replace(old_extract, new_extract, 1)

with open("/gfin/telegram_spy.py", "w") as f:
    f.write(spy)

print("Spy domain filtering updated")

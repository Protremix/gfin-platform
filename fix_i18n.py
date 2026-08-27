#!/usr/bin/env python3
"""Add data-i18n attributes to privacy, terms, and contact pages."""

def add_i18n_attrs(filename, replacements):
    content = open(filename).read()
    count = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            count += 1
    open(filename, "w").write(content)
    print(f"{filename}: {count}/{len(replacements)} attributes added")

# Privacy page
add_i18n_attrs("/gfin/privacy_policy.html", [
    ("<h1>Privacy Policy</h1>", '<h1 data-i18n="privacy_title">Privacy Policy</h1>'),
    ("<p>How GFIN collects, processes, and protects your data</p>", '<p data-i18n="privacy_subtitle">How GFIN collects, processes, and protects your data</p>'),
    ('<a href="/">\u2190 Back to Home</a>', '<a href="/" data-i18n="privacy_back">\u2190 Back to Home</a>'),
])

# Terms page
add_i18n_attrs("/gfin/terms_of_use.html", [
    ("<h1>Terms of Use</h1>", '<h1 data-i18n="terms_title">Terms of Use</h1>'),
    ("<p>Terms and conditions for using GFIN</p>", '<p data-i18n="terms_subtitle">Terms and conditions for using GFIN</p>'),
    ('<a href="/">\u2190 Back to Home</a>', '<a href="/" data-i18n="terms_back">\u2190 Back to Home</a>'),
])

# Contact page
add_i18n_attrs("/gfin/contact_page.html", [
    ("<h1>Contact GFIN</h1>", '<h1 data-i18n="contact_title">Contact GFIN</h1>'),
    ("<p>Get help with fraud reports, technical issues, or law enforcement access</p>", '<p data-i18n="contact_subtitle">Get help with fraud reports, technical issues, or law enforcement access</p>'),
    ("<h2>\u26a0\ufe0f In Immediate Danger or Financial Loss?</h2>", '<h2 data-i18n="contact_emergency_title">\u26a0\ufe0f In Immediate Danger or Financial Loss?</h2>'),
    ("<p>Contact your local emergency services (999 / 112 / 911) or your national fraud hotline immediately. GFIN processes complaints within 17 seconds but is not an emergency service.</p>", '<p data-i18n="contact_emergency_desc">Contact your local emergency services (999 / 112 / 911) or your national fraud hotline immediately. GFIN processes complaints within 17 seconds but is not an emergency service.</p>'),
    ("<h2>\U0001f4ac Telegram Bot \u2014 Fastest Response</h2>", '<h2 data-i18n="contact_telegram_title">\U0001f4ac Telegram Bot \u2014 Fastest Response</h2>'),
    ("<p>Check if a website is a scam, get scam alerts, and access awareness materials</p>", '<p data-i18n="contact_telegram_desc">Check if a website is a scam, get scam alerts, and access awareness materials</p>'),
    ("<h2>Contact Channels</h2>", '<h2 data-i18n="contact_channels_title">Contact Channels</h2>'),
    ('<a href="/">\u2190 Back to Home</a>', '<a href="/" data-i18n="contact_back">\u2190 Back to Home</a>'),
])

print("\nAll i18n attributes added!")

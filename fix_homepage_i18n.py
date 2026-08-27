#!/usr/bin/env python3
"""Add data-i18n attributes to the GFIN homepage."""
import re

content = open("/gfin/gfin_homepage.html").read()

# Map English text to i18n keys
replacements = [
    # Navigation
    ('>Home<', '>Home</a>\n', '>Home</a>'),  # Skip these - we need more context
]

# More precise replacements - find elements and add data-i18n
text_to_key = {
    # Nav
    'href="/">Home': 'href="/" data-i18n="nav_home">Home',
    'href="/victim">Report a Scam': 'href="/victim" data-i18n="nav_report">Report a Scam',
    'href="/scam-sites">Scam Database': 'href="/scam-sites" data-i18n="nav_scam_db">Scam Database',
    'href="#awareness">Awareness': 'href="#awareness" data-i18n="nav_awareness">Awareness',
    'href="#about">About': 'href="#about" data-i18n="nav_about">About',
    'href="/police/login">Police Login': 'href="/police/login" data-i18n="nav_police">Police Login',
    
    # Hero
    'Official Government-Grade Fraud Intelligence Platform': None,  # already has text
    'Protecting Citizens from': None,
    'Fraud Worldwide': None,
    
    # Footer links
    'href="/privacy">Privacy Policy': 'href="/privacy" data-i18n="footer_privacy">Privacy Policy',
    'href="/terms">Terms of Use': 'href="/terms" data-i18n="footer_terms">Terms of Use',
    'href="/api/docs">API Documentation': 'href="/api/docs" data-i18n="footer_api_docs">API Documentation',
    'href="/contact">Contact': 'href="/contact" data-i18n="footer_contact">Contact',
    'href="/sitemap.xml">Sitemap': 'href="/sitemap.xml" data-i18n="footer_sitemap">Sitemap',
}

# Add data-i18n to specific elements by finding text patterns
# Let's use a simpler approach - find text content and add data-i18n to the parent element

# Hero section
content = content.replace(
    'class="hero-badge"',
    'class="hero-badge" data-i18n="hero_badge"'
)

# Find and add data-i18n to specific text spans
specific_replacements = [
    # Stats
    ('Countries Connected', 'data-i18n="stat_countries">Countries Connected'),
    ('Intelligence Providers', 'data-i18n="stat_providers">Intelligence Providers'),
    ('Scam Categories Tracked', 'data-i18n="stat_categories">Scam Categories Tracked'),
    ('Continuous Monitoring', 'data-i18n="stat_monitoring">Continuous Monitoring'),
    
    # How it works
    ('How GFIN Works', 'data-i18n="how_title">How GFIN Works'),
    ('From Complaint to Investigation in 17 Seconds', 'data-i18n="how_subtitle">From Complaint to Investigation in 17 Seconds'),
    
    # Steps
    ('>Report a Scam<', 'data-i18n="step1_title">Report a Scam<'),  # might be too broad
]

# Let's be more surgical. Add data-i18n to elements that contain specific text.
# We'll find elements by their text content and add the attribute.

# Key text replacements that are safe (unique enough text)
safe_replacements = [
    ('The Global Fraud Intelligence Network connects law enforcement',
     'data-i18n="hero_desc"'),
    ('Our automated pipeline detects scams, collects evidence',
     'data-i18n="how_desc"'),
    ('Victims file complaints through our secure portal in any of 7 languages',
     'data-i18n="step1_desc"'),
    ('Our deterministic engine analyzes 300+ scam patterns across 15 categories',
     'data-i18n="step2_desc"'),
    ('72 intelligence providers automatically gather evidence',
     'data-i18n="step3_desc"'),
    ('Cases are automatically routed to the correct national cybercrime authority',
     'data-i18n="step4_desc"'),
    ('Secure multi-language portal for victims to report fraud',
     'data-i18n="service1_desc"'),
    ('Deterministic v3.0 engine with 300+ patterns across 15 categories',
     'data-i18n="service2_desc"'),
    ('Multi-chain cryptocurrency tracing across 10 wallet types',
     'data-i18n="service3_desc"'),
    ('13 entity types traced from domain to physical address',
     'data-i18n="service4_desc"'),
    ('Automated routing to 189 national cybercrime authorities',
     'data-i18n="service5_desc"'),
    ('Public anonymized scam alerts and 12-type awareness broadcasts',
     'data-i18n="service6_desc"'),
    ('GFIN routes intelligence to national cybercrime units',
     'data-i18n="partners_desc"'),
    ('GFIN tracks 15 categories of fraud',
     'data-i18n="awareness_desc"'),
    ('Someone promises to recover money already lost to scams',
     'data-i18n="awareness_recovery_desc"'),
    ('Fake online relationships that end in requests for money',
     'data-i18n="awareness_romance_desc"'),
    ('Fake trading platforms promising high returns',
     'data-i18n="awareness_investment_desc"'),
    ('Fake emails and websites stealing your passwords',
     'data-i18n="awareness_phishing_desc"'),
    ('Criminals posing as police, government, or tech support',
     'data-i18n="awareness_impersonation_desc"'),
    ('Fake exchanges, rug pulls, and Ponzi schemes',
     'data-i18n="awareness_crypto_desc"'),
    ('Fake Microsoft/Apple calls to gain remote access',
     'data-i18n="awareness_tech_desc"'),
    ('Pay a fee upfront to unlock a prize, loan, or inheritance',
     'data-i18n="awareness_advance_desc"'),
    ('File a complaint now. Our automated system starts investigating immediately',
     'data-i18n="cta_desc"'),
    ('An international law enforcement platform for cross-border fraud',
     'data-i18n="footer_desc"'),
    ('© 2026 Global Fraud Intelligence Network. All rights reserved.',
     'data-i18n="footer_copyright"'),
]

for text_fragment, attr in safe_replacements:
    if text_fragment in content:
        # Find the element containing this text and add data-i18n to the opening tag
        idx = content.find(text_fragment)
        if idx > 0:
            # Find the opening tag before this text
            tag_end = content.rfind('>', 0, idx)
            tag_start = content.rfind('<', 0, tag_end)
            if tag_start >= 0 and tag_end >= 0:
                tag = content[tag_start:tag_end+1]
                if 'data-i18n' not in tag:
                    new_tag = tag[:-1] + ' ' + attr + '>'
                    content = content[:tag_start] + new_tag + content[tag_end+1:]

# Also add data-i18n to specific known elements
# Hero badge
content = content.replace(
    'class="hero-badge"',
    'class="hero-badge" data-i18n="hero_badge"'
)

# CTA buttons
content = content.replace(
    '>Report a Scam in 17 Seconds<',
    ' data-i18n="cta_title">Report a Scam in 17 Seconds<'
)
content = content.replace(
    '>File a Complaint<',
    ' data-i18n="cta_btn">File a Complaint<'
)
content = content.replace(
    '>Check a Website<',
    ' data-i18n="cta_btn2">Check a Website<'
)

# Footer sections
content = content.replace(
    '>Services<',
    ' data-i18n="footer_services">Services<'
)
content = content.replace(
    '>Resources<',
    ' data-i18n="footer_resources">Resources<'
)
content = content.replace(
    '>Legal<',
    ' data-i18n="footer_legal">Legal<'
)

open("/gfin/gfin_homepage.html", "w").write(content)
print("Homepage data-i18n attributes added")
print(f"Total data-i18n attributes: {content.count('data-i18n')}")

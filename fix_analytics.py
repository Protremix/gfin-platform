#!/usr/bin/env python3
"""Add data-i18n attributes and lang switcher to analytics dashboard."""
content = open("/gfin/analytics_dashboard.html").read()

switcher = """<div style="position:relative;display:inline-block;margin-left:12px">
          <button id="langBtn" onclick="document.getElementById('langDropdown').classList.toggle('show')" style="background:transparent;border:1px solid #334155;color:#94a3b8;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px">&#127760; <span id="currentLang">EN</span> &#9662;</button>
          <div id="langDropdown" style="display:none;position:absolute;right:0;top:100%;background:#0a0e1a;border:1px solid #334155;border-radius:8px;min-width:140px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.5)"></div>
        </div>"""

# Replace Refresh Data button with switcher + button with data-i18n
old_btn = '<button class="btn" onclick="refreshAllData()">Refresh Data</button>'
new_btn = switcher + '\n            <button class="btn" onclick="refreshAllData()" data-i18n="analytics_refresh">Refresh Data</button>'
content = content.replace(old_btn, new_btn)

# Add data-i18n attributes
replacements = [
    ('<h1>Fraud Intelligence & Analytics Engine</h1>',
     '<h1 data-i18n="analytics_title">Fraud Intelligence & Analytics Engine</h1>'),
    ('<span>System Operational</span>',
     '<span data-i18n="analytics_operational">System Operational</span>'),
    ('Total Complaints', '<span data-i18n="analytics_total_complaints">Total Complaints</span>'),
    ('Active Cases', '<span data-i18n="analytics_active_cases">Active Cases</span>'),
    ('Total Losses', '<span data-i18n="analytics_total_losses">Total Losses</span>'),
    ('Wallets Traced', '<span data-i18n="analytics_wallets_traced">Wallets Traced</span>'),
    ('Global Complaint Density by Country',
     '<span data-i18n="analytics_map_title">Global Complaint Density by Country</span>'),
    ('Risk Level Breakdown',
     '<span data-i18n="analytics_risk_breakdown">Risk Level Breakdown</span>'),
]

for old, new in replacements:
    content = content.replace(old, new)

open("/gfin/analytics_dashboard.html", "w").write(content)
print("Analytics dashboard updated with i18n + lang switcher")

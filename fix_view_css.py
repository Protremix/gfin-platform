"""Remove inline style="display:none;" from the 5 new view sections — CSS already handles hiding."""

with open("/gfin/police_dashboard_mobile.html", "r") as f:
    code = f.read()

# Remove the inline style="display:none;" from the 5 new view sections
fixes = [
    ('<section id="viewLaundering" class="view-section" style="display:none;">',
     '<section id="viewLaundering" class="view-section">'),
    ('<section id="viewWallets" class="view-section" style="display:none;">',
     '<section id="viewWallets" class="view-section">'),
    ('<section id="viewEvidence" class="view-section" style="display:none;">',
     '<section id="viewEvidence" class="view-section">'),
    ('<section id="viewOperators" class="view-section" style="display:none;">',
     '<section id="viewOperators" class="view-section">'),
    ('<section id="viewOutreach" class="view-section" style="display:none;">',
     '<section id="viewOutreach" class="view-section">'),
]

for old, new in fixes:
    if old in code:
        code = code.replace(old, new)
        print(f"Fixed: {new}")
    else:
        print(f"Not found: {old}")

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(code)

print("\nDone — inline display:none removed, CSS will handle show/hide")

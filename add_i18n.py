#!/usr/bin/env python3
"""Add i18n script and language switcher to all GFIN pages."""
import sys

LANG_SWITCHER_DARK = '''<div style="position:relative;display:inline-block;margin-left:12px">
          <button id="langBtn" onclick="document.getElementById('langDropdown').classList.toggle('show')" style="background:transparent;border:1px solid #334155;color:#94a3b8;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px">&#127760; <span id="currentLang">EN</span> &#9662;</button>
          <div id="langDropdown" style="display:none;position:absolute;right:0;top:100%;background:#0a0e1a;border:1px solid #334155;border-radius:8px;min-width:140px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.5)"></div>
        </div>'''

LANG_SWITCHER_GOLD = '''<div style="position:relative;display:inline-block;margin-left:12px">
          <button id="langBtn" onclick="document.getElementById('langDropdown').classList.toggle('show')" style="background:transparent;border:1px solid rgba(201,169,90,0.3);color:#c5a55a;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px">&#127760; <span id="currentLang">EN</span> &#9662;</button>
          <div id="langDropdown" style="display:none;position:absolute;right:0;top:100%;background:#0a0e1a;border:1px solid rgba(201,169,90,0.3);border-radius:8px;min-width:140px;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,0.5)"></div>
        </div>'''

I18N_SCRIPT = '<script src="/gfin-i18n.js"></script>\n</body>'

def add_i18n_to_page(filepath, lang_switcher_html):
    try:
        content = open(filepath).read()
    except:
        print(f"  SKIP: {filepath} not found")
        return

    changed = False

    # Add script before </body>
    if 'gfin-i18n.js' not in content:
        content = content.replace('</body>', I18N_SCRIPT)
        changed = True
        print("  Added i18n script")
    else:
        print("  i18n script already present")

    # Add language switcher
    if 'langBtn' not in content:
        if '\u2190 Back to Home' in content:
            content = content.replace(
                '\u2190 Back to Home',
                '<span style="color:#64748b">\u2190 Back to Home</span>'
            )
            # Find the parent link and add switcher after it
            content = content.replace(
                'Back to Home</a>',
                'Back to Home</a>\n        ' + lang_switcher_html
            )
            changed = True
            print("  Added lang switcher (back-to-home style)")
        elif 'Back to GFIN homepage' in content:
            content = content.replace(
                'Back to GFIN homepage</a>',
                'Back to GFIN homepage</a>\n        ' + lang_switcher_html
            )
            changed = True
            print("  Added lang switcher (police back style)")
        else:
            idx = content.find('</header>')
            if idx > 0:
                content = content[:idx] + '    ' + lang_switcher_html + '\n    ' + content[idx:]
                changed = True
                print("  Added lang switcher (header style)")
            else:
                idx = content.find('</nav>')
                if idx > 0:
                    content = content[:idx] + '    ' + lang_switcher_html + '\n    ' + content[idx:]
                    changed = True
                    print("  Added lang switcher (nav style)")
                else:
                    print("  WARNING: Could not find insertion point for lang switcher")
    else:
        print("  Lang switcher already present")

    if changed:
        open(filepath, 'w').write(content)

pages = [
    ('/gfin/gfin_homepage.html', LANG_SWITCHER_GOLD),
    ('/gfin/privacy_policy.html', LANG_SWITCHER_DARK),
    ('/gfin/terms_of_use.html', LANG_SWITCHER_DARK),
    ('/gfin/contact_page.html', LANG_SWITCHER_DARK),
    ('/gfin/api_docs.html', LANG_SWITCHER_DARK),
    ('/gfin/police_login_gov.html', LANG_SWITCHER_DARK),
    ('/gfin/scam_sites_page.html', LANG_SWITCHER_DARK),
    ('/gfin/analytics_dashboard.html', LANG_SWITCHER_DARK),
    ('/gfin/victim_portal_i18n.html', LANG_SWITCHER_GOLD),
]

for filepath, switcher in pages:
    print(f"\n=== {filepath.split('/')[-1]} ===")
    add_i18n_to_page(filepath, switcher)

print("\nDONE")

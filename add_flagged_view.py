#!/usr/bin/env python3
"""
Add Flagged Domains API endpoint and dashboard view.
Shows all domains flagged by the Hunter but not promoted to full cases.
"""
import json

# 1. Add API endpoint to gfin_server.py
with open("/gfin/gfin_server.py", "r") as f:
    server = f.read()

flagged_api = '''

@app.get("/api/flagged-domains")
async def get_flagged_domains(limit: int = 50):
    """Get all flagged domains from scam_websites database."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        rows = await conn.fetch(
            "SELECT domain, scam_type, risk_level, report_count, sources, first_reported, last_reported, countries_affected, wallet_addresses, phone_numbers, status, is_verified, description FROM scam_websites ORDER BY last_reported DESC LIMIT $1",
            limit
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM scam_websites")
        high_risk = await conn.fetchval("SELECT COUNT(*) FROM scam_websites WHERE risk_level IN ('HIGH','CRITICAL')")
        verified = await conn.fetchval("SELECT COUNT(*) FROM scam_websites WHERE is_verified = true")
        return {
            "total": total,
            "high_risk": high_risk,
            "verified": verified,
            "domains": [
                {
                    "domain": r["domain"],
                    "scam_type": r["scam_type"],
                    "risk_level": r["risk_level"],
                    "report_count": r["report_count"],
                    "sources": r["sources"] or [],
                    "first_reported": r["first_reported"].isoformat() if r["first_reported"] else None,
                    "last_reported": r["last_reported"].isoformat() if r["last_reported"] else None,
                    "countries_affected": r["countries_affected"] or [],
                    "wallet_addresses": r["wallet_addresses"] or [],
                    "phone_numbers": r["phone_numbers"] or [],
                    "status": r["status"],
                    "is_verified": r["is_verified"],
                    "description": (r["description"] or "")[:200],
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()

'''

if "/api/flagged-domains" not in server:
    # Insert before the stats endpoint
    if '@app.get("/api/stats")' in server:
        server = server.replace('@app.get("/api/stats")', flagged_api + '\n@app.get("/api/stats")')
    else:
        server += flagged_api
    with open("/gfin/gfin_server.py", "w") as f:
        f.write(server)
    print("Added flagged-domains API endpoint")
else:
    print("Flagged-domains API already exists")

# 2. Add Flagged Domains view to dashboard
with open("/gfin/police_dashboard_mobile.html", "r") as f:
    html = f.read()

# Add sidebar nav item — between Hunter and Alerts
old_nav = '<a class="sidebar-item" data-view="alerts" onclick="switchView(\'alerts\')"><i class="fa-solid fa-bell"></i> Alerts</a>'
new_nav = '<a class="sidebar-item" data-view="flagged" onclick="switchView(\'flagged\')"><i class="fa-solid fa-flag"></i> Flagged</a>\n        <a class="sidebar-item" data-view="alerts" onclick="switchView(\'alerts\')"><i class="fa-solid fa-bell"></i> Alerts</a>'

if 'data-view="flagged"' not in html:
    html = html.replace(old_nav, new_nav)
    print("Added Flagged sidebar item")

# Add view section — between Hunter and Officers
old_section = """      <!-- OFFICERS -->
      <section id="viewOfficers" class="view-section">"""

flagged_section = """      <!-- FLAGGED DOMAINS -->
      <section id="viewFlagged" class="view-section">
        <div class="page-header"><div class="page-title">Flagged Domains</div><div class="page-subtitle">Suspicious domains detected by the Hunter — not yet promoted to full cases</div></div>
        <div class="stats-grid" id="flaggedStats"></div>
        <div class="info-panel">
          <div class="card-title"><i class="fa-solid fa-flag"></i> Flagged Domain List</div>
          <div id="flaggedList"></div>
        </div>
      </section>

      <!-- OFFICERS -->
      <section id="viewOfficers" class="view-section">"""

if 'id="viewFlagged"' not in html:
    html = html.replace(old_section, flagged_section)
    print("Added Flagged view section")

# Add JS for loading flagged domains — before the closing </script>
flagged_js = """
    // === FLAGGED DOMAINS ===
    async function loadFlaggedDomains() {
      try {
        const data = await apiGet('/api/flagged-domains?limit=50');
        const stats = document.getElementById('flaggedStats');
        if (!stats) return;
        stats.innerHTML =
          statCard('Flagged', data.total || 0, 'fa-flag', '#dc3545') +
          statCard('High Risk', data.high_risk || 0, 'fa-triangle-exclamation', '#fd7e14') +
          statCard('Verified', data.verified || 0, 'fa-check-circle', '#28a745') +
          statCard('Total Cases', (data.total || 0) - (data.high_risk || 0), 'fa-folder', '#6c757d');

        const listEl = document.getElementById('flaggedList');
        const domains = data.domains || [];
        if (domains.length === 0) {
          listEl.innerHTML = '<div class="empty-state"><p>No flagged domains yet.</p></div>';
          return;
        }
        listEl.innerHTML = domains.map(d => {
          const riskClass = d.risk_level === 'HIGH' || d.risk_level === 'CRITICAL' ? 'high' :
                           d.risk_level === 'MEDIUM' ? 'medium' : 'low';
          const sources = (d.sources || []).join(', ');
          const countries = (d.countries_affected || []).join(', ');
          const date = d.last_reported ? new Date(d.last_reported).toLocaleDateString('en-GB', {day:'2-digit',month:'short'}) : '';
          const wallets = (d.wallet_addresses || []).length;
          const phones = (d.phone_numbers || []).length;
          return '<div class="case-card">' +
            '<div class="case-header"><div><span style="font-weight:600;font-size:14px;color:#003366;">' + d.domain + '</span>' +
            '<span class="badge badge-' + riskClass + '" style="margin-left:8px;">' + (d.risk_level || 'UNKNOWN') + '</span></div>' +
            '<span class="badge badge-low">' + (d.status || 'FLAGGED') + '</span></div>' +
            '<div style="font-size:12px;color:var(--text-muted);margin-top:6px;">' + (d.scam_type || 'SUSPICIOUS') + ' | Reports: ' + d.report_count + ' | Source: ' + sources + '</div>' +
            '<div style="display:flex;gap:16px;margin-top:6px;font-size:11px;">' +
            (countries ? '<span style="color:#003366;"><i class="fa-solid fa-globe"></i> ' + countries + '</span>' : '') +
            (wallets ? '<span style="color:#dc3545;"><i class="fa-solid fa-wallet"></i> ' + wallets + ' wallets</span>' : '') +
            (phones ? '<span style="color:#fd7e14;"><i class="fa-solid fa-phone"></i> ' + phones + ' phones</span>' : '') +
            '<span style="color:var(--text-muted);margin-left:auto;"><i class="fa-solid fa-clock"></i> ' + date + '</span>' +
            '</div>' +
            (d.description ? '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;padding-top:6px;border-top:1px solid var(--border);">' + d.description.substring(0, 120) + '...</div>' : '') +
            '</div>';
        }).join('');
      } catch(e) {
        console.error('Flagged domains error:', e);
      }
    }

"""

# Add the loadFlaggedDomains call to switchView
old_switch = "if (viewName === 'hunter') loadHunterActivity();"
new_switch = "if (viewName === 'hunter') loadHunterActivity();\n      if (viewName === 'flagged') loadFlaggedDomains();"

if 'loadFlaggedDomains' not in html:
    # Find the last </script> and insert before it
    insert_pos = html.rfind('</script>')
    html = html[:insert_pos] + flagged_js + '\n' + html[insert_pos:]
    # Add to switchView
    html = html.replace(old_switch, new_switch)
    print("Added Flagged domains JS")

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(html)
print("Dashboard updated with Flagged Domains view")

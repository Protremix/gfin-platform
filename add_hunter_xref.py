#!/usr/bin/env python3
"""
Add two major features to GFIN:
1. Cross-reference API — find cases sharing IPs, hosting, certificates
2. Hunter Activity view in dashboard — real-time spy activity feed
"""
import json

# ============================================================
# PART 1: Add cross-reference API endpoint to gfin_server.py
# ============================================================
with open("/gfin/gfin_server.py", "r") as f:
    server = f.read()

# Add cross-reference endpoint if not present
if "/api/cases/{case_id}/cross-reference" not in server:
    xref_endpoint = '''

@app.get("/api/cases/{case_id}/cross-reference")
async def cross_reference_case(case_id: str):
    """Find other cases sharing IPs, hosting providers, or infrastructure with this case."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="GfinSecure2026!", database="gfin")
    try:
        # Get this case's identifiers
        case = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
        if not case:
            return {"error": "Case not found"}

        import json as j
        di_raw = case.get("digital_identifiers", "[]")
        if isinstance(di_raw, str):
            di = j.loads(di_raw) if di_raw else []
        else:
            di = di_raw or []

        # Extract IPs and hosting providers from this case
        this_ips = [d.get("value","") for d in di if d.get("type") == "IP"]
        this_hosting = [d.get("value","") for d in di if d.get("type") == "HOSTING_PROVIDER"]
        this_ns = [d.get("value","") for d in di if d.get("type") == "NS"]
        this_registrar = [d.get("value","") for d in di if d.get("type") == "REGISTRAR"]

        # Get all other cases
        other_cases = await conn.fetch("SELECT case_id, target, status, confidence, digital_identifiers, scam_patterns, affected_countries FROM cases WHERE case_id != $1", case_id)

        connections = []
        for oc in other_cases:
            oc_di_raw = oc.get("digital_identifiers", "[]")
            if isinstance(oc_di_raw, str):
                oc_di = j.loads(oc_di_raw) if oc_di_raw else []
            else:
                oc_di = oc_di_raw or []

            oc_ips = set(d.get("value","") for d in oc_di if d.get("type") == "IP")
            oc_hosting = set(d.get("value","") for d in oc_di if d.get("type") == "HOSTING_PROVIDER")
            oc_ns = set(d.get("value","") for d in oc_di if d.get("type") == "NS")
            oc_registrar = set(d.get("value","") for d in oc_di if d.get("type") == "REGISTRAR")

            # Find shared infrastructure
            shared_ips = set(this_ips) & oc_ips
            shared_hosting = set(this_hosting) & oc_hosting
            shared_ns = set(this_ns) & oc_ns
            shared_registrar = set(this_registrar) & oc_registrar

            if shared_ips or shared_hosting or shared_ns or shared_registrar:
                connections.append({
                    "case_id": oc["case_id"],
                    "target": oc["target"],
                    "status": oc["status"],
                    "confidence": float(oc["confidence"] or 0),
                    "scam_patterns": oc.get("scam_patterns", []) or [],
                    "affected_countries": oc.get("affected_countries", []) or [],
                    "shared_ips": list(shared_ips),
                    "shared_hosting": list(shared_hosting),
                    "shared_ns": list(shared_ns),
                    "shared_registrar": list(shared_registrar),
                    "connection_strength": len(shared_ips) * 3 + len(shared_hosting) * 2 + len(shared_ns) + len(shared_registrar),
                })

        # Sort by connection strength
        connections.sort(key=lambda x: x["connection_strength"], reverse=True)

        return {
            "case_id": case_id,
            "this_case": {
                "target": case["target"],
                "ips": this_ips,
                "hosting": this_hosting,
                "ns": this_ns,
                "registrar": this_registrar,
            },
            "connections": connections[:20],
            "total_connections": len(connections),
        }
    finally:
        await conn.close()

@app.get("/api/hunter/activity")
async def hunter_activity():
    """Get recent hunter activity — domains discovered, investigations run, intelligence collected."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="GfinSecure2026!", database="gfin")
    try:
        # Get recent cases created by hunter
        recent = await conn.fetch(
            "SELECT case_id, target, confidence, status, scam_patterns, affected_countries, digital_identifiers, physical_locations, created_date FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' ORDER BY created_date DESC LIMIT 50"
        )

        import json as j
        activities = []
        total_identifiers = 0
        total_locations = 0
        sources = {}
        patterns = {}

        for r in recent:
            di_raw = r.get("digital_identifiers", "[]")
            if isinstance(di_raw, str):
                di = j.loads(di_raw) if di_raw else []
            else:
                di = di_raw or []
            pl_raw = r.get("physical_locations", "[]")
            if isinstance(pl_raw, str):
                pl = j.loads(pl_raw) if pl_raw else []
            else:
                pl = pl_raw or []

            total_identifiers += len(di)
            total_locations += len(pl)

            # Count identifier types
            for d in di:
                t = d.get("type", "UNKNOWN")
                sources[t] = sources.get(t, 0) + 1

            for p in r.get("scam_patterns", []) or []:
                patterns[p] = patterns.get(p, 0) + 1

            activities.append({
                "case_id": r["case_id"],
                "target": r["target"],
                "confidence": float(r["confidence"] or 0),
                "status": r["status"],
                "identifier_count": len(di),
                "location_count": len(pl),
                "scam_patterns": r.get("scam_patterns", []) or [],
                "affected_countries": r.get("affected_countries", []) or [],
                "created_date": r["created_date"].isoformat() if r["created_date"] else None,
            })

        # Get total stats
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'")
        total_all = await conn.fetchval("SELECT COUNT(*) FROM cases")

        return {
            "total_hunter_cases": total_cases,
            "total_all_cases": total_all,
            "total_identifiers_collected": total_identifiers,
            "total_locations_found": total_locations,
            "identifier_types": dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)),
            "scam_patterns": dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)),
            "recent_activity": activities,
        }
    finally:
        await conn.close()

'''
    # Find a good insertion point — before the last line of the file
    # Find the @app.get("/api/stats") or similar near the end
    if '@app.get("/api/stats")' in server:
        server = server.replace('@app.get("/api/stats")', xref_endpoint + '\n@app.get("/api/stats")')
    else:
        server += xref_endpoint

    with open("/gfin/gfin_server.py", "w") as f:
        f.write(server)
    print("Added cross-reference and hunter activity API endpoints")
else:
    print("Cross-reference endpoint already exists")

# ============================================================
# PART 2: Add Hunter Activity view and Cross-reference to dashboard
# ============================================================
with open("/gfin/police_dashboard_mobile.html", "r") as f:
    dashboard = f.read()

# Add Hunter Activity nav item in sidebar
old_sidebar = """          <a class="sidebar-item" data-view="alerts" onclick="switchView('alerts')">
            <i class="fa-solid fa-bell"></i> Alerts"""

new_sidebar = """          <a class="sidebar-item" data-view="hunter" onclick="switchView('hunter')">
            <i class="fa-solid fa-satellite-dish"></i> Hunter
          </a>
          <a class="sidebar-item" data-view="alerts" onclick="switchView('alerts')">
            <i class="fa-solid fa-bell"></i> Alerts"""

if "data-view=\"hunter\"" not in dashboard:
    dashboard = dashboard.replace(old_sidebar, new_sidebar)

# Add Hunter Activity view section — after the alerts view, before settings
old_alerts_end = """        <!-- VIEW: Settings -->"""

new_hunter_view = """        <!-- VIEW: Hunter Activity -->
        <section id="viewHunter" class="view-section">
          <div class="page-header"><div class="page-title">Hunter Intelligence Activity</div><div class="page-subtitle">Autonomous scam discovery & investigation feed</div></div>

          <div class="stats-grid" id="hunterStats"></div>

          <div class="info-panel">
            <div class="card-title"><i class="fa-solid fa-chart-bar"></i> Intelligence Collected</div>
            <div id="hunterIntelTypes" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;"></div>
          </div>

          <div class="info-panel">
            <div class="card-title"><i class="fa-solid fa-radar"></i> Recent Discoveries</div>
            <div id="hunterActivityList"></div>
          </div>
        </section>

        <!-- VIEW: Settings -->"""

if "viewHunter" not in dashboard:
    dashboard = dashboard.replace(old_alerts_end, new_hunter_view)

# Add Cross-reference section to Intelligence tab — after Country Attribution
old_countries_end = """          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-globe"></i> Country Attribution</div><div id="intelCountries"></div></div>
        </div>

        <!-- TAB: Collaboration -->"""

new_countries_end = """          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-globe"></i> Country Attribution</div><div id="intelCountries"></div></div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-link"></i> Cross-Reference — Connected Cases</div><div id="intelXRef" style="font-size:12px;color:var(--text-muted);">Loading connections...</div></div>
        </div>

        <!-- TAB: Collaboration -->"""

if "intelXRef" not in dashboard:
    dashboard = dashboard.replace(old_countries_end, new_countries_end)

# Add JavaScript for Hunter Activity and Cross-reference
# Find the end of renderIntelligence function and add cross-reference call
old_intel_end = """      // Country Attribution
      const countries = c.affected_countries || [];
      const routed = c.routed_to_countries || [];
      document.getElementById('intelCountries').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Affected Countries</div>
            ${countries.length ? countries.map(cc => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-low" style="font-size:11px;">${cc}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">None identified</div>'}
          </div>
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Routed To (LEA)</div>
            ${routed.length ? routed.map(r => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-high" style="font-size:11px;">${r}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">Not routed</div>'}
          </div>
        </div>
      `;
    }"""

new_intel_end = """      // Country Attribution
      const countries = c.affected_countries || [];
      const routed = c.routed_to_countries || [];
      document.getElementById('intelCountries').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Affected Countries</div>
            ${countries.length ? countries.map(cc => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-low" style="font-size:11px;">${cc}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">None identified</div>'}
          </div>
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Routed To (LEA)</div>
            ${routed.length ? routed.map(r => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-high" style="font-size:11px;">${r}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">Not routed</div>'}
          </div>
        </div>
      `;

      // Cross-reference — load connected cases
      loadCrossReference(c.case_id);
    }

    async function loadCrossReference(caseId) {
      try {
        const xref = await apiGet('/api/cases/' + caseId + '/cross-reference');
        const el = document.getElementById('intelXRef');
        if (!xref || !xref.connections || xref.connections.length === 0) {
          el.innerHTML = '<div class="empty-state"><p>No connected cases found. This case has unique infrastructure.</p></div>';
          return;
        }
        el.innerHTML = xref.connections.map(conn => {
          const r = conn.confidence >= 0.7 ? 'high' : conn.confidence >= 0.4 ? 'medium' : 'low';
          const links = [];
          if (conn.shared_ips && conn.shared_ips.length) links.push('<span style="color:var(--navy);"><i class="fa-solid fa-network-wired"></i> Shared IP: ' + conn.shared_ips.join(', ') + '</span>');
          if (conn.shared_hosting && conn.shared_hosting.length) links.push('<span style="color:var(--navy);"><i class="fa-solid fa-building"></i> Shared hosting: ' + conn.shared_hosting.join(', ') + '</span>');
          if (conn.shared_ns && conn.shared_ns.length) links.push('<span style="color:var(--navy);"><i class="fa-solid fa-server"></i> Shared NS: ' + conn.shared_ns.join(', ') + '</span>');
          if (conn.shared_registrar && conn.shared_registrar.length) links.push('<span style="color:var(--navy);"><i class="fa-solid fa-id-card"></i> Shared registrar: ' + conn.shared_registrar.join(', ') + '</span>');
          return '<div style="margin-bottom:10px;padding:10px;border-radius:6px;background:var(--bg-page);border-left:3px solid var(--navy);cursor:pointer;" onclick="openCaseDetail(\\'' + conn.case_id + '\\')">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;">' +
            '<strong>' + conn.target + '</strong>' +
            '<span class="badge badge-' + r + '">' + Math.round(conn.confidence * 100) + '%</span>' +
            '</div>' +
            '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' + conn.case_id + ' | ' + (conn.scam_patterns || []).join(', ') + '</div>' +
            '<div style="font-size:11px;margin-top:4px;">' + links.join(' | ') + '</div>' +
            '</div>';
        }).join('');
      } catch(e) {
        document.getElementById('intelXRef').innerHTML = '<div class="empty-state"><p>Failed to load cross-reference data.</p></div>';
      }
    }

    // === HUNTER ACTIVITY ===
    async function loadHunterActivity() {
      try {
        const data = await apiGet('/api/hunter/activity');
        // Stats
        const stats = document.getElementById('hunterStats');
        stats.innerHTML = statCard('Hunter Cases', data.total_hunter_cases || 0, 'fa-satellite-dish', 'var(--navy)') +
          statCard('Total Cases', data.total_all_cases || 0, 'fa-folder', 'var(--text-muted)') +
          statCard('Identifiers', data.total_identifiers_collected || 0, 'fa-fingerprint', '#c5a55a') +
          statCard('Locations', data.total_locations_found || 0, 'fa-location-dot', '#e74c3c');

        // Intelligence types
        const typesEl = document.getElementById('hunterIntelTypes');
        const typeIcons = {'IP':'fa-network-wired','NS':'fa-server','HOSTING_PROVIDER':'fa-building','REGISTRAR':'fa-id-card','PHONE':'fa-phone','EMAIL':'fa-at','CRYPTO_WALLET':'fa-wallet','SOCIAL_ACCOUNT':'fa-share-nodes','MX':'fa-envelope'};
        if (data.identifier_types && Object.keys(data.identifier_types).length > 0) {
          typesEl.innerHTML = Object.entries(data.identifier_types).map(([type, count]) => {
            return '<div style="padding:8px 14px;border-radius:20px;background:var(--bg-page);border:1px solid var(--border);font-size:13px;">' +
              '<i class="fa-solid ' + (typeIcons[type] || 'fa-circle') + '" style="color:var(--navy);margin-right:6px;"></i>' +
              type + ': <strong>' + count + '</strong></div>';
          }).join('');
        } else {
          typesEl.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No intelligence collected yet.</div>';
        }

        // Recent activity
        const listEl = document.getElementById('hunterActivityList');
        const activities = data.recent_activity || [];
        if (activities.length === 0) {
          listEl.innerHTML = '<div class="empty-state"><p>No hunter activity yet.</p></div>';
          return;
        }
        listEl.innerHTML = activities.slice(0, 20).map(a => {
          const r = a.confidence >= 0.7 ? 'high' : a.confidence >= 0.4 ? 'medium' : 'low';
          const date = new Date(a.created_date).toLocaleString('en-GB', {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
          return '<div class="case-card" onclick="openCaseDetail(\\'' + a.case_id + '\\')">' +
            '<div class="case-header"><div><span class="case-ref">' + a.case_id + '</span>' +
            '<span class="badge badge-' + r + '" style="margin-left:8px;">' + Math.round(a.confidence * 100) + '%</span></div>' +
            '<span class="badge badge-' + (a.status || 'investigating').toLowerCase() + '">' + a.status + '</span></div>' +
            '<div class="case-target">' + a.target + '</div>' +
            '<div style="display:flex;gap:16px;margin-top:8px;font-size:12px;">' +
            '<span style="color:var(--text-muted);"><i class="fa-solid fa-fingerprint"></i> ' + a.identifier_count + ' identifiers</span>' +
            '<span style="color:var(--text-muted);"><i class="fa-solid fa-location-dot"></i> ' + a.location_count + ' locations</span>' +
            (a.affected_countries && a.affected_countries.length ? '<span style="color:var(--navy);"><i class="fa-solid fa-globe"></i> ' + a.affected_countries.join(', ') + '</span>' : '') +
            '<span style="color:var(--text-muted);margin-left:auto;"><i class="fa-solid fa-clock"></i> ' + date + '</span></div>' +
            '</div>';
        }).join('');
      } catch(e) {
        console.error('Hunter activity load error:', e);
      }
    }

    function statCard(label, value, icon, color) {
      return '<div class="stat-card"><div class="stat-card-top" style="background:' + color + ';"></div>' +
        '<div class="stat-card-body"><div class="stat-icon" style="color:' + color + ';"><i class="fa-solid ' + icon + '"></i></div>' +
        '<div class="stat-value">' + value + '</div><div class="stat-label">' + label + '</div></div></div>';
    }"""

if "loadHunterActivity" not in dashboard:
    dashboard = dashboard.replace(old_intel_end, new_intel_end)

# Add loadHunterActivity call to switchView
old_switch = """      if (viewName === 'officers') loadOfficers();"""
new_switch = """      if (viewName === 'officers') loadOfficers();
      if (viewName === 'hunter') loadHunterActivity();"""

if "loadHunterActivity()" not in dashboard or "if (viewName === 'hunter')" not in dashboard:
    dashboard = dashboard.replace(old_switch, new_switch)

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(dashboard)

print("Added Hunter Activity view and Cross-Reference to dashboard")

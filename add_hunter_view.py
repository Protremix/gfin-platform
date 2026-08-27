#!/usr/bin/env python3
"""Add Hunter Activity view section and JS to the dashboard."""

with open('/gfin/police_dashboard_mobile.html', 'r') as f:
    html = f.read()

# 1. Add Hunter view section between Alerts and Officers
old_section = """      <!-- OFFICERS -->
      <section id="viewOfficers" class="view-section">"""

hunter_section = """      <!-- HUNTER ACTIVITY -->
      <section id="viewHunter" class="view-section">
        <div class="page-header"><div class="page-title">Hunter Intelligence Activity</div><div class="page-subtitle">Autonomous scam discovery &amp; investigation feed — 24/7</div></div>
        <div class="stats-grid" id="hunterStats"></div>
        <div class="info-panel">
          <div class="card-title"><i class="fa-solid fa-chart-bar"></i> Intelligence Collected</div>
          <div id="hunterIntelTypes" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;"></div>
        </div>
        <div class="info-panel">
          <div class="card-title"><i class="fa-solid fa-satellite-dish"></i> Recent Discoveries</div>
          <div id="hunterActivityList"></div>
        </div>
      </section>

      <!-- OFFICERS -->
      <section id="viewOfficers" class="view-section">"""

if 'id="viewHunter"' not in html:
    html = html.replace(old_section, hunter_section)
    print("Hunter view section added")
else:
    print("Hunter view section already exists")

# 2. Add JS functions before the closing </script> tag
# Find a good insertion point — after the loadOfficers function
js_insert = """
    // === HUNTER ACTIVITY ===
    async function loadHunterActivity() {
      try {
        const data = await apiGet('/api/hunter/activity');
        const stats = document.getElementById('hunterStats');
        if (!stats) return;
        stats.innerHTML =
          statCard('Hunter Cases', data.total_hunter_cases || 0, 'fa-satellite-dish', '#003366') +
          statCard('Total Cases', data.total_all_cases || 0, 'fa-folder', '#6c757d') +
          statCard('Identifiers', data.total_identifiers_collected || 0, 'fa-fingerprint', '#c5a55a') +
          statCard('Locations', data.total_locations_found || 0, 'fa-location-dot', '#dc3545');

        const typesEl = document.getElementById('hunterIntelTypes');
        const typeIcons = {'IP':'fa-network-wired','NS':'fa-server','HOSTING_PROVIDER':'fa-building','REGISTRAR':'fa-id-card','PHONE':'fa-phone','EMAIL':'fa-at','CRYPTO_WALLET':'fa-wallet','SOCIAL_ACCOUNT':'fa-share-nodes','MX':'fa-envelope','COMPANY':'fa-building-columns'};
        if (data.identifier_types && Object.keys(data.identifier_types).length > 0) {
          typesEl.innerHTML = Object.entries(data.identifier_types).map(([type, count]) => {
            return '<div style="padding:8px 14px;border-radius:20px;background:var(--bg-page);border:1px solid var(--border);font-size:13px;">' +
              '<i class="fa-solid ' + (typeIcons[type] || 'fa-circle') + '" style="color:#003366;margin-right:6px;"></i>' +
              type + ': <strong>' + count + '</strong></div>';
          }).join('');
        } else {
          typesEl.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No intelligence collected yet.</div>';
        }

        const listEl = document.getElementById('hunterActivityList');
        const activities = data.recent_activity || [];
        if (activities.length === 0) {
          listEl.innerHTML = '<div class="empty-state"><p>No hunter activity yet.</p></div>';
          return;
        }
        listEl.innerHTML = activities.slice(0, 20).map(a => {
          const r = a.confidence >= 0.7 ? 'high' : a.confidence >= 0.4 ? 'medium' : 'low';
          const date = new Date(a.created_date).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
          return '<div class="case-card" onclick="openCaseDetail(\\'' + a.case_id + '\\')">' +
            '<div class="case-header"><div><span class="case-ref">' + a.case_id + '</span>' +
            '<span class="badge badge-' + r + '" style="margin-left:8px;">' + Math.round(a.confidence * 100) + '%</span></div>' +
            '<span class="badge badge-' + (a.status || 'investigating').toLowerCase() + '">' + a.status + '</span></div>' +
            '<div class="case-target">' + a.target + '</div>' +
            '<div style="display:flex;gap:16px;margin-top:8px;font-size:12px;">' +
            '<span style="color:var(--text-muted);"><i class="fa-solid fa-fingerprint"></i> ' + a.identifier_count + ' identifiers</span>' +
            '<span style="color:var(--text-muted);"><i class="fa-solid fa-location-dot"></i> ' + a.location_count + ' locations</span>' +
            (a.affected_countries && a.affected_countries.length ? '<span style="color:#003366;"><i class="fa-solid fa-globe"></i> ' + a.affected_countries.join(', ') + '</span>' : '') +
            '<span style="color:var(--text-muted);margin-left:auto;"><i class="fa-solid fa-clock"></i> ' + date + '</span></div>' +
            '</div>';
        }).join('');
      } catch(e) {
        console.error('Hunter activity error:', e);
      }
    }

    async function loadCrossReference(caseId) {
      try {
        const xref = await apiGet('/api/cases/' + caseId + '/cross-reference');
        const el = document.getElementById('intelXRef');
        if (!el) return;
        if (!xref || !xref.connections || xref.connections.length === 0) {
          el.innerHTML = '<div class="empty-state"><p>No connected cases found. This case has unique infrastructure.</p></div>';
          return;
        }
        el.innerHTML = xref.connections.map(conn => {
          const r = conn.confidence >= 0.7 ? 'high' : conn.confidence >= 0.4 ? 'medium' : 'low';
          const links = [];
          if (conn.shared_ips && conn.shared_ips.length) links.push('<span style="color:#003366;"><i class="fa-solid fa-network-wired"></i> IP: ' + conn.shared_ips.join(', ') + '</span>');
          if (conn.shared_hosting && conn.shared_hosting.length) links.push('<span style="color:#003366;"><i class="fa-solid fa-building"></i> Hosting: ' + conn.shared_hosting.join(', ') + '</span>');
          if (conn.shared_ns && conn.shared_ns.length) links.push('<span style="color:#003366;"><i class="fa-solid fa-server"></i> NS: ' + conn.shared_ns.join(', ') + '</span>');
          if (conn.shared_registrar && conn.shared_registrar.length) links.push('<span style="color:#003366;"><i class="fa-solid fa-id-card"></i> Registrar: ' + conn.shared_registrar.join(', ') + '</span>');
          return '<div style="margin-bottom:10px;padding:10px;border-radius:6px;background:var(--bg-page);border-left:3px solid #003366;cursor:pointer;" onclick="openCaseDetail(\\'' + conn.case_id + '\\')">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;">' +
            '<strong>' + conn.target + '</strong>' +
            '<span class="badge badge-' + r + '">' + Math.round(conn.confidence * 100) + '%</span>' +
            '</div>' +
            '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' + conn.case_id + '</div>' +
            '<div style="font-size:11px;margin-top:4px;">' + links.join(' | ') + '</div>' +
            '</div>';
        }).join('');
      } catch(e) {
        const el = document.getElementById('intelXRef');
        if (el) el.innerHTML = '<div class="empty-state"><p>Failed to load cross-reference data.</p></div>';
      }
    }

    function statCard(label, value, icon, color) {
      return '<div class="stat-card"><div class="stat-card-top" style="background:' + color + ';"></div>' +
        '<div class="stat-card-body"><div class="stat-icon" style="color:' + color + ';"><i class="fa-solid ' + icon + '"></i></div>' +
        '<div class="stat-value">' + value + '</div><div class="stat-label">' + label + '</div></div></div>';
    }
"""

# Find the last </script> tag and insert before it
last_script = html.rfind('</script>')
if 'loadHunterActivity' not in html[:last_script]:
    # Find a good insertion point — before the last </script>
    # Actually, find the switchView function and insert after the officers check
    insert_point = html.rfind('</script>')
    html = html[:insert_point] + js_insert + '\n' + html[insert_point:]
    print("Hunter JS functions added")
else:
    print("Hunter JS already present")

with open('/gfin/police_dashboard_mobile.html', 'w') as f:
    f.write(html)

print("Dashboard updated")

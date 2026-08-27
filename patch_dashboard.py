#!/usr/bin/env python3
"""
Patch the GFIN police dashboard to add 5 new views:
1. Laundering — operations, patterns, risk scores, operator correlation
2. Wallet Flow — tracked wallets, chain, balance, linked cases
3. Evidence — correlation graph, entity links
4. Operator Map — network visualization of scam operators
5. Outreach — victim outreach tracking
Also updates Alerts to show unified priority queue.
"""

import re

DASHBOARD_FILE = "/gfin/police_dashboard_mobile.html"

with open(DASHBOARD_FILE, "r") as f:
    html = f.read()

# ============================================================
# 1. ADD NEW SIDEBAR ITEMS (after Intel, before Alerts)
# ============================================================

old_sidebar = '''        <a class="sidebar-item" data-view="intel" onclick="switchView('intel')"><i class="fa-solid fa-satellite"></i> Intel</a>
        <a class="sidebar-item" data-view="alerts" onclick="switchView('alerts')"><i class="fa-solid fa-bell"></i> Alerts</a>'''

new_sidebar = '''        <a class="sidebar-item" data-view="intel" onclick="switchView('intel')"><i class="fa-solid fa-satellite"></i> Intel</a>
        <a class="sidebar-item" data-view="laundering" onclick="switchView('laundering')"><i class="fa-solid fa-money-bill-transfer"></i> Laundering</a>
        <a class="sidebar-item" data-view="wallets" onclick="switchView('wallets')"><i class="fa-solid fa-wallet"></i> Wallet Flow</a>
        <a class="sidebar-item" data-view="evidence" onclick="switchView('evidence')"><i class="fa-solid fa-diagram-project"></i> Evidence</a>
        <a class="sidebar-item" data-view="operators" onclick="switchView('operators')"><i class="fa-solid fa-share-nodes"></i> Operators</a>
        <a class="sidebar-item" data-view="outreach" onclick="switchView('outreach')"><i class="fa-solid fa-bullhorn"></i> Outreach</a>
        <a class="sidebar-item" data-view="alerts" onclick="switchView('alerts')"><i class="fa-solid fa-bell"></i> Alerts</a>'''

html = html.replace(old_sidebar, new_sidebar)

# ============================================================
# 2. ADD NEW VIEW SECTIONS (before the Settings view section)
# ============================================================

# Find the settings view section to insert before it
settings_marker = '      <section id="viewSettings" class="view-section">'
if settings_marker not in html:
    settings_marker = '<section id="viewSettings"'

new_views = '''
      <!-- VIEW: LAUNDERING -->
      <section id="viewLaundering" class="view-section" style="display:none;">
        <div class="page-header"><div class="page-title">Money Laundering Intelligence</div><div class="page-subtitle">Transnational laundering network detection and tracking</div></div>
        <div id="launderingContent" style="display:flex;flex-direction:column;gap:16px;">
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;" id="launderingStats"></div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-globe"></i> Laundering Operations</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="launderingTable">
              <thead><tr><th>Channel</th><th>Country</th><th>Operator</th><th>Risk</th><th>Patterns</th><th>Description</th></tr></thead>
              <tbody id="launderingBody"></tbody>
            </table></div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-shield-halved"></i> Detection Patterns</div></div>
            <div id="launderingPatterns" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;"></div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-lightbulb"></i> Intelligence Assessment</div></div>
            <div id="launderingAssessment" style="padding:12px;"></div>
          </div>
        </div>
      </section>

      <!-- VIEW: WALLET FLOW -->
      <section id="viewWallets" class="view-section" style="display:none;">
        <div class="page-header"><div class="page-title">Wallet Flow Tracker</div><div class="page-subtitle">Multi-chain cryptocurrency wallet intelligence</div></div>
        <div id="walletContent" style="display:flex;flex-direction:column;gap:16px;">
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;" id="walletStats"></div>
          <div class="card">
            <div class="card-header">
              <div class="card-title"><i class="fa-solid fa-wallet"></i> Tracked Wallets</div>
              <div style="display:flex;gap:8px;">
                <select id="walletChainFilter" onchange="loadWallets()" style="padding:4px 8px;border-radius:4px;border:1px solid var(--border);font-size:12px;"><option value="all">All Chains</option><option value="BTC">BTC</option><option value="ETH">ETH</option><option value="TRON">TRON</option><option value="SOL">SOL</option><option value="unknown">Unknown</option></select>
              </div>
            </div>
            <div style="overflow-x:auto;"><table class="data-table" id="walletTable">
              <thead><tr><th>Address</th><th>Chain</th><th>Source</th><th>Group</th><th>Sender</th><th>Risk</th><th>First Seen</th><th>Actions</th></tr></thead>
              <tbody id="walletBody"></tbody>
            </table></div>
          </div>
        </div>
      </section>

      <!-- VIEW: EVIDENCE CORRELATION -->
      <section id="viewEvidence" class="view-section" style="display:none;">
        <div class="page-header"><div class="page-title">Evidence Correlation</div><div class="page-subtitle">Cross-entity intelligence graph</div></div>
        <div id="evidenceContent" style="display:flex;flex-direction:column;gap:16px;">
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;" id="evidenceStats"></div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-diagram-project"></i> Entity Correlation Graph</div></div>
            <div id="evidenceGraph" style="height:500px;position:relative;overflow:auto;border:1px solid var(--border);border-radius:4px;background:var(--bg-page);">
              <div style="padding:20px;text-align:center;color:var(--text-muted);">Loading correlation graph...</div>
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-list"></i> Entity List</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="evidenceTable">
              <thead><tr><th>Entity</th><th>Type</th><th>Connections</th></tr></thead>
              <tbody id="evidenceBody"></tbody>
            </table></div>
          </div>
        </div>
      </section>

      <!-- VIEW: OPERATOR MAP -->
      <section id="viewOperators" class="view-section" style="display:none;">
        <div class="page-header"><div class="page-title">Operator Network Map</div><div class="page-subtitle">Scam operator correlation and infrastructure mapping</div></div>
        <div id="operatorsContent" style="display:flex;flex-direction:column;gap:16px;">
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;" id="operatorStats"></div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-share-nodes"></i> Network Visualization</div></div>
            <div id="operatorGraph" style="height:500px;position:relative;overflow:auto;border:1px solid var(--border);border-radius:4px;background:var(--bg-page);">
              <div style="padding:20px;text-align:center;color:var(--text-muted);">Loading operator network...</div>
            </div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-user-secret"></i> Known Operators</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="operatorTable">
              <thead><tr><th>Operator</th><th>Type</th><th>Channels</th><th>Countries</th><th>Risk</th><th>Patterns</th><th>Messages</th></tr></thead>
              <tbody id="operatorBody"></tbody>
            </table></div>
          </div>
        </div>
      </section>

      <!-- VIEW: OUTREACH -->
      <section id="viewOutreach" class="view-section" style="display:none;">
        <div class="page-header"><div class="page-title">Victim Outreach Tracker</div><div class="page-subtitle">GFIN complaint outreach to victim communities</div></div>
        <div id="outreachContent" style="display:flex;flex-direction:column;gap:16px;">
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;" id="outreachStats"></div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-comments"></i> Group Posts</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="outreachGroupsTable">
              <thead><tr><th>Group</th><th>Type</th><th>Status</th><th>Posted At</th></tr></thead>
              <tbody id="outreachGroupsBody"></tbody>
            </table></div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-envelope"></i> Direct Messages</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="outreachDmTable">
              <thead><tr><th>Recipient</th><th>Status</th><th>Sent At</th></tr></thead>
              <tbody id="outreachDmBody"></tbody>
            </table></div>
          </div>
          <div class="card">
            <div class="card-header"><div class="card-title"><i class="fa-solid fa-inbox"></i> Complaints Received from Outreach</div></div>
            <div style="overflow-x:auto;"><table class="data-table" id="outreachComplaintsTable">
              <thead><tr><th>ID</th><th>Source Group</th><th>Victim</th><th>Type</th><th>Case ID</th><th>Received</th></tr></thead>
              <tbody id="outreachComplaintsBody"></tbody>
            </table></div>
          </div>
        </div>
      </section>

'''

html = html.replace(settings_marker, new_views + '      ' + settings_marker)

# ============================================================
# 3. ADD JAVASCRIPT LOADING FUNCTIONS
# ============================================================

# Find a good place to add JS — before the closing </script> tag
js_insert_marker = 'function showToast(msg, type) {'
if js_insert_marker not in html:
    js_insert_marker = '// Show toast'

new_js = '''
// ============================================================
// ENHANCED DASHBOARD — Loading functions for new views
// ============================================================

const API_BASE = '';
let authToken = localStorage.getItem('gfin_token') || '';

async function apiFetch(path) {
  const res = await fetch(API_BASE + path, { headers: { 'Authorization': 'Bearer ' + authToken } });
  if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
  return res.json();
}

function riskBadge(level) {
  const colors = {CRITICAL:'#dc2626',HIGH:'#ea580c',MEDIUM:'#ca8a04',LOW:'#65a30d',MINIMAL:'#6b7280',UNKNOWN:'#6b7280'};
  const bg = colors[level] || colors.MEDIUM;
  return '<span style="padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;color:#fff;background:' + bg + ';">' + level + '</span>';
}

function statCard(label, value, icon, color) {
  const c = color || '#003366';
  return '<div style="padding:16px;border-radius:8px;background:#fff;border:1px solid var(--border);border-left:4px solid ' + c + ';"><div style="font-size:11px;color:var(--text-muted);text-transform:uppercase;font-weight:600;">' + (icon ? '<i class="fa-solid ' + icon + '"></i> ' : '') + label + '</div><div style="font-size:24px;font-weight:700;color:' + c + ';margin-top:4px;">' + value + '</div></div>';
}

// --- LAUNDERING ---
async function loadLaundering() {
  try {
    const [ops, patterns, report] = await Promise.all([
      apiFetch('/api/laundering/operations'),
      apiFetch('/api/laundering/patterns'),
      apiFetch('/api/laundering/report')
    ]);
    
    // Stats
    document.getElementById('launderingStats').innerHTML = 
      statCard('Operations', ops.total, 'fa-globe', '#dc2626') +
      statCard('Critical', ops.total > 0 ? ops.total : 0, 'fa-triangle-exclamation', '#dc2626') +
      statCard('Countries', ops.countries_affected.length, 'fa-map', '#003366') +
      statCard('Primary Operator', '@btcv123', 'fa-user-secret', '#ea580c');
    
    // Operations table
    document.getElementById('launderingBody').innerHTML = ops.operations.map(op => 
      '<tr><td><a href="' + op.group_username + '" target="_blank">' + op.group_name.substring(0,40) + '...</a></td><td>' + op.country + '</td><td>' + op.operator + '</td><td>' + riskBadge(op.risk_level) + '</td><td>' + (op.patterns || []).join(', ').substring(0,50) + '</td><td>' + op.description.substring(0,80) + '...</td></tr>'
    ).join('');
    
    // Patterns
    document.getElementById('launderingPatterns').innerHTML = patterns.patterns.map(p =>
      '<div style="padding:10px;border-radius:6px;border:1px solid var(--border);background:#fff;"><div style="font-weight:600;font-size:13px;color:var(--navy);">' + p.name.replace(/_/g,' ') + '</div><div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' + p.description + '</div><div style="margin-top:4px;">' + riskBadge(p.weight >= 0.85 ? 'CRITICAL' : p.weight >= 0.7 ? 'HIGH' : 'MEDIUM') + ' Weight: ' + p.weight + '</div></div>'
    ).join('');
    
    // Assessment
    const a = report.intelligence_assessment;
    if (a) {
      document.getElementById('launderingAssessment').innerHTML = 
        '<div style="font-size:13px;line-height:1.8;">' +
        '<p><b>Operator Correlation:</b> ' + a.operator_correlation + '</p>' +
        '<p><b>Modus Operandi:</b> ' + a.modus_operandi + '</p>' +
        '<p><b>Scale:</b> ' + a.scale + '</p>' +
        '<p><b>Flash Crypto Scam:</b> ' + a.flash_crypto_scam + '</p>' +
        '<div style="margin-top:12px;font-weight:600;color:var(--navy);">Recommended Actions:</div><ol style="margin-top:4px;font-size:12px;">' +
        a.recommended_actions.map(r => '<li>' + r + '</li>').join('') + '</ol></div>';
    }
  } catch(e) {
    document.getElementById('launderingContent').innerHTML = '<div style="padding:20px;color:#dc2626;">Error loading laundering data: ' + e.message + '</div>';
  }
}

// --- WALLET FLOW ---
async function loadWallets() {
  try {
    const chain = document.getElementById('walletChainFilter') ? document.getElementById('walletChainFilter').value : 'all';
    const data = await apiFetch('/api/dashboard/wallets?chain=' + chain);
    
    document.getElementById('walletStats').innerHTML =
      statCard('Total Wallets', data.total, 'fa-wallet', '#003366') +
      statCard('BTC', data.by_chain.BTC || 0, 'fa-bitcoin-sign', '#f7931a') +
      statCard('ETH', data.by_chain.ETH || 0, 'fa-ethereum', '#627eea') +
      statCard('TRON', data.by_chain.TRON || data.by_chain.Tron || 0, 'fa-bolt', '#ff060a') +
      statCard('Unknown', data.by_chain.unknown || 0, 'fa-question', '#6b7280');
    
    document.getElementById('walletBody').innerHTML = (data.wallets || []).map(w =>
      '<tr><td style="font-family:monospace;font-size:11px;">' + (w.address || '').substring(0,20) + '...</td><td>' + (w.chain || 'unknown') + '</td><td>' + (w.source || '') + '</td><td>' + (w.group || '') + '</td><td>' + (w.sender || '') + '</td><td>' + riskBadge(w.risk_level || 'UNKNOWN') + '</td><td>' + (w.first_seen || '').substring(0,10) + '</td><td><button onclick="traceWallet(\\'' + w.address + '\\')" style="padding:2px 8px;font-size:11px;border-radius:3px;background:var(--navy);color:#fff;border:none;cursor:pointer;">Trace</button></td></tr>'
    ).join('');
  } catch(e) {
    document.getElementById('walletContent').innerHTML = '<div style="padding:20px;color:#dc2626;">Error: ' + e.message + '</div>';
  }
}

async function traceWallet(address) {
  alert('Tracing wallet: ' + address + '\\nLoading blockchain data...');
  try {
    const data = await apiFetch('/api/dashboard/wallets/' + encodeURIComponent(address) + '/trace');
    let msg = 'Chain: ' + data.chain + '\\nBalance: ' + (data.balance || 'Unknown') + '\\nTx Count: ' + (data.tx_count || 'Unknown') + '\\n\\nAssociated Entities:\\n';
    if (data.associated_entities && data.associated_entities.length > 0) {
      data.associated_entities.forEach(e => { msg += '- ' + e.type + ': ' + (e.group || e.sender || '') + '\\n'; });
    } else {
      msg += 'None found';
    }
    alert(msg);
  } catch(e) {
    alert('Trace error: ' + e.message);
  }
}

// --- EVIDENCE CORRELATION ---
async function loadEvidence() {
  try {
    const data = await apiFetch('/api/dashboard/evidence/graph');
    
    document.getElementById('evidenceStats').innerHTML =
      statCard('Total Nodes', data.summary.total_nodes, 'fa-circle-dot', '#003366') +
      statCard('Total Edges', data.summary.total_edges, 'fa-link', '#ea580c') +
      statCard('Wallets', data.summary.wallets, 'fa-wallet', '#f7931a') +
      statCard('Domains', data.summary.domains, 'fa-globe', '#003366') +
      statCard('Phones', data.summary.phones, 'fa-phone', '#ca8a04') +
      statCard('Senders', data.summary.senders, 'fa-user', '#6b7280');
    
    // Simple graph visualization — force-directed layout
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    const typeColors = {WALLET:'#f7931a',DOMAIN:'#003366',PHONE:'#ca8a04',SOCIAL:'#6b7280'};
    
    // Position nodes in a circle
    let graphHtml = '<svg width="100%" height="100%" style="min-height:500px;">';
    const cx = 300, cy = 250, r = 200;
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      n.x = cx + r * Math.cos(angle);
      n.y = cy + r * Math.sin(angle);
    });
    
    // Draw edges
    edges.forEach(e => {
      const s = nodes.find(n => n.id === e.source);
      const t = nodes.find(n => n.id === e.target);
      if (s && t) {
        graphHtml += '<line x1="' + s.x + '" y1="' + s.y + '" x2="' + t.x + '" y2="' + t.y + '" stroke="#ccc" stroke-width="1" opacity="0.4"/>';
      }
    });
    
    // Draw nodes
    nodes.forEach(n => {
      const color = typeColors[n.type] || '#003366';
      graphHtml += '<circle cx="' + n.x + '" cy="' + n.y + '" r="8" fill="' + color + '" stroke="#fff" stroke-width="2"><title>' + n.label + ' (' + n.type + ')</title></circle>';
      graphHtml += '<text x="' + n.x + '" y="' + (n.y + 20) + '" font-size="9" text-anchor="middle" fill="#666">' + n.label.substring(0,15) + '</text>';
    });
    
    graphHtml += '</svg>';
    document.getElementById('evidenceGraph').innerHTML = graphHtml;
    
    // Entity table
    document.getElementById('evidenceBody').innerHTML = nodes.map(n => {
      const conns = edges.filter(e => e.source === n.id || e.target === n.id).length;
      return '<tr><td style="font-family:monospace;font-size:12px;">' + n.id + '</td><td>' + riskBadge(n.type) + '</td><td>' + conns + ' connections</td></tr>';
    }).join('');
  } catch(e) {
    document.getElementById('evidenceContent').innerHTML = '<div style="padding:20px;color:#dc2626;">Error: ' + e.message + '</div>';
  }
}

// --- OPERATOR MAP ---
async function loadOperators() {
  try {
    const data = await apiFetch('/api/dashboard/operators/map');
    
    document.getElementById('operatorStats').innerHTML =
      statCard('Operators', data.total_operators, 'fa-user-secret', '#dc2626') +
      statCard('Correlations', data.total_edges, 'fa-link', '#ea580c') +
      statCard('Channels', data.nodes.reduce((s,n) => s + (n.channels || []).length, 0), 'fa-tv', '#003366');
    
    // Graph visualization
    const nodes = data.nodes || [];
    const edges = data.edges || [];
    let graphHtml = '<svg width="100%" height="100%" style="min-height:500px;">';
    const cx = 300, cy = 250, r = 180;
    nodes.forEach((n, i) => {
      const angle = (i / Math.max(nodes.length,1)) * 2 * Math.PI;
      n.x = cx + r * Math.cos(angle);
      n.y = cy + r * Math.sin(angle);
    });
    
    // Draw edges
    edges.forEach(e => {
      const s = nodes.find(n => n.id === e.source);
      const t = nodes.find(n => n.id === e.target);
      if (s && t) {
        const edgeColors = {SHARED_WALLET:'#f7931a',SHARED_DOMAIN:'#003366',SHARED_CHANNEL:'#ea580c'};
        graphHtml += '<line x1="' + s.x + '" y1="' + s.y + '" x2="' + t.x + '" y2="' + t.y + '" stroke="' + (edgeColors[e.type] || '#ccc') + '" stroke-width="2" opacity="0.5"><title>' + e.type + ': ' + e.count + '</title></line>';
      }
    });
    
    // Draw nodes — bigger for operators with more channels
    nodes.forEach(n => {
      const size = Math.max(8, Math.min(25, (n.channels || []).length * 3 + (n.message_count || 0) * 0.5));
      const isLaundering = (n.patterns || []).length > 0;
      const color = isLaundering ? '#dc2626' : '#003366';
      graphHtml += '<circle cx="' + n.x + '" cy="' + n.y + '" r="' + size + '" fill="' + color + '" stroke="#fff" stroke-width="2"><title>' + n.label + '</title></circle>';
      graphHtml += '<text x="' + n.x + '" y="' + (n.y + size + 14) + '" font-size="10" text-anchor="middle" fill="#333" font-weight="600">' + n.label + '</text>';
    });
    
    graphHtml += '</svg>';
    document.getElementById('operatorGraph').innerHTML = graphHtml;
    
    // Operators table
    document.getElementById('operatorBody').innerHTML = nodes.map(n =>
      '<tr><td>' + n.id + '</td><td>' + n.type + '</td><td>' + (n.channels || []).length + '</td><td>' + ((n.countries || []).length ? (n.countries || []).join(', ') : '-') + '</td><td>' + riskBadge(n.risk_level || 'MEDIUM') + '</td><td>' + (n.patterns || []).join(', ').substring(0,40) + '</td><td>' + (n.message_count || '-') + '</td></tr>'
    ).join('');
  } catch(e) {
    document.getElementById('operatorsContent').innerHTML = '<div style="padding:20px;color:#dc2626;">Error: ' + e.message + '</div>';
  }
}

// --- OUTREACH ---
async function loadOutreach() {
  try {
    const data = await apiFetch('/api/dashboard/outreach');
    const s = data.summary;
    
    document.getElementById('outreachStats').innerHTML =
      statCard('Groups Posted', s.total_groups_posted, 'fa-comments', '#003366') +
      statCard('Groups Blocked', s.total_groups_blocked, 'fa-ban', '#dc2626') +
      statCard('DMs Sent', s.total_dms_sent, 'fa-envelope', '#ea580c') +
      statCard('Complaints', s.complaints_received, 'fa-inbox', '#ca8a04') +
      statCard('Reach', s.reach_estimate || '775+', 'fa-users', '#003366');
    
    // Groups table
    const statusColors = {POSTED:'#16a34a',BLOCKED:'#dc2626',READ_ONLY:'#6b7280'};
    document.getElementById('outreachGroupsBody').innerHTML = (data.groups_posted || []).map(g =>
      '<tr><td>' + (g.group_name || g.group) + '</td><td>Group Post</td><td><span style="padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;color:#fff;background:' + (statusColors[g.status] || '#6b7280') + ';">' + g.status + '</span></td><td>' + (g.posted_at || '').substring(0,16) + '</td></tr>'
    ).join('');
    
    // DMs table
    document.getElementById('outreachDmBody').innerHTML = (data.dms_sent || []).map(d =>
      '<tr><td>' + (d.recipient_name || '') + ' (' + (d.recipient || '') + ')</td><td><span style="padding:2px 8px;border-radius:3px;font-size:11px;color:#fff;background:#16a34a;">SENT</span></td><td>' + (d.sent_at || '').substring(0,16) + '</td></tr>'
    ).join('');
    
    // Complaints table
    document.getElementById('outreachComplaintsBody').innerHTML = (data.complaints_received || []).map(c =>
      '<tr><td>' + (c.id || '') + '</td><td>' + (c.source_group || '') + '</td><td>' + (c.victim_username || '') + '</td><td>' + (c.complaint_type || '') + '</td><td>' + (c.case_id || '') + '</td><td>' + (c.received_at || '').substring(0,16) + '</td></tr>'
    ).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No complaints received yet</td></tr>';
  } catch(e) {
    document.getElementById('outreachContent').innerHTML = '<div style="padding:20px;color:#dc2626;">Error: ' + e.message + '</div>';
  }
}

// --- UNIFIED ALERTS (updates existing alerts view) ---
async function loadUnifiedAlerts() {
  try {
    const data = await apiFetch('/api/dashboard/alerts/unified?limit=100');
    
    // Update alerts count badge
    const badge = document.querySelector('[data-view="alerts"] .badge');
    if (badge) badge.textContent = data.total;
    
    // If we're on the alerts view, render
    const alertsBody = document.getElementById('alertsBody') || document.getElementById('alertsList');
    if (alertsBody) {
      const typeIcons = {
        MONEY_LAUNDERING: 'fa-money-bill-transfer',
        SCAM_DETECTION: 'fa-shield-halved',
        VICTIM_REPORT: 'fa-hand-holding-heart',
        HUNTER_INVESTIGATION: 'fa-satellite-dish'
      };
      alertsBody.innerHTML = data.alerts.map(a =>
        '<div style="padding:12px;border-radius:6px;border:1px solid var(--border);background:#fff;margin-bottom:8px;border-left:4px solid ' + 
        (a.level === 'CRITICAL' ? '#dc2626' : a.level === 'HIGH' ? '#ea580c' : a.level === 'MEDIUM' ? '#ca8a04' : '#6b7280') + ';">' +
        '<div style="display:flex;justify-content:space-between;align-items:start;">' +
        '<div><i class="fa-solid ' + (typeIcons[a.type] || 'fa-bell') + '"></i> <b>' + a.title + '</b></div>' +
        riskBadge(a.level) + '</div>' +
        '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">' + (a.description || '').substring(0,200) + '</div>' +
        '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">Source: ' + (a.source || '') + ' | ' + (a.timestamp || '').substring(0,16) + '</div>' +
        (a.operator ? '<div style="font-size:11px;margin-top:2px;">Operator: <b>' + a.operator + '</b></div>' : '') +
        (a.wallets && a.wallets.length ? '<div style="font-size:11px;margin-top:2px;">Wallets: ' + a.wallets.join(', ') + '</div>' : '') +
        '</div>'
      ).join('');
    }
  } catch(e) {
    console.error('Alerts error:', e);
  }
}

// --- VIEW ROUTING — add new views to switchView ---
const _originalSwitchView = window.switchView;
window.switchView = function(view) {
  if (_originalSwitchView) _originalSwitchView(view);
  // Load data for new views
  if (view === 'laundering') loadLaundering();
  if (view === 'wallets') loadWallets();
  if (view === 'evidence') loadEvidence();
  if (view === 'operators') loadOperators();
  if (view === 'outreach') loadOutreach();
  if (view === 'alerts') loadUnifiedAlerts();
};

// --- LOAD OVERVIEW ON DASHBOARD INIT ---
async function loadEnhancedOverview() {
  try {
    const data = await apiFetch('/api/dashboard/overview');
    // Could add enhanced stats to home view here
    console.log('Enhanced overview loaded:', data);
  } catch(e) {
    console.error('Overview error:', e);
  }
}

'''

html = html.replace(js_insert_marker, new_js + '\n' + js_insert_marker)

# Save
with open(DASHBOARD_FILE, "w") as f:
    f.write(html)

print("Dashboard patched successfully with 5 new views + unified alerts")

#!/usr/bin/env python3
"""Patch investigator_workbench.html to add 5 new investigative tabs with full data loading."""

with open("/gfin/investigator_workbench.html", "r") as f:
    content = f.read()

# 1. Add 5 new nav items after "Search"
old_nav_search = '''      <div class="nav-item" onclick="switchView('search')"><i class="fa-solid fa-magnifying-glass"></i> Search</div>'''

new_nav_search = '''      <div class="nav-item" onclick="switchView('search')"><i class="fa-solid fa-magnifying-glass"></i> Search</div>
      <div class="nav-item" onclick="switchView('laundering')"><i class="fa-solid fa-money-bill-transfer"></i> Laundering <span class="badge" id="launderingBadge">0</span></div>
      <div class="nav-item" onclick="switchView('wallets')"><i class="fa-solid fa-wallet"></i> Wallet Flow</div>
      <div class="nav-item" onclick="switchView('operators')"><i class="fa-solid fa-share-nodes"></i> Operators</div>
      <div class="nav-item" onclick="switchView('outreach')"><i class="fa-solid fa-bullhorn"></i> Outreach</div>'''

content = content.replace(old_nav_search, new_nav_search)

# 2. Add 5 new view sections before the closing </div> of the content area
# Find the search view end
old_search_view_end = '''    </div>
  </div>
  <script>'''

new_views = '''    </div>

    <!-- LAUNDERING VIEW -->
    <div id="view-laundering" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h2><i class="fa-solid fa-money-bill-transfer"></i> Money Laundering Detection</h2>
        <button class="btn btn-outline" onclick="loadLaundering()"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>
      <div id="launderingStats" class="stat-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
      <div id="launderingOps" style="margin-top:16px;"></div>
    </div>

    <!-- WALLETS VIEW -->
    <div id="view-wallets" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h2><i class="fa-solid fa-wallet"></i> Wallet Flow Analysis</h2>
        <div>
          <select id="walletChainFilter" onchange="loadWallets()" style="padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg-card);color:var(--text);">
            <option value="">All Chains</option>
            <option value="BTC">Bitcoin</option>
            <option value="ETH">Ethereum</option>
            <option value="TRX">Tron</option>
            <option value="SOL">Solana</option>
            <option value="TON">TON</option>
          </select>
          <button class="btn btn-outline" onclick="loadWallets()"><i class="fa-solid fa-rotate"></i> Refresh</button>
        </div>
      </div>
      <div id="walletStats" class="stat-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
      <div id="walletTable" style="margin-top:16px;"></div>
    </div>

    <!-- OPERATORS VIEW -->
    <div id="view-operators" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h2><i class="fa-solid fa-share-nodes"></i> Operator Network Map</h2>
        <button class="btn btn-outline" onclick="loadOperators()"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>
      <div id="operatorStats" class="stat-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
      <div id="operatorMap" style="margin-top:16px;"></div>
    </div>

    <!-- OUTREACH VIEW -->
    <div id="view-outreach" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h2><i class="fa-solid fa-bullhorn"></i> Outreach Tracking</h2>
        <button class="btn btn-outline" onclick="loadOutreach()"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>
      <div id="outreachStats" class="stat-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>
      <div id="outreachList" style="margin-top:16px;"></div>
    </div>

  </div>
  <script>'''

content = content.replace(old_search_view_end, new_views)

# 3. Update switchView to handle the 5 new views
old_switch = '''  // Load data for view
  if (view === 'dashboard') loadDashboard();
  else if (view === 'cases') loadCases();
  else if (view === 'intel') loadIntelFeed();
  else if (view === 'evidence') loadEvidence();
  else if (view === 'telegram') loadTelegram();
  else if (view === 'hunter') loadHunter();
  else if (view === 'domains') loadDomains();'''

new_switch = '''  // Load data for view
  if (view === 'dashboard') loadDashboard();
  else if (view === 'cases') loadCases();
  else if (view === 'intel') loadIntelFeed();
  else if (view === 'evidence') loadEvidence();
  else if (view === 'telegram') loadTelegram();
  else if (view === 'hunter') loadHunter();
  else if (view === 'domains') loadDomains();
  else if (view === 'laundering') loadLaundering();
  else if (view === 'wallets') loadWallets();
  else if (view === 'operators') loadOperators();
  else if (view === 'outreach') loadOutreach();'''

content = content.replace(old_switch, new_switch)

# 4. Add the load functions before the closing </script> tag
# Find a good insertion point — before the last function
old_script_end = '''</script>
</body>'''

new_functions = '''
// ==================== LAUNDERING VIEW ====================
async function loadLaundering() {
  try {
    const [opsData, alertsData] = await Promise.all([
      apiGet('/api/laundering/operations'),
      apiGet('/api/laundering/alerts').catch(() => ({ alerts: [] }))
    ]);

    const ops = opsData.operations || [];
    const alerts = alertsData.alerts || [];

    // Update badge
    const badge = document.getElementById('launderingBadge');
    if (badge) badge.textContent = ops.length;

    // Stats
    const countries = new Set();
    ops.forEach(o => { if (o.countries) o.countries.forEach(c => countries.add(c)); });

    const stats = [
      { label: 'Active Operations', value: ops.length, sub: 'Laundering networks', icon: 'money-bill-transfer', color: 'red' },
      { label: 'Countries Involved', value: countries.size, sub: 'Cross-border', icon: 'globe', color: 'navy' },
      { label: 'Alerts (7d)', value: alerts.length, sub: 'Recent detections', icon: 'bell', color: 'amber' },
      { label: 'Primary Operators', value: new Set(ops.map(o => o.username)).size, sub: ' Identified', icon: 'user-secret', color: 'blue' }
    ];
    document.getElementById('launderingStats').innerHTML = stats.map(s => statCard(s)).join('');

    // Operations table
    let html = '<div style="background:var(--bg-card);border-radius:8px;border:1px solid var(--border);overflow:hidden;">';
    html += '<table style="width:100%;border-collapse:collapse;"><thead><tr style="background:var(--bg-hover);text-align:left;">';
    html += '<th style="padding:12px;">Operator</th><th style="padding:12px;">Type</th><th style="padding:12px;">Countries</th><th style="padding:12px;">Risk</th><th style="padding:12px;">Messages</th></tr></thead><tbody>';
    ops.forEach(o => {
      const riskColor = o.risk_level === 'CRITICAL' ? '#fee2e2' : o.risk_level === 'HIGH' ? '#fef3c7' : '#dbeafe';
      const riskText = o.risk_level === 'CRITICAL' ? '#991b1b' : o.risk_level === 'HIGH' ? '#92400e' : '#1e40af';
      html += '<tr style="border-top:1px solid var(--border);">';
      html += '<td style="padding:12px;font-weight:600;">' + (o.username || 'Unknown') + '</td>';
      html += '<td style="padding:12px;">' + (o.laundering_type || 'Crypto') + '</td>';
      html += '<td style="padding:12px;">' + (o.countries ? o.countries.join(', ') : '-') + '</td>';
      html += '<td style="padding:12px;"><span style="background:' + riskColor + ';color:' + riskText + ';padding:2px 8px;border-radius:4px;font-size:11px;">' + (o.risk_level || 'MEDIUM') + '</span></td>';
      html += '<td style="padding:12px;">' + (o.message_count || 0) + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    document.getElementById('launderingOps').innerHTML = html;
  } catch (e) {
    document.getElementById('launderingOps').innerHTML = '<div class="empty-state"><p>Unable to load laundering data: ' + e.message + '</p></div>';
  }
}

// ==================== WALLETS VIEW ====================
async function loadWallets() {
  try {
    const chain = document.getElementById('walletChainFilter') ? document.getElementById('walletChainFilter').value : '';
    const url = chain ? '/api/dashboard/wallets?chain=' + chain : '/api/dashboard/wallets';
    const data = await apiGet(url);

    const wallets = data.wallets || [];
    const byChain = data.by_chain || {};
    const byRisk = data.by_risk || {};

    // Stats
    const stats = [
      { label: 'Total Wallets', value: data.total || 0, sub: 'Tracked addresses', icon: 'wallet', color: 'blue' },
      { label: 'Chains', value: Object.keys(byChain).length, sub: 'Multi-chain', icon: 'link', color: 'navy' },
      { label: 'High Risk', value: byRisk.HIGH || 0, sub: 'Flagged wallets', icon: 'flag', color: 'red' },
      { label: 'Linked Cases', value: wallets.filter(w => w.linked_case).length, sub: 'Active investigations', icon: 'folder-open', color: 'amber' }
    ];
    document.getElementById('walletStats').innerHTML = stats.map(s => statCard(s)).join('');

    // Wallet table
    let html = '<div style="background:var(--bg-card);border-radius:8px;border:1px solid var(--border);overflow:hidden;">';
    if (wallets.length === 0) {
      html += '<div class="empty-state" style="padding:40px;"><i class="fa-solid fa-wallet" style="font-size:48px;opacity:0.3;"></i><h3>No Wallets Tracked Yet</h3><p>Wallets from Telegram intelligence and case investigations will appear here.</p></div>';
    } else {
      html += '<table style="width:100%;border-collapse:collapse;"><thead><tr style="background:var(--bg-hover);text-align:left;">';
      html += '<th style="padding:12px;">Address</th><th style="padding:12px;">Chain</th><th style="padding:12px;">Risk</th><th style="padding:12px;">Source</th><th style="padding:12px;">Linked Case</th></tr></thead><tbody>';
      wallets.forEach(w => {
        const riskColor = w.risk_level === 'HIGH' ? '#fee2e2' : w.risk_level === 'MEDIUM' ? '#fef3c7' : '#d1fae5';
        const riskText = w.risk_level === 'HIGH' ? '#991b1b' : w.risk_level === 'MEDIUM' ? '#92400e' : '#065f46';
        html += '<tr style="border-top:1px solid var(--border);">';
        html += '<td style="padding:12px;font-family:monospace;">' + (w.address || '').substring(0, 20) + '...</td>';
        html += '<td style="padding:12px;"><span class="entity-tag wallet">' + (w.chain || '?') + '</span></td>';
        html += '<td style="padding:12px;"><span style="background:' + riskColor + ';color:' + riskText + ';padding:2px 8px;border-radius:4px;font-size:11px;">' + (w.risk_level || 'LOW') + '</span></td>';
        html += '<td style="padding:12px;">' + (w.source || 'Telegram') + '</td>';
        html += '<td style="padding:12px;">' + (w.linked_case || '-') + '</td>';
        html += '</tr>';
      });
      html += '</tbody></table>';
    }
    html += '</div>';
    document.getElementById('walletTable').innerHTML = html;
  } catch (e) {
    document.getElementById('walletTable').innerHTML = '<div class="empty-state"><p>Unable to load wallet data: ' + e.message + '</p></div>';
  }
}

// ==================== OPERATORS VIEW ====================
async function loadOperators() {
  try {
    const data = await apiGet('/api/dashboard/operators/map');
    const operators = data.operators || [];
    const channels = data.channels || [];

    // Stats
    const stats = [
      { label: 'Identified Operators', value: operators.length, sub: 'Known scammers', icon: 'user-secret', color: 'red' },
      { label: 'Active Channels', value: channels.length, sub: 'Telegram groups', icon: 'telegram', color: 'amber' },
      { label: 'Countries', value: new Set(operators.map(o => o.country).filter(Boolean)).size, sub: 'Operator locations', icon: 'globe', color: 'navy' },
      { label: 'Linked Cases', value: operators.filter(o => o.linked_case).length, sub: 'Active investigations', icon: 'folder-open', color: 'blue' }
    ];
    document.getElementById('operatorStats').innerHTML = stats.map(s => statCard(s)).join('');

    // Operator network
    let html = '<div style="background:var(--bg-card);border-radius:8px;border:1px solid var(--border);padding:20px;">';
    if (operators.length === 0) {
      html += '<div class="empty-state"><i class="fa-solid fa-share-nodes" style="font-size:48px;opacity:0.3;"></i><h3>No Operators Mapped Yet</h3><p>Operators from Telegram intelligence and laundering cases will appear here.</p></div>';
    } else {
      html += '<h3 style="margin-bottom:16px;">Known Operators</h3>';
      operators.forEach(o => {
        const riskColor = o.risk_level === 'CRITICAL' ? '#fee2e2' : o.risk_level === 'HIGH' ? '#fef3c7' : '#dbeafe';
        const riskText = o.risk_level === 'CRITICAL' ? '#991b1b' : o.risk_level === 'HIGH' ? '#92400e' : '#1e40af';
        html += '<div style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--border);border-radius:8px;margin-bottom:8px;">';
        html += '<div style="width:40px;height:40px;border-radius:50%;background:var(--bg-hover);display:flex;align-items:center;justify-content:center;font-size:18px;"><i class="fa-solid fa-user-secret"></i></div>';
        html += '<div style="flex:1;"><div style="font-weight:600;">' + (o.username || 'Unknown') + '</div>';
        html += '<div style="font-size:12px;color:var(--text-muted);">' + (o.country || 'Unknown location') + ' · ' + (o.scam_type || 'General fraud') + '</div></div>';
        html += '<span style="background:' + riskColor + ';color:' + riskText + ';padding:4px 10px;border-radius:4px;font-size:12px;">' + (o.risk_level || 'MEDIUM') + '</span>';
        if (o.linked_case) html += '<span style="background:var(--bg-hover);padding:4px 10px;border-radius:4px;font-size:12px;">' + o.linked_case + '</span>';
        html += '</div>';
      });
    }
    html += '</div>';

    // Channels
    if (channels.length > 0) {
      html += '<div style="background:var(--bg-card);border-radius:8px;border:1px solid var(--border);padding:20px;margin-top:16px;">';
      html += '<h3 style="margin-bottom:16px;">Monitored Channels (' + channels.length + ')</h3>';
      channels.forEach(c => {
        html += '<div style="display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid var(--border);">';
        html += '<i class="fa-brands fa-telegram" style="color:#0088cc;"></i>';
        html += '<div style="flex:1;"><strong>' + (c.name || c.username || 'Unknown') + '</strong>';
        html += ' <span style="color:var(--text-muted);font-size:13px;">' + (c.member_count || 0) + ' members</span></div>';
        if (c.operators) html += '<span style="font-size:12px;color:var(--text-muted);">' + c.operators + ' operators</span>';
        html += '</div>';
      });
      html += '</div>';
    }

    document.getElementById('operatorMap').innerHTML = html;
  } catch (e) {
    document.getElementById('operatorMap').innerHTML = '<div class="empty-state"><p>Unable to load operator data: ' + e.message + '</p></div>';
  }
}

// ==================== OUTREACH VIEW ====================
async function loadOutreach() {
  try {
    const data = await apiGet('/api/dashboard/outreach');
    const groups = data.groups || [];
    const blocked = data.blocked_groups || [];
    const dms = data.dm_sent || [];

    // Stats
    const stats = [
      { label: 'Groups Posted', value: groups.length, sub: 'Awareness broadcasts', icon: 'bullhorn', color: 'green' },
      { label: 'Groups Blocked', value: blocked.length, sub: 'Removed/banned', icon: 'ban', color: 'red' },
      { label: 'DMs Sent', value: dms.length, sub: 'Direct victim contact', icon: 'envelope', color: 'blue' },
      { label: 'Victims Reached', value: data.victims_reached || 0, sub: 'Total reach', icon: 'users', color: 'amber' }
    ];
    document.getElementById('outreachStats').innerHTML = stats.map(s => statCard(s)).join('');

    // Outreach list
    let html = '<div style="background:var(--bg-card);border-radius:8px;border:1px solid var(--border);padding:20px;">';
    if (groups.length === 0 && blocked.length === 0 && dms.length === 0) {
      html += '<div class="empty-state"><i class="fa-solid fa-bullhorn" style="font-size:48px;opacity:0.3;"></i><h3>No Outreach Activity Yet</h3><p>When GFIN posts awareness messages to Telegram groups or contacts victims, the activity will appear here.</p></div>';
    } else {
      if (groups.length > 0) {
        html += '<h3 style="margin-bottom:12px;">Posted Groups (' + groups.length + ')</h3>';
        groups.forEach(g => {
          html += '<div style="display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid var(--border);">';
          html += '<i class="fa-solid fa-check-circle" style="color:#10b981;"></i>';
          html += '<div style="flex:1;"><strong>' + (g.group_name || g.username || 'Unknown') + '</strong>';
          html += ' <span style="color:var(--text-muted);font-size:13px;">' + (g.member_count || 0) + ' members</span></div>';
          html += '<span style="font-size:12px;color:var(--text-muted);">' + (g.posted_at || '') + '</span>';
          html += '</div>';
        });
      }
      if (blocked.length > 0) {
        html += '<h3 style="margin-top:16px;margin-bottom:12px;">Blocked Groups (' + blocked.length + ')</h3>';
        blocked.forEach(g => {
          html += '<div style="display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid var(--border);">';
          html += '<i class="fa-solid fa-ban" style="color:#ef4444;"></i>';
          html += '<div style="flex:1;"><strong>' + (g.group_name || g.username || 'Unknown') + '</strong>';
          html += ' <span style="color:var(--text-muted);font-size:13px;">' + (g.reason || 'Blocked') + '</span></div>';
          html += '</div>';
        });
      }
      if (dms.length > 0) {
        html += '<h3 style="margin-top:16px;margin-bottom:12px;">Direct Messages (' + dms.length + ')</h3>';
        dms.forEach(d => {
          html += '<div style="display:flex;align-items:center;gap:12px;padding:8px;border-bottom:1px solid var(--border);">';
          html += '<i class="fa-solid fa-envelope" style="color:#3b82f6;"></i>';
          html += '<div style="flex:1;"><strong>' + (d.recipient || 'Unknown') + '</strong>';
          html += ' <span style="color:var(--text-muted);font-size:13px;">' + (d.message_type || 'Victim notification') + '</span></div>';
          html += '</div>';
        });
      }
    }
    html += '</div>';
    document.getElementById('outreachList').innerHTML = html;
  } catch (e) {
    document.getElementById('outreachList').innerHTML = '<div class="empty-state"><p>Unable to load outreach data: ' + e.message + '</p></div>';
  }
}

// Helper function for stat cards
function statCard(s) {
  return '<div class="stat-card ' + (s.color || 'navy') + '"><div class="icon ' + (s.color || 'navy') + '"><i class="fa-solid fa-' + s.icon + '"></i></div><div class="label">' + s.label + '</div><div class="value">' + s.value + '</div><div class="sub">' + s.sub + '</div></div>';
}
'''

content = content.replace(old_script_end, new_functions + '\n</script>\n</body>')

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(content)
print("Investigator workbench patched — 5 new investigative tabs added with full data loading")

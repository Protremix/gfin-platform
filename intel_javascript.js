// ===== TELEGRAM INTELLIGENCE DASHBOARD =====
function intelTab(evt, tabName) {
  document.querySelectorAll('#viewIntel .tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('#viewIntel .tab-content').forEach(c => c.classList.remove('active'));
  evt.currentTarget.classList.add('active');
  const tab = document.getElementById('intelTab' + tabName.charAt(0).toUpperCase() + tabName.slice(1));
  if (tab) tab.classList.add('active');
  if (tabName === 'groups') loadIntelGroups();
  if (tabName === 'domains') loadIntelDomains();
  if (tabName === 'wallets') loadIntelWallets();
  if (tabName === 'victims') loadIntelVictims();
}

async function loadIntel() {
  try {
    const data = await apiGet('/api/telegram-intel/overview');
    const s = data.stats || {};
    const stats = document.getElementById('intelStats');
    if (!stats) return;

    stats.innerHTML =
      statCard('Intel Items', s.total_messages || 0, 'fa-fingerprint', '#003366') +
      statCard('Victims Found', s.victims_detected || 0, 'fa-user-injured', '#dc3545') +
      statCard('High Risk', s.high_risk_messages || 0, 'fa-triangle-exclamation', '#dc3545') +
      statCard('Groups Monitored', s.groups_monitored || 0, 'fa-satellite-dish', '#003366') +
      statCard('Domains Tracked', s.domains_tracked || 0, 'fa-globe', '#c5a55a') +
      statCard('Wallets Tracked', s.wallets_tracked || 0, 'fa-wallet', '#c5a55a');

    // Scam types
    const scamEl = document.getElementById('intelScamTypes');
    const types = data.scam_types || [];
    if (types.length > 0) {
      scamEl.innerHTML = types.map(t => {
        const pct = s.total_messages ? Math.round((t.count / s.total_messages) * 100) : 0;
        const color = t.type === 'INVESTMENT_FRAUD' ? '#dc3545' : t.type === 'RECOVERY_SCAM' ? '#fd7e14' : '#6c757d';
        return '<div style="margin-bottom:10px;">' +
          '<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px;">' +
          '<span style="font-weight:600;">' + t.type.replace(/_/g, ' ') + '</span>' +
          '<span style="color:var(--text-muted);">' + t.count + ' (' + pct + '%)</span></div>' +
          '<div style="height:8px;background:var(--bg-page);border-radius:4px;overflow:hidden;">' +
          '<div style="height:100%;width:' + pct + '%;background:' + color + ';border-radius:4px;"></div></div></div>';
      }).join('');
    } else {
      scamEl.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No scam types detected yet.</div>';
    }

    // Top domains
    const domainsEl = document.getElementById('intelTopDomains');
    const domains = data.top_domains || [];
    if (domains.length > 0) {
      const maxMentions = domains[0].mentions || 1;
      domainsEl.innerHTML = domains.slice(0, 10).map(d => {
        const pct = Math.round((d.mentions / maxMentions) * 100);
        return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">' +
          '<i class="fa-solid fa-globe" style="color:#dc3545;font-size:12px;"></i>' +
          '<span style="font-size:13px;font-family:monospace;min-width:180px;">' + d.domain + '</span>' +
          '<div style="flex:1;height:6px;background:var(--bg-page);border-radius:3px;overflow:hidden;">' +
          '<div style="height:100%;width:' + pct + '%;background:#dc3545;border-radius:3px;"></div></div>' +
          '<span style="font-size:12px;color:var(--text-muted);min-width:30px;text-align:right;">' + d.mentions + '</span></div>';
      }).join('');
    } else {
      domainsEl.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No domains tracked yet.</div>';
    }

    // Top wallets
    const walletsEl = document.getElementById('intelTopWallets');
    const wallets = data.top_wallets || [];
    if (wallets.length > 0) {
      walletsEl.innerHTML = wallets.map(w => {
        return '<div style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:6px;background:var(--bg-page);margin-bottom:6px;">' +
          '<i class="fa-solid fa-wallet" style="color:#c5a55a;"></i>' +
          '<span style="font-family:monospace;font-size:12px;word-break:break-all;">' + w.address + '</span>' +
          '<span class="badge badge-medium" style="margin-left:auto;">' + (w.type || 'UNKNOWN') + '</span>' +
          '<span style="font-size:12px;color:var(--text-muted);">' + (w.mentions || 1) + 'x</span></div>';
      }).join('');
    } else {
      walletsEl.innerHTML = '<div style="color:var(--text-muted);font-size:13px;">No wallets tracked yet. The spy is scanning messages for crypto addresses.</div>';
    }

    // Recent intel feed
    const feedEl = document.getElementById('intelFeedList');
    const recent = data.recent || [];
    if (recent.length > 0) {
      feedEl.innerHTML = recent.slice(0, 40).map(i => {
        const riskColors = {CRITICAL:'#dc3545',HIGH:'#fd7e14',MEDIUM:'#ffc107',LOW:'#28a745',VICTIM:'#dc3545'};
        const borderColor = riskColors[i.risk] || '#ccc';
        const scamText = i.scam_type ? i.scam_type.replace(/_/g,' ') : '';
        const domains = (i.domains || []).join(', ');
        const wallets = (i.wallets || []).map(w => w.type + ': ' + w.address.slice(0,12) + '...').join(', ');
        const phones = (i.phones || []).join(', ');
        const date = i.timestamp ? new Date(i.timestamp).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
        return '<div class="case-card" style="border-left:3px solid ' + borderColor + ';">' +
          '<div style="display:flex;justify-content:space-between;align-items:start;">' +
          '<div><span style="font-weight:600;">' + (i.sender || 'Unknown') + '</span>' +
          (i.is_victim ? ' <span class="badge badge-high">VICTIM</span>' : '') +
          (scamText ? ' <span class="badge badge-medium">' + scamText + '</span>' : '') + '</div>' +
          '<div><span class="badge" style="background:' + borderColor + '22;color:' + borderColor + ';">' + i.risk + '</span></div></div>' +
          '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' +
          '<i class="fa-solid fa-comments"></i> ' + (i.group || 'Unknown') + ' | ' +
          '<i class="fa-solid fa-clock"></i> ' + date +
          (domains ? ' | <i class="fa-solid fa-globe"></i> ' + domains : '') +
          (wallets ? ' | <i class="fa-solid fa-wallet"></i> ' + wallets : '') +
          (phones ? ' | <i class="fa-solid fa-phone"></i> ' + phones : '') + '</div></div>';
      }).join('');
    } else {
      feedEl.innerHTML = '<div class="empty-state"><p>No intelligence collected yet.</p></div>';
    }
  } catch(e) {
    console.error('Intel load error:', e);
  }
}

async function loadIntelGroups() {
  try {
    const data = await apiGet('/api/telegram-intel/groups');
    const el = document.getElementById('intelGroupsList');
    const groups = data.groups || [];
    if (groups.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>No groups monitored yet.</p></div>';
      return;
    }
    el.innerHTML = groups.map(g => {
      return '<div style="padding:12px;border-radius:8px;background:var(--bg-page);margin-bottom:8px;border:1px solid var(--border);">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
        '<div><i class="fa-solid fa-users" style="color:#003366;margin-right:6px;"></i>' +
        '<span style="font-weight:600;font-size:14px;">' + g.name + '</span>' +
        (g.username ? ' <a href="https://t.me/' + g.username + '" target="_blank" style="color:var(--text-muted);font-size:12px;">@' + g.username + '</a>' : '') + '</div>' +
        '<span class="badge badge-active">MONITORED</span></div>' +
        '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">' +
        '<i class="fa-solid fa-calendar"></i> First seen: ' + (g.first_seen ? new Date(g.first_seen).toLocaleDateString('en-GB') : '-') + ' | ' +
        '<i class="fa-solid fa-clock"></i> Last activity: ' + (g.last_activity ? new Date(g.last_activity).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '-') + '</div></div>';
    }).join('');
  } catch(e) {
    console.error('Groups load error:', e);
  }
}

async function loadIntelDomains() {
  try {
    const data = await apiGet('/api/telegram-intel/domains?limit=200');
    const el = document.getElementById('intelDomainsBody');
    const domains = data.domains || [];
    if (domains.length === 0) {
      el.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No domains tracked yet.</td></tr>';
      return;
    }
    el.innerHTML = domains.map(d => {
      const riskBadge = d.risk === 'HIGH' ? '<span class="badge badge-high">HIGH</span>' :
        d.risk === 'MEDIUM' ? '<span class="badge badge-medium">MEDIUM</span>' :
        d.risk === 'LOW' ? '<span class="badge badge-low">LOW</span>' :
        '<span class="badge" style="background:#e9ecef;color:#6c757d;">' + (d.risk || 'UNKNOWN') + '</span>';
      return '<tr>' +
        '<td style="font-family:monospace;font-size:12px;"><a href="https://' + d.domain + '" target="_blank" style="color:#003366;">' + d.domain + '</a></td>' +
        '<td>' + d.mentions + '</td>' +
        '<td>' + riskBadge + '</td>' +
        '<td>' + (d.group || '-') + '</td>' +
        '<td>' + (d.sender || '-') + '</td>' +
        '<td>' + (d.last_seen ? new Date(d.last_seen).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '-') + '</td></tr>';
    }).join('');
  } catch(e) {
    console.error('Domains load error:', e);
  }
}

async function loadIntelWallets() {
  try {
    const data = await apiGet('/api/telegram-intel/wallets?limit=200');
    const el = document.getElementById('intelWalletsBody');
    const wallets = data.wallets || [];
    if (wallets.length === 0) {
      el.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No wallets tracked yet. The spy scans every message for crypto addresses.</td></tr>';
      return;
    }
    el.innerHTML = wallets.map(w => {
      return '<tr>' +
        '<td style="font-family:monospace;font-size:11px;word-break:break-all;">' + w.address + '</td>' +
        '<td><span class="badge badge-medium">' + (w.type || 'UNKNOWN') + '</span></td>' +
        '<td>' + w.mentions + '</td>' +
        '<td>' + (w.group || '-') + '</td>' +
        '<td>' + (w.sender || '-') + '</td>' +
        '<td>' + (w.last_seen ? new Date(w.last_seen).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '-') + '</td></tr>';
    }).join('');
  } catch(e) {
    console.error('Wallets load error:', e);
  }
}

async function loadIntelVictims() {
  try {
    const data = await apiGet('/api/telegram-intel/victims?limit=100');
    const el = document.getElementById('intelVictimsList');
    const victims = data.victims || [];
    if (victims.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>No victims detected yet. The spy monitors messages for victim patterns.</p></div>';
      return;
    }
    el.innerHTML = victims.map(v => {
      const date = v.timestamp ? new Date(v.timestamp).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
      return '<div class="case-card" style="border-left:3px solid #dc3545;">' +
        '<div style="display:flex;justify-content:space-between;align-items:start;">' +
        '<div><i class="fa-solid fa-user-injured" style="color:#dc3545;margin-right:6px;"></i>' +
        '<span style="font-weight:600;">' + (v.name || 'Unknown') + '</span>' +
        (v.username ? ' <a href="https://t.me/' + v.username + '" target="_blank" style="font-size:12px;color:var(--text-muted);">@' + v.username + '</a>' : '') + '</div>' +
        '<div><span class="badge badge-high">VICTIM</span>' +
        (v.scam_type ? ' <span class="badge badge-medium">' + v.scam_type.replace(/_/g,' ') + '</span>' : '') + '</div></div>' +
        '<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">' +
        '<i class="fa-solid fa-comments"></i> ' + (v.group || 'Unknown') + ' | ' +
        '<i class="fa-solid fa-clock"></i> ' + date + '</div>' +
        (v.text ? '<div style="font-size:12px;margin-top:6px;padding:8px;background:var(--bg-page);border-radius:4px;font-style:italic;">"' + v.text + '"</div>' : '') +
        (v.wallets && v.wallets.length > 0 ? '<div style="font-size:11px;margin-top:4px;"><i class="fa-solid fa-wallet"></i> ' + v.wallets.length + ' wallet(s) mentioned</div>' : '') +
        (v.domains && v.domains.length > 0 ? '<div style="font-size:11px;"><i class="fa-solid fa-globe"></i> ' + v.domains.join(', ') + '</div>' : '') +
        (v.phones && v.phones.length > 0 ? '<div style="font-size:11px;"><i class="fa-solid fa-phone"></i> ' + v.phones.join(', ') + '</div>' : '') +
        '</div>';
    }).join('');
  } catch(e) {
    console.error('Victims load error:', e);
  }
}

async function intelSearch() {
  const q = document.getElementById('intelSearchInput').value.trim();
  if (q.length < 2) return;
  const el = document.getElementById('intelSearchResults');
  el.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Searching...</div>';
  try {
    const data = await apiGet('/api/telegram-intel/search?q=' + encodeURIComponent(q) + '&limit=100');
    const results = data.results || [];
    if (results.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>No results found for "' + q + '"</p></div>';
      return;
    }
    el.innerHTML = '<div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;">' + results.length + ' result(s) for "' + q + '"</div>' +
      results.map(r => {
        const riskColors = {CRITICAL:'#dc3545',HIGH:'#fd7e14',MEDIUM:'#ffc107',LOW:'#28a745',VICTIM:'#dc3545'};
        const borderColor = riskColors[r.risk] || '#ccc';
        const date = r.timestamp ? new Date(r.timestamp).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
        return '<div class="case-card" style="border-left:3px solid ' + borderColor + ';">' +
          '<div style="display:flex;justify-content:space-between;">' +
          '<div><span style="font-weight:600;">' + (r.sender || 'Unknown') + '</span>' +
          (r.is_victim ? ' <span class="badge badge-high">VICTIM</span>' : '') +
          (r.scam_type ? ' <span class="badge badge-medium">' + r.scam_type.replace(/_/g,' ') + '</span>' : '') + '</div>' +
          '<span class="badge" style="background:' + borderColor + '22;color:' + borderColor + ';">' + r.risk + '</span></div>' +
          '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' +
          '<i class="fa-solid fa-comments"></i> ' + (r.group || 'Unknown') + ' | <i class="fa-solid fa-clock"></i> ' + date + '</div>' +
          (r.text ? '<div style="font-size:12px;margin-top:6px;padding:8px;background:var(--bg-page);border-radius:4px;">"' + r.text + '"</div>' : '') +
          (r.wallets && r.wallets.length > 0 ? '<div style="font-size:11px;margin-top:4px;"><i class="fa-solid fa-wallet"></i> ' + r.wallets.map(w=>w.type+': '+w.address.slice(0,16)+'...').join(', ') + '</div>' : '') +
          (r.domains && r.domains.length > 0 ? '<div style="font-size:11px;"><i class="fa-solid fa-globe"></i> ' + r.domains.join(', ') + '</div>' : '') +
          (r.phones && r.phones.length > 0 ? '<div style="font-size:11px;"><i class="fa-solid fa-phone"></i> ' + r.phones.join(', ') + '</div>' : '') +
          '</div>';
      }).join('');
  } catch(e) {
    el.innerHTML = '<div class="empty-state"><p>Search error: ' + e.message + '</p></div>';
  }
}

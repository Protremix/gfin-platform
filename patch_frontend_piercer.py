#!/usr/bin/env python3
"""Patch case_detail.html to add Proxy Piercer button and results panel."""

with open("/gfin/web/case_detail.html", "r") as f:
    content = f.read()

# 1. Add "Run Proxy Piercer" button next to "Advance Phase" button
old_buttons = '''      <button class="btn btn-outline" onclick="setPriority()">Set Priority</button>
      <button class="btn btn-primary" onclick="advancePhase()">Advance Phase</button>'''

new_buttons = '''      <button class="btn btn-outline" onclick="setPriority()">Set Priority</button>
      <button class="btn btn-primary" onclick="advancePhase()">Advance Phase</button>
      <button class="btn btn-outline" style="border-color:var(--info);color:var(--info);" onclick="runProxyPiercer()">🔍 Pierce Proxy</button>'''

content = content.replace(old_buttons, new_buttons)

# 2. Add a new tab for Proxy Piercer results
old_tab_entities = '''      <div class="tab ${activeTab === 'evidence' ? 'active' : ''}" onclick="switchTab('evidence')">Evidence (${caseData.evidence ? caseData.evidence.length : 0})</div>'''

new_tab_entities = '''      <div class="tab ${activeTab === 'piercer' ? 'active' : ''}" onclick="switchTab('piercer')">Proxy Piercer</div>
      <div class="tab ${activeTab === 'evidence' ? 'active' : ''}" onclick="switchTab('evidence')">Evidence (${caseData.evidence ? caseData.evidence.length : 0})</div>'''

content = content.replace(old_tab_entities, new_tab_entities)

# 3. Add the Piercer tab content rendering — insert before the Evidence tab content
old_evidence_tab = '''  else if (activeTab === 'evidence') {'''

new_evidence_tab = '''  else if (activeTab === 'piercer') {
    if (piercerResults) {
      const r = piercerResults;
      html += '<div class="phase-detail"><h2>Proxy & Privacy Piercing Results</h2>';
      html += '<p class="phase-desc">' + (r.summary || 'No summary') + '</p>';
      
      // Detection status badges
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">';
      if (r.privacy_detected) {
        html += '<span class="tag" style="background:#fef3c7;color:#92400e;">🔒 WHOIS Privacy Detected</span>';
      } else {
        html += '<span class="tag" style="background:#d1fae5;color:#065f46;">✓ No WHOIS Privacy</span>';
      }
      if (r.cdn_detected) {
        html += '<span class="tag" style="background:#fee2e2;color:#991b1b;">🛡️ CDN Detected: ' + (r.cdn_provider || '?') + '</span>';
      } else {
        html += '<span class="tag" style="background:#d1fae5;color:#065f46;">✓ No CDN</span>';
      }
      if (r.origin_ip) {
        html += '<span class="tag" style="background:#dbeafe;color:#1e40af;">📍 Origin IP: ' + r.origin_ip + '</span>';
      }
      if (r.physical_location) {
        const loc = r.physical_location;
        html += '<span class="tag" style="background:#dbeafe;color:#1e40af;">📌 ' + (loc.city || '?') + ', ' + (loc.country || '?') + '</span>';
      }
      if (r.real_identity) {
        const id = r.real_identity;
        if (id.name) html += '<span class="tag" style="background:#f3e8ff;color:#6b21a8;">👤 ' + id.name + '</span>';
        if (id.email) html += '<span class="tag" style="background:#f3e8ff;color:#6b21a8;">✉️ ' + id.email + '</span>';
      }
      html += '<span class="tag" style="background:' + (r.confidence === 'HIGH' ? '#d1fae5' : r.confidence === 'MEDIUM' ? '#fef3c7' : '#f3f4f6') + ';color:' + (r.confidence === 'HIGH' ? '#065f46' : r.confidence === 'MEDIUM' ? '#92400e' : '#6b7280') + ';">Confidence: ' + r.confidence + '</span>';
      html += '</div>';
      
      // Evidence list
      if (r.evidence && r.evidence.length > 0) {
        html += '<h3>Evidence (' + r.evidence.length + ')</h3>';
        html += '<div class="step-list">';
        r.evidence.forEach(e => {
          const confColor = e.confidence === 'HIGH' ? '#d1fae5' : e.confidence === 'MEDIUM' ? '#fef3c7' : '#f3f4f6';
          const confText = e.confidence === 'HIGH' ? '#065f46' : e.confidence === 'MEDIUM' ? '#92400e' : '#6b7280';
          html += '<div class="step-item" style="flex-direction:column;align-items:stretch;">';
          html += '<div style="display:flex;align-items:center;gap:12px;">';
          html += '<div class="step-icon COMPLETED">🔍</div>';
          html += '<div class="step-name">' + e.finding + '</div>';
          html += '<span style="background:' + confColor + ';color:' + confText + ';padding:2px 8px;border-radius:4px;font-size:11px;">' + e.confidence + '</span>';
          html += '</div>';
          html += '<div style="margin-top:6px;padding-left:40px;font-size:12px;color:var(--text-muted);">';
          html += '<strong>Method:</strong> ' + e.method;
          if (e.data) {
            const dataStr = Object.entries(e.data).map(([k,v]) => k + ': ' + v).join(' · ');
            if (dataStr) html += '<br><strong>Data:</strong> ' + dataStr;
          }
          html += '</div>';
          html += '</div>';
        });
        html += '</div>';
      }
      
      // Methods tried
      if (r.methods_tried && r.methods_tried.length > 0) {
        const uniqueMethods = [...new Set(r.methods_tried)];
        html += '<h3 style="margin-top:16px;">Methods Used (' + uniqueMethods.length + ')</h3>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;">';
        uniqueMethods.forEach(m => {
          html += '<span style="background:var(--bg-card);border:1px solid var(--border);padding:4px 10px;border-radius:4px;font-size:12px;">' + m + '</span>';
        });
        html += '</div>';
      }
      
      // Correlations
      if (r.correlations && r.correlations.length > 0) {
        html += '<h3>Cross-Case Correlations</h3>';
        r.correlations.forEach(c => {
          html += '<div style="background:#fef3c7;padding:8px 12px;border-radius:4px;margin-bottom:4px;font-size:13px;">';
          html += '<strong>' + c.entity_type + ':</strong> ' + c.entity_value + ' — found in ' + c.source;
          html += '</div>';
        });
      }
      
      html += '</div>';
    } else {
      html += '<div class="empty-state"><div class="icon">🔍</div>';
      html += '<h3>Proxy & Privacy Piercing</h3>';
      html += '<p>Detect WHOIS privacy services, CDN proxies, and trace the real scammer behind them.</p>';
      html += '<p style="color:var(--text-muted);font-size:13px;max-width:500px;margin:0 auto;">';
      html += 'This will attempt to:<br>';
      html += '• Detect if the domain uses WHOIS privacy protection<br>';
      html += '• Check if the domain is behind a CDN (Cloudflare, Sucuri, etc.)<br>';
      html += '• Find the real origin IP hidden behind the CDN<br>';
      html += '• Trace the physical location of the hosting server<br>';
      html += '• Look up historical WHOIS records for the real registrant<br>';
      html += '• Find other domains sharing the same SSL certificate<br>';
      html += '• Correlate emails/phones with other cases';
      html += '</p><br>';
      html += '<button class="btn btn-primary" onclick="runProxyPiercer()">🔍 Run Proxy Piercer</button>';
      html += '</div>';
    }
  }
  else if (activeTab === 'evidence') {'''

content = content.replace(old_evidence_tab, new_evidence_tab)

# 4. Add the JavaScript function for running the piercer
old_add_evidence_func = '''function addEvidence() {'''

new_add_evidence_func = '''let piercerResults = null;

function runProxyPiercer() {
  if (!confirm('Run proxy & privacy piercing investigation on ' + (caseData.case.target || CASE_ID) + '?\\\\n\\\\nThis will check for WHOIS privacy, CDN proxies, and try to find the real scammer identity and location.')) return;
  
  // Show loading
  piercerResults = { loading: true, summary: 'Running proxy piercing investigation...' };
  switchTab('piercer');
  
  fetch(`${API}/piercer/investigate-case/${CASE_ID}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      officer_name: 'GFIN Admin',
      officer_id: 1
    })
  })
  .then(r => r.json())
  .then(data => {
    if (data.result) {
      piercerResults = data.result;
    } else {
      piercerResults = data;
    }
    switchTab('piercer');
    // Also reload case to show new evidence
    loadCase();
  })
  .catch(err => {
    piercerResults = { summary: 'Error: ' + err.message, evidence: [], confidence: 'LOW' };
    switchTab('piercer');
  });
}

function addEvidence() {'''

content = content.replace(old_add_evidence_func, new_add_evidence_func)

with open("/gfin/web/case_detail.html", "w") as f:
    f.write(content)
print("Frontend patched — Proxy Piercer tab and button added")

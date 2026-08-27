#!/usr/bin/env python3
"""Patch case_detail.html to add Evidence tab with officer tracking and add-evidence form."""

with open("/gfin/web/case_detail.html", "r") as f:
    content = f.read()

# 1. Add Evidence tab to the tab bar
old_tabs = '''      <div class="tab ${activeTab === 'entities' ? 'active' : ''}" onclick="switchTab('entities')">Entities (${caseData.entities.length})</div>'''

new_tabs = '''      <div class="tab ${activeTab === 'evidence' ? 'active' : ''}" onclick="switchTab('evidence')">Evidence (${caseData.evidence ? caseData.evidence.length : 0})</div>
      <div class="tab ${activeTab === 'entities' ? 'active' : ''}" onclick="switchTab('entities')">Entities (${caseData.entities.length})</div>'''

content = content.replace(old_tabs, new_tabs)

# 2. Add evidence tab content rendering — insert before the entities tab
old_entities_tab = '''  else if (activeTab === 'entities') {'''
new_entities_tab = '''  else if (activeTab === 'evidence') {
    const evidence = caseData.evidence || [];
    if (evidence.length === 0) {
      html += `<div class="empty-state"><div class="icon">📁</div>No evidence recorded yet<br><br>
        <button class="btn btn-primary" onclick="addEvidence()">+ Add Evidence</button></div>`;
    } else {
      html += '<div class="phase-detail"><h2>Evidence Chain</h2><p class="phase-desc">All evidence linked to this case. Each entry shows who added it and when.</p>';
      html += '<button class="btn btn-primary" style="margin-bottom:16px;" onclick="addEvidence()">+ Add Evidence</button>';
      html += '<div class="step-list">';
      evidence.forEach(e => {
        const officerName = e.added_by_officer || 'SYSTEM';
        const officerAgency = e.officer_agency || '';
        const officerCountry = e.officer_country || '';
        const addedDate = e.added_date || e.created_date;
        const dateStr = addedDate ? new Date(addedDate).toLocaleString() : '';
        const officerInfo = officerAgency ? `${officerName} (${officerAgency}${officerCountry ? ', ' + officerCountry : ''})` : officerName;
        const confClass = e.confidence === 'HIGH' ? 'confidence-HIGH' : e.confidence === 'MEDIUM' ? 'confidence-MEDIUM' : 'confidence-LOW';
        
        html += `<div class="step-item" style="flex-direction:column;align-items:stretch;">
          <div style="display:flex;align-items:center;gap:12px;">
            <div class="step-icon COMPLETED">📁</div>
            <div class="step-name">${e.evidence_id}: ${e.finding || 'No description'}</div>
            <span class="step-type ${e.source_type === 'INVESTIGATOR' ? 'MANUAL' : 'AUTO'}">${e.source_type || 'AUTO'}</span>
            <span class="entity-confidence ${confClass}">${e.confidence || 'MEDIUM'}</span>
          </div>
          <div style="margin-top:8px;padding-left:40px;font-size:12px;color:var(--text-muted);">
            <div><strong>Added by:</strong> ${officerInfo} <span style="color:var(--text-muted);">· ${dateStr}</span></div>
            ${e.source_provider ? `<div><strong>Source:</strong> ${e.source_provider}</div>` : ''}
            ${e.source_url ? `<div><strong>URL:</strong> <a href="${e.source_url}" target="_blank" style="color:var(--info);">${e.source_url}</a></div>` : ''}
            ${e.phase ? `<div><strong>Phase:</strong> ${e.phase}</div>` : ''}
          </div>
        </div>`;
      });
      html += '</div></div>';
    }
  }
  else if (activeTab === 'entities') {'''

content = content.replace(old_entities_tab, new_entities_tab)

# 3. Add addEvidence function — insert before the createAction function
old_create_action = '''function createAction() {'''
new_create_action = '''function addEvidence() {
  const finding = prompt('Evidence finding (what did you discover?):', '');
  if (!finding) return;
  const phase = prompt('Investigation phase:', caseData.current_phase);
  const source = prompt('Source (e.g. WHOIS Lookup, Blockchain Explorer, Manual Review):', 'Manual Review');
  const confidence = prompt('Confidence (LOW, MEDIUM, HIGH):', 'HIGH');
  fetch(`${API}/case/${CASE_ID}/evidence`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      finding: finding,
      phase: phase,
      source_provider: source,
      source_type: 'INVESTIGATOR',
      confidence: confidence,
      officer_name: 'GFIN Admin',
      officer_id: 1
    })
  }).then(r => r.json()).then(() => loadCase());
}

function createAction() {'''

content = content.replace(old_create_action, new_create_action)

# 4. Also update the entities tab to show who added each entity
old_entity_card = '''        byType[type].forEach(e => {
          html += `<div class="entity-card">
            <div class="entity-type">${e.entity_type}</div>
            <div class="entity-value">${e.entity_value}</div>
            <div class="entity-meta">Source: ${e.source || 'AUTO'}</div>
            <div style="margin-top:6px;">
              <span class="entity-confidence confidence-${e.confidence}">${e.confidence}</span>
              <span style="font-size:11px;color:var(--text-muted);margin-left:8px;">${e.status}</span>
            </div>
          </div>`;
        });'''

new_entity_card = '''        byType[type].forEach(e => {
          const officerName = e.added_by_officer || 'SYSTEM';
          const officerAgency = e.officer_agency || '';
          const officerInfo = officerAgency ? `${officerName} (${officerAgency})` : officerName;
          html += `<div class="entity-card">
            <div class="entity-type">${e.entity_type}</div>
            <div class="entity-value">${e.entity_value}</div>
            <div class="entity-meta">Source: ${e.source || 'AUTO'}</div>
            <div style="margin-top:6px;">
              <span class="entity-confidence confidence-${e.confidence}">${e.confidence}</span>
              <span style="font-size:11px;color:var(--text-muted);margin-left:8px;">${e.status}</span>
            </div>
            <div style="margin-top:6px;font-size:11px;color:var(--info);">
              Added by: ${officerInfo} · ${new Date(e.created_date).toLocaleDateString()}
            </div>
          </div>`;
        });'''

content = content.replace(old_entity_card, new_entity_card)

with open("/gfin/web/case_detail.html", "w") as f:
    f.write(content)
print("Frontend patched — Evidence tab with officer tracking added")

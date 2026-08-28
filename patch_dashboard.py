#!/usr/bin/env python3
"""
Patches investigator_workbench.html to add:
1. Decision Support view (analyst recommendations)
2. Victim Support view (victim timeline/updates)
"""
import re

with open("/gfin/investigator_workbench.html", "r") as f:
    html = f.read()

# 1. Add nav items after "Outreach" in sidebar
nav_marker = '<div class="nav-item" onclick="switchView(\'outreach\')"><i class="fa-solid fa-bullhorn"></i> Outreach</div>'
nav_addition = nav_marker + """
      <div class="nav-item" onclick="switchView('recommendations')"><i class="fa-solid fa-clipboard-check"></i> Recommendations <span class="badge" id="recsBadge" style="background:#dc2626;color:white">0</span></div>"""
html = html.replace(nav_marker, nav_addition, 1)

# Add Victim Support under TOOLS
tools_marker = '<div class="nav-item" onclick="switchView(\'search\')"><i class="fa-solid fa-magnifying-glass"></i> Search</div>'
tools_addition = tools_marker + """
      <div class="nav-item" onclick="switchView('victimSupport')"><i class="fa-solid fa-hand-holding-heart"></i> Victim Support</div>"""
html = html.replace(tools_marker, tools_addition, 1)

# 2. Add new view sections before the closing </div> after view-aiEngines
# Find the end of view-aiEngines
ai_marker = '  <div class="view" id="view-aiEngines">'
ai_pos = html.find(ai_marker)
# Find the closing </div> that ends the aiEngines view
# We'll insert before the final closing divs
# Actually, let's find the </main> or the end of views

# Find where views end - look for the last view and add after
last_view_end = html.find('</div>\n\n    </div>\n  <div class="view" id="view-aiEngines">')
if last_view_end == -1:
    # Try alternate pattern
    # Find end of aiEngines view - it's the last view before closing main
    main_close = html.find('</main>', ai_pos)
    if main_close == -1:
        main_close = html.find('</body>', ai_pos)

    # Insert new views before </main> or </body>
    new_views = """
    <!-- DECISION SUPPORT VIEW -->
    <div id="view-recommendations" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <div>
          <h2 class="page-title"><i class="fa-solid fa-clipboard-check" style="color:var(--navy);"></i> Analyst Decision Support</h2>
          <p style="color:var(--text-muted);font-size:13px;margin-top:4px;">AI-driven recommendations for active investigations</p>
        </div>
        <button class="btn btn-outline" onclick="loadRecommendations()"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>

      <!-- Priority Summary Cards -->
      <div id="recSummary" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;"></div>

      <!-- Recommendations List -->
      <div id="recList"></div>
    </div>

    <!-- VICTIM SUPPORT VIEW -->
    <div id="view-victimSupport" class="view">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <div>
          <h2 class="page-title"><i class="fa-solid fa-hand-holding-heart" style="color:var(--navy);"></i> Victim Support Center</h2>
          <p style="color:var(--text-muted);font-size:13px;margin-top:4px;">Track victim complaints, status updates, and support timelines</p>
        </div>
        <button class="btn btn-outline" onclick="loadVictimSupport()"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>

      <!-- Stage Distribution -->
      <div id="victimStageCards" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:20px;"></div>

      <!-- Complaint List with Timelines -->
      <div id="victimComplaintList"></div>
    </div>

"""
    html = html[:main_close] + new_views + html[main_close:]

# 3. Update switchView function to handle new views
switch_marker = "else if (view === 'aiEngines') loadAiEngines();"
switch_replacement = """else if (view === 'aiEngines') loadAiEngines();
  else if (view === 'recommendations') loadRecommendations();
  else if (view === 'victimSupport') loadVictimSupport();"""
html = html.replace(switch_marker, switch_replacement, 1)

# 4. Add JavaScript functions before the closing </script> tag
# Find the last </script> in the file
script_close = html.rfind('</script>')
if script_close == -1:
    script_close = html.rfind('</body>')

js_code = """
// === DECISION SUPPORT ===
async function loadRecommendations() {
  try {
    const data = await apiGet('/api/decision-support/recommendations');
    if (!data.recommendations) return;

    const recs = data.recommendations;
    const critical = recs.filter(r => r.priority === 'CRITICAL').length;
    const high = recs.filter(r => r.priority === 'HIGH').length;
    const medium = recs.filter(r => r.priority === 'MEDIUM').length;

    document.getElementById('recsBadge').textContent = critical > 0 ? critical : recs.length;
    document.getElementById('recsBadge').style.background = critical > 0 ? '#dc2626' : 'var(--gold)';

    // Summary cards
    const colors = { CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#ca8a04', LOW: '#64748b' };
    const summary = document.getElementById('recSummary');
    summary.innerHTML = `
      <div class="stat-card" style="padding:16px;border-left:4px solid ${colors.CRITICAL};">
        <div style="font-size:24px;font-weight:800;color:${colors.CRITICAL};">${critical}</div>
        <div style="font-size:12px;color:var(--text-muted);">CRITICAL</div>
      </div>
      <div class="stat-card" style="padding:16px;border-left:4px solid ${colors.HIGH};">
        <div style="font-size:24px;font-weight:800;color:${colors.HIGH};">${high}</div>
        <div style="font-size:12px;color:var(--text-muted);">HIGH Priority</div>
      </div>
      <div class="stat-card" style="padding:16px;border-left:4px solid ${colors.MEDIUM};">
        <div style="font-size:24px;font-weight:800;color:${colors.MEDIUM};">${medium}</div>
        <div style="font-size:12px;color:var(--text-muted);">MEDIUM</div>
      </div>
      <div class="stat-card" style="padding:16px;border-left:4px solid var(--navy);">
        <div style="font-size:24px;font-weight:800;color:var(--navy);">${recs.length}</div>
        <div style="font-size:12px;color:var(--text-muted);">Total Recommendations</div>
      </div>
    `;

    // Recommendations list
    const list = document.getElementById('recList');
    list.innerHTML = recs.map(r => {
      const actions = r.action_items ? JSON.parse(r.action_items) : [];
      const c = colors[r.priority] || colors.LOW;
      const icon = {
        TRAFFICKING: 'fa-triangle-exclamation',
        CROSS_CASE: 'fa-share-nodes',
        EVIDENCE_GAP: 'fa-magnifying-glass',
        FLIGHT_RISK: 'fa-plane-departure',
        TAKEDOWN: 'fa-ban',
        PROVENANCE: 'fa-shield-halved',
        INVESTIGATION: 'fa-folder-open',
      }[r.type] || 'fa-bell';

      return `
        <div class="stat-card" style="padding:16px;margin-bottom:12px;border-left:4px solid ${c};">
          <div style="display:flex;justify-content:space-between;align-items:start;">
            <div style="flex:1;">
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                <span style="background:${c};color:white;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;">${r.priority}</span>
                <i class="fa-solid ${icon}" style="color:${c};font-size:16px;"></i>
                <strong style="font-size:15px;color:var(--navy);">${r.title}</strong>
                <span style="font-size:11px;color:var(--text-muted);">${r.case_id}</span>
              </div>
              <p style="font-size:13px;color:var(--text-muted);margin-bottom:8px;">${r.description}</p>
              ${actions.length > 0 ? `
                <div style="background:#f8fafc;border-radius:6px;padding:10px;margin-top:8px;">
                  <div style="font-size:11px;font-weight:600;color:var(--text-muted);margin-bottom:6px;">RECOMMENDED ACTIONS:</div>
                  ${actions.map(a => `<div style="font-size:12px;padding:3px 0;display:flex;align-items:start;gap:6px;"><i class="fa-solid fa-chevron-right" style="color:${c};font-size:10px;margin-top:3px;"></i> ${a}</div>`).join('')}
                </div>
              ` : ''}
            </div>
            <div style="text-align:right;font-size:11px;color:var(--text-muted);min-width:80px;">
              <div>Risk: <strong>${(r.risk_score || 0).toFixed(2)}</strong></div>
              <div>Conf: <strong>${(r.confidence || 0).toFixed(2)}</strong></div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Recommendations error:', e);
    document.getElementById('recList').innerHTML = '<p style="color:var(--text-muted);">Unable to load recommendations.</p>';
  }
}

// === VICTIM SUPPORT ===
async function loadVictimSupport() {
  try {
    // Get all complaints with their stages
    const complaintsData = await apiGet('/api/inv/overview');
    const stageColors = {
      EVIDENCE_COLLECTED: { bg: '#dcfce7', text: '#15803d', icon: 'fa-check-circle' },
      INVESTIGATING: { bg: '#dbeafe', text: '#1d4ed8', icon: 'fa-magnifying-glass' },
      UNDER_REVIEW: { bg: '#fef3c7', text: '#a16207', icon: 'fa-eye' },
      RECEIVED: { bg: '#f1f5f9', text: '#475569', icon: 'fa-inbox' },
      REFERRED: { bg: '#e0e7ff', text: '#4338ca', icon: 'fa-paper-plane' },
      CLOSED: { bg: '#f1f5f9', text: '#64748b', icon: 'fa-circle-check' },
    };

    // Fetch victim updates for each complaint
    const complaints = complaintsData.complaints || [];
    const stageCounts = {};
    complaints.forEach(c => {
      const s = c.investigation_stage || 'RECEIVED';
      stageCounts[s] = (stageCounts[s] || 0) + 1;
    });

    // Stage distribution cards
    const cards = document.getElementById('victimStageCards');
    cards.innerHTML = Object.entries(stageCounts).map(([stage, count]) => {
      const sc = stageColors[stage] || stageColors.RECEIVED;
      return `
        <div class="stat-card" style="padding:14px;background:${sc.bg};border:none;">
          <div style="display:flex;align-items:center;gap:8px;">
            <i class="fa-solid ${sc.icon}" style="color:${sc.text};font-size:20px;"></i>
            <div>
              <div style="font-size:22px;font-weight:800;color:${sc.text};">${count}</div>
              <div style="font-size:11px;color:${sc.text};">${stage.replace(/_/g, ' ')}</div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Complaint list with expandable timelines
    const list = document.getElementById('victimComplaintList');
    list.innerHTML = complaints.map(c => {
      const stage = c.investigation_stage || 'RECEIVED';
      const sc = stageColors[stage] || stageColors.RECEIVED;
      const ref = c.reference_number || c.id;
      return `
        <div class="stat-card" style="padding:14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;cursor:pointer;" onclick="toggleVictimTimeline('${ref}')">
            <div style="display:flex;align-items:center;gap:12px;">
              <i class="fa-solid ${sc.icon}" style="color:${sc.text};font-size:18px;"></i>
              <div>
                <div style="font-weight:600;font-size:14px;">${ref}</div>
                <div style="font-size:12px;color:var(--text-muted);">${c.scam_type || 'Unknown'} &middot; ${(c.target || '').substring(0, 50)}</div>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="background:${sc.bg};color:${sc.text};font-size:11px;font-weight:600;padding:3px 10px;border-radius:4px;">${stage.replace(/_/g, ' ')}</span>
              <i class="fa-solid fa-chevron-down" id="arrow-${ref}" style="color:var(--text-muted);"></i>
            </div>
          </div>
          <div id="timeline-${ref}" style="display:none;margin-top:12px;padding-top:12px;border-top:1px solid var(--border);"></div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.error('Victim support error:', e);
    document.getElementById('victimComplaintList').innerHTML = '<p style="color:var(--text-muted);">Unable to load victim data.</p>';
  }
}

async function toggleVictimTimeline(ref) {
  const el = document.getElementById('timeline-' + ref);
  const arrow = document.getElementById('arrow-' + ref);
  if (el.style.display === 'none') {
    el.style.display = 'block';
    arrow.classList.remove('fa-chevron-down');
    arrow.classList.add('fa-chevron-up');
    el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading timeline...</p>';
    try {
      const data = await apiGet('/api/victim-support/updates/' + ref);
      if (data.updates && data.updates.length > 0) {
        el.innerHTML = '<div style="border-left:3px solid var(--navy);padding-left:16px;">' + data.updates.map(u => `
          <div style="margin-bottom:12px;">
            <div style="font-size:13px;font-weight:600;color:var(--navy);">${u.title}</div>
            <div style="font-size:12px;color:var(--text-muted);margin:4px 0;">${u.message}</div>
            <div style="font-size:11px;color:var(--text-muted);">${u.eta || ''} &middot; ${u.date ? new Date(u.date).toLocaleString() : ''}</div>
          </div>
        `).join('') + '</div>';
      } else {
        el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No updates yet.</p>';
      }
    } catch (err) {
      el.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">Error loading timeline.</p>';
    }
  } else {
    el.style.display = 'none';
    arrow.classList.remove('fa-chevron-up');
    arrow.classList.add('fa-chevron-down');
  }
}

"""

html = html[:script_close] + js_code + html[script_close:]

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(html)

print("Dashboard patched: +2 views (Recommendations, Victim Support), +2 nav items, +3 JS functions")

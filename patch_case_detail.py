#!/usr/bin/env python3
"""
Patches investigator_workbench.html to add:
1. Quality score badge on each case in the list
2. New "Quality" tab in case detail showing score breakdown + gap analysis
3. New "Timeline" tab showing chronological events
4. New "Custody" tab showing chain of custody records
"""
import re

with open("/gfin/investigator_workbench.html", "r") as f:
    html = f.read()

# 1. Add quality score badge to case rows in the cases list
# Find the case row template and add quality grade
# We'll inject it via the JS that renders cases

# Find the loadCases function and add quality fetch
cases_render_marker = "function renderCasesList"
if cases_render_marker not in html:
    # Find where cases are rendered
    cases_render_marker = "casesContainer"

# 2. Add new tabs to case detail view
# Find the existing tab buttons in case detail
tabs_marker = '<div class="tab-btn" onclick="switchTab(\'complaints\', this)">Complaints (${data.complaints.length})</div>'
if tabs_marker not in html:
    tabs_marker = "Complaints (${data.complaints.length})</div>"

# Find the position to add new tabs
tabs_pos = html.find(tabs_marker)
if tabs_pos != -1:
    # Find the closing </div> after the tab
    close_div = html.find("</div>", tabs_pos)
    insert_pos = html.find(">", close_div) + 1

    new_tabs = """
        <div class="tab-btn" onclick="switchTab('quality', this)" style="background:#f0fdf4;"><i class="fa-solid fa-star"></i> Quality</div>
        <div class="tab-btn" onclick="switchTab('crimetimeline', this)"><i class="fa-solid fa-clock-rotate-left"></i> Timeline</div>
        <div class="tab-btn" onclick="switchTab('custody', this)"><i class="fa-solid fa-shield-halved"></i> Custody</div>"""

    html = html[:tabs_pos] + new_tabs + "\n        " + html[tabs_pos:]

# 3. Add new tab content containers
# Find the last tab-content div
last_tab_content = '<div id="tab-complaints" class="tab-content">'
if last_tab_content in html:
    pos = html.find(last_tab_content)
    # Find the closing of this div
    # Insert new content divs after the complaints tab content
    end = html.find("</div>", html.find("</div>", pos) + 1)
    # Actually, let's find the pattern more carefully
    # Insert after the complaints tab content div

    # Find the closing div that ends the tab-content section
    # We need to find where tab-complaints content div closes
    # Let's just insert before the closing of the case detail section

    # Find the case detail closing
    case_detail_end = html.find('</div>\n\n      </div>\n\n    </div>', pos)
    if case_detail_end == -1:
        case_detail_end = html.find('</div>', html.find('</div>', html.find('</div>', pos) + 4) + 4)

    new_content = """
      <div id="tab-quality" class="tab-content">
        <div id="qualityContent" style="padding:8px 0;">
          <p style="color:var(--text-muted);font-size:13px;">Loading quality assessment...</p>
        </div>
      </div>

      <div id="tab-crimetimeline" class="tab-content">
        <div id="timelineContent" style="padding:8px 0;">
          <p style="color:var(--text-muted);font-size:13px;">Loading timeline...</p>
        </div>
      </div>

      <div id="tab-custody" class="tab-content">
        <div id="custodyContent" style="padding:8px 0;">
          <p style="color:var(--text-muted);font-size:13px;">Loading chain of custody...</p>
        </div>
      </div>"""

    # Find the correct insertion point - before the closing of the case detail section
    # Look for a pattern like </div>\n\n    </div> after the complaints tab
    search_start = pos
    for i in range(5):
        search_start = html.find("</div>", search_start) + 6

    html = html[:search_start] + new_content + "\n      " + html[search_start:]

# 4. Add JS to load quality, timeline, and custody data when case is opened
# Find the showCaseDetail function and add loading calls
show_detail_marker = "function showCaseDetail"
if show_detail_marker not in html:
    show_detail_marker = "async function showCaseDetail"

pos = html.find(show_detail_marker)
if pos != -1:
    # Find the end of this function or a good insertion point
    # Add calls after the function renders the case
    func_end = html.find("}", pos + 500)

    # Insert loading calls
    load_calls = """
  // Load quality, timeline, custody
  if (data.case && data.case.case_id) {
    loadQualityTab(data.case.case_id);
    loadTimelineTab(data.case.case_id);
    loadCustodyTab(data.case.case_id);
  }
"""
    html = html[:func_end] + load_calls + html[func_end:]

# 5. Add the JS functions for loading the new tabs
script_close = html.rfind('</script>')
if script_close == -1:
    script_close = html.rfind('</body>')

js_code = """
// === QUALITY TAB ===
async function loadQualityTab(caseId) {
  try {
    const qData = await apiGet('/api/inv-enhance/quality/' + caseId);
    const gData = await apiGet('/api/inv-enhance/gaps/' + caseId);

    let html_out = '';

    // Quality score
    if (qData.status === 'ok' && qData.total) {
      const gradeColors = { A: '#15803d', B: '#ca8a04', C: '#ea580c', D: '#dc2626', F: '#991b1b' };
      const gc = gradeColors[qData.grade] || '#64748b';

      html_out += '<div style="display:flex;align-items:center;gap:20px;margin-bottom:20px;">';
      html_out += '<div style="width:80px;height:80px;border-radius:50%;background:' + gc + ';color:white;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:800;">' + (qData.grade || 'F') + '</div>';
      html_out += '<div><div style="font-size:28px;font-weight:800;color:var(--navy);">' + (qData.total || 0).toFixed(1) + '/100</div>';
      html_out += '<div style="font-size:13px;color:var(--text-muted);">Investigation Quality Score</div></div></div>';

      // Score breakdown bars
      const scores = [
        { label: 'Evidence Count', value: qData.evidence || 0, max: 25, color: '#2563eb' },
        { label: 'Provenance Quality', value: qData.provenance || 0, max: 20, color: '#059669' },
        { label: 'Entity Coverage', value: qData.entity || 0, max: 15, color: '#7c3aed' },
        { label: 'Victim Count', value: qData.victim || 0, max: 15, color: '#db2777' },
        { label: 'Correlation Density', value: qData.correlation || 0, max: 15, color: '#ea580c' },
        { label: 'Investigation Steps', value: qData.steps || 0, max: 10, color: '#0891b2' },
      ];

      html_out += '<div style="margin-bottom:20px;">';
      scores.forEach(s => {
        const pct = (s.value / s.max) * 100;
        html_out += '<div style="margin-bottom:8px;">';
        html_out += '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;"><span>' + s.label + '</span><span><strong>' + s.value.toFixed(1) + '</strong>/' + s.max + '</span></div>';
        html_out += '<div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;"><div style="height:100%;width:' + pct + '%;background:' + s.color + ';border-radius:4px;"></div></div>';
        html_out += '</div>';
      });
      html_out += '</div>';
    }

    // Gap analysis
    if (gData.status === 'ok' && gData.checklist) {
      let checklist = gData.checklist;
      if (typeof checklist === 'string') checklist = JSON.parse(checklist);

      const readiness = gData.readiness || 0;
      const readyColor = readiness >= 80 ? '#15803d' : readiness >= 60 ? '#ca8a04' : '#dc2626';

      html_out += '<div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:16px;">';
      html_out += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">';
      html_out += '<div style="font-weight:700;font-size:15px;color:var(--navy);"><i class="fa-solid fa-clipboard-list"></i> Prosecution Readiness</div>';
      html_out += '<div style="font-size:24px;font-weight:800;color:' + readyColor + ';">' + readiness + '%</div></div>';

      const statusIcons = { MET: '<i class="fa-solid fa-check-circle" style="color:#15803d;"></i>', PARTIAL: '<i class="fa-solid fa-circle-half-stroke" style="color:#ca8a04;"></i>', MISSING: '<i class="fa-solid fa-times-circle" style="color:#dc2626;"></i>' };

      checklist.forEach(item => {
        html_out += '<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #e2e8f0;">';
        html_out += statusIcons[item.status] || '';
        html_out += '<div style="flex:1;font-size:13px;">' + item.item + '</div>';
        html_out += '<div style="font-size:11px;color:var(--text-muted);">' + item.current + '/' + item.target + '</div>';
        html_out += '<div style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;background:' + (item.status === 'MET' ? '#dcfce7' : item.status === 'PARTIAL' ? '#fef3c7' : '#fee2e2') + ';color:' + (item.status === 'MET' ? '#15803d' : item.status === 'PARTIAL' ? '#a16207' : '#dc2626') + ';">' + item.status + '</div>';
        html_out += '</div>';
      });

      html_out += '<div style="margin-top:10px;font-size:12px;color:var(--text-muted);">Met: ' + gData.met + ' | Partial: ' + gData.partial + ' | Missing: ' + gData.missing + '</div>';
      html_out += '</div>';
    }

    document.getElementById('qualityContent').innerHTML = html_out || '<p style="color:var(--text-muted);">No quality data available.</p>';
  } catch (e) {
    console.error('Quality tab error:', e);
    document.getElementById('qualityContent').innerHTML = '<p style="color:var(--text-muted);">Error loading quality data.</p>';
  }
}

// === TIMELINE TAB ===
async function loadTimelineTab(caseId) {
  try {
    const data = await apiGet('/api/inv-enhance/timeline/' + caseId);
    if (!data.events || data.events.length === 0) {
      document.getElementById('timelineContent').innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No timeline events recorded.</p>';
      return;
    }

    const typeColors = {
      EVIDENCE: '#2563eb', INVESTIGATION_STEP: '#059669', VICTIM_REPORT: '#db2777',
      TELEGRAM_INTEL: '#ea580c', INFRA: '#7c3aed', CONTENT: '#0891b2',
    };
    const typeIcons = {
      EVIDENCE: 'fa-vault', INVESTIGATION_STEP: 'fa-list-check', VICTIM_REPORT: 'fa-user',
      TELEGRAM_INTEL: 'fa-brands fa-telegram', INFRA: 'fa-server', CONTENT: 'fa-file-lines',
    };

    let html_out = '<div style="border-left:3px solid var(--navy);padding-left:20px;">';
    data.events.forEach(ev => {
      const c = typeColors[ev.type] || '#64748b';
      const icon = typeIcons[ev.type] || 'fa-circle';
      const date = ev.date ? new Date(ev.date).toLocaleString() : 'Unknown date';
      html_out += '<div style="margin-bottom:16px;position:relative;">';
      html_out += '<div style="position:absolute;left:-28px;width:14px;height:14px;border-radius:50%;background:' + c + ';border:2px solid white;box-shadow:0 0 0 2px ' + c + ';"></div>';
      html_out += '<div style="font-size:12px;color:' + c + ';font-weight:600;margin-bottom:2px;"><i class="fa-solid ' + icon + '"></i> ' + ev.type.replace(/_/g, ' ') + '</div>';
      html_out += '<div style="font-size:13px;">' + (ev.description || '') + '</div>';
      html_out += '<div style="font-size:11px;color:var(--text-muted);margin-top:2px;">' + date + ' &middot; ' + (ev.source || '') + '</div>';
      html_out += '</div>';
    });
    html_out += '</div>';

    document.getElementById('timelineContent').innerHTML = html_out;
  } catch (e) {
    document.getElementById('timelineContent').innerHTML = '<p style="color:var(--text-muted);">Error loading timeline.</p>';
  }
}

// === CUSTODY TAB ===
async function loadCustodyTab(caseId) {
  try {
    const data = await apiGet('/api/inv-enhance/custody/' + caseId);
    if (!data.custody_records || data.custody_records.length === 0) {
      document.getElementById('custodyContent').innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No custody records.</p>';
      return;
    }

    let html_out = '<div style="font-size:13px;">';
    html_out += '<div style="margin-bottom:12px;font-weight:600;color:var(--navy);">' + data.count + ' custody records for ' + caseId + '</div>';

    data.custody_records.forEach(r => {
      html_out += '<div style="background:#f8fafc;border-radius:6px;padding:12px;margin-bottom:8px;border-left:3px solid #059669;">';
      html_out += '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">';
      html_out += '<div style="font-weight:600;font-size:12px;">' + r.evidence_id + '</div>';
      html_out += '<div style="font-size:11px;color:var(--text-muted);">' + (r.date ? new Date(r.date).toLocaleString() : '') + '</div></div>';
      html_out += '<div style="font-size:12px;margin-bottom:4px;"><strong>Custodian:</strong> ' + r.custodian + '</div>';
      html_out += '<div style="font-size:12px;margin-bottom:4px;"><strong>Purpose:</strong> ' + r.purpose + '</div>';
      html_out += '<div style="font-size:11px;color:var(--text-muted);font-family:monospace;">Hash: ' + (r.hash || '').substring(0, 24) + '...</div>';
      html_out += '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">' + (r.notes || '') + '</div>';
      html_out += '</div>';
    });
    html_out += '</div>';

    document.getElementById('custodyContent').innerHTML = html_out;
  } catch (e) {
    document.getElementById('custodyContent').innerHTML = '<p style="color:var(--text-muted);">Error loading custody records.</p>';
  }
}

"""

html = html[:script_close] + js_code + html[script_close:]

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(html)

print("Dashboard patched: Quality + Timeline + Custody tabs in case detail")
print("Functions added: loadQualityTab(), loadTimelineTab(), loadCustodyTab()")

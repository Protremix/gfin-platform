#!/usr/bin/env python3
"""
Patch dashboard to add Attribution and Legal Framework sections to case detail view.
"""
import re

with open("/gfin/investigator_workbench.html", "r") as f:
    html = f.read()

# 1. Add two new tab buttons after the custody tab
custody_tab = 'onclick="switchTab(\'custody\', this)"><i class="fa-solid fa-shield-halved"></i> Custody</div>'
if custody_tab in html:
    new_tabs = """        <div class="tab-btn" onclick="switchTab('attribution', this)" style="background:#fef3c7;"><i class="fa-solid fa-user-secret"></i> Attribution</div>
        <div class="tab-btn" onclick="switchTab('legal', this)" style="background:#fee2e2;"><i class="fa-solid fa-gavel"></i> Legal</div>"""
    html = html.replace(custody_tab, custody_tab + "\n" + new_tabs)

# 2. Add tab content containers after the custody content div
custody_content = '<div id="tab-custody" class="tab-content">'
pos = html.find(custody_content)
if pos != -1:
    # Find end of custody content div
    end = html.find("</div>", pos)
    end = html.find("</div>", end + 6)  # Close inner div

    new_content = """
      <div id="tab-attribution" class="tab-content">
        <div id="attributionContent" style="padding:8px 0;">
          <p style="color:var(--text-muted);font-size:13px;">Loading attribution...</p>
        </div>
      </div>

      <div id="tab-legal" class="tab-content">
        <div id="legalContent" style="padding:8px 0;">
          <p style="color:var(--text-muted);font-size:13px;">Loading legal framework...</p>
        </div>
      </div>"""
    html = html[:end] + "\n" + new_content + html[end:]

# 3. Add JS functions
script_close = html.rfind('</script>')
if script_close != -1:
    js_code = """
// === ATTRIBUTION TAB ===
async function loadAttributionTab(caseId) {
  try {
    const data = await apiGet('/api/inv-advance/attribution/' + caseId);
    if (!data.attributions || data.attributions.length === 0) {
      document.getElementById('attributionContent').innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No attribution data. Run advancement suite to generate.</p>';
      return;
    }

    let html_out = '<div style="margin-bottom:16px;font-weight:700;font-size:15px;color:var(--navy);"><i class="fa-solid fa-user-secret"></i> Suspect Attribution Matrix</div>';

    data.attributions.forEach(a => {
      const conf = a.confidence || 0;
      const confColor = conf >= 0.7 ? '#15803d' : conf >= 0.5 ? '#ca8a04' : '#dc2626';
      const confLabel = conf >= 0.7 ? 'HIGH' : conf >= 0.5 ? 'MEDIUM' : 'LOW';
      let factors = a.factors ? (typeof a.factors === 'string' ? JSON.parse(a.factors) : a.factors) : {};

      html_out += '<div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid ' + confColor + ';">';
      html_out += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
      html_out += '<div style="font-weight:700;font-size:14px;">' + (a.suspect || 'Unknown') + '</div>';
      html_out += '<div style="display:flex;align-items:center;gap:8px;">';
      html_out += '<div style="width:120px;height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;"><div style="height:100%;width:' + (conf*100) + '%;background:' + confColor + ';border-radius:4px;"></div></div>';
      html_out += '<div style="font-size:13px;font-weight:700;color:' + confColor + ';">' + (conf*100).toFixed(0) + '%</div>';
      html_out += '<div style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;background:' + (conf >= 0.7 ? '#dcfce7' : conf >= 0.5 ? '#fef3c7' : '#fee2e2') + ';color:' + confColor + ';">' + confLabel + '</div>';
      html_out += '</div></div>';

      html_out += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:12px;">';
      html_out += '<div><span style="color:var(--text-muted);">Evidence:</span> <strong>' + (a.evidence_count || 0) + '</strong></div>';
      html_out += '<div><span style="color:var(--text-muted);">Type:</span> <strong>' + (a.type || 'PERSON') + '</strong></div>';
      html_out += '<div><span style="color:var(--text-muted);">Phases:</span> <strong>' + (factors.phase_diversity || 0) + '</strong></div>';
      html_out += '</div>';

      if (factors.phases) {
        html_out += '<div style="margin-top:8px;font-size:11px;color:var(--text-muted);">Evidence phases: ' + factors.phases.join(', ') + '</div>';
      }
      if (factors.target_domain) {
        html_out += '<div style="margin-top:4px;font-size:11px;color:var(--text-muted);">Target: ' + factors.target_domain + '</div>';
      }

      html_out += '</div>';
    });

    document.getElementById('attributionContent').innerHTML = html_out;
  } catch (e) {
    document.getElementById('attributionContent').innerHTML = '<p style="color:var(--text-muted);">Error loading attribution data.</p>';
  }
}

// === LEGAL TAB ===
async function loadLegalTab(caseId) {
  try {
    const data = await apiGet('/api/inv-advance/legal/' + caseId);
    if (!data.frameworks || data.frameworks.length === 0) {
      document.getElementById('legalContent').innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No legal framework mapping. Run advancement suite to generate.</p>';
      return;
    }

    let html_out = '<div style="margin-bottom:16px;font-weight:700;font-size:15px;color:var(--navy);"><i class="fa-solid fa-gavel"></i> Legal Framework Mapping</div>';

    const fwColors = { FRAUD: '#2563eb', CYBERCRIME: '#7c3aed', MONEY_LAUNDERING: '#059669', HUMAN_TRAFFICKING: '#dc2626' };
    const fwIcons = { FRAUD: 'fa-mask', CYBERCRIME: 'fa-laptop-code', MONEY_LAUNDERING: 'fa-money-bill-transfer', HUMAN_TRAFFICKING: 'fa-people-arrows' };

    data.frameworks.forEach(fw => {
      const color = fwColors[fw.framework] || '#64748b';
      const icon = fwIcons[fw.framework] || 'fa-circle';
      let statutes = fw.statutes ? (typeof fw.statutes === 'string' ? JSON.parse(fw.statutes) : fw.statutes) : [];
      let missing = fw.missing ? (typeof fw.missing === 'string' ? JSON.parse(fw.missing) : fw.missing) : [];

      html_out += '<div style="background:#f8fafc;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid ' + color + ';">';
      html_out += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
      html_out += '<div style="font-weight:700;font-size:14px;color:' + color + '"><i class="fa-solid ' + icon + '"></i> ' + fw.framework.replace(/_/g, ' ') + '</div>';
      html_out += '<div style="font-size:11px;padding:3px 10px;border-radius:4px;background:' + (fw.applicable ? '#dcfce7' : '#fee2e2') + ';color:' + (fw.applicable ? '#15803d' : '#dc2626') + ';font-weight:600;">' + (fw.applicable ? 'APPLICABLE' : 'NOT APPLICABLE') + '</div>';
      html_out += '</div>';

      html_out += '<div style="font-size:12px;margin-bottom:8px;">';
      html_out += '<span style="color:var(--text-muted);">Evidence:</span> <strong>' + (fw.evidence_met || 0) + '</strong>/<strong>' + (fw.evidence_required || 0) + '</strong> required';
      html_out += '</div>';

      // List statutes
      statutes.forEach(st => {
        html_out += '<div style="margin-bottom:6px;padding:8px;background:white;border-radius:4px;font-size:12px;">';
        html_out += '<div style="font-weight:600;margin-bottom:2px;">' + (st.code || '') + '</div>';
        html_out += '<div style="color:var(--text-muted);font-size:11px;">' + (st.title || '') + '</div>';
        html_out += '<div style="margin-top:4px;font-size:11px;">Required elements: ' + (st.required_elements || []).join(', ') + '</div>';
        html_out += '</div>';
      });

      // Show missing elements
      if (missing.length > 0) {
        html_out += '<div style="margin-top:8px;padding:8px;background:#fef2f2;border-radius:4px;font-size:11px;">';
        html_out += '<div style="font-weight:600;color:#dc2626;margin-bottom:4px;"><i class="fa-solid fa-triangle-exclamation"></i> Missing evidence elements:</div>';
        missing.forEach(m => {
          html_out += '<div style="margin-bottom:2px;color:#991b1b;">' + m.element + ' <span style="color:#999;">(' + m.statute + ')</span></div>';
        });
        html_out += '</div>';
      } else {
        html_out += '<div style="margin-top:8px;padding:8px;background:#f0fdf4;border-radius:4px;font-size:12px;color:#15803d;font-weight:600;"><i class="fa-solid fa-check-circle"></i> All required evidence elements met</div>';
      }

      html_out += '</div>';
    });

    document.getElementById('legalContent').innerHTML = html_out;
  } catch (e) {
    document.getElementById('legalContent').innerHTML = '<p style="color:var(--text-muted);">Error loading legal framework data.</p>';
  }
}

"""
    html = html[:script_close] + js_code + html[script_close:]

# 4. Add loading calls in showCaseDetail
show_marker = "loadCustodyTab(data.case.case_id);"
if show_marker in html:
    html = html.replace(show_marker, show_marker + """
    loadAttributionTab(data.case.case_id);
    loadLegalTab(data.case.case_id);""")

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(html)
print("Dashboard patched: Attribution + Legal tabs added to case detail")

#!/usr/bin/env python3
"""
Add AI Engines tab to GFIN Investigator Workbench (the actual dashboard).
"""

with open("/gfin/investigator_workbench.html", "r") as f:
    html = f.read()

# 1. Add nav-item after Outreach
old_nav = '<div class="nav-item" onclick="switchView(\'outreach\')"><i class="fa-solid fa-bullhorn"></i> Outreach</div>'
new_nav = '''<div class="nav-item" onclick="switchView('outreach')"><i class="fa-solid fa-bullhorn"></i> Outreach</div>
      <div class="nav-item" onclick="switchView('aiEngines')"><i class="fa-solid fa-brain"></i> AI Engines</div>'''
html = html.replace(old_nav, new_nav, 1)
print("1. Added nav item")

# 2. Add view section — find the last view div and insert before the closing
# Find a good insertion point: after the last view div
# Look for the pattern that closes the main content area
# The views are <div class="view" id="view-xxx">...</div>
# Let's find the closing of the last view

# Find the settings/last view section
# Let's search for the closing of the main content
last_view_marker = '</div>\n  </div>\n</div>\n<script>'
# Actually let's find the </script> that starts the JS section
script_idx = html.find('<script>')
# Find the last </div> before <script>
pre_script = html[:script_idx]
last_div = pre_script.rfind('</div>')

# Find the view div that contains this closing
ai_view_html = '''<div class="view" id="view-aiEngines">
    <div class="page-header">
      <h1><i class="fa-solid fa-brain" style="color:var(--gold);"></i> AI Intelligence Engines</h1>
      <p style="color:var(--text-muted);font-size:14px;margin-top:4px;">Advanced anomaly detection, real-time graph analysis &amp; threat intelligence sharing</p>
    </div>

    <!-- Engine Status Cards -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:24px;">
      <div class="stat-card" style="padding:18px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <i class="fa-solid fa-chart-simple" style="font-size:22px;color:var(--navy);"></i>
          <div>
            <div style="font-weight:700;color:var(--navy);font-size:14px;">PyOD Anomaly Detection</div>
            <div style="font-size:11px;color:var(--text-muted);">Isolation Forest + KNN ensemble</div>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text-muted);" id="pyodStatus">Checking status...</div>
      </div>
      <div class="stat-card" style="padding:18px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <i class="fa-solid fa-diagram-project" style="font-size:22px;color:var(--navy);"></i>
          <div>
            <div style="font-weight:700;color:var(--navy);font-size:14px;">MIDAS Graph Detection</div>
            <div style="font-size:11px;color:var(--text-muted);">Count-Min Sketch streaming</div>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text-muted);" id="midasStatus">Checking status...</div>
      </div>
      <div class="stat-card" style="padding:18px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
          <i class="fa-solid fa-share-nodes" style="font-size:22px;color:var(--navy);"></i>
          <div>
            <div style="font-weight:700;color:var(--navy);font-size:14px;">MISP Threat Sharing</div>
            <div style="font-size:11px;color:var(--text-muted);">STIX 2.1 export &amp; inter-agency</div>
          </div>
        </div>
        <div style="font-size:12px;color:var(--text-muted);" id="mispStatus">Checking status...</div>
      </div>
    </div>

    <!-- PyOD Anomaly Cases Panel -->
    <div class="card" style="margin-bottom:20px;">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;">
        <h2 style="margin:0;font-size:16px;"><i class="fa-solid fa-chart-simple" style="color:var(--gold);margin-right:8px;"></i>Anomalous Cases</h2>
        <button class="btn btn-primary" onclick="loadAnomalyCases()" style="font-size:12px;padding:6px 14px;">
          <i class="fa-solid fa-rotate"></i> Run Detection
        </button>
      </div>
      <div id="anomalyCasesResults" style="padding:16px;font-size:13px;color:var(--text-muted);">
        Click "Run Detection" to analyze all cases for anomalies using Isolation Forest + KNN ensemble.
      </div>
    </div>

    <!-- Wallet Anomaly Panel -->
    <div class="card" style="margin-bottom:20px;">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;">
        <h2 style="margin:0;font-size:16px;"><i class="fa-solid fa-wallet" style="color:var(--gold);margin-right:8px;"></i>Wallet Anomaly Detection</h2>
        <button class="btn btn-primary" onclick="loadAnomalyWallets()" style="font-size:12px;padding:6px 14px;">
          <i class="fa-solid fa-rotate"></i> Scan Wallets
        </button>
      </div>
      <div id="anomalyWalletsResults" style="padding:16px;font-size:13px;color:var(--text-muted);">
        Click "Scan Wallets" to detect anomalous wallet transaction patterns from Telegram intelligence.
      </div>
    </div>

    <!-- MIDAS Panel -->
    <div class="card" style="margin-bottom:20px;">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;">
        <h2 style="margin:0;font-size:16px;"><i class="fa-solid fa-diagram-project" style="color:var(--gold);margin-right:8px;"></i>MIDAS Real-time Graph Anomaly Detection</h2>
        <div style="display:flex;gap:8px;">
          <button class="btn btn-primary" onclick="midasProcessTelegram()" style="font-size:12px;padding:6px 14px;">
            <i class="fa-solid fa-satellite"></i> Process Telegram
          </button>
          <button class="btn btn-primary" onclick="midasProcessEvidence()" style="font-size:12px;padding:6px 14px;">
            <i class="fa-solid fa-folder-open"></i> Process Evidence
          </button>
        </div>
      </div>
      <div id="midasResults" style="padding:16px;font-size:13px;color:var(--text-muted);">
        Click "Process Telegram" or "Process Evidence" to stream intelligence through MIDAS for real-time anomaly detection.
      </div>
    </div>

    <!-- MISP/STIX Panel -->
    <div class="card" style="margin-bottom:20px;">
      <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;">
        <h2 style="margin:0;font-size:16px;"><i class="fa-solid fa-share-nodes" style="color:var(--gold);margin-right:8px;"></i>Threat Intelligence Sharing (MISP / STIX)</h2>
        <button class="btn btn-primary" onclick="loadMispStatus()" style="font-size:12px;padding:6px 14px;">
          <i class="fa-solid fa-rotate"></i> Refresh
        </button>
      </div>
      <div id="mispResults" style="padding:16px;font-size:13px;color:var(--text-muted);">
        Click "Refresh" to check MISP integration and export STIX bundles.
      </div>
    </div>
  </div>

'''

# Insert before the last closing div before <script>
html = html[:last_div] + ai_view_html + html[last_div:]
print("2. Added view section")

# 3. Add switchView handler
old_switch = "else if (view === 'outreach') loadOutreach();"
new_switch = "else if (view === 'outreach') loadOutreach();\n  else if (view === 'aiEngines') loadAiEngines();"
html = html.replace(old_switch, new_switch, 1)
print("3. Added switchView handler")

# 4. Add JS functions before </script>
js_code = r'''
    // === AI ENGINES ===
    async function loadAiEngines() {
      loadAnomalyStatus();
      loadMidasStatus();
      loadMispStatus();
    }

    async function loadAnomalyStatus() {
      try {
        const data = await apiGet('/api/anomaly/status');
        document.getElementById('pyodStatus').innerHTML = '<span style="color:#22c55e;font-weight:600;">● Operational</span> — ' + data.algorithms.join(' + ');
      } catch(e) {
        document.getElementById('pyodStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
    }

    async function loadMidasStatus() {
      try {
        const data = await apiGet('/api/midas/status');
        const stats = data.stats || {};
        document.getElementById('midasStatus').innerHTML = '<span style="color:#22c55e;font-weight:600;">● Active</span> — ' + (stats.edges_processed || 0) + ' edges, ' + (stats.anomalies_detected || 0) + ' anomalies';
      } catch(e) {
        document.getElementById('midasStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
    }

    async function loadMispStatus() {
      try {
        const data = await apiGet('/api/misp/status');
        const stixBadge = data.stix_export ? '<span style="color:#22c55e;font-weight:600;">STIX 2.1 Ready</span>' : '<span style="color:#ef4444;">STIX Unavailable</span>';
        const mispBadge = data.misp_sharing ? '<span style="color:#22c55e;font-weight:600;">MISP Connected</span>' : '<span style="color:#f59e0b;font-weight:600;">MISP Not Configured</span>';
        document.getElementById('mispStatus').innerHTML = stixBadge + ' · ' + mispBadge;
      } catch(e) {
        document.getElementById('mispStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
    }

    async function loadAnomalyCases() {
      const el = document.getElementById('anomalyCasesResults');
      el.innerHTML = '<div style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:20px;color:var(--navy);"></i><br><span style="font-size:12px;margin-top:8px;display:inline-block;">Running Isolation Forest + KNN ensemble...</span></div>';
      try {
        const data = await apiGet('/api/anomaly/cases');
        if (!data.anomalies || data.anomalies.length === 0) {
          el.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);">No anomalies detected among ' + (data.total_cases || 0) + ' cases.</div>';
          return;
        }
        let html = '<div style="margin-bottom:10px;font-size:12px;color:var(--text-muted);">' + data.anomaly_count + ' anomalies found among ' + data.total_cases + ' cases</div>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr style="border-bottom:2px solid var(--navy);"><th style="text-align:left;padding:8px;">Score</th><th style="text-align:left;padding:8px;">Case ID</th><th style="text-align:left;padding:8px;">Reason</th><th style="text-align:left;padding:8px;">Flagged By</th></tr></thead><tbody>';
        data.anomalies.forEach(a => {
          const scoreColor = a.anomaly_score > 4 ? '#ef4444' : a.anomaly_score > 2 ? '#f59e0b' : '#6b7280';
          html += '<tr style="border-bottom:1px solid #eee;"><td style="padding:8px;"><span style="background:' + scoreColor + ';color:#fff;padding:2px 8px;border-radius:4px;font-weight:600;font-size:11px;">' + a.anomaly_score.toFixed(1) + '</span></td><td style="padding:8px;font-weight:600;color:var(--navy);">' + a.case_id + '</td><td style="padding:8px;color:var(--text-muted);">' + a.reason + '</td><td style="padding:8px;"><span style="font-size:10px;background:#e0e7ff;padding:2px 6px;border-radius:3px;">' + a.flagged_by + '</span></td></tr>';
        });
        html += '</tbody></table>';
        el.innerHTML = html;
      } catch(e) {
        el.innerHTML = '<div style="color:#ef4444;padding:12px;">Error: ' + e.message + '</div>';
      }
    }

    async function loadAnomalyWallets() {
      const el = document.getElementById('anomalyWalletsResults');
      el.innerHTML = '<div style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:20px;color:var(--navy);"></i><br><span style="font-size:12px;margin-top:8px;display:inline-block;">Scanning wallet patterns...</span></div>';
      try {
        const data = await apiGet('/api/anomaly/wallets');
        if (!data.anomalies || data.anomalies.length === 0) {
          el.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);">No anomalous wallets detected among ' + (data.total_wallets || 0) + ' tracked wallets.</div>';
          return;
        }
        let html = '<div style="margin-bottom:10px;font-size:12px;color:var(--text-muted);">' + data.anomaly_count + ' anomalous wallets out of ' + data.total_wallets + '</div>';
        html += '<div style="display:flex;flex-direction:column;gap:8px;">';
        data.anomalies.forEach(a => {
          html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:12px;display:flex;justify-content:space-between;align-items:center;"><div><div style="font-weight:600;font-size:13px;color:var(--navy);">' + a.wallet.substring(0, 20) + '...</div><div style="font-size:11px;color:var(--text-muted);margin-top:2px;">' + a.reason + '</div></div><div style="text-align:right;"><span style="background:#ef4444;color:#fff;padding:3px 10px;border-radius:4px;font-weight:600;font-size:11px;">Score: ' + a.anomaly_score.toFixed(1) + '</span></div></div>';
        });
        html += '</div>';
        el.innerHTML = html;
      } catch(e) {
        el.innerHTML = '<div style="color:#ef4444;padding:12px;">Error: ' + e.message + '</div>';
      }
    }

    async function midasProcessTelegram() {
      const el = document.getElementById('midasResults');
      el.innerHTML = '<div style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:20px;color:var(--navy);"></i><br><span style="font-size:12px;margin-top:8px;display:inline-block;">Streaming Telegram intelligence through MIDAS...</span></div>';
      try {
        const data = await apiPost('/api/midas/process/telegram', {});
        let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">';
        html += '<div style="background:#f0f4f8;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--navy);">' + (data.processed || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Edges Processed</div></div>';
        html += '<div style="background:#fef3f2;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#ef4444;">' + (data.anomalies || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Anomalies</div></div>';
        html += '<div style="background:#f0fdf4;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#22c55e;">' + ((data.anomaly_rate * 100) || 0).toFixed(1) + '%</div><div style="font-size:11px;color:var(--text-muted);">Anomaly Rate</div></div>';
        html += '</div>';
        const tops = (data.stats && data.stats.top_anomalies) || [];
        if (tops.length > 0) {
          html += '<div style="font-size:12px;font-weight:600;color:var(--navy);margin-bottom:8px;">Top Anomalies:</div><div style="display:flex;flex-direction:column;gap:6px;">';
          tops.slice(0, 10).forEach(a => {
            html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:10px;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:12px;"><span style="font-weight:600;color:var(--navy);">' + (a.src || '').substring(0, 25) + '</span> &rarr; <span style="color:var(--text-muted);">' + (a.dst || '').substring(0, 30) + '</span></div><span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + (a.score || 0).toFixed(1) + '</span></div>';
          });
          html += '</div>';
        }
        el.innerHTML = html;
        loadMidasStatus();
      } catch(e) {
        el.innerHTML = '<div style="color:#ef4444;padding:12px;">Error: ' + e.message + '</div>';
      }
    }

    async function midasProcessEvidence() {
      const el = document.getElementById('midasResults');
      el.innerHTML = '<div style="text-align:center;padding:20px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:20px;color:var(--navy);"></i><br><span style="font-size:12px;margin-top:8px;display:inline-block;">Streaming case evidence through MIDAS...</span></div>';
      try {
        const data = await apiPost('/api/midas/process/evidence', {});
        let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">';
        html += '<div style="background:#f0f4f8;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--navy);">' + (data.processed || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Edges Processed</div></div>';
        html += '<div style="background:#fef3f2;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#ef4444;">' + (data.anomalies || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Anomalies</div></div>';
        html += '<div style="background:#f0fdf4;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#22c55e;">' + ((data.anomaly_rate * 100) || 0).toFixed(1) + '%</div><div style="font-size:11px;color:var(--text-muted);">Anomaly Rate</div></div>';
        html += '</div>';
        const tops = (data.stats && data.stats.top_anomalies) || [];
        if (tops.length > 0) {
          html += '<div style="font-size:12px;font-weight:600;color:var(--navy);margin-bottom:8px;">Top Anomalies:</div><div style="display:flex;flex-direction:column;gap:6px;">';
          tops.slice(0, 10).forEach(a => {
            html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:10px;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:12px;"><span style="font-weight:600;color:var(--navy);">' + (a.src || '').substring(0, 25) + '</span> &rarr; <span style="color:var(--text-muted);">' + (a.dst || '').substring(0, 30) + '</span></div><span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + (a.score || 0).toFixed(1) + '</span></div>';
          });
          html += '</div>';
        }
        el.innerHTML = html;
        loadMidasStatus();
      } catch(e) {
        el.innerHTML = '<div style="color:#ef4444;padding:12px;">Error: ' + e.message + '</div>';
      }
    }

    async function loadMispStatus() {
      const el = document.getElementById('mispResults');
      try {
        const data = await apiGet('/api/misp/status');
        let html = '<div style="margin-bottom:16px;">';
        html += '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">';
        html += '<div style="background:' + (data.stix_export ? '#f0fdf4' : '#fef3f2') + ';padding:8px 16px;border-radius:6px;font-size:13px;"><i class="fa-solid fa-' + (data.stix_export ? 'check' : 'xmark') + '" style="color:' + (data.stix_export ? '#22c55e' : '#ef4444') + ';"></i> STIX 2.1 Export: ' + (data.stix_export ? 'Available' : 'Unavailable') + '</div>';
        html += '<div style="background:' + (data.misp_sharing ? '#f0fdf4' : '#fffbeb') + ';padding:8px 16px;border-radius:6px;font-size:13px;"><i class="fa-solid fa-' + (data.misp_sharing ? 'check' : 'circle-info') + '" style="color:' + (data.misp_sharing ? '#22c55e' : '#f59e0b') + ';"></i> MISP Instance: ' + (data.misp_sharing ? 'Connected' : 'Not configured (STIX export still works)') + '</div>';
        html += '</div>';
        html += '<div style="font-size:13px;font-weight:600;color:var(--navy);margin-bottom:8px;">Export STIX Bundle for a Case:</div>';
        html += '<div style="display:flex;gap:8px;flex-wrap:wrap;">';
        if (state.cases && state.cases.length > 0) {
          state.cases.slice(0, 10).forEach(c => {
            html += '<button onclick="exportStix(\'' + c.case_id + '\')" class="btn btn-outline" style="font-size:11px;padding:4px 12px;">' + c.case_id + '</button>';
          });
          if (state.cases.length > 10) {
            html += '<span style="font-size:11px;color:var(--text-muted);padding:6px;">+' + (state.cases.length - 10) + ' more...</span>';
          }
        } else {
          html += '<span style="font-size:12px;color:var(--text-muted);">No cases loaded. Go to Cases tab first.</span>';
        }
        html += '</div></div>';
        el.innerHTML = html;
      } catch(e) {
        el.innerHTML = '<div style="color:#ef4444;padding:12px;">Error: ' + e.message + '</div>';
      }
    }

    async function exportStix(caseId) {
      try {
        const data = await apiPost('/api/misp/export-stix/' + caseId, {});
        const objects = data.objects || [];
        const indicators = objects.filter(o => o.type === 'indicator');
        const reports = objects.filter(o => o.type === 'report');
        const observed = objects.filter(o => o.type === 'observed-data');
        alert('STIX 2.1 Bundle Exported\n\nCase: ' + caseId + '\nTotal Objects: ' + objects.length + '\n  - Indicators (IOCs): ' + indicators.length + '\n  - Reports: ' + reports.length + '\n  - Observed Data: ' + observed.length + '\n\nBundle ID: ' + (data.id || 'N/A') + '\n\nThe STIX bundle is ready for inter-agency sharing via MISP or any STIX-compatible platform.');
      } catch(e) {
        alert('STIX export failed: ' + e.message);
      }
    }
'''

last_script = html.rfind('</script>')
html = html[:last_script] + js_code + '\n' + html[last_script:]
print("4. Added JavaScript functions")

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(html)
print("Dashboard updated:", len(html), "bytes")

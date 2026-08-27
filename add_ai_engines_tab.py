#!/usr/bin/env python3
"""
Add AI Engines tab to GFIN Police Dashboard:
- PyOD Anomaly Detection panel
- MIDAS Real-time Graph Anomaly panel
- MISP/STIX Threat Intelligence Sharing panel
"""

with open("/gfin/police_dashboard_mobile.html", "r") as f:
    html = f.read()

# 1. Add sidebar item after Alerts
old_sidebar = '<a class="sidebar-item" data-view="alerts" onclick="switchView(\'alerts\')"><i class="fa-solid fa-bell"></i> Alerts</a>'
new_sidebar = '''<a class="sidebar-item" data-view="alerts" onclick="switchView('alerts')"><i class="fa-solid fa-bell"></i> Alerts</a>
        <a class="sidebar-item" data-view="aiEngines" onclick="switchView('aiEngines')"><i class="fa-solid fa-brain"></i> AI Engines</a>'''
html = html.replace(old_sidebar, new_sidebar, 1)
print("1. Added sidebar item")

# 2. Add view-section before the settings view
# Find the settings view section
settings_marker = 'id="viewSettings"'
settings_idx = html.find(settings_marker)
if settings_idx < 0:
    # Try to find the last view-section
    print("WARNING: Could not find settings view, searching for last view-section")
    # Find the closing of the last view-section before </div> closing the main content
    pass

# Find the viewSettings section start (search backwards for view-section)
view_settings_start = html.rfind('<section class="view-section"', 0, settings_idx)

ai_engines_section = '''<section class="view-section" id="viewAiEngines">
  <div class="content-header" style="margin-bottom:20px;">
    <h2 style="margin:0;font-size:20px;color:var(--navy);"><i class="fa-solid fa-brain" style="color:var(--gold);margin-right:8px;"></i>AI Intelligence Engines</h2>
    <p style="margin:4px 0 0 0;color:var(--text-muted);font-size:13px;">Advanced anomaly detection, real-time graph analysis &amp; threat intelligence sharing</p>
  </div>

  <!-- Engine Status Cards -->
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin-bottom:24px;" id="aiEngineStatusGrid">
    <div class="stat-card" style="padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <i class="fa-solid fa-chart-scatter" style="font-size:20px;color:var(--navy);"></i>
        <span style="font-weight:700;color:var(--navy);font-size:14px;">PyOD Anomaly Detection</span>
      </div>
      <div style="font-size:12px;color:var(--text-muted);" id="pyodStatus">Checking status...</div>
      <div style="margin-top:6px;font-size:11px;color:var(--text-muted);">Algorithms: Isolation Forest + KNN</div>
    </div>
    <div class="stat-card" style="padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <i class="fa-solid fa-diagram-project" style="font-size:20px;color:var(--navy);"></i>
        <span style="font-weight:700;color:var(--navy);font-size:14px;">MIDAS Graph Detection</span>
      </div>
      <div style="font-size:12px;color:var(--text-muted);" id="midasStatus">Checking status...</div>
      <div style="margin-top:6px;font-size:11px;color:var(--text-muted);">Algorithm: Count-Min Sketch (streaming)</div>
    </div>
    <div class="stat-card" style="padding:18px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
        <i class="fa-solid fa-share-nodes" style="font-size:20px;color:var(--navy);"></i>
        <span style="font-weight:700;color:var(--navy);font-size:14px;">MISP Threat Sharing</span>
      </div>
      <div style="font-size:12px;color:var(--text-muted);" id="mispStatus">Checking status...</div>
      <div style="margin-top:6px;font-size:11px;color:var(--text-muted);">STIX 2.1 export &amp; MISP inter-agency sharing</div>
    </div>
  </div>

  <!-- PyOD Anomaly Detection Panel -->
  <div style="background:var(--bg-card);border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h3 style="margin:0;font-size:16px;color:var(--navy);"><i class="fa-solid fa-chart-scatter" style="margin-right:8px;color:var(--gold);"></i>Anomalous Cases Detection</h3>
      <button onclick="loadAnomalyCases()" style="background:var(--navy);color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">
        <i class="fa-solid fa-rotate"></i> Run Detection
      </button>
    </div>
    <div id="anomalyCasesResults" style="font-size:13px;color:var(--text-muted);">
      Click "Run Detection" to analyze all cases for anomalies using Isolation Forest + KNN ensemble.
    </div>
  </div>

  <!-- Wallet Anomaly Panel -->
  <div style="background:var(--bg-card);border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h3 style="margin:0;font-size:16px;color:var(--navy);"><i class="fa-solid fa-wallet" style="margin-right:8px;color:var(--gold);"></i>Wallet Anomaly Detection</h3>
      <button onclick="loadAnomalyWallets()" style="background:var(--navy);color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">
        <i class="fa-solid fa-rotate"></i> Scan Wallets
      </button>
    </div>
    <div id="anomalyWalletsResults" style="font-size:13px;color:var(--text-muted);">
      Click "Scan Wallets" to detect anomalous wallet transaction patterns from Telegram intelligence.
    </div>
  </div>

  <!-- MIDAS Panel -->
  <div style="background:var(--bg-card);border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h3 style="margin:0;font-size:16px;color:var(--navy);"><i class="fa-solid fa-diagram-project" style="margin-right:8px;color:var(--gold);"></i>MIDAS Real-time Graph Anomaly Detection</h3>
      <div style="display:flex;gap:8px;">
        <button onclick="midasProcessTelegram()" style="background:var(--navy);color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">
          <i class="fa-solid fa-satellite"></i> Process Telegram
        </button>
        <button onclick="midasProcessEvidence()" style="background:var(--navy);color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">
          <i class="fa-solid fa-folder-open"></i> Process Evidence
        </button>
      </div>
    </div>
    <div id="midasResults" style="font-size:13px;color:var(--text-muted);">
      Click "Process Telegram" or "Process Evidence" to stream intelligence through MIDAS for real-time anomaly detection.
    </div>
  </div>

  <!-- MISP/STIX Panel -->
  <div style="background:var(--bg-card);border-radius:8px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h3 style="margin:0;font-size:16px;color:var(--navy);"><i class="fa-solid fa-share-nodes" style="margin-right:8px;color:var(--gold);"></i>Threat Intelligence Sharing (MISP / STIX)</h3>
      <button onclick="loadMispStatus()" style="background:var(--navy);color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:12px;font-weight:600;">
        <i class="fa-solid fa-rotate"></i> Refresh Status
      </button>
    </div>
    <div id="mispResults" style="font-size:13px;color:var(--text-muted);">
      Click "Refresh Status" to check MISP integration and export STIX bundles.
    </div>
  </div>
</section>

'''

# Insert before viewSettings
html = html[:view_settings_start] + ai_engines_section + html[view_settings_start:]
print("2. Added view section")

# 3. Add switchView handler
old_switch = "if (viewName === 'outreach') loadOutreach();"
new_switch = "if (viewName === 'outreach') loadOutreach();\n      if (viewName === 'aiEngines') loadAiEngines();"
html = html.replace(old_switch, new_switch, 1)
print("3. Added switchView handler")

# 4. Add JavaScript functions before </script>
js_code = '''
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
        document.getElementById('midasStatus').innerHTML = '<span style="color:#22c55e;font-weight:600;">● Active</span> — ' + (stats.edges_processed || 0) + ' edges processed, ' + (stats.anomalies_detected || 0) + ' anomalies';
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
        let html = '<div style="margin-bottom:10px;font-size:12px;color:var(--text-muted);">' + data.anomaly_count + ' anomalies found among ' + data.total_cases + ' cases (algorithms: ' + Object.keys(data.algorithms || {}).join(', ') + ')</div>';
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
            html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:10px;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:12px;"><span style="font-weight:600;color:var(--navy);">' + (a.src || '').substring(0, 25) + '</span> → <span style="color:var(--text-muted);">' + (a.dst || '').substring(0, 30) + '</span></div><div style="display:flex;gap:8px;align-items:center;"><span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + (a.score || 0).toFixed(1) + '</span></div></div>';
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
            html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:10px;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:12px;"><span style="font-weight:600;color:var(--navy);">' + (a.src || '').substring(0, 25) + '</span> → <span style="color:var(--text-muted);">' + (a.dst || '').substring(0, 30) + '</span></div><span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + (a.score || 0).toFixed(1) + '</span></div>';
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
            html += '<button onclick="exportStix(\\'' + c.case_id + '\\')" style="background:#f0f4f8;border:1px solid var(--navy);color:var(--navy);padding:6px 14px;border-radius:4px;cursor:pointer;font-size:11px;font-weight:600;">' + c.case_id + '</button>';
          });
          if (state.cases.length > 10) {
            html += '<span style="font-size:11px;color:var(--text-muted);padding:6px;">+' + (state.cases.length - 10) + ' more cases...</span>';
          }
        } else {
          html += '<span style="font-size:12px;color:var(--text-muted);">No cases loaded.</span>';
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
        alert('STIX 2.1 Bundle Exported\\n\\nCase: ' + caseId + '\\nTotal Objects: ' + objects.length + '\\n  - Indicators (IOCs): ' + indicators.length + '\\n  - Reports: ' + reports.length + '\\n  - Observed Data: ' + observed.length + '\\n\\nBundle ID: ' + (data.id || 'N/A') + '\\n\\nThe STIX bundle is ready for inter-agency sharing via MISP or any STIX-compatible platform.');
      } catch(e) {
        alert('STIX export failed: ' + e.message);
      }
    }

    // === END AI ENGINES ===
'''

# Insert before the last </script> tag
last_script = html.rfind('</script>')
html = html[:last_script] + js_code + '\n' + html[last_script:]
print("4. Added JavaScript functions")

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(html)
print("Dashboard updated successfully")
print("Total size:", len(html), "bytes")

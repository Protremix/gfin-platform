#!/usr/bin/env python3
"""Add MIDAS live anomalies panel and PyOD auto-load to the AI Engines tab"""

with open("/gfin/investigator_workbench.html", "r") as f:
    code = f.read()

# 1. Enhance loadMidasStatus to also show top anomalies
old_midas_status = """    async function loadMidasStatus() {
      try {
        const data = await apiGet('/api/midas/status');
        const stats = data.stats || {};
        document.getElementById('midasStatus').innerHTML = '<span style="color:#22c55e;font-weight:600;">● Active</span> — ' + (stats.edges_processed || 0) + ' edges, ' + (stats.anomalies_detected || 0) + ' anomalies';
      } catch(e) {
        document.getElementById('midasStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
    }"""

new_midas_status = """    async function loadMidasStatus() {
      try {
        const data = await apiGet('/api/midas/status');
        const stats = data.stats || {};
        document.getElementById('midasStatus').innerHTML = '<span style="color:#22c55e;font-weight:600;">● Active</span> — ' + (stats.edges_processed || 0) + ' edges, ' + (stats.anomalies_detected || 0) + ' anomalies';
        // Also update MIDAS results with live top anomalies
        const el = document.getElementById('midasResults');
        const tops = stats.top_anomalies || [];
        if (tops.length === 0) {
          el.innerHTML = '<div style="text-align:center;padding:16px;color:var(--text-muted);font-size:13px;">No anomalies detected yet. The spy feeds edges in real-time.</div>';
          return;
        }
        let html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">';
        html += '<div style="background:#f0f4f8;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:var(--navy);">' + (stats.edges_processed || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Edges Processed</div></div>';
        html += '<div style="background:#fef3f2;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#ef4444;">' + (stats.anomalies_detected || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Anomalies</div></div>';
        html += '<div style="background:#f0fdf4;padding:12px;border-radius:6px;text-align:center;"><div style="font-size:24px;font-weight:700;color:#22c55e;">' + (stats.recent_anomalies || 0) + '</div><div style="font-size:11px;color:var(--text-muted);">Recent (window)</div></div>';
        html += '</div>';
        html += '<div style="font-size:12px;font-weight:600;color:var(--navy);margin-bottom:8px;">Top Live Anomalies (auto-refreshed):</div>';
        html += '<div style="display:flex;flex-direction:column;gap:6px;">';
        tops.slice(0, 10).forEach(a => {
          const scoreColor = (a.score || 0) > 100 ? '#ef4444' : (a.score || 0) > 10 ? '#f59e0b' : '#6b7280';
          html += '<div style="border:1px solid #e5e7eb;border-radius:6px;padding:10px;display:flex;justify-content:space-between;align-items:center;"><div style="font-size:12px;"><span style="font-weight:600;color:var(--navy);">' + (a.src || '').substring(0, 25) + '</span> &rarr; <span style="color:var(--text-muted);">' + (a.dst || '').substring(0, 30) + '</span><div style="font-size:10px;color:var(--text-muted);margin-top:2px;">' + (a.reason || '') + '</div></div><span style="background:' + scoreColor + ';color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">' + (a.score || 0).toFixed(1) + '</span></div>';
        });
        html += '</div>';
        el.innerHTML = html;
      } catch(e) {
        document.getElementById('midasStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
    }"""

if old_midas_status in code:
    code = code.replace(old_midas_status, new_midas_status, 1)
    print("Enhanced loadMidasStatus with live top anomalies")
else:
    print("loadMidasStatus block not found")

# 2. Auto-load anomaly cases when AI Engines tab is opened
old_load_ai = """    async function loadAiEngines() {
      loadAnomalyStatus();
      loadMidasStatus();
      loadMispStatus();
    }"""

new_load_ai = """    async function loadAiEngines() {
      loadAnomalyStatus();
      loadMidasStatus();
      loadMispStatus();
      loadAnomalyCases();  // Auto-load PyOD results
    }"""

if old_load_ai in code:
    code = code.replace(old_load_ai, new_load_ai, 1)
    print("Added auto-load anomaly cases to loadAiEngines")
else:
    print("loadAiEngines block not found")

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(code)
print("Done")

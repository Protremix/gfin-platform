#!/usr/bin/env python3
"""Add OSINT Engines view to the GFIN Investigator Workbench"""

with open("/gfin/investigator_workbench.html", "r") as f:
    content = f.read()

# 1. Add nav item after Hunter
old_nav = '<div class="nav-item" onclick="switchView(\'hunter\')"><i class="fa-solid fa-crosshairs"></i> Hunter</div>'
new_nav = old_nav + '\n      <div class="nav-item" onclick="switchView(\'osint\')"><i class="fa-solid fa-satellite-dish"></i> OSINT Engines</div>'
content = content.replace(old_nav, new_nav)

# 2. Add the OSINT view section after the Hunter view section
# Find the end of view-hunter section
hunter_view_end = '<div id="view-domains" class="view">'
osint_view = '''<div id="view-osint" class="view" style="display:none">
        <h2 class="page-title">OSINT Intelligence Engines</h2>
        <p class="page-subtitle">Open-source intelligence tools integrated from GitHub — 200+ modules across 6 engines</p>
        
        <!-- Engine cards -->
        <div id="osintEnginesGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:24px"></div>
        
        <!-- Full scan interface -->
        <div class="chart-container" style="margin-bottom:24px">
          <h3 style="font-size:16px;font-weight:600;margin-bottom:12px"><i class="fa-solid fa-radar"></i> Full OSINT Scan</h3>
          <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px">Runs all engines in parallel against a target. Results are correlated and can be saved as a case.</p>
          <div style="display:flex;gap:8px;margin-bottom:12px">
            <input type="text" id="osintTarget" placeholder="Enter domain (e.g. example.com) or IP address" style="flex:1;padding:12px;border:2px solid var(--border);border-radius:var(--radius);font-size:14px">
            <select id="osintType" style="padding:12px;border:2px solid var(--border);border-radius:var(--radius);font-size:14px">
              <option value="domain">Domain</option>
              <option value="ip">IP Address</option>
            </select>
            <button class="btn btn-primary" onclick="runOsintFull()"><i class="fa-solid fa-satellite-dish"></i> Run Full Scan</button>
            <button class="btn btn-gold" onclick="runOsintHunt()"><i class="fa-solid fa-gavel"></i> Hunt & Save Case</button>
          </div>
          <div id="osintResults" style="margin-top:16px"></div>
        </div>
        
        <!-- Individual engine tools -->
        <div class="chart-container" style="margin-bottom:24px">
          <h3 style="font-size:16px;font-weight:600;margin-bottom:12px"><i class="fa-solid fa-toolbox"></i> Individual Engine Tools</h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-search"></i> SpiderFoot Scan</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">200+ OSINT modules — WHOIS, DNS, subdomains, SSL, blocklists</p>
              <input type="text" id="sfTarget" placeholder="domain or IP" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runSpiderfoot()">Run SpiderFoot</button>
              <div id="sfResults" style="margin-top:8px"></div>
            </div>
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-clone"></i> DNSTwist</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">Typo-squatting & lookalike domain detection</p>
              <input type="text" id="dtTarget" placeholder="domain" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runDnstwist()">Find Lookalikes</button>
              <div id="dtResults" style="margin-top:8px"></div>
            </div>
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-server"></i> Shodan Lookup</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">Ports, services, vulnerabilities for an IP</p>
              <input type="text" id="shTarget" placeholder="IP address" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runShodan()">Lookup IP</button>
              <div id="shResults" style="margin-top:8px"></div>
            </div>
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-shield-halved"></i> WAFW00F</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">Detect Web Application Firewalls</p>
              <input type="text" id="wafTarget" placeholder="domain" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runWafw00f()">Check WAF</button>
              <div id="wafResults" style="margin-top:8px"></div>
            </div>
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-network-wired"></i> DNSRecon</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">DNS enumeration & subdomain discovery</p>
              <input type="text" id="drTarget" placeholder="domain" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runDnsrecon()">Enumerate DNS</button>
              <div id="drResults" style="margin-top:8px"></div>
            </div>
            
            <div style="border:1px solid var(--border);border-radius:8px;padding:12px">
              <h4 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-id-card"></i> WHOIS Lookup</h4>
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">Full WHOIS record with privacy detection</p>
              <input type="text" id="whoisTarget" placeholder="domain" style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;font-size:13px;margin-bottom:8px">
              <button class="btn btn-primary" style="width:100%" onclick="runWhois()">Lookup WHOIS</button>
              <div id="whoisResults" style="margin-top:8px"></div>
            </div>
            
          </div>
        </div>
      </div>
      '''

content = content.replace(hunter_view_end, osint_view + "\n      " + hunter_view_end)

# 3. Add JavaScript functions before </script>
js_code = '''
// === OSINT ENGINE FUNCTIONS ===

async function loadOsintEngines() {
  try {
    const data = await apiGet('/api/osint/engines');
    const grid = document.getElementById('osintEnginesGrid');
    if (!grid) return;
    grid.innerHTML = data.engines.map(e => `
      <div class="chart-container" style="padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
          <h4 style="font-size:15px;font-weight:600">${e.name}</h4>
          <span style="font-size:11px;padding:2px 8px;border-radius:4px;background:var(--bg-accent);color:var(--text-muted)">${e.version}</span>
        </div>
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${e.description}</p>
        <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted)">
          <span><i class="fa-solid fa-cube"></i> ${e.modules} modules</span>
          <span><i class="fa-solid fa-key"></i> ${e.requires_api_key ? 'API Key' : 'Free'}</span>
          <span><i class="fa-solid fa-scale-balanced"></i> ${e.license}</span>
        </div>
      </div>
    `).join('');
  } catch(e) { console.error('OSINT engines load error:', e); }
}

async function runOsintFull() {
  const target = document.getElementById('osintTarget').value.trim();
  const type = document.getElementById('osintType').value;
  if (!target) return alert('Enter a target domain or IP');
  
  const el = document.getElementById('osintResults');
  el.innerHTML = '<div style="text-align:center;padding:40px"><i class="fa-solid fa-spinner fa-spin" style="font-size:32px;color:var(--primary)"></i><p style="margin-top:12px;color:var(--text-muted)">Running 5+ OSINT engines in parallel...</p></div>';
  
  try {
    const data = await apiPost('/api/osint/full', { target, target_type: type });
    let html = '<div style="background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">';
    html += '<div><h4 style="font-size:16px;font-weight:600">Scan ' + data.scan_id + '</h4>';
    html += '<p style="font-size:13px;color:var(--text-muted)">' + data.summary + '</p></div>';
    const confColor = data.confidence === 'HIGH' ? '#10b981' : data.confidence === 'MEDIUM' ? '#f59e0b' : '#6b7280';
    html += '<span style="padding:4px 12px;border-radius:6px;background:' + confColor + ';color:white;font-size:12px;font-weight:600">' + data.confidence + '</span>';
    html += '</div>';
    
    // Correlations
    if (data.correlations && data.correlations.length > 0) {
      html += '<h5 style="font-size:14px;font-weight:600;margin-bottom:8px"><i class="fa-solid fa-link"></i> Intelligence Correlations (' + data.correlations.length + ')</h5>';
      for (const c of data.correlations) {
        const sevColor = c.severity === 'HIGH' ? '#ef4444' : c.severity === 'MEDIUM' ? '#f59e0b' : '#6b7280';
        html += '<div style="padding:8px 12px;border-left:3px solid ' + sevColor + ';background:var(--bg-accent);border-radius:4px;margin-bottom:6px">';
        html += '<span style="font-size:11px;font-weight:600;color:' + sevColor + '">[' + c.severity + '] ' + c.type + '</span>';
        html += '<p style="font-size:13px;margin-top:2px">' + c.description + '</p></div>';
      }
    }
    
    // Engine results
    html += '<h5 style="font-size:14px;font-weight:600;margin:16px 0 8px"><i class="fa-solid fa-microchip"></i> Engine Results (' + Object.keys(data.engines).length + ')</h5>';
    html += '<table class="data-table"><thead><tr><th>Engine</th><th>Findings</th><th>Errors</th></tr></thead><tbody>';
    for (const [name, result] of Object.entries(data.engines)) {
      const hasF = result.findings ? (Array.isArray(result.findings) ? result.findings.length : Object.keys(result.findings).length) : 0;
      const errs = result.errors ? result.errors.length : 0;
      html += '<tr><td style="font-weight:600">' + name + '</td><td>' + hasF + '</td><td>' + (errs > 0 ? '<span style="color:#ef4444">' + errs + '</span>' : '0') + '</td></tr>';
    }
    html += '</tbody></table>';
    
    // WHOIS details
    if (data.engines.whois && data.engines.whois.findings && data.engines.whois.findings.registrar) {
      const w = data.engines.whois.findings;
      html += '<h5 style="font-size:14px;font-weight:600;margin:16px 0 8px"><i class="fa-solid fa-id-card"></i> WHOIS Details</h5>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">';
      html += '<div><strong>Registrar:</strong> ' + (w.registrar || '-') + '</div>';
      html += '<div><strong>Created:</strong> ' + (w.creation_date || '-') + '</div>';
      html += '<div><strong>Country:</strong> ' + (w.country || '-') + '</div>';
      html += '<div><strong>Privacy:</strong> ' + (w.privacy_protected ? '<span style="color:#f59e0b">YES</span>' : 'No') + '</div>';
      html += '<div><strong>Registrant:</strong> ' + (w.registrant_name || '-') + '</div>';
      html += '<div><strong>Org:</strong> ' + (w.registrant_org || '-') + '</div>';
      html += '</div>';
    }
    
    // DNSTwist lookalikes
    if (data.engines.dnstwist && data.engines.dnstwist.findings && data.engines.dnstwist.findings.length > 0) {
      html += '<h5 style="font-size:14px;font-weight:600;margin:16px 0 8px"><i class="fa-solid fa-clone"></i> Lookalike Domains (' + data.engines.dnstwist.findings.length + ')</h5>';
      html += '<table class="data-table"><thead><tr><th>Domain</th><th>Fuzzer</th><th>DNS A</th></tr></thead><tbody>';
      for (const f of data.engines.dnstwist.findings.slice(0, 10)) {
        html += '<tr><td style="font-family:monospace">' + (f.domain || '-') + '</td><td>' + (f.fuzzer || '-') + '</td><td>' + (f.dns_a && f.dns_a.length ? f.dns_a.join(', ') : '-') + '</td></tr>';
      }
      html += '</tbody></table>';
    }
    
    // Shodan
    if (data.engines.shodan && data.engines.shodan.findings && data.engines.shodan.findings.org) {
      const s = data.engines.shodan.findings;
      html += '<h5 style="font-size:14px;font-weight:600;margin:16px 0 8px"><i class="fa-solid fa-server"></i> Shodan/IP Info</h5>';
      html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">';
      html += '<div><strong>Org:</strong> ' + (s.org || '-') + '</div>';
      html += '<div><strong>City:</strong> ' + (s.city || '-') + '</div>';
      html += '<div><strong>Country:</strong> ' + (s.country || '-') + '</div>';
      html += '<div><strong>Location:</strong> ' + (s.location || '-') + '</div>';
      html += '</div>';
    }
    
    html += '</div>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:#ef4444;padding:16px">Error: ' + e.message + '</div>';
  }
}

async function runOsintHunt() {
  const target = document.getElementById('osintTarget').value.trim();
  if (!target) return alert('Enter a target domain');
  
  const el = document.getElementById('osintResults');
  el.innerHTML = '<div style="text-align:center;padding:40px"><i class="fa-solid fa-spinner fa-spin" style="font-size:32px;color:var(--primary)"></i><p style="margin-top:12px;color:var(--text-muted)">Running OSINT hunt and creating case...</p></div>';
  
  try {
    const data = await apiPost('/api/osint/hunt', { target });
    let html = '<div style="background:#ecfdf5;border:1px solid #10b981;border-radius:8px;padding:16px;margin-bottom:16px">';
    html += '<h4 style="font-size:16px;font-weight:600;color:#065f46"><i class="fa-solid fa-check-circle"></i> Case Created: ' + data.case_id + '</h4>';
    html += '<p style="font-size:13px;color:#064e3b;margin-top:4px">' + data.summary + '</p>';
    html += '<p style="font-size:13px;margin-top:8px">Confidence: <strong>' + data.confidence + '</strong> | Correlations: ' + data.correlations.length + '</p>';
    html += '<button class="btn btn-primary" style="margin-top:8px" onclick="openCase(\'' + data.case_id + '\')">Open Case</button>';
    html += '</div>';
    el.innerHTML = html;
  } catch(e) {
    el.innerHTML = '<div style="color:#ef4444;padding:16px">Error: ' + e.message + '</div>';
  }
}

async function runSpiderfoot() {
  const target = document.getElementById('sfTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('sfResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Running SpiderFoot (200+ modules)...</p>';
  try {
    const data = await apiPost('/api/osint/spiderfoot', { target });
    el.innerHTML = '<p style="font-size:12px;color:var(--text-muted)">Findings: ' + data.summary.total_findings + ' | Errors: ' + data.summary.errors + '</p>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

async function runDnstwist() {
  const target = document.getElementById('dtTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('dtResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Scanning for lookalikes...</p>';
  try {
    const data = await apiPost('/api/osint/dnstwist', { domain: target });
    const count = data.summary.total_lookalikes;
    el.innerHTML = '<p style="font-size:12px">' + count + ' lookalike domains found. ' + data.summary.with_dns_records + ' with active DNS.</p>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

async function runShodan() {
  const target = document.getElementById('shTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('shResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Looking up IP...</p>';
  try {
    const data = await apiPost('/api/osint/shodan', { ip: target });
    const f = data.findings;
    el.innerHTML = '<div style="font-size:12px"><strong>Org:</strong> ' + (f.org||'-') + ' | <strong>City:</strong> ' + (f.city||'-') + ' | <strong>Country:</strong> ' + (f.country||'-') + '</div>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

async function runWafw00f() {
  const target = document.getElementById('wafTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('wafResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Checking WAF...</p>';
  try {
    const data = await apiPost('/api/osint/wafw00f', { domain: target });
    const f = data.findings;
    el.innerHTML = '<p style="font-size:12px">WAF: ' + (f.waf_detected ? '<span style="color:#f59e0b">' + f.waf_name + '</span>' : '<span style="color:#10b981">None detected</span>') + '</p>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

async function runDnsrecon() {
  const target = document.getElementById('drTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('drResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Enumerating DNS...</p>';
  try {
    const data = await apiPost('/api/osint/dnsrecon', { domain: target });
    el.innerHTML = '<p style="font-size:12px">Records: ' + data.summary.total_records + ' | Subdomains: ' + data.summary.subdomains_found + '</p>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

async function runWhois() {
  const target = document.getElementById('whoisTarget').value.trim();
  if (!target) return;
  const el = document.getElementById('whoisResults');
  el.innerHTML = '<p style="color:var(--text-muted);font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Looking up WHOIS...</p>';
  try {
    const data = await apiPost('/api/osint/whois', { domain: target });
    const f = data.findings;
    el.innerHTML = '<div style="font-size:12px"><strong>Registrar:</strong> ' + (f.registrar||'-') + ' | <strong>Privacy:</strong> ' + (f.privacy_protected ? 'YES' : 'No') + ' | <strong>Created:</strong> ' + (f.creation_date||'-').substring(0,10) + '</div>';
  } catch(e) { el.innerHTML = '<p style="color:#ef4444;font-size:12px">Error: ' + e.message + '</p>'; }
}

'''

# Insert before the last </script> tag
content = content.replace('</script>', js_code + '</script>')

# 4. Update the switchView function to load OSINT engines
old_switch = 'case \'hunter\': loadHunter(); break;'
new_switch = '''case 'hunter': loadHunter(); break;
      case 'osint': loadOsintEngines(); break;'''

# Find and update the switchView function
if old_switch in content:
    content = content.replace(old_switch, new_switch)
else:
    # Find the switchView nav map and add osint
    old_navmap = 'const navMap = { dashboard: 0, cases: 1, intel: 2, evidence: 3, telegram: 4, hunter: 5, domains: 6, search: 7 };'
    new_navmap = 'const navMap = { dashboard: 0, cases: 1, intel: 2, evidence: 3, telegram: 4, hunter: 5, osint: 6, domains: 7, search: 8 };'
    content = content.replace(old_navmap, new_navmap)

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(content)
print("Added OSINT Engines view to dashboard")

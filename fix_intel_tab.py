#!/usr/bin/env python3
"""
Add Intelligence tab to police dashboard case detail view — CORRECT version.
Uses the dashboard's actual tab system (switchTab + tab-content).
"""

with open("/gfin/police_dashboard_mobile.html", "r") as f:
    content = f.read()

# First, remove the broken Intelligence tab additions from the previous script
# Remove the bad data-tab button
content = content.replace(
    '        <button class="detail-tab" data-tab="overview">Overview</button>\n        <button class="detail-tab" data-tab="intelligence">Intelligence</button>\n        <button class="detail-tab" data-tab="collaboration">Collaboration</button>\n        <button class="detail-tab" data-tab="evidence">Evidence</button>\n        <button class="detail-tab" data-tab="files">Files</button>\n        <button class="detail-tab" data-tab="routing">LEA Routing</button>\n        <button class="detail-tab" data-tab="audit">Audit Trail</button>',
    '        <button class="tab-btn active" onclick="switchTab(event,\'overview\')"><i class="fa-solid fa-circle-info"></i> Overview</button>\n        <button class="tab-btn" onclick="switchTab(event,\'intelligence\')"><i class="fa-solid fa-microscope"></i> Intelligence</button>\n        <button class="tab-btn" onclick="switchTab(event,\'collaboration\')"><i class="fa-solid fa-comments"></i> Collaboration</button>\n        <button class="tab-btn" onclick="switchTab(event,\'evidence\')"><i class="fa-solid fa-timeline"></i> Evidence</button>\n        <button class="tab-btn" onclick="switchTab(event,\'files\')"><i class="fa-solid fa-paperclip"></i> Files</button>\n        <button class="tab-btn" onclick="switchTab(event,\'routing\')"><i class="fa-solid fa-paper-plane"></i> LEA Routing</button>\n        <button class="tab-btn" onclick="switchTab(event,\'audit\')"><i class="fa-solid fa-list-check"></i> Audit Trail</button>'
)

# Remove the broken intelligence tab div if it exists
import re
content = re.sub(r'<!-- INTELLIGENCE TAB -->.*?<!-- COLLABORATION TAB -->', '<!-- COLLABORATION TAB -->', content, flags=re.DOTALL)

# Now add the Intelligence tab properly — after Overview tab, before Collaboration tab
old_collab = """        <!-- TAB: Collaboration -->"""

new_intel_tab = """        <!-- TAB: Intelligence -->
        <div id="tabIntelligence" class="tab-content">
          <div class="info-panel"><div class="card-title">Investigation Summary</div>
            <div id="intelSummary" style="font-size:13px;line-height:1.6;color:var(--text-secondary);margin-top:10px;"></div>
          </div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-fingerprint"></i> Digital Identifiers</div><div id="intelIdentifiers"></div></div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-location-dot"></i> Physical Locations</div><div id="intelLocations"></div></div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-coins"></i> Financial Trail</div><div id="intelFinancial"></div></div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-triangle-exclamation"></i> Risk Indicators</div><div id="intelRisk"></div></div>
          <div class="info-panel"><div class="card-title"><i class="fa-solid fa-globe"></i> Country Attribution</div><div id="intelCountries"></div></div>
        </div>

        <!-- TAB: Collaboration -->"""

content = content.replace(old_collab, new_intel_tab)

# Now add the renderIntelligence function at the end of renderCaseDetail
# Find the renderCaseDetail function's audit trail code and add after it
old_audit_end = """        </tbody></table>
      </div>;
    }"""

# Find the right spot — after the audit trail rendering in renderCaseDetail
# Look for the pattern that ends renderCaseDetail
old_render_close = """      document.getElementById('auditBody').innerHTML = audit.length ? audit.map(a => `
        <tr><td style="font-size:12px;">${formatDate(a.timestamp)}</td><td><strong>${a.action || '—'}</strong></td><td>${a.actor || '—'}</td><td>${a.tool || '—'}</td><td style="font-size:12px;">${a.query || ''} ${a.result || ''}</td></tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">No audit entries.</td></tr>';
    }"""

# Check if the renderIntelligence function was already added
if 'renderIntelligence' not in content:
    new_render_close = """      document.getElementById('auditBody').innerHTML = audit.length ? audit.map(a => `
        <tr><td style="font-size:12px;">${formatDate(a.timestamp)}</td><td><strong>${a.action || '—'}</strong></td><td>${a.actor || '—'}</td><td>${a.tool || '—'}</td><td style="font-size:12px;">${a.query || ''} ${a.result || ''}</td></tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">No audit entries.</td></tr>';

      // === INTELLIGENCE TAB ===
      renderIntelligence(c);
    }

    function renderIntelligence(c) {
      // Summary
      document.getElementById('intelSummary').textContent = c.summary || 'No summary available.';

      // Digital Identifiers
      const identifiers = c.digital_identifiers || [];
      const idEl = document.getElementById('intelIdentifiers');
      if (!identifiers || identifiers.length === 0) {
        idEl.innerHTML = '<div class="empty-state"><p>No digital identifiers collected.</p></div>';
      } else {
        const grouped = {};
        identifiers.forEach(d => {
          const t = d.type || 'OTHER';
          if (!grouped[t]) grouped[t] = [];
          grouped[t].push(d);
        });
        const typeIcons = {'IP':'fa-network-wired','NS':'fa-server','MX':'fa-envelope','HOSTING_PROVIDER':'fa-building','ASN':'fa-network-wired','REGISTRAR':'fa-id-card','SSL_ISSUER':'fa-lock','SSL_SAN':'fa-link','EMAIL':'fa-at','PHONE':'fa-phone','CRYPTO_WALLET':'fa-wallet','SOCIAL_ACCOUNT':'fa-share-nodes','COMPANY':'fa-building-columns','SPF':'fa-shield-halved','VERIFICATION_TOKEN':'fa-key'};
        const typeLabels = {'IP':'IP Addresses','NS':'Name Servers','MX':'Mail Servers','HOSTING_PROVIDER':'Hosting Providers','ASN':'ASNs','REGISTRAR':'Registrar','SSL_ISSUER':'SSL Certificate Issuer','SSL_SAN':'SSL SANs (Related Domains!)','EMAIL':'Email Addresses','PHONE':'Phone Numbers','CRYPTO_WALLET':'Crypto Wallets','SOCIAL_ACCOUNT':'Social Media Accounts','COMPANY':'Company Names','SPF':'Email Security (SPF)','VERIFICATION_TOKEN':'Platform Verification Tokens'};
        idEl.innerHTML = Object.entries(grouped).map(([type, items]) => `
          <div style="margin-bottom:14px;">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:6px;text-transform:uppercase;">
              <i class="fa-solid ${typeIcons[type]||'fa-circle'}"></i> ${typeLabels[type]||type} (${items.length})
            </div>
            ${items.map(d => `
              <div style="padding:6px 0;border-bottom:1px solid var(--border);">
                <div style="font-family:monospace;font-size:13px;word-break:break-all;">${d.value||'—'}</div>
                <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${d.context||''}</div>
              </div>
            `).join('')}
          </div>
        `).join('');
      }

      // Physical Locations
      const locations = c.physical_locations || [];
      const locEl = document.getElementById('intelLocations');
      if (!locations || locations.length === 0) {
        locEl.innerHTML = '<div class="empty-state"><p>No physical locations identified.</p></div>';
      } else {
        locEl.innerHTML = locations.map(loc => `
          <div style="margin-bottom:12px;padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="margin-bottom:6px;">
              <strong style="color:var(--navy);">${loc.city||'Unknown'}, ${loc.country||loc.country_code||''}</strong>
              ${loc.type === 'CONTENT_ADDRESS' ? '<span class="badge badge-low" style="font-size:10px;margin-left:6px;">FROM WEBSITE</span>' : '<span class="badge badge-high" style="font-size:10px;margin-left:6px;">SERVER</span>'}
            </div>
            ${loc.ip ? `<div style="font-size:12px;margin-bottom:3px;"><i class="fa-solid fa-network-wired"></i> IP: <span style="font-family:monospace;">${loc.ip}</span></div>` : ''}
            ${loc.isp ? `<div style="font-size:12px;margin-bottom:3px;"><i class="fa-solid fa-building"></i> ISP: ${loc.isp}</div>` : ''}
            ${loc.asn ? `<div style="font-size:12px;margin-bottom:3px;"><i class="fa-solid fa-sitemap"></i> ASN: ${loc.asn}</div>` : ''}
            ${loc.latitude && loc.longitude ? `<div style="font-size:12px;margin-bottom:3px;"><i class="fa-solid fa-location-dot"></i> ${loc.latitude}, ${loc.longitude} <a href="https://www.google.com/maps?q=${loc.latitude},${loc.longitude}" target="_blank" style="color:var(--navy);text-decoration:underline;font-size:11px;">Map &rarr;</a></div>` : ''}
            ${loc.address ? `<div style="font-size:12px;margin-bottom:3px;"><i class="fa-solid fa-map"></i> ${loc.address}</div>` : ''}
            ${loc.timezone ? `<div style="font-size:11px;color:var(--text-muted);"><i class="fa-solid fa-clock"></i> ${loc.timezone}</div>` : ''}
          </div>
        `).join('');
      }

      // Financial Trail
      const financial = c.financial_indicators || [];
      const finEl = document.getElementById('intelFinancial');
      if (!financial || financial.length === 0) {
        finEl.innerHTML = '<div class="empty-state"><p>No financial indicators found.</p></div>';
      } else {
        finEl.innerHTML = financial.map(f => `
          <div style="margin-bottom:10px;padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="margin-bottom:4px;"><i class="fa-solid fa-wallet" style="color:#c5a55a;"></i> <strong>${f.type||'Financial'}</strong></div>
            ${f.address ? `<div style="font-family:monospace;font-size:13px;word-break:break-all;">${f.address}</div>` : ''}
            ${f.context ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${f.context}</div>` : ''}
            ${f.address ? `<a href="https://www.blockchain.com/explorer/search?search=${f.address}" target="_blank" style="font-size:11px;color:var(--navy);text-decoration:underline;">Blockchain explorer &rarr;</a>` : ''}
          </div>
        `).join('');
      }

      // Risk Indicators
      const riskData = c.scam_indicators || [];
      const riskEl = document.getElementById('intelRisk');
      if (!riskData || riskData.length === 0) {
        riskEl.innerHTML = '<div class="empty-state"><p>No risk indicators recorded.</p></div>';
      } else {
        let indicators = [];
        riskData.forEach(ri => {
          if (ri && ri.indicators && Array.isArray(ri.indicators)) indicators = indicators.concat(ri.indicators);
          else if (ri && ri.indicator) indicators.push(ri);
        });
        if (indicators.length > 0) {
          riskEl.innerHTML = indicators.map(ind => `
            <div style="margin-bottom:8px;padding:10px;border-radius:6px;background:var(--bg-page);border-left:3px solid #c5a55a;">
              <div style="font-size:13px;"><strong>${ind.indicator||'Indicator'}</strong> ${ind.weight ? `<span class="badge badge-medium" style="font-size:10px;margin-left:6px;">+${ind.weight}</span>` : ''}</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">${ind.detail||''}</div>
            </div>
          `).join('');
        } else {
          riskEl.innerHTML = `<div style="font-size:13px;">${JSON.stringify(riskData).substring(0, 500)}</div>`;
        }
      }

      // Country Attribution
      const countries = c.affected_countries || [];
      const routed = c.routed_to_countries || [];
      document.getElementById('intelCountries').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Affected Countries</div>
            ${countries.length ? countries.map(cc => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-low" style="font-size:11px;">${cc}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">None identified</div>'}
          </div>
          <div style="padding:12px;border-radius:6px;background:var(--bg-page);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Routed To (LEA)</div>
            ${routed.length ? routed.map(r => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-high" style="font-size:11px;">${r}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">Not routed</div>'}
          </div>
        </div>
      `;
    }"""

    content = content.replace(old_render_close, new_render_close)
else:
    print("renderIntelligence already exists, skipping")

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(content)

print(f"Fixed Intelligence tab. File size: {len(content)} chars")

#!/usr/bin/env python3
"""
Add Intelligence tab to police dashboard case detail view.
Shows: digital identifiers, physical locations, financial trail, risk indicators,
investigation summary — all the data the autonomous hunter collects.
"""

with open("/gfin/police_dashboard_mobile.html", "r") as f:
    content = f.read()

# 1. Add Intelligence tab to the tab navigation
old_tabs = """        <button class="detail-tab" data-tab="overview">Overview</button>
        <button class="detail-tab" data-tab="collaboration">Collaboration</button>
        <button class="detail-tab" data-tab="evidence">Evidence</button>
        <button class="detail-tab" data-tab="files">Files</button>
        <button class="detail-tab" data-tab="routing">LEA Routing</button>
        <button class="detail-tab" data-tab="audit">Audit Trail</button>"""

new_tabs = """        <button class="detail-tab" data-tab="overview">Overview</button>
        <button class="detail-tab" data-tab="intelligence">Intelligence</button>
        <button class="detail-tab" data-tab="collaboration">Collaboration</button>
        <button class="detail-tab" data-tab="evidence">Evidence</button>
        <button class="detail-tab" data-tab="files">Files</button>
        <button class="detail-tab" data-tab="routing">LEA Routing</button>
        <button class="detail-tab" data-tab="audit">Audit Trail</button>"""

content = content.replace(old_tabs, new_tabs)

# 2. Add Intelligence tab content panel — find the overview panel and add after it
old_overview_end = """      <div id="detailGrid" class="info-grid"></div>
      <div id="linkedComplaints"></div>
    </div>
    <!-- COLLABORATION TAB -->"""

new_overview_end = """      <div id="detailGrid" class="info-grid"></div>
      <div id="linkedComplaints"></div>
    </div>

    <!-- INTELLIGENCE TAB -->
    <div id="tab-intelligence" class="detail-tab-content" style="display:none;">
      <div id="intelSummary" style="margin-bottom:16px;padding:16px;border-radius:8px;background:var(--bg-card);border:1px solid var(--border);"></div>

      <h4 style="margin:20px 0 10px;color:var(--navy);font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        <i class="fa-solid fa-fingerprint"></i> Digital Identifiers
      </h4>
      <div id="intelIdentifiers" style="margin-bottom:20px;"></div>

      <h4 style="margin:20px 0 10px;color:var(--navy);font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        <i class="fa-solid fa-location-dot"></i> Physical Locations
      </h4>
      <div id="intelLocations" style="margin-bottom:20px;"></div>

      <h4 style="margin:20px 0 10px;color:var(--navy);font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        <i class="fa-solid fa-coins"></i> Financial Trail
      </h4>
      <div id="intelFinancial" style="margin-bottom:20px;"></div>

      <h4 style="margin:20px 0 10px;color:var(--navy);font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        <i class="fa-solid fa-triangle-exclamation"></i> Risk Indicators
      </h4>
      <div id="intelRisk" style="margin-bottom:20px;"></div>

      <h4 style="margin:20px 0 10px;color:var(--navy);font-size:14px;text-transform:uppercase;letter-spacing:0.5px;">
        <i class="fa-solid fa-globe"></i> Country Attribution
      </h4>
      <div id="intelCountries" style="margin-bottom:20px;"></div>
    </div>
    <!-- COLLABORATION TAB -->"""

content = content.replace(old_overview_end, new_overview_end)

# 3. Add JavaScript to render intelligence data
# Find the end of renderCaseDetail function and add intelligence rendering before it closes
old_render_end = """      // Audit trail
      const audit = detail.audit_trail || [];
      document.getElementById('auditBody').innerHTML = audit.length ? audit.map(a => `
        <tr><td style="font-size:12px;">${formatDate(a.timestamp)}</td><td><strong>${a.action || '—'}</strong></td><td>${a.actor || '—'}</td><td>${a.tool || '—'}</td><td style="font-size:12px;">${a.query || ''} ${a.result || ''}</td></tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">No audit entries.</td></tr>';
    }"""

new_render_end = """      // Audit trail
      const audit = detail.audit_trail || [];
      document.getElementById('auditBody').innerHTML = audit.length ? audit.map(a => `
        <tr><td style="font-size:12px;">${formatDate(a.timestamp)}</td><td><strong>${a.action || '—'}</strong></td><td>${a.actor || '—'}</td><td>${a.tool || '—'}</td><td style="font-size:12px;">${a.query || ''} ${a.result || ''}</td></tr>
      `).join('') : '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">No audit entries.</td></tr>';

      // === INTELLIGENCE TAB ===
      renderIntelligence(c);
    }

    function renderIntelligence(c) {
      // Summary
      const summaryEl = document.getElementById('intelSummary');
      summaryEl.innerHTML = `
        <div style="font-size:13px;line-height:1.6;color:var(--text-secondary);">
          <strong style="color:var(--navy);font-size:14px;">Investigation Summary</strong><br>
          ${c.summary || 'No summary available.'}
        </div>
      `;

      // Digital Identifiers
      const identifiers = c.digital_identifiers || [];
      const idEl = document.getElementById('intelIdentifiers');
      if (identifiers.length === 0) {
        idEl.innerHTML = '<div class="empty-state"><p>No digital identifiers collected.</p></div>';
      } else {
        // Group by type
        const grouped = {};
        identifiers.forEach(d => {
          const t = d.type || 'OTHER';
          if (!grouped[t]) grouped[t] = [];
          grouped[t].push(d);
        });

        const typeIcons = {
          'IP': 'fa-network-wired', 'NS': 'fa-server', 'MX': 'fa-envelope',
          'HOSTING_PROVIDER': 'fa-building', 'ASN': 'fa-network-wired',
          'REGISTRAR': 'fa-id-card', 'SSL_ISSUER': 'fa-lock', 'SSL_SAN': 'fa-link',
          'EMAIL': 'fa-at', 'PHONE': 'fa-phone', 'CRYPTO_WALLET': 'fa-wallet',
          'SOCIAL_ACCOUNT': 'fa-share-nodes', 'COMPANY': 'fa-building-columns',
          'SPF': 'fa-shield-halved', 'VERIFICATION_TOKEN': 'fa-key',
        };
        const typeLabels = {
          'IP': 'IP Addresses', 'NS': 'Name Servers', 'MX': 'Mail Servers',
          'HOSTING_PROVIDER': 'Hosting Providers', 'ASN': 'ASNs',
          'REGISTRAR': 'Registrar', 'SSL_ISSUER': 'SSL Certificate Issuer',
          'SSL_SAN': 'SSL Certificate SANs (Related Domains!)', 'EMAIL': 'Email Addresses',
          'PHONE': 'Phone Numbers', 'CRYPTO_WALLET': 'Crypto Wallets',
          'SOCIAL_ACCOUNT': 'Social Media Accounts', 'COMPANY': 'Company Names',
          'SPF': 'Email Security (SPF)', 'VERIFICATION_TOKEN': 'Platform Verification Tokens',
        };

        idEl.innerHTML = Object.entries(grouped).map(([type, items]) => `
          <div style="margin-bottom:14px;padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">
              <i class="fa-solid ${typeIcons[type] || 'fa-circle'}"></i> ${typeLabels[type] || type} (${items.length})
            </div>
            ${items.map(d => `
              <div style="display:flex;justify-content:space-between;align-items:start;padding:6px 0;border-bottom:1px solid var(--border);">
                <div>
                  <div style="font-family:monospace;font-size:13px;color:var(--text-primary);word-break:break-all;">${d.value || '—'}</div>
                  <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${d.context || ''}</div>
                </div>
              </div>
            `).join('')}
          </div>
        `).join('');
      }

      // Physical Locations
      const locations = c.physical_locations || [];
      const locEl = document.getElementById('intelLocations');
      if (locations.length === 0) {
        locEl.innerHTML = '<div class="empty-state"><p>No physical locations identified.</p></div>';
      } else {
        locEl.innerHTML = locations.map(loc => `
          <div style="margin-bottom:12px;padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="font-size:20px;">${loc.country_code ? String.fromCodePoint(0x1F1E6 - 65 + loc.country_code.charCodeAt(0) - 65, 0x1F1E6 - 65 + loc.country_code.charCodeAt(1) - 65) : ''}</span>
              <strong style="color:var(--navy);">${loc.city || 'Unknown'}, ${loc.country || loc.country_code || ''}</strong>
              ${loc.type === 'CONTENT_ADDRESS' ? '<span class="badge badge-low" style="font-size:10px;">FROM WEBSITE</span>' : '<span class="badge badge-high" style="font-size:10px;">SERVER LOCATION</span>'}
            </div>
            ${loc.ip ? `<div style="font-size:12px;margin-bottom:4px;"><i class="fa-solid fa-network-wired"></i> IP: <span style="font-family:monospace;">${loc.ip}</span></div>` : ''}
            ${loc.isp ? `<div style="font-size:12px;margin-bottom:4px;"><i class="fa-solid fa-building"></i> ISP: ${loc.isp}</div>` : ''}
            ${loc.asn ? `<div style="font-size:12px;margin-bottom:4px;"><i class="fa-solid fa-network-wired"></i> ASN: ${loc.asn}</div>` : ''}
            ${loc.latitude && loc.longitude ? `<div style="font-size:12px;margin-bottom:4px;"><i class="fa-solid fa-location-dot"></i> Coordinates: ${loc.latitude}, ${loc.longitude} <a href="https://www.google.com/maps?q=${loc.latitude},${loc.longitude}" target="_blank" style="color:var(--navy);text-decoration:underline;font-size:11px;">View on Map</a></div>` : ''}
            ${loc.address ? `<div style="font-size:12px;margin-bottom:4px;"><i class="fa-solid fa-map"></i> Address: ${loc.address}</div>` : ''}
            ${loc.timezone ? `<div style="font-size:12px;color:var(--text-muted);"><i class="fa-solid fa-clock"></i> ${loc.timezone}</div>` : ''}
          </div>
        `).join('');
      }

      // Financial Trail
      const financial = c.financial_indicators || [];
      const finEl = document.getElementById('intelFinancial');
      if (financial.length === 0) {
        finEl.innerHTML = '<div class="empty-state"><p>No financial indicators found.</p></div>';
      } else {
        finEl.innerHTML = financial.map(f => `
          <div style="margin-bottom:10px;padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <i class="fa-solid fa-wallet" style="color:#c5a55a;"></i>
              <strong>${f.type || 'Financial Indicator'}</strong>
            </div>
            ${f.address ? `<div style="font-family:monospace;font-size:13px;word-break:break-all;color:var(--text-primary);">${f.address}</div>` : ''}
            ${f.context ? `<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${f.context}</div>` : ''}
            ${f.address ? `<a href="https://www.blockchain.com/explorer/search?search=${f.address}" target="_blank" style="font-size:11px;color:var(--navy);text-decoration:underline;">Check on blockchain explorer &rarr;</a>` : ''}
          </div>
        `).join('');
      }

      // Risk Indicators
      const riskIndicators = c.scam_indicators || [];
      const riskEl = document.getElementById('intelRisk');
      if (Array.isArray(riskIndicators) && riskIndicators.length > 0 && typeof riskIndicators[0] === 'object') {
        // Handle both array format and nested format
        let allIndicators = [];
        riskIndicators.forEach(ri => {
          if (Array.isArray(ri.indicators)) {
            allIndicators = allIndicators.concat(ri.indicators);
          } else if (ri.indicator) {
            allIndicators.push(ri);
          }
        });

        if (allIndicators.length === 0 && riskIndicators[0].risk_score !== undefined) {
          // It's a scam analysis object, not indicators array
          riskEl.innerHTML = `
            <div style="padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
              <div style="font-size:13px;"><strong>Risk Score:</strong> ${riskIndicators[0].risk_score}/100 (${riskIndicators[0].risk_level})</div>
              ${riskIndicators[0].categories ? `<div style="font-size:12px;margin-top:4px;"><strong>Categories:</strong> ${(riskIndicators[0].categories || []).join(', ')}</div>` : ''}
              ${riskIndicators[0].indicators ? `<div style="margin-top:8px;">${riskIndicators[0].indicators.map(i => `<div style="font-size:12px;padding:4px 0;">&bull; ${i.indicator || i}: ${i.detail || ''}</div>`).join('')}</div>` : ''}
            </div>
          `;
        } else {
          riskEl.innerHTML = allIndicators.map(ind => `
            <div style="margin-bottom:8px;padding:10px;border-radius:6px;background:var(--bg-card);border-left:3px solid #c5a55a;">
              <div style="font-size:13px;"><strong>${ind.indicator || 'Indicator'}</strong> ${ind.weight ? `<span class="badge badge-medium" style="font-size:10px;margin-left:6px;">+${ind.weight} pts</span>` : ''}</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">${ind.detail || ''}</div>
            </div>
          `).join('');
        }
      } else {
        riskEl.innerHTML = '<div class="empty-state"><p>No risk indicators recorded.</p></div>';
      }

      // Country Attribution
      const countries = c.affected_countries || [];
      const routed = c.routed_to_countries || [];
      const cEl = document.getElementById('intelCountries');
      cEl.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div style="padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Affected Countries</div>
            ${countries.length ? countries.map(cc => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-low" style="font-size:11px;">${cc}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">None identified</div>'}
          </div>
          <div style="padding:12px;border-radius:6px;background:var(--bg-card);border:1px solid var(--border);">
            <div style="font-weight:600;font-size:12px;color:var(--navy);margin-bottom:8px;text-transform:uppercase;">Routed To (LEA)</div>
            ${routed.length ? routed.map(r => `<div style="font-size:13px;padding:4px 0;"><span class="badge badge-high" style="font-size:11px;">${r}</span></div>`).join('') : '<div style="color:var(--text-muted);font-size:12px;">Not routed</div>'}
          </div>
        </div>
      `;
    }"""

content = content.replace(old_render_end, new_render_end)

# 4. Make sure tab switching handles the new intelligence tab
# Check if the tab switching code handles generic data-tab attributes
# The existing code should handle it if it uses querySelectorAll('[data-tab]')

with open("/gfin/police_dashboard_mobile.html", "w") as f:
    f.write(content)

print(f"Added Intelligence tab to dashboard. File size: {len(content)} chars")

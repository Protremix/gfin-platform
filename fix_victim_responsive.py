#!/usr/bin/env python3
"""Add comprehensive responsive CSS to the victim portal."""

content = open("/gfin/victim_portal_i18n.html").read()

# Comprehensive responsive CSS to inject before </style>
responsive_css = """
        /* === TABLET RESPONSIVE === */
        @media (max-width: 768px) {
            .header-container { flex-direction: column; gap: 10px; padding: 12px 16px; }
            .branding { justify-content: center; }
            .brand-text h1 { font-size: 22px; }
            .brand-text p { font-size: 11px; }
            .logo-shield { width: 44px; height: 44px; }
            .lang-selector-bar { flex-wrap: wrap; justify-content: center; gap: 4px; }
            .lang-selector-bar button { padding: 4px 10px; font-size: 12px; }
            .button-bar { flex-direction: column; gap: 8px; width: 100%; }
            .button-bar .btn { width: 100%; }
            .card { padding: 16px; border-radius: 8px; margin: 8px 0; }
            .form-section-header h2 { font-size: 18px; }
            .form-section-header p { font-size: 13px; }
            .security-banner { font-size: 12px; padding: 8px 12px; text-align: center; }
            .step-circle { width: 28px; height: 28px; font-size: 13px; }
            .step-label { font-size: 11px; }
            .step-item { gap: 4px; }
            .tab-btn { padding: 8px 14px; font-size: 13px; }
            .notice-box { padding: 12px; font-size: 13px; }
            .case-ref-card { padding: 14px; }
            .case-ref-code { font-size: 16px; }
            .file-dropzone { padding: 20px 14px; }
            .success-box { padding: 20px 16px; }
            .success-icon { font-size: 36px; }
        }

        /* === PHONE RESPONSIVE === */
        @media (max-width: 480px) {
            body { font-size: 14px; }
            .header-container { padding: 10px 12px; }
            .brand-text h1 { font-size: 18px; letter-spacing: -0.3px; }
            .brand-text p { font-size: 10px; letter-spacing: 0.5px; }
            .logo-shield { width: 38px; height: 38px; }
            .lang-selector-bar { gap: 2px; }
            .lang-selector-bar button { padding: 3px 8px; font-size: 11px; }
            .card { padding: 14px 12px; border-radius: 6px; }
            .form-section-header { margin-bottom: 12px; }
            .form-section-header h2 { font-size: 16px; }
            .form-section-header p { font-size: 12px; }
            .form-group { margin-bottom: 12px; }
            .form-group label { font-size: 13px; }
            .form-group input,
            .form-group select,
            .form-group textarea { font-size: 15px; padding: 10px 12px; }
            .btn { padding: 10px 16px; font-size: 14px; }
            .button-bar { gap: 6px; }
            .button-bar .btn { padding: 12px; font-size: 14px; }
            .security-banner { font-size: 11px; padding: 6px 10px; }
            .step-circle { width: 24px; height: 24px; font-size: 11px; }
            .step-label { font-size: 10px; }
            .step-item { min-width: 50px; }
            .tab-btn { padding: 6px 10px; font-size: 12px; }
            .notice-box { padding: 10px 8px; font-size: 12px; border-radius: 6px; }
            .case-ref-card { padding: 12px 10px; }
            .case-ref-code { font-size: 14px; }
            .file-dropzone { padding: 16px 10px; font-size: 13px; border-radius: 6px; }
            .file-list { font-size: 13px; }
            .success-box { padding: 16px 12px; }
            .success-icon { font-size: 30px; }
            .error-message { font-size: 13px; padding: 8px 10px; }
            /* Grid columns to single */
            div[style*="grid-template-columns: 1fr 1fr"] {
                grid-template-columns: 1fr !important;
            }
            /* Reduce max-widths */
            .card[style*="max-width"] { max-width: 100% !important; }
        }

        /* === SMALL PHONE === */
        @media (max-width: 360px) {
            .brand-text h1 { font-size: 16px; }
            .brand-text p { font-size: 9px; }
            .logo-shield { width: 34px; height: 34px; }
            .step-label { display: none; }
            .step-item { min-width: auto; }
            .lang-selector-bar button { padding: 2px 6px; font-size: 10px; }
            .tab-btn { padding: 5px 8px; font-size: 11px; }
            .btn { padding: 10px 12px; font-size: 13px; }
            .card { padding: 12px 10px; }
        }
"""

# Insert before </style>
content = content.replace("    </style>", responsive_css + "    </style>", 1)
open("/gfin/victim_portal_i18n.html", "w").write(content)
print("Responsive CSS injected into victim portal")
print(f"File size: {len(content)} bytes")

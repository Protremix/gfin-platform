#!/usr/bin/env python3
"""Add comprehensive mobile responsive CSS to GFIN homepage."""

content = open("/gfin/gfin_homepage.html").read()

# Find the existing media query and replace it with comprehensive breakpoints
old_media = """        @media (max-width: 768px) {
            .nav { display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; flex-direction: column; padding: 10px; box-shadow: var(--gov-shadow-lg); }
            .nav.open { display: flex; }
            .mobile-menu-btn { display: block; }
            .hero-grid { grid-template-columns: 1fr; gap: 30px; }
            .hero h2 { font-size: 28px; }
            .hero-stats { grid-template-columns: repeat(2, 1fr); }
            .steps-grid { grid-template-columns: 1fr; }
            .services-grid { grid-template-columns: 1fr; }
            .stats-bar .container { grid-template-columns: repeat(2, 1fr); }
            .awareness-grid { grid-template-columns: 1fr; }
            .footer-grid { grid-template-columns: 1fr; }
            .scam-check-input { flex-direction: column; }
        }
    </style>"""

new_media = """        /* ===== TABLET (max-width: 768px) ===== */
        @media (max-width: 768px) {
            .nav { display: none; position: absolute; top: 100%; left: 0; right: 0; background: white; flex-direction: column; padding: 10px; box-shadow: var(--gov-shadow-lg); z-index: 100; }
            .nav.open { display: flex; }
            .nav a { padding: 12px 16px; font-size: 15px; }
            .mobile-menu-btn { display: block; }
            .top-bar { font-size: 11px; }
            .top-bar .container { flex-wrap: wrap; gap: 4px; }
            .top-bar a { font-size: 11px; padding: 2px 6px; }
            .header .container { padding: 10px 16px; }
            .logo-seal { width: 42px; height: 42px; }
            .logo-text h1 { font-size: 16px; }
            .logo-text p { font-size: 9px; }
            .hero { padding: 40px 0; }
            .hero-grid { grid-template-columns: 1fr; gap: 30px; }
            .hero h2 { font-size: 28px; }
            .hero p { font-size: 15px; }
            .hero-stats { grid-template-columns: repeat(2, 1fr); }
            .hero-stat-card { padding: 16px; }
            .hero-stat-card .number { font-size: 26px; }
            .hero-stat-card .label { font-size: 11px; }
            .hero-actions { gap: 10px; }
            .btn-primary, .btn-secondary { padding: 12px 22px; font-size: 14px; }
            section { padding: 40px 0; }
            .container { padding: 0 16px; }
            .section-header h3 { font-size: 22px; }
            .section-header p { font-size: 14px; }
            .steps-grid { grid-template-columns: repeat(2, 1fr); gap: 16px; }
            .services-grid { grid-template-columns: 1fr; gap: 16px; }
            .stats-bar .container { grid-template-columns: repeat(2, 1fr); gap: 16px; }
            .stats-bar .stat-item .number { font-size: 28px; }
            .awareness-grid { grid-template-columns: 1fr; gap: 12px; }
            .partners-grid { gap: 20px; }
            .partner-badge .badge-icon { width: 48px; height: 48px; font-size: 22px; }
            .footer-grid { grid-template-columns: 1fr 1fr; gap: 20px; }
            .footer-bottom { flex-direction: column; gap: 8px; text-align: center; }
            .scam-check-input { flex-direction: column; }
            .scam-check-input input { width: 100%; }
        }
        
        /* ===== MOBILE (max-width: 480px) ===== */
        @media (max-width: 480px) {
            .top-bar .container { justify-content: center; }
            .top-bar > .container > div:first-child { font-size: 10px; }
            .top-bar a { font-size: 10px; }
            .header .container { padding: 8px 12px; }
            .logo-seal { width: 38px; height: 38px; }
            .logo-text h1 { font-size: 15px; }
            .logo-text p { font-size: 8px; letter-spacing: 0.5px; }
            .mobile-menu-btn { font-size: 20px; }
            .hero { padding: 30px 0; }
            .hero-badge { font-size: 10px; padding: 4px 10px; margin-bottom: 16px; }
            .hero h2 { font-size: 22px; line-height: 1.2; }
            .hero p { font-size: 14px; line-height: 1.6; margin-bottom: 20px; }
            .hero-stats { grid-template-columns: 1fr 1fr; gap: 10px; }
            .hero-stat-card { padding: 14px 10px; }
            .hero-stat-card .number { font-size: 22px; }
            .hero-stat-card .label { font-size: 10px; }
            .hero-actions { flex-direction: column; gap: 10px; }
            .btn-primary, .btn-secondary { width: 100%; justify-content: center; padding: 12px 20px; font-size: 14px; }
            section { padding: 32px 0; }
            .container { padding: 0 14px; }
            .section-header .eyebrow { font-size: 11px; }
            .section-header h3 { font-size: 19px; }
            .section-header p { font-size: 13px; }
            .steps-grid { grid-template-columns: 1fr; gap: 14px; }
            .step-card { padding: 16px; }
            .step-card .step-number { width: 36px; height: 36px; font-size: 14px; }
            .services-grid { grid-template-columns: 1fr; gap: 14px; }
            .service-card { padding: 16px; }
            .service-icon { width: 42px; height: 42px; font-size: 20px; }
            .stats-bar .container { grid-template-columns: 1fr 1fr; gap: 12px; }
            .stats-bar .stat-item .number { font-size: 24px; }
            .stats-bar .stat-item .label { font-size: 11px; }
            .awareness-grid { grid-template-columns: 1fr; gap: 10px; }
            .awareness-card { padding: 14px; gap: 10px; }
            .partners-grid { gap: 16px; }
            .partner-badge .badge-icon { width: 42px; height: 42px; font-size: 18px; }
            .footer-grid { grid-template-columns: 1fr; gap: 20px; }
            .footer-bottom { font-size: 11px; }
            .scam-check-input { gap: 8px; }
            .scam-check-input input { font-size: 14px; padding: 12px 14px; }
            .scam-check-input button { width: 100%; padding: 12px; font-size: 14px; }
        }
        
        /* ===== EXTRA SMALL (max-width: 360px) ===== */
        @media (max-width: 360px) {
            .hero h2 { font-size: 19px; }
            .hero p { font-size: 13px; }
            .logo-text h1 { font-size: 14px; }
            .logo-text p { font-size: 7px; }
            .hero-stat-card .number { font-size: 18px; }
            .section-header h3 { font-size: 17px; }
        }
    </style>"""

content = content.replace(old_media, new_media)

# Also add touch-friendly improvements
content = content.replace(
    "* { margin: 0; padding: 0; box-sizing: border-box; }",
    "* { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }"
)

open("/gfin/gfin_homepage.html", "w").write(content)
print(f"Homepage updated: {len(content)} bytes")
print("Added: 768px tablet, 480px mobile, 360px small phone breakpoints")

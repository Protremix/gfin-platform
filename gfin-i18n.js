/**
 * GFIN Shared i18n Translation System
 * Supports 7 languages: EN, ES, DE, FR, AR, ZH, HI
 * Auto-detects language from URL ?lang= parameter or localStorage
 */
(function() {
  'use strict';

  const GFIN_i18n = {
    currentLang: 'en',

    translations: {
      en: {
        'nav_home': 'Home', 'nav_report': 'Report a Scam', 'nav_scam_db': 'Scam Database',
        'nav_awareness': 'Awareness', 'nav_about': 'About', 'nav_police': 'Police Login',
        'hero_badge': '🛡️ Official Government-Grade Fraud Intelligence Platform',
        'hero_title': 'Protecting Citizens from ', 'hero_title_highlight': 'Fraud Worldwide',
        'hero_desc': 'The Global Fraud Intelligence Network connects law enforcement agencies across 189 countries to detect, investigate, and prevent financial fraud — from crypto scams to cross-border impersonation networks. Report a scam in 17 seconds.',
        'hero_btn_report': '📝 Report a Scam', 'hero_btn_check': '🔍 Check a Website',
        'stat_countries': 'Countries Connected', 'stat_providers': 'Intelligence Providers',
        'stat_categories': 'Scam Categories Tracked', 'stat_monitoring': 'Continuous Monitoring',
        'how_title': 'How GFIN Works', 'how_subtitle': 'From Complaint to Investigation in 17 Seconds',
        'how_desc': 'Our automated pipeline detects scams, collects evidence, and routes cases to the correct national authorities — automatically.',
        'step1_title': 'Report a Scam', 'step1_desc': 'Victims file complaints through our secure portal in any of 7 languages. No technical knowledge required.',
        'step2_title': 'AI-Powered Detection', 'step2_desc': 'Our deterministic engine analyzes 300+ scam patterns across 15 categories to identify the scam type and risk level.',
        'step3_title': 'Evidence Collection', 'step3_desc': '72 intelligence providers automatically gather evidence — domains, wallets, IP addresses, hosting info, and more.',
        'step4_title': 'Country Routing', 'step4_desc': 'Cases are automatically routed to the correct national cybercrime authority, Interpol, and Europol (for EU countries).',
        'services_title': 'Platform Services', 'services_subtitle': 'Comprehensive Fraud Intelligence Capabilities',
        'service1_title': 'Complaint Filing', 'service1_desc': 'Secure multi-language portal for victims to report fraud with file uploads and automatic case ID assignment.',
        'service2_title': 'Scam Detection Engine', 'service2_desc': 'Deterministic v3.0 engine with 300+ patterns across 15 categories. Multi-language detection (EN, ES, DE, FR).',
        'service3_title': 'Crypto Tracing', 'service3_desc': 'Multi-chain cryptocurrency tracing across 10 wallet types and 9 USDT chains. Follow the money.',
        'service4_title': 'Intelligence Playbook', 'service4_desc': '13 entity types traced from domain to physical address. Evidence chain with SHA-256 hashing.',
        'service5_title': 'Country Routing', 'service5_desc': 'Automated routing to 189 national cybercrime authorities, Interpol, and Europol.',
        'service6_title': 'Telegram Alerts', 'service6_desc': 'Public anonymized scam alerts and 12-type awareness broadcasts via @GFINofficialbot.',
        'partners_eyebrow': 'International Cooperation', 'partners_title': 'Connected to Global Law Enforcement',
        'partners_desc': 'GFIN routes intelligence to national cybercrime units, Interpol, and Europol — ensuring cross-border cooperation across 189 countries.',
        'awareness_eyebrow': 'Public Awareness', 'awareness_title': 'Know the Signs — Protect Yourself',
        'awareness_desc': 'GFIN tracks 15 categories of fraud. Learn how to recognize and avoid each type.',
        'awareness_recovery': 'Recovery Scams', 'awareness_recovery_desc': 'Someone promises to recover money already lost to scams. They are scammers targeting previous victims.',
        'awareness_romance': 'Romance Scams', 'awareness_romance_desc': 'Fake online relationships that end in requests for money, crypto, or gifts.',
        'awareness_investment': 'Investment Fraud', 'awareness_investment_desc': 'Fake trading platforms promising high returns. Your money disappears.',
        'awareness_phishing': 'Phishing', 'awareness_phishing_desc': 'Fake emails and websites stealing your passwords and banking details.',
        'awareness_impersonation': 'Impersonation', 'awareness_impersonation_desc': 'Criminals posing as police, government, or tech support to steal money.',
        'awareness_crypto': 'Crypto Fraud', 'awareness_crypto_desc': 'Fake exchanges, rug pulls, and Ponzi schemes in the crypto space.',
        'awareness_tech': 'Tech Support', 'awareness_tech_desc': 'Fake Microsoft/Apple calls to gain remote access to your computer.',
        'awareness_advance': 'Advance Fee', 'awareness_advance_desc': 'Pay a fee upfront to unlock a prize, loan, or inheritance that does not exist.',
        'about_hero_desc': 'The Global Fraud Intelligence Network connects law enforcement agencies across 189 countries to detect, investigate, and prevent financial fraud.',
        'about_mission_desc': 'GFIN bridges the gap between citizens, national cybercrime units, and international bodies.',
        'about_mission_detect': 'Detect',
        'about_mission_detect_desc': 'Our deterministic engine analyzes 300+ scam patterns across 15 categories in multiple languages.',
        'about_mission_investigate': 'Investigate',
        'about_mission_investigate_desc': '72 intelligence providers automatically gather evidence.',
        'about_mission_prevent': 'Prevent',
        'about_mission_prevent_desc': 'Public awareness broadcasts and real-time Telegram alerts keep citizens informed.',
        'about_tech_desc': 'Built on a zero-trust security architecture with end-to-end encryption and GDPR-compliant data handling.',
        'cta_title': 'Report a Scam in 17 Seconds', 'cta_desc': 'File a complaint now. Our automated system starts investigating immediately.',
        'cta_btn': 'File a Complaint', 'cta_btn2': 'Check a Website',
        'footer_brand': 'GFIN — Global Fraud Intelligence Network',
        'footer_desc': 'An international law enforcement platform for cross-border fraud detection, investigation, and prevention. Connecting 189 countries to protect citizens from financial crime.',
        'footer_services': 'Services', 'footer_resources': 'Resources', 'footer_legal': 'Legal',
        'footer_privacy': 'Privacy Policy', 'footer_terms': 'Terms of Use', 'footer_gdpr': 'GDPR Compliance',
        'footer_data': 'Data Protection', 'footer_api_docs': 'API Documentation', 'footer_awareness': 'Awareness',
        'footer_telegram': 'Telegram Bot', 'footer_contact': 'Contact', 'footer_sitemap': 'Sitemap',
        'footer_copyright': '© 2026 Global Fraud Intelligence Network. All rights reserved.',
        'privacy_title': 'Privacy Policy', 'privacy_subtitle': 'How GFIN collects, processes, and protects your data',
        'privacy_back': '← Back to Home', 'privacy_updated': 'Last updated: August 2026',
        'terms_title': 'Terms of Use', 'terms_subtitle': 'Terms and conditions for using GFIN',
        'terms_back': '← Back to Home', 'terms_updated': 'Last updated: August 2026',
        'contact_title': 'Contact GFIN', 'contact_subtitle': 'Get help with fraud reports, technical issues, or law enforcement access',
        'contact_back': '← Back to Home',
        'contact_emergency_title': '⚠️ In Immediate Danger or Financial Loss?',
        'contact_emergency_desc': 'Contact your local emergency services (999 / 112 / 911) or your national fraud hotline immediately. GFIN processes complaints within 17 seconds but is not an emergency service.',
        'contact_telegram_title': '💬 Telegram Bot — Fastest Response',
        'contact_telegram_desc': 'Check if a website is a scam, get scam alerts, and access awareness materials',
        'contact_telegram_btn': 'Open @GFINofficialbot →',
        'contact_channels_title': 'Contact Channels',
        'contact_report': 'Report a Scam', 'contact_report_desc': 'File a complaint online',
        'contact_check': 'Check a Website', 'contact_check_desc': 'Search scam database',
        'contact_police': 'Police Access', 'contact_police_desc': 'Law enforcement login',
        'apidocs_title': 'API Documentation', 'apidocs_subtitle': 'Public and law enforcement API endpoints for GFIN',
        'apidocs_back': '← Back to Home', 'apidocs_overview': 'Overview', 'apidocs_baseurl': 'Base URL',
        'police_title': 'Law Enforcement Secure Access', 'police_subtitle': 'Police Officer Login',
        'police_authorized': 'Authorized personnel only. All access is logged.',
        'police_email': 'Email Address', 'police_password': 'Password',
        'police_signin': 'Sign In Securely', 'police_encrypted': 'Encrypted connection • JWT authenticated',
        'police_register': 'Register as officer →', 'police_back': '← Back to GFIN homepage',
        'police_warning': '⚠️ UNAUTHORIZED ACCESS IS A CRIMINAL OFFENSE',
        'police_firsttime': 'First time? Contact your GFIN administrator to register.',
        'scamsites_title': 'Scam Website Database', 'scamsites_search_placeholder': 'Search domain or scam type...',
        'scamsites_stats_total': 'Total Scam Sites', 'scamsites_stats_verified': 'Verified Sites',
        'scamsites_stats_loss': 'Total Losses', 'scamsites_stats_countries': 'Countries Affected',
        'scamsites_table_domain': 'Domain', 'scamsites_table_type': 'Scam Type', 'scamsites_table_risk': 'Risk Level',
        'scamsites_table_reports': 'Reports', 'scamsites_table_loss': 'Reported Loss',
        'scamsites_no_results': 'No scam sites found', 'scamsites_back_home': 'Back to Home',
        'analytics_title': 'Fraud Intelligence & Analytics Engine', 'analytics_subtitle': 'Real-time fraud intelligence dashboard',
        'analytics_total_complaints': 'Total Complaints', 'analytics_active_cases': 'Active Cases',
        'analytics_total_losses': 'Total Losses', 'analytics_wallets_traced': 'Wallets Traced',
        'analytics_map_title': 'Global Complaint Density by Country', 'analytics_risk_breakdown': 'Risk Level Breakdown',
        'analytics_refresh': 'Refresh Data', 'analytics_operational': 'System Operational',
        'back_home': '← Back to Home'
      },

      es: {
        'nav_home': 'Inicio', 'nav_report': 'Denunciar Estafa', 'nav_scam_db': 'Base de Estafas',
        'nav_awareness': 'Conciencia', 'nav_about': 'Acerca de', 'nav_police': 'Acceso Policial',
        'hero_badge': '🛡️ Plataforma Oficial de Inteligencia de Fraude de Nivel Gubernamental',
        'hero_title': 'Protegiendo a los Ciudadanos del ', 'hero_title_highlight': 'Fraude Mundial',
        'hero_desc': 'La Red Global de Inteligencia de Fraude (GFIN) conecta a las agencias policiales en 189 países para detectar, investigar y prevenir el fraude financiero — desde estafas cripto hasta redes de suplantación transfronteriza. Denuncie una estafa en 17 segundos.',
        'hero_btn_report': '📝 Denunciar Estafa', 'hero_btn_check': '🔍 Verificar Sitio Web',
        'stat_countries': 'Países Conectados', 'stat_providers': 'Proveedores de Inteligencia',
        'stat_categories': 'Categorías de Estafa', 'stat_monitoring': 'Monitoreo Continuo',
        'how_title': 'Cómo Funciona GFIN', 'how_subtitle': 'De Denuncia a Investigación en 17 Segundos',
        'how_desc': 'Nuestra canal automatizado detecta estafas, recopila evidencia y dirige casos a las autoridades nacionales correctas — automáticamente.',
        'step1_title': 'Denunciar Estafa', 'step1_desc': 'Las víctimas presentan quejas a través de nuestro portal seguro en cualquiera de 7 idiomas. No se requiere conocimiento técnico.',
        'step2_title': 'Detección con IA', 'step2_desc': 'Nuestro motor determinista analiza más de 300 patrones de estafa en 15 categorías para identificar el tipo de estafa y el nivel de riesgo.',
        'step3_title': 'Recopilación de Evidencia', 'step3_desc': '72 proveedores de inteligencia recopilan automáticamente evidencia — dominios, billeteras, direcciones IP, información de hosting y más.',
        'step4_title': 'Enrutamiento por País', 'step4_desc': 'Los casos se dirigen automáticamente a la autoridad nacional de ciberdelincuencia, Interpol y Europol (para países de la UE).',
        'services_title': 'Servicios de la Plataforma', 'services_subtitle': 'Capacidades Integrales de Inteligencia de Fraude',
        'service1_title': 'Presentación de Quejas', 'service1_desc': 'Portal seguro multilingüe para que las víctimas denuncien fraude con carga de archivos y asignación automática de ID de caso.',
        'service2_title': 'Motor de Detección', 'service2_desc': 'Motor determinista v3.0 con más de 300 patrones en 15 categorías. Detección multilingüe (EN, ES, DE, FR).',
        'service3_title': 'Rastreo Cripto', 'service3_desc': 'Rastreo de criptomonedas multichain en 10 tipos de billetera y 9 cadenas USDT. Siga el dinero.',
        'service4_title': 'Playbook de Inteligencia', 'service4_desc': '13 tipos de entidad rastreados de dominio a dirección física. Cadena de evidencia con hash SHA-256.',
        'service5_title': 'Enrutamiento por País', 'service5_desc': 'Enrutamiento automático a 189 autoridades nacionales de ciberdelincuencia, Interpol y Europol.',
        'service6_title': 'Alertas de Telegram', 'service6_desc': 'Alertas públicas anonimizadas y 12 tipos de difusión de conciencia vía @GFINofficialbot.',
        'partners_eyebrow': 'Cooperación Internacional', 'partners_title': 'Conectado a la Aplicación de la Ley Global',
        'partners_desc': 'GFIN dirige la inteligencia a las unidades nacionales de ciberdelincuencia, Interpol y Europol — garantizando la cooperación transfronteriza en 189 países.',
        'awareness_eyebrow': 'Conciencia Pública', 'awareness_title': 'Conozca las Señales — Protéjase',
        'awareness_desc': 'GFIN rastrea 15 categorías de fraude. Aprenda a reconocer y evitar cada tipo.',
        'awareness_recovery': 'Estafas de Recuperación', 'awareness_recovery_desc': 'Alguien promete recuperar dinero ya perdido por estafas. Son estafadores que se dirigen a víctimas anteriores.',
        'awareness_romance': 'Estafas Románticas', 'awareness_romance_desc': 'Relaciones en línea falsas que terminan en solicitudes de dinero, cripto o regalos.',
        'awareness_investment': 'Fraude de Inversión', 'awareness_investment_desc': 'Plataformas de trading falsas que prometen altos retornos. Su dinero desaparece.',
        'awareness_phishing': 'Phishing', 'awareness_phishing_desc': 'Correos y sitios web falsos que roban sus contraseñas y datos bancarios.',
        'awareness_impersonation': 'Suplantación', 'awareness_impersonation_desc': 'Criminales que se hacen pasar por policía, gobierno o soporte técnico para robar dinero.',
        'awareness_crypto': 'Fraude Cripto', 'awareness_crypto_desc': 'Exchanges falsos, rug pulls y esquemas Ponzi en el espacio cripto.',
        'awareness_tech': 'Soporte Técnico Falso', 'awareness_tech_desc': 'Llamadas falsas de Microsoft/Apple para obtener acceso remoto a su computadora.',
        'awareness_advance': 'Pago por Adelantado', 'awareness_advance_desc': 'Pagar una tarifa por adelantado para desbloquear un premio, préstamo o herencia que no existe.',
        'about_hero_desc': 'La Red Global de Inteligencia de Fraude conecta agencias en 189 paises para detectar y prevenir el fraude.',
        'about_mission_desc': 'GFIN une a ciudadanos y unidades nacionales de ciberdelincuencia.',
        'about_mission_detect': 'Detectar',
        'about_mission_detect_desc': 'Nuestro motor analiza mas de 300 patrones en 15 categorias.',
        'about_mission_investigate': 'Investigar',
        'about_mission_investigate_desc': '72 proveedores recopilan evidencia automaticamente.',
        'about_mission_prevent': 'Prevenir',
        'about_mission_prevent_desc': 'Difusion de conciencia publica y alertas de Telegram.',
        'about_tech_desc': 'Arquitectura de confianza cero con cifrado y datos conforme al GDPR.',
        'cta_title': 'Denuncie una Estafa en 17 Segundos', 'cta_desc': 'Presente una queja ahora. Nuestro sistema automatizado comienza a investigar inmediatamente.',
        'cta_btn': 'Presentar Queja', 'cta_btn2': 'Verificar Sitio Web',
        'footer_brand': 'GFIN — Red Global de Inteligencia de Fraude',
        'footer_desc': 'Plataforma internacional de aplicación de la ley para la detección, investigación y prevención de fraude transfronterizo. Conectando 189 países para proteger a los ciudadanos del delito financiero.',
        'footer_services': 'Servicios', 'footer_resources': 'Recursos', 'footer_legal': 'Legal',
        'footer_privacy': 'Política de Privacidad', 'footer_terms': 'Términos de Uso', 'footer_gdpr': 'Cumplimiento GDPR',
        'footer_data': 'Protección de Datos', 'footer_api_docs': 'Documentación API', 'footer_awareness': 'Conciencia',
        'footer_telegram': 'Bot de Telegram', 'footer_contact': 'Contacto', 'footer_sitemap': 'Mapa del Sitio',
        'footer_copyright': '© 2026 Red Global de Inteligencia de Fraude. Todos los derechos reservados.',
        'privacy_title': 'Política de Privacidad', 'privacy_subtitle': 'Cómo GFIN recopila, procesa y protege sus datos',
        'privacy_back': '← Volver al Inicio', 'privacy_updated': 'Última actualización: Agosto 2026',
        'terms_title': 'Términos de Uso', 'terms_subtitle': 'Términos y condiciones para usar GFIN',
        'terms_back': '← Volver al Inicio', 'terms_updated': 'Última actualización: Agosto 2026',
        'contact_title': 'Contactar GFIN', 'contact_subtitle': 'Obtenga ayuda con denuncias de fraude, problemas técnicos o acceso policial',
        'contact_back': '← Volver al Inicio',
        'contact_emergency_title': '⚠️ ¿En Peligro Inmediato o Pérdida Financiera?',
        'contact_emergency_desc': 'Contacte a sus servicios de emergencia locales (999 / 112 / 911) o a su línea nacional de fraude inmediatamente. GFIN procesa denuncias en 17 segundos pero no es un servicio de emergencia.',
        'contact_telegram_title': '💬 Bot de Telegram — Respuesta Más Rápida',
        'contact_telegram_desc': 'Verifique si un sitio web es una estafa, reciba alertas y acceda a materiales de conciencia',
        'contact_telegram_btn': 'Abrir @GFINofficialbot →',
        'contact_channels_title': 'Canales de Contacto',
        'contact_report': 'Denunciar Estafa', 'contact_report_desc': 'Presentar una queja en línea',
        'contact_check': 'Verificar Sitio', 'contact_check_desc': 'Buscar en base de datos de estafas',
        'contact_police': 'Acceso Policial', 'contact_police_desc': 'Inicio de sesión policial',
        'apidocs_title': 'Documentación API', 'apidocs_subtitle': 'Endpoints API públicos y policiales para GFIN',
        'apidocs_back': '← Volver al Inicio', 'apidocs_overview': 'Resumen', 'apidocs_baseurl': 'URL Base',
        'police_title': 'Acceso Seguro Policial', 'police_subtitle': 'Inicio de Sesión de Oficial',
        'police_authorized': 'Solo personal autorizado. Todo acceso es registrado.',
        'police_email': 'Correo Electrónico', 'police_password': 'Contraseña',
        'police_signin': 'Iniciar Sesión', 'police_encrypted': 'Conexión cifrada • Autenticación JWT',
        'police_register': 'Registrarse como oficial →', 'police_back': '← Volver al inicio',
        'police_warning': '⚠️ EL ACCESO NO AUTORIZADO ES UN DELITO',
        'police_firsttime': '¿Primera vez? Contacte a su administrador GFIN para registrarse.',
        'scamsites_title': 'Base de Datos de Sitios de Estafa', 'scamsites_search_placeholder': 'Buscar dominio o tipo de estafa...',
        'scamsites_stats_total': 'Sitios de Estafa Totales', 'scamsites_stats_verified': 'Sitios Verificados',
        'scamsites_stats_loss': 'Pérdidas Totales', 'scamsites_stats_countries': 'Países Afectados',
        'scamsites_table_domain': 'Dominio', 'scamsites_table_type': 'Tipo de Estafa', 'scamsites_table_risk': 'Nivel de Riesgo',
        'scamsites_table_reports': 'Reportes', 'scamsites_table_loss': 'Pérdida Reportada',
        'scamsites_no_results': 'No se encontraron sitios de estafa', 'scamsites_back_home': 'Volver al Inicio',
        'analytics_title': 'Motor de Análisis e Inteligencia de Fraude', 'analytics_subtitle': 'Panel de inteligencia de fraude en tiempo real',
        'analytics_total_complaints': 'Denuncias Totales', 'analytics_active_cases': 'Casos Activos',
        'analytics_total_losses': 'Pérdidas Totales', 'analytics_wallets_traced': 'Billeteras Rastreadas',
        'analytics_map_title': 'Densidad de Denuncias por País', 'analytics_risk_breakdown': 'Desglose por Nivel de Riesgo',
        'analytics_refresh': 'Actualizar Datos', 'analytics_operational': 'Sistema Operativo',
        'back_home': '← Volver al Inicio'
      },

      de: {
        'nav_home': 'Startseite', 'nav_report': 'Betrug melden', 'nav_scam_db': 'Betrugsdatenbank',
        'nav_awareness': 'Aufklärung', 'nav_about': 'Über uns', 'nav_police': 'Polizeizugang',
        'hero_badge': '🛡️ Offizielle Betrugsaufklärungsplattform in Regierungsqualität',
        'hero_title': 'Bürger schützen vor ', 'hero_title_highlight': 'weltweitem Betrug',
        'hero_desc': 'Das Global Fraud Intelligence Network (GFIN) verbindet Strafverfolgungsbehörden in 189 Ländern zur Erkennung, Untersuchung und Verhinderung von Finanzbetrug — von Krypto-Betrug bis zu grenzüberschreitenden Täuschungsnetzwerken. Melden Sie Betrug in 17 Sekunden.',
        'hero_btn_report': '📝 Betrug melden', 'hero_btn_check': '🔍 Website prüfen',
        'stat_countries': 'Verbundene Länder', 'stat_providers': 'Intelligenzanbieter',
        'stat_categories': 'Betrugskategorien', 'stat_monitoring': 'Rund-um-die-Uhr-Überwachung',
        'how_title': 'Wie GFIN funktioniert', 'how_subtitle': 'Von der Meldung zur Untersuchung in 17 Sekunden',
        'how_desc': 'Unsere automatisierte Pipeline erkennt Betrug, sammelt Beweise und leitet Fälle an die zuständigen nationalen Behörden weiter — automatisch.',
        'step1_title': 'Betrug melden', 'step1_desc': 'Opfer reichen Beschwerden über unser sicheres Portal in 7 Sprachen ein. Kein technisches Wissen erforderlich.',
        'step2_title': 'KI-gestützte Erkennung', 'step2_desc': 'Unsere deterministische Engine analysiert 300+ Betrugsmuster in 15 Kategorien, um die Betrugsart und das Risikoniveau zu identifizieren.',
        'step3_title': 'Beweissammlung', 'step3_desc': '72 Intelligenzanbieter sammeln automatisch Beweise — Domains, Wallets, IP-Adressen, Hosting-Informationen und mehr.',
        'step4_title': 'Länderweiterleitung', 'step4_desc': 'Fälle werden automatisch an die zuständige nationale Cybercrime-Behörde, Interpol und Europol (für EU-Länder) weitergeleitet.',
        'services_title': 'Plattformdienste', 'services_subtitle': 'Umfassende Betrugsintelligenz-Funktionen',
        'service1_title': 'Beschwerdeeinreichung', 'service1_desc': 'Sicheres mehrsprachiges Portal für Opfer zur Meldung von Betrug mit Datei-Uploads und automatischer Fall-ID-Zuweisung.',
        'service2_title': 'Betrugserkennungs-Engine', 'service2_desc': 'Deterministische v3.0-Engine mit 300+ Mustern in 15 Kategorien. Mehrsprachige Erkennung (EN, ES, DE, FR).',
        'service3_title': 'Krypto-Verfolgung', 'service3_desc': 'Multi-Chain Krypto-Verfolgung über 10 Wallet-Typen und 9 USDT-Chains. Folgen Sie dem Geld.',
        'service4_title': 'Intelligenz-Playbook', 'service4_desc': '13 Entitätstypen verfolgt von Domain bis zur physischen Adresse. Beweiskette mit SHA-256-Hashing.',
        'service5_title': 'Länderweiterleitung', 'service5_desc': 'Automatische Weiterleitung an 189 nationale Cybercrime-Behörden, Interpol und Europol.',
        'service6_title': 'Telegramm-Alerts', 'service6_desc': 'Öffentliche anonymisierte Betrugs-Alerts und 12 Aufklärungssendungen via @GFINofficialbot.',
        'partners_eyebrow': 'Internationale Zusammenarbeit', 'partners_title': 'Verbunden mit globaler Strafverfolgung',
        'partners_desc': 'GFIN leitet Intelligenz an nationale Cybercrime-Einheiten, Interpol und Europol — und gewährleistet grenzüberschreitende Zusammenarbeit in 189 Ländern.',
        'awareness_eyebrow': 'Öffentliche Aufklärung', 'awareness_title': 'Erkennen Sie die Zeichen — Schützen Sie sich',
        'awareness_desc': 'GFIN verfolgt 15 Betrugskategorien. Lernen Sie, wie Sie jeden Typ erkennen und vermeiden.',
        'awareness_recovery': 'Wiederherstellungsbetrug', 'awareness_recovery_desc': 'Jemand verspricht, bereits verloren gegangenes Geld zurückzuholen. Es sind Betrüger, die frühere Opfer ins Visier nehmen.',
        'awareness_romance': 'Romance Scams', 'awareness_romance_desc': 'Falsche Online-Beziehungen, die in Geldforderungen, Krypto oder Geschenken enden.',
        'awareness_investment': 'Anlagebetrug', 'awareness_investment_desc': 'Falsche Handelsplattformen, die hohe Renditen versprechen. Ihr Geld verschwindet.',
        'awareness_phishing': 'Phishing', 'awareness_phishing_desc': 'Falsche E-Mails und Websites, die Ihre Passwörter und Bankdaten stehlen.',
        'awareness_impersonation': 'Identitätsmissbrauch', 'awareness_impersonation_desc': 'Kriminelle, die sich als Polizei, Regierung oder Tech-Support ausgeben, um Geld zu stehlen.',
        'awareness_crypto': 'Krypto-Betrug', 'awareness_crypto_desc': 'Falsche Exchanges, Rug Pulls und Ponzi-Systeme im Krypto-Bereich.',
        'awareness_tech': 'Tech-Support-Betrug', 'awareness_tech_desc': 'Falsche Microsoft/Apple-Anrufe, um Fernzugriff auf Ihren Computer zu erhalten.',
        'awareness_advance': 'Vorauszahlungsbetrug', 'awareness_advance_desc': 'Vorauszahlung einer Gebühr, um einen Preis, ein Darlehen oder ein Erbe freizuschalten, das nicht existiert.',
        'about_hero_desc': 'Das Global Fraud Intelligence Network verbindet Behorden in 189 Landern zur Aufdeckung und Verhinderung von Finanzbetrug.',
        'about_mission_desc': 'GFIN verbindet Burger, nationale Cybercrime-Einheiten und internationale Organisationen.',
        'about_mission_detect': 'Erkennen',
        'about_mission_detect_desc': 'Unsere Engine analysiert uber 300 Betrugsmuster in 15 Kategorien in mehreren Sprachen.',
        'about_mission_investigate': 'Untersuchen',
        'about_mission_investigate_desc': '72 Inteligenz-Anbieter sammeln automatisch Beweise.',
        'about_mission_prevent': 'Verhindern',
        'about_mission_prevent_desc': 'Offentliche Aufklarung und Echtzeit-Telegram-Warnungen halten Burger informiert.',
        'about_tech_desc': 'Built on Zero-Trust-Architektur mit End-to-End-Verschlusselung und DSGVO-konformer Datenverarbeitung.',
        'cta_title': 'Betrug in 17 Sekunden melden', 'cta_desc': 'Reichen Sie jetzt eine Beschwerde ein. Unser automatisiertes System beginnt sofort mit der Untersuchung.',
        'cta_btn': 'Beschwerde einreichen', 'cta_btn2': 'Website prüfen',
        'footer_brand': 'GFIN — Global Fraud Intelligence Network',
        'footer_desc': 'Eine internationale Strafverfolgungsplattform zur grenzüberschreitenden Betrugserkennung, -untersuchung und -prävention. Verbindet 189 Länder zum Schutz der Bürger vor Finanzkriminalität.',
        'footer_services': 'Dienste', 'footer_resources': 'Ressourcen', 'footer_legal': 'Rechtliches',
        'footer_privacy': 'Datenschutz', 'footer_terms': 'Nutzungsbedingungen', 'footer_gdpr': 'DSGVO-Konformität',
        'footer_data': 'Datenschutz', 'footer_api_docs': 'API-Dokumentation', 'footer_awareness': 'Aufklärung',
        'footer_telegram': 'Telegramm-Bot', 'footer_contact': 'Kontakt', 'footer_sitemap': 'Sitemap',
        'footer_copyright': '© 2026 Global Fraud Intelligence Network. Alle Rechte vorbehalten.',
        'privacy_title': 'Datenschutzerklärung', 'privacy_subtitle': 'Wie GFIN Ihre Daten erfasst, verarbeitet und schützt',
        'privacy_back': '← Zurück zur Startseite', 'privacy_updated': 'Zuletzt aktualisiert: August 2026',
        'terms_title': 'Nutzungsbedingungen', 'terms_subtitle': 'Geschäftsbedingungen für die Nutzung von GFIN',
        'terms_back': '← Zurück zur Startseite', 'terms_updated': 'Zuletzt aktualisiert: August 2026',
        'contact_title': 'GFIN kontaktieren', 'contact_subtitle': 'Hilfe bei Betrugsmeldungen, technischen Problemen oder Polizeizugang',
        'contact_back': '← Zurück zur Startseite',
        'contact_emergency_title': '⚠️ In akuter Gefahr oder mit finanziellen Verlusten?',
        'contact_emergency_desc': 'Kontaktieren Sie sofort Ihre lokalen Notdienste (999 / 112 / 911) oder Ihre nationale Betrugshotline. GFIN bearbeitet Beschwerden in 17 Sekunden, ist aber kein Notdienst.',
        'contact_telegram_title': '💬 Telegramm-Bot — Schnellste Antwort',
        'contact_telegram_desc': 'Prüfen Sie, ob eine Website ein Betrug ist, erhalten Sie Alerts und Zugriff auf Aufklärungsmaterial',
        'contact_telegram_btn': '@GFINofficialbot öffnen →',
        'contact_channels_title': 'Kontaktkanäle',
        'contact_report': 'Betrug melden', 'contact_report_desc': 'Beschwerde online einreichen',
        'contact_check': 'Website prüfen', 'contact_check_desc': 'Betrugsdatenbank durchsuchen',
        'contact_police': 'Polizeizugang', 'contact_police_desc': 'Polizeiliche Anmeldung',
        'apidocs_title': 'API-Dokumentation', 'apidocs_subtitle': 'Öffentliche und polizeiliche API-Endpunkte für GFIN',
        'apidocs_back': '← Zurück zur Startseite', 'apidocs_overview': 'Überblick', 'apidocs_baseurl': 'Basis-URL',
        'police_title': 'Sicherer Polizeizugang', 'police_subtitle': 'Beamten-Anmeldung',
        'police_authorized': 'Nur autorisiertes Personal. Alle Zugriffe werden protokolliert.',
        'police_email': 'E-Mail-Adresse', 'police_password': 'Passwort',
        'police_signin': 'Sicher anmelden', 'police_encrypted': 'Verschlüsselte Verbindung • JWT-authentifiziert',
        'police_register': 'Als Beamter registrieren →', 'police_back': '← Zurück zur GFIN-Startseite',
        'police_warning': '⚠️ UNBEFUGTER ZUGRIFF IST EINE STRAFTAT',
        'police_firsttime': 'Zum ersten Mal? Kontaktieren Sie Ihren GFIN-Administrator zur Registrierung.',
        'scamsites_title': 'Betrugs-Website-Datenbank', 'scamsites_search_placeholder': 'Domain oder Betrugstyp suchen...',
        'scamsites_stats_total': 'Betrugs-Websites gesamt', 'scamsites_stats_verified': 'Verifizierte Websites',
        'scamsites_stats_loss': 'Gesamtverluste', 'scamsites_stats_countries': 'Betroffene Länder',
        'scamsites_table_domain': 'Domain', 'scamsites_table_type': 'Betrugsart', 'scamsites_table_risk': 'Risikolevel',
        'scamsites_table_reports': 'Meldungen', 'scamsites_table_loss': 'Gemeldeter Verlust',
        'scamsites_no_results': 'Keine Betrugs-Websites gefunden', 'scamsites_back_home': 'Zurück zur Startseite',
        'analytics_title': 'Betrugs-Intelligenz- und Analyse-Engine', 'analytics_subtitle': 'Echtzeit-Betrugs-Intelligenz-Dashboard',
        'analytics_total_complaints': 'Beschwerden gesamt', 'analytics_active_cases': 'Aktive Fälle',
        'analytics_total_losses': 'Gesamtverluste', 'analytics_wallets_traced': 'Verfolgte Wallets',
        'analytics_map_title': 'Globale Beschwerdedichte nach Land', 'analytics_risk_breakdown': 'Risiko-Verteilung',
        'analytics_refresh': 'Daten aktualisieren', 'analytics_operational': 'System betriebsbereit',
        'back_home': '← Zurück zur Startseite'
      },

      fr: {
        'nav_home': 'Accueil', 'nav_report': 'Signaler une Arnaque', 'nav_scam_db': 'Base d\'Arnaques',
        'nav_awareness': 'Sensibilisation', 'nav_about': 'À propos', 'nav_police': 'Accès Police',
        'hero_badge': '🛡️ Plateforme Officielle d\'Intelligence de Fraude de Qualité Gouvernementale',
        'hero_title': 'Protéger les Citoyens contre la ', 'hero_title_highlight': 'Fraude Mondiale',
        'hero_desc': 'Le Global Fraud Intelligence Network (GFIN) relie les autorités répressives de 189 pays pour détecter, enquêter et prévenir la fraude financière — des arnaques crypto aux réseaux d\'usurpation transfrontaliers. Signalez une arnaque en 17 secondes.',
        'hero_btn_report': '📝 Signaler une Arnaque', 'hero_btn_check': '🔍 Vérifier un Site',
        'stat_countries': 'Pays Connectés', 'stat_providers': 'Fournisseurs d\'Intelligence',
        'stat_categories': 'Catégories d\'Arnaque', 'stat_monitoring': 'Surveillance Continue',
        'how_title': 'Comment GFIN Fonctionne', 'how_subtitle': 'De la Plainte à l\'Enquête en 17 Secondes',
        'how_desc': 'Notre pipeline automatisé détecte les arnaques, collecte des preuves et achemine les cas vers les autorités nationales compétentes — automatiquement.',
        'step1_title': 'Signaler une Arnaque', 'step1_desc': 'Les victimes déposent des plaintes via notre portail sécurisé dans 7 langues. Aucune connaissance technique requise.',
        'step2_title': 'Détection par IA', 'step2_desc': 'Notre moteur déterministe analyse plus de 300 modèles d\'arnaques dans 15 catégories pour identifier le type d\'arnaque et le niveau de risque.',
        'step3_title': 'Collecte de Preuves', 'step3_desc': '72 fournisseurs d\'intelligence collectent automatiquement des preuves — domaines, portefeuilles, adresses IP, informations d\'hébergement et plus.',
        'step4_title': 'Routage par Pays', 'step4_desc': 'Les cas sont automatiquement acheminés vers l\'autorité nationale de cybercriminalité, Interpol et Europol (pour les pays de l\'UE).',
        'services_title': 'Services de la Plateforme', 'services_subtitle': 'Capacités Complètes d\'Intelligence de Fraude',
        'service1_title': 'Dépôt de Plainte', 'service1_desc': 'Portail multilingue sécurisé pour que les victimes signalent des fraudes avec téléchargement de fichiers et attribution automatique d\'ID de cas.',
        'service2_title': 'Moteur de Détection', 'service2_desc': 'Moteur déterministe v3.0 avec plus de 300 modèles dans 15 catégories. Détection multilingue (EN, ES, DE, FR).',
        'service3_title': 'Traçage Crypto', 'service3_desc': 'Traçage multi-chaînes de cryptomonnaies sur 10 types de portefeuilles et 9 chaînes USDT. Suivez l\'argent.',
        'service4_title': 'Playbook d\'Intelligence', 'service4_desc': '13 types d\'entités tracés du domaine à l\'adresse physique. Chaîne de preuves avec hachage SHA-256.',
        'service5_title': 'Routage par Pays', 'service5_desc': 'Routage automatique vers 189 autorités nationales de cybercriminalité, Interpol et Europol.',
        'service6_title': 'Alertes Telegram', 'service6_desc': 'Alertes publiques anonymisées et 12 types de diffusions de sensibilisation via @GFINofficialbot.',
        'partners_eyebrow': 'Coopération Internationale', 'partners_title': 'Connecté à la Police Mondiale',
        'partners_desc': 'GFIN achemine l\'intelligence vers les unités nationales de cybercriminalité, Interpol et Europol — garantissant la coopération transfrontalière dans 189 pays.',
        'awareness_eyebrow': 'Sensibilisation Publique', 'awareness_title': 'Connaissez les Signes — Protégez-vous',
        'awareness_desc': 'GFIN suit 15 catégories de fraude. Apprenez à reconnaître et éviter chaque type.',
        'awareness_recovery': 'Arnaques de Récupération', 'awareness_recovery_desc': 'Quelqu\'un promet de récupérer l\'argent déjà perdu. Ce sont des escrocs ciblant les victimes précédentes.',
        'awareness_romance': 'Arnaques Romantiques', 'awareness_romance_desc': 'Fausses relations en ligne se terminant par des demandes d\'argent, de crypto ou de cadeaux.',
        'awareness_investment': 'Fraude d\'Investissement', 'awareness_investment_desc': 'Fausses plateformes de trading promettant des rendements élevés. Votre argent disparaît.',
        'awareness_phishing': 'Phishing', 'awareness_phishing_desc': 'Faux e-mails et sites web volant vos mots de passe et données bancaires.',
        'awareness_impersonation': 'Usurpation', 'awareness_impersonation_desc': 'Criminels se faisant passer pour la police, le gouvernement ou le support technique pour voler de l\'argent.',
        'awareness_crypto': 'Fraude Crypto', 'awareness_crypto_desc': 'Faux exchanges, rug pulls et schémas Ponzi dans l\'espace crypto.',
        'awareness_tech': 'Faux Support Technique', 'awareness_tech_desc': 'Faux appels Microsoft/Apple pour obtenir l\'accès à distance à votre ordinateur.',
        'awareness_advance': 'Fraude d\'Avance de Frais', 'awareness_advance_desc': 'Payer des frais à l\'avance pour débloquer un prix, un prêt ou un héritage qui n\'existe pas.',
        'about_hero_desc': 'Le Reseau Mondial de Renseignement sur la Fraude connecte les agences dans 189 pays pour detecter et prevenir la fraude financiere.',
        'about_mission_desc': 'GFIN relie les citoyens, les unites nationales de cybercriminalite et les organismes internationaux.',
        'about_mission_detect': 'Detecter',
        'about_mission_detect_desc': 'Notre moteur analyse plus de 300 modeles d arnaque dans 15 categories en plusieurs langues.',
        'about_mission_investigate': 'Enqueter',
        'about_mission_investigate_desc': '72 fournisseurs de renseignements collectent automatiquement des preuves.',
        'about_mission_prevent': 'Prevenir',
        'about_mission_prevent_desc': 'Diffusion de sensibilisation publique et alertes Telegram informent les citoyens.',
        'about_tech_desc': 'Architecture de confiance zero avec chiffrement et traitement des donnees conforme au RGPD.',
        'cta_title': 'Signalez une Arnaque en 17 Secondes', 'cta_desc': 'Déposez une plainte maintenant. Notre système automatisé commence l\'enquête immédiatement.',
        'cta_btn': 'Déposer une Plainte', 'cta_btn2': 'Vérifier un Site',
        'footer_brand': 'GFIN — Global Fraud Intelligence Network',
        'footer_desc': 'Plateforme internationale de lutte contre la fraude pour la détection, l\'enquête et la prévention transfrontalières. Connectant 189 pays pour protéger les citoyens contre la criminalité financière.',
        'footer_services': 'Services', 'footer_resources': 'Ressources', 'footer_legal': 'Mentions légales',
        'footer_privacy': 'Politique de Confidentialité', 'footer_terms': 'Conditions d\'Utilisation', 'footer_gdpr': 'Conformité RGPD',
        'footer_data': 'Protection des Données', 'footer_api_docs': 'Documentation API', 'footer_awareness': 'Sensibilisation',
        'footer_telegram': 'Bot Telegram', 'footer_contact': 'Contact', 'footer_sitemap': 'Plan du Site',
        'footer_copyright': '© 2026 Global Fraud Intelligence Network. Tous droits réservés.',
        'privacy_title': 'Politique de Confidentialité', 'privacy_subtitle': 'Comment GFIN collecte, traite et protège vos données',
        'privacy_back': '← Retour à l\'Accueil', 'privacy_updated': 'Dernière mise à jour : Août 2026',
        'terms_title': 'Conditions d\'Utilisation', 'terms_subtitle': 'Termes et conditions d\'utilisation de GFIN',
        'terms_back': '← Retour à l\'Accueil', 'terms_updated': 'Dernière mise à jour : Août 2026',
        'contact_title': 'Contacter GFIN', 'contact_subtitle': 'Obtenez de l\'aide pour les signalements de fraude, problèmes techniques ou accès police',
        'contact_back': '← Retour à l\'Accueil',
        'contact_emergency_title': '⚠️ En Danger Immédiat ou Perte Financière ?',
        'contact_emergency_desc': 'Contactez immédiatement vos services d\'urgence locaux (999 / 112 / 911) ou votre ligne nationale anti-fraude. GFIN traite les plaintes en 17 secondes mais n\'est pas un service d\'urgence.',
        'contact_telegram_title': '💬 Bot Telegram — Réponse la Plus Rapide',
        'contact_telegram_desc': 'Vérifiez si un site est une arnaque, recevez des alertes et accédez aux supports de sensibilisation',
        'contact_telegram_btn': 'Ouvrir @GFINofficialbot →',
        'contact_channels_title': 'Canaux de Contact',
        'contact_report': 'Signaler une Arnaque', 'contact_report_desc': 'Déposer une plainte en ligne',
        'contact_check': 'Vérifier un Site', 'contact_check_desc': 'Rechercher dans la base d\'arnaques',
        'contact_police': 'Accès Police', 'contact_police_desc': 'Connexion des forces de l\'ordre',
        'apidocs_title': 'Documentation API', 'apidocs_subtitle': 'Endpoints API publics et police pour GFIN',
        'apidocs_back': '← Retour à l\'Accueil', 'apidocs_overview': 'Aperçu', 'apidocs_baseurl': 'URL de Base',
        'police_title': 'Accès Sécurisé Police', 'police_subtitle': 'Connexion Officier de Police',
        'police_authorized': 'Personnel autorisé uniquement. Tous les accès sont journalisés.',
        'police_email': 'Adresse E-mail', 'police_password': 'Mot de Passe',
        'police_signin': 'Se Connecter', 'police_encrypted': 'Connexion chiffrée • Authentification JWT',
        'police_register': 'S\'enregistrer comme officier →', 'police_back': '← Retour à l\'accueil GFIN',
        'police_warning': '⚠️ L\'ACCÈS NON AUTORISÉ EST UN DÉLIT',
        'police_firsttime': 'Première fois ? Contactez votre administrateur GFIN pour vous enregistrer.',
        'scamsites_title': 'Base de Données des Sites d\'Arnaque', 'scamsites_search_placeholder': 'Rechercher domaine ou type d\'arnaque...',
        'scamsites_stats_total': 'Sites d\'Arnaque Totaux', 'scamsites_stats_verified': 'Sites Vérifiés',
        'scamsites_stats_loss': 'Pertes Totales', 'scamsites_stats_countries': 'Pays Affectés',
        'scamsites_table_domain': 'Domaine', 'scamsites_table_type': 'Type d\'Arnaque', 'scamsites_table_risk': 'Niveau de Risque',
        'scamsites_table_reports': 'Signalements', 'scamsites_table_loss': 'Perte Signalée',
        'scamsites_no_results': 'Aucun site d\'arnaque trouvé', 'scamsites_back_home': 'Retour à l\'Accueil',
        'analytics_title': 'Moteur d\'Analyse et d\'Intelligence de Fraude', 'analytics_subtitle': 'Tableau de bord d\'intelligence de fraude en temps réel',
        'analytics_total_complaints': 'Plaintes Totales', 'analytics_active_cases': 'Cas Actifs',
        'analytics_total_losses': 'Pertes Totales', 'analytics_wallets_traced': 'Portefeuilles Tracés',
        'analytics_map_title': 'Densité de Plaintes par Pays', 'analytics_risk_breakdown': 'Répartition par Niveau de Risque',
        'analytics_refresh': 'Actualiser', 'analytics_operational': 'Système Opérationnel',
        'back_home': '← Retour à l\'Accueil'
      },

      ar: {
        'nav_home': 'الرئيسية', 'nav_report': 'الإبلاغ عن احتيال', 'nav_scam_db': 'قاعدة بيانات الاحتيال',
        'nav_awareness': 'التوعية', 'nav_about': 'حول', 'nav_police': 'دخول الشرطة',
        'hero_badge': '🛡️ منصة استخبارات احتيال حكومية رسمية',
        'hero_title': 'حماية المواطنين من ', 'hero_title_highlight': 'الاحتيال العالمي',
        'hero_desc': 'تربط شبكة ذكاء الاحتيال العالمية (GFIN) وكالات إنفاذ القانون في 189 دولة للكشف عن الاحتيال المالي والتحقيق فيه ومنعه — من عمليات الاحتيال بالعملات الرقمية إلى شبكات انتحال الهوية عبر الحدود. أبلغ عن احتيال في 17 ثانية.',
        'hero_btn_report': '📝 الإبلاغ عن احتيال', 'hero_btn_check': '🔍 فحص موقع',
        'stat_countries': 'الدول المتصلة', 'stat_providers': 'مزودو الاستخبارات',
        'stat_categories': 'فئات الاحتيال', 'stat_monitoring': 'مراقبة مستمرة',
        'how_title': 'كيف يعمل GFIN', 'how_subtitle': 'من البلاغ إلى التحقيق في 17 ثانية',
        'how_desc': 'يكشف نظامنا الآلي عمليات الاحتيال ويجمع الأدلة ويحيل القضايا إلى السلطات الوطنية المختصة — تلقائياً.',
        'step1_title': 'الإبلاغ عن احتيال', 'step1_desc': 'يقدم الضحايا شكاواهم عبر بوابتنا الآمنة بأي من 7 لغات. لا تتطلب معرفة تقنية.',
        'step2_title': 'كشف بالذكاء الاصطناعي', 'step2_desc': 'يحلل محركنا الحتمي أكثر من 300 نمط احتيال في 15 فئة لتحديد نوع الاحتيال ومستوى الخطر.',
        'step3_title': 'جمع الأدلة', 'step3_desc': 'يجمع 72 مزود استخبارات الأدلة تلقائياً — النطاقات والمحافظ وعناوين IP ومعلومات الاستضافة والمزيد.',
        'step4_title': 'التوجيه حسب الدولة', 'step4_desc': 'تُحال القضايا تلقائياً إلى سلطة الجرائم الإلكترونية الوطنية والإنتربول ويوروبول (لدول الاتحاد الأوروبي).',
        'services_title': 'خدمات المنصة', 'services_subtitle': 'قدرات استخبارات الاحتيال الشاملة',
        'service1_title': 'تقديم الشكاوى', 'service1_desc': 'بوابة آمنة متعددة اللغات للضحايا للإبلاغ عن الاحتيال مع تحميل الملفات وتخصيص رقم القضية تلقائياً.',
        'service2_title': 'محرك كشف الاحتيال', 'service2_desc': 'محرك حتمي v3.0 بأكثر من 300 نمط في 15 فئة. كشف متعدد اللغات (EN, ES, DE, FR).',
        'service3_title': 'تتبع العملات الرقمية', 'service3_desc': 'تتبع متعدد السلاسل للعملات الرقمية عبر 10 أنواع محافظ و9 سلاسل USDT. تتبع المال.',
        'service4_title': 'دليل الاستخبارات', 'service4_desc': '13 نوع كيان يتم تتبعها من النطاق إلى العنوان الفعلي. سلسلة الأدلة بتشفير SHA-256.',
        'service5_title': 'التوجيه حسب الدولة', 'service5_desc': 'توجيه تلقائي إلى 189 سلطة وطنية للجرائم الإلكترونية والإنتربول ويوروبول.',
        'service6_title': 'تنبيهات تيليجرام', 'service6_desc': 'تنبيهات احتيال عامة مجهولة الهوية و12 نوعاً من بث التوعية عبر @GFINofficialbot.',
        'partners_eyebrow': 'تعاون دولي', 'partners_title': 'متصل بإنفاذ القانون العالمي',
        'partners_desc': 'يوجه GFIN الاستخبارات إلى وحدات الجرائم الإلكترونية الوطنية والإنتربول ويوروبول — ضماناً للتعاون عبر الحدود في 189 دولة.',
        'awareness_eyebrow': 'التوعية العامة', 'awareness_title': 'اعرف العلامات — احمِ نفسك',
        'awareness_desc': 'يتتبع GFIN 15 فئة من الاحتيال. تعلم كيفية التعرف على كل نوع وتجنبه.',
        'awareness_recovery': 'احتيال الاسترداد', 'awareness_recovery_desc': 'يعد شخص باسترداد الأموال المفقودة بالفعل. إنهم محتالون يستهدفون الضحايا السابقين.',
        'awareness_romance': 'احتيال رومانسي', 'awareness_romance_desc': 'علاقات وهمية عبر الإنترنت تنتهي بطلبات مالية أو عملات رقمية أو هدايا.',
        'awareness_investment': 'احتيال استثماري', 'awareness_investment_desc': 'منصات تداول وهمية تعد بعوائد عالية. أموالك تختفي.',
        'awareness_phishing': 'التصيد الاحتيالي', 'awareness_phishing_desc': 'رسائل بريد ومواقع وهمية تسرق كلمات المرور والبيانات المصرفية.',
        'awareness_impersonation': 'انتحال الهوية', 'awareness_impersonation_desc': 'مجرمون ينتحلون صفة الشرطة أو الحكومة أو الدعم الفني لسرقة الأموال.',
        'awareness_crypto': 'احتيال العملات الرقمية', 'awareness_crypto_desc': 'منصات تبادل وهمية وهببات وخطط بونزي في فضاء العملات الرقمية.',
        'awareness_tech': 'دعم فني وهمي', 'awareness_tech_desc': 'مكالمات وهمية من Microsoft/Apple للحصول على وصول عن بعد لجهازك.',
        'awareness_advance': 'احتيال الدفع المقدم', 'awareness_advance_desc': 'دفع رسوم مقدماً لفتح جائزة أو قرض أو ميراث غير موجود.',
        'cta_title': 'أبلغ عن احتيال في 17 ثانية', 'cta_desc': 'قدم شكوى الآن. نظامنا الآلي يبدأ التحقيق فوراً.',
        'cta_btn': 'تقديم شكوى', 'cta_btn2': 'فحص موقع',
        'footer_brand': 'GFIN — شبكة ذكاء الاحتيال العالمية',
        'footer_desc': 'منصة إنفاذ قانون دولية للكشف عن الاحتيال والتحقيق فيه ومنعه عبر الحدود. تربط 189 دولة لحماية المواطنين من الجرائم المالية.',
        'footer_services': 'الخدمات', 'footer_resources': 'الموارد', 'footer_legal': 'قانوني',
        'footer_privacy': 'سياسة الخصوصية', 'footer_terms': 'شروط الاستخدام', 'footer_gdpr': 'الامتثال للائحة حماية البيانات',
        'footer_data': 'حماية البيانات', 'footer_api_docs': 'توثيق API', 'footer_awareness': 'التوعية',
        'footer_telegram': 'بوت تيليجرام', 'footer_contact': 'اتصل بنا', 'footer_sitemap': 'خريطة الموقع',
        'footer_copyright': '© 2026 شبكة ذكاء الاحتيال العالمية. جميع الحقوق محفوظة.',
        'privacy_title': 'سياسة الخصوصية', 'privacy_subtitle': 'كيف يجمع GFIN بياناتك ويعالجها ويحميها',
        'privacy_back': '← العودة للرئيسية', 'privacy_updated': 'آخر تحديث: أغسطس 2026',
        'terms_title': 'شروط الاستخدام', 'terms_subtitle': 'الشروط والأحكام لاستخدام GFIN',
        'terms_back': '← العودة للرئيسية', 'terms_updated': 'آخر تحديث: أغسطس 2026',
        'contact_title': 'اتصل بـ GFIN', 'contact_subtitle': 'احصل على مساعدة في بلاغات الاحتيال أو المشاكل التقنية أو الوصول الشرطي',
        'contact_back': '← العودة للرئيسية',
        'contact_emergency_title': '⚠️ في خطر مباشر أو خسارة مالية؟',
        'contact_emergency_desc': 'اتصل بخدمات الطوارئ المحلية (999 / 112 / 911) أو بخط الاحتيال الوطني فوراً. يعالج GFIN البلاغات في 17 ثانية ولكنه ليس خدمة طوارئ.',
        'contact_telegram_title': '💬 بوت تيليجرام — أسرع رد',
        'contact_telegram_desc': 'تحقق مما إذا كان موقعاً ما احتيالاً، واحصل على تنبيهات ووصول لمواد التوعية',
        'contact_telegram_btn': 'فتح @GFINofficialbot →',
        'contact_channels_title': 'قنوات الاتصال',
        'contact_report': 'الإبلاغ عن احتيال', 'contact_report_desc': 'تقديم شكوى عبر الإنترنت',
        'contact_check': 'فحص موقع', 'contact_check_desc': 'البحث في قاعدة بيانات الاحتيال',
        'contact_police': 'دخول الشرطة', 'contact_police_desc': 'تسجيل دخول الشرطة',
        'apidocs_title': 'توثيق API', 'apidocs_subtitle': 'نقاط نهاية API العامة والشرطية لـ GFIN',
        'apidocs_back': '← العودة للرئيسية', 'apidocs_overview': 'نظرة عامة', 'apidocs_baseurl': 'عنوان URL الأساسي',
        'police_title': 'وصول شرطة آمن', 'police_subtitle': 'تسجيل دخول الضابط',
        'police_authorized': 'الموظفون المصرح لهم فقط. يتم تسجيل جميع عمليات الوصول.',
        'police_email': 'البريد الإلكتروني', 'police_password': 'كلمة المرور',
        'police_signin': 'تسجيل الدخول', 'police_encrypted': 'اتصال مشفر • مصادقة JWT',
        'police_register': 'التسجيل كضابط →', 'police_back': '← العودة لرئيسية GFIN',
        'police_warning': '⚠️ الدخول غير المصرح به جريمة',
        'police_firsttime': 'أول مرة؟ اتصل بمسؤول GFIN للتسجيل.',
        'scamsites_title': 'قاعدة بيانات مواقع الاحتيال', 'scamsites_search_placeholder': 'البحث عن نطاق أو نوع احتيال...',
        'scamsites_stats_total': 'إجمالي مواقع الاحتيال', 'scamsites_stats_verified': 'مواقع موثقة',
        'scamsites_stats_loss': 'إجمالي الخسائر', 'scamsites_stats_countries': 'الدول المتأثرة',
        'scamsites_table_domain': 'النطاق', 'scamsites_table_type': 'نوع الاحتيال', 'scamsites_table_risk': 'مستوى الخطر',
        'scamsites_table_reports': 'البلاغات', 'scamsites_table_loss': 'الخسارة المبلغ عنها',
        'scamsites_no_results': 'لم يتم العثور على مواقع احتيال', 'scamsites_back_home': 'العودة للرئيسية',
        'analytics_title': 'محرك تحليلات واستخبارات الاحتيال', 'analytics_subtitle': 'لوحة تحكم استخبارات الاحتيال في الوقت الفعلي',
        'analytics_total_complaints': 'إجمالي الشكاوى', 'analytics_active_cases': 'الحالات النشطة',
        'analytics_total_losses': 'إجمالي الخسائر', 'analytics_wallets_traced': 'المحافظ المتتبعة',
        'analytics_map_title': 'كثافة الشكاوى حسب الدولة', 'analytics_risk_breakdown': 'توزيع مستوى المخاطر',
        'analytics_refresh': 'تحديث البيانات', 'analytics_operational': 'النظام يعمل',
        'back_home': '← العودة للرئيسية'
      },

      zh: {
        'nav_home': '首页', 'nav_report': '举报诈骗', 'nav_scam_db': '诈骗数据库',
        'nav_awareness': '防范意识', 'nav_about': '关于', 'nav_police': '警察登录',
        'hero_badge': '🛡️ 官方政府级欺诈情报平台',
        'hero_title': '保护公民免受 ', 'hero_title_highlight': '全球欺诈',
        'hero_desc': '全球欺诈情报网络（GFIN）连接189个国家的执法机构，用于检测、调查和预防金融欺诈 — 从加密货币诈骗到跨国冒充网络。17秒内举报诈骗。',
        'hero_btn_report': '📝 举报诈骗', 'hero_btn_check': '🔍 检查网站',
        'stat_countries': '连接国家', 'stat_providers': '情报提供商',
        'stat_categories': '追踪的诈骗类别', 'stat_monitoring': '全天候监控',
        'how_title': 'GFIN 如何运作', 'how_subtitle': '从举报到调查只需17秒',
        'how_desc': '我们的自动化管道检测诈骗、收集证据，并将案件自动路由到正确的国家当局。',
        'step1_title': '举报诈骗', 'step1_desc': '受害者通过我们的安全门户以7种语言提交投诉。无需技术知识。',
        'step2_title': 'AI驱动检测', 'step2_desc': '我们的确定性引擎分析15个类别中300多种诈骗模式，以识别诈骗类型和风险等级。',
        'step3_title': '证据收集', 'step3_desc': '72个情报提供商自动收集证据 — 域名、钱包、IP地址、托管信息等。',
        'step4_title': '国家路由', 'step4_desc': '案件自动路由到正确的国家网络犯罪机构、国际刑警组织和欧洲刑警组织（欧盟国家）。',
        'services_title': '平台服务', 'services_subtitle': '全面的欺诈情报能力',
        'service1_title': '投诉提交', 'service1_desc': '安全的多语言门户，供受害者举报欺诈并上传文件，自动分配案件ID。',
        'service2_title': '诈骗检测引擎', 'service2_desc': '确定性v3.0引擎，涵盖15个类别中300多种模式。多语言检测（EN、ES、DE、FR）。',
        'service3_title': '加密货币追踪', 'service3_desc': '跨10种钱包类型和9条USDT链的多链加密货币追踪。追踪资金流向。',
        'service4_title': '情报手册', 'service4_desc': '从域名到物理地址追踪13种实体类型。带有SHA-256哈希的证据链。',
        'service5_title': '国家路由', 'service5_desc': '自动路由到189个国家网络犯罪机构、国际刑警组织和欧洲刑警组织。',
        'service6_title': 'Telegram警报', 'service6_desc': '通过@GFINofficialbot发布公开匿名诈骗警报和12种类型的防范广播。',
        'partners_eyebrow': '国际合作', 'partners_title': '连接全球执法机构',
        'partners_desc': 'GFIN将情报路由到国家网络犯罪部门、国际刑警组织和欧洲刑警组织 — 确保189个国家的跨境合作。',
        'awareness_eyebrow': '公众防范意识', 'awareness_title': '识别迹象 — 保护自己',
        'awareness_desc': 'GFIN追踪15个类别的欺诈。学习如何识别和避免每种类型。',
        'awareness_recovery': '追回诈骗', 'awareness_recovery_desc': '有人承诺追回之前因诈骗损失的钱。他们实际上是针对前受害者的骗子。',
        'awareness_romance': '浪漫诈骗', 'awareness_romance_desc': '虚假的网络恋爱关系，最终以索要金钱、加密货币或礼物告终。',
        'awareness_investment': '投资欺诈', 'awareness_investment_desc': '虚假交易平台承诺高回报。你的钱会消失。',
        'awareness_phishing': '网络钓鱼', 'awareness_phishing_desc': '虚假邮件和网站窃取你的密码和银行信息。',
        'awareness_impersonation': '冒充身份', 'awareness_impersonation_desc': '犯罪分子冒充警察、政府或技术支持来窃取钱财。',
        'awareness_crypto': '加密货币欺诈', 'awareness_crypto_desc': '加密领域的虚假交易所、拉地毯和庞氏骗局。',
        'awareness_tech': '技术支持诈骗', 'awareness_tech_desc': '虚假的Microsoft/Apple电话以获取对你电脑的远程访问权限。',
        'awareness_advance': '预付费诈骗', 'awareness_advance_desc': '预先支付费用以解锁不存在的奖品、贷款或遗产。',
        'cta_title': '17秒内举报诈骗', 'cta_desc': '立即提交投诉。我们的自动化系统立即开始调查。',
        'cta_btn': '提交投诉', 'cta_btn2': '检查网站',
        'footer_brand': 'GFIN — 全球欺诈情报网络',
        'footer_desc': '用于跨境欺诈检测、调查和预防的国际执法平台。连接189个国家以保护公民免受金融犯罪。',
        'footer_services': '服务', 'footer_resources': '资源', 'footer_legal': '法律',
        'footer_privacy': '隐私政策', 'footer_terms': '使用条款', 'footer_gdpr': 'GDPR合规',
        'footer_data': '数据保护', 'footer_api_docs': 'API文档', 'footer_awareness': '防范意识',
        'footer_telegram': 'Telegram机器人', 'footer_contact': '联系我们', 'footer_sitemap': '网站地图',
        'footer_copyright': '© 2026 全球欺诈情报网络。保留所有权利。',
        'privacy_title': '隐私政策', 'privacy_subtitle': 'GFIN如何收集、处理和保护您的数据',
        'privacy_back': '← 返回首页', 'privacy_updated': '最后更新：2026年8月',
        'terms_title': '使用条款', 'terms_subtitle': '使用GFIN的条款和条件',
        'terms_back': '← 返回首页', 'terms_updated': '最后更新：2026年8月',
        'contact_title': '联系GFIN', 'contact_subtitle': '获取欺诈举报、技术问题或执法访问方面的帮助',
        'contact_back': '← 返回首页',
        'contact_emergency_title': '⚠️ 处于紧急危险或财务损失中？',
        'contact_emergency_desc': '立即联系当地紧急服务（999 / 112 / 911）或国家欺诈热线。GFIN在17秒内处理投诉，但不是紧急服务。',
        'contact_telegram_title': '💬 Telegram机器人 — 最快响应',
        'contact_telegram_desc': '检查网站是否为诈骗，获取诈骗警报和防范材料',
        'contact_telegram_btn': '打开 @GFINofficialbot →',
        'contact_channels_title': '联系渠道',
        'contact_report': '举报诈骗', 'contact_report_desc': '在线提交投诉',
        'contact_check': '检查网站', 'contact_check_desc': '搜索诈骗数据库',
        'contact_police': '警察访问', 'contact_police_desc': '执法人员登录',
        'apidocs_title': 'API文档', 'apidocs_subtitle': 'GFIN的公开和执法API端点',
        'apidocs_back': '← 返回首页', 'apidocs_overview': '概述', 'apidocs_baseurl': '基础URL',
        'police_title': '执法安全访问', 'police_subtitle': '警官登录',
        'police_authorized': '仅限授权人员。所有访问均被记录。',
        'police_email': '电子邮件地址', 'police_password': '密码',
        'police_signin': '安全登录', 'police_encrypted': '加密连接 • JWT认证',
        'police_register': '注册为警官 →', 'police_back': '← 返回GFIN首页',
        'police_warning': '⚠️ 未经授权的访问是犯罪行为',
        'police_firsttime': '第一次？请联系您的GFIN管理员注册。',
        'scamsites_title': '诈骗网站数据库', 'scamsites_search_placeholder': '搜索域名或诈骗类型...',
        'scamsites_stats_total': '诈骗网站总数', 'scamsites_stats_verified': '已验证网站',
        'scamsites_stats_loss': '总损失', 'scamsites_stats_countries': '受影响国家',
        'scamsites_table_domain': '域名', 'scamsites_table_type': '诈骗类型', 'scamsites_table_risk': '风险等级',
        'scamsites_table_reports': '举报次数', 'scamsites_table_loss': '举报损失',
        'scamsites_no_results': '未找到诈骗网站', 'scamsites_back_home': '返回首页',
        'analytics_title': '欺诈情报与分析引擎', 'analytics_subtitle': '实时欺诈情报仪表板',
        'analytics_total_complaints': '总投诉量', 'analytics_active_cases': '活跃案件',
        'analytics_total_losses': '总损失', 'analytics_wallets_traced': '追踪的钱包',
        'analytics_map_title': '按国家的投诉密度', 'analytics_risk_breakdown': '风险等级分布',
        'analytics_refresh': '刷新数据', 'analytics_operational': '系统运行中',
        'back_home': '← 返回首页'
      },

      hi: {
        'nav_home': 'होम', 'nav_report': 'धोखाधड़ी रिपोर्ट करें', 'nav_scam_db': 'धोखाधड़ी डेटाबेस',
        'nav_awareness': 'जागरूकता', 'nav_about': 'बारे में', 'nav_police': 'पुलिस लॉगिन',
        'hero_badge': '🛡️ आधिकारिक सरकारी स्तर का धोखाधड़ी खुफिया प्लेटफॉर्म',
        'hero_title': 'नागरिकों को बचाना ', 'hero_title_highlight': 'वैश्विक धोखाधड़ी से',
        'hero_desc': 'ग्लोबल फ्रॉड इंटेलिजेंस नेटवर्क (GFIN) 189 देशों के कानून प्रवर्तन एजेंसियों को जोड़ता है ताकि वित्तीय धोखाधड़ी की पहचान, जांच और रोकथाम हो सके — क्रिप्टो घोटालों से लेकर सीमा पार प्रतिरूपण नेटवर्क तक। 17 सेकंड में धोखाधड़ी रिपोर्ट करें।',
        'hero_btn_report': '📝 धोखाधड़ी रिपोर्ट करें', 'hero_btn_check': '🔍 वेबसाइट जांचें',
        'stat_countries': 'जुड़े हुए देश', 'stat_providers': 'खुफिया प्रदाता',
        'stat_categories': 'ट्रैक की गई घोटाले की श्रेणियाँ', 'stat_monitoring': 'निरंतर निगरानी',
        'how_title': 'GFIN कैसे काम करता है', 'how_subtitle': 'शिकायत से जांच तक 17 सेकंड में',
        'how_desc': 'हमारी स्वचालित पाइपलाइन धोखाधड़ी का पता लगाती है, साक्ष्य एकत्र करती है, और मामलों को सही राष्ट्रीय अधिकारियों के पास भेजती है — स्वचालित रूप से।',
        'step1_title': 'धोखाधड़ी रिपोर्ट करें', 'step1_desc': 'पीड़ित हमारे सुरक्षित पोर्टल के माध्यम से 7 भाषाओं में शिकायत दर्ज करते हैं। तकनीकी ज्ञान आवश्यक नहीं।',
        'step2_title': 'AI-संचालित पहचान', 'step2_desc': 'हमारा नियतात्मक इंजन 15 श्रेणियों में 300+ घोटाले पैटर्न का विश्लेषण करता है।',
        'step3_title': 'साक्ष्य संग्रह', 'step3_desc': '72 खुफिया प्रदाता स्वचालित रूप से साक्ष्य एकत्र करते हैं — डोमेन, वॉलेट, IP पते, होस्टिंग जानकारी और बहुत कुछ।',
        'step4_title': 'देश रूटिंग', 'step4_desc': 'मामले स्वचालित रूप से सही राष्ट्रीय साइबरक्राइम प्राधिकरण, इंटरपोल और यूरोपोल (EU देशों के लिए) को भेजे जाते हैं।',
        'services_title': 'प्लेटफॉर्म सेवाएँ', 'services_subtitle': 'व्यापक धोखाधड़ी खुफिया क्षमताएँ',
        'service1_title': 'शिकायत दाखिल करना', 'service1_desc': 'पीड़ितों के लिए सुरक्षित बहुभाषी पोर्टल, फाइल अपलोड और स्वचालित केस ID असाइनमेंट के साथ।',
        'service2_title': 'घोटाला पहचान इंजन', 'service2_desc': 'नियतात्मक v3.0 इंजन, 15 श्रेणियों में 300+ पैटर्न के साथ। बहुभाषी पहचान (EN, ES, DE, FR)।',
        'service3_title': 'क्रिप्टो ट्रैकिंग', 'service3_desc': '10 वॉलेट प्रकार और 9 USDT चेन में मल्टी-चेन क्रिप्टोकरेंसी ट्रैकिंग। पैसे का पीछा करें।',
        'service4_title': 'खुफिया प्लेबुक', 'service4_desc': 'डोमेन से भौतिक पते तक 13 इकाई प्रकार ट्रैक किए गए। SHA-256 हैशिंग के साथ साक्ष्य श्रृंखला।',
        'service5_title': 'देश रूटिंग', 'service5_desc': '189 राष्ट्रीय साइबरक्राइम प्राधिकरणों, इंटरपोल और यूरोपोल को स्वचालित रूटिंग।',
        'service6_title': 'टेलीग्राम अलर्ट', 'service6_desc': '@GFINofficialbot के माध्यम से सार्वजनिक गुमनाम धोखाधड़ी अलर्ट और 12-प्रकार के जागरूकता प्रसारण।',
        'partners_eyebrow': 'अंतर्राष्ट्रीय सहयोग', 'partners_title': 'वैश्विक कानून प्रवर्तन से जुड़ा',
        'partners_desc': 'GFIN राष्ट्रीय साइबरक्राइम इकाइयों, इंटरपोल और यूरोपोल को खुफिया जानकारी भेजता है — 189 देशों में सीमा पार सहयोग सुनिश्चित करता है।',
        'awareness_eyebrow': 'सार्वजनिक जागरूकता', 'awareness_title': 'संकेत पहचानें — खुद को बचाएँ',
        'awareness_desc': 'GFIN धोखाधड़ी की 15 श्रेणियों को ट्रैक करता है। प्रत्येक प्रकार को पहचानना और बचना सीखें।',
        'awareness_recovery': 'रिकवरी घोटाले', 'awareness_recovery_desc': 'कोई पहले खोए हुए पैसे वापस दिलाने का वादा करता है। वे पिछले पीड़ितों को निशाना बनाने वाले ठग हैं।',
        'awareness_romance': 'रोमांस घोटाले', 'awareness_romance_desc': 'फेक ऑनलाइन रिश्ते जो पैसे, क्रिप्टो या उपहारों की मांग पर खत्म होते हैं।',
        'awareness_investment': 'निवेश धोखाधड़ी', 'awareness_investment_desc': 'फेक ट्रेडिंग प्लेटफॉर्म जो उच्च रिटर्न का वादा करते हैं। आपका पैसा गायब हो जाता है।',
        'awareness_phishing': 'फिशिंग', 'awareness_phishing_desc': 'फेक ईमेल और वेबसाइटें जो आपके पासवर्ड और बैंकिंग विवरण चुराती हैं।',
        'awareness_impersonation': 'प्रतिरूपण', 'awareness_impersonation_desc': 'पैसे चुराने के लिए पुलिस, सरकार या तकनीकी सहायता का रूप धारण करने वाले अपराधी।',
        'awareness_crypto': 'क्रिप्टो धोखाधड़ी', 'awareness_crypto_desc': 'क्रिप्टो स्पेस में फेक एक्सचेंज, रग पुल और पोंजी स्कीम।',
        'awareness_tech': 'फेक तकनीकी सहायता', 'awareness_tech_desc': 'आपके कंप्यूटर तक दूरस्थ पहुँच प्राप्त करने के लिए फेक Microsoft/Apple कॉल।',
        'awareness_advance': 'अग्रिम शुल्क घोटाले', 'awareness_advance_desc': 'ऐसा इनाम, ऋण या विरासत जो मौजूद नहीं है, उसे अनलॉक करने के लिए पहले शुल्क का भुगतान करना।',
        'cta_title': '17 सेकंड में धोखाधड़ी रिपोर्ट करें', 'cta_desc': 'अभी शिकायत दर्ज करें। हमारी स्वचालित प्रणाली तुरंत जांच शुरू करती है।',
        'cta_btn': 'शिकायत दर्ज करें', 'cta_btn2': 'वेबसाइट जांचें',
        'footer_brand': 'GFIN — ग्लोबल फ्रॉड इंटेलिजेंस नेटवर्क',
        'footer_desc': 'सीमा पार धोखाधड़ी पहचान, जांच और रोकथाम के लिए एक अंतर्राष्ट्रीय कानून प्रवर्तन प्लेटफॉर्म। 189 देशों को जोड़ते हुए वित्तीय अपराध से नागरिकों की रक्षा।',
        'footer_services': 'सेवाएँ', 'footer_resources': 'संसाधन', 'footer_legal': 'कानूनी',
        'footer_privacy': 'गोपनीयता नीति', 'footer_terms': 'उपयोग की शर्तें', 'footer_gdpr': 'GDPR अनुपालन',
        'footer_data': 'डेटा सुरक्षा', 'footer_api_docs': 'API दस्तावेज़', 'footer_awareness': 'जागरूकता',
        'footer_telegram': 'टेलीग्राम बॉट', 'footer_contact': 'संपर्क', 'footer_sitemap': 'साइटमैप',
        'footer_copyright': '© 2026 ग्लोबल फ्रॉड इंटेलिजेंस नेटवर्क। सर्वाधिकार सुरक्षित।',
        'privacy_title': 'गोपनीयता नीति', 'privacy_subtitle': 'GFIN आपका डेटा कैसे एकत्र, प्रोसेस और सुरक्षित करता है',
        'privacy_back': '← होम पर वापस', 'privacy_updated': 'अंतिम अपडेट: अगस्त 2026',
        'terms_title': 'उपयोग की शर्तें', 'terms_subtitle': 'GFIN का उपयोग करने के लिए नियम और शर्तें',
        'terms_back': '← होम पर वापस', 'terms_updated': 'अंतिम अपडेट: अगस्त 2026',
        'contact_title': 'GFIN से संपर्क करें', 'contact_subtitle': 'धोखाधड़ी रिपोर्ट, तकनीकी समस्याओं या पुलिस पहुँच में सहायता प्राप्त करें',
        'contact_back': '← होम पर वापस',
        'contact_emergency_title': '⚠️ तत्काल खतरे या वित्तीय नुकसान में हैं?',
        'contact_emergency_desc': 'तुरंत अपनी स्थानीय आपातकालीन सेवाओं (999 / 112 / 911) या राष्ट्रीय धोखाधड़ी हॉटलाइन से संपर्क करें। GFIN 17 सेकंड में शिकायतों को संसाधित करता है लेकिन आपातकालीन सेवा नहीं है।',
        'contact_telegram_title': '💬 टेलीग्राम बॉट — सबसे तेज़ प्रतिक्रिया',
        'contact_telegram_desc': 'जांचें कि वेबसाइट धोखाधड़ी है या नहीं, अलर्ट प्राप्त करें और जागरूकता सामग्री तक पहुँच प्राप्त करें',
        'contact_telegram_btn': '@GFINofficialbot खोलें →',
        'contact_channels_title': 'संपर्क चैनल',
        'contact_report': 'धोखाधड़ी रिपोर्ट करें', 'contact_report_desc': 'ऑनलाइन शिकायत दर्ज करें',
        'contact_check': 'वेबसाइट जांचें', 'contact_check_desc': 'धोखाधड़ी डेटाबेस में खोजें',
        'contact_police': 'पुलिस पहुँच', 'contact_police_desc': 'कानून प्रवर्तन लॉगिन',
        'apidocs_title': 'API दस्तावेज़', 'apidocs_subtitle': 'GFIN के लिए सार्वजनिक और कानून प्रवर्तन API एंडपॉइंट',
        'apidocs_back': '← होम पर वापस', 'apidocs_overview': 'अवलोकन', 'apidocs_baseurl': 'बेस URL',
        'police_title': 'पुलिस सुरक्षित पहुँच', 'police_subtitle': 'पुलिस अधिकारी लॉगिन',
        'police_authorized': 'केवल अधिकृत व्यक्ति। सभी पहुँच लॉग की जाती है।',
        'police_email': 'ईमेल पता', 'police_password': 'पासवर्ड',
        'police_signin': 'सुरक्षित रूप से साइन इन करें', 'police_encrypted': 'एन्क्रिप्टेड कनेक्शन • JWT प्रमाणीकृत',
        'police_register': 'अधिकारी के रूप में पंजीकरण करें →', 'police_back': '← GFIN होम पर वापस',
        'police_warning': '⚠️ अनधिकृत पहुँच एक आपराधिक अपराध है',
        'police_firsttime': 'पहली बार? पंजीकरण के लिए अपने GFIN व्यवस्थापक से संपर्क करें।',
        'scamsites_title': 'धोखाधड़ी वेबसाइट डेटाबेस', 'scamsites_search_placeholder': 'डोमेन या घोटाले का प्रकार खोजें...',
        'scamsites_stats_total': 'कुल धोखाधड़ी साइटें', 'scamsites_stats_verified': 'सत्यापित साइटें',
        'scamsites_stats_loss': 'कुल नुकसान', 'scamsites_stats_countries': 'प्रभावित देश',
        'scamsites_table_domain': 'डोमेन', 'scamsites_table_type': 'घोटाले का प्रकार', 'scamsites_table_risk': 'जोखिम स्तर',
        'scamsites_table_reports': 'रिपोर्ट', 'scamsites_table_loss': 'रिपोर्ट किया गया नुकसान',
        'scamsites_no_results': 'कोई धोखाधड़ी साइट नहीं मिली', 'scamsites_back_home': 'होम पर वापस',
        'analytics_title': 'धोखाधड़ी खुफिया और विश्लेषण इंजन', 'analytics_subtitle': 'रीयल-टाइम धोखाधड़ी खुफिया डैशबोर्ड',
        'analytics_total_complaints': 'कुल शिकायतें', 'analytics_active_cases': 'सक्रिय मामले',
        'analytics_total_losses': 'कुल नुकसान', 'analytics_wallets_traced': 'ट्रैक किए गए वॉलेट',
        'analytics_map_title': 'देश के अनुसार शिकायत घनत्व', 'analytics_risk_breakdown': 'जोखिम स्तर वितरण',
        'analytics_refresh': 'डेटा रिफ्रेश करें', 'analytics_operational': 'सिस्टम संचालित',
        'back_home': '← होम पर वापस'
      }
    },

    langNames: {
      en: '🇬🇧 English', es: '🇪🇸 Español', de: '🇩🇪 Deutsch',
      fr: '🇫🇷 Français', ar: '🇸🇦 العربية', zh: '🇨🇳 中文', hi: '🇮🇳 हिन्दी'
    },

    langCodes: ['en', 'es', 'de', 'fr', 'ar', 'zh', 'hi'],

    getLangFromURL: function() {
      var params = new URLSearchParams(window.location.search);
      var lang = params.get('lang');
      if (lang && this.langCodes.indexOf(lang) >= 0) return lang;
      return null;
    },

    getLangFromStorage: function() {
      var saved = localStorage.getItem('gfin_lang');
      if (saved && this.langCodes.indexOf(saved) >= 0) return saved;
      return null;
    },

    translatePage: function(lang) {
      if (!this.translations[lang]) lang = 'en';
      var t = this.translations[lang];
      this.currentLang = lang;
      document.documentElement.lang = lang;
      document.documentElement.dir = (lang === 'ar') ? 'rtl' : 'ltr';
      document.querySelectorAll('[data-i18n]').forEach(function(el) {
        var key = el.getAttribute('data-i18n');
        if (t[key]) el.innerHTML = t[key];
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-placeholder');
        if (t[key]) el.placeholder = t[key];
      });
      var titleEl = document.querySelector('[data-i18n-title]');
      if (titleEl) { var key = titleEl.getAttribute('data-i18n-title'); if (t[key]) document.title = t[key]; }
      var langDisplay = document.getElementById('currentLang');
      if (langDisplay) langDisplay.textContent = lang.toUpperCase();
      localStorage.setItem('gfin_lang', lang);
    },

    setLanguage: function(lang) {
      this.translatePage(lang);
      var url = new URL(window.location.href);
      if (lang !== 'en') url.searchParams.set('lang', lang);
      else url.searchParams.delete('lang');
      window.history.replaceState({}, '', url.toString());
      var dropdown = document.getElementById('langDropdown');
      if (dropdown) dropdown.classList.remove('show');
    },

    createLangSwitcher: function() {
      var self = this;
      var dropdown = document.getElementById('langDropdown');
      if (!dropdown) return;
      var html = '';
      this.langCodes.forEach(function(code) {
        html += '<a class="lang-item" data-lang="' + code + '" style="display:block;padding:8px 16px;color:inherit;text-decoration:none;font-size:13px;cursor:pointer;border:none;background:none;width:100%;text-align:left">' + self.langNames[code] + '</a>';
      });
      dropdown.innerHTML = html;
      var items = dropdown.querySelectorAll('.lang-item');
      items.forEach(function(item) {
        item.addEventListener('click', function() { self.setLanguage(item.getAttribute('data-lang')); });
      });
      document.addEventListener('click', function(e) {
        if (dropdown && !dropdown.contains(e.target) && e.target.id !== 'langBtn') {
          dropdown.classList.remove('show');
        }
      });
    },

    init: function() {
      var lang = this.getLangFromURL() || this.getLangFromStorage() || 'en';
      this.translatePage(lang);
      this.createLangSwitcher();
    }
  };

  window.GFIN_i18n = GFIN_i18n;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { GFIN_i18n.init(); });
  } else {
    GFIN_i18n.init();
  }
})();


// === VICTIM PORTAL TRANSLATIONS ===

// Added victim portal keys for en
if (typeof translations["en"] !== "undefined") translations["en"]["victim_app_name"] = "GFIN";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step1_name"] = "Your Info";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step2_name"] = "Scam Details";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step3_name"] = "Evidence";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step4_name"] = "Review & Submit";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step1_title"] = "Step 1: Victim Contact Information";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step2_title"] = "Step 2: Fraud & Incident Details";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step3_title"] = "Step 3: Upload Evidence & Proofs";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_step4_title"] = "Step 4: Review & Submit Report";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_name"] = "Full Name (Optional)";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_email"] = "Email Address (Required for status updates) *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_phone"] = "Phone Number (Optional)";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_country"] = "Country of Residence *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_scam_type"] = "Scam / Fraud Category *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_target"] = "Scam Target / Scammer Identifier *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_loss_amount"] = "Financial Loss Amount *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_currency"] = "Currency *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_incident_date"] = "Date of Incident *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_description"] = "Detailed Scam Description *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_evidence"] = "Upload Evidence Files (Optional)";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_consent"] = "I confirm the information provided is accurate and consent to GFIN processing this data for fraud investigation purposes.";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_success_title"] = "Complaint Filed Successfully!";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_next_steps_header"] = "What Happens Next?";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_status_search_title"] = "Track Complaint Status";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_lbl_ref_input"] = "Case Reference Number *";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_btn_prev"] = "Previous";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_btn_next"] = "Next";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_btn_submit"] = "Submit Complaint";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_btn_search_status"] = "Track";
if (typeof translations["en"] !== "undefined") translations["en"]["victim_footer"] = "© 2026 GFIN - Global Fraud Intelligence Network. Confidential Victim Complaint Portal.";

// Added victim portal keys for es
if (typeof translations["es"] !== "undefined") translations["es"]["victim_app_name"] = "GFIN";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step1_name"] = "Tu Información";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step2_name"] = "Detalles de la Estafa";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step3_name"] = "Evidencia";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step4_name"] = "Revisar y Enviar";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step1_title"] = "Paso 1: Información de Contacto de la Víctima";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step2_title"] = "Paso 2: Detalles del Fraude y del Incidente";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step3_title"] = "Paso 3: Subir Evidencia y Pruebas";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_step4_title"] = "Paso 4: Revisar y Enviar Reporte";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_name"] = "Nombre Completo (Opcional)";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_email"] = "Correo Electrónico (Requerido para actualizaciones) *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_phone"] = "Número de Teléfono (Opcional)";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_country"] = "País de Residencia *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_scam_type"] = "Categoría de Estafa / Fraude *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_target"] = "Objetivo de la Estafa / Identificador del Estafador *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_loss_amount"] = "Monto de Pérdida Financiera *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_currency"] = "Moneda *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_incident_date"] = "Fecha del Incidente *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_description"] = "Descripción Detallada de la Estafa *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_evidence"] = "Subir Archivos de Evidencia (Opcional)";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_consent"] = "Confirmo que la información proporcionada es precisa y doy mi consentimiento para que GFIN procese estos datos con fines de investigación de fraude.";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_success_title"] = "¡Denuncia Presentada con Éxito!";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_next_steps_header"] = "¿Qué Sucede Ahora?";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_status_search_title"] = "Rastrear Estado de la Denuncia";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_lbl_ref_input"] = "Número de Referencia del Caso *";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_btn_prev"] = "Anterior";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_btn_next"] = "Siguiente";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_btn_submit"] = "Enviar Denuncia";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_btn_search_status"] = "Rastrear";
if (typeof translations["es"] !== "undefined") translations["es"]["victim_footer"] = "© 2026 GFIN - Red Global de Inteligencia de Fraude. Portal Confidencial de Denuncias de Víctimas.";

// Added victim portal keys for de
if (typeof translations["de"] !== "undefined") translations["de"]["victim_app_name"] = "GFIN";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step1_name"] = "Ihre Informationen";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step2_name"] = "Betrugsdetails";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step3_name"] = "Beweise";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step4_name"] = "Prüfen & Senden";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step1_title"] = "Schritt 1: Kontaktinformationen des Opfers";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step2_title"] = "Schritt 2: Betrugs- & Vorfallsdetails";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step3_title"] = "Schritt 3: Beweise & Nachweise Hochladen";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_step4_title"] = "Schritt 4: Bericht Prüfen & Senden";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_name"] = "Vollständiger Name (Optional)";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_email"] = "E-Mail-Adresse (Erforderlich für Statusaktualisierungen) *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_phone"] = "Telefonnummer (Optional)";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_country"] = "Wohnsitzland *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_scam_type"] = "Betrugs- / Fraud-Kategorie *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_target"] = "Betrugsziel / Betrüger-Identifikator *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_loss_amount"] = "Finanzieller Verlustbetrag *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_currency"] = "Währung *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_incident_date"] = "Datum des Vorfalls *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_description"] = "Detaillierte Betrugsbeschreibung *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_evidence"] = "Beweisdateien Hochladen (Optional)";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_consent"] = "Ich bestätige, dass die bereitgestellten Informationen korrekt sind, und stimme zu, dass GFIN diese Daten für Betrugsuntersuchungen verarbeitet.";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_success_title"] = "Beschreibung Erfolgreich Eingereicht!";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_next_steps_header"] = "Was Passiert Als Nächstes?";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_status_search_title"] = "Beschwerdstatus Verfolgen";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_lbl_ref_input"] = "Fall-Referenznummer *";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_btn_prev"] = "Zurück";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_btn_next"] = "Weiter";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_btn_submit"] = "Beschreibung Einreichen";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_btn_search_status"] = "Verfolgen";
if (typeof translations["de"] !== "undefined") translations["de"]["victim_footer"] = "© 2026 GFIN - Globales Betrugsintelligenz-Netzwerk. Vertrauliches Opfer-Beschwerdeportal.";

// Added victim portal keys for fr
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_app_name"] = "GFIN";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step1_name"] = "Vos Informations";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step2_name"] = "Détails de l'Arnaque";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step3_name"] = "Preuves";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step4_name"] = "Vérifier & Soumettre";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step1_title"] = "Étape 1: Informations de Contact de la Victime";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step2_title"] = "Étape 2: Détails de la Fraude et de l'Incident";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step3_title"] = "Étape 3: Télécharger les Preuves et les Justificatifs";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_step4_title"] = "Étape 4: Vérifier et Soumettre le Rapport";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_name"] = "Nom Complet (Optionnel)";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_email"] = "Adresse E-mail (Requis pour les mises à jour) *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_phone"] = "Numéro de Téléphone (Optionnel)";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_country"] = "Pays de Résidence *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_scam_type"] = "Catégorie d'Arnaque / Fraude *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_target"] = "Cible de l'Arnaque / Identifiant de l'Escroc *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_loss_amount"] = "Montant de la Perte Financière *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_currency"] = "Devise *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_incident_date"] = "Date de l'Incident *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_description"] = "Description Détaillée de l'Arnaque *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_evidence"] = "Télécharger les Fichiers de Preuve (Optionnel)";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_consent"] = "Je confirme que les informations fournies sont exactes et consens à ce que GFIN traite ces données à des fins d'investigation de fraude.";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_success_title"] = "Plainte Déposée avec Succès !";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_next_steps_header"] = "Que Se Passe-t-il Ensuite ?";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_status_search_title"] = "Suivre le Statut de la Plainte";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_lbl_ref_input"] = "Numéro de Référence du Cas *";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_btn_prev"] = "Précédent";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_btn_next"] = "Suivant";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_btn_submit"] = "Soumettre la Plainte";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_btn_search_status"] = "Suivre";
if (typeof translations["fr"] !== "undefined") translations["fr"]["victim_footer"] = "© 2026 GFIN - Réseau Mondial d'Intelligence contre la Fraude. Portail Confidentiel de Plaintes des Victimes.";

// Added victim portal keys for it
if (typeof translations["it"] !== "undefined") translations["it"]["victim_app_name"] = "GFIN";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step1_name"] = "Le Tue Info";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step2_name"] = "Dettagli Truffa";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step3_name"] = "Prove";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step4_name"] = "Rivedi & Invia";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step1_title"] = "Passo 1: Informazioni di Contatto della Vittima";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step2_title"] = "Passo 2: Dettagli della Frode e dell'Incidente";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step3_title"] = "Passo 3: Carica Prove e Documentazioni";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_step4_title"] = "Passo 4: Rivedi e Invia il Rapporto";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_name"] = "Nome Completo (Opzionale)";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_email"] = "Indirizzo Email (Richiesto per aggiornamenti) *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_phone"] = "Numero di Telefono (Opzionale)";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_country"] = "Paese di Residenza *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_scam_type"] = "Categoria di Truffa / Frode *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_target"] = "Obiettivo della Truffa / Identificatore del Truffatore *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_loss_amount"] = "Importo della Perdita Finanziaria *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_currency"] = "Valuta *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_incident_date"] = "Data dell'Incidente *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_description"] = "Descrizione Dettagliata della Truffa *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_evidence"] = "Carica File di Prova (Opzionale)";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_consent"] = "Confermo che le informazioni fornite sono accurate e acconsento al trattamento di questi dati da parte di GFIN per scopi di indagine sulla frode.";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_success_title"] = "Denuncia Inviata con Successo!";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_next_steps_header"] = "Cosa Succede Dopo?";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_status_search_title"] = "Traccia lo Stato della Denuncia";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_lbl_ref_input"] = "Numero di Riferimento del Caso *";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_btn_prev"] = "Precedente";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_btn_next"] = "Successivo";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_btn_submit"] = "Invia Denuncia";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_btn_search_status"] = "Traccia";
if (typeof translations["it"] !== "undefined") translations["it"]["victim_footer"] = "© 2026 GFIN - Rete Globale di Intelligence sulle Frodi. Portale Confidenziale delle Denunce delle Vittime.";

// Added victim portal keys for pt
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_app_name"] = "GFIN";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step1_name"] = "Suas Informações";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step2_name"] = "Detalhes da Fraude";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step3_name"] = "Evidências";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step4_name"] = "Revisar & Enviar";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step1_title"] = "Passo 1: Informações de Contato da Vítima";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step2_title"] = "Passo 2: Detalhes da Fraude e do Incidente";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step3_title"] = "Passo 3: Carregar Evidências e Provas";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_step4_title"] = "Passo 4: Revisar e Enviar o Relatório";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_name"] = "Nome Completo (Opcional)";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_email"] = "Endereço de E-mail (Necessário para atualizações) *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_phone"] = "Número de Telefone (Opcional)";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_country"] = "País de Residência *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_scam_type"] = "Categoria de Fraude / Golpe *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_target"] = "Alvo da Fraude / Identificador do Golpista *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_loss_amount"] = "Valor da Perda Financeira *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_currency"] = "Moeda *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_incident_date"] = "Data do Incidente *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_description"] = "Descrição Detalhada da Fraude *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_evidence"] = "Carregar Arquivos de Evidência (Opcional)";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_consent"] = "Confirmo que as informações fornecidas são precisas e consinto que a GFIN processe estes dados para fins de investigação de fraude.";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_success_title"] = "Denúncia Apresentada com Sucesso!";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_next_steps_header"] = "O Que Acontece Agora?";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_status_search_title"] = "Acompanhar o Status da Denúncia";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_lbl_ref_input"] = "Número de Referência do Caso *";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_btn_prev"] = "Anterior";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_btn_next"] = "Próximo";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_btn_submit"] = "Enviar Denúncia";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_btn_search_status"] = "Acompanhar";
if (typeof translations["pt"] !== "undefined") translations["pt"]["victim_footer"] = "© 2026 GFIN - Rede Global de Inteligência contra Fraudes. Portal Confidencial de Denúncias de Vítimas.";

// Added victim portal keys for pl
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_app_name"] = "GFIN";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step1_name"] = "Twoje Dane";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step2_name"] = "Szczegóły Oszustwa";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step3_name"] = "Dowody";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step4_name"] = "Sprawdź & Wyślij";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step1_title"] = "Krok 1: Dane Kontaktowe Ofiary";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step2_title"] = "Krok 2: Szczegóły Oszustwa i Incydentu";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step3_title"] = "Krok 3: Prześlij Dowody i Materialy";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_step4_title"] = "Krok 4: Sprawdź i Wyślij Zgłoszenie";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_name"] = "Pełne Imię i Nazwisko (Opcjonalnie)";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_email"] = "Adres E-mail (Wymagany do aktualizacji statusu) *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_phone"] = "Numer Telefonu (Opcjonalnie)";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_country"] = "Kraj Zamieszkania *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_scam_type"] = "Kategoria Oszustwa / Nadużycia *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_target"] = "Cel Oszustwa / Identyfikator Oszusta *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_loss_amount"] = "Kwota Straty Finansowej *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_currency"] = "Waluta *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_incident_date"] = "Data Incydentu *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_description"] = "Szczegółowy Opis Oszustwa *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_evidence"] = "Prześlij Pliki Dowodowe (Opcjonalnie)";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_consent"] = "Potwierdzam, że podane informacje są dokładne i wyrażam zgodę na przetwarzanie tych danych przez GFIN w celu śledztwa oszustw.";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_success_title"] = "Skarga Złożona Pomyślnie!";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_next_steps_header"] = "Co Teraz?";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_status_search_title"] = "Śledź Status Skargi";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_lbl_ref_input"] = "Numer Referencyjny Sprawy *";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_btn_prev"] = "Wstecz";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_btn_next"] = "Dalej";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_btn_submit"] = "Złóż Skargę";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_btn_search_status"] = "Śledź";
if (typeof translations["pl"] !== "undefined") translations["pl"]["victim_footer"] = "© 2026 GFIN - Globalna Sieć Wywiadu ds. Oszustw. Poufny Portal Skarg Ofiar.";

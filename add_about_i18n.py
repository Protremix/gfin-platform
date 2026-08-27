#!/usr/bin/env python3
"""Add about_ i18n keys to gfin-i18n.js"""

content = open("/gfin/gfin-i18n.js").read()

if "about_hero_desc" in content:
    print("About keys already exist")
    exit(0)

en_about = """        'about_hero_desc': 'The Global Fraud Intelligence Network connects law enforcement agencies across 189 countries to detect, investigate, and prevent financial fraud.',
        'about_mission_desc': 'GFIN bridges the gap between citizens, national cybercrime units, and international bodies.',
        'about_mission_detect': 'Detect',
        'about_mission_detect_desc': 'Our deterministic engine analyzes 300+ scam patterns across 15 categories in multiple languages.',
        'about_mission_investigate': 'Investigate',
        'about_mission_investigate_desc': '72 intelligence providers automatically gather evidence.',
        'about_mission_prevent': 'Prevent',
        'about_mission_prevent_desc': 'Public awareness broadcasts and real-time Telegram alerts keep citizens informed.',
        'about_tech_desc': 'Built on a zero-trust security architecture with end-to-end encryption and GDPR-compliant data handling.',"""

es_about = """        'about_hero_desc': 'La Red Global de Inteligencia de Fraude conecta agencias en 189 paises para detectar, investigar y prevenir el fraude financiero.',
        'about_mission_desc': 'GFIN une a ciudadanos y unidades nacionales de ciberdelincuencia con organismos internacionales.',
        'about_mission_detect': 'Detectar',
        'about_mission_detect_desc': 'Nuestro motor analiza mas de 300 patrones de estafa en 15 categorias en multiples idiomas.',
        'about_mission_investigate': 'Investigar',
        'about_mission_investigate_desc': '72 proveedores de inteligencia recopilan evidencia automaticamente.',
        'about_mission_prevent': 'Prevenir',
        'about_mission_prevent_desc': 'Difusion de conciencia publica y alertas de Telegram mantienen a los ciudadanos informados.',
        'about_tech_desc': 'Construido sobre arquitectura de confianza cero con cifrado y manejo de datos conforme al GDPR.',"""

de_about = """        'about_hero_desc': 'Das Global Fraud Intelligence Network verbindet Behorden in 189 Landern zur Aufdeckung und Verhinderung von Finanzbetrug.',
        'about_mission_desc': 'GFIN verbindet Burger, nationale Cybercrime-Einheiten und internationale Organisationen.',
        'about_mission_detect': 'Erkennen',
        'about_mission_detect_desc': 'Unsere Engine analysiert uber 300 Betrugsmuster in 15 Kategorien in mehreren Sprachen.',
        'about_mission_investigate': 'Untersuchen',
        'about_mission_investigate_desc': '72 Inteligenz-Anbieter sammeln automatisch Beweise.',
        'about_mission_prevent': 'Verhindern',
        'about_mission_prevent_desc': 'Offentliche Aufklarung und Echtzeit-Telegram-Warnungen halten Burger informiert.',
        'about_tech_desc': 'Built on Zero-Trust-Architektur mit End-to-End-Verschlusselung und DSGVO-konformer Datenverarbeitung.',"""

fr_about = """        'about_hero_desc': 'Le Reseau Mondial de Renseignement sur la Fraude connecte les agences dans 189 pays pour detecter et prevenir la fraude financiere.',
        'about_mission_desc': 'GFIN relie les citoyens, les unites nationales de cybercriminalite et les organismes internationaux.',
        'about_mission_detect': 'Detecter',
        'about_mission_detect_desc': 'Notre moteur analyse plus de 300 modeles d arnaque dans 15 categories en plusieurs langues.',
        'about_mission_investigate': 'Enqueter',
        'about_mission_investigate_desc': '72 fournisseurs de renseignements collectent automatiquement des preuves.',
        'about_mission_prevent': 'Prevenir',
        'about_mission_prevent_desc': 'Diffusion de sensibilisation publique et alertes Telegram informent les citoyens.',
        'about_tech_desc': 'Architecture de confiance zero avec chiffrement et traitement des donnees conforme au RGPD.',"""

# Find the last awareness_advance line in each language and add about_ keys after it
# English
content = content.replace(
    "        'awareness_advance': 'Advance Fee', 'awareness_advance_desc': 'Pay a fee upfront to unlock a prize, loan, or inheritance that does not exist.',",
    "        'awareness_advance': 'Advance Fee', 'awareness_advance_desc': 'Pay a fee upfront to unlock a prize, loan, or inheritance that does not exist.',\n" + en_about
)

# Spanish
content = content.replace(
    "        'awareness_advance': 'Estafa de Pago Adelantado', 'awareness_advance_desc': 'Pague una tarifa por adelantado para desbloquear un premio,",
    "        'awareness_advance': 'Estafa de Pago Adelantado', 'awareness_advance_desc': 'Pague una tarifa por adelantado para desbloquear un premio,",
)

# German
content = content.replace(
    "        'awareness_advance': 'Vorauszahlungsbetrug', 'awareness_advance_desc': 'Zahlen Sie eine Gebuehr im Voraus,",
    "        'awareness_advance': 'Vorauszahlungsbetrug', 'awareness_advance_desc': 'Zahlen Sie eine Gebuehr im Voraus,",
)

# French
content = content.replace(
    "        'awareness_advance': 'Avance de Frais', 'awareness_advance_desc': 'Payez des frais a",
    "        'awareness_advance': 'Avance de Frais', 'awareness_advance_desc': 'Payez des frais a",
)

# Let me try a different approach - find the end of each language section and insert
# Actually, let me find lines containing awareness_advance and insert after them
lines = content.split("\n")
new_lines = []
for line in lines:
    new_lines.append(line)
    if "awareness_advance" in line and "about_hero_desc" not in line:
        # Determine which language section we're in
        if "Advance Fee" in line:
            new_lines.append(en_about)
        elif "Estafa de Pago" in line:
            new_lines.append(es_about)
        elif "Vorauszahlungsbetrug" in line:
            new_lines.append(de_about)
        elif "Avance de Frais" in line:
            new_lines.append(fr_about)

content = "\n".join(new_lines)
open("/gfin/gfin-i18n.js", "w").write(content)
count = content.count("about_")
print(f"About i18n keys added: {count} occurrences")
print(f"File: {len(content.splitlines())} lines")

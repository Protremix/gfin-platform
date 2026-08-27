"""
Add data-i18n attributes to victim portal HTML and translation keys to i18n JS.
"""
import re

# Read the HTML
with open("/gfin/victim_portal_i18n.html", "r") as f:
    html = f.read()

# Map of txt- IDs to data-i18n keys
id_to_i18n = {
    "txt-appName": "victim_app_name",
    "txt-step1Name": "victim_step1_name",
    "txt-step2Name": "victim_step2_name",
    "txt-step3Name": "victim_step3_name",
    "txt-step4Name": "victim_step4_name",
    "txt-step1Title": "victim_step1_title",
    "txt-step2Title": "victim_step2_title",
    "txt-step3Title": "victim_step3_title",
    "txt-step4Title": "victim_step4_title",
    "txt-lblVictimName": "victim_lbl_name",
    "txt-lblVictimEmail": "victim_lbl_email",
    "txt-lblVictimPhone": "victim_lbl_phone",
    "txt-lblCountry": "victim_lbl_country",
    "txt-lblScamType": "victim_lbl_scam_type",
    "txt-lblTarget": "victim_lbl_target",
    "txt-lblLossAmount": "victim_lbl_loss_amount",
    "txt-lblCurrency": "victim_lbl_currency",
    "txt-lblIncidentDate": "victim_lbl_incident_date",
    "txt-lblDescription": "victim_lbl_description",
    "txt-lblEvidence": "victim_lbl_evidence",
    "txt-lblConsent": "victim_lbl_consent",
    "txt-successTitle": "victim_success_title",
    "txt-nextStepsHeader": "victim_next_steps_header",
    "txt-statusSearchTitle": "victim_status_search_title",
    "txt-lblRefInput": "victim_lbl_ref_input",
}

# Button IDs
button_ids = {
    "btnPrev": "victim_btn_prev",
    "btnNext": "victim_btn_next",
    "btnSubmit": "victim_btn_submit",
    "btnSearchStatusSubmit": "victim_btn_search_status",
}

# Add data-i18n attributes to elements with txt- IDs
count = 0
for element_id, i18n_key in {**id_to_i18n, **button_ids}.items():
    # Pattern: id="element_id" (with or without other attributes)
    pattern = f'id="{element_id}"'
    replacement = f'id="{element_id}" data-i18n="{i18n_key}"'
    
    if pattern in html and f'data-i18n="{i18n_key}"' not in html:
        html = html.replace(pattern, replacement)
        count += 1

# Also add data-i18n to the footer
footer_pattern = '<p>&copy; 2026 GFIN'
footer_replacement = '<p data-i18n="victim_footer">&copy; 2026 GFIN'
if footer_pattern in html and 'data-i18n="victim_footer"' not in html:
    html = html.replace(footer_pattern, footer_replacement)
    count += 1

# Write updated HTML
with open("/gfin/victim_portal_i18n.html", "w") as f:
    f.write(html)

print(f"Added {count} data-i18n attributes to victim portal HTML")

# Now add translation keys to gfin-i18n.js
with open("/gfin/gfin-i18n.js", "r") as f:
    i18n = f.read()

# Translation dictionary for all 7 languages
translations = {
    "en": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Your Info",
        "victim_step2_name": "Scam Details",
        "victim_step3_name": "Evidence",
        "victim_step4_name": "Review & Submit",
        "victim_step1_title": "Step 1: Victim Contact Information",
        "victim_step2_title": "Step 2: Fraud & Incident Details",
        "victim_step3_title": "Step 3: Upload Evidence & Proofs",
        "victim_step4_title": "Step 4: Review & Submit Report",
        "victim_lbl_name": "Full Name (Optional)",
        "victim_lbl_email": "Email Address (Required for status updates) *",
        "victim_lbl_phone": "Phone Number (Optional)",
        "victim_lbl_country": "Country of Residence *",
        "victim_lbl_scam_type": "Scam / Fraud Category *",
        "victim_lbl_target": "Scam Target / Scammer Identifier *",
        "victim_lbl_loss_amount": "Financial Loss Amount *",
        "victim_lbl_currency": "Currency *",
        "victim_lbl_incident_date": "Date of Incident *",
        "victim_lbl_description": "Detailed Scam Description *",
        "victim_lbl_evidence": "Upload Evidence Files (Optional)",
        "victim_lbl_consent": "I confirm the information provided is accurate and consent to GFIN processing this data for fraud investigation purposes.",
        "victim_success_title": "Complaint Filed Successfully!",
        "victim_next_steps_header": "What Happens Next?",
        "victim_status_search_title": "Track Complaint Status",
        "victim_lbl_ref_input": "Case Reference Number *",
        "victim_btn_prev": "Previous",
        "victim_btn_next": "Next",
        "victim_btn_submit": "Submit Complaint",
        "victim_btn_search_status": "Track",
        "victim_footer": "\u00a9 2026 GFIN - Global Fraud Intelligence Network. Confidential Victim Complaint Portal.",
    },
    "es": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Tu Informaci\u00f3n",
        "victim_step2_name": "Detalles de la Estafa",
        "victim_step3_name": "Evidencia",
        "victim_step4_name": "Revisar y Enviar",
        "victim_step1_title": "Paso 1: Informaci\u00f3n de Contacto de la V\u00edctima",
        "victim_step2_title": "Paso 2: Detalles del Fraude y del Incidente",
        "victim_step3_title": "Paso 3: Subir Evidencia y Pruebas",
        "victim_step4_title": "Paso 4: Revisar y Enviar Reporte",
        "victim_lbl_name": "Nombre Completo (Opcional)",
        "victim_lbl_email": "Correo Electr\u00f3nico (Requerido para actualizaciones) *",
        "victim_lbl_phone": "N\u00famero de Tel\u00e9fono (Opcional)",
        "victim_lbl_country": "Pa\u00eds de Residencia *",
        "victim_lbl_scam_type": "Categor\u00eda de Estafa / Fraude *",
        "victim_lbl_target": "Objetivo de la Estafa / Identificador del Estafador *",
        "victim_lbl_loss_amount": "Monto de P\u00e9rdida Financiera *",
        "victim_lbl_currency": "Moneda *",
        "victim_lbl_incident_date": "Fecha del Incidente *",
        "victim_lbl_description": "Descripci\u00f3n Detallada de la Estafa *",
        "victim_lbl_evidence": "Subir Archivos de Evidencia (Opcional)",
        "victim_lbl_consent": "Confirmo que la informaci\u00f3n proporcionada es precisa y doy mi consentimiento para que GFIN procese estos datos con fines de investigaci\u00f3n de fraude.",
        "victim_success_title": "\u00a1Denuncia Presentada con \u00c9xito!",
        "victim_next_steps_header": "\u00bfQu\u00e9 Sucede Ahora?",
        "victim_status_search_title": "Rastrear Estado de la Denuncia",
        "victim_lbl_ref_input": "N\u00famero de Referencia del Caso *",
        "victim_btn_prev": "Anterior",
        "victim_btn_next": "Siguiente",
        "victim_btn_submit": "Enviar Denuncia",
        "victim_btn_search_status": "Rastrear",
        "victim_footer": "\u00a9 2026 GFIN - Red Global de Inteligencia de Fraude. Portal Confidencial de Denuncias de V\u00edctimas.",
    },
    "de": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Ihre Informationen",
        "victim_step2_name": "Betrugsdetails",
        "victim_step3_name": "Beweise",
        "victim_step4_name": "Pr\u00fcfen & Senden",
        "victim_step1_title": "Schritt 1: Kontaktinformationen des Opfers",
        "victim_step2_title": "Schritt 2: Betrugs- & Vorfallsdetails",
        "victim_step3_title": "Schritt 3: Beweise & Nachweise Hochladen",
        "victim_step4_title": "Schritt 4: Bericht Pr\u00fcfen & Senden",
        "victim_lbl_name": "Vollst\u00e4ndiger Name (Optional)",
        "victim_lbl_email": "E-Mail-Adresse (Erforderlich f\u00fcr Statusaktualisierungen) *",
        "victim_lbl_phone": "Telefonnummer (Optional)",
        "victim_lbl_country": "Wohnsitzland *",
        "victim_lbl_scam_type": "Betrugs- / Fraud-Kategorie *",
        "victim_lbl_target": "Betrugsziel / Betr\u00fcger-Identifikator *",
        "victim_lbl_loss_amount": "Finanzieller Verlustbetrag *",
        "victim_lbl_currency": "W\u00e4hrung *",
        "victim_lbl_incident_date": "Datum des Vorfalls *",
        "victim_lbl_description": "Detaillierte Betrugsbeschreibung *",
        "victim_lbl_evidence": "Beweisdateien Hochladen (Optional)",
        "victim_lbl_consent": "Ich best\u00e4tige, dass die bereitgestellten Informationen korrekt sind, und stimme zu, dass GFIN diese Daten f\u00fcr Betrugsuntersuchungen verarbeitet.",
        "victim_success_title": "Beschreibung Erfolgreich Eingereicht!",
        "victim_next_steps_header": "Was Passiert Als N\u00e4chstes?",
        "victim_status_search_title": "Beschwerdstatus Verfolgen",
        "victim_lbl_ref_input": "Fall-Referenznummer *",
        "victim_btn_prev": "Zur\u00fcck",
        "victim_btn_next": "Weiter",
        "victim_btn_submit": "Beschreibung Einreichen",
        "victim_btn_search_status": "Verfolgen",
        "victim_footer": "\u00a9 2026 GFIN - Globales Betrugsintelligenz-Netzwerk. Vertrauliches Opfer-Beschwerdeportal.",
    },
    "fr": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Vos Informations",
        "victim_step2_name": "D\u00e9tails de l'Arnaque",
        "victim_step3_name": "Preuves",
        "victim_step4_name": "V\u00e9rifier & Soumettre",
        "victim_step1_title": "\u00c9tape 1: Informations de Contact de la Victime",
        "victim_step2_title": "\u00c9tape 2: D\u00e9tails de la Fraude et de l'Incident",
        "victim_step3_title": "\u00c9tape 3: T\u00e9l\u00e9charger les Preuves et les Justificatifs",
        "victim_step4_title": "\u00c9tape 4: V\u00e9rifier et Soumettre le Rapport",
        "victim_lbl_name": "Nom Complet (Optionnel)",
        "victim_lbl_email": "Adresse E-mail (Requis pour les mises \u00e0 jour) *",
        "victim_lbl_phone": "Num\u00e9ro de T\u00e9l\u00e9phone (Optionnel)",
        "victim_lbl_country": "Pays de R\u00e9sidence *",
        "victim_lbl_scam_type": "Cat\u00e9gorie d'Arnaque / Fraude *",
        "victim_lbl_target": "Cible de l'Arnaque / Identifiant de l'Escroc *",
        "victim_lbl_loss_amount": "Montant de la Perte Financi\u00e8re *",
        "victim_lbl_currency": "Devise *",
        "victim_lbl_incident_date": "Date de l'Incident *",
        "victim_lbl_description": "Description D\u00e9taill\u00e9e de l'Arnaque *",
        "victim_lbl_evidence": "T\u00e9l\u00e9charger les Fichiers de Preuve (Optionnel)",
        "victim_lbl_consent": "Je confirme que les informations fournies sont exactes et consens \u00e0 ce que GFIN traite ces donn\u00e9es \u00e0 des fins d'investigation de fraude.",
        "victim_success_title": "Plainte D\u00e9pos\u00e9e avec Succ\u00e8s !",
        "victim_next_steps_header": "Que Se Passe-t-il Ensuite ?",
        "victim_status_search_title": "Suivre le Statut de la Plainte",
        "victim_lbl_ref_input": "Num\u00e9ro de R\u00e9f\u00e9rence du Cas *",
        "victim_btn_prev": "Pr\u00e9c\u00e9dent",
        "victim_btn_next": "Suivant",
        "victim_btn_submit": "Soumettre la Plainte",
        "victim_btn_search_status": "Suivre",
        "victim_footer": "\u00a9 2026 GFIN - R\u00e9seau Mondial d'Intelligence contre la Fraude. Portail Confidentiel de Plaintes des Victimes.",
    },
    "it": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Le Tue Info",
        "victim_step2_name": "Dettagli Truffa",
        "victim_step3_name": "Prove",
        "victim_step4_name": "Rivedi & Invia",
        "victim_step1_title": "Passo 1: Informazioni di Contatto della Vittima",
        "victim_step2_title": "Passo 2: Dettagli della Frode e dell'Incidente",
        "victim_step3_title": "Passo 3: Carica Prove e Documentazioni",
        "victim_step4_title": "Passo 4: Rivedi e Invia il Rapporto",
        "victim_lbl_name": "Nome Completo (Opzionale)",
        "victim_lbl_email": "Indirizzo Email (Richiesto per aggiornamenti) *",
        "victim_lbl_phone": "Numero di Telefono (Opzionale)",
        "victim_lbl_country": "Paese di Residenza *",
        "victim_lbl_scam_type": "Categoria di Truffa / Frode *",
        "victim_lbl_target": "Obiettivo della Truffa / Identificatore del Truffatore *",
        "victim_lbl_loss_amount": "Importo della Perdita Finanziaria *",
        "victim_lbl_currency": "Valuta *",
        "victim_lbl_incident_date": "Data dell'Incidente *",
        "victim_lbl_description": "Descrizione Dettagliata della Truffa *",
        "victim_lbl_evidence": "Carica File di Prova (Opzionale)",
        "victim_lbl_consent": "Confermo che le informazioni fornite sono accurate e acconsento al trattamento di questi dati da parte di GFIN per scopi di indagine sulla frode.",
        "victim_success_title": "Denuncia Inviata con Successo!",
        "victim_next_steps_header": "Cosa Succede Dopo?",
        "victim_status_search_title": "Traccia lo Stato della Denuncia",
        "victim_lbl_ref_input": "Numero di Riferimento del Caso *",
        "victim_btn_prev": "Precedente",
        "victim_btn_next": "Successivo",
        "victim_btn_submit": "Invia Denuncia",
        "victim_btn_search_status": "Traccia",
        "victim_footer": "\u00a9 2026 GFIN - Rete Globale di Intelligence sulle Frodi. Portale Confidenziale delle Denunce delle Vittime.",
    },
    "pt": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Suas Informa\u00e7\u00f5es",
        "victim_step2_name": "Detalhes da Fraude",
        "victim_step3_name": "Evid\u00eancias",
        "victim_step4_name": "Revisar & Enviar",
        "victim_step1_title": "Passo 1: Informa\u00e7\u00f5es de Contato da V\u00edtima",
        "victim_step2_title": "Passo 2: Detalhes da Fraude e do Incidente",
        "victim_step3_title": "Passo 3: Carregar Evid\u00eancias e Provas",
        "victim_step4_title": "Passo 4: Revisar e Enviar o Relat\u00f3rio",
        "victim_lbl_name": "Nome Completo (Opcional)",
        "victim_lbl_email": "Endere\u00e7o de E-mail (Necess\u00e1rio para atualiza\u00e7\u00f5es) *",
        "victim_lbl_phone": "N\u00famero de Telefone (Opcional)",
        "victim_lbl_country": "Pa\u00eds de Resid\u00eancia *",
        "victim_lbl_scam_type": "Categoria de Fraude / Golpe *",
        "victim_lbl_target": "Alvo da Fraude / Identificador do Golpista *",
        "victim_lbl_loss_amount": "Valor da Perda Financeira *",
        "victim_lbl_currency": "Moeda *",
        "victim_lbl_incident_date": "Data do Incidente *",
        "victim_lbl_description": "Descri\u00e7\u00e3o Detalhada da Fraude *",
        "victim_lbl_evidence": "Carregar Arquivos de Evid\u00eancia (Opcional)",
        "victim_lbl_consent": "Confirmo que as informa\u00e7\u00f5es fornecidas s\u00e3o precisas e consinto que a GFIN processe estes dados para fins de investiga\u00e7\u00e3o de fraude.",
        "victim_success_title": "Den\u00fancia Apresentada com Sucesso!",
        "victim_next_steps_header": "O Que Acontece Agora?",
        "victim_status_search_title": "Acompanhar o Status da Den\u00fancia",
        "victim_lbl_ref_input": "N\u00famero de Refer\u00eancia do Caso *",
        "victim_btn_prev": "Anterior",
        "victim_btn_next": "Pr\u00f3ximo",
        "victim_btn_submit": "Enviar Den\u00fancia",
        "victim_btn_search_status": "Acompanhar",
        "victim_footer": "\u00a9 2026 GFIN - Rede Global de Intelig\u00eancia contra Fraudes. Portal Confidencial de Den\u00fancias de V\u00edtimas.",
    },
    "pl": {
        "victim_app_name": "GFIN",
        "victim_step1_name": "Twoje Dane",
        "victim_step2_name": "Szczeg\u00f3\u0142y Oszustwa",
        "victim_step3_name": "Dowody",
        "victim_step4_name": "Sprawd\u017a & Wy\u015blij",
        "victim_step1_title": "Krok 1: Dane Kontaktowe Ofiary",
        "victim_step2_title": "Krok 2: Szczeg\u00f3\u0142y Oszustwa i Incydentu",
        "victim_step3_title": "Krok 3: Prze\u015blij Dowody i Materialy",
        "victim_step4_title": "Krok 4: Sprawd\u017a i Wy\u015blij Zg\u0142oszenie",
        "victim_lbl_name": "Pe\u0142ne Imi\u0119 i Nazwisko (Opcjonalnie)",
        "victim_lbl_email": "Adres E-mail (Wymagany do aktualizacji statusu) *",
        "victim_lbl_phone": "Numer Telefonu (Opcjonalnie)",
        "victim_lbl_country": "Kraj Zamieszkania *",
        "victim_lbl_scam_type": "Kategoria Oszustwa / Nadu\u017cycia *",
        "victim_lbl_target": "Cel Oszustwa / Identyfikator Oszusta *",
        "victim_lbl_loss_amount": "Kwota Straty Finansowej *",
        "victim_lbl_currency": "Waluta *",
        "victim_lbl_incident_date": "Data Incydentu *",
        "victim_lbl_description": "Szczeg\u00f3\u0142owy Opis Oszustwa *",
        "victim_lbl_evidence": "Prze\u015blij Pliki Dowodowe (Opcjonalnie)",
        "victim_lbl_consent": "Potwierdzam, \u017ce podane informacje s\u0105 dok\u0142adne i wyra\u017cam zgod\u0119 na przetwarzanie tych danych przez GFIN w celu \u015bledztwa oszustw.",
        "victim_success_title": "Skarga Z\u0142o\u017cona Pomy\u015blnie!",
        "victim_next_steps_header": "Co Teraz?",
        "victim_status_search_title": "\u015aled\u017a Status Skargi",
        "victim_lbl_ref_input": "Numer Referencyjny Sprawy *",
        "victim_btn_prev": "Wstecz",
        "victim_btn_next": "Dalej",
        "victim_btn_submit": "Z\u0142\u00f3\u017c Skarg\u0119",
        "victim_btn_search_status": "\u015aled\u017a",
        "victim_footer": "\u00a9 2026 GFIN - Globalna Sie\u0107 Wywiadu ds. Oszustw. Poufny Portal Skarg Ofiar.",
    },
}

# Build the JS code to add to gfin-i18n.js
# Find the structure of the i18n file and add victim keys to each language
js_addition = "\n\n// === VICTIM PORTAL TRANSLATIONS ===\n"

for lang, keys in translations.items():
    js_addition += f"\n// Added victim portal keys for {lang}\n"
    for key, value in keys.items():
        # Escape quotes in value
        escaped = value.replace('"', '\\"')
        js_addition += f'if (typeof translations["{lang}"] !== "undefined") translations["{lang}"]["{key}"] = "{escaped}";\n'

# Write updated i18n file
with open("/gfin/gfin-i18n.js", "a") as f:
    f.write(js_addition)

print(f"Added {len(translations['en'])} translation keys x 7 languages = {len(translations) * len(translations['en'])} translations to i18n file")
print("Done!")

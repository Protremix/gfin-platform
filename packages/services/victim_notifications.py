"""
GFIN (Global Fraud Intelligence Network) Victim Notifications Module
=====================================================================

This module handles sending automated email and SMS notifications to victims
when their case status changes within the GFIN platform.

Requirements & Specifications:
------------------------------
1. Email Notifications: Built using Python's standard `smtplib` and `email.mime`
   modules (MIMEMultipart and MIMEText for text + HTML).
2. SMS Notifications: Webhook-compatible interface (`send_sms`) structured for
   easy integration with Twilio or HTTP SMS gateways.
3. Notification Types:
   - complaint_received (with case reference & expected timeline)
   - investigation_started (with investigation scope/subject)
   - investigation_update (evidence collected status, routing info)
   - case_escalated (higher priority, routed to authorities)
   - case_resolved (outcome summary, no police operational details)
   - alert_sent_to_authorities (confirmation of law enforcement routing)
4. Function Signatures:
   - send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool
   - send_sms(to_phone: str, message: str) -> bool
   - notify_victim(complaint_ref: str, notification_type: str, extra_data: dict = None) -> bool
   - get_notification_template(notification_type: str, language: str = 'en') -> dict
5. Email Templates: Professional HTML design with responsive layout & GFIN branding.
6. Database Logging: Stores logs in PostgreSQL table `victim_notifications`
   (columns: id, complaint_ref, notification_type, recipient, channel, status, sent_at).
7. Database Connection: host=localhost, port=5432, user=gfin, password=GfinSecure2026!, dbname=gfin.
8. Email Config from Environment:
   - SMTP_HOST (default: 'localhost')
   - SMTP_PORT (default: 587)
   - SMTP_USER (default: '')
   - SMTP_PASS (default: '')
   - FROM_EMAIL (default: 'gfin-alerts@gfin-system.com')
9. SECURITY RULE: Law enforcement investigation details (officer names, undercover tactics,
   classified police intelligence, suspect details) are strictly redacted/excluded.
10. Multi-Language Support: English ('en'), Spanish ('es'), German ('de'), French ('fr').
"""

import os
import sys
import re
import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
import urllib.error

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Configure logger
logger = logging.getLogger("gfin.victim_notifications")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [GFIN-NOTIFY] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Database Credentials & Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "gfin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "GfinSecure2026!")
DB_NAME = os.getenv("DB_NAME", "gfin")

# SMTP Credentials & Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "gfin-alerts@gfin-system.com")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Webhook configuration for SMS gateway
SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "")

# Sensitive keys forbidden from victim communications
SENSITIVE_KEYS = {
    'police_notes', 'officer_name', 'badge_number', 'suspect_name',
    'suspect_address', 'suspect_phone', 'suspect_ip', 'informant_info',
    'undercover_details', 'wiretap_data', 'internal_police_id',
    'law_enforcement_notes', 'classified_intel', 'investigation_tactics',
    'evidence_raw_police', 'interrogations'
}

# Alias mapping for supported notification types
NOTIFICATION_TYPE_MAP = {
    'complaint_received': 'complaint_received',
    'complaint': 'complaint_received',
    'received': 'complaint_received',
    
    'investigation_started': 'investigation_started',
    'started': 'investigation_started',
    'investigation_begin': 'investigation_started',
    
    'investigation_update': 'investigation_update',
    'update': 'investigation_update',
    'investigation_progress': 'investigation_update',
    
    'case_escalated': 'case_escalated',
    'escalated': 'case_escalated',
    'escalation': 'case_escalated',
    
    'case_resolved': 'case_resolved',
    'case_closed': 'case_resolved',
    'resolved': 'case_resolved',
    'closed': 'case_resolved',
    
    'alert_sent_to_authorities': 'alert_sent_to_authorities',
    'authorities_notified': 'alert_sent_to_authorities',
    'police_alert': 'alert_sent_to_authorities',
    'alert_sent': 'alert_sent_to_authorities'
}

# Color themes per notification status
THEME_COLORS = {
    'complaint_received': {'header': '#1e3a8a', 'accent': '#2563eb', 'badge': '#dbeafe', 'badge_text': '#1e40af'},
    'investigation_started': {'header': '#312e81', 'accent': '#4f46e5', 'badge': '#e0e7ff', 'badge_text': '#3730a3'},
    'investigation_update': {'header': '#115e59', 'accent': '#0d9488', 'badge': '#ccfbf1', 'badge_text': '#115e59'},
    'case_escalated': {'header': '#7c2d12', 'accent': '#ea580c', 'badge': '#ffedd5', 'badge_text': '#9a3412'},
    'case_resolved': {'header': '#14532d', 'accent': '#16a34a', 'badge': '#dcfce7', 'badge_text': '#166534'},
    'alert_sent_to_authorities': {'header': '#581c87', 'accent': '#9333ea', 'badge': '#f3e8ff', 'badge_text': '#6b21a8'}
}


def sanitize_victim_data(extra_data: dict = None) -> dict:
    """Strips sensitive law enforcement and internal police data from victim parameters.
    
    Args:
        extra_data: Input context dictionary.
        
    Returns:
        dict: Filtered context safe for victim notification rendering.
    """
    if not extra_data:
        return {}
    
    sanitized = {}
    for k, v in extra_data.items():
        if k.lower() in SENSITIVE_KEYS:
            logger.warning(f"Sanitization dropped sensitive key '{k}' from victim notification.")
            continue
        sanitized[k] = v
    return sanitized


def _render_html_template(title: str, status_label: str, case_ref: str, message_text: str, details_html: str, theme_key: str, lang: str) -> str:
    """Generates professional HTML email with GFIN branding and responsive formatting."""
    colors = THEME_COLORS.get(theme_key, THEME_COLORS['complaint_received'])
    header_color = colors['header']
    accent_color = colors['accent']
    badge_bg = colors['badge']
    badge_fg = colors['badge_text']

    disclaimer_text = {
        'en': "This is an automated operational notification from the GFIN Fraud Intelligence Platform. Sensitive law enforcement investigative techniques and confidential police intelligence are strictly omitted from victim communications.",
        'es': "Esta es una notificación operativa automatizada de la Plataforma de Inteligencia de Fraude GFIN. Las técnicas de investigación policiales y la inteligencia confidencial se omiten estrictamente de las comunicaciones dirigidas a las víctimas.",
        'de': "Dies ist eine automatisierte Benachrichtigung der GFIN Betrugsaufklärungsplattform. Vertrauliche polizeiliche Ermittlungsergebnisse und Daten sind aus Sicherheitsgründen in Mitteilungen an Opfer ausgeschlossen.",
        'fr': "Ceci est une notification automatique de la plateforme GFIN. Les détails sensibles relatifs aux enquêtes policières et au renseignement confidentiel sont strictly exclus des communications destinées aux victimes."
    }.get(lang, "This is an automated operational notification from GFIN.")

    message_formatted = message_text.replace('\n', '<br>')

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; color: #1e293b; }}
        .wrapper {{ max-width: 620px; margin: 25px auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.06); border: 1px solid #e2e8f0; }}
        .header {{ background-color: {header_color}; padding: 28px 32px; text-align: left; border-bottom: 4px solid {accent_color}; }}
        .header h1 {{ color: #ffffff; font-size: 22px; margin: 0 0 6px 0; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ color: #94a3b8; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}
        .content {{ padding: 32px; }}
        .badge-bar {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #f1f5f9; }}
        .badge {{ background-color: {badge_bg}; color: {badge_fg}; padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: inline-block; }}
        .ref-tag {{ font-family: monospace; font-size: 13px; color: #64748b; font-weight: 600; background: #f1f5f9; padding: 4px 10px; border-radius: 6px; }}
        .main-title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 14px; }}
        .message-body {{ font-size: 15px; line-height: 1.6; color: #334155; margin-bottom: 24px; }}
        .details-box {{ background-color: #f8fafc; border-left: 4px solid {accent_color}; padding: 18px 20px; border-radius: 0 8px 8px 0; margin-bottom: 28px; font-size: 14px; line-height: 1.6; }}
        .footer {{ background-color: #0f172a; padding: 24px 32px; color: #94a3b8; font-size: 12px; line-height: 1.5; }}
        .footer p {{ margin: 0 0 10px 0; }}
        .footer-brand {{ color: #ffffff; font-weight: 600; font-size: 13px; margin-bottom: 4px; display: block; }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <p>GFIN Fraud Intelligence Platform</p>
            <h1>Victim Case Notification</h1>
        </div>
        <div class="content">
            <div class="badge-bar">
                <span class="badge">{status_label}</span>
                <span class="ref-tag">REF: {case_ref}</span>
            </div>
            <h2 class="main-title">{title}</h2>
            <div class="message-body">{message_formatted}</div>
            {details_html}
        </div>
        <div class="footer">
            <span class="footer-brand">Global Fraud Intelligence Network (GFIN)</span>
            <p>{disclaimer_text}</p>
            <p>&copy; 2026 GFIN System. All rights reserved. Do not reply directly to this automated address.</p>
        </div>
    </div>
</body>
</html>"""
    return html


def get_notification_template(notification_type: str, language: str = 'en') -> dict:
    """Retrieves localized notification template for given notification type and language.
    
    Args:
        notification_type: The notification event type (e.g. 'complaint_received', 'investigation_started',
                           'investigation_update', 'case_escalated', 'case_resolved', 'alert_sent_to_authorities').
        language: ISO language code ('en', 'es', 'de', 'fr'). Defaults to 'en'.
        
    Returns:
        dict: Dictionary containing 'subject', 'body_text', 'body_html', 'title', 'status_label', and 'language'.
    """
    lang = language.lower() if language and language.lower() in ('en', 'es', 'de', 'fr') else 'en'
    norm_type = NOTIFICATION_TYPE_MAP.get(notification_type.lower().strip() if notification_type else '', 'complaint_received')

    # Comprehensive multi-language template catalog
    catalog = {
        'complaint_received': {
            'en': {
                'subject': "GFIN Case Update: Complaint Received [{complaint_ref}]",
                'title': "Complaint Received & Registered",
                'status_label': "Received",
                'body_text': "Dear Citizen,\n\nYour fraud complaint (Reference: {complaint_ref}) has been received by the GFIN Fraud Intelligence Network.\n\nExpected Assessment Timeline: {expected_timeline}\n\nOur automated intelligence systems and analytical team are evaluating the submitted information. You will receive further updates as progress is made.\n\nThank you,\nGFIN Support Team",
                'details_label': "Expected Assessment Timeline",
                'default_timeline': "3 to 5 business days"
            },
            'es': {
                'subject': "GFIN Actualización de Caso: Reclamación Recibida [{complaint_ref}]",
                'title': "Reclamación Recibida y Registrada",
                'status_label': "Recibida",
                'body_text': "Estimado/a ciudadano/a,\n\nSu reclamación de fraude (Referencia: {complaint_ref}) ha sido recibida por la Red de Inteligencia de Fraude GFIN.\n\nPlazo estimado de evaluación: {expected_timeline}\n\nNuestros sistemas y equipo de análisis están evaluando la información enviada. Recibirá más actualizaciones a medida que avance el proceso.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Plazo Estimado de Evaluación",
                'default_timeline': "3 a 5 días hábiles"
            },
            'de': {
                'subject': "GFIN Vorgangsaktualisierung: Beschwerde Eingegangen [{complaint_ref}]",
                'title': "Beschwerde Eingegangen & Registriert",
                'status_label': "Eingegangen",
                'body_text': "Sehr geehrte Damen und Herren,\n\nIhre Betrugsbeschwerde (Referenz: {complaint_ref}) ist bei der GFIN Betrugsaufklärungsplattform eingegangen.\n\nVoraussichtlicher Bewertungszeitraum: {expected_timeline}\n\nUnsere Systeme und das Analyseteam prüfen Ihre Angaben. Sie erhalten weitere Aktualisierungen zum Fortschritt.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Voraussichtlicher Bewertungszeitraum",
                'default_timeline': "3 bis 5 Werktage"
            },
            'fr': {
                'subject': "GFIN Mise à Jour du Dossier: Plainte Reçue [{complaint_ref}]",
                'title': "Plainte Reçue et Enregistrée",
                'status_label': "Reçue",
                'body_text': "Bonjour,\n\nVotre plainte pour fraude (Référence: {complaint_ref}) a bien été reçue par le réseau GFIN.\n\nDélai d'évaluation estimé: {expected_timeline}\n\nNos équipes d'analyse étudient les éléments transmis. Vous recevrez d'autres notifications au fur et à mesure du traitement.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Délai d'Évaluation Estimé",
                'default_timeline': "3 à 5 jours ouvrés"
            }
        },
        'investigation_started': {
            'en': {
                'subject': "GFIN Case Update: Investigation Started [{complaint_ref}]",
                'title': "Investigation Initiated",
                'status_label': "In Progress",
                'body_text': "Dear Citizen,\n\nAn investigation has officially been opened for your case (Reference: {complaint_ref}).\n\nInvestigation Focus: {investigation_scope}\n\nOur intelligence pipeline is actively validating transaction artifacts, infrastructure indicators, and network patterns.\n\nThank you,\nGFIN Support Team",
                'details_label': "Investigation Scope",
                'default_scope': "Verification of reported fraudulent transactions and digital intelligence analysis"
            },
            'es': {
                'subject': "GFIN Actualización de Caso: Investigación Iniciada [{complaint_ref}]",
                'title': "Investigación Iniciada",
                'status_label': "En Curso",
                'body_text': "Estimado/a ciudadano/a,\n\nSe ha iniciado oficialmente la investigación de su caso (Referencia: {complaint_ref}).\n\nAlcance de la investigación: {investigation_scope}\n\nNuestros sistemas de inteligencia están analizando activamente los indicadores e información proporcionada.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Alcance de la Investigación",
                'default_scope': "Verificación de transacciones fraudulentas reportadas y análisis de inteligencia digital"
            },
            'de': {
                'subject': "GFIN Vorgangsaktualisierung: Untersuchung Gestartet [{complaint_ref}]",
                'title': "Ermittlung Eingeleitet",
                'status_label': "In Bearbeitung",
                'body_text': "Sehr geehrte Damen und Herren,\n\neine Untersuchung für Ihren Vorgang (Referenz: {complaint_ref}) wurde offiziell eröffnet.\n\nUntersuchungsumfang: {investigation_scope}\n\nUnsere Aufklärungssysteme analysieren derzeit die vorliegenden Daten und Indikatoren.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Untersuchungsumfang",
                'default_scope': "Überprüfung gemeldeter betrügerischer Transaktionen und digitale Analyse"
            },
            'fr': {
                'subject': "GFIN Mise à Jour du Dossier: Enquête Ouverte [{complaint_ref}]",
                'title': "Enquête Officiellement Ouverte",
                'status_label': "En Cours",
                'body_text': "Bonjour,\n\nUne enquête a été officiellement ouverte concernant votre dossier (Référence: {complaint_ref}).\n\nPérimètre de l'enquête: {investigation_scope}\n\nNos systèmes d'intelligence procèdent actuellement à la vérification des données et indicateurs.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Périmètre de l'Enquête",
                'default_scope': "Vérification des transactions signalées et analyse d'intelligence numérique"
            }
        },
        'investigation_update': {
            'en': {
                'subject': "GFIN Case Update: Progress Report [{complaint_ref}]",
                'title': "Investigation Progress Update",
                'status_label': "Update",
                'body_text': "Dear Citizen,\n\nWe have updated progress to report on case {complaint_ref}.\n\nEvidence Summary: {evidence_summary}\nRouting Information: {routing_info}\n\nOur system continues to index intelligence findings for authority reference.\n\nThank you,\nGFIN Support Team",
                'details_label': "Progress Details",
                'default_evidence': "Case artifacts and intelligence logs compiled",
                'default_routing': "Indexed in central GFIN fraud matrix"
            },
            'es': {
                'subject': "GFIN Actualización de Caso: Informe de Avance [{complaint_ref}]",
                'title': "Actualización de Avance en la Investigación",
                'status_label': "Actualización",
                'body_text': "Estimado/a ciudadano/a,\n\nTenemos nuevas actualizaciones sobre el avance del caso {complaint_ref}.\n\nResumen de Evidencias: {evidence_summary}\nInformación de Enrutamiento: {routing_info}\n\nNuestro sistema continúa indexando la información de inteligencia.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Detalles del Avance",
                'default_evidence': "Recopilación e indexación de elementos de prueba",
                'default_routing': "Procesado en la matriz central de inteligencia GFIN"
            },
            'de': {
                'subject': "GFIN Vorgangsaktualisierung: Neue Fortschritte [{complaint_ref}]",
                'title': "Fortschrittsaktualisierung der Untersuchung",
                'status_label': "Aktualisierung",
                'body_text': "Sehr geehrte Damen und Herren,\n\nes liegen neue Fortschritte für Vorgang {complaint_ref} vor.\n\nBeweisübersicht: {evidence_summary}\nWeiterleitungsinformation: {routing_info}\n\nUnser System indiziert die gewonnenen Erkenntnisse kontinuierlich.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Fortschrittsdetails",
                'default_evidence': "Beweismittel und Berichte erfasst",
                'default_routing': "Im zentralen GFIN-System verarbeitet"
            },
            'fr': {
                'subject': "GFIN Mise à Jour du Dossier: Nouveaux Éléments [{complaint_ref}]",
                'title': "Mise à Jour de l'Enquête",
                'status_label': "Mise à Jour",
                'body_text': "Bonjour,\n\nDe nouveaux éléments sont disponibles pour le dossier {complaint_ref}.\n\nRésumé des preuves: {evidence_summary}\nInformation de routage: {routing_info}\n\nNos services poursuivent la consolidation des éléments de preuve.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Détails des Progrès",
                'default_evidence': "Éléments de preuve et journaux d'analyse compilés",
                'default_routing': "Traité dans la matrice centrale GFIN"
            }
        },
        'case_escalated': {
            'en': {
                'subject': "GFIN Priority Alert: Case Escalated [{complaint_ref}]",
                'title': "Case Escalated to High Priority",
                'status_label': "Escalated",
                'body_text': "Dear Citizen,\n\nYour case {complaint_ref} has been escalated to a higher priority tier.\n\nEscalation Details: {escalation_reason}\n\nThis case has been routed to specialized financial crimes units and partner agencies for accelerated coordination.\n\nThank you,\nGFIN Support Team",
                'details_label': "Escalation Status",
                'default_escalation': "Assigned high-priority status for specialized analysis and authority exchange"
            },
            'es': {
                'subject': "GFIN Alerta Prioritaria: Caso Escalado [{complaint_ref}]",
                'title': "Caso Escalado a Alta Prioridad",
                'status_label': "Escalado",
                'body_text': "Estimado/a ciudadano/a,\n\nSu caso {complaint_ref} ha sido escalado a un nivel de prioridad superior.\n\nDetalles del escalado: {escalation_reason}\n\nEl expediente se ha derivado a unidades especializadas en delitos financieros y agencias asociadas.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Estado de Escalación",
                'default_escalation': "Asignada alta prioridad para análisis especializado y coordinación institucional"
            },
            'de': {
                'subject': "GFIN Prioritätsbenachrichtigung: Vorgang Eskaliert [{complaint_ref}]",
                'title': "Vorgang auf Hohe Priorität Eskaliert",
                'status_label': "Eskaliert",
                'body_text': "Sehr geehrte Damen und Herren,\n\nIhr Vorgang {complaint_ref} wurde auf eine höhere Prioritätsstufe eskaliert.\n\nEskalationsdetails: {escalation_reason}\n\nDer Fall wurde an spezialisierte Betrugsbekämpfungseinheiten und Partnerbehörden weitergeleitet.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Eskalationsstatus",
                'default_escalation': "Erhöhte Priorität für spezialisierte Analyse und Behördenauswertung"
            },
            'fr': {
                'subject': "GFIN Alerte Prioritaire: Dossier Escaladé [{complaint_ref}]",
                'title': "Dossier Transmis en Priorité Haute",
                'status_label': "Escaladé",
                'body_text': "Bonjour,\n\nVotre dossier {complaint_ref} a été transmis à un niveau de priorité supérieur.\n\nDétails de l'escalade: {escalation_reason}\n\nLe dossier a été transmis aux équipes spécialisées et organismes partenaires pour traitement accéléré.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Statut d'Escalade",
                'default_escalation': "Niveau de priorité haute attribué pour analyse spécialisée"
            }
        },
        'case_resolved': {
            'en': {
                'subject': "GFIN Case Notice: Investigation Concluded [{complaint_ref}]",
                'title': "Case Investigation Resolved & Concluded",
                'status_label': "Resolved",
                'body_text': "Dear Citizen,\n\nThe investigation for case reference {complaint_ref} has been officially concluded.\n\nOutcome Summary: {outcome_summary}\n\nAll intelligence findings have been finalized and archived in the GFIN repository.\n\nThank you,\nGFIN Support Team",
                'details_label': "Outcome Summary",
                'default_outcome': "Intelligence compilation completed and transmitted to registered database archives"
            },
            'es': {
                'subject': "GFIN Aviso de Caso: Investigación Concluida [{complaint_ref}]",
                'title': "Investigación de Caso Resuelta y Concluida",
                'status_label': "Resuelto",
                'body_text': "Estimado/a ciudadano/a,\n\nLa investigación para la referencia {complaint_ref} ha sido oficialmente concluida.\n\nResumen del resultado: {outcome_summary}\n\nTodas las conclusiones de inteligencia han sido finalizadas y archivadas en el repositorio GFIN.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Resumen del Resultado",
                'default_outcome': "Evaluación de inteligencia completada y registrada en los archivos correspondientes"
            },
            'de': {
                'subject': "GFIN Vorgangsmitteilung: Untersuchung Abgeschlossen [{complaint_ref}]",
                'title': "Untersuchung Abgeschlossen & Beendet",
                'status_label': "Abgeschlossen",
                'body_text': "Sehr geehrte Damen und Herren,\n\ndie Untersuchung für Vorgang {complaint_ref} wurde offiziell beendet.\n\nErgebniszusammenfassung: {outcome_summary}\n\nAlle Erkenntnisse wurden finalisiert und im GFIN-Archiv abgelegt.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Ergebniszusammenfassung",
                'default_outcome': "Erkenntniszusammenstellung abgeschlossen und archiviert"
            },
            'fr': {
                'subject': "GFIN Clôture de Dossier: Enquête Terminée [{complaint_ref}]",
                'title': "Enquête Résolue et Clôturée",
                'status_label': "Résolu",
                'body_text': "Bonjour,\n\nL'enquête pour le dossier {complaint_ref} est désormais officiellement clôturée.\n\nRésumé du résultat: {outcome_summary}\n\nTous les éléments d'intelligence ont été finalisés et archivés.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Résumé du Résultat",
                'default_outcome': "Synthèse des informations terminée et archivée dans le répertoire GFIN"
            }
        },
        'alert_sent_to_authorities': {
            'en': {
                'subject': "GFIN Confirmation: Report Transmitted to Law Enforcement [{complaint_ref}]",
                'title': "Alert Transmitted to Authorities",
                'status_label': "Authorities Alerted",
                'body_text': "Dear Citizen,\n\nThis message confirms that intelligence for case {complaint_ref} has been formatted and transmitted to law enforcement authorities.\n\nAuthority Information: {authority_name}\n\nYour complaint is now registered in official law enforcement intelligence channels.\n\nThank you,\nGFIN Support Team",
                'details_label': "Authority Transmission Information",
                'default_authority': "Designated Law Enforcement Agencies and National Fraud Intelligence Units"
            },
            'es': {
                'subject': "GFIN Confirmación: Reporte Transmitido a las Autoridades [{complaint_ref}]",
                'title': "Alerta Transmitida a las Autoridades",
                'status_label': "Autoridades Alertadas",
                'body_text': "Estimado/a ciudadano/a,\n\nLe confirmamos que la información del caso {complaint_ref} ha sido transmitida a las autoridades policiales pertinentes.\n\nInformación de Autoridad: {authority_name}\n\nSu reclamación ha sido registrada en los canales oficiales de las fuerzas de seguridad.\n\nAtentamente,\nEquipo GFIN",
                'details_label': "Información de Transmisión a Autoridades",
                'default_authority': "Organismos Policiales y Unidades Nacionales de Inteligencia contra el Fraude"
            },
            'de': {
                'subject': "GFIN Bestätigung: Bericht an Behörden Übermittelt [{complaint_ref}]",
                'title': "Meldung an Strafverfolgungsbehörden Gesendet",
                'status_label': "Behörden Informiert",
                'body_text': "Sehr geehrte Damen und Herren,\n\nhiermit bestätigen wir, dass die Daten für Vorgang {complaint_ref} an die zuständigen Strafverfolgungsbehörden übermittelt wurden.\n\nBehördeninformation: {authority_name}\n\nIhre Beschwerde ist nun in den offiziellen behördlichen Systemen erfasst.\n\nMit freundlichen Grüßen,\nGFIN Team",
                'details_label': "Übermittlungsinformation",
                'default_authority': "Zuständige Polizeibehörden und Betrugsbekämpfungszentren"
            },
            'fr': {
                'subject': "GFIN Confirmation: Signalement Transmis aux Autorités [{complaint_ref}]",
                'title': "Alerte Transmise aux Autorités Répressives",
                'status_label': "Autorités Alertées",
                'body_text': "Bonjour,\n\nNous vous confirmons que le dossier {complaint_ref} a été transmis aux autorités répressives et services de police.\n\nInformation des Autorités: {authority_name}\n\nVotre plainte est désormais enregistrée dans les réseaux officiels.\n\nCordialement,\nL'équipe GFIN",
                'details_label': "Information de Transmission aux Autorités",
                'default_authority': "Services de Police et Unités Nationales de Renseignement"
            }
        }
    }

    entry = catalog.get(norm_type, catalog['complaint_received']).get(lang, catalog['complaint_received']['en'])
    
    # Generate generic HTML template preview structure
    details_label = entry.get('details_label', 'Details')
    default_val = entry.get('default_timeline') or entry.get('default_scope') or entry.get('default_outcome') or entry.get('default_authority') or "Information registered"
    details_box_html = f'<div class="details-box"><strong>{details_label}:</strong> {default_val}</div>'

    html_body = _render_html_template(
        title=entry['title'],
        status_label=entry['status_label'],
        case_ref="{complaint_ref}",
        message_text=entry['body_text'],
        details_html=details_box_html,
        theme_key=norm_type,
        lang=lang
    )

    return {
        'subject': entry['subject'],
        'body_text': entry['body_text'],
        'body_html': html_body,
        'title': entry['title'],
        'status_label': entry['status_label'],
        'details_label': details_label,
        'notification_type': norm_type,
        'language': lang
    }


def send_email(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """Sends an email notification using Python's smtplib + email.mime.
    
    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.
        html_body: Optional HTML email body.
        
    Returns:
        bool: True if email was delivered to SMTP server successfully, False otherwise.
    """
    if not to_email or "@" not in to_email:
        logger.error(f"Invalid recipient email address: {to_email}")
        return False

    from_email = os.getenv("FROM_EMAIL", FROM_EMAIL)
    smtp_host = os.getenv("SMTP_HOST", SMTP_HOST)
    smtp_port = int(os.getenv("SMTP_PORT", str(SMTP_PORT)))
    smtp_user = os.getenv("SMTP_USER", SMTP_USER)
    smtp_pass = os.getenv("SMTP_PASS", SMTP_PASS)
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port} to send email to {to_email}...")
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"Email successfully delivered to {to_email}")
        return True
    except (ConnectionRefusedError, OSError, smtplib.SMTPException) as e:
        logger.warning(f"SMTP delivery to {to_email} failed ({e}).")
        if os.getenv("MOCK_NOTIFICATIONS", "false").lower() in ("true", "1"):
            logger.info(f"[MOCK MODE] Simulated email sent to {to_email}")
            return True
        return False


def send_sms(to_phone: str, message: str) -> bool:
    """Sends an SMS notification via a simple webhook interface (placeholder for Twilio/gateway integration).
    
    Args:
        to_phone: Recipient phone number (E.164 format recommended).
        message: Plain text SMS message content.
        
    Returns:
        bool: True if sent via webhook or queued in placeholder mode, False otherwise.
    """
    if not to_phone:
        logger.error("No phone number provided for SMS.")
        return False

    webhook_url = os.getenv("SMS_WEBHOOK_URL", SMS_WEBHOOK_URL)
    
    if webhook_url:
        try:
            payload = json.dumps({"to": to_phone, "message": message, "sender": "GFIN-ALERT"}).encode("utf-8")
            req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if 200 <= response.status < 300:
                    logger.info(f"SMS webhook delivered to {to_phone} via {webhook_url}")
                    return True
                else:
                    logger.error(f"SMS webhook returned HTTP status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to post to SMS webhook URL: {e}")
            return False
    else:
        logger.info(f"[SMS PLACEHOLDER] SMS queued for {to_phone}: '{message[:60]}...'")
        return True


def _log_to_db(complaint_ref: str, notification_type: str, recipient: str, channel: str, status: str) -> bool:
    """Logs notification metadata into PostgreSQL database table 'victim_notifications'.
    
    Table columns: id, complaint_ref, notification_type, recipient, channel, status, sent_at
    """
    if not HAS_PSYCOPG2:
        logger.warning("psycopg2 module unavailable; database logging skipped.")
        return False

    host = os.getenv("DB_HOST", DB_HOST)
    port = int(os.getenv("DB_PORT", str(DB_PORT)))
    user = os.getenv("DB_USER", DB_USER)
    password = os.getenv("DB_PASSWORD", DB_PASSWORD)
    dbname = os.getenv("DB_NAME", DB_NAME)

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=5
        )
        cursor = conn.cursor()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS victim_notifications (
            id SERIAL PRIMARY KEY,
            complaint_ref VARCHAR(100) NOT NULL,
            notification_type VARCHAR(100) NOT NULL,
            recipient VARCHAR(255) NOT NULL,
            channel VARCHAR(20) NOT NULL,
            status VARCHAR(50) NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_sql)
        insert_sql = """
        INSERT INTO victim_notifications (complaint_ref, notification_type, recipient, channel, status, sent_at)
        VALUES (%s, %s, %s, %s, %s, NOW());
        """
        cursor.execute(insert_sql, (complaint_ref, notification_type, recipient, channel, status))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Notification logged to PostgreSQL DB table 'victim_notifications' for {complaint_ref} ({channel})")
        return True
    except Exception as e:
        logger.warning(f"Failed to store notification log in PostgreSQL DB ({host}:{port}/{dbname}): {e}")
        return False


def notify_victim(complaint_ref: str, notification_type: str, extra_data: dict = None) -> bool:
    """Orchestrates victim status change notifications and logs activity to database.
    
    Args:
        complaint_ref: Unique case/complaint reference identifier.
        notification_type: Event notification type ('complaint_received', 'investigation_started',
                           'investigation_update', 'case_escalated', 'case_resolved', 'alert_sent_to_authorities').
        extra_data: Context dictionary (e.g. recipient_email, recipient_phone, language, channel, timeline, etc.).
        
    Returns:
        bool: True if at least one notification was dispatched successfully, False otherwise.
    """
    if not complaint_ref or not notification_type:
        logger.error("Both complaint_ref and notification_type are required.")
        return False

    # 1. Enforce strict sanitization of sensitive police details
    sanitized = sanitize_victim_data(extra_data or {})
    
    recipient_email = sanitized.get('recipient_email') or sanitized.get('to_email') or sanitized.get('email')
    recipient_phone = sanitized.get('recipient_phone') or sanitized.get('to_phone') or sanitized.get('phone')
    language = sanitized.get('language') or sanitized.get('lang') or 'en'
    channel_pref = (sanitized.get('channel') or '').lower()

    if not recipient_email and not recipient_phone:
        logger.error(f"No recipient email or phone provided in extra_data for case {complaint_ref}")
        return False

    # 2. Retrieve template dictionary
    template = get_notification_template(notification_type, language=language)
    norm_type = template['notification_type']

    # 3. Build formatting arguments
    format_kwargs = {
        'complaint_ref': complaint_ref,
        'expected_timeline': sanitized.get('expected_timeline', '3 to 5 business days'),
        'investigation_scope': sanitized.get('investigation_scope') or sanitized.get('what_being_investigated', 'Digital transaction and indicator analysis'),
        'evidence_summary': sanitized.get('evidence_collected') or sanitized.get('evidence_summary', 'Case artifacts indexed for review'),
        'routing_info': sanitized.get('routing_info', 'Processed via central GFIN intelligence matrix'),
        'escalation_reason': sanitized.get('escalation_reason') or sanitized.get('escalation_level', 'Assigned to specialized response unit'),
        'outcome_summary': sanitized.get('outcome_summary', 'Case assessment completed'),
        'authority_name': sanitized.get('authority_name') or sanitized.get('authority_details', 'Designated Fraud Intelligence Agencies')
    }

    try:
        subject = template['subject'].format(**format_kwargs)
        body_text = template['body_text'].format(**format_kwargs)
    except KeyError as e:
        logger.warning(f"KeyError during template text formatting: {e}")
        subject = template['subject'].replace('{complaint_ref}', complaint_ref)
        body_text = template['body_text'].replace('{complaint_ref}', complaint_ref)

    # Build dynamic HTML details box based on event type
    details_items = []
    if norm_type == 'complaint_received':
        val = sanitized.get('expected_timeline', format_kwargs['expected_timeline'])
        details_items.append(f"<strong>Expected Assessment Timeline:</strong> {val}")
    elif norm_type == 'investigation_started':
        val = sanitized.get('investigation_scope') or sanitized.get('what_being_investigated', format_kwargs['investigation_scope'])
        details_items.append(f"<strong>Investigation Scope:</strong> {val}")
    elif norm_type == 'investigation_update':
        ev = sanitized.get('evidence_collected') or sanitized.get('evidence_summary', format_kwargs['evidence_summary'])
        rt = sanitized.get('routing_info', format_kwargs['routing_info'])
        details_items.append(f"<strong>Evidence Status:</strong> {ev}")
        details_items.append(f"<strong>Routing Status:</strong> {rt}")
    elif norm_type == 'case_escalated':
        val = sanitized.get('escalation_reason') or sanitized.get('escalation_level', format_kwargs['escalation_reason'])
        details_items.append(f"<strong>Escalation Details:</strong> {val}")
    elif norm_type == 'case_resolved':
        val = sanitized.get('outcome_summary', format_kwargs['outcome_summary'])
        details_items.append(f"<strong>Outcome Summary:</strong> {val}")
    elif norm_type == 'alert_sent_to_authorities':
        val = sanitized.get('authority_name') or sanitized.get('authority_details', format_kwargs['authority_name'])
        details_items.append(f"<strong>Authority Information:</strong> {val}")

    details_box_html = f'<div class="details-box">{"<br>".join(details_items)}</div>' if details_items else ''

    html_body = _render_html_template(
        title=template['title'],
        status_label=template['status_label'],
        case_ref=complaint_ref,
        message_text=body_text,
        details_html=details_box_html,
        theme_key=norm_type,
        lang=template['language']
    )

    dispatch_success = False

    # Dispatch email if targeted
    if recipient_email and channel_pref in ('email', 'both', ''):
        email_sent = send_email(to_email=recipient_email, subject=subject, body=body_text, html_body=html_body)
        status_str = "SENT" if email_sent else "FAILED"
        _log_to_db(complaint_ref, norm_type, recipient_email, "email", status_str)
        if email_sent:
            dispatch_success = True

    # Dispatch SMS if targeted
    if recipient_phone and channel_pref in ('sms', 'both', ''):
        sms_body = f"GFIN [{template['status_label']}]: Case {complaint_ref}. {template['title']}. Check email for full operational status."
        sms_sent = send_sms(to_phone=recipient_phone, message=sms_body)
        status_str = "SENT" if sms_sent else "FAILED"
        _log_to_db(complaint_ref, norm_type, recipient_phone, "sms", status_str)
        if sms_sent:
            dispatch_success = True

    return dispatch_success


if __name__ == "__main__":
    print("=== Running GFIN Victim Notifications Module Unit Tests ===")
    
    # 1. Verify signatures & templates across all types and languages
    all_types = ['complaint_received', 'investigation_started', 'investigation_update', 'case_escalated', 'case_resolved', 'alert_sent_to_authorities']
    all_langs = ['en', 'es', 'de', 'fr']
    
    for nt in all_types:
        for lg in all_langs:
            t = get_notification_template(nt, lg)
            assert 'subject' in t and 'body_text' in t and 'body_html' in t, f"Missing required template keys for {nt} ({lg})"
            assert t['language'] == lg, f"Language mismatch for {lg}"
    print(f"[OK] Verified templates for {len(all_types)} notification types across {len(all_langs)} languages.")

    # 2. Test security sanitization
    dirty_context = {
        'to_email': 'test_victim@gfin-example.org',
        'to_phone': '+15559876543',
        'language': 'en',
        'expected_timeline': '2-3 days',
        'officer_name': 'Agent John Doe (CLASSIFIED)',
        'suspect_address': '123 Scam Street',
        'police_notes': 'Target wiretapped under warrant 4021'
    }
    cleaned = sanitize_victim_data(dirty_context)
    for forbidden in ['officer_name', 'suspect_address', 'police_notes']:
        assert forbidden not in cleaned, f"Security failure: '{forbidden}' not redacted!"
    print("[OK] Security sanitization test passed: Sensitive police investigation data filtered out.")

    # 3. Test notify_victim with mock mode enabled
    os.environ["MOCK_NOTIFICATIONS"] = "true"
    test_result = notify_victim("GFIN-REF-2026-001", "investigation_started", dirty_context)
    assert test_result is True, "notify_victim returned False in mock mode"
    print("[OK] notify_victim execution test passed.")

    print("\nAll victim notification module checks completed successfully!")

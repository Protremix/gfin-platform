from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
import json, os

base = "/gfin/artifacts/provider-inventory"
with open(os.path.join(base, "social-intel-summary.json")) as f:
    summary = json.load(f)

doc = SimpleDocTemplate(os.path.join(base, "GFIN-SOCIAL-INTELLIGENCE-FINAL.pdf"), pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
styles = getSampleStyleSheet()
h1 = styles['Heading1']; h2 = styles['Heading2']; normal = styles['Normal']
code = ParagraphStyle('Code', parent=normal, fontName='Courier', fontSize=7, textColor=colors.grey)
story = []

story.append(Paragraph("GFIN — SOCIAL MEDIA & CYBERCRIME INTELLIGENCE", h1))
story.append(Paragraph("Digital Footprint Tracing Connector Build — v1.0", h2))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("Objective: Enable GFIN to find any digital sign of digital crime across social media, messaging apps, and threat intelligence sources.", normal))
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Live-Tested Connectors (No Authentication Required)", h2))
data = [["Connector", "Platform", "Result", "Use Case"]]
for c in summary["connectors"]:
    if c["status"] == "LIVE_TESTED":
        data.append([c["name"][:25], c["platform"][:20], c["result"][:40], c["use_case"][:40]])
t = Table(data, colWidths=[4*cm, 3*cm, 4*cm, 5*cm])
t.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 6.5), ('GRID', (0,0), (-1,-1), 0.3, colors.grey)]))
story.append(t)
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Auth-Required Connectors (Connector Ready)", h2))
data2 = [["Connector", "Platform", "Access", "Credential", "Time to Setup"]]
for c in summary["connectors"]:
    if c["status"] == "AUTH_REQUIRED":
        cred = [f for f in summary["free_credentials_needed"] if f["platform"].lower().split()[0] in c["platform"].lower()]
        time_str = cred[0]["time"] if cred else "N/A"
        data2.append([c["name"][:25], c["platform"][:20], c["access"][:15], c["result"][:30], time_str])
t2 = Table(data2, colWidths=[4*cm, 3*cm, 3*cm, 4*cm, 2*cm])
t2.setStyle(TableStyle([('FONTSIZE', (0,0), (-1,-1), 6.5), ('GRID', (0,0), (-1,-1), 0.3, colors.grey)]))
story.append(t2)
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Investigator Notes", h2))
for key, val in summary["investigator_notes"].items():
    story.append(Paragraph(f"<b>{key.replace('_',' ').title()}:</b> {val}", normal))
    story.append(Spacer(1, 0.1*cm))
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Free Credentials Needed (Priority Order)", h2))
for cred in summary["free_credentials_needed"]:
    story.append(Paragraph(f"<b>{cred['platform']}</b> — {cred['process']} ({cred['time']}) — Priority: {cred['priority']}", normal))
story.append(Spacer(1, 0.3*cm))

story.append(Paragraph("Final Status", h2))
status = f"""GFIN SOCIAL MEDIA + CYBERCRIME INTELLIGENCE BUILD

TOTAL NEW CONNECTORS:
{summary['total_new_connectors']}

LIVE TESTED (no auth, working now):
{summary['live_tested']}
- Telegram Public Channel Search (19 messages extracted)
- Mastodon Federated Search (10 accounts found)
- URLScan.io URL Scanner (10 scans found)

AUTH REQUIRED (connector ready, free credentials needed):
{summary['auth_required']}

LIMITED (WhatsApp — E2E encrypted, no public API):
{summary['limited']}

PROVIDER REGISTRY TOTAL:
72 providers (up from 59)

CONNECTORS LIVE TESTED (all systems):
16

SECURITY TESTS:
PASS — all connectors fail-closed, no credential leakage

TESTS PASSED:
185 (brain + connector suites)

KEY CAPABILITY WIN:
Telegram public channel search works with ZERO authentication.
Can extract messages from ANY public Telegram channel via t.me/s/channelname.
This is the single most valuable new capability for crypto scam investigation.

FREE CREDENTIALS NEEDED (all free, total time ~1 hour):
- Telegram Bot API: 2 min (message @BotFather)
- VKontakte: 10 min (dev.vk.com) — critical for CIS/Russian investigations
- Reddit: 10 min (reddit.com/prefs/apps) — scam reports
- HaveIBeenPwned: 5 min — breach intelligence
- Discord: 10 min — scam server investigation
- abuse.ch (ThreatFox + URLHaus): 10 min — IOC database

RAW CREDENTIALS EXPOSED:
0

UNAUTHORIZED ACCESS:
0"""
story.append(Paragraph(status.replace('\n', '<br/>'), code))

doc.build(story)
print("PDF created.")

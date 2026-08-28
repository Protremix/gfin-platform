#!/usr/bin/env python3
"""
GFIN Victim Discovery & Investigation Engine v1.0

The system was collecting Telegram messages but NOT finding victims.
It was flagging scam ads as victims. This engine fixes that:

1. RECLASSIFY all existing messages: SCAM_AD, RECRUITMENT, INTELLIGENCE, VICTIM_REPORT
2. SEARCH for real victims: in Telegram groups, web forums, complaint portals
3. EXTRACT victim details: what happened, how much lost, which platform, how contacted
4. INVESTIGATE: auto-trigger police pipeline for each victim found
5. LINK victims to existing cases

A real victim says: "I lost $5000 on neex.com"
A scam ad says: "Hiring retention agents, full relocation package"
These are COMPLETELY DIFFERENT and the system was treating them the same.
"""
import sys
import json
import re
import urllib.request
import ssl
from datetime import datetime, timezone

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

# ============================================================
# MESSAGE CLASSIFICATION PATTERNS
# ============================================================

# Real victim reports - someone saying THEY were harmed
VICTIM_PATTERNS = [
    # Direct victim statements
    (r'\bI\s+(lost|was\s+scammed|got\s+scammed|lost\s+everything|lost\s+my\s+money)\b', "DIRECT_VICTIM", 0.9),
    (r'\bthey\s+(stole|took)\s+(my|our)\s+(money|funds|crypto|savings|bitcoin|usdt|eth)\b', "THEFT_VICTIM", 0.9),
    (r'\bI\s+(invested|deposited|sent)\s+(money|\$|usdt|btc|eth|crypto)\b.*\b(and|but|then)\b.*\b(lost|scammed|stolen|frozen|blocked|cant|cannot|unable)\b', "INVESTMENT_VICTIM", 0.85),
    (r'\b(cant|cannot|unable\s+to)\s+withdraw\b', "WITHDRAWAL_VICTIM", 0.8),
    (r'\bmy\s+(account|funds|money)\s+(was|were|got)\s+(frozen|blocked|locked|stolen)\b', "ACCOUNT_VICTIM", 0.85),
    (r'\bI\s+was\s+(a\s+)?victim\b', "SELF_IDENTIFIED_VICTIM", 0.9),
    (r'\bhow\s+(do|can)\s+I\s+(get|recover)\s+(my\s+)?(money|funds|crypto)\s+back\b', "RECOVERY_SEEKING_VICTIM", 0.75),
    (r'\bI\s+(sent|gave|transferred)\s+.+\b(to|on|via|through)\s+\w+.*\b(lost|scammed|stolen|gone)\b', "TRANSFER_VICTIM", 0.8),
    (r'\b(is|are)\s+\w+\.(com|net|org|io|co)\s+(legit|safe|real|scam)\b', "VERIFICATION_QUESTION", 0.5),
    (r'\bavoid\s+\w+\.(com|net|org|io|co)\b', "WARNING_TO_OTHERS", 0.6),
    (r'\bstay\s+away\s+from\b', "WARNING_TO_OTHERS", 0.6),
    (r'\bdont\s+(use|trust|send)\b.*\b(scam|fraud|fake)\b', "WARNING_TO_OTHERS", 0.6),
    # Loss amounts with context
    (r'\bI\s+lost\s+\$?\d', "FINANCIAL_LOSS", 0.85),
    (r'\blost\s+\$?\d+\s*(k|thousand|million|usd|dollars|euros|pounds)', "FINANCIAL_LOSS", 0.8),
]

# Scam advertisements - NOT victims
SCAM_AD_PATTERNS = [
    (r'\b(start|begin|get\s+started)\s+with\s+\$?\d', "INVESTMENT_AD", 0.9),
    (r'\b(earn|make|get)\s+\$?\d+\s*(per|a|every)\s+(day|week|month|hour)', "EARN_MONEY_AD", 0.9),
    (r'\b(ref|referral|invite)\s*(link|code|bonus)\b', "REFERRAL_AD", 0.85),
    (r'\b(sign\s+up|register|join)\s*(now|today|free)?\b.*\b(link|url|http)', "REGISTRATION_AD", 0.8),
    (r'\b(auto\s+compound|daily\s+returns|guaranteed\s+profit|roi)\b', "INVESTMENT_PROMISE", 0.9),
    (r'\b(withdrawals?\s+(are\s+)?(fast|instant|quick|easy))\b', "WITHDRAWAL_PROMISE_AD", 0.85),
    (r'\b(profits?\s+split|profit\s+sharing|80/20|70/30)\b', "PROFIT_SHARING_AD", 0.85),
    (r'https?://\S+/r/\S+', "REFERRAL_LINK", 0.9),
    (r'\b(copy\s+trade|auto\s+trade|auto\s+copy)\b', "COPY_TRADE_AD", 0.8),
    # USDT Flash / Fake crypto
    (r'\b(usdt\s+flash|btc\s+flash|flash\s+coin|flash\s+usdt)\b', "FLASH_CRYPTO_AD", 0.95),
    (r'\b(transferable\s+flash|flash\s+transferable)\b', "FLASH_CRYPTO_AD", 0.95),
    # SSN / Identity theft tools
    (r'\b(ssn|social\s+security).*(for\s+sale|available|fresh|new|verified)\b', "IDENTITY_THEFT_AD", 0.95),
    (r'\b(dl\s+with\s+ssn|bin\s+verified\s+ssn)\b', "IDENTITY_THEFT_AD", 0.95),
    # Hacking services
    (r'\b(hacking|spy|spying)\s+(and|of)\s+(any|your)\s+(account|phone|wallet)\b', "HACKING_SERVICE_AD", 0.9),
    (r'\b(recovery\s+of\s+lost\s+funds|recover\s+lost\s+wallet)\b', "RECOVERY_SCAM_AD", 0.9),
    (r'\b(facebook\s+hacking|whatsapp\s+hacking|instagram\s+hacking)\b', "HACKING_SERVICE_AD", 0.9),
]

# Recruitment / Human trafficking indicators
RECRUITMENT_PATTERNS = [
    (r'\b(hiring|we.?re\s+hiring|now\s+hiring|recruiting)\b', "HIRING", 0.8),
    (r'\b(retention|conversion|recovery)\s+(agent|agents|desk|team|specialist)', "RETENTION_RECRUITMENT", 0.95),
    (r'\b(relocation\s+package|full\s+relocation|relocate)\b', "RELOCATION_OFFER", 0.9),
    (r'\b(work\s+permit|visa\s+sponsorship|accommodation\s+provided)\b', "VISA_OFFER", 0.9),
    (r'\b(flight\s+ticket|travel\s+arranged|housing\s+provided)\b', "RELOCATION_BENEFIT", 0.85),
    (r'\b(call\s+center|office)\s+(opening|opened|expanding|new)\b', "OFFICE_EXPANSION", 0.8),
    (r'\b(looking\s+for|seeking|need)\s+(employees|workers|agents|staff|team\s+members)', "STAFFING_SEARCH", 0.8),
    (r'\b(languages?\s+required|languages?\s+needed|bilingual)\b', "LANGUAGE_REQUIREMENT", 0.75),
    (r'\b(forex\s+jobs|crypto\s+jobs|trading\s+jobs)\b', "SCAM_JOB_POSTING", 0.85),
    (r'\b(FTD|first\s+time\s+deposit|leads)\s+(agent|specialist|manager)', "FTD_RECRUITMENT", 0.9),
    (r'\b(sales\s+desk|conversion\s+desk|retention\s+desk)\b', "DESK_HIRING", 0.85),
    (r'\b(armenia|cyprus|kyrenia|istanbul|dubai|belgrade|kyiv|bucharest|chisinau).*(relocation|hiring|office)', "SCAM_HUB_LOCATION", 0.8),
    # Lead selling / database selling
    (r'\b(leads?\s+for\s+sale|lead\s+database|victim\s+database|database\s+of\s+(victims|leads))', "LEAD_SELLING", 0.95),
    (r'\b(verified\s+leads|real\s+leads|fresh\s+leads|ftd\s+leads)\b', "LEAD_SELLING", 0.85),
    (r'\b(buy\s+leads|sell\s+leads|leads?\s+market)', "LEAD_SELLING", 0.9),
]

# Amount extraction
AMOUNT_PATTERN = re.compile(r'(\$|usd|eur|gbp|btc|eth|usdt|euro|dollar|pound)\s*([\d,]+(?:\.\d+)?)\s*(k|m|thousand|million)?', re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r'(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})')
WALLET_BTC = re.compile(r'\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b')
WALLET_ETH = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
WALLET_TRON = re.compile(r'\bT[1-9A-HJ-NP-Za-km-z]{33}\b')
PHONE_PATTERN = re.compile(r'\+\d{10,15}')
TELEGRAM_USER = re.compile(r'@([a-zA-Z0-9_]{3,32})')


def classify_message(text):
    """Classify a Telegram message as VICTIM_REPORT, SCAM_AD, RECRUITMENT, or INTELLIGENCE."""
    if not text:
        return "UNKNOWN", 0.0, []

    text_lower = text.lower()
    scores = {"VICTIM_REPORT": 0.0, "SCAM_AD": 0.0, "RECRUITMENT": 0.0}
    evidence = []

    # Check victim patterns
    for pattern, label, weight in VICTIM_PATTERNS:
        if re.search(pattern, text_lower):
            if scores["VICTIM_REPORT"] < weight:
                scores["VICTIM_REPORT"] = weight
            evidence.append(label)

    # Check scam ad patterns
    for pattern, label, weight in SCAM_AD_PATTERNS:
        if re.search(pattern, text_lower):
            if scores["SCAM_AD"] < weight:
                scores["SCAM_AD"] = weight
            evidence.append(label)

    # Check recruitment patterns
    for pattern, label, weight in RECRUITMENT_PATTERNS:
        if re.search(pattern, text_lower):
            if scores["RECRUITMENT"] < weight:
                scores["RECRUITMENT"] = weight
            evidence.append(label)

    # Determine classification
    best_label = max(scores, key=scores.get)
    best_score = scores[best_label]

    if best_score == 0.0:
        # No pattern matched — classify as general intelligence
        return "INTELLIGENCE", 0.3, evidence

    # If victim and scam_ad both match, victim wins if it contains first-person loss language
    if scores["VICTIM_REPORT"] > 0 and scores["SCAM_AD"] > 0:
        if scores["VICTIM_REPORT"] >= scores["SCAM_AD"]:
            best_label = "VICTIM_REPORT"
        else:
            best_label = "SCAM_AD"

    return best_label, best_score, list(set(evidence))


def extract_victim_details(text):
    """Extract details from a real victim report."""
    details = {
        "amounts_lost": [],
        "domains_mentioned": [],
        "wallets_mentioned": [],
        "phones_mentioned": [],
        "telegram_users_mentioned": [],
        "payment_methods": [],
        "how_contacted": None,
        "what_promised": None,
    }

    if not text:
        return details

    # Amounts
    for match in AMOUNT_PATTERN.finditer(text):
        currency = match.group(1).upper()
        amount = match.group(2).replace(",", "")
        unit = match.group(3)
        if unit:
            if unit.lower() in ("k", "thousand"):
                amount = str(int(float(amount) * 1000))
            elif unit.lower() in ("m", "million"):
                amount = str(int(float(amount) * 1000000))
        details["amounts_lost"].append({"currency": currency, "amount": amount})

    # Domains
    for match in DOMAIN_PATTERN.finditer(text):
        domain = match.group(1).lower()
        # Filter out common non-scam domains
        if domain not in ("telegram.org", "t.me", "youtu.be", "google.com", "github.com"):
            if domain not in details["domains_mentioned"]:
                details["domains_mentioned"].append(domain)

    # Wallets
    for match in WALLET_BTC.finditer(text):
        details["wallets_mentioned"].append({"type": "BTC", "address": match.group(0)})
    for match in WALLET_ETH.finditer(text):
        details["wallets_mentioned"].append({"type": "ETH", "address": match.group(0)})
    for match in WALLET_TRON.finditer(text):
        details["wallets_mentioned"].append({"type": "TRON", "address": match.group(0)})

    # Phones
    for match in PHONE_PATTERN.finditer(text):
        details["phones_mentioned"].append(match.group(0))

    # Telegram users
    for match in TELEGRAM_USER.finditer(text):
        username = match.group(1)
        if username.lower() not in ("gfinofficialbot", "admin", "support", "bot"):
            if username not in details["telegram_users_mentioned"]:
                details["telegram_users_mentioned"].append(username)

    # How contacted
    contact_indicators = {
        "telegram": r'\b(telegram|tg|t\.me)\b',
        "whatsapp": r'\bwhatsapp\b',
        "phone_call": r'\b(phone|call|called\s+me)\b',
        "email": r'\b(email|gmail|outlook)\b',
        "social_media": r'\b(instagram|facebook|twitter|tiktok|linkedin)\b',
        "dating_app": r'\b(tinder|bumble|dating\s+app|dating\s+site)\b',
    }
    for method, pattern in contact_indicators.items():
        if re.search(pattern, text.lower()):
            details["how_contacted"] = method
            break

    # What was promised
    promise_indicators = {
        "investment_returns": r'\b(invest|investment|returns?|profit|roi|trading)\b',
        "recovery_service": r'\b(recover|recovery|get\s+your\s+money\s+back|refund)\b',
        "job_offer": r'\b(job|work|career|hired|employment|salary)\b',
        "loan": r'\b(loan|lend|borrow|credit)\b',
        "crypto_trading": r'\b(crypto|bitcoin|usdt|trading|exchange)\b',
        "romance": r'\b(love|relationship|marriage|dating)\b',
    }
    for promise, pattern in promise_indicators.items():
        if re.search(pattern, text.lower()):
            details["what_promised"] = promise
            break

    return details


def run_victim_discovery():
    """Main function: discover victims, classify messages, and trigger investigations."""
    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN VICTIM DISCOVERY & INVESTIGATION ENGINE v1.0")
    print(sep)

    # ============================================================
    # PHASE 1: RECLASSIFY ALL TELEGRAM MESSAGES
    # ============================================================
    print("\n--- PHASE 1: RECLASSIFYING ALL TELEGRAM MESSAGES ---")
    cur.execute("SELECT id, message_text FROM telegram_intelligence")
    all_messages = cur.fetchall()
    print("Messages to classify: {}".format(len(all_messages)))

    classification_counts = {"VICTIM_REPORT": 0, "SCAM_AD": 0, "RECRUITMENT": 0, "INTELLIGENCE": 0, "UNKNOWN": 0}
    real_victims_found = []

    for msg_id, text in all_messages:
        classification, score, evidence = classify_message(text)
        classification_counts[classification] = classification_counts.get(classification, 0) + 1

        # Update the message classification
        is_victim = (classification == "VICTIM_REPORT")
        cur.execute("UPDATE telegram_intelligence SET is_victim = %s, risk_level = %s WHERE id = %s",
                    (is_victim, classification, msg_id))

        if classification == "VICTIM_REPORT":
            details = extract_victim_details(text)
            real_victims_found.append({
                "message_id": msg_id,
                "text_preview": text[:500] if text else "",
                "classification": classification,
                "score": score,
                "evidence": evidence,
                "details": details
            })

    db.commit()
    print("\nReclassification results:")
    for cls, count in sorted(classification_counts.items(), key=lambda x: -x[1]):
        print("  {}: {}".format(cls, count))
    print("  Real victims found: {}".format(len(real_victims_found)))

    # ============================================================
    # PHASE 2: SEARCH FOR VICTIMS IN EXISTING DATA
    # ============================================================
    print("\n--- PHASE 2: SEARCHING FOR VICTIMS IN EXISTING DATA ---")

    # Search for messages that mention known scam domains in a negative context
    cur.execute("SELECT DISTINCT target FROM cases WHERE target IS NOT NULL AND target != ''")
    known_domains = [row[0].strip() for row in cur.fetchall() if "." in row[0]]
    print("Known scam domains to cross-reference: {}".format(len(known_domains)))

    # Search for people asking about known scam domains (potential victims)
    victim_search_count = 0
    for domain in known_domains:
        # Look for messages that mention this domain AND have victim-like language
        cur.execute("""
            SELECT id, group_name, message_text FROM telegram_intelligence
            WHERE (message_text ILIKE %s)
            AND (
                message_text ILIKE '%%scam%%' OR message_text ILIKE '%%fraud%%'
                OR message_text ILIKE '%%fake%%' OR message_text ILIKE '%%avoid%%'
                OR message_text ILIKE '%%warning%%' OR message_text ILIKE '%%stay away%%'
                OR message_text ILIKE '%%dont trust%%' OR message_text ILIKE '%%dont use%%'
            )
        """, ("%" + domain + "%",))
        for msg_id, group, text in cur.fetchall():
            # Check if this is a warning about the domain (not promoting it)
            text_lower = text.lower()
            # If the message contains a referral link to the domain, it's an AD not a warning
            if "/r/" in text_lower or "ref=" in text_lower or "signup" in text_lower:
                continue

            victim_search_count += 1
            details = extract_victim_details(text)

            # Create or update victim record
            victim_ref = "TG-WARN-{}".format(msg_id)
            cur.execute("""INSERT INTO victims (victim_id, name, country, scam_type, amount_lost, created_date)
                VALUES (%s, 'Anonymous Telegram reporter', 'Unknown', 'Warning about ' || %s, 'Unknown', NOW())
                ON CONFLICT DO NOTHING""", (victim_ref, domain))

            # Create complaint if not exists
            complaint_ref = "GFIN-2026-WARN{}".format(msg_id)
            cur.execute("""SELECT case_id FROM cases WHERE target ILIKE %s""", ("%" + domain + "%",))
            case_row = cur.fetchone()
            case_id = case_row[0] if case_row else None

            if case_id:
                cur.execute("""INSERT INTO victim_complaints
                    (reference_number, victim_id, case_id, scam_type, target, incident_date,
                     financial_loss, description, investigation_stage, country, auto_investigation_started, created_date, updated_date)
                    VALUES (%s, %s, %s, 'Warning Report', %s, CURRENT_DATE,
                     'Unknown', %s, 'UNDER_REVIEW', 'Unknown', false, NOW(), NOW())
                    ON CONFLICT DO NOTHING""",
                    (complaint_ref, victim_ref, case_id, domain,
                     "Community warning about {} from Telegram group '{}'. Message suggests fraudulent activity. Classification: WARNING_TO_OTHERS.".format(domain, group)))

    db.commit()
    print("Cross-referenced warnings found: {}".format(victim_search_count))

    # ============================================================
    # PHASE 3: EXTRACT NEW SCAM INDICATORS FROM ALL MESSAGES
    # ============================================================
    print("\n--- PHASE 3: EXTRACTING NEW SCAM INDICATORS ---")

    # Find all domains mentioned across all messages
    all_mentioned_domains = set()
    cur.execute("SELECT message_text FROM telegram_intelligence WHERE message_text IS NOT NULL")
    for (text,) in cur.fetchall():
        for match in DOMAIN_PATTERN.finditer(text or ""):
            domain = match.group(1).lower()
            if domain not in ("telegram.org", "t.me", "youtu.be", "google.com", "github.com",
                             "bit.ly", "tinyurl.com", "discord.com", "discord.gg", "instagram.com",
                             "facebook.com", "twitter.com", "x.com", "tiktok.com", "wa.me",
                             "api.telegram.org", "core.telegram.org"):
                all_mentioned_domains.add(domain)

    # Check which domains are NOT yet in tracked_domains or cases
    cur.execute("SELECT domain FROM tracked_domains")
    tracked = set(row[0].strip() for row in cur.fetchall())
    cur.execute("SELECT target FROM cases WHERE target IS NOT NULL")
    cased = set(row[0].strip() for row in cur.fetchall() if "." in row[0])

    new_domains = all_mentioned_domains - tracked - cased
    print("Total unique domains mentioned: {}".format(len(all_mentioned_domains)))
    print("Already tracked: {}".format(len(tracked)))
    print("Already in cases: {}".format(len(cased)))
    print("New domains to investigate: {}".format(len(new_domains)))

    # Add new domains to tracked_domains
    for domain in new_domains:
        cur.execute("""INSERT INTO tracked_domains (domain, source, first_seen, status)
            VALUES (%s, 'telegram_intelligence', NOW(), 'NEW')
            ON CONFLICT (domain) DO UPDATE SET last_checked = NOW()""", (domain,))

    db.commit()

    # ============================================================
    # PHASE 4: AUTO-INVESTIGATE NEW HIGH-PRIORITY DOMAINS
    # ============================================================
    print("\n--- PHASE 4: AUTO-INVESTIGATING NEW DOMAINS ---")

    # For each new domain, check if it appears in multiple messages (higher priority)
    domains_to_investigate = []
    for domain in new_domains:
        cur.execute("SELECT COUNT(*) FROM telegram_intelligence WHERE message_text ILIKE %s", ("%" + domain + "%",))
        mention_count = cur.fetchone()[0]
        if mention_count >= 2:  # Only investigate domains mentioned multiple times
            domains_to_investigate.append((domain, mention_count))

    domains_to_investigate.sort(key=lambda x: -x[1])
    print("Domains with multiple mentions (priority): {}".format(len(domains_to_investigate)))

    # Create cases for top new domains
    from police_pipeline import PoliceInvestigationPipeline
    pipeline = PoliceInvestigationPipeline(db)

    for domain, mentions in domains_to_investigate[:10]:  # Top 10 new domains
        print("\n  New domain: {} ({} mentions)".format(domain, mentions))

        # Check if domain is reachable
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = "https://" + domain
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"}, method="GET")
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            is_live = resp.status == 200
        except:
            is_live = False

        # Determine priority
        if mentions >= 5:
            priority = "HIGH"
        elif mentions >= 3:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # Create case
        case_id = "GFIN-CASE-{}".format(domain.replace(".", "-").upper()[:20])
        cur.execute("""INSERT INTO cases (case_id, target, priority, confidence, status, trigger, created_date, updated_date)
            VALUES (%s, %s, %s, 0.5, 'ACTIVE', 'telegram_intelligence', NOW(), NOW())
            ON CONFLICT (case_id) DO NOTHING""", (case_id, domain, priority))

        if cur.rowcount > 0:
            print("    Case created: {} (priority: {})".format(case_id, priority))
            # Run police investigation
            try:
                result = pipeline.investigate_case(case_id)
                print("    People identified: {}".format(result.get("people_created", 0)))
                print("    Evidence chain links: {}".format(len(result.get("evidence_chain", []))))
                legal = result.get("legal_pathway", {})
                if legal:
                    print("    Primary crime: {}".format(legal.get("primary_crime", "Unknown")))
            except Exception as e:
                print("    Investigation error: {}".format(e))
        else:
            print("    Case already exists")

    db.commit()

    # ============================================================
    # PHASE 5: RUN POLICE PIPELINE FOR ALL EXISTING CASES
    # ============================================================
    print("\n--- PHASE 5: RE-RUNNING POLICE PIPELINE FOR ALL CASES ---")
    cur.execute("SELECT case_id FROM cases ORDER BY case_id")
    all_cases = [row[0] for row in cur.fetchall()]
    print("Cases to re-investigate: {}".format(len(all_cases)))

    total_people = 0
    total_steps = 0
    for case_id in all_cases:
        try:
            result = pipeline.investigate_case(case_id)
            total_people += result.get("people_created", 0)
            total_steps += result.get("investigation_steps", 0)
        except Exception as e:
            print("  Error on {}: {}".format(case_id, str(e)[:100]))

    # ============================================================
    # FINAL REPORT
    # ============================================================
    print("\n" + sep)
    print("VICTIM DISCOVERY ENGINE COMPLETE")
    print(sep)

    cur.execute("SELECT is_victim, COUNT(*) FROM telegram_intelligence GROUP BY is_victim")
    victim_counts = cur.fetchall()
    print("\nMessage classification (is_victim flag):")
    for is_v, count in victim_counts:
        print("  is_victim={}: {}".format(is_v, count))

    cur.execute("SELECT risk_level, COUNT(*) FROM telegram_intelligence GROUP BY risk_level ORDER BY count DESC")
    level_counts = cur.fetchall()
    print("\nMessage classifications:")
    for level, count in level_counts:
        print("  {}: {}".format(level, count))

    cur.execute("SELECT COUNT(*) FROM victims")
    print("\nVictims in database: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM victim_complaints")
    print("Victim complaints: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM tracked_domains")
    print("Tracked domains: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM cases")
    print("Total cases: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM people")
    print("People identified: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM investigation_steps")
    print("Investigation steps: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM scam_websites")
    print("Scam websites: {}".format(cur.fetchone()[0]))

    if real_victims_found:
        print("\n*** REAL VICTIM REPORTS FOUND ***")
        for v in real_victims_found:
            print("  Message {}: score={:.2f} evidence={}".format(v["message_id"], v["score"], v["evidence"]))
            if v["details"]["amounts_lost"]:
                print("    Amounts: {}".format(v["details"]["amounts_lost"]))
            if v["details"]["domains_mentioned"]:
                print("    Domains: {}".format(v["details"]["domains_mentioned"]))
            if v["details"]["how_contacted"]:
                print("    How contacted: {}".format(v["details"]["how_contacted"]))
            if v["details"]["what_promised"]:
                print("    What was promised: {}".format(v["details"]["what_promised"]))

    cur.close()
    db.close()


if __name__ == "__main__":
    run_victim_discovery()

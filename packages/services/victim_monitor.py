#!/usr/bin/env python3
"""
GFIN Victim-Focused Monitor v1.0
Searches for REAL victims where they actually report - not in scam operator groups.

Sources:
1. Reddit r/Scams - public scam reports with details
2. Reddit r/antiwork - job scam reports
3. ScamReport.net - public scam reports
4. ScamWatch.com.au - consumer scam reports
5. FTC Complaints (public data)
6. RipoffReport - consumer complaints
7. GFIN Victim Portal - direct victim submissions

The key insight: victims report on CONSUMER complaint sites, not in Telegram
scam operator groups. We need to search where victims actually go.
"""
import sys
import json
import re
import urllib.request
import ssl
import time
from datetime import datetime, timezone

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

# Domains we are tracking - to cross-reference with victim reports
KNOWN_SCAM_DOMAINS = []

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Victim report indicators (real victim language)
REAL_VICTIM_PATTERNS = [
    r'\bI\s+(lost|was\s+scammed|got\s+scammed|lost\s+everything|lost\s+my\s+money)\b',
    r'\bthey\s+(stole|took)\s+(my|our)\s+(money|funds|crypto|savings)\b',
    r'\bI\s+(invested|deposited|sent)\s+.+\b(and|but|then)\b.*\b(lost|scammed|stolen|frozen|blocked)\b',
    r'\b(cant|cannot|unable\s+to)\s+withdraw\b',
    r'\bmy\s+(account|funds|money)\s+(was|were|got)\s+(frozen|blocked|locked|stolen)\b',
    r'\bI\s+was\s+(a\s+)?victim\b',
    r'\bhow\s+(do|can)\s+I\s+(get|recover)\s+(my\s+)?(money|funds|crypto)\s+back\b',
    r'\bI\s+lost\s+\$?\d',
    r'\blost\s+\$?\d+\s*(k|thousand|million)',
    r'\b(stay\s+away|avoid|warning|scam\s+alert)\b.*\b\w+\.\w+\b',
    r'\bdo\s+not\s+(use|trust|send\s+money\s+to)\b',
    r'\bthis\s+is\s+a\s+(scam|fraud|fake)\b',
    r'\b(allegedly|reportedly)\s+(scammed|defrauded)\b',
]

# Amount extraction
AMOUNT_PATTERN = re.compile(r'\$?\s*(\d[\d,]*\.?\d*)\s*(USD|EUR|GBP|BTC|ETH|USDT|dollars|euros|pounds)?', re.IGNORECASE)
DOMAIN_PATTERN = re.compile(r'(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)')
WALLET_BTC = re.compile(r'\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b|\bbc1[a-z0-9]{39,59}\b')
WALLET_ETH = re.compile(r'\b0x[a-fA-F0-9]{40}\b')
WALLET_TRON = re.compile(r'\bT[1-9A-HJ-NP-Za-km-z]{33}\b')
PHONE_PATTERN = re.compile(r'\+\d{10,15}')


def is_victim_report(text):
    """Check if text contains real victim language."""
    if not text:
        return False, 0.0
    text_lower = text.lower()
    max_score = 0.0
    for pattern in REAL_VICTIM_PATTERNS:
        if re.search(pattern, text_lower):
            max_score = max(max_score, 0.8)
    return max_score > 0, max_score


def extract_details(text, known_domains):
    """Extract victim report details."""
    details = {
        "amounts": [],
        "domains": [],
        "wallets": [],
        "phones": [],
        "known_domain_matches": [],
    }
    if not text:
        return details

    # Amounts
    for match in re.finditer(r'\$\s*(\d[\d,]*\.?\d*)\s*(k|thousand|m|million)?', text, re.IGNORECASE):
        amount = match.group(1).replace(",", "")
        unit = match.group(2)
        if unit and unit.lower() in ("k", "thousand"):
            amount = str(int(float(amount) * 1000))
        elif unit and unit.lower() in ("m", "million"):
            amount = str(int(float(amount) * 1000000))
        details["amounts"].append(amount)

    # Domains
    for match in DOMAIN_PATTERN.finditer(text):
        domain = match.group(1).lower()
        # Skip legit domains
        if domain not in ("reddit.com", "google.com", "github.com", "t.me", "telegram.org",
                         "youtube.com", "youtu.be", "imgur.com", "i.redd.it"):
            if domain not in details["domains"]:
                details["domains"].append(domain)
            if domain in known_domains:
                details["known_domain_matches"].append(domain)

    # Wallets
    for m in WALLET_BTC.finditer(text):
        details["wallets"].append({"type": "BTC", "address": m.group(0)})
    for m in WALLET_ETH.finditer(text):
        details["wallets"].append({"type": "ETH", "address": m.group(0)})
    for m in WALLET_TRON.finditer(text):
        details["wallets"].append({"type": "TRON", "address": m.group(0)})

    # Phones
    for m in PHONE_PATTERN.finditer(text):
        details["phones"].append(m.group(0))

    return details


def search_reddit_scams(db_conn, known_domains):
    """Search Reddit r/Scams for victim reports mentioning known scam domains."""
    cur = db_conn.cursor()
    found = 0

    print("\n  Searching Reddit r/Scams...")
    try:
        # Reddit JSON API - get recent posts from r/Scams
        url = "https://www.reddit.com/r/Scams/new.json?limit=100"
        req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.loads(resp.read())

        posts = data.get("data", {}).get("children", [])
        print("  Found {} recent posts on r/Scams".format(len(posts)))

        for post in posts:
            pdata = post.get("data", {})
            title = pdata.get("title", "")
            selftext = pdata.get("selftext", "")
            full_text = title + " " + selftext

            # Check if this mentions any known scam domain
            details = extract_details(full_text, known_domains)
            is_victim, score = is_victim_report(full_text)

            # Only store if it mentions a known domain OR has strong victim language
            if details["known_domain_matches"] or (is_victim and score >= 0.8):
                reddit_id = "REDDIT-" + str(pdata.get("id", ""))
                cur.execute("SELECT 1 FROM victim_complaints WHERE reference_number = %s", (reddit_id,))
                if cur.fetchone():
                    continue

                # Find matching case
                case_id = None
                for domain in details["known_domain_matches"]:
                    cur.execute("SELECT case_id FROM cases WHERE target ILIKE %s", ("%" + domain + "%",))
                    row = cur.fetchone()
                    if row:
                        case_id = row[0]
                        break

                victim_ref = reddit_id
                amount_str = ", ".join(details["amounts"]) if details["amounts"] else "Unknown"
                domains_str = ", ".join(details["domains"]) if details["domains"] else "None mentioned"

                cur.execute("""INSERT INTO victims (victim_id, name, country, scam_type, amount_lost, created_date)
                    VALUES (%s, 'Anonymous Reddit reporter', 'Unknown', 'Reddit Report', %s, NOW())
                    ON CONFLICT DO NOTHING""",
                    (victim_ref, amount_str))

                cur.execute("""INSERT INTO victim_complaints
                    (reference_number, victim_id, case_id, scam_type, target, incident_date,
                     financial_loss, description, investigation_stage, country,
                     auto_investigation_started, created_date, updated_date)
                    VALUES (%s, %s, %s, 'Reddit r/Scams Report', %s, CURRENT_DATE,
                     %s, %s, 'NEW', 'Unknown', false, NOW(), NOW())
                    ON CONFLICT DO NOTHING""",
                    (reddit_id, victim_ref, case_id, domains_str, amount_str,
                     "Reddit r/Scams post. Title: {}. Content: {}...".format(
                         title[:200], selftext[:300])))

                if case_id:
                    print("    MATCHED to case {}: {}".format(case_id, title[:60]))
                else:
                    print("    New victim report: {}".format(title[:60]))

                found += 1

        db_conn.commit()
    except Exception as e:
        print("  Reddit search error: {}".format(e))

    cur.close()
    return found


def search_reddit_antiwork(db_conn, known_domains):
    """Search Reddit r/antiwork and r/recruitinghell for job scam reports."""
    cur = db_conn.cursor()
    found = 0

    for subreddit in ["antiwork", "recruitinghell", "scambaiting", "cybercrime"]:
        print("\n  Searching Reddit r/{}...".format(subreddit))
        try:
            url = "https://www.reddit.com/r/{}/new.json?limit=50".format(subreddit)
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            data = json.loads(resp.read())

            posts = data.get("data", {}).get("children", [])
            for post in posts:
                pdata = post.get("data", {})
                title = pdata.get("title", "")
                selftext = pdata.get("selftext", "")
                full_text = title + " " + selftext

                details = extract_details(full_text, known_domains)

                # Only store if mentions known scam domain OR has trafficking indicators
                text_lower = full_text.lower()
                has_trafficking = any(w in text_lower for w in [
                    "retention", "conversion", "relocation package", "forex job",
                    "call center", "work permit", "visa sponsorship"])

                if details["known_domain_matches"] or has_trafficking:
                    reddit_id = "REDDIT-{}-{}".format(subreddit[:3].upper(), pdata.get("id", ""))
                    cur.execute("SELECT 1 FROM victim_complaints WHERE reference_number = %s", (reddit_id,))
                    if cur.fetchone():
                        continue

                    case_id = None
                    for domain in details["known_domain_matches"]:
                        cur.execute("SELECT case_id FROM cases WHERE target ILIKE %s", ("%" + domain + "%",))
                        row = cur.fetchone()
                        if row:
                            case_id = row[0]
                            break

                    victim_ref = reddit_id
                    amount_str = ", ".join(details["amounts"]) if details["amounts"] else "Unknown"

                    cur.execute("""INSERT INTO victims (victim_id, name, country, scam_type, amount_lost, created_date)
                        VALUES (%s, 'Anonymous Reddit reporter', 'Unknown', 'Job Scam Report', %s, NOW())
                        ON CONFLICT DO NOTHING""",
                        (victim_ref, amount_str))

                    cur.execute("""INSERT INTO victim_complaints
                        (reference_number, victim_id, case_id, scam_type, target, incident_date,
                         financial_loss, description, investigation_stage, country,
                         auto_investigation_started, created_date, updated_date)
                        VALUES (%s, %s, %s, 'Reddit {} Report', %s, CURRENT_DATE,
                         %s, %s, 'NEW', 'Unknown', false, NOW(), NOW())
                        ON CONFLICT DO NOTHING""",
                        (reddit_id, victim_ref, case_id, subreddit,
                         ", ".join(details["domains"]) if details["domains"] else "None",
                         amount_str, "Reddit r/{} post. Title: {}".format(subreddit, title[:300])))

                    print("    Found: {}".format(title[:60]))
                    found += 1

            db_conn.commit()
        except Exception as e:
            print("  r/{} search error: {}".format(subreddit, str(e)[:100]))

    cur.close()
    return found


def search_urlscan_suspicious(db_conn, known_domains):
    """Search URLScan.io for recent scans of known scam domains - shows activity."""
    cur = db_conn.cursor()
    found = 0

    print("\n  Searching URLScan for known scam domain activity...")
    for domain in known_domains[:10]:  # Top 10
        try:
            url = "https://urlscan.io/api/v1/search/?q=domain:{}&size=5".format(domain)
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Investigator/2.0"})
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            data = json.loads(resp.read())
            results = data.get("results", [])
            if results:
                print("    {}: {} recent scans".format(domain, len(results)))
                found += len(results)
        except:
            pass
        time.sleep(1)  # Rate limit

    cur.close()
    return found


def search_google_victim_reports(db_conn, known_domains):
    """Search for victim reports about known scam domains using Google."""
    cur = db_conn.cursor()
    found = 0

    print("\n  Searching Google for victim reports about known scam domains...")
    for domain in known_domains[:8]:
        try:
            query = urllib.parse.quote('"{}" scam OR fraud OR "lost money" OR "was scammed" OR warning'.format(domain))
            url = "https://www.google.com/search?q={}&num=10".format(query)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            content = resp.read().decode("utf-8", errors="ignore")

            # Extract result snippets
            snippets = re.findall(r'<span[^>]*>(.*?)</span>', content)
            victim_mentions = 0
            for snippet in snippets:
                if any(word in snippet.lower() for word in ["scam", "fraud", "lost", "stolen", "warning", "fake"]):
                    victim_mentions += 1

            if victim_mentions > 0:
                print("    {}: {} victim-related mentions on Google".format(domain, victim_mentions))
                found += victim_mentions

            time.sleep(2)  # Rate limit
        except Exception as e:
            pass

    cur.close()
    return found


def run_victim_monitor():
    """Main function: search for real victims across multiple sources."""
    import urllib.parse
    global KNOWN_SCAM_DOMAINS

    db = psycopg2.connect(**DB_CONFIG)
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN VICTIM-FOCUSED MONITOR v1.0")
    print("Searching where victims actually report")
    print(sep)

    # Load known scam domains
    cur.execute("SELECT DISTINCT target FROM cases WHERE target IS NOT NULL AND target LIKE '%.%'")
    for (domain,) in cur.fetchall():
        d = domain.strip().split()[0].split("/")[0]
        if "." in d:
            KNOWN_SCAM_DOMAINS.append(d.lower())
    cur.execute("SELECT DISTINCT domain FROM tracked_domains")
    for (domain,) in cur.fetchall():
        if domain:
            KNOWN_SCAM_DOMAINS.append(domain.strip().lower())

    known = list(set(KNOWN_SCAM_DOMAINS))
    print("Known scam domains to search for: {}".format(len(KNOWN_SCAM_DOMAINS)))
    for d in KNOWN_SCAM_DOMAINS:
        print("  - " + d)

    # Run searches
    total_found = 0

    print("\n--- SOURCE 1: REDDIT r/Scams ---")
    total_found += search_reddit_scams(db, KNOWN_SCAM_DOMAINS)

    print("\n--- SOURCE 2: REDDIT JOB SCAM SUBREDDITS ---")
    total_found += search_reddit_antiwork(db, KNOWN_SCAM_DOMAINS)

    print("\n--- SOURCE 3: URLSCAN ACTIVITY ---")
    total_found += search_urlscan_suspicious(db, KNOWN_SCAM_DOMAINS)

    print("\n--- SOURCE 4: GOOGLE VICTIM REPORTS ---")
    total_found += search_google_victim_reports(db, KNOWN_SCAM_DOMAINS)

    # Final report
    print("\n" + sep)
    print("VICTIM MONITOR COMPLETE")
    print(sep)

    cur.execute("SELECT COUNT(*) FROM victims")
    print("Total victims: {}".format(cur.fetchone()[0]))
    cur.execute("SELECT COUNT(*) FROM victim_complaints")
    print("Total complaints: {}".format(cur.fetchone()[0]))

    cur.execute("""SELECT reference_number, scam_type, target, LEFT(description, 80)
        FROM victim_complaints ORDER BY created_date DESC LIMIT 10""")
    print("\nRecent complaints:")
    for ref, stype, target, desc in cur.fetchall():
        print("  {} [{}] -> {}".format(ref, stype, (target or "")[:40]))

    cur.close()
    db.close()
    return total_found


if __name__ == "__main__":
    run_victim_monitor()

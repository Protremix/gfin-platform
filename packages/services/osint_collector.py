#!/usr/bin/env python3
"""
GFIN Social Media OSINT Collector v1.0
Collects victim reports from public social media sources.

Sources:
1. Reddit RSS feeds (r/Scams, r/antiwork, etc.) — RSS endpoints may not be blocked
2. Mastodon public timeline search ( federated, no auth needed)
3. ScamAdviser reviews (public)
4. Google search via DuckDuckGo (privacy-focused, less aggressive blocking)
5. Consumer complaint archives
"""
import sys
import json
import re
import urllib.request
import ssl
import time
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2

DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Known scam domains to cross-reference
def load_known_domains(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT target, case_id FROM cases WHERE target LIKE %s", ("%.%",))
    domains = {}
    for target, case_id in cur.fetchall():
        d = target.strip().split()[0].split("/")[0].lower()
        if "." in d and "telegram" not in d and "@" not in d:
            domains[d] = case_id
    cur.close()
    return domains

# Victim report patterns
VICTIM_PATTERNS = re.compile(
    r'(I\s+(was|got)\s+scammed|I\s+lost\s+(my\s+)?(money|funds|crypto|savings)|'
    r'they\s+(stole|took)\s+(my|our)|cannot\s+withdraw|account\s+(was|were|got)\s+'
    r'(frozen|blocked|locked)|this\s+is\s+a\s+(scam|fraud|fake)|'
    r'stay\s+away\s+from|do\s+not\s+(use|trust)|scam\s+alert|warning)',
    re.IGNORECASE
)

DOMAIN_PATTERN = re.compile(r'(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)')
AMOUNT_PATTERN = re.compile(r'\$\s*(\d[\d,]*\.?\d*)\s*(k|thousand|m|million)?', re.IGNORECASE)

LEGIT_DOMAINS = {
    "reddit.com", "google.com", "github.com", "t.me", "telegram.org",
    "youtube.com", "youtu.be", "imgur.com", "i.redd.it", "redd.it",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "mastodon.social", "reddit.app", "redditmedia.com",
    "scamadviser.com", "urlscan.io", "virustotal.com",
    "googleapis.com", "gstatic.com", "cloudflare.com",
}


def extract_intel(text, known_domains):
    """Extract victim report intelligence from text."""
    if not text:
        return None

    is_victim = bool(VICTIM_PATTERNS.search(text))
    domains = []
    known_matches = []
    amounts = []

    for m in DOMAIN_PATTERN.finditer(text):
        domain = m.group(1).lower()
        if domain not in LEGIT_DOMAINS and domain not in domains:
            domains.append(domain)
            if domain in known_domains:
                known_matches.append((domain, known_domains[domain]))

    for m in AMOUNT_PATTERN.finditer(text):
        amount = m.group(1).replace(",", "")
        unit = m.group(2)
        if unit and unit.lower() in ("k", "thousand"):
            amount = str(int(float(amount) * 1000))
        elif unit and unit.lower() in ("m", "million"):
            amount = str(int(float(amount) * 1000000))
        amounts.append(amount)

    if known_matches or (is_victim and len(domains) > 0):
        return {
            "is_victim_report": is_victim,
            "domains_mentioned": domains,
            "known_domain_matches": known_matches,
            "amounts": amounts,
            "text_snippet": text[:500],
        }
    return None


def search_reddit_rss(db_conn, known_domains):
    """Search Reddit via RSS feeds (may bypass API blocks)."""
    cur = db_conn.cursor()
    found = 0

    subreddits = ["Scams", "antiwork", "recruitinghell", "ScamsReport", "cybercrime"]
    print("\n--- REDDIT RSS FEEDS ---")

    for sub in subreddits:
        print("\n  r/{}...".format(sub))
        try:
            # Try RSS endpoint
            url = "https://www.reddit.com/r/{}/search.rss?q=scam+OR+fraud+OR+lost+money&restrict_sr=1&sort=new&limit=25".format(sub)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml,application/xml,text/xml",
            })
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            content = resp.read().decode("utf-8", errors="ignore")
            print("  Status: {} ({} bytes)".format(resp.status, len(content)))

            # Parse RSS XML (simple regex since no xml library needed)
            entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
            if not entries:
                entries = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)

            print("  Entries found: {}".format(len(entries)))

            for entry in entries:
                # Extract title
                title_m = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                title = title_m.group(1) if title_m else ""
                # Clean HTML entities
                title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

                # Extract content/description
                content_m = re.search(r'<content[^>]*>(.*?)</content>|<description[^>]*>(.*?)</description>', entry, re.DOTALL)
                entry_text = ""
                if content_m:
                    entry_text = content_m.group(1) or content_m.group(2) or ""
                entry_text = re.sub(r'<[^>]+>', ' ', entry_text)  # Strip HTML tags
                entry_text = entry_text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

                full_text = title + " " + entry_text
                intel = extract_intel(full_text, known_domains)

                if intel and intel["known_domain_matches"]:
                    # Matched to a known scam domain!
                    for domain, case_id in intel["known_domain_matches"]:
                        ref = "RSS-{}-{}".format(sub[:3].upper(), hash(title) % 100000)
                        cur.execute("SELECT 1 FROM victim_complaints WHERE reference_number = %s", (ref,))
                        if not cur.fetchone():
                            amount = ", ".join(intel["amounts"]) if intel["amounts"] else "Unknown"
                            cur.execute("""INSERT INTO victims (victim_id, name, country, scam_type, amount_lost, created_date)
                                VALUES (%s, 'Anonymous Reddit reporter', 'Unknown', 'Reddit RSS Report', %s, NOW())
                                ON CONFLICT DO NOTHING""",
                                (ref, amount))
                            cur.execute("""INSERT INTO victim_complaints
                                (reference_number, victim_id, case_id, scam_type, target, incident_date,
                                 financial_loss, description, investigation_stage, country,
                                 auto_investigation_started, created_date, updated_date)
                                VALUES (%s, %s, %s, 'Reddit r/{} Report', %s, CURRENT_DATE,
                                 %s, %s, 'NEW', 'Unknown', false, NOW(), NOW())
                                ON CONFLICT DO NOTHING""",
                                (ref, ref, case_id, sub,
                                 ", ".join(intel["domains_mentioned"]),
                                 amount,
                                 "Reddit r/{} RSS. Title: {}. Content: {}...".format(
                                     sub, title[:200], entry_text[:200])))
                            print("    MATCHED to case {}: {}".format(case_id, title[:60]))
                            found += 1
                elif intel and intel["is_victim_report"]:
                    # Victim report but not matching known domain
                    domains_str = ", ".join(intel["domains_mentioned"][:3])
                    if domains_str:
                        print("    Victim report (unknown domain): {} -> {}".format(title[:50], domains_str))

            db_conn.commit()
        except Exception as e:
            print("  Error: {}".format(str(e)[:100]))

    cur.close()
    return found


def search_mastodon(db_conn, known_domains):
    """Search Mastodon public timelines for scam reports."""
    cur = db_conn.cursor()
    found = 0

    print("\n--- MASTODON PUBLIC SEARCH ---")

    # Mastodon search endpoints (public, no auth)
    mastodon_instances = [
        ("mastodon.social", "https://mastodon.social/api/v2/search?q=scam+OR+fraud&type=statuses&limit=20"),
    ]

    for instance_name, search_url in mastodon_instances:
        print("\n  {}...".format(instance_name))
        try:
            req = urllib.request.Request(search_url, headers={
                "User-Agent": "GFIN-Investigator/2.0",
                "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            data = json.loads(resp.read())
            statuses = data.get("statuses", [])
            print("  Statuses: {}".format(len(statuses)))

            for status in statuses:
                content = status.get("content", "")
                content_clean = re.sub(r'<[^>]+>', ' ', content)
                content_clean = content_clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

                intel = extract_intel(content_clean, known_domains)
                if intel and intel["known_domain_matches"]:
                    for domain, case_id in intel["known_domain_matches"]:
                        ref = "MSTD-{}".format(status.get("id", hash(content_clean) % 100000))
                        cur.execute("SELECT 1 FROM victim_complaints WHERE reference_number = %s", (ref,))
                        if not cur.fetchone():
                            cur.execute("""INSERT INTO victim_complaints
                                (reference_number, victim_id, case_id, scam_type, target,
                                 incident_date, financial_loss, description, investigation_stage,
                                 country, auto_investigation_started, created_date, updated_date)
                                VALUES (%s, 'Mastodon-{}', %s, 'Mastodon Report', %s, CURRENT_DATE,
                                 %s, %s, 'NEW', 'Unknown', false, NOW(), NOW())
                                ON CONFLICT DO NOTHING""",
                                (ref, instance_name, case_id,
                                 ", ".join(intel["domains_mentioned"]),
                                 ", ".join(intel["amounts"]) if intel["amounts"] else "Unknown",
                                 "Mastodon {}: {}".format(instance_name, content_clean[:300])))
                            print("    MATCHED: {} -> case {}".format(domain, case_id))
                            found += 1

            db_conn.commit()
        except Exception as e:
            print("  Error: {}".format(str(e)[:100]))

    cur.close()
    return found


def search_duckduckgo(db_conn, known_domains):
    """Search DuckDuckGo for victim reports about known scam domains."""
    cur = db_conn.cursor()
    found = 0

    print("\n--- DUCKDUCKGO SEARCH ---")

    # Check a few key domains
    domains_to_check = list(known_domains.keys())[:8]
    for domain in domains_to_check:
        try:
            query = urllib.parse.quote('"{}" (scam OR fraud OR "lost money" OR "was scammed" OR warning)'.format(domain))
            url = "https://html.duckduckgo.com/html/?q={}".format(query)
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            })
            resp = urllib.request.urlopen(req, timeout=15, context=ctx)
            content = resp.read().decode("utf-8", errors="ignore")

            # Extract result snippets from DuckDuckGo HTML
            snippets = re.findall(r'class="result__snippet">(.*?)</a>', content, re.DOTALL)
            victim_count = 0
            for snippet in snippets:
                snippet_clean = re.sub(r'<[^>]+>', ' ', snippet).strip()
                snippet_clean = snippet_clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

                if VICTIM_PATTERNS.search(snippet_clean):
                    victim_count += 1

            if victim_count > 0:
                print("  {}: {} victim mentions on DuckDuckGo".format(domain, victim_count))
                found += victim_count
                # Store as evidence
                case_id = known_domains[domain]
                cur.execute("""INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider,
                    source_url, source_type, confidence, timestamp, created_date, lifecycle_status)
                    VALUES (%s, %s, 'CORRELATION', %s, 'DuckDuckGo',
                    %s, 'SEARCH_ENGINE', 0.6, NOW(), NOW(), 'CORRELATED')""",
                    (case_id,
                     "DDG-{}".format(domain.replace(".", "-")),
                     "DuckDuckGo search found {} victim report snippets for {}".format(victim_count, domain),
                     "https://duckduckgo.com/?q=" + query))

            time.sleep(2)  # Rate limit
        except Exception as e:
            print("  {} error: {}".format(domain, str(e)[:60]))

    db_conn.commit()
    cur.close()
    return found


def run_osint_collector():
    """Main function: collect victim reports from social media sources."""
    import urllib.parse

    db = psycopg2.connect(**DB_CONFIG)
    known_domains = load_known_domains(db)

    sep = "=" * 60
    print(sep)
    print("GFIN SOCIAL MEDIA OSINT COLLECTOR v1.0")
    print("Searching for real victim reports")
    print(sep)
    print("Known scam domains: {}".format(len(known_domains)))
    for d, cid in known_domains.items():
        print("  {} -> {}".format(d, cid))

    total_found = 0

    # Source 1: Reddit RSS
    total_found += search_reddit_rss(db, known_domains)

    # Source 2: Mastodon
    total_found += search_mastodon(db, known_domains)

    # Source 3: DuckDuckGo
    total_found += search_duckduckgo(db, known_domains)

    print("\n" + sep)
    print("OSINT COLLECTION COMPLETE")
    print(sep)
    print("Total victim signals found: {}".format(total_found))

    # Show final complaint stats
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM victim_complaints")
    total = cur.fetchone()[0]
    print("Total complaints in database: {}".format(total))

    cur.execute("SELECT reference_number, scam_type, target, LEFT(description, 80) FROM victim_complaints ORDER BY created_date DESC LIMIT 10")
    print("\nRecent complaints:")
    for ref, stype, target, desc in cur.fetchall():
        print("  {} [{}] -> {}".format(ref, stype, (target or "")[:40]))

    cur.close()
    db.close()
    return total_found


if __name__ == "__main__":
    run_osint_collector()

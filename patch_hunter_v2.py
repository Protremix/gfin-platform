#!/usr/bin/env python3
"""Patch autonomous_hunter_v2.py with evidence gating."""
import re

with open('/gfin/autonomous_hunter_v2.py', 'r') as f:
    code = f.read()

# 1. Add flag_domain_in_db and has_strong_evidence before create_case
m = re.search(r'^async def create_case', code, re.MULTILINE)
if not m:
    print('ERROR: create_case not found')
    exit(1)

pos = m.start()

flag_funcs = '''
# ============================================================
# FLAG DOMAIN (always) + EVIDENCE GATE (case opening)
# ============================================================

async def flag_domain_in_db(domain, inv):
    """Flag a domain in scam_websites without opening a full case."""
    import asyncpg
    DB = {"host": "127.0.0.1", "port": 5432, "user": "gfin", "password": "GfinSecure2026!", "database": "gfin"}
    conn = await asyncpg.connect(**DB)
    try:
        existing = await conn.fetchrow("SELECT id, report_count, sources FROM scam_websites WHERE domain = $1", domain)
        si = inv.get("scam_indicators", [{}])
        risk_score = si[0].get("risk_score", 0) if si and isinstance(si[0], dict) else 0
        risk_level = si[0].get("risk_level", "UNKNOWN") if si and isinstance(si[0], dict) else "UNKNOWN"
        cats = si[0].get("categories", []) if si and isinstance(si[0], dict) else []
        wallets = [d.get("value", "") for d in inv.get("digital_identifiers", []) if isinstance(d, dict) and d.get("type") == "CRYPTO_WALLET"]
        phones = [d.get("value", "") for d in inv.get("digital_identifiers", []) if isinstance(d, dict) and d.get("type") == "PHONE"]
        countries = inv.get("affected_countries", [])
        source = inv.get("source", "HUNTER")
        if existing:
            old_sources = list(existing.get("sources", []) or [])
            new_sources = list(set(old_sources + [source]))
            await conn.execute(
                "UPDATE scam_websites SET report_count=$1, sources=$2, last_reported=NOW(), risk_level=$3, countries_affected=$4, wallet_addresses=$5, phone_numbers=$6, description=$7 WHERE domain=$8",
                (existing["report_count"] or 1) + 1, new_sources, risk_level, countries, wallets, phones,
                inv.get("summary", "")[:500], domain)
            logger.info("  Flagged (updated): %s (report #%d)" % (domain, (existing["report_count"] or 1) + 1))
            return False
        else:
            await conn.execute(
                "INSERT INTO scam_websites (domain, scam_type, risk_level, report_count, sources, description, countries_affected, wallet_addresses, phone_numbers, is_verified, status) VALUES ($1,$2,$3,1,$4,$5,$6,$7,$8,false,'FLAGGED')",
                domain, ", ".join(cats) if cats else "SUSPICIOUS", risk_level, [source],
                inv.get("summary", "")[:500], countries, wallets, phones)
            logger.info("  Flagged (new): %s (risk: %s, source: %s)" % (domain, risk_level, source))
            return True
    except Exception as e:
        logger.error("  Flag failed for %s: %s" % (domain, e))
        return False
    finally:
        await conn.close()


def has_strong_evidence(inv):
    """Only open a case if there is REAL evidence."""
    si = inv.get("scam_indicators", [])
    risk_score = 0
    risk_level = "UNKNOWN"
    categories = []
    if si and isinstance(si, list) and isinstance(si[0], dict):
        risk_score = si[0].get("risk_score", 0)
        risk_level = si[0].get("risk_level", "UNKNOWN")
        categories = si[0].get("categories", [])

    if risk_score >= 40:
        logger.info("  GATE PASS: risk %d (%s)" % (risk_score, risk_level))
        return True
    if categories:
        logger.info("  GATE PASS: patterns %s" % categories)
        return True
    if "OPENPHISH" in inv.get("source", "").upper():
        logger.info("  GATE PASS: OpenPhish confirmed")
        return True
    if len(inv.get("digital_identifiers", [])) >= 5:
        logger.info("  GATE PASS: %d identifiers" % len(inv["digital_identifiers"]))
        return True
    if inv.get("confidence", 0) >= 0.5:
        logger.info("  GATE PASS: confidence %.2f" % inv["confidence"])
        return True
    for loc in inv.get("physical_locations", []):
        isp = str(loc.get("isp", "")).lower()
        if isp and "cloudflare" not in isp and "amazon" not in isp:
            logger.info("  GATE PASS: real location %s (%s)" % (loc.get("city", "?"), loc.get("isp", "?")))
            return True

    logger.info("  GATE FAIL: risk=%d, patterns=%s, ids=%d, conf=%.2f" % (
        risk_score, categories, len(inv.get("digital_identifiers", [])), inv.get("confidence", 0)))
    return False

'''

code = code[:pos] + flag_funcs + code[pos:]

# 2. Replace run_cycle
old_run = '''async def run_cycle():
    logger.info("=" * 60)
    logger.info("STARTING AUTONOMOUS HUNTER v2.0 CYCLE")
    logger.info("=" * 60)
    targets = discover_targets()
    if not targets:
        logger.info("No new targets. Sleeping."); return 0
    cases = 0
    for t in targets[:MAX_CASES_PER_CYCLE]:
        d = t["domain"]
        if d in _investigated: continue
        logger.info(f"INVESTIGATING: {d} (source: {t['source']})")
        try:
            inv = investigate_domain(d, t["source"], t)
            await create_case(inv)
            _investigated.add(d)
            cases += 1
        except Exception as e:
            logger.error(f"  Failed: {e}")
        time.sleep(3)
    logger.info(f"Cycle complete: {cases} cases from {len(targets)} targets")
    return cases'''

new_run = '''async def run_cycle():
    logger.info("=" * 60)
    logger.info("STARTING AUTONOMOUS HUNTER v2.1 EVIDENCE-GATED CYCLE")
    logger.info("=" * 60)
    targets = discover_targets()
    if not targets:
        logger.info("No new targets. Sleeping."); return 0
    cases = 0
    flagged = 0
    skipped = 0
    for t in targets[:MAX_CASES_PER_CYCLE]:
        d = t["domain"]
        if d in _investigated:
            skipped += 1
            continue
        logger.info("INVESTIGATING: %s (source: %s)" % (d, t["source"]))
        try:
            inv = investigate_domain(d, t["source"], t)

            # ALWAYS flag in database
            await flag_domain_in_db(d, inv)
            flagged += 1

            # Only open case with STRONG evidence
            if has_strong_evidence(inv):
                case_id = await create_case(inv)
                cases += 1
                logger.info("  => CASE OPENED: %s for %s" % (case_id, d))
            else:
                logger.info("  => FLAGGED ONLY: %s (insufficient evidence)" % d)

            _investigated.add(d)
        except Exception as e:
            logger.error("  Failed: %s" % e)
        time.sleep(3)
    logger.info("Cycle complete: %d cases opened, %d flagged, %d skipped" % (cases, flagged, skipped))
    return cases'''

if old_run in code:
    code = code.replace(old_run, new_run)
    print("run_cycle replaced OK")
else:
    print("ERROR: run_cycle pattern not found")
    # Debug
    for i, line in enumerate(code.split("\n")):
        if "run_cycle" in line:
            print("  Line %d: %s" % (i, repr(line)))

# 3. Update version
code = code.replace("v2.0", "v2.1")

with open('/gfin/autonomous_hunter_v2.py', 'w') as f:
    f.write(code)
print("Done")

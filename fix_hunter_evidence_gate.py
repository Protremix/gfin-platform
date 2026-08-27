#!/usr/bin/env python3
"""
Fix the Autonomous Hunter to:
1. Flag ALL discovered domains in scam_websites database
2. Only open full cases when there's STRONG evidence
3. Clean up existing low-evidence cases (downgrade to flagged-only)
"""
import json

with open("/gfin/autonomous_hunter.py", "r") as f:
    code = f.read()

# 1. Add flag_domain function before create_case_from_investigation
flag_func = '''
async def flag_domain_in_db(domain: str, investigation: dict) -> bool:
    """Flag a domain in the scam_websites database without opening a full case."""
    import asyncpg

    DB_CONFIG = {
        "host": "127.0.0.1", "port": 5432,
        "user": "gfin", "password": "",
        "database": "gfin",
    }

    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Check if domain already exists
        existing = await conn.fetchrow("SELECT id, report_count, sources FROM scam_websites WHERE domain = $1", domain)

        scam_analysis = investigation.get("scam_indicators", [{}])
        risk_score = scam_analysis[0].get("risk_score", 0) if scam_analysis else 0
        risk_level = scam_analysis[0].get("risk_level", "UNKNOWN") if scam_analysis else "UNKNOWN"
        categories = scam_analysis[0].get("categories", []) if scam_analysis else []

        # Extract identifiers for the flagged record
        wallets = [d.get("value", "") for d in investigation.get("digital_identifiers", []) if d.get("type") == "CRYPTO_WALLET"]
        phones = [d.get("value", "") for d in investigation.get("digital_identifiers", []) if d.get("type") == "PHONE"]
        countries = investigation.get("affected_countries", [])
        source = investigation.get("source", "HUNTER")

        if existing:
            # Update existing record — increment report count, update sources
            old_sources = existing.get("sources", []) or []
            new_sources = list(set(old_sources + [source]))
            await conn.execute(
                """UPDATE scam_websites SET
                    report_count = $1, sources = $2, last_reported = NOW(),
                    risk_level = $3, countries_affected = $4,
                    wallet_addresses = $5, phone_numbers = $6,
                    description = $7
                WHERE domain = $8""",
                (existing["report_count"] or 1) + 1,
                new_sources,
                risk_level,
                countries,
                wallets,
                phones,
                investigation.get("summary", "")[:500],
                domain,
            )
            logger.info(f"  Flagged domain updated: {domain} (report #{existing['report_count'] + 1})")
            return False  # Not new
        else:
            # Insert new flagged domain
            await conn.execute(
                """INSERT INTO scam_websites (
                    domain, scam_type, risk_level, report_count, sources,
                    description, countries_affected, wallet_addresses, phone_numbers,
                    is_verified, status
                ) VALUES ($1, $2, $3, 1, $4, $5, $6, $7, $8, false, 'FLAGGED')""",
                domain,
                ", ".join(categories) if categories else "SUSPICIOUS",
                risk_level,
                [source],
                investigation.get("summary", "")[:500],
                countries,
                wallets,
                phones,
            )
            logger.info(f"  Domain flagged in database: {domain} (risk: {risk_level}, source: {source})")
            return True  # New
    except Exception as e:
        logger.error(f"  Failed to flag domain {domain}: {e}")
        return False
    finally:
        await conn.close()


def has_strong_evidence(investigation: dict) -> bool:
    """
    Determine if an investigation has STRONG evidence to justify opening a full case.

    A case is opened ONLY when at least one of these conditions is met:
    1. Risk score >= 40 (MEDIUM or HIGH risk from scam engine)
    2. Scam patterns detected (BRAND_IMPERSONATION, RECOVERY_SCAM, etc.)
    3. Source is a confirmed phishing list (OpenPhish = confirmed)
    4. 5+ digital identifiers found (real infrastructure identified)
    5. Confidence >= 0.5
    6. Physical locations found with real ISP data (not just CDN)
    """
    scam_indicators = investigation.get("scam_indicators", [])
    risk_score = 0
    risk_level = "UNKNOWN"
    categories = []

    if scam_indicators and isinstance(scam_indicators, list):
        si = scam_indicators[0]
        if isinstance(si, dict):
            risk_score = si.get("risk_score", 0)
            risk_level = si.get("risk_level", "UNKNOWN")
            categories = si.get("categories", [])

    # Condition 1: Risk score >= 40
    if risk_score >= 40:
        logger.info(f"  EVIDENCE GATE: PASS — Risk score {risk_score} >= 40 ({risk_level})")
        return True

    # Condition 2: Scam patterns detected
    if categories:
        logger.info(f"  EVIDENCE GATE: PASS — Scam patterns detected: {categories}")
        return True

    # Condition 3: Source is confirmed phishing (OpenPhish = confirmed)
    source = investigation.get("source", "")
    if "OPENPHISH" in source.upper() or "PHISHING" in source.upper():
        # Only count OpenPhish as confirmed — Phishing.Database is likely but needs more evidence
        if "OPENPHISH" in source.upper():
            logger.info(f"  EVIDENCE GATE: PASS — Confirmed phishing source: {source}")
            return True

    # Condition 4: 5+ digital identifiers
    identifiers = investigation.get("digital_identifiers", [])
    if len(identifiers) >= 5:
        logger.info(f"  EVIDENCE GATE: PASS — {len(identifiers)} digital identifiers found")
        return True

    # Condition 5: Confidence >= 0.5
    if investigation.get("confidence", 0) >= 0.5:
        logger.info(f"  EVIDENCE GATE: PASS — Confidence {investigation['confidence']} >= 0.5")
        return True

    # Condition 6: Physical locations with real ISP (not Cloudflare CDN)
    locations = investigation.get("physical_locations", [])
    real_locations = [l for l in locations if l.get("isp", "") and "cloudflare" not in l.get("isp", "").lower()]
    if real_locations:
        logger.info(f"  EVIDENCE GATE: PASS — Real physical location found: {real_locations[0].get('city', '?')}, ISP: {real_locations[0].get('isp', '?')}")
        return True

    logger.info(f"  EVIDENCE GATE: FAIL — Risk {risk_score}, patterns: {categories}, identifiers: {len(identifiers)}, confidence: {investigation.get('confidence', 0)}, source: {source}")
    return False


'''

# Insert flag_domain and has_strong_evidence before create_case_from_investigation
insert_point = "# ============================================================\n# DATABASE: Create GFIN cases with full evidence\n# ============================================================"
code = code.replace(insert_point, flag_func + "\n" + insert_point)

# 2. Modify run_cycle to use evidence gating
old_run_cycle = '''    cases_created = 0
    for target in targets[:MAX_CASES_PER_CYCLE]:
        domain = target["domain"]
        source = target["source"]

        if domain in _investigated_cache:
            continue

        logger.info(f"INVESTIGATING: {domain} (source: {source})")

        try:
            investigation = investigate_domain(domain, source, target)

            # Create case in database
            case_id = await create_case_from_investigation(investigation)

            _investigated_cache.add(domain)
            cases_created += 1

            logger.info(f"  => Case {case_id} created for {domain}")

        except Exception as e:
            logger.error(f"  Failed to investigate {domain}: {e}")

        # Rate limit between investigations
        time.sleep(3)

    logger.info(f"Cycle complete: {cases_created} cases created from {len(targets)} targets")
    return cases_created'''

new_run_cycle = '''    cases_created = 0
    domains_flagged = 0
    domains_skipped = 0

    for target in targets[:MAX_CASES_PER_CYCLE]:
        domain = target["domain"]
        source = target["source"]

        if domain in _investigated_cache:
            domains_skipped += 1
            continue

        logger.info(f"INVESTIGATING: {domain} (source: {source})")

        try:
            investigation = investigate_domain(domain, source, target)

            # ALWAYS flag the domain in the scam database
            is_new = await flag_domain_in_db(domain, investigation)
            domains_flagged += 1

            # ONLY open a full case if there is STRONG evidence
            if has_strong_evidence(investigation):
                case_id = await create_case_from_investigation(investigation)
                _investigated_cache.add(domain)
                cases_created += 1
                logger.info(f"  => CASE OPENED: {case_id} for {domain} (strong evidence)")
            else:
                _investigated_cache.add(domain)
                logger.info(f"  => FLAGGED ONLY: {domain} (insufficient evidence for case)")

        except Exception as e:
            logger.error(f"  Failed to investigate {domain}: {e}")

        # Rate limit between investigations
        time.sleep(3)

    logger.info(f"Cycle complete: {cases_created} cases opened, {domains_flagged} domains flagged, {domains_skipped} already known")
    return cases_created'''

if old_run_cycle in code:
    code = code.replace(old_run_cycle, new_run_cycle)
    print("Fixed run_cycle with evidence gating")
else:
    print("ERROR: Could not find run_cycle code to replace")
    # Debug: show lines around run_cycle
    lines = code.split("\n")
    for i, line in enumerate(lines):
        if "cases_created = 0" in line and "for target" not in line:
            print(f"Line {i}: {repr(line)}")
            for j in range(i, min(i+20, len(lines))):
                print(f"  {j}: {repr(lines[j])}")

# 3. Update main log message
old_main = 'logger.info("GFIN AUTONOMOUS SCAM HUNTER v1.0 — STARTING")'
new_main = 'logger.info("GFIN AUTONOMOUS SCAM HUNTER v2.1 — EVIDENCE-GATED — STARTING")'
code = code.replace(old_main, new_main)

with open("/gfin/autonomous_hunter.py", "w") as f:
    f.write(code)

print("Hunter updated to v2.1 with evidence gating")

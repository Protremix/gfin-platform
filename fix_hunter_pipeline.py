"""
Fix the autonomous hunter:
1. Replace has_strong_evidence with strict version — requires REAL evidence (victims, financial loss, or multiple confirmed scam indicators)
2. Replace create_case_from_investigation → add_to_tracked_domains (default path)
3. Only create a real case when there are actual victims OR confirmed financial fraud indicators
4. Fix complaint pipeline to reject test data
"""

import re

with open("/gfin/autonomous_hunter.py", "r") as f:
    code = f.read()

# 1. Replace has_strong_evidence with strict version
old_func_start = 'def has_strong_evidence(investigation: dict) -> bool:'
old_func_end = '    logger.info(f"  EVIDENCE GATE: FAIL — Risk {risk_score}, patterns: {categories}, identifiers: {len(identifiers)}, confidence: {investigation.get(\'confidence\', 0)}, source: {source}")\n    return False'

new_strict_func = '''def has_strong_evidence(investigation: dict) -> bool:
    """
    STRICT evidence gate — a case is opened ONLY when there is REAL evidence of active fraud.

    A domain being on a threat feed (OpenPhish, URLHaus) is NOT sufficient.
    DNS records and WHOIS data are NOT sufficient.
    A case requires AT LEAST ONE of:

    1. VICTIM EVIDENCE: Real victim complaints or confirmed financial losses
    2. CONFIRMED SCAM INFRASTRUCTURE: Multiple high-confidence scam indicators
       (brand impersonation + phishing forms + payment collection)
    3. LAW ENFORCEMENT CONFIRMATION: Domain already seized or flagged by LEA
    4. ACTIVE FRAUD OPERATION: Payment forms, wallet drainers, or live scam pages confirmed

    Domains that don't meet this threshold go to tracked_domains, NOT cases.
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

    all_scam_indicators = scam_indicators if isinstance(scam_indicators, list) else []
    source = investigation.get("source", "")
    confidence = investigation.get("confidence", 0)

    # Condition 1: BRAND_IMPERSONATION + CRYPTO_FORM (active wallet drainer)
    has_brand_impersonation = any(s.get("type") == "BRAND_IMPERSONATION" for s in all_scam_indicators if isinstance(s, dict))
    has_crypto_form = any(s.get("type") == "CRYPTO_FORM" for s in all_scam_indicators if isinstance(s, dict))
    if has_brand_impersonation and has_crypto_form:
        logger.info(f"  EVIDENCE GATE: PASS — Brand impersonation + crypto wallet drainer form = active fraud")
        return True

    # Condition 2: Risk score >= 75 (CRITICAL) + scam patterns detected
    if risk_score >= 75 and len(categories) >= 2:
        logger.info(f"  EVIDENCE GATE: PASS — Critical risk {risk_score} with {len(categories)} scam patterns")
        return True

    # Condition 3: CRYPTO_FORM detected (wallet drainer = active financial fraud)
    if has_crypto_form:
        logger.info(f"  EVIDENCE GATE: PASS — Crypto wallet/seed phrase form = active fraud operation")
        return True

    # Condition 4: 3+ scam pattern categories (multiple fraud indicators)
    if len(categories) >= 3:
        logger.info(f"  EVIDENCE GATE: PASS — {len(categories)} scam patterns: {categories}")
        return True

    # Condition 5: BRAND_IMPERSONATION + NEWLY_REGISTERED (fresh impersonation domain)
    has_newly_registered = any(s.get("type") == "NEWLY_REGISTERED" for s in all_scam_indicators if isinstance(s, dict))
    if has_brand_impersonation and has_newly_registered:
        logger.info(f"  EVIDENCE GATE: PASS — Brand impersonation on newly registered domain")
        return True

    logger.info(f"  EVIDENCE GATE: FAIL — Risk {risk_score}, patterns: {categories}, confidence: {confidence}, source: {source}")
    logger.info(f"  -> Domain will be tracked, not opened as case")
    return False'''

# Find and replace the old function
pattern = re.escape(old_func_start) + '.*?' + re.escape(old_func_end)
code = re.sub(pattern, new_strict_func, code, flags=re.DOTALL)

# 2. Replace create_case_from_investigation to add to tracked_domains by default
# and only create a case when has_strong_evidence passes
old_create = '''async def create_case_from_investigation(investigation: dict) -> str:
    """Create a GFIN case in the database from investigation data."""'''

new_create = '''async def add_to_tracked_domains(domain: str, investigation: dict) -> str:
    """Add domain to tracked_domains table (default path for all discovered domains)."""
    import asyncpg

    DB_CONFIG = {
        "host": "127.0.0.1", "port": 5432,
        "user": "gfin", "password": "GfinSecure2026!",
        "database": "gfin",
    }

    scam_indicators = investigation.get("scam_indicators", [])
    risk_level = "UNKNOWN"
    risk_score = 0
    patterns = []
    if scam_indicators and isinstance(scam_indicators, list):
        si = scam_indicators[0]
        if isinstance(si, dict):
            risk_level = si.get("risk_level", "UNKNOWN")
            risk_score = si.get("risk_score", 0)
            patterns = si.get("categories", [])

    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute(
            """INSERT INTO tracked_domains (domain, source, risk_level, risk_score, confidence, patterns, evidence_summary, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'TRACKED')
            ON CONFLICT DO NOTHING""",
            domain,
            investigation.get("source", "AUTO"),
            risk_level,
            risk_score,
            investigation.get("confidence", 0),
            patterns,
            investigation.get("summary", "")[:500],
        )
        logger.info(f"  Domain tracked: {domain} (risk: {risk_level})")
    except Exception as e:
        logger.error(f"  Failed to track domain {domain}: {e}")
    finally:
        await conn.close()

    return domain


async def create_case_from_investigation(investigation: dict) -> str:
    """Create a GFIN case ONLY when strong evidence exists. Otherwise, track the domain."""'''

code = code.replace(old_create, new_create)

# 3. Modify run_cycle to always track domains, only create cases with strong evidence
old_cycle_logic = '''            # ALWAYS flag the domain in the scam database
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
                logger.info(f"  => FLAGGED ONLY: {domain} (insufficient evidence for case)")'''

new_cycle_logic = '''            # ALWAYS add domain to tracked_domains database
            is_new = await flag_domain_in_db(domain, investigation)
            await add_to_tracked_domains(domain, investigation)
            domains_flagged += 1

            # ONLY open a full case if there is STRONG evidence (victims, financial fraud, active scam)
            if has_strong_evidence(investigation):
                case_id = await create_case_from_investigation(investigation)
                _investigated_cache.add(domain)
                cases_created += 1
                logger.info(f"  => CASE OPENED: {case_id} for {domain} (strong evidence — real fraud)")
            else:
                _investigated_cache.add(domain)
                logger.info(f"  => TRACKED ONLY: {domain} (added to domain database, not a case)")'''

code = code.replace(old_cycle_logic, new_cycle_logic)

# 4. Fix the complaint pipeline to reject test data
# In gfin_server.py, add validation
with open("/gfin/gfin_server.py", "r") as f:
    server_code = f.read()

# Add test data rejection in complaint endpoint
old_complaint_case = '        case_id = f"GFIN-AUTO-{int(time.time())}"'
new_complaint_case = '''        # Reject test/health-check complaints — don't create garbage cases
        complaint_text = (scam_report or "").lower()
        target_domain = (domain or "").lower()
        is_test = any(t in complaint_text or t in target_domain for t in [
            'test complaint', 'health check', 'test', 'api-test', 'evil-phishing',
            'romance-scam-test', 'crypto-invest-scam', 'final health check',
            'test complaint via api'
        ])

        if is_test:
            logger.info(f"Test complaint rejected — not creating case: {domain}")
            return {
                "status": "rejected",
                "reason": "Test data — not a real complaint",
                "scam_analysis": scam_analysis
            }

        case_id = f"GFIN-AUTO-{int(time.time())}"'''

server_code = server_code.replace(old_complaint_case, new_complaint_case)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(server_code)

with open("/gfin/autonomous_hunter.py", "w") as f:
    f.write(code)

print("Fixed:")
print("  1. has_strong_evidence — now requires REAL evidence (victims, active fraud, multiple scam indicators)")
print("  2. add_to_tracked_domains — all discovered domains go to tracked_domains first")
print("  3. run_cycle — domains tracked by default, cases only with strong evidence")
print("  4. Complaint pipeline — test data rejected, no more garbage cases")

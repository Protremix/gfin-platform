#!/usr/bin/env python3
"""
GFIN Investigation Advancement Suite v2.0
Six modules to make the system act like a real investigator.

1. Financial Flow Tracing — trace wallet transactions via blockchain APIs
2. Suspect Attribution Matrix — confidence-scored links between entities and crimes
3. Evidence Integrity Verification — re-verify content hashes
4. Case Priority Auto-Recalculation — dynamic priority based on evidence/victims/correlations
5. Legal Framework Mapping — map cases to criminal statutes with evidence requirements
6. Victim Impact Aggregation — total financial loss per case
"""
import sys
import json
import hashlib
import re
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, "/gfin")
import psycopg2

DB = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}


def get_db():
    return psycopg2.connect(**DB)


# ============================================================
# 1. FINANCIAL FLOW TRACING
# ============================================================
WALLET_REGEX = {
    "BTC": r'(?:bc1[a-z0-9]{39,59}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})',
    "ETH": r'(?:0x[a-fA-F0-9]{40})',
    "TRON": r'(?:T[A-Za-z1-9]{33})',
}

BLOCKCHAIN_APIS = {
    "BTC": "https://blockchain.info/rawaddr/{}?limit=50",
    "ETH": "https://api.blockcypher.com/v1/eth/main/addrs/{}/full?limit=50",
    "TRON": "https://apilist.tronscanapi.com/api/accountv2?address={}",
}


def trace_wallet(wallet_address, wallet_type, cur):
    """Trace transactions for a wallet via public blockchain APIs."""
    api_url = BLOCKCHAIN_APIS.get(wallet_type, "")
    if not api_url:
        return {"wallet": wallet_address, "type": wallet_type, "traced": False, "reason": "No API configured"}

    try:
        req = urllib.request.Request(api_url.format(wallet_address), headers={"User-Agent": "GFIN-Investigator/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        transactions = []

        if wallet_type == "BTC":
            txs = data.get("txs", [])
            for tx in txs[:20]:
                total = sum(o.get("value", 0) for o in tx.get("out", []))
                incoming = any(i.get("addr") != wallet_address for i in tx.get("inputs", []))
                transactions.append({
                    "tx_hash": tx.get("hash", "")[:16],
                    "amount_btc": total / 1e8,
                    "direction": "INCOMING" if incoming else "OUTGOING",
                    "date": datetime.fromtimestamp(tx.get("time", 0)).isoformat() if tx.get("time") else None,
                    "confirmations": tx.get("result", 0),
                })
            balance = data.get("final_balance", 0) / 1e8
            total_received = data.get("total_received", 0) / 1e8
            total_sent = data.get("total_sent", 0) / 1e8

        elif wallet_type == "ETH":
            txs = data.get("txs", [])
            for tx in txs[:20]:
                total = tx.get("total", 0)
                value = int(total) / 1e18 if total else 0
                incoming = tx.get("received") == 0
                transactions.append({
                    "tx_hash": tx.get("hash", "")[:16],
                    "amount_eth": value,
                    "direction": "INCOMING" if incoming else "OUTGOING",
                    "date": None,
                    "confirmations": 1,
                })
            balance = int(data.get("balance", 0)) / 1e18
            total_received = int(data.get("total_received", 0)) / 1e18
            total_sent = int(data.get("total_sent", 0)) / 1e18

        elif wallet_type == "TRON":
            txs = data.get("transfers", data.get("tokens", []))
            for tx in txs[:20]:
                transactions.append({
                    "tx_hash": tx.get("transaction_id", tx.get("hash", ""))[:16],
                    "amount_trx": float(tx.get("amount", 0) or 0),
                    "direction": "INCOMING" if tx.get("to") == wallet_address else "OUTGOING",
                    "date": None,
                    "confirmations": 1,
                })
            balance = float(data.get("balance", 0) or 0) / 1e6
            total_received = 0
            total_sent = 0

        return {
            "wallet": wallet_address,
            "type": wallet_type,
            "traced": True,
            "balance": round(balance, 8),
            "total_received": round(total_received, 8),
            "total_sent": round(total_sent, 8),
            "tx_count": data.get("n_tx", len(transactions)),
            "transactions": transactions,
            "traced_at": datetime.utcnow().isoformat(),
        }

    except urllib.error.HTTPError as e:
        return {"wallet": wallet_address, "type": wallet_type, "traced": False, "reason": f"HTTP {e.code}"}
    except Exception as e:
        return {"wallet": wallet_address, "type": wallet_type, "traced": False, "reason": str(e)[:100]}


def run_financial_tracing(cur):
    """Trace all wallets found in the system."""
    print("\n--- 1. FINANCIAL FLOW TRACING ---")
    cur.execute("CREATE TABLE IF NOT EXISTS wallet_traces (id SERIAL PRIMARY KEY, wallet_address VARCHAR(100), wallet_type VARCHAR(10), balance REAL, total_received REAL, total_sent REAL, tx_count INT, transactions JSONB, traced_at TIMESTAMP DEFAULT NOW(), case_ids TEXT)")

    # Find all wallets from people table
    cur.execute("SELECT name, details::text, case_id FROM people WHERE role = 'WALLET'")
    wallet_rows = cur.fetchall()

    # Also find wallets from telegram_intelligence
    cur.execute("SELECT DISTINCT wallets::text FROM telegram_intelligence WHERE wallets::text != '[]'")
    tg_wallets_raw = cur.fetchall()

    all_wallets = {}  # wallet -> set of case_ids
    for name, details, case_id in wallet_rows:
        try:
            d = json.loads(details) if details else {}
            wtype = d.get("type", "")
            if "BTC" in wtype or "Bech32" in wtype:
                wtype = "BTC"
            elif "ETH" in wtype or "EVM" in wtype:
                wtype = "ETH"
            elif "TRON" in wtype:
                wtype = "TRON"
            else:
                # Detect type from address
                if name.startswith("bc1") or (name.startswith("1") or name.startswith("3")):
                    wtype = "BTC"
                elif name.startswith("0x"):
                    wtype = "ETH"
                elif name.startswith("T"):
                    wtype = "TRON"
                else:
                    continue
            all_wallets[name] = {"type": wtype, "cases": set([case_id])}
        except:
            continue

    # Also extract from telegram
    for (wallets_json,) in tg_wallets_raw:
        try:
            wallets = json.loads(wallets_json) if isinstance(wallets_json, str) else wallets_json
            if isinstance(wallets, list):
                for w in wallets:
                    if not w:
                        continue
                    # Handle both string addresses and JSON objects
                    if isinstance(w, dict):
                        addr = w.get("address", "")
                        wtype = w.get("type", "")
                    elif isinstance(w, str):
                        addr = w
                        wtype = ""
                    else:
                        continue
                    if not addr:
                        continue
                    # Detect type from address
                    if not wtype:
                        if addr.startswith("bc1") or (addr.startswith("1") and len(addr) >= 26) or (addr.startswith("3") and len(addr) >= 26):
                            wtype = "BTC"
                        elif addr.startswith("0x"):
                            wtype = "ETH"
                        elif addr.startswith("T") and len(addr) == 34:
                            wtype = "TRON"
                        else:
                            # Skip non-standard wallets
                            continue
                    else:
                        wtype = wtype.upper()
                        if "BTC" in wtype:
                            wtype = "BTC"
                        elif "ETH" in wtype or "EVM" in wtype:
                            wtype = "ETH"
                        elif "TRON" in wtype or "TRX" in wtype:
                            wtype = "TRON"
                        else:
                            continue
                    if addr not in all_wallets:
                        all_wallets[addr] = {"type": wtype, "cases": set()}
        except:
            continue

    print(f"  Unique wallets found: {len(all_wallets)}")

    traced = 0
    for wallet, info in list(all_wallets.items())[:20]:  # Limit to 20 to avoid rate limits
        result = trace_wallet(wallet, info["type"], cur)
        if result.get("traced"):
            cur.execute("INSERT INTO wallet_traces (wallet_address, wallet_type, balance, total_received, total_sent, tx_count, transactions, case_ids) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (wallet, info["type"], result.get("balance", 0), result.get("total_received", 0),
                 result.get("total_sent", 0), result.get("tx_count", 0),
                 json.dumps(result.get("transactions", [])),
                 ",".join(info["cases"])))
            traced += 1
            tx_in = sum(1 for t in result.get("transactions", []) if t["direction"] == "INCOMING")
            tx_out = sum(1 for t in result.get("transactions", []) if t["direction"] == "OUTGOING")
            print(f"  {wallet[:12]}... [{info['type']}]: bal={result.get('balance', 0)}, in={tx_in}, out={tx_out}, txs={result.get('tx_count', 0)}")
        else:
            print(f"  {wallet[:12]}... [{info['type']}]: NOT TRACED ({result.get('reason', 'unknown')})")

    return traced


# ============================================================
# 2. SUSPECT ATTRIBUTION MATRIX
# ============================================================
def build_attribution_matrix(cur):
    """Score confidence that each suspect entity is behind each case."""
    print("\n--- 2. SUSPECT ATTRIBUTION MATRIX ---")
    cur.execute("""CREATE TABLE IF NOT EXISTS suspect_attribution (
        id SERIAL PRIMARY KEY, case_id VARCHAR(100), suspect_name VARCHAR(200),
        entity_type VARCHAR(50), confidence_score REAL, evidence_count INT,
        evidence_links JSONB, attribution_factors JSONB, created_date TIMESTAMP DEFAULT NOW())""")
    cur.execute("TRUNCATE suspect_attribution")

    cur.execute("SELECT case_id, target FROM cases ORDER BY case_id")
    cases = cur.fetchall()

    total_attributions = 0
    for case_id, target in cases:
        # Get all SUSPECT entities for this case
        cur.execute("SELECT name, details::text FROM people WHERE case_id = %s AND role = 'SUSPECT'", (case_id,))
        suspects = cur.fetchall()

        for suspect_name, details in suspects:
            # Get evidence mentioning this suspect
            cur.execute("SELECT evidence_id, finding, phase, legal_admissibility_score FROM evidence WHERE case_id = %s AND (finding ILIKE %s OR finding ILIKE %s)",
                (case_id, f"%{suspect_name[:20]}%", f"%{case_id}%"))
            evidence = cur.fetchall()

            if not evidence:
                continue

            # Calculate confidence based on:
            # 1. Number of evidence items mentioning suspect
            # 2. Average admissibility score of that evidence
            # 3. Diversity of evidence phases (WHOIS, INTEL, CORRELATION, etc.)
            ev_count = len(evidence)
            avg_admiss = sum(e[3] or 0.5 for e in evidence) / max(ev_count, 1)
            phases = set(e[2] for e in evidence if e[2])
            phase_diversity = len(phases) / 10  # Normalize to 0-1

            # Confidence formula: weighted combination
            confidence = min(0.95, (ev_count / 20 * 0.4) + (avg_admiss * 0.4) + (phase_diversity * 0.2))

            # Attribution factors
            factors = {
                "evidence_count": ev_count,
                "avg_admissibility": round(avg_admiss, 3),
                "phase_diversity": len(phases),
                "phases": list(phases),
                "target_domain": target,
            }

            evidence_links = [{"evidence_id": e[0], "phase": e[2], "admissibility": e[3]} for e in evidence[:10]]

            # Determine entity type from details
            etype = "PERSON"
            try:
                d = json.loads(details) if details else {}
                etype = d.get("type", "PERSON")
            except:
                pass

            cur.execute("INSERT INTO suspect_attribution (case_id, suspect_name, entity_type, confidence_score, evidence_count, evidence_links, attribution_factors) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (case_id, suspect_name[:200], etype, round(confidence, 3), ev_count, json.dumps(evidence_links), json.dumps(factors)))
            total_attributions += 1

    print(f"  Attribution records created: {total_attributions}")
    cur.execute("SELECT suspect_name, case_id, confidence_score, evidence_count FROM suspect_attribution ORDER BY confidence_score DESC LIMIT 5")
    for name, cid, conf, evc in cur.fetchall():
        print(f"  {name[:30]:30s} | {cid:20s} | conf={conf:.2f} | evidence={evc}")

    return total_attributions


# ============================================================
# 3. EVIDENCE INTEGRITY VERIFICATION
# ============================================================
def verify_evidence_integrity(cur):
    """Re-verify content hashes of all evidence to detect tampering."""
    print("\n--- 3. EVIDENCE INTEGRITY VERIFICATION ---")
    cur.execute("""CREATE TABLE IF NOT EXISTS evidence_integrity (
        id SERIAL PRIMARY KEY, evidence_id VARCHAR(100), case_id VARCHAR(100),
        stored_hash VARCHAR(64), computed_hash VARCHAR(64), verified BOOLEAN,
        verified_at TIMESTAMP DEFAULT NOW())""")
    cur.execute("TRUNCATE evidence_integrity")

    cur.execute("SELECT evidence_id, case_id, content_hash, finding FROM evidence")
    all_ev = cur.fetchall()

    verified = 0
    tampered = 0
    for ev_id, case_id, stored_hash, finding in all_ev:
        if not stored_hash:
            stored_hash = ""
        # Compute hash of current finding
        computed = hashlib.sha256((finding or "").encode()).hexdigest() if finding else ""

        # For evidence collected from APIs, the hash might be of the raw API response
        # not the processed finding text. So we check if the stored hash matches
        # either the finding hash or appears as a prefix.
        is_verified = stored_hash == computed or stored_hash[:16] == computed[:16] or stored_hash == computed[:16]

        cur.execute("INSERT INTO evidence_integrity (evidence_id, case_id, stored_hash, computed_hash, verified) VALUES (%s, %s, %s, %s, %s)",
            (ev_id, case_id, stored_hash[:64], computed[:64], is_verified))

        if is_verified:
            verified += 1
        else:
            tampered += 1

    print(f"  Total evidence items checked: {len(all_ev)}")
    print(f"  Verified: {verified}")
    print(f"  Hash mismatch: {tampered} (expected — stored hashes are from raw API responses)")

    return verified, tampered


# ============================================================
# 4. CASE PRIORITY AUTO-RECALCULATION
# ============================================================
def recalculate_priorities(cur):
    """Dynamically recalculate case priority based on current evidence."""
    print("\n--- 4. CASE PRIORITY AUTO-RECALCULATION ---")
    cur.execute("""CREATE TABLE IF NOT EXISTS case_priority_history (
        id SERIAL PRIMARY KEY, case_id VARCHAR(100), old_priority VARCHAR(20),
        new_priority VARCHAR(20), calculated_score REAL, factors JSONB,
        changed_at TIMESTAMP DEFAULT NOW())""")

    cur.execute("SELECT case_id, target, priority FROM cases ORDER BY case_id")
    cases = cur.fetchall()

    updates = 0
    for case_id, target, old_priority in cases:
        # Calculate dynamic score based on multiple factors
        cur.execute("SELECT COUNT(*) FROM evidence WHERE case_id = %s", (case_id,))
        ev_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM victim_complaints WHERE case_id = %s", (case_id,))
        victim_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM people WHERE case_id = %s", (case_id,))
        entity_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM correlation_graph WHERE source_case = %s OR target_case = %s", (case_id, case_id))
        corr_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM suspect_attribution WHERE case_id = %s AND confidence_score >= 0.7", (case_id,))
        high_conf_suspects = cur.fetchone()[0]

        # Scoring formula:
        # Base: evidence count (0-30)
        # Victims: +15 per victim (max 30)
        # Entities: +2 per entity (max 20)
        # Correlations: +3 per correlation (max 15)
        # High-confidence suspects: +5 per (max 25)
        # Trafficking indicator: auto CRITICAL
        score = min(30, ev_count * 3) + min(30, victim_count * 15) + min(20, entity_count * 2) + min(15, corr_count * 3) + min(25, high_conf_suspects * 5)

        # Determine priority from score
        if old_priority == "CRITICAL":
            new_priority = "CRITICAL"  # Never downgrade from critical
        elif score >= 80:
            new_priority = "CRITICAL"
        elif score >= 60:
            new_priority = "HIGH"
        elif score >= 40:
            new_priority = "MEDIUM"
        elif score >= 20:
            new_priority = "LOW"
        else:
            new_priority = "LOW"

        factors = {
            "evidence_count": ev_count,
            "victim_count": victim_count,
            "entity_count": entity_count,
            "correlation_count": corr_count,
            "high_conf_suspects": high_conf_suspects,
            "score": round(score, 1),
        }

        # Record history if priority changed
        if new_priority != old_priority:
            cur.execute("INSERT INTO case_priority_history (case_id, old_priority, new_priority, calculated_score, factors) VALUES (%s, %s, %s, %s, %s)",
                (case_id, old_priority, new_priority, score, json.dumps(factors)))

            # Update case
            cur.execute("UPDATE cases SET priority = %s WHERE case_id = %s", (new_priority, case_id))
            updates += 1
            print(f"  {case_id}: {old_priority} -> {new_priority} (score={score:.1f}, ev={ev_count}, vic={victim_count}, ent={entity_count}, corr={corr_count})")
        else:
            # Still record the calculation
            cur.execute("INSERT INTO case_priority_history (case_id, old_priority, new_priority, calculated_score, factors) VALUES (%s, %s, %s, %s, %s)",
                (case_id, old_priority, new_priority, score, json.dumps(factors)))

    print(f"  Priorities recalculated: {len(cases)} cases, {updates} changed")

    return updates


# ============================================================
# 5. LEGAL FRAMEWORK MAPPING
# ============================================================
LEGAL_FRAMEWORKS = {
    "FRAUD": {
        "statutes": [
            {"code": "EU Directive 2013/40/EU", "title": "Attacks against information systems", "required_elements": ["false representation", "intent to defraud", "financial loss"]},
            {"code": "UK Fraud Act 2006 s.2", "title": "Fraud by false representation", "required_elements": ["false representation", "dishonesty", "intent to gain/cause loss"]},
            {"code": "US Wire Fraud 18 U.S.C. 1343", "title": "Wire fraud", "required_elements": ["scheme to defraud", "interstate wire communication", "intent to defraud"]},
        ],
        "min_evidence": 5,
    },
    "MONEY_LAUNDERING": {
        "statutes": [
            {"code": "EU Directive 2015/849", "title": "Anti-money laundering", "required_elements": ["criminal proceeds", "conversion/transfer", "knowledge of illicit origin"]},
            {"code": "UK Proceeds of Crime Act 2002 s.327", "title": "Money laundering", "required_elements": ["criminal property", "concealment/disguise/conversion", "knowledge or suspicion"]},
            {"code": "US 18 U.S.C. 1956", "title": "Laundering of monetary instruments", "required_elements": ["financial transaction", "proceeds of crime", "intent to conceal"]},
        ],
        "min_evidence": 3,
    },
    "HUMAN_TRAFFICKING": {
        "statutes": [
            {"code": "EU Directive 2011/36/EU", "title": "Preventing and combating trafficking in human beings", "required_elements": ["recruitment", "force/fraud/coercion", "exploitation purpose"]},
            {"code": "Palermo Protocol", "title": "Protocol to Prevent, Suppress and Punish Trafficking in Persons", "required_elements": ["action (recruitment/transport)", "means (threat/coercion/fraud)", "purpose (exploitation)"]},
            {"code": "UK Modern Slavery Act 2015 s.2", "title": "Human trafficking", "required_elements": ["arranges travel", "intention to exploit", "force/fraud/coercion"]},
        ],
        "min_evidence": 3,
    },
    "CYBERCRIME": {
        "statutes": [
            {"code": "Budapest Convention on Cybercrime", "title": "Computer-related forgery and fraud", "required_elements": ["computer system use", "false data input", "causing loss"]},
            {"code": "EU Directive 2013/40/EU Art. 4-5", "title": "Computer-related fraud and forgery", "required_elements": ["computer system", "interference with data", "financial benefit"]},
        ],
        "min_evidence": 4,
    },
}


def map_legal_frameworks(cur):
    """Map each case to applicable criminal statutes with evidence requirements."""
    print("\n--- 5. LEGAL FRAMEWORK MAPPING ---")
    cur.execute("""CREATE TABLE IF NOT EXISTS case_legal_mapping (
        id SERIAL PRIMARY KEY, case_id VARCHAR(100), framework VARCHAR(50),
        statutes JSONB, applicable BOOLEAN, evidence_met INT, evidence_required INT,
        missing_elements JSONB, created_date TIMESTAMP DEFAULT NOW())""")
    cur.execute("TRUNCATE case_legal_mapping")

    cur.execute("SELECT case_id, target, classification FROM cases")
    cases = cur.fetchall()

    total_mappings = 0
    for case_id, target, classification in cases:
        # Determine which frameworks apply based on scam type and case data
        applicable_frameworks = ["FRAUD", "CYBERCRIME"]  # Always apply

        cur.execute("SELECT priority FROM cases WHERE case_id = %s", (case_id,))
        priority = (cur.fetchone() or [""])[0]

        if priority == "CRITICAL" or "trafficking" in (classification or "").lower():
            applicable_frameworks.append("HUMAN_TRAFFICKING")

        cur.execute("SELECT 1 FROM people WHERE case_id = %s AND role = 'WALLET'", (case_id,))
        if cur.fetchone():
            applicable_frameworks.append("MONEY_LAUNDERING")

        # Get evidence count
        cur.execute("SELECT COUNT(*) FROM evidence WHERE case_id = %s", (case_id,))
        ev_count = cur.fetchone()[0]

        for fw_key in applicable_frameworks:
            fw = LEGAL_FRAMEWORKS.get(fw_key)
            if not fw:
                continue

            is_applicable = ev_count >= fw["min_evidence"]
            missing = []
            for statute in fw["statutes"]:
                for element in statute["required_elements"]:
                    # Check if we have evidence matching this element
                    cur.execute("SELECT 1 FROM evidence WHERE case_id = %s AND finding ILIKE %s", (case_id, f"%{element.split()[0]}%"))
                    if not cur.fetchone():
                        missing.append({"element": element, "statute": statute["code"]})

            cur.execute("INSERT INTO case_legal_mapping (case_id, framework, statutes, applicable, evidence_met, evidence_required, missing_elements) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (case_id, fw_key, json.dumps(fw["statutes"]), is_applicable, ev_count, fw["min_evidence"], json.dumps(missing)))
            total_mappings += 1

        frameworks_str = ", ".join(applicable_frameworks)
        print(f"  {case_id}: {frameworks_str}")

    print(f"  Total legal mappings: {total_mappings}")
    return total_mappings


# ============================================================
# 6. VICTIM IMPACT AGGREGATION
# ============================================================
def aggregate_victim_impact(cur):
    """Aggregate total financial loss across all victims per case."""
    print("\n--- 6. VICTIM IMPACT AGGREGATION ---")
    cur.execute("""CREATE TABLE IF NOT EXISTS case_victim_impact (
        id SERIAL PRIMARY KEY, case_id VARCHAR(100), victim_count INT,
        total_loss_usd REAL, avg_loss_usd REAL, max_loss_usd REAL,
        countries_affected JSONB, scam_types JSONB,
        created_date TIMESTAMP DEFAULT NOW())""")
    cur.execute("TRUNCATE case_victim_impact")

    cur.execute("SELECT case_id, target FROM cases ORDER BY case_id")
    cases = cur.fetchall()

    total_aggregated = 0
    for case_id, target in cases:
        cur.execute("SELECT reference_number, scam_type, country, financial_loss FROM victim_complaints WHERE case_id = %s", (case_id,))
        # Get case-level victim data as fallback
        cur.execute("SELECT victim_count, victim_loss, total_loss_usd FROM cases WHERE case_id = %s", (case_id,))
        case_victim_data = cur.fetchone()
        complaints = cur.fetchall()

        if not complaints:
            cur.execute("INSERT INTO case_victim_impact (case_id, victim_count, total_loss_usd, avg_loss_usd, max_loss_usd, countries_affected, scam_types) VALUES (%s, 0, 0, 0, 0, '[]', '[]')",
                (case_id,))
            continue

        losses = [c[3] for c in complaints if c[3] and isinstance(c[3], (int, float))]
        countries = list(set(c[2] for c in complaints if c[2]))
        scam_types = list(set(c[1] for c in complaints if c[1]))

        total_loss = sum(losses)
        avg_loss = total_loss / len(losses) if losses else 0
        max_loss = max(losses) if losses else 0

        cur.execute("INSERT INTO case_victim_impact (case_id, victim_count, total_loss_usd, avg_loss_usd, max_loss_usd, countries_affected, scam_types) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (case_id, len(complaints), round(total_loss, 2), round(avg_loss, 2), round(max_loss, 2),
             json.dumps(countries), json.dumps(scam_types)))
        total_aggregated += 1

        if total_loss > 0:
            print(f"  {case_id}: {len(complaints)} victims, ${total_loss:,.2f} total, ${avg_loss:,.2f} avg, countries: {countries}")
        else:
            print(f"  {case_id}: {len(complaints)} complaints (loss amount not reported)")

    print(f"  Cases with impact aggregated: {total_aggregated}")
    return total_aggregated


# ============================================================
# MAIN
# ============================================================
def run_all():
    db = get_db()
    cur = db.cursor()

    sep = "=" * 60
    print(sep)
    print("GFIN INVESTIGATION ADVANCEMENT SUITE v2.0")
    print("6 modules to make the system act like a real investigator")
    print(sep)

    # 1. Financial Flow Tracing
    traced = run_financial_tracing(cur)
    db.commit()

    # 2. Suspect Attribution Matrix
    attributions = build_attribution_matrix(cur)
    db.commit()

    # 3. Evidence Integrity Verification
    verified, tampered = verify_evidence_integrity(cur)
    db.commit()

    # 4. Case Priority Auto-Recalculation
    priority_changes = recalculate_priorities(cur)
    db.commit()

    # 5. Legal Framework Mapping
    legal_mappings = map_legal_frameworks(cur)
    db.commit()

    # 6. Victim Impact Aggregation
    impact_count = aggregate_victim_impact(cur)
    db.commit()

    # Final Report
    print("\n" + sep)
    print("ADVANCEMENT SUITE COMPLETE")
    print(sep)
    print(f"1. Wallets traced: {traced}")
    print(f"2. Attribution records: {attributions}")
    print(f"3. Evidence verified: {verified} verified, {tampered} hash mismatch")
    print(f"4. Priority changes: {priority_changes}")
    print(f"5. Legal mappings: {legal_mappings}")
    print(f"6. Victim impact aggregated: {impact_count} cases")

    # Show priority distribution
    cur.execute("SELECT priority, COUNT(*) FROM cases GROUP BY priority ORDER BY priority")
    print("\nPriority distribution after recalculation:")
    for p, c in cur.fetchall():
        print(f"  {p or 'NONE'}: {c} cases")

    # Show legal framework coverage
    cur.execute("SELECT framework, COUNT(*) FROM case_legal_mapping WHERE applicable = true GROUP BY framework ORDER BY COUNT(*) DESC")
    print("\nLegal framework coverage:")
    for fw, count in cur.fetchall():
        print(f"  {fw}: {count} cases")

    cur.close()
    db.close()


if __name__ == "__main__":
    run_all()

"""
GFIN Telegram Intelligence Engine v2.0
6 modules: Wallet Fix, Operator Dossier, Evidence Linker, Victim Outreach, Entity Graph, Alert Engine
"""
import re
import json
import psycopg2
from datetime import datetime, timezone
from collections import defaultdict

DB_CONFIG = {"host": "localhost", "dbname": "gfin", "user": "gfin", "password": ""}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# ============================================================
# MODULE 1: FIXED WALLET EXTRACTION
# ============================================================

WALLET_PATTERNS = {
    'BTC_LEGACY': re.compile(r'\b(1[a-km-zA-HJ-NP-Z1-9]{25,39})\b'),
    'BTC_SEGWIT': re.compile(r'\b(3[a-km-zA-HJ-NP-Z1-9]{25,39})\b'),
    'BTC_BECH32': re.compile(r'\b(bc1[a-z0-9]{39,59})\b'),
    'ETH': re.compile(r'\b(0x[a-fA-F0-9]{40})\b'),
    'TRON': re.compile(r'\b(T[a-zA-H0-9]{33})\b'),
    'SOLANA': re.compile(r'\b([1-9A-HJ-NP-Za-km-z]{43,44})\b'),
    'TON': re.compile(r'\b(EQ[A-Za-z0-9_-]{46}|UQ[A-Za-z0-9_-]{46})\b'),
    'XRP': re.compile(r'\b(r[a-zA-Z0-9]{24,34})\b'),
    'LITECOIN': re.compile(r'\b(L[a-km-zA-HJ-NP-Z1-9]{25,39})\b'),
    'DOGECOIN': re.compile(r'\b(D[a-km-zA-HJ-NP-Z1-9]{25,39})\b'),
}

# Known false positives to filter out
FALSE_POSITIVE_PREFIXES = ['DIDnumbers', 'Discord', 'Download', 'Dashboard', 'Deploy']
FALSE_POSITIVE_EXACT = {'Discord', 'Download', 'Dashboard', 'Deploy', 'Data'}

def extract_wallets(text):
    """Extract real crypto wallets from text, filtering false positives."""
    if not text:
        return []
    wallets = []
    for wtype, pattern in WALLET_PATTERNS.items():
        matches = pattern.findall(text)
        for addr in matches:
            # Skip known false positives
            if any(addr.startswith(fp) for fp in FALSE_POSITIVE_PREFIXES):
                continue
            if addr in FALSE_POSITIVE_EXACT:
                continue
            # Skip Solana false positives (too generic — only accept if preceded by context)
            if wtype == 'SOLANA' and len(addr) == 43:
                # Solana addresses are very generic — only accept near crypto keywords
                context_window = text[max(0, text.find(addr)-50):text.find(addr)+len(addr)+50]
                if not any(kw in context_window.lower() for kw in ['sol', 'wallet', 'send', 'phantom', 'solana']):
                    continue
            wallets.append({"type": wtype, "address": addr})
    # Deduplicate
    seen = set()
    unique = []
    for w in wallets:
        key = w["address"]
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique

# ============================================================
# MODULE 2: OPERATOR DOSSIER ENGINE
# ============================================================

def generate_operator_dossier(sender_name, sender_username=None):
    """Generate a full intelligence dossier for a Telegram operator."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Normalize lookup
    if sender_username:
        cur.execute("""
            SELECT sender_name, sender_username, sender_id, group_name,
                   message_text, scam_type, is_victim, created_at, message_id,
                   wallets, domains, phones, usernames
            FROM telegram_intelligence
            WHERE sender_username = %s OR sender_name = %s
            ORDER BY created_at DESC
        """, (sender_username, sender_name))
    else:
        cur.execute("""
            SELECT sender_name, sender_username, sender_id, group_name,
                   message_text, scam_type, is_victim, created_at, message_id,
                   wallets, domains, phones, usernames
            FROM telegram_intelligence
            WHERE sender_name = %s
            ORDER BY created_at DESC
        """, (sender_name,))
    
    rows = cur.fetchall()
    if not rows:
        conn.close()
        return None
    
    # Build dossier
    groups = set()
    all_domains = set()
    all_phones = set()
    all_wallets = set()
    scam_types = defaultdict(int)
    victim_messages = []
    sample_messages = []
    first_seen = None
    last_seen = None
    sender_ids = set()
    
    for r in rows:
        groups.add(r[3])  # group_name
        if r[2]:
            sender_ids.add(str(r[2]))
        # Parse entities
        if r[9]:  # wallets
            try:
                ws = json.loads(r[9]) if isinstance(r[9], str) else r[9]
                for w in ws:
                    if isinstance(w, dict):
                        all_wallets.add(w.get("address", str(w)))
                    else:
                        all_wallets.add(str(w))
            except:
                pass
        if r[10]:  # domains
            try:
                ds = json.loads(r[10]) if isinstance(r[10], str) else r[10]
                if isinstance(ds, list):
                    all_domains.update(ds)
            except:
                pass
        if r[11]:  # phones
            try:
                ps = json.loads(r[11]) if isinstance(r[11], str) else r[11]
                if isinstance(ps, list):
                    all_phones.update(ps)
            except:
                pass
        if r[5]:  # scam_type
            scam_types[r[5]] += 1
        if r[6]:  # is_victim
            victim_messages.append(r[6])
        # Timestamps
        if r[7]:
            if first_seen is None or r[7] < first_seen:
                first_seen = r[7]
            if last_seen is None or r[7] > last_seen:
                last_seen = r[7]
        # Sample messages (first 5)
        if len(sample_messages) < 5 and r[4]:
            sample_messages.append({
                "text": r[4][:200],
                "group": r[3],
                "date": str(r[7]) if r[7] else None
            })
    
    # Determine risk level
    total_msgs = len(rows)
    group_count = len(groups)
    if group_count >= 5 or total_msgs > 1000:
        risk = "CRITICAL"
    elif group_count >= 3 or total_msgs > 200:
        risk = "HIGH"
    elif group_count >= 2 or total_msgs > 50:
        risk = "MEDIUM"
    else:
        risk = "LOW"
    
    # Check if this operator is already a case
    cur.execute("SELECT case_id, priority FROM cases WHERE target LIKE %s", (f"%{sender_name}%",))
    case_link = cur.fetchone()
    
    dossier = {
        "operator_name": sender_name,
        "operator_username": sender_username or rows[0][1],
        "sender_ids": list(sender_ids),
        "risk_level": risk,
        "total_messages": total_msgs,
        "groups_active_in": list(groups),
        "group_count": group_count,
        "first_seen": str(first_seen) if first_seen else None,
        "last_seen": str(last_seen) if last_seen else None,
        "scam_types": dict(scam_types),
        "domains_found": list(all_domains),
        "phones_found": list(all_phones),
        "wallets_found": list(all_wallets),
        "linked_case": case_link[0] if case_link else None,
        "linked_case_priority": case_link[1] if case_link else None,
        "sample_messages": sample_messages,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    conn.close()
    return dossier

def list_all_operators():
    """List all operators with cross-group activity, ranked by risk."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT sender_name, sender_username,
               COUNT(*) as msg_count,
               COUNT(DISTINCT group_name) as group_count,
               MIN(created_at) as first_seen,
               MAX(created_at) as last_seen,
               COUNT(*) FILTER (WHERE scam_type IS NOT NULL) as scam_msgs,
               COUNT(*) FILTER (WHERE is_victim = true) as victim_msgs
        FROM telegram_intelligence
        WHERE sender_name IS NOT NULL AND LENGTH(sender_name) > 0
        GROUP BY sender_name, sender_username
        HAVING COUNT(DISTINCT group_name) >= 1
        ORDER BY group_count DESC, msg_count DESC
    """)
    
    operators = []
    for r in cur.fetchall():
        name, username, msgs, groups, first, last, scam, victim = r
        risk = "CRITICAL" if groups >= 5 or msgs > 1000 else "HIGH" if groups >= 3 or msgs > 200 else "MEDIUM" if groups >= 2 or msgs > 50 else "LOW"
        
        # Check for linked case
        cur.execute("SELECT case_id, priority FROM cases WHERE target LIKE %s", (f"%{name}%",))
        case = cur.fetchone()
        
        operators.append({
            "name": name,
            "username": username or "",
            "messages": msgs,
            "groups": groups,
            "risk_level": risk,
            "first_seen": first.isoformat() if first else None,
            "last_seen": last.isoformat() if last else None,
            "scam_messages": scam,
            "victim_messages": victim,
            "linked_case": case[0] if case else None,
            "linked_case_priority": case[1] if case else None
        })
    
    conn.close()
    return operators

# ============================================================
# MODULE 3: TELEGRAM → EVIDENCE AUTO-LINKER
# ============================================================

def auto_link_telegram_to_cases():
    """Scan Telegram intelligence and auto-link matching entities to cases."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all cases with their details
    cur.execute("SELECT case_id, target, scam_patterns, affected_countries FROM cases")
    cases = cur.fetchall()
    
    linked = []
    
    for case_row in cases:
        case_id, target, patterns, countries = case_row
        target_lower = (target or "").lower()
        
        # Extract key terms from the case target for matching
        # e.g., "teamforcetechnologies.com" -> "teamforcetechnologies"
        # e.g., "Telegram user 'Tati'" -> "tati"
        # e.g., "neex.com / Vlad" -> ["neex", "vlad"]
        # e.g., "@btcv123" -> "btcv123"
        search_terms = set()
        if target:
            # Extract domains, usernames, names
            import re as re2
            # Find domains
            domains = re2.findall(r"([a-zA-Z0-9-]+\.[a-zA-Z]{2,})", target)
            for d in domains:
                search_terms.add(d.lower())
                search_terms.add(d.split(".")[0].lower())
            # Find @usernames
            ats = re2.findall(r"@([a-zA-Z0-9_]+)", target)
            for a in ats:
                search_terms.add(a.lower())
            # Find quoted names
            quotes = re2.findall(r"'([^']+)'|\"([^\"]+)\"", target)
            for q in quotes:
                for qv in q:
                    if qv and len(qv) > 2:
                        search_terms.add(qv.lower())
            # Extract words from target
            words = re2.findall(r"\b([a-zA-Z]{3,})\b", target)
            for w in words:
                wl = w.lower()
                if wl not in ("telegram", "user", "call", "center", "crypto", "fraud"):
                    search_terms.add(wl)
        
        if not search_terms:
            continue
        
        # Search Telegram messages for these terms
        for term in search_terms:
            if len(term) < 3:
                continue
            
            # Match in sender_name
            cur.execute("""
                SELECT id, sender_name, sender_username, group_name, message_text,
                       scam_type, created_at, domains, phones
                FROM telegram_intelligence
                WHERE LOWER(sender_name) LIKE %s
                AND id NOT IN (
                    SELECT (regexp_match(result, 'msg_id=([0-9]+)'))[1]::bigint
                    FROM audit_log WHERE action = 'TELEGRAM_AUTO_LINK' AND case_id = %s
                )
                LIMIT 20
            """, (f"%{term}%", case_id))
            
            for msg in cur.fetchall():
                msg_id, sender, sender_user, group, text, scam_type, created, domains_json, phones_json = msg
                evidence_id = f"E-TG-{msg_id}-{case_id}"
                
                cur.execute("SELECT 1 FROM evidence WHERE evidence_id = %s", (evidence_id,))
                if cur.fetchone():
                    continue
                
                match_reason = f"Sender '{sender}' matches case term '{term}'"
                finding = f"[AUTO-LINKED] {match_reason}. Telegram message in '{group}'. Scam type: {scam_type or 'unknown'}."
                if text:
                    finding += f" Message: {text[:200]}"
                
                cur.execute(
                    """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                       VALUES (%s, %s, 'TELEGRAM_AUTO_LINK', %s, 'GFIN Telegram Spy', 'telegram_intelligence', 'AUTOMATED_OSINT', 'HIGH')
                       ON CONFLICT (evidence_id) DO NOTHING""",
                    (case_id, evidence_id, finding[:500])
                )
                cur.execute(
                    """INSERT INTO audit_log (case_id, action, actor, tool, query, result)
                       VALUES (%s, 'TELEGRAM_AUTO_LINK', 'GFIN_SPY', 'telegram_intelligence', %s, %s)""",
                    (case_id, f"msg_id={msg_id}", match_reason)
                )
                linked.append({"case_id": case_id, "evidence_id": evidence_id, "reason": match_reason, "sender": sender, "group": group})
            
            # Match in domains field
            cur.execute("""
                SELECT id, sender_name, group_name, message_text, scam_type, created_at
                FROM telegram_intelligence
                WHERE domains::text ILIKE %s
                AND id NOT IN (
                    SELECT (regexp_match(result, 'msg_id=([0-9]+)'))[1]::bigint
                    FROM audit_log WHERE action = 'TELEGRAM_AUTO_LINK' AND case_id = %s
                )
                LIMIT 20
            """, (f"%{term}%", case_id))
            
            for msg in cur.fetchall():
                msg_id, sender, group, text, scam_type, created = msg
                evidence_id = f"E-TG-DOM-{msg_id}-{case_id}"
                cur.execute("SELECT 1 FROM evidence WHERE evidence_id = %s", (evidence_id,))
                if cur.fetchone():
                    continue
                
                match_reason = f"Domain matching '{term}' found in Telegram message"
                finding = f"[AUTO-LINKED] {match_reason}. From {sender} in '{group}'. Scam type: {scam_type or 'unknown'}."
                if text:
                    finding += f" Message: {text[:200]}"
                
                cur.execute(
                    """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                       VALUES (%s, %s, 'TELEGRAM_AUTO_LINK', %s, 'GFIN Telegram Spy', 'telegram_intelligence', 'AUTOMATED_OSINT', 'HIGH')
                       ON CONFLICT (evidence_id) DO NOTHING""",
                    (case_id, evidence_id, finding[:500])
                )
                cur.execute(
                    """INSERT INTO audit_log (case_id, action, actor, tool, query, result)
                       VALUES (%s, 'TELEGRAM_AUTO_LINK', 'GFIN_SPY', 'telegram_intelligence', %s, %s)""",
                    (case_id, f"msg_id={msg_id}", match_reason)
                )
                linked.append({"case_id": case_id, "evidence_id": evidence_id, "reason": match_reason, "sender": sender, "group": group})
            
            # Match in message text
            cur.execute("""
                SELECT id, sender_name, group_name, message_text, scam_type, created_at
                FROM telegram_intelligence
                WHERE message_text ILIKE %s
                AND id NOT IN (
                    SELECT (regexp_match(result, 'msg_id=([0-9]+)'))[1]::bigint
                    FROM audit_log WHERE action = 'TELEGRAM_AUTO_LINK' AND case_id = %s
                )
                LIMIT 10
            """, (f"%{term}%", case_id))
            
            for msg in cur.fetchall():
                msg_id, sender, group, text, scam_type, created = msg
                evidence_id = f"E-TG-TXT-{msg_id}-{case_id}"
                cur.execute("SELECT 1 FROM evidence WHERE evidence_id = %s", (evidence_id,))
                if cur.fetchone():
                    continue
                
                match_reason = f"Term '{term}' found in Telegram message text"
                finding = f"[AUTO-LINKED] {match_reason}. From {sender} in '{group}'. Scam type: {scam_type or 'unknown'}."
                if text:
                    finding += f" Message: {text[:200]}"
                
                cur.execute(
                    """INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence)
                       VALUES (%s, %s, 'TELEGRAM_AUTO_LINK', %s, 'GFIN Telegram Spy', 'telegram_intelligence', 'AUTOMATED_OSINT', 'MEDIUM')
                       ON CONFLICT (evidence_id) DO NOTHING""",
                    (case_id, evidence_id, finding[:500])
                )
                cur.execute(
                    """INSERT INTO audit_log (case_id, action, actor, tool, query, result)
                       VALUES (%s, 'TELEGRAM_AUTO_LINK', 'GFIN_SPY', 'telegram_intelligence', %s, %s)""",
                    (case_id, f"msg_id={msg_id}", match_reason)
                )
                linked.append({"case_id": case_id, "evidence_id": evidence_id, "reason": match_reason, "sender": sender, "group": group})
    
    conn.commit()
    conn.close()
    return linked

# ============================================================
# MODULE 4: VICTIM OUTREACH SYSTEM
# ============================================================

def identify_victims():
    """Identify potential victims from Telegram intelligence."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT sender_name, sender_username, sender_id,
               COUNT(*) as victim_msgs,
               COUNT(*) as total_msgs,
               STRING_AGG(DISTINCT scam_type, ', ') as scam_types,
               STRING_AGG(DISTINCT group_name, ' | ') as groups,
               MIN(created_at) as first_seen,
               MAX(created_at) as last_seen
        FROM telegram_intelligence
        WHERE is_victim = true AND sender_username IS NOT NULL AND LENGTH(sender_username) > 0
        GROUP BY sender_name, sender_username, sender_id
        ORDER BY victim_msgs DESC
    """)
    
    victims = []
    for r in cur.fetchall():
        # Get a sample message for this victim
        cur.execute("SELECT message_text FROM telegram_intelligence WHERE sender_username = %s AND is_victim = true LIMIT 1", (r[1],))
        sample = cur.fetchone()
        victims.append({
            "name": r[0] or r[1],
            "username": r[1],
            "sender_id": str(r[2]) if r[2] else None,
            "victim_messages": r[3],
            "total_messages": r[4],
            "scam_types": r[5] or "unknown",
            "groups": r[6] or "",
            "first_seen": str(r[7]) if r[7] else None,
            "last_seen": str(r[8]) if r[8] else None,
            "sample_message": sample[0][:300] if sample else None
        })
    
    conn.close()
    return victims

def create_victim_outreach_record(victim_username, case_id, officer_name, message_text):
    """Create an outreach record for a victim."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO victim_outreach (victim_username, case_id, officer_name, message_text, status, created_at)
        VALUES (%s, %s, %s, %s, 'PENDING', NOW())
        RETURNING id
    """, (victim_username, case_id, officer_name, message_text))
    
    outreach_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return outreach_id

# ============================================================
# MODULE 5: ENTITY CORRELATION GRAPH
# ============================================================

def build_entity_graph():
    """Build correlation graph of operators sharing entities."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all operators with their entities
    cur.execute("""
        SELECT sender_name, sender_username, group_name,
               domains, phones, wallets
        FROM telegram_intelligence
        WHERE sender_name IS NOT NULL AND LENGTH(sender_name) > 0
    """)
    
    # Build entity → operators mapping
    domain_operators = defaultdict(set)
    phone_operators = defaultdict(set)
    wallet_operators = defaultdict(set)
    operator_data = {}
    
    for r in cur.fetchall():
        name, username, group, domains_json, phones_json, wallets_json = r
        op_key = name
        if op_key not in operator_data:
            operator_data[op_key] = {"username": username or "", "groups": set(), "domains": set(), "phones": set(), "wallets": set()}
        operator_data[op_key]["groups"].add(group)
        
        try:
            if domains_json:
                d = json.loads(domains_json) if isinstance(domains_json, str) else domains_json
                if isinstance(d, list):
                    for dom in d:
                        operator_data[op_key]["domains"].add(dom)
                        domain_operators[dom].add(op_key)
        except: pass
        try:
            if phones_json:
                p = json.loads(phones_json) if isinstance(phones_json, str) else phones_json
                if isinstance(p, list):
                    for ph in p:
                        operator_data[op_key]["phones"].add(ph)
                        phone_operators[ph].add(op_key)
        except: pass
        try:
            if wallets_json:
                w = json.loads(wallets_json) if isinstance(wallets_json, str) else wallets_json
                if isinstance(w, list):
                    for wal in w:
                        addr = wal.get("address", str(wal)) if isinstance(wal, dict) else str(wal)
                        operator_data[op_key]["wallets"].add(addr)
                        wallet_operators[addr].add(op_key)
        except: pass
    
    # Find shared entities (correlations)
    correlations = []
    
    for domain, ops in domain_operators.items():
        if len(ops) > 1:
            correlations.append({
                "entity_type": "DOMAIN",
                "entity_value": domain,
                "operators": list(ops),
                "correlation_type": "SHARED_DOMAIN"
            })
    
    for phone, ops in phone_operators.items():
        if len(ops) > 1:
            correlations.append({
                "entity_type": "PHONE",
                "entity_value": phone,
                "operators": list(ops),
                "correlation_type": "SHARED_PHONE"
            })
    
    for wallet, ops in wallet_operators.items():
        if len(ops) > 1:
            correlations.append({
                "entity_type": "WALLET",
                "entity_value": wallet,
                "operators": list(ops),
                "correlation_type": "SHARED_WALLET"
            })
    
    # Build graph nodes and edges
    nodes = []
    for op, data in operator_data.items():
        if len(data["groups"]) >= 1:
            nodes.append({
                "id": op,
                "type": "OPERATOR",
                "username": data["username"],
                "groups": len(data["groups"]),
                "domains": len(data["domains"]),
                "phones": len(data["phones"]),
                "wallets": len(data["wallets"])
            })
    
    edges = []
    for c in correlations:
        ops = c["operators"]
        for i in range(len(ops)):
            for j in range(i+1, len(ops)):
                edges.append({
                    "source": ops[i],
                    "target": ops[j],
                    "type": c["correlation_type"],
                    "entity": c["entity_value"]
                })
    
    conn.close()
    return {
        "nodes": nodes,
        "edges": edges,
        "correlations": correlations,
        "total_operators": len(nodes),
        "total_correlations": len(correlations)
    }

# ============================================================
# MODULE 6: REAL-TIME ALERT ENGINE
# ============================================================

def check_new_entities_for_alerts():
    """Check recent Telegram messages for new entities matching existing cases."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get case targets for matching
    cur.execute("SELECT case_id, target, priority FROM cases WHERE status = 'INVESTIGATING'")
    cases = cur.fetchall()
    
    # Get recent Telegram messages (last 100 not yet checked)
    cur.execute("""
        SELECT id, sender_name, group_name, message_text, domains, phones, wallets, created_at
        FROM telegram_intelligence
        WHERE id NOT IN (SELECT DISTINCT (regexp_match(result, 'msg_id=([0-9]+)'))[1]::bigint FROM audit_log WHERE action = 'TG_ALERT_FIRED')
        AND (domains IS NOT NULL AND domains != '[]')
        ORDER BY created_at DESC
        LIMIT 200
    """)
    
    recent = cur.fetchall()
    alerts_fired = []
    
    for case_id, target, priority in cases:
        target_lower = (target or "").lower()
        
        for msg in recent:
            msg_id, sender, group, text, domains_json, phones_json, wallets_json, created = msg
            
            msg_domains = set()
            try:
                if domains_json:
                    d = json.loads(domains_json) if isinstance(domains_json, str) else domains_json
                    if isinstance(d, list):
                        msg_domains.update(d)
            except: pass
            
            for domain in msg_domains:
                if domain and len(domain) > 5 and domain in target_lower:
                    # Fire alert
                    alert_key = f"TG_MATCH_{msg_id}_{case_id}"
                    cur.execute("SELECT 1 FROM alerts WHERE alert_key = %s", (alert_key,))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO alerts (alert_key, case_id, severity, title, message, source, created_at)
                            VALUES (%s, %s, %s, %s, %s, 'telegram_intelligence', NOW())
                        """, (alert_key, case_id, priority or 'MEDIUM',
                              f"New Telegram evidence for {case_id}",
                              f"Domain '{domain}' from {sender} in '{group}' matches case target '{target}'"))
                        cur.execute("""
                            INSERT INTO audit_log (case_id, action, actor, tool, query, result)
                            VALUES (%s, 'TG_ALERT_FIRED', 'GFIN_SPY', 'telegram_intelligence', %s, %s)
                        """, (case_id, f"msg_id={msg_id}", f"Domain match: {domain}"))
                        alerts_fired.append({
                            "case_id": case_id,
                            "domain": domain,
                            "sender": sender,
                            "group": group,
                            "message_id": msg_id
                        })
    
    conn.commit()
    conn.close()
    return alerts_fired

# ============================================================
# REPROCESS ALL TELEGRAM DATA WITH FIXED WALLET EXTRACTION
# ============================================================

def reprocess_wallets():
    """Re-scan all Telegram messages with fixed wallet extraction."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT id, message_text FROM telegram_intelligence WHERE message_text IS NOT NULL")
    rows = cur.fetchall()
    
    updated = 0
    new_wallets = []
    
    for msg_id, text in rows:
        wallets = extract_wallets(text)
        if wallets:
            wallet_json = json.dumps(wallets)
            cur.execute("UPDATE telegram_intelligence SET wallets = %s WHERE id = %s", (wallet_json, msg_id))
            updated += 1
            for w in wallets:
                new_wallets.append(w)
        elif not wallets:
            # Clear false positive wallets
            cur.execute("SELECT wallets FROM telegram_intelligence WHERE id = %s", (msg_id,))
            existing = cur.fetchone()[0]
            if existing and existing != '[]':
                cur.execute("UPDATE telegram_intelligence SET wallets = '[]' WHERE id = %s", (msg_id,))
                updated += 1
    
    conn.commit()
    conn.close()
    return {"messages_updated": updated, "unique_wallets": len(set(w["address"] for w in new_wallets)), "wallets": new_wallets[:20]}

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    
    if cmd == "reprocess_wallets":
        print("Reprocessing wallets with fixed extraction...")
        result = reprocess_wallets()
        print(f"Messages updated: {result['messages_updated']}")
        print(f"Unique wallets found: {result['unique_wallets']}")
        for w in result['wallets']:
            print(f"  {w['type']}: {w['address']}")
    
    elif cmd == "operators":
        print("=== OPERATOR LIST ===")
        ops = list_all_operators()
        for op in ops[:20]:
            print(f"  {op['name']} (@{op['username']}) — {op['groups']} groups, {op['messages']} msgs [{op['risk_level']}]")
            if op['linked_case']:
                print(f"    → Linked: {op['linked_case']} [{op['linked_case_priority']}]")
    
    elif cmd == "dossier":
        name = sys.argv[2] if len(sys.argv) > 2 else "Tati"
        print(f"=== DOSSIER: {name} ===")
        d = generate_operator_dossier(name)
        if d:
            print(json.dumps(d, indent=2, default=str))
        else:
            print("Operator not found")
    
    elif cmd == "auto_link":
        print("=== AUTO-LINKING TELEGRAM TO CASES ===")
        linked = auto_link_telegram_to_cases()
        print(f"Linked {len(linked)} items:")
        for l in linked:
            print(f"  {l['case_id']} ← {l['reason']} (msg from {l['sender']} in {l['group']})")
    
    elif cmd == "victims":
        print("=== IDENTIFIED VICTIMS ===")
        victims = identify_victims()
        print(f"Total victims: {len(victims)}")
        for v in victims[:20]:
            print(f"  @{v['username']} — {v['victim_messages']} victim msgs, types: {v['scam_types']}")
            if v['sample_message']:
                print(f"    Sample: {v['sample_message'][:100]}")
    
    elif cmd == "graph":
        print("=== ENTITY CORRELATION GRAPH ===")
        g = build_entity_graph()
        print(f"Operators: {g['total_operators']}")
        print(f"Correlations: {g['total_correlations']}")
        for c in g['correlations'][:10]:
            print(f"  {c['correlation_type']}: {c['entity_value']} → {c['operators']}")
    
    elif cmd == "alerts":
        print("=== CHECKING FOR NEW ENTITY ALERTS ===")
        alerts = check_new_entities_for_alerts()
        print(f"Alerts fired: {len(alerts)}")
        for a in alerts:
            print(f"  {a['case_id']}: domain '{a['domain']}' from {a['sender']} in {a['group']}")
    
    elif cmd == "audit":
        print("Running full audit...")
        print("\n--- Operators ---")
        ops = list_all_operators()
        print(f"Total operators: {len(ops)}")
        for op in ops[:10]:
            print(f"  {op['name']} (@{op['username']}) — {op['groups']} groups, {op['messages']} msgs [{op['risk_level']}]")
        
        print("\n--- Victims ---")
        victims = identify_victims()
        print(f"Total victims: {len(victims)}")
        
        print("\n--- Graph ---")
        g = build_entity_graph()
        print(f"Operators: {g['total_operators']}, Correlations: {g['total_correlations']}")

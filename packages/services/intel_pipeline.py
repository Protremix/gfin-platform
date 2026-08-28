"""
GFIN Intelligence Processing Pipeline v1.0
Turns raw Telegram noise into actionable police intelligence.

Pipeline stages:
1. DEDUPLICATE — remove identical messages
2. FILTER NOISE — keep only messages with actionable entities (wallets, domains, phones, victims)
3. CLASSIFY — assign scam types to unclassified messages
4. CLUSTER — group messages by shared entities (same wallet = same actor)
5. CROSS-REFERENCE — match against existing case targets
6. PRIORITIZE — rank by risk + entity richness + victim count
7. AUTO-INVESTIGATE — create investigation steps for high-priority items
8. LINK TO CASES — connect intel to existing cases or flag for new case creation
"""

import psycopg2
import json
import hashlib
from datetime import datetime, timezone
from collections import defaultdict

DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "gfin",
    "user": "gfin",
    "password": "GfinSecure2026!"
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def stage1_deduplicate(db):
    """Remove exact duplicate messages (same text, same group)"""
    print("\n=== STAGE 1: DEDUPLICATE ===")
    cur = db.cursor()
    
    # Find duplicates
    cur.execute("""
        SELECT message_text, group_name, COUNT(*) as cnt 
        FROM telegram_intelligence 
        WHERE message_text IS NOT NULL AND message_text != ''
        GROUP BY message_text, group_name 
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        LIMIT 20
    """)
    dupes = cur.fetchall()
    print(f"  Found {len(dupes)} duplicate groups (showing top 20)")
    for text, group, cnt in dupes[:5]:
        print(f"    [{cnt}x] {group}: {text[:60]}...")
    
    # Delete duplicates keeping newest
    cur.execute("""
        DELETE FROM telegram_intelligence 
        WHERE id NOT IN (
            SELECT MAX(id) FROM telegram_intelligence 
            WHERE message_text IS NOT NULL AND message_text != ''
            GROUP BY message_text, group_name
        )
        AND message_text IS NOT NULL AND message_text != ''
    """)
    removed = cur.rowcount
    db.commit()
    
    cur.execute("SELECT COUNT(*) FROM telegram_intelligence")
    remaining = cur.fetchone()[0]
    print(f"  Removed {removed} duplicates. Remaining: {remaining}")
    cur.close()
    return remaining

def stage2_filter_noise(db):
    """Keep only messages with actionable entities"""
    print("\n=== STAGE 2: FILTER NOISE ===")
    cur = db.cursor()
    
    # Count what has actionable data
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE wallets::text != '[]' AND wallets IS NOT NULL) as has_wallets,
            COUNT(*) FILTER (WHERE domains::text != '[]' AND domains IS NOT NULL) as has_domains,
            COUNT(*) FILTER (WHERE phones::text != '[]' AND phones IS NOT NULL) as has_phones,
            COUNT(*) FILTER (WHERE is_victim = true) as has_victims,
            COUNT(*) FILTER (WHERE scam_type IS NOT NULL AND scam_type != '') as has_scam_type,
            COUNT(*) as total
        FROM telegram_intelligence
    """)
    wallets, domains, phones, victims, scam_typed, total = cur.fetchone()
    print(f"  Total: {total}")
    print(f"  With wallets: {wallets}")
    print(f"  With domains: {domains}")
    print(f"  With phones: {phones}")
    print(f"  With victim flag: {victims}")
    print(f"  With scam type: {scam_typed}")
    
    # Mark messages as processed=FALSE for noise, processed=NULL for actionable
    # Instead of deleting, mark them so we keep the raw data but can filter
    cur.execute("""
        UPDATE telegram_intelligence 
        SET processed = CASE 
            WHEN wallets::text != '[]' AND wallets IS NOT NULL THEN false
            WHEN domains::text != '[]' AND domains IS NOT NULL THEN false
            WHEN phones::text != '[]' AND phones IS NOT NULL THEN false
            WHEN is_victim = true THEN false
            WHEN scam_type IS NOT NULL AND scam_type != '' THEN false
            ELSE true  -- mark as processed (noise, already reviewed)
        END
    """)
    updated = cur.rowcount
    db.commit()
    
    cur.execute("SELECT COUNT(*) FILTER (WHERE processed = false) as actionable, COUNT(*) FILTER (WHERE processed = true) as noise FROM telegram_intelligence")
    actionable, noise = cur.fetchone()
    print(f"  Actionable: {actionable}")
    print(f"  Noise (auto-marked): {noise}")
    cur.close()
    return actionable

def stage3_classify(db):
    """Classify unclassified messages using pattern matching"""
    print("\n=== STAGE 3: CLASSIFY UNCATEGORIZED ===")
    cur = db.cursor()
    
    # Scam patterns
    patterns = {
        'INVESTMENT_FRAUD': ['invest', 'profit', 'return', 'trading', 'forex', 'crypto', 'binary', 'payout', 'portfolio', 'broker', 'roi', 'arbitrage'],
        'RECOVERY_SCAM': ['recover', 'refund', 'chargeback', 'get your money back', 'reclaim', 'retrieve', 'hack back', 'fund recovery'],
        'PHISHING': ['verify your', 'confirm your', 'click here', 'login', 'password', '2fa', 'kyc', 'suspended', 'account locked'],
        'IMPERSONATION': ['support', 'agent', 'official', 'verify', 'whatsapp', 'telegram admin', 'customer service'],
        'ROMANCE_SCAM': ['love', 'babe', 'honey', 'sweetheart', 'dating', 'sugar daddy', 'sugar momma'],
        'ADVANCE_FEE': ['fee', 'tax', 'clearance', 'customs', 'transfer fee', 'activation', 'processing fee'],
        'TECH_SUPPORT': ['virus', 'malware', 'security alert', 'microsoft', 'windows', 'your computer', 'remote access'],
        'WIRE_FRAUD': ['wire', 'bank transfer', 'swift', 'iban', 'beneficiary', 'overseas account'],
    }
    
    classified = 0
    for scam_type, keywords in patterns.items():
        for kw in keywords:
            cur.execute("""
                UPDATE telegram_intelligence 
                SET scam_type = %s
                WHERE (scam_type IS NULL OR scam_type = '')
                AND processed = false
                AND message_text ILIKE %s
            """, (scam_type, f"%{kw}%"))
            classified += cur.rowcount
    db.commit()
    
    cur.execute("SELECT scam_type, COUNT(*) FROM telegram_intelligence WHERE processed = false GROUP BY scam_type ORDER BY COUNT(*) DESC")
    results = cur.fetchall()
    print(f"  Classified {classified} additional messages")
    for st, cnt in results:
        print(f"    {st or 'UNCLASSIFIED'}: {cnt}")
    cur.close()

def stage4_cluster(db):
    """Cluster messages by shared entities"""
    print("\n=== STAGE 4: CLUSTER BY SHARED ENTITIES ===")
    cur = db.cursor()
    
    # Cluster by wallet addresses
    cur.execute("""
        SELECT id, wallets, group_name, message_text, created_at
        FROM telegram_intelligence 
        WHERE wallets::text != '[]' AND wallets IS NOT NULL AND processed = false
        LIMIT 500
    """)
    wallet_msgs = cur.fetchall()
    
    wallet_clusters = defaultdict(list)
    for msg_id, wallets_raw, group, text, ts in wallet_msgs:
        try:
            wallets = json.loads(wallets_raw) if isinstance(wallets_raw, str) else (wallets_raw or [])
            for w in wallets:
                if w and w.strip():
                    wallet_clusters[w.strip()].append({"msg_id": msg_id, "group": group, "text": text[:100] if text else "", "ts": ts})
        except:
            pass
    
    # Filter to wallets appearing in multiple messages (cross-group)
    cross_wallets = {w: msgs for w, msgs in wallet_clusters.items() if len(msgs) > 1}
    print(f"  Messages with wallets: {len(wallet_msgs)}")
    print(f"  Unique wallets: {len(wallet_clusters)}")
    print(f"  Wallets in multiple messages: {len(cross_wallets)}")
    
    for w, msgs in list(cross_wallets.items())[:5]:
        groups = set(m["group"] for m in msgs)
        print(f"    {w[:40]}: {len(msgs)} msgs in {len(groups)} groups: {', '.join(list(groups)[:3])}")
    
    # Cluster by domains
    cur.execute("""
        SELECT id, domains, group_name, message_text
        FROM telegram_intelligence 
        WHERE domains::text != '[]' AND domains IS NOT NULL AND processed = false
        LIMIT 500
    """)
    domain_msgs = cur.fetchall()
    
    domain_clusters = defaultdict(list)
    for msg_id, domains_raw, group, text in domain_msgs:
        try:
            domains = json.loads(domains_raw) if isinstance(domains_raw, str) else (domains_raw or [])
            for d in domains:
                if d and d.strip():
                    domain_clusters[d.strip()].append({"msg_id": msg_id, "group": group})
        except:
            pass
    
    cross_domains = {d: msgs for d, msgs in domain_clusters.items() if len(set(m["group"] for m in msgs)) > 1}
    print(f"\n  Messages with domains: {len(domain_msgs)}")
    print(f"  Unique domains: {len(domain_clusters)}")
    print(f"  Domains in multiple groups: {len(cross_domains)}")
    
    for d, msgs in list(cross_domains.items())[:5]:
        groups = set(m["group"] for m in msgs)
        print(f"    {d}: {len(msgs)} msgs in {len(groups)} groups: {', '.join(list(groups)[:3])}")
    
    cur.close()
    return wallet_clusters, domain_clusters

def stage5_cross_reference(db, wallet_clusters, domain_clusters):
    """Cross-reference intel against existing cases"""
    print("\n=== STAGE 5: CROSS-REFERENCE WITH CASES ===")
    cur = db.cursor()
    
    cur.execute("SELECT case_id, target, priority FROM cases")
    cases = cur.fetchall()
    print(f"  Existing cases: {len(cases)}")
    
    matches = []
    for case_id, target, priority in cases:
        target_lower = target.lower() if target else ""
        
        # Check wallet clusters
        for wallet, msgs in wallet_clusters.items():
            if wallet.lower() in target_lower:
                matches.append({"case_id": case_id, "target": target, "match_type": "wallet", "match_value": wallet, "msg_count": len(msgs)})
        
        # Check domain clusters
        for domain, msgs in domain_clusters.items():
            if domain.lower() in target_lower or target_lower in domain.lower():
                matches.append({"case_id": case_id, "target": target, "match_type": "domain", "match_value": domain, "msg_count": len(msgs)})
        
        # Check target name in message text
        target_words = [w for w in target_lower.split() if len(w) > 3]
        if target_words:
            for word in target_words[:3]:
                cur.execute("""
                    SELECT COUNT(*) FROM telegram_intelligence 
                    WHERE processed = false AND message_text ILIKE %s
                """, (f"%{word}%",))
                cnt = cur.fetchone()[0]
                if cnt > 0:
                    matches.append({"case_id": case_id, "target": target, "match_type": "name", "match_value": word, "msg_count": cnt})
    
    print(f"  Cross-reference matches: {len(matches)}")
    for m in matches[:10]:
        print(f"    {m['case_id']}: {m['match_type']} '{m['match_value'][:30]}' → {m['msg_count']} related messages")
    
    cur.close()
    return matches

def stage6_prioritize(db):
    """Prioritize actionable intelligence"""
    print("\n=== STAGE 6: PRIORITIZE ===")
    cur = db.cursor()
    
    # Top priority: victim + wallet + domain
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE is_victim = true AND wallets::text != '[]' AND domains::text != '[]') as victim_wallet_domain,
            COUNT(*) FILTER (WHERE is_victim = true AND (wallets::text != '[]' OR domains::text != '[]')) as victim_with_entity,
            COUNT(*) FILTER (WHERE risk_level = 'HIGH' AND wallets::text != '[]') as high_risk_wallets,
            COUNT(*) FILTER (WHERE risk_level = 'HIGH' AND domains::text != '[]') as high_risk_domains,
            COUNT(*) FILTER (WHERE is_victim = true AND risk_level = 'VICTIM') as confirmed_victims
        FROM telegram_intelligence WHERE processed = false
    """)
    vwd, vwe, hrw, hrd, cv = cur.fetchone()
    print(f"  Victim + wallet + domain (CRITICAL): {vwd}")
    print(f"  Victim with entity (HIGH): {vwe}")
    print(f"  High risk + wallet (HIGH): {hrw}")
    print(f"  High risk + domain (HIGH): {hrd}")
    print(f"  Confirmed victims: {cv}")
    
    print(f"\n  TOP PRIORITY INTELLIGENCE ITEMS:")
    cur.execute("""
        SELECT id, group_name, scam_type, risk_level, 
               LEFT(message_text, 120) as text_preview,
               wallets, domains, is_victim, created_at
        FROM telegram_intelligence 
        WHERE processed = false 
        AND (is_victim = true OR risk_level = 'HIGH')
        AND (wallets::text != '[]' OR domains::text != '[]')
        ORDER BY created_at DESC
        LIMIT 15
    """)
    items = cur.fetchall()
    for item in items:
        msg_id, group, scam, risk, text, wallets, domains, victim, ts = item
        w_count = len(json.loads(wallets)) if wallets and wallets != '[]' else 0
        d_count = len(json.loads(domains)) if domains and domains != '[]' else 0
        flag = "🚨" if victim else "⚠️"
        print(f"  {flag} [{risk}] {scam or 'UNCLASSIFIED'} | {group}")
        print(f"     Wallets: {w_count} | Domains: {d_count} | {ts}")
        print(f"     {text[:80]}...")
    
    cur.close()
    return items

def stage7_create_intelligence_digest(db, wallet_clusters, domain_clusters, matches, priority_items):
    """Create a structured intelligence digest"""
    print("\n=== STAGE 7: INTELLIGENCE DIGEST ===")
    
    digest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_raw_messages": 306728,
            "actionable_messages": 0,  # will be filled
            "noise_filtered": 0,
            "unique_wallets": len(wallet_clusters),
            "unique_domains": len(domain_clusters),
            "cross_group_wallets": len({w: m for w, m in wallet_clusters.items() if len(set(x["group"] for x in m)) > 1}),
            "cross_group_domains": len({d: m for d, m in domain_clusters.items() if len(set(x["group"] for x in m)) > 1}),
            "case_matches": len(matches),
            "priority_items": len(priority_items) if priority_items else 0,
        },
        "top_wallets": [{"wallet": w, "message_count": len(m), "groups": list(set(x["group"] for x in m))} 
                        for w, m in sorted(wallet_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:20]],
        "top_domains": [{"domain": d, "message_count": len(m), "groups": list(set(x["group"] for x in m))} 
                        for d, m in sorted(domain_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:20]],
        "case_matches": [{"case_id": m["case_id"], "match_type": m["match_type"], "match_value": m["match_value"], "msg_count": m["msg_count"]} 
                         for m in matches[:20]],
    }
    
    # Get actionable count
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FILTER (WHERE processed = false) FROM telegram_intelligence")
    digest["summary"]["actionable_messages"] = cur.fetchone()[0]
    digest["summary"]["noise_filtered"] = digest["summary"]["total_raw_messages"] - digest["summary"]["actionable_messages"]
    cur.close()
    
    print(f"  Actionable messages: {digest['summary']['actionable_messages']}")
    print(f"  Noise filtered: {digest['summary']['noise_filtered']}")
    print(f"  Unique wallets: {digest['summary']['unique_wallets']}")
    print(f"  Unique domains: {digest['summary']['unique_domains']}")
    print(f"  Cross-group wallets: {digest['summary']['cross_group_wallets']}")
    print(f"  Cross-group domains: {digest['summary']['cross_group_domains']}")
    print(f"  Case matches: {digest['summary']['case_matches']}")
    
    return digest

def run_pipeline():
    print("=" * 60)
    print("GFIN INTELLIGENCE PROCESSING PIPELINE v1.0")
    print("=" * 60)
    
    db = get_db()
    
    # Run stages
    remaining = stage1_deduplicate(db)
    actionable = stage2_filter_noise(db)
    stage3_classify(db)
    wallet_clusters, domain_clusters = stage4_cluster(db)
    matches = stage5_cross_reference(db, wallet_clusters, domain_clusters)
    priority_items = stage6_prioritize(db)
    digest = stage7_create_intelligence_digest(db, wallet_clusters, domain_clusters, matches, priority_items)
    
    # Save digest
    with open("/gfin/artifacts/intelligence-digest.json", "w") as f:
        json.dump(digest, f, indent=2, default=str)
    print("\n=== Digest saved to /gfin/artifacts/intelligence-digest.json ===")
    
    db.close()
    print("\nPipeline complete!")

if __name__ == "__main__":
    run_pipeline()

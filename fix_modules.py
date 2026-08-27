#!/usr/bin/env python3
"""Fix anomaly detector and MIDAS to use correct telegram_intelligence schema"""

# Fix gfin_anomaly_detector.py — wallet query
with open("/gfin/gfin_anomaly_detector.py", "r") as f:
    code = f.read()

old_wallet_query = '''            # Get wallet data from telegram_intelligence
            rows = await conn.fetch("""
                SELECT entity_value as wallet, entity_type, group_name, 
                       COUNT(*) as mention_count,
                       COUNT(DISTINCT group_name) as group_count
                FROM telegram_intelligence
                WHERE entity_type IN ('wallet_btc', 'wallet_eth', 'wallet_tron', 'wallet_solana')
                GROUP BY entity_value, entity_type
                HAVING COUNT(*) > 1
            """)'''

new_wallet_query = '''            # Get wallet data from telegram_intelligence
            rows = await conn.fetch("""
                SELECT group_name, wallets, scam_type, risk_level, created_at,
                       COUNT(*) as mention_count,
                       COUNT(DISTINCT group_name) as group_count
                FROM telegram_intelligence
                WHERE wallets IS NOT NULL AND wallets != '"'"''"'"' AND wallets != '[]'
                GROUP BY group_name, wallets, scam_type, risk_level, created_at
                LIMIT 500
            """)'''

if old_wallet_query in code:
    code = code.replace(old_wallet_query, new_wallet_query)
    print("Fixed wallet query in anomaly_detector")
else:
    print("WARNING: Could not find wallet query to replace")

# Fix the wallet feature extraction
old_wallet_features = '''        features = np.array([[r["mention_count"], r["group_count"]] for r in rows], dtype=np.float64)'''
new_wallet_features = '''        # Extract wallet mentions per group
        import json as _json
        wallet_data = []
        for r in rows:
            wallets = r.get("wallets", "[]")
            if isinstance(wallets, str):
                try: wallets = _json.loads(wallets)
                except: wallets = [wallets] if wallets else []
            for w in (wallets if isinstance(wallets, list) else [wallets]):
                if w:
                    wallet_data.append({
                        "wallet": str(w),
                        "group": r.get("group_name", "unknown"),
                        "scam_type": r.get("scam_type", ""),
                        "risk_level": r.get("risk_level", "")
                    })
        
        if len(wallet_data) < 3:
            return {"anomalies": [], "message": "Not enough wallet data"}
        
        # Aggregate by wallet
        from collections import Counter
        wallet_counts = Counter(wd["wallet"] for wd in wallet_data)
        wallet_groups = defaultdict(set)
        for wd in wallet_data:
            wallet_groups[wd["wallet"]].add(wd["group"])
        
        features = np.array([[
            float(wallet_counts[w]),
            float(len(wallet_groups[w]))
        ] for w in wallet_counts], dtype=np.float64)
        wallet_list = list(wallet_counts.keys())'''

if old_wallet_features in code:
    code = code.replace(old_wallet_features, new_wallet_features)
    print("Fixed wallet feature extraction")
else:
    print("WARNING: Could not find wallet features")

# Fix wallet anomaly output
old_wallet_output = '''        anomalies = []
        for i, r in enumerate(rows):
            if detector.labels_[i] == 1:
                anomalies.append({
                    "wallet": r["wallet"],
                    "type": r["entity_type"],
                    "mention_count": r["mention_count"],
                    "group_count": r["group_count"],
                    "anomaly_score": float(detector.decision_scores_[i]),
                    "reason": f"Mentioned in {r['mention_count']} messages across {r['group_count']} groups"
                })
        
        return {"anomalies": anomalies, "total_wallets": len(rows), "anomaly_count": len(anomalies)}'''

new_wallet_output = '''        anomalies = []
        for i, w in enumerate(wallet_list):
            if detector.labels_[i] == 1:
                anomalies.append({
                    "wallet": w,
                    "mention_count": wallet_counts[w],
                    "group_count": len(wallet_groups[w]),
                    "anomaly_score": float(detector.decision_scores_[i]),
                    "reason": f"Mentioned {wallet_counts[w]}x across {len(wallet_groups[w])} groups"
                })
        
        return {"anomalies": anomalies, "total_wallets": len(wallet_list), "anomaly_count": len(anomalies)}'''

if old_wallet_output in code:
    code = code.replace(old_wallet_output, new_wallet_output)
    print("Fixed wallet anomaly output")
else:
    print("WARNING: Could not find wallet output section")

with open("/gfin/gfin_anomaly_detector.py", "w") as f:
    f.write(code)
print("Anomaly detector fixed")

# Fix MIDAS telegram query
with open("/gfin/gfin_midas.py", "r") as f:
    midas_code = f.read()

old_midas_telegram = '''        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT entity_type, entity_value, group_name, message_snippet, created_at
                FROM telegram_intelligence
                ORDER BY created_at ASC
                LIMIT 5000
            """)'''

new_midas_telegram = '''        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT group_name, wallets, domains, phones, ips, usernames,
                       scam_type, risk_level, created_at
                FROM telegram_intelligence
                ORDER BY created_at ASC
                LIMIT 5000
            """)'''

if old_midas_telegram in midas_code:
    midas_code = midas_code.replace(old_midas_telegram, new_midas_telegram)
    print("Fixed MIDAS telegram query")
else:
    print("WARNING: Could not find MIDAS telegram query")

# Fix MIDAS telegram processing loop
old_midas_loop = '''        processed = 0
        anomalies = 0
        for row in rows:
            src = row["group_name"] or "unknown"
            dst = row["entity_value"]
            result = self.midas.add_edge(src, dst, 
                timestamp=row["created_at"].timestamp() if row["created_at"] else None)
            processed += 1
            if result["is_anomalous"]:
                anomalies += 1'''

new_midas_loop = '''        processed = 0
        anomalies = 0
        import json as _json
        for row in rows:
            src = row["group_name"] or "unknown"
            ts = row["created_at"].timestamp() if row["created_at"] else None
            # Extract entities from text columns
            for field in ["wallets", "domains", "phones", "ips", "usernames"]:
                vals = row.get(field, "[]")
                if isinstance(vals, str):
                    try: vals = _json.loads(vals)
                    except: vals = [vals] if vals else []
                if not isinstance(vals, list): vals = [vals] if vals else []
                for v in vals:
                    if v:
                        result = self.midas.add_edge(src, str(v), timestamp=ts)
                        processed += 1
                        if result["is_anomalous"]:
                            anomalies += 1
            # Also add scam_type as edge
            if row.get("scam_type"):
                result = self.midas.add_edge(src, f"scam:{row['scam_type']}", timestamp=ts)
                processed += 1
                if result["is_anomalous"]:
                    anomalies += 1'''

if old_midas_loop in midas_code:
    midas_code = midas_code.replace(old_midas_loop, new_midas_loop)
    print("Fixed MIDAS processing loop")
else:
    print("WARNING: Could not find MIDAS processing loop")

with open("/gfin/gfin_midas.py", "w") as f:
    f.write(midas_code)
print("MIDAS module fixed")

#!/usr/bin/env python3
"""
Patch telegram_spy.py to stream all intelligence through MIDAS in real-time.
Every entity (wallet, domain, phone, IP, username) becomes a graph edge
from sender → entity, processed through MIDAS for instant anomaly detection.
"""

with open("/gfin/telegram_spy.py", "r") as f:
    code = f.read()

# 1. Add MIDAS import at the top (after other imports)
import_marker = "import json"
import_idx = code.find(import_marker)
if import_idx >= 0 and "midas" not in code[:import_idx + 100]:
    midas_import = """
# === MIDAS Real-time Graph Anomaly Detection ===
import sys
sys.path.insert(0, '/gfin')
try:
    from gfin_midas import midas_pipeline
    MIDAS_AVAILABLE = True
except Exception as e:
    print(f"MIDAS import warning: {e}")
    MIDAS_AVAILABLE = False
"""
    # Insert after the first import json
    code = code[:import_idx + len(import_marker)] + midas_import + code[import_idx + len(import_marker):]
    print("1. Added MIDAS import")
else:
    print("1. MIDAS import already present or import marker not found")

# 2. Add MIDAS edge processing after store_intel(msg_data)
store_marker = "        store_intel(msg_data)"
midas_hook = """        store_intel(msg_data)
        
        # === STREAM THROUGH MIDAS FOR REAL-TIME ANOMALY DETECTION ===
        if MIDAS_AVAILABLE:
            try:
                sender_node = sender_username or sender_name or f"user_{sender_id}"
                anomalies = []
                # Create edges: sender → each entity
                for w in wallets:
                    result = midas_pipeline.midas.add_edge(sender_node, f"WALLET:{w['address']}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Wallet {w['address'][:15]}... score={result['combined_score']:.1f}")
                for d in domains:
                    result = midas_pipeline.midas.add_edge(sender_node, f"DOMAIN:{d}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Domain {d} score={result['combined_score']:.1f}")
                for p in phones:
                    result = midas_pipeline.midas.add_edge(sender_node, f"PHONE:{p}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Phone {p} score={result['combined_score']:.1f}")
                for ip in ips:
                    result = midas_pipeline.midas.add_edge(sender_node, f"IP:{ip}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"IP {ip} score={result['combined_score']:.1f}")
                for u in usernames:
                    result = midas_pipeline.midas.add_edge(sender_node, f"USER:{u}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"User @{u} score={result['combined_score']:.1f}")
                # Create edge: group → sender (track which groups senders operate in)
                midas_pipeline.midas.add_edge(f"GROUP:{group_name}", sender_node)
                # Create edge: group → scam_type (track scam type frequency per group)
                if scam_type:
                    midas_pipeline.midas.add_edge(f"GROUP:{group_name}", f"SCAM:{scam_type}")
                
                if anomalies:
                    logger.warning(f"  🔴 MIDAS ANOMALY: {'; '.join(anomalies)}")
            except Exception as e:
                logger.debug(f"  MIDAS processing error: {e}")"""

if store_marker in code and "MIDAS REAL-TIME" not in code:
    code = code.replace(store_marker, midas_hook, 1)
    print("2. Added MIDAS real-time hook")
else:
    print("2. MIDAS hook already present or marker not found")

# 3. Add periodic MIDAS stats logging (every 100 messages)
# Find the end of process_message function or add a counter
log_marker = "        # Log"
if log_marker in code and "midas_stats_counter" not in code:
    stats_code = """        # Periodic MIDAS stats
        if MIDAS_AVAILABLE and not hasattr(process_message, '_msg_count'):
            process_message._msg_count = 0
        if MIDAS_AVAILABLE:
            process_message._msg_count += 1
            if process_message._msg_count % 100 == 0:
                stats = midas_pipeline.midas.get_stats()
                logger.info(f"  📊 MIDAS: {stats['edges_processed']} edges, {stats['anomalies_detected']} anomalies, {stats['recent_anomalies']} recent")
        
        # Log"""
    code = code.replace(log_marker, stats_code, 1)
    print("3. Added periodic MIDAS stats logging")
else:
    print("3. Stats logging already present or marker not found")

with open("/gfin/telegram_spy.py", "w") as f:
    f.write(code)
print(f"\nDone. File size: {len(code)} bytes")

#!/usr/bin/env python3
"""Patch telegram_spy.py to send MIDAS edges to GFIN server API too"""

with open("/gfin/telegram_spy.py", "r") as f:
    code = f.read()

# The current MIDAS block uses local midas_pipeline only.
# We'll add API calls alongside the local processing.

old_block = """        # === STREAM THROUGH MIDAS FOR REAL-TIME ANOMALY DETECTION ===
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
                # Create edge: group -> sender (track which groups senders operate in)
                midas_pipeline.midas.add_edge(f"GROUP:{group_name}", sender_node)
                # Create edge: group -> scam_type (track scam type frequency per group)
                if scam_type:
                    midas_pipeline.midas.add_edge(f"GROUP:{group_name}", f"SCAM:{scam_type}")
                
                if anomalies:
                    logger.warning(f"  MIDAS ANOMALY: {'; '.join(anomalies)}")
            except Exception as e:
                logger.debug(f"  MIDAS processing error: {e}")"""

new_block = """        # === STREAM THROUGH MIDAS FOR REAL-TIME ANOMALY DETECTION ===
        if MIDAS_AVAILABLE:
            try:
                sender_node = sender_username or sender_name or f"user_{sender_id}"
                anomalies = []
                # Process locally AND send to server API (dual: local + shared)
                def midas_add(src, dst):
                    # Local processing
                    result = midas_pipeline.midas.add_edge(src, dst)
                    # Send to server API (shared MIDAS instance for dashboard)
                    try:
                        req = urllib.request.Request(
                            f"{GFIN_API}/api/midas/edge",
                            data=json.dumps({"src": src, "dst": dst}).encode(),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        urllib.request.urlopen(req, timeout=2)
                    except:
                        pass
                    return result

                for w in wallets:
                    result = midas_add(sender_node, f"WALLET:{w['address']}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Wallet {w['address'][:15]}... score={result['combined_score']:.1f}")
                for d in domains:
                    result = midas_add(sender_node, f"DOMAIN:{d}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Domain {d} score={result['combined_score']:.1f}")
                for p in phones:
                    result = midas_add(sender_node, f"PHONE:{p}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"Phone {p} score={result['combined_score']:.1f}")
                for ip in ips:
                    result = midas_add(sender_node, f"IP:{ip}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"IP {ip} score={result['combined_score']:.1f}")
                for u in usernames:
                    result = midas_add(sender_node, f"USER:{u}")
                    if result.get("is_anomalous"):
                        anomalies.append(f"User @{u} score={result['combined_score']:.1f}")
                midas_add(f"GROUP:{group_name}", sender_node)
                if scam_type:
                    midas_add(f"GROUP:{group_name}", f"SCAM:{scam_type}")

                if anomalies:
                    logger.warning(f"  MIDAS ANOMALY: {'; '.join(anomalies)}")
            except Exception as e:
                logger.debug(f"  MIDAS processing error: {e}")"""

if old_block in code:
    code = code.replace(old_block, new_block, 1)
    with open("/gfin/telegram_spy.py", "w") as f:
        f.write(code)
    print("Updated MIDAS hook with dual local+API processing")
    print(f"Size: {len(code)} bytes")
else:
    print("Old block not found — may have different formatting")
    # Try to find it
    import difflib
    midas_idx = code.find("STREAM THROUGH MIDAS")
    if midas_idx >= 0:
        print(f"Found MIDAS block at char {midas_idx}")
        print("Context:", repr(code[midas_idx:midas_idx+200]))

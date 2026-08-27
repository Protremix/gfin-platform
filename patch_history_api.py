#!/usr/bin/env python3
"""Patch history scan to also send MIDAS edges via API"""

with open("/gfin/telegram_spy.py", "r") as f:
    code = f.read()

# Find the history scan MIDAS block and add API calls
old = """            # Stream through MIDAS
            if MIDAS_AVAILABLE:
                try:
                    snode = sender_username or sender_name.strip() or f"user_{sender_id}"
                    for w in wallets:
                        midas_pipeline.midas.add_edge(snode, f"WALLET:{w['address']}\")
                        midas_edges += 1
                    for d in domains:
                        midas_pipeline.midas.add_edge(snode, f"DOMAIN:{d}\")
                        midas_edges += 1
                    for p in phones:
                        midas_pipeline.midas.add_edge(snode, f"PHONE:{p}\")
                    for ip in ips:
                        midas_pipeline.midas.add_edge(snode, f"IP:{ip}\")
                    for u in usernames:
                        midas_pipeline.midas.add_edge(snode, f"USER:{u}\")
                    midas_pipeline.midas.add_edge(f"GROUP:{title}\", snode)
                    if scam_type:
                        midas_pipeline.midas.add_edge(f"GROUP:{title}\", f"SCAM:{scam_type}\")
                except Exception as e:
                    pass"""

new = """            # Stream through MIDAS (local + server API)
            if MIDAS_AVAILABLE:
                try:
                    snode = sender_username or sender_name.strip() or f"user_{sender_id}"
                    def hist_midas_add(src, dst):
                        midas_pipeline.midas.add_edge(src, dst)
                        try:
                            req = urllib.request.Request(
                                f"{GFIN_API}/api/midas/edge",
                                data=json.dumps({"src": src, "dst": dst}).encode(),
                                headers={"Content-Type": "application/json"},
                                method="POST"
                            )
                            urllib.request.urlopen(req, timeout=1)
                        except:
                            pass
                    for w in wallets:
                        hist_midas_add(snode, f"WALLET:{w['address']}\")
                        midas_edges += 1
                    for d in domains:
                        hist_midas_add(snode, f"DOMAIN:{d}\")
                        midas_edges += 1
                    for p in phones:
                        hist_midas_add(snode, f"PHONE:{p}\")
                    for ip in ips:
                        hist_midas_add(snode, f"IP:{ip}\")
                    for u in usernames:
                        hist_midas_add(snode, f"USER:{u}\")
                    hist_midas_add(f"GROUP:{title}", snode)
                    if scam_type:
                        hist_midas_add(f"GROUP:{title}", f"SCAM:{scam_type}")
                except Exception as e:
                    pass"""

if old in code:
    code = code.replace(old, new, 1)
    with open("/gfin/telegram_spy.py", "w") as f:
        f.write(code)
    print("Updated history scan with API calls")
    print(f"Size: {len(code)} bytes")
else:
    print("Block not found — trying flexible match")
    # Try with arrow characters
    code2 = code.replace("\u2192", "->")  # Replace Unicode arrows
    if old in code2:
        code = code2.replace(old, new, 1)
        with open("/gfin/telegram_spy.py", "w") as f:
            f.write(code)
        print("Updated with flexible match")
    else:
        # Find the block and show context
        idx = code.find("Stream through MIDAS")
        if idx >= 0:
            print("Context:", repr(code[idx:idx+300]))

#!/usr/bin/env python3
"""Patch MIDAS in telegram_spy.py — add API calls alongside local processing"""

with open("/gfin/telegram_spy.py", "r") as f:
    lines = f.readlines()

# Find the MIDAS block start and end
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "STREAM THROUGH MIDAS FOR REAL-TIME" in line:
        start_idx = i
    if start_idx is not None and i > start_idx and "MIDAS processing error" in line:
        end_idx = i + 1  # include the except line
        break

if start_idx is None:
    print("MIDAS block not found!")
    exit(1)

print(f"Found MIDAS block at lines {start_idx+1}-{end_idx}")

# Build the new block
new_lines = [
    "        # === STREAM THROUGH MIDAS FOR REAL-TIME ANOMALY DETECTION ===\n",
    "        if MIDAS_AVAILABLE:\n",
    "            try:\n",
    "                sender_node = sender_username or sender_name or f\"user_{sender_id}\"\n",
    "                anomalies = []\n",
    "                # Process locally AND send to server API (dual: local + shared)\n",
    "                def midas_add(src, dst):\n",
    "                    result = midas_pipeline.midas.add_edge(src, dst)\n",
    "                    try:\n",
    "                        req = urllib.request.Request(\n",
    "                            f\"{GFIN_API}/api/midas/edge\",\n",
    "                            data=json.dumps({\"src\": src, \"dst\": dst}).encode(),\n",
    "                            headers={\"Content-Type\": \"application/json\"},\n",
    "                            method=\"POST\"\n",
    "                        )\n",
    "                        urllib.request.urlopen(req, timeout=2)\n",
    "                    except:\n",
    "                        pass\n",
    "                    return result\n",
    "                for w in wallets:\n",
    "                    result = midas_add(sender_node, f\"WALLET:{w['address']}\")\n",
    "                    if result.get(\"is_anomalous\"):\n",
    "                        anomalies.append(f\"Wallet {w['address'][:15]}... score={result['combined_score']:.1f}\")\n",
    "                for d in domains:\n",
    "                    result = midas_add(sender_node, f\"DOMAIN:{d}\")\n",
    "                    if result.get(\"is_anomalous\"):\n",
    "                        anomalies.append(f\"Domain {d} score={result['combined_score']:.1f}\")\n",
    "                for p in phones:\n",
    "                    result = midas_add(sender_node, f\"PHONE:{p}\")\n",
    "                    if result.get(\"is_anomalous\"):\n",
    "                        anomalies.append(f\"Phone {p} score={result['combined_score']:.1f}\")\n",
    "                for ip in ips:\n",
    "                    result = midas_add(sender_node, f\"IP:{ip}\")\n",
    "                    if result.get(\"is_anomalous\"):\n",
    "                        anomalies.append(f\"IP {ip} score={result['combined_score']:.1f}\")\n",
    "                for u in usernames:\n",
    "                    result = midas_add(sender_node, f\"USER:{u}\")\n",
    "                    if result.get(\"is_anomalous\"):\n",
    "                        anomalies.append(f\"User @{u} score={result['combined_score']:.1f}\")\n",
    "                midas_add(f\"GROUP:{group_name}\", sender_node)\n",
    "                if scam_type:\n",
    "                    midas_add(f\"GROUP:{group_name}\", f\"SCAM:{scam_type}\")\n",
    "                if anomalies:\n",
    "                    logger.warning(f\"  MIDAS ANOMALY: {'; '.join(anomalies)}\")\n",
    "            except Exception as e:\n",
    "                logger.debug(f\"  MIDAS processing error: {e}\")\n",
]

# Replace the old block with the new block
lines = lines[:start_idx] + new_lines + lines[end_idx:]

with open("/gfin/telegram_spy.py", "w") as f:
    f.writelines(lines)

print(f"Replaced MIDAS block with dual local+API version")
print(f"Total lines: {len(lines)}")

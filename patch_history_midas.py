#!/usr/bin/env python3
"""Patch telegram_spy.py scan_history to process through MIDAS"""

with open("/gfin/telegram_spy.py", "r") as f:
    lines = f.readlines()

# Find the history scan section and add MIDAS processing + store_intel
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if "async def scan_history" in line:
        start_idx = i
    if start_idx is not None and i > start_idx:
        if "Scanned" in line and "messages" in line:
            end_idx = i + 1
            break

if start_idx is None:
    print("scan_history not found!")
    exit(1)

print(f"Found scan_history at lines {start_idx+1}-{end_idx}")

new_scan = [
    "async def scan_history(group_entity, limit=100):\n",
    "    \"\"\"Scan recent message history of a group.\"\"\"\n",
    "    title = group_entity.title if hasattr(group_entity, 'title') else str(group_entity.id)\n",
    "    logger.info(f\"Scanning history of {title}...\")\n",
    "    count = 0\n",
    "    intel_count = 0\n",
    "    midas_edges = 0\n",
    "    async for message in client.iter_messages(group_entity, limit=limit):\n",
    "        if not message.text:\n",
    "            continue\n",
    "        count += 1\n",
    "        text = message.text\n",
    "        \n",
    "        wallets = extract_wallets(text)\n",
    "        domains = extract_domains(text)\n",
    "        phones = extract_phones(text)\n",
    "        ips = extract_ips(text)\n",
    "        usernames = extract_usernames(text)\n",
    "        is_victim, victim_patterns = detect_victim(text)\n",
    "        scam_type, scam_indicators = detect_scam(text)\n",
    "        risk_level = calculate_risk(wallets, domains, is_victim, scam_indicators, scam_type)\n",
    "        \n",
    "        if wallets or domains or is_victim or scam_indicators or phones:\n",
    "            intel_count += 1\n",
    "            sender = await message.get_sender()\n",
    "            sender_name = (sender.first_name + \" \" + (sender.last_name or \"\")) if sender and hasattr(sender, \"first_name\") else \"Unknown\"\n",
    "            sender_username = sender.username if sender and hasattr(sender, \"username\") else \"\"\n",
    "            sender_id = sender.id if sender and hasattr(sender, \"id\") else 0\n",
    "            \n",
    "            if wallets:\n",
    "                logger.info(f\"  [HISTORY] {sender_name}: {len(wallets)} wallets\")\n",
    "            if domains:\n",
    "                logger.info(f\"  [HISTORY] {sender_name}: domains={domains[:3]}\")\n",
    "            if is_victim:\n",
    "                logger.info(f\"  [HISTORY] {sender_name}: VICTIM detected\")\n",
    "            if scam_type:\n",
    "                logger.info(f\"  [HISTORY] {sender_name}: scam={scam_type}\")\n",
    "            \n",
    "            # Store intelligence in DB\n",
    "            msg_data = {\n",
    "                \"message_id\": message.id,\n",
    "                \"group_id\": group_entity.id if hasattr(group_entity, 'id') else 0,\n",
    "                \"group_name\": title,\n",
    "                \"sender_id\": sender_id,\n",
    "                \"sender_name\": sender_name.strip(),\n",
    "                \"sender_username\": sender_username or \"\",\n",
    "                \"message_text\": text[:5000],\n",
    "                \"wallets\": wallets,\n",
    "                \"domains\": domains,\n",
    "                \"phones\": phones,\n",
    "                \"ips\": ips,\n",
    "                \"usernames\": usernames,\n",
    "                \"is_victim\": is_victim,\n",
    "                \"victim_patterns\": victim_patterns,\n",
    "                \"scam_type\": scam_type,\n",
    "                \"scam_indicators\": scam_indicators,\n",
    "                \"risk_level\": risk_level,\n",
    "            }\n",
    "            store_intel(msg_data)\n",
    "            \n",
    "            # Stream through MIDAS\n",
    "            if MIDAS_AVAILABLE:\n",
    "                try:\n",
    "                    snode = sender_username or sender_name.strip() or f\"user_{sender_id}\"\n",
    "                    for w in wallets:\n",
    "                        midas_pipeline.midas.add_edge(snode, f\"WALLET:{w['address']}\")\n",
    "                        midas_edges += 1\n",
    "                    for d in domains:\n",
    "                        midas_pipeline.midas.add_edge(snode, f\"DOMAIN:{d}\")\n",
    "                        midas_edges += 1\n",
    "                    for p in phones:\n",
    "                        midas_pipeline.midas.add_edge(snode, f\"PHONE:{p}\")\n",
    "                    for ip in ips:\n",
    "                        midas_pipeline.midas.add_edge(snode, f\"IP:{ip}\")\n",
    "                    for u in usernames:\n",
    "                        midas_pipeline.midas.add_edge(snode, f\"USER:{u}\")\n",
    "                    midas_pipeline.midas.add_edge(f\"GROUP:{title}\", snode)\n",
    "                    if scam_type:\n",
    "                        midas_pipeline.midas.add_edge(f\"GROUP:{title}\", f\"SCAM:{scam_type}\")\n",
    "                except Exception as e:\n",
    "                    pass\n",
    "    \n",
    "    logger.info(f\"  Scanned {count} messages, {intel_count} with intelligence, {midas_edges} MIDAS edges\")\n",
]

lines = lines[:start_idx] + new_scan + lines[end_idx:]

with open("/gfin/telegram_spy.py", "w") as f:
    f.writelines(lines)
print(f"Updated scan_history with MIDAS + store_intel integration")
print(f"Total lines: {len(lines)}")

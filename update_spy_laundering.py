#!/usr/bin/env python3
"""
Update the GFIN Telegram spy to include money laundering detection.
This patch adds laundering detection to the existing spy's message analysis.
"""

import re

SPY_FILE = "/gfin/telegram_spy.py"

# Read the current spy file
with open(SPY_FILE, "r") as f:
    spy_code = f.read()

# Check if laundering detection already added
if "money_laundering" in spy_code.lower() and "detect_money_laundering" in spy_code:
    print("Money laundering detection already in spy")
else:
    # Add import for laundering detector
    spy_code = spy_code.replace(
        "import asyncio",
        "import asyncio\nimport sys\nsys.path.insert(0, \"/gfin\")\nfrom money_laundering_detector import detect_money_laundering, create_laundering_alert"
    )
    
    # Add laundering detection to message analysis function
    # Find the pattern where messages are analyzed and add laundering check
    laundering_check = '''
        # Money Laundering Detection
        try:
            laundering_result = detect_money_laundering(text)
            if laundering_result["is_laundering"]:
                laundering_alert = create_laundering_alert(
                    source="telegram_spy",
                    group_name=group_title,
                    group_username=group_username,
                    message_text=text,
                    detected=laundering_result
                )
                # Save to laundering alerts file
                import json
                alerts_file = "/gfin/laundering_alerts.json"
                try:
                    with open(alerts_file, "r") as af:
                        alerts = json.load(af)
                except:
                    alerts = []
                alerts.append(laundering_alert)
                with open(alerts_file, "w") as af:
                    json.dump(alerts, af, indent=2)
                
                print(f"  [LAUNDERING ALERT] {laudering_result['risk_level']} - {group_title} - Score: {laudering_result['risk_score']}")
                print(f"  Patterns: {laudering_result['detected_patterns']}")
                
                # Also store in intelligence database
                try:
                    import urllib.request
                    data = json.dumps({
                        "text": text,
                        "group_name": group_title,
                        "group_username": group_username,
                        "source": "telegram_spy"
                    }).encode()
                    req = urllib.request.Request(
                        "http://127.0.0.1:8000/api/laundering/analyze-message",
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=5)
                except:
                    pass
        except Exception as e:
            print(f"  Laundering detection error: {e}")
'''
    
    # Insert after scam detection block (find a good insertion point)
    # Look for where scam patterns are checked and add after that
    if "scam_indicators" in spy_code and "scam_type" in spy_code:
        # Find the end of the scam detection section
        insert_marker = "# Store intelligence"
        if insert_marker in spy_code:
            spy_code = spy_code.replace(
                insert_marker,
                laundering_check + "\n        " + insert_marker
            )
            print("Laundering detection added to spy message analysis")
        else:
            # Try another insertion point
            insert_marker = "intel_item = {"
            if insert_marker in spy_code:
                spy_code = spy_code.replace(
                    insert_marker,
                    laundering_check + "\n        " + insert_marker
                )
                print("Laundering detection added to spy (alt insertion)")
            else:
                print("WARNING: Could not find insertion point in spy")
    else:
        print("WARNING: Could not find scam detection section in spy")
    
    with open(SPY_FILE, "w") as f:
        f.write(spy_code)
    print("Spy file updated with money laundering detection")

print("Done")

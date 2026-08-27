"""Fix incident_date parsing in gfin_server.py"""
import re

content = open("/gfin/gfin_server.py").read()

# Check if already fixed
if "def parse_date" in content:
    print("Already fixed")
    exit(0)

# Find the incident_date line in file_complaint
# The line passes incident_date as a string to PostgreSQL
old_line = "    incident_date or None, financial_loss, description, country"
new_line = "    _parse_date(incident_date), financial_loss, description, country"

if old_line in content:
    content = content.replace(old_line, new_line)
    print("Replaced incident_date line")
else:
    # Try to find the pattern
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "incident_date" in line and "financial_loss" in line:
            print(f"Found at line {i+1}: {line.strip()}")
            content = content.replace(line, line.replace("incident_date or None", "_parse_date(incident_date)"))
            break

# Add _parse_date helper and datetime import
if "from datetime import" not in content:
    content = content.replace(
        "import hashlib",
        "import hashlib\nfrom datetime import datetime as _dt\n\n\ndef _parse_date(date_str):\n    if not date_str:\n        return None\n    try:\n        return _dt.strptime(date_str, '%Y-%m-%d').date()\n    except Exception:\n        try:\n            return _dt.strptime(date_str, '%d/%m/%Y').date()\n        except Exception:\n            return None\n"
    )
    print("Added _parse_date helper and datetime import")
else:
    # datetime already imported, just add _parse_date
    if "def _parse_date" not in content:
        helper = "\n\ndef _parse_date(date_str):\n    if not date_str:\n        return None\n    try:\n        return _dt.strptime(date_str, '%Y-%m-%d').date()\n    except Exception:\n        try:\n            return _dt.strptime(date_str, '%d/%m/%Y').date()\n        except Exception:\n            return None\n"
        # Add before the complaint endpoint
        content = content.replace(
            '@app.post("/api/victim/complaint")',
            helper + '\n@app.post("/api/victim/complaint")'
        )
        print("Added _parse_date helper")

open("/gfin/gfin_server.py", "w").write(content)
print(f"Done ({len(content.splitlines())} lines)")

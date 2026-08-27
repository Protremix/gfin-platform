"""Fix the evidence correlation endpoint — variable scope issue."""
import re

with open("/gfin/dashboard_enhanced_routes.py", "r") as f:
    content = f.read()

# Fix: the case_wallets etc variables are declared inside a try block but used outside
# Need to initialize them before the try block
old = '''    # Load case data from telegram intelligence
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        
        # Find all items that mention this case or share entities
        case_wallets = set()
        case_domains = set()
        case_phones = set()
        case_senders = set()'''

new = '''    # Load case data from telegram intelligence
    case_wallets = set()
    case_domains = set()
    case_phones = set()
    case_senders = set()
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        
        # Find all items that mention this case or share entities'''

content = content.replace(old, new)

with open("/gfin/dashboard_enhanced_routes.py", "w") as f:
    f.write(content)
print("Fixed evidence correlation endpoint")

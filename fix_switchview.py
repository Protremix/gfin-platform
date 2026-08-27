"""Fix the switchView function to call load functions for the 5 new views."""

with open("/gfin/police_dashboard_mobile.html", "r") as f:
    code = f.read()

old_switch = """      if (viewName === 'officers') loadOfficers();
      if (viewName === 'hunter') loadHunterActivity();
      if (viewName === 'flagged') loadFlaggedDomains();
      if (viewName === 'intel') loadIntel();"""

new_switch = """      if (viewName === 'officers') loadOfficers();
      if (viewName === 'hunter') loadHunterActivity();
      if (viewName === 'flagged') loadFlaggedDomains();
      if (viewName === 'intel') loadIntel();
      if (viewName === 'laundering') loadLaundering();
      if (viewName === 'wallets') loadWallets();
      if (viewName === 'evidence') loadEvidence();
      if (viewName === 'operators') loadOperators();
      if (viewName === 'outreach') loadOutreach();"""

if old_switch in code:
    code = code.replace(old_switch, new_switch)
    with open("/gfin/police_dashboard_mobile.html", "w") as f:
        f.write(code)
    print("FIXED: switchView now calls load functions for all 5 new views")
else:
    print("ERROR: Could not find the switchView block to replace")
    # Try a more flexible match
    import re
    pattern = r"if \(viewName === 'officers'\) loadOfficers\(\);.*?if \(viewName === 'intel'\) loadIntel\(\);"
    match = re.search(pattern, code, re.DOTALL)
    if match:
        code = code[:match.start()] + new_switch + code[match.end():]
        with open("/gfin/police_dashboard_mobile.html", "w") as f:
            f.write(code)
        print("FIXED (flexible match): switchView now calls all 5 new view load functions")
    else:
        print("FATAL: Could not locate switchView load calls")

#!/usr/bin/env python3
"""Fix duplicate loadMispStatus - merge both into one"""

with open("/gfin/investigator_workbench.html", "r") as f:
    code = f.read()

# The first loadMispStatus (line ~2260) updates mispStatus card
# The second loadMispStatus (line ~2364) updates mispResults panel
# We need to merge them: the second one should also update the status card

old_second = """    async function loadMispStatus() {
      const el = document.getElementById('mispResults');"""

new_second = """    async function loadMispStatus() {
      // Update status card
      try {
        const statusData = await apiGet('/api/misp/status');
        const stixBadge = statusData.stix_export ? '<span style="color:#22c55e;font-weight:600;">STIX 2.1 Ready</span>' : '<span style="color:#ef4444;">STIX Unavailable</span>';
        const mispBadge = statusData.misp_sharing ? '<span style="color:#22c55e;font-weight:600;">MISP Connected</span>' : '<span style="color:#f59e0b;font-weight:600;">MISP Not Configured</span>';
        document.getElementById('mispStatus').innerHTML = stixBadge + ' &middot; ' + mispBadge;
      } catch(e) {
        document.getElementById('mispStatus').innerHTML = '<span style="color:#ef4444;">● Error</span>';
      }
      // Update results panel
      const el = document.getElementById('mispResults');"""

if old_second in code:
    code = code.replace(old_second, new_second, 1)
    with open("/gfin/investigator_workbench.html", "w") as f:
        f.write(code)
    print("Fixed duplicate loadMispStatus - merged status card + results panel")
else:
    print("Second loadMispStatus not found")

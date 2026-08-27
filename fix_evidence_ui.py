#!/usr/bin/env python3
"""Fix evidence UI: use correct API endpoint + show who added evidence"""

with open("/gfin/investigator_workbench.html", "r") as f:
    content = f.read()

# 1. Fix submitEvidence to use the correct API endpoint
old_submit = '''    await apiPost(`/api/inv/case/${currentCaseId}/evidence`, { phase, finding, confidence, source_provider: officerInfo?.agency || 'OFFICER' });
    openCase(currentCaseId);'''

new_submit = '''    await apiPost(`/api/evidence/${currentCaseId}`, { phase, finding, confidence, source_provider: 'OFFICER', source_type: 'MANUAL' });
    openCase(currentCaseId);'''

content = content.replace(old_submit, new_submit)

# 2. Update renderEvidence to show who added each evidence item
old_evidence_meta = '''            <span><i class="fa-solid fa-gauge"></i> ${e.confidence || 'MEDIUM'}</span>
            <span><i class="fa-solid fa-clock"></i> ${e.created_date ? new Date(e.created_date).toLocaleString() : '—'}</span>
          </div>'''

new_evidence_meta = '''            <span><i class="fa-solid fa-gauge"></i> ${e.confidence || 'MEDIUM'}</span>
            <span><i class="fa-solid fa-user-shield"></i> ${e.added_by_officer || 'SYSTEM'}</span>
            <span><i class="fa-solid fa-clock"></i> ${e.created_date ? new Date(e.created_date).toLocaleString() : '—'}</span>
          </div>'''

content = content.replace(old_evidence_meta, new_evidence_meta)

# 3. Fix addNote to use correct endpoint
old_note = '''    await apiPost(`/api/inv/case/${currentCaseId}/note`, { note });'''
new_note = '''    await apiPost(`/api/cases/${currentCaseId}/notes`, { note_text: note, note_type: 'INFO' });'''

content = content.replace(old_note, new_note)

with open("/gfin/investigator_workbench.html", "w") as f:
    f.write(content)
print("Fixed evidence UI: API endpoint + officer attribution display")

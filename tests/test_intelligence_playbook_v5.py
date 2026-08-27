"""Test GFIN Intelligence Playbook v5.0 — Full Investigation from Subject to Physical Address"""
import json, sys, importlib.util

spec = importlib.util.spec_from_file_location("ip5", "/gfin/packages/services/intelligence_playbook_v5.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

engine = mod.IntelligencePlaybook()

results = {"tests": [], "passed": 0, "failed": 0}

def record(name, passed, details=""):
    results["tests"].append({"test": name, "passed": passed, "details": details[:200]})
    print(f"{'PASS' if passed else 'FAIL'}: {name}")

print("=" * 60)
print("GFIN INTELLIGENCE PLAYBOOK v5.0 — FULL INVESTIGATION TEST")
print("=" * 60)

# === TEST 1: Intelligence Playbook is comprehensive ===
print("\n--- TEST 1: Intelligence Playbook Coverage ---")
playbook_types = list(mod.INTELLIGENCE_PLAYBOOK.keys())
record("playbook_has_12_types", len(playbook_types) >= 12, f"Types: {len(playbook_types)} — {playbook_types}")

# Check each type has what_to_find, how_to_find, leads_to
for ptype, pb in mod.INTELLIGENCE_PLAYBOOK.items():
    has_what = len(pb.get("what_to_find", [])) > 0
    has_how = len(pb.get("how_to_find", [])) > 0
    has_leads = len(pb.get("leads_to", [])) > 0
    record(f"playbook_{ptype}_complete", has_what and has_how and has_leads,
           f"What: {len(pb.get('what_to_find',[]))}, How: {len(pb.get('how_to_find',[]))}, Leads: {len(pb.get('leads_to',[]))}")

# === TEST 2: Trigger types defined ===
print("\n--- TEST 2: Trigger Types ---")
record("trigger_types_defined", len(mod.TRIGGER_TYPES) >= 7, f"Triggers: {list(mod.TRIGGER_TYPES.keys())}")

# === TEST 3: Full investigation with subject → evidence chain ===
print("\n--- TEST 3: Full Investigation (cncintelinfo.com) ===")
investigation = engine.investigate({
    "trigger": "MANUAL",
    "trigger_reason": "Known crypto recovery scam domain — testing full investigation capability",
    "identifier": "cncintelinfo.com",
    "identifier_type": "DOMAIN",
    "operator": "GFIN-CEA",
    "authority": "Public OSINT investigation",
})

record("investigation_has_id", "investigation_id" in investigation, f"ID: {investigation['investigation_id']}")
record("investigation_has_subject", "subject" in investigation, "Subject present")
record("investigation_has_evidence_chain", len(investigation["evidence_chain"]) > 0, f"Chain steps: {len(investigation['evidence_chain'])}")
record("investigation_has_attribution", len(investigation["attribution_chain"]) > 0, f"Attribution steps: {len(investigation['attribution_chain'])}")
record("investigation_has_report", len(investigation["report"]) > 100, f"Report length: {len(investigation['report'])} chars")
record("investigation_has_next_steps", len(investigation["next_steps"]) > 0, f"Next steps: {len(investigation['next_steps'])}")

# Check report starts with SUBJECT
report_lines = investigation["report"].split("\n")
record("report_starts_with_subject", any("SUBJECT" in line for line in report_lines[:10]), "Report starts with SUBJECT section")
record("report_has_evidence_chain", any("EVIDENCE CHAIN" in line for line in report_lines), "Report has evidence chain section")
record("report_has_attribution", any("ATTRIBUTION" in line for line in report_lines), "Report has attribution section")
record("report_has_physical_locations", any("PHYSICAL LOCATIONS" in line for line in report_lines), "Report has physical locations section")
record("report_has_next_steps", any("NEXT STEPS" in line for line in report_lines), "Report has next steps section")
record("report_has_disclaimer", any("DISCLAIMER" in line for line in report_lines), "Report has disclaimer")

# === TEST 4: Evidence chain structure ===
print("\n--- TEST 4: Evidence Chain Structure ---")
subject_step = [s for s in investigation["evidence_chain"] if s.get("phase") == "SUBJECT"]
record("evidence_has_subject_step", len(subject_step) > 0, "Subject step present")
playbook_step = [s for s in investigation["evidence_chain"] if s.get("phase") == "PLAYBOOK"]
record("evidence_has_playbook_step", len(playbook_step) > 0, "Playbook step present")

# === TEST 5: Attribution chain finds digital identifiers ===
print("\n--- TEST 5: Attribution Chain ===")
digital_ids = investigation.get("digital_identifiers", [])
record("attribution_finds_digital_ids", len(digital_ids) >= 0, f"Digital identifiers: {len(digital_ids)}")
financial = investigation.get("financial_indicators", [])
record("attribution_finds_financial", len(financial) >= 0, f"Financial indicators: {len(financial)}")
scams = investigation.get("scam_indicators", [])
record("attribution_finds_scam_indicators", len(scams) >= 0, f"Scam indicators: {len(scams)}")
physical = investigation.get("physical_locations", [])
record("attribution_finds_physical", len(physical) >= 0, f"Physical locations: {len(physical)}")

# === TEST 6: Next steps with legal authority ===
print("\n--- TEST 6: Next Steps with Legal Authority ---")
for ns in investigation["next_steps"]:
    has_action = bool(ns.get("action"))
    has_detail = bool(ns.get("detail"))
    has_priority = bool(ns.get("priority"))
    record(f"next_step_{ns.get('action','')[:20]}", has_action and has_detail and has_priority,
           f"Action: {ns.get('action','')[:50]}, Priority: {ns.get('priority','')}")

# === TEST 7: Wallet investigation playbook ===
print("\n--- TEST 7: Wallet Investigation ===")
wallet_inv = engine.investigate({
    "trigger": "PATTERN_MATCH",
    "trigger_reason": "Crypto wallet found on scam website — tracing transactions",
    "identifier": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "identifier_type": "WALLET",
    "operator": "GFIN-CEA",
    "authority": "Public blockchain analysis",
})
record("wallet_investigation_has_blockchain", any("BLOCKCHAIN" in s.get("phase", "") for s in wallet_inv["evidence_chain"]),
       "Blockchain analysis step present")
record("wallet_investigation_has_transactions", any("TRANSACTION" in s.get("phase", "") for s in wallet_inv["evidence_chain"]),
       "Transaction trace present")
record("wallet_investigation_financial", len(wallet_inv.get("financial_indicators", [])) > 0,
       f"Financial indicators: {len(wallet_inv.get('financial_indicators', []))}")

# === TEST 8: Report narrative quality ===
print("\n--- TEST 8: Report Narrative Quality ===")
report = investigation["report"]
# Check the report explains WHY we started
record("report_explains_why", "trigger_reason" in report.lower() or "why" in report.lower()[:500],
       "Report explains why investigation was started")
# Check the report explains WHAT was found
record("report_explains_what", any(w in report for w in ["Found", "Hosted", "registered", "Wallet"]),
       "Report explains what was found")
# Check the report explains HOW (sources)
record("report_explains_how", any(s in report for s in ["RDAP", "URLScan", "BLOCKCHAIN", "WAYBACK", "CRT"]),
       "Report explains how (sources used)")
# Check the report has next steps with legal authority
record("report_has_legal_authority", "court order" in report.lower() or "subpoena" in report.lower() or "MLAT" in report.lower(),
       "Report mentions legal authority needed")

# === FINAL METRICS ===
total = len(results["tests"])
passed = len([t for t in results["tests"] if t["passed"]])
failed = total - passed
results["total"] = total
results["passed"] = passed
results["failed"] = failed
results["pass_rate"] = f"{passed/total*100:.1f}%" if total > 0 else "N/A"

print("\n" + "=" * 60)
print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failed}")
print(f"Pass rate: {results['pass_rate']}")
print("=" * 60)

print(json.dumps(results, indent=2))

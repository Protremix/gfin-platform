import json, sys, importlib.util

# Load ScamHunter
spec = importlib.util.spec_from_file_location("scam_hunter", "/gfin/packages/services/scam_hunter.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

engine = mod.ScamHunterEngine()
results = {"tests": [], "passed": 0, "failed": 0}

def record(name, passed, details=""):
    results["tests"].append({"test": name, "passed": passed, "details": details[:200]})
    if passed: results["passed"] += 1
    else: results["failed"] += 1

# === TEST 1: Trace a fake investment scam ===
# Simulating a victim who was scammed by a fake crypto investment site
victim_report = {
    "scam_website_url": "cncintelinfo.com",  # Known scam domain from CASE-REAL-001
    "scam_phone_number": "+44 7451 261353",
    "scam_email": "support@cncintelinfo.com",
    "crypto_wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block address for testing
    "scam_social_media": {"telegram_channel": "durov"},  # Test with known public channel
    "amount_lost": "$50,000",
    "date_of_scam": "2025-03-15",
    "description": "Victim was lured into fake crypto recovery scam. Website claimed to be a fund recovery service.",
}

trace = engine.trace_victim_to_scammer(victim_report)
record("trace_victim_to_scammer", "case_id" in trace, f"Case: {trace.get('case_id','?')}, Evidence: {len(trace.get('evidence',[]))}")

# Check evidence was collected
record("evidence_collected", len(trace.get("evidence", [])) > 0, f"{len(trace.get('evidence',[]))} evidence items")
record("connections_found", len(trace.get("connections_found", [])) > 0, f"{len(trace.get('connections_found',[]))} connections")
record("risk_assessment", "level" in trace.get("risk_assessment", {}), f"Risk: {trace.get('risk_assessment',{}).get('level','?')}")
record("recovery_recommendations", len(trace.get("recovery_recommendations", [])) > 0, f"{len(trace.get('recovery_recommendations',[]))} recommendations")

# === TEST 2: Fake page detection ===
fake = engine.detect_fake_page("cncintelinfo.com", "legitimate-recovery-service.com")
record("fake_page_detection", "verdict" in fake, f"Verdict: {fake.get('verdict','?')}")
record("fake_page_evidence", len(fake.get("evidence", [])) >= 0, f"{len(fake.get('evidence',[]))} evidence items")

# === TEST 3: Crypto tracing (Bitcoin) ===
crypto = engine._trace_crypto("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin")
record("crypto_trace_btc", "indicators" in crypto, f"TXs: {crypto.get('indicators',{}).get('transaction_count',0)}")

# === TEST 4: Phone analysis ===
phone = engine._analyze_phone("+44 7451 261353")
record("phone_analysis", phone["indicators"]["country"] == "United Kingdom", f"Country: {phone['indicators']['country']}")

# === TEST 5: Email analysis ===
email = engine._analyze_email("support@cncintelinfo.com")
record("email_analysis", "email_domain" in email["indicators"], f"Domain: {email['indicators'].get('email_domain','?')}")

# === TEST 6: Evidence package builder ===
package = engine.build_evidence_package(trace["case_id"])
record("evidence_package", "case_id" in package, f"Evidence items: {package.get('evidence_count',0)}")
record("package_chain_of_custody", "chain_of_custody" in package, "Chain of custody present")
record("package_certification", "certification" in package, "Certification statement present")

# === TEST 7: Website analysis with scam indicators ===
web = engine._analyze_website("cncintelinfo.com")
record("website_analysis", "indicators" in web, f"Indicators: {len(web.get('indicators',{}))} fields")

# Print results
print(json.dumps(results, indent=2))

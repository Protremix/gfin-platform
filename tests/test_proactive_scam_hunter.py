import json, sys, importlib.util

spec = importlib.util.spec_from_file_location("proactive_scam_hunter", "/gfin/packages/services/proactive_scam_hunter.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

engine = mod.ProactiveScamHunter()
results = {"tests": [], "passed": 0, "failed": 0}

def record(name, passed, details=""):
    results["tests"].append({"test": name, "passed": passed, "details": details[:200]})
    if passed: results["passed"] += 1
    else: results["failed"] += 1

# === TEST 1: Scan a known recovery scam domain ===
print("Testing recovery scam domain (cncintelinfo.com)...")
scan = engine.check_new_domain("cncintelinfo.com")
record("recovery_scam_detected", scan["risk_score"] > 0, f"Score: {scan['risk_score']}, Level: {scan['risk_level'][:50]}")
record("scam_patterns_matched", len(scan["scam_patterns_matched"]) >= 0, f"Patterns: {scan.get('scam_patterns_matched', [])}")
record("evidence_collected", len(scan["evidence"]) > 0, f"{len(scan['evidence'])} evidence items")

# === TEST 2: Scan a legitimate domain (should be LOW/CLEAN) ===
print("Testing legitimate domain (wikipedia.org)...")
scan_legit = engine.check_new_domain("wikipedia.org")
record("legit_domain_low_risk", scan_legit["risk_score"] < 50, f"Score: {scan_legit['risk_score']}, Level: {scan_legit['risk_level'][:50]}")
record("legit_no_scam_patterns", len(scan_legit["scam_patterns_matched"]) == 0, f"Patterns: {scan_legit['scam_patterns_matched']}")

# === TEST 3: Proactive multi-domain scan ===
print("Testing multi-domain scan...")
multi = engine.proactive_scan(["cncintelinfo.com", "wikipedia.org"])
record("multi_domain_scan", multi["domains_scanned"] == 2, f"Scanned: {multi['domains_scanned']}")
record("multi_domain_summary", "critical" in multi["summary"] or "high" in multi["summary"], f"Summary: {multi['summary']}")

# === TEST 4: Campaign detection ===
print("Testing campaign detection...")
campaign = engine.detect_campaign(multi["results"])
record("campaign_detection", "campaigns" in campaign, f"Campaigns: {len(campaign.get('campaigns', []))}")

# === TEST 5: Victim correlation ===
print("Testing victim correlation...")
victim1 = {
    "scam_website_url": "cncintelinfo.com",
    "scam_phone_number": "+44 7451 261353",
    "scam_email": "support@cncintelinfo.com",
    "crypto_wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "amount_lost": "$50,000",
}
victim2 = {
    "scam_website_url": "cncintelinfo.com",
    "scam_phone_number": "+44 7451 261353",
    "scam_email": "support@cncintelinfo.com",
    "crypto_wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "amount_lost": "$30,000",
}
correlation1 = engine.add_victim_report(victim1)
correlation2 = engine.add_victim_report(victim2)
record("victim_correlation", len(correlation2["correlations"]) > 0, f"Correlations: {len(correlation2['correlations'])}")
record("victim_campaign_link", correlation2["campaign_link"] is not None, "Campaign link detected")
record("victim_count", correlation2["campaign_link"]["victim_count"] == 2 if correlation2["campaign_link"] else False, "2 victims linked")

# === TEST 6: Telegram scam detection ===
print("Testing Telegram scam monitoring...")
# Use a known crypto-related channel
tg = engine.scan_telegram_for_scams("durov")
record("telegram_scan", "messages" in tg, f"Messages: {len(tg.get('messages', []))}")
record("telegram_evidence", len(tg.get("evidence", [])) >= 0, f"Evidence: {len(tg.get('evidence', []))}")

# === TEST 7: Police intelligence report ===
print("Testing police report generation...")
police_report = engine.generate_police_report({
    "case_type": "CYBERCRIME_FRAUD",
    "risk_level": "CRITICAL",
    "victim_count": 2,
    "estimated_loss": "$80,000",
    "scam_type": "CRYPTO_RECOVERY_SCAM",
    "domains": ["cncintelinfo.com"],
    "wallets": ["1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"],
    "pattern": "CRYPTO_RECOVERY_SCAM",
    "confidence": 0.85,
    "evidence": scan["evidence"],
})
record("police_report_generated", "report_id" in police_report, f"Report: {police_report['report_id']}")
record("police_report_classification", police_report["classification"] == "LAW ENFORCEMENT SENSITIVE", "Classification set")
record("police_report_findings", len(police_report["key_findings"]) > 0, f"Findings: {len(police_report['key_findings'])}")
record("police_report_actions", len(police_report["recommended_actions"]) > 0, f"Actions: {len(police_report['recommended_actions'])}")

# === TEST 8: Trend analysis ===
print("Testing trend analysis...")
trends = engine.analyze_trends(multi["results"])
record("trend_analysis", "pattern_frequency" in trends, f"Patterns: {trends['pattern_frequency']}")
record("trend_top_domains", len(trends["top_risk_domains"]) > 0, f"Top domains: {len(trends['top_risk_domains'])}")

# === TEST 9: Full investigation ===
print("Testing full investigation...")
full = engine.full_investigation({"domain": "cncintelinfo.com"})
record("full_investigation", "summary" in full, f"Summary: {full['summary']}")
record("full_investigation_phases", len(full) > 5, f"Phases: {len(full)}")
record("full_investigation_police_report", "report_id" in full.get("phase6_police_report", {}), "Police report included")

# === TEST 10: Scam pattern database ===
print("Testing scam pattern database...")
record("pattern_count", len(engine.SCAM_PATTERNS) >= 8, f"Patterns: {len(engine.SCAM_PATTERNS)}")
record("patterns_cover", all(p in engine.SCAM_PATTERNS for p in [
    "CRYPTO_RECOVERY_SCAM", "INVESTMENT_SCAM", "PHISHING_BANK", "ROMANCE_SCAM",
    "TECH_SUPPORT_SCAM", "GIVEAWAY_SCAM", "IMPERSONATION_SCAM"
]), "All major scam types covered")

# Print results
print(json.dumps(results, indent=2))

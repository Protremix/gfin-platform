import json, sys, importlib.util

spec = importlib.util.spec_from_file_location("scam_hunter_v2", "/gfin/packages/services/scam_hunter_v2.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

engine = mod.ScamHunterV2()

# Same victim report as CASE-SCAM-1787763540
victim_report = {
    "scam_website_url": "cncintelinfo.com",
    "scam_phone_number": "+44 7451 261353",
    "scam_email": "support@cncintelinfo.com",
    "crypto_wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "scam_social_media": {"telegram_channel": "durov"},
    "amount_lost": "$50,000",
    "date_of_scam": "2025-03-15",
    "description": "Victim was lured into fake crypto recovery scam. Website claimed to be a fund recovery service.",
}

investigation = engine.investigate(victim_report)

# Summary
print(json.dumps({
    "case_id": investigation["case_id"],
    "case_subjects": investigation["case_subjects"],
    "investigation_steps": [s["step"] for s in investigation["investigation_steps"]],
    "evidence_count": len(investigation["evidence_table"]),
    "evidence_by_grade": {
        "A": len([e for e in investigation["evidence_table"] if "A —" in e.get("grade","")]),
        "B": len([e for e in investigation["evidence_table"] if "B —" in e.get("grade","")]),
        "C": len([e for e in investigation["evidence_table"] if "C —" in e.get("grade","")]),
        "D": len([e for e in investigation["evidence_table"] if "D —" in e.get("grade","")]),
        "E": len([e for e in investigation["evidence_table"] if "E —" in e.get("grade","")]),
    },
    "rejected_count": len(investigation["rejected_findings"]),
    "rejected_categories": list(set(r["category"] for r in investigation["rejected_findings"])),
    "false_positive_test": investigation["false_positive_test"],
    "telegram_quality": {
        "found": investigation["telegram_quality"].get("messages_found", 0),
        "qualified": investigation["telegram_quality"].get("messages_qualified", 0),
        "rejected": investigation["telegram_quality"].get("messages_rejected", 0),
    },
    "crypto_attribution": {
        "on_chain_facts": len(investigation["crypto_attribution"].get("on_chain_facts", [])),
        "transactions": len(investigation["crypto_attribution"].get("transactions", [])),
        "counterparties": len(investigation["crypto_attribution"].get("counterparties", [])),
        "inferences": len(investigation["crypto_attribution"].get("inferences", [])),
        "identity": investigation["crypto_attribution"].get("identity", "")[:200],
    },
    "contradictions": len(investigation["contradictions"]),
    "risk_assessment": investigation["risk_assessment"],
    "recovery_actions": len(investigation["recovery_actions"]),
    "unknowns": len(investigation["unknowns"]),
    "next_lawful_steps": len(investigation["next_lawful_steps"]),
}, indent=2))

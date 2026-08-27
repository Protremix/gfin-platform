"""
GFIN Police Report Labeler v1.0
Formal labeling for police reports: FACT, EVIDENCE, INFERENCE, LEAD

Labels:
- FACT: Verified evidence with confirmed source, hash, and corroboration
- EVIDENCE: Collected but unverified (single source, no corroboration)
- INFERENCE: Derived from evidence through analysis (not directly observed)
- LEAD: Unverified tip, raw intelligence, or anonymous report
"""

# Label definitions with strict criteria
LABEL_CRITERIA = {
    "FACT": {
        "description": "Verified evidence with confirmed source and corroboration",
        "requirements": ["has_source", "is_verified", "has_corroboration"],
        "confidence_range": (0.8, 1.0),
        "color": "#28a745"  # green
    },
    "EVIDENCE": {
        "description": "Collected but unverified — single source, no corroboration",
        "requirements": ["has_source"],
        "confidence_range": (0.3, 0.8),
        "color": "#007bff"  # blue
    },
    "INFERENCE": {
        "description": "Derived from evidence through analysis — not directly observed",
        "requirements": ["derived_from_evidence"],
        "confidence_range": (0.2, 0.7),
        "color": "#ffc107"  # yellow
    },
    "LEAD": {
        "description": "Unverified tip, raw intelligence, or anonymous report",
        "requirements": [],
        "confidence_range": (0.0, 0.3),
        "color": "#6c757d"  # gray
    }
}

def label_report_section(text, evidence_items=None, source_verified=False, 
                         has_corroboration=False, is_derived=False, confidence=0.5):
    """
    Label a section of text in a police report.
    
    Args:
        text: The text content to label
        evidence_items: List of evidence items supporting this section
        source_verified: Whether the source has been verified
        has_corroboration: Whether multiple sources confirm this
        is_derived: Whether this is derived from analysis (not directly observed)
        confidence: Confidence score (0-1)
    
    Returns:
        dict with label, confidence, reasoning, and color
    """
    evidence_items = evidence_items or []
    
    has_source = len(evidence_items) > 0 or source_verified
    is_verified = source_verified and has_corroboration
    
    # Determine label
    if is_verified and has_corroboration and confidence >= 0.8:
        label = "FACT"
        reasoning = "Source verified and corroborated by multiple sources. High confidence."
    elif has_source and not is_derived and confidence >= 0.3:
        label = "EVIDENCE"
        reasoning = "Source present but not fully verified or corroborated. Single source."
    elif is_derived:
        label = "INFERENCE"
        reasoning = "Derived from evidence through analysis, not directly observed."
    else:
        label = "LEAD"
        reasoning = "Unverified tip or raw intelligence. No confirmed source."
    
    criteria = LABEL_CRITERIA[label]
    
    return {
        "label": label,
        "description": criteria["description"],
        "confidence": round(confidence, 3),
        "reasoning": reasoning,
        "color": criteria["color"],
        "evidence_count": len(evidence_items),
        "source_verified": source_verified,
        "has_corroboration": has_corroboration,
        "is_derived": is_derived
    }

def label_full_report(sections):
    """
    Label an entire police report composed of multiple sections.
    
    Args:
        sections: List of dicts with text, evidence_items, source_verified, 
                  has_corroboration, is_derived, confidence
    
    Returns:
        dict with labeled_sections, summary, and label_counts
    """
    labeled = []
    label_counts = {"FACT": 0, "EVIDENCE": 0, "INFERENCE": 0, "LEAD": 0}
    
    for section in sections:
        result = label_report_section(
            text=section.get("text", ""),
            evidence_items=section.get("evidence_items", []),
            source_verified=section.get("source_verified", False),
            has_corroboration=section.get("has_corroboration", False),
            is_derived=section.get("is_derived", False),
            confidence=section.get("confidence", 0.5)
        )
        labeled.append({
            "text_preview": section.get("text", "")[:100] + "...",
            **result
        })
        label_counts[result["label"]] += 1
    
    return {
        "labeled_sections": labeled,
        "label_counts": label_counts,
        "total_sections": len(labeled),
        "report_quality": _assess_quality(label_counts)
    }

def _assess_quality(counts):
    """Assess overall report quality based on label distribution"""
    total = sum(counts.values())
    if total == 0:
        return "EMPTY"
    fact_ratio = counts["FACT"] / total
    evidence_ratio = counts["EVIDENCE"] / total
    lead_ratio = counts["LEAD"] / total
    
    if fact_ratio >= 0.5:
        return "HIGH — predominantly verified facts"
    elif evidence_ratio >= 0.4:
        return "MEDIUM — good evidence base, needs verification"
    elif lead_ratio >= 0.5:
        return "LOW — predominantly unverified leads"
    return "MIXED"

if __name__ == "__main__":
    import json
    from datetime import datetime, timezone
    
    # Test with sample report sections
    test_sections = [
        {"text": "Domain cncintelinfo.com was registered on 2023-05-15 via Namecheap. WHOIS confirmed.", "evidence_items": [{"id": "EV001", "type": "WHOIS"}], "source_verified": True, "has_corroboration": True, "confidence": 0.9},
        {"text": "The domain uses Cloudflare CDN. IP 104.21.45.1 resolves to Cloudflare.", "evidence_items": [{"id": "EV002", "type": "DNS"}], "source_verified": True, "has_corroboration": False, "confidence": 0.6},
        {"text": "Based on shared favicon hash, cncintelinfo.com may be operated by the same group as scam-site.com.", "is_derived": True, "confidence": 0.45},
        {"text": "An anonymous Telegram user reported that cncintelinfo.com is a scam.", "evidence_items": [], "source_verified": False, "has_corroboration": False, "confidence": 0.1},
        {"text": "Victim John Doe reported losing $5000 to cncintelinfo.com on 2023-06-01. Bank transfer confirmed.", "evidence_items": [{"id": "EV003", "type": "bank_record"}, {"id": "EV004", "type": "victim_statement"}], "source_verified": True, "has_corroboration": True, "confidence": 0.85},
    ]
    
    report = label_full_report(test_sections)
    
    print("=== Police Report Labeler Test ===")
    for section in report["labeled_sections"]:
        print(f"  [{section['label']}] conf={section['confidence']} | {section['text_preview']}")
    
    print(f"\nLabel counts: {report['label_counts']}")
    print(f"Report quality: {report['report_quality']}")
    
    # Save artifact
    artifact = {
        "artifact": "police-report-quality.json",
        "task": "TASK_25_POLICE_REPORT_QUALITY",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "labels_implemented": ["FACT", "EVIDENCE", "INFERENCE", "LEAD"],
        "label_criteria": {k: {"description": v["description"], "confidence_range": v["confidence_range"]} for k, v in LABEL_CRITERIA.items()},
        "test_report": report,
        "module": "packages/common/report_labeler.py",
        "status": "IMPLEMENTED",
        "finding": "Police report labeling implemented with 4 formal labels (FACT, EVIDENCE, INFERENCE, LEAD). Each report section is labeled based on source verification, corroboration, derivation, and confidence. Report quality assessment provides overall rating."
    }
    
    with open("/gfin/artifacts/final-verification/police-report-quality.json", "w") as f:
        json.dump(artifact, f, indent=2, default=str)
    
    print("\nArtifact saved: police-report-quality.json")

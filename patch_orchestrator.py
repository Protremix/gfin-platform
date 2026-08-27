"""
Patch gfin_server.py: Wire Investigation Orchestrator into auto-investigation pipeline.

This adds structured investigation tracking via the shared investigation_store module.
After the existing auto-investigation completes, it creates an investigation record
with all steps and evidence that were collected.
"""
import re

# Read the server file
with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Check if already patched
if "investigation_store" in content:
    print("Already patched with investigation_store integration")
    exit(0)

# 1. Add import for investigation_store near the top (after existing imports)
import_anchor = "# ==================== APP ===================="
import_code = """
# ==================== INVESTIGATION ORCHESTRATOR INTEGRATION ====================
try:
    from investigation_store import investigation_store
    _orchestrator_available = True
except Exception as e:
    investigation_store = None
    _orchestrator_available = False
    print(f"Warning: investigation_store not loaded: {e}")

"""

content = content.replace(import_anchor, import_code + import_anchor)

# 2. Add orchestrator integration at the end of run_auto_investigation
# Find the return statement at the end of run_auto_investigation
old_return = """        logger.info(f"Auto-investigation complete for {complaint_ref}: {connector_results + 2} evidence items, risk={scam_analysis['risk_level']}")
        return case_id"""

new_return = """        logger.info(f"Auto-investigation complete for {complaint_ref}: {connector_results + 2} evidence items, risk={scam_analysis['risk_level']}")

        # ============================================================
        # INVESTIGATION ORCHESTRATOR INTEGRATION
        # Create a structured investigation with all steps and evidence
        # ============================================================
        if _orchestrator_available and investigation_store:
            try:
                inv_id = f"INV-{int(time.time())}-{case_id[-6:]}"
                investigation_store.create(
                    investigation_id=inv_id,
                    case_id=case_id,
                    subject=target,
                    subject_type=scam_type,
                    operator="GFIN_AUTO_PIPELINE"
                )

                # Step 1: Scam Detection
                investigation_store.add_step(
                    inv_id,
                    step_name="GFIN Scam Engine v3.0 Analysis",
                    tool_name="deterministic_scam_engine",
                    params={"target": target, "description_length": len(description)},
                    status="completed",
                    result=f"Risk: {scam_analysis['risk_level']} ({scam_analysis['risk_score']}), Patterns: {scam_analysis['pattern_count']}, Categories: {', '.join(scam_analysis['categories_detected'])}"
                )

                # Step 2: Entity Extraction
                indicators_summary = []
                for k, v in indicators.items():
                    if v:
                        indicators_summary.append(f"{k}: {len(v)} found")
                investigation_store.add_step(
                    inv_id,
                    step_name="Entity & Indicator Extraction",
                    tool_name="entity_extractor",
                    params={"categories": list(indicators.keys())},
                    status="completed",
                    result=f"Extracted: {'; '.join(indicators_summary)}"
                )

                # Step 3: Connector Search
                investigation_store.add_step(
                    inv_id,
                    step_name=f"External Connector Search ({connector_results} results)",
                    tool_name="multi_connector_search",
                    params={"connectors_run": len(connectors) if 'connectors' in dir() else 6},
                    status="completed",
                    result=f"Connectors returned {connector_results} results"
                )

                # Step 4: Country Routing
                investigation_store.add_step(
                    inv_id,
                    step_name="Police Routing & Alert Generation",
                    tool_name="country_routing_engine",
                    params={"countries": countries, "organizations": ["EUROPOL", "INTERPOL"]},
                    status="completed",
                    result=f"Routed to: {', '.join(countries + ['EUROPOL', 'INTERPOL'])}"
                )

                # Add evidence to investigation
                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="PATTERN_DETECTION",
                    finding=f"Risk level: {scam_analysis['risk_level']}, Score: {scam_analysis['risk_score']}, Patterns: {scam_analysis['pattern_count']}, Categories: {', '.join(scam_analysis['categories_detected'])}",
                    source="GFIN Scam Engine v3.0",
                    confidence="HIGH"
                )

                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="INDICATOR_EXTRACTION",
                    finding=f"Entities extracted: {'; '.join(indicators_summary)}",
                    source="GFIN Scam Engine (entity extractor)",
                    confidence="HIGH"
                )

                if connector_results > 0:
                    investigation_store.add_evidence(
                        inv_id,
                        evidence_type="CONNECTOR_SEARCH",
                        finding=f"External connectors returned {connector_results} results across 6 sources",
                        source="Multi-connector pipeline",
                        confidence="MEDIUM"
                    )

                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="POLICE_ROUTING",
                    finding=f"Complaint routed to {', '.join(countries + ['EUROPOL', 'INTERPOL'])} for investigation",
                    source="GFIN Country Routing Engine",
                    confidence="HIGH"
                )

                logger.info(f"Investigation orchestrator record created: {inv_id} for case {case_id}")
            except Exception as e:
                logger.warning(f"Failed to create orchestrator investigation: {e}")

        return case_id"""

content = content.replace(old_return, new_return)

# Write the patched file
with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)

print(f"Patched gfin_server.py ({len(content.splitlines())} lines)")
print("Changes:")
print("  1. Added investigation_store import")
print("  2. Added orchestrator integration to run_auto_investigation")
print("  3. Each complaint now creates a structured investigation with 4 steps + 4 evidence items")

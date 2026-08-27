#!/usr/bin/env python3
"""Add API endpoints for PyOD anomaly detection, MISP integration, and MIDAS graph anomaly detection"""

with open("/gfin/gfin_server.py", "r") as f:
    code = f.read()

# Add imports
import_section = "import os"
if "from gfin_anomaly_detector" not in code:
    code = code.replace(import_section, 
        "from gfin_anomaly_detector import anomaly_detector\nfrom gfin_misp_integration import misp_integration\nfrom gfin_midas import midas_pipeline\n" + import_section, 1)

# Add API endpoints before the main block
api_code = '''
# ============================================================
# ANOMALY DETECTION API (PyOD-powered)
# ============================================================

@app.get("/api/anomaly/cases")
async def detect_anomalous_cases(request: Request):
    """Detect anomalous cases using PyOD (Isolation Forest + KNN ensemble)"""
    payload = await auth_police(request)
    results = await anomaly_detector.detect_anomalous_cases(db_pool)
    return results

@app.get("/api/anomaly/wallets")
async def detect_anomalous_wallets(request: Request):
    """Detect anomalous wallet transaction patterns"""
    payload = await auth_police(request)
    results = await anomaly_detector.detect_wallet_anomalies(db_pool)
    return results

@app.get("/api/anomaly/status")
async def anomaly_status():
    """Get anomaly detection engine status"""
    return {
        "engine": "PyOD",
        "algorithms": ["Isolation Forest", "KNN"],
        "status": "operational"
    }

# ============================================================
# MISP THREAT INTELLIGENCE SHARING API
# ============================================================

@app.get("/api/misp/status")
async def misp_status():
    """Get MISP integration status"""
    return misp_integration.get_status()

@app.post("/api/misp/export-stix/{case_id}")
async def export_stix(case_id: str, request: Request):
    """Export a GFIN case as STIX 2.1 bundle for inter-agency sharing"""
    payload = await auth_police(request)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    
    case = dict(row)
    # Parse JSON fields
    import json as _json
    for field in ["scam_patterns", "scam_indicators", "affected_countries",
                  "financial_indicators", "digital_identifiers", "evidence_chain",
                  "attribution_data", "risk_assessment", "action_plan"]:
        if isinstance(case.get(field), str):
            try:
                case[field] = _json.loads(case[field])
            except:
                case[field] = []
    
    stix_bundle = misp_integration.export_stix(case)
    return stix_bundle

@app.post("/api/misp/share/{case_id}")
async def share_to_misp(case_id: str, request: Request):
    """Push a GFIN case to a configured MISP instance"""
    payload = await auth_police(request)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    
    case = dict(row)
    import json as _json
    for field in ["scam_patterns", "scam_indicators", "affected_countries",
                  "financial_indicators", "digital_identifiers", "evidence_chain"]:
        if isinstance(case.get(field), str):
            try:
                case[field] = _json.loads(case[field])
            except:
                case[field] = []
    
    result = await misp_integration.share_case_to_misp(case)
    return result

# ============================================================
# MIDAS REAL-TIME GRAPH ANOMALY DETECTION API
# ============================================================

@app.get("/api/midas/status")
async def midas_status():
    """Get MIDAS pipeline status"""
    return midas_pipeline.get_status()

@app.post("/api/midas/process/telegram")
async def midas_process_telegram(request: Request):
    """Process telegram intelligence through MIDAS for anomaly detection"""
    payload = await auth_police(request)
    results = await midas_pipeline.stream_telegram_intelligence(db_pool)
    return results

@app.post("/api/midas/process/evidence")
async def midas_process_evidence(request: Request):
    """Process case evidence chains through MIDAS"""
    payload = await auth_police(request)
    results = await midas_pipeline.stream_case_evidence(db_pool)
    return results

@app.post("/api/midas/edge")
async def midas_add_edge(request: Request):
    """Manually add an edge to MIDAS for real-time scoring"""
    payload = await auth_police(request)
    body = await request.json()
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        raise HTTPException(400, "src and dst required")
    result = midas_pipeline.midas.add_edge(src, dst)
    return result

@app.get("/api/midas/anomalies")
async def midas_anomalies(request: Request):
    """Get top anomalies detected by MIDAS"""
    payload = await auth_police(request)
    stats = midas_pipeline.midas.get_stats()
    return {"top_anomalies": stats["top_anomalies"], "stats": stats}

'''

# Insert before if __name__
if "if __name__" in code:
    code = code.replace("if __name__", api_code + "\nif __name__", 1)
    print("Added API endpoints")
else:
    print("Could not find insertion point")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(code)
print("Server code updated with 11 new API endpoints")

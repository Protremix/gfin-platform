#!/usr/bin/env python3
"""Add OSINT engine API endpoints to gfin_server.py"""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

osint_endpoints = '''

# ============================================================
# OSINT ENGINE API — GitHub Open-Source Intelligence Integration
# ============================================================

from osint_engine import (
    run_spiderfoot_scan, run_dnstwist_scan, run_shodan_lookup,
    run_wafw00f_check, run_dnsrecon, run_whois_lookup,
    run_full_osint_scan, AVAILABLE_ENGINES
)

@app.get("/api/osint/engines")
async def list_osint_engines():
    """List all available OSINT engines."""
    return {"total": len(AVAILABLE_ENGINES), "engines": AVAILABLE_ENGINES}

@app.post("/api/osint/spiderfoot")
async def spiderfoot_scan(target: str = Body(..., embed=True), 
    modules: List[str] = Body(default=None, embed=True)):
    """Run SpiderFoot OSINT scan (200+ modules)."""
    return await run_spiderfoot_scan(target, modules)

@app.post("/api/osint/dnstwist")
async def dnstwist_scan(domain: str = Body(..., embed=True)):
    """Run DNSTwist typo-squatting detection."""
    return await run_dnstwist_scan(domain)

@app.post("/api/osint/shodan")
async def shodan_lookup(ip: str = Body(..., embed=True)):
    """Look up IP in Shodan (ports, services, vulnerabilities)."""
    return await run_shodan_lookup(ip)

@app.post("/api/osint/wafw00f")
async def wafw00f_check(domain: str = Body(..., embed=True)):
    """Detect WAF protection on a website."""
    return await run_wafw00f_check(domain)

@app.post("/api/osint/dnsrecon")
async def dnsrecon_scan(domain: str = Body(..., embed=True)):
    """Run DNS enumeration on a domain."""
    return await run_dnsrecon(domain)

@app.post("/api/osint/whois")
async def whois_lookup(domain: str = Body(..., embed=True)):
    """Full WHOIS lookup with privacy detection."""
    return await run_whois_lookup(domain)

@app.post("/api/osint/full")
async def full_osint_scan(target: str = Body(..., embed=True),
    target_type: str = Body("domain", embed=True)):
    """Run ALL OSINT engines in parallel — full intelligence scan."""
    return await run_full_osint_scan(target, target_type)

@app.post("/api/osint/hunt")
async def osint_hunt(request: Request, target: str = Body(..., embed=True)):
    """Run full OSINT hunt + save results to case evidence. Requires police auth."""
    payload = await auth_police(request)
    officer_name = payload.get("agency", "SYSTEM")
    
    # Run full scan
    results = await run_full_osint_scan(target, "domain")
    
    # Create case
    conn = await asyncpg.connect(**DB_CONFIG)
    case_id = f"GFIN-OSINT-{int(time.time())}"
    
    await conn.execute(
        "INSERT INTO cases (case_id, target, target_type, trigger, summary, status) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, target, "domain", "OSINT_HUNT", results.get("summary", f"OSINT hunt of {target}"),
        "INVESTIGATING"
    )
    
    # Save each engine result as evidence
    for engine_name, engine_data in results.get("engines", {}).items():
        findings = engine_data.get("findings", [])
        if findings:
            finding_text = json.dumps(findings)[:500]
            evidence_id = f"EVID-{int(time.time()*1000)}-{engine_name}"
            await conn.execute(
                "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                case_id, evidence_id, "OSINT_" + engine_name.upper(),
                finding_text, engine_name.upper(), "AUTOMATED_OSINT",
                results.get("confidence", "MEDIUM"), officer_name
            )
    
    # Save correlations as evidence
    for corr in results.get("correlations", []):
        evidence_id = f"EVID-{int(time.time()*1000)}-CORR"
        await conn.execute(
            "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            case_id, evidence_id, "INTELLIGENCE_CORRELATION",
            "[" + corr["severity"] + "] " + corr["description"],
            "GFIN_CORRELATION_ENGINE", "CORRELATION", "HIGH", officer_name
        )
    
    await conn.close()
    
    results["case_id"] = case_id
    return results

'''

insert_marker = "# ============================================================\n# CASE COLLABORATION API"
if insert_marker not in content:
    # Fallback: add at end
    content = content + osint_endpoints
else:
    content = content.replace(insert_marker, osint_endpoints + "\n" + insert_marker)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("Added 8 OSINT engine API endpoints")

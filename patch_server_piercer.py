#!/usr/bin/env python3
"""Patch gfin_server.py to add proxy piercing API endpoints."""

with open("/gfin/gfin_server.py", "r") as f:
    content = f.read()

# Add import at the top (after other imports)
import_marker = "import investigation_lifecycle"
if "from proxy_piercer import ProxyPiercer" not in content:
    content = content.replace(
        import_marker,
        import_marker + "\nfrom proxy_piercer import ProxyPiercer"
    )

# Add API endpoints before the last "# ===" marker or at the end of the file
# Find a good insertion point — after the lifecycle routes
api_endpoints = '''

# ==================== PROXY & PRIVACY PIERCING ====================

@app.get("/api/piercer/investigate/{domain}")
async def piercer_investigate(domain: str):
    """Run full proxy/privacy piercing investigation on a domain.
    Detects WHOIS privacy, CDN proxies, finds real origin IP, traces physical location.
    """
    piercer = ProxyPiercer()
    result = await piercer.investigate(domain)
    return result

@app.post("/api/piercer/investigate-case/{case_id}")
async def piercer_investigate_case(case_id: str, request: Request):
    """Run proxy piercing on the primary domain of a case.
    Saves all findings as evidence and entities in the case lifecycle.
    """
    import asyncpg, os
    body = await request.json() if request.headers.get("content-type") else {}
    officer_name = body.get("officer_name", "SYSTEM")
    officer_id = body.get("officer_id")
    
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        database="gfin", user="gfin",
        password=os.environ.get("DB_PASSWORD", "GfinSecure2026!")
    )
    try:
        # Get the case target domain
        case = await conn.fetchrow("SELECT case_id, target, target_type FROM cases WHERE case_id = $1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        
        domain = case["target"]
        if case["target_type"] != "DOMAIN":
            # Try to extract domain from the target
            import re
            domain_match = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})', domain)
            if domain_match:
                domain = domain_match.group(1)
            else:
                raise HTTPException(400, "Case target is not a domain")
        
        # Run the piercer
        piercer = ProxyPiercer()
        result = await piercer.investigate(domain, db_conn=conn)
        
        # Save evidence to the case
        evidence_count = 0
        for ev in result.get("evidence", []):
            count = await conn.fetchval("SELECT COUNT(*) FROM evidence WHERE case_id = $1", case_id)
            evidence_id = f"E-{count + 1:03d}"
            
            await conn.execute(
                """INSERT INTO evidence 
                   (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer, added_by_officer_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                case_id, evidence_id,
                "ACTIVE_INVESTIGATION",
                ev["finding"],
                f"ProxyPiercer/{ev['method']}",
                "AUTO",
                ev["confidence"],
                officer_name, officer_id
            )
            evidence_count += 1
        
        # Save origin IP as entity
        if result.get("origin_ip"):
            existing = await conn.fetchrow(
                "SELECT id FROM case_entities WHERE case_id = $1 AND entity_type = 'IP' AND entity_value = $2",
                case_id, result["origin_ip"]
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'IP', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)""",
                    case_id, result["origin_ip"],
                    json.dumps({"method": "origin_discovery", "cdn_provider": result.get("cdn_provider"), "physical_location": result.get("physical_location")}),
                    officer_name
                )
        
        # Save physical location as entity
        if result.get("physical_location"):
            loc = result["physical_location"]
            loc_str = f"{loc.get('city', '?')}, {loc.get('country', '?')}"
            existing = await conn.fetchrow(
                "SELECT id FROM case_entities WHERE case_id = $1 AND entity_type = 'ADDRESS' AND entity_value = $2",
                case_id, loc_str
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'ADDRESS', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)""",
                    case_id, loc_str,
                    json.dumps({"lat": loc.get("lat"), "lon": loc.get("lon"), "city": loc.get("city"), "country": loc.get("country"), "timezone": loc.get("timezone")}),
                    officer_name
                )
        
        # Save real identity as entity if found
        if result.get("real_identity"):
            ident = result["real_identity"]
            if ident.get("email"):
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'EMAIL', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)
                       ON CONFLICT DO NOTHING""",
                    case_id, ident["email"],
                    json.dumps({"source": "historical_whois", "name": ident.get("name")}),
                    officer_name
                )
            if ident.get("name"):
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'PERSON', $2, $3::jsonb, 'PROXY_PIERCER', 'MEDIUM', 'SUSPECTED', $4)
                       ON CONFLICT DO NOTHING""",
                    case_id, ident["name"],
                    json.dumps({"source": "historical_whois", "email": ident.get("email")}),
                    officer_name
                )
        
        # Save shared cert domains as entities
        for shared_domain in result.get("correlations", []):
            if shared_domain.get("entity_type") in ["DOMAIN", "EMAIL", "PHONE"]:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, $2, $3, $4::jsonb, 'PROXY_PIERCER', 'MEDIUM', 'CORRELATED', $5)
                       ON CONFLICT DO NOTHING""",
                    case_id, shared_domain["entity_type"], shared_domain["entity_value"],
                    json.dumps({"correlated_case": shared_domain.get("source"), "evidence": shared_domain.get("evidence")}),
                    officer_name
                )
        
        # Add timeline event
        await conn.execute(
            """INSERT INTO case_timeline (case_id, event_type, event_title, event_description, event_metadata, officer_name)
               VALUES ($1, 'PROXY_PIERCING', $2, $3, $4::jsonb, $5)""",
            case_id,
            f"Proxy piercing completed for {domain}",
            result.get("summary", "")[:500],
            json.dumps({
                "cdn_detected": result.get("cdn_detected"),
                "privacy_detected": result.get("privacy_detected"),
                "origin_ip": result.get("origin_ip"),
                "confidence": result.get("confidence"),
                "evidence_count": evidence_count
            }),
            officer_name
        )
        
        return {
            "status": "ok",
            "domain": domain,
            "evidence_added": evidence_count,
            "result": result
        }
    finally:
        await conn.close()

@app.get("/api/piercer/quick/{domain}")
async def piercer_quick_check(domain: str):
    """Quick proxy/CDN check — returns just the detection results without full investigation."""
    piercer = ProxyPiercer()
    
    # Only run CDN detection and privacy check
    import socket
    ip_info = {}
    primary_ip = None
    try:
        addrs = socket.getaddrinfo(domain, None)
        primary_ip = addrs[0][4][0]
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{primary_ip}/json") as r:
                if r.status == 200:
                    ip_info = await r.json()
    except Exception:
        pass
    
    cdn_result = await piercer.detect_cdn(domain, ip_info)
    
    return {
        "domain": domain,
        "ip": primary_ip,
        "ip_info": ip_info,
        "is_cdn_protected": cdn_result["is_cdn_protected"],
        "cdn_provider": cdn_result["cdn_provider"],
        "cdn_indicators": cdn_result["cdn_indicators"],
        "bypass_available": cdn_result.get("bypass_methods", []),
    }
'''

# Insert before the health check endpoint
health_marker = "@app.get(\"/health\""
if "/api/piercer/investigate" not in content:
    content = content.replace(health_marker, api_endpoints + "\n" + health_marker)

with open("/gfin/gfin_server.py", "w") as f:
    f.write(content)
print("API endpoints added — proxy piercer integrated into GFIN server")

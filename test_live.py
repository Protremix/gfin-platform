import sys, json
sys.path.insert(0, "/gfin")
from autonomous_hunter_v2 import investigate_domain, has_strong_evidence
from hunter_v3_advanced import run_advanced_intelligence, query_related_domains

domains_to_test = [
    ("www.roblox.com.am", "OPENPHISH"),
]

for domain, source in domains_to_test:
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"INVESTIGATING: {domain} (source: {source})")
    print(f"{sep}")
    
    inv = investigate_domain(domain, source)
    
    print(f"\n--- INVESTIGATION SUMMARY ---")
    print(f"Domain: {inv['domain']}")
    print(f"Evidence steps: {len(inv.get('evidence_chain', []))}")
    print(f"Digital identifiers: {len(inv.get('digital_identifiers', []))}")
    print(f"Confidence: {inv.get('confidence', 0)}")
    print(f"Scam patterns: {inv.get('scam_patterns', [])}")
    scam_types = [s.get("type") for s in inv.get("scam_indicators", []) if isinstance(s, dict)]
    print(f"Scam indicator types: {scam_types}")
    print(f"Physical locations: {len(inv.get('physical_locations', []))}")
    print(f"Financial indicators: {len(inv.get('financial_indicators', []))}")
    
    print(f"\n--- EVIDENCE PHASES ---")
    for e in inv.get("evidence_chain", []):
        phase = e.get("phase", "?")
        finding = e.get("finding", "")[:120]
        print(f"  [{phase}] {finding}")
    
    print(f"\n--- ADVANCED INTELLIGENCE ---")
    advanced = run_advanced_intelligence(inv)
    
    if advanced.get("privacy_guard"):
        print(f"  Privacy guard: {advanced['privacy_guard']['privacy_service']}")
    if advanced.get("subdomains", {}).get("total_count", 0) > 0:
        subs = advanced["subdomains"]
        print(f"  Subdomains: {subs['total_count']} found, {len(subs.get('suspicious_subdomains', []))} suspicious")
        for s in subs.get("suspicious_subdomains", [])[:3]:
            print(f"    SUSPICIOUS: {s['subdomain']} ({s['prefix']})")
    if advanced.get("wallet_intelligence"):
        for w in advanced["wallet_intelligence"]:
            addr = w["address"][:20]
            print(f"  Wallet: {w['type']} {addr}... balance={w.get('balance', '?')} risk={w.get('risk_level', '?')}")
    if advanced.get("takedown_report"):
        r = advanced["takedown_report"]
        print(f"  Takedown report: {r['report_id']}")
        print(f"    Hosting: {r['hosting_provider']}")
        print(f"    Registrar: {r['registrar']}")
        print(f"    CDN: {r['cdn_provider']}")
        print(f"    Classification: {r['classification']}")
    if advanced.get("neo4j_stored"):
        print(f"  Neo4j graph: STORED")
    else:
        print(f"  Neo4j graph: not stored")
    
    related = query_related_domains(domain)
    if related.get("related_domains"):
        print(f"  Related domains in graph: {len(related['related_domains'])}")
        for rd in related["related_domains"][:5]:
            print(f"    {rd['domain']} (shared: {rd['shared_infrastructure']})")
    
    gate = has_strong_evidence(inv)
    gate_status = "PASS" if gate else "FAIL"
    print(f"\n--- EVIDENCE GATE: {gate_status} ---")
    if gate:
        print(f"  => CASE WOULD BE CREATED")
    else:
        print(f"  => FLAGGED ONLY")
    
    print(f"\n--- IDENTIFIER TYPES ---")
    id_types = {}
    for d in inv.get("digital_identifiers", []):
        t = d.get("type", "UNKNOWN")
        id_types[t] = id_types.get(t, 0) + 1
    for t, c in sorted(id_types.items()):
        print(f"  {t}: {c}")

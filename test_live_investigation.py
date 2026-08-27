import sys, json
sys.path.insert(0, '/gfin')
from autonomous_hunter_v2 import investigate_domain, has_strong_evidence
from hunter_v3_advanced import run_advanced_intelligence, query_related_domains, store_investigation_in_neo4j

# Test with a known phishing domain from OpenPhish
domains_to_test = [
    ('welcomeio-ledger.typedream.app', 'OPENPHISH'),
    ('www.roblox.com.am', 'OPENPHISH'),
]

for domain, source in domains_to_test:
    print(f'\n"=" * 60')
    print(f'INVESTIGATING: {domain} (source: {source})')
    print(f'"=" * 60')
    
    inv = investigate_domain(domain, source)
    
    print(f'\n--- INVESTIGATION SUMMARY ---')
    print(f'Domain: {inv[domain]}')
    print(f'Evidence steps: {len(inv[evidence_chain])}')
    print(f'Digital identifiers: {len(inv[digital_identifiers])}')
    print(f'Confidence: {inv[confidence]}')
    print(f'Scam patterns: {inv.get(scam_patterns, [])}')
    print(f'Scam indicators: {[s.get(type) for s in inv.get(scam_indicators, []) if isinstance(s, dict)]}')
    print(f'Physical locations: {len(inv.get(physical_locations, []))}')
    print(f'Financial indicators: {len(inv.get(financial_indicators, []))}')
    
    # Show evidence phases
    print(f'\n--- EVIDENCE PHASES ---')
    for e in inv.get(evidence_chain, []):
        print(f'  [{e.get(phase, ?)}] {e.get(finding, )[:120]}')
    
    # Run advanced intelligence
    print(f'\n--- ADVANCED INTELLIGENCE ---')
    advanced = run_advanced_intelligence(inv)
    
    if advanced.get(privacy_guard):
        print(f'  Privacy guard: {advanced[privacy_guard][privacy_service]}')
    if advanced.get(subdomains, {}).get(total_count, 0) > 0:
        print(f'  Subdomains: {advanced[subdomains][total_count]} found, {len(advanced[subdomains][suspicious_subdomains])} suspicious')
        for s in advanced[subdomains][suspicious_subdomains][:3]:
            print(f'    SUSPICIOUS: {s[subdomain]} ({s[prefix]})')
    if advanced.get(wallet_intelligence):
        for w in advanced[wallet_intelligence]:
            print(f'  Wallet: {w[type]} {w[address][:20]}... balance={w.get(balance, ?)} risk={w.get(risk_level, ?)}')
    if advanced.get(takedown_report):
        r = advanced[takedown_report]
        print(f'  Takedown report: {r[report_id]}')
        print(f'    Hosting: {r[hosting_provider]}')
        print(f'    Registrar: {r[registrar]}')
        print(f'    CDN: {r[cdn_provider]}')
        print(f'    Classification: {r[classification]}')
    if advanced.get(neo4j_stored):
        print(f'  Neo4j graph: STORED')
    
    # Query Neo4j for related domains
    related = query_related_domains(domain)
    if related.get(related_domains):
        print(f'  Related domains in graph: {len(related[related_domains])}')
        for r in related[related_domains][:5]:
            print(f'    {r[domain]} (shared: {r[shared_infrastructure]})')
    
    # Evidence gate
    gate = has_strong_evidence(inv)
    print(f'\n--- EVIDENCE GATE: {PASS if gate else FAIL} ---')
    if gate:
        print(f'  => CASE WOULD BE CREATED')
    
    # Print identifier types
    print(f'\n--- IDENTIFIER TYPES ---')
    id_types = {}
    for d in inv.get(digital_identifiers, []):
        t = d.get(type, UNKNOWN)
        id_types[t] = id_types.get(t, 0) + 1
    for t, c in sorted(id_types.items()):
        print(f'  {t}: {c}')

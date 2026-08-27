import sys, json
sys.path.insert(0, '/gfin')
from hunter_v3_advanced import *

print('=== WHOIS PRIVACY GUARD ===')
rdap = {'entities': [{'vcardArray': [{}, [['fn', 'text', 'Withheld for Privacy']]], 'roles': ['registrant']}]}
result = detect_privacy_guard(rdap)
print(f'  Detected: {result["uses_privacy_guard"]}, Service: {result["privacy_service"]}')

print('\n=== SUBDOMAIN ENUMERATION ===')
subs = enumerate_subdomains('binance.com')
print(f'  Total subdomains: {subs["total_count"]}')
print(f'  Sample: {subs["subdomains"][:5]}')
print(f'  Suspicious: {len(subs["suspicious_subdomains"])}')
for s in subs['suspicious_subdomains'][:3]:
    print(f'    {s["subdomain"]} ({s["prefix"]})')

print('\n=== WALLET INTELLIGENCE ===')
btc = check_wallet_intelligence('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', 'BTC')
print(f'  BTC: balance={btc["balance"]}, txs={btc["tx_count"]}, risk={btc["risk_level"]}')
eth = check_wallet_intelligence('0x742d35Cc6634C0532925a3b844Bc454e4438f44e', 'ETH')
print(f'  ETH: balance={eth["balance"]}, txs={eth["tx_count"]}, risk={eth["risk_level"]}')

print('\n=== TAKEDOWN REPORT ===')
inv = {
    'domain': 'paypa1-login-secure.com',
    'source': 'PHISHING_DATABASE',
    'confidence': 0.75,
    'evidence_chain': [
        {'phase': 'DNS_RESOLUTION', 'finding': 'A records: 192.168.1.1', 'source': 'DNS'},
        {'phase': 'TYPO_SQUATTING', 'finding': 'DOMAIN IMPERSONATES paypal (homoglyph)', 'source': 'GFIN'},
    ],
    'digital_identifiers': [
        {'type': 'IP', 'value': '192.168.1.1', 'context': 'A record'},
        {'type': 'REGISTRAR', 'value': 'NameCheap', 'context': 'Registrar'},
        {'type': 'NS', 'value': 'dns1.cloudflare.com', 'context': 'Nameserver'},
    ],
    'physical_locations': [{'city': 'San Francisco', 'country': 'US', 'isp': 'Cloudflare, Inc.'}],
    'financial_indicators': [],
    'scam_patterns': ['PHISHING', 'BRAND_IMPERSONATION'],
    'scam_indicators': [{'risk_level': 'CRITICAL', 'risk_score': 85, 'categories': ['PHISHING']}],
    'affected_countries': ['US', 'GB', 'DE'],
}
report = generate_takedown_report(inv)
print(f'  Report ID: {report["report_id"]}')
print(f'  Hosting: {report["hosting_provider"]}')
print(f'  Registrar: {report["registrar"]}')
print(f'  CDN: {report["cdn_provider"]}')
print(f'  Classification: {report["classification"]}')

print('\n=== NEO4J GRAPH STORAGE ===')
inv2 = {
    'domain': 'test-scam-example.com',
    'source': 'TEST',
    'confidence': 0.8,
    'evidence_chain': [],
    'digital_identifiers': [
        {'type': 'IP', 'value': '1.2.3.4', 'context': 'test'},
        {'type': 'NS', 'value': 'ns1.test.com', 'context': 'test'},
        {'type': 'FAVICON_HASH', 'value': 'abc123', 'context': 'test'},
    ],
    'physical_locations': [{'isp': 'TestHost Inc.', 'country': 'US', 'asn': 'AS123'}],
    'financial_indicators': [],
    'scam_patterns': ['PHISHING'],
    'scam_indicators': [{'risk_level': 'HIGH', 'risk_score': 60, 'categories': ['PHISHING']}],
    'affected_countries': ['US'],
}
stored = store_investigation_in_neo4j(inv2, 'TEST-001')
print(f'  Stored in Neo4j: {stored}')
related = query_related_domains('test-scam-example.com')
print(f'  Related domains: {related["related_domains"]}')
print(f'  Total graph nodes: {related["total_graph_nodes"]}')

print('\n=== ALL TESTS PASSED ===')

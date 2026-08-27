import json, sys, importlib.util, time

sys.path.insert(0, '/gfin/packages/connectors')
spec_base = importlib.util.spec_from_file_location("base", "/gfin/packages/connectors/base.py")
base_module = importlib.util.module_from_spec(spec_base)
sys.modules["base"] = base_module
spec_base.loader.exec_module(base_module)

spec_exp = importlib.util.spec_from_file_location("expanded_connectors", "/gfin/packages/connectors/expanded_connectors.py")
exp_module = importlib.util.module_from_spec(spec_exp)
sys.modules["expanded_connectors"] = exp_module
spec_exp.loader.exec_module(exp_module)

results = {"tests": [], "passed": 0, "failed": 0}

def record(name, passed, details=""):
    results["tests"].append({"test": name, "passed": passed, "details": details[:200]})
    if passed: results["passed"] += 1
    else: results["failed"] += 1

ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

# LIVE TESTS (free, no auth)

# 1. SEC EDGAR — live test
conn = exp_module.SECEdgarConnector()
result = conn.query(company_name="Apple")
record("sec_edgar_live", result.success, f"Success: {result.success}")

# 2. ICIJ Offshore Leaks — live test
conn = exp_module.ICIJConnector()
result = conn.query(search_term="Gordons")
record("icij_live", result.success, f"Success: {result.success}, Data: {str(result.data)[:100]}")

# 3. GDELT — live test
conn = exp_module.GDELTConnector()
result = conn.query(search_term="fraud UK company")
record("gdelt_live", result.success, f"Articles: {result.data.get('articles_found',0) if isinstance(result.data, dict) else 'N/A'}")

# 4. Blockchair — live test
conn = exp_module.BlockchairConnector()
result = conn.query(address="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
record("blockchair_live", result.success, f"Success: {result.success}")

# 5. GitLab — live test
conn = exp_module.GitLabConnector()
result = conn.query(username="gitlab")
record("gitlab_live", result.success, f"Data type: {type(result.data).__name__}")

# 6. npm — live test
conn = exp_module.NpmConnector()
result = conn.query(package="express")
record("npm_live", result.success, f"Name: {result.data.get('name','') if isinstance(result.data, dict) else 'N/A'}")

# 7. PyPI — live test
conn = exp_module.PyPIConnector()
result = conn.query(package="requests")
record("pypi_live", result.success, f"Name: {result.data.get('info',{}).get('name','') if isinstance(result.data, dict) else 'N/A'}")

# 8. Crossref — live test
conn = exp_module.CrossrefConnector()
result = conn.query(search_term="fraud investigation")
record("crossref_live", result.success, f"Status: {result.success}")

# 9. OpenAlex — live test
conn = exp_module.OpenAlexConnector()
result = conn.query(search_term="financial fraud")
record("openalex_live", result.success, f"Success: {result.success}")

# 10. OFAC — live test (bulk CSV)
conn = exp_module.OFACConnector()
result = conn.query(search_term="Gordons")
record("ofac_live", result.success, f"Found in SDN: {result.data.get('found_in_sdn','N/A') if isinstance(result.data, dict) else 'N/A'}")

# AUTH-REQUIRED TESTS (should fail closed)

# 11. Shodan — auth test
conn = exp_module.ShodanConnector()
result = conn.query(ip="8.8.8.8")
record("shodan_auth", not result.success and "AUTH" in str(result.error), f"Correctly returned AUTH_REQUIRED")

# 12. Censys — auth test
conn = exp_module.CensysConnector()
result = conn.query(domain="example.com")
record("censys_auth", not result.success and "AUTH" in str(result.error), f"Correctly returned AUTH_REQUIRED")

# 13. Mapbox — auth test
conn = exp_module.MapboxConnector()
result = conn.query(address="London")
record("mapbox_auth", not result.success and "AUTH" in str(result.error), f"Correctly returned AUTH_REQUIRED")

# 14. DomainTools — auth test
conn = exp_module.DomainToolsConnector()
result = conn.query(domain="example.com")
record("domaintools_auth", not result.success and "AUTH" in str(result.error), f"Correctly returned AUTH_REQUIRED")

# SECURITY TESTS
for name in exp_module.EXPANDED_REGISTRY:
    conn_cls = exp_module.EXPANDED_REGISTRY[name]
    conn = conn_cls()
    if conn.credential_type != "NONE":
        # Test fail-closed
        result = conn.query(search_term="test", ip="1.1.1.1", domain="test.com", address="test", package="test", company_name="test")
        fail_closed = not result.success and ("AUTH" in str(result.error) or "AUTH" in str(result.authorization_status))
        record(f"security_fail_closed_{name}", fail_closed, "Fail-closed verified")

print(json.dumps(results, indent=2))

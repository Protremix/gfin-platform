"""
GFIN Expanded Connector Set v1.0
New connectors from the Global Provider/API Master Inventory
All follow the BaseConnector pipeline.
"""
import json, time, urllib.request, urllib.parse, ssl, sys
sys.path.insert(0, '/gfin/packages/connectors')
from base import BaseConnector, ConnectorResult

# SEC EDGAR — Free, no auth (rate limit 10 req/sec)
class SECEdgarConnector(BaseConnector):
    provider_id = "sec-edgar"
    provider = "SEC EDGAR"
    source_class = "CORPORATE"
    jurisdiction = "USA"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "10 req/sec"
    api_url = "https://data.sec.gov"
    documentation = "https://www.sec.gov/edgar/sec-api-documentation"
    license = "Public data"
    
    def query(self, company_name: str = "", cik: str = "", **kwargs) -> ConnectorResult:
        if cik:
            url = f"{self.api_url}/submissions/CIK{cik.zfill(10)}.json"
        else:
            # Search by company name
            url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={urllib.parse.quote(company_name)}&output=atom"
        headers = {"User-Agent": "GFIN Research contact@gfin.local"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# ICIJ Offshore Leaks — Free, no auth
class ICIJConnector(BaseConnector):
    provider_id = "icij-offshore"
    provider = "ICIJ Offshore Leaks Database"
    source_class = "OFFSHORE_BENEFICIAL_OWNERSHIP"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "Reasonable use"
    api_url = "https://offshoreleaks.icij.org"
    documentation = "https://offshoreleaks.icij.org/"
    license = "Free public access"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        # ICIJ provides a search API
        url = f"https://offshoreleaks.icij.org/api/1/search?q={urllib.parse.quote(search_term)}&type=entities"
        headers = {"User-Agent": "GFIN/1.0", "Accept": "application/json"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            # Fallback to web search URL
            url2 = f"https://offshoreleaks.icij.org/search?q={urllib.parse.quote(search_term)}"
            try:
                result = self._make_request(url2)
                if result.success:
                    text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                    has_results = search_term.lower() in text.lower() and "no results" not in text.lower()
                    result.data = {"has_results": has_results, "search_term": search_term, "method": "web_search"}
                return result
            except Exception as e2:
                return ConnectorResult(success=False, error=f"API: {e}, Web: {e2}", provider=self.provider, source_class=self.source_class)

# GDELT — Free, no auth
class GDELTConnector(BaseConnector):
    provider_id = "gdelt"
    provider = "GDELT (Global Database of Events, Language, and Tone)"
    source_class = "PUBLIC_DATA_NEWS"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "None documented"
    api_url = "https://api.gdeltproject.org/api/v2"
    documentation = "https://www.gdeltproject.org/"
    license = "Free (Open Access)"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/doc/doc?query={urllib.parse.quote(search_term)}&format=json&mode=ArtList&maxrecords=10"
        try:
            result = self._make_request(url)
            if result.success and isinstance(result.data, dict):
                articles = result.data.get("articles", [])
                result.data = {"articles_found": len(articles), "articles": articles[:5] if articles else [], "search_term": search_term}
                result.quality_score = 1.0 if articles else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# Shodan — API key required (free tier available)
class ShodanConnector(BaseConnector):
    provider_id = "shodan"
    provider = "Shodan"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "shodan_api_key"
    rate_limit = "Varies by plan (free: 1 req/sec)"
    api_url = "https://api.shodan.io"
    documentation = "https://developer.shodan.io/api"
    
    def query(self, ip: str = "", domain: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Shodan API key required (free tier at shodan.io)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        api_key = self.credentials["shodan_api_key"]
        if ip:
            url = f"{self.api_url}/shodan/host/{ip}?key={api_key}"
        else:
            url = f"{self.api_url}/dns/domain/{domain}?key={api_key}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# Censys — API key required (free tier)
class CensysConnector(BaseConnector):
    provider_id = "censys"
    provider = "Censys"
    source_class = "THREAT_INTERNET_INFRASTRUCTURE"
    auth_method = "API_KEY"
    credential_type = "censys_api_id"
    api_url = "https://search.censys.io/api/v2"
    documentation = "https://search.censys.io/api"
    
    def query(self, domain: str = "", ip: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Censys API credentials required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        return ConnectorResult(success=False, error="AUTHORIZATION_REQUIRED", provider=self.provider, source_class=self.source_class)

# Blockchair — Free, no auth (rate limited)
class BlockchairConnector(BaseConnector):
    provider_id = "blockchair"
    provider = "Blockchair"
    source_class = "BLOCKCHAIN_CRYPTO"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "30 req/min (free)"
    api_url = "https://api.blockchair.com"
    documentation = "https://blockchair.com/api"
    license = "Free tier available"
    
    def query(self, address: str = "", blockchain: str = "bitcoin", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/{blockchain}/dashboards/address/{address}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# GitLab — Free, no auth (rate limited)
class GitLabConnector(BaseConnector):
    provider_id = "gitlab"
    provider = "GitLab"
    source_class = "APP_SOFTWARE_ECOSYSTEM"
    auth_method = "NONE (optional token)"
    credential_type = "gitlab_token"
    rate_limit = "60 req/min without token"
    api_url = "https://gitlab.com/api/v4"
    documentation = "https://docs.gitlab.com/ee/api/"
    
    def query(self, username: str = "", project: str = "", **kwargs) -> ConnectorResult:
        if project:
            url = f"{self.api_url}/projects/{urllib.parse.quote(project, safe='')}"
        else:
            url = f"{self.api_url}/users?username={urllib.parse.quote(username)}"
        headers = {}
        if self._check_credential():
            headers["PRIVATE-TOKEN"] = self.credentials["gitlab_token"]
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# npm registry — Free, no auth
class NpmConnector(BaseConnector):
    provider_id = "npm"
    provider = "npm Registry"
    source_class = "APP_SOFTWARE_ECOSYSTEM"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://registry.npmjs.org"
    documentation = "https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md"
    
    def query(self, package: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/{urllib.parse.quote(package)}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# PyPI — Free, no auth
class PyPIConnector(BaseConnector):
    provider_id = "pypi"
    provider = "PyPI (Python Package Index)"
    source_class = "APP_SOFTWARE_ECOSYSTEM"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://pypi.org/pypi"
    documentation = "https://warehouse.pypa.io/api-reference/"
    
    def query(self, package: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/{urllib.parse.quote(package)}/json"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# Crossref — Free, no auth
class CrossrefConnector(BaseConnector):
    provider_id = "crossref"
    provider = "Crossref"
    source_class = "PUBLIC_DATA_NEWS"
    auth_method = "NONE (polite pool with email)"
    credential_type = "NONE"
    rate_limit = "50 req/sec (polite pool)"
    api_url = "https://api.crossref.org"
    documentation = "https://api.crossref.org"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/works?query={urllib.parse.quote(search_term)}&rows=10"
        headers = {"User-Agent": "GFIN/1.0 (mailto:research@gfin.local)"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# OpenAlex — Free, no auth
class OpenAlexConnector(BaseConnector):
    provider_id = "openalex"
    provider = "OpenAlex"
    source_class = "PUBLIC_DATA_NEWS"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "100K req/day"
    api_url = "https://api.openalex.org"
    documentation = "https://docs.openalex.org/"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/works?search={urllib.parse.quote(search_term)}&per-page=10"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# Mapbox — API key required (free tier)
class MapboxConnector(BaseConnector):
    provider_id = "mapbox"
    provider = "Mapbox"
    source_class = "GEOINT"
    auth_method = "API_KEY"
    credential_type = "mapbox_access_token"
    api_url = "https://api.mapbox.com"
    documentation = "https://docs.mapbox.com/api/"
    
    def query(self, address: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Mapbox access token required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        token = self.credentials["mapbox_access_token"]
        url = f"{self.api_url}/geocoding/v5/mapbox.places/{urllib.parse.quote(address)}.json?access_token={token}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# OFAC — Free, no auth (bulk data download)
class OFACConnector(BaseConnector):
    provider_id = "ofac"
    provider = "OFAC (US Treasury Sanctions)"
    source_class = "SANCTIONS_AML"
    jurisdiction = "USA"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://www.treasury.gov/resource-center/sanctions"
    documentation = "https://ofac.treasury.gov/"
    license = "Public data"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        # OFAC provides bulk data downloads (XML/CSV), not a search API
        # We can check the SDN list URL for reference
        url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
        try:
            result = self._make_request(url)
            if result.success:
                # Check if search_term appears in the SDN list
                text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                found = search_term.lower() in text.lower() if search_term else False
                result.data = {"search_term": search_term, "found_in_sdn": found, "note": "OFAC SDN list checked (bulk CSV)"}
                result.quality_score = 1.0 if found else 0.5
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# DomainTools — API key required
class DomainToolsConnector(BaseConnector):
    provider_id = "domaintools"
    provider = "DomainTools"
    source_class = "DNS_DOMAIN_CERTIFICATE"
    auth_method = "API_KEY"
    credential_type = "domaintools_api_key"
    api_url = "https://api.domaintools.com"
    documentation = "https://www.domaintools.com/resources/api-documentation/"
    
    def query(self, domain: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — DomainTools API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/v1/{domain}/whois/"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# Register new connectors
EXPANDED_REGISTRY = {
    "sec_edgar": SECEdgarConnector,
    "icij": ICIJConnector,
    "gdelt": GDELTConnector,
    "shodan": ShodanConnector,
    "censys": CensysConnector,
    "blockchair": BlockchairConnector,
    "gitlab": GitLabConnector,
    "npm": NpmConnector,
    "pypi": PyPIConnector,
    "crossref": CrossrefConnector,
    "openalex": OpenAlexConnector,
    "mapbox": MapboxConnector,
    "ofac": OFACConnector,
    "domaintools": DomainToolsConnector,
}

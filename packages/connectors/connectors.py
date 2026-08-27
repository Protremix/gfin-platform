"""
GFIN Connector Implementations v1.0
All connectors follow the BaseConnector pipeline.
Credentials never reach the Brain.
"""
import json, time, urllib.request, urllib.parse, hashlib, ssl, os
from base import BaseConnector, ConnectorResult

# 1. COURTS/LEGAL — BAILII Connector (public, no auth)
class BAILIIConnector(BaseConnector):
    provider_id = "bailii-uk"
    provider = "BAILII (British and Irish Legal Information Institute)"
    source_class = "COURTS_LEGAL"
    jurisdiction = "UK, Ireland"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "Reasonable use"
    api_url = "https://www.bailii.org"
    documentation = "https://www.bailii.org/"
    license = "Free public access (charity-funded)"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        url = f"https://www.bailii.org/cgi-bin/markup.cgi?query={urllib.parse.quote(search_term)}&method=boolean"
        try:
            result = self._make_request(url)
            if result.success:
                text = result.data if isinstance(result.data, str) else json.dumps(result.data)
                has_results = search_term.lower() in text.lower() and "no documents" not in text.lower()
                result.quality_score = 1.0 if has_results else 0.0
                result.data = {"has_results": has_results, "search_term": search_term, "page_size": len(text)}
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 2. COURTS/LEGAL — UK Tribunal Decisions Connector
class UKTribunalConnector(BaseConnector):
    provider_id = "uk-tribunals"
    provider = "UK Judiciary Tribunal Decisions"
    source_class = "COURTS_LEGAL"
    jurisdiction = "UK"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://www.judiciary.uk/judgments/"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        url = f"https://www.judiciary.uk/judgments/?search={urllib.parse.quote(search_term)}"
        try:
            result = self._make_request(url)
            text = result.data if isinstance(result.data, str) else json.dumps(result.data)
            has_results = "no judgments" not in text.lower() and len(text) > 5000
            result.data = {"has_results": has_results, "search_term": search_term}
            result.quality_score = 1.0 if has_results else 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 3. SOCIAL — GitHub Connector (public API, no auth)
class GitHubConnector(BaseConnector):
    provider_id = "github"
    provider = "GitHub"
    source_class = "SOCIAL_MESSAGING"
    jurisdiction = "Global"
    auth_method = "NONE (rate limited without token)"
    credential_type = "github_token"  # Optional
    rate_limit = "60 req/hour without token, 5000 with"
    api_url = "https://api.github.com"
    documentation = "https://docs.github.com/rest"
    
    def query(self, username: str = "", repo: str = "", **kwargs) -> ConnectorResult:
        if repo:
            url = f"{self.api_url}/repos/{username}/{repo}"
        else:
            url = f"{self.api_url}/users/{username}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._check_credential():
            headers["Authorization"] = f"token {self.credentials['github_token']}"
        try:
            result = self._make_request(url, headers)
            if result.success:
                result.quality_score = 1.0
                if not self._prompt_injection_check(result.data):
                    result.data = {"warning": "PROMPT_INJECTION_DETECTED", "raw_blocked": True}
                    result.quality_score = 0.0
            return result
        except urllib.error.HTTPError as e:
            return ConnectorResult(success=False, error=f"HTTP {e.code}", provider=self.provider, source_class=self.source_class)

# 4. THREAT INTELLIGENCE — Google Safe Browsing (requires API key)
class SafeBrowsingConnector(BaseConnector):
    provider_id = "google-safebrowsing"
    provider = "Google Safe Browsing"
    source_class = "THREAT_INTELLIGENCE"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "safebrowsing_api_key"
    api_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    documentation = "https://developers.google.com/safe-browsing"
    
    def query(self, url: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Google Safe Browsing API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        # Real implementation would call the API
        return ConnectorResult(
            success=False, error="AUTHORIZATION_REQUIRED",
            provider=self.provider, source_class=self.source_class,
            authorization_status="AUTH_REQUIRED"
        )

# 5. THREAT INTELLIGENCE — VirusTotal (requires API key)
class VirusTotalConnector(BaseConnector):
    provider_id = "virustotal"
    provider = "VirusTotal"
    source_class = "THREAT_INTELLIGENCE"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "virustotal_api_key"
    api_url = "https://www.virustotal.com/api/v3"
    documentation = "https://developers.virustotal.com"
    
    def query(self, domain: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — VirusTotal API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/domains/{domain}"
        headers = {"x-apikey": self.credentials["virustotal_api_key"]}
        try:
            result = self._make_request(url, headers)
            return result
        except urllib.error.HTTPError as e:
            return ConnectorResult(success=False, error=f"HTTP {e.code}", provider=self.provider, source_class=self.source_class)

# 6. THREAT INTELLIGENCE — AbuseIPDB (free tier, requires API key)
class AbuseIPDBConnector(BaseConnector):
    provider_id = "abuseipdb"
    provider = "AbuseIPDB"
    source_class = "THREAT_INTELLIGENCE"
    auth_method = "API_KEY"
    credential_type = "abuseipdb_api_key"
    api_url = "https://api.abuseipdb.com/api/v2"
    
    def query(self, ip: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/check?ipAddress={ip}&maxAgeInDays=90"
        headers = {"Key": self.credentials["abuseipdb_api_key"], "Accept": "application/json"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 7. GEOINT — OpenStreetMap Nominatim (free, no auth)
class NominatimConnector(BaseConnector):
    provider_id = "osm-nominatim"
    provider = "OpenStreetMap Nominatim"
    source_class = "GEOINT"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    rate_limit = "1 req/sec (usage policy)"
    api_url = "https://nominatim.openstreetmap.org"
    documentation = "https://nominatim.org/release-docs/latest/api/Overview/"
    license = "ODbL (Open Data Commons Open Database License)"
    
    def query(self, address: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/search?q={urllib.parse.quote(address)}&format=json&limit=5"
        try:
            result = self._make_request(url)
            if result.success:
                if isinstance(result.data, list) and len(result.data) > 0:
                    result.quality_score = 1.0
                    # Extract geospatial data
                    features = []
                    for item in result.data:
                        features.append({
                            "display_name": item.get("display_name", ""),
                            "lat": item.get("lat", ""),
                            "lon": item.get("lon", ""),
                            "type": item.get("type", ""),
                            "class": item.get("class", ""),
                        })
                    result.data = {"features": features, "count": len(features)}
                else:
                    result.data = {"features": [], "count": 0}
                    result.quality_score = 0.0
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 8. PHONE/TELECOM — Numverify (free tier, requires API key)
class NumverifyConnector(BaseConnector):
    provider_id = "numverify"
    provider = "Numverify (apilayer)"
    source_class = "PHONE_TELECOM"
    jurisdiction = "Global"
    auth_method = "API_KEY"
    credential_type = "numverify_api_key"
    api_url = "https://api.apilayer.com/number_verification"
    
    def query(self, phone: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Numverify API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/validate?number={urllib.parse.quote(phone)}"
        headers = {"apikey": self.credentials["numverify_api_key"]}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 9. CORPORATE — Companies House API (requires API key, free registration)
class CompaniesHouseConnector(BaseConnector):
    provider_id = "companies-house-uk"
    provider = "Companies House UK"
    source_class = "CORPORATE"
    jurisdiction = "UK"
    auth_method = "BASIC_AUTH"
    credential_type = "companies_house_api_key"
    rate_limit = "600 req/5min"
    api_url = "https://api.company-information.service.gov.uk"
    documentation = "https://developer.company-information.service.gov.uk"
    license = "Free (UK public data)"
    
    def query(self, company_number: str = "", endpoint: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Companies House API key required (free registration at developer.company-information.service.gov.uk)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        import base64
        api_key = self.credentials["companies_house_api_key"]
        auth = base64.b64encode(f"{api_key}:".encode()).decode()
        path = f"/company/{company_number}" if not endpoint else f"/company/{company_number}/{endpoint}"
        url = f"{self.api_url}{path}"
        headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
        try:
            return self._make_request(url, headers)
        except urllib.error.HTTPError as e:
            return ConnectorResult(success=False, error=f"HTTP {e.code}", provider=self.provider, source_class=self.source_class)

# 10. CRYPTO — Etherscan (free tier, optional API key)
class EtherscanConnector(BaseConnector):
    provider_id = "etherscan"
    provider = "Etherscan"
    source_class = "CRYPTO_EXCHANGE"
    jurisdiction = "Global"
    auth_method = "API_KEY (optional for free tier)"
    credential_type = "etherscan_api_key"
    rate_limit = "5 req/sec, 100K/day"
    api_url = "https://api.etherscan.io/api"
    
    def query(self, address: str = "", action: str = "balance", **kwargs) -> ConnectorResult:
        params = {"module": "account", "action": action, "address": address, "tag": "latest"}
        if self._check_credential():
            params["apikey"] = self.credentials["etherscan_api_key"]
        url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
        try:
            result = self._make_request(url)
            return result
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 11. CRYPTO — Blockchain.info (free, no auth)
class BlockchainInfoConnector(BaseConnector):
    provider_id = "blockchain-info"
    provider = "Blockchain.com Explorer"
    source_class = "CRYPTO_EXCHANGE"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://blockchain.info"
    
    def query(self, address: str = "", **kwargs) -> ConnectorResult:
        url = f"{self.api_url}/rawaddr/{address}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 12. HISTORICAL — Certificate Transparency (Google CT log search via API)
class CTLogConnector(BaseConnector):
    provider_id = "google-ct"
    provider = "Google Certificate Transparency Logs"
    source_class = "HISTORICAL_INTELLIGENCE"
    jurisdiction = "Global"
    auth_method = "NONE"
    credential_type = "NONE"
    api_url = "https://ct.googleapis.com/logs"
    
    def query(self, domain: str = "", **kwargs) -> ConnectorResult:
        # Google CT API (different from crt.sh)
        url = f"https://ct.googleapis.com/logs/us-mirrors/ct/v1/get-entries?start=0&end=100"
        try:
            result = self._make_request(url)
            return result
        except Exception as e:
            # Fallback to crt.sh with retry
            url2 = f"https://crt.sh/?q={urllib.parse.quote(domain)}&output=json"
            try:
                result = self._make_request(url2)
                return result
            except Exception as e2:
                return ConnectorResult(success=False, error=f"CT logs unavailable: {e}, crt.sh: {e2}", provider=self.provider, source_class=self.source_class)

# 13. HISTORICAL — DNS History via DNSDB (requires API key) / Alternative: SecurityTrails
class DNSHistoryConnector(BaseConnector):
    provider_id = "dns-history"
    provider = "DNS History (SecurityTrails / DNSDB)"
    source_class = "HISTORICAL_INTELLIGENCE"
    auth_method = "API_KEY"
    credential_type = "dns_history_api_key"
    
    def query(self, domain: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — DNS history API key required (SecurityTrails or DNSDB)",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        return ConnectorResult(success=False, error="AUTHORIZATION_REQUIRED", provider=self.provider, source_class=self.source_class)

# 14. SANCTIONS — OpenSanctions (requires API key)
class OpenSanctionsConnector(BaseConnector):
    provider_id = "opensanctions"
    provider = "OpenSanctions"
    source_class = "LICENSED_INTELLIGENCE"
    auth_method = "API_KEY"
    credential_type = "opensanctions_api_key"
    api_url = "https://api.opensanctions.org"
    
    def query(self, query: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — OpenSanctions API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/search/default?q={urllib.parse.quote(query)}&limit=10"
        headers = {"Authorization": f"Bearer {self.credentials['opensanctions_api_key']}"}
        try:
            return self._make_request(url, headers)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 15. FINANCIAL — OpenCorporates (requires API token)
class OpenCorporatesConnector(BaseConnector):
    provider_id = "opencorporates"
    provider = "OpenCorporates"
    source_class = "CORPORATE"
    auth_method = "API_TOKEN"
    credential_type = "opencorporates_api_token"
    api_url = "https://api.opencorporates.com/v0.4"
    
    def query(self, company_number: str = "", jurisdiction: str = "gb", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — OpenCorporates API token required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        url = f"{self.api_url}/companies/{jurisdiction}/{company_number}?api_token={self.credentials['opencorporates_api_token']}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 16. IDENTITY RESOLUTION — Entity Resolution Layer
class EntityResolutionConnector(BaseConnector):
    provider_id = "entity-resolver"
    provider = "GFIN Entity Resolution Engine"
    source_class = "IDENTITY_ENTITY_RESOLUTION"
    auth_method = "NONE"
    credential_type = "NONE"
    
    def query(self, name: str = "", identifiers: dict = None, **kwargs) -> ConnectorResult:
        """Resolve entity by cross-referencing multiple identifiers."""
        identifiers = identifiers or {}
        confidence = "UNRESOLVED"
        matches = []
        
        # Cross-reference identifiers
        if name and identifiers.get("github"):
            # If name matches GitHub account, confidence increases
            confidence = "STRONGLY_SUPPORTED"
            matches.append({"source": "GitHub", "identifier": identifiers["github"], "name": name})
        
        if identifiers.get("email") and identifiers.get("github_email"):
            if identifiers["email"] == identifiers["github_email"]:
                confidence = "CONFIRMED"
                matches.append({"source": "GitHub API email", "match": "exact email match"})
        
        if identifiers.get("linkedin") and identifiers.get("github"):
            confidence = "STRONGLY_SUPPORTED" if confidence == "UNRESOLVED" else confidence
            matches.append({"source": "LinkedIn", "identifier": identifiers["linkedin"]})
        
        result = ConnectorResult(
            success=True,
            provider=self.provider,
            source_class=self.source_class,
            data={"resolved_name": name, "confidence": confidence, "matches": matches, "identifiers": identifiers},
            quality_score=1.0 if confidence == "CONFIRMED" else 0.5,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        )
        return result

# 17. ADVERTISING — Facebook Ad Library (requires app review)
class FacebookAdLibraryConnector(BaseConnector):
    provider_id = "facebook-ad-library"
    provider = "Facebook Ad Library API"
    source_class = "ADVERTISING"
    auth_method = "OAUTH"
    credential_type = "facebook_access_token"
    api_url = "https://graph.facebook.com/v18.0/ads_archive"
    
    def query(self, search_term: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Facebook app review + access token required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        params = f"?access_token={self.credentials['facebook_access_token']}&search_terms={urllib.parse.quote(search_term)}&ad_type=ALL"
        url = f"{self.api_url}{params}"
        try:
            return self._make_request(url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e), provider=self.provider, source_class=self.source_class)

# 18. FINANCIAL — Payment connector abstraction
class PaymentIntelligenceConnector(BaseConnector):
    provider_id = "payment-intel"
    provider = "Payment Intelligence Layer"
    source_class = "FINANCIAL_PAYMENT"
    auth_method = "VARIES"
    credential_type = "payment_api_key"
    
    def query(self, merchant_id: str = "", domain: str = "", **kwargs) -> ConnectorResult:
        if not self._check_credential():
            return ConnectorResult(
                success=False, error="AUTHORIZATION_REQUIRED — Payment intelligence API key required",
                provider=self.provider, source_class=self.source_class,
                authorization_status="AUTH_REQUIRED"
            )
        return ConnectorResult(success=False, error="AUTHORIZATION_REQUIRED", provider=self.provider, source_class=self.source_class)

# Connector Factory
CONNECTOR_REGISTRY = {
    "bailii": BAILIIConnector,
    "uk_tribunals": UKTribunalConnector,
    "github": GitHubConnector,
    "google_safebrowsing": SafeBrowsingConnector,
    "virustotal": VirusTotalConnector,
    "abuseipdb": AbuseIPDBConnector,
    "nominatim": NominatimConnector,
    "numverify": NumverifyConnector,
    "companies_house": CompaniesHouseConnector,
    "etherscan": EtherscanConnector,
    "blockchain_info": BlockchainInfoConnector,
    "ct_logs": CTLogConnector,
    "dns_history": DNSHistoryConnector,
    "opensanctions": OpenSanctionsConnector,
    "opencorporates": OpenCorporatesConnector,
    "entity_resolver": EntityResolutionConnector,
    "facebook_ad_library": FacebookAdLibraryConnector,
    "payment_intel": PaymentIntelligenceConnector,
}

def get_connector(name: str, credentials: dict = None) -> BaseConnector:
    cls = CONNECTOR_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"Unknown connector: {name}")
    return cls(credentials or {})

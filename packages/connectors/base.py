"""
GFIN Universal Connector Framework v1.0
Common pipeline: discovery → validation → auth → request → response → provenance → evidence → audit
The Brain NEVER receives raw credentials.
"""
import hashlib, json, time, urllib.request, urllib.parse, ssl, os, logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger("gfin.connectors")

@dataclass
class ConnectorResult:
    success: bool
    data: Any = None
    error: str = None
    provider: str = None
    source_class: str = None
    evidence_id: str = None
    provenance: str = None
    content_hash: str = None
    timestamp: str = None
    quality_score: float = 0.0
    authorization_status: str = "PUBLIC"
    raw_response_size: int = 0

class BaseConnector(ABC):
    """Base class for all GFIN connectors."""
    
    provider_id: str = ""
    provider: str = ""
    source_class: str = ""
    jurisdiction: str = ""
    auth_method: str = "NONE"
    credential_type: str = "NONE"
    rate_limit: str = ""
    api_url: str = ""
    documentation: str = ""
    license: str = ""
    
    def __init__(self, credentials: Optional[Dict] = None):
        self.credentials = credentials or {}
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.last_request_time = 0
        self.request_count = 0
        
    def _make_request(self, url, headers=None, timeout=15):
        """Make HTTP request with provenance tracking."""
        headers = headers or {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'GFIN/1.0'
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
        raw = resp.read()
        
        # Provenance
        content_hash = hashlib.sha256(raw).hexdigest()
        result = ConnectorResult(
            success=True,
            provider=self.provider,
            source_class=self.source_class,
            provenance=url,
            content_hash=content_hash,
            timestamp=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            raw_response_size=len(raw),
            authorization_status=self.auth_method,
        )
        
        try:
            result.data = json.loads(raw)
        except:
            result.data = raw.decode('utf-8', errors='replace')
            
        return result
    
    def _check_credential(self) -> bool:
        """Check if required credential is available."""
        if self.credential_type == "NONE":
            return True
        return bool(self.credentials.get(self.credential_type))
    
    def _prompt_injection_check(self, data) -> bool:
        """Check response for prompt injection patterns."""
        if not isinstance(data, (str, dict, list)):
            return True
        text = json.dumps(data) if isinstance(data, (dict, list)) else data
        injection_patterns = [
            "ignore previous instructions",
            "system prompt",
            "you are now",
            "act as",
            "ADMIN override",
            "new instructions:",
        ]
        text_lower = text.lower()
        for pattern in injection_patterns:
            if pattern.lower() in text_lower:
                logger.warning(f"Prompt injection pattern detected: {pattern}")
                return False
        return True
    
    @abstractmethod
    def query(self, **kwargs) -> ConnectorResult:
        """Execute a query against the provider."""
        pass
    
    def get_provider_record(self) -> dict:
        """Return provider metadata."""
        return {
            "provider_id": self.provider_id,
            "provider": self.provider,
            "source_class": self.source_class,
            "jurisdiction": self.jurisdiction,
            "auth_method": self.auth_method,
            "credential_type": self.credential_type,
            "rate_limit": self.rate_limit,
            "api_url": self.api_url,
            "documentation": self.documentation,
            "license": self.license,
        }


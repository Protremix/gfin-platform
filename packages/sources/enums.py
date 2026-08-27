"""GFIN Source enums — shared enums to avoid circular imports."""
from enum import Enum


class AuthMethod(str, Enum):
    PUBLIC_API = "public_api"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    SERVICE_ACCOUNT = "service_account"
    MUTUAL_TLS = "mutual_tls"
    SIGNED_REQUEST = "signed_request"
    LAW_ENFORCEMENT_CREDENTIAL = "law_enforcement_credential"
    CASE_SCOPED_TOKEN = "case_scoped_token"

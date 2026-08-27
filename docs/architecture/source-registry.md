# GFIN Source Registry

## Overview
Central registry for all authorized data sources. No unregistered external source may be used by the Brain.

## Source Record Fields
source_id, provider, connector, base_url, auth_method, data_categories,
jurisdictions, allowed_data, classification, required_permissions, legal_basis,
rate_limit, audit_policy, enabled, version, reliability, last_verified

## Authentication Modes
PUBLIC_API, API_KEY, OAUTH2, SERVICE_ACCOUNT, MUTUAL_TLS, SIGNED_REQUEST,
LAW_ENFORCEMENT_CREDENTIAL, CASE_SCOPED_TOKEN

## Provider Validation (12 steps)
1. Official documentation  2. Provider identity  3. Endpoint  4. Authentication
5. Terms/license  6. Data provenance  7. Jurisdiction  8. Retention
9. Security  10. Connector tests  11. Failure tests  12. Provenance tests

Version: 1.0.0

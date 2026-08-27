# GFIN — MISP Integration Specification

**Version:** 1.0
**Status:** SPECIFICATION
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Overview

MISP (Malware Information Sharing Platform) is integrated as an external threat intelligence sharing platform. GFIN communicates with MISP exclusively through the PyMISP REST API client (BSD-2-Clause). MISP core (AGPL-3.0) runs as a separate service — GFIN never modifies MISP source code.

## Official Sources

| Resource | URL |
|----------|-----|
| MISP Core Repository | https://github.com/MISP/MISP |
| PyMISP (Python Client) | https://github.com/MISP/PyMISP |
| Official Website | https://www.misp-project.org/ |
| Documentation | https://misp.github.io/MISP/ |
| OpenAPI Spec | https://www.misp-project.org/documentation/openapi.html |
| Licensing | https://www.misp-project.org/license/ |
| Docker | https://github.com/MISP/misp-docker |

## License

- **MISP Core:** AGPL-3.0-or-later
- **PyMISP:** BSD-2-Clause
- **Taxonomies/Galaxies/Objects:** CC0 1.0 / BSD-2-Clause

**AGPL Exemption (VERIFIED from official source):**
> "AGPL only applies to the MISP core software and not to any other software using the API of MISP."
> Source: https://www.misp-project.org/license/

**Architectural Implication:** GFIN communicates with MISP via REST API / PyMISP. No AGPL copyleft obligations are triggered. Source code disclosure only applies if MISP core PHP code is modified and offered as a network service.

**NOTE:** This is an engineering assessment, not legal advice. Formal legal counsel required before production.

## Integration Architecture

```text
GFIN Platform
    │
    ▼
MISP Adapter (Python, PyMISP BSD-2)
    │
    ├── Inbound: MISP Events/Attributes → GFIN Observations
    ├── Outbound: GFIN Intelligence → MISP Events (optional)
    └── Health Check: MISP API status
    │
    ▼
MISP Server (separate service, AGPL-3.0)
    │
    ├── Events, Attributes, Objects
    ├── Galaxies, Taxonomies, Warning Lists
    ├── Synchronization (Push/Pull)
    └── STIX/TAXII conversion
```

## Fraud-Specific Capabilities

MISP has built-in financial fraud support:

### Taxonomies
- `misp-taxonomy:financial-fraud`: Money mules, credit card fraud, APP fraud, BEC/CEO fraud, ATO, SIM swapping
- `gsma-fraud`: Telecommunication and mobile money fraud

### Galaxies
- `misp-galaxy:financial-fraud`: Financial threat tactics, scam frameworks
- `misp-galaxy:threat-actor`: Financial cybercrime groups (Carbanak, FIN7, TA505)

### Objects
- `bank-account`: IBAN, BIC, account holder, bank name
- `credit-card`: PAN, BIN, expiration, cardholder
- `transaction`: Amount, currency, source/destination account, timestamp
- `cryptocurrency-transaction` / `btc-wallet` / `coin-address`: Crypto wallets, transaction hashes
- `mule-account`: Mule account mapping
- `person` / `legal-entity`: Identity context for fraudsters

## GFIN ↔ MISP Data Mapping

| MISP Concept | GFIN Concept | Transformation |
|-------------|-------------|----------------|
| Event | Report / Campaign | Event UUID → GFIN report ID, Event info → title |
| Attribute (IP) | Entity (IP) | Attribute value → normalized_value |
| Attribute (Domain) | Entity (Domain) | Attribute value → normalized_value |
| Attribute (URL) | Entity (URL) | Attribute value → normalized_value |
| Attribute (Email) | Entity (Email) | Attribute value → normalized_value |
| Object (bank-account) | Entity (Payment Identifier) | IBAN → normalized_value, BIC → metadata |
| Object (credit-card) | Entity (Payment Identifier) | Card number → normalized_value (hashed) |
| Object (transaction) | Entity (Transaction) | Transaction ID → normalized_value |
| Object (btc-wallet) | Entity (Crypto Wallet) | Address → normalized_value |
| Galaxy (financial-fraud) | Fraud Pattern | Galaxy name → fraud_pattern_type |
| Taxonomy (financial-fraud) | Classification tags | Taxonomy tag → metadata tags |
| Sighting | Observation | Sighting timestamp → observation time, source → provenance |
| Org (creator) | Source | Org UUID → source_id, Org name → source_name |

## Inbound Flow (MISP → GFIN)

```text
MISP Server
    │
    ▼
PyMISP Client (BSD-2)
    │
    ▼
MISP Adapter
    │
    ├── Fetch events by tag (e.g., financial-fraud, tlp:amber)
    ├── Fetch attributes by type (ip, domain, url, email, IBAN)
    ├── Fetch objects (bank-account, transaction, btc-wallet)
    └── Fetch sightings for provenance
    │
    ▼
Ingestion Gateway
    │
    ├── Schema validation
    ├── Deduplication
    ├── Normalization (MISP → GFIN canonical)
    ├── Provenance assignment (source: MISP, org: creator)
    ├── Classification (from TLP tag → GFIN classification)
    ├── Jurisdiction tagging (from event org country)
    ├── Confidence scoring (from MISP threat level)
    └── Source restriction check (TLP compliance)
    │
    ▼
GFIN Intelligence Graph
```

### TLP → GFIN Classification Mapping

| MISP TLP Tag | GFIN Classification |
|-------------|-------------------|
| tlp:white | PUBLIC |
| tlp:green | COMMUNITY |
| tlp:amber | RESTRICTED |
| tlp:red | LAW_ENFORCEMENT |

## Outbound Flow (GFIN → MISP, Optional)

```text
GFIN Intelligence
    │
    ▼
Policy Filter (organization, classification)
    │
    ▼
Classification Check (PUBLIC / COMMUNITY only)
    │
    ▼
Source Restriction Check
    │
    ▼
MISP Adapter (GFIN → MISP Event)
    │
    ├── Create event with TLP tag
    ├── Add attributes (IP, domain, URL, email)
    ├── Add objects (bank-account, transaction)
    └── Set distribution level (community, sharing group)
    │
    ▼
MISP Server (push or pull)
```

## Security Model

| Requirement | Implementation |
|-------------|---------------|
| Authentication | MISP API key (per-user, scoped to GFIN org) |
| Authorization | Dedicated sync user with restricted permissions |
| Network | MISP on isolated network segment |
| Data in transit | TLS/HTTPS mandatory |
| Audit | All API calls logged in GFIN audit trail |
| Rate limiting | PyMISP handles pagination and rate limits |
| Provenance | Every imported item tagged with MISP source |

## Deployment (Layer B — REQUIRES EXTERNAL INFRASTRUCTURE)

| Component | Specification |
|-----------|--------------|
| MISP Core | Docker container (official misp-docker) |
| Database | MySQL 8.0 or MariaDB 10.x+ |
| Cache | Redis 7.x+ |
| Resources | 4-8 vCPUs, 16-32 GB RAM, SSD storage |
| Network | Isolated segment, TLS to GFIN |
| K8s | Community Helm charts available |
| Federation | Hub-and-spoke (GFIN hub → bank spokes) |

## POC Plan

1. Deploy MISP in Docker (Layer B)
2. Configure financial-fraud taxonomy and galaxy
3. Implement MISP Adapter using PyMISP
4. Test inbound: Create MISP event → verify GFIN ingestion
5. Test outbound: Create GFIN entity → verify MISP event creation
6. Test federation: Push/pull between two MISP instances
7. Verify provenance, classification, and audit trail

## Status

| Component | Status |
|-----------|--------|
| Specification | COMPLETE |
| POC | PENDING (Layer B infrastructure required) |
| Adapter implementation | PENDING |
| Integration tests | PENDING |
| Legal review | REQUIRED (AGPL verification) |

# ADR-006: MISP Integration via API

**Status:** ACCEPTED
**Date:** 2026-08-26
**Author:** GPT Luna (GFIN-CEA)

---

## Context

GFIN needs a threat intelligence sharing platform for federated exchange of fraud indicators with central banks, financial institutions, and law enforcement. MISP is the de facto standard for threat intelligence sharing with built-in financial fraud taxonomies.

## Decision

**INTEGRATE MISP via PyMISP REST API client (BSD-2-Clause).**

MISP core (AGPL-3.0) runs as a separate service. GFIN communicates exclusively through the API. The official MISP licensing FAQ confirms: "AGPL only applies to the MISP core software and not to any other software using the API of MISP."

## Rationale

1. **Fraud-native:** MISP has built-in `bank-account`, `credit-card`, `transaction`, `mule-account` objects and `financial-fraud` taxonomies
2. **Federation:** Hub-and-spoke sync model matches GFIN's central-bank-to-commercial-bank topology
3. **License-safe:** API usage exempts GFIN from AGPL copyleft (verified from official source)
4. **STIX/TAXII:** Native STIX 2.1 conversion and TAXII 2.1 support
5. **Mature:** Monthly releases, 283+ contributors, deployed by FS-ISAC, CERT-C3, CIRCL

## Consequences

- GFIN must deploy and maintain a MISP instance (MySQL, Redis, PHP stack)
- Legal counsel must verify AGPL API-use exemption before production
- MISP Adapter must normalize events/attributes to GFIN canonical schema
- TLP tags must map to GFIN classification levels

## Alternatives Considered

- **Build custom sharing platform:** Rejected — MISP provides 90% of needed functionality
- **Use OpenCTI for sharing:** Possible but MISP's federation model is better suited for hub-and-spoke

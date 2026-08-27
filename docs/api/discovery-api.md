# GFIN — API: Discovery API

**Version:** 1.0
**Status:** SPECIFICATION (Layer A — API endpoints defined, Layer B — REST server required)
**Date:** 2026-08-26

---

## Endpoints

### Start Discovery Run

```http
POST /api/v1/discovery/runs
```

**Request:**
```json
{
    "seed_entity_id": "ENT-001",
    "seed_entity_type": "DOMAIN",
    "seed_entity_value": "suspicious-domain.example",
    "config": {
        "max_depth": 5,
        "max_nodes": 100,
        "max_tasks": 50,
        "enable_anomaly_detection": true,
        "enable_campaign_detection": true,
        "enable_monitoring": true
    }
}
```

**Response:**
```json
{
    "run_id": "RUN-ABCD1234",
    "status": "COMPLETED",
    "discovered_entities": 12,
    "leads": 8,
    "campaign_candidates": 2,
    "anomalies": 3,
    "coverage": {...}
}
```

### Get Discovery Run

```http
GET /api/v1/discovery/runs/{id}
```

### Get Investigation Graph

```http
GET /api/v1/discovery/runs/{id}/graph
```

**Response:** Adjacency list representation of the investigation graph.

### Get Leads

```http
GET /api/v1/discovery/runs/{id}/leads
```

**Response:** List of InvestigationLead objects with evidence, confidence, priority, and explanation.

### Expand Lead

```http
POST /api/v1/discovery/leads/{id}/expand
```

Start a new discovery run using the lead's discovered entity as a seed.

### Confirm Lead

```http
POST /api/v1/discovery/leads/{id}/confirm
```

Human-in-the-loop: investigator confirms the lead.

### Reject Lead

```http
POST /api/v1/discovery/leads/{id}/reject
```

Human-in-the-loop: investigator rejects the lead.

### Get Coverage Report

```http
GET /api/v1/discovery/coverage/{id}
```

**Response:** DiscoveryCoverage showing checked, not_checked, failed, unavailable, authorization_required sources.

### Create Monitoring Rule

```http
POST /api/v1/monitoring/rules
```

**Request:**
```json
{
    "entity_id": "ENT-001",
    "entity_type": "DOMAIN",
    "entity_value": "suspicious-domain.example",
    "monitor_types": ["dns", "certificate", "whois"],
    "ttl": "7d",
    "priority": 0.8
}
```

## Authorization

All endpoints apply existing RBAC/ABAC, classification, jurisdiction, and organization controls.

| Role | Can Access |
|------|-----------|
| investigator | Public sources, MISP, OpenCTI, Cortex (no police_database) |
| police_officer | All sources including police_database |
| admin | All sources + configuration management |

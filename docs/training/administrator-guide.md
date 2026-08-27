# GFIN Administrator Guide & Reference

**Document Version:** 1.0  
**Target Audience:** System Administrators, Security Officers, Compliance Managers  
**Scope:** Security Administration, Access Control, Audit Verification, Compliance, and Operations Maintenance  

---

## 1. Role-Based & Attribute-Based Access Control (RBAC/ABAC)

GFIN enforces a Zero Trust security posture across all services. Access evaluation follows a dual RBAC + ABAC architecture:

```
[ Request ] ──▶ [ 1. RBAC Permission Check ] ──▶ [ 2. ABAC Classification Level Check ]
                                                                  │
[ Access Granted ] ◄── [ 4. ABAC Org Scope Check ] ◄── [ 3. ABAC Jurisdiction Check ]
```

### 1.1 The 7 GFIN System Roles

1. `citizen`: Public user reporting fraud or checking public indicators. Restricted to `PUBLIC` classification data.
2. `analyst`: Junior intelligence analyst capable of creating/updating basic entities, reports, and evidence.
3. `investigator`: Full investigator with authority to create campaigns, execute AI investigation tools, and initiate intelligence requests.
4. `officer`: Sworn law enforcement officer authorized to handle `LAW_ENFORCEMENT` classified data and cross-border requests.
5. `supervisor`: Senior operational lead with approval rights for cross-border requests, alerts, campaign dismantlement, and high-risk actions.
6. `administrator`: Platform administrator managing users, system configurations, access matrices, and audit logs.
7. `system`: Internal system services executing automated background jobs, event bus handlers, and AI processing.

---

## 2. Comprehensive Access Control Matrix (9 Resources × 8 Actions)

**Actions (8):** `read`, `create`, `update`, `delete`, `export`, `share`, `classify`, `approve`  
**Resources (9):** `entity`, `evidence`, `campaign`, `report`, `alert`, `audit_log`, `federation_request`, `system_config`, `user_management`

### Complete Permission Matrix Table

| Resource | Citizen | Analyst | Investigator | Officer | Supervisor | Administrator | System |
|----------|---------|---------|--------------|---------|------------|---------------|--------|
| **entity** | read | read, create, update | read, create, update | read, create, update, delete | read, create, update, delete | read, create, update, delete, export, classify | ALL |
| **evidence** | - | read, create | read, create, export | read, create, export | read, create, export, share | read, create, update, delete, export, share, classify | ALL |
| **campaign** | - | read, create | read, create, update | read, create, update | read, create, update, delete | read, create, update, delete, export | ALL |
| **report** | create, read | read, create, update | read, create, update, delete | read, create, update, delete | read, create, update, delete, approve | read, create, update, delete, export, share, classify, approve | ALL |
| **alert** | - | read | read | read, classify | read, classify, approve | read, classify, approve | ALL |
| **audit_log** | - | - | - | read | read | read, export | ALL |
| **federation_request** | - | - | read | read, create, share | read, approve, share | read, create, update, approve, share | ALL |
| **system_config** | - | - | - | - | read | read, create, update, delete | ALL |
| **user_management** | - | - | - | - | - | read, create, update, delete | ALL |

---

## 3. User Management and Role Assignment (Module 02)

Administrators create and manage user accounts, assigning roles, organization IDs, and jurisdiction scopes.

```python
import sys
sys.path.insert(0, '/gfin')
from packages.auth.rbac import AuthorizationEngine, AccessRequest, UserRole, DataClassification

# Example User Provisioning Logic
def create_user(username: str, role: UserRole, organization_id: str, jurisdiction: str):
    user_record = {
        "user_id": f"USER-{username.upper()}",
        "role": role,
        "organization_id": organization_id,
        "jurisdiction": jurisdiction,
        "status": "ACTIVE"
    }
    print(f"User {user_record['user_id']} created with role {role.value}")
    return user_record

user = create_user(
    username="jsmith",
    role=UserRole.INVESTIGATOR,
    organization_id="ORG-US-FBI",
    jurisdiction="US"
)
```

---

## 4. Audit Log Review & Verification (Module 02)

GFIN maintains an immutable, tamper-evident audit log for all system events and access requests.

```python
from packages.auth.audit import AuditLogger, AuditEvent

audit_logger = AuditLogger()

# Log Security Audit Event
audit_logger.log_event(
    user_id="USER-JSMITH",
    action="cross_border_request_create",
    resource_type="federation_request",
    resource_id="CBR-2026-001",
    status="SUCCESS",
    ip_address="192.0.2.50"
)

# Audit Trail Verification Check
is_chain_valid = audit_logger.verify_audit_chain()
print(f"Audit Log Cryptographic Chain Integrity: {'VALID' if is_chain_valid else 'CORRUPTED'}")
```

---

## 5. Rate Limiting Configuration (Module 02)

Rate limits prevent API abuse and DoS attacks across platform endpoints.

```python
from packages.auth.rate_limit import RateLimiter

limiter = RateLimiter()

# Configure Tiered Rate Limits (Requests per Minute)
limiter.set_limit(role="citizen", max_requests=30, window_seconds=60)
limiter.set_limit(role="analyst", max_requests=300, window_seconds=60)
limiter.set_limit(role="investigator", max_requests=1000, window_seconds=60)

# Check Rate Limit Status
allowed = limiter.check_rate_limit(user_id="USER-CITIZEN-01", role="citizen")
print(f"Citizen Request Allowed: {allowed}")
```

---

## 6. Compliance & Data Classification (Module 33)

GFIN defines 5 explicit Data Classification levels:

1. `PUBLIC` (Level 0): Citizen-accessible indicators, public advisories.
2. `COMMUNITY` (Level 1): Shared across accredited NGO/Financial Institution network.
3. `RESTRICTED` (Level 2): Internal intelligence analysts and investigators.
4. `LAW_ENFORCEMENT` (Level 3): Sworn law enforcement officers within legal jurisdiction.
5. `HIGHLY_RESTRICTED` (Level 4): Administrator access only, protected source attribution.

---

## 7. Retention Policy Management (Module 06 & 33)

Data retention schedules are enforced automatically by background retention workers:

| Classification | Retention Period | Action Upon Expiration |
|----------------|------------------|------------------------|
| PUBLIC | 5 Years | Soft Delete → Purge Archive |
| COMMUNITY | 7 Years | Soft Delete → Purge Archive |
| LAW_ENFORCEMENT | 10 Years | Soft Delete → Purge Archive |
| RESTRICTED | 15 Years | Anonymize → Archive |
| HIGHLY_RESTRICTED | 20 Years | Cryptographic Erasure |

---

## 8. GDPR & Data Deletion Procedures (Runbook 6)

When executing a Data Subject Access Request (DSAR) or Right to Erasure under GDPR/Privacy rules:

```python
from packages.services.compliance import ComplianceService

compliance = ComplianceService()

# Step 1: Execute DSAR Data Export
dsar_data = compliance.export_subject_data(subject_email="subject@example.com")
print(f"DSAR Records Exported: {len(dsar_data.get('records', []))}")

# Step 2: Execute Erasure Procedure
erasure_result = compliance.execute_gdpr_erasure(
    subject_email="subject@example.com",
    request_reference="DSAR-2026-0812",
    authorized_by="ADMIN-01"
)

print(f"Entities Soft Deleted: {erasure_result.soft_deleted_count}")
print(f"Graph Nodes Removed: {erasure_result.graph_nodes_removed}")
print(f"Search Index Sanitized: {erasure_result.search_cleared}")
print(f"Audit Trail Anonymized: {erasure_result.audit_anonymized}")
```

---

## 9. Cryptographic Key Rotation Procedures (Runbook 3)

Key rotation schedules must be maintained in HashiCorp Vault:

- **JWT Signing Keys:** 30 Days
- **API Keys & Webhooks:** 90 Days
- **Kafka SASL Credentials:** 90 Days
- **Database Credentials:** 180 Days
- **TLS Certificates:** 365 Days

### Key Rotation Execution Steps (CLI)
```bash
# 1. Store new key in HashiCorp Vault
vault kv put gfin/production/api-keys key_v2="new-secret-token-value"

# 2. Update Kubernetes secrets manifest
kubectl apply -f infrastructure/secrets/api-keys.yaml

# 3. Perform zero-downtime rolling restart
kubectl rollout restart deployment/gfin-api -n gfin
kubectl rollout status deployment/gfin-api -n gfin
```

---

## 10. Backup & Restore Procedures (Runbook 5)

### Backup Schedule
- **PostgreSQL:** Daily full dump + WAL archiving (30-day retention in S3)
- **Neo4j Graph:** Daily `neo4j-admin dump` (7-day retention)
- **OpenSearch:** Snapshot API every 24 hours (7-day retention)
- **Redis:** RDB snapshots every 6 hours (3-day retention)

### Execution Procedures
```bash
# PostgreSQL Backup Execution
pg_dump -h db.gfin.internal -U gfin_admin -F c -b -v -f "/backups/pg_gfin_$(date +%F).dump" gfin_db

# PostgreSQL Restore Execution
pg_restore -h db.gfin.internal -U gfin_admin -d gfin_db -v "/backups/pg_gfin_2026-08-26.dump"
```

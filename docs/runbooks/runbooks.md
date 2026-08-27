# GFIN Runbooks

**Document ID:** GFIN-OPS-001
**Last Updated:** 2026-08-26
**Status:** PREPARATION DOCUMENT

---

## 1. Deployment Runbook

### Pre-Deployment Checklist
- [ ] All 12 go/no-go gates evaluated
- [ ] Infrastructure health verified (K8s, Vault, Kafka, PostgreSQL, Neo4j, OpenSearch, Redis, S3)
- [ ] Secrets provisioned in Vault
- [ ] TLS certificates valid (not expiring within 30 days)
- [ ] Database migrations tested in staging
- [ ] Rollback plan reviewed
- [ ] Monitoring stack active (Prometheus, Grafana)
- [ ] On-call team notified

### Deployment Steps
1. Verify cluster health: `kubectl get nodes -o wide`
2. Verify secrets: `vault kv get gfin/production/api-keys`
3. Deploy database migrations: `python -m packages.common.run_migrations`
4. Deploy services via Helm: `helm upgrade gfin ./infrastructure/helm/gfin`
5. Wait for rollout: `kubectl rollout status deployment/gfin-api`
6. Verify health endpoints: `curl https://api.gfin.io/health`
7. Run smoke tests against production

### Post-Deployment Verification
- [ ] All pods running and healthy
- [ ] API health check returns 200
- [ ] Kafka topics accessible
- [ ] Database connectivity confirmed
- [ ] Monitoring dashboards showing data
- [ ] No error spikes in logs

### Rollback Trigger
- Error rate > 5% for 5 minutes
- P95 latency exceeds SLO by 2x
- Data integrity issues detected

---

## 2. Rollback Runbook

### When to Rollback
- Deployment causes error rate > 5%
- P95 latency exceeds SLO by 2x
- Critical functionality broken
- Data integrity issues

### Rollback Steps
1. Execute rollback: `helm rollback gfin`
2. Verify rollback: `kubectl rollout status deployment/gfin-api`
3. Check API health: `curl https://api.gfin.io/health`
4. Verify data consistency
5. Notify stakeholders
6. Create post-mortem

### Data Safety Checks
- Verify no data loss (compare entity counts)
- Verify evidence vault integrity (hash check)
- Verify graph consistency (node/edge count)
- Verify audit log continuity

---

## 3. Key Rotation Runbook

### Rotation Schedule
- API keys: Every 90 days
- TLS certificates: Every 365 days
- JWT signing key: Every 30 days
- Database credentials: Every 180 days
- Kafka SASL credentials: Every 90 days

### Rotation Steps
1. Generate new secret in Vault: `vault kv put gfin/production/api-keys key=new_value`
2. Update Kubernetes secret: `kubectl apply -f infrastructure/secrets/api-keys.yaml`
3. Restart affected services: `kubectl rollout restart deployment/gfin-api`
4. Verify services using new key
5. Revoke old key after verification
6. Update audit log

---

## 4. Incident Response Runbook

### Severity Levels
| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| P1 | System down, data loss | 15 min | CTO + on-call |
| P2 | Major feature broken | 30 min | Team lead |
| P3 | Minor feature broken | 4 hours | On-call engineer |
| P4 | Cosmetic issue | 24 hours | Backlog |

### Incident Steps
1. **Detect**: Alert triggered by monitoring
2. **Assess**: Determine severity level
3. **Contain**: Isolate affected systems
4. **Eradicate**: Remove root cause
5. **Recover**: Restore service
6. **Post-mortem**: Document within 48 hours

---

## 5. Backup and Restore Runbook

### Backup Schedule
| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Daily + WAL | 30 days | pg_dump + WAL archiving |
| Neo4j | Daily | 7 days | neo4j-admin dump |
| OpenSearch | Daily | 7 days | Snapshot API |
| Redis | Every 6h | 3 days | RDB snapshot |
| S3 | Continuous | 365 days | Versioning |
| Kafka | Continuous | 7 days | MirrorMaker2 |

### Restore Steps
1. Identify backup to restore from
2. Stop affected service
3. Restore from backup
4. Verify data integrity
5. Restart service
6. Run health checks

---

## 6. Data Deletion Runbook (GDPR)

### Data Subject Rights
- Right to access (DSAR)
- Right to erasure (right to be forgotten)
- Right to rectification
- Right to data portability

### Entity Deletion Procedure
1. Verify subject identity
2. Export all data (DSAR)
3. Soft-delete entities (preserve audit trail)
4. After legal retention period, hard-delete
5. Remove from graph (cascade)
6. Remove from search index
7. Anonymize in audit logs
8. Document deletion in compliance log

### Evidence Retention
- PUBLIC: 5 years
- COMMUNITY: 7 years
- LAW_ENFORCEMENT: 10 years
- RESTRICTED: 15 years
- HIGHLY_RESTRICTED: 20 years

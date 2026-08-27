# GFIN Known Issues

**Last Updated:** 2026-08-27  

---

## Active Blockers (Requires External Action)

### B-001: Production Cloud Credentials
- **Status:** BLOCKED
- **Description:** Layer B Terraform IaC is validated (26/26 tests pass) but cannot be provisioned without cloud provider credentials (AWS/GCP/Azure)
- **Impact:** Production infrastructure remains on single Hetzner server (Layer A)
- **Resolution:** Obtain cloud provider credentials and run `terraform apply`

### B-002: External Penetration Testing
- **Status:** PENDING
- **Description:** External pentest required before production deployment
- **Impact:** Security validation incomplete
- **Resolution:** Engage certified penetration testing firm

### B-003: Officer Registration
- **Status:** LOW PRIORITY
- **Description:** Only 2 officers registered (GFIN Admin in GB, Det. Insp. Vance in FR)
- **Impact:** Limited operational capacity
- **Resolution:** Register additional law enforcement officers

### B-004: GitHub Repository Access
- **Status:** BLOCKED
- **Description:** No GitHub Personal Access Token configured on server for git push
- **Impact:** 383 files with changes cannot be pushed to Protremix/gfin-platform
- **Resolution:** Create GitHub PAT with repo scope and configure credential store

---

## Resolved Issues

### R-001: System Purge — Junk Cases (RESOLVED 2026-08-27)
- Purged 94 GFIN-AUTO-* garbage cases from URLHAUS/OPENPHISH feed scrapers
- Purged 1,667 evidence items, 746 case_entities, 96 investigation_steps
- Purged 152 scam_websites (unverified noise), 67 tracked_domains
- Auto-hunter service stopped and disabled
- Hunter code modified to NEVER create cases from feed discoveries

### R-002: False-Positive Victim Classification (RESOLVED 2026-08-27)
- 16,592 scam operator messages were misclassified as victim messages
- Scam recruiters, lead sellers, and service providers were flagged as victims
- Cleaned: from 15 "victims" to 3 real confirmed victims
- Fixed by keyword filtering (hiring, recruitment, hacking services, lead selling)

### R-003: Telegram Bot Token (RESOLVED)
- Bot token was returning 401 Unauthorized
- New token obtained from @BotFather
- Group Privacy disabled for monitoring

### R-004: Kafka Image Compatibility (RESOLVED)
- Bitnami Kafka image incompatible with new architecture
- Switched to apache/kafka:3.7.1
- Fixed advertised listeners configuration

### R-005: PostgreSQL Date Handling (RESOLVED)
- incident_date was passed as string to PostgreSQL
- Fixed to pass as date object

---

## Operational Notes

### Evidence Gating (Strict)
Cases require at least one of:
- Verified victim report
- Active financial drainer infrastructure
- Confirmed fraud pattern correlation
- Telegram intelligence with clear criminal activity

### Data Separation
- **Cases table:** Real investigations only (10 cases)
- **telegram_intelligence:** Raw intelligence (78K messages) — NOT cases
- **tracked_domains:** Available for domain tracking (currently 0 — purged)
- **scam_websites:** Available for verified scam sites (currently 0 — purged)


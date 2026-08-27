# GFIN Project State

**Last Updated:** 2026-08-27 20:30 UTC  
**Maintained by:** GPT Luna (GFIN-CEA)  
**Version:** 2.1.0  

---

## Executive Summary

The Global Fraud Intelligence Network (GFIN) is a secure, evidence-based, internationally federated digital fraud intelligence platform. The system operates on a two-layer architecture: Layer A (production MVP on Hetzner) and Layer B (Terraform IaC, validated but not provisioned).

**Current Status:** OPERATIONAL — Layer A live on gfin-system.com  
**Layer B:** REQUIRES EXTERNAL INFRASTRUCTURE (Terraform validated, needs cloud credentials)

---

## Live Infrastructure

- **Server:** Hetzner CX42 (83.136.252.48, 4 vCPU/8GB, Ubuntu 22.04, London)
- **Domain:** gfin-system.com (DNS confirmed, Nginx TLS)
- **Containers:** 11 Docker services running (PostgreSQL 16, Redis 7, MinIO, Vault, Neo4j 5, OpenSearch 2.18, Kafka 3.7.1, Prometheus, Grafana, Nginx, k3s)
- **Systemd Services:** gfin-server (port 8000), gfin-monitor (24/7 intelligence), gfin-telethon-spy (24/7 Telegram monitoring), tor@default (SOCKS proxy)
- **Test Suite:** 2,466 tests passed, 0 failed, 0 skipped

---

## Module Integration — ALL 39 MODULES COMPLETE

| Batch | Modules | Endpoints | Status |
|-------|---------|-----------|--------|
| 1-3 | evidence_vault, fraud_graph, search_platform, compliance, campaign_engine, global_matching, early_warning, continuous_monitoring, investigation_orchestrator, police_console, entity_resolution | 52 | ✅ VERIFIED |
| 4-5 | campaign_dna, web_discovery, proactive_scamhunter, domain_intelligence, pattern_engine, gdpr_compliance, security_dashboard, local_ai, investigation_copilot, citizen_platform | 46 | ✅ VERIFIED |
| 6-7 | crypto_intelligence, temporal_intelligence, infrastructure_intelligence, evidence_explainability, cross_border_requests, federation, unknown_fraud_discovery | 25 | ✅ VERIFIED |
| 8 | disaster_recovery, alert_engine, analytics, multilingual, kafka_event_bus, pdf_reports | 15 | ✅ VERIFIED |
| 9 | dark_web_monitor, ai_summaries, websocket_hub | 18 | ✅ VERIFIED |
| **TOTAL** | **39 modules** | **234 endpoints** | **ALL HTTP 200** |

---

## Active Cases — 10 Real Evidence-Based Investigations

| Case ID | Target | Priority | Evidence |
|---------|--------|----------|----------|
| GFIN-CASE-001 | cncintelinfo.com — brand impersonation | MEDIUM | 7 items |
| GFIN-CASE-002 | neex.com / Vlad — investment fraud network | HIGH | Telegram intel |
| GFIN-CASE-003 | teamforcetechnologies.com — Cyprus call center | HIGH | Telegram intel |
| GFIN-CASE-004 | REVERSE ENGINEER — scam service provider | MEDIUM | Telegram intel |
| GFIN-CASE-005 | Monde HR — human trafficking recruitment | CRITICAL | Telegram intel |
| GFIN-CASE-006 | RS Database House — victim database selling | HIGH | Telegram intel |
| GFIN-CASE-007 | Tati — FX agent recruitment/trafficking | CRITICAL | Telegram intel |
| GFIN-CASE-008 | Kyiv call center — crypto fraud | HIGH | Telegram intel |
| GFIN-LAUDR-001 | @btcv123 — laundering, 6 countries | CRITICAL | 6 evidence |
| GFIN-LAUDR-002 | @Karl_Fx — flash crypto scam | MEDIUM | 1 evidence |

**Total evidence items:** 21 (all tied to real cases)

---

## Telegram Intelligence Network

- **Spy Mode:** Telethon user-mode session (account 'Meni', +44 7446378384, ID 8935933339)
- **Groups Monitored:** 32 scam-related Telegram groups
- **Messages Collected:** 78,089 intelligence items
- **Operators Identified:** 86 cross-group operators
- **Real Victims Identified:** 3 (after false-positive cleanup)
  - @Tonytony150 — "almost got scammed" (Gothix AI group)
  - @twelve0099 — "We got scammed" (Gothix AI group)
  - @N0h1D34 — discussing recovery scam dangers

---

## Scammer Network Correlation Map

Cross-entity correlation engine identified **5 scammer networks** linked by shared phones, domains, wallets, and emails:

### Network #1: Sabbir Network (Bangladesh)
- **Operators:** Sabbir26ahmed, Sabbir27ahamed, Sabbirdigitalden
- **Shared phones:** +8801757175803, +8801729792380
- **Groups:** Crypto Forex Jobs, Forex | Crypto | Jobs | Work

### Network #2: Moldova Forex Jobs Network
- **Operators:** antor Babu, fbads455, wallenmgcole
- **Shared domain:** wa.me (WhatsApp links)
- **Phones:** +6285134710169 (Indonesia), +447724099309 (UK)
- **Groups:** Forex Jobs in Moldova, Forex | Crypto | Solutions | Affiliate| Jobs

### Network #3: Shark-Trades Scam Network
- **Operators:** Damilola Adebola, ioanaMzo, twelve0099
- **Shared domain:** shark-trades.com
- **Key finding:** twelve0099 has 10 domains (marsses.com, polygate.tech, apex-option.to, beta-arena.io, profitchips.com, onetrade.ltd, aevos.org, timetrade.live, vellius.com)
- **Groups:** Gothix AI Scammed Users

### Network #4: VoIP Spam Network
- **Operators:** VoipBank, scottie_Spam
- **Shared phone:** +1 (235) 214 8349 (US VoIP)
- **Groups:** Forex Jobs in Moldova

### Network #5: Bitcoin Magazine Scam Network
- **Operators:** Aronjons, jonsonleads
- **Shared domain:** 2fbitcoinmagazine.com
- **Groups:** Forex | Crypto | Jobs | Solutions

---

## Case Evidence — Key Entities Extracted

| Case | Type | Entity | Finding |
|------|------|--------|---------|
| CASE-001 | Domain | cncintelinfo.com | Registered 2024-06-15 via NameCheap, Proton |
| CASE-001 | IP | 91.195.240.123 | AS47846 SEDO GmbH, Munich |
| CASE-001 | Domains | forex-investor.net, forexchanger.com | Linked scam domains |
| CASE-002 | Domain | neex.com | Vlad's investment fraud |
| CASE-003 | Phone | +357 9636 7698 | Cyprus number — TeamForce Technologies |
| CASE-008 | Phone | +380966344929 | Ukraine — Kyiv call center |
| LAUDR-001 | Phone | +852 65836981 | Hong Kong — laundering operation |

---

## Dashboard Architecture

### Sidebar — 3 Clear Sections

**INVESTIGATIONS:**
- Dashboard (overview)
- Cases (10 active investigations)
- Evidence Vault (21 items)
- Laundering (7 channels across 6 countries)
- Operators (86 cross-group operators, entity correlation graph)
- Outreach (victim contact tracking)

**RAW INTELLIGENCE:**
- Telegram (78,089 messages)
- Intel Feed (real-time message stream)
- Wallet Flow (crypto wallet tracking)
- OSINT Engines (6 connectors)
- AI Engines (gpt-5.6-luna model gateway)

**TOOLS:**
- Officer profile / Admin

---

## Security Posture

- **Middleware:** gfin_security.py — blocks SQL injection, XSS, path traversal, command injection, LDAP injection, SSRF
- **Rate Limiting:** 100/min general, 10/min auth
- **Security Headers:** HSTS, CSP, X-Frame, X-Content-Type
- **Nginx:** TLS 1.2/1.3 only, server_tokens off
- **Firewall:** K8s ports closed, only SSH+HTTPS
- **SSH:** Key-only root, password auth disabled, MaxAuthTries 3
- **Fail2ban:** Active
- **Tor:** SOCKS proxy on 127.0.0.1:9050 (exit IP 192.42.116.145)

---

## System Purge — Completed 2026-08-27

### What was purged (ALL GARBAGE):
- 94 GFIN-AUTO-* garbage cases (from feed scrapers)
- 1,667 evidence items tied to garbage cases
- 746 case_entities, 96 investigation_steps, 8 timeline entries
- 67 tracked_domains (noise)
- 152 scam_websites (unverified noise)
- 4 test victims + 4 test complaints + 2 test sessions
- 3 alerts for AUTO cases
- 16,592 false-positive victim flags (scam recruiters misclassified as victims)

### What remains (ALL REAL):
- 10 evidence-based cases
- 21 evidence items
- 78K+ Telegram intelligence items (raw intel)
- 32 monitored groups, 3 real victims, 2 officers
- 189 country routing entries

### Prevention:
- Auto-hunter service stopped and disabled
- Hunter code modified to NEVER create cases from feed discoveries
- Only real victim complaints or Telegram intelligence operations can create cases
- Strict evidence gating: requires victim reports, active drainer infrastructure, or confirmed fraud patterns

---

## Blockers — REQUIRES EXTERNAL ACTION

1. **Production cloud credentials** — Layer B Terraform validated but not provisioned
2. **External penetration testing** — pending
3. **Register more officers** — only 2 currently (GFIN Admin in GB, Det. Insp. Vance in FR)
4. **GitHub push** — needs Personal Access Token for repository updates

---

## Technology Stack

- **Backend:** Python/FastAPI, Go (planned for high-perf)
- **Database:** PostgreSQL 16, Redis 7, Neo4j 5, OpenSearch 2.18
- **Infrastructure:** Docker, Kubernetes (k3s), Kafka 3.7.1, Nginx TLS
- **AI:** OpenAI gpt-5.6-luna via Model Gateway (provider independence)
- **Monitoring:** Prometheus, Grafana
- **Security:** Fail2ban, Tor, Vault, MinIO
- **Telegram:** Telethon user-mode spy (24/7), Telegram Bot (@GFINofficialbot)


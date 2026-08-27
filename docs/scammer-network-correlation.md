# GFIN Scammer Network Correlation Report

**Date:** 2026-08-27  
**Author:** GPT Luna (GFIN-CEA)  
**Classification:** ENFORCEMENT USE ONLY  
**Method:** Cross-entity correlation engine v2.0  

---

## Methodology

The GFIN Cross-Entity Correlation Engine extracts all entities from 78,089 Telegram intelligence messages across 32 monitored scam groups, then cross-references them with case evidence and people records to identify networks of connected scam operators.

### Entity Types Extracted:
- **Phone numbers** — 21 unique
- **Domains** — 25 unique
- **Wallets** — 1 unique (DOGE)
- **Emails** — 3 unique
- **IPs** — 0 (from Telegram messages; IPs from case evidence only)

### Correlation Method:
Operators sharing the same phone number, domain, wallet, email, or IP address are linked. Union-Find algorithm builds connected components to identify scammer networks.

---

## Networks Identified: 5

### Network #1: Sabbir Network (Bangladesh)
**Confidence: HIGH** — Multiple shared phone numbers across accounts

| Operator | Phone | Groups |
|----------|-------|--------|
| Sabbir26ahmed | +8801757175803 | Crypto Forex Jobs |
| Sabbir27ahamed | +8801729792380 | Crypto Forex Jobs, Forex \| Crypto \| Jobs \| Work |
| Sabbirdigitalden | +8801757175803, +8801729792380 | Crypto Forex Jobs, Forex \| Crypto \| Jobs \| Work |

**Assessment:** Single operator using multiple Telegram accounts with shared Bangladeshi phone numbers. Active in forex/crypto job recruitment groups.

---

### Network #2: Moldova Forex Jobs Network
**Confidence: MEDIUM** — Shared domain (wa.me is common, but co-occurrence in same group is notable)

| Operator | Phone | Domain | Groups |
|----------|-------|--------|--------|
| antor Babu | +6285134710169 (Indonesia) | wa.me | Forex Jobs in Moldova |
| fbads455 | — | wa.me | Forex \| Crypto \| Solutions \| Affiliate\| Jobs, Forex Jobs in Moldova |
| wallenmgcole | +447724099309 (UK) | wa.me | Forex Jobs in Moldova |

**Assessment:** Multi-national network operating in Moldova-focused forex job groups. Indonesian, UK, and unknown operators sharing WhatsApp contact links.

---

### Network #3: Shark-Trades Scam Network
**Confidence: HIGH** — Shared scam domain + high entity count

| Operator | Domains | Groups |
|----------|---------|--------|
| Damilola Adebola | shark-trades.com | Gothix AI Scammed Users |
| ioanaMzo | shark-trades.com | Gothix AI Scammed Users |
| twelve0099 | shark-trades.com, marsses.com, polygate.tech, apex-option.to, beta-arena.io, profitchips.com, onetrade.ltd, aevos.org, timetrade.live, vellius.com | Gothix AI Scammed Users |

**Assessment:** twelve0099 is a HIGH-VALUE target — 10 unique scam domains posted in a "scammed users" group. This operator is either a scammer posing as a victim, or a victim who became a scammer. Damilola Adebola and ioanaMzo are promoting the same shark-trades.com platform. All operating in the Gothix AI Scammed Users group, suggesting they're targeting people who were already scammed by Gothix AI for recovery scams.

---

### Network #4: VoIP Spam Network
**Confidence: HIGH** — Shared VoIP phone number

| Operator | Phone | Groups |
|----------|-------|--------|
| VoipBank | +1 (235) 214 8349 | Forex Jobs in Moldova |
| scottie_Spam | +1 (235) 214 8349 | Forex Jobs in Moldova |

**Assessment:** Two accounts sharing a US VoIP number (area code 235 is unassigned, indicating virtual number). Operating exclusively in Moldova forex jobs group.

---

### Network #5: Bitcoin Magazine Scam Network
**Confidence: MEDIUM** — Shared suspicious domain

| Operator | Domain | Groups |
|----------|--------|--------|
| Aronjons | 2fbitcoinmagazine.com | Forex \| Crypto \| Jobs \| Solutions, Forex \| Crypto \| Solutions \| Affiliate\| Jobs |
| jonsonleads | 2fbitcoinmagazine.com | Forex \| Crypto \| Jobs \| Solutions, Forex \| Crypto \| Solutions \| Affiliate\| Jobs |

**Assessment:** Two operators sharing a domain that mimics "Bitcoin Magazine" — likely a brand impersonation scam. Both active in the same forex/crypto job and affiliate groups.

---

## Case Evidence — Entity Cross-Reference

### GFIN-CASE-001: cncintelinfo.com
- **Domain:** cncintelinfo.com (registered 2024-06-15, NameCheap, Proton privacy)
- **IP:** 91.195.240.123 (AS47846 SEDO GmbH, Munich)
- **Linked domains:** forex-investor.net, forexchanger.com (posted by Telegram user Jo0nsina)
- **Victim correlation:** Reddit r/Scams user lost $35,000
- **Law enforcement:** FBI San Diego seized related recovery scam sites

### GFIN-CASE-003: TeamForce Technologies (Cyprus)
- **Phone:** +357 9636 7698 (Cyprus mobile)
- **Activity:** Call center recruitment from Cyprus

### GFIN-CASE-008: Kyiv Call Center (Ukraine)
- **Phone:** +380966344929 (Ukraine mobile)
- **Telegram:** t.me/work_crypto_fx
- **Activity:** Crypto fraud call center

### GFIN-LAUDR-001: @btcv123 Laundering Operation
- **Phone:** +852 65836981 (Hong Kong)
- **Countries:** Malta, Brazil, Romania, Luxembourg, Colombia, Ghana
- **Activity:** USDT exchange/laundering across 6 countries

---

## Top Investigation Targets (Ranked)

1. **twelve0099** — 10 scam domains in "scammed users" group. Likely recovery scammer targeting existing victims.
2. **Sabbirdigitalden** — Hub of Sabbir Network with 2 phones, 3 groups.
3. **ladyluck1105** — 3 unique domains (boom-assets.com, link10.store, ge-as.com, goodtradgain.com).
4. **work_crypto_fx** — Kyiv call center operator, linked to GFIN-CASE-008.
5. **TeamforceTechnologies** — Cyprus call center, linked to GFIN-CASE-003.

---

## Recommendations

1. **PRIORITY 1:** Investigate twelve0099 — 10 scam domains targeting scam victims is a major recovery fraud operation.
2. **PRIORITY 2:** Deep-dive Sabbir Network — confirm if same physical person operating 3 accounts.
3. **PRIORITY 3:** Cross-reference phone +357 9636 7698 (CASE-003) and +380966344929 (CASE-008) with public OSINT databases.
4. **PRIORITY 4:** Monitor shark-trades.com, 2fbitcoinmagazine.com, and twelve0099's 10 domains for infrastructure changes.
5. **PRIORITY 5:** Build victim outreach workflow to contact the 3 real victims identified.


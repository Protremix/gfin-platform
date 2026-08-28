#!/usr/bin/env python3
"""
GFIN Intelligence Integration Layer v1.0
Bridges Telegram intelligence → Hunter v4 → Evidence store.

Problem: Hunter v4 analyzes domains in isolation, ignoring Telegram context.
Solution: Before running Hunter, query Telegram intel for all mentions of the
target domain, build an intel context, and feed it to an enriched scoring engine.

Architecture:
  Telegram Intel DB → Intel Context Builder → Hunter v4 + Context → Enriched Score → Evidence Store
"""
import sys
import json
import hashlib
import re
import time
from datetime import datetime, timezone

sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import psycopg2
from scam_hunter_v4 import ProactiveScamHunterV4


class IntelContextBuilder:
    """Builds intelligence context from Telegram data for a given target."""

    def __init__(self, db_conn):
        self.conn = db_conn

    def build_context(self, domain: str) -> dict:
        """Query Telegram intelligence for all mentions of this domain."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, group_name, message_text, wallets::text, domains::text,
                   phones::text, is_victim, scam_type, risk_level, created_at
            FROM telegram_intelligence
            WHERE domains::text ILIKE %s
            ORDER BY is_victim DESC, created_at DESC
        """, (f"%{domain}%",))
        rows = cur.fetchall()
        cur.close()

        if not rows:
            return {
                "domain": domain,
                "total_mentions": 0,
                "unique_groups": 0,
                "victim_reports": 0,
                "scam_types": {},
                "risk_level": "UNKNOWN",
                "groups": [],
                "has_wallets": False,
                "has_phones": False,
                "telegram_context_score": 0,
            }

        groups = set()
        scam_types = {}
        victim_count = 0
        has_wallets = False
        has_phones = False
        risk_levels = []

        for row in rows:
            _id, group_name, _text, wallets_raw, _domains_raw, phones_raw, is_victim, scam_type, risk_level, _ts = row
            groups.add(group_name or "unknown")
            if is_victim:
                victim_count += 1
            if scam_type:
                scam_types[scam_type] = scam_types.get(scam_type, 0) + 1
            if risk_level:
                risk_levels.append(risk_level)
            # Parse wallets
            try:
                wallets = json.loads(wallets_raw) if isinstance(wallets_raw, str) else (wallets_raw or [])
                if wallets and len(wallets) > 0:
                    has_wallets = True
            except:
                pass
            try:
                phones = json.loads(phones_raw) if isinstance(phones_raw, str) else (phones_raw or [])
                if phones and len(phones) > 0:
                    has_phones = True
            except:
                pass

        # Telegram context score (0-100)
        # - victim reports: +25 each (max 50)
        # - total mentions: +5 each (max 25)
        # - unique groups: +10 each (max 20)
        # - has wallets: +5
        # - has phones: +5
        tcs = 0
        tcs += min(50, victim_count * 25)
        tcs += min(25, len(rows) * 5)
        tcs += min(20, len(groups) * 10)
        if has_wallets:
            tcs += 5
        if has_phones:
            tcs += 5

        # Determine overall risk level
        if victim_count > 0 or any(r == "VICTIM" for r in risk_levels):
            overall_risk = "CRITICAL"
        elif tcs >= 50:
            overall_risk = "HIGH"
        elif tcs >= 25:
            overall_risk = "MEDIUM"
        elif tcs > 0:
            overall_risk = "LOW"
        else:
            overall_risk = "UNKNOWN"

        return {
            "domain": domain,
            "total_mentions": len(rows),
            "unique_groups": len(groups),
            "victim_reports": victim_count,
            "scam_types": scam_types,
            "risk_level": overall_risk,
            "groups": list(groups),
            "has_wallets": has_wallets,
            "has_phones": has_phones,
            "telegram_context_score": tcs,
        }


class EnrichedScorer:
    """Combines Hunter v4 results with Telegram intel context for final scoring."""

    # Scam type mapping: Telegram → Hunter
    TYPE_MAP = {
        "INVESTMENT_FRAUD": "INVESTMENT_SCAM",
        "RECOVERY_SCAM": "CRYPTO_RECOVERY_SCAM",
        "IMPERSONATION": "IMPERSONATION_SCAM",
        "PHISHING": "PHISHING_BANK",
        "ADVANCE_FEE": "CRYPTO_RECOVERY_SCAM",  # closest match
    }

    def __init__(self):
        self.hunter = ProactiveScamHunterV4()

    def investigate_with_context(self, domain: str, intel_context: dict) -> dict:
        """Run Hunter investigation enriched with Telegram intel context."""

        # Run standard Hunter v4
        hunter_result = self.hunter.investigate({"domain": domain})
        entity = hunter_result.get("entity_pipeline", {})
        validation = entity.get("step5_evidence_validation", {})
        discovery = entity.get("step1_source_discovery", {})

        # Base score from Hunter
        hunter_risk = validation.get("risk_score", 0)
        hunter_confidence = validation.get("confidence", 0.0)

        # Telegram context boost
        tcs = intel_context.get("telegram_context_score", 0)
        victim_count = intel_context.get("victim_reports", 0)
        total_mentions = intel_context.get("total_mentions", 0)
        unique_groups = intel_context.get("unique_groups", 0)
        scam_types = intel_context.get("scam_types", {})

        # Enriched risk score: weighted combination
        # Hunter page analysis: 40% weight
        # Telegram intel: 60% weight (because Telegram is our primary intelligence source)
        enriched_risk = int(hunter_risk * 0.4 + tcs * 0.6)

        # Domain name analysis bonus
        domain_lower = domain.lower()
        fraud_keywords = ["trade", "forex", "crypto", "profit", "invest", "fx", "coin", "bit", "hr", "career", "job", "retention"]
        domain_keyword_matches = [kw for kw in fraud_keywords if kw in domain_lower]
        if domain_keyword_matches:
            enriched_risk += min(15, len(domain_keyword_matches) * 5)

        # Registration recency bonus (from Hunter RDAP)
        rdap = discovery.get("data", {}).get("rdap", {})
        reg_date = rdap.get("registration_date", "")
        if reg_date:
            try:
                reg_dt = datetime.fromisoformat(reg_date.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - reg_dt).days
                if days_old < 30:
                    enriched_risk += 20  # Brand new domain
                elif days_old < 90:
                    enriched_risk += 10  # Recent domain
                elif days_old < 365:
                    enriched_risk += 5  # Less than 1 year
            except:
                pass

        # Dead domain but has Telegram mentions = likely taken down after scam
        page_data = discovery.get("data", {}).get("page", {})
        has_page = bool(page_data and page_data.get("status"))
        if not has_page and total_mentions > 0:
            enriched_risk += 15  # Dead domain with fraud mentions

        # Cap at 100
        enriched_risk = min(100, enriched_risk)

        # Enriched confidence
        enriched_confidence = min(1.0, enriched_risk / 100)

        # Determine accusation level
        if enriched_risk >= 80:
            accusation = "SUPPORTED_BY_EVIDENCE"
        elif enriched_risk >= 50:
            accusation = "REQUIRES_INVESTIGATION"
        elif enriched_risk >= 25:
            accusation = "SUSPICIOUS"
        elif enriched_risk > 0:
            accusation = "SUSPICIOUS"
        else:
            accusation = "NOT_ESTABLISHED"

        # Map Telegram scam types to Hunter types for display
        mapped_types = []
        for tg_type, count in scam_types.items():
            mapped = self.TYPE_MAP.get(tg_type, tg_type)
            mapped_types.append({"telegram_type": tg_type, "hunter_type": mapped, "count": count})

        return {
            "domain": domain,
            "hunter_risk_score": hunter_risk,
            "hunter_confidence": hunter_confidence,
            "telegram_context_score": tcs,
            "enriched_risk_score": enriched_risk,
            "enriched_confidence": enriched_confidence,
            "accusation_level": accusation,
            "intel_context": intel_context,
            "hunter_result": hunter_result,
            "domain_keyword_matches": domain_keyword_matches,
            "registration_age_days": int((datetime.now(timezone.utc) - datetime.fromisoformat(reg_date.replace("Z", "+00:00"))).days) if reg_date else None,
            "scam_types_mapped": mapped_types,
            "sources_checked": discovery.get("sources_checked", []),
            "sources_found": discovery.get("sources_found", []),
            "rdap_data": rdap,
            "urlscan_data": discovery.get("data", {}).get("urlscan", {}),
            "page_data": {"status": page_data.get("status", 0), "content_length": page_data.get("content_length", 0)} if page_data else {},
            "wayback_data": discovery.get("data", {}).get("wayback", {}),
        }


class EvidenceStore:
    """Creates real evidence records from enriched investigation results."""

    def __init__(self, db_conn):
        self.conn = db_conn

    def store_evidence(self, case_id: str, enriched_result: dict) -> int:
        """Create evidence items from the enriched investigation."""
        cur = self.conn.cursor()
        domain = enriched_result["domain"]
        ev_count = 0

        def _insert(eid, phase, finding, provider, stype, confidence, content, endpoint, query, ref, hist):
            ch = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
            cur.execute("""INSERT INTO evidence (
                evidence_id, case_id, phase, finding, source_provider, source_type, confidence,
                content_hash, timestamp, created_date, added_date, lifecycle_status, found_at,
                provenance_source, provenance_provider, provenance_endpoint, provenance_query,
                provenance_original_ref, provenance_content_hash, provenance_processing_history,
                provenance_collector, provenance_complete
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW(),NOW(),'FOUND',NOW(),
              %s,%s,%s,%s,%s,%s,%s,'GFIN-INTEL-LAYER',true) ON CONFLICT DO NOTHING""",
                (eid, case_id, phase, finding, provider, stype, confidence, ch,
                 provider.lower(), provider, endpoint, query, ref, ch, json.dumps(hist)))
            return 1

        def _eid():
            return "EVD-ENR-{}-{:04d}".format(case_id, ev_count)

        # 1. Telegram Intelligence Context Evidence
        ctx = enriched_result.get("intel_context", {})
        if ctx.get("total_mentions", 0) > 0:
            finding = "Telegram Intel: {} mentioned {}x across {} groups, {} victim reports, scam types: {}".format(
                domain, ctx["total_mentions"], ctx["unique_groups"], ctx["victim_reports"],
                ", ".join(["{}({})".format(k, v) for k, v in ctx["scam_types"].items()]))
            ev_count += _insert(_eid(), "INTEL_CONTEXT", finding,
                "TELEGRAM_INTELLIGENCE", "telegram", 0.85, ctx,
                "telegram_intelligence_db", "domain:{}".format(domain),
                "telegram_mentions:{}".format(domain),
                ["telegram_query", "mention_count", "victim_check", "scam_type_aggregation", "evidence_created"])

        # 2. RDAP/WHOIS Evidence
        rdap = enriched_result.get("rdap_data", {})
        if rdap:
            reg_date = rdap.get("registration_date", "")
            days = enriched_result.get("registration_age_days")
            age_str = " ({} days old)".format(days) if days is not None else ""
            finding = "RDAP/WHOIS: {} registered on {}{}".format(domain, reg_date, age_str)
            ev_count += _insert(_eid(), "WHOIS", finding,
                "ICANN_RDAP", "api", 0.9, rdap,
                "https://rdap.org/domain/{}".format(domain), "domain:{}".format(domain),
                "rdap:{}".format(domain), ["rdap_lookup", "registration_date_extract", "age_analysis", "evidence_created"])

        # 3. URLScan Infrastructure Evidence
        urlscan = enriched_result.get("urlscan_data", {})
        if urlscan:
            finding = "URLScan: {} on {} ({}) in {}".format(
                domain, urlscan.get("ip", "?"), urlscan.get("server", "?"), urlscan.get("country", "?"))
            ev_count += _insert(_eid(), "INFRA", finding,
                "URLSCAN_IO", "api", 0.85, urlscan,
                "https://urlscan.io/api/v1/search/?q=domain:{}".format(domain), "domain:{}".format(domain),
                "urlscan:{}".format(domain), ["urlscan_search", "infrastructure_analysis", "evidence_created"])

        # 4. Page Content Evidence
        page = enriched_result.get("page_data", {})
        if page.get("status"):
            finding = "Page Content: {} returned HTTP {} with {} bytes".format(
                domain, page.get("status", "?"), page.get("content_length", 0))
            ev_count += _insert(_eid(), "CONTENT", finding,
                "GFIN_HUNTER", "crawler", 0.8, page,
                "https://{}".format(domain), "domain:{}".format(domain),
                "page:{}".format(domain), ["http_fetch", "content_analysis", "evidence_created"])

        # 5. Dead Domain Evidence
        if not page.get("status") and ctx.get("total_mentions", 0) > 0:
            finding = "Dead Domain: {} has no live website but {} Telegram mentions. Likely taken down after fraudulent activity.".format(
                domain, ctx["total_mentions"])
            ev_count += _insert(_eid(), "INFRA", finding,
                "GFIN_HUNTER", "analysis", 0.85,
                {"domain": domain, "has_page": False, "telegram_mentions": ctx["total_mentions"]},
                "dns:{}".format(domain), "domain:{}".format(domain),
                "dead_domain:{}".format(domain), ["dns_lookup", "http_check", "telegram_correlation", "evidence_created"])

        # 6. Domain Name Pattern Evidence
        kw_matches = enriched_result.get("domain_keyword_matches", [])
        if kw_matches:
            finding = "Domain Name Analysis: {} contains fraud-associated keywords: {}".format(
                domain, ", ".join(kw_matches))
            ev_count += _insert(_eid(), "DOMAIN_ANALYSIS", finding,
                "GFIN_INTEL_LAYER", "analysis", 0.6,
                {"domain": domain, "matched_keywords": kw_matches},
                "domain_name:{}".format(domain), "domain:{}".format(domain),
                "keyword_match:{}".format(domain), ["domain_name_analysis", "keyword_match", "evidence_created"])

        # 7. Scam Type Correlation Evidence
        scam_types = enriched_result.get("scam_types_mapped", [])
        if scam_types:
            finding = "Scam Type Correlation: Telegram classifies as {}".format(
                ", ".join(["{} ({}x, maps to {})".format(s["telegram_type"], s["count"], s["hunter_type"]) for s in scam_types]))
            ev_count += _insert(_eid(), "CORRELATION", finding,
                "GFIN_INTEL_LAYER", "analysis", 0.8,
                {"scam_types": scam_types, "domain": domain},
                "scam_type_mapping:{}".format(domain), "domain:{}".format(domain),
                "type_correlation:{}".format(domain), ["telegram_classification", "hunter_type_mapping", "correlation", "evidence_created"])

        # 8. Enriched Risk Assessment Evidence (always created)
        finding = "Enriched Risk Assessment: {} — risk={}, confidence={:.2f}, telegram_score={}, hunter_score={}".format(
            enriched_result["accusation_level"], enriched_result["enriched_risk_score"],
            enriched_result["enriched_confidence"], enriched_result["telegram_context_score"],
            enriched_result["hunter_risk_score"])
        ev_count += _insert(_eid(), "RISK_ASSESSMENT", finding,
            "GFIN_INTEL_LAYER", "analysis", enriched_result["enriched_confidence"],
            {"enriched_risk": enriched_result["enriched_risk_score"],
             "enriched_confidence": enriched_result["enriched_confidence"],
             "accusation_level": enriched_result["accusation_level"],
             "telegram_context_score": enriched_result["telegram_context_score"],
             "hunter_risk_score": enriched_result["hunter_risk_score"],
             "victim_reports": ctx.get("victim_reports", 0),
             "total_mentions": ctx.get("total_mentions", 0)},
            "enriched_score:{}".format(domain), "domain:{}".format(domain),
            "risk_assessment:{}".format(domain),
            ["hunter_v4", "telegram_context", "domain_analysis", "registration_check", "enriched_scoring", "evidence_created"])

        self.conn.commit()
        cur.close()
        return ev_count


def run_enriched_investigations():
    """Main entry: run enriched investigations for all telegram_intelligence cases."""
    DB_CONFIG = {"host": "127.0.0.1", "database": "gfin", "user": "gfin", "password": "GfinSecure2026!"}
    db = psycopg2.connect(**DB_CONFIG)

    # Get all telegram_intelligence cases
    cur = db.cursor()
    cur.execute("SELECT case_id, target FROM cases WHERE trigger = 'telegram_intelligence' ORDER BY case_id")
    cases = cur.fetchall()
    cur.close()

    sep = "=" * 60
    print(sep)
    print("GFIN INTELLIGENCE INTEGRATION LAYER v1.0")
    print("Enriched Investigations: Hunter v4 + Telegram Context")
    print(sep)
    print("Cases to investigate: {}".format(len(cases)))

    # First: delete old EVD-INV evidence (from previous run)
    cur = db.cursor()
    cur.execute("DELETE FROM evidence WHERE evidence_id LIKE 'EVD-INV-%' OR evidence_id LIKE 'EVD-ENR-%'")
    deleted = cur.rowcount
    db.commit()
    cur.close()
    print("Cleaned {} old investigation evidence items".format(deleted))

    # Initialize components
    ctx_builder = IntelContextBuilder(db)
    scorer = EnrichedScorer()
    store = EvidenceStore(db)

    total_evidence = 0

    for case_id, target in cases:
        domain = target.strip()
        print("\n" + "-" * 40)
        print("CASE: {} | DOMAIN: {}".format(case_id, domain))

        # Build Telegram context
        ctx = ctx_builder.build_context(domain)
        print("  Telegram: {} mentions, {} groups, {} victims, score={}".format(
            ctx["total_mentions"], ctx["unique_groups"], ctx["victim_reports"], ctx["telegram_context_score"]))

        # Run enriched investigation
        result = scorer.investigate_with_context(domain, ctx)
        print("  Hunter risk: {} | Telegram score: {} | Enriched risk: {} | Confidence: {:.2f}".format(
            result["hunter_risk_score"], result["telegram_context_score"],
            result["enriched_risk_score"], result["enriched_confidence"]))
        print("  Accusation: {}".format(result["accusation_level"]))

        if result.get("registration_age_days") is not None:
            print("  Domain age: {} days".format(result["registration_age_days"]))

        if result.get("domain_keyword_matches"):
            print("  Domain keywords: {}".format(result["domain_keyword_matches"]))

        # Store evidence
        ev_count = store.store_evidence(case_id, result)
        print("  Evidence created: {}".format(ev_count))
        total_evidence += ev_count

        # Update case confidence
        cur = db.cursor()
        cur.execute("UPDATE cases SET confidence = %s WHERE case_id = %s",
            (result["enriched_confidence"], case_id))
        db.commit()
        cur.close()

    # Final summary
    print("\n" + sep)
    print("ENRICHED INVESTIGATION COMPLETE")
    print(sep)

    cur = db.cursor()
    cur.execute("""SELECT c.case_id, c.target, c.priority, c.confidence,
                   COUNT(e.id) as evidence_count
                   FROM cases c LEFT JOIN evidence e ON c.case_id = e.case_id
                   WHERE c.trigger = 'telegram_intelligence'
                   GROUP BY c.case_id, c.target, c.priority, c.confidence
                   ORDER BY c.confidence DESC""")
    print("\n{:<18} {:<30} {:<10} {:<8} {:<8}".format("CASE", "TARGET", "PRIORITY", "CONF", "EVIDENCE"))
    print("-" * 80)
    for r in cur.fetchall():
        print("{:<18} {:<30} {:<10} {:<8.2f} {:<8}".format(r[0], r[1][:30], r[2], float(r[3]), r[4]))
    cur.close()

    # System-wide stats
    cur = db.cursor()
    cur.execute("SELECT COUNT(*), AVG(confidence::numeric)::numeric(4,2) FROM cases")
    stats = cur.fetchone()
    print("\nSystem: {} cases, avg confidence: {}".format(stats[0], stats[1]))
    cur.close()

    db.close()
    print("Total new evidence: {}".format(total_evidence))
    return total_evidence


if __name__ == "__main__":
    run_enriched_investigations()

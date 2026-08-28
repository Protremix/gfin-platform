"""
GFIN Standalone Server v2.0
Fully autonomous fraud intelligence server — no Base44 dependency.

Features:
- Victim registration, login, complaint filing with file uploads
- Auto-investigation trigger on complaint submission
- Victim tracking dashboard (separate from police view)
- Police notifications to victims
- Local scam pattern detection engine (no AI needed)
- All connectors (public APIs, no tokens required)
- PostgreSQL local storage
- Serves both police dashboard and victim portal
"""
from gfin_anomaly_detector import anomaly_detector
from gfin_misp_integration import misp_integration
from gfin_midas import midas_pipeline
from midas_alert_bridge import midas_alert_bridge
from gfin_logging import setup_logging, get_logger, create_request_logger
import os, sys, json, time, hashlib, logging, secrets, shutil
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

sys.path.insert(0, '/gfin')
sys.path.insert(0, '/gfin/packages/services')
try:
    from scam_engine_v3 import DeterministicScamEngine
except Exception as e:
    print(f"Warning: v3 engine not loaded: {e}")
try:
    import police_auth
    from police_auth import (generate_token, verify_token, hash_password, verify_password, validate_refresh_token, generate_refresh_token, revoke_token, revoke_all_tokens, init_auth_tables,
        auth_police, auth_police_admin, rate_limiter, POLICE_LOGIN_HTML, POLICE_SCHEMA)
    _police_auth = True
    try:
        init_auth_tables()
    except:
        pass
except Exception as e:
    _police_auth = False
    print(f"Warning: police auth not loaded: {e}")
try:
    from telegram_alerts import broadcast_scam_alert, get_bot, process_bot_updates
    _telegram = True
except Exception as e:
    _telegram = False
    print(f"Warning: telegram alerts not loaded: {e}")
try:
    from scam_awareness import send_awareness_broadcast, get_awareness_stats, send_custom_awareness, SCAM_AWARENESS_MESSAGES
    _awareness = True
except Exception as e:
    _awareness = False
    print(f"Warning: scam awareness not loaded: {e}")
try:
    from scam_sites_db import init_scam_sites_table, add_scam_website, check_domain, list_scam_sites, search_scam_sites, get_scam_sites_stats, format_check_result_telegram
    init_scam_sites_table()
    _scam_sites = True
except Exception as e:
    _scam_sites = False
    print(f"Warning: scam sites db not loaded: {e}")
try:
    from pdf_reports import generate_case_report, hash_evidence, create_chain_of_custody, generate_evidence_receipt
    _pdf_reports = True
except Exception as e:
    _pdf_reports = False
    print(f"Warning: pdf reports not loaded: {e}")
try:
    from dashboard_analytics import get_overview, get_scam_types, get_risk_levels, get_countries, get_timeline, get_financial_loss, get_crypto_analytics
    _analytics = True
except Exception as e:
    _analytics = False
    print(f"Warning: dashboard analytics not loaded: {e}")
try:
    from victim_notifications import notify_victim, send_email, get_notification_template
    _notifications = True
except Exception as e:
    _notifications = False
    print(f"Warning: victim notifications not loaded: {e}")
try:
    from intelligence_playbook_v52 import IntelligencePlaybook as Playbook
    _playbook = Playbook()
except Exception as e:
    _playbook = None
    print(f"Warning: playbook not loaded: {e}")
sys.path.insert(0, '/gfin/packages')

from fastapi import FastAPI, HTTPException, Query, Body, Depends, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import asyncpg

# --- Configuration ---
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "gfin")
DB_NAME = os.getenv("DB_NAME", "gfin")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_CONFIG = {"host": DB_HOST, "port": DB_PORT, "user": DB_USER, "password": DB_PASSWORD, "database": DB_NAME}
EVIDENCE_UPLOAD_DIR = Path("/gfin/evidence_uploads")
EVIDENCE_UPLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("gfin.server")

db_pool: Optional[asyncpg.Pool] = None

# ==================== DATABASE SCHEMA ====================

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME,
        min_size=2, max_size=10
    )
    async with db_pool.acquire() as conn:
        # Existing tables from v1.0
        await conn.execute("""CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY, case_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'INVESTIGATING', target TEXT, target_type TEXT,
            trigger TEXT DEFAULT 'PUBLIC_REPORT', summary TEXT, subject_reason TEXT,
            classification TEXT DEFAULT 'LAW ENFORCEMENT SENSITIVE', accusation_level TEXT,
            confidence REAL DEFAULT 0.0, scam_patterns TEXT[], scam_indicators JSONB DEFAULT '[]',
            affected_countries TEXT[], routed_to_countries TEXT[],
            physical_locations JSONB DEFAULT '[]', financial_indicators JSONB DEFAULT '[]',
            digital_identifiers JSONB DEFAULT '[]', evidence_chain JSONB DEFAULT '[]',
            victim_count INT DEFAULT 0, victim_loss TEXT,
            created_date TIMESTAMPTZ DEFAULT NOW(), updated_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS people (
            id SERIAL PRIMARY KEY, case_id TEXT NOT NULL, role TEXT NOT NULL,
            name TEXT NOT NULL, entity_type TEXT, details TEXT,
            is_verified BOOLEAN DEFAULT FALSE, source TEXT, confidence TEXT DEFAULT 'UNVERIFIED',
            created_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS evidence (
            id SERIAL PRIMARY KEY, case_id TEXT NOT NULL, evidence_id TEXT UNIQUE NOT NULL,
            phase TEXT, finding TEXT, source_provider TEXT, source_url TEXT, source_type TEXT,
            confidence TEXT DEFAULT 'MEDIUM', content_hash TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW(), created_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY, alert_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL,
            country TEXT NOT NULL, level TEXT NOT NULL, message TEXT, next_action TEXT,
            police_contact TEXT, delivery_status TEXT DEFAULT 'PENDING',
            delivery_timestamp TIMESTAMPTZ, routed_from TEXT DEFAULT 'GFIN_AUTOMATED_ROUTING',
            target TEXT, created_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS country_routing (
            id SERIAL PRIMARY KEY, country_code TEXT UNIQUE NOT NULL,
            country_name TEXT NOT NULL, contacts JSONB DEFAULT '[]',
            europol_contact TEXT, interpol_contact TEXT, languages TEXT[], timezone TEXT
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS police_officers (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'investigator',
            agency TEXT NOT NULL,
            country_code TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            badge_number TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMPTZ DEFAULT NOW(),
            last_login TIMESTAMPTZ,
            approved_by TEXT DEFAULT 'SYSTEM'
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY, case_id TEXT, action TEXT, actor TEXT,
            tool TEXT, query TEXT, result TEXT, evidence_id TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY, key_hash TEXT UNIQUE NOT NULL, agency TEXT NOT NULL,
            jurisdiction TEXT, scope TEXT[], is_active BOOLEAN DEFAULT TRUE,
            created_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        await conn.execute("""CREATE TABLE IF NOT EXISTS search_cache (
            id SERIAL PRIMARY KEY, query_hash TEXT UNIQUE NOT NULL, query TEXT,
            results JSONB, connector TEXT, created_date TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ
        )""")

        # NEW v2.0 — Victim tables
        await conn.execute("""CREATE TABLE IF NOT EXISTS victims (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            country TEXT,
            phone TEXT,
            is_verified BOOLEAN DEFAULT FALSE,
            created_date TIMESTAMPTZ DEFAULT NOW()
        )""")
        
        await conn.execute("""CREATE TABLE IF NOT EXISTS victim_complaints (
            id SERIAL PRIMARY KEY,
            reference_number TEXT UNIQUE NOT NULL,
            victim_id INT NOT NULL,
            case_id TEXT,
            scam_type TEXT NOT NULL,
            target TEXT NOT NULL,
            incident_date DATE,
            financial_loss TEXT,
            description TEXT,
            investigation_stage TEXT DEFAULT 'RECEIVED',
            country TEXT,
            auto_investigation_started BOOLEAN DEFAULT FALSE,
            created_date TIMESTAMPTZ DEFAULT NOW(),
            updated_date TIMESTAMPTZ DEFAULT NOW()
        )""")

        await conn.execute("""CREATE TABLE IF NOT EXISTS complaint_files (
            id SERIAL PRIMARY KEY,
            complaint_ref TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_size INT,
            mime_type TEXT,
            uploaded_date TIMESTAMPTZ DEFAULT NOW()
        )""")

        await conn.execute("""CREATE TABLE IF NOT EXISTS victim_notifications (
            id SERIAL PRIMARY KEY,
            complaint_ref TEXT NOT NULL,
            victim_id INT NOT NULL,
            message TEXT NOT NULL,
            from_agency TEXT DEFAULT 'GFIN System',
            is_read BOOLEAN DEFAULT FALSE,
            created_date TIMESTAMPTZ DEFAULT NOW()
        )""")

        await conn.execute("""CREATE TABLE IF NOT EXISTS victim_sessions (
            token TEXT PRIMARY KEY,
            victim_id INT NOT NULL,
            created_date TIMESTAMPTZ DEFAULT NOW(),
            expires_at TIMESTAMPTZ
        )""")

        logger.info("Database tables initialized (v2.0)")


# ==================== SCAM PATTERN DETECTION ENGINE ====================

SCAM_PATTERNS = {
    "RECOVERY_SCAM": [
        r"recover(y)?\s+(your\s+)?(lost\s+)?(funds|money|crypto|bitcoin)",
        r"we\s+can\s+help\s+you\s+get\s+your\s+money\s+back",
        r"chargeback\s+(service|guarantee|fee)",
        r"recovery\s+(expert|specialist|agent|service)",
        r"100%\s+(guaranteed|success)\s+recovery",
        r"no\s+win\s+no\s+fee",
        r"(pay|fee)\s+(upfront|in\s+advance|first)",
    ],
    "INVESTMENT_FRAUD": [
        r"guaranteed\s+(returns?|profit|ROI)",
        r"\d{3}%\s+(return|profit|ROI)",
        r"(binary|forex|crypto)\s+(trading|investment)\s+platform",
        r"send\s+(bitcoin|crypto|usdt|eth)\s+to\s+(this|our)\s+(wallet|address)",
        r"minimum\s+(investment|deposit)\s+of\s+\$?\d+",
        r"double\s+your\s+(bitcoin|crypto|money)\s+in\s+\d+\s+hours",
    ],
    "BRAND_IMPERSONATION": [
        r"(official|authorized|certified|genuine)\s+(recovery|investigation|legal)\s+(agent|service|company)",
        r"we\s+are\s+(the|a)\s+(legitimate|real|original)\s+(recovery|investigation)\s+(company|firm|agency)",
        r"(contact|call|email)\s+(us|me)\s+(urgently|immediately|now)",
        r"(limited|special)\s+(time|offer)\s+(offer|promotion|discount)",
    ],
    "PHISHING": [
        r"(verify|confirm|update)\s+your\s+(account|wallet|identity|information)",
        r"(your\s+account\s+(has\s+been|will\s+be)\s+(suspended|locked|closed))",
        r"(click\s+here|follow\s+this\s+link)\s+to\s+(verify|confirm|update)",
        r"dear\s+(customer|user|client|valued\s+customer)",
    ],
    "ROMANCE_SCAM": [
        r"(i\s+love\s+you|i'm\s+falling\s+for\s+you|you're\s+the\s+one)",
        r"(stuck|stranded)\s+in\s+(the\s+)?\w+\s+(need\s+help|send\s+money)",
        r"(military|army|navy|UN\s+soldier|doctor)\s+(stationed|deployed)\s+in",
        r"(widow|widower|orphan)\s+(seeking|looking\s+for)",
        r"(send\s+me\s+money|i\s+need\s+a\s+loan|can\s+you\s+help\s+me\s+financially)",
    ],
}

# Known scam domain patterns (checked against domain registrations)
SCAM_DOMAIN_INDICATORS = [
    "recovery", "payback", "claimback", "refund", "retrieve",
    "hack-back", "hackback", "crypto-recovery", "fund-recovery",
    "bitcoin-recovery", "scam-recovery", "chargeback",
]

# Legitimate financial regulators / references (not scams)
LEGITIMATE_REFERENCES = [
    "fca.org.uk", "sec.gov", "esma.europa.eu", "bafin.de",
    "actionfraud.police.uk", "fbi.gov", "ic3.gov",
    "consumerfinance.gov", "ftc.gov",
]


class ScamDetectionEngine:
    """Local scam detection engine — no AI dependency."""

    @staticmethod
    def detect_scam_patterns(text: str) -> Dict[str, Any]:
        """Detect scam patterns in text using regex. Returns patterns found + risk score."""
        import re
        text_lower = text.lower()
        patterns_found = []
        categories_hit = set()

        for category, patterns in SCAM_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    patterns_found.append({
                        "category": category,
                        "pattern": pattern,
                        "match_count": len(matches),
                        "sample": matches[0][:100] if matches else ""
                    })
                    categories_hit.add(category)

        # Check for scam domain indicators in target
        for indicator in SCAM_DOMAIN_INDICATORS:
            if indicator in text_lower:
                if "DOMAIN_INDICATOR" not in categories_hit:
                    categories_hit.add("DOMAIN_INDICATOR")
                    patterns_found.append({
                        "category": "DOMAIN_INDICATOR",
                        "pattern": indicator,
                        "match_count": 1,
                        "sample": indicator
                    })

        # Check for crypto wallet addresses
        btc_pattern = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', text)
        eth_pattern = re.findall(r'0x[a-fA-F0-9]{40}', text)
        if btc_pattern:
            patterns_found.append({"category": "CRYPTO_WALLET", "pattern": "BTC", "match_count": len(btc_pattern), "sample": btc_pattern[0]})
            categories_hit.add("CRYPTO_WALLET")
        if eth_pattern:
            patterns_found.append({"category": "CRYPTO_WALLET", "pattern": "ETH", "match_count": len(eth_pattern), "sample": eth_pattern[0]})
            categories_hit.add("CRYPTO_WALLET")

        # Risk scoring
        risk_score = min(len(categories_hit) * 0.2 + len(patterns_found) * 0.05, 1.0)
        risk_level = "LOW"
        if risk_score > 0.7: risk_level = "CRITICAL"
        elif risk_score > 0.5: risk_level = "HIGH"
        elif risk_score > 0.3: risk_level = "MEDIUM"

        # Check for legitimate references (reduces risk)
        for ref in LEGITIMATE_REFERENCES:
            if ref in text_lower:
                risk_score = max(0, risk_score - 0.1)

        return {
            "patterns_found": patterns_found,
            "categories_hit": list(categories_hit),
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "pattern_count": len(patterns_found)
        }

    @staticmethod
    def extract_indicators(text: str, target: str) -> Dict[str, Any]:
        """Extract investigative indicators from complaint text."""
        import re
        indicators = {
            "domains": [],
            "emails": [],
            "phones": [],
            "crypto_wallets": [],
            "urls": [],
            "social_media": []
        }

        # Domains
        domains = re.findall(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}', text)
        indicators["domains"] = list(set(domains))[:20]

        # Emails
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        indicators["emails"] = list(set(emails))[:20]

        # Phone numbers
        phones = re.findall(r'\+?\d{1,4}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{3,4}', text)
        indicators["phones"] = list(set(phones))[:10]

        # Crypto wallets
        btc = re.findall(r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}', text)
        eth = re.findall(r'0x[a-fA-F0-9]{40}', text)
        indicators["crypto_wallets"] = list(set(btc + eth))[:10]

        # URLs
        urls = re.findall(r'https?://[^\s<>"\')]+', text)
        indicators["urls"] = list(set(urls))[:20]

        # Social media handles
        social = re.findall(r'@(?:telegram|signal|whatsapp)[^\s]+', text, re.IGNORECASE)
        telegram = re.findall(r't\.me/[^\s]+', text)
        indicators["social_media"] = list(set(social + telegram))[:10]

        return indicators


# ==================== CONNECTOR LOADING ====================

def load_connectors():
    """Load all available connectors — pure Python, no Base44 tokens."""
    connectors = {}
    try:
        sys.path.insert(0, '/gfin/packages/connectors')
        from connectors import BAILIIConnector, UKTribunalConnector, GitHubConnector
        connectors["bailii"] = BAILIIConnector()
        connectors["uk-tribunals"] = UKTribunalConnector()
        connectors["github"] = GitHubConnector()
    except Exception as e:
        logger.warning(f"Base connectors: {e}")
    try:
        from expanded_connectors import SECEdgarConnector, ICIJConnector, GDELTConnector
        connectors["sec-edgar"] = SECEdgarConnector()
        connectors["icij"] = ICIJConnector()
        connectors["gdelt"] = GDELTConnector()
    except Exception as e:
        logger.warning(f"Expanded connectors: {e}")
    return connectors


# ==================== AUTO-INVESTIGATION ====================

async def run_auto_investigation(complaint_ref: str, target: str, scam_type: str, description: str):
    """Automatically start investigation when a complaint is filed."""
    logger.info(f"Auto-investigation started for {complaint_ref} — target: {target}")

    async with db_pool.acquire() as conn:
        # Create a case linked to the complaint
        # Reject test/health-check complaints — don't create garbage cases
        complaint_text = (scam_report or "").lower()
        target_domain = (domain or "").lower()
        is_test = any(t in complaint_text or t in target_domain for t in [
            'test complaint', 'health check', 'test', 'api-test', 'evil-phishing',
            'romance-scam-test', 'crypto-invest-scam', 'final health check',
            'test complaint via api'
        ])

        if is_test:
            logger.info(f"Test complaint rejected — not creating case: {domain}")
            return {
                "status": "rejected",
                "reason": "Test data — not a real complaint",
                "scam_analysis": scam_analysis
            }

        case_id = f"GFIN-AUTO-{int(time.time())}"
        scam_analysis_result = DeterministicScamEngine.analyze(description, target)
        scam_analysis = scam_analysis_result['summary']
        scam_report = scam_analysis_result['report']
        scam_entities = scam_analysis_result['entities']
        indicators = scam_entities

        # Determine affected countries based on indicators
        countries = []
        victim_row = await conn.fetchrow(
            "SELECT v.country FROM victims v JOIN victim_complaints c ON c.victim_id = v.id WHERE c.reference_number = $1",
            complaint_ref
        )
        if victim_row and victim_row["country"]:
            countries.append(victim_row["country"])

        # Insert case
        await conn.execute(
            """INSERT INTO cases (case_id, target, target_type, trigger, summary, status, confidence,
               scam_patterns, affected_countries, routed_to_countries, victim_count,
               scam_indicators, digital_identifiers)
               VALUES ($1, $2, 'COMPLAINT', $3, $4, 'INVESTIGATING', $5, $6, $7, $8, 1, $9, $10)""",
            case_id, target, f"Victim complaint: {scam_type}",
            description[:500], scam_analysis["risk_score"],
            scam_analysis["categories_detected"], countries,
            countries + ["EUROPOL", "INTERPOL"],
            json.dumps(scam_analysis_result), json.dumps(indicators)
        )

        # Link case to complaint
        await conn.execute(
            "UPDATE victim_complaints SET case_id=$1, auto_investigation_started=TRUE, investigation_stage='UNDER_REVIEW' WHERE reference_number=$2",
            case_id, complaint_ref
        )

        # Log to audit
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "AUTO_INVESTIGATION_STARTED", "GFIN_SCAM_ENGINE", "local_detection",
            target, f"Risk: {scam_analysis['risk_level']} ({scam_analysis['risk_score']}), Patterns: {scam_analysis['pattern_count']}"
        )

        # Save detection evidence
        evidence_id = f"E-AUTO-001"
        await conn.execute(
            "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            case_id, evidence_id, "PATTERN_DETECTION",
            f"GFIN Scam Engine v3.0: {scam_analysis['risk_level']} risk, {scam_analysis['pattern_count']} patterns, {scam_analysis['behavioral_indicators']} behavioral indicators, {scam_analysis['pattern_count']} patterns found. Categories: {', '.join(scam_analysis['categories_detected'])}",
            "GFIN Scam Engine v3.0 (local)", "internal", "Deterministic pattern matching + behavioral heuristics", "HIGH"
        )

        # Save indicator extraction
        evidence_id2 = f"E-AUTO-002"
        indicators_summary = []
        for k, v in indicators.items():
            if v: indicators_summary.append(f"{k}: {len(v)} found")
        await conn.execute(
            "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            case_id, evidence_id2, "INDICATOR_EXTRACTION",
            f"Extracted: {'; '.join(indicators_summary)}",
            "GFIN Scam Engine (local)", "internal", "Regex extraction", "HIGH"
        )

        # Update stage to INVESTIGATING
        await conn.execute(
            "UPDATE victim_complaints SET investigation_stage='INVESTIGATING', updated_date=NOW() WHERE reference_number=$1",
            complaint_ref
        )

        # Run connectors in background (best effort)
        connectors = load_connectors()
        connector_results = 0
        for name, connector in connectors.items():
            try:
                result = connector.query(search_term=target)
                if result.success:
                    connector_results += 1
                    ev_id = f"E-CONN-{connector_results:03d}"
                    finding_text = str(result.data)[:500] if result.data else "Data retrieved"
                    await conn.execute(
                        "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence, content_hash) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                        case_id, ev_id, "CONNECTOR_SEARCH", finding_text,
                        connector.provider, result.provenance, connector.source_class,
                        "HIGH" if result.quality_score > 0.5 else "MEDIUM", result.content_hash
                    )
            except Exception as e:
                logger.warning(f"Connector {name} failed: {e}")

        # Update stage to EVIDENCE_COLLECTED
        await conn.execute(
            "UPDATE victim_complaints SET investigation_stage='EVIDENCE_COLLECTED', updated_date=NOW() WHERE reference_number=$1",
            complaint_ref
        )

        # Route to police based on country
        if countries:
            for country in countries:
                alert_id = f"ALERT-{complaint_ref}-{country}"
                level = scam_analysis["risk_level"]
                message = f"New victim complaint: {scam_type} targeting {target}. Risk: {level}. Auto-investigation completed with {connector_results + 2} evidence items."
                await conn.execute(
                    "INSERT INTO alerts (alert_id, case_id, country, level, message, next_action, target) VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT (alert_id) DO NOTHING",
                    alert_id, case_id, country, level, message,
                    "Review auto-investigation evidence. Contact victim for additional information if needed.",
                    target
                )

            # Also route to EUROPOL and INTERPOL for cross-border
            for org in ["EUROPOL", "INTERPOL"]:
                alert_id = f"ALERT-{complaint_ref}-{org}"
                await conn.execute(
                    "INSERT INTO alerts (alert_id, case_id, country, level, message, target) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (alert_id) DO NOTHING",
                    alert_id, case_id, org, "MEDIUM",
                    f"Cross-border complaint: {scam_type} — {target}. Affected: {', '.join(countries)}",
                    target
                )

        # Update stage to ROUTED_TO_POLICE
        await conn.execute(
            "UPDATE victim_complaints SET investigation_stage='ROUTED_TO_POLICE', updated_date=NOW() WHERE reference_number=$1",
            complaint_ref
        )

        # Notify victim
        await conn.execute(
            "INSERT INTO victim_notifications (complaint_ref, victim_id, message, from_agency) VALUES ($1, $2, $3, $4)",
            complaint_ref,
            victim_row["country"] and (await conn.fetchval("SELECT v.id FROM victims v JOIN victim_complaints c ON c.victim_id = v.id WHERE c.reference_number = $1", complaint_ref)),
            f"Your complaint has been automatically investigated. Risk level: {scam_analysis['risk_level']}. Evidence has been collected and routed to police. Your case is now under review.",
            "GFIN System"
        )

        # Final audit log
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "AUTO_INVESTIGATION_COMPLETE", "GFIN_SCAM_ENGINE", "full_pipeline",
            target, f"Evidence: {connector_results + 2} items, Risk: {scam_analysis['risk_level']}, Stage: ROUTED_TO_POLICE"
        )

        logger.info(f"Auto-investigation complete for {complaint_ref}: {connector_results + 2} evidence items, risk={scam_analysis['risk_level']}")

        # ============================================================
        # INVESTIGATION ORCHESTRATOR INTEGRATION
        # Create a structured investigation with all steps and evidence
        # ============================================================
        if _orchestrator_available and investigation_store:
            try:
                inv_id = f"INV-{int(time.time())}-{case_id[-6:]}"
                investigation_store.create(
                    investigation_id=inv_id,
                    case_id=case_id,
                    subject=target,
                    subject_type=scam_type,
                    operator="GFIN_AUTO_PIPELINE"
                )

                # Step 1: Scam Detection
                investigation_store.add_step(
                    inv_id,
                    step_name="GFIN Scam Engine v3.0 Analysis",
                    tool_name="deterministic_scam_engine",
                    params={"target": target, "description_length": len(description)},
                    status="completed",
                    result=f"Risk: {scam_analysis['risk_level']} ({scam_analysis['risk_score']}), Patterns: {scam_analysis['pattern_count']}, Categories: {', '.join(scam_analysis['categories_detected'])}"
                )

                # Step 2: Entity Extraction
                indicators_summary = []
                for k, v in indicators.items():
                    if v:
                        indicators_summary.append(f"{k}: {len(v)} found")
                investigation_store.add_step(
                    inv_id,
                    step_name="Entity & Indicator Extraction",
                    tool_name="entity_extractor",
                    params={"categories": list(indicators.keys())},
                    status="completed",
                    result=f"Extracted: {'; '.join(indicators_summary)}"
                )

                # Step 3: Connector Search
                investigation_store.add_step(
                    inv_id,
                    step_name=f"External Connector Search ({connector_results} results)",
                    tool_name="multi_connector_search",
                    params={"connectors_run": len(connectors) if 'connectors' in dir() else 6},
                    status="completed",
                    result=f"Connectors returned {connector_results} results"
                )

                # Step 4: Country Routing
                investigation_store.add_step(
                    inv_id,
                    step_name="Police Routing & Alert Generation",
                    tool_name="country_routing_engine",
                    params={"countries": countries, "organizations": ["EUROPOL", "INTERPOL"]},
                    status="completed",
                    result=f"Routed to: {', '.join(countries + ['EUROPOL', 'INTERPOL'])}"
                )

                # Add evidence to investigation
                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="PATTERN_DETECTION",
                    finding=f"Risk level: {scam_analysis['risk_level']}, Score: {scam_analysis['risk_score']}, Patterns: {scam_analysis['pattern_count']}, Categories: {', '.join(scam_analysis['categories_detected'])}",
                    source="GFIN Scam Engine v3.0",
                    confidence="HIGH"
                )

                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="INDICATOR_EXTRACTION",
                    finding=f"Entities extracted: {'; '.join(indicators_summary)}",
                    source="GFIN Scam Engine (entity extractor)",
                    confidence="HIGH"
                )

                if connector_results > 0:
                    investigation_store.add_evidence(
                        inv_id,
                        evidence_type="CONNECTOR_SEARCH",
                        finding=f"External connectors returned {connector_results} results across 6 sources",
                        source="Multi-connector pipeline",
                        confidence="MEDIUM"
                    )

                investigation_store.add_evidence(
                    inv_id,
                    evidence_type="POLICE_ROUTING",
                    finding=f"Complaint routed to {', '.join(countries + ['EUROPOL', 'INTERPOL'])} for investigation",
                    source="GFIN Country Routing Engine",
                    confidence="HIGH"
                )

                logger.info(f"Investigation orchestrator record created: {inv_id} for case {case_id}")
            except Exception as e:
                logger.warning(f"Failed to create orchestrator investigation: {e}")

        return case_id



# ==================== INVESTIGATION ORCHESTRATOR INTEGRATION ====================
try:
    from investigation_store import investigation_store
    _orchestrator_available = True
except Exception as e:
    investigation_store = None
    _orchestrator_available = False
    print(f"Warning: investigation_store not loaded: {e}")

# ==================== APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start MIDAS Alert Bridge background task
    asyncio.create_task(midas_alert_bridge())
    await seed_data()
    yield
    if db_pool: await db_pool.close()

app = FastAPI(title="GFIN Server v2.0", version="2.0.0", lifespan=lifespan)
setup_logging()
_gfin_logger = get_logger()
_gfin_logger.info("GFIN server starting up")
app.middleware("http")(create_request_logger())
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==================== SEO ROUTUTES ====================

@app.get("/og-image.png", response_class=Response)
async def og_image():
    try:
        with open("/gfin/web/og-image.png", "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    except:
        return Response(status_code=404)

@app.get("/about", response_class=HTMLResponse)
async def about_page():
    try:
        with open("/gfin/about_page.html") as f:
            return f.read()
    except:
        return HTMLResponse("<h1>About GFIN</h1><p>Page loading...</p>")

@app.get("/awareness", response_class=HTMLResponse)
async def awareness_page():
    try:
        with open("/gfin/awareness_page.html") as f:
            return f.read()
    except:
        return HTMLResponse("<h1>Scam Awareness</h1><p>Page loading...</p>")

@app.get('/robots.txt', response_class=PlainTextResponse)
async def robots_txt():
    return PlainTextResponse(open('/gfin/robots.txt').read(), media_type='text/plain')

@app.get('/sitemap.xml', response_class=Response)
async def sitemap_xml():
    return Response(content=open('/gfin/sitemap.xml').read(), media_type='application/xml')

@app.get('/sitemap-pages.xml', response_class=Response)
async def sitemap_pages_xml():
    return Response(content=open('/gfin/sitemap.xml').read(), media_type='application/xml')


# ===== SECURITY MIDDLEWARE =====
try:
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    from gfin_security import setup_security_middleware, detect_attack, sanitize_input, validate_file_upload, validate_password_strength, rate_limiter
    setup_security_middleware(app)
    _security = True
    print("✅ GFIN Security middleware loaded")
except Exception as e:
    _security = False
    print(f"Warning: security middleware not loaded: {e}")


# ==================== VICTIM ENDPOINTS ====================

@app.post("/api/victim/register")
async def victim_register(
    name: str = Body(...), email: str = Body(...),
    password: str = Body(...), country: str = Body(""), phone: str = Body("")
):
    """Register a new victim account."""
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    async with db_pool.acquire() as conn:
        existing = await conn.fetchval("SELECT id FROM victims WHERE email=$1", email.lower())
        if existing:
            return {"success": False, "error": "Email already registered"}
        row = await conn.fetchrow(
            "INSERT INTO victims (email, name, password_hash, country, phone) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            email.lower(), name, pwd_hash, country, phone
        )
    return {"success": True, "victim_id": row["id"]}


@app.post("/api/victim/login")
async def victim_login(email: str = Body(...), password: str = Body(...)):
    """Login victim and return session token."""
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, country FROM victims WHERE email=$1 AND password_hash=$2",
            email.lower(), pwd_hash
        )
        if not row:
            return {"success": False, "error": "Invalid credentials"}
        token = secrets.token_hex(32)
        await conn.execute(
            "INSERT INTO victim_sessions (token, victim_id, expires_at) VALUES ($1, $2, NOW() + INTERVAL '7 days')",
            token, row["id"]
        )
    return {"success": True, "token": token, "victim": dict(row)}


@app.get("/api/victim/me")
async def victim_me(request: Request):
    """Get current victim info."""
    victim_id = await auth_victim(request)
    if not victim_id:
        raise HTTPException(401, "Not authenticated")
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, email, country, phone FROM victims WHERE id=$1", victim_id)
    return {"success": True, "victim": dict(row)}




def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return _dt.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        try:
            return _dt.strptime(date_str, '%d/%m/%Y').date()
        except Exception:
            return None

@app.post("/api/victim/complaint")
async def file_complaint(
    request: Request,
    scam_type: str = Form(...),
    target: str = Form(...),
    incident_date: str = Form(""),
    financial_loss: str = Form(""),
    description: str = Form(...),
    files: List[UploadFile] = File(default=[])
):
    """File a new complaint — triggers auto-investigation."""
    victim_id = await auth_victim(request)
    if not victim_id:
        raise HTTPException(401, "Not authenticated")

    # Generate reference number
    ref_number = f"GFIN-2026-{secrets.token_hex(4).upper()}"

    async with db_pool.acquire() as conn:
        # Get victim's country
        country = await conn.fetchval("SELECT country FROM victims WHERE id=$1", victim_id) or "UNKNOWN"

        # Insert complaint
        await conn.execute(
            """INSERT INTO victim_complaints (reference_number, victim_id, scam_type, target,
               incident_date, financial_loss, description, country, investigation_stage)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'RECEIVED')""",
            ref_number, victim_id, scam_type, target,
            _parse_date(incident_date), financial_loss, description, country
        )

        # Save uploaded files
        for f in files:
            if f and f.filename:
                safe_name = f"{secrets.token_hex(4)}_{f.filename}"
                filepath = EVIDENCE_UPLOAD_DIR / safe_name
                content = await f.read()
                with open(filepath, "wb") as out:
                    out.write(content)
                file_hash = hashlib.sha256(content).hexdigest()
                await conn.execute(
                    "INSERT INTO complaint_files (complaint_ref, filename, filepath, file_hash, file_size, mime_type) VALUES ($1, $2, $3, $4, $5, $6)",
                    ref_number, f.filename, str(filepath), file_hash, len(content), f.content_type
                )

        # Log audit
        await conn.execute(
            "INSERT INTO audit_log (action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5)",
            "COMPLAINT_FILED", f"victim:{victim_id}", "victim_portal",
            target, f"Ref: {ref_number}, Type: {scam_type}, Files: {len(files)}"
        )

    # Trigger auto-investigation (async, non-blocking response)
    try:
        await run_auto_investigation(ref_number, target, scam_type, description)
    except Exception as e:
        logger.error(f"Auto-investigation error for {ref_number}: {e}")

    return {"success": True, "reference_number": ref_number, "message": "Complaint filed. Investigation started automatically."}

@app.post("/api/victim/public-complaint")
async def public_file_complaint(
    scam_type: str = Form(...),
    target: str = Form(...),
    incident_date: str = Form(""),
    financial_loss: str = Form(""),
    description: str = Form(...),
    victim_name: str = Form(""),
    victim_email: str = Form(""),
    victim_phone: str = Form(""),
    country: str = Form(""),
    currency: str = Form("USD"),
    files: List[UploadFile] = File(default=[])
):
    """Public complaint filing — auto-registers victim if needed, no login required."""
    import secrets as _sec
    import hashlib as _hl
    
    victim_id = None
    generated_password = None
    
    async with db_pool.acquire() as conn:
        if victim_email:
            # Check if victim already exists
            existing = await conn.fetchval("SELECT id FROM victims WHERE email=$1", victim_email.lower())
            if existing:
                victim_id = existing
            else:
                # Auto-register the victim with a generated password
                generated_password = _sec.token_hex(8)
                pwd_hash = _hl.sha256(generated_password.encode()).hexdigest()
                row = await conn.fetchrow(
                    "INSERT INTO victims (email, name, password_hash, country, phone) VALUES ($1, $2, $3, $4, $5) RETURNING id",
                    victim_email.lower(), victim_name or "Anonymous", pwd_hash, country or "UNKNOWN", victim_phone or ""
                )
                victim_id = row["id"]
        else:
            # Anonymous complaint — create anonymous victim record
            anon_email = f"anon-{_sec.token_hex(4)}@gfin-anonymous.local"
            generated_password = _sec.token_hex(8)
            pwd_hash = _hl.sha256(generated_password.encode()).hexdigest()
            row = await conn.fetchrow(
                "INSERT INTO victims (email, name, password_hash, country, phone) VALUES ($1, $2, $3, $4, $5) RETURNING id",
                anon_email, victim_name or "Anonymous Reporter", pwd_hash, country or "UNKNOWN", victim_phone or ""
            )
            victim_id = row["id"]
        
        # Generate reference number
        ref_number = f"GFIN-2026-{_sec.token_hex(4).upper()}"
        
        # Ensure country is set
        if not country:
            country = await conn.fetchval("SELECT country FROM victims WHERE id=$1", victim_id) or "UNKNOWN"
        
        # Insert complaint
        await conn.execute(
            """INSERT INTO victim_complaints (reference_number, victim_id, scam_type, target,
               incident_date, financial_loss, description, country, investigation_stage)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'RECEIVED')""",
            ref_number, victim_id, scam_type, target,
            _parse_date(incident_date), f"{financial_loss} {currency}" if financial_loss else "", description, country
        )
        
        # Save uploaded files
        for f in files:
            if f and f.filename:
                safe_name = f"{_sec.token_hex(4)}_{f.filename}"
                filepath = EVIDENCE_UPLOAD_DIR / safe_name
                content = await f.read()
                with open(filepath, "wb") as out:
                    out.write(content)
                file_hash = _hl.sha256(content).hexdigest()
                await conn.execute(
                    "INSERT INTO complaint_files (complaint_ref, filename, filepath, file_hash, file_size, mime_type) VALUES ($1, $2, $3, $4, $5, $6)",
                    ref_number, f.filename, str(filepath), file_hash, len(content), f.content_type
                )
        
        # Log audit
        await conn.execute(
            "INSERT INTO audit_log (action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5)",
            "COMPLAINT_FILED", f"victim:{victim_id}", "victim_portal_public",
            target, f"Ref: {ref_number}, Type: {scam_type}, Files: {len(files)}"
        )
    
    # Trigger auto-investigation
    try:
        await run_auto_investigation(ref_number, target, scam_type, description)
    except Exception as e:
        logger.error(f"Auto-investigation error for {ref_number}: {e}")
    
    response = {
        "success": True,
        "reference_number": ref_number,
        "message": "Complaint filed successfully. Investigation started automatically."
    }
    if generated_password and victim_email:
        response["temp_password"] = generated_password
        response["login_note"] = "Save this password to check your case status later."
    
    return response



@app.get("/api/victim/complaints")
async def my_complaints(request: Request):
    """Get all complaints for the logged-in victim."""
    victim_id = await auth_victim(request)
    if not victim_id:
        raise HTTPException(401, "Not authenticated")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM victim_complaints WHERE victim_id=$1 ORDER BY created_date DESC",
            victim_id
        )
    return {"success": True, "complaints": [dict(r) for r in rows]}


@app.get("/api/victim/complaint/{ref}")
async def get_my_complaint(ref: str, request: Request):
    """Get a specific complaint with stage info and notifications — victim view only."""
    victim_id = await auth_victim(request)
    if not victim_id:
        raise HTTPException(401, "Not authenticated")
    async with db_pool.acquire() as conn:
        complaint = await conn.fetchrow(
            "SELECT * FROM victim_complaints WHERE reference_number=$1 AND victim_id=$2",
            ref.upper(), victim_id
        )
        if not complaint:
            return {"success": False, "error": "Complaint not found"}
        notifications = await conn.fetch(
            "SELECT message, from_agency, is_read, created_date FROM victim_notifications WHERE complaint_ref=$1 ORDER BY created_date DESC",
            ref.upper()
        )
    return {"success": True, "complaint": {**dict(complaint), "notifications": [dict(n) for n in notifications]}}


@app.get("/api/victim/track/{ref}")
async def track_complaint(ref: str):
    """Track a complaint by reference number — no login required."""
    async with db_pool.acquire() as conn:
        complaint = await conn.fetchrow(
            "SELECT reference_number, scam_type, target, investigation_stage, created_date, updated_date FROM victim_complaints WHERE reference_number=$1",
            ref.upper()
        )
        if not complaint:
            return {"success": False, "error": "Complaint not found"}
    return {"success": True, "complaint": dict(complaint)}


@app.post("/api/victim/notification")
async def police_notify_victim(
    complaint_ref: str = Body(...), message: str = Body(...),
    from_agency: str = Body("Police"), request: Request = None
):
    """Police sends a notification to the victim. (Police-only endpoint.)"""
    async with db_pool.acquire() as conn:
        complaint = await conn.fetchrow(
            "SELECT victim_id, investigation_stage FROM victim_complaints WHERE reference_number=$1",
            complaint_ref.upper()
        )
        if not complaint:
            return {"success": False, "error": "Complaint not found"}
        await conn.execute(
            "INSERT INTO victim_notifications (complaint_ref, victim_id, message, from_agency) VALUES ($1, $2, $3, $4)",
            complaint_ref.upper(), complaint["victim_id"], message, from_agency
        )
        # Update stage if specified in message
        stage_map = {
            "under review": "UNDER_REVIEW", "investigating": "INVESTIGATING",
            "evidence collected": "EVIDENCE_COLLECTED", "routed": "ROUTED_TO_POLICE",
            "police review": "POLICE_REVIEW", "action taken": "ACTION_TAKEN",
            "closed": "CLOSED"
        }
        msg_lower = message.lower()
        for keyword, stage in stage_map.items():
            if keyword in msg_lower:
                await conn.execute(
                    "UPDATE victim_complaints SET investigation_stage=$1, updated_date=NOW() WHERE reference_number=$2",
                    stage, complaint_ref.upper()
                )
                break
    return {"success": True}


# --- Auth helper ---
async def auth_victim(request: Request) -> Optional[int]:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT victim_id FROM victim_sessions WHERE token=$1 AND expires_at > NOW()",
            token
        )
    return row["victim_id"] if row else None


# ==================== POLICE ENDPOINTS (from v1.0) ====================

@app.get("/api/cases")
async def list_cases():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM cases ORDER BY created_date DESC")
    return [dict(r) for r in rows]

# ==================== CASE FAVORITES API ====================

@app.get("/api/cases/favorites")
async def get_favorites(request: Request):
    """Get all favorited cases for the authenticated officer."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT cf.case_id, cf.created_at as favorited_at,
                      c.summary as title, c.status, c.confidence, c.priority, c.target,
                      c.scam_patterns as scam_types, c.victim_count, c.total_loss_usd as total_loss
               FROM case_favorites cf
               LEFT JOIN cases c ON c.case_id = cf.case_id
               WHERE cf.officer_id = $1
               ORDER BY cf.created_at DESC""",
            officer_id
        )
    return {"favorites": [dict(r) for r in rows], "total": len(rows)}

@app.post("/api/cases/{case_id}/favorite")
async def add_favorite(case_id: str, request: Request):
    """Add a case to favorites."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    async with db_pool.acquire() as conn:
        # Check case exists
        case = await conn.fetchval("SELECT case_id FROM cases WHERE case_id=$1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        await conn.execute(
            "INSERT INTO case_favorites (officer_id, case_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            officer_id, case_id
        )
        # Audit log
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "FAVORITE_ADDED", payload.get("email", str(officer_id)), "DASHBOARD", "case_favorites", "SUCCESS"
        )
    return {"success": True, "message": "Case added to favorites"}

@app.delete("/api/cases/{case_id}/favorite")
async def remove_favorite(case_id: str, request: Request):
    """Remove a case from favorites."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM case_favorites WHERE officer_id=$1 AND case_id=$2",
            officer_id, case_id
        )
        # Audit log
        await conn.execute(
            "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
            case_id, "FAVORITE_REMOVED", payload.get("email", str(officer_id)), "DASHBOARD", "case_favorites", "SUCCESS"
        )
    return {"success": True, "message": "Case removed from favorites"}

@app.get("/api/cases/{case_id}/favorite")
async def check_favorite(case_id: str, request: Request):
    """Check if a case is favorited by the current officer."""
    try:
        payload = await auth_police(request)
        officer_id = payload.get("oid") or payload.get("officer_id")
        async with db_pool.acquire() as conn:
            row = await conn.fetchval(
                "SELECT id FROM case_favorites WHERE officer_id=$1 AND case_id=$2",
                officer_id, case_id
            )
        return {"is_favorite": row is not None}
    except:
        return {"is_favorite": False}



@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    async with db_pool.acquire() as conn:
        case = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
        if not case: raise HTTPException(404, "Case not found")
        people = await conn.fetch("SELECT * FROM people WHERE case_id=$1", case_id)
        evidence = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1", case_id)
        alerts = await conn.fetch("SELECT * FROM alerts WHERE case_id=$1", case_id)
        complaints = await conn.fetch("SELECT * FROM victim_complaints WHERE case_id=$1", case_id)
    return {"case": dict(case), "people": [dict(p) for p in people],
            "evidence": [dict(e) for e in evidence], "alerts": [dict(a) for a in alerts],
            "linked_complaints": [dict(c) for c in complaints]}

@app.get("/api/people/{case_id}")
async def get_people(case_id: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM people WHERE case_id=$1", case_id)
    return [dict(r) for r in rows]

@app.get("/api/evidence/{case_id}")
async def get_evidence(case_id: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1", case_id)
    return [dict(r) for r in rows]

@app.post("/api/evidence/{case_id}")
async def add_evidence(request: Request, case_id: str,
    finding: str = Body(..., embed=True),
    phase: str = Body("MANUAL", embed=True),
    source_provider: str = Body("OFFICER", embed=True),
    source_url: str = Body("", embed=True),
    source_type: str = Body("MANUAL", embed=True),
    confidence: str = Body("MEDIUM", embed=True),
    content_hash: str = Body("", embed=True)):
    """Add evidence to a case — requires police auth. Tracks which officer added it."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Get officer name
    officer = await conn.fetchrow("SELECT name, agency FROM police_officers WHERE id=$1", officer_id)
    officer_name = officer["name"] if officer else "UNKNOWN"
    
    evidence_id = f"EVID-{int(time.time())}-{case_id}"
    
    await conn.execute("""
        INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, 
                             source_type, confidence, content_hash, added_by_officer, added_by_officer_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    """, case_id, evidence_id, phase, finding, source_provider, source_url,
        source_type, confidence.upper(), content_hash if content_hash else None, 
        officer_name, officer_id)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "ADD_EVIDENCE", officer_name, "DASHBOARD", f"Manual evidence: {finding[:80]}", 
        f"evidence_id={evidence_id}"
    )
    
    # Update case updated_date
    await conn.execute("UPDATE cases SET updated_date=NOW() WHERE case_id=$1", case_id)
    
    await conn.close()
    
    return {
        "success": True,
        "evidence_id": evidence_id,
        "added_by": officer_name,
        "officer_id": officer_id,
        "message": f"Evidence added to {case_id} by {officer_name}"
    }

@app.delete("/api/evidence/{evidence_id}")
async def delete_evidence(request: Request, evidence_id: str):
    """Delete evidence — requires police auth. Tracks who deleted it."""
    payload = await auth_police(request)
    officer_id = payload.get("oid") or payload.get("officer_id")
    officer_name = payload.get("agency", "UNKNOWN")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Get the evidence before deleting
    row = await conn.fetchrow("SELECT case_id, finding FROM evidence WHERE evidence_id=$1", evidence_id)
    if not row:
        await conn.close()
        return {"success": False, "message": "Evidence not found"}
    
    case_id = row["case_id"]
    
    await conn.execute("DELETE FROM evidence WHERE evidence_id=$1", evidence_id)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "DELETE_EVIDENCE", officer_name, "DASHBOARD", f"Delete evidence {evidence_id}",
        "deleted"
    )
    
    await conn.close()
    
    return {"success": True, "message": f"Evidence {evidence_id} deleted by {officer_name}"}

@app.get("/api/alerts")
async def get_alerts(country: Optional[str] = None):
    async with db_pool.acquire() as conn:
        if country:
            rows = await conn.fetch("SELECT * FROM alerts WHERE country=$1 ORDER BY created_date DESC", country)
        else:
            rows = await conn.fetch("SELECT * FROM alerts ORDER BY created_date DESC")
    return [dict(r) for r in rows]

@app.get("/api/countries")
async def get_countries():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM country_routing ORDER BY country_name")
    return [dict(r) for r in rows]

@app.post("/api/search")
async def search(query: str = Body(...), connectors: List[str] = Body(default=[])):
    connectors_dict = load_connectors()
    results = []
    connector_list = connectors if connectors else list(connectors_dict.keys())
    for name in connector_list:
        if name not in connectors_dict:
            results.append({"connector": name, "success": False, "error": "Not available"})
            continue
        c = connectors_dict[name]
        try:
            r = c.query(search_term=query)
            results.append({"connector": name, "provider": c.provider, "success": r.success,
                          "data": r.data if r.success else None, "error": r.error if not r.success else None,
                          "provenance": r.provenance, "content_hash": r.content_hash,
                          "quality_score": r.quality_score, "timestamp": r.timestamp})
        except Exception as e:
            results.append({"connector": name, "success": False, "error": str(e)})
    return {"query": query, "connectors_used": len(results), "results": results}

@app.get("/api/connectors")
async def list_connectors():
    connectors = load_connectors()
    return {"total": len(connectors), "connectors": [{**c.get_provider_record(), "name": n} for n, c in connectors.items()]}

@app.post("/api/investigate")
async def start_investigation(target: str = Body(...), target_type: str = Body("domain"), goal: str = Body(""), trigger: str = Body("MANUAL")):
    case_id = f"GFIN-CASE-{int(time.time())}"
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO cases (case_id, target, target_type, trigger, summary, status) VALUES ($1, $2, $3, $4, $5, 'INVESTIGATING')",
            case_id, target, target_type, trigger, goal or f"Investigation of {target}"
        )
        connectors = load_connectors()
        search_results = []
        for name, connector in connectors.items():
            try:
                result = connector.query(search_term=target)
                if result.success:
                    evidence_id = f"E-{len(search_results)+1:03d}"
                    await conn.execute(
                        "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence, content_hash) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                        case_id, evidence_id, "INITIAL_SEARCH", str(result.data)[:500],
                        connector.provider, result.provenance, connector.source_class,
                        "HIGH" if result.quality_score > 0.5 else "MEDIUM", result.content_hash
                    )
                    search_results.append({"connector": name, "evidence_id": evidence_id, "success": True})
                else:
                    search_results.append({"connector": name, "success": False, "error": result.error})
            except Exception as e:
                search_results.append({"connector": name, "success": False, "error": str(e)})
    return {"case_id": case_id, "target": target, "status": "INVESTIGATING",
            "connectors_run": len(search_results),
            "successful": sum(1 for r in search_results if r.get("success", False)),
            "results": search_results}



@app.get("/api/cases/{case_id}/cross-reference")
async def cross_reference_case(case_id: str):
    """Find other cases sharing IPs, hosting providers, or infrastructure with this case."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        # Get this case's identifiers
        case = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
        if not case:
            return {"error": "Case not found"}

        import json as j
        di_raw = case.get("digital_identifiers", "[]")
        if isinstance(di_raw, str):
            di = j.loads(di_raw) if di_raw else []
        else:
            di = di_raw or []

        # Extract IPs and hosting providers from this case
        this_ips = [d.get("value","") for d in di if d.get("type") == "IP"]
        this_hosting = [d.get("value","") for d in di if d.get("type") == "HOSTING_PROVIDER"]
        this_ns = [d.get("value","") for d in di if d.get("type") == "NS"]
        this_registrar = [d.get("value","") for d in di if d.get("type") == "REGISTRAR"]

        # Get all other cases
        other_cases = await conn.fetch("SELECT case_id, target, status, confidence, digital_identifiers, scam_patterns, affected_countries FROM cases WHERE case_id != $1", case_id)

        connections = []
        for oc in other_cases:
            oc_di_raw = oc.get("digital_identifiers", "[]")
            if isinstance(oc_di_raw, str):
                oc_di = j.loads(oc_di_raw) if oc_di_raw else []
            else:
                oc_di = oc_di_raw or []

            def safe_get(items, field_type):
                result = set()
                for d in items:
                    if isinstance(d, dict):
                        if d.get("type") == field_type:
                            result.add(d.get("value", ""))
                    elif isinstance(d, str):
                        try:
                            dd = json.loads(d)
                            if isinstance(dd, dict) and dd.get("type") == field_type:
                                result.add(dd.get("value", ""))
                        except: pass
                return result
            oc_ips = safe_get(oc_di, "IP")
            oc_hosting = safe_get(oc_di, "HOSTING_PROVIDER")
            oc_ns = safe_get(oc_di, "NS")
            oc_registrar = safe_get(oc_di, "REGISTRAR")

            # Find shared infrastructure
            shared_ips = set(this_ips) & oc_ips
            shared_hosting = set(this_hosting) & oc_hosting
            shared_ns = set(this_ns) & oc_ns
            shared_registrar = set(this_registrar) & oc_registrar

            if shared_ips or shared_hosting or shared_ns or shared_registrar:
                connections.append({
                    "case_id": oc["case_id"],
                    "target": oc["target"],
                    "status": oc["status"],
                    "confidence": float(oc["confidence"] or 0),
                    "scam_patterns": oc.get("scam_patterns", []) or [],
                    "affected_countries": oc.get("affected_countries", []) or [],
                    "shared_ips": list(shared_ips),
                    "shared_hosting": list(shared_hosting),
                    "shared_ns": list(shared_ns),
                    "shared_registrar": list(shared_registrar),
                    "connection_strength": len(shared_ips) * 3 + len(shared_hosting) * 2 + len(shared_ns) + len(shared_registrar),
                })

        # Sort by connection strength
        connections.sort(key=lambda x: x["connection_strength"], reverse=True)

        return {
            "case_id": case_id,
            "this_case": {
                "target": case["target"],
                "ips": this_ips,
                "hosting": this_hosting,
                "ns": this_ns,
                "registrar": this_registrar,
            },
            "connections": connections[:20],
            "total_connections": len(connections),
        }
    finally:
        await conn.close()

@app.get("/api/hunter/activity")
async def hunter_activity():
    """Get recent hunter activity — domains discovered, investigations run, intelligence collected."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        # Get recent cases created by hunter
        recent = await conn.fetch(
            "SELECT case_id, target, confidence, status, scam_patterns, affected_countries, digital_identifiers, physical_locations, created_date FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' ORDER BY created_date DESC LIMIT 50"
        )

        import json as j
        activities = []
        total_identifiers = 0
        total_locations = 0
        sources = {}
        patterns = {}

        for r in recent:
            di_raw = r.get("digital_identifiers", "[]")
            if isinstance(di_raw, str):
                di = j.loads(di_raw) if di_raw else []
            else:
                di = di_raw or []
            pl_raw = r.get("physical_locations", "[]")
            if isinstance(pl_raw, str):
                pl = j.loads(pl_raw) if pl_raw else []
            else:
                pl = pl_raw or []

            total_identifiers += len(di)
            total_locations += len(pl)

            # Count identifier types
            for d in di:
                t = d.get("type", "UNKNOWN")
                sources[t] = sources.get(t, 0) + 1

            for p in r.get("scam_patterns", []) or []:
                patterns[p] = patterns.get(p, 0) + 1

            activities.append({
                "case_id": r["case_id"],
                "target": r["target"],
                "confidence": float(r["confidence"] or 0),
                "status": r["status"],
                "identifier_count": len(di),
                "location_count": len(pl),
                "scam_patterns": r.get("scam_patterns", []) or [],
                "affected_countries": r.get("affected_countries", []) or [],
                "created_date": r["created_date"].isoformat() if r["created_date"] else None,
            })

        # Get total stats
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'")
        total_all = await conn.fetchval("SELECT COUNT(*) FROM cases")

        return {
            "total_hunter_cases": total_cases,
            "total_all_cases": total_all,
            "total_identifiers_collected": total_identifiers,
            "total_locations_found": total_locations,
            "identifier_types": dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)),
            "scam_patterns": dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True)),
            "recent_activity": activities,
        }
    finally:
        await conn.close()




@app.get("/api/flagged-domains")
async def get_flagged_domains(limit: int = 50):
    """Get all flagged domains from scam_websites database."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        rows = await conn.fetch(
            "SELECT domain, scam_type, risk_level, report_count, sources, first_reported, last_reported, countries_affected, wallet_addresses, phone_numbers, status, is_verified, description FROM scam_websites ORDER BY last_reported DESC LIMIT $1",
            limit
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM scam_websites")
        high_risk = await conn.fetchval("SELECT COUNT(*) FROM scam_websites WHERE risk_level IN ('HIGH','CRITICAL')")
        verified = await conn.fetchval("SELECT COUNT(*) FROM scam_websites WHERE is_verified = true")
        return {
            "total": total,
            "high_risk": high_risk,
            "verified": verified,
            "domains": [
                {
                    "domain": r["domain"],
                    "scam_type": r["scam_type"],
                    "risk_level": r["risk_level"],
                    "report_count": r["report_count"],
                    "sources": r["sources"] or [],
                    "first_reported": r["first_reported"].isoformat() if r["first_reported"] else None,
                    "last_reported": r["last_reported"].isoformat() if r["last_reported"] else None,
                    "countries_affected": r["countries_affected"] or [],
                    "wallet_addresses": r["wallet_addresses"] or [],
                    "phone_numbers": r["phone_numbers"] or [],
                    "status": r["status"],
                    "is_verified": r["is_verified"],
                    "description": (r["description"] or "")[:200],
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()




@app.get("/api/telegram/intelligence")
async def get_telegram_intelligence(limit: int = 50, type: str = None):
    """Get intelligence collected from Telegram groups."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        where = ""
        params = []
        if type:
            where = "WHERE intel_type = $1"
            params = [type]
        
        rows = await conn.fetch(
            f"SELECT id, detected_at, chat_id, chat_title, chat_type, username, message_id, intel_type, intel_value, intel_subtype, is_victim, scam_types, scam_keywords, is_known_scam, cross_group_count, groups_seen, investigated, case_id FROM telegram_intelligence {where} ORDER BY detected_at DESC LIMIT {limit}",
            *params
        )
        
        # Get summary stats
        total = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence")
        wallets = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE intel_type='WALLET'")
        domains = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE intel_type='DOMAIN'")
        phones = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE intel_type='PHONE'")
        ips = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE intel_type='IP'")
        usernames = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE intel_type='USERNAME'")
        victims = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE is_victim=true")
        cross_group = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE cross_group_count > 1")
        known_scams = await conn.fetchval("SELECT COUNT(*) FROM telegram_intelligence WHERE is_known_scam=true")
        
        # Type breakdown
        type_rows = await conn.fetch("SELECT intel_type, COUNT(*) as count, COUNT(CASE WHEN is_victim THEN 1 END) as victims, COUNT(CASE WHEN cross_group_count > 1 THEN 1 END) as cross_group FROM telegram_intelligence GROUP BY intel_type")
        
        return {
            "total": total,
            "wallets": wallets,
            "domains": domains,
            "phones": phones,
            "ips": ips,
            "usernames": usernames,
            "victims_detected": victims,
            "cross_group_entities": cross_group,
            "known_scams": known_scams,
            "type_breakdown": {r["intel_type"]: {"count": r["count"], "victims": r["victims"], "cross_group": r["cross_group"]} for r in type_rows},
            "intelligence": [
                {
                    "id": r["id"],
                    "detected_at": r["detected_at"].isoformat() if r["detected_at"] else None,
                    "chat_title": r["chat_title"],
                    "username": r["username"],
                    "intel_type": r["intel_type"],
                    "intel_value": r["intel_value"],
                    "intel_subtype": r["intel_subtype"],
                    "is_victim": r["is_victim"],
                    "scam_types": r["scam_types"] or [],
                    "is_known_scam": r["is_known_scam"],
                    "cross_group_count": r["cross_group_count"],
                    "groups_seen": r["groups_seen"] or [],
                    "investigated": r["investigated"],
                    "case_id": r["case_id"],
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()

@app.get("/api/telegram/groups")
async def get_telegram_groups():
    """Get all Telegram groups the intelligence bot is monitoring."""
    conn = await asyncpg.connect(host="127.0.0.1", port=5432, user="gfin", password="", database="gfin")
    try:
        rows = await conn.fetch("SELECT chat_id, chat_title, chat_type, chat_username, member_count, joined_at, last_activity, messages_scanned, intel_items_found, victims_helped, scams_detected, is_active FROM telegram_groups ORDER BY last_activity DESC")
        total = await conn.fetchval("SELECT COUNT(*) FROM telegram_groups")
        total_messages = await conn.fetchval("SELECT COALESCE(SUM(messages_scanned), 0) FROM telegram_groups")
        total_intel = await conn.fetchval("SELECT COALESCE(SUM(intel_items_found), 0) FROM telegram_groups")
        total_victims = await conn.fetchval("SELECT COALESCE(SUM(victims_helped), 0) FROM telegram_groups")
        total_scams = await conn.fetchval("SELECT COALESCE(SUM(scams_detected), 0) FROM telegram_groups")
        total_members = await conn.fetchval("SELECT COALESCE(SUM(member_count), 0) FROM telegram_groups")
        
        return {
            "total_groups": total,
            "total_members_reached": total_members,
            "total_messages_scanned": total_messages,
            "total_intel_items": total_intel,
            "total_victims_helped": total_victims,
            "total_scams_detected": total_scams,
            "groups": [
                {
                    "chat_id": r["chat_id"],
                    "chat_title": r["chat_title"],
                    "chat_type": r["chat_type"],
                    "chat_username": r["chat_username"],
                    "member_count": r["member_count"],
                    "joined_at": r["joined_at"].isoformat() if r["joined_at"] else None,
                    "last_activity": r["last_activity"].isoformat() if r["last_activity"] else None,
                    "messages_scanned": r["messages_scanned"],
                    "intel_items_found": r["intel_items_found"],
                    "victims_helped": r["victims_helped"],
                    "scams_detected": r["scams_detected"],
                    "is_active": r["is_active"],
                }
                for r in rows
            ]
        }
    finally:
        await conn.close()


@app.get("/api/stats")
async def get_stats():
    async with db_pool.acquire() as conn:
        cases = await conn.fetchval("SELECT COUNT(*) FROM cases")
        evidence = await conn.fetchval("SELECT COUNT(*) FROM evidence")
        alerts = await conn.fetchval("SELECT COUNT(*) FROM alerts WHERE delivery_status='PENDING'")
        people = await conn.fetchval("SELECT COUNT(*) FROM people")
        countries = await conn.fetchval("SELECT COUNT(*) FROM country_routing")
        victims = await conn.fetchval("SELECT COUNT(*) FROM victims")
        complaints = await conn.fetchval("SELECT COUNT(*) FROM victim_complaints")
        pending_inv = await conn.fetchval("SELECT COUNT(*) FROM victim_complaints WHERE investigation_stage NOT IN ('CLOSED')")
    connectors = load_connectors()
    return {"cases": cases, "evidence_items": evidence, "pending_alerts": alerts,
            "people_tracked": people, "countries_configured": countries,
            "victims_registered": victims, "complaints_filed": complaints,
            "pending_investigations": pending_inv,
            "connectors_available": len(connectors),
            "server": "GFIN Standalone v2.0", "database": "PostgreSQL (local)",
            "base44_dependency": "NONE", "ai_dependency": "NONE (deterministic engine v3.0)",
            "engine_version": "3.0",
            "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/audit/{case_id}")
async def get_audit_trail(case_id: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM audit_log WHERE case_id=$1 ORDER BY timestamp", case_id)
    return [dict(r) for r in rows]

@app.get("/api/scam-detect")
async def scam_detect_endpoint(text: str = Query(...), target: str = Query("")):
    """Test the scam detection engine v3.0 on any text."""
    result = DeterministicScamEngine.analyze(text, target)
    return result

# Police endpoint: list all victim complaints (police view)
@app.get("/api/complaints")
async def list_all_complaints():
    """List all victim complaints — police view (shows all, not just one victim's)."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT vc.*, v.name as victim_name, v.email as victim_email, v.country as victim_country
            FROM victim_complaints vc
            JOIN victims v ON vc.victim_id = v.id
            ORDER BY vc.created_date DESC
        """)
    return [dict(r) for r in rows]

@app.get("/api/complaints/{ref}")
async def get_complaint_detail(ref: str):
    """Get full complaint detail — police view (includes victim info, files, evidence)."""
    async with db_pool.acquire() as conn:
        complaint = await conn.fetchrow("""
            SELECT vc.*, v.name as victim_name, v.email as victim_email, v.country as victim_country, v.phone as victim_phone
            FROM victim_complaints vc JOIN victims v ON vc.victim_id = v.id
            WHERE vc.reference_number = $1
        """, ref.upper())
        if not complaint:
            raise HTTPException(404, "Complaint not found")
        files = await conn.fetch("SELECT * FROM complaint_files WHERE complaint_ref=$1", ref.upper())
        notifications = await conn.fetch("SELECT * FROM victim_notifications WHERE complaint_ref=$1", ref.upper())
        if complaint["case_id"]:
            evidence = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1", complaint["case_id"])
        else:
            evidence = []
    return {"complaint": dict(complaint), "files": [dict(f) for f in files],
            "notifications": [dict(n) for n in notifications], "evidence": [dict(e) for e in evidence]}



# ============================================================
# POLICE AUTHENTICATION API
# ============================================================

@app.get("/police/login", response_class=HTMLResponse)
async def police_login_page():
    """Police login page."""
    if _police_auth:
        return POLICE_LOGIN_HTML
    return HTMLResponse(open("/gfin/police_login_gov.html").read())

@app.post("/api/police/login")
async def police_login(request: Request, email: str = Body(...), password: str = Body(...)):
    """Police officer login — returns JWT token."""
    if not _police_auth:
        return {"error": "Police auth not configured"}, 500
    
    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip, max_requests=10, window=60):
        raise HTTPException(429, "Too many login attempts. Wait 60 seconds.")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    officer = await conn.fetchrow(
        "SELECT * FROM police_officers WHERE email=$1 AND is_active=TRUE", email.lower()
    )
    await conn.close()
    
    if not officer or not verify_password(password, officer["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    
    token = generate_token(officer["id"], officer["role"], officer["agency"])
    
    # Update last login
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("UPDATE police_officers SET last_login=NOW() WHERE id=$1", officer["id"])
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        "SYSTEM", "POLICE_LOGIN", officer["email"], "AUTH", client_ip, "SUCCESS"
    )
    await conn.close()
    
    return {
        "token": token,
        "officer": {
            "id": officer["id"],
            "name": officer["name"],
            "email": officer["email"],
            "role": officer["role"],
            "agency": officer["agency"],
            "country_code": officer["country_code"],
        }
    }

@app.get("/api/police/me")
async def police_me(request: Request):
    """Get current officer info."""
    if not _police_auth:
        raise HTTPException(500, "Police auth not configured")
    payload = await auth_police(request)
    return payload

@app.post("/api/police/register")
async def police_register(request: Request, 
    email: str = Body(...), name: str = Body(...), password: str = Body(...),
    agency: str = Body(...), country_code: str = Body(...), 
    badge_number: str = Body("", embed=True), role: str = Body("investigator", embed=True)):
    """Register a new police officer. First officer becomes admin."""
    if not _police_auth:
        raise HTTPException(500, "Police auth not configured")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Check if any officers exist
    count = await conn.fetchval("SELECT COUNT(*) FROM police_officers")
    
    if count == 0:
        # First officer — auto-admin
        role = "admin"
        approved_by = "SYSTEM_AUTO"
    else:
        # Check if requester is admin
        try:
            payload = await auth_police(request)
            if payload.get("role") != "admin":
                await conn.close()
                raise HTTPException(403, "Only admins can register new officers")
            approved_by = payload.get("agency", "ADMIN")
        except HTTPException:
            await conn.close()
            raise HTTPException(403, "Admin login required to register new officers")
    
    pwd_hash = hash_password(password)
    
    try:
        officer_id = await conn.fetchval(
            """INSERT INTO police_officers (email, name, role, agency, country_code, password_hash, badge_number, approved_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
            email.lower(), name, role, agency, country_code.upper(), pwd_hash, badge_number, approved_by
        )
    except asyncpg.UniqueViolationError:
        await conn.close()
        raise HTTPException(409, "Email already registered")
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        "SYSTEM", "POLICE_REGISTER", email, "AUTH", agency, f"OFFICER_ID={officer_id}, ROLE={role}"
    )
    await conn.close()
    
    return {"success": True, "officer_id": officer_id, "role": role, "message": f"Officer {name} registered as {role}"}

@app.get("/api/police/officers")
async def list_officers(request: Request):
    """List all police officers (admin only)."""
    if not _police_auth:
        raise HTTPException(500, "Police auth not configured")
    payload = await auth_police_admin(request)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    officers = await conn.fetch(
        "SELECT id, email, name, role, agency, country_code, badge_number, is_active, created_date, last_login FROM police_officers ORDER BY created_date"
    )
    await conn.close()
    return {"officers": [dict(o) for o in officers]}


# ============================================================
# PROTECTED API ENDPOINTS — REQUIRE POLICE AUTH
# ============================================================

@app.get("/api/cases-secure")
async def list_cases_secure(request: Request):
    """List all cases — requires police auth."""
    payload = await auth_police(request)
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch("SELECT * FROM cases ORDER BY created_date DESC")
    await conn.close()
    return {"cases": [dict(r) for r in rows], "officer": payload.get("agency", "")}

@app.get("/api/alerts-secure")
async def list_alerts_secure(request: Request):
    """List alerts — requires police auth."""
    payload = await auth_police(request)
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch("SELECT * FROM alerts ORDER BY created_date DESC LIMIT 100")
    await conn.close()
    return {"alerts": [dict(r) for r in rows], "officer": payload.get("agency", "")}

@app.get("/api/evidence-secure/{case_id}")
async def list_evidence_secure(request: Request, case_id: str):
    """List evidence for a case — requires police auth."""
    payload = await auth_police(request)
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1 ORDER BY collected_date", case_id)
    await conn.close()
    
    # Audit log
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "VIEW_EVIDENCE", payload.get("agency", "unknown"), "DASHBOARD", "evidence list", f"{len(rows)} items"
    )
    await conn.close()
    
    return {"evidence": [dict(r) for r in rows], "officer": payload.get("agency", "")}






# ============================================================
# OSINT ENGINE API — GitHub Open-Source Intelligence Integration
# ============================================================

from osint_engine import (
    run_spiderfoot_scan, run_dnstwist_scan, run_shodan_lookup,
    run_wafw00f_check, run_dnsrecon, run_whois_lookup,
    run_full_osint_scan, AVAILABLE_ENGINES
)

@app.get("/api/osint/engines")
async def list_osint_engines():
    """List all available OSINT engines."""
    return {"total": len(AVAILABLE_ENGINES), "engines": AVAILABLE_ENGINES}

@app.post("/api/osint/spiderfoot")
async def spiderfoot_scan(target: str = Body(..., embed=True), 
    modules: List[str] = Body(default=None, embed=True)):
    """Run SpiderFoot OSINT scan (200+ modules)."""
    return await run_spiderfoot_scan(target, modules)

@app.post("/api/osint/dnstwist")
async def dnstwist_scan(domain: str = Body(..., embed=True)):
    """Run DNSTwist typo-squatting detection."""
    return await run_dnstwist_scan(domain)

@app.post("/api/osint/shodan")
async def shodan_lookup(ip: str = Body(..., embed=True)):
    """Look up IP in Shodan (ports, services, vulnerabilities)."""
    return await run_shodan_lookup(ip)

@app.post("/api/osint/wafw00f")
async def wafw00f_check(domain: str = Body(..., embed=True)):
    """Detect WAF protection on a website."""
    return await run_wafw00f_check(domain)

@app.post("/api/osint/dnsrecon")
async def dnsrecon_scan(domain: str = Body(..., embed=True)):
    """Run DNS enumeration on a domain."""
    return await run_dnsrecon(domain)

@app.post("/api/osint/whois")
async def whois_lookup(domain: str = Body(..., embed=True)):
    """Full WHOIS lookup with privacy detection."""
    return await run_whois_lookup(domain)

@app.post("/api/osint/full")
async def full_osint_scan(target: str = Body(..., embed=True),
    target_type: str = Body("domain", embed=True)):
    """Run ALL OSINT engines in parallel — full intelligence scan."""
    return await run_full_osint_scan(target, target_type)

@app.post("/api/osint/hunt")
async def osint_hunt(request: Request, target: str = Body(..., embed=True)):
    """Run full OSINT hunt + save results to case evidence. Requires police auth."""
    payload = await auth_police(request)
    officer_name = payload.get("agency", "SYSTEM")
    
    # Run full scan
    results = await run_full_osint_scan(target, "domain")
    
    # Create case
    conn = await asyncpg.connect(**DB_CONFIG)
    case_id = f"GFIN-OSINT-{int(time.time())}"
    
    await conn.execute(
        "INSERT INTO cases (case_id, target, target_type, trigger, summary, status) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, target, "domain", "OSINT_HUNT", results.get("summary", f"OSINT hunt of {target}"),
        "INVESTIGATING"
    )
    
    # Save each engine result as evidence
    for engine_name, engine_data in results.get("engines", {}).items():
        findings = engine_data.get("findings", [])
        if findings:
            finding_text = json.dumps(findings)[:500]
            evidence_id = f"EVID-{int(time.time()*1000)}-{engine_name}"
            await conn.execute(
                "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                case_id, evidence_id, "OSINT_" + engine_name.upper(),
                finding_text, engine_name.upper(), "AUTOMATED_OSINT",
                results.get("confidence", "MEDIUM"), officer_name
            )
    
    # Save correlations as evidence
    for corr in results.get("correlations", []):
        evidence_id = f"EVID-{int(time.time()*1000)}-CORR"
        await conn.execute(
            "INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            case_id, evidence_id, "INTELLIGENCE_CORRELATION",
            "[" + corr["severity"] + "] " + corr["description"],
            "GFIN_CORRELATION_ENGINE", "CORRELATION", "HIGH", officer_name
        )
    
    await conn.close()
    
    results["case_id"] = case_id
    return results


# ============================================================
# CASE COLLABORATION API — Cross-Country Police Cooperation
# ============================================================

@app.get("/api/cases/{case_id}/notes")
async def get_case_notes(case_id: str):
    """Get all collaboration notes for a case — real data from DB."""
    conn = await asyncpg.connect(**DB_CONFIG)
    notes = await conn.fetch("""
        SELECT cn.*, po.email as officer_email, po.badge_number
        FROM case_notes cn
        LEFT JOIN police_officers po ON cn.officer_id = po.id
        WHERE cn.case_id = $1
        ORDER BY cn.created_date DESC
    """, case_id)
    await conn.close()
    return [dict(n) for n in notes]

@app.post("/api/cases/{case_id}/notes")
async def add_case_note(request: Request, case_id: str,
    note_text: str = Body(...), note_type: str = Body("INFO", embed=True)):
    """Add a collaboration note to a case — requires police auth. Tracks officer."""
    payload = await auth_police(request)
    officer_id = payload.get("oid")
    officer_agency = payload.get("agency", "Unknown")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    # Get officer name and country
    officer = await conn.fetchrow("SELECT name, country_code FROM police_officers WHERE id=$1", officer_id)
    if not officer:
        await conn.close()
        raise HTTPException(404, "Officer not found")
    
    # Verify case exists
    case = await conn.fetchrow("SELECT case_id FROM cases WHERE case_id=$1", case_id)
    if not case:
        await conn.close()
        raise HTTPException(404, "Case not found")
    
    note = await conn.fetchrow("""
        INSERT INTO case_notes (case_id, officer_id, officer_name, officer_agency, officer_country, note_text, note_type)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
    """, case_id, officer_id, officer["name"], officer_agency, officer["country_code"], note_text, note_type)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "ADD_NOTE", officer["name"], "COLLABORATION", f"note_type={note_type}", f"note_id={note['id']}"
    )
    # Update case timestamp
    await conn.execute("UPDATE cases SET updated_date=NOW() WHERE case_id=$1", case_id)
    await conn.close()
    
    return {"success": True, "note": dict(note)}

@app.get("/api/cases/{case_id}/files")
async def get_case_files(case_id: str):
    """Get all evidence files uploaded for a case."""
    conn = await asyncpg.connect(**DB_CONFIG)
    files = await conn.fetch("SELECT * FROM case_files WHERE case_id=$1 ORDER BY uploaded_date DESC", case_id)
    await conn.close()
    return [dict(f) for f in files]

@app.post("/api/cases/{case_id}/files")
async def upload_case_file(request: Request, case_id: str,
    file: UploadFile = File(...), description: str = Form("")):
    """Upload an evidence file to a case — requires police auth."""
    payload = await auth_police(request)
    officer_id = payload.get("oid")
    
    conn = await asyncpg.connect(**DB_CONFIG)
    officer = await conn.fetchrow("SELECT name FROM police_officers WHERE id=$1", officer_id)
    if not officer:
        await conn.close()
        raise HTTPException(404, "Officer not found")
    
    # Verify case exists
    case = await conn.fetchrow("SELECT case_id FROM cases WHERE case_id=$1", case_id)
    if not case:
        await conn.close()
        raise HTTPException(404, "Case not found")
    
    # Save file
    import os, hashlib
    upload_dir = f"/gfin/evidence_files/{case_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    safe_filename = os.path.basename(file.filename or "unnamed")
    filepath = f"{upload_dir}/{safe_filename}"
    with open(filepath, "wb") as f:
        f.write(file_content)
    
    record = await conn.fetchrow("""
        INSERT INTO case_files (case_id, officer_id, officer_name, filename, filepath, file_hash, file_size, mime_type, description)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
    """, case_id, officer_id, officer["name"], safe_filename, filepath, file_hash, len(file_content), file.content_type or "application/octet-stream", description)
    
    # Audit log
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "UPLOAD_FILE", officer["name"], "EVIDENCE", safe_filename, f"file_id={record['id']}, size={len(file_content)}"
    )
    await conn.close()
    
    return {"success": True, "file": dict(record)}

@app.get("/api/cases/{case_id}/full")
async def get_case_full(case_id: str):
    """Get full case detail with notes, files, evidence, audit trail, and officer info."""
    conn = await asyncpg.connect(**DB_CONFIG)
    case = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not case:
        await conn.close()
        raise HTTPException(404, "Case not found")
    
    evidence = await conn.fetch("SELECT * FROM evidence WHERE case_id=$1 ORDER BY created_date", case_id)
    alerts = await conn.fetch("SELECT * FROM alerts WHERE case_id=$1 ORDER BY created_date DESC", case_id)
    notes = await conn.fetch("""
        SELECT cn.*, po.email as officer_email, po.badge_number
        FROM case_notes cn
        LEFT JOIN police_officers po ON cn.officer_id = po.id
        WHERE cn.case_id = $1 ORDER BY cn.created_date DESC
    """, case_id)
    files = await conn.fetch("SELECT * FROM case_files WHERE case_id=$1 ORDER BY uploaded_date DESC", case_id)
    audit = await conn.fetch("SELECT * FROM audit_log WHERE case_id=$1 ORDER BY timestamp DESC", case_id)
    people = await conn.fetch("SELECT * FROM people WHERE case_id=$1", case_id)
    complaints = await conn.fetch("""
        SELECT vc.reference_number, vc.scam_type, vc.created_date, v.name as victim_name, v.country as victim_country
        FROM victim_complaints vc JOIN victims v ON vc.victim_id = v.id
        WHERE vc.case_id = $1 ORDER BY vc.created_date DESC
    """, case_id)
    await conn.close()
    
    return {
        "case": dict(case),
        "evidence": [dict(e) for e in evidence],
        "alerts": [dict(a) for a in alerts],
        "notes": [dict(n) for n in notes],
        "files": [dict(f) for f in files],
        "audit_trail": [dict(a) for a in audit],
        "people": [dict(p) for p in people],
        "linked_complaints": [dict(c) for c in complaints]
    }

@app.get("/api/officers/directory")
async def officers_directory(request: Request):
    """List all police officers for contact directory — requires auth (any role)."""
    payload = await auth_police(request)
    conn = await asyncpg.connect(**DB_CONFIG)
    officers = await conn.fetch("""
        SELECT id, name, email, role, agency, country_code, badge_number, is_active, created_date, last_login
        FROM police_officers WHERE is_active = TRUE
        ORDER BY country_code, agency, name
    """)
    await conn.close()
    return {"officers": [dict(o) for o in officers], "current_officer_id": payload.get("oid")}

@app.post("/api/cases/{case_id}/assign")
async def assign_case(request: Request, case_id: str, officer_name: str = Body(..., embed=True)):
    """Assign a case to a specific officer — requires auth."""
    payload = await auth_police(request)
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute("UPDATE cases SET assigned_to_officer=$1, updated_date=NOW() WHERE case_id=$2", officer_name, case_id)
    await conn.execute(
        "INSERT INTO audit_log (case_id, action, actor, tool, query, result) VALUES ($1, $2, $3, $4, $5, $6)",
        case_id, "ASSIGN_CASE", payload.get("agency", "unknown"), "DASHBOARD", f"assigned_to={officer_name}", "SUCCESS"
    )
    await conn.close()
    return {"success": True, "assigned_to": officer_name}


# ============================================================
# TELEGRAM ALERT CONFIGURATION
# ============================================================

    
    process_bot_updates()
    from telegram_alerts import load_subscribers
    subs = load_subscribers()
    return {"processed": True, "total_subscribers": len(subs)}

@app.get("/api/telegram/subscribers")
async def telegram_subscribers(request: Request):
    """Get subscriber count. Requires police auth."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    
    from telegram_alerts import load_subscribers
    subs = load_subscribers() if _telegram else []
    return {"subscriber_count": len(subs)}



# ============================================================
# TELEGRAM BOT STATUS (PUBLIC — NO AUTH)
# ============================================================

@app.get("/api/telegram/status")
async def telegram_bot_status():
    """Public endpoint — check Telegram bot status."""
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    bot_name = "not_configured"
    sub_count = 0
    if _telegram and token:
        try:
            from telegram_alerts import get_bot, load_subscribers
            bot = get_bot()
            if bot:
                info = bot.get_bot_info()
                if info.get("ok"):
                    bot_name = info.get("result", {}).get("username", "unknown")
            subs = load_subscribers()
            sub_count = len(subs)
        except Exception as e:
            bot_name = f"error"
    return {
        "configured": bool(token),
        "bot_username": bot_name,
        "subscribers": sub_count,
        "ready": _telegram,
    }


# ============================================================
# SCAM AWARENESS BROADCAST (PUBLIC)
# ============================================================

@app.get("/api/awareness/stats")
async def awareness_stats():
    """Get awareness broadcast statistics (public)."""
    if not _awareness:
        return {"ready": False, "error": "Awareness module not loaded"}
    return get_awareness_stats()

@app.get("/api/awareness/types")
async def awareness_types():
    """List all scam types covered by awareness system (public)."""
    if not _awareness:
        return {"types": [], "ready": False}
    return {
        "types": [
            {"scam_type": m["scam_type"], "title": m["title"], "emoji": m["emoji"]}
            for m in SCAM_AWARENESS_MESSAGES
        ],
        "total": len(SCAM_AWARENESS_MESSAGES)
    }

@app.post("/api/awareness/broadcast")
async def awareness_broadcast(request: Request):
    """Trigger a scam awareness broadcast to all subscribers. Police only."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    if not _awareness:
        return {"error": "Awareness module not loaded"}
    sent = send_awareness_broadcast()
    return {"sent": sent, "message": f"Awareness broadcast sent to {sent} subscribers"}

@app.post("/api/awareness/broadcast/{scam_type}")
async def awareness_broadcast_specific(scam_type: str, request: Request):
    """Broadcast a specific scam awareness message. Police only."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    if not _awareness:
        return {"error": "Awareness module not loaded"}
    sent = send_custom_awareness(scam_type)
    return {"sent": sent, "scam_type": scam_type}


# ============================================================
# SCAM WEBSITES DATABASE (PUBLIC)
# ============================================================

@app.get("/api/scam-sites/check/{domain}")
async def scam_sites_check(domain: str):
    """Check if a domain is a known scam site (public)."""
    if not _scam_sites:
        return {"found": False, "error": "Database not configured"}
    return check_domain(domain)

@app.get("/api/scam-sites/list")
async def scam_sites_list(limit: int = 50, offset: int = 0, scam_type: str = None, risk_level: str = None, sort: str = "report_count"):
    """List known scam websites (public)."""
    if not _scam_sites:
        return {"sites": [], "total": 0, "error": "Database not configured"}
    return list_scam_sites(limit=limit, offset=offset, scam_type=scam_type, risk_level=risk_level, sort=sort)

@app.get("/api/scam-sites/search")
async def scam_sites_search(q: str = "", limit: int = 20):
    """Search scam websites by domain name (public)."""
    if not _scam_sites or not q:
        return {"sites": [], "query": q}
    return search_scam_sites(q, limit=limit)

@app.get("/api/scam-sites/stats")
async def scam_sites_stats():
    """Get scam websites database statistics (public)."""
    if not _scam_sites:
        return {"error": "Database not configured"}
    return get_scam_sites_stats()

@app.get("/scam-sites")
async def scam_sites_page():
    """Public scam website database page."""
    return HTMLResponse(open("/gfin/scam_sites_page.html").read())


# ============================================================
# PDF CASE REPORTS
# ============================================================

@app.post("/api/reports/generate")
async def generate_report(request: Request):
    """Generate a PDF case report. Police only."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    if not _pdf_reports:
        return {"error": "PDF module not loaded"}
    
    import json as _json
    body = await request.json()
    case_data = body.get("case_data", {})
    evidence_items = body.get("evidence_items", [])
    
    output_path = f"/gfin/reports/case_{case_data.get('case_id', 'unknown')}_{int(time.time())}.pdf"
    import os
    os.makedirs("/gfin/reports", exist_ok=True)
    
    try:
        result_path = generate_case_report(case_data, evidence_items, output_path)
        return {"success": True, "path": result_path, "filename": os.path.basename(result_path)}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/reports/download/{filename}")
async def download_report(filename: str, request: Request):
    """Download a generated PDF report. Police only."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    
    import os
    filepath = f"/gfin/reports/{filename}"
    if not os.path.exists(filepath) or not filename.endswith(".pdf"):
        raise HTTPException(404, "Report not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(filepath, media_type="application/pdf", filename=filename)

# ============================================================
# DASHBOARD ANALYTICS (PUBLIC)
# ============================================================

@app.get("/api/analytics/overview")
async def analytics_overview():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_overview()

@app.get("/api/analytics/scam-types")
async def analytics_scam_types():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_scam_types()

@app.get("/api/analytics/risk-levels")
async def analytics_risk_levels():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_risk_levels()

@app.get("/api/analytics/countries")
async def analytics_countries():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_countries()

@app.get("/api/analytics/timeline")
async def analytics_timeline(period: str = "daily"):
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_timeline(period)

@app.get("/api/analytics/financial-loss")
async def analytics_financial_loss():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_financial_loss()

@app.get("/api/analytics/crypto")
async def analytics_crypto():
    if not _analytics:
        return {"error": "Analytics module not loaded"}
    return await get_crypto_analytics()

# ============================================================
# VICTIM NOTIFICATIONS
# ============================================================

@app.post("/api/notifications/send")
async def send_notification(request: Request):
    """Send a notification to a victim. Police only."""
    if not _police_auth:
        raise HTTPException(500, "Auth not configured")
    payload = await auth_police(request)
    if not _notifications:
        return {"error": "Notifications module not loaded"}
    
    import json as _json
    body = await request.json()
    result = notify_victim(
        complaint_ref=body.get("complaint_ref", ""),
        notification_type=body.get("notification_type", "update"),
        extra_data=body.get("extra_data", {})
    )
    return {"success": result}

# ============================================================
# ADDITIONAL PAGES
# ============================================================

@app.get("/analytics")
async def analytics_page():
    return HTMLResponse(open("/gfin/analytics_dashboard.html").read())

@app.get("/victim-portal")
async def victim_portal_i18n_page():
    return HTMLResponse(open("/gfin/victim_portal_i18n.html").read())

@app.get("/police/mobile")
async def police_mobile_dashboard():
    """Mobile-responsive police dashboard."""
    return HTMLResponse(open("/gfin/investigator_workbench.html").read())

@app.get("/case", response_class=HTMLResponse)
async def case_detail_page(request: Request):
    if _police_auth:
        from urllib.parse import unquote
        token = unquote(request.cookies.get("gfin_police_token", ""))
        if not token:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
    with open("/gfin/web/case_detail.html") as f:
        return HTMLResponse(f.read())

# ==================== DASHBOARD & PORTAL ====================

@app.get("/", response_class=HTMLResponse)
async def homepage():
    """Official GFIN homepage."""
    return HTMLResponse(open("/gfin/gfin_homepage.html").read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_alias(request: Request):
    """Police dashboard - checks for auth, redirects if not logged in."""
    token = ""
    if _police_auth:
        from urllib.parse import unquote
        token = unquote(request.cookies.get("gfin_police_token", ""))
        if not token:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
        payload = verify_token(token)
        if not payload:
            return HTMLResponse('<script>window.location.href="/police/login";</script>')
    try:
        with open("/gfin/investigator_workbench.html") as f:
            html = f.read()
        if token:
            # Server token takes priority over localStorage (which may have stale token)
            html = html.replace(
                "let authToken = localStorage.getItem('gfin_token') || '';",
                "let authToken = '" + token + "'; localStorage.setItem('gfin_token', authToken);"
            )
            # Also inject CSS to hide the login overlay since server already verified the token
            html = html.replace(
                '<div id="loginOverlay" class="login-overlay">',
                '<div id="loginOverlay" class="login-overlay" style="display:none !important;">'
            )
            # And show the app content - replace existing style, don't add duplicate
            html = html.replace(
                '<div id="app" style="display:none">',
                '<div id="app" style="display:block !important;">'
            )
        from starlette.responses import Response
        return Response(content=html, media_type="text/html", headers={"Cache-Control": "no-store, no-cache, must-revalidate"})
    except:
        return HTMLResponse("<h1>GFIN Server</h1><p>Dashboard at /gfin/police_dashboard_mobile.html</p>")

@app.get("/victim", response_class=HTMLResponse)
async def victim_portal():
    try:
        with open("/gfin/victim_portal_i18n.html") as f:
            return f.read()
    except:
        return HTMLResponse("<h1>GFIN Victim Portal</h1><p>File not found</p>")

@app.get('/favicon.ico', response_class=Response)
async def favicon():
    return Response(content=open('/gfin/web/favicon.svg','rb').read(), media_type='image/svg+xml')

@app.get('/report', response_class=HTMLResponse)
async def report_page():
    return HTMLResponse('<script>window.location.href="/victim";</script>')




# ==================== TRACKED DOMAINS (Domain Intelligence Database) ====================

@app.get("/api/domains")
async def list_tracked_domains(
    risk_level: str = None,
    source: str = None,
    limit: int = 100,
    offset: int = 0
):
    """List all tracked domains — these are NOT cases, just domain intelligence."""
    async with db_pool.acquire() as conn:
        query = "SELECT * FROM tracked_domains"
        params = []
        conditions = []
        if risk_level:
            conditions.append("risk_level = $%d" % (len(params) + 1))
            params.append(risk_level.upper())
        if source:
            conditions.append("source = $%d" % (len(params) + 1))
            params.append(source.upper())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY risk_score DESC, first_seen DESC LIMIT $%d OFFSET $%d" % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])
        
        domains = await conn.fetch(query, *params)
        total = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains")
        
        return {
            "total": total,
            "returned": len(domains),
            "domains": [dict(d) for d in domains]
        }


@app.get("/api/domains/stats")
async def domain_stats():
    """Get statistics for tracked domains."""
    async with db_pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM tracked_domains")
        by_risk = await conn.fetch("SELECT risk_level, COUNT(*) as count FROM tracked_domains GROUP BY risk_level ORDER BY count DESC")
        by_source = await conn.fetch("SELECT source, COUNT(*) as count FROM tracked_domains GROUP BY source ORDER BY count DESC")
        
        return {
            "total_domains": total,
            "by_risk": [{"level": r["risk_level"], "count": r["count"]} for r in by_risk],
            "by_source": [{"source": r["source"], "count": r["count"]} for r in by_source],
        }

@app.get("/api/domains/{domain}")
async def get_tracked_domain(domain: str):
    """Get details for a specific tracked domain."""
    async with db_pool.acquire() as conn:
        d = await conn.fetchrow("SELECT * FROM tracked_domains WHERE domain = $1", domain)
        if not d:
            raise HTTPException(status_code=404, detail="Domain not found")
        return dict(d)




# ==================== PROXY & PRIVACY PIERCING ====================

@app.get("/api/piercer/investigate/{domain}")
async def piercer_investigate(domain: str):
    """Run full proxy/privacy piercing investigation on a domain.
    Detects WHOIS privacy, CDN proxies, finds real origin IP, traces physical location.
    """
    piercer = ProxyPiercer()
    result = await piercer.investigate(domain)
    return result

@app.post("/api/piercer/investigate-case/{case_id}")
async def piercer_investigate_case(case_id: str, request: Request):
    """Run proxy piercing on the primary domain of a case.
    Saves all findings as evidence and entities in the case lifecycle.
    """
    import asyncpg, os
    body = await request.json() if request.headers.get("content-type") else {}
    officer_name = body.get("officer_name", "SYSTEM")
    officer_id = body.get("officer_id")
    
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        database="gfin", user="gfin",
        password=os.environ.get("DB_PASSWORD", "")
    )
    try:
        # Get the case target domain
        case = await conn.fetchrow("SELECT case_id, target, target_type FROM cases WHERE case_id = $1", case_id)
        if not case:
            raise HTTPException(404, "Case not found")
        
        domain = case["target"]
        if case["target_type"] != "DOMAIN":
            # Try to extract domain from the target
            import re
            domain_match = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})', domain)
            if domain_match:
                domain = domain_match.group(1)
            else:
                raise HTTPException(400, "Case target is not a domain")
        
        # Run the piercer
        piercer = ProxyPiercer()
        result = await piercer.investigate(domain, db_conn=conn)
        
        # Save evidence to the case
        evidence_count = 0
        for ev in result.get("evidence", []):
            count = await conn.fetchval("SELECT COUNT(*) FROM evidence WHERE case_id = $1", case_id)
            evidence_id = f"E-{count + 1:03d}"
            
            await conn.execute(
                """INSERT INTO evidence 
                   (case_id, evidence_id, phase, finding, source_provider, source_type, confidence, added_by_officer, added_by_officer_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                case_id, evidence_id,
                "ACTIVE_INVESTIGATION",
                ev["finding"],
                f"ProxyPiercer/{ev['method']}",
                "AUTO",
                ev["confidence"],
                officer_name, officer_id
            )
            evidence_count += 1
        
        # Save origin IP as entity
        if result.get("origin_ip"):
            existing = await conn.fetchrow(
                "SELECT id FROM case_entities WHERE case_id = $1 AND entity_type = 'IP' AND entity_value = $2",
                case_id, result["origin_ip"]
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'IP', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)""",
                    case_id, result["origin_ip"],
                    json.dumps({"method": "origin_discovery", "cdn_provider": result.get("cdn_provider"), "physical_location": result.get("physical_location")}),
                    officer_name
                )
        
        # Save physical location as entity
        if result.get("physical_location"):
            loc = result["physical_location"]
            loc_str = f"{loc.get('city', '?')}, {loc.get('country', '?')}"
            existing = await conn.fetchrow(
                "SELECT id FROM case_entities WHERE case_id = $1 AND entity_type = 'ADDRESS' AND entity_value = $2",
                case_id, loc_str
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'ADDRESS', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)""",
                    case_id, loc_str,
                    json.dumps({"lat": loc.get("lat"), "lon": loc.get("lon"), "city": loc.get("city"), "country": loc.get("country"), "timezone": loc.get("timezone")}),
                    officer_name
                )
        
        # Save real identity as entity if found
        if result.get("real_identity"):
            ident = result["real_identity"]
            if ident.get("email"):
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'EMAIL', $2, $3::jsonb, 'PROXY_PIERCER', 'HIGH', 'IDENTIFIED', $4)
                       ON CONFLICT DO NOTHING""",
                    case_id, ident["email"],
                    json.dumps({"source": "historical_whois", "name": ident.get("name")}),
                    officer_name
                )
            if ident.get("name"):
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, 'PERSON', $2, $3::jsonb, 'PROXY_PIERCER', 'MEDIUM', 'SUSPECTED', $4)
                       ON CONFLICT DO NOTHING""",
                    case_id, ident["name"],
                    json.dumps({"source": "historical_whois", "email": ident.get("email")}),
                    officer_name
                )
        
        # Save shared cert domains as entities
        for shared_domain in result.get("correlations", []):
            if shared_domain.get("entity_type") in ["DOMAIN", "EMAIL", "PHONE"]:
                await conn.execute(
                    """INSERT INTO case_entities 
                       (case_id, entity_type, entity_value, entity_metadata, source, confidence, status, added_by_officer)
                       VALUES ($1, $2, $3, $4::jsonb, 'PROXY_PIERCER', 'MEDIUM', 'CORRELATED', $5)
                       ON CONFLICT DO NOTHING""",
                    case_id, shared_domain["entity_type"], shared_domain["entity_value"],
                    json.dumps({"correlated_case": shared_domain.get("source"), "evidence": shared_domain.get("evidence")}),
                    officer_name
                )
        
        # Add timeline event
        await conn.execute(
            """INSERT INTO case_timeline (case_id, event_type, event_title, event_description, event_metadata, officer_name)
               VALUES ($1, 'PROXY_PIERCING', $2, $3, $4::jsonb, $5)""",
            case_id,
            f"Proxy piercing completed for {domain}",
            result.get("summary", "")[:500],
            json.dumps({
                "cdn_detected": result.get("cdn_detected"),
                "privacy_detected": result.get("privacy_detected"),
                "origin_ip": result.get("origin_ip"),
                "confidence": result.get("confidence"),
                "evidence_count": evidence_count
            }),
            officer_name
        )
        
        return {
            "status": "ok",
            "domain": domain,
            "evidence_added": evidence_count,
            "result": result
        }
    finally:
        await conn.close()

@app.get("/api/piercer/quick/{domain}")
async def piercer_quick_check(domain: str):
    """Quick proxy/CDN check — returns just the detection results without full investigation."""
    piercer = ProxyPiercer()
    
    # Only run CDN detection and privacy check
    import socket
    ip_info = {}
    primary_ip = None
    try:
        addrs = socket.getaddrinfo(domain, None)
        primary_ip = addrs[0][4][0]
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{primary_ip}/json") as r:
                if r.status == 200:
                    ip_info = await r.json()
    except Exception:
        pass
    
    cdn_result = await piercer.detect_cdn(domain, ip_info)
    
    return {
        "domain": domain,
        "ip": primary_ip,
        "ip_info": ip_info,
        "is_cdn_protected": cdn_result["is_cdn_protected"],
        "cdn_provider": cdn_result["cdn_provider"],
        "cdn_indicators": cdn_result["cdn_indicators"],
        "bypass_available": cdn_result.get("bypass_methods", []),
    }

@app.get("/health")
async def health():
    return {"status": "OK", "server": "GFIN Standalone v2.0",
            "database": "connected" if db_pool else "disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat()}


# ==================== SEED DATA ====================

async def seed_data():
    async with db_pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE case_id='GFIN-CASE-001'")
        if existing > 0:
            logger.info("Already seeded")
            return

        await conn.execute("""INSERT INTO cases (case_id, status, target, target_type, trigger, summary, classification,
            accusation_level, confidence, scam_patterns, affected_countries, routed_to_countries, victim_count, victim_loss)
            VALUES ('GFIN-CASE-001', 'INVESTIGATING', 'cncintelinfo.com', 'DOMAIN', 'PUBLIC_REPORT',
            'Large-scale brand impersonation campaign targeting CNC Intelligence Inc. 50+ fraudulent domains since June 2024.',
            'LAW ENFORCEMENT SENSITIVE', 'REQUIRES_INVESTIGATION', 0.8,
            ARRAY['BRAND_IMPERSONATION', 'RECOVERY_SCAM', 'EMAIL_PHISHING'],
            ARRAY['GB', 'ES', 'DE'], ARRAY['GB', 'ES', 'DE', 'EUROPOL', 'INTERPOL'], 3, '$35,000+')""")

        people = [
            ('GFIN-CASE-001', 'VICTIM', 'CNC Intelligence Inc.', 'ORGANIZATION', 'Legitimate crypto investigation firm being impersonated.', 'CNC Intelligence report', 'CONFIRMED'),
            ('GFIN-CASE-001', 'SUSPECT', 'Scammer(s) — Real Name Unknown', 'UNKNOWN', 'Domain privacy protection active. Requires legal process.', 'RDAP/WHOIS', 'UNRESOLVED'),
            ('GFIN-CASE-001', 'SUSPECT', 'Payback LTD', 'ORGANIZATION', 'Recovery scam — website SEIZED by FBI San Diego.', 'Reddit + FBI press release', 'STRONGLY_SUPPORTED'),
            ('GFIN-CASE-001', 'SUSPECT', 'MyChargeBack', 'ORGANIZATION', 'Recovery scam — website SEIZED by FBI.', 'FBI press release', 'STRONGLY_SUPPORTED'),
            ('GFIN-CASE-001', 'SUSPECT', 'Claim Justice', 'ORGANIZATION', 'Recovery scam — website SEIZED by FBI.', 'FBI press release', 'STRONGLY_SUPPORTED'),
            ('GFIN-CASE-001', 'SUSPECT', 'Cyber-Forensics.net', 'ORGANIZATION', 'Recovery scam listed on CryptoLegal UK.', 'CryptoLegal UK + LegalByte', 'STRONGLY_SUPPORTED'),
            ('GFIN-CASE-001', 'WITNESS', 'FBI San Diego Field Office', 'ORGANIZATION', 'Seized Payback LTD, MyChargeBack, Claim Justice websites.', 'FBI press release', 'CONFIRMED'),
            ('GFIN-CASE-001', 'VICTIM', 'Reddit r/Scams user', 'PSEUDONYMOUS', 'Reported $35,000 loss to fake CNC Intelligence rep.', 'Reddit r/Scams', 'POSSIBLE'),
            ('GFIN-CASE-001', 'INFRASTRUCTURE', 'NameCheap, Inc.', 'REGISTRAR', 'Domain registrar for cncintelinfo.com. Not complicit.', 'RDAP', 'CONFIRMED'),
            ('GFIN-CASE-001', 'INFRASTRUCTURE', 'ProtonMail (Proton AG)', 'EMAIL_PROVIDER', 'Email provider. Swiss-based.', 'DNS MX records', 'CONFIRMED'),
            ('GFIN-CASE-001', 'INFRASTRUCTURE', 'SEDO GmbH', 'HOSTING', 'Domain parking in Munich. Infrastructure lead only.', 'ipinfo.io', 'CONFIRMED'),
            ('GFIN-CASE-001', 'INVESTIGATOR', 'GPT Luna (GFIN-CEA)', 'AI_AGENT', 'GFIN Chief Engineering Agent.', 'GFIN system', 'CONFIRMED'),
        ]
        for p in people:
            await conn.execute("INSERT INTO people (case_id, role, name, entity_type, details, source, confidence) VALUES ($1,$2,$3,$4,$5,$6,$7)", *p)

        evidence_items = [
            ('E-001', 'CAMPAIGN_DISCOVERY', '50+ domains impersonating CNC Intelligence', 'CNC Intelligence Inc.', 'https://cncintel.com/report', 'Public corporate report', 'HIGH'),
            ('E-004', 'DOMAIN_REGISTRATION', 'cncintelinfo.com registered 2026-02-26 via NameCheap, ProtonMail MX only', 'Google DoH', 'dns.google', 'DNS protocol query', 'HIGH'),
            ('E-007', 'IP_INTELLIGENCE', 'IP 91.195.240.123 = AS47846 SEDO GmbH, Munich', 'ipinfo.io', 'ipinfo.io', 'IP geolocation', 'HIGH'),
            ('E-011', 'VICTIM_CORRELATION', 'Reddit victims report losing $35,000 to fake CNC Intelligence representatives', 'Reddit', 'reddit.com/r/Scams', 'Public forum posts', 'MEDIUM'),
            ('E-016', 'LAW_ENFORCEMENT', 'FBI San Diego seized MyChargeBack, Payback LTD, Claim Justice as connected recovery scam network', 'FBI', 'fbi.gov', 'Law enforcement press release', 'HIGH'),
        ]
        for e in evidence_items:
            await conn.execute("INSERT INTO evidence (case_id, evidence_id, phase, finding, source_provider, source_url, source_type, confidence) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (evidence_id) DO NOTHING", 'GFIN-CASE-001', *e)

        alerts = [
            ('ALERT-REAL-001', 'GFIN-CASE-001', 'GB', 'CRITICAL', 'cncintelinfo.com — brand impersonation. 50+ domains. UK + ES victims. $35K+ losses.', 'Action Fraud should review full report.', 'reports@actionfraud.police.uk', 'cncintelinfo.com'),
            ('ALERT-REAL-002', 'GFIN-CASE-001', 'ES', 'HIGH', 'Spanish victims targeted by fake CNC Intelligence recovery scam.', 'Policía Nacional should investigate.', 'denuncias.policia@policia.es', 'cncintelinfo.com'),
            ('ALERT-REAL-003', 'GFIN-CASE-001', 'DE', 'MEDIUM', 'cncintelltd.com hosted on SEDO GmbH in Munich.', 'BKA should note infrastructure lead.', 'cybercrime@bka.de', 'cncintelltd.com'),
            ('ALERT-REAL-004', 'GFIN-CASE-001', 'EUROPOL', 'CRITICAL', 'CROSS-BORDER: CNC Intelligence network affects GB+ES+DE. FBI-seized Payback LTD connected.', 'Europol ECCC should coordinate.', '', 'cncintelinfo.com'),
            ('ALERT-REAL-005', 'GFIN-CASE-001', 'INTERPOL', 'HIGH', 'CROSS-BORDER: FBI seized connected sites. 50+ domains.', 'INTERPOL should coordinate with FBI.', '', 'cncintelinfo.com'),
        ]
        for a in alerts:
            await conn.execute("INSERT INTO alerts (alert_id, case_id, country, level, message, next_action, police_contact, target) VALUES ($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT (alert_id) DO NOTHING", *a)

        countries = [
            ('GB', 'United Kingdom', json.dumps(["Action Fraud", "NCA Cyber Crime Unit"]), 'europol@cityoflondon.police.uk', 'interpollondon@nca.gov.uk', ["en"], 'Europe/London'),
            ('ES', 'Spain', json.dumps(["Policía Nacional", "Guardia Civil TECO"]), '', '', ["es"], 'Europe/Madrid'),
            ('DE', 'Germany', json.dumps(["BKA Cybercrime", "LKA"]), '', '', ["de"], 'Europe/Berlin'),
            ('EUROPOL', 'Europol ECCC', json.dumps(["European Cyber Crime Centre"]), '', '', ["en"], 'Europe/Amsterdam'),
            ('INTERPOL', 'INTERPOL', json.dumps(["Cybercrime Directorate"]), '', '', ["en", "fr"], 'Europe/Paris'),
        ]
        for c in countries:
            await conn.execute("INSERT INTO country_routing (country_code, country_name, contacts, europol_contact, interpol_contact, languages, timezone) VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (country_code) DO NOTHING", *c)

        logger.info("Seed data inserted")




# ============================================================
# INTELLIGENCE PLAYBOOK API — Subject to Evidence to Physical Address
# ============================================================


# ==================== INFO PAGES ====================

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Privacy Policy page."""
    return HTMLResponse(open("/gfin/privacy_policy.html").read())

@app.get("/terms", response_class=HTMLResponse)
async def terms_of_use():
    """Terms of Use page."""
    return HTMLResponse(open("/gfin/terms_of_use.html").read())

@app.get("/contact", response_class=HTMLResponse)
async def contact_page():
    """Contact page."""
    return HTMLResponse(open("/gfin/contact_page.html").read())

@app.get("/api/docs", response_class=HTMLResponse)
async def api_docs_page():
    """API documentation page."""
    return HTMLResponse(open("/gfin/api_docs.html").read())


@app.get("/gfin-i18n.js")
async def serve_i18n():
    """Serve the shared i18n translations JavaScript file."""
    import os
    js_path = "/gfin/gfin-i18n.js"
    if os.path.exists(js_path):
        return HTMLResponse(open(js_path).read(), media_type="application/javascript")
    return HTMLResponse("// i18n file not found", media_type="application/javascript", status_code=404)

@app.get("/api/playbook/investigate")
async def playbook_investigate(
    identifier: str = Query(..., description="Domain, IP, wallet, or company number to investigate"),
    identifier_type: str = Query("DOMAIN", description="DOMAIN, IP, WALLET, COMPANY, etc."),
    trigger: str = Query("MANUAL", description="Trigger type"),
    trigger_reason: str = Query("", description="Why we started investigating"),
    operator: str = Query("GFIN", description="Who authorized this"),
    authority: str = Query("", description="Legal authority")
):
    """Run a full intelligence playbook investigation: Subject -> Evidence -> Physical Address."""
    if not _playbook:
        return {"error": "Playbook engine not loaded"}, 500
    
    result = _playbook.investigate({
        "trigger": trigger,
        "trigger_reason": trigger_reason,
        "identifier": identifier,
        "identifier_type": identifier_type,
        "operator": operator,
        "authority": authority,
    })
    
    # Return everything except the raw report (it's in the report field)
    return {
        "investigation_id": result["investigation_id"],
        "timestamp": result["timestamp"],
        "subject": result["subject"],
        "evidence_chain": result["evidence_chain"],
        "attribution_chain": result["attribution_chain"],
        "physical_locations": result["physical_locations"],
        "people_identified": result["people_identified"],
        "companies_identified": result["companies_identified"],
        "digital_identifiers": result["digital_identifiers"],
        "financial_indicators": result["financial_indicators"],
        "scam_indicators": result["scam_indicators"],
        "confidence": result["confidence"],
        "accusation_level": result["accusation_level"],
        "next_steps": result["next_steps"],
        "report": result["report"],
        "summary": {
            "evidence_steps": len(result["evidence_chain"]),
            "physical_locations_found": len(result["physical_locations"]),
            "digital_identifiers_found": len(result["digital_identifiers"]),
            "scam_indicators_found": len(result["scam_indicators"]),
            "accusation_level": result["accusation_level"],
            "confidence": result["confidence"],
        }
    }


@app.get("/api/playbook/entities")
async def playbook_entities():
    """List all entity types in the intelligence playbook and what they discover."""
    from intelligence_playbook_v52 import INTELLIGENCE_PLAYBOOK, TRIGGER_TYPES
    return {
        "entity_types": {
            k: {
                "what_to_find": v["what_to_find"],
                "how_to_find": v["how_to_find"],
                "leads_to": v["leads_to"],
                "attribution_note": v.get("attribution_note", ""),
            }
            for k, v in INTELLIGENCE_PLAYBOOK.items()
        },
        "trigger_types": TRIGGER_TYPES,
    }


@app.post("/api/playbook/investigate-domain")
async def playbook_investigate_domain(request: Request):
    """Investigate a domain — full Subject to Evidence to Physical Address chain."""
    body = await request.json()
    if not _playbook:
        return {"error": "Playbook engine not loaded"}, 500
    
    domain = body.get("domain", "")
    trigger_reason = body.get("trigger_reason", f"Manual investigation of {domain}")
    
    result = _playbook.investigate({
        "trigger": body.get("trigger", "MANUAL"),
        "trigger_reason": trigger_reason,
        "identifier": domain,
        "identifier_type": "DOMAIN",
        "operator": body.get("operator", "GFIN"),
        "authority": body.get("authority", ""),
    })
    return result




# ============================================================
# GLOBAL COUNTRY ROUTING API
# ============================================================

@app.get("/api/countries")
async def list_countries():
    """List all configured countries with their cybercrime contacts."""
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch("""
        SELECT country_code, country_name, contacts, languages, timezone,
               interpol_contact, europol_contact
        FROM country_routing ORDER BY country_name
    """)
    await conn.close()
    return {
        "total_countries": len(rows),
        "countries": [
            {
                "code": r["country_code"],
                "name": r["country_name"],
                "contacts": r["contacts"],
                "languages": r["languages"] if r["languages"] else [],
                "timezone": r["timezone"],
                "interpol_contact": r["interpol_contact"] or "",
                "europol_contact": r["europol_contact"] or "",
                "has_europol": bool(r["europol_contact"]),
            }
            for r in rows
        ]
    }


@app.get("/api/countries/{country_code}")
async def get_country(country_code: str):
    """Get routing details for a specific country."""
    conn = await asyncpg.connect(**DB_CONFIG)
    row = await conn.fetchrow(
        "SELECT * FROM country_routing WHERE country_code = UPPER(\)", country_code
    )
    await conn.close()
    if not row:
        return {"error": f"Country {country_code} not configured", "fallback": "INTERPOL"}
    return dict(row)


@app.get("/api/countries/search/{name}")
async def search_country(name: str):
    """Search countries by name (partial match)."""
    conn = await asyncpg.connect(**DB_CONFIG)
    rows = await conn.fetch(
        "SELECT country_code, country_name FROM country_routing WHERE country_name ILIKE %s ORDER BY country_name",
        "%' + name + '%"
    )
    await conn.close()
    return {"matches": [{"code": r[0], "name": r[1]} for r in rows]}



# ============================================================
# MODULE API ROUTES — Batch Integration (11 modules)
# ============================================================

try:
    from module_routes_batch1 import register_batch1_routes
    register_batch1_routes(app, auth_police, auth_police_admin, rate_limiter)
    print("✅ Batch 1 routes loaded: evidence_vault, fraud_graph, search_platform, compliance")
except Exception as e:
    print(f"Warning: batch 1 routes not loaded: {e}")

try:
    from module_routes_batch2 import register_batch2_routes
    register_batch2_routes(app, auth_police, auth_police_admin, rate_limiter)
    print("✅ Batch 2 routes loaded: campaign_engine, global_matching, early_warning, continuous_monitoring")
except Exception as e:
    print(f"Warning: batch 2 routes not loaded: {e}")

try:
    from module_routes_batch3 import register_batch3_routes
    from module_routes_batch4 import register_batch4_routes
    from module_routes_batch5 import register_batch5_routes
    from module_routes_batch6 import register_batch6_routes
    from module_routes_batch7 import register_batch7_routes
    from module_routes_batch8 import register_batch8_routes
    from module_routes_batch9 import register_batch9_routes
    register_batch3_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch4_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch5_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch6_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch7_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch8_routes(app, auth_police, auth_police_admin, rate_limiter)
    register_batch9_routes(app, auth_police, auth_police_admin, rate_limiter)
    from laundering_routes import router as laundering_router
    app.include_router(laundering_router)
    from dashboard_enhanced_routes import router as dashboard_enhanced_router
    app.include_router(dashboard_enhanced_router)
    try:
        from proxy_piercer import ProxyPiercer
        from investigation_lifecycle import router as lifecycle_router
        app.include_router(lifecycle_router)
        from investigation_routes import router as inv_router, init
        init(DB_CONFIG, __import__("police_auth") if _police_auth else None)
        app.include_router(inv_router)
        print("✅ Investigation workbench routes loaded")
    except Exception as e:
        print(f"Warning: investigation routes not loaded: {e}")
    print("    Enhanced dashboard routes loaded: wallets, evidence, operators, outreach, unified alerts")
    print("    Laundering detection routes loaded: detect, report, operations, alerts")
    # Telegram Intelligence v2 routes
    from telegram_intel_v2_routes import router as tg_v2_router
    app.include_router(tg_v2_router)
    print("✅ Telegram Intelligence v2 routes loaded")
    # Telegram Intelligence routes
    try:
        from telegram_intel_routes import register_telegram_intel_routes
        register_telegram_intel_routes(app, auth_police, auth_police_admin, rate_limiter)
    except Exception as e:
        print(f"Warning: telegram intel routes not loaded: {e}")
    print("✅ Batch 3 routes loaded: investigation_orchestrator, police_console, entity_resolution")
except Exception as e:
    print(f"Warning: batch 3 routes not loaded: {e}")


# ============================================================
# AUTONOMOUS HUNTER ENDPOINTS
# ============================================================

@app.get("/api/hunter/status")
async def hunter_status():
    """Get autonomous hunter status and statistics."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as total, "
            "COUNT(CASE WHEN created_date > NOW() - interval '1 hour' THEN 1 END) as last_hour, "
            "COUNT(CASE WHEN created_date > NOW() - interval '24 hours' THEN 1 END) as last_24h, "
            "AVG(confidence) as avg_confidence "
            "FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        countries = await conn.fetch(
            "SELECT DISTINCT unnest(affected_countries) as country FROM cases "
            "WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        patterns = await conn.fetch(
            "SELECT DISTINCT unnest(scam_patterns) as pattern FROM cases "
            "WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER'"
        )

        recent = await conn.fetch(
            "SELECT case_id, target, affected_countries, confidence, scam_patterns, created_date "
            "FROM cases WHERE created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' "
            "ORDER BY created_date DESC LIMIT 10"
        )

    import subprocess
    try:
        result = subprocess.run(["systemctl", "is-active", "gfin-hunter"], capture_output=True, text=True, timeout=5)
        hunter_active = result.stdout.strip() == "active"
    except:
        hunter_active = False

    return {
        "status": "ACTIVE" if hunter_active else "INACTIVE",
        "service_running": hunter_active,
        "total_cases": row["total"] if row else 0,
        "cases_last_hour": row["last_hour"] if row else 0,
        "cases_last_24h": row["last_24h"] if row else 0,
        "avg_confidence": round(float(row["avg_confidence"] or 0), 2),
        "countries_involved": [r["country"] for r in countries if r["country"]],
        "scam_patterns_detected": [r["pattern"] for r in patterns if r["pattern"]],
        "recent_cases": [
            {
                "case_id": r["case_id"],
                "target": r["target"],
                "countries": r["affected_countries"],
                "confidence": r["confidence"],
                "patterns": r["scam_patterns"],
                "created": r["created_date"].isoformat() if r["created_date"] else None,
            }
            for r in recent
        ],
    }


@app.get("/api/hunter/recent")
async def hunter_recent(limit: int = 20):
    """Get recent cases created by the autonomous hunter."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT c.case_id, c.target, c.status, c.confidence, c.affected_countries, "
            "c.routed_to_countries, c.scam_patterns, c.digital_identifiers, "
            "c.physical_locations, c.created_date, "
            "COUNT(e.id) as evidence_count "
            "FROM cases c LEFT JOIN evidence e ON e.case_id = c.case_id "
            "WHERE c.created_by_officer = 'GFIN_AUTONOMOUS_HUNTER' "
            "GROUP BY c.case_id ORDER BY c.created_date DESC LIMIT $1",
            limit
        )

    return [
        {
            "case_id": r["case_id"],
            "target": r["target"],
            "status": r["status"],
            "confidence": r["confidence"],
            "affected_countries": r["affected_countries"],
            "routed_to_countries": r["routed_to_countries"],
            "scam_patterns": r["scam_patterns"],
            "entity_count": len(r["digital_identifiers"]) if r["digital_identifiers"] else 0,
            "location_count": len(r["physical_locations"]) if r["physical_locations"] else 0,
            "evidence_count": r["evidence_count"],
            "created_date": r["created_date"].isoformat() if r["created_date"] else None,
        }
        for r in rows
    ]




# ============================================================
# ANOMALY DETECTION API (PyOD-powered)
# ============================================================

@app.get("/api/anomaly/cases")
async def detect_anomalous_cases(request: Request):
    """Detect anomalous cases using PyOD (Isolation Forest + KNN ensemble)"""
    payload = await auth_police(request)
    results = await anomaly_detector.detect_anomalous_cases(db_pool)
    return results

@app.get("/api/anomaly/wallets")
async def detect_anomalous_wallets(request: Request):
    """Detect anomalous wallet transaction patterns"""
    payload = await auth_police(request)
    results = await anomaly_detector.detect_wallet_anomalies(db_pool)
    return results

@app.get("/api/anomaly/status")
async def anomaly_status():
    """Get anomaly detection engine status"""
    return {
        "engine": "PyOD",
        "algorithms": ["Isolation Forest", "KNN"],
        "status": "operational"
    }

# ============================================================
# MISP THREAT INTELLIGENCE SHARING API
# ============================================================

@app.get("/api/misp/status")
async def misp_status():
    """Get MISP integration status"""
    return misp_integration.get_status()

@app.post("/api/misp/export-stix/{case_id}")
async def export_stix(case_id: str, request: Request):
    """Export a GFIN case as STIX 2.1 bundle for inter-agency sharing"""
    payload = await auth_police(request)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    
    case = dict(row)
    # Parse JSON fields
    import json as _json
    for field in ["scam_patterns", "scam_indicators", "affected_countries",
                  "financial_indicators", "digital_identifiers", "evidence_chain",
                  "attribution_data", "risk_assessment", "action_plan"]:
        if isinstance(case.get(field), str):
            try:
                case[field] = _json.loads(case[field])
            except:
                case[field] = []
    
    stix_bundle = misp_integration.export_stix(case)
    return stix_bundle

@app.post("/api/misp/share/{case_id}")
async def share_to_misp(case_id: str, request: Request):
    """Push a GFIN case to a configured MISP instance"""
    payload = await auth_police(request)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cases WHERE case_id=$1", case_id)
    if not row:
        raise HTTPException(404, "Case not found")
    
    case = dict(row)
    import json as _json
    for field in ["scam_patterns", "scam_indicators", "affected_countries",
                  "financial_indicators", "digital_identifiers", "evidence_chain"]:
        if isinstance(case.get(field), str):
            try:
                case[field] = _json.loads(case[field])
            except:
                case[field] = []
    
    result = await misp_integration.share_case_to_misp(case)
    return result

# ============================================================
# MIDAS REAL-TIME GRAPH ANOMALY DETECTION API
# ============================================================

@app.get("/api/midas/status")
async def midas_status():
    """Get MIDAS pipeline status"""
    return midas_pipeline.get_status()

@app.post("/api/midas/process/telegram")
async def midas_process_telegram(request: Request):
    """Process telegram intelligence through MIDAS for anomaly detection"""
    payload = await auth_police(request)
    results = await midas_pipeline.stream_telegram_intelligence(db_pool)
    return results

@app.post("/api/midas/process/evidence")
async def midas_process_evidence(request: Request):
    """Process case evidence chains through MIDAS"""
    payload = await auth_police(request)
    results = await midas_pipeline.stream_case_evidence(db_pool)
    return results

@app.post("/api/midas/internal/edge")
async def midas_add_edge_internal(request: Request):
    """Internal endpoint for spy/monitor to stream edges (localhost only, no auth)"""
    client_ip = request.client.host if request.client else ""
    if client_ip not in ("127.0.0.1", "::1", "localhost"):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"error": "Internal only"})
    body = await request.json()
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        return {"error": "src and dst required"}
    result = midas_pipeline.midas.add_edge(src, dst)
    # Convert numpy types to native Python for JSON serialization
    if isinstance(result, dict):
        result = {k: bool(v) if hasattr(v, 'item') else v for k, v in result.items()}
    return result

@app.post("/api/midas/edge")
async def midas_add_edge(request: Request):
    """Manually add an edge to MIDAS for real-time scoring"""
    payload = await auth_police(request)
    body = await request.json()
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        raise HTTPException(400, "src and dst required")
    result = midas_pipeline.midas.add_edge(src, dst)
    return result

@app.get("/api/midas/anomalies")
async def midas_anomalies(request: Request):
    """Get top anomalies detected by MIDAS"""
    payload = await auth_police(request)
    stats = midas_pipeline.midas.get_stats()
    return {"top_anomalies": stats["top_anomalies"], "stats": stats}



# ============================================================
# PROMETHEUS METRICS ENDPOINT
# ============================================================
REQUEST_COUNT = 0
SERVER_START_TIME = time.time()

@app.middleware("http")
async def count_requests(request: Request, call_next):
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    response = await call_next(request)
    return response

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    import time as _t
    lines = []
    lines.append("# TYPE gfin_server_up gauge")
    lines.append("gfin_server_up 1")
    lines.append("# TYPE gfin_server_uptime_seconds counter")
    lines.append(f"gfin_server_uptime_seconds {_t.time() - SERVER_START_TIME}")
    lines.append("# TYPE gfin_http_requests_total counter")
    lines.append(f"gfin_http_requests_total {REQUEST_COUNT}")
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        row = await conn.fetchrow("SELECT count(*) as c FROM cases WHERE status != 'CLOSED'")
        if row:
            lines.append("# TYPE gfin_active_cases gauge")
            lines.append(f"gfin_active_cases {row['c']}")
        row = await conn.fetchrow("SELECT count(*) as c FROM evidence")
        if row:
            lines.append("# TYPE gfin_evidence_items gauge")
            lines.append(f"gfin_evidence_items {row['c']}")
        row = await conn.fetchrow("SELECT count(*) as c FROM police_officers WHERE is_active = true")
        if row:
            lines.append("# TYPE gfin_active_officers gauge")
            lines.append(f"gfin_active_officers {row['c']}")
        row = await conn.fetchrow("SELECT count(*) as c FROM telegram_intelligence")
        if row:
            lines.append("# TYPE gfin_telegram_messages gauge")
            lines.append(f"gfin_telegram_messages {row['c']}")
        await conn.close()
    except Exception as e:
        lines.append(f"# DB error: {e}")
    return PlainTextResponse("\n".join(lines) + "\n")

# ============================================================
# TOKEN REFRESH & REVOCATION ENDPOINTS
# ============================================================
@app.post("/api/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """Exchange a refresh token for a new access token."""
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="JSON body required")
    refresh_tok = body.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(status_code=400, detail="Refresh token required")
    if _police_auth:
        officer_id = police_auth.validate_refresh_token(refresh_tok)
        if not officer_id:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        conn = await asyncpg.connect(**DB_CONFIG)
        officer = await conn.fetchrow("SELECT * FROM police_officers WHERE id = $1", officer_id)
        await conn.close()
        if not officer:
            raise HTTPException(status_code=401, detail="Officer not found")
        new_access = police_auth.generate_token(officer["id"], officer["role"], officer["agency"])
        new_refresh = police_auth.generate_refresh_token(
            officer["id"],
            request.client.host if request.client else "",
            request.headers.get("user-agent", "")
        )
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": 86400 * 7
        }
    raise HTTPException(status_code=501, detail="Auth not configured")

@app.post("/api/auth/revoke")
async def revoke_token_endpoint(request: Request):
    """Revoke current access token (logout)."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    if _police_auth and token:
        payload = police_auth.verify_token(token)
        if payload:
            police_auth.revoke_token(token, payload.get("oid", 0))
    return {"status": "revoked"}

@app.post("/api/auth/logout-all")
async def logout_all_endpoint(request: Request):
    """Revoke all tokens for current user."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "")
    if _police_auth and token:
        payload = police_auth.verify_token(token)
        if payload:
            police_auth.revoke_all_tokens(payload.get("oid", 0))
    return {"status": "all_tokens_revoked"}






@app.get("/api/intelligence/digest")
async def get_intelligence_digest(request: Request):
    """Get processed intelligence digest"""
    async with db_pool.acquire() as conn:
        # Stats
        total, actionable, noise = await conn.fetchrow("""
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE processed = false),
                   COUNT(*) FILTER (WHERE processed = true)
            FROM telegram_intelligence
        """)
        
        # Unique messages
        unique_msgs = await conn.fetchval("""
            SELECT COUNT(DISTINCT message_text || '|' || group_name)
            FROM telegram_intelligence WHERE message_text IS NOT NULL AND message_text != ''
        """)
        
        # Scam types
        scam_rows = await conn.fetch("""
            SELECT COALESCE(scam_type, 'UNCLASSIFIED') as scam_type, COUNT(*) as cnt
            FROM telegram_intelligence WHERE processed = false
            GROUP BY scam_type ORDER BY cnt DESC
        """)
        scam_types = [{"type": r["scam_type"], "count": r["cnt"]} for r in scam_rows]
        
        # Top domains
        domain_rows = await conn.fetch("""
            SELECT domains::text as d, COUNT(*) as mentions,
                   array_agg(DISTINCT group_name) as groups,
                   array_agg(DISTINCT scam_type) as scam_types,
                   bool_or(is_victim) as has_victim
            FROM telegram_intelligence 
            WHERE domains::text != '[]' AND processed = false
            GROUP BY domains::text ORDER BY mentions DESC LIMIT 20
        """)
        top_domains = []
        for r in domain_rows:
            try:
                domains = json.loads(r["d"]) if isinstance(r["d"], str) else (r["d"] or [])
            except:
                domains = []
            top_domains.append({
                "domains": domains, "mentions": r["mentions"],
                "groups": list(set(r["groups"])) if r["groups"] else [],
                "scam_types": [x for x in r["scam_types"] if x],
                "has_victim": r["has_victim"]
            })
        
        # Priority items
        priority_rows = await conn.fetch("""
            SELECT id, group_name, COALESCE(scam_type, 'UNCLASSIFIED') as scam_type,
                   risk_level, LEFT(message_text, 200) as preview,
                   domains::text, phones::text, is_victim, created_at
            FROM telegram_intelligence
            WHERE processed = false AND (is_victim = true OR risk_level = 'HIGH')
            ORDER BY is_victim DESC, created_at DESC LIMIT 30
        """)
        priority = []
        for r in priority_rows:
            try:
                domains = json.loads(r["domains"]) if isinstance(r["domains"], str) else (r["domains"] or [])
                phones = json.loads(r["phones"]) if isinstance(r["phones"], str) else (r["phones"] or [])
            except:
                domains, phones = [], []
            priority.append({
                "id": r["id"], "group": r["group_name"], "scam_type": r["scam_type"],
                "risk": r["risk_level"], "preview": r["preview"],
                "domains": domains, "phones": phones, "is_victim": r["is_victim"],
                "timestamp": r["created_at"].isoformat() if r["created_at"] else None
            })
        
        # Case cross-references
        case_rows = await conn.fetch("SELECT case_id, target FROM cases")
        existing_targets = {r["target"].lower() for r in case_rows if r["target"]}
        case_refs = []
        for cr in case_rows:
            target_lower = (cr["target"] or "").lower()
            for word in [w for w in target_lower.split() if len(w) > 4][:3]:
                cnt = await conn.fetchval(
                    "SELECT COUNT(*) FROM telegram_intelligence WHERE processed = false AND message_text ILIKE $1",
                    f"%{word}%"
                )
                if cnt > 0:
                    case_refs.append({"case_id": cr["case_id"], "target": cr["target"], "match": word, "msg_count": cnt})
        
        # New investigation targets
        new_targets = []
        for d in top_domains:
            for domain in d["domains"]:
                if domain not in existing_targets and domain not in ["wa.me"] and d["mentions"] >= 3:
                    new_targets.append({
                        "domain": domain, "mentions": d["mentions"],
                        "groups": d["groups"], "has_victim": d["has_victim"],
                        "priority": "HIGH" if d["mentions"] >= 5 or d["has_victim"] else "MEDIUM"
                    })
    
    return {
        "total_raw": total, "unique_messages": unique_msgs,
        "actionable": actionable, "noise_filtered": noise,
        "scam_types": scam_types, "top_domains": top_domains,
        "priority_items": priority, "case_cross_references": case_refs[:20],
        "new_investigation_targets": new_targets
    }


# ============================================================
# INTELLIGENCE INTEGRATION LAYER API
# ============================================================

@app.get("/api/intel/enriched-investigations")
async def api_enriched_investigations():
    """Run enriched investigations (Hunter v4 + Telegram context) for all telegram_intelligence cases."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from intel_integration_layer import run_enriched_investigations
        result = run_enriched_investigations()
        return {"status": "ok", "evidence_created": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/intel/correlations")
async def api_correlations():
    """Run cross-case correlation engine and return found correlations."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from cross_case_correlation import run_correlation_engine
        count = run_correlation_engine()
        return {"status": "ok", "correlations_found": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/intel/case/{case_id}/context")
async def api_case_context(case_id: str):
    """Get Telegram intelligence context for a specific case."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from intel_integration_layer import IntelContextBuilder
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT target FROM cases WHERE case_id = %s", (case_id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return {"status": "error", "message": "Case not found"}
        domain = row[0].strip()
        builder = IntelContextBuilder(db)
        ctx = builder.build_context(domain)
        db.close()
        return {"status": "ok", "case_id": case_id, "domain": domain, "context": ctx}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/intel/system-health")
async def api_intel_health():
    """Check intelligence pipeline health."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    health = {
        "intel_layer": "available",
        "correlation_engine": "available",
        "hunter_v4": "available",
        "telegram_spy": "unknown",
        "monitor": "fixed",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        from intel_integration_layer import IntelContextBuilder, EnrichedScorer
        health["intel_layer"] = "operational"
    except:
        health["intel_layer"] = "error"
    try:
        from cross_case_correlation import CrossCaseCorrelator
        health["correlation_engine"] = "operational"
    except:
        health["correlation_engine"] = "error"
    try:
        from scam_hunter_v4 import ProactiveScamHunterV4
        health["hunter_v4"] = "operational"
    except:
        health["hunter_v4"] = "error"
    return health



# ============================================================
# POLICE INVESTIGATION PIPELINE API
# ============================================================

@app.get("/api/police/run-investigations")
async def api_run_police_investigations():
    """Run full police investigation pipeline for all cases."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from police_pipeline import run_police_pipeline
        run_police_pipeline()
        return {"status": "ok", "message": "Police investigation pipeline complete"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/police/case/{case_id}/investigation")
async def api_police_case_investigation(case_id: str):
    """Run police investigation for a single case and return full results."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from police_pipeline import PoliceInvestigationPipeline, DB_CONFIG
        import psycopg2
        db = psycopg2.connect(**DB_CONFIG)
        pipeline = PoliceInvestigationPipeline(db)
        result = pipeline.investigate_case(case_id)
        db.close()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/police/case/{case_id}/people")
async def api_police_case_people(case_id: str):
    """Get all people identified in a case investigation."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("""SELECT role, name, entity_type, details, is_verified, source, confidence
            FROM people WHERE case_id = %s ORDER BY role, name""", (case_id,))
        people = []
        for row in cur.fetchall():
            people.append({"role": row[0], "name": row[1], "entity_type": row[2],
                          "details": row[3], "is_verified": row[4], "source": row[5], "confidence": row[6]})
        cur.close()
        db.close()
        return {"status": "ok", "case_id": case_id, "people": people}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/police/case/{case_id}/legal-pathway")
async def api_police_legal_pathway(case_id: str):
    """Get legal pathway assessment for a case."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from police_pipeline import PoliceInvestigationPipeline, DB_CONFIG
        import psycopg2
        db = psycopg2.connect(**DB_CONFIG)
        pipeline = PoliceInvestigationPipeline(db)
        
        cur = db.cursor()
        cur.execute("SELECT target FROM cases WHERE case_id = %s", (case_id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return {"status": "error", "message": "Case not found"}
        
        domain = row[0].strip()
        osint = pipeline._collect_osint(domain)
        telegram_intel = pipeline._analyze_telegram_intelligence(case_id, domain)
        legal = pipeline._determine_legal_pathway(domain, osint, telegram_intel, "telegram_intelligence")
        db.close()
        
        return {"status": "ok", "case_id": case_id, "domain": domain, "legal_pathway": legal}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ============================================================
# VICTIM DISCOVERY ENGINE API
# ============================================================

@app.get("/api/victim-discovery/run")
async def api_run_victim_discovery():
    """Run victim discovery and investigation engine."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from victim_discovery import run_victim_discovery
        run_victim_discovery()
        return {"status": "ok", "message": "Victim discovery engine complete"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/victim-discovery/classification-stats")
async def api_classification_stats():
    """Get message classification statistics."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT risk_level, COUNT(*) FROM telegram_intelligence GROUP BY risk_level ORDER BY count DESC")
        classifications = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM victims")
        victims = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM victim_complaints")
        complaints = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tracked_domains")
        tracked = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM cases")
        cases = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM people")
        people = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM scam_websites")
        websites = cur.fetchone()[0]
        cur.close()
        db.close()
        return {
            "status": "ok",
            "message_classifications": classifications,
            "victims": victims,
            "complaints": complaints,
            "tracked_domains": tracked,
            "cases": cases,
            "people": people,
            "scam_websites": websites
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ============================================================
# CORRELATION ENGINE API
# ============================================================

@app.get("/api/correlation/run")
async def api_run_correlation():
    """Run cross-case correlation engine."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from correlation_engine import run_correlation_engine
        total = run_correlation_engine()
        return {"status": "ok", "total_correlations": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/correlation/stats")
async def api_correlation_stats():
    """Get correlation statistics."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT correlation_type, COUNT(*) FROM correlation_graph GROUP BY correlation_type ORDER BY count DESC")
        by_type = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM correlation_graph")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM correlation_graph WHERE confidence >= 0.8")
        high = cur.fetchone()[0]
        
        # Most connected cases
        cur.execute("""SELECT case_id, COUNT(*) as links FROM (
            SELECT source_case as case_id FROM correlation_graph
            UNION ALL SELECT target_case as case_id FROM correlation_graph
        ) t GROUP BY case_id ORDER BY links DESC LIMIT 10""")
        top = [{"case_id": r[0], "links": r[1]} for r in cur.fetchall()]
        
        # High confidence links
        cur.execute("""SELECT source_case, target_case, correlation_type, entity_value, confidence
            FROM correlation_graph WHERE confidence >= 0.8 ORDER BY confidence DESC LIMIT 10""")
        high_links = [{"source": r[0], "target": r[1], "type": r[2], "entity": r[3], "confidence": r[4]} for r in cur.fetchall()]
        
        cur.close()
        db.close()
        return {"status": "ok", "total": total, "high_confidence": high, "by_type": by_type, "top_cases": top, "high_confidence_links": high_links}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/correlation/case/{case_id}")
async def api_case_correlations(case_id: str):
    """Get all correlations for a specific case."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("""SELECT target_case, correlation_type, entity_value, confidence, description
            FROM correlation_graph WHERE source_case = %s
            UNION ALL
            SELECT source_case, correlation_type, entity_value, confidence, description
            FROM correlation_graph WHERE target_case = %s
            ORDER BY confidence DESC""", (case_id, case_id))
        correlations = []
        for r in cur.fetchall():
            correlations.append({"linked_case": r[0], "type": r[1], "entity": r[2], "confidence": r[3], "description": r[4]})
        cur.close()
        db.close()
        return {"status": "ok", "case_id": case_id, "correlations": correlations, "count": len(correlations)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# VICTIM MONITOR API
# ============================================================

@app.get("/api/victim-monitor/run")
async def api_run_victim_monitor():
    """Run victim-focused monitor to search for real victims."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from victim_monitor import run_victim_monitor
        total = run_victim_monitor()
        return {"status": "ok", "found": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/scam-websites/external-scores")
async def api_external_scores():
    """Get external trust scores for scam websites."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("""SELECT domain, scam_type, risk_level, external_trust_score, external_trust_source
            FROM scam_websites ORDER BY external_trust_score ASC NULLS LAST""")
        sites = []
        for r in cur.fetchall():
            sites.append({"domain": r[0], "scam_type": r[1], "risk_level": r[2],
                         "trust_score": r[3], "trust_source": r[4]})
        cur.close()
        db.close()
        return {"status": "ok", "websites": sites}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ============================================================
# ENTITY RESOLUTION API
# ============================================================

@app.get("/api/entity-resolution/run")
async def api_run_entity_resolution():
    """Run entity resolution engine."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from entity_resolution import run_entity_resolution
        total = run_entity_resolution()
        return {"status": "ok", "total_entities": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/entity-resolution/entities")
async def api_resolved_entities():
    """Get all resolved entities."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("""SELECT canonical_id, entity_type, primary_name, confidence,
            telegram_usernames::text, social_media::text, linked_cases::text, description
            FROM resolved_entities ORDER BY confidence DESC""")
        entities = []
        for r in cur.fetchall():
            entities.append({"canonical_id": r[0], "entity_type": r[1], "primary_name": r[2],
                           "confidence": r[3], "telegram": r[4], "social_media": r[5],
                           "linked_cases": r[6], "description": r[7]})
        cur.close()
        db.close()
        return {"status": "ok", "entities": entities, "count": len(entities)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# WALLET INTELLIGENCE API
# ============================================================

@app.get("/api/wallet-intelligence/run")
async def api_run_wallet_intelligence():
    """Run wallet intelligence engine."""
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from wallet_intelligence import run_wallet_intelligence
        total = run_wallet_intelligence()
        return {"status": "ok", "total_wallets": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/wallet-intelligence/wallets")
async def api_wallets():
    """Get all tracked wallets."""
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("""SELECT wallet_type, address, source, source_case, blockchain_active,
            linked_cases::text, context FROM wallet_intelligence""")
        wallets = []
        for r in cur.fetchall():
            wallets.append({"type": r[0], "address": r[1], "source": r[2], "case": r[3],
                           "active": r[4], "linked_cases": r[5], "context": r[6]})
        cur.close()
        db.close()
        return {"status": "ok", "wallets": wallets, "count": len(wallets)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# TAXONOMY API
# ============================================================

@app.get("/api/taxonomy/run")
async def api_run_taxonomy():
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from taxonomy_alignment import run_taxonomy_alignment
        total = run_taxonomy_alignment()
        return {"status": "ok", "total_updates": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/taxonomy/types")
async def api_taxonomy_types():
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT canonical_type, description, severity, aliases::text, common_indicators::text FROM taxonomy_mapping ORDER BY severity DESC, canonical_type")
        types = []
        for r in cur.fetchall():
            types.append({"canonical_type": r[0], "description": r[1], "severity": r[2], "aliases": r[3], "indicators": r[4]})
        cur.close()
        db.close()
        return {"status": "ok", "types": types, "count": len(types)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# OSINT COLLECTOR API
# ============================================================

@app.get("/api/osint/run")
async def api_run_osint():
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from osint_collector import run_osint_collector
        total = run_osint_collector()
        return {"status": "ok", "total_signals": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# PROVENANCE API
# ============================================================

@app.get("/api/provenance/run")
async def api_run_provenance():
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from provenance_validator import run_provenance_validator
        total = run_provenance_validator()
        return {"status": "ok", "total_complete": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/provenance/stats")
async def api_provenance_stats():
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM evidence WHERE provenance_complete = true")
        complete = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM evidence")
        total = cur.fetchone()[0]
        cur.execute("SELECT AVG(legal_admissibility_score) FROM evidence")
        avg = cur.fetchone()[0]
        cur.execute("SELECT provenance_chain_strength, COUNT(*) FROM evidence GROUP BY provenance_chain_strength")
        strength = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        db.close()
        return {"status": "ok", "total": total, "complete": complete, "avg_score": round(avg or 0, 3), "strength": strength}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# DECISION SUPPORT API
# ============================================================

@app.get("/api/decision-support/run")
async def api_run_decision_support():
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from decision_support import run_decision_support
        total = run_decision_support()
        return {"status": "ok", "total_recommendations": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/decision-support/recommendations")
async def api_recommendations():
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT case_id, recommendation_type, priority, title, description, action_items::text, risk_score, confidence FROM analyst_recommendations ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, risk_score DESC")
        recs = []
        for r in cur.fetchall():
            recs.append({"case_id": r[0], "type": r[1], "priority": r[2], "title": r[3], "description": r[4], "action_items": r[5], "risk_score": r[6], "confidence": r[7]})
        cur.close()
        db.close()
        return {"status": "ok", "recommendations": recs, "count": len(recs)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# VICTIM SUPPORT API
# ============================================================

@app.get("/api/victim-support/run")
async def api_run_victim_support():
    import sys
    sys.path.insert(0, "/gfin/packages/services")
    try:
        from victim_support import run_victim_support
        total = run_victim_support()
        return {"status": "ok", "total_actions": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/victim-support/updates/{reference}")
async def api_victim_updates(reference: str):
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT stage, title, message, eta, created_date FROM victim_updates WHERE reference_number = %s ORDER BY created_date DESC", (reference,))
        updates = []
        for r in cur.fetchall():
            updates.append({"stage": r[0], "title": r[1], "message": r[2], "eta": r[3], "date": r[4].isoformat() if r[4] else None})
        cur.close()
        db.close()
        return {"status": "ok", "reference": reference, "updates": updates}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/victim-support/timeline/{reference}")
async def api_victim_timeline(reference: str):
    try:
        import psycopg2
        db = psycopg2.connect(host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!")
        cur = db.cursor()
        cur.execute("SELECT event_date, event_type, title, description FROM victim_timeline WHERE reference_number = %s ORDER BY event_date DESC", (reference,))
        timeline = []
        for r in cur.fetchall():
            timeline.append({"date": r[0].isoformat() if r[0] else None, "type": r[1], "title": r[2], "description": r[3]})
        cur.close()
        db.close()
        return {"status": "ok", "reference": reference, "timeline": timeline}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/intelligence/auto-investigate")
async def auto_investigate_targets(request: Request):
    """Auto-create cases for new high-priority targets from Telegram intel"""
    async with db_pool.acquire() as conn:
        case_rows = await conn.fetch("SELECT case_id, target FROM cases")
        existing = {r["target"].lower() for r in case_rows if r["target"]}
        case_count = len(case_rows)
        
        domain_rows = await conn.fetch("""
            SELECT domains::text, COUNT(*) as mentions,
                   array_agg(DISTINCT group_name) as groups,
                   bool_or(is_victim) as has_victim
            FROM telegram_intelligence 
            WHERE domains::text != '[]' AND processed = false
            GROUP BY domains::text HAVING COUNT(*) >= 3
        """)
        
        created = []
        for r in domain_rows:
            try:
                domains = json.loads(r["domains"]) if isinstance(r["domains"], str) else (r["domains"] or [])
            except:
                continue
            for domain in domains:
                if domain not in existing and domain not in ["wa.me"]:
                    case_id = f"GFIN-CASE-{case_count + len(created) + 1:03d}"
                    priority = "CRITICAL" if r["has_victim"] else ("HIGH" if r["mentions"] >= 5 else "MEDIUM")
                    
                    await conn.execute("""
                        INSERT INTO cases (case_id, status, target, target_type, trigger, summary,
                                          classification, confidence, victim_count, priority, created_date)
                        VALUES ($1, 'INVESTIGATING', $2, 'domain', 'telegram_intelligence',
                                $3, 'LAW ENFORCEMENT SENSITIVE', 0.6, 0, $4, NOW())
                        ON CONFLICT (case_id) DO NOTHING
                    """, case_id, domain,
                        f"Auto-detected from Telegram: {domain} mentioned {r['mentions']} times across {len(set(r['groups']))} groups",
                        priority)
                    
                    await conn.execute("""
                        INSERT INTO investigation_steps (case_id, phase, step_type, step_name, status, result, created_date)
                        VALUES ($1, 'INTEL', 'auto_investigation', 'Telegram Intel Analysis', 'COMPLETED', $2, NOW())
                    """, case_id, json.dumps({
                        "source": "telegram_intelligence",
                        "mentions": r["mentions"],
                        "groups": list(set(r["groups"])),
                        "has_victim": r["has_victim"],
                        "domain": domain
                    }))
                    
                    await conn.execute("""
                        UPDATE telegram_intelligence SET investigated = true
                        WHERE domains::text ILIKE $1 AND processed = false
                    """, f"%{domain}%")
                    
                    # Create evidence items from Telegram messages
                    import hashlib as _hl
                    _msgs = await conn.fetch(
                        "SELECT id, group_name, message_text, is_victim, risk_level, created_at FROM telegram_intelligence WHERE domains::text ILIKE $1 AND processed = false ORDER BY is_victim DESC, created_at DESC LIMIT 20",
                        f"%{domain}%"
                    )
                    _evc = 0
                    for _m in _msgs:
                        _txt = (_m["message_text"] or "")[:2000]
                        _ch = _hl.sha256(_txt.encode()).hexdigest()
                        _conf = 0.85 if _m["is_victim"] else (0.75 if _m["risk_level"] == "HIGH" else 0.6)
                        _grp = _m["group_name"] or "unknown"
                        _find = f"[VICTIM REPORT] {domain} in {_grp}" if _m["is_victim"] else f"[Telegram Intel] {domain} in {_grp}"
                        _eid = f"EVD-{case_id}-{_evc+1:04d}"
                        await conn.execute(
                            "INSERT INTO evidence (evidence_id, case_id, phase, finding, source_provider, source_type, confidence, content_hash, timestamp, created_date, added_date, lifecycle_status, found_at, provenance_source, provenance_provider, provenance_endpoint, provenance_query, provenance_original_ref, provenance_content_hash, provenance_processing_history, provenance_collector, provenance_complete) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$9,$9,$10,$9,$11,$12,$13,$14,$15,$8,$16,$17,true) ON CONFLICT DO NOTHING",
                            _eid, case_id, _find, "telegram_intelligence", "telegram", _conf, _ch, _m["created_at"], "FOUND",
                            "telegram", "telegram_intelligence", f"telegram_group:{_grp}", f"domain:{domain}", f"msg_id:{_m['id']}",
                            json.dumps(["collected","deduplicated","filtered","cross_referenced","evidence_created"]), "GFIN-AUTO-PIPELINE"
                        )
                        _evc += 1
                    created.append({"case_id": case_id, "domain": domain, "mentions": r["mentions"], "priority": priority, "evidence_created": _evc})
                    existing.add(domain)
    
    return {"created_cases": created, "total": len(created)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


# ============================================================
# ADVANCED INTELLIGENCE API ENDPOINTS (Hunter v3.0)
# ============================================================

@app.get("/api/graph/related/{domain}")
async def get_related_domains(domain: str):
    """Get all domains related to this domain through shared infrastructure (Neo4j graph)."""
    try:
        from hunter_v3_advanced import query_related_domains
        result = query_related_domains(domain)
        return {"status": "ok", "domain": domain, **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/wallet/intelligence/{address}")
async def get_wallet_intelligence(address: str, wallet_type: str = "BTC"):
    """Check a crypto wallet against blockchain APIs."""
    try:
        from hunter_v3_advanced import check_wallet_intelligence
        result = check_wallet_intelligence(address, wallet_type)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/subdomains/{domain}")
async def get_subdomains(domain: str):
    """Enumerate subdomains for a domain via Certificate Transparency logs."""
    try:
        from hunter_v3_advanced import enumerate_subdomains
        result = enumerate_subdomains(domain)
        return {"status": "ok", "domain": domain, **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/takedown/{case_id}")
async def get_takedown_report(case_id: str):
    """Generate or retrieve a takedown report for a case."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT target, digital_identifiers, physical_locations, financial_indicators, scam_indicators, scam_patterns, affected_countries, confidence, summary FROM cases WHERE case_id = %s", (case_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"status": "error", "message": "Case not found"}
        
        # Build investigation dict for takedown report
        import json
        inv = {
            "domain": row[0],
            "digital_identifiers": json.loads(row[1]) if row[1] else [],
            "physical_locations": json.loads(row[2]) if row[2] else [],
            "financial_indicators": json.loads(row[3]) if row[3] else [],
            "scam_indicators": json.loads(row[4]) if row[4] else [],
            "scam_patterns": json.loads(row[5]) if row[5] else [],
            "affected_countries": json.loads(row[6]) if row[6] else [],
            "confidence": row[7] or 0,
            "evidence_chain": [],
        }
        
        from hunter_v3_advanced import generate_takedown_report
        report = generate_takedown_report(inv)
        return {"status": "ok", **report}
    except Exception as e:
        return {"status": "error", "message": str(e)}




@app.get("/api/graph/stats")
async def get_graph_stats():
    """Get Neo4j graph database statistics."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "gfin_temp_password"))
        with driver.session() as session:
            # Count nodes by type
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            node_stats = {r["type"]: r["count"] for r in result}
            
            # Count relationships
            result2 = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            rel_stats = {r["type"]: r["count"] for r in result2}
            
            # Total
            total_nodes = sum(node_stats.values())
            total_rels = sum(rel_stats.values())
        
        driver.close()
        return {
            "status": "ok",
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "nodes_by_type": node_stats,
            "relationships_by_type": rel_stats,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/hunter/v3/status")
async def get_hunter_v3_status():
    """Get Hunter v3.0 advanced intelligence status."""
    try:
        from neo4j import GraphDatabase
        neo4j_connected = False
        try:
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "gfin_temp_password"))
            with driver.session() as s:
                s.run("RETURN 1")
            neo4j_connected = True
            driver.close()
        except:
            pass
        
        return {
            "status": "ok",
            "version": "3.0",
            "features": {
                "favicon_hashing": True,
                "analytics_id_extraction": True,
                "redirect_chain_analysis": True,
                "tech_stack_fingerprinting": True,
                "form_detection": True,
                "typo_squatting_detection": True,
                "domain_age_analysis": True,
                "page_metadata_extraction": True,
                "neo4j_graph_storage": neo4j_connected,
                "whois_privacy_guard": True,
                "subdomain_enumeration": True,
                "wallet_intelligence": True,
                "takedown_report_generation": True,
            },
            "feeds": [
                "CT Logs (crt.sh)",
                "URLScan.io",
                "Phishing.Database (GitHub)",
                "OpenPhish",
                "URLHaus (abuse.ch)",
                "ThreatFox (abuse.ch)",
            ],
            "investigation_phases": 17,
            "evidence_gate_conditions": 10,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


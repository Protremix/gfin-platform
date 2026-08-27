#!/usr/bin/env python3
"""
GFIN Scam Website Database
- Auto-adds scam websites from complaints and monitor detections
- Telegram bot can check: /check example.com
- Website API: GET /api/scam-sites/check/{domain}, GET /api/scam-sites/list
- Maintains evidence count and last reported date per domain
"""
import json, time, re, hashlib, os
from datetime import datetime, timezone
from typing import List, Dict, Optional


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "gfin",
    "password": "",
    "dbname": "gfin",
}

SCAM_SITES_TABLE = "scam_websites"


def _get_db():
    """Get database connection."""
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"DB connection error: {e}")
        return None


def init_scam_sites_table():
    """Create the scam_websites table if it doesn't exist."""
    conn = _get_db()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCAM_SITES_TABLE} (
                id SERIAL PRIMARY KEY,
                domain VARCHAR(255) UNIQUE NOT NULL,
                scam_type VARCHAR(100),
                risk_level VARCHAR(50),
                report_count INTEGER DEFAULT 1,
                first_reported TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_reported TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                sources TEXT[],
                evidence_hashes TEXT[],
                description TEXT,
                status VARCHAR(50) DEFAULT 'ACTIVE',
                target_type VARCHAR(50) DEFAULT 'domain',
                related_domains TEXT[],
                wallet_addresses TEXT[],
                phone_numbers TEXT[],
                countries_affected TEXT[],
                total_loss_reported DECIMAL(15,2) DEFAULT 0,
                is_verified BOOLEAN DEFAULT FALSE,
                verified_by VARCHAR(255),
                verified_at TIMESTAMP WITH TIME ZONE,
                created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create indexes for fast lookup
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_scam_sites_domain ON {SCAM_SITES_TABLE}(domain);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_scam_sites_status ON {SCAM_SITES_TABLE}(status);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_scam_sites_scam_type ON {SCAM_SITES_TABLE}(scam_type);")
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating scam_sites table: {e}")
        if conn:
            conn.close()
        return False


def add_scam_website(domain: str, scam_type: str = "UNKNOWN", 
                      risk_level: str = "MEDIUM", source: str = "complaint",
                      description: str = "", wallet_addresses: List[str] = None,
                      phone_numbers: List[str] = None, countries: List[str] = None,
                      loss_amount: float = 0, evidence_hash: str = "") -> Dict:
    """
    Add or update a scam website in the database.
    If domain already exists, increments report_count and updates info.
    
    Returns dict with operation result.
    """
    # Normalize domain
    domain = domain.lower().strip().rstrip("/")
    if domain.startswith("http://"):
        domain = domain[7:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.startswith("www."):
        domain = domain[4:]
    # Take only the domain part (no path)
    domain = domain.split("/")[0]
    
    if not domain or "." not in domain:
        return {"success": False, "error": "Invalid domain"}
    
    conn = _get_db()
    if not conn:
        return {"success": False, "error": "Database connection failed"}
    
    try:
        cur = conn.cursor()
        
        # Check if domain already exists
        cur.execute(f"SELECT id, report_count, sources, evidence_hashes FROM {SCAM_SITES_TABLE} WHERE domain = %s", (domain,))
        existing = cur.fetchone()
        
        if existing:
            # Update existing record
            site_id, report_count, sources, evidence_hashes = existing
            sources = sources or []
            evidence_hashes = evidence_hashes or []
            
            if source not in sources:
                sources.append(source)
            if evidence_hash and evidence_hash not in evidence_hashes:
                evidence_hashes.append(evidence_hash)
            
            # Update related data if provided
            if wallet_addresses:
                cur.execute(f"SELECT wallet_addresses FROM {SCAM_SITES_TABLE} WHERE id = %s", (site_id,))
                existing_wallets = cur.fetchone()[0] or []
                new_wallets = list(set((existing_wallets or []) + wallet_addresses))
                cur.execute(f"UPDATE {SCAM_SITES_TABLE} SET wallet_addresses = %s WHERE id = %s", (new_wallets, site_id))
            
            if phone_numbers:
                cur.execute(f"SELECT phone_numbers FROM {SCAM_SITES_TABLE} WHERE id = %s", (site_id,))
                existing_phones = cur.fetchone()[0] or []
                new_phones = list(set((existing_phones or []) + phone_numbers))
                cur.execute(f"UPDATE {SCAM_SITES_TABLE} SET phone_numbers = %s WHERE id = %s", (new_phones, site_id))
            
            if countries:
                cur.execute(f"SELECT countries_affected FROM {SCAM_SITES_TABLE} WHERE id = %s", (site_id,))
                existing_countries = cur.fetchone()[0] or []
                new_countries = list(set((existing_countries or []) + countries))
                cur.execute(f"UPDATE {SCAM_SITES_TABLE} SET countries_affected = %s WHERE id = %s", (new_countries, site_id))
            
            cur.execute(f"""
                UPDATE {SCAM_SITES_TABLE} SET 
                    report_count = %s,
                    last_reported = NOW(),
                    sources = %s,
                    evidence_hashes = %s,
                    total_loss_reported = total_loss_reported + %s,
                    risk_level = CASE WHEN %s = 'CRITICAL' THEN 'CRITICAL'
                               WHEN %s = 'HIGH' AND risk_level != 'CRITICAL' THEN 'HIGH'
                               WHEN %s = 'MEDIUM' AND risk_level NOT IN ('CRITICAL', 'HIGH') THEN 'MEDIUM'
                               ELSE risk_level END,
                    updated_date = NOW()
                WHERE id = %s
            """, (report_count + 1, sources, evidence_hashes, loss_amount,
                  risk_level, risk_level, risk_level, site_id))
            
            conn.commit()
            cur.close()
            conn.close()
            return {"success": True, "action": "updated", "domain": domain, "report_count": report_count + 1}
        else:
            # Insert new record
            cur.execute(f"""
                INSERT INTO {SCAM_SITES_TABLE} 
                    (domain, scam_type, risk_level, report_count, sources, evidence_hashes,
                     description, wallet_addresses, phone_numbers, countries_affected,
                     total_loss_reported)
                VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s)
            """, (
                domain, scam_type, risk_level,
                [source] if source else ["complaint"],
                [evidence_hash] if evidence_hash else [],
                description,
                wallet_addresses or [],
                phone_numbers or [],
                countries or [],
                loss_amount
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            return {"success": True, "action": "added", "domain": domain, "report_count": 1}
    
    except Exception as e:
        print(f"Error adding scam website: {e}")
        if conn:
            conn.close()
        return {"success": False, "error": str(e)}


def check_domain(domain: str) -> Dict:
    """
    Check if a domain is in the scam database.
    Returns domain status and details if found.
    """
    domain = domain.lower().strip().rstrip("/")
    if domain.startswith("http://"):
        domain = domain[7:]
    if domain.startswith("https://"):
        domain = domain[8:]
    if domain.startswith("www."):
        domain = domain[4:]
    domain = domain.split("/")[0]
    
    if not domain or "." not in domain:
        return {"found": False, "error": "Invalid domain", "domain": domain}
    
    conn = _get_db()
    if not conn:
        return {"found": False, "error": "Database connection failed", "domain": domain}
    
    try:
        cur = conn.cursor()
        
        # Exact match
        cur.execute(f"""
            SELECT domain, scam_type, risk_level, report_count, 
                   first_reported, last_reported, status, description,
                   wallet_addresses, phone_numbers, countries_affected,
                   total_loss_reported, is_verified
            FROM {SCAM_SITES_TABLE} WHERE domain = %s
        """, (domain,))
        result = cur.fetchone()
        
        if not result:
            # Check if it's a subdomain of a known scam domain
            parts = domain.split(".")
            for i in range(len(parts) - 1):
                parent = ".".join(parts[i:])
                cur.execute(f"SELECT domain, scam_type, risk_level, report_count, status FROM {SCAM_SITES_TABLE} WHERE domain = %s", (parent,))
                result = cur.fetchone()
                if result:
                    cur.close()
                    conn.close()
                    return {
                        "found": True,
                        "domain": domain,
                        "parent_domain": result[0],
                        "scam_type": result[1],
                        "risk_level": result[2],
                        "report_count": result[3],
                        "status": result[4],
                        "match_type": "subdomain",
                        "warning": f"This domain is a subdomain of known scam site {result[0]}"
                    }
            
            cur.close()
            conn.close()
            return {"found": False, "domain": domain, "message": "Domain not found in scam database"}
        
        cur.close()
        conn.close()
        
        return {
            "found": True,
            "domain": result[0],
            "scam_type": result[1],
            "risk_level": result[2],
            "report_count": result[3],
            "first_reported": result[4].isoformat() if result[4] else None,
            "last_reported": result[5].isoformat() if result[5] else None,
            "status": result[6],
            "description": result[7] or "",
            "wallet_addresses": result[8] or [],
            "phone_numbers": result[9] or [],
            "countries_affected": result[10] or [],
            "total_loss_reported": float(result[11]) if result[11] else 0,
            "is_verified": result[12] or False,
            "match_type": "exact"
        }
    
    except Exception as e:
        if conn:
            conn.close()
        return {"found": False, "error": str(e), "domain": domain}


def list_scam_sites(limit: int = 50, offset: int = 0, 
                    scam_type: str = None, risk_level: str = None,
                    status: str = "ACTIVE", sort: str = "report_count") -> Dict:
    """
    List scam websites from the database.
    Returns list and total count.
    """
    conn = _get_db()
    if not conn:
        return {"sites": [], "total": 0, "error": "Database connection failed"}
    
    try:
        cur = conn.cursor()
        
        # Build query
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        if scam_type:
            where_clauses.append("scam_type = %s")
            params.append(scam_type)
        if risk_level:
            where_clauses.append("risk_level = %s")
            params.append(risk_level)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Sort
        sort_map = {
            "report_count": "report_count DESC",
            "recent": "last_reported DESC",
            "loss": "total_loss_reported DESC",
            "domain": "domain ASC",
        }
        sort_sql = sort_map.get(sort, "report_count DESC")
        
        # Get total count
        cur.execute(f"SELECT COUNT(*) FROM {SCAM_SITES_TABLE} WHERE {where_sql}", params)
        total = cur.fetchone()[0]
        
        # Get sites
        cur.execute(f"""
            SELECT domain, scam_type, risk_level, report_count,
                   first_reported, last_reported, status, is_verified,
                   countries_affected, total_loss_reported
            FROM {SCAM_SITES_TABLE} WHERE {where_sql}
            ORDER BY {sort_sql}
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        
        sites = []
        for row in cur.fetchall():
            sites.append({
                "domain": row[0],
                "scam_type": row[1],
                "risk_level": row[2],
                "report_count": row[3],
                "first_reported": row[4].isoformat() if row[4] else None,
                "last_reported": row[5].isoformat() if row[5] else None,
                "status": row[6],
                "is_verified": row[7] or False,
                "countries": row[8] or [],
                "total_loss": float(row[9]) if row[9] else 0,
            })
        
        cur.close()
        conn.close()
        
        return {"sites": sites, "total": total, "limit": limit, "offset": offset}
    
    except Exception as e:
        if conn:
            conn.close()
        return {"sites": [], "total": 0, "error": str(e)}


def search_scam_sites(query: str, limit: int = 20) -> Dict:
    """Search scam sites by domain name (partial match)."""
    conn = _get_db()
    if not conn:
        return {"sites": [], "error": "Database connection failed"}
    
    try:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT domain, scam_type, risk_level, report_count, status
            FROM {SCAM_SITES_TABLE} 
            WHERE domain LIKE %s AND status = 'ACTIVE'
            ORDER BY report_count DESC
            LIMIT %s
        """, (f"%{query}%", limit))
        
        sites = []
        for row in cur.fetchall():
            sites.append({
                "domain": row[0],
                "scam_type": row[1],
                "risk_level": row[2],
                "report_count": row[3],
                "status": row[4],
            })
        
        cur.close()
        conn.close()
        return {"sites": sites, "query": query, "total": len(sites)}
    
    except Exception as e:
        if conn:
            conn.close()
        return {"sites": [], "error": str(e)}


def get_scam_sites_stats() -> Dict:
    """Get statistics about scam websites database."""
    conn = _get_db()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cur = conn.cursor()
        
        # Total sites
        cur.execute(f"SELECT COUNT(*) FROM {SCAM_SITES_TABLE} WHERE status = 'ACTIVE'")
        total = cur.fetchone()[0]
        
        # By risk level
        cur.execute(f"""
            SELECT risk_level, COUNT(*) FROM {SCAM_SITES_TABLE} WHERE status = 'ACTIVE'
            GROUP BY risk_level ORDER BY COUNT(*) DESC
        """)
        by_risk = {row[0]: row[1] for row in cur.fetchall()}
        
        # By scam type
        cur.execute(f"""
            SELECT scam_type, COUNT(*) FROM {SCAM_SITES_TABLE} WHERE status = 'ACTIVE'
            GROUP BY scam_type ORDER BY COUNT(*) DESC
        """)
        by_type = {row[0]: row[1] for row in cur.fetchall()}
        
        # Most reported
        cur.execute(f"""
            SELECT domain, scam_type, report_count, risk_level FROM {SCAM_SITES_TABLE}
            WHERE status = 'ACTIVE' ORDER BY report_count DESC LIMIT 5
        """)
        top_reported = [
            {"domain": row[0], "scam_type": row[1], "reports": row[2], "risk_level": row[3]}
            for row in cur.fetchall()
        ]
        
        # Total loss reported
        cur.execute(f"SELECT COALESCE(SUM(total_loss_reported), 0) FROM {SCAM_SITES_TABLE}")
        total_loss = float(cur.fetchone()[0])
        
        cur.close()
        conn.close()
        
        return {
            "total_sites": total,
            "by_risk_level": by_risk,
            "by_scam_type": by_type,
            "top_reported": top_reported,
            "total_loss_reported": total_loss,
        }
    
    except Exception as e:
        if conn:
            conn.close()
        return {"error": str(e)}


def format_check_result_telegram(check_result: Dict) -> str:
    """Format check result as a Telegram message."""
    if not check_result.get("found"):
        return f"""✅ <b>Domain Check Result</b>

🌐 <b>Domain:</b> <code>{check_result.get('domain', 'N/A')}</code>
📊 <b>Status:</b> NOT FOUND in scam database

ℹ️ This domain has not been reported as a scam. However, this does NOT guarantee it's safe — new scams appear daily.

<b>Stay vigilant and report suspicious sites at:</b>
🔗 gfin-system.com/victim

<i>— GFIN Global Fraud Intelligence Network</i>"""
    
    risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
        check_result.get("risk_level", "MEDIUM"), "🟡")
    
    verified_badge = " ✅ <i>Verified</i>" if check_result.get("is_verified") else ""
    parent_info = ""
    if check_result.get("parent_domain"):
        parent_info = f"\n⚠️ <b>Parent domain:</b> <code>{check_result['parent_domain']}</code>"
    
    wallets = check_result.get("wallet_addresses", [])
    wallets_text = ""
    if wallets:
        wallets_text = f"\n₿ <b>Linked wallets:</b> {len(wallets)}"
    
    countries = check_result.get("countries_affected", [])
    countries_text = ""
    if countries:
        countries_text = f"\n🌍 <b>Countries affected:</b> {', '.join(countries[:5])}"
    
    loss = check_result.get("total_loss_reported", 0)
    loss_text = f"\n💰 <b>Total loss reported:</b> ${loss:,.2f}" if loss > 0 else ""
    
    return f"""{risk_emoji} <b>SCAM WEBSITE DETECTED</b>{verified_badge}

🌐 <b>Domain:</b> <code>{check_result['domain']}</code>
🏷️ <b>Scam Type:</b> {check_result.get('scam_type', 'Unknown').replace('_', ' ').title()}
{risk_emoji} <b>Risk Level:</b> {check_result.get('risk_level', 'Unknown')}
📊 <b>Reports:</b> {check_result.get('report_count', 1)}
📅 <b>First reported:</b> {check_result.get('first_reported', 'N/A')[:10] if check_result.get('first_reported') else 'N/A'}
📅 <b>Last reported:</b> {check_result.get('last_reported', 'N/A')[:10] if check_result.get('last_reported') else 'N/A'}{parent_info}{wallets_text}{countries_text}{loss_text}

⚠️ <b>WARNING: This website has been reported as a scam.</b>
Do NOT send money, personal information, or cryptocurrency to this site.

🔗 <b>Report a scam:</b> gfin-system.com/victim
🔗 <b>Full list:</b> gfin-system.com/scam-sites

<i>— GFIN Global Fraud Intelligence Network</i>"""


if __name__ == "__main__":
    # Initialize the table
    init_scam_sites_table()
    print("Scam sites table initialized")
    
    # Test
    result = add_scam_website("test-scam.example.com", "RECOVERY_SCAM", "CRITICAL", "test")
    print(f"Add result: {result}")
    
    check = check_domain("test-scam.example.com")
    print(f"Check result: {check}")
    
    stats = get_scam_sites_stats()
    print(f"Stats: {stats}")

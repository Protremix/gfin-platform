"""Telegram Intelligence API endpoints for GFIN server."""
from fastapi import APIRouter, Query
from typing import Optional
import json, psycopg2
from datetime import datetime, timezone

router = APIRouter(prefix="/api/telegram-intel", tags=["telegram-intelligence"])

def get_db():
    return psycopg2.connect(
        host="127.0.0.1", database="gfin", user="gfin", password="GfinSecure2026!", port=5432
    )

@router.get("/overview")
async def intel_overview():
    """Overview of all Telegram intelligence."""
    conn = get_db()
    cur = conn.cursor()
    
    # Counts
    cur.execute("SELECT COUNT(*) FROM telegram_intelligence")
    total_messages = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM telegram_intelligence WHERE is_victim = TRUE")
    victim_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM telegram_wallets")
    wallet_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM telegram_domains")
    domain_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM telegram_groups")
    group_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM telegram_intelligence WHERE risk_level IN ('CRITICAL', 'HIGH')")
    high_risk = cur.fetchone()[0]
    
    # Scam types
    cur.execute("SELECT scam_type, COUNT(*) FROM telegram_intelligence WHERE scam_type IS NOT NULL GROUP BY scam_type ORDER BY count DESC LIMIT 10")
    scam_types = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
    
    # Top domains
    cur.execute("SELECT domain, mention_count, risk_level FROM telegram_domains ORDER BY mention_count DESC LIMIT 20")
    top_domains = [{"domain": r[0], "mentions": r[1], "risk": r[2]} for r in cur.fetchall()]
    
    # Top wallets
    cur.execute("SELECT wallet_address, wallet_type, mention_count FROM telegram_wallets ORDER BY mention_count DESC LIMIT 20")
    top_wallets = [{"address": r[0], "type": r[1], "mentions": r[2]} for r in cur.fetchall()]
    
    # Monitored groups
    cur.execute("SELECT group_name, group_username, member_count, last_activity FROM telegram_groups ORDER BY last_activity DESC")
    groups = [{"name": r[0], "username": r[1], "members": r[2], "last_activity": r[3].isoformat() if r[3] else None} for r in cur.fetchall()]
    
    # Recent intelligence
    cur.execute("""
        SELECT id, group_name, sender_name, risk_level, scam_type, is_victim,
               wallets, domains, phones, created_at
        FROM telegram_intelligence
        ORDER BY created_at DESC LIMIT 50
    """)
    recent = [{
        "id": r[0], "group": r[1], "sender": r[2], "risk": r[3],
        "scam_type": r[4], "is_victim": r[5],
        "wallets": r[6] if isinstance(r[6], list) else json.loads(r[6] or "[]"),
        "domains": r[7] if isinstance(r[7], list) else json.loads(r[7] or "[]"),
        "phones": r[8] if isinstance(r[8], list) else json.loads(r[8] or "[]"),
        "timestamp": r[9].isoformat() if r[9] else None,
    } for r in cur.fetchall()]
    
    conn.close()
    return {
        "stats": {
            "total_messages": total_messages,
            "victims_detected": victim_count,
            "wallets_tracked": wallet_count,
            "domains_tracked": domain_count,
            "groups_monitored": group_count,
            "high_risk_messages": high_risk,
        },
        "scam_types": scam_types,
        "top_domains": top_domains,
        "top_wallets": top_wallets,
        "groups": groups,
        "recent_intelligence": recent,
    }

@router.get("/wallets")
async def list_wallets(limit: int = Query(50, le=500)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT wallet_address, wallet_type, first_seen_group, first_seen_sender,
               mention_count, last_seen, investigated, created_at
        FROM telegram_wallets ORDER BY mention_count DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return {"wallets": [{"address": r[0], "type": r[1], "group": r[2], "sender": r[3],
                        "mentions": r[4], "last_seen": r[5].isoformat() if r[5] else None,
                        "investigated": r[6], "first_seen": r[7].isoformat() if r[7] else None}
                       for r in rows]}

@router.get("/domains")
async def list_domains(limit: int = Query(50, le=500)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT domain, first_seen_group, first_seen_sender, mention_count,
               investigated, scam_detected, risk_level, last_seen, created_at
        FROM telegram_domains ORDER BY mention_count DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return {"domains": [{"domain": r[0], "group": r[1], "sender": r[2], "mentions": r[3],
                        "investigated": r[4], "scam_detected": r[5], "risk": r[6],
                        "last_seen": r[7].isoformat() if r[7] else None,
                        "first_seen": r[8].isoformat() if r[8] else None}
                       for r in rows]}

@router.get("/victims")
async def list_victims(limit: int = Query(50, le=500)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, group_name, sender_name, sender_username, message_text,
               scam_type, risk_level, wallets, domains, phones, created_at
        FROM telegram_intelligence WHERE is_victim = TRUE
        ORDER BY created_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return {"victims": [{"id": r[0], "group": r[1], "name": r[2], "username": r[3],
                        "text": r[4][:200] if r[4] else "", "scam_type": r[5],
                        "risk": r[6],
                        "wallets": r[7] if isinstance(r[7], list) else json.loads(r[7] or "[]"),
                        "domains": r[8] if isinstance(r[8], list) else json.loads(r[8] or "[]"),
                        "phones": r[9] if isinstance(r[9], list) else json.loads(r[9] or "[]"),
                        "timestamp": r[10].isoformat() if r[10] else None}
                       for r in rows]}

@router.get("/groups")
async def list_groups():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT group_name, group_username, member_count, is_monitored, last_activity, first_seen
        FROM telegram_groups ORDER BY last_activity DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return {"groups": [{"name": r[0], "username": r[1], "members": r[2],
                       "monitored": r[3], "last_activity": r[4].isoformat() if r[4] else None,
                       "first_seen": r[5].isoformat() if r[5] else None}
                      for r in rows]}

@router.get("/search")
async def search_intel(q: str = Query(..., min_length=2), limit: int = Query(50, le=200)):
    """Search intelligence by wallet, domain, phone, name, or keyword."""
    conn = get_db()
    cur = conn.cursor()
    pattern = f"%{q}%"
    cur.execute("""
        SELECT id, group_name, sender_name, risk_level, scam_type, is_victim,
               wallets, domains, phones, ips, message_text, created_at
        FROM telegram_intelligence
        WHERE message_text ILIKE %s OR sender_name ILIKE %s
        ORDER BY created_at DESC LIMIT %s
    """, (pattern, pattern, limit))
    rows = cur.fetchall()
    conn.close()
    return {"results": [{"id": r[0], "group": r[1], "sender": r[2], "risk": r[3],
                         "scam_type": r[4], "is_victim": r[5],
                         "wallets": r[6] if isinstance(r[6], list) else json.loads(r[6] or "[]"),
                         "domains": r[7] if isinstance(r[7], list) else json.loads(r[7] or "[]"),
                         "phones": r[8] if isinstance(r[8], list) else json.loads(r[8] or "[]"),
                         "ips": r[9] if isinstance(r[9], list) else json.loads(r[9] or "[]"),
                         "text": r[10][:300] if r[10] else "",
                         "timestamp": r[11].isoformat() if r[11] else None}
                        for r in rows]}

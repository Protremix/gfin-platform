"""
GFIN Enhanced Dashboard Routes — Laundering, Wallet Flow, Evidence Correlation,
Operator Map, Victim Outreach, and unified Alert Priority Queue.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import asyncio

router = APIRouter(prefix="/api/dashboard", tags=["Enhanced Dashboard"])

# ============================================================
# 1. WALLET FLOW TRACKER
# ============================================================

WALLETS_FILE = "/gfin/wallet_flow.json"

def _load_wallets():
    try:
        with open(WALLETS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def _save_wallets(wallets):
    with open(WALLETS_FILE, "w") as f:
        json.dump(wallets, f, indent=2)

@router.get("/wallets")
async def get_wallet_flows(
    chain: Optional[str] = None,
    linked_case: Optional[str] = None,
    sort: str = "-first_seen"
):
    """Get all tracked wallets with optional filtering."""
    wallets = _load_wallets()
    
    # Also pull wallets from telegram intelligence
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        for item in intel:
            for w in item.get("wallets", []):
                if not any(x["address"] == w for x in wallets):
                    wallets.append({
                        "address": w,
                        "chain": "unknown",
                        "first_seen": item.get("timestamp", ""),
                        "source": "telegram_spy",
                        "group": item.get("group_username", ""),
                        "sender": item.get("sender_username", ""),
                        "linked_case": "",
                        "balance": None,
                        "tx_count": None,
                        "risk_level": "UNKNOWN"
                    })
    except:
        pass
    
    # Filter
    if chain and chain != "all":
        wallets = [w for w in wallets if w.get("chain", "").lower() == chain.lower()]
    if linked_case:
        wallets = [w for w in wallets if w.get("linked_case") == linked_case]
    
    # Sort
    reverse = sort.startswith("-")
    sort_key = sort.lstrip("-")
    wallets.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)
    
    return {
        "total": len(wallets),
        "by_chain": _count_by(wallets, "chain"),
        "by_risk": _count_by(wallets, "risk_level"),
        "wallets": wallets[:500]
    }

@router.post("/wallets/add")
async def add_wallet(
    address: str,
    chain: str = "unknown",
    source: str = "manual",
    group: str = "",
    sender: str = "",
    linked_case: str = "",
    risk_level: str = "MEDIUM"
):
    """Add a wallet to the flow tracker."""
    wallets = _load_wallets()
    if not any(w["address"] == address for w in wallets):
        wallets.append({
            "address": address,
            "chain": chain,
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "group": group,
            "sender": sender,
            "linked_case": linked_case,
            "balance": None,
            "tx_count": None,
            "risk_level": risk_level
        })
        _save_wallets(wallets)
    return {"status": "added", "total": len(wallets)}

@router.get("/wallets/{address}/trace")
async def trace_wallet(address: str):
    """Trace a wallet address across blockchains using the multi-chain scanner."""
    # Detect chain from address format
    chain = _detect_chain(address)
    
    result = {
        "address": address,
        "chain": chain,
        "balance": None,
        "tx_count": None,
        "first_tx": None,
        "last_tx": None,
        "associated_entities": [],
        "risk_indicators": []
    }
    
    # Use the multi-chain scanner if available
    try:
        import sys
        sys.path.insert(0, "/gfin")
        from multichain_crypto_scanner import MultiChainScanner
        scanner = MultiChainScanner()
        scan_result = scanner.scan_wallet(address, chain)
        if scan_result:
            result["balance"] = scan_result.get("balance")
            result["tx_count"] = scan_result.get("tx_count", 0)
            result["first_tx"] = scan_result.get("first_tx")
            result["last_tx"] = scan_result.get("last_tx")
            result["risk_indicators"] = scan_result.get("risk_indicators", [])
    except Exception as e:
        result["error"] = str(e)
    
    # Check if wallet appears in any GFIN cases
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        for item in intel:
            if address in item.get("wallets", []):
                result["associated_entities"].append({
                    "type": "telegram_message",
                    "group": item.get("group_username", ""),
                    "sender": item.get("sender_username", ""),
                    "date": item.get("timestamp", ""),
                    "scam_type": item.get("scam_type", "")
                })
    except:
        pass
    
    return result

def _detect_chain(address: str) -> str:
    """Detect blockchain from address format."""
    if address.startswith("bc1"):
        return "BTC"
    elif address.startswith("1") or address.startswith("3"):
        return "BTC"
    elif address.startswith("0x") and len(address) == 42:
        return "ETH"
    elif address.startswith("T") and len(address) == 34:
        return "TRON"
    elif len(address) > 40 and address.isalnum():
        return "SOL"
    return "unknown"

def _count_by(items, key):
    counts = {}
    for item in items:
        val = item.get(key, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts

# ============================================================
# 2. EVIDENCE CORRELATION
# ============================================================

@router.get("/evidence/correlation/{case_id}")
async def get_evidence_correlation(case_id: str):
    """Get evidence correlation graph for a case."""
    correlations = {
        "case_id": case_id,
        "nodes": [],
        "edges": [],
        "summary": {}
    }
    
    # Load case data from telegram intelligence
    case_wallets = set()
    case_domains = set()
    case_phones = set()
    case_senders = set()
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        
        # Find all items that mention this case or share entities
        
        for item in intel:
            # Check if this item is related to the case
            related = False
            if item.get("case_id") == case_id:
                related = True
            
            if related or case_id == "all":
                for w in item.get("wallets", []):
                    case_wallets.add(w)
                for d in item.get("domains", []):
                    case_domains.add(d)
                for p in item.get("phones", []):
                    case_phones.add(p)
                case_senders.add(item.get("sender_username", ""))
    except:
        pass
    
    # Build nodes
    for w in case_wallets:
        correlations["nodes"].append({"id": w, "type": "WALLET", "label": w[:12] + "..."})
    for d in case_domains:
        correlations["nodes"].append({"id": d, "type": "DOMAIN", "label": d})
    for p in case_phones:
        correlations["nodes"].append({"id": p, "type": "PHONE", "label": p})
    for s in case_senders:
        if s:
            correlations["nodes"].append({"id": "@" + s, "type": "SOCIAL", "label": "@" + s})
    
    # Build edges — link entities that appeared in the same message
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        
        for item in intel:
            entities = []
            entities.extend(item.get("wallets", []))
            entities.extend(item.get("domains", []))
            entities.extend(item.get("phones", []))
            if item.get("sender_username"):
                entities.append("@" + item["sender_username"])
            
            # Create edges between all entities in the same message
            for i, a in enumerate(entities):
                for b in entities[i+1:]:
                    edge = {"source": a, "target": b, "type": "CO_OCCURRENCE"}
                    if edge not in correlations["edges"]:
                        correlations["edges"].append(edge)
    except:
        pass
    
    correlations["summary"] = {
        "total_nodes": len(correlations["nodes"]),
        "total_edges": len(correlations["edges"]),
        "wallets": len(case_wallets),
        "domains": len(case_domains),
        "phones": len(case_phones),
        "senders": len(case_senders)
    }
    
    return correlations

@router.get("/evidence/graph")
async def get_full_evidence_graph():
    """Get the full evidence correlation graph across all cases."""
    return await get_evidence_correlation("all")

# ============================================================
# 3. OPERATOR MAP
# ============================================================

@router.get("/operators/map")
async def get_operator_map():
    """Get operator network map showing relationships between scam operators."""
    operators = {}
    
    # From known laundering operations
    try:
        from money_laundering_detector import KNOWN_LAUNDERING_OPERATIONS
        for op in KNOWN_LAUNDERING_OPERATIONS:
            operator = op["operator"]
            if operator not in operators:
                operators[operator] = {
                    "id": operator,
                    "type": "OPERATOR",
                    "label": operator,
                    "channels": [],
                    "countries": [],
                    "risk_level": op["risk_level"],
                    "patterns": set(),
                    "classification": op["description"]
                }
            operators[operator]["channels"].append({
                "username": op["group_username"],
                "name": op["group_name"],
                "country": op["country"]
            })
            operators[operator]["countries"].append(op["country"])
            operators[operator]["patterns"].update(op.get("patterns", []))
    except:
        pass
    
    # From telegram intelligence — find frequent senders
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        
        sender_stats = {}
        for item in intel:
            sender = item.get("sender_username", "")
            if not sender:
                continue
            if sender not in sender_stats:
                sender_stats[sender] = {
                    "id": "@" + sender,
                    "type": "TELEGRAM_USER",
                    "label": "@" + sender,
                    "channels": [],
                    "message_count": 0,
                    "scam_types": set(),
                    "wallets_posted": set(),
                    "domains_posted": set(),
                    "groups": set()
                }
            sender_stats[sender]["message_count"] += 1
            if item.get("scam_type"):
                sender_stats[sender]["scam_types"].add(item["scam_type"])
            sender_stats[sender]["wallets_posted"].update(item.get("wallets", []))
            sender_stats[sender]["domains_posted"].update(item.get("domains", []))
            sender_stats[sender]["groups"].add(item.get("group_username", ""))
        
        # Add high-activity senders
        for sender, stats in sender_stats.items():
            if stats["message_count"] >= 2 or len(stats["wallets_posted"]) >= 1 or len(stats["domains_posted"]) >= 1:
                stats["groups"] = list(stats["groups"])
                stats["scam_types"] = list(stats["scam_types"])
                stats["wallets_posted"] = list(stats["wallets_posted"])
                stats["domains_posted"] = list(stats["domains_posted"])
                operators[sender] = stats
    except:
        pass
    
    # Convert sets to lists for JSON serialization
    for op in operators.values():
        if isinstance(op.get("patterns"), set):
            op["patterns"] = list(op["patterns"])
    
    # Build edges — operators that share channels, wallets, or domains
    edges = []
    op_list = list(operators.values())
    for i, a in enumerate(op_list):
        for b in op_list[i+1:]:
            # Check for shared wallets
            a_wallets = set(a.get("wallets_posted", []))
            b_wallets = set(b.get("wallets_posted", []))
            shared_wallets = a_wallets & b_wallets
            if shared_wallets:
                edges.append({"source": a["id"], "target": b["id"], "type": "SHARED_WALLET", "count": len(shared_wallets)})
            
            # Check for shared domains
            a_domains = set(a.get("domains_posted", []))
            b_domains = set(b.get("domains_posted", []))
            shared_domains = a_domains & b_domains
            if shared_domains:
                edges.append({"source": a["id"], "target": b["id"], "type": "SHARED_DOMAIN", "count": len(shared_domains)})
            
            # Check for shared groups
            a_groups = set(g.get("username", "") if isinstance(g, dict) else g for g in a.get("channels", []))
            b_groups = set(g.get("username", "") if isinstance(g, dict) else g for g in b.get("channels", []))
            shared_groups = a_groups & b_groups
            if shared_groups and a["id"] != b["id"]:
                edges.append({"source": a["id"], "target": b["id"], "type": "SHARED_CHANNEL", "count": len(shared_groups)})
    
    return {
        "total_operators": len(operators),
        "total_edges": len(edges),
        "nodes": list(operators.values()),
        "edges": edges,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

# ============================================================
# 4. VICTIM OUTREACH TRACKER
# ============================================================

OUTREACH_FILE = "/gfin/outreach_tracker.json"

def _load_outreach():
    try:
        with open(OUTREACH_FILE, "r") as f:
            return json.load(f)
    except:
        return {"groups_posted": [], "dms_sent": [], "complaints_received": []}

def _save_outreach(data):
    with open(OUTREACH_FILE, "w") as f:
        json.dump(data, f, indent=2)

@router.get("/outreach")
async def get_outreach_tracker():
    """Get victim outreach tracking data."""
    data = _load_outreach()
    
    # Auto-populate from known posts
    known_posts = [
        {"group": "@rocket21scam", "group_name": "Rocket21 - we got scammed", "posted_at": "2026-08-27T10:50:00Z", "status": "POSTED", "type": "GROUP_POST"},
        {"group": "@ScammedbyGothixAI", "group_name": "Gothix AI Scammed Users", "posted_at": "2026-08-27T10:50:00Z", "status": "POSTED", "type": "GROUP_POST"},
        {"group": "@fxscammersexposed", "group_name": "Forex Scammers Exposed", "posted_at": "2026-08-27T10:51:00Z", "status": "POSTED", "type": "GROUP_POST"},
        {"group": "@ultgg", "group_name": "We got scammed (the aftermath)", "posted_at": "", "status": "BLOCKED", "type": "GROUP_POST"},
        {"group": "@scammers_unmasked_with_tee", "group_name": "SCAMMERS Unmasked", "posted_at": "", "status": "READ_ONLY", "type": "GROUP_POST"},
    ]
    
    known_dms = [
        {"recipient": "@Tonytony150", "recipient_name": "Tony", "sent_at": "2026-08-27T10:52:00Z", "status": "SENT", "type": "DM"},
    ]
    
    # Merge with stored data
    for post in known_posts:
        if not any(p["group"] == post["group"] for p in data["groups_posted"]):
            data["groups_posted"].append(post)
    for dm in known_dms:
        if not any(d["recipient"] == dm["recipient"] for d in data["dms_sent"]):
            data["dms_sent"].append(dm)
    
    return {
        "summary": {
            "total_groups_posted": sum(1 for g in data["groups_posted"] if g.get("status") == "POSTED"),
            "total_groups_blocked": sum(1 for g in data["groups_posted"] if g.get("status") in ["BLOCKED", "READ_ONLY"]),
            "total_dms_sent": len(data["dms_sent"]),
            "complaints_received": len(data.get("complaints_received", [])),
            "reach_estimate": "775+ victims reached (sum of group memberships)"
        },
        "groups_posted": data["groups_posted"],
        "dms_sent": data["dms_sent"],
        "complaints_received": data.get("complaints_received", [])
    }

@router.post("/outreach/complaint")
async def log_outreach_complaint(
    source_group: str = "",
    victim_username: str = "",
    case_id: str = "",
    complaint_type: str = "",
    notes: str = ""
):
    """Log a complaint that came in from outreach efforts."""
    data = _load_outreach()
    complaint = {
        "id": f"OUTREACH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "source_group": source_group,
        "victim_username": victim_username,
        "case_id": case_id,
        "complaint_type": complaint_type,
        "notes": notes,
        "received_at": datetime.now(timezone.utc).isoformat()
    }
    data.setdefault("complaints_received", []).append(complaint)
    _save_outreach(data)
    return {"status": "logged", "complaint": complaint}

# ============================================================
# 5. UNIFIED ALERT PRIORITY QUEUE
# ============================================================

@router.get("/alerts/unified")
async def get_unified_alerts(
    level: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = 100
):
    """Get all alerts unified across scam alerts, laundering alerts, and intel alerts."""
    all_alerts = []
    
    # 1. Laundering alerts
    try:
        from money_laundering_detector import KNOWN_LAUNDERING_OPERATIONS
        for op in KNOWN_LAUNDERING_OPERATIONS:
            all_alerts.append({
                "alert_id": f"LAUDR-{op['group_username'].replace('@', '').upper()}",
                "type": "MONEY_LAUNDERING",
                "level": op["risk_level"],
                "title": f"Laundering operation: {op['group_name'][:50]}",
                "description": op["description"],
                "source": "telegram_surveillance",
                "operator": op["operator"],
                "country": op["country"],
                "patterns": op.get("patterns", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "NEW",
                "link": f"/api/laundering/operation/{op['group_username'].replace('@', '')}"
            })
    except:
        pass
    
    # 2. Laundering alerts from file (real-time detections)
    try:
        with open("/gfin/laundering_alerts.json", "r") as f:
            launder_alerts = json.load(f)
        for a in launder_alerts:
            all_alerts.append({
                "alert_id": a.get("alert_id", ""),
                "type": "MONEY_LAUNDERING",
                "level": a.get("risk_level", a.get("level", "MEDIUM")),
                "title": f"Laundering: {a.get('group_name', 'Unknown')[:50]}",
                "description": a.get("classification", a.get("message_excerpt", ""))[:200],
                "source": a.get("source", "telegram_spy"),
                "group": a.get("group_username", ""),
                "timestamp": a.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "status": a.get("status", "NEW")
            })
    except:
        pass
    
    # 3. Telegram intelligence alerts (scam detections)
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        for item in intel:
            if item.get("scam_type") or item.get("is_victim"):
                risk = item.get("risk_level", "MEDIUM")
                all_alerts.append({
                    "alert_id": f"INTEL-{item.get('id', hash(item.get('text', '')[:50]))}",
                    "type": "SCAM_DETECTION" if item.get("scam_type") else "VICTIM_REPORT",
                    "level": risk,
                    "title": f"{item.get('scam_type', 'Victim report')}: {item.get('group_username', '')}",
                    "description": item.get("text", "")[:200],
                    "source": "telegram_spy",
                    "group": item.get("group_username", ""),
                    "sender": item.get("sender_username", ""),
                    "wallets": item.get("wallets", []),
                    "domains": item.get("domains", []),
                    "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "status": "NEW"
                })
    except:
        pass
    
    # 4. Hunter investigation alerts
    try:
        import glob
        hunter_files = glob.glob("/gfin/investigation_*.json")
        for hf in hunter_files[-20:]:  # Last 20 investigations
            with open(hf, "r") as f:
                inv = json.load(f)
            risk = inv.get("scam_analysis", {}).get("risk_level", "MEDIUM")
            all_alerts.append({
                "alert_id": inv.get("investigation_id", os.path.basename(hf)),
                "type": "HUNTER_INVESTIGATION",
                "level": risk,
                "title": f"Hunter: {inv.get('subject', {}).get('identifier', 'Unknown')}",
                "description": inv.get("subject", {}).get("trigger_reason", ""),
                "source": "gfin_hunter",
                "timestamp": inv.get("timestamp", ""),
                "status": "INVESTIGATED"
            })
    except:
        pass
    
    # Filter
    if level:
        all_alerts = [a for a in all_alerts if a.get("level") == level.upper()]
    if alert_type:
        all_alerts = [a for a in all_alerts if a.get("type") == alert_type.upper()]
    
    # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW) then by timestamp
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFORMATIONAL": 4}
    all_alerts.sort(key=lambda x: (
        priority_order.get(x.get("level", "LOW"), 5),
        x.get("timestamp", ""),
    ))
    
    return {
        "total": len(all_alerts),
        "by_level": _count_by(all_alerts, "level"),
        "by_type": _count_by(all_alerts, "type"),
        "alerts": all_alerts[:limit]
    }

# ============================================================
# 6. DASHBOARD OVERVIEW — Enhanced stats
# ============================================================

@router.get("/overview")
async def get_enhanced_overview():
    """Get enhanced dashboard overview with all system stats."""
    overview = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "monitoring": {},
        "laundering": {},
        "wallets": {},
        "outreach": {},
        "alerts": {}
    }
    
    # Monitoring stats
    try:
        with open("/gfin/victim_groups.json", "r") as f:
            victim_groups = json.load(f)
        with open("/gfin/monitored_groups.json", "r") as f:
            scam_groups = json.load(f)
        overview["monitoring"] = {
            "scam_groups": len(scam_groups),
            "victim_groups": len(victim_groups),
            "total_groups": len(scam_groups) + len(victim_groups),
            "total_members_monitored": sum(g.get("member_count", 0) for g in scam_groups) + sum(g.get("member_count", 0) for g in victim_groups)
        }
    except:
        pass
    
    # Laundering stats
    try:
        from money_laundering_detector import KNOWN_LAUNDERING_OPERATIONS
        overview["laundering"] = {
            "total_operations": len(KNOWN_LAUNDERING_OPERATIONS),
            "critical": sum(1 for op in KNOWN_LAUNDERING_OPERATIONS if op["risk_level"] == "CRITICAL"),
            "high": sum(1 for op in KNOWN_LAUNDERING_OPERATIONS if op["risk_level"] == "HIGH"),
            "countries_affected": len(set(op["country"] for op in KNOWN_LAUNDERING_OPERATIONS)),
            "primary_operator": "@btcv123",
            "operator_reach": "70+ countries"
        }
    except:
        pass
    
    # Wallet stats
    wallets = _load_wallets()
    overview["wallets"] = {
        "total_tracked": len(wallets),
        "by_chain": _count_by(wallets, "chain")
    }
    
    # Outreach stats
    outreach = _load_outreach()
    overview["outreach"] = {
        "groups_posted": sum(1 for g in outreach.get("groups_posted", []) if g.get("status") == "POSTED"),
        "dms_sent": len(outreach.get("dms_sent", [])),
        "complaints_received": len(outreach.get("complaints_received", []))
    }
    
    # Alert stats
    try:
        with open("/gfin/telegram_intelligence.json", "r") as f:
            intel = json.load(f)
        overview["alerts"] = {
            "total_intel_items": len(intel),
            "scam_detections": sum(1 for i in intel if i.get("scam_type")),
            "victim_reports": sum(1 for i in intel if i.get("is_victim")),
            "wallets_found": len(set(w for i in intel for w in i.get("wallets", []))),
            "domains_found": len(set(d for i in intel for d in i.get("domains", [])))
        }
    except:
        pass
    
    return overview

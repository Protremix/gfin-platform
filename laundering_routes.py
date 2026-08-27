"""Money Laundering Alert API routes for GFIN"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from money_laundering_detector import (
    detect_money_laundering,
    create_laundering_alert,
    generate_laundering_report,
    KNOWN_LAUNDERING_OPERATIONS
)

router = APIRouter(prefix="/api/laundering", tags=["Money Laundering Detection"])

class DetectionRequest(BaseModel):
    text: str
    source: Optional[str] = "manual"
    group_name: Optional[str] = ""
    group_username: Optional[str] = ""


@router.post("/detect")
async def detect_laundering(req: DetectionRequest):
    """Detect money laundering indicators in text."""
    result = detect_money_laundering(req.text)
    
    # If laundering detected and group info provided, create alert
    if result["is_laundering"] and req.group_username:
        alert = create_laundering_alert(
            source=req.source,
            group_name=req.group_name,
            group_username=req.group_username,
            message_text=req.text,
            detected=result
        )
        result["alert"] = alert
    
    return result


@router.get("/report")
async def get_laundering_report():
    """Get full money laundering intelligence report."""
    report = generate_laundering_report()
    return report


@router.get("/operations")
async def list_laundering_operations():
    """List all known money laundering operations."""
    return {
        "total": len(KNOWN_LAUNDERING_OPERATIONS),
        "operations": KNOWN_LAUNDERING_OPERATIONS,
        "primary_operator": "@btcv123",
        "countries_affected": list(set(op["country"] for op in KNOWN_LAUNDERING_OPERATIONS)),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/operation/{username}")
async def get_operation(username: str):
    """Get details of a specific laundering operation by group username."""
    for op in KNOWN_LAUNDERING_OPERATIONS:
        if op["group_username"].replace("@", "").lower() == username.lower().replace("@", ""):
            return op
    raise HTTPException(status_code=404, detail="Operation not found")


@router.get("/patterns")
async def list_detection_patterns():
    """List all money laundering detection patterns."""
    from money_laundering_detector import LAUNDERING_PATTERNS
    patterns = []
    for name, defn in LAUNDERING_PATTERNS.items():
        patterns.append({
            "name": name,
            "description": defn["description"],
            "weight": defn["weight"],
            "keyword_count": len(defn["keywords"])
        })
    return {"total": len(patterns), "patterns": patterns}


@router.post("/analyze-message")
async def analyze_telegram_message(
    text: str,
    group_name: str = "",
    group_username: str = "",
    source: str = "telegram_spy"
):
    """Analyze a Telegram message for money laundering indicators.
    Used by the spy system for real-time detection."""
    result = detect_money_laundering(text)
    
    if result["is_laundering"]:
        alert = create_laundering_alert(
            source=source,
            group_name=group_name,
            group_username=group_username,
            message_text=text,
            detected=result
        )
        # Save alert to file for persistence
        alerts_file = "/gfin/laundering_alerts.json"
        try:
            with open(alerts_file, "r") as f:
                alerts = json.load(f)
        except:
            alerts = []
        alerts.append(alert)
        with open(alerts_file, "w") as f:
            json.dump(alerts, f, indent=2)
        
        return {"detected": True, "alert": alert, "analysis": result}
    
    return {"detected": False, "analysis": result}


@router.get("/alerts")
async def list_laundering_alerts():
    """List all filed money laundering alerts."""
    alerts_file = "/gfin/laundering_alerts.json"
    try:
        with open(alerts_file, "r") as f:
            alerts = json.load(f)
    except:
        alerts = []
    
    # Also include pre-filed alerts for known operations
    for op in KNOWN_LAUNDERING_OPERATIONS:
        alert_id = f"LAUNDER-KNOWN-{op['group_username'].replace('@', '').upper()}"
        if not any(a.get("alert_id") == alert_id for a in alerts):
            alerts.append({
                "alert_id": alert_id,
                "type": "MONEY_LAUNDERING",
                "level": op["risk_level"],
                "source": "telegram_surveillance",
                "group_name": op["group_name"],
                "group_username": op["group_username"],
                "country": op["country"],
                "operator": op["operator"],
                "classification": op["description"],
                "detected_patterns": op["patterns"],
                "status": "NEW",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    return {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a.get("level") == "CRITICAL"),
        "high": sum(1 for a in alerts if a.get("level") == "HIGH"),
        "alerts": sorted(alerts, key=lambda x: x.get("timestamp", ""), reverse=True)
    }

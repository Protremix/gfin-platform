"""API routes for Telegram Intelligence v2.0"""
from fastapi import APIRouter, Query
from telegram_intel_v2 import (
    list_all_operators, generate_operator_dossier,
    auto_link_telegram_to_cases, identify_victims,
    build_entity_graph, check_new_entities_for_alerts,
    reprocess_wallets
)

router = APIRouter()

@router.get("/api/tg-intel/operators")
async def get_operators():
    """List all Telegram operators with cross-group activity, ranked by risk."""
    return list_all_operators()

@router.get("/api/tg-intel/dossier")
async def get_dossier(sender_name: str = Query(...)):
    """Generate a full intelligence dossier for a Telegram operator."""
    dossier = generate_operator_dossier(sender_name)
    if not dossier:
        return {"error": "Operator not found", "sender_name": sender_name}
    return dossier

@router.post("/api/tg-intel/auto-link")
async def run_auto_link():
    """Auto-link Telegram intelligence to existing cases."""
    linked = auto_link_telegram_to_cases()
    return {"linked_count": len(linked), "linked": linked}

@router.get("/api/tg-intel/victims")
async def get_victims():
    """List identified potential victims from Telegram."""
    return identify_victims()

@router.get("/api/tg-intel/graph")
async def get_entity_graph():
    """Get entity correlation graph showing shared entities between operators."""
    return build_entity_graph()

@router.post("/api/tg-intel/check-alerts")
async def run_alert_check():
    """Check for new Telegram entities matching existing cases."""
    alerts = check_new_entities_for_alerts()
    return {"alerts_fired": len(alerts), "alerts": alerts}

@router.post("/api/tg-intel/reprocess-wallets")
async def run_wallet_reprocess():
    """Reprocess all Telegram messages with fixed wallet extraction."""
    return reprocess_wallets()

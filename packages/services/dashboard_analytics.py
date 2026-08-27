"""
GFIN Fraud Intelligence Platform - Dashboard & Analytics Module

Provides FastAPI analytics endpoints and PostgreSQL database integrations
for complaints, cases, alerts, police officers, and country routing metrics.
"""

from typing import Any, Dict, List, Optional
import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import asyncpg

logger = logging.getLogger("gfin.dashboard_analytics")
logging.basicConfig(level=logging.INFO)

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "gfin")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "gfin")


# Chart.js formatting helper functions
def format_chartjs_bar(
    labels: List[str],
    data: List[float],
    label: str = "Count",
    background_colors: Optional[List[str]] = None,
    border_colors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Format data structure for Chart.js Bar Charts."""
    default_colors = [
        "#e94560", "#0f3460", "#533483", "#00b4d8", "#0077b6",
        "#ffb703", "#fb8500", "#2a9d8f", "#e76f51", "#9d4edd"
    ]
    bg_colors = background_colors or (default_colors * (len(data) // len(default_colors) + 1))[:len(data)]
    return {
        "labels": labels,
        "datasets": [
            {
                "label": label,
                "data": data,
                "backgroundColor": bg_colors,
                "borderColor": border_colors or bg_colors,
                "borderWidth": 1,
            }
        ],
    }


def format_chartjs_pie(
    labels: List[str],
    data: List[float],
    label: str = "Distribution",
    colors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Format data structure for Chart.js Pie / Doughnut Charts."""
    default_colors = ["#e94560", "#ff6b6b", "#fca311", "#4ecdc4", "#457b9d", "#1d3557"]
    bg_colors = colors or (default_colors * (len(data) // len(default_colors) + 1))[:len(data)]
    return {
        "labels": labels,
        "datasets": [
            {
                "label": label,
                "data": data,
                "backgroundColor": bg_colors,
                "borderColor": "#1a1a2e",
                "borderWidth": 2,
            }
        ],
    }


def format_chartjs_line(
    labels: List[str],
    data: List[float],
    label: str = "Complaints Trend",
    line_color: str = "#e94560",
    fill_color: str = "rgba(233, 69, 96, 0.15)",
) -> Dict[str, Any]:
    """Format data structure for Chart.js Line Charts."""
    return {
        "labels": labels,
        "datasets": [
            {
                "label": label,
                "data": data,
                "borderColor": line_color,
                "backgroundColor": fill_color,
                "fill": True,
                "tension": 0.4,
                "pointRadius": 4,
                "pointHoverRadius": 6,
                "pointBackgroundColor": line_color,
            }
        ],
    }


async def get_db_connection():
    """Establish asyncpg connection to GFIN PostgreSQL database."""
    return await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        timeout=5.0,
    )


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Fallback Datasets when DB is offline or empty
FALLBACK_OVERVIEW = {
    "total_complaints": 1248,
    "active_cases": 342,
    "resolved_cases": 816,
    "critical_alerts": 45,
    "total_victims": 1105,
    "total_losses": 14250000.00,
    "is_fallback": True,
}

FALLBACK_SCAM_TYPES = [
    {"scam_type": "Investment / Pig Butchering", "count": 412, "percentage": 33.0, "total_loss": 6500000.00},
    {"scam_type": "Crypto Phishing", "count": 285, "percentage": 22.8, "total_loss": 3800000.00},
    {"scam_type": "Impersonation", "count": 210, "percentage": 16.8, "total_loss": 1200000.00},
    {"scam_type": "Romance Fraud", "count": 165, "percentage": 13.2, "total_loss": 2100000.00},
    {"scam_type": "Tech Support Scam", "count": 110, "percentage": 8.8, "total_loss": 450000.00},
    {"scam_type": "E-commerce Fraud", "count": 66, "percentage": 5.3, "total_loss": 200000.00},
]

FALLBACK_RISK_LEVELS = [
    {"risk_level": "CRITICAL", "count": 185, "percentage": 14.8},
    {"risk_level": "HIGH", "count": 420, "percentage": 33.7},
    {"risk_level": "MEDIUM", "count": 480, "percentage": 38.5},
    {"risk_level": "LOW", "count": 163, "percentage": 13.0},
]

FALLBACK_COUNTRIES = [
    {"country_code": "US", "country_name": "United States", "count": 380, "percentage": 30.4, "total_loss": 4500000.00, "lat": 37.0902, "lng": -95.7129},
    {"country_code": "GB", "country_name": "United Kingdom", "count": 210, "percentage": 16.8, "total_loss": 2800000.00, "lat": 55.3781, "lng": -3.4360},
    {"country_code": "CA", "country_name": "Canada", "count": 140, "percentage": 11.2, "total_loss": 1600000.00, "lat": 56.1304, "lng": -106.3468},
    {"country_code": "AU", "country_name": "Australia", "count": 115, "percentage": 9.2, "total_loss": 1250000.00, "lat": -25.2744, "lng": 133.7751},
    {"country_code": "DE", "country_name": "Germany", "count": 95, "percentage": 7.6, "total_loss": 980000.00, "lat": 51.1657, "lng": 10.4515},
    {"country_code": "SG", "country_name": "Singapore", "count": 85, "percentage": 6.8, "total_loss": 1100000.00, "lat": 1.3521, "lng": 103.8198},
    {"country_code": "FR", "country_name": "France", "count": 70, "percentage": 5.6, "total_loss": 720000.00, "lat": 46.2276, "lng": 2.2137},
    {"country_code": "JP", "country_name": "Japan", "count": 55, "percentage": 4.4, "total_loss": 550000.00, "lat": 36.2048, "lng": 138.2529},
    {"country_code": "IN", "country_name": "India", "count": 50, "percentage": 4.0, "total_loss": 400000.00, "lat": 20.5937, "lng": 78.9629},
    {"country_code": "AE", "country_name": "UAE", "count": 48, "percentage": 3.8, "total_loss": 350000.00, "lat": 23.4241, "lng": 53.8478},
]

FALLBACK_CRYPTO = {
    "wallets_found": 248,
    "usdt_traced": 8450200.00,
    "chains_involved": ["Tron (TRC-20)", "Ethereum (ERC-20)", "BNB Smart Chain", "Bitcoin", "Solana", "Polygon"],
    "chain_breakdown": [
        {"chain": "Tron (TRC-20)", "wallets": 104, "usdt_amount": 3549084.00, "percentage": 42.0},
        {"chain": "Ethereum (ERC-20)", "wallets": 87, "usdt_amount": 2957570.00, "percentage": 35.0},
        {"chain": "BNB Smart Chain", "wallets": 30, "usdt_amount": 1014024.00, "percentage": 12.0},
        {"chain": "Bitcoin", "wallets": 15, "usdt_amount": 507012.00, "percentage": 6.0},
        {"chain": "Solana", "wallets": 8, "usdt_amount": 253506.00, "percentage": 3.0},
        {"chain": "Polygon", "wallets": 4, "usdt_amount": 169004.00, "percentage": 2.0},
    ],
    "is_fallback": True,
}


@router.get("/overview")
async def get_overview():
    """GET /api/analytics/overview — total complaints, active cases, resolved cases, critical alerts, total victims, total losses"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                (SELECT COUNT(*) FROM complaints) as total_complaints,
                (SELECT COUNT(*) FROM cases WHERE LOWER(status) NOT IN ('resolved', 'closed')) as active_cases,
                (SELECT COUNT(*) FROM cases WHERE LOWER(status) IN ('resolved', 'closed')) as resolved_cases,
                (SELECT COUNT(*) FROM alerts WHERE UPPER(risk_level) = $1 OR UPPER(severity) = $1) as critical_alerts,
                (SELECT COUNT(DISTINCT victim_id) FROM complaints) as total_victims,
                (SELECT COALESCE(SUM(loss_amount), 0) FROM complaints) as total_losses
        """
        row = await conn.fetchrow(query, "CRITICAL")
        if row and row["total_complaints"] is not None:
            return {
                "total_complaints": int(row["total_complaints"]),
                "active_cases": int(row["active_cases"]),
                "resolved_cases": int(row["resolved_cases"]),
                "critical_alerts": int(row["critical_alerts"]),
                "total_victims": int(row["total_victims"]),
                "total_losses": float(row["total_losses"]),
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /overview, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    return FALLBACK_OVERVIEW


@router.get("/scam-types")
async def get_scam_types():
    """GET /api/analytics/scam-types — breakdown by scam type (counts + percentages)"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                COALESCE(scam_type, 'Unspecified') as scam_type,
                COUNT(*) as count,
                COALESCE(SUM(loss_amount), 0) as total_loss
            FROM complaints
            GROUP BY COALESCE(scam_type, 'Unspecified')
            ORDER BY count DESC
        """
        rows = await conn.fetch(query)
        if rows:
            total_count = sum(r["count"] for r in rows) or 1
            items = []
            for r in rows:
                c = int(r["count"])
                items.append({
                    "scam_type": r["scam_type"],
                    "count": c,
                    "percentage": round((c / total_count) * 100, 1),
                    "total_loss": float(r["total_loss"]),
                })
            labels = [item["scam_type"] for item in items]
            data = [item["count"] for item in items]
            chart_data = format_chartjs_bar(labels, data, label="Complaints by Scam Type")
            return {
                "total_complaints": total_count,
                "items": items,
                "chart_data": chart_data,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /scam-types, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    labels = [item["scam_type"] for item in FALLBACK_SCAM_TYPES]
    data = [item["count"] for item in FALLBACK_SCAM_TYPES]
    chart_data = format_chartjs_bar(labels, data, label="Complaints by Scam Type")
    return {
        "total_complaints": sum(item["count"] for item in FALLBACK_SCAM_TYPES),
        "items": FALLBACK_SCAM_TYPES,
        "chart_data": chart_data,
        "is_fallback": True,
    }


@router.get("/risk-levels")
async def get_risk_levels():
    """GET /api/analytics/risk-levels — breakdown by risk level (CRITICAL/HIGH/MEDIUM/LOW)"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                UPPER(COALESCE(risk_level, 'MEDIUM')) as risk_level,
                COUNT(*) as count
            FROM complaints
            GROUP BY UPPER(COALESCE(risk_level, 'MEDIUM'))
            ORDER BY count DESC
        """
        rows = await conn.fetch(query)
        if rows:
            total = sum(r["count"] for r in rows) or 1
            items = []
            for r in rows:
                c = int(r["count"])
                items.append({
                    "risk_level": r["risk_level"],
                    "count": c,
                    "percentage": round((c / total) * 100, 1),
                })
            labels = [item["risk_level"] for item in items]
            data = [item["count"] for item in items]
            risk_color_map = {
                "CRITICAL": "#e94560",
                "HIGH": "#ff6b6b",
                "MEDIUM": "#fca311",
                "LOW": "#4ecdc4",
            }
            colors = [risk_color_map.get(lbl, "#0f3460") for lbl in labels]
            chart_data = format_chartjs_pie(labels, data, label="Risk Level Breakdown", colors=colors)
            return {
                "total": total,
                "items": items,
                "chart_data": chart_data,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /risk-levels, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    labels = [item["risk_level"] for item in FALLBACK_RISK_LEVELS]
    data = [item["count"] for item in FALLBACK_RISK_LEVELS]
    colors = ["#e94560", "#ff6b6b", "#fca311", "#4ecdc4"]
    chart_data = format_chartjs_pie(labels, data, label="Risk Level Breakdown", colors=colors)
    return {
        "total": sum(item["count"] for item in FALLBACK_RISK_LEVELS),
        "items": FALLBACK_RISK_LEVELS,
        "chart_data": chart_data,
        "is_fallback": True,
    }


@router.get("/countries")
async def get_countries(limit: int = Query(10, ge=1, le=100)):
    """GET /api/analytics/countries — top 10 countries by complaint count"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                c.country_code,
                COALESCE(cr.country_name, c.country_code, 'Unknown') as country_name,
                COUNT(*) as count,
                COALESCE(SUM(c.loss_amount), 0) as total_loss
            FROM complaints c
            LEFT JOIN country_routing cr ON UPPER(c.country_code) = UPPER(cr.code)
            GROUP BY c.country_code, cr.country_name
            ORDER BY count DESC
            LIMIT $1
        """
        rows = await conn.fetch(query, limit)
        if rows:
            total = sum(r["count"] for r in rows) or 1
            items = []
            for r in rows:
                cnt = int(r["count"])
                items.append({
                    "country_code": r["country_code"],
                    "country_name": r["country_name"],
                    "count": cnt,
                    "percentage": round((cnt / total) * 100, 1),
                    "total_loss": float(r["total_loss"]),
                })
            labels = [item["country_name"] for item in items]
            data = [item["count"] for item in items]
            chart_data = format_chartjs_bar(labels, data, label="Complaints by Country")
            return {
                "top_countries": items,
                "chart_data": chart_data,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /countries, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    top_items = FALLBACK_COUNTRIES[:limit]
    labels = [item["country_name"] for item in top_items]
    data = [item["count"] for item in top_items]
    chart_data = format_chartjs_bar(labels, data, label="Complaints by Country")
    return {
        "top_countries": top_items,
        "chart_data": chart_data,
        "is_fallback": True,
    }


@router.get("/timeline")
async def get_timeline(
    interval: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365)
):
    """GET /api/analytics/timeline — complaints over time (daily/weekly/monthly)"""
    conn = None
    try:
        conn = await get_db_connection()
        if interval == "daily":
            query = """
                SELECT
                    TO_CHAR(created_at, 'YYYY-MM-DD') as period,
                    COUNT(*) as count,
                    COALESCE(SUM(loss_amount), 0) as total_loss
                FROM complaints
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
                GROUP BY period
                ORDER BY period ASC
            """
        elif interval == "weekly":
            query = """
                SELECT
                    TO_CHAR(DATE_TRUNC('week', created_at), 'YYYY-MM-DD') as period,
                    COUNT(*) as count,
                    COALESCE(SUM(loss_amount), 0) as total_loss
                FROM complaints
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
                GROUP BY period
                ORDER BY period ASC
            """
        else:  # monthly
            query = """
                SELECT
                    TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY-MM') as period,
                    COUNT(*) as count,
                    COALESCE(SUM(loss_amount), 0) as total_loss
                FROM complaints
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
                GROUP BY period
                ORDER BY period ASC
            """
        rows = await conn.fetch(query, days)
        if rows:
            timeline_items = [
                {
                    "date": r["period"],
                    "count": int(r["count"]),
                    "total_loss": float(r["total_loss"]),
                }
                for r in rows
            ]
            labels = [item["date"] for item in timeline_items]
            data = [item["count"] for item in timeline_items]
            chart_data = format_chartjs_line(labels, data, label=f"Complaints ({interval.capitalize()})")
            return {
                "interval": interval,
                "days": days,
                "timeline": timeline_items,
                "chart_data": chart_data,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /timeline, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    # Generate realistic fallback timeline data based on selected interval
    now = datetime.utcnow()
    timeline_items = []
    if interval == "daily":
        points = min(days, 30)
        base_count = 35
        for i in range(points - 1, -1, -1):
            dt = now - timedelta(days=i)
            variation = (dt.day * 7 + dt.month * 13) % 25 - 10
            c = max(10, base_count + variation)
            timeline_items.append({
                "date": dt.strftime("%Y-%m-%d"),
                "count": c,
                "total_loss": float(c * 11500 + (dt.day * 1000)),
            })
    elif interval == "weekly":
        weeks = min(days // 7, 12) or 8
        for i in range(weeks - 1, -1, -1):
            dt = now - timedelta(weeks=i)
            c = 220 + (i * 15) % 80
            timeline_items.append({
                "date": dt.strftime("%Y-%W"),
                "count": c,
                "total_loss": float(c * 12000),
            })
    else:  # monthly
        months = 12
        for i in range(months - 1, -1, -1):
            dt = now - timedelta(days=i * 30)
            c = 850 + (i * 45) % 250
            timeline_items.append({
                "date": dt.strftime("%Y-%m"),
                "count": c,
                "total_loss": float(c * 11800),
            })

    labels = [item["date"] for item in timeline_items]
    data = [item["count"] for item in timeline_items]
    chart_data = format_chartjs_line(labels, data, label=f"Complaints ({interval.capitalize()})")
    return {
        "interval": interval,
        "days": days,
        "timeline": timeline_items,
        "chart_data": chart_data,
        "is_fallback": True,
    }


@router.get("/financial-loss")
async def get_financial_loss():
    """GET /api/analytics/financial-loss — total losses by scam type"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                COALESCE(scam_type, 'Unspecified') as scam_type,
                COALESCE(SUM(loss_amount), 0) as total_loss,
                COUNT(*) as count,
                COALESCE(AVG(loss_amount), 0) as avg_loss
            FROM complaints
            GROUP BY COALESCE(scam_type, 'Unspecified')
            ORDER BY total_loss DESC
        """
        rows = await conn.fetch(query)
        if rows:
            grand_total = sum(float(r["total_loss"]) for r in rows) or 1.0
            items = []
            for r in rows:
                tot = float(r["total_loss"])
                items.append({
                    "scam_type": r["scam_type"],
                    "total_loss": tot,
                    "count": int(r["count"]),
                    "avg_loss": float(r["avg_loss"]),
                    "percentage": round((tot / grand_total) * 100, 1),
                })
            labels = [item["scam_type"] for item in items]
            data = [item["total_loss"] for item in items]
            chart_data = format_chartjs_bar(
                labels, data, label="Total Loss ($)", background_colors=["#e94560", "#ff6b6b", "#fca311", "#4ecdc4", "#457b9d", "#1d3557"]
            )
            return {
                "grand_total_loss": grand_total,
                "items": items,
                "chart_data": chart_data,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /financial-loss, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    items = [
        {"scam_type": "Investment / Pig Butchering", "total_loss": 6500000.00, "count": 412, "avg_loss": 15776.70, "percentage": 45.6},
        {"scam_type": "Crypto Phishing", "total_loss": 3800000.00, "count": 285, "avg_loss": 13333.33, "percentage": 26.7},
        {"scam_type": "Romance Fraud", "total_loss": 2100000.00, "count": 165, "avg_loss": 12727.27, "percentage": 14.7},
        {"scam_type": "Impersonation", "total_loss": 1200000.00, "count": 210, "avg_loss": 5714.28, "percentage": 8.4},
        {"scam_type": "Tech Support Scam", "total_loss": 450000.00, "count": 110, "avg_loss": 4090.90, "percentage": 3.2},
        {"scam_type": "E-commerce Fraud", "total_loss": 200000.00, "count": 66, "avg_loss": 3030.30, "percentage": 1.4},
    ]
    grand_total = sum(item["total_loss"] for item in items)
    labels = [item["scam_type"] for item in items]
    data = [item["total_loss"] for item in items]
    chart_data = format_chartjs_bar(
        labels, data, label="Total Loss ($)", background_colors=["#e94560", "#ff6b6b", "#fca311", "#4ecdc4", "#457b9d", "#1d3557"]
    )
    return {
        "grand_total_loss": grand_total,
        "items": items,
        "chart_data": chart_data,
        "is_fallback": True,
    }


@router.get("/crypto")
async def get_crypto_analytics():
    """GET /api/analytics/crypto — wallets found, USDT traced, chains involved"""
    conn = None
    try:
        conn = await get_db_connection()
        query = """
            SELECT
                COUNT(DISTINCT wallet_address) as wallets_found,
                COALESCE(SUM(usdt_amount), 0) as usdt_traced,
                ARRAY_AGG(DISTINCT chain) as chains
            FROM crypto_tracing
        """
        row = await conn.fetchrow(query)
        if row and row["wallets_found"]:
            chains = row["chains"] or []
            return {
                "wallets_found": int(row["wallets_found"]),
                "usdt_traced": float(row["usdt_traced"]),
                "chains_involved": chains,
                "is_fallback": False,
            }
    except Exception as e:
        logger.warning(f"Database query failed for /crypto, using fallback: {e}")
    finally:
        if conn:
            await conn.close()

    labels = [item["chain"] for item in FALLBACK_CRYPTO["chain_breakdown"]]
    data = [item["usdt_amount"] for item in FALLBACK_CRYPTO["chain_breakdown"]]
    colors = ["#00b4d8", "#e94560", "#ffb703", "#f7931a", "#9945ff", "#8247e5"]
    chart_data = format_chartjs_pie(labels, data, label="USDT Traced by Chain", colors=colors)

    res = dict(FALLBACK_CRYPTO)
    res["chart_data"] = chart_data
    return res


# Create FastAPI App for standalone execution and dashboard serving
app = FastAPI(
    title="GFIN Analytics API & Dashboard",
    description="GFIN Global Fraud Intelligence Platform Analytics Service",
    version="1.0.0",
)

app.include_router(router)


@app.get("/analytics", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the HTML Analytics Dashboard."""
    html_file_path = "/app/conversations/6a8e022d12b12b3300f74d59/analytics_dashboard.html"
    if os.path.exists(html_file_path):
        with open(html_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>GFIN Analytics Dashboard file not found</h1>", status_code=404)

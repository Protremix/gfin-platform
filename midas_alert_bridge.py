#!/usr/bin/env python3
"""
GFIN MIDAS Anomaly Alert Bridge
Monitors MIDAS for high-score anomalies and creates GFIN alerts.
Runs as a background task within the GFIN server.
"""

import asyncio
import time
import json
import traceback
from datetime import datetime, timezone

MIDAS_ALERT_BRIDGE_INTERVAL = 60  # seconds
_last_anomaly_count = 0

async def midas_alert_bridge():
    """Background task: check MIDAS anomalies and create GFIN alerts."""
    global _last_anomaly_count
    
    # Wait for server to be fully initialized
    await asyncio.sleep(10)
    print("[MIDAS-BRIDGE] Starting bridge...", flush=True)
    
    from gfin_midas import midas_pipeline
    
    while True:
        try:
            # Get db_pool fresh each cycle from the running server
            import sys
            main_mod = sys.modules.get('__main__')
            db_pool = getattr(main_mod, 'db_pool', None) if main_mod else None
            
            if db_pool is None:
                print("[MIDAS-BRIDGE] db_pool is None, waiting...", flush=True)
                await asyncio.sleep(MIDAS_ALERT_BRIDGE_INTERVAL)
                continue
            
            stats = midas_pipeline.midas.get_stats()
            current_anomalies = stats.get("anomalies_detected", 0)
            recent = stats.get("top_anomalies", [])
            
            print(f"[MIDAS-BRIDGE] anomalies={current_anomalies}, last={_last_anomaly_count}, top={len(recent)}", flush=True)
            
            # Only process new anomalies since last check
            if current_anomalies > _last_anomaly_count:
                alerts_created = 0
                # Get the top recent anomalies and create alerts for high scores
                for anomaly in recent[:5]:
                    score = anomaly.get("score", 0)
                    if score < 5.0:
                        continue
                    
                    src = anomaly.get("src", "unknown")
                    dst = anomaly.get("dst", "unknown")
                    reason = anomaly.get("reason", "Statistical anomaly")
                    
                    alert_id = f"MIDAS-{int(time.time())}-{src[:8]}"
                    
                    try:
                        async with db_pool.acquire() as conn:
                            # Check if this anomaly was already alerted
                            existing = await conn.fetchval(
                                "SELECT id FROM alerts WHERE alert_id = $1",
                                alert_id
                            )
                            if existing:
                                continue
                            
                            await conn.execute("""
                                INSERT INTO alerts (alert_id, case_id, country, level, message, next_action, police_contact, delivery_status, routed_from, target)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                            """,
                                alert_id,
                                "MIDAS-AUTO",
                                "GLOBAL",
                                "HIGH" if score >= 10 else "MEDIUM",
                                f"MIDAS Graph Anomaly: {reason} (score={score:.1f}) src={src} dst={dst}",
                                "Review anomaly in AI Engines tab - MIDAS panel",
                                "INTERPOL (auto)",
                                "pending",
                                "MIDAS Real-time Detection",
                                f"{src} -> {dst}"
                            )
                            alerts_created += 1
                    except Exception as e:
                        print(f"[MIDAS-BRIDGE] DB error: {e}", flush=True)
                
                if alerts_created:
                    print(f"[MIDAS-BRIDGE] Created {alerts_created} alerts", flush=True)
                
                _last_anomaly_count = current_anomalies
        except Exception as e:
            print(f"[MIDAS-BRIDGE] Error: {e}", flush=True)
            traceback.print_exc()
        
        await asyncio.sleep(MIDAS_ALERT_BRIDGE_INTERVAL)

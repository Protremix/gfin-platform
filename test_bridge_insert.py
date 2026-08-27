#!/usr/bin/env python3
"""Test MIDAS bridge manually"""
import asyncio
import sys
sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

import asyncpg

async def test():
    from gfin_midas import midas_pipeline
    
    stats = midas_pipeline.midas.get_stats()
    print(f"Edges: {stats['edges_processed']}, Anomalies: {stats['anomalies_detected']}")
    print(f"Top anomalies: {len(stats.get('top_anomalies', []))}")
    
    if stats.get('top_anomalies'):
        a = stats['top_anomalies'][0]
        print(f"First anomaly: src={a.get('src')} dst={a.get('dst')} score={a.get('score')}")
        
        # Try the DB insert
        pool = await asyncpg.create_pool(
            host="localhost", port=5432,
            user="gfin", password="",
            database="gfin"
        )
        
        score = a.get('score', 0)
        src = a.get('src', 'unknown')
        dst = a.get('dst', 'unknown')
        reason = a.get('reason', 'Statistical anomaly')
        alert_id = f"MIDAS-TEST-{int(__import__('time').time())}-{src[:8]}"
        
        print(f"Attempting insert: {alert_id}")
        
        async with pool.acquire() as conn:
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
            print("INSERT SUCCESS!")
        
        await pool.close()
    else:
        print("No top anomalies found")

asyncio.run(test())

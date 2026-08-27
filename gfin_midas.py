#!/usr/bin/env python3
"""
GFIN MIDAS Integration — Real-time Graph Anomaly Detection
Uses the MIDAS algorithm (Microcluster-Based Anomaly Detection for Streaming Graphs)
to detect suspicious nodes and edges in real-time as intelligence flows in.

This is a pure-Python implementation of the MIDAS Normal Core algorithm,
based on Count-Min Sketch for streaming graph anomaly detection.
Reference: https://github.com/Stream-AD/MIDAS
"""

import numpy as np
import hashlib
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

class CountMinSketch:
    """Count-Min Sketch for frequency estimation in streaming data"""
    
    def __init__(self, width: int = 1024, depth: int = 4):
        self.width = width
        self.depth = depth
        self.table = np.zeros((depth, width), dtype=np.float64)
        self._seeds = np.random.randint(0, 2**31 - 1, size=depth)
    
    def _hash(self, key: str, seed: int) -> int:
        h = hashlib.md5(f"{seed}:{key}".encode()).hexdigest()
        return int(h[:8], 16) % self.width
    
    def add(self, key: str, count: float = 1.0):
        for d in range(self.depth):
            idx = self._hash(key, self._seeds[d])
            self.table[d][idx] += count
    
    def estimate(self, key: str) -> float:
        return min(self.table[d][self._hash(key, self._seeds[d])] for d in range(self.depth))
    
    def reset(self):
        self.table.fill(0.0)


class MIDASCore:
    """
    MIDAS Normal Core — Streaming graph anomaly detection.
    Tracks edge counts over time windows and flags anomalous edges/nodes.
    
    For each edge (src, dst, time_window):
    - Current count: how many times this edge appeared in the current time window
    - Total count: how many times it appeared historically
    - Anomaly score: ratio of current to historical frequency
    
    High scores indicate sudden bursts of activity (potential fraud signal).
    """
    
    def __init__(self, num_windows: int = 10, window_size: float = 60.0,
                 width: int = 1024, depth: int = 4, lambda_decay: float = 0.5):
        self.num_windows = num_windows
        self.window_size = window_size  # seconds per window
        self.lambda_ = lambda_decay  # decay factor for historical counts
        self.width = width
        self.depth = depth
        
        # Current window counts
        self.current_src = CountMinSketch(width, depth)
        self.current_dst = CountMinSketch(width, depth)
        self.current_edge = CountMinSketch(width, depth)
        
        # Historical (total) counts
        self.total_src = CountMinSketch(width, depth)
        self.total_dst = CountMinSketch(width, depth)
        self.total_edge = CountMinSketch(width, depth)
        
        # Current time window
        self.current_window = 0
        self.window_start_time = time.time()
        
        # Tracking
        self.edges_processed = 0
        self.anomalies_detected = 0
        self.high_score_edges = []  # Recent anomalies
    
    def _check_window(self, current_time: float):
        """Check if we need to advance the time window"""
        elapsed = current_time - self.window_start_time
        new_window = int(elapsed / self.window_size)
        
        if new_window > self.current_window:
            # Decay historical counts and add current window
            self.total_src.table = (self.total_src.table * self.lambda_) + self.current_src.table
            self.total_dst.table = (self.total_dst.table * self.lambda_) + self.current_dst.table
            self.total_edge.table = (self.total_edge.table * self.lambda_) + self.current_edge.table
            
            # Reset current window
            self.current_src.reset()
            self.current_dst.reset()
            self.current_edge.reset()
            
            self.current_window = new_window
    
    def add_edge(self, src: str, dst: str, timestamp: Optional[float] = None) -> Dict:
        """
        Process a new edge in the streaming graph.
        Returns anomaly score and metadata.
        
        Args:
            src: Source node identifier (e.g., wallet address, username)
            dst: Destination node identifier (e.g., domain, wallet)
            timestamp: Event timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = time.time()
        
        self._check_window(timestamp)
        
        edge_key = f"{src}->{dst}"
        
        # Increment current window counts
        self.current_src.add(src)
        self.current_dst.add(dst)
        self.current_edge.add(edge_key)
        
        # Get current and historical counts
        curr_src_count = self.current_src.estimate(src)
        curr_dst_count = self.current_dst.estimate(dst)
        curr_edge_count = self.current_edge.estimate(edge_key)
        
        total_src_count = self.total_src.estimate(src)
        total_dst_count = self.total_dst.estimate(dst)
        total_edge_count = self.total_edge.estimate(edge_key)
        
        # Compute anomaly scores (MIDAS formula)
        # Score = max(current / (sqrt(total) + 1), ...) — higher = more anomalous
        src_score = curr_src_count / (np.sqrt(total_src_count) + 1)
        dst_score = curr_dst_count / (np.sqrt(total_dst_count) + 1)
        edge_score = curr_edge_count / (np.sqrt(total_edge_count) + 1)
        
        # Combined score — take the max of the three
        combined_score = max(src_score, dst_score, edge_score)
        
        self.edges_processed += 1
        
        result = {
            "src": src,
            "dst": dst,
            "edge_key": edge_key,
            "current_edge_count": float(curr_edge_count),
            "total_edge_count": float(total_edge_count),
            "src_score": float(src_score),
            "dst_score": float(dst_score),
            "edge_score": float(edge_score),
            "combined_score": float(combined_score),
            "is_anomalous": combined_score > 3.0,  # Threshold
            "window": self.current_window
        }
        
        if combined_score > 3.0:
            self.anomalies_detected += 1
            self.high_score_edges.append({
                "src": src,
                "dst": dst,
                "score": float(combined_score),
                "timestamp": timestamp,
                "reason": self._explain_anomaly(result)
            })
            # Keep only recent 100 anomalies
            if len(self.high_score_edges) > 100:
                self.high_score_edges = self.high_score_edges[-100:]
        
        return result
    
    def _explain_anomaly(self, result: Dict) -> str:
        """Explain why this edge is anomalous"""
        reasons = []
        if result["src_score"] == result["combined_score"] and result["src_score"] > 3.0:
            reasons.append(f"Source node burst: {result['src']} appeared {int(result['current_edge_count'])}x this window")
        if result["dst_score"] == result["combined_score"] and result["dst_score"] > 3.0:
            reasons.append(f"Destination node burst: {result['dst']} received {int(result['current_edge_count'])}x this window")
        if result["edge_score"] == result["combined_score"] and result["edge_score"] > 3.0:
            reasons.append(f"Edge burst: {result['src']} → {result['dst']} appeared {int(result['current_edge_count'])}x this window")
        return "; ".join(reasons) if reasons else "Statistical anomaly in edge frequency"
    
    def get_stats(self) -> Dict:
        """Get MIDAS processing statistics"""
        return {
            "edges_processed": self.edges_processed,
            "anomalies_detected": self.anomalies_detected,
            "current_window": self.current_window,
            "window_size_seconds": self.window_size,
            "recent_anomalies": len(self.high_score_edges),
            "top_anomalies": sorted(
                self.high_score_edges[-20:], 
                key=lambda x: x["score"], reverse=True
            )[:10]
        }
    
    def reset(self):
        """Reset all counters"""
        self.current_src.reset()
        self.current_dst.reset()
        self.current_edge.reset()
        self.total_src.reset()
        self.total_dst.reset()
        self.total_edge.reset()
        self.edges_processed = 0
        self.anomalies_detected = 0
        self.high_score_edges = []
        self.current_window = 0
        self.window_start_time = time.time()


class GFINMIDASPipeline:
    """
    Integrates MIDAS into the GFIN intelligence pipeline.
    Streams intelligence events (domain detections, wallet mentions, entity correlations)
    through MIDAS for real-time anomaly detection.
    """
    
    def __init__(self):
        self.midas = MIDASCore(
            num_windows=10,
            window_size=3600,  # 1 hour windows
            width=2048,
            depth=6,
            lambda_decay=0.3  # Aggressive decay — recent activity matters more
        )
        self._running = False
    
    async def stream_telegram_intelligence(self, db_pool):
        """Process all telegram intelligence through MIDAS"""
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT group_name, wallets, domains, phones, ips, usernames,
                       scam_type, risk_level, created_at
                FROM telegram_intelligence
                ORDER BY created_at ASC
                LIMIT 5000
            """)
        
        processed = 0
        anomalies = 0
        import json as _json
        for row in rows:
            src = row["group_name"] or "unknown"
            ts = row["created_at"].timestamp() if row["created_at"] else None
            # Extract entities from text columns
            for field in ["wallets", "domains", "phones", "ips", "usernames"]:
                vals = row.get(field, "[]")
                if isinstance(vals, str):
                    try: vals = _json.loads(vals)
                    except: vals = [vals] if vals else []
                if not isinstance(vals, list): vals = [vals] if vals else []
                for v in vals:
                    if v:
                        result = self.midas.add_edge(src, str(v), timestamp=ts)
                        processed += 1
                        if result["is_anomalous"]:
                            anomalies += 1
            # Also add scam_type as edge
            if row.get("scam_type"):
                result = self.midas.add_edge(src, f"scam:{row['scam_type']}", timestamp=ts)
                processed += 1
                if result["is_anomalous"]:
                    anomalies += 1
        
        return {
            "processed": processed,
            "anomalies": anomalies,
            "anomaly_rate": anomalies / max(processed, 1),
            "stats": self.midas.get_stats()
        }
    
    async def stream_case_evidence(self, db_pool):
        """Process case evidence chains through MIDAS"""
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT case_id, target, evidence_chain, created_date
                FROM cases
                WHERE evidence_chain IS NOT NULL
                ORDER BY created_date ASC
            """)
        
        processed = 0
        anomalies = 0
        for row in rows:
            case_id = row["case_id"]
            target = row["target"]
            evidence = row["evidence_chain"]
            
            if isinstance(evidence, str):
                try:
                    evidence = json.loads(evidence)
                except:
                    evidence = []
            
            if isinstance(evidence, list):
                for step in evidence:
                    if isinstance(step, dict):
                        # Each evidence step is an edge: case → evidence_target
                        step_target = step.get("target", step.get("value", ""))
                        if step_target:
                            result = self.midas.add_edge(
                                case_id, str(step_target),
                                timestamp=row["created_date"].timestamp() if row["created_date"] else None
                            )
                            processed += 1
                            if result["is_anomalous"]:
                                anomalies += 1
            elif isinstance(evidence, dict):
                for key, val in evidence.items():
                    if isinstance(val, (str, int)):
                        result = self.midas.add_edge(
                            case_id, f"{key}:{val}",
                            timestamp=row["created_date"].timestamp() if row["created_date"] else None
                        )
                        processed += 1
                        if result["is_anomalous"]:
                            anomalies += 1
        
        return {
            "processed": processed,
            "anomalies": anomalies,
            "anomaly_rate": anomalies / max(processed, 1),
            "stats": self.midas.get_stats()
        }
    
    def get_status(self) -> Dict:
        """Get MIDAS pipeline status"""
        return {
            "running": self._running,
            "algorithm": "MIDAS Normal Core (Count-Min Sketch)",
            "window_size": "1 hour",
            "decay_factor": 0.3,
            "sketch_width": 2048,
            "sketch_depth": 6,
            "stats": self.midas.get_stats()
        }


# Singleton
midas_pipeline = GFINMIDASPipeline()

import json  # needed in stream_case_evidence

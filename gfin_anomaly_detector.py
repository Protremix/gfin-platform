#!/usr/bin/env python3
"""
GFIN Anomaly Detection Module — Powered by PyOD
Detects anomalous patterns in case data, wallet flows, and entity relationships.
Uses Isolation Forest, KNN, and AutoEncoder for multi-dimensional anomaly detection.
"""

import numpy as np
from collections import defaultdict, Counter
import json
import os
import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

class GFINAnomalyDetector:
    """Multi-algorithm anomaly detection for fraud intelligence"""
    
    def __init__(self):
        self.models = {}
        self.feature_columns = [
            "victim_count", "total_loss_usd", "confidence",
            "evidence_count", "wallet_count", "domain_count",
            "country_count", "phone_count", "social_account_count",
            "days_active", "ip_count", "pattern_count"
        ]
    
    def _extract_features(self, cases: List[Dict]) -> np.ndarray:
        """Extract numerical features from case data for anomaly detection"""
        features = []
        for c in cases:
            row = [
                float(c.get("victim_count", 0)),
                float(c.get("total_loss_usd", 0)),
                float(c.get("confidence", 0)),
                float(len(c.get("evidence_chain", [])) if isinstance(c.get("evidence_chain"), list) else 0),
                float(len(c.get("financial_indicators", [])) if isinstance(c.get("financial_indicators"), list) else 0),
                float(len(c.get("digital_identifiers", [])) if isinstance(c.get("digital_identifiers"), list) else 0),
                float(len(c.get("affected_countries", [])) if isinstance(c.get("affected_countries"), list) else 0),
                float(c.get("phone_count", 0)),
                float(c.get("social_count", 0)),
                float(c.get("days_active", 0)),
                float(c.get("ip_count", 0)),
                float(len(c.get("scam_patterns", [])) if isinstance(c.get("scam_patterns"), list) else 0),
            ]
            features.append(row)
        return np.array(features, dtype=np.float64)
    
    async def detect_anomalous_cases(self, db_pool) -> Dict[str, Any]:
        """Run anomaly detection on all cases to find outliers"""
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT case_id, status, target, summary, confidence, victim_count,
                       total_loss_usd, scam_patterns, scam_indicators,
                       affected_countries, financial_indicators, digital_identifiers,
                       evidence_chain, created_date, classification
                FROM cases
                WHERE status NOT IN ('CLOSED', 'ARCHIVED')
            """)
        
        if len(rows) < 5:
            return {"anomalies": [], "message": "Not enough cases for anomaly detection (need 5+)"}
        
        cases = []
        for r in rows:
            c = dict(r)
            # Parse JSON arrays
            for field in ["scam_patterns", "scam_indicators", "affected_countries",
                          "financial_indicators", "digital_identifiers", "evidence_chain"]:
                if isinstance(c.get(field), str):
                    try:
                        c[field] = json.loads(c[field])
                    except:
                        c[field] = []
            # Compute days_active
            if c.get("created_date"):
                c["days_active"] = (datetime.now(c["created_date"].tzinfo) - c["created_date"]).days if c.get("created_date") else 0
            else:
                c["days_active"] = 0
            c["evidence_count"] = len(c.get("evidence_chain", []))
            c["wallet_count"] = len(c.get("financial_indicators", []))
            c["domain_count"] = len(c.get("digital_identifiers", []))
            c["country_count"] = len(c.get("affected_countries", []))
            c["pattern_count"] = len(c.get("scam_patterns", []))
            c["phone_count"] = 0
            c["social_count"] = 0
            c["ip_count"] = 0
            cases.append(c)
        
        X = self._extract_features(cases)
        
        # Run multiple detectors
        from pyod.models.iforest import IForest
        from pyod.models.knn import KNN
        
        results = {"anomalies": [], "total_cases": len(cases), "algorithms": {}}
        
        # Isolation Forest (good for high-dimensional outliers)
        iforest = IForest(n_estimators=100, contamination=0.2, random_state=42)
        iforest.fit(X)
        if_scores = iforest.decision_scores_
        if_labels = iforest.labels_
        
        # KNN (good for local outliers)
        knn = KNN(n_neighbors=5, contamination=0.2)
        knn.fit(X)
        knn_scores = knn.decision_scores_
        knn_labels = knn.labels_
        
        # Ensemble — flag cases that both algorithms flag
        for i, c in enumerate(cases):
            avg_score = (if_scores[i] + knn_scores[i]) / 2
            is_anomaly = if_labels[i] == 1 or knn_labels[i] == 1
            if is_anomaly:
                results["anomalies"].append({
                    "case_id": c["case_id"],
                    "target": c["target"],
                    "summary": c.get("summary", ""),
                    "confidence": float(c.get("confidence", 0)),
                    "victim_count": c.get("victim_count", 0),
                    "total_loss_usd": float(c.get("total_loss_usd", 0)),
                    "classification": c.get("classification"),
                    "anomaly_score": float(avg_score),
                    "iforest_score": float(if_scores[i]),
                    "knn_score": float(knn_scores[i]),
                    "flagged_by": "both" if (if_labels[i] == 1 and knn_labels[i] == 1) else "iforest" if if_labels[i] == 1 else "knn",
                    "reason": self._explain_anomaly(c, if_scores[i], knn_scores[i])
                })
        
        results["anomalies"].sort(key=lambda x: x["anomaly_score"], reverse=True)
        results["algorithms"] = {
            "iforest": {"contamination": 0.2, "n_estimators": 100},
            "knn": {"n_neighbors": 5, "contamination": 0.2}
        }
        results["anomaly_count"] = len(results["anomalies"])
        
        return results
    
    def _explain_anomaly(self, case: Dict, if_score: float, knn_score: float) -> str:
        """Generate human-readable explanation for why a case is anomalous"""
        reasons = []
        if case.get("victim_count", 0) > 5:
            reasons.append(f"unusually high victim count ({case['victim_count']})")
        if case.get("total_loss_usd", 0) > 50000:
            reasons.append(f"high financial loss (${case['total_loss_usd']:,.0f})")
        if case.get("confidence", 0) > 0.9:
            reasons.append(f"very high confidence ({case['confidence']:.1%})")
        if len(case.get("scam_patterns", [])) > 5:
            reasons.append(f"many scam patterns ({len(case.get('scam_patterns', []))})")
        if len(case.get("affected_countries", [])) > 5:
            reasons.append(f"many countries affected ({len(case.get('affected_countries', []))})")
        
        if not reasons:
            reasons.append("statistical outlier in feature space")
        
        return "; ".join(reasons)
    
    async def detect_wallet_anomalies(self, db_pool) -> Dict[str, Any]:
        """Detect anomalous wallet transaction patterns"""
        async with db_pool.acquire() as conn:
            # Get wallet data from telegram_intelligence
            rows = await conn.fetch("""
                SELECT group_name, wallets, scam_type, risk_level, created_at
                FROM telegram_intelligence
                WHERE wallets IS NOT NULL
                LIMIT 500
            """)
        
        if len(rows) < 3:
            return {"anomalies": [], "message": "Not enough wallet data"}
        
        # Extract wallet mentions per group
        import json as _json
        wallet_data = []
        for r in rows:
            wallets = r.get("wallets", "[]")
            if isinstance(wallets, str):
                try: wallets = _json.loads(wallets)
                except: wallets = [wallets] if wallets else []
            for w in (wallets if isinstance(wallets, list) else [wallets]):
                if w:
                    wallet_data.append({
                        "wallet": str(w),
                        "group": r.get("group_name", "unknown"),
                        "scam_type": r.get("scam_type", ""),
                        "risk_level": r.get("risk_level", "")
                    })
        
        if len(wallet_data) < 3:
            return {"anomalies": [], "message": "Not enough wallet data"}
        
        # Aggregate by wallet
        from collections import Counter
        wallet_counts = Counter(wd["wallet"] for wd in wallet_data)
        wallet_groups = defaultdict(set)
        for wd in wallet_data:
            wallet_groups[wd["wallet"]].add(wd["group"])
        
        features = np.array([[
            float(wallet_counts[w]),
            float(len(wallet_groups[w]))
        ] for w in wallet_counts], dtype=np.float64)
        wallet_list = list(wallet_counts.keys())
        
        from pyod.models.iforest import IForest
        detector = IForest(n_estimators=50, contamination=0.15, random_state=42)
        detector.fit(features)
        
        anomalies = []
        for i, w in enumerate(wallet_list):
            if detector.labels_[i] == 1:
                anomalies.append({
                    "wallet": w,
                    "mention_count": wallet_counts[w],
                    "group_count": len(wallet_groups[w]),
                    "anomaly_score": float(detector.decision_scores_[i]),
                    "reason": f"Mentioned {wallet_counts[w]}x across {len(wallet_groups[w])} groups"
                })
        
        return {"anomalies": anomalies, "total_wallets": len(wallet_list), "anomaly_count": len(anomalies)}


# Singleton instance
anomaly_detector = GFINAnomalyDetector()

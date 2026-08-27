"""
GFIN Shared Investigation Store
Used by both gfin_server.py (auto-investigation) and module_routes_batch3.py (API routes)
to share in-memory investigation state.
"""
import time
from typing import Any


class InvestigationStore:
    """Thread-safe in-memory store for investigations (Layer A — MVP)."""
    _instance = None
    _investigations: dict = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create(self, investigation_id: str, case_id: str, subject: str, 
               subject_type: str, operator: str = "GFIN_AUTO") -> dict:
        """Create a new investigation record."""
        record = {
            "id": investigation_id,
            "case_id": case_id,
            "subject": subject,
            "subject_type": subject_type,
            "status": "active",
            "steps": [],
            "evidence": [],
            "claims": [],
            "created_at": time.time(),
            "operator": operator,
            "plan": {
                "id": investigation_id,
                "target": subject,
                "objective": f"Investigate {subject_type}: {subject} for case {case_id}"
            }
        }
        self._investigations[investigation_id] = record
        return record

    def get(self, investigation_id: str) -> dict | None:
        return self._investigations.get(investigation_id)

    def list(self, limit: int = 20) -> list:
        return list(self._investigations.values())[:limit]

    def add_step(self, investigation_id: str, step_name: str, tool_name: str, 
                 params: dict = None, status: str = "completed", result: str = "") -> dict:
        inv = self._investigations.get(investigation_id)
        if not inv:
            return {}
        step = {
            "step_id": f"STEP-{len(inv['steps'])+1}",
            "name": step_name,
            "tool": tool_name,
            "params": params or {},
            "status": status,
            "result": result,
            "created_at": time.time()
        }
        inv["steps"].append(step)
        return step

    def add_evidence(self, investigation_id: str, evidence_type: str, 
                     finding: str, source: str = "GFIN_AUTO", confidence: str = "HIGH") -> dict:
        inv = self._investigations.get(investigation_id)
        if not inv:
            return {}
        evidence = {
            "evidence_id": f"E-{len(inv['evidence'])+1:03d}",
            "type": evidence_type,
            "finding": finding,
            "source": source,
            "confidence": confidence,
            "timestamp": time.time()
        }
        inv["evidence"].append(evidence)
        return evidence

    def count(self) -> int:
        return len(self._investigations)


# Singleton
investigation_store = InvestigationStore.get_instance()

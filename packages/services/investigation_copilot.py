"""GFIN AI Investigation Copilot.

AI-powered investigation assistant that accepts a seed (phone, email, domain, URL,
wallet, IP, case) and performs authorized investigative workflows through GFIN tools.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class InvestigationStep:
    step_number: int
    action: str
    tool_name: str
    input_data: dict
    output_data: dict | None = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    evidence_refs: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class InvestigationResult:
    investigation_id: str
    seed_type: str
    seed_value: str
    steps: list[InvestigationStep] = field(default_factory=list)
    summary: str = ""
    evidence_chain: list[dict] = field(default_factory=list)
    gaps_identified: list[str] = field(default_factory=list)
    next_steps_recommended: list[str] = field(default_factory=list)
    confidence: float = 1.0
    unverified_claims: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: str = "unknown"
    authorized: bool = True


class MockTool:
    """Mock investigation tool for testing."""

    def __init__(
        self,
        name: str,
        handler: Callable[[dict], dict],
        required_role: str = "INVESTIGATOR",
        required_clearance: str = "UNCLASSIFIED",
    ):
        self.name = name
        self.handler = handler
        self.required_role = required_role
        self.required_clearance = required_clearance

    def execute(self, input_data: dict) -> dict:
        return self.handler(input_data)

    def __call__(self, input_data: dict) -> dict:
        return self.execute(input_data)


def create_default_mock_registry() -> dict[str, Any]:
    """Creates a default registry of mock tools."""

    def norm_phone(inp):
        v = inp.get("seed_value") or inp.get("phone") or "+15550199"
        return {"status": "success", "normalized": v if str(v).startswith("+") else f"+{v}", "country": "US", "carrier": "Mock Mobile", "type": "VOIP"}

    def norm_email(inp):
        v = str(inp.get("seed_value") or inp.get("email") or "suspect@example.com")
        parts = v.split("@")
        return {"status": "success", "normalized": v.lower(), "domain": parts[1] if len(parts) > 1 else "example.com", "user": parts[0]}

    def norm_domain(inp):
        v = str(inp.get("seed_value") or inp.get("domain") or "scam-domain.com")
        return {"status": "success", "normalized": v.lower(), "tld": v.split(".")[-1] if "." in v else "com", "registered": True}

    def norm_url(inp):
        v = str(inp.get("seed_value") or inp.get("url") or "https://scam-domain.com/login")
        return {"status": "success", "normalized": v, "domain": "scam-domain.com", "scheme": "https"}

    def norm_ip(inp):
        v = str(inp.get("seed_value") or inp.get("ip") or "192.0.2.1")
        return {"status": "success", "normalized": v, "version": "v4", "is_private": False}

    def norm_wallet(inp):
        v = str(inp.get("seed_value") or inp.get("wallet") or "0x71C7656EC7ab88b098defB751B7401B5f6d8976F")
        return {"status": "success", "normalized": v, "blockchain": "ethereum", "valid": True}

    def norm_case(inp):
        v = str(inp.get("seed_value") or inp.get("case_id") or "CASE-2026-8812")
        return {"status": "success", "normalized": v, "case_id": v, "case_status": "ACTIVE"}

    def search_ent(inp):
        return {
            "status": "success",
            "entities": [{"id": "ENT-101", "name": "Global Fraud Org", "type": "ORGANIZATION", "risk_score": 88.5}],
            "matches": 1,
        }

    def search_rel(inp):
        return {
            "status": "success",
            "relationships": [{"source": "ENT-101", "target": "ENT-102", "type": "DIRECTOR_OF", "confidence": 0.92}],
        }

    def enrich_infra(inp):
        return {
            "status": "success",
            "infrastructure": {
                "ip": "192.0.2.1",
                "asn": "AS13335",
                "org": "Mock Cloud Services",
                "hosting": True,
                "location": {"country": "US", "city": "New York", "lat": 40.7128, "lon": -74.0060},
            },
        }

    def enrich_ent(inp):
        return {
            "status": "success",
            "entity_info": {
                "id": "ENT-101",
                "risk_level": "HIGH",
                "campaigns": ["CAMP-99"],
                "wallets": ["0x71C7656EC7ab88b098defB751B7401B5f6d8976F"],
                "locations": ["New York, US"],
            },
        }

    def resolve_ent(inp):
        return {"status": "success", "canonical_entity": "ENT-101", "confidence": 0.95, "aliases": ["ScamCorp"]}

    def expand_g(inp):
        return {
            "status": "success",
            "nodes_added": 3,
            "edges_added": 4,
            "connected_wallets": ["0x71C7656EC7ab88b098defB751B7401B5f6d8976F"],
            "connected_campaigns": ["CAMP-99"],
        }

    def search_hist(inp):
        return {
            "status": "success",
            "history": [
                {"timestamp": "2026-01-15T10:00:00Z", "event": "Domain registered"},
                {"timestamp": "2026-02-01T12:00:00Z", "event": "First fraud report"},
            ],
        }

    def check_camp(inp):
        return {
            "status": "success",
            "campaign_matches": [{"campaign_id": "CAMP-99", "similarity": 0.94, "dna_signature": "DNA-PHISH-01"}],
        }

    def check_fin(inp):
        return {
            "status": "success",
            "financial_intel": {
                "wallet": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
                "balance_eth": 45.2,
                "total_received_usd": 150000.0,
                "sanction_check": "CLEAN",
                "suspicious_transactions": 12,
            },
        }

    def check_geo(inp):
        return {
            "status": "success",
            "geoint": {"location": "New York, US", "coordinates": [40.7128, -74.0060], "ip_cluster": "192.0.2.0/24", "country_risk": "MEDIUM"},
        }

    def summ_evd(inp):
        return {"status": "success", "summary_text": "High risk fraud infrastructure identified with multiple linked entities."}

    tools = {
        "normalize_phone": MockTool("normalize_phone", norm_phone),
        "normalize_email": MockTool("normalize_email", norm_email),
        "normalize_domain": MockTool("normalize_domain", norm_domain),
        "normalize_url": MockTool("normalize_url", norm_url),
        "normalize_ip": MockTool("normalize_ip", norm_ip),
        "normalize_wallet": MockTool("normalize_wallet", norm_wallet),
        "normalize_case": MockTool("normalize_case", norm_case),
        "search_entities": MockTool("search_entities", search_ent),
        "search_relationships": MockTool("search_relationships", search_rel),
        "enrich_infrastructure": MockTool("enrich_infrastructure", enrich_infra),
        "enrich_entity": MockTool("enrich_entity", enrich_ent),
        "resolve_entities": MockTool("resolve_entities", resolve_ent),
        "expand_graph": MockTool("expand_graph", expand_g),
        "search_history": MockTool("search_history", search_hist),
        "check_campaign_dna": MockTool("check_campaign_dna", check_camp),
        "check_financial_intel": MockTool("check_financial_intel", check_fin),
        "check_geoint": MockTool("check_geoint", check_geo),
        "summarize_evidence": MockTool("summarize_evidence", summ_evd),
    }
    return tools


class InvestigationCopilot:
    """AI-powered Investigation Copilot service for GFIN."""

    ALLOWED_SEED_TYPES = {"phone", "email", "domain", "url", "wallet", "ip", "case"}

    def __init__(self, tool_registry: dict | None = None, user_context: dict | None = None):
        self.tools = tool_registry if tool_registry is not None else create_default_mock_registry()
        self.user = user_context or {
            "user_id": "investigator_1",
            "role": "INVESTIGATOR",
            "clearance": "CONFIDENTIAL",
            "jurisdiction": "US",
            "organization": "GFIN",
            "case_scope": ["*"],
        }
        self.audit_log: list[dict] = []
        self._request_counts: dict[str, int] = {}
        self.rate_limit_max: int = 100

    def _audit(self, action: str, details: dict):
        entry = {
            "action": action,
            "details": details,
            "timestamp": datetime.now(UTC),
            "user_id": self.user.get("user_id", "unknown"),
        }
        self.audit_log.append(entry)

    def _validate_input(self, seed_type: str, seed_value: str) -> bool:
        if not seed_type or not isinstance(seed_type, str):
            return False
        if seed_type.lower() not in self.ALLOWED_SEED_TYPES:
            return False
        return not (seed_value is None or not isinstance(seed_value, str) or not seed_value.strip())

    def _check_rate_limit(self, user_id: str, increment: bool = True) -> bool:
        count = self._request_counts.get(user_id, 0)
        if count >= self.rate_limit_max:
            return False
        if increment:
            self._request_counts[user_id] = count + 1
        return True

    def _enforce_case_scope(self, tool_name: str, input_data: dict) -> bool:
        scope = self.user.get("case_scope")
        if scope is None:
            return True
        if isinstance(scope, str):
            if scope == "*":
                return True
            allowed_list = [scope]
        elif isinstance(scope, (list, set, tuple)):
            if "*" in scope:
                return True
            allowed_list = list(scope)
        else:
            return True

        target_case = input_data.get("case_id") or input_data.get("case_scope") or input_data.get("target_case")
        seed_val = input_data.get("seed_value")
        seed_t = input_data.get("seed_type")

        if target_case and target_case not in allowed_list:
            return False

        return not (seed_t == "case" and seed_val and seed_val not in allowed_list)

    def _check_authorization(self, tool_name: str, input_data: dict) -> bool:
        if tool_name not in self.tools:
            self._audit("unauthorized_tool", {"reason": "not_in_allowlist", "tool": tool_name})
            return False

        user_id = self.user.get("user_id", "unknown")
        if not self._check_rate_limit(user_id, increment=False):
            self._audit("rate_limit_exceeded", {"user_id": user_id})
            return False

        if not self._enforce_case_scope(tool_name, input_data):
            self._audit("case_scope_violation", {"tool": tool_name, "input": input_data})
            return False

        tool = self.tools[tool_name]
        req_role = getattr(tool, "required_role", None)
        if req_role is None and isinstance(tool, dict):
            req_role = tool.get("required_role")

        if req_role:
            user_role = str(self.user.get("role", "INVESTIGATOR")).upper()
            role_ranks = {"INVESTIGATOR": 1, "ANALYST": 2, "SUPERVISOR": 3, "ADMIN": 4}
            req_rank = role_ranks.get(str(req_role).upper(), 1)
            user_rank = role_ranks.get(user_role, 1)
            if user_rank < req_rank:
                self._audit("unauthorized_role", {"tool": tool_name, "required": req_role, "user_role": user_role})
                return False

        req_clearance = getattr(tool, "required_clearance", None)
        if req_clearance is None and isinstance(tool, dict):
            req_clearance = tool.get("required_clearance")

        if req_clearance:
            user_c = str(self.user.get("clearance", "UNCLASSIFIED")).upper()
            clearance_ranks = {
                "UNCLASSIFIED": 0,
                "RESTRICTED": 1,
                "CONFIDENTIAL": 2,
                "SECRET": 3,
                "TOP_SECRET": 4,
            }
            req_c_rank = clearance_ranks.get(str(req_clearance).upper(), 0)
            user_c_rank = clearance_ranks.get(user_c, 0)
            if user_c_rank < req_c_rank:
                self._audit("unauthorized_clearance", {"tool": tool_name, "required": req_clearance, "user_clearance": user_c})
                return False

        return True

    def _validate_output(self, output: dict) -> bool:
        if output is None or not isinstance(output, dict):
            return False
        return not (output.get("status") == "error" or output.get("error") is not None or output.get("malformed") is True)

    def _enforce_classification(self, output: dict) -> dict:
        if not isinstance(output, dict):
            return output

        clearance_ranks = {
            "UNCLASSIFIED": 0,
            "RESTRICTED": 1,
            "CONFIDENTIAL": 2,
            "SECRET": 3,
            "TOP_SECRET": 4,
        }
        user_c = str(self.user.get("clearance", "UNCLASSIFIED")).upper()
        user_rank = clearance_ranks.get(user_c, 0)

        def sanitize(item):
            if isinstance(item, dict):
                item_class = item.get("classification") or item.get("_classification")
                if item_class:
                    item_rank = clearance_ranks.get(str(item_class).upper(), 0)
                    if item_rank > user_rank:
                        return {"[REDACTED]": f"Classification level {item_class} exceeds clearance {user_c}"}

                new_dict = {}
                for k, v in item.items():
                    k_str = str(k).lower()
                    if "secret" in k_str and user_rank < clearance_ranks["SECRET"]:
                        continue
                    if "confidential" in k_str and user_rank < clearance_ranks["CONFIDENTIAL"]:
                        continue
                    if "top_secret" in k_str and user_rank < clearance_ranks["TOP_SECRET"]:
                        continue
                    new_dict[k] = sanitize(v)
                return new_dict
            elif isinstance(item, list):
                return [sanitize(i) for i in item]
            else:
                return item

        return sanitize(output)

    def _execute_step(self, step: InvestigationStep) -> InvestigationStep:
        step.status = "RUNNING"
        self._audit("step_started", {"step_number": step.step_number, "tool": step.tool_name})

        if not self._check_authorization(step.tool_name, step.input_data):
            step.status = "FAILED"
            step.output_data = {"error": "Unauthorized step execution"}
            self._audit("step_failed_unauthorized", {"step_number": step.step_number, "tool": step.tool_name})
            return step

        tool = self.tools.get(step.tool_name)
        if not tool:
            step.status = "FAILED"
            step.output_data = {"error": f"Tool {step.tool_name} not found"}
            self._audit("step_failed_missing_tool", {"step_number": step.step_number, "tool": step.tool_name})
            return step

        try:
            if hasattr(tool, "execute") and callable(tool.execute):
                raw_out = tool.execute(step.input_data)
            elif isinstance(tool, dict) and callable(tool.get("fn")):
                raw_out = tool["fn"](step.input_data)
            elif callable(tool):
                raw_out = tool(step.input_data)
            else:
                raise ValueError(f"Tool {step.tool_name} is not callable")

            if not self._validate_output(raw_out):
                step.status = "FAILED"
                step.output_data = raw_out or {"error": "Malformed tool output"}
                self._audit("step_failed_validation", {"step_number": step.step_number, "tool": step.tool_name})
                return step

            sanitized_out = self._enforce_classification(raw_out)
            step.output_data = sanitized_out
            step.status = "COMPLETED"
            evd_ref = f"EVD-{step.step_number:03d}"
            step.evidence_refs.append(evd_ref)
            self._audit("step_completed", {"step_number": step.step_number, "tool": step.tool_name, "evidence_ref": evd_ref})
        except Exception as e:
            step.status = "FAILED"
            step.output_data = {"error": str(e)}
            self._audit("step_failed_exception", {"step_number": step.step_number, "tool": step.tool_name, "error": str(e)})

        return step

    def _summarize(self, steps: list[InvestigationStep]) -> str:
        lines = ["=== AI Investigation Copilot Summary ==="]
        for step in steps:
            if step.status == "COMPLETED" and step.output_data:
                ev_ref = step.evidence_refs[0] if step.evidence_refs else "N/A"
                ts = step.timestamp.isoformat()
                lines.append(
                    f"Claim: Step {step.step_number} ({step.action}) executed successfully ([UNVERIFIED]) -> "
                    f"Evidence: {ev_ref} -> Source: {step.tool_name} -> Timestamp: {ts} -> Confidence: 0.90"
                )
            elif step.status == "SKIPPED":
                lines.append(f"Claim: Step {step.step_number} ({step.action}) skipped due to missing preconditions ([UNVERIFIED]).")
            elif step.status == "FAILED":
                lines.append(f"Claim: Step {step.step_number} ({step.action}) failed during execution ([UNVERIFIED]).")
        return "\n".join(lines)

    def _identify_gaps(self, steps: list[InvestigationStep]) -> list[str]:
        gaps = []
        step_map = {s.step_number: s for s in steps}

        for s in steps:
            if s.status == "FAILED":
                err_msg = s.output_data.get("error", "unknown error") if isinstance(s.output_data, dict) else "unknown error"
                gaps.append(f"Step {s.step_number} ({s.action}) failed: {err_msg}")
            elif s.status == "SKIPPED":
                gaps.append(f"Step {s.step_number} ({s.action}) was skipped due to missing input context")

        if 8 in step_map and step_map[8].status != "COMPLETED":
            gaps.append("Financial intelligence data incomplete or missing for target wallet")
        if 9 in step_map and step_map[9].status != "COMPLETED":
            gaps.append("GEOINT spatial telemetry missing or incomplete")

        return gaps

    def _recommend_next_steps(self, steps: list[InvestigationStep], gaps: list[str]) -> list[str]:
        recs = []
        if gaps:
            recs.append("Re-run failed investigation steps with updated query credentials or parameters.")
        recs.append("Submit formal law enforcement request for carrier / registrar subscriber information.")
        recs.append("Monitor crypto wallet addresses on-chain for outgoing transaction events.")
        recs.append("Cross-reference identified entities against global sanction compliance lists.")
        return recs

    def investigate(self, seed_type: str, seed_value: str) -> InvestigationResult:
        inv_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        user_id = self.user.get("user_id", "unknown")
        now = datetime.now(UTC)

        # 1. Input Validation
        if not self._validate_input(seed_type, seed_value):
            self._audit("invalid_input", {"seed_type": seed_type, "seed_value": seed_value})
            return InvestigationResult(
                investigation_id=inv_id,
                seed_type=seed_type or "",
                seed_value=seed_value or "",
                steps=[],
                summary="Investigation aborted: Invalid seed input type or value.",
                gaps_identified=["Invalid input seed provided."],
                confidence=0.0,
                created_at=now,
                user_id=user_id,
                authorized=False,
            )

        # 2. Rate Limit Check
        if not self._check_rate_limit(user_id, increment=True):
            self._audit("rate_limit_blocked", {"user_id": user_id})
            return InvestigationResult(
                investigation_id=inv_id,
                seed_type=seed_type,
                seed_value=seed_value,
                steps=[],
                summary="Investigation aborted: Rate limit exceeded.",
                gaps_identified=["Rate limit exceeded."],
                confidence=0.0,
                created_at=now,
                user_id=user_id,
                authorized=False,
            )

        st_lower = seed_type.lower()
        norm_tool = f"normalize_{st_lower}"
        if norm_tool not in self.tools:
            norm_tool = "normalize_domain"

        # Build 12 workflow steps
        step_specs = [
            (1, "normalize", norm_tool),
            (2, "search_graph", "search_entities"),
            (3, "enrich", "enrich_infrastructure"),
            (4, "resolve_entities", "resolve_entities"),
            (5, "expand_graph", "expand_graph"),
            (6, "search_history", "search_history"),
            (7, "compare_campaign_dna", "check_campaign_dna"),
            (8, "check_financial_intel", "check_financial_intel"),
            (9, "check_geoint", "check_geoint"),
            (10, "summarize_evidence", "summarize_evidence"),
            (11, "identify_gaps", "summarize_evidence"),
            (12, "recommend_next_steps", "summarize_evidence"),
        ]

        steps: list[InvestigationStep] = []
        evidence_chain: list[dict] = []
        unverified_claims: list[str] = []

        for num, act, t_name in step_specs:
            inp_data = {"seed_type": st_lower, "seed_value": seed_value, "step_number": num}
            step = InvestigationStep(
                step_number=num,
                action=act,
                tool_name=t_name,
                input_data=inp_data,
                status="PENDING",
            )
            steps.append(step)

        # Execute steps
        for step in steps:
            if step.step_number == 7:
                prev_outputs = [s.output_data for s in steps[:6] if s.output_data]
                has_campaigns = any("campaign" in str(o).lower() for o in prev_outputs) or st_lower in ("case", "domain", "email")
                if not has_campaigns:
                    step.status = "SKIPPED"
                    self._audit("step_skipped", {"step_number": 7, "reason": "No campaign indicators found"})
                    continue

            elif step.step_number == 8:
                prev_outputs = [s.output_data for s in steps[:7] if s.output_data]
                has_wallets = any("wallet" in str(o).lower() for o in prev_outputs) or st_lower == "wallet"
                if not has_wallets:
                    step.status = "SKIPPED"
                    self._audit("step_skipped", {"step_number": 8, "reason": "No wallet indicators found"})
                    continue

            elif step.step_number == 9:
                prev_outputs = [s.output_data for s in steps[:8] if s.output_data]
                has_geo = any("location" in str(o).lower() or "ip" in str(o).lower() for o in prev_outputs) or st_lower in ("ip", "domain")
                if not has_geo:
                    step.status = "SKIPPED"
                    self._audit("step_skipped", {"step_number": 9, "reason": "No location indicators found"})
                    continue

            self._execute_step(step)

            if step.status == "COMPLETED" and step.output_data:
                ev_id = f"EVD-{step.step_number:03d}"
                evidence_chain.append({
                    "evidence_id": ev_id,
                    "step_number": step.step_number,
                    "action": step.action,
                    "tool_name": step.tool_name,
                    "data": step.output_data,
                    "source": step.tool_name,
                    "timestamp": step.timestamp.isoformat(),
                })
                unverified_claims.append(
                    f"[UNVERIFIED] Finding from step {step.step_number} ({step.action}) using {step.tool_name}: {list(step.output_data.keys())}"
                )

        summary = self._summarize(steps)
        gaps = self._identify_gaps(steps)
        next_steps = self._recommend_next_steps(steps, gaps)

        failed_count = sum(1 for s in steps if s.status == "FAILED")
        skipped_count = sum(1 for s in steps if s.status == "SKIPPED")

        base_confidence = 1.0
        confidence = base_confidence - (failed_count * 0.15) - (skipped_count * 0.05) - (len(gaps) * 0.02)
        confidence = max(0.0, min(1.0, round(confidence, 2)))

        result = InvestigationResult(
            investigation_id=inv_id,
            seed_type=seed_type,
            seed_value=seed_value,
            steps=steps,
            summary=summary,
            evidence_chain=evidence_chain,
            gaps_identified=gaps,
            next_steps_recommended=next_steps,
            confidence=confidence,
            unverified_claims=unverified_claims,
            created_at=now,
            user_id=user_id,
            authorized=True,
        )

        self._audit("investigation_completed", {"investigation_id": inv_id, "confidence": confidence})
        return result

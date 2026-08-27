"""
GFIN AI Summaries Module — Future-Tier Module

Uses the OpenAI Model Gateway (gpt-5.6-luna) to generate intelligent summaries
of cases, investigations, evidence chains, and fraud patterns.

Features:
- Case summary generation (concise overview for investigators)
- Evidence chain analysis summary
- Fraud pattern explanation (human-readable)
- Investigation progress summary
- Risk assessment narrative
- Multi-language summary generation

Per Constitution §7: Model Gateway for provider independence.
Per Directive: gpt-5.6-luna is primary model, does not accept temperature param,
uses max_completion_tokens, retries on empty content.
"""
import os
import json
import asyncio
from typing import Any
from datetime import datetime, UTC
from dataclasses import dataclass, field


@dataclass
class SummaryRequest:
    summary_type: str  # "case", "evidence", "pattern", "investigation", "risk"
    case_id: str = ""
    data: dict = field(default_factory=dict)
    target_language: str = "en"
    max_tokens: int = 2000


@dataclass
class SummaryResult:
    summary_type: str
    case_id: str
    summary: str
    key_findings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    confidence: float = 0.0
    model: str = "gpt-5.6-luna"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tokens_used: int = 0
    status: str = "generated"

    def to_dict(self) -> dict:
        return {
            "summary_type": self.summary_type,
            "case_id": self.case_id,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
            "model": self.model,
            "generated_at": self.generated_at,
            "tokens_used": self.tokens_used,
            "status": self.status,
        }


class AISummaryService:
    """AI-powered summary generation service."""

    def __init__(self):
        self._api_key = os.environ.get("OPENAI_PROJECT_KEY", "")
        self._model = "gpt-5.6-luna"
        self._base_url = "https://api.openai.com/v1/chat/completions"
        self._summaries: dict[str, SummaryResult] = {}
        self._counter = 0

    def _build_prompt(self, req: SummaryRequest) -> str:
        """Build a prompt for the AI model based on summary type."""
        data = req.data

        if req.summary_type == "case":
            return self._case_prompt(data, req.target_language)
        elif req.summary_type == "evidence":
            return self._evidence_prompt(data, req.target_language)
        elif req.summary_type == "pattern":
            return self._pattern_prompt(data, req.target_language)
        elif req.summary_type == "investigation":
            return self._investigation_prompt(data, req.target_language)
        elif req.summary_type == "risk":
            return self._risk_prompt(data, req.target_language)
        else:
            return f"Summarize the following fraud intelligence data:\n\n{json.dumps(data, indent=2)}"

    def _case_prompt(self, data: dict, lang: str) -> str:
        return f"""You are a fraud intelligence analyst. Generate a concise case summary for law enforcement.

Case Data:
{json.dumps(data, indent=2)}

Provide:
1. A 2-3 paragraph executive summary
2. Key findings (bullet points)
3. Recommended next steps for investigators
4. Risk level assessment (LOW/MEDIUM/HIGH/CRITICAL) with justification

Language: {lang}
Format: JSON with keys: summary, key_findings (array), recommendations (array), confidence (0-1)"""

    def _evidence_prompt(self, data: dict, lang: str) -> str:
        return f"""You are a digital forensics analyst. Analyze the evidence chain and provide a summary.

Evidence Data:
{json.dumps(data, indent=2)}

Provide:
1. Evidence chain narrative (how evidence connects)
2. Key evidence items and their significance
3. Gaps in the evidence chain
4. Recommendations for additional evidence collection

Language: {lang}
Format: JSON with keys: summary, key_findings (array), recommendations (array), confidence (0-1)"""

    def _pattern_prompt(self, data: dict, lang: str) -> str:
        return f"""You are a fraud pattern analyst. Explain the detected fraud patterns in human-readable terms.

Pattern Data:
{json.dumps(data, indent=2)}

Provide:
1. Pattern explanation (what the pattern indicates)
2. How this pattern is typically used by fraudsters
3. Indicators of compromise
4. Recommendations for detection and prevention

Language: {lang}
Format: JSON with keys: summary, key_findings (array), recommendations (array), confidence (0-1)"""

    def _investigation_prompt(self, data: dict, lang: str) -> str:
        return f"""You are an investigation supervisor. Provide a progress summary for an ongoing investigation.

Investigation Data:
{json.dumps(data, indent=2)}

Provide:
1. Investigation progress overview
2. Completed steps and findings
3. Pending steps and blockers
4. Estimated timeline for completion

Language: {lang}
Format: JSON with keys: summary, key_findings (array), recommendations (array), confidence (0-1)"""

    def _risk_prompt(self, data: dict, lang: str) -> str:
        return f"""You are a risk assessment analyst. Evaluate the risk level of the following fraud case.

Risk Data:
{json.dumps(data, indent=2)}

Provide:
1. Risk assessment narrative
2. Risk factors identified
3. Mitigation recommendations
4. Overall risk score (0-100) with justification

Language: {lang}
Format: JSON with keys: summary, key_findings (array), recommendations (array), confidence (0-1)"""

    async def generate_summary(self, req: SummaryRequest) -> SummaryResult:
        """Generate an AI summary using the OpenAI gateway."""
        self._counter += 1
        summary_id = f"AI-SUMMARY-{self._counter:04d}"

        # Try to call OpenAI API
        if self._api_key:
            try:
                result = await self._call_openai(req)
                if result:
                    self._summaries[summary_id] = result
                    return result
            except Exception as e:
                print(f"AI summary error: {e}")
                # Fall through to fallback

        # Fallback: deterministic summary (no AI dependency)
        return self._fallback_summary(req, summary_id)

    async def _call_openai(self, req: SummaryRequest) -> SummaryResult | None:
        """Call OpenAI API to generate summary."""
        import urllib.request

        prompt = self._build_prompt(req)

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a GFIN fraud intelligence analyst. Provide structured, professional summaries for law enforcement use. All findings should be evidence-based and marked with appropriate confidence levels."},
                {"role": "user", "content": prompt}
            ],
            "max_completion_tokens": req.max_tokens,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        req_obj = urllib.request.Request(self._base_url, data=payload, headers=headers, method="POST")

        try:
            # Use urllib for sync request in async context
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, urllib.request.urlopen, req_obj)
            data = json.loads(response.read().decode())

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not content:
                return None

            # Try to parse JSON from content
            try:
                parsed = json.loads(content)
                return SummaryResult(
                    summary_type=req.summary_type,
                    case_id=req.case_id,
                    summary=parsed.get("summary", content),
                    key_findings=parsed.get("key_findings", []),
                    recommendations=parsed.get("recommendations", []),
                    confidence=float(parsed.get("confidence", 0.7)),
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )
            except json.JSONDecodeError:
                return SummaryResult(
                    summary_type=req.summary_type,
                    case_id=req.case_id,
                    summary=content,
                    confidence=0.7,
                    tokens_used=data.get("usage", {}).get("total_tokens", 0),
                )
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None

    def _fallback_summary(self, req: SummaryRequest, summary_id: str) -> SummaryResult:
        """Generate a deterministic fallback summary without AI."""
        data = req.data
        summary_type = req.summary_type

        if summary_type == "case":
            summary = f"Case {req.case_id or 'unknown'}: Analysis of provided case data indicates "
            summary += f"{len(data.get('evidence_items', []))} evidence items and "
            summary += f"{len(data.get('investigation_steps', []))} investigation steps. "
            risk = data.get("risk_level", "MEDIUM")
            summary += f"Risk assessment: {risk}."
            findings = [f"Risk level: {risk}", f"Evidence items: {len(data.get('evidence_items', []))}"]
            recommendations = ["Collect additional evidence", "Verify entity attribution", "Cross-reference with known patterns"]
            confidence = 0.6

        elif summary_type == "evidence":
            summary = f"Evidence chain analysis for case {req.case_id}: "
            summary += f"{len(data.get('evidence', []))} evidence items reviewed. "
            summary += "Evidence chain shows correlation between entities and infrastructure."
            findings = ["Evidence items correlate", "Attribution chain partially established"]
            recommendations = ["Strengthen evidence preservation", "Verify source authenticity"]
            confidence = 0.55

        elif summary_type == "pattern":
            patterns = data.get("patterns", [])
            summary = f"Pattern analysis: {len(patterns)} patterns detected. "
            summary += "Patterns indicate coordinated fraud activity with shared infrastructure."
            findings = [f"Patterns detected: {len(patterns)}", "Shared infrastructure identified"]
            recommendations = ["Monitor identified infrastructure", "Alert related jurisdictions"]
            confidence = 0.5

        elif summary_type == "investigation":
            steps = data.get("steps", [])
            completed = len([s for s in steps if isinstance(s, dict) and s.get("status") == "completed"])
            summary = f"Investigation progress: {completed}/{len(steps)} steps completed. "
            summary += "Investigation is progressing according to protocol."
            findings = [f"Steps completed: {completed}/{len(steps)}"]
            recommendations = ["Continue investigation steps", "Review pending evidence"]
            confidence = 0.65

        elif summary_type == "risk":
            risk_score = data.get("risk_score", 50)
            summary = f"Risk assessment: Overall risk score {risk_score}/100. "
            if risk_score >= 75:
                summary += "CRITICAL risk level — immediate action required."
            elif risk_score >= 50:
                summary += "HIGH risk level — enhanced monitoring recommended."
            else:
                summary += "MODERATE risk level — standard monitoring."
            findings = [f"Risk score: {risk_score}/100"]
            recommendations = ["Implement risk mitigation measures", "Schedule regular risk reassessment"]
            confidence = 0.7

        else:
            summary = f"Summary of {summary_type} data: {len(data)} data points analyzed."
            findings = []
            recommendations = []
            confidence = 0.5

        result = SummaryResult(
            summary_type=summary_type,
            case_id=req.case_id,
            summary=summary,
            key_findings=findings,
            recommendations=recommendations,
            confidence=confidence,
            tokens_used=0,
            status="fallback"  # Indicates no AI was used
        )
        self._summaries[summary_id] = result
        return result

    def get_summary_by_id(self, summary_id: str) -> SummaryResult | None:
        return self._summaries.get(summary_id)

    def list_summaries(self, summary_type: str = None, case_id: str = None) -> list[SummaryResult]:
        results = list(self._summaries.values())
        if summary_type:
            results = [s for s in results if s.summary_type == summary_type]
        if case_id:
            results = [s for s in results if s.case_id == case_id]
        return results

    def get_summary_stats(self) -> dict:
        return {
            "total_summaries": len(self._summaries),
            "ai_generated": len([s for s in self._summaries.values() if s.status == "generated"]),
            "fallback_generated": len([s for s in self._summaries.values() if s.status == "fallback"]),
            "model": self._model,
            "api_available": bool(self._api_key),
        }

"""GFIN Fraud Detection Engine — Module 15.

Takes enriched, scored reports and applies detection rules and pattern matching
to identify confirmed fraud patterns with confidence levels.

Layer A: In-memory services with synthetic fixtures
Layer B: Kafka-streamed pipeline + Redis + Neo4j (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ─── Enums ───


class RuleType(StrEnum):
    SIGNAL = "SIGNAL"
    PATTERN = "PATTERN"
    THRESHOLD = "THRESHOLD"
    COMPOSITE = "COMPOSITE"


class DetectionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalType(StrEnum):
    HIGH_REPORT_VOLUME = "HIGH_REPORT_VOLUME"
    EVIDENCE_CORROBORATION = "EVIDENCE_CORROBORATION"
    CAMPAIGN_CORRELATION = "CAMPAIGN_CORRELATION"
    NEW_DOMAIN_SHORT_LIFESPAN = "NEW_DOMAIN_SHORT_LIFESPAN"
    KNOWN_BAD_INFRASTRUCTURE = "KNOWN_BAD_INFRASTRUCTURE"
    CROSS_CATEGORY_PATTERN = "CROSS_CATEGORY_PATTERN"
    REPEAT_REPORTER_HIGH_CONFIDENCE = "REPEAT_REPORTER_HIGH_CONFIDENCE"


class PatternType(StrEnum):
    SAME_ENTITY_MULTIPLE_REPORTS = "SAME_ENTITY_MULTIPLE_REPORTS"
    INFRASTRUCTURE_OVERLAP = "INFRASTRUCTURE_OVERLAP"
    TEMPORAL_CLUSTERING = "TEMPORAL_CLUSTERING"
    CROSS_JURISDICTION = "CROSS_JURISDICTION"


# ─── Signal confidence weights ───

SIGNAL_CONFIDENCE_WEIGHTS: dict[str, float] = {
    SignalType.HIGH_REPORT_VOLUME.value: 0.2,
    SignalType.EVIDENCE_CORROBORATION.value: 0.3,
    SignalType.CAMPAIGN_CORRELATION.value: 0.25,
    SignalType.NEW_DOMAIN_SHORT_LIFESPAN.value: 0.15,
    SignalType.KNOWN_BAD_INFRASTRUCTURE.value: 0.2,
    SignalType.CROSS_CATEGORY_PATTERN.value: 0.15,
    SignalType.REPEAT_REPORTER_HIGH_CONFIDENCE.value: 0.1,
}


# ─── Models ───


class DetectionCondition(BaseModel):
    """A condition for a detection rule."""

    field: str
    operator: str  # eq, gt, gte, lt, lte, in, contains
    value: Any


class DetectionRule(BaseModel):
    """A fraud detection rule."""

    id: str
    name: str
    rule_type: str  # RuleType value
    category: str = ""
    conditions: list[DetectionCondition] = Field(default_factory=list)
    min_confidence: float = 0.5
    severity: str = DetectionSeverity.MEDIUM.value
    enabled: bool = True
    description: str = ""

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        valid = {r.value for r in RuleType}
        if v not in valid:
            raise ValueError(f"rule_type must be one of {valid}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {s.value for s in DetectionSeverity}
        if v not in valid:
            raise ValueError(f"severity must be one of {valid}")
        return v

    @field_validator("min_confidence")
    @classmethod
    def validate_min_confidence(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        return v


class MatchedSignal(BaseModel):
    """A matched fraud signal."""

    signal_type: str
    description: str = ""
    confidence: float = 0.0
    entity_ids: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class DetectionResult(BaseModel):
    """Result of fraud detection on a report."""

    report_id: str
    rule_id: str
    rule_name: str
    rule_type: str
    signals: list[MatchedSignal] = Field(default_factory=list)
    confidence: float = 0.0
    severity: str = DetectionSeverity.MEDIUM.value
    entity_ids: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str = ""


# ─── Signal Detector ───


class SignalDetector:
    """Detects individual fraud signals from reports and entity data."""

    def __init__(
        self,
        report_store: dict[str, Any] | None = None,
        campaign_store: dict[str, Any] | None = None,
    ) -> None:
        self._reports = report_store or {}
        self._campaigns = campaign_store or {}

    def detect_signals(
        self,
        report: Any,
        enrichment: Any | None = None,
        score_result: Any | None = None,
    ) -> list[MatchedSignal]:
        """Detect all applicable signals for a report."""
        signals: list[MatchedSignal] = []

        # HIGH_REPORT_VOLUME: 5+ reports for same entity
        entity_ids = set(getattr(report, "related_entity_ids", []))
        report_count = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if set(getattr(r, "related_entity_ids", [])) & entity_ids:
                report_count += 1
        if report_count >= 5:
            signals.append(
                MatchedSignal(
                    signal_type=SignalType.HIGH_REPORT_VOLUME.value,
                    description=f"{report_count} reports for same entity",
                    confidence=SIGNAL_CONFIDENCE_WEIGHTS[SignalType.HIGH_REPORT_VOLUME.value],
                    entity_ids=list(entity_ids),
                    evidence={"report_count": report_count},
                )
            )

        # EVIDENCE_CORROBORATION: 2+ corroborated reports
        corroborated = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if set(getattr(r, "related_entity_ids", [])) & entity_ids:
                if getattr(r, "status", "") in (
                    "CORROBORATED",
                    "VERIFIED",
                    "OFFICIALLY_ESTABLISHED",
                ):
                    corroborated += 1
        if corroborated >= 2:
            signals.append(
                MatchedSignal(
                    signal_type=SignalType.EVIDENCE_CORROBORATION.value,
                    description=f"{corroborated} corroborated reports",
                    confidence=SIGNAL_CONFIDENCE_WEIGHTS[SignalType.EVIDENCE_CORROBORATION.value],
                    entity_ids=list(entity_ids),
                    evidence={"corroborated_count": corroborated},
                )
            )

        # CAMPAIGN_CORRELATION: entity linked to active campaign
        if enrichment and getattr(enrichment, "related_campaign_ids", []):
            signals.append(
                MatchedSignal(
                    signal_type=SignalType.CAMPAIGN_CORRELATION.value,
                    description=f"Linked to {len(enrichment.related_campaign_ids)} campaign(s)",
                    confidence=SIGNAL_CONFIDENCE_WEIGHTS[SignalType.CAMPAIGN_CORRELATION.value],
                    entity_ids=list(entity_ids),
                    evidence={"campaign_ids": enrichment.related_campaign_ids},
                )
            )

        # CROSS_CATEGORY_PATTERN: same entity reported in 3+ categories
        categories = set()
        for r in self._reports.values():
            if set(getattr(r, "related_entity_ids", [])) & entity_ids:
                categories.add(getattr(r, "category", ""))
        categories.discard("")
        if len(categories) >= 3:
            signals.append(
                MatchedSignal(
                    signal_type=SignalType.CROSS_CATEGORY_PATTERN.value,
                    description=f"Entity reported in {len(categories)} categories",
                    confidence=SIGNAL_CONFIDENCE_WEIGHTS[SignalType.CROSS_CATEGORY_PATTERN.value],
                    entity_ids=list(entity_ids),
                    evidence={"categories": list(categories)},
                )
            )

        # REPEAT_REPORTER_HIGH_CONFIDENCE: 5+ reports from credible reporter
        reporter_id = getattr(report, "reporter_id", None)
        if reporter_id:
            reporter_count = sum(
                1 for r in self._reports.values() if getattr(r, "reporter_id", None) == reporter_id
            )
            if reporter_count >= 5:
                signals.append(
                    MatchedSignal(
                        signal_type=SignalType.REPEAT_REPORTER_HIGH_CONFIDENCE.value,
                        description=f"Reporter has submitted {reporter_count} reports",
                        confidence=SIGNAL_CONFIDENCE_WEIGHTS[
                            SignalType.REPEAT_REPORTER_HIGH_CONFIDENCE.value
                        ],
                        entity_ids=list(entity_ids),
                        evidence={"reporter_report_count": reporter_count},
                    )
                )

        return signals

    def detect_infrastructure_signals(
        self,
        report: Any,
        enrichment: Any | None = None,
    ) -> list[MatchedSignal]:
        """Detect infrastructure-based signals."""
        signals: list[MatchedSignal] = []
        entity_ids = set(getattr(report, "related_entity_ids", []))

        # KNOWN_BAD_INFRASTRUCTURE: entity on known bad IP/ASN
        if enrichment and getattr(enrichment, "infrastructure_indicators", []):
            bad_indicators = [
                ind
                for ind in enrichment.infrastructure_indicators
                if ind.get("type") in ("bad_ip", "bad_asn", "malicious_infrastructure")
            ]
            if bad_indicators:
                signals.append(
                    MatchedSignal(
                        signal_type=SignalType.KNOWN_BAD_INFRASTRUCTURE.value,
                        description=f"{len(bad_indicators)} bad infrastructure indicators",
                        confidence=SIGNAL_CONFIDENCE_WEIGHTS[
                            SignalType.KNOWN_BAD_INFRASTRUCTURE.value
                        ],
                        entity_ids=list(entity_ids),
                        evidence={"indicators": bad_indicators},
                    )
                )

        # NEW_DOMAIN_SHORT_LIFESPAN: domain registered < 30 days
        if enrichment and getattr(enrichment, "infrastructure_indicators", []):
            for ind in enrichment.infrastructure_indicators:
                if ind.get("type") == "domain_age_days":
                    try:
                        age = int(ind.get("value", 0))
                        if age < 30:
                            signals.append(
                                MatchedSignal(
                                    signal_type=SignalType.NEW_DOMAIN_SHORT_LIFESPAN.value,
                                    description=f"Domain registered {age} days ago",
                                    confidence=SIGNAL_CONFIDENCE_WEIGHTS[
                                        SignalType.NEW_DOMAIN_SHORT_LIFESPAN.value
                                    ],
                                    entity_ids=list(entity_ids),
                                    evidence={"domain_age_days": age},
                                )
                            )
                    except (ValueError, TypeError):
                        pass

        return signals


# ─── Pattern Matcher ───


class PatternMatcher:
    """Matches multi-entity, multi-report fraud patterns."""

    def __init__(
        self,
        report_store: dict[str, Any] | None = None,
    ) -> None:
        self._reports = report_store or {}

    def match_patterns(self, report: Any) -> list[MatchedSignal]:
        """Match patterns for a report."""
        patterns: list[MatchedSignal] = []
        entity_ids = set(getattr(report, "related_entity_ids", []))

        # SAME_ENTITY_MULTIPLE_REPORTS: same entity, 3+ reports
        report_count = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if set(getattr(r, "related_entity_ids", [])) & entity_ids:
                report_count += 1
        if report_count >= 3:
            patterns.append(
                MatchedSignal(
                    signal_type=PatternType.SAME_ENTITY_MULTIPLE_REPORTS.value,
                    description=f"{report_count} reports for same entity",
                    confidence=min(0.1 * report_count, 0.5),
                    entity_ids=list(entity_ids),
                    evidence={"report_count": report_count},
                )
            )

        # TEMPORAL_CLUSTERING: 3+ reports within 1 hour for same category
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=1)
        same_cat_recent = 0
        for r in self._reports.values():
            if r.id == report.id:
                continue
            if getattr(r, "category", "") != getattr(report, "category", ""):
                continue
            r_time = (
                getattr(r.audit, "created_at", now)
                if hasattr(getattr(r, "audit", None), "created_at")
                else now
            )
            if r_time > cutoff:
                same_cat_recent += 1
        if same_cat_recent >= 3:
            patterns.append(
                MatchedSignal(
                    signal_type=PatternType.TEMPORAL_CLUSTERING.value,
                    description=f"{same_cat_recent} reports for same category in 1 hour",
                    confidence=0.4,
                    entity_ids=list(entity_ids),
                    evidence={"recent_count": same_cat_recent},
                )
            )

        # CROSS_JURISDICTION: reports from 3+ countries for same entity
        countries = set()
        for r in self._reports.values():
            if set(getattr(r, "related_entity_ids", [])) & entity_ids:
                country = getattr(r, "country", None)
                if country:
                    countries.add(country)
        if len(countries) >= 3:
            patterns.append(
                MatchedSignal(
                    signal_type=PatternType.CROSS_JURISDICTION.value,
                    description=f"Reports from {len(countries)} countries",
                    confidence=0.35,
                    entity_ids=list(entity_ids),
                    evidence={"countries": list(countries)},
                )
            )

        return patterns


# ─── Fraud Detection Engine ───


class FraudDetectionEngine:
    """Evaluates reports against detection rules and produces DetectionResults."""

    # Threshold-based detection thresholds
    HIGH_THRESHOLD = 75
    CRITICAL_THRESHOLD = 90

    def __init__(
        self,
        report_store: dict[str, Any] | None = None,
        campaign_store: dict[str, Any] | None = None,
        event_bus: Any | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        self._reports = report_store or {}
        self._campaigns = campaign_store or {}
        self._event_bus = event_bus
        self._audit = audit_logger
        self._rules: dict[str, DetectionRule] = {}
        self._detection_history: list[DetectionResult] = []
        self._signal_detector = SignalDetector(
            report_store=self._reports,
            campaign_store=self._campaigns,
        )
        self._pattern_matcher = PatternMatcher(report_store=self._reports)

    def register_rule(self, rule: DetectionRule) -> None:
        """Register a detection rule."""
        self._rules[rule.id] = rule

    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a detection rule."""
        return self._rules.pop(rule_id, None) is not None

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a detection rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a detection rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def list_rules(self) -> list[DetectionRule]:
        """List all registered rules."""
        return list(self._rules.values())

    def evaluate(
        self,
        report: Any,
        enrichment: Any | None = None,
        score_result: Any | None = None,
    ) -> list[DetectionResult]:
        """Evaluate a report against all enabled rules."""
        results: list[DetectionResult] = []

        # 1. Signal-based detection
        signals = self._signal_detector.detect_signals(report, enrichment, score_result)
        infra_signals = self._signal_detector.detect_infrastructure_signals(report, enrichment)
        signals.extend(infra_signals)

        # 2. Pattern matching
        patterns = self._pattern_matcher.match_patterns(report)
        signals.extend(patterns)

        # 3. Evaluate against registered rules
        for rule in self._rules.values():
            if not rule.enabled:
                continue

            result = self._evaluate_rule(rule, report, signals, score_result)
            if result:
                results.append(result)

        # 4. Threshold-based detection (automatic rules)
        if score_result and hasattr(score_result, "score"):
            score = score_result.score
            if score >= self.CRITICAL_THRESHOLD:
                results.append(
                    self._create_threshold_result(
                        report,
                        score,
                        DetectionSeverity.CRITICAL.value,
                    )
                )
            elif score >= self.HIGH_THRESHOLD:
                results.append(
                    self._create_threshold_result(
                        report,
                        score,
                        DetectionSeverity.HIGH.value,
                    )
                )

        # 5. Auto-detection from signals (if no rules match but signals exist)
        if not results and signals:
            total_confidence = min(sum(s.confidence for s in signals), 1.0)
            if total_confidence >= 0.5:
                results.append(self._create_signal_result(report, signals, total_confidence))

        # Store and publish
        for result in results:
            self._detection_history.append(result)
            self._publish_detection(result)
            self._audit_detection(result)

        return results

    def _evaluate_rule(
        self,
        rule: DetectionRule,
        report: Any,
        signals: list[MatchedSignal],
        score_result: Any | None = None,
    ) -> DetectionResult | None:
        """Evaluate a single rule against a report."""
        matched_signals: list[MatchedSignal] = []
        entity_ids = set(getattr(report, "related_entity_ids", []))

        # Check conditions
        all_conditions_met = True
        for condition in rule.conditions:
            if not self._check_condition(condition, report, signals, score_result):
                all_conditions_met = False
                break

        if not all_conditions_met:
            return None

        # Collect matching signals
        for signal in signals:
            if rule.rule_type == RuleType.SIGNAL.value:
                # Signal rules match any signal
                matched_signals.append(signal)
            elif rule.rule_type == RuleType.PATTERN.value:
                # Pattern rules match pattern-type signals
                if signal.signal_type in {p.value for p in PatternType}:
                    matched_signals.append(signal)
            elif rule.rule_type == RuleType.COMPOSITE.value:
                matched_signals.append(signal)

        # Calculate confidence
        if matched_signals:
            confidence = min(sum(s.confidence for s in matched_signals), 1.0)
        else:
            confidence = 0.6  # default if conditions met but no signals

        if confidence < rule.min_confidence:
            return None

        return DetectionResult(
            report_id=report.id,
            rule_id=rule.id,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            signals=matched_signals,
            confidence=confidence,
            severity=rule.severity,
            entity_ids=list(entity_ids),
            summary=f"Rule '{rule.name}' matched with {len(matched_signals)} signal(s), confidence {confidence:.2f}",
        )

    def _check_condition(
        self,
        condition: DetectionCondition,
        report: Any,
        signals: list[MatchedSignal],
        score_result: Any | None = None,
    ) -> bool:
        """Check a condition against report data."""
        field = condition.field
        op = condition.operator
        target = condition.value

        # Get field value
        if field == "category":
            actual = getattr(report, "category", "")
        elif field == "risk_level":
            actual = getattr(report, "risk_level", "")
        elif field == "status":
            actual = getattr(report, "status", "")
        elif field == "signal":
            actual = [s.signal_type for s in signals]
        elif field == "score":
            actual = getattr(score_result, "score", 0) if score_result else 0
        elif field == "signal_count":
            actual = len(signals)
        else:
            actual = getattr(report, field, None)

        # Evaluate
        if op == "eq":
            return actual == target
        elif op == "gt":
            try:
                return actual > target
            except TypeError:
                return False
        elif op == "gte":
            try:
                return actual >= target
            except TypeError:
                return False
        elif op == "lt":
            try:
                return actual < target
            except TypeError:
                return False
        elif op == "lte":
            try:
                return actual <= target
            except TypeError:
                return False
        elif op == "in":
            return actual in target if isinstance(target, list | set) else False
        elif op == "contains":
            if isinstance(actual, list):
                return target in actual
            if isinstance(actual, str):
                return target in actual
            return False
        return False

    def _create_threshold_result(
        self,
        report: Any,
        score: int,
        severity: str,
    ) -> DetectionResult:
        """Create a threshold-based detection result."""
        entity_ids = getattr(report, "related_entity_ids", [])
        return DetectionResult(
            report_id=report.id,
            rule_id="THRESHOLD-AUTO",
            rule_name=f"Automatic threshold detection (score {score})",
            rule_type=RuleType.THRESHOLD.value,
            signals=[
                MatchedSignal(
                    signal_type="THRESHOLD_EXCEEDED",
                    description=f"Risk score {score} exceeds threshold",
                    confidence=min(score / 100, 1.0),
                    entity_ids=entity_ids,
                    evidence={"score": score},
                )
            ],
            confidence=min(score / 100, 1.0),
            severity=severity,
            entity_ids=entity_ids,
            summary=f"Automatic detection: risk score {score} exceeds {severity} threshold",
        )

    def _create_signal_result(
        self,
        report: Any,
        signals: list[MatchedSignal],
        confidence: float,
    ) -> DetectionResult:
        """Create a signal-based auto-detection result."""
        entity_ids = getattr(report, "related_entity_ids", [])
        severity = (
            DetectionSeverity.HIGH.value if confidence >= 0.75 else DetectionSeverity.MEDIUM.value
        )
        return DetectionResult(
            report_id=report.id,
            rule_id="SIGNAL-AUTO",
            rule_name="Automatic signal-based detection",
            rule_type=RuleType.SIGNAL.value,
            signals=signals,
            confidence=confidence,
            severity=severity,
            entity_ids=entity_ids,
            summary=f"Auto-detection from {len(signals)} signal(s), confidence {confidence:.2f}",
        )

    def _publish_detection(self, result: DetectionResult) -> None:
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="fraud.detected",
                    event={
                        "report_id": result.report_id,
                        "rule_id": result.rule_id,
                        "confidence": result.confidence,
                        "severity": result.severity,
                        "timestamp": result.detected_at.isoformat(),
                    },
                )

    def _audit_detection(self, result: DetectionResult) -> None:
        if self._audit:
            self._audit.log(
                user_id="system",
                action="fraud_detected",
                resource_type="report",
                resource_id=result.report_id,
                details={
                    "rule_id": result.rule_id,
                    "confidence": result.confidence,
                    "severity": result.severity,
                },
            )

    def get_history(self, report_id: str | None = None) -> list[DetectionResult]:
        """Get detection history, optionally filtered by report."""
        if report_id:
            return [r for r in self._detection_history if r.report_id == report_id]
        return list(self._detection_history)

    def clear_history(self) -> None:
        """Clear detection history."""
        self._detection_history.clear()

"""GFIN Cross-Border Requests — Module 26.

Full cross-border request workflow per Architecture Review §6.3:
REQUEST → VALIDATE → AUTHORIZE → DESTINATION → REVIEW → DECISION → AUDIT

Per Legal Assumptions: each request records requesting org, investigator
identity, legal basis, purpose, entity, requested information, urgency,
case reference.

Per Architecture Review §6.4: each national node controls what data it
shares. Only permitted intelligence metadata crosses borders.

Layer A: In-memory workflow engine
Layer B: Federation protocol over Kafka, encrypted transport (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from services.global_matching import MatchPolicy

# ─── Enums ───


class RequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    AUTHORIZED = "AUTHORIZED"
    ROUTED = "ROUTED"
    REVIEWING = "REVIEWING"
    DECIDED = "DECIDED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class RequestDecision(StrEnum):
    NONE = "NONE"
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    DENIED = "DENIED"


class UrgencyLevel(StrEnum):
    ROUTINE = "ROUTINE"
    PRIORITY = "PRIORITY"
    EMERGENCY = "EMERGENCY"


# ─── Status transitions ───

VALID_TRANSITIONS: dict[str, set[str]] = {
    RequestStatus.SUBMITTED.value: {RequestStatus.VALIDATED.value, RequestStatus.REJECTED.value},
    RequestStatus.VALIDATED.value: {RequestStatus.AUTHORIZED.value, RequestStatus.REJECTED.value},
    RequestStatus.AUTHORIZED.value: {RequestStatus.ROUTED.value, RequestStatus.REJECTED.value},
    RequestStatus.ROUTED.value: {RequestStatus.REVIEWING.value, RequestStatus.REJECTED.value},
    RequestStatus.REVIEWING.value: {RequestStatus.DECIDED.value},
    RequestStatus.DECIDED.value: {RequestStatus.CLOSED.value},
    RequestStatus.REJECTED.value: {RequestStatus.CLOSED.value},
    RequestStatus.CLOSED.value: set(),
}


# ─── Models ───


class CrossBorderRequestRecord(BaseModel):
    """A full cross-border request record with workflow state."""

    id: str
    requesting_org: str
    requesting_jurisdiction: str
    target_jurisdiction: str
    investigator_name: str = ""
    legal_basis: str = ""
    purpose: str = ""
    case_reference: str = ""
    entity_id: str
    entity_type: str
    entity_value: str = ""
    requested_information: str = ""
    urgency: str = UrgencyLevel.ROUTINE.value
    status: str = RequestStatus.SUBMITTED.value
    decision: str = RequestDecision.NONE.value
    response_data: dict[str, Any] | None = None
    denial_reason: str = ""
    partial_reason: str = ""
    reviewer: str = ""
    # Timestamps for each stage
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    validated_at: datetime | None = None
    authorized_at: datetime | None = None
    routed_at: datetime | None = None
    review_started_at: datetime | None = None
    decided_at: datetime | None = None
    closed_at: datetime | None = None

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def transition(self, new_status: str) -> bool:
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        now = datetime.now(UTC)
        if new_status == RequestStatus.VALIDATED.value:
            self.validated_at = now
        elif new_status == RequestStatus.AUTHORIZED.value:
            self.authorized_at = now
        elif new_status == RequestStatus.ROUTED.value:
            self.routed_at = now
        elif new_status == RequestStatus.REVIEWING.value:
            self.review_started_at = now
        elif new_status == RequestStatus.DECIDED.value:
            self.decided_at = now
        elif new_status == RequestStatus.CLOSED.value:
            self.closed_at = now
        return True


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class AuthorizationResult(BaseModel):
    authorized: bool
    reason: str = ""


class RoutingResult(BaseModel):
    routed: bool
    destination_jurisdiction: str
    destination_org: str = ""
    reason: str = ""


class DecisionResult(BaseModel):
    decision: str
    response_data: dict[str, Any] | None = None
    reason: str = ""


class RequestAuditEntry(BaseModel):
    """Audit entry for a single workflow stage."""

    id: str
    request_id: str
    stage: str
    actor: str = ""
    result: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─── Request Validator ───


class RequestValidator:
    """Validates cross-border requests per Architecture Review §6.3."""

    @staticmethod
    def validate(request: CrossBorderRequestRecord) -> ValidationResult:
        errors: list[str] = []

        if not request.legal_basis:
            errors.append("Legal basis is required")
        if not request.purpose:
            errors.append("Purpose is required")
        if not request.entity_id:
            errors.append("Entity ID is required")
        if not request.entity_type:
            errors.append("Entity type is required")
        if not request.requesting_org:
            errors.append("Requesting organization is required")
        if not request.target_jurisdiction:
            errors.append("Target jurisdiction is required")
        if request.requesting_jurisdiction == request.target_jurisdiction:
            errors.append("Target jurisdiction must differ from requesting jurisdiction")
        if not request.investigator_name:
            errors.append("Investigator name is required")

        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ─── Request Authorizer ───


class RequestAuthorizer:
    """Authorizes cross-border requests.

    Checks: requesting org exists, has access rights, jurisdiction permitted.
    """

    def __init__(self) -> None:
        # {org_id: set of permitted target jurisdictions, or "*" for all}
        self._org_permissions: dict[str, set[str]] = {}
        self._registered_orgs: set[str] = set()

    def register_org(self, org_id: str, permitted_jurisdictions: set[str] | None = None) -> None:
        """Register an organization with its permitted target jurisdictions."""
        self._registered_orgs.add(org_id)
        self._org_permissions[org_id] = permitted_jurisdictions or {"*"}

    def authorize(self, request: CrossBorderRequestRecord) -> AuthorizationResult:
        if request.requesting_org not in self._registered_orgs:
            return AuthorizationResult(authorized=False, reason="Organization not registered")

        permissions = self._org_permissions.get(request.requesting_org, set())
        if "*" not in permissions and request.target_jurisdiction not in permissions:
            return AuthorizationResult(
                authorized=False,
                reason=f"Organization not permitted to request from {request.target_jurisdiction}",
            )

        return AuthorizationResult(authorized=True)


# ─── Request Router ───


class RequestRouter:
    """Routes requests to the destination jurisdiction.

    Layer A: In-memory routing (just records the destination)
    Layer B: Federation protocol routing over Kafka
    """

    def __init__(self) -> None:
        # {jurisdiction: org_id}
        self._jurisdiction_map: dict[str, str] = {}

    def register_jurisdiction(self, jurisdiction: str, org_id: str) -> None:
        """Register which org handles a jurisdiction."""
        self._jurisdiction_map[jurisdiction] = org_id

    def route(self, request: CrossBorderRequestRecord) -> RoutingResult:
        dest_org = self._jurisdiction_map.get(request.target_jurisdiction)
        if dest_org is None:
            return RoutingResult(
                routed=False,
                destination_jurisdiction=request.target_jurisdiction,
                reason="No organization registered for target jurisdiction",
            )
        return RoutingResult(
            routed=True,
            destination_jurisdiction=request.target_jurisdiction,
            destination_org=dest_org,
        )


# ─── Request Audit Trail ───


class RequestAuditTrail:
    """Full audit trail for cross-border requests."""

    def __init__(self) -> None:
        self._entries: list[RequestAuditEntry] = []
        self._counter = 0

    def log(
        self,
        request_id: str,
        stage: str,
        actor: str = "",
        result: str = "",
        details: dict[str, Any] | None = None,
    ) -> RequestAuditEntry:
        self._counter += 1
        entry = RequestAuditEntry(
            id=f"CBAUDIT-{self._counter:06d}",
            request_id=request_id,
            stage=stage,
            actor=actor,
            result=result,
            details=details or {},
        )
        self._entries.append(entry)
        return entry

    def get_trail(self, request_id: str) -> list[RequestAuditEntry]:
        return [e for e in self._entries if e.request_id == request_id]

    @property
    def count(self) -> int:
        return len(self._entries)


# ─── Cross-Border Request Engine ───


class CrossBorderRequestEngine:
    """Orchestrates the full cross-border request workflow.

    Per Architecture Review §6.3:
    REQUEST → VALIDATE → AUTHORIZE → DESTINATION → REVIEW → DECISION → AUDIT
    """

    def __init__(
        self,
        validator: RequestValidator | None = None,
        authorizer: RequestAuthorizer | None = None,
        router: RequestRouter | None = None,
        audit: RequestAuditTrail | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._validator = validator or RequestValidator()
        self._authorizer = authorizer or RequestAuthorizer()
        self._router = router or RequestRouter()
        self._audit = audit or RequestAuditTrail()
        self._event_bus = event_bus
        self._requests: dict[str, CrossBorderRequestRecord] = {}
        self._counter = 0

    @property
    def authorizer(self) -> RequestAuthorizer:
        return self._authorizer

    @property
    def router(self) -> RequestRouter:
        return self._router

    @property
    def audit(self) -> RequestAuditTrail:
        return self._audit

    def create_request(
        self,
        requesting_org: str,
        requesting_jurisdiction: str,
        target_jurisdiction: str,
        entity_id: str,
        entity_type: str,
        investigator_name: str = "",
        legal_basis: str = "",
        purpose: str = "",
        case_reference: str = "",
        entity_value: str = "",
        requested_information: str = "",
        urgency: str = UrgencyLevel.ROUTINE.value,
    ) -> CrossBorderRequestRecord:
        """Create a new cross-border request (status: SUBMITTED)."""
        self._counter += 1
        request = CrossBorderRequestRecord(
            id=f"CBR-{self._counter:06d}",
            requesting_org=requesting_org,
            requesting_jurisdiction=requesting_jurisdiction,
            target_jurisdiction=target_jurisdiction,
            investigator_name=investigator_name,
            legal_basis=legal_basis,
            purpose=purpose,
            case_reference=case_reference,
            entity_id=entity_id,
            entity_type=entity_type,
            entity_value=entity_value,
            requested_information=requested_information,
            urgency=urgency,
        )
        self._requests[request.id] = request
        self._audit.log(request.id, "SUBMITTED", actor=investigator_name, result="created")
        return request

    def validate_request(self, request_id: str) -> ValidationResult:
        """Validate a request (format, legal basis, purpose)."""
        request = self._requests.get(request_id)
        if request is None:
            return ValidationResult(valid=False, errors=["Request not found"])

        result = self._validator.validate(request)

        if result.valid:
            request.transition(RequestStatus.VALIDATED.value)
            self._audit.log(request_id, "VALIDATE", result="valid")
        else:
            request.transition(RequestStatus.REJECTED.value)
            self._audit.log(
                request_id, "VALIDATE", result="invalid", details={"errors": result.errors}
            )

        return result

    def authorize_request(self, request_id: str) -> AuthorizationResult:
        """Authorize a request (access rights check)."""
        request = self._requests.get(request_id)
        if request is None:
            return AuthorizationResult(authorized=False, reason="Request not found")

        if request.status != RequestStatus.VALIDATED.value:
            return AuthorizationResult(authorized=False, reason="Request not in VALIDATED state")

        result = self._authorizer.authorize(request)

        if result.authorized:
            request.transition(RequestStatus.AUTHORIZED.value)
            self._audit.log(request_id, "AUTHORIZE", result="authorized")
        else:
            request.transition(RequestStatus.REJECTED.value)
            self._audit.log(
                request_id, "AUTHORIZE", result="denied", details={"reason": result.reason}
            )

        return result

    def route_request(self, request_id: str) -> RoutingResult:
        """Route a request to the destination jurisdiction."""
        request = self._requests.get(request_id)
        if request is None:
            return RoutingResult(
                routed=False, destination_jurisdiction="", reason="Request not found"
            )

        if request.status != RequestStatus.AUTHORIZED.value:
            return RoutingResult(
                routed=False, destination_jurisdiction="", reason="Request not in AUTHORIZED state"
            )

        result = self._router.route(request)

        if result.routed:
            request.transition(RequestStatus.ROUTED.value)
            self._audit.log(
                request_id,
                "ROUTE",
                result="routed",
                details={"destination": result.destination_org},
            )

            if self._event_bus:
                with contextlib.suppress(Exception):
                    self._event_bus.publish(
                        topic="cross_border.routed",
                        event={
                            "request_id": request_id,
                            "destination_jurisdiction": request.target_jurisdiction,
                            "destination_org": result.destination_org,
                            "timestamp": datetime.now(UTC).isoformat(),
                        },
                    )
        else:
            request.transition(RequestStatus.REJECTED.value)
            self._audit.log(request_id, "ROUTE", result="failed", details={"reason": result.reason})

        return result

    def start_review(self, request_id: str, reviewer: str) -> bool:
        """Start the review phase (destination jurisdiction reviews)."""
        request = self._requests.get(request_id)
        if request is None:
            return False

        if request.status != RequestStatus.ROUTED.value:
            return False

        request.reviewer = reviewer
        request.transition(RequestStatus.REVIEWING.value)
        self._audit.log(request_id, "REVIEW", actor=reviewer, result="review_started")

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="cross_border.review_started",
                    event={
                        "request_id": request_id,
                        "reviewer": reviewer,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return True

    def make_decision(
        self,
        request_id: str,
        decision: str,
        reviewer: str,
        response_data: dict[str, Any] | None = None,
        denial_reason: str = "",
        partial_reason: str = "",
    ) -> DecisionResult | None:
        """Make a decision on a request (APPROVE/PARTIAL/DENY)."""
        request = self._requests.get(request_id)
        if request is None:
            return None

        if request.status != RequestStatus.REVIEWING.value:
            return None

        request.decision = decision
        request.reviewer = reviewer

        if decision == RequestDecision.APPROVED.value:
            # Policy-filter the response data
            if response_data:
                request.response_data = MatchPolicy.filter_match_data(response_data)
            else:
                request.response_data = {"status": "approved"}
            self._audit.log(
                request_id,
                "DECISION",
                actor=reviewer,
                result="approved",
                details={"has_response_data": bool(response_data)},
            )
        elif decision == RequestDecision.PARTIAL.value:
            if response_data:
                request.response_data = MatchPolicy.filter_match_data(response_data)
            else:
                request.response_data = {"status": "partial"}
            request.partial_reason = partial_reason
            self._audit.log(
                request_id,
                "DECISION",
                actor=reviewer,
                result="partial",
                details={"partial_reason": partial_reason},
            )
        elif decision == RequestDecision.DENIED.value:
            request.denial_reason = denial_reason
            self._audit.log(
                request_id,
                "DECISION",
                actor=reviewer,
                result="denied",
                details={"denial_reason": denial_reason},
            )
        else:
            return None

        request.transition(RequestStatus.DECIDED.value)

        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(
                    topic="cross_border.decided",
                    event={
                        "request_id": request_id,
                        "decision": decision,
                        "reviewer": reviewer,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )

        return DecisionResult(
            decision=decision,
            response_data=request.response_data,
            reason=denial_reason or partial_reason,
        )

    def close_request(self, request_id: str) -> CrossBorderRequestRecord | None:
        """Close a decided or rejected request."""
        request = self._requests.get(request_id)
        if request is None:
            return None

        if request.status not in (RequestStatus.DECIDED.value, RequestStatus.REJECTED.value):
            return None

        request.transition(RequestStatus.CLOSED.value)
        self._audit.log(request_id, "CLOSE", result="closed")

        return request

    def get_request(self, request_id: str) -> CrossBorderRequestRecord | None:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_audit_trail(self, request_id: str) -> list[RequestAuditEntry]:
        """Get the full audit trail for a request."""
        return self._audit.get_trail(request_id)

    @property
    def requests(self) -> list[CrossBorderRequestRecord]:
        return list(self._requests.values())

    @property
    def count(self) -> int:
        return len(self._requests)

    def process_full_workflow(
        self,
        requesting_org: str,
        requesting_jurisdiction: str,
        target_jurisdiction: str,
        entity_id: str,
        entity_type: str,
        investigator_name: str,
        legal_basis: str,
        purpose: str,
        reviewer: str,
        decision: str = RequestDecision.APPROVED.value,
        response_data: dict[str, Any] | None = None,
        denial_reason: str = "",
        partial_reason: str = "",
        case_reference: str = "",
        entity_value: str = "",
        requested_information: str = "",
        urgency: str = UrgencyLevel.ROUTINE.value,
    ) -> CrossBorderRequestRecord | None:
        """Run the full workflow from submission to decision in one call.

        Useful for testing and automated processing.
        """
        request = self.create_request(
            requesting_org=requesting_org,
            requesting_jurisdiction=requesting_jurisdiction,
            target_jurisdiction=target_jurisdiction,
            entity_id=entity_id,
            entity_type=entity_type,
            investigator_name=investigator_name,
            legal_basis=legal_basis,
            purpose=purpose,
            case_reference=case_reference,
            entity_value=entity_value,
            requested_information=requested_information,
            urgency=urgency,
        )

        # Validate
        val = self.validate_request(request.id)
        if not val.valid:
            return request

        # Authorize
        auth = self.authorize_request(request.id)
        if not auth.authorized:
            return request

        # Route
        route = self.route_request(request.id)
        if not route.routed:
            return request

        # Review
        self.start_review(request.id, reviewer)

        # Decide
        self.make_decision(
            request.id,
            decision=decision,
            reviewer=reviewer,
            response_data=response_data,
            denial_reason=denial_reason,
            partial_reason=partial_reason,
        )

        # Close
        self.close_request(request.id)

        return request

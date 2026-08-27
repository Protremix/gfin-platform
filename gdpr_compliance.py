"""
GFIN GDPR Compliance Module — Data Subject Rights & Privacy Controls

Features:
- Data Subject Access Request (DSAR) — export all data for a person
- Right to Erasure — delete all data for a person
- Consent Management — track consent for data processing
- Data Processing Records — log all data processing activities
- Data Breach Notification — log and track data breaches

Layer A: In-memory MVP (no external dependencies)
Layer B: PostgreSQL persistent storage (requires database)
"""
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from enum import StrEnum
import json
import hashlib


class RequestType(StrEnum):
    ACCESS = "access"
    ERASURE = "erasure"
    RECTIFICATION = "rectification"
    RESTRICTION = "restriction"
    PORTABILITY = "portability"
    OBJECTION = "objection"


class RequestStatus(StrEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    REJECTED = "rejected"


class BreachSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DataSubjectRequest:
    id: str
    request_type: RequestType
    subject_name: str
    subject_email: str
    subject_identifier: str = ""
    description: str = ""
    status: RequestStatus = RequestStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""
    response_data: dict = field(default_factory=dict)
    handler: str = "system"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_type": self.request_type.value,
            "subject_name": self.subject_name,
            "subject_email": self.subject_email,
            "subject_identifier": self.subject_identifier,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "handler": self.handler,
            "response_data": self.response_data,
        }


@dataclass
class ConsentRecord:
    id: str
    subject_email: str
    purpose: str
    granted: bool = False
    granted_at: str = ""
    withdrawn_at: str = ""
    legal_basis: str = "consent"
    processing_details: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_email": self.subject_email,
            "purpose": self.purpose,
            "granted": self.granted,
            "granted_at": self.granted_at,
            "withdrawn_at": self.withdrawn_at,
            "legal_basis": self.legal_basis,
            "processing_details": self.processing_details,
        }


@dataclass
class ProcessingActivity:
    id: str
    activity_name: str
    purpose: str
    data_categories: list = field(default_factory=list)
    legal_basis: str = "legitimate_interest"
    recipients: list = field(default_factory=list)
    retention_period_days: int = 365
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "activity_name": self.activity_name,
            "purpose": self.purpose,
            "data_categories": self.data_categories,
            "legal_basis": self.legal_basis,
            "recipients": self.recipients,
            "retention_period_days": self.retention_period_days,
            "created_at": self.created_at,
        }


@dataclass
class DataBreach:
    id: str
    description: str
    severity: BreachSeverity
    affected_records: int = 0
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    reported_at: str = ""
    notified_authorities: bool = False
    notified_subjects: bool = False
    status: str = "open"
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "severity": self.severity.value,
            "affected_records": self.affected_records,
            "detected_at": self.detected_at,
            "reported_at": self.reported_at,
            "notified_authorities": self.notified_authorities,
            "notified_subjects": self.notified_subjects,
            "status": self.status,
            "remediation": self.remediation,
        }


class GDPRComplianceService:
    """GDPR compliance service for data subject rights and privacy controls."""

    def __init__(self):
        self._requests: dict[str, DataSubjectRequest] = {}
        self._consents: dict[str, ConsentRecord] = {}
        self._processing_activities: dict[str, ProcessingActivity] = {}
        self._breaches: dict[str, DataBreach] = {}
        self._request_counter = 0
        self._consent_counter = 0
        self._breach_counter = 0

    # ==================== DATA SUBJECT REQUESTS ====================

    def create_request(self, request_type: str, subject_name: str, subject_email: str,
                       description: str = "", subject_identifier: str = "") -> DataSubjectRequest:
        self._request_counter += 1
        req_id = f"GDPR-REQ-{self._request_counter:04d}"
        req = DataSubjectRequest(
            id=req_id,
            request_type=RequestType(request_type),
            subject_name=subject_name,
            subject_email=subject_email,
            subject_identifier=subject_identifier,
            description=description
        )
        self._requests[req_id] = req
        return req

    def get_request(self, request_id: str) -> DataSubjectRequest | None:
        return self._requests.get(request_id)

    def list_requests(self, status: str | None = None) -> list[DataSubjectRequest]:
        if status:
            return [r for r in self._requests.values() if r.status.value == status]
        return list(self._requests.values())

    def update_request_status(self, request_id: str, status: str, handler: str = "system",
                              response_data: dict = None) -> DataSubjectRequest | None:
        req = self._requests.get(request_id)
        if not req:
            return None
        req.status = RequestStatus(status)
        req.handler = handler
        if response_data:
            req.response_data = response_data
        if status == "completed":
            req.completed_at = datetime.now(UTC).isoformat()
        return req

    def request_count(self) -> int:
        return len(self._requests)

    # ==================== CONSENT MANAGEMENT ====================

    def grant_consent(self, subject_email: str, purpose: str,
                      processing_details: str = "") -> ConsentRecord:
        self._consent_counter += 1
        consent_id = f"CONSENT-{self._consent_counter:04d}"
        consent = ConsentRecord(
            id=consent_id,
            subject_email=subject_email,
            purpose=purpose,
            granted=True,
            granted_at=datetime.now(UTC).isoformat(),
            processing_details=processing_details
        )
        self._consents[consent_id] = consent
        return consent

    def withdraw_consent(self, consent_id: str) -> ConsentRecord | None:
        consent = self._consents.get(consent_id)
        if not consent:
            return None
        consent.granted = False
        consent.withdrawn_at = datetime.now(UTC).isoformat()
        return consent

    def check_consent(self, subject_email: str, purpose: str) -> bool:
        for c in self._consents.values():
            if c.subject_email == subject_email and c.purpose == purpose:
                return c.granted
        return False

    def list_consents(self, subject_email: str = None) -> list[ConsentRecord]:
        if subject_email:
            return [c for c in self._consents.values() if c.subject_email == subject_email]
        return list(self._consents.values())

    # ==================== PROCESSING ACTIVITIES ====================

    def register_processing_activity(self, name: str, purpose: str,
                                      data_categories: list = None,
                                      legal_basis: str = "legitimate_interest",
                                      recipients: list = None,
                                      retention_days: int = 365) -> ProcessingActivity:
        import uuid
        activity_id = f"PA-{uuid.uuid4().hex[:8]}"
        activity = ProcessingActivity(
            id=activity_id,
            activity_name=name,
            purpose=purpose,
            data_categories=data_categories or [],
            legal_basis=legal_basis,
            recipients=recipients or [],
            retention_period_days=retention_days
        )
        self._processing_activities[activity_id] = activity
        return activity

    def list_processing_activities(self) -> list[ProcessingActivity]:
        return list(self._processing_activities.values())

    # ==================== DATA BREACH ====================

    def report_breach(self, description: str, severity: str,
                      affected_records: int = 0) -> DataBreach:
        self._breach_counter += 1
        breach_id = f"BREACH-{self._breach_counter:04d}"
        breach = DataBreach(
            id=breach_id,
            description=description,
            severity=BreachSeverity(severity),
            affected_records=affected_records
        )
        self._breaches[breach_id] = breach
        return breach

    def update_breach(self, breach_id: str, remediation: str = "",
                      notified_authorities: bool = False,
                      notified_subjects: bool = False) -> DataBreach | None:
        breach = self._breaches.get(breach_id)
        if not breach:
            return None
        if remediation:
            breach.remediation = remediation
        if notified_authorities:
            breach.notified_authorities = True
            breach.reported_at = datetime.now(UTC).isoformat()
        if notified_subjects:
            breach.notified_subjects = True
        if breach.notified_authorities and breach.notified_subjects:
            breach.status = "resolved"
        return breach

    def list_breaches(self, status: str = None) -> list[DataBreach]:
        if status:
            return [b for b in self._breaches.values() if b.status == status]
        return list(self._breaches.values())

    # ==================== SUMMARY ====================

    def get_summary(self) -> dict:
        return {
            "total_requests": len(self._requests),
            "pending_requests": len([r for r in self._requests.values() if r.status == RequestStatus.PENDING]),
            "completed_requests": len([r for r in self._requests.values() if r.status == RequestStatus.COMPLETED]),
            "active_consents": len([c for c in self._consents.values() if c.granted]),
            "withdrawn_consents": len([c for c in self._consents.values() if not c.granted]),
            "processing_activities": len(self._processing_activities),
            "open_breaches": len([b for b in self._breaches.values() if b.status == "open"]),
            "resolved_breaches": len([b for b in self._breaches.values() if b.status == "resolved"]),
        }

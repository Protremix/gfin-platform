"""GFIN Pilot — Module 39.

Pilot program management: pilot deployments, participant tracking,
feedback collection, and pilot success criteria evaluation.

Layer A: In-memory pilot management
Layer B: Real pilot deployment tracking (REQUIRES EXTERNAL INFRASTRUCTURE)
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PilotStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ParticipantStatus(str, Enum):
    INVITED = "INVITED"
    ENROLLED = "ENROLLED"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"


class PilotParticipant(BaseModel):
    """A pilot program participant."""

    id: str
    pilot_id: str
    name: str = ""
    organization: str = ""
    jurisdiction: str = ""
    role: str = ""
    status: str = ParticipantStatus.INVITED.value
    enrolled_at: datetime | None = None
    feedback: list[dict[str, Any]] = Field(default_factory=list)

    def enroll(self) -> None:
        self.status = ParticipantStatus.ENROLLED.value
        self.enrolled_at = datetime.now(UTC)

    def activate(self) -> None:
        self.status = ParticipantStatus.ACTIVE.value

    def withdraw(self) -> None:
        self.status = ParticipantStatus.WITHDRAWN.value

    def add_feedback(self, rating: int, comment: str = "") -> None:
        self.feedback.append(
            {
                "rating": rating,
                "comment": comment,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    @property
    def avg_rating(self) -> float:
        if not self.feedback:
            return 0.0
        return sum(f["rating"] for f in self.feedback) / len(self.feedback)


class PilotProgram(BaseModel):
    """A pilot program."""

    id: str
    name: str
    description: str = ""
    status: str = PilotStatus.PLANNED.value
    start_date: datetime | None = None
    end_date: datetime | None = None
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def activate(self, start_date: datetime | None = None) -> None:
        self.status = PilotStatus.ACTIVE.value
        self.start_date = start_date or datetime.now(UTC)

    def complete(self, end_date: datetime | None = None) -> None:
        self.status = PilotStatus.COMPLETED.value
        self.end_date = end_date or datetime.now(UTC)

    def pause(self) -> None:
        self.status = PilotStatus.PAUSED.value

    def cancel(self) -> None:
        self.status = PilotStatus.CANCELLED.value


class PilotService:
    """Service for managing pilot programs.

    Per development phases: pilot is Phase 10 (Module 39).
    """

    def __init__(self) -> None:
        self._programs: dict[str, PilotProgram] = {}
        self._participants: dict[str, PilotParticipant] = {}
        self._program_counter = 0
        self._participant_counter = 0

    def create_program(
        self, name: str, description: str = "", success_criteria: dict[str, Any] | None = None
    ) -> PilotProgram:
        self._program_counter += 1
        program = PilotProgram(
            id=f"PILOT-{self._program_counter:06d}",
            name=name,
            description=description,
            success_criteria=success_criteria or {},
        )
        self._programs[program.id] = program
        return program

    def get_program(self, program_id: str) -> PilotProgram | None:
        return self._programs.get(program_id)

    def list_programs(self, status: str | None = None) -> list[PilotProgram]:
        programs = list(self._programs.values())
        if status:
            programs = [p for p in programs if p.status == status]
        return programs

    def activate_program(self, program_id: str) -> bool:
        program = self._programs.get(program_id)
        if program is None:
            return False
        program.activate()
        return True

    def complete_program(self, program_id: str) -> bool:
        program = self._programs.get(program_id)
        if program is None:
            return False
        program.complete()
        return True

    def pause_program(self, program_id: str) -> bool:
        program = self._programs.get(program_id)
        if program is None:
            return False
        program.pause()
        return True

    def cancel_program(self, program_id: str) -> bool:
        program = self._programs.get(program_id)
        if program is None:
            return False
        program.cancel()
        return True

    def add_participant(
        self,
        pilot_id: str,
        name: str = "",
        organization: str = "",
        jurisdiction: str = "",
        role: str = "",
    ) -> PilotParticipant | None:
        if pilot_id not in self._programs:
            return None
        self._participant_counter += 1
        participant = PilotParticipant(
            id=f"PART-{self._participant_counter:06d}",
            pilot_id=pilot_id,
            name=name,
            organization=organization,
            jurisdiction=jurisdiction,
            role=role,
        )
        self._participants[participant.id] = participant
        return participant

    def get_participant(self, participant_id: str) -> PilotParticipant | None:
        return self._participants.get(participant_id)

    def list_participants(
        self, pilot_id: str | None = None, status: str | None = None
    ) -> list[PilotParticipant]:
        participants = list(self._participants.values())
        if pilot_id:
            participants = [p for p in participants if p.pilot_id == pilot_id]
        if status:
            participants = [p for p in participants if p.status == status]
        return participants

    def enroll_participant(self, participant_id: str) -> bool:
        p = self._participants.get(participant_id)
        if p is None:
            return False
        p.enroll()
        return True

    def activate_participant(self, participant_id: str) -> bool:
        p = self._participants.get(participant_id)
        if p is None:
            return False
        p.activate()
        return True

    def withdraw_participant(self, participant_id: str) -> bool:
        p = self._participants.get(participant_id)
        if p is None:
            return False
        p.withdraw()
        return True

    def add_feedback(self, participant_id: str, rating: int, comment: str = "") -> bool:
        p = self._participants.get(participant_id)
        if p is None:
            return False
        p.add_feedback(rating, comment)
        return True

    def get_program_summary(self, program_id: str) -> dict[str, Any]:
        program = self._programs.get(program_id)
        if program is None:
            return {}
        participants = [p for p in self._participants.values() if p.pilot_id == program_id]
        active = [p for p in participants if p.status == ParticipantStatus.ACTIVE.value]
        all_feedback = [f for p in participants for f in p.feedback]
        avg_rating = (
            sum(f["rating"] for f in all_feedback) / len(all_feedback) if all_feedback else 0
        )
        return {
            "program_id": program_id,
            "name": program.name,
            "status": program.status,
            "total_participants": len(participants),
            "active_participants": len(active),
            "total_feedback": len(all_feedback),
            "avg_rating": round(avg_rating, 2),
        }

    @property
    def program_count(self) -> int:
        return len(self._programs)

    @property
    def participant_count(self) -> int:
        return len(self._participants)

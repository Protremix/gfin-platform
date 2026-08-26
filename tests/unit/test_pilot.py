"""Tests for Pilot — Module 39."""

import pytest

from services.pilot import (
    ParticipantStatus,
    PilotParticipant,
    PilotService,
    PilotStatus,
)


@pytest.fixture
def service():
    return PilotService()


@pytest.fixture
def program(service):
    return service.create_program("GFIN Pilot Q1", "First pilot deployment")


class TestPilotProgram:
    def test_activate(self, program):
        program.activate()
        assert program.status == PilotStatus.ACTIVE.value
        assert program.start_date is not None

    def test_complete(self, program):
        program.activate()
        program.complete()
        assert program.status == PilotStatus.COMPLETED.value
        assert program.end_date is not None

    def test_pause(self, program):
        program.activate()
        program.pause()
        assert program.status == PilotStatus.PAUSED.value

    def test_cancel(self, program):
        program.cancel()
        assert program.status == PilotStatus.CANCELLED.value


class TestPilotParticipant:
    def test_enroll(self):
        p = PilotParticipant(id="P1", pilot_id="PILOT-001", name="Smith")
        p.enroll()
        assert p.status == ParticipantStatus.ENROLLED.value
        assert p.enrolled_at is not None

    def test_activate(self):
        p = PilotParticipant(id="P1", pilot_id="PILOT-001", name="Smith")
        p.activate()
        assert p.status == ParticipantStatus.ACTIVE.value

    def test_withdraw(self):
        p = PilotParticipant(id="P1", pilot_id="PILOT-001", name="Smith")
        p.withdraw()
        assert p.status == ParticipantStatus.WITHDRAWN.value

    def test_add_feedback(self):
        p = PilotParticipant(id="P1", pilot_id="PILOT-001", name="Smith")
        p.add_feedback(5, "Great system")
        p.add_feedback(4, "Needs improvement")
        assert len(p.feedback) == 2
        assert p.avg_rating == 4.5

    def test_avg_rating_empty(self):
        p = PilotParticipant(id="P1", pilot_id="PILOT-001", name="Smith")
        assert p.avg_rating == 0.0


class TestPilotService:
    def test_create_program(self, service):
        p = service.create_program("Test Pilot")
        assert p.id.startswith("PILOT-")
        assert service.program_count == 1

    def test_get_program(self, service, program):
        assert service.get_program(program.id) is not None
        assert service.get_program("nonexistent") is None

    def test_list_programs(self, service):
        service.create_program("A")
        service.create_program("B")
        assert len(service.list_programs()) == 2

    def test_list_programs_by_status(self, service):
        p = service.create_program("A")
        service.activate_program(p.id)
        service.create_program("B")
        active = service.list_programs(status=PilotStatus.ACTIVE.value)
        planned = service.list_programs(status=PilotStatus.PLANNED.value)
        assert len(active) == 1
        assert len(planned) == 1

    def test_activate_program(self, service, program):
        assert service.activate_program(program.id) is True
        assert service.activate_program("nonexistent") is False

    def test_complete_program(self, service, program):
        assert service.complete_program(program.id) is True
        assert service.complete_program("nonexistent") is False

    def test_pause_program(self, service, program):
        assert service.pause_program(program.id) is True

    def test_cancel_program(self, service, program):
        assert service.cancel_program(program.id) is True

    def test_add_participant(self, service, program):
        p = service.add_participant(program.id, "Det. Smith", "BKA", "DE", "officer")
        assert p.id.startswith("PART-")
        assert service.participant_count == 1

    def test_add_participant_nonexistent_program(self, service):
        assert service.add_participant("nonexistent") is None

    def test_get_participant(self, service, program):
        p = service.add_participant(program.id, "Smith")
        assert service.get_participant(p.id) is not None
        assert service.get_participant("nonexistent") is None

    def test_list_participants(self, service, program):
        service.add_participant(program.id, "A")
        service.add_participant(program.id, "B")
        assert len(service.list_participants(pilot_id=program.id)) == 2

    def test_list_participants_by_status(self, service, program):
        p1 = service.add_participant(program.id, "A")
        p2 = service.add_participant(program.id, "B")
        service.enroll_participant(p1.id)
        enrolled = service.list_participants(status=ParticipantStatus.ENROLLED.value)
        invited = service.list_participants(status=ParticipantStatus.INVITED.value)
        assert len(enrolled) == 1
        assert len(invited) == 1

    def test_enroll_participant(self, service, program):
        p = service.add_participant(program.id, "Smith")
        assert service.enroll_participant(p.id) is True
        assert service.enroll_participant("nonexistent") is False

    def test_activate_participant(self, service, program):
        p = service.add_participant(program.id, "Smith")
        assert service.activate_participant(p.id) is True

    def test_withdraw_participant(self, service, program):
        p = service.add_participant(program.id, "Smith")
        assert service.withdraw_participant(p.id) is True

    def test_add_feedback(self, service, program):
        p = service.add_participant(program.id, "Smith")
        assert service.add_feedback(p.id, 5, "Great") is True
        assert service.add_feedback("nonexistent", 5) is False

    def test_program_summary(self, service, program):
        service.add_participant(program.id, "A", "BKA", "DE")
        service.add_participant(program.id, "B", "DGSI", "FR")
        summary = service.get_program_summary(program.id)
        assert summary["total_participants"] == 2
        assert summary["status"] == PilotStatus.PLANNED.value

    def test_program_summary_nonexistent(self, service):
        assert service.get_program_summary("nonexistent") == {}

    def test_program_summary_with_feedback(self, service, program):
        p1 = service.add_participant(program.id, "A")
        p2 = service.add_participant(program.id, "B")
        service.add_feedback(p1.id, 4, "Good")
        service.add_feedback(p2.id, 5, "Excellent")
        summary = service.get_program_summary(program.id)
        assert summary["total_feedback"] == 2
        assert summary["avg_rating"] == 4.5

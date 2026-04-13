"""Tests for sprint note injection into agent context."""

import pytest

from agents.blueprints.base import WorkforceBlueprint
from agents.models import Agent, AgentTask
from projects.models import Department, Project, Sprint, SprintNote


class ConcreteWorkforceBlueprint(WorkforceBlueprint):
    """Minimal concrete subclass for testing BaseBlueprint methods."""

    @property
    def system_prompt(self) -> str:
        return "Test system prompt"


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(email="test@test.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test", goal="Test goal", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="writers_room", project=project)


@pytest.fixture
def sprint(project, department, user):
    s = Sprint.objects.create(project=project, text="Write a pitch", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Test Agent",
        agent_type="test_agent",
        department=department,
        status="active",
    )


@pytest.fixture
def task(agent, sprint):
    return AgentTask.objects.create(
        agent=agent,
        sprint=sprint,
        exec_summary="Test task",
        step_plan="Do something",
        status="processing",
    )


@pytest.mark.django_db
class TestSprintNotesInContext:
    def test_notes_appear_in_task_message(self, agent, task, sprint, user):
        SprintNote.objects.create(sprint=sprint, user=user, text="Change the name to Kaya")
        SprintNote.objects.create(sprint=sprint, user=user, text="Make the ending ambiguous")

        bp = ConcreteWorkforceBlueprint()
        bp._system_prompt = "Test"
        _, msg = bp.build_task_message(agent, task)

        assert "Change the name to Kaya" in msg
        assert "Make the ending ambiguous" in msg
        assert "User Notes" in msg

    def test_no_notes_section_when_empty(self, agent, task, sprint):
        bp = ConcreteWorkforceBlueprint()
        bp._system_prompt = "Test"
        _, msg = bp.build_task_message(agent, task)

        assert "User Notes" not in msg

    def test_note_sources_appear(self, agent, task, sprint, user, project):
        from projects.models import Source

        source = Source.objects.create(
            project=project,
            source_type="text",
            raw_content="Reference doc content",
            original_filename="reference.md",
            user=user,
        )
        note = SprintNote.objects.create(sprint=sprint, user=user, text="See attached")
        note.sources.add(source)

        bp = ConcreteWorkforceBlueprint()
        bp._system_prompt = "Test"
        _, msg = bp.build_task_message(agent, task)

        assert "reference.md" in msg
        assert "Reference doc content" in msg

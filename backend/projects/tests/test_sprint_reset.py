"""Tests for the Reset Sprint admin action."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from agents.models import Agent, AgentTask, ClonedAgent
from projects.admin.sprint_admin import SprintAdmin
from projects.models import Department, Document, Output, Project, Sprint


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_superuser(email="admin@test.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test Project", goal="Test", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="sales", project=project)


@pytest.fixture
def sprint(department, user):
    s = Sprint.objects.create(project=department.project, text="Test sprint", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.fixture
def leader(department):
    return Agent.objects.create(
        name="Head of Sales",
        agent_type="leader",
        department=department,
        is_leader=True,
        status="active",
    )


@pytest.fixture
def workforce(department):
    agents = {}
    for slug in ["researcher", "strategist", "pitch_personalizer", "sales_qa", "email_outreach"]:
        agents[slug] = Agent.objects.create(
            name=f"Test {slug}",
            agent_type=slug,
            department=department,
            status="active",
            outreach=(slug == "email_outreach"),
        )
    return agents


def _run_reset(sprint, user):
    """Helper to run the admin action."""
    admin_instance = SprintAdmin(Sprint, AdminSite())
    request = RequestFactory().post("/admin/")
    request.user = user
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    admin_instance.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))


@pytest.mark.django_db
class TestResetSprint:
    def test_deletes_tasks(self, sprint, leader, workforce, user):
        AgentTask.objects.create(
            agent=workforce["researcher"], sprint=sprint, command_name="research-industry", status="done", report="Done"
        )
        AgentTask.objects.create(
            agent=workforce["strategist"], sprint=sprint, command_name="draft-strategy", status="done", report="Done"
        )

        _run_reset(sprint, user)
        assert AgentTask.objects.filter(sprint=sprint).count() == 0

    def test_deletes_clones(self, sprint, workforce, user):
        parent = workforce["pitch_personalizer"]
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)

        _run_reset(sprint, user)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_deletes_documents(self, sprint, department, user):
        Document.objects.create(title="Test", content="X", department=department, doc_type="research", sprint=sprint)

        _run_reset(sprint, user)
        assert Document.objects.filter(sprint=sprint).count() == 0

    def test_deletes_outputs(self, sprint, department, user):
        Output.objects.create(sprint=sprint, department=department, title="Test", label="outreach", content="X")

        _run_reset(sprint, user)
        assert Output.objects.filter(sprint=sprint).count() == 0

    def test_clears_department_state(self, sprint, department, user):
        sprint.set_department_state(department.id, {"pipeline_step": "finalize"})

        _run_reset(sprint, user)
        sprint.refresh_from_db()
        assert sprint.department_state == {}

    def test_resets_status_to_running(self, sprint, department, user):
        from django.utils import timezone

        sprint.status = "done"
        sprint.completion_summary = "Completed"
        sprint.completed_at = timezone.now()
        sprint.save()

        _run_reset(sprint, user)
        sprint.refresh_from_db()
        assert sprint.status == "running"
        assert sprint.completion_summary == ""
        assert sprint.completed_at is None

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from agents.models import Agent, AgentTask
from projects.models import Department, Project

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="agent-tester@example.com", password="pass1234")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@example.com", password="pass1234")


@pytest.fixture
def project(user):
    p = Project.objects.create(name="Agent Test Project", goal="Test", owner=user)
    p.members.add(user)
    return p


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        is_leader=False,
        status="active",
        instructions="Tweet stuff",
    )


@pytest.fixture
def leader(department):
    return Agent.objects.create(
        name="Marketing Lead",
        agent_type="leader",
        department=department,
        is_leader=True,
        status="active",
    )


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


# ── ProjectTaskListView ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProjectTaskListView:
    def test_returns_tasks(self, authed_client, project, agent):
        AgentTask.objects.create(agent=agent, exec_summary="Task 1")
        AgentTask.objects.create(agent=agent, exec_summary="Task 2")
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_requires_auth(self, api_client, project):
        resp = api_client.get(f"/api/projects/{project.id}/tasks/")
        assert resp.status_code in (401, 403)

    def test_only_shows_member_tasks(self, api_client, other_user, project, agent):
        AgentTask.objects.create(agent=agent, exec_summary="Secret task")
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/projects/{project.id}/tasks/")
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_filter_by_status_single(self, authed_client, project, agent):
        AgentTask.objects.create(agent=agent, exec_summary="Queued", status=AgentTask.Status.QUEUED)
        AgentTask.objects.create(agent=agent, exec_summary="Done", status=AgentTask.Status.DONE)
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?status=queued")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["status"] == "queued"

    def test_filter_by_status_comma_separated(self, authed_client, project, agent):
        AgentTask.objects.create(agent=agent, exec_summary="Queued", status=AgentTask.Status.QUEUED)
        AgentTask.objects.create(agent=agent, exec_summary="Waiting", status=AgentTask.Status.AWAITING_APPROVAL)
        AgentTask.objects.create(agent=agent, exec_summary="Done", status=AgentTask.Status.DONE)
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?status=queued,awaiting_approval")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_x_total_count_header(self, authed_client, project, agent):
        for _ in range(5):
            AgentTask.objects.create(agent=agent, exec_summary="Task", status=AgentTask.Status.QUEUED)
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?status=queued&limit=2")
        assert resp.status_code == 200
        assert resp["X-Total-Count"] == "5"
        assert len(resp.data) == 2

    def test_filter_by_department(self, authed_client, project, agent, department):
        AgentTask.objects.create(agent=agent, exec_summary="In dept")
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?department={department.id}")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_filter_by_agent(self, authed_client, project, agent):
        AgentTask.objects.create(agent=agent, exec_summary="Agent task")
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?agent={agent.id}")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_pagination_before_cursor(self, authed_client, project, agent):
        import urllib.parse

        t1 = AgentTask.objects.create(agent=agent, exec_summary="Older")
        # Use the older task's created_at as cursor — nothing before it
        before_val = urllib.parse.quote(t1.created_at.isoformat())
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?before={before_val}&limit=10")
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_limit_caps_at_100(self, authed_client, project, agent):
        # Just ensure limit=200 doesn't crash
        resp = authed_client.get(f"/api/projects/{project.id}/tasks/?limit=200")
        assert resp.status_code == 200


# ── TaskApproveView ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskApproveView:
    @patch("agents.tasks.execute_agent_task")
    def test_approve_changes_status(self, mock_exec, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent, exec_summary="Approve me", status=AgentTask.Status.AWAITING_APPROVAL
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/approve/")
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED

    @patch("agents.tasks.execute_agent_task")
    def test_approve_edits_step_plan_and_summary(self, mock_exec, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Original",
            step_plan="Old plan",
            status=AgentTask.Status.AWAITING_APPROVAL,
        )
        resp = authed_client.post(
            f"/api/projects/{project.id}/tasks/{task.id}/approve/",
            {"step_plan": "New plan", "exec_summary": "Updated summary"},
            format="json",
        )
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.step_plan == "New plan"
        assert task.exec_summary == "Updated summary"

    def test_approve_rejects_non_awaiting_task(self, authed_client, project, agent):
        task = AgentTask.objects.create(agent=agent, exec_summary="Already done", status=AgentTask.Status.DONE)
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/approve/")
        assert resp.status_code == 400
        assert "not awaiting_approval" in resp.data["error"]

    def test_approve_requires_membership(self, api_client, other_user, project, agent):
        task = AgentTask.objects.create(agent=agent, exec_summary="Task", status=AgentTask.Status.AWAITING_APPROVAL)
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(f"/api/projects/{project.id}/tasks/{task.id}/approve/")
        assert resp.status_code == 404


# ── TaskRejectView ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskRejectView:
    def test_reject_changes_status_to_failed(self, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent, exec_summary="Reject me", status=AgentTask.Status.AWAITING_APPROVAL
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/reject/")
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == AgentTask.Status.FAILED
        assert task.error_message == "Rejected"
        assert task.completed_at is not None

    def test_reject_non_awaiting_returns_400(self, authed_client, project, agent):
        task = AgentTask.objects.create(agent=agent, exec_summary="Processing", status=AgentTask.Status.PROCESSING)
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/reject/")
        assert resp.status_code == 400


# ── Broadcast WebSocket on approve/reject ────────────────────────────────────


@pytest.mark.django_db
class TestTaskBroadcast:
    @patch("agents.views.agent_task_view._broadcast_task")
    @patch("agents.tasks.create_next_leader_task.delay")
    @patch("agents.tasks.execute_agent_task.delay")
    def test_approve_calls_broadcast(
        self, mock_exec_delay, mock_next_leader_delay, mock_broadcast, authed_client, project, agent
    ):
        task = AgentTask.objects.create(
            agent=agent, exec_summary="Broadcast on approve", status=AgentTask.Status.AWAITING_APPROVAL
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/approve/")
        assert resp.status_code == 200
        mock_broadcast.assert_called_once()
        broadcast_arg = mock_broadcast.call_args[0][0]
        assert broadcast_arg.id == task.id

    @patch("agents.views.agent_task_view._broadcast_task")
    def test_reject_calls_broadcast(self, mock_broadcast, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent, exec_summary="Broadcast on reject", status=AgentTask.Status.AWAITING_APPROVAL
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/reject/")
        assert resp.status_code == 200
        mock_broadcast.assert_called_once()
        broadcast_arg = mock_broadcast.call_args[0][0]
        assert broadcast_arg.id == task.id


# ── TaskRetryView ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaskRetryView:
    @patch("agents.tasks.execute_agent_task")
    def test_retry_requeues_failed_task(self, mock_exec, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Failed task",
            status=AgentTask.Status.FAILED,
            error_message="Worker died",
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED
        assert task.error_message == ""
        assert task.report == ""
        assert task.started_at is None
        assert task.completed_at is None
        mock_exec.delay.assert_called_once_with(str(task.id))

    def test_retry_rejects_non_failed_task(self, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Processing task",
            status=AgentTask.Status.PROCESSING,
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 400

    def test_retry_requires_membership(self, api_client, other_user, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Failed task",
            status=AgentTask.Status.FAILED,
        )
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 404


# ── AgentUpdateView ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAgentUpdateView:
    def test_patch_updates_instructions(self, authed_client, agent):
        resp = authed_client.patch(
            f"/api/agents/{agent.id}/",
            {"instructions": "New instructions"},
            format="json",
        )
        assert resp.status_code == 200
        agent.refresh_from_db()
        assert agent.instructions == "New instructions"

    def test_patch_updates_status(self, authed_client, agent):
        resp = authed_client.patch(
            f"/api/agents/{agent.id}/",
            {"status": "inactive"},
            format="json",
        )
        assert resp.status_code == 200
        agent.refresh_from_db()
        assert agent.status == "inactive"

    def test_patch_requires_membership(self, api_client, other_user, agent):
        api_client.force_authenticate(user=other_user)
        resp = api_client.patch(
            f"/api/agents/{agent.id}/",
            {"instructions": "Hacked"},
            format="json",
        )
        assert resp.status_code == 404


# ── AddAgentView ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAddAgentView:
    @patch("projects.tasks.provision_single_agent.delay")
    def test_add_agent_to_department(self, mock_provision, authed_client, department):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "web_researcher"},
            format="json",
        )
        assert resp.status_code == 202
        assert resp.data["agent_type"] == "web_researcher"
        assert resp.data["status"] == "provisioning"
        mock_provision.assert_called_once()

    @patch("projects.tasks.provision_single_agent.delay")
    def test_rejects_unknown_agent_type(self, mock_provision, authed_client, department):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "nonexistent"},
            format="json",
        )
        assert resp.status_code == 400

    @patch("projects.tasks.provision_single_agent.delay")
    def test_rejects_duplicate_agent(self, mock_provision, authed_client, department, agent):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "twitter"},
            format="json",
        )
        assert resp.status_code == 400
        assert "already exists" in resp.data["error"].lower()

    def test_requires_membership(self, api_client, other_user, department):
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "web_researcher"},
            format="json",
        )
        assert resp.status_code == 404


# ── AgentBlueprintView ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAgentBlueprintView:
    def test_returns_blueprint_info(self, authed_client, agent):
        resp = authed_client.get(f"/api/agents/{agent.id}/blueprint/")
        assert resp.status_code == 200
        assert "name" in resp.data
        assert "commands" in resp.data
        assert "config_schema" in resp.data

    def test_requires_membership(self, api_client, other_user, agent):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(f"/api/agents/{agent.id}/blueprint/")
        assert resp.status_code == 404

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.db import IntegrityError
from django.utils import timezone

from agents.models import Agent, AgentTask
from projects.models import Project, Department


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(email="test@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test Project", goal="Ship it", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(name="Marketing", project=project)


@pytest.fixture
def department2(project):
    return Department.objects.create(name="Engineering", project=project)


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        is_leader=False,
        instructions="Be nice",
        config={"api_key": "xxx"},
        auto_actions={"engage-tweets": True, "post-content": False},
    )


@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Department Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
    )


# ── Agent model tests ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAgentModel:
    def test_create_with_all_fields(self, agent):
        assert agent.pk is not None
        assert agent.name == "Twitter Bot"
        assert agent.agent_type == "twitter"
        assert agent.instructions == "Be nice"
        assert agent.config == {"api_key": "xxx"}
        assert agent.auto_actions == {"engage-tweets": True, "post-content": False}
        assert agent.is_active is True
        assert agent.is_leader is False
        assert agent.created_at is not None

    def test_is_leader_unique_per_department(self, leader_agent, department):
        with pytest.raises(IntegrityError):
            Agent.objects.create(
                name="Second Leader",
                agent_type="leader",
                department=department,
                is_leader=True,
            )

    def test_is_leader_allowed_across_departments(self, leader_agent, department2):
        second_leader = Agent.objects.create(
            name="Eng Leader",
            agent_type="leader",
            department=department2,
            is_leader=True,
        )
        assert second_leader.pk is not None

    def test_is_action_enabled_true(self, agent):
        assert agent.is_action_enabled("engage-tweets") is True

    def test_is_action_enabled_false(self, agent):
        assert agent.is_action_enabled("post-content") is False

    def test_is_action_enabled_missing_key(self, agent):
        assert agent.is_action_enabled("nonexistent") is False

    def test_get_blueprint_returns_correct_instance(self, agent):
        from agents.blueprints.twitter.agent import TwitterBlueprint
        bp = agent.get_blueprint()
        assert isinstance(bp, TwitterBlueprint)

    def test_str_non_leader(self, agent):
        assert str(agent) == "Twitter Bot (twitter)"

    def test_str_leader(self, leader_agent):
        assert str(leader_agent) == "Department Leader (leader) [LEADER]"


# ── AgentTask model tests ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestAgentTaskModel:
    def test_status_choices(self):
        slugs = {c[0] for c in AgentTask.Status.choices}
        assert slugs == {
            "awaiting_approval",
            "planned",
            "queued",
            "processing",
            "done",
            "failed",
        }

    @patch("agents.tasks.execute_agent_task")
    def test_approve_transitions_to_queued(self, mock_exec, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Do stuff",
        )
        result = task.approve()
        assert result is True
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED
        mock_exec.delay.assert_called_once_with(str(task.id))

    @patch("agents.tasks.create_next_leader_task")
    @patch("agents.tasks.execute_agent_task")
    def test_approve_transitions_to_planned_for_future(self, mock_exec, mock_next, agent):
        future = timezone.now() + timedelta(hours=2)
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Future task",
            proposed_exec_at=future,
        )
        result = task.approve()
        assert result is True
        task.refresh_from_db()
        assert task.status == AgentTask.Status.PLANNED
        assert task.scheduled_at == future
        mock_exec.apply_async.assert_called_once()

    @patch("agents.tasks.execute_agent_task")
    def test_approve_on_non_awaiting_returns_false(self, mock_exec, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.QUEUED,
            exec_summary="Already queued",
        )
        result = task.approve()
        assert result is False
        mock_exec.delay.assert_not_called()

    @patch("agents.tasks.create_next_leader_task")
    @patch("agents.tasks.execute_agent_task")
    def test_approve_triggers_create_next_leader_task_for_leaders(
        self, mock_exec, mock_next, leader_agent
    ):
        task = AgentTask.objects.create(
            agent=leader_agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Leader task",
        )
        task.approve()
        mock_next.delay.assert_called_once_with(str(leader_agent.id))

    @patch("agents.tasks.execute_agent_task")
    def test_approve_does_not_trigger_next_for_non_leader(self, mock_exec, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Worker task",
        )
        with patch("agents.tasks.create_next_leader_task") as mock_next:
            task.approve()
            mock_next.delay.assert_not_called()

    def test_str_format(self, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Engage with high-impact tweets in the crypto space right now",
        )
        s = str(task)
        assert s.startswith("[Awaiting Approval]")
        assert "Twitter Bot" in s
        assert "Engage with" in s

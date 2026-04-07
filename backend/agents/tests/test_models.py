from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from agents.models import Agent, AgentTask
from projects.models import Department, Project


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
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def department2(user):
    project2 = Project.objects.create(name="Other Project", goal="Other goal", owner=user)
    return Department.objects.create(department_type="marketing", project=project2)


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        is_leader=False,
        status=Agent.Status.ACTIVE,
        instructions="Be nice",
        config={"api_key": "xxx"},
        enabled_commands={"post-content": True, "place-content": True, "search-trends": True},
    )


@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Department Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
        status=Agent.Status.ACTIVE,
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
        assert agent.enabled_commands == {"post-content": True, "place-content": True, "search-trends": True}
        assert agent.status == Agent.Status.ACTIVE
        assert agent.is_leader is False
        assert agent.created_at is not None

    def test_status_choices(self, agent):
        assert set(Agent.Status.values) == {"provisioning", "active", "inactive", "failed"}

    def test_default_status_is_provisioning(self, department):
        a = Agent.objects.create(name="New", agent_type="twitter", department=department)
        assert a.status == Agent.Status.PROVISIONING

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

    def test_enabled_commands_default_empty(self, department):
        a = Agent.objects.create(name="New", agent_type="twitter", department=department)
        assert a.enabled_commands == {}

    def test_is_action_enabled_true_when_command_enabled(self, department):
        a = Agent.objects.create(
            name="Test",
            agent_type="twitter",
            department=department,
            status=Agent.Status.ACTIVE,
            enabled_commands={"post-content": True},
        )
        assert a.is_action_enabled("post-content") is True

    def test_is_action_enabled_false_when_command_disabled(self, department):
        a = Agent.objects.create(
            name="Test",
            agent_type="twitter",
            department=department,
            status=Agent.Status.ACTIVE,
            enabled_commands={"post-content": False},
        )
        assert a.is_action_enabled("post-content") is False

    def test_is_action_enabled_false_when_command_absent(self, department):
        a = Agent.objects.create(
            name="Test",
            agent_type="twitter",
            department=department,
            status=Agent.Status.ACTIVE,
            enabled_commands={"research": True},
        )
        assert a.is_action_enabled("post-content") is False

    def test_all_commands_enabled(self, department):
        a = Agent.objects.create(
            name="Test",
            agent_type="twitter",
            department=department,
            status=Agent.Status.ACTIVE,
            enabled_commands={"post-content": True, "search-trends": True},
        )
        assert a.all_commands_enabled is True

    def test_all_commands_enabled_false_when_mixed(self, department):
        a = Agent.objects.create(
            name="Test",
            agent_type="twitter",
            department=department,
            status=Agent.Status.ACTIVE,
            enabled_commands={"post-content": True, "search-trends": False},
        )
        assert a.all_commands_enabled is False

    def test_get_blueprint_returns_correct_instance(self, agent):
        from agents.blueprints.marketing.workforce.twitter.agent import TwitterBlueprint

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
            "awaiting_dependencies",
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
            command_name="post-content",
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
            command_name="post-content",
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
            command_name="post-content",
        )
        result = task.approve()
        assert result is False
        mock_exec.delay.assert_not_called()

    @patch("agents.tasks.create_next_leader_task")
    @patch("agents.tasks.execute_agent_task")
    def test_approve_triggers_create_next_leader_task_for_leaders(self, mock_exec, mock_next, leader_agent):
        task = AgentTask.objects.create(
            agent=leader_agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Leader task",
            command_name="post-content",
        )
        task.approve()
        mock_next.delay.assert_called_once_with(str(leader_agent.id))

    @patch("agents.tasks.execute_agent_task")
    def test_approve_does_not_trigger_next_for_non_leader(self, mock_exec, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Worker task",
            command_name="post-content",
        )
        with patch("agents.tasks.create_next_leader_task") as mock_next:
            task.approve()
            mock_next.delay.assert_not_called()

    def test_command_name_required(self, agent):
        from django.core.exceptions import ValidationError

        task = AgentTask(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="No command",
            command_name="",
        )
        with pytest.raises(ValidationError, match="command_name"):
            task.full_clean()

    def test_command_name_validated_against_blueprint(self, agent):
        from django.core.exceptions import ValidationError

        task = AgentTask(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Invalid command",
            command_name="nonexistent_command",
        )
        with pytest.raises(ValidationError, match="not a valid command"):
            task.full_clean()

    def test_valid_command_name_passes_validation(self, agent):
        task = AgentTask(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Valid command",
            command_name="post-content",
        )
        task.full_clean()  # Should not raise

    def test_str_format(self, agent):
        task = AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary="Engage with high-impact tweets in the crypto space right now",
            command_name="post-content",
        )
        s = str(task)
        assert s.startswith("[Awaiting Approval]")
        assert "Twitter Bot" in s
        assert "Engage with" in s


# ── AgentTask review fields tests ───────────────────────────────────────────


@pytest.mark.django_db
class TestAgentTaskReviewFields:
    def test_review_fields_default_empty(self, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Default fields check",
            command_name="post-content",
        )
        task.refresh_from_db()
        assert task.review_verdict == ""
        assert task.review_score is None

    def test_review_fields_persist(self, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Review fields persist check",
            command_name="post-content",
            review_verdict="APPROVED",
            review_score=9.5,
        )
        task.refresh_from_db()
        assert task.review_verdict == "APPROVED"
        assert task.review_score == 9.5

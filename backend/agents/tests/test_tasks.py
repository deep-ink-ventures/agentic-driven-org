import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone

from agents.models import Agent, AgentTask
from projects.models import Project, Department


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(email="test@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="TestProj", goal="Ship", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def twitter_agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        auto_actions={"place-content": True, "post-content": False},
    )


@pytest.fixture
def twitter_agent_disabled(department):
    return Agent.objects.create(
        name="Twitter Disabled",
        agent_type="twitter",
        department=department,
        auto_actions={},
    )


@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
        auto_actions={"create-priority-task": True},
    )


@pytest.fixture
def inactive_leader(department):
    """An inactive leader for skip tests. Needs different project to avoid unique constraint."""
    from accounts.models import User
    user2 = User.objects.create_user(email="other@example.com", password="pass")
    project2 = Project.objects.create(name="Other", goal="Other", owner=user2)
    dept2 = Department.objects.create(department_type="marketing", project=project2)
    return Agent.objects.create(
        name="Inactive Leader",
        agent_type="leader",
        department=dept2,
        is_leader=True,
        is_active=False,
    )


# ── run_scheduled_actions ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRunScheduledActions:
    @patch("agents.tasks.execute_agent_task")
    def test_hourly_creates_tasks_for_enabled(self, mock_exec, twitter_agent):
        from agents.tasks import run_scheduled_actions

        run_scheduled_actions("hourly")

        # engage-tweets is hourly + enabled => task created
        tasks = AgentTask.objects.filter(agent=twitter_agent)
        assert tasks.count() == 1
        t = tasks.first()
        assert t.status == AgentTask.Status.QUEUED
        assert t.auto_execute is True
        mock_exec.delay.assert_called_once_with(str(t.id))

    @patch("agents.tasks.execute_agent_task")
    def test_hourly_skips_disabled(self, mock_exec, twitter_agent_disabled):
        from agents.tasks import run_scheduled_actions

        run_scheduled_actions("hourly")

        tasks = AgentTask.objects.filter(agent=twitter_agent_disabled)
        assert tasks.count() == 0
        mock_exec.delay.assert_not_called()

    @patch("agents.tasks.execute_agent_task")
    def test_daily_creates_tasks(self, mock_exec, twitter_agent):
        from agents.tasks import run_scheduled_actions

        # post-content is daily but disabled => no task for that
        # engage-tweets is hourly => not picked for daily
        run_scheduled_actions("daily")

        tasks = AgentTask.objects.filter(agent=twitter_agent)
        assert tasks.count() == 0

    @patch("agents.tasks.execute_agent_task")
    def test_daily_with_enabled_daily_action(self, mock_exec, department):
        from agents.tasks import run_scheduled_actions

        agent = Agent.objects.create(
            name="Daily Twitter",
            agent_type="twitter",
            department=department,
            auto_actions={"post-content": True},
        )
        run_scheduled_actions("daily")

        tasks = AgentTask.objects.filter(agent=agent)
        assert tasks.count() == 1
        mock_exec.delay.assert_called_once()


# ── execute_agent_task ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestExecuteAgentTask:
    @patch("agents.blueprints.marketing.workforce.twitter.agent.TwitterBlueprint.execute_task", return_value="Done tweeting")
    def test_transitions_queued_to_done(self, mock_bp_exec, twitter_agent):
        from agents.tasks import execute_agent_task

        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.QUEUED,
            exec_summary="Tweet stuff",
        )
        execute_agent_task(str(task.id))

        task.refresh_from_db()
        assert task.status == AgentTask.Status.DONE
        assert task.report == "Done tweeting"
        assert task.completed_at is not None

    @patch("agents.blueprints.marketing.workforce.twitter.agent.TwitterBlueprint.execute_task", return_value="Done planned")
    def test_handles_planned_status(self, mock_bp_exec, twitter_agent):
        from agents.tasks import execute_agent_task

        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PLANNED,
            exec_summary="Planned tweet",
        )
        execute_agent_task(str(task.id))

        task.refresh_from_db()
        assert task.status == AgentTask.Status.DONE

    def test_atomic_guard_prevents_double_execution(self, twitter_agent):
        from agents.tasks import execute_agent_task

        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Already running",
        )
        # Should skip (status is processing, not queued/planned)
        execute_agent_task(str(task.id))

        task.refresh_from_db()
        assert task.status == AgentTask.Status.PROCESSING  # unchanged

    @patch(
        "agents.blueprints.marketing.workforce.twitter.agent.TwitterBlueprint.execute_task",
        side_effect=RuntimeError("API down"),
    )
    def test_failure_sets_failed_status(self, mock_bp_exec, twitter_agent):
        from agents.tasks import execute_agent_task

        task = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.QUEUED,
            exec_summary="Will fail",
        )
        execute_agent_task(str(task.id))

        task.refresh_from_db()
        assert task.status == AgentTask.Status.FAILED
        assert "API down" in task.error_message
        assert task.completed_at is not None


# ── create_next_leader_task ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestCreateNextLeaderTask:
    @patch("agents.ai.claude_client.call_claude")
    def test_creates_proposal_for_workforce(
        self, mock_claude, leader_agent, twitter_agent
    ):
        import json

        mock_claude.return_value = (
            json.dumps(
                {
                    "target_agent_type": "twitter",
                    "exec_summary": "Engage crypto influencers",
                    "step_plan": "1. Find influencers\n2. Engage",
                }
            ),
            {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50},
        )

        from agents.tasks import create_next_leader_task

        create_next_leader_task(str(leader_agent.id))

        # Should create a task for the twitter agent
        task = AgentTask.objects.filter(agent=twitter_agent).first()
        assert task is not None
        assert task.status == AgentTask.Status.AWAITING_APPROVAL
        assert task.created_by_agent == leader_agent
        assert "Engage crypto influencers" in task.exec_summary

    def test_skips_inactive_leader(self, inactive_leader):
        from agents.tasks import create_next_leader_task

        # Should not raise, just log warning and return
        create_next_leader_task(str(inactive_leader.id))

        assert AgentTask.objects.count() == 0

    def test_skips_nonexistent_agent(self):
        from agents.tasks import create_next_leader_task

        fake_id = str(uuid.uuid4())
        create_next_leader_task(fake_id)

        assert AgentTask.objects.count() == 0

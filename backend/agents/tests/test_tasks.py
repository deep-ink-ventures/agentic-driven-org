import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from agents.models import Agent, AgentTask
from agents.tasks import recover_stuck_tasks
from projects.models import Department, Project

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
        auto_approve=True,
        status="active",
    )


@pytest.fixture
def twitter_agent_disabled(department):
    return Agent.objects.create(
        name="Twitter Disabled",
        agent_type="twitter",
        department=department,
        auto_approve=False,
        status="active",
    )


@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
        auto_approve=True,
        status="active",
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
        status="inactive",
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
    def test_daily_creates_tasks_when_approved(self, mock_exec, twitter_agent):
        from agents.tasks import run_scheduled_actions

        # twitter_agent has auto_approve=True, so daily command runs
        run_scheduled_actions("daily")

        tasks = AgentTask.objects.filter(agent=twitter_agent)
        assert tasks.count() == 1

    @patch("agents.tasks.execute_agent_task")
    def test_daily_with_enabled_daily_action(self, mock_exec, department):
        from agents.tasks import run_scheduled_actions

        agent = Agent.objects.create(
            name="Daily Twitter",
            agent_type="twitter",
            department=department,
            auto_approve=True,
            status="active",
        )
        run_scheduled_actions("daily")

        tasks = AgentTask.objects.filter(agent=agent)
        assert tasks.count() == 1
        mock_exec.delay.assert_called_once()


# ── execute_agent_task ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestExecuteAgentTask:
    @patch(
        "agents.blueprints.marketing.workforce.twitter.agent.TwitterBlueprint.execute_task",
        return_value="Done tweeting",
    )
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

    @patch(
        "agents.blueprints.marketing.workforce.twitter.agent.TwitterBlueprint.execute_task", return_value="Done planned"
    )
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
    def test_creates_proposal_for_workforce(self, mock_claude, leader_agent, twitter_agent):
        import json

        mock_claude.return_value = (
            json.dumps(
                {
                    "exec_summary": "Engage crypto influencers",
                    "tasks": [
                        {
                            "target_agent_type": "twitter",
                            "command_name": "place-content",
                            "exec_summary": "Engage crypto influencers on Twitter",
                            "step_plan": "1. Find influencers\n2. Engage",
                        }
                    ],
                }
            ),
            {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50},
        )

        from agents.tasks import create_next_leader_task

        create_next_leader_task(str(leader_agent.id))

        # Should create a task for the twitter agent
        task = AgentTask.objects.filter(agent=twitter_agent).first()
        assert task is not None
        # auto_approve is True on twitter_agent, so task is auto-queued
        assert task.status in [AgentTask.Status.QUEUED, AgentTask.Status.AWAITING_APPROVAL]
        assert task.created_by_agent == leader_agent
        assert task.command_name == "place-content"
        assert "crypto influencers" in task.exec_summary

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


# ── recover_stuck_tasks ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRecoverStuckTasks:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(email="stuck@test.com", password="pass")
        self.project = Project.objects.create(name="Test", goal="g", owner=self.user)
        self.project.members.add(self.user)
        self.dept = Department.objects.create(project=self.project, department_type="eng")
        self.agent = Agent.objects.create(name="Bot", agent_type="bot", department=self.dept)

    @patch("agents.tasks._broadcast_task")
    def test_marks_stuck_processing_tasks_as_failed(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Stuck task",
            started_at=timezone.now() - timedelta(hours=2),
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.FAILED
        assert "Worker died" in task.error_message
        assert task.completed_at is not None
        mock_broadcast.assert_called_once()

    @patch("agents.tasks._broadcast_task")
    def test_ignores_recent_processing_tasks(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Recent task",
            started_at=timezone.now() - timedelta(minutes=30),
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.PROCESSING
        mock_broadcast.assert_not_called()

    @patch("agents.tasks._broadcast_task")
    def test_ignores_non_processing_tasks(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.QUEUED,
            exec_summary="Queued task",
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED
        mock_broadcast.assert_not_called()

    @patch("agents.tasks._broadcast_task")
    def test_recover_stuck_tasks_cascades_failure(self, mock_broadcast):
        parent = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Stuck parent",
            started_at=timezone.now() - timedelta(hours=2),
        )
        child = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=parent,
            exec_summary="Waiting child",
        )
        recover_stuck_tasks()
        child.refresh_from_db()
        assert child.status == AgentTask.Status.FAILED

    @patch("agents.tasks._broadcast_task")
    def test_handles_processing_with_no_started_at(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="No started_at",
            started_at=None,
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.FAILED


# ── _fail_dependents ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestFailedTaskCascade:
    def test_failed_task_fails_dependents(self, twitter_agent):
        parent = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Parent task",
        )
        child = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=parent,
            exec_summary="Child task",
        )
        from agents.tasks import _fail_dependents

        _fail_dependents(parent)
        child.refresh_from_db()
        assert child.status == AgentTask.Status.FAILED
        assert "upstream task failed" in child.error_message.lower()

    def test_failed_task_cascades_chain(self, twitter_agent):
        a = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Task A",
        )
        b = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=a,
            exec_summary="Task B",
        )
        c = AgentTask.objects.create(
            agent=twitter_agent,
            status=AgentTask.Status.AWAITING_DEPENDENCIES,
            blocked_by=b,
            exec_summary="Task C",
        )
        from agents.tasks import _fail_dependents

        _fail_dependents(a)
        b.refresh_from_db()
        c.refresh_from_db()
        assert b.status == AgentTask.Status.FAILED
        assert c.status == AgentTask.Status.FAILED

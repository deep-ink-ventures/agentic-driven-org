"""Tests for agent instructions review after sprint completion and goal changes."""

import json
from unittest.mock import patch

import pytest

from agents.models import Agent, AgentTask
from projects.models import Department, Project, Sprint
from projects.tasks_consolidation import (
    review_agent_instructions_after_sprint,
    review_single_agent_instructions,
)


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(email="test@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Acme Corp", goal="Build and sell SaaS", owner=user)


@pytest.fixture
def sales_dept(project):
    return Department.objects.create(department_type="sales", project=project)


@pytest.fixture
def writers_dept(project):
    return Department.objects.create(department_type="writers_room", project=project)


@pytest.fixture
def sales_leader(sales_dept):
    return Agent.objects.create(
        name="Head of Sales",
        agent_type="leader",
        department=sales_dept,
        is_leader=True,
        status="active",
    )


@pytest.fixture
def sales_agents(sales_dept):
    return {
        "researcher": Agent.objects.create(
            name="Sales Researcher",
            agent_type="researcher",
            department=sales_dept,
            status="active",
            instructions="Research fintech companies targeting Series A startups.",
        ),
        "strategist": Agent.objects.create(
            name="Sales Strategist",
            agent_type="strategist",
            department=sales_dept,
            status="active",
            instructions="Focus target areas on European fintech. Product name: FinFlow.",
        ),
    }


@pytest.fixture
def sprint(project, writers_dept, user):
    s = Sprint.objects.create(
        project=project,
        text="Rebrand product from FinFlow to PayBridge",
        status=Sprint.Status.DONE,
        created_by=user,
    )
    s.departments.add(writers_dept)
    return s


@pytest.mark.django_db
class TestReviewAgentInstructionsAfterSprint:
    def test_skips_when_no_sprint(self):
        """Does not crash on missing sprint."""
        review_agent_instructions_after_sprint("00000000-0000-0000-0000-000000000000")

    def test_skips_when_no_completed_tasks(self, sprint):
        """No outcomes → nothing to review."""
        with patch("projects.tasks_consolidation.call_claude") as mock:
            review_agent_instructions_after_sprint(str(sprint.id))
            mock.assert_not_called()

    def test_skips_unaffected_departments(self, sprint, sales_dept, sales_leader, sales_agents):
        """When Claude says no departments are affected, no agent review happens."""
        AgentTask.objects.create(
            agent=sales_leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Internal code refactor",
            report="Refactored the database schema.",
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                json.dumps(
                    {
                        "affected_departments": [],
                        "reasoning": "Code refactor does not affect any department instructions",
                    }
                ),
                {"input_tokens": 100, "output_tokens": 50},
            )

            review_agent_instructions_after_sprint(str(sprint.id))

            # Only called once for department assessment, not for agent review
            assert mock_claude.call_count == 1

    def test_fans_out_per_agent_for_affected_departments(self, sprint, sales_dept, sales_leader, sales_agents):
        """When Claude says sales is affected, fans out one task per agent."""
        AgentTask.objects.create(
            agent=sales_leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Rebrand to PayBridge",
            report="Product renamed from FinFlow to PayBridge.",
        )

        with (
            patch("projects.tasks_consolidation.call_claude") as mock_claude,
            patch("projects.tasks_consolidation.review_single_agent_instructions") as mock_review,
        ):
            mock_claude.return_value = (
                json.dumps(
                    {
                        "affected_departments": ["sales"],
                        "reasoning": "Product rebrand affects sales agents",
                    }
                ),
                {"input_tokens": 100, "output_tokens": 50},
            )

            review_agent_instructions_after_sprint(str(sprint.id))

            # Should fan out one task per active agent in the sales dept
            # (leader + 2 agents = 3 active agents)
            assert mock_review.delay.call_count == 3


@pytest.mark.django_db
class TestReviewSingleAgentInstructions:
    def test_updates_instructions_directly_when_affected(self, project, sales_dept, sales_leader, sales_agents):
        strategist = sales_agents["strategist"]
        assert "FinFlow" in strategist.instructions

        with patch("agents.ai.claude_client.call_claude_structured") as mock_claude:
            mock_claude.return_value = (
                {
                    "affected": True,
                    "reason": "Product name changed from FinFlow to PayBridge",
                    "updated_instructions": "Focus target areas on European fintech. Product name: PayBridge. Expanded instructions for the new brand.",
                },
                {"input_tokens": 100, "output_tokens": 50},
            )

            review_single_agent_instructions(str(strategist.id), str(project.id))

        strategist.refresh_from_db()
        assert "PayBridge" in strategist.instructions
        assert "FinFlow" not in strategist.instructions

        # No approval tasks created — instructions are applied directly
        tasks = AgentTask.objects.filter(exec_summary__contains="Update instructions")
        assert tasks.count() == 0

    def test_no_task_when_not_affected(self, project, sales_dept, sales_leader, sales_agents):
        researcher = sales_agents["researcher"]

        with patch("agents.ai.claude_client.call_claude_structured") as mock_claude:
            mock_claude.return_value = (
                {
                    "affected": False,
                    "reason": "Research instructions don't reference product name",
                },
                {"input_tokens": 100, "output_tokens": 50},
            )

            review_single_agent_instructions(str(researcher.id), str(project.id))

        tasks = AgentTask.objects.filter(exec_summary__contains="Update instructions")
        assert tasks.count() == 0

    def test_restores_active_status_on_failure(self, project, sales_dept, sales_leader, sales_agents):
        strategist = sales_agents["strategist"]
        strategist.status = Agent.Status.PROVISIONING
        strategist.save()

        with (
            patch("agents.ai.claude_client.call_claude_structured", side_effect=RuntimeError("API down")),
            pytest.raises(RuntimeError),
        ):
            review_single_agent_instructions(str(strategist.id), str(project.id))

        strategist.refresh_from_db()
        assert strategist.status == Agent.Status.ACTIVE  # restored

    def test_restores_active_on_success(self, project, sales_dept, sales_leader, sales_agents):
        strategist = sales_agents["strategist"]
        strategist.status = Agent.Status.PROVISIONING
        strategist.save()

        with patch("agents.ai.claude_client.call_claude_structured") as mock_claude:
            mock_claude.return_value = (
                {"affected": False, "reason": "No change needed"},
                {"input_tokens": 100, "output_tokens": 50},
            )

            review_single_agent_instructions(str(strategist.id), str(project.id))

        strategist.refresh_from_db()
        assert strategist.status == Agent.Status.ACTIVE


@pytest.mark.django_db
class TestSignalIntegration:
    def test_signal_dispatches_review(self, sprint):
        """Sprint status change to done triggers the review task."""
        with (
            patch("projects.signals.consolidate_sprint_documents"),
            patch("projects.signals.review_agent_instructions_after_sprint") as mock_review,
        ):
            # Re-trigger the signal by saving
            sprint.status = Sprint.Status.DONE
            sprint.save()

            mock_review.delay.assert_called_once_with(str(sprint.id))

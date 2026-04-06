"""Tests for agent instructions review after sprint completion."""

import json
from unittest.mock import patch

import pytest

from agents.models import Agent, AgentTask
from projects.models import Department, Project, Sprint
from projects.tasks_consolidation import (
    _review_department_agents,
    review_agent_instructions_after_sprint,
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
        # Create a completed task on the sprint
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

    def test_reviews_affected_departments(self, sprint, sales_dept, sales_leader, sales_agents):
        """When Claude says sales is affected, proceeds to review sales agents."""
        AgentTask.objects.create(
            agent=sales_leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Rebrand to PayBridge",
            report="Product renamed from FinFlow to PayBridge.",
        )

        call_count = [0]

        def mock_claude_side_effect(system_prompt, user_message, max_tokens=8192):
            call_count[0] += 1
            if call_count[0] == 1:
                # Step 1: department assessment
                return (
                    json.dumps(
                        {
                            "affected_departments": ["sales"],
                            "reasoning": "Product rebrand affects sales agent instructions referencing FinFlow",
                        }
                    ),
                    {"input_tokens": 100, "output_tokens": 50},
                )
            else:
                # Step 2+3: agent assessment
                return (
                    json.dumps(
                        {
                            "agents": [
                                {
                                    "agent_type": "researcher",
                                    "affected": False,
                                    "reason": "Research instructions don't reference product name",
                                },
                                {
                                    "agent_type": "strategist",
                                    "affected": True,
                                    "reason": "References FinFlow which is now PayBridge",
                                    "updated_instructions": "Focus target areas on European fintech. Product name: PayBridge.",
                                },
                            ]
                        }
                    ),
                    {"input_tokens": 200, "output_tokens": 100},
                )

        with patch("projects.tasks_consolidation.call_claude", side_effect=mock_claude_side_effect):
            review_agent_instructions_after_sprint(str(sprint.id))

        # Should have created one awaiting-approval task for the strategist update
        update_tasks = AgentTask.objects.filter(
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary__contains="Update instructions",
        )
        assert update_tasks.count() == 1

        task = update_tasks.first()
        assert "strategist" in task.exec_summary or "Strategist" in task.exec_summary
        assert "PayBridge" in task.step_plan
        assert "FinFlow" in task.step_plan  # reason references old name


@pytest.mark.django_db
class TestReviewDepartmentAgents:
    def test_creates_update_task_for_affected_agent(self, sales_dept, sales_leader, sales_agents, sprint):
        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                json.dumps(
                    {
                        "agents": [
                            {
                                "agent_type": "strategist",
                                "affected": True,
                                "reason": "Product name changed",
                                "updated_instructions": "New instructions here.",
                            },
                            {
                                "agent_type": "researcher",
                                "affected": False,
                                "reason": "Not affected",
                            },
                        ]
                    }
                ),
                {"input_tokens": 100, "output_tokens": 50},
            )

            _review_department_agents(sales_dept.id, sprint, "Product renamed")

        tasks = AgentTask.objects.filter(
            status=AgentTask.Status.AWAITING_APPROVAL,
            exec_summary__contains="Update instructions",
        )
        assert tasks.count() == 1
        assert tasks.first().agent == sales_leader  # assigned to leader

    def test_no_tasks_when_no_agents_affected(self, sales_dept, sales_leader, sales_agents, sprint):
        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                json.dumps(
                    {
                        "agents": [
                            {"agent_type": "strategist", "affected": False, "reason": "Not affected"},
                            {"agent_type": "researcher", "affected": False, "reason": "Not affected"},
                        ]
                    }
                ),
                {"input_tokens": 100, "output_tokens": 50},
            )

            _review_department_agents(sales_dept.id, sprint, "Minor change")

        tasks = AgentTask.objects.filter(exec_summary__contains="Update instructions")
        assert tasks.count() == 0

    def test_handles_parse_failure_gracefully(self, sales_dept, sales_leader, sales_agents, sprint):
        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = ("Not valid JSON at all", {"input_tokens": 50, "output_tokens": 20})

            # Should not crash
            _review_department_agents(sales_dept.id, sprint, "Some outcomes")

        tasks = AgentTask.objects.filter(exec_summary__contains="Update instructions")
        assert tasks.count() == 0


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

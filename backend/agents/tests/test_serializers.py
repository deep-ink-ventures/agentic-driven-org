"""Tests for agent serializers."""

from unittest.mock import MagicMock

import pytest

from agents.serializers.agent_task_serializer import AgentTaskSerializer
from agents.serializers.blueprint_info_serializer import get_blueprint_info


@pytest.mark.django_db
class TestAgentTaskSerializer:
    def _create_task(self):
        from accounts.models import User
        from agents.models import Agent, AgentTask
        from projects.models import Department, Project

        user = User.objects.create_user(email="ser@test.com", password="pass")
        project = Project.objects.create(name="Ser Project", owner=user)
        project.members.add(user)
        dept = Department.objects.create(project=project, department_type="marketing")
        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="twitter",
            department=dept,
            status="active",
        )
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Test task summary",
            step_plan="Step 1\nStep 2",
            status="awaiting_approval",
            command_name="post-content",
        )
        return task

    def test_serializes_all_expected_fields(self):
        task = self._create_task()
        serializer = AgentTaskSerializer(task)
        data = serializer.data

        expected_fields = {
            "id",
            "agent",
            "agent_name",
            "agent_type",
            "created_by_agent",
            "created_by_agent_name",
            "status",
            "auto_execute",
            "command_name",
            "blocked_by",
            "blocked_by_summary",
            "sprint",
            "exec_summary",
            "step_plan",
            "report",
            "error_message",
            "proposed_exec_at",
            "scheduled_at",
            "started_at",
            "completed_at",
            "token_usage",
            "created_at",
            "updated_at",
            "review_verdict",
            "review_score",
        }
        assert set(data.keys()) == expected_fields

    def test_agent_name_from_source(self):
        task = self._create_task()
        data = AgentTaskSerializer(task).data
        assert data["agent_name"] == "Test Agent"
        assert data["agent_type"] == "twitter"

    def test_created_by_agent_name_none_when_no_creator(self):
        task = self._create_task()
        data = AgentTaskSerializer(task).data
        assert data["created_by_agent_name"] is None

    def test_created_by_agent_name_when_set(self):
        from agents.models import Agent

        task = self._create_task()
        leader = Agent.objects.create(
            name="Leader Agent",
            agent_type="marketing_leader",
            department=task.agent.department,
            is_leader=True,
        )
        task.created_by_agent = leader
        task.save()
        data = AgentTaskSerializer(task).data
        assert data["created_by_agent_name"] == "Leader Agent"

    def test_blocked_by_summary_none_when_no_blocker(self):
        task = self._create_task()
        data = AgentTaskSerializer(task).data
        assert data["blocked_by_summary"] is None

    def test_blocked_by_summary_truncated(self):
        from agents.models import AgentTask

        task = self._create_task()
        blocker = AgentTask.objects.create(
            agent=task.agent,
            exec_summary="A" * 200,
            status="processing",
        )
        task.blocked_by = blocker
        task.save()
        data = AgentTaskSerializer(task).data
        assert data["blocked_by_summary"] is not None
        assert len(data["blocked_by_summary"]) <= 100

    def test_read_only_fields(self):
        serializer = AgentTaskSerializer()
        for field_name in serializer.Meta.read_only_fields:
            assert field_name in serializer.fields


class TestBlueprintInfoSerializer:
    def test_get_blueprint_info_returns_expected_keys(self):
        agent = MagicMock()
        bp = MagicMock()
        bp.name = "Twitter Agent"
        bp.slug = "twitter"
        bp.description = "Posts tweets"
        bp.tags = ["social", "marketing"]
        bp.default_model = "claude-haiku-4-5-20251001"
        bp.skills_description = "Can post tweets"
        bp.get_commands.return_value = [{"name": "post-content"}]
        bp.get_config_json_schema.return_value = {"type": "object"}
        agent.get_blueprint.return_value = bp

        result = get_blueprint_info(agent)

        assert result["name"] == "Twitter Agent"
        assert result["slug"] == "twitter"
        assert result["description"] == "Posts tweets"
        assert result["tags"] == ["social", "marketing"]
        assert result["default_model"] == "claude-haiku-4-5-20251001"
        assert result["commands"] == [{"name": "post-content"}]
        assert "config_schema" in result

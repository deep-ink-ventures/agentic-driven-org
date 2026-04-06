"""Tests for WritersRoomFeedbackBlueprint context scoping."""
from unittest.mock import MagicMock, patch

import pytest


class TestWritersRoomFeedbackBlueprint:
    def test_blueprint_exists(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
        assert WritersRoomFeedbackBlueprint is not None

    def test_inherits_workforce_blueprint(self):
        from agents.blueprints.base import WorkforceBlueprint
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
        assert issubclass(WritersRoomFeedbackBlueprint, WorkforceBlueprint)

    def test_get_context_strips_sibling_reports(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "## dialogue_writer\n  - [done] Write scenes\n    Report: <long dialogue>",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "long dialogue" not in ctx["sibling_agents"]
        assert "Stage Deliverable" in ctx["sibling_agents"]

    def test_department_documents_preserved(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "some reports",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert ctx["department_documents"] == "--- [stage_deliverable] Expose v1 ---\ncontent"

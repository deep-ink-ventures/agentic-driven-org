"""Tests for AuthenticityAnalystMixin and Writers Room integration."""

from unittest.mock import MagicMock


class TestAuthenticityAnalystMixin:
    def test_mixin_exists(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        assert AuthenticityAnalystMixin is not None

    def test_mixin_is_not_blueprint_subclass(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        from agents.blueprints.base import BaseBlueprint

        assert not issubclass(AuthenticityAnalystMixin, BaseBlueprint)

    def test_mixin_has_system_prompt_property(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        prompt = bp.system_prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_contains_five_checks(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        prompt = Concrete().system_prompt
        assert "Linguistic Tells" in prompt
        assert "Voice Flattening" in prompt
        assert "Cliche" in prompt or "Cliché" in prompt
        assert "Coherence" in prompt
        assert "Overall Authenticity" in prompt

    def test_get_task_suffix_includes_locale(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        agent = MagicMock()
        agent.get_config_value.return_value = "de"
        task = MagicMock()

        suffix = bp.get_task_suffix(agent, task)
        assert "Output language: de" in suffix

    def test_get_max_tokens(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        assert bp.get_max_tokens(MagicMock(), MagicMock()) == 8000

    def test_mixin_has_slug(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        assert AuthenticityAnalystMixin.slug == "authenticity_analyst"

    def test_command_description_exported(self):
        from agents.ai.archetypes.authenticity_analyst import COMMAND_DESCRIPTION

        assert isinstance(COMMAND_DESCRIPTION, str)
        assert "authenticity" in COMMAND_DESCRIPTION.lower() or "coherence" in COMMAND_DESCRIPTION.lower()


class TestWritersRoomAuthenticityAnalyst:
    def test_blueprint_exists(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        assert AuthenticityAnalystBlueprint is not None

    def test_inherits_feedback_blueprint(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        assert issubclass(AuthenticityAnalystBlueprint, WritersRoomFeedbackBlueprint)

    def test_inherits_mixin(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        assert issubclass(AuthenticityAnalystBlueprint, AuthenticityAnalystMixin)

    def test_system_prompt_comes_from_mixin(self):
        from agents.ai.archetypes.authenticity_analyst import SYSTEM_PROMPT
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        bp = AuthenticityAnalystBlueprint()
        assert bp.system_prompt == SYSTEM_PROMPT

    def test_get_context_strips_sibling_reports(self):
        from unittest.mock import patch

        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        bp = AuthenticityAnalystBlueprint()
        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "## dialogue_writer\n  - [done] Write scenes\n    Report: long dialogue",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch("agents.blueprints.base.WorkforceBlueprint.get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "long dialogue" not in ctx["sibling_agents"]
        assert "Stage Deliverable" in ctx["sibling_agents"] or "Sibling task reports" in ctx["sibling_agents"]

    def test_has_analyze_command(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        bp = AuthenticityAnalystBlueprint()
        commands = bp.get_commands()
        command_names = [c["name"] for c in commands]
        assert "analyze" in command_names

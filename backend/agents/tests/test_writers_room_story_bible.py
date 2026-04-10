"""Tests for story bible generation, rendering, and injection."""

from unittest.mock import patch

import pytest

from agents.blueprints.writers_room.leader.agent import (
    STORY_BIBLE_SCHEMA,
    WritersRoomLeaderBlueprint,
)


class TestStoryBibleSchema:
    def test_schema_has_required_sections(self):
        props = STORY_BIBLE_SCHEMA["properties"]
        assert "characters" in props
        assert "timeline" in props
        assert "canon_facts" in props
        assert "world_rules" in props
        assert "changelog" in props

    def test_character_schema_has_voice_directives(self):
        char_props = STORY_BIBLE_SCHEMA["properties"]["characters"]["items"]["properties"]
        assert "voice_directives" in char_props
        assert char_props["voice_directives"]["type"] == "array"

    def test_timeline_status_enum(self):
        timeline_props = STORY_BIBLE_SCHEMA["properties"]["timeline"]["items"]["properties"]
        assert timeline_props["status"]["enum"] == ["established", "tbd"]


class TestRenderStoryBible:
    def setup_method(self):
        self.bp = WritersRoomLeaderBlueprint()

    def test_renders_characters(self):
        data = {
            "characters": [
                {
                    "name": "Jakob Hartmann",
                    "role": "CEO, eldest brother",
                    "status": "active protagonist [ESTABLISHED]",
                    "key_decisions": ["Signed Friedrichshain acquisition [ESTABLISHED]"],
                    "relationships": ["Felix — resentful, excluded from board [ESTABLISHED]"],
                    "voice_directives": ["Short declarative sentences. Never apologizes."],
                }
            ],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Characters" in result
        assert "### Jakob Hartmann" in result
        assert "Short declarative sentences" in result
        assert "Signed Friedrichshain acquisition" in result

    def test_renders_timeline(self):
        data = {
            "characters": [],
            "timeline": [
                {"when": "Ep1", "what": "First acquisition", "source": "pitch", "status": "established"},
            ],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Timeline" in result
        assert "First acquisition" in result
        assert "[ESTABLISHED]" in result

    def test_renders_canon_facts(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": ["Company name: Hartmann Capital GmbH & Co. KG"],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Established Facts (Canon)" in result
        assert "Hartmann Capital" in result

    def test_renders_world_rules(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": ["No character has direct access to the Bürgermeister"],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## World Rules" in result
        assert "Bürgermeister" in result

    def test_renders_changelog(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [
                {
                    "transition": "Pitch → Expose",
                    "added": ["Felix's side deal"],
                    "changed": ["Katrin from neutral to antagonist"],
                    "dropped": [],
                }
            ],
        }
        result = self.bp._render_story_bible(data)
        assert "## Stage Changelog" in result
        assert "Pitch → Expose" in result
        assert "Felix's side deal" in result

    def test_empty_sections_omitted(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Characters" not in result
        assert "## Timeline" not in result


@pytest.mark.django_db
class TestUpdateStoryBible:
    def _make_agent(self, department):
        from agents.models import Agent

        return Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
            internal_state={"format_type": "standalone", "current_stage": "pitch"},
        )

    def _make_sprint(self, project, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=project,
            text="Write a pitch",
            status=Sprint.Status.RUNNING,
        )
        sprint.departments.add(department)
        return sprint

    def _make_project_and_dept(self):
        from projects.models import Department, Project

        project = Project.objects.create(name="Test Project", goal="A story about brothers")
        dept = Department.objects.create(
            project=project,
            name="Writers Room",
            department_type="writers_room",
        )
        return project, dept

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_creates_story_bible_output(self, mock_structured):
        mock_structured.return_value = (
            {
                "characters": [
                    {
                        "name": "Jakob",
                        "role": "CEO",
                        "status": "active [ESTABLISHED]",
                        "key_decisions": [],
                        "relationships": [],
                        "voice_directives": [],
                    }
                ],
                "timeline": [],
                "canon_facts": ["Company: Hartmann Capital"],
                "world_rules": [],
                "changelog": [],
            },
            {"model": "claude-opus-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Pitch v1 — Deliverable",
            content="Jakob signs the deal.",
            sprint=sprint,
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "pitch")

        from projects.models import Output

        bible = Output.objects.get(sprint=sprint, department=dept, label="story_bible")
        assert "Jakob" in bible.content
        assert "Story Bible" in bible.title

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_updates_existing_bible(self, mock_structured):
        mock_structured.return_value = (
            {
                "characters": [
                    {
                        "name": "Jakob",
                        "role": "CEO",
                        "status": "active [ESTABLISHED]",
                        "key_decisions": ["Signed deal [ESTABLISHED]"],
                        "relationships": [],
                        "voice_directives": [],
                    }
                ],
                "timeline": [],
                "canon_facts": [],
                "world_rules": [],
                "changelog": [{"transition": "Pitch → Expose", "added": ["New subplot"], "changed": [], "dropped": []}],
            },
            {"model": "claude-opus-4-6", "input_tokens": 200, "output_tokens": 100, "cost_usd": 0.02},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        from projects.models import Output

        Output.objects.create(
            sprint=sprint,
            department=dept,
            label="story_bible",
            title="Story Bible",
            output_type="markdown",
            content="# Story Bible\n\nOld content",
        )

        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Expose v1 — Deliverable",
            content="Jakob expands.",
            sprint=sprint,
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "expose")

        bible = Output.objects.get(sprint=sprint, department=dept, label="story_bible")
        assert "Signed deal" in bible.content
        assert "Pitch → Expose" in bible.content
        assert Output.objects.filter(sprint=sprint, department=dept, label="story_bible").count() == 1

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_includes_voice_profile_in_prompt(self, mock_structured):
        mock_structured.return_value = (
            {"characters": [], "timeline": [], "canon_facts": [], "world_rules": [], "changelog": []},
            {"model": "claude-opus-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Pitch v1 — Deliverable",
            content="Story content.",
            sprint=sprint,
        )
        Document.objects.create(
            department=dept,
            doc_type="voice_profile",
            title="Voice Profile",
            content="Short sentences. No apologies.",
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "pitch")

        call_args = mock_structured.call_args
        user_message = (
            call_args[1].get("user_message")
            if len(call_args) > 1 and isinstance(call_args[1], dict)
            else call_args.kwargs.get("user_message", "")
        )
        assert "Short sentences" in user_message


@pytest.mark.django_db
class TestBibleContextInjection:
    def _make_setup(self):
        from agents.models import Agent
        from projects.models import Department, Output, Project, Sprint

        project = Project.objects.create(name="Test", goal="Story")
        dept = Department.objects.create(project=project, name="WR", department_type="writers_room")
        leader = Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={
                "format_type": "standalone",
                "current_stage": "expose",
                "entry_detected": True,
            },
        )
        sprint = Sprint.objects.create(project=project, text="Write", status=Sprint.Status.RUNNING)
        sprint.departments.add(dept)
        Output.objects.create(
            sprint=sprint,
            department=dept,
            label="story_bible",
            title="Story Bible",
            output_type="markdown",
            content="# Story Bible\n\n## Characters\n\n### Jakob\n- **Role:** CEO",
        )
        return leader, dept, sprint

    def test_delegation_context_includes_bible(self):
        leader, dept, sprint = self._make_setup()
        bp = WritersRoomLeaderBlueprint()
        context = bp._get_delegation_context(leader)
        assert "Story Bible (CANON" in context
        assert "Jakob" in context

    def test_delegation_context_without_bible(self):
        from agents.models import Agent
        from projects.models import Department, Project

        project = Project.objects.create(name="Test2", goal="Story2")
        dept = Department.objects.create(project=project, name="WR2", department_type="writers_room")
        leader = Agent.objects.create(
            name="Showrunner2",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={"current_stage": "pitch"},
        )
        bp = WritersRoomLeaderBlueprint()
        context = bp._get_delegation_context(leader)
        assert "Story Bible" not in context


class TestCreativeReviewerEnhancements:
    def test_system_prompt_includes_canon_verification(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "CANON VERIFICATION" in prompt
        assert "[ESTABLISHED]" in prompt

    def test_system_prompt_includes_dramatic_weakness(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "DRAMATIC WEAKNESS" in prompt or "WEAK_IDEA" in prompt
        assert "stakes" in prompt.lower()

    def test_system_prompt_includes_weak_idea_verdict(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "WEAK_IDEA" in prompt

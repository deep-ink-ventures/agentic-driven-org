"""Tests for Lead Writer agent and writers room pipeline refactor."""

from agents.blueprints import get_blueprint
from projects.models import Document


class TestStageDocTypes:
    def test_stage_deliverable_doc_type_exists(self):
        assert "stage_deliverable" in [c[0] for c in Document.DocType.choices]

    def test_stage_research_doc_type_exists(self):
        assert "stage_research" in [c[0] for c in Document.DocType.choices]

    def test_stage_critique_doc_type_exists(self):
        assert "stage_critique" in [c[0] for c in Document.DocType.choices]


class TestLeadWriterBlueprint:
    def test_blueprint_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        assert bp is not None
        assert bp.name == "Lead Writer"
        assert bp.slug == "lead_writer"

    def test_write_pitch_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_pitch" in cmds

    def test_write_expose_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_expose" in cmds

    def test_write_treatment_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_treatment" in cmds

    def test_write_concept_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_concept" in cmds

    def test_write_first_draft_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_first_draft" in cmds

    def test_all_commands_use_sonnet(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        for name in ["write_pitch", "write_expose", "write_treatment", "write_concept", "write_first_draft"]:
            assert cmds[name]["model"] == "claude-sonnet-4-6", f"{name} should use claude-sonnet-4-6"

    def test_system_prompt_contains_key_principles(self):
        bp = get_blueprint("lead_writer", "writers_room")
        prompt = bp.system_prompt
        assert "synthesize" in prompt.lower() or "synthesis" in prompt.lower()
        assert "do not invent" in prompt.lower() or "not alter" in prompt.lower()

    def test_skills_defined(self):
        bp = get_blueprint("lead_writer", "writers_room")
        assert len(bp.skills) >= 3

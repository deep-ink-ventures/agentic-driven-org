"""Tests for action-first instruction mandates across all writers room agents."""

from agents.blueprints import get_blueprint


class TestStoryArchitectActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_scenes_not_frameworks(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "WHO does WHAT" in prompt
        assert "WHAT CHANGES as a result" in prompt

    def test_system_prompt_forbids_framework_exposition(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "NO FRAMEWORK EXPOSITION" in prompt

    def test_system_prompt_no_framework_listing(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        # The old prompt listed all frameworks as bullet points — that should be gone
        assert "- **Three-Act**" not in prompt
        assert "- **Five-Act**" not in prompt
        assert "- **Save the Cat**" not in prompt


class TestCharacterDesignerActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_decisions(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "THREE DECISIONS" in prompt
        assert "ONE DECISION that destroys" in prompt

    def test_system_prompt_decisions_before_schemas(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "The decisions come first" in prompt


class TestDialogWriterActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_scene_samples_at_every_stage(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "At pitch stage" in prompt
        assert "At expose stage" in prompt

    def test_system_prompt_scene_change_test(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "Does something CHANGE between the first line and the last line" in prompt


class TestLeadWriterActionFirst:
    def test_pitch_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_pitch"]

    def test_pitch_directive_forbids_mechanism_language(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "FORBIDDEN PHRASES" in CRAFT_DIRECTIVES["write_pitch"]
        assert "Der dramatische Mechanismus funktioniert wie folgt" in CRAFT_DIRECTIVES["write_pitch"]

    def test_pitch_directive_demands_shootable_test(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "Could a director shoot this" in CRAFT_DIRECTIVES["write_pitch"]

    def test_expose_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_expose"]

    def test_treatment_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_treatment"]

    def test_concept_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_concept"]

    def test_first_draft_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_first_draft"]

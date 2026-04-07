"""Tests for action-first instruction mandates across all writers room agents."""

from unittest.mock import MagicMock, patch

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


class TestFeedbackBaseCheck0:
    def test_review_methodology_contains_check_0(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "A story",
            "department_name": "Writers Room",
            "department_documents": "",
            "sibling_agents": "",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "CHECK 0" in ctx["department_documents"]
        assert "ACTION TEST" in ctx["department_documents"]
        assert "retell what happens" in ctx["department_documents"].lower()
        assert "Score: 0/10" in ctx["department_documents"]


class TestStructureAnalystActionFirst:
    def test_system_prompt_scene_sequence_method(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "What happens?" in prompt
        assert "Why does it happen?" in prompt
        assert "What changes?" in prompt

    def test_system_prompt_forbids_framework_exposition(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "NO FRAMEWORK EXPOSITION" in prompt

    def test_system_prompt_no_framework_listing(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        # The old prompt listed 13+ frameworks as bullet points
        assert "- Save the Cat (Blake Snyder)" not in prompt
        assert "- Story (Robert McKee)" not in prompt
        assert "- Anatomy of Story (Truby)" not in prompt


class TestCharacterAnalystActionFirst:
    def test_system_prompt_action_existence_check(self):
        bp = get_blueprint("character_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "CONCRETE ACTION" in prompt
        assert "character does not exist" in prompt.lower()

    def test_system_prompt_agent_execution_test(self):
        bp = get_blueprint("character_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "execute" in prompt.lower()

    def test_task_suffix_action_existence(self):
        bp = get_blueprint("character_analyst", "writers_room")
        agent = MagicMock()
        agent.get_config_value.return_value = "en"
        task = MagicMock()
        suffix = bp.get_task_suffix(agent, task)
        assert "CONCRETE ACTION" in suffix


class TestDialogueAnalystActionFirst:
    def test_system_prompt_line_by_line(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "EVERY line of dialogue" in prompt or "every line of dialogue" in prompt

    def test_system_prompt_character_would_say_this(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "Would this character say this" in prompt

    def test_system_prompt_no_meta_analysis(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "NO META-ANALYSIS" in prompt

    def test_system_prompt_no_dialogue_flag(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "No dialogue to analyze" in prompt


class TestMarketAnalystActionFirst:
    def test_system_prompt_action_test(self):
        bp = get_blueprint("market_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION TEST" in prompt
        assert "does not contain a story" in prompt.lower()

    def test_system_prompt_no_market_fit_without_story(self):
        bp = get_blueprint("market_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "Cannot assess market fit" in prompt


class TestCreativeReviewerActionFirst:
    def test_review_dimensions_includes_dramatic_action(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        assert "dramatic_action" in bp.review_dimensions

    def test_dramatic_action_is_first_dimension(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        assert bp.review_dimensions[0] == "dramatic_action"

    def test_system_prompt_dimension_0(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "DRAMATIC ACTION" in prompt
        assert "Overall score = 0" in prompt


class TestAuthenticityAnalystActionFirst:
    def test_system_prompt_scene_retelling_test(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "SCENE RETELLING TEST" in prompt

    def test_system_prompt_scene_retelling_is_check_1(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        check1_pos = prompt.find("CHECK 1")
        assert check1_pos != -1
        assert "SCENE RETELLING" in prompt[check1_pos : check1_pos + 200]

    def test_system_prompt_line_by_line_logic(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "LINE-BY-LINE" in prompt

    def test_system_prompt_calibration_point(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "1/10" in prompt

    def test_system_prompt_framework_exposition_is_defect(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "framework exposition" in prompt.lower()

    def test_task_suffix_scene_retelling_first(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import WRITERS_ROOM_TASK_SUFFIX

        assert "SCENE RETELLING" in WRITERS_ROOM_TASK_SUFFIX
        scene_pos = WRITERS_ROOM_TASK_SUFFIX.find("SCENE RETELLING")
        causal_pos = WRITERS_ROOM_TASK_SUFFIX.find("CAUSAL CHAIN")
        assert scene_pos < causal_pos


class TestStoryResearcherActionFirst:
    def test_system_prompt_stay_in_lane(self):
        bp = get_blueprint("story_researcher", "writers_room")
        prompt = bp.system_prompt
        assert "Stay in your lane" in prompt or "stay in your lane" in prompt

    def test_system_prompt_no_meta_analysis(self):
        bp = get_blueprint("story_researcher", "writers_room")
        prompt = bp.system_prompt
        assert "Do NOT produce meta-analysis" in prompt or "not produce meta-analysis" in prompt

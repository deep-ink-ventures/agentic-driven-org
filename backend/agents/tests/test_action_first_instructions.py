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

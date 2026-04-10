"""Tests for story bible generation, rendering, and injection."""

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

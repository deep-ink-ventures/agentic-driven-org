"""Tests for writers room ideation & smart entry."""

from unittest.mock import MagicMock, patch

from agents.blueprints import get_blueprint
from projects.models import Document


class TestDocumentDocTypes:
    def test_concept_doc_type_exists(self):
        assert "concept" in [choice[0] for choice in Document.DocType.choices]

    def test_voice_profile_doc_type_exists(self):
        assert "voice_profile" in [choice[0] for choice in Document.DocType.choices]


class TestStoryArchitectIdeationCommands:
    def test_generate_concepts_command_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "generate_concepts" in cmds

    def test_develop_concept_command_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "develop_concept" in cmds

    def test_generate_concepts_metadata(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["generate_concepts"]["model"] == "claude-sonnet-4-6"

    def test_develop_concept_metadata(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["develop_concept"]["model"] == "claude-sonnet-4-6"

    def test_existing_commands_still_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_structure" in cmds
        assert "fix_structure" in cmds
        assert "outline_act_structure" in cmds
        assert "map_subplot_threads" in cmds


class TestStagesAndMatrices:
    def test_stages_include_ideation_and_concept(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        assert STAGES[0] == "ideation"
        assert STAGES[1] == "concept"
        assert STAGES[2] == "logline"

    def test_creative_matrix_has_ideation(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "ideation" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["ideation"]
        assert "story_architect" in CREATIVE_MATRIX["ideation"]

    def test_creative_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "concept" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["concept"]
        assert "story_architect" in CREATIVE_MATRIX["concept"]
        assert "character_designer" in CREATIVE_MATRIX["concept"]

    def test_feedback_matrix_has_ideation(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "ideation" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["ideation"]]
        assert "market_analyst" in agents

    def test_feedback_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "concept" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["concept"]]
        assert "market_analyst" in agents
        assert "character_analyst" in agents


class TestEntryDetection:
    def test_run_entry_detection_returns_stage(self):
        from agents.blueprints.writers_room.leader.agent import _run_entry_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Write me a blockbuster"
        mock_agent.department.project.sources.all.return_value = []
        mock_agent.internal_state = {}
        mock_agent.get_config_value.return_value = None

        with (
            patch("agents.blueprints.writers_room.leader.agent.call_claude") as mock_claude,
            patch("agents.blueprints.writers_room.leader.agent.parse_json_response") as mock_parse,
        ):
            mock_claude.return_value = (
                '{"detected_stage": "ideation"}',
                {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
            )
            mock_parse.return_value = {
                "detected_stage": "ideation",
                "detected_format": "film",
                "format_confidence": "medium",
                "reasoning": "Vague goal",
                "recommended_config": {"target_format": "film"},
            }
            result = _run_entry_detection(mock_agent)

        assert result == "ideation"
        state = mock_agent.internal_state
        assert state["entry_detected"] is True
        assert state["detected_format"] == "film"

    def test_run_entry_detection_with_draft_material(self):
        from agents.blueprints.writers_room.leader.agent import _run_entry_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Polish my screenplay"
        mock_agent.department.project.sources.all.return_value = []
        mock_agent.internal_state = {}
        mock_agent.get_config_value.return_value = None

        with (
            patch("agents.blueprints.writers_room.leader.agent.call_claude") as mock_claude,
            patch("agents.blueprints.writers_room.leader.agent.parse_json_response") as mock_parse,
        ):
            mock_claude.return_value = (
                '{"detected_stage": "first_draft"}',
                {"model": "claude-sonnet-4-6", "input_tokens": 200, "output_tokens": 50, "cost_usd": 0.02},
            )
            mock_parse.return_value = {
                "detected_stage": "first_draft",
                "detected_format": "film",
                "format_confidence": "high",
                "reasoning": "Full screenplay uploaded",
                "recommended_config": {"target_format": "film", "genre": "drama"},
            }
            result = _run_entry_detection(mock_agent)

        assert result == "first_draft"


class TestIdeationCreativeTaskFraming:
    def test_ideation_stage_uses_generate_concepts_command(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "story_architect",
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "ideation", {"locale": "en"})

        tasks = result["tasks"]
        architect_task = next((t for t in tasks if t["target_agent_type"] == "story_architect"), None)
        assert architect_task is not None
        assert architect_task.get("command_name") == "generate_concepts"

    def test_concept_stage_uses_develop_concept_command(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "story_architect",
            "character_designer",
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "concept", {"locale": "en"})

        tasks = result["tasks"]
        architect_task = next((t for t in tasks if t["target_agent_type"] == "story_architect"), None)
        assert architect_task is not None
        assert architect_task.get("command_name") == "develop_concept"

    def test_logline_stage_unchanged(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "dialog_writer",
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "logline", {"locale": "en"})

        tasks = result["tasks"]
        for t in tasks:
            assert t.get("command_name") is None or t["command_name"] not in ("generate_concepts", "develop_concept")

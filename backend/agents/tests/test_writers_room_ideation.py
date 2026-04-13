"""Tests for writers room ideation & smart entry."""

from unittest.mock import MagicMock, patch

from agents.blueprints import get_blueprint
from projects.models import Document


def _mock_sprint(dept_state=None):
    """Create a mock sprint with department_state helpers."""
    state = {"test-dept-id": dept_state or {}}
    sprint = MagicMock()
    sprint.text = "Write a series concept"

    def get_dept_state(dept_id):
        return state.get(dept_id, {})

    def set_dept_state(dept_id, new_state):
        state[dept_id] = new_state

    sprint.get_department_state = MagicMock(side_effect=get_dept_state)
    sprint.set_department_state = MagicMock(side_effect=set_dept_state)
    return sprint


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

    def test_generate_concepts_no_command_model_override(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["generate_concepts"].get("model") is None

    def test_develop_concept_no_command_model_override(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["develop_concept"].get("model") is None

    def test_existing_commands_still_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_structure" in cmds
        assert "fix_structure" in cmds
        assert "outline_act_structure" in cmds
        assert "map_subplot_threads" in cmds


class TestStagesAndMatrices:
    def test_stages_are_four_stage_pipeline(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        assert STAGES == ["pitch", "expose", "treatment", "first_draft"]

    def test_creative_matrix_has_pitch(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "pitch" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["pitch"]
        assert "story_architect" in CREATIVE_MATRIX["pitch"]

    def test_creative_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "concept" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["concept"]
        assert "story_architect" in CREATIVE_MATRIX["concept"]
        assert "character_designer" in CREATIVE_MATRIX["concept"]

    def test_feedback_matrix_has_pitch(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "pitch" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["pitch"]]
        assert "market_analyst" in agents

    def test_feedback_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "concept" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["concept"]]
        assert "market_analyst" in agents
        assert "character_analyst" in agents


class TestFormatDetectionLegacy:
    def test_run_format_detection_returns_dict(self):
        from agents.blueprints.writers_room.leader.agent import _run_format_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Write me a series concept"
        mock_agent.department.project.sources.all.return_value = []
        mock_agent.department_id = "test-dept-id"
        mock_sprint = _mock_sprint()
        mock_sprint.text = "Write a series concept"

        with patch("agents.ai.claude_client.call_claude_with_tools") as mock_claude:
            mock_claude.return_value = (
                "response text",
                {
                    "format_type": "series",
                    "terminal_stage": "concept",
                    "entry_stage": "pitch",
                    "reasoning": "User wants a series concept",
                },
                {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
            )
            result = _run_format_detection(mock_agent, mock_sprint)

        assert result["format_type"] == "series"
        assert result["terminal_stage"] == "concept"
        # Verify state stored in sprint department_state
        mock_sprint.set_department_state.assert_called()
        call_args = mock_sprint.set_department_state.call_args
        assert call_args[0][0] == "test-dept-id"
        stored_state = call_args[0][1]
        assert stored_state["entry_detected"] is True
        assert stored_state["format_type"] == "series"

    def test_run_format_detection_standalone(self):
        from agents.blueprints.writers_room.leader.agent import _run_format_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Polish my screenplay"
        mock_agent.department.project.sources.all.return_value = []
        mock_agent.department_id = "test-dept-id"
        mock_sprint = _mock_sprint()
        mock_sprint.text = "Write a screenplay"

        with patch("agents.ai.claude_client.call_claude_with_tools") as mock_claude:
            mock_claude.return_value = (
                "response text",
                {
                    "format_type": "standalone",
                    "terminal_stage": "first_draft",
                    "entry_stage": "first_draft",
                    "reasoning": "Full screenplay uploaded",
                },
                {"input_tokens": 200, "output_tokens": 50, "cost_usd": 0.02},
            )
            result = _run_format_detection(mock_agent, mock_sprint)

        assert result["format_type"] == "standalone"
        assert result["terminal_stage"] == "first_draft"


class TestPitchCreativeTaskFraming:
    def test_pitch_stage_dispatches_creative_agents(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "story_architect",
            "character_designer",
            "dialog_writer",
        ]
        mock_agent.department_id = "test-dept-id"
        mock_agent.get_config_value.return_value = None
        sprint = _mock_sprint({"stage_status": {}})

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"}, sprint=sprint)

        tasks = result["tasks"]
        agent_types = [t["target_agent_type"] for t in tasks]
        assert "story_researcher" in agent_types
        assert "story_architect" in agent_types

    def test_concept_stage_dispatches_all_creative_agents(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "story_architect",
            "character_designer",
            "dialog_writer",
        ]
        mock_agent.department_id = "test-dept-id"
        mock_agent.get_config_value.return_value = None
        sprint = _mock_sprint({"stage_status": {}})

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "concept", {"locale": "en"}, sprint=sprint)

        tasks = result["tasks"]
        agent_types = [t["target_agent_type"] for t in tasks]
        assert "story_researcher" in agent_types
        assert "story_architect" in agent_types
        assert "character_designer" in agent_types

    def test_expose_stage_dispatches_creative_agents(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            "story_researcher",
            "story_architect",
            "character_designer",
            "dialog_writer",
        ]
        mock_agent.department_id = "test-dept-id"
        mock_agent.get_config_value.return_value = None
        sprint = _mock_sprint({"stage_status": {}})

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "expose", {"locale": "en"}, sprint=sprint)

        tasks = result["tasks"]
        agent_types = [t["target_agent_type"] for t in tasks]
        assert "story_researcher" in agent_types
        assert "dialog_writer" in agent_types

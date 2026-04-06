"""Tests for Lead Writer agent and writers room pipeline refactor."""

from unittest.mock import patch

import pytest

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


class TestNewStagesAndMatrices:
    def test_stages_are_four(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        assert STAGES == ["pitch", "expose", "treatment", "first_draft"]

    def test_creative_matrix_all_stages(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        for stage in ["pitch", "expose", "treatment", "concept", "first_draft"]:
            assert stage in CREATIVE_MATRIX, f"Missing creative matrix for {stage}"

    def test_creative_matrix_excludes_lead_writer(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        for stage, agents in CREATIVE_MATRIX.items():
            assert "lead_writer" not in agents, f"lead_writer should not be in CREATIVE_MATRIX[{stage}]"

    def test_feedback_matrix_all_stages(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        for stage in ["pitch", "expose", "treatment", "concept", "first_draft"]:
            assert stage in FEEDBACK_MATRIX, f"Missing feedback matrix for {stage}"

    def test_flag_routing_removed(self):
        """FLAG_ROUTING should no longer exist."""
        import agents.blueprints.writers_room.leader.agent as mod

        assert not hasattr(mod, "FLAG_ROUTING"), "FLAG_ROUTING should be removed"

    def test_old_stages_removed(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        for old in ["ideation", "concept", "logline", "step_outline", "revised_draft"]:
            assert old not in STAGES, f"Old stage '{old}' should not be in STAGES"


class TestFormatDetection:
    def test_format_detection_prompt_exists(self):
        from agents.blueprints.writers_room.leader.agent import FORMAT_DETECTION_PROMPT

        assert "format_type" in FORMAT_DETECTION_PROMPT
        assert "terminal_stage" in FORMAT_DETECTION_PROMPT

    def test_format_detection_function_exists(self):
        from agents.blueprints.writers_room.leader.agent import _run_format_detection

        assert callable(_run_format_detection)


# ── State machine and document creation tests ──────────────────────────────


@pytest.fixture
def leader_blueprint():
    from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

    return WritersRoomLeaderBlueprint()


@pytest.fixture
def mock_leader_agent(db):
    """Create a minimal leader agent with department and project."""
    from django.contrib.auth import get_user_model

    from agents.models import Agent
    from projects.models import Department, Project, Sprint

    User = get_user_model()
    user = User.objects.create_user(email="test-wr@example.com", password="pass1234")
    project = Project.objects.create(name="Test Project", goal="A test story about brothers", owner=user)
    dept = Department.objects.create(
        project=project,
        department_type="writers_room",
    )
    leader = Agent.objects.create(
        department=dept,
        name="Showrunner",
        agent_type="leader",
        is_leader=True,
        status="active",
        internal_state={},
    )
    for agent_type in [
        "story_researcher",
        "story_architect",
        "character_designer",
        "dialog_writer",
        "lead_writer",
        "market_analyst",
        "structure_analyst",
        "character_analyst",
        "creative_reviewer",
    ]:
        Agent.objects.create(
            department=dept,
            name=agent_type.replace("_", " ").title(),
            agent_type=agent_type,
            is_leader=False,
            status="active",
        )
    sprint = Sprint.objects.create(
        project=project,
        text="Write a series concept for a banking scandal drama",
        status=Sprint.Status.RUNNING,
        created_by=user,
    )
    sprint.departments.add(dept)
    return leader


class TestStateMachine:
    @pytest.mark.django_db
    @patch("agents.blueprints.writers_room.leader.agent._run_format_detection")
    def test_not_started_dispatches_creative_agents(self, mock_detect, leader_blueprint, mock_leader_agent):
        mock_detect.return_value = {
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_stage": "pitch",
        }
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        assert "tasks" in proposal
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "lead_writer" not in agent_types
        assert "story_researcher" in agent_types

    @pytest.mark.django_db
    def test_creative_writing_done_dispatches_lead_writer(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "creative_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert agent_types == ["lead_writer"]

    @pytest.mark.django_db
    def test_lead_writing_done_dispatches_feedback(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        with patch.object(leader_blueprint, "_create_deliverable_and_research_docs"):
            proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "lead_writer" not in agent_types
        assert any(a in agent_types for a in ["market_analyst", "structure_analyst", "character_analyst"])

    @pytest.mark.django_db
    def test_review_pairs_only_lead_writer(self, leader_blueprint):
        pairs = leader_blueprint.get_review_pairs()
        assert len(pairs) == 1
        assert pairs[0]["creator"] == "lead_writer"
        assert pairs[0]["reviewer"] == "creative_reviewer"


class TestDocumentCreation:
    @pytest.mark.django_db
    def test_create_stage_documents_v1_no_archive(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable", "stage_research"],
            contents={
                "stage_deliverable": "The pitch",
                "stage_research": "Research notes",
            },
        )
        docs = Document.objects.filter(department=mock_leader_agent.department, is_archived=False)
        assert docs.filter(doc_type="stage_deliverable").count() == 1
        assert docs.filter(doc_type="stage_research").count() == 1

    @pytest.mark.django_db
    def test_create_stage_documents_v2_archives_v1(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Pitch v1"},
        )
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=2,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Pitch v2"},
        )
        all_docs = Document.objects.filter(department=mock_leader_agent.department, doc_type="stage_deliverable")
        assert all_docs.count() == 2
        archived = all_docs.filter(is_archived=True).first()
        active = all_docs.filter(is_archived=False).first()
        assert archived is not None
        assert active is not None
        assert archived.consolidated_into == active
        assert "v1" in archived.title
        assert "v2" in active.title

    @pytest.mark.django_db
    def test_effective_stage_series_treatment(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {"format_type": "series"}
        mock_leader_agent.save(update_fields=["internal_state"])
        assert leader_blueprint._get_effective_stage(mock_leader_agent, "treatment") == "concept"

    @pytest.mark.django_db
    def test_effective_stage_standalone_treatment(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {"format_type": "standalone"}
        mock_leader_agent.save(update_fields=["internal_state"])
        assert leader_blueprint._get_effective_stage(mock_leader_agent, "treatment") == "treatment"

    @pytest.mark.django_db
    def test_series_documents_titled_concept_not_treatment(self, leader_blueprint, mock_leader_agent):
        """For series, documents at the treatment stage position should be titled 'Concept', not 'Treatment'."""
        mock_leader_agent.internal_state = {"format_type": "series", "stage_status": {"treatment": {"iterations": 0}}}
        mock_leader_agent.save(update_fields=["internal_state"])
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="treatment",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "The series concept"},
        )
        doc = Document.objects.filter(department=mock_leader_agent.department, doc_type="stage_deliverable").first()
        assert doc is not None
        assert "Concept" in doc.title
        assert "Treatment" not in doc.title

    @pytest.mark.django_db
    def test_standalone_documents_titled_treatment(self, leader_blueprint, mock_leader_agent):
        """For standalone, documents at the treatment stage should be titled 'Treatment'."""
        mock_leader_agent.internal_state = {
            "format_type": "standalone",
            "stage_status": {"treatment": {"iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="treatment",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "The treatment"},
        )
        doc = Document.objects.filter(department=mock_leader_agent.department, doc_type="stage_deliverable").first()
        assert doc is not None
        assert "Treatment" in doc.title

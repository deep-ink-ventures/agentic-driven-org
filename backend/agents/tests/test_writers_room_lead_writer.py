"""Tests for Lead Writer agent and writers room pipeline refactor."""

from unittest.mock import MagicMock, patch

import pytest

from agents.blueprints import get_blueprint
from projects.models import Document, Output


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

    def test_commands_use_blueprint_default_model(self):
        bp = get_blueprint("lead_writer", "writers_room")
        assert bp.default_model == "claude-opus-4-6"
        cmds = {c["name"]: c for c in bp.get_commands()}
        for name in ["write_pitch", "write_expose", "write_treatment", "write_concept", "write_first_draft"]:
            assert cmds[name].get("model") is None, f"{name} should not override model"

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


def _set_dept_state(leader, state):
    """Helper: set sprint department_state for a leader's department."""
    from projects.models import Sprint

    sprint = Sprint.objects.filter(
        departments=leader.department,
        status=Sprint.Status.RUNNING,
    ).first()
    if sprint:
        sprint.set_department_state(str(leader.department_id), state)
    return sprint


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
        "authenticity_analyst",
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
        _set_dept_state(
            mock_leader_agent,
            {
                "current_stage": "pitch",
                "format_type": "series",
                "terminal_stage": "concept",
                "entry_detected": True,
                "stage_status": {"pitch": {"status": "creative_writing", "iterations": 0}},
            },
        )
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert agent_types == ["lead_writer"]

    @pytest.mark.django_db
    def test_lead_writing_done_dispatches_deliverable_gate(self, leader_blueprint, mock_leader_agent):
        from agents.models import AgentTask

        sprint = _set_dept_state(
            mock_leader_agent,
            {
                "current_stage": "pitch",
                "format_type": "series",
                "terminal_stage": "concept",
                "entry_detected": True,
                "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
            },
        )
        # Create a completed lead_writer task so the guard passes
        lead_writer = mock_leader_agent.department.agents.get(agent_type="lead_writer")
        AgentTask.objects.create(
            agent=lead_writer,
            sprint=sprint,
            command_name="write_pitch",
            status=AgentTask.Status.DONE,
            exec_summary="Write the pitch",
            report="# Test Pitch\nA compelling story.",
        )
        with patch.object(leader_blueprint, "_create_deliverable_and_research_docs"):
            proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "authenticity_analyst" in agent_types
        assert "market_analyst" not in agent_types

    @pytest.mark.django_db
    def test_deliverable_gate_done_dispatches_feedback(self, leader_blueprint, mock_leader_agent):
        _set_dept_state(
            mock_leader_agent,
            {
                "current_stage": "pitch",
                "format_type": "series",
                "terminal_stage": "concept",
                "entry_detected": True,
                "stage_status": {"pitch": {"status": "deliverable_gate_done", "iterations": 0}},
            },
        )
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert any(a in agent_types for a in ["market_analyst", "structure_analyst", "character_analyst"])


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
        _set_dept_state(mock_leader_agent, {"format_type": "series"})
        assert leader_blueprint._get_effective_stage(mock_leader_agent, "treatment") == "concept"

    @pytest.mark.django_db
    def test_effective_stage_standalone_treatment(self, leader_blueprint, mock_leader_agent):
        _set_dept_state(mock_leader_agent, {"format_type": "standalone"})
        assert leader_blueprint._get_effective_stage(mock_leader_agent, "treatment") == "treatment"

    @pytest.mark.django_db
    def test_series_documents_titled_concept_not_treatment(self, leader_blueprint, mock_leader_agent):
        """For series, documents at the treatment stage position should be titled 'Concept', not 'Treatment'."""
        _set_dept_state(mock_leader_agent, {"format_type": "series", "stage_status": {"treatment": {"iterations": 0}}})
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
        _set_dept_state(
            mock_leader_agent,
            {
                "format_type": "standalone",
                "stage_status": {"treatment": {"iterations": 0}},
            },
        )
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


class TestDocumentLocking:
    def test_document_has_is_locked_field(self):
        assert hasattr(Document, "is_locked")

    def test_is_locked_defaults_to_false(self):
        field = Document._meta.get_field("is_locked")
        assert field.default is False


class TestApplySectionUpdates:
    @pytest.fixture
    def blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    def test_no_headers_full_replacement(self, blueprint):
        existing = "Old document content without headers."
        revised = "Completely new document content."
        result = blueprint._apply_section_updates(existing, revised)
        assert result == revised

    def test_replace_matching_section(self, blueprint):
        existing = "# Title\n\nIntro.\n\n## Section A\n\nOld content A.\n\n## Section B\n\nContent B."
        revised = "## Section A\n\nNew content A.\n"
        result = blueprint._apply_section_updates(existing, revised)
        assert "New content A." in result
        assert "Old content A." not in result
        assert "Content B." in result

    def test_unmatched_section_appended(self, blueprint):
        existing = "## Section A\n\nContent A."
        revised = "## Section Z\n\nNew content Z.\n"
        result = blueprint._apply_section_updates(existing, revised)
        assert "Content A." in result
        assert "New content Z." in result

    def test_replace_last_section(self, blueprint):
        existing = "## Section A\n\nContent A.\n\n## Section B\n\nOld content B."
        revised = "## Section B\n\nNew content B.\n"
        result = blueprint._apply_section_updates(existing, revised)
        assert "New content B." in result
        assert "Old content B." not in result
        assert "Content A." in result

    def test_respects_header_level(self, blueprint):
        existing = "## Main\n\nIntro.\n\n### Sub A\n\nSub content A.\n\n### Sub B\n\nSub content B.\n\n## Other\n\nOther content."
        revised = "## Main\n\nNew main content.\n"
        result = blueprint._apply_section_updates(existing, revised)
        assert "New main content." in result
        assert "Sub content A." not in result
        assert "Other content." in result

    def test_multiple_sections_replaced(self, blueprint):
        existing = "## Premise\n\nOld premise.\n\n## Characters\n\nOld chars.\n\n## Tone\n\nOld tone."
        revised = "## Premise\n\nNew premise.\n\n## Tone\n\nNew tone.\n"
        result = blueprint._apply_section_updates(existing, revised)
        assert "New premise." in result
        assert "Old premise." not in result
        assert "Old chars." in result  # untouched
        assert "New tone." in result
        assert "Old tone." not in result

    def test_empty_revised_output_keeps_existing(self, blueprint):
        existing = "## Section A\n\nContent."
        result = blueprint._apply_section_updates(existing, "")
        assert result == existing

    def test_whitespace_only_revised_output_keeps_existing(self, blueprint):
        existing = "## Section A\n\nContent."
        result = blueprint._apply_section_updates(existing, "   \n  ")
        assert result == existing


class TestStructureRequirements:
    def test_craft_directives_have_structure_info(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        for key, directive in CRAFT_DIRECTIVES.items():
            assert "## Document Structure" in directive, f"{key} missing structure requirements"

    def test_pitch_no_mandatory_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        d = CRAFT_DIRECTIVES["write_pitch"].lower()
        assert "flowing prose" in d or "no mandatory sections" in d

    def test_expose_requires_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "##" in CRAFT_DIRECTIVES["write_expose"]
        assert "Premise" in CRAFT_DIRECTIVES["write_expose"]

    def test_concept_requires_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        directive = CRAFT_DIRECTIVES["write_concept"]
        assert "Story Engine" in directive
        assert "Characters" in directive
        assert "Episode" in directive

    def test_first_draft_mentions_screenplay_format(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        directive = CRAFT_DIRECTIVES["write_first_draft"]
        assert "SCREENPLAY" in directive or "screenplay" in directive
        assert "slugline" in directive.lower() or "INT." in directive


class TestRevisionAwareDocCreation:
    @pytest.fixture
    def leader_blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    @pytest.fixture
    def mock_leader_agent(self, db):
        from django.contrib.auth import get_user_model

        from agents.models import Agent
        from projects.models import Department, Project

        User = get_user_model()
        user = User.objects.create_user(email="rev-test@example.com", password="pass1234")
        project = Project.objects.create(name="RevTest", goal="Test story", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        return Agent.objects.create(
            department=dept,
            name="Showrunner",
            agent_type="leader",
            is_leader=True,
            status="active",
            internal_state={},
        )

    @pytest.mark.django_db
    def test_new_documents_are_locked(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "The pitch"},
        )
        doc = Document.objects.filter(department=mock_leader_agent.department, doc_type="stage_deliverable").first()
        assert doc.is_locked is True

    @pytest.mark.django_db
    def test_archived_documents_are_unlocked(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "v1"},
        )
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=2,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "v2"},
        )
        archived = Document.objects.filter(
            department=mock_leader_agent.department, doc_type="stage_deliverable", is_archived=True
        ).first()
        assert archived.is_locked is False

    @pytest.mark.django_db
    def test_section_update_applied_to_existing_doc(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="expose",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "## Premise\n\nOld premise.\n\n## Characters\n\nOld chars."},
        )
        existing_doc = Document.objects.filter(
            department=mock_leader_agent.department,
            doc_type="stage_deliverable",
            is_archived=False,
        ).first()
        revised = leader_blueprint._apply_section_updates(existing_doc.content, "## Premise\n\nNew premise.\n")
        assert "New premise." in revised
        assert "Old chars." in revised

    @pytest.mark.django_db
    def test_prose_full_replacement_when_no_headers(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Old pitch content."},
        )
        revised = leader_blueprint._apply_section_updates("Old pitch content.", "Completely new pitch content.")
        assert revised == "Completely new pitch content."


def _make_mock_sprint(dept_state=None):
    """Create a mock sprint with get/set_department_state."""
    state = {"mock-dept-id": dept_state or {}}
    sprint = MagicMock()
    sprint.text = "Test sprint"

    def get_dept_state(dept_id):
        return state.get(dept_id, {})

    def set_dept_state(dept_id, new_state):
        state[dept_id] = new_state

    sprint.get_department_state = MagicMock(side_effect=get_dept_state)
    sprint.set_department_state = MagicMock(side_effect=set_dept_state)
    return sprint


class TestRevisionInstructions:
    @pytest.fixture
    def leader_blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    def test_lead_writer_iteration_0_no_revision_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint(
            {
                "format_type": "standalone",
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "lead_writing_pending", "iterations": 0}},
            }
        )
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "pitch", {"locale": "en"}, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION MODE" not in step_plan

    def test_lead_writer_iteration_1_has_section_revision_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint(
            {
                "format_type": "standalone",
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "lead_writing_pending", "iterations": 1}},
            }
        )
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "pitch", {"locale": "en"}, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION MODE" in step_plan
        assert "sections you changed" in step_plan
        # No JSON instructions
        assert "old_text" not in step_plan
        assert "revision JSON" not in step_plan

    def test_lead_writer_revision_no_json_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint(
            {
                "format_type": "standalone",
                "current_stage": "expose",
                "stage_status": {"expose": {"status": "lead_writing_pending", "iterations": 1}},
            }
        )
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "expose", {"locale": "en"}, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]
        assert "replace_section" not in step_plan
        assert "replace_between" not in step_plan
        assert "revision JSON" not in step_plan
        assert "Output ONLY the JSON" not in step_plan

    def test_creative_agents_iteration_0_no_revision_preamble(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.department_id = "mock-dept-id"
        mock_agent.get_config_value.return_value = None
        sprint = _make_mock_sprint({"stage_status": {"pitch": {"iterations": 0}}, "current_stage": "pitch"})
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"}, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION ROUND" not in step_plan

    def test_creative_agents_iteration_1_has_revision_preamble(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.department_id = "mock-dept-id"
        mock_agent.get_config_value.return_value = None
        sprint = _make_mock_sprint({"stage_status": {"pitch": {"iterations": 1}}, "current_stage": "pitch"})
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"}, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION ROUND" in step_plan
        assert "critique" in step_plan.lower()


class TestSprintOutput:
    @pytest.fixture
    def leader_blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    @pytest.fixture
    def sprint_setup(self, db):
        from django.contrib.auth import get_user_model

        from agents.models import Agent
        from projects.models import Department, Project, Sprint

        User = get_user_model()
        user = User.objects.create_user(email="sprint-output@test.com", password="test")
        project = Project.objects.create(name="OutputTest", goal="Test", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        leader = Agent.objects.create(
            department=dept,
            name="Showrunner",
            agent_type="leader",
            is_leader=True,
            status="active",
            internal_state={},
        )
        sprint = Sprint.objects.create(
            project=project, text="Write a pitch", created_by=user, status=Sprint.Status.RUNNING
        )
        sprint.departments.add(dept)
        sprint.set_department_state(str(dept.id), {"format_type": "standalone"})
        return leader, sprint

    @pytest.mark.django_db
    def test_update_sprint_output_creates_output(self, leader_blueprint, sprint_setup):
        leader, sprint = sprint_setup
        leader_blueprint._update_sprint_output(leader, sprint, "pitch", "The pitch content")
        output = Output.objects.filter(sprint=sprint, department=leader.department).first()
        assert output is not None
        assert output.title == "Pitch Deliverable"
        assert output.label == "pitch:deliverable"
        assert output.output_type == "markdown"
        assert output.content == "The pitch content"

    @pytest.mark.django_db
    def test_update_sprint_output_updates_in_place(self, leader_blueprint, sprint_setup):
        leader, sprint = sprint_setup
        leader_blueprint._update_sprint_output(leader, sprint, "pitch", "v1")
        leader_blueprint._update_sprint_output(leader, sprint, "pitch", "v2")
        assert Output.objects.filter(sprint=sprint, department=leader.department).count() == 1
        output = Output.objects.get(sprint=sprint, department=leader.department)
        assert output.content == "v2"

    @pytest.mark.django_db
    def test_series_output_titled_concept(self, leader_blueprint, sprint_setup):
        leader, sprint = sprint_setup
        sprint.set_department_state(str(leader.department_id), {"format_type": "series"})
        leader_blueprint._update_sprint_output(leader, sprint, "treatment", "Series concept")
        output = Output.objects.get(sprint=sprint, department=leader.department)
        assert output.title == "Concept Deliverable"
        assert output.label == "concept:deliverable"


class TestLeadWriterRevisionPrompt:
    def test_revision_step_plan_uses_section_mode(self):
        """Revision step_plan must instruct section-based output, not JSON."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint(
            {
                "current_stage": "expose",
                "format_type": "standalone",
                "stage_status": {"expose": {"iterations": 1}},
            }
        )
        config = {"locale": "en"}

        result = bp._propose_lead_writer_task(agent, "expose", config, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]

        assert "REVISION MODE" in step_plan
        assert "sections you changed" in step_plan
        assert "revision JSON" not in step_plan
        assert "Output ONLY the JSON" not in step_plan

    def test_revision_step_plan_includes_research_hint(self):
        """Revision step_plan must hint at incorporating creative agents' work."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint(
            {
                "current_stage": "expose",
                "format_type": "standalone",
                "stage_status": {"expose": {"iterations": 1}},
            }
        )
        config = {"locale": "en"}

        result = bp._propose_lead_writer_task(agent, "expose", config, sprint=sprint)
        step_plan = result["tasks"][0]["step_plan"]

        assert "Research & Notes" in step_plan
        assert "creative agents" in step_plan.lower()


class TestUpdateSprintOutput:
    def test_update_sprint_output_uses_label_with_type(self):
        """_update_sprint_output must include output_type in the label."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint({"format_type": "standalone"})

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content", "deliverable")
            call_kwargs = mock_uoc.call_args
            assert (
                call_kwargs.kwargs["label"] == "expose:deliverable"
                or call_kwargs[1]["label"] == "expose:deliverable"
                or "expose:deliverable" in str(call_kwargs)
            )

    def test_update_sprint_output_critique_label(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint({"format_type": "standalone"})

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content", "critique")
            call_kwargs = mock_uoc.call_args
            assert "expose:critique" in str(call_kwargs)

    def test_update_sprint_output_default_is_deliverable(self):
        """output_type defaults to 'deliverable' for backwards compatibility."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.department_id = "mock-dept-id"
        sprint = _make_mock_sprint({"format_type": "standalone"})

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content")
            call_kwargs = mock_uoc.call_args
            assert "expose:deliverable" in str(call_kwargs)

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


class TestDocumentLocking:
    def test_document_has_is_locked_field(self):
        assert hasattr(Document, "is_locked")

    def test_is_locked_defaults_to_false(self):
        field = Document._meta.get_field("is_locked")
        assert field.default is False


class TestApplyRevisions:
    @pytest.fixture
    def blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    def test_replace_single_match(self, blueprint):
        content = "The cat sat on the mat. The dog ran in the park."
        revisions = [{"type": "replace", "old_text": "sat on the mat", "new_text": "slept on the rug"}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "slept on the rug" in result
        assert "sat on the mat" not in result
        assert len(failed) == 0

    def test_replace_not_found(self, blueprint):
        content = "The cat sat on the mat."
        revisions = [{"type": "replace", "old_text": "the dog barked", "new_text": "the dog whispered"}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert result == content
        assert len(failed) == 1
        assert failed[0]["reason"] == "not_found"

    def test_replace_ambiguous(self, blueprint):
        content = "The cat sat. The cat sat. The dog ran."
        revisions = [{"type": "replace", "old_text": "The cat sat.", "new_text": "The cat slept."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert result == content
        assert len(failed) == 1
        assert "ambiguous" in failed[0]["reason"]

    def test_replace_section_basic(self, blueprint):
        content = "# Title\n\nIntro.\n\n## Section A\n\nOld content A.\n\n## Section B\n\nContent B."
        revisions = [{"type": "replace_section", "section": "## Section A", "new_content": "New content A."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "New content A." in result
        assert "Old content A." not in result
        assert "Content B." in result
        assert len(failed) == 0

    def test_replace_section_not_found(self, blueprint):
        content = "## Section A\n\nContent."
        revisions = [{"type": "replace_section", "section": "## Section Z", "new_content": "New."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert result == content
        assert len(failed) == 1
        assert failed[0]["reason"] == "section_not_found"

    def test_replace_section_last_section(self, blueprint):
        content = "## Section A\n\nContent A.\n\n## Section B\n\nOld content B."
        revisions = [{"type": "replace_section", "section": "## Section B", "new_content": "New content B."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "New content B." in result
        assert "Old content B." not in result
        assert "Content A." in result

    def test_replace_between_basic(self, blueprint):
        content = "Opening.\n\nStart marker text.\n\nMiddle content to replace.\n\nEnd marker text.\n\nClosing."
        revisions = [
            {
                "type": "replace_between",
                "start": "Start marker text.",
                "end": "End marker text.",
                "new_content": "Completely new middle.",
            }
        ]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "Completely new middle." in result
        assert "Middle content to replace." not in result
        assert "Opening." in result
        assert "Closing." in result
        assert len(failed) == 0

    def test_replace_between_anchors_not_found(self, blueprint):
        content = "Some content."
        revisions = [
            {"type": "replace_between", "start": "nonexistent start", "end": "nonexistent end", "new_content": "new"}
        ]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert result == content
        assert len(failed) == 1
        assert failed[0]["reason"] == "anchors_not_found"

    def test_multiple_revisions_applied_sequentially(self, blueprint):
        content = "Alice went home. Bob went to work. Carol stayed."
        revisions = [
            {"type": "replace", "old_text": "Alice went home.", "new_text": "Alice ran home."},
            {"type": "replace", "old_text": "Bob went to work.", "new_text": "Bob drove to work."},
        ]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "Alice ran home." in result
        assert "Bob drove to work." in result
        assert "Carol stayed." in result
        assert len(failed) == 0

    def test_replace_section_respects_header_level(self, blueprint):
        content = "## Main\n\nIntro.\n\n### Sub A\n\nSub content A.\n\n### Sub B\n\nSub content B.\n\n## Other\n\nOther content."
        revisions = [{"type": "replace_section", "section": "## Main", "new_content": "New main content."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "New main content." in result
        assert "Sub content A." not in result
        assert "Other content." in result


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
    def test_revision_json_applied_to_existing_doc(self, leader_blueprint, mock_leader_agent):
        import json

        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "The old pitch content. This part stays."},
        )
        revision_json = json.dumps(
            {
                "revisions": [
                    {"type": "replace", "old_text": "The old pitch content.", "new_text": "The new pitch content."}
                ],
                "preserved": "Kept: This part stays.",
            }
        )
        revised, applied = leader_blueprint._apply_revision_or_replace(
            agent=mock_leader_agent,
            doc_type="stage_deliverable",
            new_content=revision_json,
            stage="pitch",
        )
        assert "The new pitch content." in revised
        assert "This part stays." in revised
        assert applied is True

    @pytest.mark.django_db
    def test_prose_fallback_when_not_json(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Old content."},
        )
        revised, applied = leader_blueprint._apply_revision_or_replace(
            agent=mock_leader_agent,
            doc_type="stage_deliverable",
            new_content="Completely new prose content.",
            stage="pitch",
        )
        assert revised == "Completely new prose content."
        assert applied is False


class TestRevisionInstructions:
    @pytest.fixture
    def leader_blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    def test_lead_writer_iteration_0_no_revision_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.internal_state = {
            "format_type": "standalone",
            "current_stage": "pitch",
            "stage_status": {"pitch": {"status": "creative_done", "iterations": 0}},
        }
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION MODE" not in step_plan

    def test_lead_writer_iteration_1_has_revision_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.internal_state = {
            "format_type": "standalone",
            "current_stage": "pitch",
            "stage_status": {"pitch": {"status": "creative_done", "iterations": 1}},
        }
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION MODE" in step_plan
        assert "replace" in step_plan.lower()
        assert "old_text" in step_plan

    def test_lead_writer_expose_has_replace_section(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.internal_state = {
            "format_type": "standalone",
            "current_stage": "expose",
            "stage_status": {"expose": {"status": "creative_done", "iterations": 1}},
        }
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "expose", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "replace_section" in step_plan

    def test_lead_writer_first_draft_has_replace_between(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.internal_state = {
            "format_type": "standalone",
            "current_stage": "first_draft",
            "stage_status": {"first_draft": {"status": "creative_done", "iterations": 1}},
        }
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "first_draft", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "replace_between" in step_plan

    def test_creative_agents_iteration_0_no_revision_preamble(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.internal_state = {"stage_status": {"pitch": {"iterations": 0}}, "current_stage": "pitch"}
        mock_agent.get_config_value.return_value = None
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION ROUND" not in step_plan

    def test_creative_agents_iteration_1_has_revision_preamble(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.internal_state = {"stage_status": {"pitch": {"iterations": 1}}, "current_stage": "pitch"}
        mock_agent.get_config_value.return_value = None
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "REVISION ROUND" in step_plan
        assert "Critique" in step_plan


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
            internal_state={"format_type": "standalone"},
        )
        sprint = Sprint.objects.create(project=project, text="Write a pitch", created_by=user)
        sprint.departments.add(dept)
        return leader, sprint

    @pytest.mark.django_db
    def test_update_sprint_output_creates_output(self, leader_blueprint, sprint_setup):
        leader, sprint = sprint_setup
        leader_blueprint._update_sprint_output(leader, sprint, "pitch", "The pitch content")
        output = Output.objects.filter(sprint=sprint, department=leader.department).first()
        assert output is not None
        assert output.title == "Pitch"
        assert output.label == "pitch"
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
        leader.internal_state = {"format_type": "series"}
        leader.save(update_fields=["internal_state"])
        leader_blueprint._update_sprint_output(leader, sprint, "treatment", "Series concept")
        output = Output.objects.get(sprint=sprint, department=leader.department)
        assert output.title == "Concept"
        assert output.label == "concept"


class TestLeadWriterRevisionPrompt:
    def test_revision_step_plan_requires_json_only(self):
        """Revision step_plan must instruct the model to output only JSON."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
        from unittest.mock import MagicMock

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.internal_state = {
            "current_stage": "expose",
            "format_type": "standalone",
            "stage_status": {"expose": {"iterations": 1}},
        }
        config = {"locale": "en"}

        result = bp._propose_lead_writer_task(agent, "expose", config)
        step_plan = result["tasks"][0]["step_plan"]

        assert "Output ONLY the JSON" in step_plan
        assert "No preamble" in step_plan

    def test_revision_step_plan_includes_research_hint(self):
        """Revision step_plan must hint at incorporating praised research material."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
        from unittest.mock import MagicMock

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.internal_state = {
            "current_stage": "expose",
            "format_type": "standalone",
            "stage_status": {"expose": {"iterations": 1}},
        }
        config = {"locale": "en"}

        result = bp._propose_lead_writer_task(agent, "expose", config)
        step_plan = result["tasks"][0]["step_plan"]

        assert "stage research document" in step_plan
        assert "creative decision is yours" in step_plan

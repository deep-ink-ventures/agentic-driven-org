"""Tests for the Writers Room state machine (generate_task_proposal orchestration).

Covers every state transition, edge case, and assumption in the
writers room leader's generate_task_proposal loop.
"""

import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from agents.blueprints.writers_room.leader.agent import (
    CREATIVE_MATRIX,
    FEEDBACK_MATRIX,
    WritersRoomLeaderBlueprint,
    _next_stage,
)


def _uuid():
    return str(uuid.uuid4())


# ── Mock factories ─────────────────────────────────────────────────────────


def _make_sprint(dept_id, dept_state=None):
    """Return a mock Sprint with get/set_department_state."""
    sprint = MagicMock()
    sprint.id = _uuid()
    sprint.text = "test sprint"
    sprint.status = "running"
    _states = {dept_id: dept_state or {}}

    def get_dept_state(did):
        return dict(_states.get(did, {}))

    def set_dept_state(did, state):
        _states[did] = state

    sprint.get_department_state = MagicMock(side_effect=get_dept_state)
    sprint.set_department_state = MagicMock(side_effect=set_dept_state)
    sprint._states = _states
    return sprint


def _make_agent(dept_id, active_agent_types=None, config=None):
    """Return a mock leader Agent."""
    agent = MagicMock()
    agent.id = _uuid()
    agent.name = "Showrunner"
    agent.is_leader = True
    agent.department_id = dept_id
    agent.department.id = dept_id
    agent.department.department_type = "writers_room"
    agent.department.config = config or {}
    agent.department.project.config = {}
    agent.config = {}
    agent.internal_state = {}

    def get_config_value(key):
        return (config or {}).get(key)

    agent.get_config_value = get_config_value

    if active_agent_types is None:
        active_agent_types = list(CREATIVE_MATRIX.get("pitch", []))

    qs = MagicMock()
    qs.values_list.return_value = active_agent_types
    agent.department.agents.filter.return_value = qs

    return agent


def _patch_agent_task():
    """Patch AgentTask at the models module level (local imports read from there)."""
    return patch("agents.models.AgentTask")


def _setup_task_mock(MockTask, active_tasks=None):
    """Configure an AgentTask mock with standard Status attrs and no active tasks."""
    MockTask.Status = MagicMock()
    MockTask.Status.PROCESSING = "processing"
    MockTask.Status.QUEUED = "queued"
    MockTask.Status.AWAITING_APPROVAL = "awaiting_approval"
    MockTask.Status.AWAITING_DEPENDENCIES = "awaiting_dependencies"
    MockTask.Status.PLANNED = "planned"
    MockTask.Status.DONE = "done"

    # Default: no active tasks
    if active_tasks is None:
        MockTask.objects.filter.return_value.values_list.return_value = []
        MockTask.objects.filter.return_value.exists.return_value = False
    else:
        MockTask.objects.filter.return_value.values_list.return_value = active_tasks

    return MockTask


def _run_proposal(bp, agent, sprint, MockTask, doc_exists=True):
    """Run generate_task_proposal with standard mocks.

    Patches Sprint query to return our mock sprint, and Document.exists
    to control voice profile gate.
    """
    with patch("projects.models.Sprint") as MockSprint:
        qs = MagicMock()
        qs.exists.return_value = True
        qs.order_by.return_value.first.return_value = sprint
        MockSprint.objects.filter.return_value = qs
        MockSprint.Status = MagicMock(RUNNING="running", DONE="done")
        with (
            patch.object(bp, "_get_current_sprint", return_value=sprint),
            patch("agents.blueprints.writers_room.leader.agent.Document") as MockDoc,
        ):
            MockDoc.objects.filter.return_value.exists.return_value = doc_exists
            MockDoc.objects.filter.return_value.exclude.return_value.exists.return_value = doc_exists
            return bp.generate_task_proposal(agent)


# ── _next_stage tests ──────────────────────────────────────────────────────


class TestNextStage(TestCase):
    def test_pitch_to_expose(self):
        self.assertEqual(_next_stage("pitch"), "expose")

    def test_expose_to_treatment(self):
        self.assertEqual(_next_stage("expose"), "treatment")

    def test_treatment_to_first_draft(self):
        self.assertEqual(_next_stage("treatment"), "first_draft")

    def test_first_draft_is_terminal(self):
        self.assertIsNone(_next_stage("first_draft"))

    def test_unknown_stage_returns_none(self):
        self.assertIsNone(_next_stage("nonexistent"))


# ── State: not_started ─────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestNotStarted(TestCase):
    """not_started → creative tasks for all active creative agents."""

    def test_proposes_creative_agents(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["pitch"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        tasks = result.get("tasks", [])
        proposed_types = {t["target_agent_type"] for t in tasks}
        self.assertEqual(proposed_types, set(all_creative))
        self.assertEqual(result["_on_dispatch"]["set_status"], "creative_writing")

    def test_proposes_only_active_agents(self):
        dept_id = _uuid()
        active = ["story_researcher", "dialog_writer"]
        agent = _make_agent(dept_id, active_agent_types=active)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        tasks = result.get("tasks", [])
        proposed_types = {t["target_agent_type"] for t in tasks}
        self.assertEqual(proposed_types, set(active))


# ── Voice profiling gate ───────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestVoiceProfilingGate(TestCase):
    """No voice profile + source material → voice_profiling status."""

    def test_triggers_profiling_when_no_voice_profile(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            with patch("projects.models.Sprint") as MockSprint:
                qs = MagicMock()
                qs.exists.return_value = True
                qs.order_by.return_value.first.return_value = sprint
                MockSprint.objects.filter.return_value = qs
                MockSprint.Status = MagicMock(RUNNING="running")
                with (
                    patch.object(bp, "_get_current_sprint", return_value=sprint),
                    patch("agents.blueprints.writers_room.leader.agent.Document") as MockDoc,
                ):
                    # voice_profile check → False, source material → True
                    voice_qs = MagicMock()
                    voice_qs.exists.return_value = False
                    source_qs = MagicMock()
                    source_qs.exists.return_value = True
                    voice_qs.exclude.return_value = source_qs

                    MockDoc.objects.filter.return_value = voice_qs

                    result = bp.generate_task_proposal(agent)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "voice_profiling")
        self.assertEqual(result["tasks"][0]["target_agent_type"], "story_researcher")
        self.assertEqual(result["tasks"][0]["command_name"], "profile_voice")

    def test_voice_profiling_done_dispatches_creative_agents(self):
        """After voice profiling: voice_profiling → not_started → creative tasks."""
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["pitch"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "voice_profiling", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "creative_writing")
        proposed_types = {t["target_agent_type"] for t in result["tasks"]}
        self.assertEqual(proposed_types, set(all_creative))


# ── State: creative_writing ────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestCreativeWritingToLeadWriter(TestCase):
    """creative_writing → lead_writing_pending → dispatch lead writer."""

    def test_dispatches_lead_writer(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "creative_writing", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "lead_writing")
        self.assertEqual(result["tasks"][0]["target_agent_type"], "lead_writer")
        # Intermediate state should be lead_writing_pending
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "lead_writing_pending")


# ── State: lead_writing ────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestLeadWriting(TestCase):
    """lead_writing → wait or dispatch deliverable gate."""

    def test_waits_if_lead_writer_not_done(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            # No active tasks but lead_writer NOT done
            MockTask.objects.filter.return_value.exists.return_value = False
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNone(result)

    def test_dispatches_gate_when_done(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            # lead_writer done: the first filter().exists() is for active tasks (False),
            # the second filter().exists() is for lead_writer done (True).
            # We need the active tasks check to return empty list, and lead_writer done to return True.
            # Active tasks: filter().values_list() returns []
            # Lead writer done: filter().exists() returns True
            MockTask.objects.filter.return_value.values_list.return_value = []
            MockTask.objects.filter.return_value.exists.return_value = True
            with patch.object(bp, "_create_deliverable_and_research_docs"):
                result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["tasks"][0]["target_agent_type"], "authenticity_analyst")
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "deliverable_gate")


# ── State: deliverable_gate ────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestDeliverableGate(TestCase):
    """deliverable_gate → deliverable_gate_done → feedback agents."""

    def test_dispatches_feedback_agents(self):
        dept_id = _uuid()
        feedback_types = [at for at, _ in FEEDBACK_MATRIX.get("pitch", [])]
        creative_types = list(CREATIVE_MATRIX.get("pitch", []))
        all_active = list(set(feedback_types + creative_types))
        agent = _make_agent(dept_id, active_agent_types=all_active)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "deliverable_gate", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "feedback")
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "deliverable_gate_done")


# ── State: feedback ────────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestFeedback(TestCase):
    """feedback → feedback_done → creative_reviewer."""

    def test_dispatches_creative_reviewer(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "feedback", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            # review task query for feedback text
            MockTask.objects.filter.return_value.order_by.return_value.__getitem__ = lambda self, s: MagicMock(
                values_list=MagicMock(return_value=[])
            )
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "review")
        self.assertEqual(result["tasks"][0]["target_agent_type"], "creative_reviewer")
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "feedback_done")


# ── State: review ──────────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestReviewOutcomes(TestCase):
    """review → pass/fail/weak_idea/escalate."""

    def _make_review_task(self, score, verdict="CHANGES_REQUESTED"):
        task = MagicMock()
        task.review_score = score
        task.review_verdict = verdict
        task.report = "test report"
        return task

    def test_high_score_passes_and_advances(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["expose"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "review", "iterations": 1}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        review_task = self._make_review_task(score=9.8, verdict="APPROVED")

        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            MockTask.objects.filter.return_value.order_by.return_value.first.return_value = review_task
            with patch.object(bp, "_create_critique_doc"), patch.object(bp, "_update_story_bible"):
                result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "creative_writing")
        saved = sprint._states[dept_id]
        self.assertEqual(saved["current_stage"], "expose")
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "passed")

    def test_low_score_loops_back(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["pitch"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "review", "iterations": 1}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        review_task = self._make_review_task(score=6.0, verdict="CHANGES_REQUESTED")

        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            MockTask.objects.filter.return_value.order_by.return_value.first.return_value = review_task
            with patch.object(bp, "_create_critique_doc"):
                result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        saved = sprint._states[dept_id]
        self.assertEqual(saved["current_stage"], "pitch")  # still pitch

    def test_weak_idea_resets_iterations(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["pitch"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "review", "iterations": 2}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        review_task = self._make_review_task(score=4.0, verdict="WEAK_IDEA")

        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            MockTask.objects.filter.return_value.order_by.return_value.first.return_value = review_task
            with patch.object(bp, "_create_critique_doc"):
                result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["iterations"], 0)
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "not_started")


# ── Escalation ─────────────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestMaxReviewRoundsEscalation(TestCase):
    """Safety cap triggers human escalation."""

    def test_escalates_at_max_rounds(self):
        from agents.blueprints.base import MAX_REVIEW_ROUNDS

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": MAX_REVIEW_ROUNDS}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertIn("ESCALATION", result["exec_summary"])


# ── Active tasks blocking ──────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestActiveTasksBlocking(TestCase):
    """Active tasks in department block new proposals."""

    def test_returns_none_when_tasks_active(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(
                MockTask,
                active_tasks=[
                    ("Writing pitch", "processing", "dialog_writer", "Dialog Writer"),
                ],
            )
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNone(result)


# ── Stage advancement ──────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestStageAdvancement(TestCase):
    """Stage passed → advance or complete sprint."""

    def test_terminal_stage_completes_sprint(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "treatment",
                "stage_status": {"treatment": {"status": "review", "iterations": 1}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )
        sprint.save = MagicMock()

        bp = WritersRoomLeaderBlueprint()
        review_task = MagicMock()
        review_task.review_score = 9.8
        review_task.review_verdict = "APPROVED"
        review_task.report = "Excellent"

        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            MockTask.objects.filter.return_value.order_by.return_value.first.return_value = review_task
            with (
                patch.object(bp, "_create_critique_doc"),
                patch.object(bp, "_update_story_bible"),
                patch("projects.views.sprint_view._broadcast_sprint"),
            ):
                result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNone(result)
        self.assertEqual(sprint.status, "done")

    def test_passed_stage_advances_on_next_invocation(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["expose"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "passed"}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        saved = sprint._states[dept_id]
        self.assertEqual(saved["current_stage"], "expose")


# ── Series concept slot ────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestSeriesConceptSlot(TestCase):
    """Series: treatment slot → concept."""

    def test_effective_stage_is_concept(self):
        bp = WritersRoomLeaderBlueprint()
        agent = _make_agent(_uuid())
        sprint = _make_sprint(str(agent.department_id), {"format_type": "series"})
        self.assertEqual(bp._get_effective_stage(agent, "treatment", sprint=sprint), "concept")

    def test_effective_stage_unchanged_standalone(self):
        bp = WritersRoomLeaderBlueprint()
        agent = _make_agent(_uuid())
        sprint = _make_sprint(str(agent.department_id), {"format_type": "standalone"})
        self.assertEqual(bp._get_effective_stage(agent, "treatment", sprint=sprint), "treatment")


# ── No creative agents → skip stage ───────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestNoCreativeAgentsSkipsStage(TestCase):
    """No active creative agents → auto-pass stage."""

    def test_skips_to_next_stage(self):
        dept_id = _uuid()
        # No creative agents active
        agent = _make_agent(dept_id, active_agent_types=[])
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            # _propose_creative_tasks recurses when skipping — eventually returns None
            # if all stages have no creative agents
            _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "passed")


# ── Retry states ───────────────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestRetryStates(TestCase):
    """Retry/pending states dispatch the expected agent."""

    def test_lead_writing_pending_dispatches_lead_writer(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "lead_writing_pending", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "lead_writing")
        self.assertEqual(result["tasks"][0]["target_agent_type"], "lead_writer")

    def test_feedback_done_dispatches_reviewer(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "feedback_done", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            MockTask.objects.filter.return_value.order_by.return_value.__getitem__ = lambda self, s: MagicMock(
                values_list=MagicMock(return_value=[])
            )
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "review")
        self.assertEqual(result["tasks"][0]["target_agent_type"], "creative_reviewer")

    def test_deliverable_gate_done_dispatches_feedback(self):
        dept_id = _uuid()
        feedback_types = [at for at, _ in FEEDBACK_MATRIX.get("pitch", [])]
        creative_types = list(CREATIVE_MATRIX.get("pitch", []))
        all_active = list(set(feedback_types + creative_types))
        agent = _make_agent(dept_id, active_agent_types=all_active)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "deliverable_gate_done", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask)

        self.assertIsNotNone(result)
        self.assertEqual(result["_on_dispatch"]["set_status"], "feedback")


# ── Unknown status reset ──────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestUnknownStatusReset(TestCase):
    """Bogus status → reset to not_started."""

    def test_resets_and_proposes_creative(self):
        dept_id = _uuid()
        all_creative = list(CREATIVE_MATRIX["pitch"])
        agent = _make_agent(dept_id, active_agent_types=all_creative)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "bogus_state", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        self.assertIsNotNone(result)
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "not_started")
        self.assertEqual(result["_on_dispatch"]["set_status"], "creative_writing")


# ── Lead writer command mapping ────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestLeadWriterCommandMapping(TestCase):
    """Lead writer gets correct command per stage/format."""

    def _get_command(self, stage, format_type="standalone"):
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": stage,
                "stage_status": {},
                "format_type": format_type,
            },
        )
        with patch.object(bp, "_get_current_sprint", return_value=sprint):
            result = bp._propose_lead_writer_task(agent, stage, {"locale": "en"}, sprint=sprint)
        return result["tasks"][0]["command_name"]

    def test_pitch(self):
        self.assertEqual(self._get_command("pitch"), "write_pitch")

    def test_expose(self):
        self.assertEqual(self._get_command("expose"), "write_expose")

    def test_treatment_standalone(self):
        self.assertEqual(self._get_command("treatment", "standalone"), "write_treatment")

    def test_treatment_series(self):
        self.assertEqual(self._get_command("treatment", "series"), "write_concept")

    def test_first_draft(self):
        self.assertEqual(self._get_command("first_draft"), "write_first_draft")


# ── No sprint → no work ───────────────────────────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestNoSprintNoWork(TestCase):
    """No running sprint → return None."""

    def test_returns_none(self):
        dept_id = _uuid()
        agent = _make_agent(dept_id)

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            with patch("projects.models.Sprint") as MockSprint:
                qs = MagicMock()
                qs.exists.return_value = False
                MockSprint.objects.filter.return_value = qs
                MockSprint.Status = MagicMock(RUNNING="running")
                result = bp.generate_task_proposal(agent)

        self.assertIsNone(result)


# ── #26: _apply_on_dispatch writes status to sprint state ──────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestApplyOnDispatch(TestCase):
    """_apply_on_dispatch correctly persists status to sprint department_state."""

    def test_sets_status_on_sprint(self):
        from agents.tasks import _apply_on_dispatch

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 0}},
            },
        )

        with patch("projects.models.Sprint") as MockSprint:
            MockSprint.objects.filter.return_value.first.return_value = sprint
            _apply_on_dispatch(agent, {"set_status": "creative_writing", "stage": "pitch"}, sprint_id=sprint.id)

        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "creative_writing")

    def test_preserves_iterations(self):
        from agents.tasks import _apply_on_dispatch

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "not_started", "iterations": 3}},
            },
        )

        with patch("projects.models.Sprint") as MockSprint:
            MockSprint.objects.filter.return_value.first.return_value = sprint
            _apply_on_dispatch(agent, {"set_status": "feedback", "stage": "pitch"}, sprint_id=sprint.id)

        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["iterations"], 3)
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "feedback")

    def test_no_op_without_set_status(self):
        from agents.tasks import _apply_on_dispatch

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "stage_status": {"pitch": {"status": "not_started"}},
            },
        )

        with patch("projects.models.Sprint") as MockSprint:
            MockSprint.objects.filter.return_value.first.return_value = sprint
            _apply_on_dispatch(agent, {}, sprint_id=sprint.id)

        # State should be unchanged
        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "not_started")

    def test_fallback_to_agent_internal_state_without_sprint(self):
        from agents.tasks import _apply_on_dispatch

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        agent.internal_state = {"stage_status": {"pitch": {"status": "not_started", "iterations": 0}}}
        agent.refresh_from_db = MagicMock()
        agent.save = MagicMock()

        _apply_on_dispatch(agent, {"set_status": "creative_writing", "stage": "pitch"})

        agent.save.assert_called_once()
        self.assertEqual(agent.internal_state["stage_status"]["pitch"]["status"], "creative_writing")


# ── #27: No feedback agents → stage passes without review ──────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestNoFeedbackAgentsPassesStage(TestCase):
    """When all feedback agents are inactive, stage passes without review."""

    def test_passes_stage_and_advances(self):
        dept_id = _uuid()
        # Only a creative agent active, no feedback agents
        agent = _make_agent(dept_id, active_agent_types=["dialog_writer"])
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "pitch",
                "stage_status": {"pitch": {"status": "deliverable_gate", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["pitch"]["status"], "passed")
        # Should have advanced to expose
        self.assertEqual(saved["current_stage"], "expose")

    def test_no_feedback_at_terminal_returns_none(self):
        """No feedback agents at terminal stage → stage passes, sprint complete."""
        dept_id = _uuid()
        agent = _make_agent(dept_id, active_agent_types=["dialog_writer"])
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "treatment",
                "stage_status": {"treatment": {"status": "deliverable_gate", "iterations": 0}},
                "entry_detected": True,
                "terminal_stage": "treatment",
                "format_type": "standalone",
            },
        )

        bp = WritersRoomLeaderBlueprint()
        with _patch_agent_task() as MockTask:
            _setup_task_mock(MockTask)
            result = _run_proposal(bp, agent, sprint, MockTask, doc_exists=True)

        saved = sprint._states[dept_id]
        self.assertEqual(saved["stage_status"]["treatment"]["status"], "passed")
        # At terminal, returns None (no next stage)
        self.assertIsNone(result)


# ── #28: Feedback agent skipped when controlled creative is inactive ───────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestFeedbackControllerFiltering(TestCase):
    """Feedback agents are skipped when their controlled creative is inactive."""

    def test_dialogue_analyst_skipped_without_dialog_writer(self):
        """dialogue_analyst controls dialog_writer — skip if dialog_writer inactive."""
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        # structure_analyst active, but NOT dialog_writer
        # So dialogue_analyst should be skipped
        agent = _make_agent(
            dept_id,
            active_agent_types=[
                "structure_analyst",
                "character_analyst",
                "market_analyst",
                "dialogue_analyst",  # feedback agent is active...
                "story_architect",  # ...but its controlled creative is NOT active
            ],
        )
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "treatment",
                "stage_status": {},
                "format_type": "standalone",
            },
        )

        with patch.object(bp, "_get_current_sprint", return_value=sprint):
            result = bp._propose_feedback_tasks(agent, "treatment", {"locale": "en"}, sprint=sprint)

        if result and "tasks" in result:
            proposed_types = {t["target_agent_type"] for t in result["tasks"]}
            # dialogue_analyst should be filtered because dialog_writer is not in active_types
            self.assertNotIn("dialogue_analyst", proposed_types)

    def test_feedback_agent_included_when_controlled_creative_active(self):
        """dialogue_analyst IS included when dialog_writer is active."""
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(
            dept_id,
            active_agent_types=[
                "structure_analyst",
                "character_analyst",
                "dialogue_analyst",
                "dialog_writer",  # controlled creative IS active
                "story_architect",
                "character_designer",
            ],
        )
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": "treatment",
                "stage_status": {},
                "format_type": "standalone",
            },
        )

        with patch.object(bp, "_get_current_sprint", return_value=sprint):
            result = bp._propose_feedback_tasks(agent, "treatment", {"locale": "en"}, sprint=sprint)

        self.assertIsNotNone(result)
        proposed_types = {t["target_agent_type"] for t in result["tasks"]}
        self.assertIn("dialogue_analyst", proposed_types)


# ── #29: Revision mode (iteration > 0) sends revision instructions ────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestLeadWriterRevisionMode(TestCase):
    """iteration > 0 triggers revision instructions instead of synthesis."""

    def _get_step_plan(self, stage, iteration, format_type="standalone"):
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(
            dept_id,
            {
                "current_stage": stage,
                "stage_status": {stage: {"iterations": iteration}},
                "format_type": format_type,
            },
        )
        with patch.object(bp, "_get_current_sprint", return_value=sprint):
            result = bp._propose_lead_writer_task(agent, stage, {"locale": "de"}, sprint=sprint)
        return result["tasks"][0]["step_plan"]

    def test_iteration_0_is_synthesis(self):
        plan = self._get_step_plan("pitch", 0)
        self.assertIn("Synthesize", plan)
        self.assertNotIn("REVISION", plan)

    def test_iteration_1_is_revision(self):
        plan = self._get_step_plan("pitch", 1)
        self.assertIn("REVISION MODE", plan)
        self.assertIn("Round: 2", plan)
        self.assertIn("revision JSON", plan)

    def test_pitch_revision_ops_note_only_replace(self):
        plan = self._get_step_plan("pitch", 1)
        # The ops_note line for pitch should only mention replace
        self.assertIn("Available operations: replace (surgical text edits).", plan)
        # Should NOT include replace_section or replace_between in the ops_note
        self.assertNotIn("Available operations: replace (surgical text edits), replace_section", plan)
        self.assertNotIn("Available operations: replace (surgical text edits), replace_between", plan)

    def test_expose_revision_ops_note_has_replace_section(self):
        plan = self._get_step_plan("expose", 1)
        self.assertIn("replace_section", plan)

    def test_first_draft_revision_ops_note_has_replace_between(self):
        plan = self._get_step_plan("first_draft", 1)
        self.assertIn("replace_between", plan)

    def test_revision_locale_passed(self):
        plan = self._get_step_plan("pitch", 2)
        self.assertIn("de", plan)


# ── #30: Format detection sets entry_stage and validates ───────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestFormatDetection(TestCase):
    """Format detection on first invocation sets entry_stage, format_type, terminal."""

    def _run_detection(self, tool_result):
        from agents.blueprints.writers_room.leader.agent import _run_format_detection

        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(dept_id, {})
        agent.department.project.goal = "Test project"
        agent.department.project.sources.all.return_value = []

        with patch("agents.ai.claude_client.call_claude_with_tools") as mock_call:
            mock_call.return_value = ("", tool_result, {"model": "test", "input_tokens": 0, "output_tokens": 0})
            result = _run_format_detection(agent, sprint)

        return result, sprint._states[dept_id]

    def test_standalone_movie(self):
        result, state = self._run_detection(
            {
                "format_type": "standalone",
                "terminal_stage": "treatment",
                "entry_stage": "pitch",
                "reasoning": "Movie project",
            }
        )
        self.assertEqual(result["format_type"], "standalone")
        self.assertEqual(result["terminal_stage"], "treatment")
        self.assertEqual(result["entry_stage"], "pitch")
        self.assertTrue(state["entry_detected"])

    def test_series_format(self):
        result, state = self._run_detection(
            {
                "format_type": "series",
                "terminal_stage": "concept",
                "entry_stage": "pitch",
                "reasoning": "TV series",
            }
        )
        self.assertEqual(result["format_type"], "series")
        self.assertEqual(result["terminal_stage"], "concept")

    def test_invalid_terminal_stage_corrected(self):
        result, _ = self._run_detection(
            {
                "format_type": "standalone",
                "terminal_stage": "bogus_stage",
                "entry_stage": "pitch",
                "reasoning": "test",
            }
        )
        self.assertEqual(result["terminal_stage"], "treatment")

    def test_invalid_entry_stage_corrected(self):
        result, _ = self._run_detection(
            {
                "format_type": "standalone",
                "terminal_stage": "treatment",
                "entry_stage": "nonexistent",
                "reasoning": "test",
            }
        )
        self.assertEqual(result["entry_stage"], "pitch")

    def test_tool_call_failure_returns_defaults(self):
        result, _ = self._run_detection(None)
        self.assertEqual(result["format_type"], "standalone")
        self.assertEqual(result["terminal_stage"], "treatment")
        self.assertEqual(result["entry_stage"], "pitch")


# ── #31: Story bible updated after stage passes ────────────────────────────


@override_settings(ANTHROPIC_API_KEY="test-key")
class TestStoryBibleUpdate(TestCase):
    """_update_story_bible calls Claude and creates/updates Output."""

    def test_creates_story_bible_output(self):
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(dept_id, {"format_type": "standalone"})

        mock_deliverable = MagicMock()
        mock_deliverable.content = "# Pitch\nA story about Berlin."

        with patch("agents.blueprints.writers_room.leader.agent.Document") as MockDoc:
            MockDoc.objects.filter.return_value.order_by.return_value.first.side_effect = [
                mock_deliverable,  # stage_deliverable
                None,  # voice_profile
            ]
            with patch("projects.models.Output") as MockOutput:
                MockOutput.objects.filter.return_value.first.return_value = None  # no existing bible
                with patch("agents.ai.claude_client.call_claude_structured") as mock_claude:
                    mock_claude.return_value = (
                        {
                            "characters": [],
                            "timeline": [],
                            "canon_facts": [],
                            "world_rules": [],
                            "open_questions": [],
                            "changelog": [],
                        },
                        {"model": "test", "input_tokens": 0, "output_tokens": 0},
                    )
                    bp._update_story_bible(agent, sprint, "pitch")

                MockOutput.objects.update_or_create.assert_called_once()
                call_kwargs = MockOutput.objects.update_or_create.call_args
                self.assertEqual(call_kwargs[1]["label"], "story_bible")

    def test_skips_when_no_deliverable(self):
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(dept_id, {"format_type": "standalone"})

        with (
            patch("agents.blueprints.writers_room.leader.agent.Document") as MockDoc,
            patch("projects.models.Output"),
            patch("agents.ai.claude_client.call_claude_structured") as mock_claude,
        ):
            MockDoc.objects.filter.return_value.order_by.return_value.first.return_value = None
            bp._update_story_bible(agent, sprint, "pitch")
            # Should not call Claude if no deliverable
            mock_claude.assert_not_called()

    def test_includes_previous_bible(self):
        bp = WritersRoomLeaderBlueprint()
        dept_id = _uuid()
        agent = _make_agent(dept_id)
        sprint = _make_sprint(dept_id, {"format_type": "standalone"})

        mock_deliverable = MagicMock()
        mock_deliverable.content = "# Expose\nMore story."

        mock_existing_bible = MagicMock()
        mock_existing_bible.content = "Previous bible content"

        with patch("agents.blueprints.writers_room.leader.agent.Document") as MockDoc:
            MockDoc.objects.filter.return_value.order_by.return_value.first.side_effect = [
                mock_deliverable,  # stage_deliverable
                None,  # voice_profile
            ]
            with patch("projects.models.Output") as MockOutput:
                MockOutput.objects.filter.return_value.first.return_value = mock_existing_bible
                with patch("agents.ai.claude_client.call_claude_structured") as mock_claude:
                    mock_claude.return_value = (
                        {
                            "characters": [],
                            "timeline": [],
                            "canon_facts": [],
                            "world_rules": [],
                            "open_questions": [],
                            "changelog": [],
                        },
                        {"model": "test", "input_tokens": 0, "output_tokens": 0},
                    )
                    bp._update_story_bible(agent, sprint, "expose")

                # Verify the user message included the previous bible
                call_args = mock_claude.call_args
                user_msg = call_args[1]["user_message"]
                self.assertIn("Previous Story Bible", user_msg)
                self.assertIn("Previous bible content", user_msg)

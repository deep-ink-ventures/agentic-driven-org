"""Tests for Problem Solver department: GitHub service extensions, blueprints, pipeline."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from django.test import SimpleTestCase

from agents.blueprints import DEPARTMENTS, get_blueprint, get_department
from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.problem_solver.leader import ProblemSolverLeaderBlueprint
from agents.blueprints.problem_solver.workforce.out_of_box_thinker import OutOfBoxThinkerBlueprint
from agents.blueprints.problem_solver.workforce.playground import PlaygroundBlueprint
from agents.blueprints.problem_solver.workforce.reviewer import ReviewerBlueprint
from agents.blueprints.problem_solver.workforce.synthesizer import SynthesizerBlueprint
from agents.models import Agent, AgentTask
from integrations.github_dev.service import create_or_update_file, list_workflow_runs
from projects.models import Department, Project, Sprint


class TestGitHubServiceExtensions(SimpleTestCase):
    """Tests for the problem-solver GitHub service functions."""

    @patch("integrations.github_dev.service.requests.get")
    def test_list_workflow_runs_returns_recent_runs(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "workflow_runs": [
                {
                    "id": 101,
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/owner/repo/actions/runs/101",
                    "created_at": "2026-04-11T10:00:00Z",
                    "extra_field": "ignored",
                },
                {
                    "id": 102,
                    "status": "in_progress",
                    "conclusion": None,
                    "html_url": "https://github.com/owner/repo/actions/runs/102",
                    "created_at": "2026-04-11T11:00:00Z",
                    "extra_field": "ignored",
                },
            ]
        }
        mock_get.return_value = mock_response

        result = list_workflow_runs("tok", "owner/repo", "ci.yml", per_page=2)

        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/actions/workflows/ci.yml/runs",
            headers={
                "Authorization": "Bearer tok",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"per_page": 2},
            timeout=30,
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 101)
        self.assertEqual(result[0]["status"], "completed")
        self.assertEqual(result[0]["conclusion"], "success")
        self.assertEqual(result[0]["url"], "https://github.com/owner/repo/actions/runs/101")
        self.assertEqual(result[0]["created_at"], "2026-04-11T10:00:00Z")
        # Ensure extra fields are not leaked
        self.assertNotIn("extra_field", result[0])

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_creates_new(self, mock_get, mock_put):
        # GET returns 404 — file does not exist yet
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 404
        mock_get.return_value = mock_get_resp

        # PUT creates the file
        mock_put_resp = MagicMock()
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {
            "content": {"sha": "abc123"},
        }
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "owner/repo", "path/to/file.txt", "hello", "add file")

        # Should have tried GET first
        mock_get.assert_called_once()

        # PUT should NOT include sha (new file)
        put_call = mock_put.call_args
        put_json = put_call.kwargs.get("json") or put_call[1].get("json")
        self.assertNotIn("sha", put_json)
        self.assertEqual(put_json["message"], "add file")
        self.assertEqual(put_json["content"], base64.b64encode(b"hello").decode())

        self.assertEqual(result, {"sha": "abc123"})

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_updates_existing(self, mock_get, mock_put):
        # GET returns existing file with sha
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sha": "existing_sha_999"}
        mock_get.return_value = mock_get_resp

        # PUT updates
        mock_put_resp = MagicMock()
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {
            "content": {"sha": "new_sha_000"},
        }
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "owner/repo", "README.md", "updated", "update readme")

        # PUT should include sha for update
        put_call = mock_put.call_args
        put_json = put_call.kwargs.get("json") or put_call[1].get("json")
        self.assertEqual(put_json["sha"], "existing_sha_999")
        self.assertEqual(put_json["message"], "update readme")
        self.assertEqual(put_json["content"], base64.b64encode(b"updated").decode())

        self.assertEqual(result, {"sha": "new_sha_000"})


# ---------------------------------------------------------------------------
# Blueprint unit tests (no DB needed)
# ---------------------------------------------------------------------------


class TestOutOfBoxThinkerBlueprint:
    def test_has_required_attributes(self):
        bp = OutOfBoxThinkerBlueprint()
        assert bp.name == "Out-of-Box Thinker"
        assert bp.slug == "out_of_box_thinker"
        assert bp.essential is True
        assert len(bp.skills) > 0

    def test_has_propose_fields_command(self):
        bp = OutOfBoxThinkerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "propose-fields" in cmd_names


class TestPlaygroundBlueprint:
    def test_has_required_attributes(self):
        bp = PlaygroundBlueprint()
        assert bp.name == "Playground"
        assert bp.slug == "playground"
        assert bp.essential is True

    def test_has_explore_field_command(self):
        bp = PlaygroundBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "explore-field" in cmd_names

    def test_system_prompt_requires_pseudocode(self):
        bp = PlaygroundBlueprint()
        assert "pseudocode" in bp.system_prompt.lower()


class TestSynthesizerBlueprint:
    def test_has_required_attributes(self):
        bp = SynthesizerBlueprint()
        assert bp.name == "Synthesizer"
        assert bp.slug == "synthesizer"
        assert bp.essential is True

    def test_has_both_commands(self):
        bp = SynthesizerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "build-poc" in cmd_names
        assert "fix-poc" in cmd_names

    def test_parse_playground_repo(self):
        bp = SynthesizerBlueprint()
        assert bp.parse_playground_repo("https://github.com/org/playground") == "org/playground"
        assert bp.parse_playground_repo("https://github.com/my-org/my-repo") == "my-org/my-repo"


class TestReviewerBlueprint:
    def test_has_required_attributes(self):
        bp = ReviewerBlueprint()
        assert bp.name == "Reviewer"
        assert bp.slug == "reviewer"
        assert bp.essential is True

    def test_review_dimensions(self):
        bp = ReviewerBlueprint()
        assert bp.review_dimensions[0] == "legitimacy"
        assert "dod_validation" in bp.review_dimensions
        assert "mathematical_rigor" in bp.review_dimensions
        assert "reproducibility" in bp.review_dimensions
        assert "insight_novelty" in bp.review_dimensions

    def test_has_review_solution_command(self):
        bp = ReviewerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "review-solution" in cmd_names

    def test_system_prompt_mentions_legitimacy(self):
        bp = ReviewerBlueprint()
        prompt = bp.system_prompt.lower()
        assert "legitimacy" in prompt or "brute force" in prompt


class TestProblemSolverLeaderBlueprint:
    def test_has_required_attributes(self):
        bp = ProblemSolverLeaderBlueprint()
        assert bp.name == "First Principle Thinker"
        assert bp.slug == "leader"

    def test_inherits_leader(self):
        bp = ProblemSolverLeaderBlueprint()
        assert isinstance(bp, LeaderBlueprint)

    def test_has_decompose_problem_command(self):
        bp = ProblemSolverLeaderBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "decompose-problem" in cmd_names

    def test_config_schema(self):
        bp = ProblemSolverLeaderBlueprint()
        assert "github_playground_repo" in bp.config_schema
        assert bp.config_schema["github_playground_repo"]["required"] is True
        assert "github_token" in bp.config_schema
        assert bp.config_schema["github_token"]["required"] is True

    def test_review_pairs(self):
        bp = ProblemSolverLeaderBlueprint()
        pairs = bp.get_review_pairs()
        assert len(pairs) == 1
        assert pairs[0]["creator"] == "synthesizer"
        assert pairs[0]["reviewer"] == "reviewer"
        assert pairs[0]["creator_fix_command"] == "fix-poc"
        assert pairs[0]["reviewer_command"] == "review-solution"
        assert "legitimacy" in pairs[0]["dimensions"]


# ---------------------------------------------------------------------------
# Registration test (no DB needed)
# ---------------------------------------------------------------------------


class TestProblemSolverRegistration:
    def test_department_registered(self):
        assert "problem_solver" in DEPARTMENTS

    def test_department_name(self):
        dept = get_department("problem_solver")
        assert dept["name"] == "Problem Solver"

    def test_leader_is_problem_solver_leader(self):
        bp = get_blueprint("leader", "problem_solver")
        assert isinstance(bp, ProblemSolverLeaderBlueprint)

    def test_workforce_contains_all_agents(self):
        dept = get_department("problem_solver")
        workforce_types = set(dept["workforce"].keys())
        assert workforce_types == {"out_of_box_thinker", "playground", "synthesizer", "reviewer"}


# ---------------------------------------------------------------------------
# Pipeline integration tests (need DB)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProblemSolverPipeline:
    @pytest.fixture
    def user(self, db):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(email="ps_test@example.com", password="pass")

    @pytest.fixture
    def project(self, user):
        return Project.objects.create(name="PS Test", goal="Test goal", owner=user)

    @pytest.fixture
    def ps_department(self, project):
        return Department.objects.create(department_type="problem_solver", project=project)

    @pytest.fixture
    def ps_sprint(self, ps_department, user):
        s = Sprint.objects.create(
            project=ps_department.project,
            text="Find an algorithm to predict stock price direction with >60% accuracy",
            created_by=user,
        )
        s.departments.add(ps_department)
        return s

    @pytest.fixture
    def ps_leader(self, ps_department):
        return Agent.objects.create(
            name="FPT Leader",
            agent_type="leader",
            department=ps_department,
            is_leader=True,
            status="active",
        )

    @pytest.fixture
    def ps_workforce(self, ps_department):
        agents = {}
        for agent_type in ("out_of_box_thinker", "playground", "synthesizer", "reviewer"):
            agents[agent_type] = Agent.objects.create(
                name=f"PS {agent_type}",
                agent_type=agent_type,
                department=ps_department,
                status="active",
            )
        return agents

    def test_first_proposal_is_decomposition(self, ps_leader, ps_workforce, ps_sprint):
        bp = ProblemSolverLeaderBlueprint()
        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is not None
        assert len(proposal["tasks"]) == 1
        assert proposal["tasks"][0]["command_name"] == "decompose-problem"

    def test_after_decomposition_proposes_fields(self, ps_leader, ps_workforce, ps_sprint):
        bp = ProblemSolverLeaderBlueprint()
        dept_id = str(ps_leader.department_id)
        ps_sprint.set_department_state(
            dept_id,
            {
                "status": "running",
                "round": 0,
                "decomposition": {
                    "actors": ["market", "traders"],
                    "dynamics": ["price movement"],
                    "definition_of_done": "Predict direction with >60% accuracy on held-out data",
                    "math_bias": "statistical modelling",
                },
            },
        )
        AgentTask.objects.create(
            agent=ps_leader,
            sprint=ps_sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Decompose problem",
            report='{"decomposition": {}}',
        )
        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is not None
        assert proposal["tasks"][0]["target_agent_type"] == "out_of_box_thinker"
        assert proposal["tasks"][0]["command_name"] == "propose-fields"

    def test_exhausted_after_max_rounds(self, ps_leader, ps_workforce, ps_sprint):
        bp = ProblemSolverLeaderBlueprint()
        dept_id = str(ps_leader.department_id)
        ps_sprint.set_department_state(
            dept_id,
            {
                "status": "running",
                "round": 10,
                "decomposition": {"definition_of_done": "test"},
            },
        )
        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is None
        ps_sprint.refresh_from_db()
        assert ps_sprint.status == Sprint.Status.DONE

    def test_no_running_sprints_returns_none(self, ps_leader, ps_workforce):
        bp = ProblemSolverLeaderBlueprint()
        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is None

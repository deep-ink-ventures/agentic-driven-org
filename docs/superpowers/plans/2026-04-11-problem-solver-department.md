# Problem Solver Department Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Problem Solver department — first-principles decomposition, cross-domain ideation, parallel hypothesis testing via GitHub Actions sandbox, and reviewed proof-of-concept synthesis.

**Architecture:** New department registered in the blueprint registry following the existing lazy-import pattern. Leader (First Principle Thinker) orchestrates a linear pipeline per round: Out-of-Box Thinker proposes 5 fields, 5 Playground agents explore in parallel, Synthesizer builds PoCs for high-scoring hypotheses (8+) using GitHub Actions as sandbox, Reviewer gates quality. Up to 10 rounds with standard 9.0/9.5 quality gate.

**Tech Stack:** Django, Python 3.13, existing blueprint framework (LeaderBlueprint / WorkforceBlueprint), existing `integrations.github_dev.service` for GitHub API, Celery task system.

**Spec:** `docs/superpowers/specs/2026-04-11-problem-solver-department-design.md`

---

## File Structure

```
backend/integrations/github_dev/service.py                          — MODIFY: add create_or_update_file, list_workflow_runs
backend/agents/blueprints/problem_solver/__init__.py                — CREATE: empty
backend/agents/blueprints/problem_solver/leader/__init__.py         — CREATE: re-export
backend/agents/blueprints/problem_solver/leader/agent.py            — CREATE: ProblemSolverLeaderBlueprint
backend/agents/blueprints/problem_solver/leader/commands/__init__.py — CREATE: command registry
backend/agents/blueprints/problem_solver/leader/commands/decompose_problem.py — CREATE
backend/agents/blueprints/problem_solver/workforce/__init__.py      — CREATE: empty
backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/__init__.py — CREATE: re-export
backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/agent.py   — CREATE
backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/__init__.py — CREATE
backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/propose_fields.py — CREATE
backend/agents/blueprints/problem_solver/workforce/playground/__init__.py       — CREATE: re-export
backend/agents/blueprints/problem_solver/workforce/playground/agent.py          — CREATE
backend/agents/blueprints/problem_solver/workforce/playground/commands/__init__.py — CREATE
backend/agents/blueprints/problem_solver/workforce/playground/commands/explore_field.py — CREATE
backend/agents/blueprints/problem_solver/workforce/synthesizer/__init__.py      — CREATE: re-export
backend/agents/blueprints/problem_solver/workforce/synthesizer/agent.py         — CREATE
backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/__init__.py — CREATE
backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/build_poc.py — CREATE
backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/fix_poc.py   — CREATE
backend/agents/blueprints/problem_solver/workforce/reviewer/__init__.py         — CREATE: re-export
backend/agents/blueprints/problem_solver/workforce/reviewer/agent.py            — CREATE
backend/agents/blueprints/problem_solver/workforce/reviewer/commands/__init__.py — CREATE
backend/agents/blueprints/problem_solver/workforce/reviewer/commands/review_solution.py — CREATE
backend/agents/blueprints/__init__.py                               — MODIFY: register department
backend/agents/tests/test_problem_solver.py                         — CREATE: tests
```

---

### Task 1: Extend GitHub integration service

**Files:**
- Modify: `backend/integrations/github_dev/service.py:59-73`
- Test: `backend/agents/tests/test_problem_solver.py`

The Synthesizer needs to push code files and find workflow runs triggered by dispatch. Two new functions in the existing service.

- [ ] **Step 1: Write failing tests for the new GitHub service functions**

Create `backend/agents/tests/test_problem_solver.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

from integrations.github_dev.service import create_or_update_file, list_workflow_runs


class TestGitHubServiceExtensions:
    @patch("integrations.github_dev.service.requests.get")
    def test_list_workflow_runs_returns_recent_runs(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "workflow_runs": [
                {"id": 123, "status": "completed", "conclusion": "success", "html_url": "https://github.com/org/repo/actions/runs/123", "created_at": "2026-04-11T10:00:00Z"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = list_workflow_runs("tok", "org/repo", "poc.yml")
        assert len(result) == 1
        assert result[0]["id"] == 123
        assert result[0]["status"] == "completed"
        assert result[0]["conclusion"] == "success"
        mock_get.assert_called_once()

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_creates_new(self, mock_get, mock_put):
        # GET returns 404 (file does not exist)
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 404
        mock_get.return_value = mock_get_resp

        # PUT creates file
        mock_put_resp = MagicMock()
        mock_put_resp.status_code = 201
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {"content": {"sha": "abc123"}}
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "org/repo", "src/main.py", "print('hello')", "add main.py")
        assert result["sha"] == "abc123"
        mock_put.assert_called_once()

    @patch("integrations.github_dev.service.requests.put")
    @patch("integrations.github_dev.service.requests.get")
    def test_create_or_update_file_updates_existing(self, mock_get, mock_put):
        # GET returns existing file with sha
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sha": "old_sha"}
        mock_get.return_value = mock_get_resp

        # PUT updates file
        mock_put_resp = MagicMock()
        mock_put_resp.status_code = 200
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {"content": {"sha": "new_sha"}}
        mock_put.return_value = mock_put_resp

        result = create_or_update_file("tok", "org/repo", "src/main.py", "print('updated')", "update main.py")
        assert result["sha"] == "new_sha"
        # Verify sha was sent in the PUT body
        put_data = mock_put.call_args[1]["json"]
        assert put_data["sha"] == "old_sha"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestGitHubServiceExtensions -v`
Expected: FAIL with ImportError (functions don't exist yet)

- [ ] **Step 3: Implement create_or_update_file and list_workflow_runs**

Add to `backend/integrations/github_dev/service.py` after the `get_workflow_logs` function (after line 72):

```python
def list_workflow_runs(token: str, repo: str, workflow_file: str, per_page: int = 5) -> list[dict]:
    """List recent workflow runs for a specific workflow file."""
    resp = requests.get(
        f"{BASE_URL}/repos/{repo}/actions/workflows/{workflow_file}/runs",
        headers=_headers(token),
        params={"per_page": per_page},
    )
    resp.raise_for_status()
    return [
        {
            "id": r["id"],
            "status": r["status"],
            "conclusion": r.get("conclusion"),
            "url": r["html_url"],
            "created_at": r["created_at"],
        }
        for r in resp.json().get("workflow_runs", [])
    ]


def create_or_update_file(token: str, repo: str, path: str, content: str, message: str) -> dict:
    """Create or update a file in a repo. Handles the sha lookup for updates."""
    import base64

    # Check if file exists to get its sha
    get_resp = requests.get(f"{BASE_URL}/repos/{repo}/contents/{path}", headers=_headers(token))
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json()["sha"]

    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(f"{BASE_URL}/repos/{repo}/contents/{path}", headers=_headers(token), json=data)
    resp.raise_for_status()
    return {"sha": resp.json()["content"]["sha"]}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestGitHubServiceExtensions -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/integrations/github_dev/service.py backend/agents/tests/test_problem_solver.py
git commit -m "feat: add create_or_update_file and list_workflow_runs to GitHub service"
```

---

### Task 2: Create directory structure and __init__.py files

**Files:**
- Create: All `__init__.py` files in the problem_solver blueprint tree

- [ ] **Step 1: Create the directory structure and all __init__.py files**

```bash
# Create directories
mkdir -p backend/agents/blueprints/problem_solver/leader/commands
mkdir -p backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands
mkdir -p backend/agents/blueprints/problem_solver/workforce/playground/commands
mkdir -p backend/agents/blueprints/problem_solver/workforce/synthesizer/commands
mkdir -p backend/agents/blueprints/problem_solver/workforce/reviewer/commands
```

Create `backend/agents/blueprints/problem_solver/__init__.py`:
```python
```

Create `backend/agents/blueprints/problem_solver/workforce/__init__.py`:
```python
```

Create `backend/agents/blueprints/problem_solver/leader/__init__.py`:
```python
from .agent import ProblemSolverLeaderBlueprint

__all__ = ["ProblemSolverLeaderBlueprint"]
```

Create `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/__init__.py`:
```python
from .agent import OutOfBoxThinkerBlueprint

__all__ = ["OutOfBoxThinkerBlueprint"]
```

Create `backend/agents/blueprints/problem_solver/workforce/playground/__init__.py`:
```python
from .agent import PlaygroundBlueprint

__all__ = ["PlaygroundBlueprint"]
```

Create `backend/agents/blueprints/problem_solver/workforce/synthesizer/__init__.py`:
```python
from .agent import SynthesizerBlueprint

__all__ = ["SynthesizerBlueprint"]
```

Create `backend/agents/blueprints/problem_solver/workforce/reviewer/__init__.py`:
```python
from .agent import ReviewerBlueprint

__all__ = ["ReviewerBlueprint"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/problem_solver/
git commit -m "feat: scaffold problem_solver department directory structure"
```

---

### Task 3: Out-of-Box Thinker (workforce agent)

**Files:**
- Create: `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/agent.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/__init__.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/propose_fields.py`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints.problem_solver.workforce.out_of_box_thinker import OutOfBoxThinkerBlueprint


class TestOutOfBoxThinkerBlueprint:
    def test_has_required_attributes(self):
        bp = OutOfBoxThinkerBlueprint()
        assert bp.name == "Out-of-Box Thinker"
        assert bp.slug == "out_of_box_thinker"
        assert len(bp.skills) > 0

    def test_has_propose_fields_command(self):
        bp = OutOfBoxThinkerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "propose-fields" in cmd_names

    def test_system_prompt_contains_bisociation(self):
        bp = OutOfBoxThinkerBlueprint()
        assert "bisociation" in bp.system_prompt.lower() or "cross-domain" in bp.system_prompt.lower()

    def test_essential_is_true(self):
        bp = OutOfBoxThinkerBlueprint()
        assert bp.essential is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestOutOfBoxThinkerBlueprint -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the command**

Create `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/propose_fields.py`:

```python
"""Out-of-Box Thinker command: propose cross-domain fields for problem solving."""

from agents.blueprints.base import command


@command(
    name="propose-fields",
    description=(
        "Propose 5 cross-domain fields via bisociation: 2 same-domain, "
        "2 associated-domain, 1 random-associative. Must not repeat fields from prior rounds."
    ),
    model="claude-opus-4-6",
)
def propose_fields(self, agent) -> dict:
    return {
        "exec_summary": "Propose 5 cross-domain fields for hypothesis exploration",
        "step_plan": (
            "1. Review the problem decomposition and definition of done\n"
            "2. Review prior round history — which fields were tried and their scores\n"
            "3. Propose 2 same-domain fields (e.g. two math subfields)\n"
            "4. Propose 2 associated-domain fields (related but distinct disciplines)\n"
            "5. Propose 1 random-associative field (unexpected domain with structural similarity)\n"
            "6. For each field, explain the structural analogy to the problem"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/commands/__init__.py`:

```python
"""Out-of-Box Thinker commands registry."""

from .propose_fields import propose_fields

ALL_COMMANDS = [propose_fields]
```

- [ ] **Step 4: Create the blueprint**

Create `backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.out_of_box_thinker.commands import propose_fields

logger = logging.getLogger(__name__)


class OutOfBoxThinkerBlueprint(WorkforceBlueprint):
    name = "Out-of-Box Thinker"
    slug = "out_of_box_thinker"
    description = (
        "Cross-domain innovator — proposes 5 fields via bisociation, lateral thinking, "
        "and analogical reasoning for hypothesis exploration"
    )
    tags = ["ideation", "cross-domain", "lateral-thinking", "bisociation"]
    essential = True
    skills = [
        {
            "name": "Bisociation",
            "description": "Combine two habitually incompatible frames of reference to produce novel insight (Koestler)",
        },
        {
            "name": "Lateral Thinking",
            "description": "Apply de Bono's provocation, random entry, and challenge techniques to escape conventional thinking",
        },
        {
            "name": "Analogical Reasoning",
            "description": "Map structural patterns from distant fields onto the problem — biomimicry, cross-disciplinary transfer",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a cross-domain innovation specialist. Your job is to propose fields from which breakthrough insights might emerge for the given problem.

Your methodology combines:
- **Bisociation** (Arthur Koestler): creative breakthroughs happen when two previously unconnected "matrices of thought" collide. Gutenberg combined the wine press + coin punch. Watson/Crick combined X-ray crystallography + model building.
- **Lateral thinking** (Edward de Bono): provocation (make deliberately absurd statements, extract useful ideas), random entry (inject unrelated stimulus, force connections), challenge (ask "why do we do it this way?" about unquestioned assumptions).
- **Analogical reasoning**: map structural patterns from distant fields. Velcro from burrs. Bullet train nose from kingfisher beak. Fourier transforms from music theory to data compression.

You MUST propose exactly 5 fields, categorized:
- **2 same-domain fields**: subfields within the problem's primary domain (e.g. if the problem involves optimization, propose two specific mathematical subfields like topology and convex analysis)
- **2 associated-domain fields**: related but distinct disciplines that share structural patterns with the problem (e.g. chemistry + biology for a physics problem)
- **1 random-associative field**: an unexpected, seemingly unrelated domain that has some structural or mechanical similarity to the problem (like wine presses for printing — connected by the concept of pressure)

For EACH field, explain:
1. The field's core principle that is relevant
2. The structural analogy to the problem
3. Why this connection might yield insight

## Output Format

Respond with JSON:
{
    "fields": [
        {
            "name": "Field name",
            "category": "same_domain|associated_domain|random_associative",
            "core_principle": "The relevant principle from this field",
            "structural_analogy": "How this maps onto the problem",
            "insight_potential": "Why this might yield a breakthrough"
        }
    ],
    "provocation": "One deliberately absurd inversion of the problem and what useful idea it surfaces",
    "report": "Summary of the ideation process and why these 5 fields were chosen"
}

## Anti-Patterns
- Do NOT repeat fields from prior rounds (check round_history)
- Do NOT propose fields that are too obvious or directly related (that's not cross-domain thinking)
- Do NOT propose fields you cannot articulate a structural analogy for
- The random-associative field should genuinely surprise — if it doesn't feel unexpected, it's not random enough"""

    propose_fields = propose_fields

    def get_task_suffix(self, agent, task):
        return """# CROSS-DOMAIN IDEATION METHODOLOGY

## Provocation Step (Mandatory)
Before proposing fields, generate one deliberately absurd inversion of the problem.
Example: "What if gravity pushed instead of pulled?" → leads to thinking about repulsive forces, which connects to electrostatics.
Mine this provocation for at least one real field proposal.

## Field Selection Criteria
- Same-domain: must be specific subfields, not the parent field itself
- Associated-domain: must share a structural pattern (not just topical overlap)
- Random-associative: must connect through an abstract mechanical or structural property

## Quality Check
For each field, ask: "Can I describe a specific concept from this field that maps onto a specific aspect of the problem?" If not, the field is too vague."""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestOutOfBoxThinkerBlueprint -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/problem_solver/workforce/out_of_box_thinker/ backend/agents/tests/test_problem_solver.py
git commit -m "feat: Out-of-Box Thinker agent — cross-domain field ideation via bisociation"
```

---

### Task 4: Playground agent (workforce)

**Files:**
- Create: `backend/agents/blueprints/problem_solver/workforce/playground/agent.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/playground/commands/__init__.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/playground/commands/explore_field.py`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints.problem_solver.workforce.playground import PlaygroundBlueprint


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

    def test_system_prompt_requires_score(self):
        bp = PlaygroundBlueprint()
        assert "1-10" in bp.system_prompt or "score" in bp.system_prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestPlaygroundBlueprint -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the command**

Create `backend/agents/blueprints/problem_solver/workforce/playground/commands/explore_field.py`:

```python
"""Playground command: explore a single field for problem-solving insight."""

from agents.blueprints.base import command


@command(
    name="explore-field",
    description=(
        "Explore one assigned field — find applications that could generate insight "
        "for the problem. Produce a hypothesis + pseudocode sketch. Score 1-10."
    ),
    model="claude-opus-4-6",
)
def explore_field(self, agent) -> dict:
    return {
        "exec_summary": "Explore assigned field for problem-solving hypotheses",
        "step_plan": (
            "1. Study the assigned field's core principles\n"
            "2. Map structural similarities to the problem\n"
            "3. Formulate a clear hypothesis\n"
            "4. Write a pseudocode sketch of the algorithmic approach\n"
            "5. Self-score on 1-10 scale with honest justification"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/workforce/playground/commands/__init__.py`:

```python
"""Playground commands registry."""

from .explore_field import explore_field

ALL_COMMANDS = [explore_field]
```

- [ ] **Step 4: Create the blueprint**

Create `backend/agents/blueprints/problem_solver/workforce/playground/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.playground.commands import explore_field

logger = logging.getLogger(__name__)


class PlaygroundBlueprint(WorkforceBlueprint):
    name = "Playground"
    slug = "playground"
    description = (
        "Hypothesis explorer — takes one assigned field and the problem decomposition, "
        "maps structural analogies, produces hypothesis + pseudocode sketch, scores 1-10"
    )
    tags = ["hypothesis", "exploration", "pseudocode", "scoring"]
    essential = True
    skills = [
        {
            "name": "Structural Mapping",
            "description": "Map principles from an assigned field onto the problem's core dynamics",
        },
        {
            "name": "Hypothesis Formulation",
            "description": "Articulate a clear, testable hypothesis connecting the field to the problem",
        },
        {
            "name": "Pseudocode Sketching",
            "description": "Translate a hypothesis into an algorithmic sketch that a Synthesizer can implement",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a hypothesis explorer. You receive ONE assigned field and a problem decomposition. Your job is to find applications from that field that could generate insight for the problem.

## Your Process
1. **Study the field**: What are its core principles, techniques, and solved problems?
2. **Map to the problem**: Where do structural similarities exist between this field's solutions and the problem's dynamics?
3. **Formulate hypothesis**: "If we apply [concept from field X] to [aspect of the problem], then [expected insight/result] because [structural reason]"
4. **Write pseudocode**: An algorithmic sketch showing how the approach would work. This must be concrete enough for a Synthesizer to turn into executable code.
5. **Score honestly**: Rate your hypothesis on a 1-10 scale.

## Scoring Calibration
- **1-2**: Dead end. The field has no meaningful structural connection to the problem.
- **3-4**: Superficial similarity exists but no actionable insight emerges.
- **5-6**: Interesting connection. The analogy holds structurally but the path to a solution is unclear.
- **7**: Strong hypothesis. Clear structural mapping with a plausible algorithmic approach.
- **8-9**: Exceptional. The field provides a principle that directly addresses a core aspect of the problem. The pseudocode is concrete and the path to validation is clear.
- **10**: One-in-a-generation insight. Like Wiles connecting modular forms to elliptic curves — a deep structural bridge that fundamentally reframes the problem.

Be brutally honest. Most hypotheses should score 3-6. An 8+ should genuinely excite you.

## Output Format

Respond with JSON:
{
    "field": "The assigned field name",
    "field_principles": "Key principles from this field relevant to the problem",
    "structural_mapping": "How these principles map onto the problem's dynamics",
    "hypothesis": "If we apply [X] to [Y], then [Z] because [reason]",
    "pseudocode": "```\\ndef approach(problem_inputs):\\n    # Step-by-step algorithmic sketch\\n    ...\\n```",
    "score": 7,
    "score_justification": "Why this score — what makes it strong or weak",
    "report": "Summary of exploration and findings"
}

## Anti-Patterns
- Do NOT inflate scores to seem productive. A score of 3 with honest reasoning is better than a score of 8 with hand-waving.
- Do NOT write vague pseudocode. "Apply machine learning" is not pseudocode. Show the actual algorithmic steps.
- Do NOT force connections that don't exist. If the field genuinely has no relevant structural analogy, say so and score 1-2."""

    explore_field = explore_field

    def get_task_suffix(self, agent, task):
        return """# HYPOTHESIS EXPLORATION METHODOLOGY

## Bias Toward Mathematical/Computational Solutions
The department has a heavy bias toward mathematical modelling, statistical pattern establishment, and computational approaches. When exploring your field:
- Look for mathematical structures, equations, or algorithms from the field
- Prefer quantitative approaches over qualitative ones
- The pseudocode should be implementable as actual code

## Pseudocode Quality Bar
Your pseudocode must be detailed enough that a programmer could implement it without needing to understand the source field. Include:
- Input/output types
- Core algorithm steps
- Key mathematical operations
- How to validate the result"""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestPlaygroundBlueprint -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/problem_solver/workforce/playground/ backend/agents/tests/test_problem_solver.py
git commit -m "feat: Playground agent — hypothesis exploration with pseudocode sketches"
```

---

### Task 5: Synthesizer agent (workforce)

**Files:**
- Create: `backend/agents/blueprints/problem_solver/workforce/synthesizer/agent.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/__init__.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/build_poc.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/fix_poc.py`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints.problem_solver.workforce.synthesizer import SynthesizerBlueprint


class TestSynthesizerBlueprint:
    def test_has_required_attributes(self):
        bp = SynthesizerBlueprint()
        assert bp.name == "Synthesizer"
        assert bp.slug == "synthesizer"
        assert bp.essential is True

    def test_has_build_poc_command(self):
        bp = SynthesizerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "build-poc" in cmd_names

    def test_has_fix_poc_command(self):
        bp = SynthesizerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "fix-poc" in cmd_names

    def test_system_prompt_mentions_github_actions(self):
        bp = SynthesizerBlueprint()
        prompt = bp.system_prompt.lower()
        assert "github" in prompt or "workflow" in prompt

    def test_parse_playground_repo_extracts_org_name(self):
        bp = SynthesizerBlueprint()
        assert bp.parse_playground_repo("https://github.com/org/playground") == "org/playground"
        assert bp.parse_playground_repo("https://github.com/my-org/my-repo") == "my-org/my-repo"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestSynthesizerBlueprint -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the commands**

Create `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/build_poc.py`:

```python
"""Synthesizer command: build and validate proof of concept."""

from agents.blueprints.base import command


@command(
    name="build-poc",
    description=(
        "Build a proof of concept from a high-scoring hypothesis. Push code to the "
        "playground repo, trigger GitHub Action, validate results against definition of done."
    ),
    model="claude-opus-4-6",
    max_tokens=16000,
)
def build_poc(self, agent) -> dict:
    return {
        "exec_summary": "Build and validate proof of concept against definition of done",
        "step_plan": (
            "1. Review the hypothesis and pseudocode sketch\n"
            "2. Translate pseudocode into executable code\n"
            "3. Push code to playground repo via GitHub API\n"
            "4. Trigger GitHub Action workflow\n"
            "5. Read back results and validate against definition of done\n"
            "6. Self-score 1-10 on how well the DoD is met"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/fix_poc.py`:

```python
"""Synthesizer command: revise proof of concept based on reviewer feedback."""

from agents.blueprints.base import command


@command(
    name="fix-poc",
    description=(
        "Revise the proof of concept based on reviewer feedback. "
        "Address specific issues, re-push, re-trigger, re-validate."
    ),
    model="claude-opus-4-6",
    max_tokens=16000,
)
def fix_poc(self, agent) -> dict:
    return {
        "exec_summary": "Revise proof of concept based on reviewer feedback",
        "step_plan": (
            "1. Review the reviewer's feedback and score breakdown\n"
            "2. Identify the weakest dimensions\n"
            "3. Revise the code to address feedback\n"
            "4. Re-push to playground repo\n"
            "5. Re-trigger GitHub Action and validate\n"
            "6. Self-score the revised PoC"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/workforce/synthesizer/commands/__init__.py`:

```python
"""Synthesizer commands registry."""

from .build_poc import build_poc
from .fix_poc import fix_poc

ALL_COMMANDS = [build_poc, fix_poc]
```

- [ ] **Step 4: Create the blueprint**

Create `backend/agents/blueprints/problem_solver/workforce/synthesizer/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.synthesizer.commands import build_poc, fix_poc

logger = logging.getLogger(__name__)


class SynthesizerBlueprint(WorkforceBlueprint):
    name = "Synthesizer"
    slug = "synthesizer"
    description = (
        "Builder — takes high-scoring hypotheses and turns them into working code. "
        "Pushes PoC to a playground repo, triggers GitHub Actions for validation, "
        "and compares results against the definition of done."
    )
    tags = ["synthesis", "implementation", "poc", "github-actions", "validation"]
    essential = True
    skills = [
        {
            "name": "Code Translation",
            "description": "Translate pseudocode sketches into executable, tested code",
        },
        {
            "name": "GitHub Actions Execution",
            "description": "Push code to playground repo and trigger workflow dispatch for sandboxed execution",
        },
        {
            "name": "DoD Validation",
            "description": "Parse execution results and validate against the definition of done criteria",
        },
    ]
    config_schema = {}

    @staticmethod
    def parse_playground_repo(url: str) -> str:
        """Extract org/name from a full GitHub URL."""
        parsed = urlparse(url)
        # path is like /org/repo or /org/repo/
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        raise ValueError(f"Cannot parse GitHub repo from URL: {url}")

    @property
    def system_prompt(self) -> str:
        return """You are a proof-of-concept builder. You receive a high-scoring hypothesis with a pseudocode sketch and turn it into working, executable code that validates against the definition of done.

## Your Process
1. **Understand the hypothesis**: Read the structural mapping and pseudocode carefully.
2. **Write executable code**: Translate the pseudocode into a complete, runnable script. Include all imports, data setup, and output formatting.
3. **Push to playground repo**: Use the GitHub API to create/update files in the playground repository.
4. **Trigger workflow**: Dispatch the poc.yml GitHub Action with appropriate inputs.
5. **Read results**: Parse the workflow run logs to extract validation results.
6. **Validate against DoD**: Compare results to the definition of done criteria.

## Code Quality Requirements
- The code must be self-contained — all dependencies must be installable via pip/npm
- Include a requirements.txt or package.json if external libraries are needed
- The main script must print structured output (JSON preferred) that can be parsed for DoD validation
- Include clear comments explaining the mathematical/algorithmic approach

## Iteration Rules
- You have up to 5 tries that make no progress, or 10 tries total
- Each try must genuinely change the approach, not just tweak parameters
- If you're stuck, report honestly rather than thrashing

## Self-Scoring Calibration
- **1-3**: PoC runs but results don't meet the DoD
- **4-6**: Partial progress — some DoD criteria met, others not
- **7-8**: Most DoD criteria met with minor gaps
- **9-10**: DoD fully met with clear, reproducible results

## Output Format

Respond with JSON:
{
    "files_pushed": [{"path": "src/main.py", "description": "Main PoC script"}],
    "workflow_triggered": true,
    "run_id": 12345,
    "results": "Structured output from the workflow run",
    "dod_validation": {
        "criteria_met": ["criterion 1", "criterion 2"],
        "criteria_failed": ["criterion 3"],
        "details": "Explanation of how results map to DoD"
    },
    "score": 7,
    "score_justification": "Why this score",
    "tries_used": 2,
    "report": "Summary of what was built, tested, and learned"
}"""

    build_poc = build_poc
    fix_poc = fix_poc

    def get_task_suffix(self, agent, task):
        repo_url = agent.get_config_value("github_playground_repo") or "NOT CONFIGURED"
        return f"""# SANDBOX EXECUTION

## Playground Repository
URL: {repo_url}

## GitHub API Functions Available
You can instruct the system to call these functions:
- create_or_update_file(token, repo, path, content, message) — push code files
- dispatch_workflow(token, repo, "poc.yml", inputs={{...}}) — trigger execution
- list_workflow_runs(token, repo, "poc.yml") — find your run
- get_workflow_run(token, repo, run_id) — check status
- get_workflow_logs(token, repo, run_id) — read output

## Legitimacy Requirements
Your PoC MUST demonstrate genuine insight, not shortcuts:
- No brute force / random search
- No hardcoded results
- No trivial lookups of known answers
- No overfitting to pass specific DoD checks without the approach actually working
The Reviewer will reject illegitimate approaches with a score of 0."""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestSynthesizerBlueprint -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/problem_solver/workforce/synthesizer/ backend/agents/tests/test_problem_solver.py
git commit -m "feat: Synthesizer agent — PoC builder with GitHub Actions sandbox"
```

---

### Task 6: Reviewer agent (workforce)

**Files:**
- Create: `backend/agents/blueprints/problem_solver/workforce/reviewer/agent.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/reviewer/commands/__init__.py`
- Create: `backend/agents/blueprints/problem_solver/workforce/reviewer/commands/review_solution.py`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints.problem_solver.workforce.reviewer import ReviewerBlueprint


class TestReviewerBlueprint:
    def test_has_required_attributes(self):
        bp = ReviewerBlueprint()
        assert bp.name == "Reviewer"
        assert bp.slug == "reviewer"
        assert bp.essential is True

    def test_has_review_dimensions(self):
        bp = ReviewerBlueprint()
        assert "legitimacy" in bp.review_dimensions
        assert "dod_validation" in bp.review_dimensions
        assert "mathematical_rigor" in bp.review_dimensions
        assert "reproducibility" in bp.review_dimensions
        assert "insight_novelty" in bp.review_dimensions

    def test_has_review_solution_command(self):
        bp = ReviewerBlueprint()
        cmd_names = {c["name"] for c in bp.get_commands()}
        assert "review-solution" in cmd_names

    def test_system_prompt_mentions_legitimacy_gate(self):
        bp = ReviewerBlueprint()
        prompt = bp.system_prompt.lower()
        assert "brute force" in prompt or "illegitimate" in prompt or "legitimacy" in prompt

    def test_legitimacy_is_first_dimension(self):
        bp = ReviewerBlueprint()
        assert bp.review_dimensions[0] == "legitimacy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestReviewerBlueprint -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the command**

Create `backend/agents/blueprints/problem_solver/workforce/reviewer/commands/review_solution.py`:

```python
"""Reviewer command: independently score Synthesizer output against the DoD."""

from agents.blueprints.base import command


@command(
    name="review-solution",
    description=(
        "Score a Synthesizer's proof of concept against the definition of done. "
        "Check legitimacy first, then score all dimensions. Submit verdict via tool call."
    ),
    model="claude-opus-4-6",
)
def review_solution(self, agent) -> dict:
    return {
        "exec_summary": "Review proof of concept against definition of done",
        "step_plan": (
            "1. Check legitimacy — is this genuine insight or a shortcut?\n"
            "2. Score dod_validation — does the PoC meet the definition of done?\n"
            "3. Score mathematical_rigor — is the approach mathematically sound?\n"
            "4. Score reproducibility — can results be independently reproduced?\n"
            "5. Score insight_novelty — how novel is the cross-domain insight?\n"
            "6. Overall score = minimum of all dimensions\n"
            "7. Submit verdict via submit_verdict tool"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/workforce/reviewer/commands/__init__.py`:

```python
"""Reviewer commands registry."""

from .review_solution import review_solution

ALL_COMMANDS = [review_solution]
```

- [ ] **Step 4: Create the blueprint**

Create `backend/agents/blueprints/problem_solver/workforce/reviewer/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.problem_solver.workforce.reviewer.commands import review_solution

logger = logging.getLogger(__name__)


class ReviewerBlueprint(WorkforceBlueprint):
    name = "Reviewer"
    slug = "reviewer"
    description = (
        "Independent quality gate — scores Synthesizer output against the definition of done "
        "without anchoring on the Synthesizer's self-score. Enforces legitimacy gate."
    )
    tags = ["review", "quality-gate", "validation", "scoring"]
    essential = True
    review_dimensions = [
        "legitimacy",
        "dod_validation",
        "mathematical_rigor",
        "reproducibility",
        "insight_novelty",
    ]
    skills = [
        {
            "name": "Legitimacy Detection",
            "description": "Identify brute force, hardcoded results, trivial lookups, and overfitted solutions",
        },
        {
            "name": "DoD Validation",
            "description": "Rigorously compare PoC results against the definition of done criteria",
        },
        {
            "name": "Mathematical Review",
            "description": "Verify mathematical soundness of the approach — correct formulas, valid assumptions, proper statistical methods",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are an independent solution reviewer. Your job is to score a Synthesizer's proof of concept against the definition of done. You must NOT anchor on the Synthesizer's self-score — form your own independent assessment.

## Legitimacy Gate (MUST CHECK FIRST)

Before scoring anything else, determine if the solution is legitimate. Score legitimacy 0 if ANY of these apply:
- **Brute force / random search**: randomly trying combinations until one works is not a solution
- **Hardcoded results**: embedding the expected answer and "discovering" it is fraud
- **Trivial lookup**: if the answer is publicly known and the PoC just retrieves it, no insight was generated
- **Overfitting to DoD**: engineering the PoC to pass specific checks without the approach actually working in general

A legitimate solution must demonstrate a **causal chain of insight**: the cross-domain field provided a structural analogy or principle that, when applied to the problem, produces the result for an identifiable reason. You must be able to articulate *why* the approach works, not just *that* it passes.

If legitimacy = 0, the overall score is 0 regardless of other dimensions. Set verdict to CHANGES_REQUESTED with feedback explaining why the approach is illegitimate.

## Scoring Dimensions (1.0-10.0, use decimals)

1. **legitimacy**: Is this a genuine insight? (0 = instant reject, 10 = undeniably original)
2. **dod_validation**: Does the PoC actually meet the definition of done criteria?
3. **mathematical_rigor**: Is the mathematical/algorithmic approach sound? Correct formulas, valid assumptions, proper statistical methods?
4. **reproducibility**: Can the result be reproduced independently? Clear code, documented steps, deterministic output?
5. **insight_novelty**: How novel is the cross-domain insight? How surprising and deep is the connection?

**Overall score = MINIMUM of all dimension scores.**

The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold.

After your review, call the submit_verdict tool with your verdict and score.
For CHANGES_REQUESTED, list the specific issues preventing excellence with actionable fix suggestions.

## Scoring Calibration
- Below 3.0: Fundamental problems — approach doesn't work or is illegitimate
- 3.0-5.9: Significant issues — partially works but major gaps
- 6.0-7.9: Decent but not excellent — clear path to improvement
- 8.0-8.9: Strong — minor issues to polish
- 9.0-9.4: Near-excellent — very close to the bar
- 9.5-10.0: Excellent — meets the quality threshold"""

    review_solution = review_solution

    def get_task_suffix(self, agent, task):
        return f"""# REVIEW METHODOLOGY

## Step 1: Legitimacy Check
Read the Synthesizer's report. Can you identify:
- What cross-domain field was used?
- What specific principle from that field was applied?
- WHY does this principle produce the observed result?
If you cannot answer all three, the approach is likely illegitimate.

## Step 2: Dimension Scoring
Score each dimension independently. Write the worst problem you found BEFORE assigning the score. Do not let a strong dimension compensate for a weak one — the overall score is the MINIMUM.

## Step 3: Verdict
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with specific, actionable feedback

After your review, call the submit_verdict tool with your verdict and score."""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestReviewerBlueprint -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/problem_solver/workforce/reviewer/ backend/agents/tests/test_problem_solver.py
git commit -m "feat: Reviewer agent — independent quality gate with legitimacy enforcement"
```

---

### Task 7: Leader agent (First Principle Thinker)

**Files:**
- Create: `backend/agents/blueprints/problem_solver/leader/agent.py`
- Create: `backend/agents/blueprints/problem_solver/leader/commands/__init__.py`
- Create: `backend/agents/blueprints/problem_solver/leader/commands/decompose_problem.py`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints.problem_solver.leader import ProblemSolverLeaderBlueprint
from agents.blueprints.base import LeaderBlueprint


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

    def test_config_schema_has_playground_repo(self):
        bp = ProblemSolverLeaderBlueprint()
        assert "github_playground_repo" in bp.config_schema
        assert bp.config_schema["github_playground_repo"]["required"] is True

    def test_config_schema_has_github_token(self):
        bp = ProblemSolverLeaderBlueprint()
        assert "github_token" in bp.config_schema
        assert bp.config_schema["github_token"]["required"] is True

    def test_review_pairs_defines_synthesizer_reviewer(self):
        bp = ProblemSolverLeaderBlueprint()
        pairs = bp.get_review_pairs()
        assert len(pairs) == 1
        assert pairs[0]["creator"] == "synthesizer"
        assert pairs[0]["reviewer"] == "reviewer"
        assert pairs[0]["creator_fix_command"] == "fix-poc"
        assert pairs[0]["reviewer_command"] == "review-solution"
        assert "legitimacy" in pairs[0]["dimensions"]

    def test_system_prompt_mentions_first_principles(self):
        bp = ProblemSolverLeaderBlueprint()
        prompt = bp.system_prompt.lower()
        assert "first" in prompt and "principle" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestProblemSolverLeaderBlueprint -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Create the command**

Create `backend/agents/blueprints/problem_solver/leader/commands/decompose_problem.py`:

```python
"""Problem Solver leader command: decompose problem into first principles."""

from agents.blueprints.base import command


@command(
    name="decompose-problem",
    description=(
        "Break a problem into its fundamental building blocks using first-principles thinking. "
        "Identify actors, dynamics, and variants. Define a falsifiable definition of done. "
        "Reject problems that cannot have a clear DoD."
    ),
    model="claude-opus-4-6",
    max_tokens=8000,
)
def decompose_problem(self, agent) -> dict:
    return {
        "exec_summary": "Decompose problem into first principles and define definition of done",
        "step_plan": (
            "1. List all assumptions about the problem explicitly\n"
            "2. Challenge each: physical law, mathematical truth, convention, or unknown?\n"
            "3. Discard conventions, keep only laws and verified data\n"
            "4. Identify core actors, dynamics, and variants\n"
            "5. Define a falsifiable, measurable definition of done\n"
            "6. If no clear DoD is possible, reject the problem as invalid"
        ),
    }
```

Create `backend/agents/blueprints/problem_solver/leader/commands/__init__.py`:

```python
"""Problem Solver leader commands registry."""

from .decompose_problem import decompose_problem

ALL_COMMANDS = [decompose_problem]
```

- [ ] **Step 4: Create the leader blueprint**

Create `backend/agents/blueprints/problem_solver/leader/agent.py`:

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.problem_solver.leader.commands import decompose_problem

logger = logging.getLogger(__name__)

MAX_ROUNDS = 10
PLAYGROUND_SCORE_THRESHOLD = 8


class ProblemSolverLeaderBlueprint(LeaderBlueprint):
    name = "First Principle Thinker"
    slug = "leader"
    description = (
        "First-principles problem decomposer — breaks problems into fundamental truths, "
        "defines falsifiable definitions of done, orchestrates cross-domain ideation pipeline, "
        "rejects unsolvable problems"
    )
    tags = ["leadership", "first-principles", "decomposition", "orchestration"]
    skills = [
        {
            "name": "First-Principles Decomposition",
            "description": "Break any problem to its irreducible truths — physics, math, verified data, logical axioms — then reconstruct",
        },
        {
            "name": "Assumption Challenging",
            "description": "Classify every assumption as physical law, mathematical truth, convention, or unknown. Discard conventions.",
        },
        {
            "name": "Definition of Done",
            "description": "Define a falsifiable, measurable DoD — a backtest target, a mathematical proof, a concrete validation criterion",
        },
        {
            "name": "Problem Rejection",
            "description": "Reject problems that cannot have a clear DoD. This is a first-class outcome, not a failure.",
        },
    ]
    config_schema = {
        "github_playground_repo": {
            "type": "str",
            "required": True,
            "label": "Playground Repository",
            "description": "Full URL of the GitHub repo for PoC execution, e.g. https://github.com/org/playground",
        },
        "github_token": {
            "type": "str",
            "required": True,
            "label": "GitHub Token",
            "description": "PAT with repo + workflow permissions for the playground repo",
        },
    }

    def get_review_pairs(self):
        return [
            {
                "creator": "synthesizer",
                "creator_fix_command": "fix-poc",
                "reviewer": "reviewer",
                "reviewer_command": "review-solution",
                "dimensions": [
                    "legitimacy",
                    "dod_validation",
                    "mathematical_rigor",
                    "reproducibility",
                    "insight_novelty",
                ],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return f"""You are the First Principle Thinker — the leader of the Problem Solver department. You decompose problems into their fundamental building blocks using Aristotelian first-principles methodology.

## Your Core Method
1. **List all assumptions** about the problem explicitly
2. **Challenge each assumption**: Is this a physical law? A mathematical truth? A convention? An unknown?
3. **Discard conventions**: Keep only laws, mathematical truths, and verified data
4. **Reconstruct from fundamentals**: Build understanding using only irreducible truths
5. **Identify core elements**:
   - **Actors**: Who or what are the entities involved?
   - **Dynamics**: How do they interact, evolve, influence each other?
   - **Variants**: What are the variables, parameters, degrees of freedom?

## Definition of Done
You MUST define a clear, falsifiable, measurable definition of done. Examples:
- "A mathematical model that backtests with X% gains against the S&P 500 over 10 years"
- "An algorithm that factors a 256-bit semiprime in under 1 hour on commodity hardware"
- "A statistical model that predicts Y with R² > 0.85 on held-out data"

If the problem CANNOT have a clear DoD (e.g. "solve climate change"), you MUST reject it.

## Mathematical/Computational Bias
You have a heavy bias toward solving problems via:
- Mathematical modelling
- Statistical pattern establishment
- Software and automation
- Algorithmic approaches
Frame the DoD in these terms whenever possible.

## Pipeline Orchestration
After decomposition, you orchestrate a multi-round pipeline:
1. Out-of-Box Thinker proposes 5 cross-domain fields
2. 5 Playground agents explore in parallel (one per field)
3. Synthesizer builds PoC for hypotheses scoring {PLAYGROUND_SCORE_THRESHOLD}+
4. Reviewer gates quality
Maximum {MAX_ROUNDS} rounds. Each round feeds results back to improve the next.

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When a synthesizer task completes, the system automatically:
1. Routes the PoC to the reviewer for quality check
2. If score < 9.5/10 → fix task auto-created for synthesizer with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
4. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept
Do NOT manually create review tasks — the system handles the loop."""

    decompose_problem = decompose_problem

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Orchestrate the problem-solving pipeline round by round."""
        # Check for review cycle triggers first (synthesizer -> reviewer ping-pong)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result

        # Get sprint and department state
        from projects.models import Sprint

        department = agent.department
        running_sprints = list(
            Sprint.objects.filter(
                departments=department,
                status=Sprint.Status.RUNNING,
            ).order_by("updated_at")
        )
        if not running_sprints:
            return None

        sprint = running_sprints[0]
        dept_id = str(department.id)
        dept_state = sprint.get_department_state(dept_id)

        status = dept_state.get("status", "new")
        current_round = dept_state.get("round", 0)

        # Check termination
        if status in ("solved", "invalid_problem", "exhausted"):
            return None
        if current_round >= MAX_ROUNDS:
            dept_state["status"] = "exhausted"
            sprint.set_department_state(dept_id, dept_state)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = (
                f"Exhausted {MAX_ROUNDS} rounds without reaching quality threshold. "
                f"See solution_round_* outputs for best attempts."
            )
            sprint.completed_at = __import__("django").utils.timezone.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])
            return None

        # Determine pipeline stage from completed tasks
        from agents.models import AgentTask

        recent_tasks = list(
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .select_related("agent")[:20]
        )

        last_type = recent_tasks[0].agent.agent_type if recent_tasks else None

        # Stage 1: No decomposition yet → decompose
        if status == "new" or not dept_state.get("decomposition"):
            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": "Decompose problem into first principles",
                "tasks": [
                    {
                        "target_agent_type": "leader",
                        "command_name": "decompose-problem",
                        "exec_summary": f"First-principles decomposition of: {sprint.text[:100]}",
                        "step_plan": (
                            f"Problem statement: {sprint.text}\n\n"
                            "Apply first-principles methodology:\n"
                            "1. List all assumptions\n"
                            "2. Challenge each — law, truth, convention, or unknown?\n"
                            "3. Identify actors, dynamics, variants\n"
                            "4. Define a falsifiable, measurable definition of done\n"
                            "5. If no clear DoD possible, declare invalid_problem\n\n"
                            "Respond with JSON:\n"
                            '{"decomposition": {"actors": [...], "dynamics": [...], '
                            '"variants": [...], "assumptions_challenged": [...], '
                            '"definition_of_done": "...", "math_bias": "..."}, '
                            '"status": "running" or "invalid_problem", '
                            '"rejection_reason": "..." (if invalid), '
                            '"report": "..."}'
                        ),
                        "depends_on_previous": False,
                    }
                ],
            }

        # Stage 2: Decomposition done, need fields → dispatch Out-of-Box Thinker
        if last_type == "leader" or (
            dept_state.get("decomposition") and not self._has_pending_work(recent_tasks)
        ):
            current_round = dept_state.get("round", 0) + 1
            dept_state["round"] = current_round
            sprint.set_department_state(dept_id, dept_state)

            round_history = dept_state.get("round_history", [])
            history_text = json.dumps(round_history, indent=2) if round_history else "No prior rounds."

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: propose 5 cross-domain fields",
                "tasks": [
                    {
                        "target_agent_type": "out_of_box_thinker",
                        "command_name": "propose-fields",
                        "exec_summary": f"Round {current_round}: propose 5 cross-domain fields for exploration",
                        "step_plan": (
                            f"## Problem Decomposition\n"
                            f"{json.dumps(dept_state.get('decomposition', {}), indent=2)}\n\n"
                            f"## Definition of Done\n"
                            f"{dept_state.get('decomposition', {}).get('definition_of_done', 'Not defined')}\n\n"
                            f"## Prior Round History\n{history_text}\n\n"
                            "Propose 5 NEW fields (never repeat prior round fields):\n"
                            "- 2 same-domain\n- 2 associated-domain\n- 1 random-associative"
                        ),
                        "depends_on_previous": False,
                    }
                ],
            }

        # Stage 3: Fields proposed → dispatch 5 Playground agents in parallel
        if last_type == "out_of_box_thinker":
            last_report = recent_tasks[0].report or ""
            try:
                fields_data = json.loads(last_report)
                fields = fields_data.get("fields", [])
            except (json.JSONDecodeError, AttributeError):
                fields = []

            if not fields:
                logger.warning("PROBLEM_SOLVER no fields parsed from Out-of-Box Thinker report")
                return None

            decomposition = json.dumps(dept_state.get("decomposition", {}), indent=2)
            dod = dept_state.get("decomposition", {}).get("definition_of_done", "Not defined")

            tasks = []
            for i, field in enumerate(fields[:5]):
                field_name = field.get("name", f"Field {i + 1}")
                tasks.append(
                    {
                        "target_agent_type": "playground",
                        "command_name": "explore-field",
                        "exec_summary": f"Explore field: {field_name}",
                        "step_plan": (
                            f"## Assigned Field\n{json.dumps(field, indent=2)}\n\n"
                            f"## Problem Decomposition\n{decomposition}\n\n"
                            f"## Definition of Done\n{dod}\n\n"
                            "Explore this field for structural analogies to the problem.\n"
                            "Produce a hypothesis + pseudocode sketch.\n"
                            "Score honestly on 1-10 scale."
                        ),
                        "depends_on_previous": False,
                    }
                )

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: explore 5 fields in parallel",
                "tasks": tasks,
            }

        # Stage 4: Playground agents done → filter for 8+ scores → dispatch Synthesizer
        playground_tasks = [t for t in recent_tasks if t.agent.agent_type == "playground"]
        if playground_tasks and last_type == "playground":
            high_scorers = []
            for pt in playground_tasks:
                try:
                    report = json.loads(pt.report or "{}")
                    score = report.get("score", 0)
                    if score >= PLAYGROUND_SCORE_THRESHOLD:
                        high_scorers.append((pt, report, score))
                except (json.JSONDecodeError, AttributeError):
                    pass

            if not high_scorers:
                # No hypotheses scored 8+ — record round and loop
                round_entry = {
                    "round": current_round,
                    "fields_proposed": [
                        json.loads(pt.report or "{}").get("field", "unknown") for pt in playground_tasks
                    ],
                    "playground_scores": {
                        json.loads(pt.report or "{}").get("field", "unknown"): json.loads(pt.report or "{}").get(
                            "score", 0
                        )
                        for pt in playground_tasks
                    },
                    "synthesizer_invoked_for": [],
                    "feedback": "No hypotheses scored 8+. All fields were dead ends this round.",
                }
                history = dept_state.get("round_history", [])
                history.append(round_entry)
                dept_state["round_history"] = history
                sprint.set_department_state(dept_id, dept_state)

                logger.info(
                    "PROBLEM_SOLVER round=%d no_high_scorers — looping to new fields",
                    current_round,
                )
                # Recurse to propose new fields
                return self.generate_task_proposal(agent)

            # Dispatch Synthesizer for each high-scoring hypothesis
            dod = dept_state.get("decomposition", {}).get("definition_of_done", "Not defined")
            tasks = []
            for pt, report, score in high_scorers:
                tasks.append(
                    {
                        "target_agent_type": "synthesizer",
                        "command_name": "build-poc",
                        "exec_summary": f"Build PoC for: {report.get('field', 'unknown')} (score {score})",
                        "step_plan": (
                            f"## Hypothesis (scored {score}/10)\n"
                            f"Field: {report.get('field', 'unknown')}\n"
                            f"Hypothesis: {report.get('hypothesis', 'N/A')}\n\n"
                            f"## Pseudocode\n{report.get('pseudocode', 'N/A')}\n\n"
                            f"## Structural Mapping\n{report.get('structural_mapping', 'N/A')}\n\n"
                            f"## Definition of Done\n{dod}\n\n"
                            "Build a working PoC, push to playground repo, "
                            "trigger GitHub Action, validate against DoD."
                        ),
                        "depends_on_previous": False,
                    }
                )

            return {
                "_sprint_id": str(sprint.id),
                "exec_summary": f"Round {current_round}: synthesize {len(tasks)} high-scoring hypotheses",
                "tasks": tasks,
            }

        # Stage 5: Reviewer accepted → write Output, mark solved
        if last_type == "reviewer":
            reviewer_tasks = [t for t in recent_tasks if t.agent.agent_type == "reviewer"]
            for rt in reviewer_tasks:
                if rt.review_verdict == "APPROVED" and rt.review_score and rt.review_score >= 9.0:
                    # Find the corresponding synthesizer task
                    synth_tasks = [t for t in recent_tasks if t.agent.agent_type == "synthesizer"]
                    best_report = synth_tasks[0].report if synth_tasks else "No synthesizer report."

                    from projects.models import Output

                    # Write round output
                    Output.objects.create(
                        sprint=sprint,
                        department=department,
                        title=f"Solution Round {current_round}",
                        label=f"solution_round_{current_round}",
                        output_type=Output.OutputType.MARKDOWN,
                        content=best_report,
                    )
                    # Write final solution output
                    Output.objects.create(
                        sprint=sprint,
                        department=department,
                        title=f"Solution — {sprint.text[:80]}",
                        label="solution",
                        output_type=Output.OutputType.MARKDOWN,
                        content=best_report,
                    )

                    dept_state["status"] = "solved"
                    sprint.set_department_state(dept_id, dept_state)
                    sprint.status = Sprint.Status.DONE
                    sprint.completion_summary = f"Solved in round {current_round} with score {rt.review_score}/10."
                    sprint.completed_at = __import__("django").utils.timezone.now()
                    sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])
                    return None

        # Default: fall back to base class proposal logic
        return super().generate_task_proposal(agent)

    def _has_pending_work(self, recent_tasks) -> bool:
        """Check if there are still pending/processing tasks this round."""
        from agents.models import AgentTask

        for t in recent_tasks:
            if t.status in (AgentTask.Status.QUEUED, AgentTask.Status.PROCESSING, AgentTask.Status.AWAITING_APPROVAL):
                return True
        return False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestProblemSolverLeaderBlueprint -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/problem_solver/leader/ backend/agents/tests/test_problem_solver.py
git commit -m "feat: First Principle Thinker leader — decomposition, DoD, pipeline orchestration"
```

---

### Task 8: Register department in blueprint registry

**Files:**
- Modify: `backend/agents/blueprints/__init__.py:193-203`
- Test: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write failing test**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
from agents.blueprints import DEPARTMENTS, get_blueprint, get_department


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

    def test_config_schema_from_leader(self):
        dept = get_department("problem_solver")
        assert "github_playground_repo" in dept["leader"].config_schema
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestProblemSolverRegistration -v`
Expected: FAIL (department not registered yet)

- [ ] **Step 3: Register the department**

Add to `backend/agents/blueprints/__init__.py` before the `DEPARTMENT_TYPE_CHOICES` line (before line 196). Insert after the Community & Partnerships block:

```python
# ── Problem Solver ─────────────────────────────────────────────────────────

try:
    from agents.blueprints.problem_solver.leader import ProblemSolverLeaderBlueprint
except ImportError:
    ProblemSolverLeaderBlueprint = None

_problem_solver_workforce = {}
_problem_solver_imports = {
    "out_of_box_thinker": (
        "agents.blueprints.problem_solver.workforce.out_of_box_thinker",
        "OutOfBoxThinkerBlueprint",
    ),
    "playground": ("agents.blueprints.problem_solver.workforce.playground", "PlaygroundBlueprint"),
    "synthesizer": ("agents.blueprints.problem_solver.workforce.synthesizer", "SynthesizerBlueprint"),
    "reviewer": ("agents.blueprints.problem_solver.workforce.reviewer", "ReviewerBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _problem_solver_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _problem_solver_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if ProblemSolverLeaderBlueprint is not None:
    _problem_solver_leader = ProblemSolverLeaderBlueprint()
    DEPARTMENTS["problem_solver"] = {
        "name": "Problem Solver",
        "description": (
            "First-principles problem decomposition, cross-domain ideation, "
            "parallel hypothesis testing, and validated proof-of-concept synthesis"
        ),
        "leader": _problem_solver_leader,
        "workforce": _problem_solver_workforce,
        "config_schema": _problem_solver_leader.config_schema,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py::TestProblemSolverRegistration -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the full existing blueprint test suite to check for regressions**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_blueprints.py -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/__init__.py backend/agents/tests/test_problem_solver.py
git commit -m "feat: register Problem Solver department in blueprint registry"
```

---

### Task 9: Full integration test

**Files:**
- Modify: `backend/agents/tests/test_problem_solver.py`

- [ ] **Step 1: Write integration test for the leader's generate_task_proposal pipeline**

Append to `backend/agents/tests/test_problem_solver.py`:

```python
@pytest.mark.django_db
class TestProblemSolverPipeline:
    @pytest.fixture
    def ps_department(self, project):
        return Department.objects.create(department_type="problem_solver", project=project)

    @pytest.fixture
    def ps_sprint(self, ps_department, user):
        s = Sprint.objects.create(
            project=ps_department.project,
            text="Find an algorithm to predict stock price direction with >60% accuracy using cross-domain insight",
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

        # Simulate decomposition completed
        dept_id = str(ps_leader.department_id)
        ps_sprint.set_department_state(dept_id, {
            "status": "running",
            "round": 0,
            "decomposition": {
                "actors": ["market", "traders"],
                "dynamics": ["price movement", "volume"],
                "definition_of_done": "Predict direction with >60% accuracy on held-out data",
                "math_bias": "statistical modelling",
            },
        })

        # Create a completed leader task
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
        ps_sprint.set_department_state(dept_id, {
            "status": "running",
            "round": 10,
            "decomposition": {"definition_of_done": "test"},
        })

        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is None
        ps_sprint.refresh_from_db()
        assert ps_sprint.status == Sprint.Status.DONE

    def test_no_running_sprints_returns_none(self, ps_leader, ps_workforce):
        bp = ProblemSolverLeaderBlueprint()
        proposal = bp.generate_task_proposal(ps_leader)
        assert proposal is None
```

- [ ] **Step 2: Add required imports at top of test file**

Ensure these imports are at the top of `backend/agents/tests/test_problem_solver.py`:

```python
import pytest

from agents.models import Agent, AgentTask
from projects.models import Department, Project, Sprint
```

- [ ] **Step 3: Run the full test suite**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_problem_solver.py -v`
Expected: ALL tests pass

- [ ] **Step 4: Run the complete blueprint test suite for regressions**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_blueprints.py backend/agents/tests/test_problem_solver.py -v`
Expected: ALL tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/agents/tests/test_problem_solver.py
git commit -m "test: integration tests for Problem Solver pipeline orchestration"
```

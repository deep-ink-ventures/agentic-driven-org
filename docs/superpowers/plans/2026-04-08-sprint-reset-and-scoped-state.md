# Sprint Reset & Sprint-Scoped Agent State — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `AgentSprintState` model so agent state is sprint-scoped, and a Django admin action to fully reset a sprint for testing.

**Architecture:** New `AgentSprintState` model with `(agent, sprint)` unique constraint holds sprint-specific state (stage_status, review_rounds, etc.). Blueprint code migrates from `agent.internal_state` to `AgentSprintState.state` for sprint-scoped keys. Admin action bulk-deletes tasks, docs, outputs, and agent states for selected sprints.

**Tech Stack:** Django ORM, Django Admin, pytest

---

### Task 1: AgentSprintState Model

**Files:**
- Create: `backend/agents/models/agent_sprint_state.py`
- Modify: `backend/agents/models/__init__.py`
- Test: `backend/agents/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

In `backend/agents/tests/test_models.py`, add at the end:

```python
from agents.models import AgentSprintState
from projects.models import Sprint


@pytest.fixture
def sprint(department):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(email="sprint-state@example.com", password="pass")
    return Sprint.objects.create(
        project=department.project,
        text="Test sprint",
        created_by=user,
    )


@pytest.mark.django_db
class TestAgentSprintState:
    def test_create_sprint_state(self, agent, sprint):
        state = AgentSprintState.objects.create(
            agent=agent,
            sprint=sprint,
            state={"stage_status": {"pitch": {"status": "not_started"}}},
        )
        assert state.pk is not None
        assert state.state["stage_status"]["pitch"]["status"] == "not_started"

    def test_unique_constraint(self, agent, sprint):
        AgentSprintState.objects.create(agent=agent, sprint=sprint)
        with pytest.raises(IntegrityError):
            AgentSprintState.objects.create(agent=agent, sprint=sprint)

    def test_cascade_on_agent_delete(self, agent, sprint):
        state = AgentSprintState.objects.create(agent=agent, sprint=sprint)
        state_pk = state.pk
        agent.delete()
        assert not AgentSprintState.objects.filter(pk=state_pk).exists()

    def test_cascade_on_sprint_delete(self, agent, sprint):
        state = AgentSprintState.objects.create(agent=agent, sprint=sprint)
        state_pk = state.pk
        sprint.delete()
        assert not AgentSprintState.objects.filter(pk=state_pk).exists()

    def test_default_state_is_empty_dict(self, agent, sprint):
        state = AgentSprintState.objects.create(agent=agent, sprint=sprint)
        assert state.state == {}

    def test_str(self, agent, sprint):
        state = AgentSprintState.objects.create(agent=agent, sprint=sprint)
        result = str(state)
        assert agent.name in result
        assert "Test sprint" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_models.py::TestAgentSprintState -v`
Expected: ImportError — `AgentSprintState` does not exist yet.

- [ ] **Step 3: Create the model**

Create `backend/agents/models/agent_sprint_state.py`:

```python
import uuid

from django.db import models


class AgentSprintState(models.Model):
    """Sprint-scoped state for an agent.

    Holds state like stage_status, review_rounds, pipeline_steps that
    must be isolated per sprint. Agent.internal_state remains for
    non-sprint state (webhooks, hourly tasks).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="sprint_states",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="agent_states",
    )
    state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "sprint"],
                name="one_state_per_agent_per_sprint",
            ),
        ]

    def __str__(self):
        sprint_text = self.sprint.text[:40] if self.sprint else "?"
        return f"{self.agent.name} — {sprint_text}"
```

- [ ] **Step 4: Export from `__init__.py`**

In `backend/agents/models/__init__.py`, add the import:

```python
from .agent import Agent
from .agent_sprint_state import AgentSprintState
from .agent_task import AgentTask

__all__ = ["Agent", "AgentSprintState", "AgentTask"]
```

- [ ] **Step 5: Create and run migration**

Run: `cd backend && python manage.py makemigrations agents --name agent_sprint_state && python manage.py migrate`
Expected: Migration created and applied successfully.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_models.py::TestAgentSprintState -v`
Expected: All 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/models/agent_sprint_state.py backend/agents/models/__init__.py backend/agents/migrations/ backend/agents/tests/test_models.py
git commit -m "feat: add AgentSprintState model for sprint-scoped agent state"
```

---

### Task 2: Sprint State Helper Functions

**Files:**
- Create: `backend/agents/state.py`
- Test: `backend/agents/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

Create `backend/agents/tests/test_state.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from agents.models import Agent, AgentSprintState
from agents.state import get_sprint_state, save_sprint_state
from projects.models import Department, Project, Sprint

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="state-test@example.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="State Test", goal="Test", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="marketing", project=project)


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Test Agent",
        agent_type="twitter",
        department=department,
        status=Agent.Status.ACTIVE,
    )


@pytest.fixture
def sprint(project, user):
    return Sprint.objects.create(project=project, text="Test sprint", created_by=user)


@pytest.mark.django_db
class TestGetSprintState:
    def test_creates_new_state(self, agent, sprint):
        state_obj = get_sprint_state(agent, sprint)
        assert state_obj.pk is not None
        assert state_obj.agent == agent
        assert state_obj.sprint == sprint
        assert state_obj.state == {}

    def test_returns_existing_state(self, agent, sprint):
        existing = AgentSprintState.objects.create(
            agent=agent, sprint=sprint, state={"foo": "bar"}
        )
        state_obj = get_sprint_state(agent, sprint)
        assert state_obj.pk == existing.pk
        assert state_obj.state == {"foo": "bar"}

    def test_returns_none_when_no_sprint(self, agent):
        state_obj = get_sprint_state(agent, None)
        assert state_obj is None


@pytest.mark.django_db
class TestSaveSprintState:
    def test_save_persists_state(self, agent, sprint):
        state_obj = get_sprint_state(agent, sprint)
        state_obj.state["stage_status"] = {"pitch": {"status": "running"}}
        save_sprint_state(state_obj)

        state_obj.refresh_from_db()
        assert state_obj.state["stage_status"]["pitch"]["status"] == "running"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_state.py -v`
Expected: ImportError — `agents.state` does not exist.

- [ ] **Step 3: Implement the helpers**

Create `backend/agents/state.py`:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentSprintState
    from projects.models import Sprint


def get_sprint_state(agent: Agent, sprint: Sprint | None) -> AgentSprintState | None:
    """Get or create the AgentSprintState for this agent+sprint pair.

    Returns None if sprint is None (e.g. non-sprint tasks).
    """
    if sprint is None:
        return None
    from agents.models import AgentSprintState

    obj, _ = AgentSprintState.objects.get_or_create(agent=agent, sprint=sprint)
    return obj


def save_sprint_state(state_obj: AgentSprintState) -> None:
    """Save the sprint state object."""
    state_obj.save(update_fields=["state", "updated_at"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_state.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/state.py backend/agents/tests/test_state.py
git commit -m "feat: add get_sprint_state/save_sprint_state helper functions"
```

---

### Task 3: Migrate Base Blueprint Review State to Sprint-Scoped

**Files:**
- Modify: `backend/agents/blueprints/base.py` (lines 541-667)
- Test: `backend/agents/tests/test_models.py` (add review state tests)

The base blueprint's `_propose_review_chain`, `_apply_quality_gate`, and `_evaluate_review_and_loop` currently read/write `agent.internal_state` for review_rounds, active_review_key, and polish_attempts. These must use `AgentSprintState` instead.

Key: all three methods have access to a task (`creator_task` or `review_task`) which has `.sprint`.

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_models.py` inside the `TestAgentSprintState` class:

```python
    def test_review_state_isolated_per_sprint(self, agent, sprint, department):
        """Two sprints on the same agent get independent review state."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(email="sprint2@example.com", password="pass")
        sprint2 = Sprint.objects.create(
            project=department.project,
            text="Second sprint",
            created_by=user,
        )
        state1 = AgentSprintState.objects.create(
            agent=agent, sprint=sprint,
            state={"review_rounds": {"task-a": 3}},
        )
        state2 = AgentSprintState.objects.create(
            agent=agent, sprint=sprint2,
            state={"review_rounds": {"task-b": 1}},
        )
        assert state1.state["review_rounds"] == {"task-a": 3}
        assert state2.state["review_rounds"] == {"task-b": 1}
        # Mutating one does not affect the other
        state1.state["review_rounds"]["task-a"] = 5
        state1.save()
        state2.refresh_from_db()
        assert state2.state["review_rounds"]["task-b"] == 1
```

- [ ] **Step 2: Run test to verify it passes** (this is a data isolation test that should pass immediately with the model from Task 1)

Run: `cd backend && python -m pytest agents/tests/test_models.py::TestAgentSprintState::test_review_state_isolated_per_sprint -v`
Expected: PASS.

- [ ] **Step 3: Update `_propose_review_chain` in base.py**

In `backend/agents/blueprints/base.py`, replace lines 541-550:

Old code:
```python
        # Track review round and active chain key
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        task_key = str(creator_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        internal_state["review_rounds"] = review_rounds
        internal_state["active_review_key"] = task_key  # so _evaluate_review_and_loop can find it
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
```

New code:
```python
        # Track review round and active chain key (sprint-scoped)
        from agents.state import get_sprint_state, save_sprint_state

        sprint_state = get_sprint_state(agent, creator_task.sprint)
        if sprint_state:
            review_rounds = sprint_state.state.get("review_rounds", {})
            task_key = str(creator_task.id)
            round_num = review_rounds.get(task_key, 0) + 1
            review_rounds[task_key] = round_num
            sprint_state.state["review_rounds"] = review_rounds
            sprint_state.state["active_review_key"] = task_key
            save_sprint_state(sprint_state)
        else:
            task_key = str(creator_task.id)
            round_num = 1
```

- [ ] **Step 4: Update `_apply_quality_gate` in base.py**

Replace lines 612-667 of `_apply_quality_gate`:

Old code:
```python
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        polish_attempts_map = internal_state.get("polish_attempts", {})
```
...through to...
```python
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
        return accepted, polish_count, round_num
```

New code — the full method body becomes:

```python
    def _apply_quality_gate(self, agent: Agent, score: float, stage_key: str, sprint=None) -> tuple[bool, int, int]:
        """Apply universal quality scoring logic.

        Tracks polish attempts and evaluates acceptance.
        Returns (accepted, polish_count, round_num).

        Args:
            agent: The leader agent.
            score: The review score (0.0-10.0).
            stage_key: Key to track this review chain in state.
            sprint: The sprint context (for sprint-scoped state).
        """
        from agents.state import get_sprint_state, save_sprint_state

        sprint_state = get_sprint_state(agent, sprint)
        state = sprint_state.state if sprint_state else (agent.internal_state or {})

        review_rounds = state.get("review_rounds", {})
        polish_attempts_map = state.get("polish_attempts", {})

        round_num = review_rounds.get(stage_key, 1)

        # Update polish attempts counter (count attempts after reaching 9.0)
        polish_count = polish_attempts_map.get(stage_key, 0)
        if score >= NEAR_EXCELLENCE_THRESHOLD:
            polish_count += 1
            polish_attempts_map[stage_key] = polish_count

        dept_name = agent.department.name if hasattr(agent, "department") else "?"
        logger.info(
            "REVIEW_DECISION dept=%s agent=%s score=%.1f/10 round=%d polish=%d/%d key=%s",
            dept_name,
            agent.name,
            score,
            round_num,
            polish_count,
            MAX_POLISH_ATTEMPTS,
            stage_key,
        )

        accepted = should_accept_review(score, round_num, polish_count)

        if accepted:
            reason = "excellence" if score >= EXCELLENCE_THRESHOLD else f"diminishing_returns (polish={polish_count})"
            logger.info(
                "REVIEW_ACCEPTED dept=%s score=%.1f/10 reason=%s key=%s",
                dept_name,
                score,
                reason,
                stage_key,
            )
            # Clear tracking for this key
            review_rounds.pop(stage_key, None)
            polish_attempts_map.pop(stage_key, None)
            state["review_rounds"] = review_rounds
            state["polish_attempts"] = polish_attempts_map
            state.pop("active_review_key", None)
        else:
            gap = EXCELLENCE_THRESHOLD - score
            logger.info(
                "REVIEW_REJECTED dept=%s score=%.1f/10 gap=%.1f round=%d key=%s",
                dept_name,
                score,
                gap,
                round_num,
                stage_key,
            )
            # Persist polish tracking
            state["polish_attempts"] = polish_attempts_map

        if sprint_state:
            sprint_state.state = state
            save_sprint_state(sprint_state)
        else:
            agent.internal_state = state
            agent.save(update_fields=["internal_state"])

        return accepted, polish_count, round_num
```

- [ ] **Step 5: Update `_evaluate_review_and_loop` in base.py**

In `_evaluate_review_and_loop` (around line 690-701), replace the state lookup:

Old code:
```python
        # Find the task key: use stored active_review_key (set when review chain starts)
        internal_state = agent.internal_state or {}
        task_key = internal_state.get("active_review_key")
        if not task_key:
            review_rounds = internal_state.get("review_rounds", {})
            for key in review_rounds:
                task_key = key
                break
        if not task_key:
            task_key = str(review_task.id)

        accepted, polish_count, round_num = self._apply_quality_gate(agent, score, task_key)
```

New code:
```python
        # Find the task key: use stored active_review_key (set when review chain starts)
        from agents.state import get_sprint_state

        sprint_state = get_sprint_state(agent, review_task.sprint)
        state = sprint_state.state if sprint_state else (agent.internal_state or {})
        task_key = state.get("active_review_key")
        if not task_key:
            review_rounds = state.get("review_rounds", {})
            for key in review_rounds:
                task_key = key
                break
        if not task_key:
            task_key = str(review_task.id)

        accepted, polish_count, round_num = self._apply_quality_gate(agent, score, task_key, sprint=review_task.sprint)
```

- [ ] **Step 6: Update `_get_review_round_count` if it exists**

Search for `_get_review_round_count` in base.py. If it reads `agent.internal_state`, update it to use sprint state. (From the grep output, the method name wasn't found — the round count is read inline in `_apply_quality_gate`, which is already updated.)

- [ ] **Step 7: Run full test suite for agents**

Run: `cd backend && python -m pytest agents/tests/ -v --tb=short`
Expected: All tests pass (existing tests may need minor updates if they mock `agent.internal_state` for review state).

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_models.py
git commit -m "refactor: migrate base blueprint review state to AgentSprintState"
```

---

### Task 4: Migrate `_apply_on_dispatch` to Sprint-Scoped State

**Files:**
- Modify: `backend/agents/tasks.py` (lines 232-252, 431-432)

The `_apply_on_dispatch` function writes `stage_status` into `agent.internal_state`. It needs to use `AgentSprintState` instead. It currently receives `(agent, on_dispatch)` but doesn't have the sprint. We need to pass the sprint_id through.

- [ ] **Step 1: Update `_apply_on_dispatch` signature and body**

In `backend/agents/tasks.py`, replace lines 232-252:

Old code:
```python
def _apply_on_dispatch(agent, on_dispatch):
    """Apply state transition after tasks are successfully created.

    Prevents state desync: if task creation fails (celery down, old worker, etc.),
    the leader state remains unchanged and can be retried cleanly.
    """
    set_status = on_dispatch.get("set_status")
    stage = on_dispatch.get("stage")
    if not set_status or not stage:
        return

    agent.refresh_from_db()
    internal_state = agent.internal_state or {}
    stage_status = internal_state.get("stage_status", {})
    current_info = stage_status.get(stage, {"iterations": 0})
    current_info["status"] = set_status
    stage_status[stage] = current_info
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    logger.info("Leader %s: stage '%s' → %s (on_dispatch)", agent.name, stage, set_status)
```

New code:
```python
def _apply_on_dispatch(agent, on_dispatch, sprint_id=None):
    """Apply state transition after tasks are successfully created.

    Prevents state desync: if task creation fails (celery down, old worker, etc.),
    the leader state remains unchanged and can be retried cleanly.
    """
    set_status = on_dispatch.get("set_status")
    stage = on_dispatch.get("stage")
    if not set_status or not stage:
        return

    agent.refresh_from_db()

    from agents.state import get_sprint_state, save_sprint_state
    from projects.models import Sprint

    sprint = Sprint.objects.filter(id=sprint_id).first() if sprint_id else None
    sprint_state = get_sprint_state(agent, sprint)

    if sprint_state:
        state = sprint_state.state
    else:
        state = agent.internal_state or {}

    stage_status = state.get("stage_status", {})
    current_info = stage_status.get(stage, {"iterations": 0})
    current_info["status"] = set_status
    stage_status[stage] = current_info
    state["stage_status"] = stage_status

    if sprint_state:
        sprint_state.state = state
        save_sprint_state(sprint_state)
    else:
        agent.internal_state = state
        agent.save(update_fields=["internal_state"])

    logger.info("Leader %s: stage '%s' → %s (on_dispatch)", agent.name, stage, set_status)
```

- [ ] **Step 2: Update the call site to pass sprint_id**

In the same file, around line 431-432, change:

Old:
```python
            if created > 0 and on_dispatch:
                _apply_on_dispatch(agent, on_dispatch)
```

New:
```python
            if created > 0 and on_dispatch:
                _apply_on_dispatch(agent, on_dispatch, sprint_id=sprint_id)
```

- [ ] **Step 3: Run existing task tests**

Run: `cd backend && python -m pytest agents/tests/test_tasks.py -v --tb=short`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add backend/agents/tasks.py
git commit -m "refactor: migrate _apply_on_dispatch stage_status to sprint-scoped state"
```

---

### Task 5: Migrate Writers Room Leader to Sprint-Scoped State

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`

This is the most heavily affected file. The writers room leader stores `current_stage`, `stage_status`, `current_iteration`, `format_type`, `entry_detected`, and `terminal_stage` in `agent.internal_state`. All of these are sprint-scoped.

The pattern is the same everywhere: replace `internal_state = agent.internal_state or {}` with sprint state lookup, and replace `agent.internal_state = internal_state; agent.save(...)` with `save_sprint_state(sprint_state)`.

The leader always has access to `sprint` from `running_sprints[0]` in the `_get_delegation_context` and `generate_task_proposal` override.

- [ ] **Step 1: Add sprint-state imports at the top of the file**

Add after existing imports in `backend/agents/blueprints/writers_room/leader/agent.py`:

```python
from agents.state import get_sprint_state, save_sprint_state
```

- [ ] **Step 2: Update `_get_delegation_context`**

This method (around line 162) takes `agent` but doesn't have the sprint. It needs to accept a sprint parameter. Find the caller and pass it.

Old (line ~162):
```python
    def _get_delegation_context(self, agent):
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_stage = internal_state.get("current_stage", STAGES[0])
```

New:
```python
    def _get_delegation_context(self, agent, sprint=None):
        sprint_state = get_sprint_state(agent, sprint)
        state = sprint_state.state if sprint_state else {}
        stage_status = state.get("stage_status", {})
        current_stage = state.get("current_stage", STAGES[0])
```

Also update `_get_effective_stage` (around line 174):

Old:
```python
    def _get_effective_stage(self, agent, current_stage: str) -> str:
        """For series at treatment position, return 'concept' for matrix lookups."""
        internal_state = agent.internal_state or {}
        format_type = internal_state.get("format_type", "standalone")
```

New:
```python
    def _get_effective_stage(self, agent, current_stage: str, sprint=None) -> str:
        """For series at treatment position, return 'concept' for matrix lookups."""
        sprint_state = get_sprint_state(agent, sprint)
        state = sprint_state.state if sprint_state else {}
        format_type = state.get("format_type", "standalone")
```

- [ ] **Step 3: Update `generate_task_proposal` override**

This is the main method (starts around line 340). It already has `sprint` from the running sprint lookup. Every occurrence of:
```python
internal_state = agent.internal_state or {}
```
becomes:
```python
sprint_state = get_sprint_state(agent, sprint)
state = sprint_state.state
```

And every occurrence of:
```python
agent.internal_state = internal_state
agent.save(update_fields=["internal_state"])
```
becomes:
```python
sprint_state.state = state
save_sprint_state(sprint_state)
```

Apply this transformation to ALL occurrences in the `generate_task_proposal` method and all the sub-methods it calls that currently use `agent.internal_state`:

- The initial format detection block (~line 348-362)
- The stage advancement block (~line 370-384)
- The `creative_gate` status handler (~line 449-452)
- The `creative_gate_done` handler (~line 464-481)
- The `deliverable_gate` handler (~line 495-498)
- The `deliverable_gate_done` handler (~line 510-527)
- The `feedback_done` handler (~line 539-542)
- The passed/advance handler (~line 551-574)
- The unknown status fallback (~line 601-604)

**Important:** Since `sprint` is available at the top of `generate_task_proposal`, pass it through to all helper methods that need state. For methods called within generate_task_proposal, use the `sprint_state` / `state` variables already in scope rather than re-fetching.

- [ ] **Step 4: Update helper methods that read internal_state**

The following helper methods currently read `agent.internal_state` and need sprint passed in:

- `_propose_creative_tasks` (~line 628, 663): reads `internal_state` for `current_stage` and `stage_status`
- `_propose_lead_writer_task` (~line 1127): reads `format_type`, `stage_status`
- `_create_deliverable_and_research_docs` (~line 1271): reads `stage_status` iterations

For each, add a `sprint=None` parameter and use sprint state. Since these are called from `generate_task_proposal` which has `sprint`, pass it through.

- [ ] **Step 5: Update callers of `_get_delegation_context` and `_get_effective_stage`**

Search for calls to these methods and pass the sprint argument. These are called from `generate_task_proposal` which has `sprint` available.

- [ ] **Step 6: Run writers room tests**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_feedback_blueprint.py -v --tb=short`
Expected: Tests pass (may need mock updates if they mock `agent.internal_state` for these keys).

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py
git commit -m "refactor: migrate writers room leader state to AgentSprintState"
```

---

### Task 6: Migrate Sales Leader to Sprint-Scoped State

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py`

The sales leader already keys `pipeline_steps` by sprint_id within `internal_state`. Moving to `AgentSprintState` simplifies this — the sprint scoping is handled by the model, so `pipeline_steps` becomes a flat key.

- [ ] **Step 1: Update the pipeline state reads/writes**

In `backend/agents/blueprints/sales/leader/agent.py`, the `generate_task_proposal` override (around line 190) does:

Old:
```python
        internal_state = agent.internal_state or {}
        pipeline_steps = internal_state.get("pipeline_steps", {})
        current_step = pipeline_steps.get(sprint_id, None)
```

New:
```python
        from agents.state import get_sprint_state, save_sprint_state

        sprint_state = get_sprint_state(agent, sprint)
        state = sprint_state.state if sprint_state else {}
        current_step = state.get("pipeline_step", None)
```

Note: since state is now sprint-scoped, we no longer need the `pipeline_steps[sprint_id]` nesting. It becomes a flat `pipeline_step` key.

Apply the same pattern to all state writes in this file:
- Initial step set (~line 199-202): `state["pipeline_step"] = current_step; save_sprint_state(sprint_state)`
- Step advancement (~line 260-263): `state["pipeline_step"] = next_step; save_sprint_state(sprint_state)`
- Cleanup in `_handle_dispatch_step` (~line 307-310): `state.pop("pipeline_step", None); save_sprint_state(sprint_state)`

Also update `_handle_dispatch_step` signature to receive `sprint_state` instead of `internal_state` and `pipeline_steps`.

- [ ] **Step 2: Run sales tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v --tb=short`
Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/sales/leader/agent.py
git commit -m "refactor: migrate sales leader pipeline state to AgentSprintState"
```

---

### Task 7: Admin Action — Reset Sprint

**Files:**
- Modify: `backend/projects/admin/sprint_admin.py`
- Test: `backend/projects/tests/test_sprints.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/projects/tests/test_sprints.py`:

```python
from agents.models import AgentSprintState
from projects.models import Document, Output


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Test Worker",
        agent_type="backend_engineer",
        department=department,
        status=Agent.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestResetSprintAdminAction:
    def test_reset_deletes_tasks(self, sprint, department, agent):
        AgentTask.objects.create(agent=agent, sprint=sprint, exec_summary="Task 1", command_name="post-content")
        AgentTask.objects.create(agent=agent, sprint=sprint, exec_summary="Task 2", command_name="post-content")
        assert sprint.tasks.count() == 2

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        assert sprint.tasks.count() == 0

    def test_reset_deletes_outputs(self, sprint, department):
        Output.objects.create(sprint=sprint, department=department, title="Draft 1")
        assert sprint.outputs.count() == 1

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        assert sprint.outputs.count() == 0

    def test_reset_deletes_documents(self, sprint, department):
        Document.objects.create(
            title="Sprint Progress",
            department=department,
            sprint=sprint,
            doc_type="sprint_progress",
        )
        assert sprint.documents.count() == 1

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        assert sprint.documents.count() == 0

    def test_reset_deletes_agent_sprint_state(self, sprint, agent):
        AgentSprintState.objects.create(
            agent=agent, sprint=sprint,
            state={"stage_status": {"pitch": {"status": "running"}}},
        )
        assert sprint.agent_states.count() == 1

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        assert sprint.agent_states.count() == 0

    def test_reset_preserves_sources(self, sprint, project, user):
        from projects.models import Source
        source = Source.objects.create(
            project=project,
            sprint=sprint,
            title="Reference doc",
            source_type="file",
        )

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        source.refresh_from_db()
        assert source.sprint == sprint  # preserved

    def test_reset_resets_sprint_fields(self, sprint):
        sprint.status = Sprint.Status.DONE
        sprint.completion_summary = "All done"
        sprint.completed_at = timezone.now()
        sprint.save()

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        sprint.refresh_from_db()
        assert sprint.status == Sprint.Status.RUNNING
        assert sprint.completion_summary == ""
        assert sprint.completed_at is None

    def test_reset_preserves_sprint_text(self, sprint):
        original_text = sprint.text

        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        sprint.refresh_from_db()
        assert sprint.text == original_text

    def test_reset_preserves_departments(self, sprint, department):
        from projects.admin.sprint_admin import reset_sprint
        reset_sprint(None, None, Sprint.objects.filter(pk=sprint.pk))

        sprint.refresh_from_db()
        assert sprint.departments.filter(pk=department.pk).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest projects/tests/test_sprints.py::TestResetSprintAdminAction -v`
Expected: ImportError — `reset_sprint` does not exist.

- [ ] **Step 3: Implement the admin action**

Replace the contents of `backend/projects/admin/sprint_admin.py`:

```python
from django.contrib import admin

from projects.models import Sprint


@admin.action(description="Reset selected sprints (delete all tasks, docs, outputs, agent state)")
def reset_sprint(modeladmin, request, queryset):
    """Wipe all generated artifacts and reset sprint to fresh RUNNING state.

    Preserves: sprint text, sources, department assignments.
    Deletes: tasks, documents, outputs, agent sprint state.
    """
    for sprint in queryset:
        sprint.tasks.all().delete()
        sprint.documents.all().delete()
        sprint.outputs.all().delete()
        sprint.agent_states.all().delete()
        sprint.status = Sprint.Status.RUNNING
        sprint.completion_summary = ""
        sprint.completed_at = None
        sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "status", "project", "created_at")
    list_filter = ("status", "project")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at", "completed_at")
    actions = [reset_sprint]

    def text_preview(self, obj):
        return obj.text[:80]

    text_preview.short_description = "Text"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest projects/tests/test_sprints.py::TestResetSprintAdminAction -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/projects/admin/sprint_admin.py backend/projects/tests/test_sprints.py
git commit -m "feat: add reset_sprint admin action to wipe sprint artifacts"
```

---

### Task 8: Full Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All tests pass. If any fail, fix them — likely mock updates needed where tests set `agent.internal_state` for sprint-scoped keys.

- [ ] **Step 2: Check for any remaining direct internal_state usage for sprint-scoped keys**

Run: `cd backend && grep -rn "internal_state.*stage_status\|internal_state.*review_rounds\|internal_state.*active_review_key\|internal_state.*polish_attempts\|internal_state.*pipeline_steps\|internal_state.*current_stage\|internal_state.*format_type\|internal_state.*terminal_stage\|internal_state.*entry_detected\|internal_state.*current_iteration" agents/blueprints/ agents/tasks.py`

Expected: No matches. If any remain, migrate them.

- [ ] **Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: update remaining tests for sprint-scoped state migration"
```

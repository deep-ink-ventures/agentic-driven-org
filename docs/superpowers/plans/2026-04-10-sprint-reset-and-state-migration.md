# Sprint Reset + State Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move pipeline state from leader `internal_state` to `sprint.department_state`, add "Reset Sprint" admin action.

**Architecture:** New JSONField on Sprint keyed by department ID. Base class review methods resolve sprint from task FK. Each leader reads/writes state via `sprint.get_department_state()` / `sprint.set_department_state()`. Admin action deletes all derived artifacts and resets state in one click.

**Tech Stack:** Django models, Django admin, pytest

---

## File Structure

### New/modified files
- `backend/projects/models/sprint.py` — add `department_state` field + helper methods
- `backend/projects/migrations/0024_sprint_department_state.py` — auto-generated
- `backend/agents/blueprints/base.py` — update review methods to use sprint state
- `backend/agents/blueprints/sales/leader/agent.py` — migrate from internal_state to sprint state
- `backend/agents/blueprints/writers_room/leader/agent.py` — migrate from internal_state to sprint state
- `backend/projects/admin/sprint_admin.py` — add reset action
- `backend/agents/tests/test_sales_department.py` — update tests
- `backend/projects/tests/test_sprint_reset.py` — new test file for reset action

---

### Task 1: Sprint Model — Add `department_state` Field

**Files:**
- Modify: `backend/projects/models/sprint.py`
- Migration: auto-generated
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/agents/tests/test_sales_department.py`, new test class:

```python
@pytest.mark.django_db
class TestSprintDepartmentState:
    def test_default_empty(self, sprint):
        assert sprint.department_state == {}

    def test_get_department_state_empty(self, sprint, department):
        state = sprint.get_department_state(department.id)
        assert state == {}

    def test_set_and_get_department_state(self, sprint, department):
        sprint.set_department_state(department.id, {"pipeline_step": "research"})
        sprint.refresh_from_db()
        state = sprint.get_department_state(department.id)
        assert state == {"pipeline_step": "research"}

    def test_multiple_departments(self, sprint, department, project):
        from projects.models import Department
        dept2 = Department.objects.create(department_type="writers_room", project=project)
        sprint.departments.add(dept2)

        sprint.set_department_state(department.id, {"pipeline_step": "research"})
        sprint.set_department_state(dept2.id, {"current_stage": "concept"})
        sprint.refresh_from_db()

        assert sprint.get_department_state(department.id)["pipeline_step"] == "research"
        assert sprint.get_department_state(dept2.id)["current_stage"] == "concept"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestSprintDepartmentState -v`
Expected: AttributeError — `department_state` doesn't exist.

- [ ] **Step 3: Add field and helpers to Sprint model**

In `backend/projects/models/sprint.py`, add after `completed_at`:

```python
    department_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-department pipeline state keyed by department ID. Reset clears this.",
    )

    def get_department_state(self, department_id) -> dict:
        """Get pipeline state for a department in this sprint."""
        return self.department_state.get(str(department_id), {})

    def set_department_state(self, department_id, state: dict):
        """Set pipeline state for a department in this sprint."""
        self.department_state[str(department_id)] = state
        self.save(update_fields=["department_state", "updated_at"])
```

- [ ] **Step 4: Generate and apply migration**

Run: `cd backend && python manage.py makemigrations projects --name sprint_department_state && python manage.py migrate`

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestSprintDepartmentState -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/models/sprint.py backend/projects/migrations/ backend/agents/tests/test_sales_department.py
git commit -m "feat: add department_state JSONField to Sprint with helper methods"
```

---

### Task 2: Migrate Base Class Review Methods to Sprint State

**Files:**
- Modify: `backend/agents/blueprints/base.py:548-733` (review methods in LeaderBlueprint)
- Test: `backend/agents/tests/test_sales_department.py`

The base class review methods (`_propose_review_chain`, `_apply_quality_gate`, `_evaluate_review_and_loop`, `_check_review_trigger`) currently store `review_rounds`, `polish_attempts`, and `active_review_key` on `agent.internal_state`. They need to store them on `sprint.department_state` instead.

**Key challenge:** These methods receive an `agent` and a `task` (AgentTask). The task has a `sprint` FK, so we can resolve the sprint. The department comes from `agent.department`.

- [ ] **Step 1: Update `_propose_review_chain`**

In `backend/agents/blueprints/base.py`, find `_propose_review_chain` (around line 548). Change the state tracking from `agent.internal_state` to `sprint.department_state`:

Current code stores review_rounds on agent.internal_state (lines 567-575):
```python
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        task_key = str(creator_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        internal_state["review_rounds"] = review_rounds
        internal_state["active_review_key"] = task_key
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
```

Replace with:
```python
        sprint = creator_task.sprint
        if not sprint:
            logger.warning("REVIEW_NO_SPRINT task=%s — cannot track review state", creator_task.id)
            return None

        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        review_rounds = dept_state.get("review_rounds", {})
        task_key = str(creator_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        dept_state["review_rounds"] = review_rounds
        dept_state["active_review_key"] = task_key
        sprint.set_department_state(dept_id, dept_state)
```

- [ ] **Step 2: Update `_apply_quality_gate`**

The method signature needs to change. Currently:
```python
def _apply_quality_gate(self, agent: Agent, score: float, stage_key: str) -> tuple[bool, int, int]:
```

It needs the sprint to read/write state. Add sprint parameter:
```python
def _apply_quality_gate(self, agent: Agent, sprint, score: float, stage_key: str) -> tuple[bool, int, int]:
```

Replace the internal_state reads (lines 637-639):
```python
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        polish_attempts_map = internal_state.get("polish_attempts", {})
```

With:
```python
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id) if sprint else {}
        review_rounds = dept_state.get("review_rounds", {})
        polish_attempts_map = dept_state.get("polish_attempts", {})
```

Replace the state writes (lines 672-692):
```python
        if accepted:
            ...
            review_rounds.pop(stage_key, None)
            polish_attempts_map.pop(stage_key, None)
            internal_state["review_rounds"] = review_rounds
            internal_state["polish_attempts"] = polish_attempts_map
            internal_state.pop("active_review_key", None)
        else:
            ...
            internal_state["polish_attempts"] = polish_attempts_map

        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
```

With:
```python
        if accepted:
            ...
            review_rounds.pop(stage_key, None)
            polish_attempts_map.pop(stage_key, None)
            dept_state["review_rounds"] = review_rounds
            dept_state["polish_attempts"] = polish_attempts_map
            dept_state.pop("active_review_key", None)
        else:
            ...
            dept_state["polish_attempts"] = polish_attempts_map

        if sprint:
            sprint.set_department_state(dept_id, dept_state)
```

- [ ] **Step 3: Update `_evaluate_review_and_loop`**

This method reads `active_review_key` from `agent.internal_state` (lines 716-724). Change to sprint state:

```python
        # Find the task key from sprint state
        sprint = review_task.sprint
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id) if sprint else {}
        task_key = dept_state.get("active_review_key")
        if not task_key:
            review_rounds = dept_state.get("review_rounds", {})
            for key in review_rounds:
                task_key = key
                break
        if not task_key:
            task_key = str(review_task.id)

        accepted, polish_count, round_num = self._apply_quality_gate(agent, sprint, score, task_key)
```

- [ ] **Step 4: Update `_check_review_trigger` in base class**

The base class `_check_review_trigger` (around line 789) calls `_propose_review_chain` and `_evaluate_review_and_loop`. No direct state access to change — but verify the calls still work since the child methods now use sprint state. No code change needed here if the callees handle sprint resolution themselves.

- [ ] **Step 5: Run all tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v`

Some tests may fail because the sales leader still reads from `agent.internal_state` — that's expected, we'll fix it in Task 3. The important thing is the base class methods don't crash.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/base.py
git commit -m "refactor: move review tracking from leader internal_state to sprint.department_state"
```

---

### Task 3: Migrate Sales Leader to Sprint State

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py`
- Test: `backend/agents/tests/test_sales_department.py`

Every place the sales leader reads/writes `internal_state["pipeline_steps"]` changes to `sprint.department_state`.

- [ ] **Step 1: Update `generate_task_proposal` — state reading**

Find lines 245-255 in the sales leader:
```python
        # 3. Determine current pipeline step
        internal_state = agent.internal_state or {}
        pipeline_steps = internal_state.get("pipeline_steps", {})
        current_step = pipeline_steps.get(sprint_id, None)

        if current_step is None:
            current_step = "research"
            pipeline_steps[sprint_id] = current_step
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
```

Replace with:
```python
        # 3. Determine current pipeline step from sprint state
        dept_id = str(department.id)
        dept_state = sprint.get_department_state(dept_id)
        current_step = dept_state.get("pipeline_step")

        if current_step is None:
            current_step = "research"
            dept_state["pipeline_step"] = current_step
            sprint.set_department_state(dept_id, dept_state)
```

- [ ] **Step 2: Update all method signatures and calls**

The sales leader passes `sprint_id`, `internal_state`, `pipeline_steps` through many methods. Replace these with the sprint object (which is already available). Each helper method should read/write state via `sprint.get_department_state()`/`sprint.set_department_state()`.

Methods to update:
- `_handle_linear_step` — remove `sprint_id, internal_state, pipeline_steps` params, add sprint
- `_handle_personalization_step` — same
- `_handle_dispatch_step` — same
- `_advance_to_next_step` (or `_advance_pipeline`) — same
- `_create_clones_and_dispatch` — same

For each, the pattern is:
```python
# OLD: pipeline_steps[sprint_id] = next_step; internal_state["pipeline_steps"] = pipeline_steps; agent.internal_state = internal_state; agent.save(...)
# NEW: dept_state = sprint.get_department_state(dept_id); dept_state["pipeline_step"] = next_step; sprint.set_department_state(dept_id, dept_state)
```

- [ ] **Step 3: Update dispatch completion — clean up state**

In `_handle_dispatch_step`, the sprint completion code currently does:
```python
pipeline_steps.pop(sprint_id, None)
internal_state["pipeline_steps"] = pipeline_steps
agent.internal_state = internal_state
agent.save(update_fields=["internal_state"])
```

This is no longer needed — when the sprint is DONE, the `department_state` stays as a record. No cleanup required. Remove the pipeline_steps cleanup code.

- [ ] **Step 4: Update tests**

Update `TestLeaderStateMachine` and `TestFanOutPersonalization` tests. They currently set up leader state with:
```python
leader.internal_state = {"pipeline_steps": {str(sprint.id): "research"}}
leader.save(update_fields=["internal_state"])
```

Change to:
```python
sprint.set_department_state(department.id, {"pipeline_step": "research"})
```

- [ ] **Step 5: Run all sales tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/leader/agent.py backend/agents/tests/test_sales_department.py
git commit -m "refactor: sales leader reads/writes pipeline state from sprint.department_state"
```

---

### Task 4: Migrate Writers Room Leader to Sprint State

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` (~50 sites)
- Test: existing writers room tests

This is the largest task — the writers room leader has ~50 read/write sites for `agent.internal_state`. The keys that move to sprint state:
- `current_stage`
- `current_iteration`
- `stage_status`
- `format_type`
- `terminal_stage`
- `detection_reasoning`
- `entry_detected`

**Strategy:** Search-and-replace pattern. Every instance of:
```python
internal_state = agent.internal_state or {}
```
becomes:
```python
dept_state = sprint.get_department_state(str(agent.department_id))
```

And every instance of:
```python
agent.internal_state = internal_state
agent.save(update_fields=["internal_state"])
```
becomes:
```python
sprint.set_department_state(str(agent.department_id), dept_state)
```

- [ ] **Step 1: Identify the sprint in writers room leader methods**

The writers room leader's `generate_task_proposal` already finds the sprint (same pattern as sales). Ensure the sprint object is passed through to all helper methods that need state. The writers room leader's generate_task_proposal resolves the sprint the same way as sales — find running sprints for the department.

Read the file and identify:
1. Where `sprint` is resolved (in generate_task_proposal)
2. All helper methods that need it passed in
3. The variable rename: `internal_state` → `dept_state` throughout

- [ ] **Step 2: Perform the migration**

Go through each of the ~50 sites identified in the exploration:
- Lines with `internal_state = agent.internal_state or {}` → `dept_state = sprint.get_department_state(dept_id)`
- Lines with `internal_state.get("current_stage"...)` → `dept_state.get("current_stage"...)`
- Lines with `internal_state["stage_status"] = ...` → `dept_state["stage_status"] = ...`
- Lines with `agent.internal_state = internal_state; agent.save(...)` → `sprint.set_department_state(dept_id, dept_state)`

Key: the sprint must be available in every method that accesses state. Thread it through method parameters where needed.

- [ ] **Step 3: Run writers room tests**

Run: `cd backend && python -m pytest agents/tests/test_writers_room*.py -v --tb=short`

Fix any failures. The tests may set up state via `leader.internal_state = {...}` — change to `sprint.set_department_state(...)`.

- [ ] **Step 4: Run full test suite**

Run: `cd backend && python -m pytest -q --tb=short`
Verify no regressions.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/
git commit -m "refactor: writers room leader reads/writes pipeline state from sprint.department_state"
```

---

### Task 5: Reset Sprint Admin Action

**Files:**
- Modify: `backend/projects/admin/sprint_admin.py`
- Create: `backend/projects/tests/test_sprint_reset.py`

- [ ] **Step 1: Write failing test**

Create `backend/projects/tests/test_sprint_reset.py`:

```python
"""Tests for the Reset Sprint admin action."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from agents.models import Agent, AgentTask, ClonedAgent
from projects.admin.sprint_admin import SprintAdmin
from projects.models import Department, Document, Output, Project, Sprint


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_superuser(email="admin@test.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test Project", goal="Test", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="sales", project=project)


@pytest.fixture
def sprint(department, user):
    s = Sprint.objects.create(project=department.project, text="Test sprint", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.fixture
def leader(department):
    return Agent.objects.create(
        name="Head of Sales", agent_type="leader", department=department,
        is_leader=True, status="active",
    )


@pytest.fixture
def workforce(department):
    agents = {}
    for slug in ["researcher", "strategist", "pitch_personalizer", "sales_qa", "email_outreach"]:
        agents[slug] = Agent.objects.create(
            name=f"Test {slug}", agent_type=slug, department=department,
            status="active", outreach=(slug == "email_outreach"),
        )
    return agents


@pytest.mark.django_db
class TestResetSprint:
    def test_deletes_tasks(self, sprint, leader, workforce):
        AgentTask.objects.create(agent=workforce["researcher"], sprint=sprint,
                                 command_name="research-industry", status="done", report="Done")
        AgentTask.objects.create(agent=workforce["strategist"], sprint=sprint,
                                 command_name="draft-strategy", status="done", report="Done")

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = leader  # any user object works for the action
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        assert AgentTask.objects.filter(sprint=sprint).count() == 0

    def test_deletes_clones(self, sprint, workforce):
        parent = workforce["pitch_personalizer"]
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = parent
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_deletes_documents(self, sprint, department):
        Document.objects.create(title="Test", content="X", department=department,
                                doc_type="research", sprint=sprint)

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = department
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        assert Document.objects.filter(sprint=sprint).count() == 0

    def test_deletes_outputs(self, sprint, department):
        Output.objects.create(sprint=sprint, department=department,
                              title="Test", label="outreach", content="X")

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = department
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        assert Output.objects.filter(sprint=sprint).count() == 0

    def test_clears_department_state(self, sprint, department):
        sprint.set_department_state(department.id, {"pipeline_step": "finalize"})

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = department
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        sprint.refresh_from_db()
        assert sprint.department_state == {}

    def test_resets_status_to_running(self, sprint, department):
        from django.utils import timezone
        sprint.status = "done"
        sprint.completion_summary = "Completed"
        sprint.completed_at = timezone.now()
        sprint.save()

        admin = SprintAdmin(Sprint, AdminSite())
        request = RequestFactory().post("/admin/")
        request.user = department
        admin.reset_and_restart(request, Sprint.objects.filter(id=sprint.id))

        sprint.refresh_from_db()
        assert sprint.status == "running"
        assert sprint.completion_summary == ""
        assert sprint.completed_at is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest projects/tests/test_sprint_reset.py -v`
Expected: AttributeError — `reset_and_restart` not found.

- [ ] **Step 3: Implement the admin action**

Rewrite `backend/projects/admin/sprint_admin.py`:

```python
import logging

from django.contrib import admin

from projects.models import Sprint

logger = logging.getLogger(__name__)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "status", "project", "created_at")
    list_filter = ("status", "project")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at", "completed_at")
    actions = ["reset_and_restart"]

    def text_preview(self, obj):
        return obj.text[:80]

    text_preview.short_description = "Text"

    @admin.action(description="Reset and restart sprint (deletes all tasks, docs, outputs)")
    def reset_and_restart(self, request, queryset):
        from agents.models import AgentTask, ClonedAgent
        from projects.models import Document, Output

        for sprint in queryset:
            # Delete derived artifacts
            tasks_deleted = AgentTask.objects.filter(sprint=sprint).delete()[0]
            clones_deleted = ClonedAgent.objects.filter(sprint=sprint).delete()[0]
            docs_deleted = Document.objects.filter(sprint=sprint).delete()[0]
            outputs_deleted = Output.objects.filter(sprint=sprint).delete()[0]

            # Clear pipeline state
            sprint.department_state = {}
            sprint.status = Sprint.Status.RUNNING
            sprint.completion_summary = ""
            sprint.completed_at = None
            sprint.save(update_fields=[
                "department_state", "status", "completion_summary",
                "completed_at", "updated_at",
            ])

            # Trigger leader task chains for each department
            from agents.tasks import create_next_leader_task

            for dept in sprint.departments.all():
                leader = dept.agents.filter(is_leader=True, status="active").first()
                if leader:
                    create_next_leader_task.delay(str(leader.id))

            logger.info(
                "SPRINT_RESET sprint=%s tasks=%d clones=%d docs=%d outputs=%d",
                str(sprint.id)[:8],
                tasks_deleted,
                clones_deleted,
                docs_deleted,
                outputs_deleted,
            )

        self.message_user(
            request,
            f"Reset {queryset.count()} sprint(s). Leaders will pick up fresh.",
        )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest projects/tests/test_sprint_reset.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `cd backend && python -m pytest -q --tb=short`
Verify no regressions.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/admin/sprint_admin.py backend/projects/tests/test_sprint_reset.py
git commit -m "feat: add Reset Sprint admin action — deletes tasks, clones, docs, outputs, restarts pipeline"
```

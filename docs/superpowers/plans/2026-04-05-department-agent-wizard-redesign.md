# Department & Agent Wizard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give users full visibility and control over which agents are provisioned per department, with Claude providing recommendations rather than making decisions.

**Architecture:** Add `essential` and `controls` fields to BaseBlueprint. Replace `is_active` with a `status` field on Agent. Redesign the wizard to show all departments/agents with Claude's recommendations pre-checked. Add inline agent addition on department pages.

**Tech Stack:** Django REST Framework, Celery, Channels (WebSocket), Next.js/React, TypeScript

---

## File Structure

### Backend — Modified
- `backend/agents/blueprints/base.py` — add `essential`, `controls` to BaseBlueprint
- `backend/agents/blueprints/__init__.py` — add `get_workforce_metadata()` helper
- `backend/agents/blueprints/writers_room/workforce/*/agent.py` — set `essential`/`controls` (6 files)
- `backend/agents/blueprints/engineering/workforce/*/agent.py` — set `essential`/`controls` (5 files)
- `backend/agents/models/agent.py` — replace `is_active` with `status` field
- `backend/agents/serializers/agent_update_serializer.py` — `is_active` → `status`
- `backend/agents/admin/agent_admin.py` — `is_active` → `status`
- `backend/agents/views/agent_view.py` — add `AddAgentView`
- `backend/agents/urls.py` — add route for AddAgentView
- `backend/projects/serializers/project_detail_serializer.py` — `is_active` → `status`
- `backend/projects/views/add_department_view.py` — Claude recommendations in GET, explicit agent selection in POST
- `backend/projects/views/bootstrap_view.py` — apply essential/controls logic
- `backend/projects/tasks.py` — modify `configure_new_department`, add `provision_single_agent`
- `backend/projects/consumers.py` — agent-level WebSocket events

### Backend — New
- `backend/agents/migrations/NNNN_agent_status_field.py` — auto-generated migration

### Backend — Tests
- `backend/agents/tests/test_models.py` — update fixtures and tests for `status`
- `backend/agents/tests/test_views.py` — update fixtures, add AddAgentView tests
- `backend/agents/tests/test_blueprints.py` — test `essential`/`controls` fields, `get_workforce_metadata`
- `backend/projects/tests/test_views.py` — test updated available/add endpoints

### Frontend — Modified
- `frontend/lib/types.ts` — update types
- `frontend/lib/api.ts` — update API methods
- `frontend/components/add-department-wizard.tsx` — full redesign
- `frontend/app/(app)/project/[...path]/page.tsx` — department page: available agents, provisioning states

---

## Task 1: Add `essential` and `controls` to BaseBlueprint

**Files:**
- Modify: `backend/agents/blueprints/base.py:50-58`
- Test: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write failing test for `essential` and `controls` fields**

In `backend/agents/tests/test_blueprints.py`, add:

```python
@pytest.mark.django_db
class TestBlueprintMetadata:
    def test_base_blueprint_defaults(self):
        """BaseBlueprint defaults essential=False and controls=None."""
        from agents.blueprints.marketing.workforce.twitter.agent import TwitterBlueprint

        bp = TwitterBlueprint()
        assert bp.essential is False
        assert bp.controls is None

    def test_essential_field_on_blueprint(self):
        """Blueprints can declare essential=True."""
        from agents.blueprints.writers_room.workforce.format_analyst.agent import FormatAnalystBlueprint

        bp = FormatAnalystBlueprint()
        assert bp.essential is True

    def test_controls_field_string(self):
        """Blueprints can declare controls as a string."""
        from agents.blueprints.writers_room.workforce.market_analyst.agent import MarketAnalystBlueprint

        bp = MarketAnalystBlueprint()
        assert bp.controls == "story_researcher"

    def test_controls_field_list(self):
        """Blueprints can declare controls as a list."""
        from agents.blueprints.engineering.workforce.review_engineer.agent import ReviewEngineerBlueprint

        bp = ReviewEngineerBlueprint()
        assert bp.controls == ["backend_engineer", "frontend_engineer"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_blueprints.py::TestBlueprintMetadata -v`
Expected: FAIL — `essential` and `controls` attributes don't exist

- [ ] **Step 3: Add fields to BaseBlueprint**

In `backend/agents/blueprints/base.py`, add after line 58 (`config_schema`):

```python
    essential: bool = False  # always pre-selected when department is added
    controls: str | list[str] | None = None  # auto-selected when controlled agent is selected
```

- [ ] **Step 4: Set `essential` and `controls` on Writers Room blueprints**

In `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py`, add to the class body:
```python
    controls = "story_researcher"
```

In `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`:
```python
    controls = "story_architect"
```

In `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`:
```python
    controls = "character_designer"
```

In `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`:
```python
    controls = "dialog_writer"
```

In `backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py`:
```python
    essential = True
```

In `backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py`:
```python
    essential = True
```

- [ ] **Step 5: Set `essential` and `controls` on Engineering blueprints**

In `backend/agents/blueprints/engineering/workforce/review_engineer/agent.py`:
```python
    controls = ["backend_engineer", "frontend_engineer"]
```

In `backend/agents/blueprints/engineering/workforce/test_engineer/agent.py`:
```python
    controls = ["backend_engineer", "frontend_engineer"]
```

In `backend/agents/blueprints/engineering/workforce/security_auditor/agent.py`:
```python
    controls = ["backend_engineer", "frontend_engineer"]
```

In `backend/agents/blueprints/engineering/workforce/accessibility_engineer/agent.py`:
```python
    controls = "frontend_engineer"
```

In `backend/agents/blueprints/engineering/workforce/ticket_manager/agent.py`:
```python
    essential = True
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_blueprints.py::TestBlueprintMetadata -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/blueprints/writers_room/ backend/agents/blueprints/engineering/ backend/agents/tests/test_blueprints.py
git commit -m "feat: add essential and controls fields to BaseBlueprint"
```

---

## Task 2: Add `get_workforce_metadata()` helper

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`
- Test: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write failing test**

In `backend/agents/tests/test_blueprints.py`, add:

```python
class TestGetWorkforceMetadata:
    def test_returns_all_agents_with_metadata(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        slugs = {m["agent_type"] for m in metadata}
        # Should include all 10 workforce agents
        assert "dialog_writer" in slugs
        assert "dialogue_analyst" in slugs
        assert "format_analyst" in slugs

    def test_includes_essential_flag(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        by_slug = {m["agent_type"]: m for m in metadata}
        assert by_slug["format_analyst"]["essential"] is True
        assert by_slug["dialog_writer"]["essential"] is False

    def test_includes_controls_field(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        by_slug = {m["agent_type"]: m for m in metadata}
        assert by_slug["market_analyst"]["controls"] == "story_researcher"
        assert by_slug["dialog_writer"]["controls"] is None

    def test_includes_name_and_description(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        for m in metadata:
            assert "name" in m
            assert "description" in m
            assert len(m["name"]) > 0

    def test_unknown_department_returns_empty(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("nonexistent")
        assert metadata == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_blueprints.py::TestGetWorkforceMetadata -v`
Expected: FAIL — `get_workforce_metadata` does not exist

- [ ] **Step 3: Implement `get_workforce_metadata`**

In `backend/agents/blueprints/__init__.py`, add at the end of the file:

```python
def get_workforce_metadata(department_type: str) -> list[dict]:
    """Return all workforce agents for a department with essential/controls metadata."""
    workforce = get_workforce_for_department(department_type)
    if not workforce:
        return []
    return [
        {
            "agent_type": slug,
            "name": bp.name,
            "description": bp.description,
            "essential": bp.essential,
            "controls": bp.controls,
        }
        for slug, bp in workforce.items()
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_blueprints.py::TestGetWorkforceMetadata -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/__init__.py backend/agents/tests/test_blueprints.py
git commit -m "feat: add get_workforce_metadata helper"
```

---

## Task 3: Replace `is_active` with `status` on Agent model

**Files:**
- Modify: `backend/agents/models/agent.py`
- Create: migration (auto-generated)
- Test: `backend/agents/tests/test_models.py`

- [ ] **Step 1: Write failing test for Agent.status**

In `backend/agents/tests/test_models.py`, update the `agent` fixture and add tests. First replace the existing `agent` fixture (lines 37-47):

```python
@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Twitter Bot",
        agent_type="twitter",
        department=department,
        is_leader=False,
        status=Agent.Status.ACTIVE,
        instructions="Be nice",
        config={"api_key": "xxx"},
        auto_actions={"place-content": True, "post-content": False},
    )
```

Replace the `leader_agent` fixture (lines 50-58):

```python
@pytest.fixture
def leader_agent(department):
    return Agent.objects.create(
        name="Department Leader",
        agent_type="leader",
        department=department,
        is_leader=True,
        status=Agent.Status.ACTIVE,
    )
```

Add new tests to `TestAgentModel`:

```python
    def test_status_choices(self, agent):
        assert set(Agent.Status.values) == {"provisioning", "active", "inactive", "failed"}

    def test_default_status_is_provisioning(self, department):
        a = Agent.objects.create(
            name="New Agent",
            agent_type="twitter",
            department=department,
        )
        assert a.status == Agent.Status.PROVISIONING

    def test_status_active(self, agent):
        assert agent.status == Agent.Status.ACTIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_models.py::TestAgentModel::test_status_choices -v`
Expected: FAIL — `Agent.Status` does not exist

- [ ] **Step 3: Update Agent model**

Replace `is_active` field in `backend/agents/models/agent.py` (line 41):

Remove:
```python
    is_active = models.BooleanField(default=False)
```

Add in its place:
```python
    class Status(models.TextChoices):
        PROVISIONING = "provisioning"
        ACTIVE = "active"
        INACTIVE = "inactive"
        FAILED = "failed"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROVISIONING,
        help_text="Agent lifecycle status",
    )
```

- [ ] **Step 4: Generate and customize the migration**

Run: `cd backend && ../venv/bin/python manage.py makemigrations agents`

This should generate a migration that:
1. Adds the `status` field
2. Removes `is_active`

If Django doesn't auto-detect the rename, manually edit the migration to add a `RunPython` step between add and remove:

```python
def migrate_is_active_to_status(apps, schema_editor):
    Agent = apps.get_model("agents", "Agent")
    Agent.objects.filter(is_active=True).update(status="active")
    Agent.objects.filter(is_active=False).update(status="inactive")
```

The migration operations should be ordered:
1. `AddField("status", default="provisioning")`
2. `RunPython(migrate_is_active_to_status)`
3. `RemoveField("is_active")`

- [ ] **Step 5: Run migration**

Run: `cd backend && ../venv/bin/python manage.py migrate agents`

- [ ] **Step 6: Run model tests**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_models.py::TestAgentModel -v`
Expected: PASS (update any remaining `is_active` references in tests — the `test_create_with_all_fields` test needs `assert agent.status == Agent.Status.ACTIVE` instead of `assert agent.is_active is True`)

- [ ] **Step 7: Commit**

```bash
git add backend/agents/models/agent.py backend/agents/migrations/ backend/agents/tests/test_models.py
git commit -m "feat: replace Agent.is_active with status field (provisioning/active/inactive/failed)"
```

---

## Task 4: Update all `is_active` references across the codebase

**Files:**
- Modify: `backend/agents/serializers/agent_update_serializer.py`
- Modify: `backend/agents/admin/agent_admin.py`
- Modify: `backend/agents/views/agent_view.py`
- Modify: `backend/projects/serializers/project_detail_serializer.py`
- Modify: `backend/agents/tasks.py`
- Modify: `backend/agents/tests/test_views.py`
- Modify: `backend/agents/tests/test_serializers.py`
- Modify: All blueprint files that reference `is_active`

This task is a find-and-replace sweep. Run `grep -rn "is_active" backend/ --include="*.py"` to find all references, excluding migrations.

- [ ] **Step 1: Update AgentUpdateSerializer**

In `backend/agents/serializers/agent_update_serializer.py`, change line 9:

```python
        fields = ["instructions", "config", "auto_actions", "status"]
```

- [ ] **Step 2: Update project detail serializer**

In `backend/projects/serializers/project_detail_serializer.py`, change `is_active` to `status` in the `AgentSummarySerializer` fields list (around line 39).

- [ ] **Step 3: Update agent admin**

In `backend/agents/admin/agent_admin.py`, replace `is_active` in `list_display` and `list_filter` with `status`. Update fieldsets to replace `is_active` with `status`.

- [ ] **Step 4: Update agent views**

In `backend/agents/views/agent_view.py`, the `AgentUpdateView` queryset filter may use `is_active` — update any such references.

- [ ] **Step 5: Update blueprint references**

Search all blueprint files for `is_active`. Key files:
- `backend/agents/blueprints/base.py` — `get_context()` method filters `is_active=True` for sibling agents. Change to `status=Agent.Status.ACTIVE` (import Agent or use string `"active"`).
- `backend/agents/blueprints/marketing/leader/agent.py` and similar — any `is_active` references.
- `backend/agents/blueprints/engineering/leader/agent.py` — any `is_active` references.
- `backend/agents/blueprints/writers_room/leader/agent.py` — any `is_active` references.

- [ ] **Step 6: Update tasks.py references**

In `backend/agents/tasks.py`, replace any `is_active` references with `status`. Key places:
- Task execution logic that checks if agent is active
- `configure_new_department` in `backend/projects/tasks.py` — replace `is_active=not needs_config` with `status="active"` or `status="inactive"` based on config needs.

- [ ] **Step 7: Update bootstrap_view.py**

In `backend/projects/views/bootstrap_view.py`, replace `is_active=not leader_needs_config` (line 128) with:
```python
status=Agent.Status.INACTIVE if leader_needs_config else Agent.Status.ACTIVE,
```

Same for workforce agent creation (line 143).

- [ ] **Step 8: Update test fixtures**

In `backend/agents/tests/test_views.py`, update all fixtures that set `is_active=True` to `status=Agent.Status.ACTIVE`:
- `agent` fixture (line 36-43): `status=Agent.Status.ACTIVE` instead of `is_active=True`
- `leader` fixture (line 47-54): same
- `test_patch_updates_is_active` (line 227-235): rename to `test_patch_updates_status`, change to `{"status": "inactive"}`, assert `agent.status == "inactive"`

In `backend/agents/tests/test_serializers.py`, update any `is_active` references.
In `backend/agents/tests/test_tasks.py`, update any `is_active` references.

- [ ] **Step 9: Run full test suite**

Run: `cd backend && ../venv/bin/python -m pytest agents/ projects/ -v`
Expected: All tests PASS with no `is_active` references remaining (except in migrations)

- [ ] **Step 10: Verify no remaining references**

Run: `grep -rn "is_active" backend/ --include="*.py" | grep -v migrations | grep -v venv`
Expected: No output (all references updated)

- [ ] **Step 11: Commit**

```bash
git add -A backend/
git commit -m "refactor: update all is_active references to Agent.status"
```

---

## Task 5: Add recommendation Claude prompt and update `AvailableDepartmentsView`

**Files:**
- Modify: `backend/projects/views/add_department_view.py`
- Modify: `backend/projects/tasks.py` (add recommendation prompt)
- Test: `backend/projects/tests/test_views.py`

- [ ] **Step 1: Write failing test for recommendations in available endpoint**

In `backend/projects/tests/test_views.py`, add:

```python
from unittest.mock import patch


@pytest.mark.django_db
class TestAvailableDepartmentsView:
    def test_returns_departments_with_recommendations(self, authed_client, project):
        mock_response = {
            "departments": ["marketing"],
            "agents": {
                "marketing": ["twitter", "web_researcher"],
            },
        }
        with patch("projects.views.add_department_view.get_department_recommendations") as mock_rec:
            mock_rec.return_value = mock_response
            resp = authed_client.get(f"/api/projects/{project.id}/departments/available/")
        assert resp.status_code == 200
        data = resp.data
        assert "departments" in data
        assert len(data["departments"]) > 0
        dept = data["departments"][0]
        assert "recommended" in dept
        assert "workforce" in dept
        agent = dept["workforce"][0]
        assert "recommended" in agent
        assert "essential" in agent
        assert "controls" in agent

    def test_essential_agents_included_regardless_of_recommendation(self, authed_client, project):
        """Essential agents should be marked even if Claude didn't recommend them."""
        mock_response = {
            "departments": ["engineering"],
            "agents": {"engineering": ["backend_engineer"]},
        }
        with patch("projects.views.add_department_view.get_department_recommendations") as mock_rec:
            mock_rec.return_value = mock_response
            resp = authed_client.get(f"/api/projects/{project.id}/departments/available/")
        assert resp.status_code == 200
        eng = next((d for d in resp.data["departments"] if d["department_type"] == "engineering"), None)
        if eng:
            ticket_mgr = next((a for a in eng["workforce"] if a["agent_type"] == "ticket_manager"), None)
            assert ticket_mgr is not None
            assert ticket_mgr["essential"] is True
```

You'll need to add the standard `user`, `project`, `authed_client` fixtures if they don't exist in this test file — check the existing file first and reuse existing fixtures.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestAvailableDepartmentsView -v`
Expected: FAIL — `get_department_recommendations` doesn't exist

- [ ] **Step 3: Create recommendation prompt and function**

In `backend/projects/tasks.py`, add after line 274 (after `ADD_DEPARTMENT_SYSTEM_PROMPT`):

```python
RECOMMEND_DEPARTMENTS_SYSTEM_PROMPT = """You are a project setup analyst for an AI agent platform. Given a project's context, recommend which departments and agents would be most valuable.

You MUST respond with valid JSON. No markdown, no explanation outside the JSON.

## Rules

1. Only recommend department types and agent types from the AVAILABLE list provided.
2. Consider the project's domain, goals, and existing setup.
3. Focus on creative/production agents — essential and controller agents are auto-included by the system.
4. Leaders are auto-created — do NOT include leaders.

## Response JSON Schema

{
    "departments": ["department_type_slug", ...],
    "agents": {
        "department_type_slug": ["agent_type_slug", ...],
        ...
    }
}"""


def get_department_recommendations(project) -> dict:
    """Call Claude to get department and agent recommendations for a project."""
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.blueprints import DEPARTMENTS, get_workforce_metadata

    # Gather project context
    from projects.models import Source

    sources = Source.objects.filter(project=project)
    sources_summary = ""
    for s in sources:
        text = s.extracted_text or s.raw_content or ""
        if not text:
            continue
        name = s.original_filename or s.url or "Text input"
        snippet = text[:2000]
        if len(text) > 2000:
            snippet += "\n[... truncated ...]"
        sources_summary += f"\n### {name}\n{snippet}\n"

    # Existing departments
    installed = set(project.departments.values_list("department_type", flat=True))

    # Available departments with workforce
    available_text = ""
    for slug, dept in DEPARTMENTS.items():
        if slug in installed:
            continue
        metadata = get_workforce_metadata(slug)
        agents_text = "\n".join(
            f"  - **{m['agent_type']}** ({m['name']}): {m['description']}"
            for m in metadata
        )
        available_text += f"\n### {slug} — {dept['name']}\n{dept['description']}\n{agents_text}\n"

    if not available_text:
        return {"departments": [], "agents": {}}

    user_message = f"""# Project: {project.name}

<project_goal>
{project.goal or "No goal set."}
</project_goal>

## Sources Summary
<sources>
{sources_summary or "No sources available."}
</sources>

## Available Departments and Agents
{available_text}

Recommend which departments and agents to activate. Respond with JSON only."""

    response, _usage = call_claude(
        system_prompt=RECOMMEND_DEPARTMENTS_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=2048,
    )

    result = parse_json_response(response)
    if result is None:
        return {"departments": [], "agents": {}}
    return result
```

- [ ] **Step 4: Rewrite `AvailableDepartmentsView`**

Replace the entire `AvailableDepartmentsView` class in `backend/projects/views/add_department_view.py`:

```python
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.blueprints import DEPARTMENTS, get_department_config_schema, get_workforce_metadata
from projects.models import Department, Project

logger = logging.getLogger(__name__)


def get_department_recommendations(project):
    """Imported from tasks to keep view thin — allows easy mocking in tests."""
    from projects.tasks import get_department_recommendations as _get_recs

    return _get_recs(project)


class AvailableDepartmentsView(APIView):
    """GET /api/projects/{project_id}/departments/available/ — all departments with Claude recommendations."""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        installed = set(project.departments.values_list("department_type", flat=True))

        # Get Claude's recommendations
        try:
            recommendations = get_department_recommendations(project)
        except Exception:
            logger.exception("Failed to get recommendations")
            recommendations = {"departments": [], "agents": {}}

        recommended_depts = set(recommendations.get("departments", []))
        recommended_agents = recommendations.get("agents", {})

        departments = []
        for slug, dept in DEPARTMENTS.items():
            if slug in installed:
                continue
            metadata = get_workforce_metadata(slug)
            rec_agents = set(recommended_agents.get(slug, []))

            workforce = []
            for m in metadata:
                workforce.append(
                    {
                        "agent_type": m["agent_type"],
                        "name": m["name"],
                        "description": m["description"],
                        "recommended": m["agent_type"] in rec_agents,
                        "essential": m["essential"],
                        "controls": m["controls"],
                    }
                )

            departments.append(
                {
                    "department_type": slug,
                    "name": dept["name"],
                    "description": dept["description"],
                    "recommended": slug in recommended_depts,
                    "config_schema": get_department_config_schema(slug),
                    "workforce": workforce,
                }
            )

        return Response({"departments": departments})
```

- [ ] **Step 5: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestAvailableDepartmentsView -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/projects/views/add_department_view.py backend/projects/tasks.py backend/projects/tests/test_views.py
git commit -m "feat: add Claude recommendations to available departments endpoint"
```

---

## Task 6: Update `AddDepartmentView` for explicit agent selection

**Files:**
- Modify: `backend/projects/views/add_department_view.py`
- Modify: `backend/projects/tasks.py`
- Test: `backend/projects/tests/test_views.py`

- [ ] **Step 1: Write failing test for new request format**

In `backend/projects/tests/test_views.py`, add:

```python
@pytest.mark.django_db
class TestAddDepartmentView:
    @patch("projects.tasks.configure_new_department.delay")
    def test_add_department_with_agent_selection(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {
                "departments": [
                    {
                        "department_type": "marketing",
                        "agents": ["twitter", "web_researcher"],
                    }
                ],
                "context": "Test context",
            },
            format="json",
        )
        assert resp.status_code == 202
        assert len(resp.data["departments"]) == 1
        mock_configure.assert_called_once()
        # Verify agents list is passed to the task
        call_args = mock_configure.call_args
        assert call_args[1].get("agents") == ["twitter", "web_researcher"] or \
               (len(call_args[0]) >= 3 and call_args[0][2] == ["twitter", "web_researcher"])

    @patch("projects.tasks.configure_new_department.delay")
    def test_rejects_unknown_department(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {"departments": [{"department_type": "nonexistent", "agents": []}]},
            format="json",
        )
        assert resp.status_code == 400

    @patch("projects.tasks.configure_new_department.delay")
    def test_rejects_empty_departments(self, mock_configure, authed_client, project):
        resp = authed_client.post(
            f"/api/projects/{project.id}/departments/add/",
            {"departments": []},
            format="json",
        )
        assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestAddDepartmentView -v`
Expected: FAIL — old request format expected

- [ ] **Step 3: Rewrite `AddDepartmentView`**

Replace the `AddDepartmentView` class in `backend/projects/views/add_department_view.py`:

```python
class AddDepartmentView(APIView):
    """POST /api/projects/{project_id}/departments/add/ — add departments with explicit agent selection."""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        departments_data = request.data.get("departments", [])
        context = request.data.get("context", "")

        if not departments_data:
            return Response({"error": "departments is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate all department types
        for dept_data in departments_data:
            dt = dept_data.get("department_type")
            if not dt or dt not in DEPARTMENTS:
                return Response(
                    {"error": f"Unknown department type: {dt}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        created = []
        agent_selections = {}
        for dept_data in departments_data:
            dt = dept_data["department_type"]
            if project.departments.filter(department_type=dt).exists():
                continue
            dept = Department.objects.create(project=project, department_type=dt)
            created.append(dept)
            agent_selections[str(dept.id)] = dept_data.get("agents", [])

        if not created:
            return Response(
                {"error": "No new departments to add — all requested are already installed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from projects.tasks import configure_new_department

        for dept in created:
            configure_new_department.delay(
                str(dept.id), context, agent_selections.get(str(dept.id), [])
            )

        return Response(
            {
                "departments": [
                    {"id": str(d.id), "department_type": d.department_type} for d in created
                ],
                "status": "configuring",
            },
            status=status.HTTP_202_ACCEPTED,
        )
```

- [ ] **Step 4: Update `configure_new_department` task signature**

In `backend/projects/tasks.py`, update the task signature to accept an agents list. Change the function signature (around line 329):

```python
@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def configure_new_department(self, department_id: str, context: str = "", selected_agents: list[str] | None = None):
    """Auto-configure a newly added department — create leader + user-selected workforce agents."""
```

Replace the agent creation loop (the section after "Create workforce agents per Claude's recommendations") with:

```python
        # 6. Create workforce agents — use user selection if provided, else Claude's
        agents_to_create = selected_agents if selected_agents else [
            a.get("agent_type", "") for a in result.get("agents", [])
        ]
        instructions_map = {
            a.get("agent_type", ""): a.get("instructions", "")
            for a in result.get("agents", [])
        }

        for agent_type in agents_to_create:
            if agent_type not in workforce:
                logger.warning("Skipping unknown agent type: %s", agent_type)
                continue
            bp = workforce[agent_type]
            needs_config = any(s.get("required") for s in bp.config_schema.values())
            Agent.objects.create(
                name=instructions_map.get(agent_type, {}).get("name", bp.name) if isinstance(instructions_map.get(agent_type), dict) else bp.name,
                agent_type=agent_type,
                department=department,
                is_leader=False,
                status=Agent.Status.INACTIVE if needs_config else Agent.Status.ACTIVE,
                instructions=instructions_map.get(agent_type, ""),
            )
```

Wait — the Claude response still has the old format with name+instructions per agent. Let me simplify: Claude still returns instructions per agent_type, we just don't let it decide which agents to create.

Replace the agent creation section more cleanly:

```python
        # 6. Build instructions map from Claude's response
        instructions_by_type = {}
        names_by_type = {}
        for agent_data in result.get("agents", []):
            at = agent_data.get("agent_type", "")
            instructions_by_type[at] = agent_data.get("instructions", "")
            names_by_type[at] = agent_data.get("name", "")

        # 7. Create workforce agents — user selection takes precedence
        agents_to_create = selected_agents if selected_agents else list(instructions_by_type.keys())

        for agent_type in agents_to_create:
            if agent_type not in workforce:
                logger.warning("Skipping unknown agent type: %s", agent_type)
                continue
            bp = workforce[agent_type]
            needs_config = any(s.get("required") for s in bp.config_schema.values())
            Agent.objects.create(
                name=names_by_type.get(agent_type) or bp.name,
                agent_type=agent_type,
                department=department,
                is_leader=False,
                status=Agent.Status.INACTIVE if needs_config else Agent.Status.ACTIVE,
                instructions=instructions_by_type.get(agent_type, ""),
            )
```

Also update the leader creation to use `status` instead of `is_active`:

```python
            Agent.objects.create(
                name=f"Head of {department.name}",
                agent_type="leader",
                department=department,
                is_leader=True,
                status=Agent.Status.INACTIVE if leader_needs_config else Agent.Status.ACTIVE,
                instructions=f"Lead the {department.name} department for project: {project.name}. Goal: {(project.goal or '')[:200]}",
            )
```

- [ ] **Step 5: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestAddDepartmentView -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/projects/views/add_department_view.py backend/projects/tasks.py backend/projects/tests/test_views.py
git commit -m "feat: add department endpoint accepts explicit agent selection"
```

---

## Task 7: Add `AddAgentView` for single agent provisioning

**Files:**
- Modify: `backend/agents/views/agent_view.py`
- Modify: `backend/agents/urls.py`
- Modify: `backend/projects/tasks.py` (add `provision_single_agent` task)
- Modify: `backend/projects/consumers.py` (add agent events)
- Test: `backend/agents/tests/test_views.py`

- [ ] **Step 1: Write failing test**

In `backend/agents/tests/test_views.py`, add:

```python
@pytest.mark.django_db
class TestAddAgentView:
    @patch("projects.tasks.provision_single_agent.delay")
    def test_add_agent_to_department(self, mock_provision, authed_client, department):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "web_researcher"},
            format="json",
        )
        assert resp.status_code == 202
        assert resp.data["agent_type"] == "web_researcher"
        assert resp.data["status"] == "provisioning"
        mock_provision.assert_called_once()

    @patch("projects.tasks.provision_single_agent.delay")
    def test_rejects_unknown_agent_type(self, mock_provision, authed_client, department):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "nonexistent"},
            format="json",
        )
        assert resp.status_code == 400

    @patch("projects.tasks.provision_single_agent.delay")
    def test_rejects_duplicate_agent(self, mock_provision, authed_client, department, agent):
        resp = authed_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "twitter"},
            format="json",
        )
        assert resp.status_code == 400
        assert "already exists" in resp.data["error"].lower()

    def test_requires_membership(self, api_client, other_user, department):
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(
            "/api/agents/add/",
            {"department_id": str(department.id), "agent_type": "web_researcher"},
            format="json",
        )
        assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_views.py::TestAddAgentView -v`
Expected: FAIL — URL not found

- [ ] **Step 3: Create `AddAgentView`**

In `backend/agents/views/agent_view.py`, add:

```python
from rest_framework import status as http_status


class AddAgentView(APIView):
    """POST /api/agents/add/ — add a single agent to an existing department."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from agents.blueprints import get_workforce_for_department
        from projects.models import Department

        department_id = request.data.get("department_id")
        agent_type = request.data.get("agent_type")

        if not department_id or not agent_type:
            return Response(
                {"error": "department_id and agent_type are required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        department = get_object_or_404(
            Department.objects.select_related("project"),
            id=department_id,
            project__members=request.user,
        )

        workforce = get_workforce_for_department(department.department_type)
        if agent_type not in workforce:
            return Response(
                {"error": f"Unknown agent type '{agent_type}' for department '{department.department_type}'."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        if department.agents.filter(agent_type=agent_type).exists():
            return Response(
                {"error": f"Agent '{agent_type}' already exists in this department."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        bp = workforce[agent_type]
        agent = Agent.objects.create(
            name=bp.name,
            agent_type=agent_type,
            department=department,
            is_leader=False,
            status=Agent.Status.PROVISIONING,
        )

        from projects.tasks import provision_single_agent

        provision_single_agent.delay(str(agent.id))

        return Response(
            {
                "id": str(agent.id),
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": agent.status,
            },
            status=http_status.HTTP_202_ACCEPTED,
        )
```

Add necessary imports at the top of the file:
```python
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
```

- [ ] **Step 4: Add URL route**

In `backend/agents/urls.py`, add:

```python
    path("agents/add/", views.AddAgentView.as_view(), name="agent-add"),
```

- [ ] **Step 5: Create `provision_single_agent` task**

In `backend/projects/tasks.py`, add:

```python
@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def provision_single_agent(self, agent_id: str):
    """Generate tailored instructions for a single agent using Claude."""
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.models import Agent
    from projects.models import Source

    try:
        agent = Agent.objects.select_related("department__project").get(id=agent_id)
    except Agent.DoesNotExist:
        logger.error("Agent %s not found", agent_id)
        return

    department = agent.department
    project = department.project
    bp = agent.get_blueprint()

    _broadcast_agent(project.id, department.id, agent_id, "provisioning")

    try:
        # Gather context
        sources_summary = ""
        for s in Source.objects.filter(project=project):
            text = s.extracted_text or s.raw_content or ""
            if not text:
                continue
            name = s.original_filename or s.url or "Text input"
            snippet = text[:2000]
            if len(text) > 2000:
                snippet += "\n[... truncated ...]"
            sources_summary += f"\n### {name}\n{snippet}\n"

        existing_agents = [
            {"name": a.name, "agent_type": a.agent_type, "instructions": a.instructions[:200]}
            for a in department.agents.exclude(id=agent.id).filter(status=Agent.Status.ACTIVE)
        ]

        user_message = f"""# Project: {project.name}

<project_goal>
{project.goal or "No goal set."}
</project_goal>

## Sources Summary
<sources>
{sources_summary or "No sources available."}
</sources>

## Department: {department.name}

## Existing Agents in Department
{existing_agents}

## Agent to Configure
- Type: {agent.agent_type}
- Name: {bp.name}
- Description: {bp.description}

Generate tailored instructions for this agent. Respond with JSON:
{{"instructions": "specific instructions for this agent...", "name": "Display Name"}}"""

        response, _usage = call_claude(
            system_prompt="You are a project setup analyst. Generate tailored agent instructions based on the project context. Respond with valid JSON only.",
            user_message=user_message,
            max_tokens=1024,
        )

        result = parse_json_response(response)
        if result:
            agent.instructions = result.get("instructions", "")
            if result.get("name"):
                agent.name = result["name"]

        agent.status = Agent.Status.ACTIVE
        agent.save(update_fields=["instructions", "name", "status", "updated_at"])

        _broadcast_agent(project.id, department.id, agent_id, "configured")
        logger.info("Agent %s provisioned for department %s", agent.name, department.name)

    except Exception as e:
        logger.exception("Failed to provision agent %s: %s", agent_id, e)
        agent.status = Agent.Status.FAILED
        agent.save(update_fields=["status", "updated_at"])
        _broadcast_agent(project.id, department.id, agent_id, "failed", str(e)[:200])
```

- [ ] **Step 6: Add `_broadcast_agent` helper**

In `backend/projects/tasks.py`, add after `_broadcast_department`:

```python
def _broadcast_agent(project_id, department_id, agent_id, agent_status, error_message=""):
    """Send agent provisioning status update via WebSocket."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{project_id}",
            {
                "type": "agent.status",
                "agent_id": str(agent_id),
                "department_id": str(department_id),
                "status": agent_status,
                "error_message": error_message,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast agent status")
```

- [ ] **Step 7: Add WebSocket handler in consumer**

In `backend/projects/consumers.py`, add to `ProjectConsumer` class:

```python
    async def agent_status(self, event):
        """Send agent provisioning status update to the client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "agent.status",
                    "agent_id": event.get("agent_id"),
                    "department_id": event.get("department_id"),
                    "status": event.get("status"),
                    "error_message": event.get("error_message", ""),
                }
            )
        )
```

- [ ] **Step 8: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest agents/tests/test_views.py::TestAddAgentView -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/agents/views/agent_view.py backend/agents/urls.py backend/projects/tasks.py backend/projects/consumers.py backend/agents/tests/test_views.py
git commit -m "feat: add single agent provisioning endpoint with WebSocket events"
```

---

## Task 8: Apply essential/controls logic in bootstrap

**Files:**
- Modify: `backend/projects/views/bootstrap_view.py`
- Test: `backend/projects/tests/test_views.py`

- [ ] **Step 1: Write failing test**

In `backend/projects/tests/test_views.py`, add:

```python
@pytest.mark.django_db
class TestBootstrapEssentialAgents:
    def test_apply_proposal_includes_essential_agents(self, user):
        """Bootstrap should add essential agents even if Claude's proposal omits them."""
        from agents.blueprints import get_workforce_for_department
        from projects.models import BootstrapProposal, Department, Project

        project = Project.objects.create(name="Test", goal="Test goal", owner=user)
        project.members.add(user)
        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PROPOSED,
            proposal={
                "summary": "Test",
                "departments": [
                    {
                        "department_type": "engineering",
                        "documents": [],
                        "agents": [
                            {"agent_type": "backend_engineer", "name": "Backend Dev", "instructions": "Build stuff"},
                        ],
                    }
                ],
            },
        )

        from projects.views.bootstrap_view import BootstrapApproveView

        view = BootstrapApproveView()
        view._apply_proposal(proposal)

        dept = Department.objects.get(project=project, department_type="engineering")
        agent_types = set(dept.agents.values_list("agent_type", flat=True))

        # ticket_manager is essential — should be included even though Claude didn't recommend it
        assert "ticket_manager" in agent_types
        # review_engineer controls backend_engineer — should be included
        assert "review_engineer" in agent_types
        # test_engineer controls backend_engineer — should be included
        assert "test_engineer" in agent_types
        # security_auditor controls backend_engineer — should be included
        assert "security_auditor" in agent_types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestBootstrapEssentialAgents -v`
Expected: FAIL — essential agents not created

- [ ] **Step 3: Update `_apply_proposal` in bootstrap_view.py**

In `backend/projects/views/bootstrap_view.py`, update `_apply_proposal` after the workforce agent creation loop. Add after line 145 (after the agent creation for-loop ends):

```python
            # Ensure essential agents and controller agents are included
            created_types = set(department.agents.values_list("agent_type", flat=True))
            created_types.discard("leader")

            from agents.blueprints import get_workforce_metadata

            metadata = get_workforce_metadata(department_type)

            # Add essential agents
            for m in metadata:
                if m["essential"] and m["agent_type"] not in created_types:
                    bp = available_workforce[m["agent_type"]]
                    needs_config = any(s.get("required") for s in bp.config_schema.values())
                    Agent.objects.create(
                        name=bp.name,
                        agent_type=m["agent_type"],
                        department=department,
                        is_leader=False,
                        status=Agent.Status.INACTIVE if needs_config else Agent.Status.ACTIVE,
                    )
                    created_types.add(m["agent_type"])

            # Add controller agents for any created agent
            for m in metadata:
                if not m["controls"]:
                    continue
                controls_list = m["controls"] if isinstance(m["controls"], list) else [m["controls"]]
                if any(c in created_types for c in controls_list) and m["agent_type"] not in created_types:
                    bp = available_workforce[m["agent_type"]]
                    needs_config = any(s.get("required") for s in bp.config_schema.values())
                    Agent.objects.create(
                        name=bp.name,
                        agent_type=m["agent_type"],
                        department=department,
                        is_leader=False,
                        status=Agent.Status.INACTIVE if needs_config else Agent.Status.ACTIVE,
                    )
                    created_types.add(m["agent_type"])
```

Also update the existing agent creation code to use `status` instead of `is_active` and add the `Agent` import with Status:

```python
from agents.models import Agent
```

- [ ] **Step 4: Run tests**

Run: `cd backend && ../venv/bin/python -m pytest projects/tests/test_views.py::TestBootstrapEssentialAgents -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/projects/views/bootstrap_view.py backend/projects/tests/test_views.py
git commit -m "feat: bootstrap applies essential and controls logic for agent provisioning"
```

---

## Task 9: Update frontend types and API client

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Update TypeScript types**

In `frontend/lib/types.ts`, update `AgentSummary` (around line 60):

Replace `is_active: boolean;` with `status: "provisioning" | "active" | "inactive" | "failed";`

Update `AvailableDepartment` (around line 158) — replace the entire interface:

```typescript
export interface AvailableAgent {
  agent_type: string;
  name: string;
  description: string;
  recommended: boolean;
  essential: boolean;
  controls: string | string[] | null;
}

export interface AvailableDepartment {
  department_type: string;
  name: string;
  description: string;
  recommended: boolean;
  config_schema: Record<string, unknown>;
  workforce: AvailableAgent[];
}

export interface AvailableDepartmentsResponse {
  departments: AvailableDepartment[];
}
```

- [ ] **Step 2: Update API client methods**

In `frontend/lib/api.ts`, update `getAvailableDepartments` (around line 211):

```typescript
  getAvailableDepartments: (projectId: string) =>
    request<import("./types").AvailableDepartmentsResponse>(
      `/api/projects/${projectId}/departments/available/`,
    ),
```

Update `addDepartments` (around line 216):

```typescript
  addDepartments: (
    projectId: string,
    data: {
      departments: { department_type: string; agents: string[] }[];
      context?: string;
    },
  ) =>
    request<{ departments: { id: string; department_type: string }[]; status: string }>(
      `/api/projects/${projectId}/departments/add/`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),
```

Add new `addAgent` method:

```typescript
  addAgent: (data: { department_id: string; agent_type: string }) =>
    request<{ id: string; name: string; agent_type: string; status: string }>(
      "/api/agents/add/",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),
```

Update `updateAgent` — replace `is_active` with `status`:

```typescript
  updateAgent: (
    agentId: string,
    data: {
      instructions?: string;
      config?: Record<string, unknown>;
      auto_actions?: Record<string, boolean>;
      status?: string;
    },
  ) => request<unknown>(`/api/agents/${agentId}/`, { method: "PATCH", body: JSON.stringify(data) }),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts frontend/lib/api.ts
git commit -m "feat: update frontend types and API for wizard redesign"
```

---

## Task 10: Redesign the Add Department Wizard

**Files:**
- Modify: `frontend/components/add-department-wizard.tsx`

- [ ] **Step 1: Rewrite the wizard component**

Replace the entire content of `frontend/components/add-department-wizard.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import type { AvailableDepartment, AvailableAgent } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  X,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Building2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Users,
} from "lucide-react";

interface AddDepartmentWizardProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onAdded: () => void;
}

/** Compute the full pre-selected agent set given recommendations + essential + controls logic. */
function computePreselected(
  dept: AvailableDepartment,
  recommendedAgents: Set<string>,
): Set<string> {
  const selected = new Set(recommendedAgents);

  // Add essential agents
  for (const a of dept.workforce) {
    if (a.essential) selected.add(a.agent_type);
  }

  // Add controller agents for any selected agent
  for (const a of dept.workforce) {
    if (!a.controls) continue;
    const controlsList = Array.isArray(a.controls) ? a.controls : [a.controls];
    if (controlsList.some((c) => selected.has(c))) {
      selected.add(a.agent_type);
    }
  }

  return selected;
}

/** Check if an agent is essential or a controller for currently selected agents. */
function getAgentWarning(
  agent: AvailableAgent,
  allAgents: AvailableAgent[],
  selectedAgents: Set<string>,
): string | null {
  if (agent.essential) {
    return "This agent is essential for this department. Removing it may reduce quality.";
  }
  if (agent.controls) {
    const controlsList = Array.isArray(agent.controls) ? agent.controls : [agent.controls];
    const controlledNames = controlsList
      .filter((c) => selectedAgents.has(c))
      .map((c) => allAgents.find((a) => a.agent_type === c)?.name ?? c);
    if (controlledNames.length > 0) {
      return `This agent reviews ${controlledNames.join(", ")}. Removing it weakens the feedback loop.`;
    }
  }
  return null;
}

export function AddDepartmentWizard({
  projectId,
  isOpen,
  onClose,
  onAdded,
}: AddDepartmentWizardProps) {
  const [step, setStep] = useState(1);
  const [departments, setDepartments] = useState<AvailableDepartment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [context, setContext] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  // Selection state: which departments are checked
  const [selectedDepts, setSelectedDepts] = useState<Set<string>>(new Set());
  // Which departments are expanded (showing agents)
  const [expandedDepts, setExpandedDepts] = useState<Set<string>>(new Set());
  // Per-department agent selections
  const [agentSelections, setAgentSelections] = useState<Record<string, Set<string>>>({});
  // Warning dismissals
  const [dismissedWarnings, setDismissedWarnings] = useState<Set<string>>(new Set());

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Fetch available departments with recommendations
  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setError("");
    api
      .getAvailableDepartments(projectId)
      .then((resp) => {
        const depts = resp.departments;
        setDepartments(depts);

        // Pre-select recommended departments
        const recDepts = new Set(depts.filter((d) => d.recommended).map((d) => d.department_type));
        setSelectedDepts(recDepts);
        setExpandedDepts(new Set(recDepts));

        // Pre-select agents per department using selection logic
        const selections: Record<string, Set<string>> = {};
        for (const dept of depts) {
          const recAgents = new Set(
            dept.workforce.filter((a) => a.recommended).map((a) => a.agent_type),
          );
          selections[dept.department_type] = computePreselected(dept, recAgents);
        }
        setAgentSelections(selections);
      })
      .catch(() => setError("Failed to load departments"))
      .finally(() => setLoading(false));
  }, [isOpen, projectId]);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setContext("");
      setSubmitting(false);
      setError("");
      setDismissedWarnings(new Set());
    }
    return () => closeWs();
  }, [isOpen, closeWs]);

  function toggleDepartment(dt: string) {
    setSelectedDepts((prev) => {
      const next = new Set(prev);
      if (next.has(dt)) {
        next.delete(dt);
        setExpandedDepts((e) => {
          const ne = new Set(e);
          ne.delete(dt);
          return ne;
        });
      } else {
        next.add(dt);
        setExpandedDepts((e) => new Set(e).add(dt));
      }
      return next;
    });
  }

  function toggleExpand(dt: string) {
    if (!selectedDepts.has(dt)) return;
    setExpandedDepts((prev) => {
      const next = new Set(prev);
      if (next.has(dt)) next.delete(dt);
      else next.add(dt);
      return next;
    });
  }

  function toggleAgent(deptType: string, agentType: string) {
    setAgentSelections((prev) => {
      const current = new Set(prev[deptType] || new Set());
      const dept = departments.find((d) => d.department_type === deptType);
      if (!dept) return prev;

      if (current.has(agentType)) {
        current.delete(agentType);
        // If deselecting a controlled agent, check if we should warn about its controller
      } else {
        current.add(agentType);
        // Auto-add controller agents
        for (const a of dept.workforce) {
          if (!a.controls) continue;
          const controlsList = Array.isArray(a.controls) ? a.controls : [a.controls];
          if (controlsList.includes(agentType) && !current.has(a.agent_type)) {
            current.add(a.agent_type);
          }
        }
      }

      return { ...prev, [deptType]: current };
    });
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      const deptPayload = Array.from(selectedDepts).map((dt) => ({
        department_type: dt,
        agents: Array.from(agentSelections[dt] || new Set()),
      }));

      await api.addDepartments(projectId, {
        departments: deptPayload,
        context: context.trim() || undefined,
      });

      try {
        const { connectWs } = await import("@/lib/ws");
        const ws = await connectWs(`/ws/project/${projectId}/`, (data) => {
          if ((data.type as string) === "department.configured") {
            closeWs();
            onAdded();
            onClose();
          }
        });
        wsRef.current = ws;
      } catch {
        // WS fallback
      }

      setTimeout(() => {
        onAdded();
        onClose();
      }, 5000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add departments");
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-bg-primary border border-border rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[min(700px,90vh)]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-accent-gold" />
            <span className="text-sm font-medium text-text-heading">
              {step === 1 ? "Add Departments" : "Additional Context"}
            </span>
            <span className="text-xs text-text-secondary">Step {step} of 2</span>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="flex items-center gap-2 text-flag-critical text-sm mb-4 p-3 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {step === 1 && (
            <>
              {loading ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <Loader2 className="h-5 w-5 text-text-secondary animate-spin" />
                  <p className="text-xs text-text-secondary">Getting recommendations...</p>
                </div>
              ) : departments.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <CheckCircle2 className="h-10 w-10 text-flag-strength/60" />
                  <p className="text-sm text-text-secondary">
                    All departments are already installed
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {departments.map((dept) => {
                    const isSelected = selectedDepts.has(dept.department_type);
                    const isExpanded = expandedDepts.has(dept.department_type);
                    const selectedCount = agentSelections[dept.department_type]?.size ?? 0;

                    return (
                      <div
                        key={dept.department_type}
                        className={`rounded-lg border transition-colors ${
                          isSelected
                            ? "border-accent-gold bg-accent-gold/5"
                            : "border-border bg-bg-surface"
                        }`}
                      >
                        {/* Department header */}
                        <button
                          onClick={() => toggleDepartment(dept.department_type)}
                          className="w-full text-left p-4 flex items-center gap-3"
                        >
                          <div
                            className={`h-5 w-5 rounded border flex items-center justify-center shrink-0 transition-colors ${
                              isSelected
                                ? "bg-accent-gold border-accent-gold"
                                : "border-border bg-bg-input"
                            }`}
                          >
                            {isSelected && (
                              <CheckCircle2 className="h-3.5 w-3.5 text-bg-primary" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-text-heading">
                                {dept.name}
                              </p>
                              {dept.recommended && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-gold/10 text-accent-gold font-medium">
                                  Recommended
                                </span>
                              )}
                            </div>
                            {dept.description && (
                              <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">
                                {dept.description}
                              </p>
                            )}
                          </div>
                          {isSelected && (
                            <div className="flex items-center gap-2 shrink-0">
                              <span className="text-[10px] text-text-secondary">
                                {selectedCount}/{dept.workforce.length} agents
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleExpand(dept.department_type);
                                }}
                                className="text-text-secondary hover:text-text-primary"
                              >
                                {isExpanded ? (
                                  <ChevronUp className="h-4 w-4" />
                                ) : (
                                  <ChevronDown className="h-4 w-4" />
                                )}
                              </button>
                            </div>
                          )}
                        </button>

                        {/* Agent list (expanded) */}
                        {isSelected && isExpanded && (
                          <div className="px-4 pb-4 pt-0 border-t border-border/50">
                            <div className="flex items-center gap-2 mt-3 mb-2">
                              <Users className="h-3.5 w-3.5 text-text-secondary" />
                              <span className="text-xs font-medium text-text-secondary uppercase">
                                Agents
                              </span>
                            </div>
                            <div className="space-y-1">
                              {dept.workforce.map((agent) => {
                                const agentSelected =
                                  agentSelections[dept.department_type]?.has(agent.agent_type) ??
                                  false;
                                const warning = !agentSelected
                                  ? null
                                  : null; // warning only shows on deselect attempt
                                const deselectedWarning =
                                  !agentSelected &&
                                  !dismissedWarnings.has(
                                    `${dept.department_type}:${agent.agent_type}`,
                                  )
                                    ? getAgentWarning(
                                        agent,
                                        dept.workforce,
                                        agentSelections[dept.department_type] || new Set(),
                                      )
                                    : null;

                                return (
                                  <div key={agent.agent_type}>
                                    <button
                                      onClick={() =>
                                        toggleAgent(dept.department_type, agent.agent_type)
                                      }
                                      className={`w-full text-left rounded-md px-3 py-2 flex items-start gap-2.5 transition-colors ${
                                        agentSelected
                                          ? "bg-bg-primary"
                                          : "bg-bg-surface/50 opacity-60"
                                      }`}
                                    >
                                      <div
                                        className={`mt-0.5 h-4 w-4 rounded border flex items-center justify-center shrink-0 transition-colors ${
                                          agentSelected
                                            ? "bg-accent-gold border-accent-gold"
                                            : "border-border bg-bg-input"
                                        }`}
                                      >
                                        {agentSelected && (
                                          <CheckCircle2 className="h-2.5 w-2.5 text-bg-primary" />
                                        )}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                          <span className="text-xs font-medium text-text-primary">
                                            {agent.name}
                                          </span>
                                          {agent.essential && (
                                            <span className="text-[9px] px-1 py-0.5 rounded bg-flag-strength/10 text-flag-strength font-medium">
                                              Essential
                                            </span>
                                          )}
                                          {agent.controls && (
                                            <span className="text-[9px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400 font-medium">
                                              Reviews{" "}
                                              {Array.isArray(agent.controls)
                                                ? agent.controls
                                                    .map(
                                                      (c) =>
                                                        dept.workforce.find(
                                                          (w) => w.agent_type === c,
                                                        )?.name ?? c,
                                                    )
                                                    .join(", ")
                                                : dept.workforce.find(
                                                    (w) => w.agent_type === agent.controls,
                                                  )?.name ?? agent.controls}
                                            </span>
                                          )}
                                          {agent.recommended && (
                                            <span className="text-[9px] px-1 py-0.5 rounded bg-accent-gold/10 text-accent-gold font-medium">
                                              Recommended
                                            </span>
                                          )}
                                        </div>
                                        <p className="text-[11px] text-text-secondary mt-0.5 line-clamp-1">
                                          {agent.description}
                                        </p>
                                      </div>
                                    </button>
                                    {deselectedWarning && (
                                      <div className="flex items-start gap-2 ml-6 mt-1 mb-1 p-2 rounded bg-flag-caution/10 text-flag-caution text-[11px]">
                                        <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
                                        <span>{deselectedWarning}</span>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-text-secondary mb-3">
                  Adding:{" "}
                  {Array.from(selectedDepts)
                    .map(
                      (dt) =>
                        departments.find((d) => d.department_type === dt)?.name ?? dt,
                    )
                    .join(", ")}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-text-heading block mb-2">
                  Any specific context for these departments?
                </label>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="e.g., We're launching a new product next month..."
                  rows={4}
                  className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-sm text-text-primary placeholder:text-text-secondary/50 outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-none"
                />
                <p className="text-[10px] text-text-secondary mt-1">
                  Optional — helps tailor the department setup to your needs.
                </p>
              </div>

              {submitting && (
                <div className="flex items-center gap-3 p-4 rounded-lg bg-accent-gold/5 border border-accent-gold/20">
                  <Loader2 className="h-4 w-4 text-accent-gold animate-spin" />
                  <span className="text-sm text-text-primary">Configuring departments...</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border shrink-0">
          {step === 1 && (
            <div className="flex justify-end">
              <Button
                onClick={() => setStep(2)}
                disabled={selectedDepts.size === 0}
                className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
              >
                Next
              </Button>
            </div>
          )}
          {step === 2 && (
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                disabled={submitting}
                className="border-border text-text-secondary hover:text-text-primary"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting}
                className="bg-accent-gold text-bg-primary hover:bg-accent-gold-hover disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                    Configuring...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                    Add Departments
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/add-department-wizard.tsx
git commit -m "feat: redesign wizard with department+agent selection and Claude recommendations"
```

---

## Task 11: Add available agents section to department page

**Files:**
- Modify: `frontend/app/(app)/project/[...path]/page.tsx`

- [ ] **Step 1: Update `is_active` references to `status` across the page**

Search for `is_active` in the file and replace with `status` checks. Key changes:
- Agent active badge: `a.is_active` → `a.status === "active"`
- Any filtering by active status

- [ ] **Step 2: Add available agents section to `DepartmentView`**

In `frontend/app/(app)/project/[...path]/page.tsx`, update `DepartmentView` function. After the workforce grid (after line 685), add the available agents section. The component needs to:

1. Fetch the available departments endpoint to get unprovisioned agents for this department type
2. Show "Available Agents" section with agents not yet provisioned
3. Handle the "Add" button click with provisioning state

Add this inside the `DepartmentView` function body, before the return:

```tsx
  const [availableAgents, setAvailableAgents] = useState<
    { agent_type: string; name: string; description: string; essential: boolean; controls: string | string[] | null }[]
  >([]);
  const [provisioningAgents, setProvisioningAgents] = useState<Set<string>>(new Set());
  const [loadingAvailable, setLoadingAvailable] = useState(true);

  useEffect(() => {
    api
      .getAvailableDepartments(projectId)
      .then((resp) => {
        const thisDept = resp.departments.find(
          (d) => d.department_type === dept.department_type,
        );
        if (!thisDept) {
          // Department is installed — get agent metadata from the available endpoint
          // We need to compare against installed agents
          setAvailableAgents([]);
          return;
        }
        // Filter out already-provisioned agents
        const provisionedTypes = new Set(dept.agents.map((a) => a.agent_type));
        setAvailableAgents(
          thisDept.workforce
            .filter((a) => !provisionedTypes.has(a.agent_type))
            .map((a) => ({
              agent_type: a.agent_type,
              name: a.name,
              description: a.description,
              essential: a.essential,
              controls: a.controls,
            })),
        );
      })
      .catch(() => setAvailableAgents([]))
      .finally(() => setLoadingAvailable(false));
  }, [projectId, dept]);

  async function handleAddAgent(agentType: string) {
    setProvisioningAgents((prev) => new Set(prev).add(agentType));
    try {
      await api.addAgent({ department_id: dept.id, agent_type: agentType });
      // Agent will appear via page refresh or WS update
    } catch {
      setProvisioningAgents((prev) => {
        const next = new Set(prev);
        next.delete(agentType);
        return next;
      });
    }
  }
```

Wait — the available departments endpoint only returns departments NOT installed. For an installed department, we can't use it to get unprovisioned agents. We need a different approach.

Better approach: the department page should call a new lightweight endpoint, OR we can compute it client-side by comparing the full blueprint agent list against provisioned agents. Since the blueprint info is available per-agent, we'd need a way to get all blueprint agent types for a department.

Simpler solution: modify the `AvailableDepartmentsView` to also return installed departments' unprovisioned agents, OR add a separate endpoint. But let's keep it simple — add a new parameter to the existing endpoint: `?include_installed=true` returns all departments including installed ones but marks them. Actually that overcomplicates things.

Simplest: add a new endpoint `GET /api/projects/{project_id}/departments/{dept_id}/available-agents/` that returns unprovisioned agents for an installed department.

Add to `backend/projects/views/add_department_view.py`:

```python
class AvailableAgentsView(APIView):
    """GET /api/projects/{project_id}/departments/{dept_id}/available-agents/"""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, dept_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        department = get_object_or_404(Department, id=dept_id, project=project)
        metadata = get_workforce_metadata(department.department_type)
        provisioned = set(department.agents.values_list("agent_type", flat=True))

        available = [
            m for m in metadata if m["agent_type"] not in provisioned
        ]
        return Response({"agents": available})
```

Add URL in `backend/projects/urls.py`:
```python
    path(
        "projects/<uuid:project_id>/departments/<uuid:dept_id>/available-agents/",
        views.AvailableAgentsView.as_view(),
        name="department-available-agents",
    ),
```

Add API method in `frontend/lib/api.ts`:
```typescript
  getAvailableAgents: (projectId: string, deptId: string) =>
    request<{ agents: import("./types").AvailableAgent[] }>(
      `/api/projects/${projectId}/departments/${deptId}/available-agents/`,
    ),
```

Now update the `DepartmentView` to use this endpoint:

```tsx
  const [availableAgents, setAvailableAgents] = useState<
    { agent_type: string; name: string; description: string; essential: boolean; controls: string | string[] | null }[]
  >([]);
  const [provisioningAgents, setProvisioningAgents] = useState<Set<string>>(new Set());

  useEffect(() => {
    api
      .getAvailableAgents(projectId, dept.id)
      .then((resp) => setAvailableAgents(resp.agents))
      .catch(() => setAvailableAgents([]));
  }, [projectId, dept.id, dept.agents.length]);

  async function handleAddAgent(agentType: string) {
    setProvisioningAgents((prev) => new Set(prev).add(agentType));
    try {
      await api.addAgent({ department_id: dept.id, agent_type: agentType });
    } catch {
      setProvisioningAgents((prev) => {
        const next = new Set(prev);
        next.delete(agentType);
        return next;
      });
    }
  }
```

Then in the return JSX, after the workforce grid and before the Separator, add:

```tsx
      {availableAgents.length > 0 && (
        <>
          <Separator className="my-6" />
          <h3 className="text-xs uppercase text-text-secondary font-medium mb-3">
            Available Agents
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
            {availableAgents.map((agent) => {
              const isProvisioning = provisioningAgents.has(agent.agent_type);
              return (
                <div
                  key={agent.agent_type}
                  className="rounded-xl border border-dashed border-border/60 bg-bg-surface/30 p-4 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-secondary">
                      {agent.name}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {agent.essential && (
                        <span className="text-[9px] px-1 py-0.5 rounded bg-flag-strength/10 text-flag-strength font-medium">
                          Essential
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-[11px] text-text-secondary line-clamp-2">
                    {agent.description}
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={isProvisioning}
                    onClick={() => handleAddAgent(agent.agent_type)}
                    className="mt-auto text-xs border-border hover:border-accent-gold hover:text-accent-gold"
                  >
                    {isProvisioning ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Adding...
                      </>
                    ) : (
                      <>
                        <Plus className="h-3 w-3 mr-1" />
                        Add
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        </>
      )}
```

- [ ] **Step 3: Add WebSocket listener for agent status events**

In the main page component, add a handler for `agent.status` WebSocket events that triggers a project detail refresh when an agent is configured. This should be in the existing WebSocket setup (look for where `task.updated` is handled).

- [ ] **Step 4: Commit**

```bash
git add backend/projects/views/add_department_view.py backend/projects/urls.py frontend/lib/api.ts frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: add available agents section to department page with inline provisioning"
```

---

## Task 12: Update `is_active` references in frontend

**Files:**
- Modify: `frontend/app/(app)/project/[...path]/page.tsx`

- [ ] **Step 1: Find and replace `is_active` references**

Search the page.tsx file for all `is_active` references. Replace each with the appropriate `status` check:
- `agent.is_active` → `agent.status === "active"`
- `is_active: true/false` in API calls → `status: "active"` / `status: "inactive"`
- Toggle rendering: where a toggle switches `is_active`, change to toggle between `"active"` and `"inactive"` status

Also add visual handling for `provisioning` and `failed` states on agent cards — a provisioning agent should show a pulse/spinner, a failed agent should show an error indicator.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "refactor: update frontend is_active references to agent status field"
```

---

## Task 13: Run full test suite and verify

- [ ] **Step 1: Run backend tests**

Run: `cd backend && ../venv/bin/python -m pytest agents/ projects/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Check for remaining `is_active` references**

Run: `grep -rn "is_active" backend/ --include="*.py" | grep -v migrations | grep -v venv`
Expected: No output

Run: `grep -rn "is_active" frontend/ --include="*.ts" --include="*.tsx" | grep -v node_modules`
Expected: No output

- [ ] **Step 3: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: resolve remaining issues from wizard redesign"
```

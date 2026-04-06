# Writers Room Output Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three bugs: revision patches not applying, feedback agents critiquing raw creative work instead of the deliverable, and sprint output showing only the deliverable.

**Architecture:** Four targeted changes — fix the lead_writer revision prompt, add a `WritersRoomFeedbackBlueprint` base class that strips sibling reports, update the Output unique constraint to `(sprint, department, label)`, and update the leader to create three Output records per cycle.

**Tech Stack:** Django, Python, pytest

---

### Task 1: Fix lead_writer revision prompt

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write the failing test**

Add to `test_writers_room_lead_writer.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestLeadWriterRevisionPrompt -v
```

Expected: FAIL — assertions on missing text.

- [ ] **Step 3: Update the revision step_plan in `_propose_lead_writer_task`**

In `backend/agents/blueprints/writers_room/leader/agent.py`, find the `if iteration > 0:` block (around line 990). Replace the `step_plan` assignment with:

```python
            step_plan = (
                f"Locale: {locale}\nFormat: {format_type}\nStage: {stage_display}\n"
                f"Round: {iteration + 1} (REVISION)\n\n"
                "## REVISION MODE\n"
                "The current Stage Deliverable and the Critique are in the department documents. "
                "Your job is to REVISE the existing deliverable, NOT rewrite it.\n\n"
                "Output your changes as revision JSON.\n\n"
                "OUTPUT FORMAT — CRITICAL:\n"
                "Output ONLY the JSON revision object. No preamble, no explanation, no prose. "
                "Your response must start with `{` and end with `}`. Nothing before or after.\n\n"
                "```json\n"
                "{\n"
                '  "revisions": [\n'
                '    {"type": "replace", "old_text": "exact text from document", '
                '"new_text": "revised text"},\n'
                '    {"type": "replace_section", "section": "## Section Header", '
                '"new_content": "new section content"},\n'
                '    {"type": "replace_between", "start": "unique start anchor", '
                '"end": "unique end anchor", "new_content": "new content"}\n'
                "  ],\n"
                '  "preserved": "Brief note on what was deliberately kept and why"\n'
                "}\n"
                "```\n\n"
                f"{ops_note}\n\n"
                "RULES:\n"
                "- Quote old_text EXACTLY from the existing document — character for character\n"
                "- Quote enough context for uniqueness (if old_text matches multiple times, the edit fails)\n"
                "- For replace_section, use the exact markdown header from the document\n"
                "- For replace_between, quote unique start and end anchor passages\n"
                "- ONLY change what the Critique flagged. Everything else stays BYTE-IDENTICAL.\n"
                "- If the Critique praised a section, do NOT touch it.\n\n"
                "If the critique praises material not yet present in the deliverable, check the "
                "stage research document — it contains the raw creative work. You may incorporate "
                "it if it serves the story, but the creative decision is yours.\n\n"
                "Read the Critique carefully. Address EVERY flagged issue. Preserve EVERYTHING praised.\n\n"
                f"Your output must be in {locale}."
            )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestLeadWriterRevisionPrompt -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "fix(writers-room): lead_writer revision prompt outputs JSON only"
```

---

### Task 2: Add WritersRoomFeedbackBlueprint

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/base.py`
- Test: `backend/agents/tests/test_writers_room_feedback_blueprint.py` (new)

- [ ] **Step 1: Write the failing test**

Create `backend/agents/tests/test_writers_room_feedback_blueprint.py`:

```python
"""Tests for WritersRoomFeedbackBlueprint context scoping."""
from unittest.mock import MagicMock, patch

import pytest


class TestWritersRoomFeedbackBlueprint:
    def test_blueprint_exists(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
        assert WritersRoomFeedbackBlueprint is not None

    def test_inherits_workforce_blueprint(self):
        from agents.blueprints.base import WorkforceBlueprint
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
        assert issubclass(WritersRoomFeedbackBlueprint, WorkforceBlueprint)

    def test_get_context_strips_sibling_reports(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "## dialogue_writer\n  - [done] Write scenes\n    Report: <long dialogue>",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "long dialogue" not in ctx["sibling_agents"]
        assert "Stage Deliverable" in ctx["sibling_agents"]

    def test_department_documents_preserved(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "some reports",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert ctx["department_documents"] == "--- [stage_deliverable] Expose v1 ---\ncontent"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_feedback_blueprint.py -v
```

Expected: FAIL — `WritersRoomFeedbackBlueprint` does not exist.

- [ ] **Step 3: Create `backend/agents/blueprints/writers_room/workforce/base.py`**

```python
"""Shared base class for Writers Room feedback agents."""
from agents.blueprints.base import WorkforceBlueprint


class WritersRoomFeedbackBlueprint(WorkforceBlueprint):
    """Base for all Writers Room feedback/review agents.

    Overrides get_context() to strip sibling task reports — feedback agents
    analyse the synthesised Stage Deliverable document only, not raw creative
    fragments from individual creative agents.
    """

    def get_context(self, agent):
        ctx = super().get_context(agent)
        ctx["sibling_agents"] = (
            "Sibling task reports are not available to feedback agents. "
            "Focus your analysis exclusively on the Stage Deliverable document above."
        )
        return ctx
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_feedback_blueprint.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/base.py backend/agents/tests/test_writers_room_feedback_blueprint.py
git commit -m "feat(writers-room): add WritersRoomFeedbackBlueprint with scoped context"
```

---

### Task 3: Update feedback agents to inherit WritersRoomFeedbackBlueprint

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`
- Test: `backend/agents/tests/test_writers_room_feedback_blueprint.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/agents/tests/test_writers_room_feedback_blueprint.py`:

```python
class TestFeedbackAgentInheritance:
    @pytest.mark.parametrize("agent_type", [
        "market_analyst",
        "structure_analyst",
        "character_analyst",
        "dialogue_analyst",
        "format_analyst",
        "production_analyst",
        "creative_reviewer",
    ])
    def test_inherits_feedback_blueprint(self, agent_type):
        from agents.blueprints import get_blueprint
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = get_blueprint(agent_type, "writers_room")
        assert isinstance(bp, WritersRoomFeedbackBlueprint), (
            f"{agent_type} must inherit WritersRoomFeedbackBlueprint"
        )
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_feedback_blueprint.py::TestFeedbackAgentInheritance -v
```

Expected: FAIL for all 7 agents.

- [ ] **Step 3: Update each agent's import and base class**

For each of the 7 files, replace:
```python
from agents.blueprints.base import WorkforceBlueprint
```
with:
```python
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
```

And replace `(WorkforceBlueprint)` with `(WritersRoomFeedbackBlueprint)` in the class definition.

`market_analyst/agent.py` — change:
```python
from agents.blueprints.base import WorkforceBlueprint
...
class MarketAnalystBlueprint(WorkforceBlueprint):
```
to:
```python
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
...
class MarketAnalystBlueprint(WritersRoomFeedbackBlueprint):
```

Repeat for `structure_analyst`, `character_analyst`, `dialogue_analyst`, `format_analyst`, `production_analyst`, `creative_reviewer`. Same two-line change in each.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_feedback_blueprint.py -v
```

Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py \
        backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py \
        backend/agents/tests/test_writers_room_feedback_blueprint.py
git commit -m "fix(writers-room): feedback agents inherit WritersRoomFeedbackBlueprint"
```

---

### Task 4: Update Output unique constraint

**Files:**
- Modify: `backend/projects/models/output.py`
- Create: `backend/projects/migrations/0023_output_unique_by_label.py`
- Modify: `backend/projects/tests/test_output.py`

- [ ] **Step 1: Write the failing tests**

In `backend/projects/tests/test_output.py`, replace the existing `TestOutputConstraints` class with:

```python
class TestOutputConstraints:
    @pytest.mark.django_db
    def test_two_outputs_same_label_rejected(self):
        """Two outputs with the same (sprint, department, label) must fail."""
        from django.contrib.auth import get_user_model
        from projects.models import Department, Project, Sprint

        User = get_user_model()
        user = User.objects.create_user(email="test2@test.com", password="test")
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        sprint = Sprint.objects.create(project=project, text="Write a pitch", created_by=user)
        sprint.departments.add(dept)

        Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="v1")

        with pytest.raises(IntegrityError):
            Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="v2")

    @pytest.mark.django_db
    def test_three_outputs_different_labels_allowed(self):
        """Three outputs with different labels for same sprint+dept must succeed."""
        from django.contrib.auth import get_user_model
        from projects.models import Department, Project, Sprint

        User = get_user_model()
        user = User.objects.create_user(email="test3@test.com", password="test")
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(project=project, department_type="writers_room")
        sprint = Sprint.objects.create(project=project, text="Write a pitch", created_by=user)
        sprint.departments.add(dept)

        Output.objects.create(sprint=sprint, department=dept, title="Expose Deliverable", label="expose:deliverable", output_type="markdown", content="d")
        Output.objects.create(sprint=sprint, department=dept, title="Expose Critique", label="expose:critique", output_type="markdown", content="c")
        Output.objects.create(sprint=sprint, department=dept, title="Expose Research", label="expose:research", output_type="markdown", content="r")

        assert Output.objects.filter(sprint=sprint, department=dept).count() == 3
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest projects/tests/test_output.py::TestOutputConstraints -v
```

Expected: `test_three_outputs_different_labels_allowed` FAILS with IntegrityError (old constraint blocks it).

- [ ] **Step 3: Update the Output model constraint**

In `backend/projects/models/output.py`, replace the `Meta` class:

```python
    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sprint", "department", "label"],
                name="one_output_per_department_per_sprint_per_label",
            ),
        ]
```

- [ ] **Step 4: Generate and apply the migration**

```bash
cd backend && python manage.py makemigrations projects --name output_unique_by_label
python manage.py migrate
```

Expected: new migration file created and applied without errors.

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd backend && python -m pytest projects/tests/test_output.py -v
```

Expected: PASS all.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/models/output.py backend/projects/tests/test_output.py
git add backend/projects/migrations/
git commit -m "feat(output): unique constraint on (sprint, department, label)"
```

---

### Task 5: Leader creates three Output records

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
class TestUpdateSprintOutput:
    def test_update_sprint_output_uses_label_with_type(self):
        """_update_sprint_output must include output_type in the label."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
        from unittest.mock import MagicMock, patch

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.internal_state = {"format_type": "standalone"}
        sprint = MagicMock()

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content", "deliverable")
            call_kwargs = mock_uoc.call_args
            assert call_kwargs.kwargs["label"] == "expose:deliverable" or \
                   call_kwargs[1]["label"] == "expose:deliverable" or \
                   "expose:deliverable" in str(call_kwargs)

    def test_update_sprint_output_critique_label(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
        from unittest.mock import MagicMock, patch

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.internal_state = {"format_type": "standalone"}
        sprint = MagicMock()

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content", "critique")
            call_kwargs = mock_uoc.call_args
            assert "expose:critique" in str(call_kwargs)

    def test_update_sprint_output_default_is_deliverable(self):
        """output_type defaults to 'deliverable' for backwards compatibility."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
        from unittest.mock import MagicMock, patch

        bp = WritersRoomLeaderBlueprint()
        agent = MagicMock()
        agent.internal_state = {"format_type": "standalone"}
        sprint = MagicMock()

        with patch("projects.models.Output.objects.update_or_create") as mock_uoc:
            bp._update_sprint_output(agent, sprint, "expose", "content")
            call_kwargs = mock_uoc.call_args
            assert "expose:deliverable" in str(call_kwargs)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestUpdateSprintOutput -v
```

Expected: FAIL — `_update_sprint_output` doesn't accept `output_type`.

- [ ] **Step 3: Update `_update_sprint_output` in `leader/agent.py`**

Replace the existing `_update_sprint_output` method (around line 1175):

```python
    def _update_sprint_output(self, agent, sprint, stage: str, content: str, output_type: str = "deliverable"):
        """Update or create a sprint output record for this department.

        Label format: {effective_stage}:{output_type}
        e.g. "expose:deliverable", "expose:critique", "expose:research"
        """
        from projects.models import Output

        effective_stage = self._get_effective_stage(agent, stage)
        stage_display = effective_stage.replace("_", " ").title()
        type_display = output_type.title()
        label = f"{effective_stage}:{output_type}"

        Output.objects.update_or_create(
            sprint=sprint,
            department=agent.department,
            label=label,
            defaults={
                "title": f"{stage_display} {type_display}",
                "output_type": "markdown",
                "content": content,
            },
        )
```

- [ ] **Step 4: Update `_create_deliverable_and_research_docs` to emit research output**

Find the call to `_update_sprint_output` near line 1173 (inside `_create_deliverable_and_research_docs`). Replace:

```python
        # Update the sprint output with the latest deliverable
        if deliverable_content and sprint:
            self._update_sprint_output(agent, sprint, stage, deliverable_content)
```

with:

```python
        # Update sprint outputs — one for deliverable, one for research
        if sprint:
            if deliverable_content:
                self._update_sprint_output(agent, sprint, stage, deliverable_content, "deliverable")
            if research_content:
                self._update_sprint_output(agent, sprint, stage, research_content, "research")
```

- [ ] **Step 5: Update `_create_critique_doc` to emit critique output**

Find `_create_critique_doc` (around line 1196). After the `_create_stage_documents` call, add:

```python
        if critique_content and sprint:
            self._update_sprint_output(agent, sprint, stage, critique_content, "critique")
```

The full end of `_create_critique_doc` should look like:

```python
        if critique_content:
            self._create_stage_documents(
                agent=agent,
                stage=stage,
                version=version,
                doc_types=["stage_critique"],
                contents={"stage_critique": critique_content},
                sprint=sprint,
            )
            if sprint:
                self._update_sprint_output(agent, sprint, stage, critique_content, "critique")
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestUpdateSprintOutput -v
```

Expected: PASS.

- [ ] **Step 7: Run the full test suite to check for regressions**

```bash
cd backend && python -m pytest agents/tests/ projects/tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): emit deliverable, critique, research as separate Output records"
```

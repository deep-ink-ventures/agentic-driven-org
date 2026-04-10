# Story Bible Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent canon tracking to the writers room so agents never contradict established facts between stages.

**Architecture:** The writers room leader generates a structured story bible (via `call_claude_structured`) after each stage passes, stores it as an Output with `label="story_bible"`, and injects it into every creative task's context. The creative reviewer gains canon verification and dramatic weakness detection with a new WEAK_IDEA verdict.

**Tech Stack:** Django, Anthropic Claude API (`call_claude_structured`), pytest

**Spec:** `docs/superpowers/specs/2026-04-10-story-bible-design.md`

---

### Task 1: Story Bible Schema and Rendering on the Leader

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Write tests for STORY_BIBLE_SCHEMA and _render_story_bible**

Create `backend/agents/tests/test_writers_room_story_bible.py`:

```python
"""Tests for story bible generation, rendering, and injection."""

from unittest.mock import MagicMock, patch

import pytest

from agents.blueprints.writers_room.leader.agent import (
    STORY_BIBLE_SCHEMA,
    WritersRoomLeaderBlueprint,
)


class TestStoryBibleSchema:
    def test_schema_has_required_sections(self):
        props = STORY_BIBLE_SCHEMA["properties"]
        assert "characters" in props
        assert "timeline" in props
        assert "canon_facts" in props
        assert "world_rules" in props
        assert "changelog" in props

    def test_character_schema_has_voice_directives(self):
        char_props = STORY_BIBLE_SCHEMA["properties"]["characters"]["items"]["properties"]
        assert "voice_directives" in char_props
        assert char_props["voice_directives"]["type"] == "array"

    def test_timeline_status_enum(self):
        timeline_props = STORY_BIBLE_SCHEMA["properties"]["timeline"]["items"]["properties"]
        assert timeline_props["status"]["enum"] == ["established", "tbd"]


class TestRenderStoryBible:
    def setup_method(self):
        self.bp = WritersRoomLeaderBlueprint()

    def test_renders_characters(self):
        data = {
            "characters": [
                {
                    "name": "Jakob Hartmann",
                    "role": "CEO, eldest brother",
                    "status": "active protagonist [ESTABLISHED]",
                    "key_decisions": ["Signed Friedrichshain acquisition [ESTABLISHED]"],
                    "relationships": ["Felix — resentful, excluded from board [ESTABLISHED]"],
                    "voice_directives": ["Short declarative sentences. Never apologizes."],
                }
            ],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Characters" in result
        assert "### Jakob Hartmann" in result
        assert "Short declarative sentences" in result
        assert "Signed Friedrichshain acquisition" in result

    def test_renders_timeline(self):
        data = {
            "characters": [],
            "timeline": [
                {"when": "Ep1", "what": "First acquisition", "source": "pitch", "status": "established"},
            ],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Timeline" in result
        assert "First acquisition" in result
        assert "[ESTABLISHED]" in result

    def test_renders_canon_facts(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": ["Company name: Hartmann Capital GmbH & Co. KG"],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Established Facts (Canon)" in result
        assert "Hartmann Capital" in result

    def test_renders_world_rules(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": ["No character has direct access to the Bürgermeister"],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## World Rules" in result
        assert "Bürgermeister" in result

    def test_renders_changelog(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [
                {
                    "transition": "Pitch → Expose",
                    "added": ["Felix's side deal"],
                    "changed": ["Katrin from neutral to antagonist"],
                    "dropped": [],
                }
            ],
        }
        result = self.bp._render_story_bible(data)
        assert "## Stage Changelog" in result
        assert "Pitch → Expose" in result
        assert "Felix's side deal" in result

    def test_empty_sections_omitted(self):
        data = {
            "characters": [],
            "timeline": [],
            "canon_facts": [],
            "world_rules": [],
            "changelog": [],
        }
        result = self.bp._render_story_bible(data)
        assert "## Characters" not in result
        assert "## Timeline" not in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: ImportError — `STORY_BIBLE_SCHEMA` and `_render_story_bible` don't exist yet.

- [ ] **Step 3: Add STORY_BIBLE_SCHEMA constant to leader**

In `backend/agents/blueprints/writers_room/leader/agent.py`, after the `CREATIVE_MATRIX` dict (around line 69), add:

```python
# ── Story Bible schema (structured output for canon tracking) ─────────────

STORY_BIBLE_SCHEMA = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "relationships": {"type": "array", "items": {"type": "string"}},
                    "voice_directives": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "when": {"type": "string"},
                    "what": {"type": "string"},
                    "source": {"type": "string"},
                    "status": {"type": "string", "enum": ["established", "tbd"]},
                },
            },
        },
        "canon_facts": {"type": "array", "items": {"type": "string"}},
        "world_rules": {"type": "array", "items": {"type": "string"}},
        "changelog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transition": {"type": "string"},
                    "added": {"type": "array", "items": {"type": "string"}},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "dropped": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}
```

- [ ] **Step 4: Add _render_story_bible method to WritersRoomLeaderBlueprint**

Add this method to the `WritersRoomLeaderBlueprint` class, after `_get_current_sprint`:

```python
def _render_story_bible(self, data: dict) -> str:
    """Render structured bible JSON to markdown."""
    sections = []

    # Characters
    characters = data.get("characters", [])
    if characters:
        lines = ["## Characters\n"]
        for char in characters:
            lines.append(f"### {char.get('name', 'Unknown')}")
            if char.get("role"):
                lines.append(f"- **Role:** {char['role']}")
            if char.get("status"):
                lines.append(f"- **Status:** {char['status']}")
            decisions = char.get("key_decisions", [])
            if decisions:
                lines.append("- **Key Decisions:**")
                for d in decisions:
                    lines.append(f"  - {d}")
            relationships = char.get("relationships", [])
            if relationships:
                lines.append("- **Relationships:**")
                for r in relationships:
                    lines.append(f"  - {r}")
            directives = char.get("voice_directives", [])
            if directives:
                lines.append("- **Voice Directives:**")
                for v in directives:
                    lines.append(f"  - {v}")
            lines.append("")
        sections.append("\n".join(lines))

    # Timeline
    timeline = data.get("timeline", [])
    if timeline:
        lines = ["## Timeline\n"]
        lines.append("| When | What | Source | Status |")
        lines.append("|------|------|--------|--------|")
        for entry in timeline:
            status_tag = "[ESTABLISHED]" if entry.get("status") == "established" else "[TBD]"
            lines.append(
                f"| {entry.get('when', '')} | {entry.get('what', '')} "
                f"| {entry.get('source', '')} | {status_tag} |"
            )
        lines.append("")
        sections.append("\n".join(lines))

    # Canon Facts
    canon_facts = data.get("canon_facts", [])
    if canon_facts:
        lines = ["## Established Facts (Canon)\n"]
        for fact in canon_facts:
            lines.append(f"- {fact}")
        lines.append("")
        sections.append("\n".join(lines))

    # World Rules
    world_rules = data.get("world_rules", [])
    if world_rules:
        lines = ["## World Rules\n"]
        for rule in world_rules:
            lines.append(f"- {rule}")
        lines.append("")
        sections.append("\n".join(lines))

    # Changelog
    changelog = data.get("changelog", [])
    if changelog:
        lines = ["## Stage Changelog\n"]
        for entry in changelog:
            lines.append(f"### {entry.get('transition', 'Unknown')}")
            added = entry.get("added", [])
            if added:
                lines.append("- **Added:**")
                for a in added:
                    lines.append(f"  - {a}")
            changed = entry.get("changed", [])
            if changed:
                lines.append("- **Changed:**")
                for c in changed:
                    lines.append(f"  - {c}")
            dropped = entry.get("dropped", [])
            if dropped:
                lines.append("- **Dropped:**")
                for d in dropped:
                    lines.append(f"  - {d}")
            lines.append("")
        sections.append("\n".join(lines))

    return "# Story Bible\n\n" + "\n".join(sections) if sections else "# Story Bible\n\n(No content yet)"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: add STORY_BIBLE_SCHEMA and _render_story_bible to writers room leader"
```

---

### Task 2: Bible Generation Method (_update_story_bible)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Write test for _update_story_bible**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
@pytest.mark.django_db
class TestUpdateStoryBible:
    def _make_agent(self, department):
        """Create a leader agent with the required department."""
        from agents.models import Agent

        return Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
            internal_state={"format_type": "standalone", "current_stage": "pitch"},
        )

    def _make_sprint(self, project, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=project,
            text="Write a pitch",
            status=Sprint.Status.RUNNING,
        )
        sprint.departments.add(department)
        return sprint

    def _make_project_and_dept(self):
        from projects.models import Department, Project

        project = Project.objects.create(name="Test Project", goal="A story about brothers")
        dept = Department.objects.create(
            project=project,
            name="Writers Room",
            department_type="writers_room",
        )
        return project, dept

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_creates_story_bible_output(self, mock_structured):
        mock_structured.return_value = (
            {
                "characters": [
                    {
                        "name": "Jakob",
                        "role": "CEO",
                        "status": "active [ESTABLISHED]",
                        "key_decisions": [],
                        "relationships": [],
                        "voice_directives": [],
                    }
                ],
                "timeline": [],
                "canon_facts": ["Company: Hartmann Capital"],
                "world_rules": [],
                "changelog": [],
            },
            {"model": "claude-opus-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        # Create a deliverable for the bible to read
        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Pitch v1 — Deliverable",
            content="Jakob signs the deal.",
            sprint=sprint,
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "pitch")

        from projects.models import Output

        bible = Output.objects.get(sprint=sprint, department=dept, label="story_bible")
        assert "Jakob" in bible.content
        assert "Story Bible" in bible.title

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_updates_existing_bible(self, mock_structured):
        mock_structured.return_value = (
            {
                "characters": [
                    {
                        "name": "Jakob",
                        "role": "CEO",
                        "status": "active [ESTABLISHED]",
                        "key_decisions": ["Signed deal [ESTABLISHED]"],
                        "relationships": [],
                        "voice_directives": [],
                    }
                ],
                "timeline": [],
                "canon_facts": [],
                "world_rules": [],
                "changelog": [
                    {"transition": "Pitch → Expose", "added": ["New subplot"], "changed": [], "dropped": []}
                ],
            },
            {"model": "claude-opus-4-6", "input_tokens": 200, "output_tokens": 100, "cost_usd": 0.02},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        # Pre-existing bible
        from projects.models import Output

        Output.objects.create(
            sprint=sprint,
            department=dept,
            label="story_bible",
            title="Story Bible",
            output_type="markdown",
            content="# Story Bible\n\nOld content",
        )

        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Expose v1 — Deliverable",
            content="Jakob expands.",
            sprint=sprint,
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "expose")

        bible = Output.objects.get(sprint=sprint, department=dept, label="story_bible")
        assert "Signed deal" in bible.content
        assert "Pitch → Expose" in bible.content
        # Should be 1 output, not 2 (update_or_create)
        assert Output.objects.filter(sprint=sprint, department=dept, label="story_bible").count() == 1

    @patch("agents.ai.claude_client.call_claude_structured")
    def test_includes_voice_profile_in_prompt(self, mock_structured):
        mock_structured.return_value = (
            {"characters": [], "timeline": [], "canon_facts": [], "world_rules": [], "changelog": []},
            {"model": "claude-opus-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        project, dept = self._make_project_and_dept()
        agent = self._make_agent(dept)
        sprint = self._make_sprint(project, dept)

        from projects.models import Document

        Document.objects.create(
            department=dept,
            doc_type="stage_deliverable",
            title="Pitch v1 — Deliverable",
            content="Story content.",
            sprint=sprint,
        )
        Document.objects.create(
            department=dept,
            doc_type="voice_profile",
            title="Voice Profile",
            content="Short sentences. No apologies.",
        )

        bp = WritersRoomLeaderBlueprint()
        bp._update_story_bible(agent, sprint, "pitch")

        # Check that voice profile was included in the user_message
        call_args = mock_structured.call_args
        user_message = call_args.kwargs.get("user_message") or call_args[1] if len(call_args) > 1 else call_args.kwargs.get("user_message", "")
        # The user_message is the second positional arg
        if isinstance(user_message, str):
            assert "Short sentences" in user_message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestUpdateStoryBible -v`
Expected: FAIL — `_update_story_bible` doesn't exist.

- [ ] **Step 3: Implement _update_story_bible**

Add this method to `WritersRoomLeaderBlueprint`, after `_render_story_bible`:

```python
def _update_story_bible(self, agent, sprint, stage: str):
    """Generate or update the story bible after a stage passes.

    Reads the current bible (if any), the stage deliverable, and the voice
    profile. Calls call_claude_structured to produce an updated bible,
    renders it to markdown, and stores it as an Output.
    """
    from agents.ai.claude_client import call_claude_structured
    from projects.models import Output

    effective_stage = self._get_effective_stage(agent, stage)

    # Gather inputs
    deliverable_doc = (
        Document.objects.filter(
            department=agent.department,
            doc_type="stage_deliverable",
            is_archived=False,
        )
        .order_by("-created_at")
        .first()
    )
    deliverable_text = deliverable_doc.content if deliverable_doc else ""

    if not deliverable_text:
        logger.warning("Story Bible: no deliverable found for stage '%s' — skipping", stage)
        return

    # Previous bible
    existing_bible = Output.objects.filter(
        sprint=sprint,
        department=agent.department,
        label="story_bible",
    ).first()
    previous_bible = existing_bible.content if existing_bible else ""

    # Voice profile
    voice_doc = (
        Document.objects.filter(
            department=agent.department,
            doc_type="voice_profile",
            is_archived=False,
        )
        .order_by("-created_at")
        .first()
    )
    voice_text = voice_doc.content if voice_doc else ""

    # Build prompt
    user_parts = [f"## Stage: {effective_stage}\n"]
    if previous_bible:
        user_parts.append(f"## Previous Story Bible\n{previous_bible}\n")
    user_parts.append(f"## Stage Deliverable\n{deliverable_text}\n")
    if voice_text:
        user_parts.append(f"## Voice Profile\n{voice_text}\n")
    user_message = "\n".join(user_parts)

    system_prompt = (
        "You are extracting and updating a story bible from creative writing deliverables.\n\n"
        "Extract every fact, character decision, relationship, and world rule. "
        "Be exhaustive — anything not in the bible does not exist for future stages.\n\n"
        "Mark items as 'established' (dramatized in a deliverable) or 'tbd' "
        "(mentioned but not yet dramatized).\n\n"
        "EXTRACTION RULES:\n"
        "- Extract new facts established in this deliverable\n"
        "- Identify what changed from the previous bible\n"
        "- Flag anything dropped (present in prior bible but contradicted or absent)\n"
        "- Populate the changelog with added/changed/dropped\n"
        "- Flip 'tbd' items to 'established' when dramatized in the deliverable\n"
        "- Flag 'tbd' items that should have been resolved by this stage but weren't\n"
        "- Incorporate voice directives from the voice profile for each character\n\n"
        "Be specific and concrete. Names, places, decisions — not summaries."
    )

    bible_data, usage = call_claude_structured(
        system_prompt=system_prompt,
        user_message=user_message,
        output_schema=STORY_BIBLE_SCHEMA,
        tool_name="update_story_bible",
        tool_description="Submit the updated story bible with all extracted facts",
        max_tokens=8192,
    )

    bible_markdown = self._render_story_bible(bible_data)

    Output.objects.update_or_create(
        sprint=sprint,
        department=agent.department,
        label="story_bible",
        defaults={
            "title": "Story Bible",
            "output_type": "markdown",
            "content": bible_markdown,
        },
    )
    logger.info("Story Bible: updated for stage '%s' (sprint %s)", stage, sprint.id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: add _update_story_bible to generate bible from stage deliverables"
```

---

### Task 3: Hook Bible Generation Into the State Machine

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

The bible generates at one point: when a stage reaches `"review"` status (accepted by creative_reviewer) and transitions to `"passed"`. This is in `generate_task_proposal`, around the `if status == "review":` block (line ~548).

- [ ] **Step 1: Write test for bible generation on stage pass**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
@pytest.mark.django_db
class TestBibleTriggeredOnStagePass:
    def _setup_department_with_agents(self):
        from agents.models import Agent
        from projects.models import Department, Project, Sprint

        project = Project.objects.create(name="Test", goal="Story about brothers")
        dept = Department.objects.create(
            project=project, name="WR", department_type="writers_room"
        )
        leader = Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={
                "format_type": "standalone",
                "current_stage": "pitch",
                "terminal_stage": "treatment",
                "entry_detected": True,
                "stage_status": {"pitch": {"status": "review", "iterations": 0}},
            },
        )
        sprint = Sprint.objects.create(
            project=project, text="Write a pitch", status=Sprint.Status.RUNNING
        )
        sprint.departments.add(dept)
        return leader, dept, sprint

    @patch.object(WritersRoomLeaderBlueprint, "_update_story_bible")
    def test_bible_updated_on_stage_pass(self, mock_bible):
        leader, dept, sprint = self._setup_department_with_agents()
        bp = WritersRoomLeaderBlueprint()

        # The creative_reviewer has already accepted (status == "review" means accepted)
        # generate_task_proposal should call _update_story_bible and advance
        result = bp.generate_task_proposal(leader)

        mock_bible.assert_called_once_with(leader, sprint, "pitch")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestBibleTriggeredOnStagePass -v`
Expected: FAIL — `_update_story_bible` is not called in the state machine.

- [ ] **Step 3: Add _update_story_bible call in the state machine**

In the `generate_task_proposal` method, find the `if status == "review":` block (around line 548). Currently it does:

```python
if status == "review":
    # creative_reviewer completed and was accepted
    self._create_critique_doc(agent, current_stage, sprint)
    current_info["status"] = "passed"
```

Add the bible update call right after `_create_critique_doc`:

```python
if status == "review":
    # creative_reviewer completed and was accepted
    self._create_critique_doc(agent, current_stage, sprint)
    self._update_story_bible(agent, sprint, current_stage)
    current_info["status"] = "passed"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Run full writers room test suite to check for regressions**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_lead_writer.py backend/agents/tests/test_writers_room_feedback_blueprint.py backend/agents/tests/test_writers_room_ideation.py -v`
Expected: All existing tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: trigger story bible generation when stage passes review"
```

---

### Task 4: Bible Context Injection

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

The bible must be injected into the context that creative agents receive. The injection point is `_get_delegation_context` on the leader (line ~162) and `_propose_creative_tasks` where `step_plan` is built (line ~1007).

- [ ] **Step 1: Write test for bible injection in delegation context**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
@pytest.mark.django_db
class TestBibleContextInjection:
    def _make_setup(self):
        from agents.models import Agent
        from projects.models import Department, Output, Project, Sprint

        project = Project.objects.create(name="Test", goal="Story")
        dept = Department.objects.create(
            project=project, name="WR", department_type="writers_room"
        )
        leader = Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={
                "format_type": "standalone",
                "current_stage": "expose",
                "entry_detected": True,
            },
        )
        sprint = Sprint.objects.create(
            project=project, text="Write", status=Sprint.Status.RUNNING
        )
        sprint.departments.add(dept)
        Output.objects.create(
            sprint=sprint,
            department=dept,
            label="story_bible",
            title="Story Bible",
            output_type="markdown",
            content="# Story Bible\n\n## Characters\n\n### Jakob\n- **Role:** CEO",
        )
        return leader, dept, sprint

    def test_delegation_context_includes_bible(self):
        leader, dept, sprint = self._make_setup()
        bp = WritersRoomLeaderBlueprint()
        context = bp._get_delegation_context(leader)
        assert "Story Bible (CANON" in context
        assert "Jakob" in context

    def test_delegation_context_without_bible(self):
        from agents.models import Agent
        from projects.models import Department, Project

        project = Project.objects.create(name="Test2", goal="Story2")
        dept = Department.objects.create(
            project=project, name="WR2", department_type="writers_room"
        )
        leader = Agent.objects.create(
            name="Showrunner2",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={"current_stage": "pitch"},
        )
        bp = WritersRoomLeaderBlueprint()
        context = bp._get_delegation_context(leader)
        assert "Story Bible" not in context
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestBibleContextInjection -v`
Expected: FAIL — `_get_delegation_context` doesn't include bible.

- [ ] **Step 3: Modify _get_delegation_context to inject bible**

Replace the current `_get_delegation_context` method (line ~162):

```python
def _get_delegation_context(self, agent):
    internal_state = agent.internal_state or {}
    stage_status = internal_state.get("stage_status", {})
    current_stage = internal_state.get("current_stage", STAGES[0])

    context = (
        f"# Current Stage: {current_stage}\n"
        f"# Stage Status: {json.dumps(stage_status, indent=2)}\n"
        f"# Quality: Excellence threshold {EXCELLENCE_THRESHOLD}/10 (minimum dimension score)"
    )

    # Inject story bible if one exists
    sprint = self._get_current_sprint(agent)
    if sprint:
        from projects.models import Output

        bible_output = Output.objects.filter(
            sprint=sprint,
            department=agent.department,
            label="story_bible",
        ).first()
        if bible_output and bible_output.content:
            context += (
                f"\n\n## Story Bible (CANON — do not contradict)\n"
                f"{bible_output.content}"
            )

    return context
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: inject story bible into creative task delegation context"
```

---

### Task 5: Creative Reviewer — Canon Verification and WEAK_IDEA Verdict

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/commands/review_creative.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Write tests for creative reviewer enhancements**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
class TestCreativeReviewerEnhancements:
    def test_system_prompt_includes_canon_verification(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "CANON VERIFICATION" in prompt
        assert "[ESTABLISHED]" in prompt

    def test_system_prompt_includes_dramatic_weakness(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "DRAMATIC WEAKNESS" in prompt or "WEAK_IDEA" in prompt
        assert "stakes" in prompt.lower()

    def test_system_prompt_includes_weak_idea_verdict(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "WEAK_IDEA" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestCreativeReviewerEnhancements -v`
Expected: FAIL — system prompt doesn't contain canon verification.

- [ ] **Step 3: Add canon verification and dramatic weakness to creative reviewer system prompt**

In `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`, add the new sections to the `system_prompt` property. After the existing `FIX ROUTING` section (before the closing `"""`), add:

```python
## CANON VERIFICATION (when Story Bible is present in context)

If a Story Bible is provided in the task context, perform canon verification:

For every character mentioned in the deliverable:
  - Does their behavior match established key decisions in the bible?
  - Do their relationships match the bible?
  - Does dialogue match voice directives?

For every scene:
  - Does it respect world rules?
  - Does it fit the established timeline?
  - Are there new facts that should be added to canon?

Any contradiction with [ESTABLISHED] items = critical failure (dimension score 0).
[TBD] items may be freely developed — but must be internally consistent.

## DRAMATIC WEAKNESS DETECTION

Beyond consistency, evaluate dramatic quality:

- **Logical threshold:** Does the cause-effect chain hold? Would a smart character make this decision given what they know? Plot-convenient stupidity = rejection.
- **Stakes calibration:** Proportional to the stage. Pitch needs existential stakes for the protagonist. Expose needs escalation. Treatment needs no scene without consequence. First draft needs every page to matter.
- **Dramatic economy:** If a subplot could be cut without the main arc collapsing, it's weak.

Scope scaling by stage:
- Pitch/expose: reject full storylines, character arcs, central conflicts that are weak
- Treatment/concept: reject scene sequences, subplot arcs, weak turning points
- First draft: reject individual scenes, dialogue decisions, weak beats

If the idea itself is wrong — not poorly executed but fundamentally weak — use verdict WEAK_IDEA instead of CHANGES_REQUESTED. WEAK_IDEA means: "this direction is wrong, try a different one." Your feedback says what is weak and why, but does NOT prescribe the replacement. The creative team must generate a fresh idea, not patch a bad one.

VERDICT OPTIONS:
- APPROVED: meets excellence threshold
- CHANGES_REQUESTED: execution needs improvement (revision loop)
- WEAK_IDEA: direction is fundamentally wrong (re-ideation loop)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestCreativeReviewerEnhancements -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py
git commit -m "feat: add canon verification and WEAK_IDEA verdict to creative reviewer"
```

---

### Task 6: Leader State Machine — Handle WEAK_IDEA Verdict

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

Currently `_propose_fix_task` always loops back for revision. A WEAK_IDEA verdict should reset more aggressively — back to creative ideation with no revision preamble (iteration resets to 0 so agents don't get revision instructions).

- [ ] **Step 1: Write test for WEAK_IDEA handling**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
@pytest.mark.django_db
class TestWeakIdeaVerdict:
    def _setup(self):
        from agents.models import Agent
        from projects.models import Department, Project, Sprint

        project = Project.objects.create(name="Test", goal="Story")
        dept = Department.objects.create(
            project=project, name="WR", department_type="writers_room"
        )
        leader = Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={
                "format_type": "standalone",
                "current_stage": "pitch",
                "terminal_stage": "treatment",
                "entry_detected": True,
                "stage_status": {"pitch": {"status": "not_started", "iterations": 2}},
            },
        )
        sprint = Sprint.objects.create(
            project=project, text="Write", status=Sprint.Status.RUNNING
        )
        sprint.departments.add(dept)
        return leader, dept, sprint

    @patch.object(WritersRoomLeaderBlueprint, "_create_critique_doc")
    @patch.object(WritersRoomLeaderBlueprint, "_propose_creative_tasks")
    def test_weak_idea_resets_iterations(self, mock_propose, mock_critique):
        mock_propose.return_value = {"exec_summary": "Creative tasks", "tasks": []}
        leader, dept, sprint = self._setup()
        bp = WritersRoomLeaderBlueprint()

        review_task = MagicMock()
        review_task.review_verdict = "WEAK_IDEA"

        bp._propose_fix_task(leader, review_task, score=3.0, round_num=1, polish_count=0)

        leader.refresh_from_db()
        stage_info = leader.internal_state["stage_status"]["pitch"]
        # WEAK_IDEA resets iterations to 0 (fresh ideation, not revision)
        assert stage_info["iterations"] == 0

    @patch.object(WritersRoomLeaderBlueprint, "_create_critique_doc")
    @patch.object(WritersRoomLeaderBlueprint, "_propose_creative_tasks")
    def test_changes_requested_increments_iterations(self, mock_propose, mock_critique):
        mock_propose.return_value = {"exec_summary": "Creative tasks", "tasks": []}
        leader, dept, sprint = self._setup()
        bp = WritersRoomLeaderBlueprint()

        review_task = MagicMock()
        review_task.review_verdict = "CHANGES_REQUESTED"

        bp._propose_fix_task(leader, review_task, score=7.0, round_num=1, polish_count=0)

        leader.refresh_from_db()
        stage_info = leader.internal_state["stage_status"]["pitch"]
        # CHANGES_REQUESTED increments as before
        assert stage_info["iterations"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestWeakIdeaVerdict -v`
Expected: FAIL — `_propose_fix_task` doesn't check verdict type.

- [ ] **Step 3: Modify _propose_fix_task to handle WEAK_IDEA**

Replace the `_propose_fix_task` method (line ~1557):

```python
def _propose_fix_task(
    self, agent: Agent, review_task, score: float, round_num: int, polish_count: int
) -> dict | None:
    """On failed review: create critique doc, reset to creative_writing.

    WEAK_IDEA verdict resets iterations to 0 (fresh ideation).
    CHANGES_REQUESTED increments iterations (revision of same material).
    """
    internal_state = agent.internal_state or {}
    current_stage = internal_state.get("current_stage", STAGES[0])
    stage_status = internal_state.get("stage_status", {})
    current_info = stage_status.get(current_stage, {})

    sprint = self._get_current_sprint(agent)
    self._create_critique_doc(agent, current_stage, sprint)

    verdict = getattr(review_task, "review_verdict", "CHANGES_REQUESTED")

    if verdict == "WEAK_IDEA":
        # Fresh ideation — reset iterations so agents don't get revision instructions
        current_info["iterations"] = 0
        logger.info(
            "Writers Room: WEAK_IDEA for stage '%s' — resetting to fresh ideation",
            current_stage,
        )
    else:
        current_info["iterations"] = current_info.get("iterations", 0) + 1

    current_info["status"] = "not_started"
    stage_status[current_stage] = current_info
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    config = _get_merged_config(agent)
    effective_stage = self._get_effective_stage(agent, current_stage)
    return self._propose_creative_tasks(agent, effective_stage, config)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestWeakIdeaVerdict -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: handle WEAK_IDEA verdict — reset to fresh ideation instead of revision"
```

---

### Task 7: Voice Profile Reform (Story Researcher)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Write test for directive-style voice profile**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
class TestVoiceProfileReform:
    def test_voice_system_prompt_requires_directives(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("story_researcher", "writers_room")
        # The voice profiling system uses a custom system prompt built in _execute_profile_voice
        # Check the main system prompt for directive language
        prompt = bp.system_prompt
        # The reform adds directive language to the main prompt
        assert "directive" in prompt.lower() or "DIRECTIVE" in prompt

    def test_voice_suffix_requires_directive_format(self):
        """The profile_voice suffix should instruct directive output, not analytical."""
        import inspect

        from agents.blueprints import get_blueprint

        bp = get_blueprint("story_researcher", "writers_room")
        source = inspect.getsource(bp._execute_profile_voice)
        assert "directive" in source.lower() or "DIRECTIVE" in source
        assert "When writing" in source or "mechanically" in source
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestVoiceProfileReform -v`
Expected: FAIL — current prompts don't mention directives.

- [ ] **Step 3: Update story_researcher voice profiling prompts**

In `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`, modify the `_execute_profile_voice` method.

Update the `voice_system` string (line ~266). Replace the current `"VOICE DNA ANALYSIS:\n"` block with:

```python
voice_system = (
    self.system_prompt + "\n\n"
    "VOICE DNA ANALYSIS — DIRECTIVE OUTPUT:\n"
    "You are producing a VOICE DNA profile — not vague descriptions, but OPERATIONAL "
    "DIRECTIVES that a writer can follow mechanically to reproduce this voice.\n\n"
    "The author's voice is SACRED. Structure, plot, characters can be radically changed — "
    "but the writing style, rhythm, humor, tone must be preserved. The original author "
    "should read output written in their voice and think: 'that's me — the best version of me.'\n\n"
    "RULES FOR VOICE DNA:\n"
    "1. Every pattern claim MUST be backed by 2-3 EXACT QUOTES from the source material.\n"
    "2. Not paraphrases. Not summaries. EXACT quotes, in quotation marks.\n"
    "3. Be surgical: 'average sentence length ~8 words' not 'short sentences'.\n"
    "4. The WHAT THIS VOICE IS NOT section is as important as what it IS.\n"
    "5. The VOICE COMMANDMENTS must be DIRECTIVES — instructions a writer follows "
    "mechanically. 'When writing dialogue, never exceed 15 words per line' not "
    "'the dialogue tends to be brief'.\n"
    "6. If humor is absent, say so explicitly — do not invent humor patterns.\n"
    "7. If dialogue is absent from the source, note that and skip the dialogue section.\n"
    "8. Voice profiles are DIRECTIVES, not descriptions. Write instructions: "
    "'Short declarative sentences. Never apologize.' not "
    "'The speech patterns are characterized by directness.'"
)
```

Also add to the system_prompt property (line ~53), append before the CRITICAL locale line:

```python
"Voice profiles must be DIRECTIVES, not descriptions. Write instructions that a "
"writer can follow mechanically. Each directive is one line. Include example phrases "
"in the original language.\n\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestVoiceProfileReform -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: reform voice profiles to directive format instead of analytical"
```

---

### Task 8: Creative Writing Skills — System Prompt Enhancements

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Write tests for system prompt additions**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
class TestCreativeWritingSkillsIntegration:
    """Test that creative writing research skills are integrated into agent prompts."""

    def test_lead_writer_has_continuity_protocol(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("lead_writer", "writers_room")
        prompt = bp.system_prompt
        assert "cross-reference" in prompt.lower() or "bible" in prompt.lower()
        assert "contradiction" in prompt.lower()

    def test_lead_writer_has_action_first_sharpening(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("lead_writer", "writers_room")
        prompt = bp.system_prompt
        assert "observable action" in prompt.lower() or "abstract psychology" in prompt.lower()

    def test_story_architect_has_bible_consultation(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "bible" in prompt.lower() or "canon" in prompt.lower()

    def test_dialog_writer_has_bible_consultation(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "bible" in prompt.lower() or "voice directive" in prompt.lower()

    def test_character_designer_has_bible_consultation(self):
        from agents.blueprints import get_blueprint

        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "bible" in prompt.lower() or "canon" in prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestCreativeWritingSkillsIntegration -v`
Expected: FAIL — current prompts don't mention bible/canon.

- [ ] **Step 3: Add continuity protocol and action-first to lead_writer system prompt**

In `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`, add to the `system_prompt` property, before the `ANTI_AI_RULES` concatenation (line ~432). Insert before `"CRITICAL: Your ENTIRE output..."`:

```python
"\n## Continuity Protocol\n"
"Before synthesizing creative team output into a deliverable: list every character "
"mentioned in the creative team's output. Cross-reference each against the Story Bible "
"(if provided in context). Flag any contradiction before writing. Resolve contradictions "
"in favor of the bible — it is canon.\n\n"
"## Action-First Sharpening\n"
"Show observable actions, not abstract psychology. Replace 'Jakob felt betrayed' with "
"'Jakob closed the folder and walked out.' Replace 'She was nervous' with 'She checked "
"her phone three times in a minute.' Internal states must be externalized through "
"behavior, dialogue, or physical detail.\n\n"
```

- [ ] **Step 4: Add pre-writing bible consultation to story_architect, dialog_writer, character_designer**

In each of these three files, add to the `system_prompt` property, before the CRITICAL locale line:

For `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`:

```python
"## Pre-Writing Bible Consultation\n"
"If a Story Bible is provided in context, check before writing any scene:\n"
"(1) Are all characters consistent with bible key decisions?\n"
"(2) Do relationships match?\n"
"(3) Does the setting respect world rules?\n"
"(4) Does the timeline fit?\n"
"Do not invent facts that contradict [ESTABLISHED] items. "
"You may freely develop [TBD] items.\n\n"
```

For `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`:

```python
"## Pre-Writing Bible Consultation\n"
"If a Story Bible is provided in context, the bible's voice directives are your "
"primary constraint for each character. Every line of dialogue must pass: would this "
"character say this, given their directives? Check key decisions and relationships "
"before writing any exchange. Do not contradict [ESTABLISHED] items.\n\n"
```

For `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py`:

```python
"## Pre-Writing Bible Consultation\n"
"If a Story Bible is provided in context, check before designing or developing characters:\n"
"(1) Are all characters consistent with bible key decisions?\n"
"(2) Do relationships match established dynamics?\n"
"(3) Do character arcs respect the established timeline?\n"
"Do not contradict [ESTABLISHED] items. You may freely develop [TBD] items.\n\n"
```

Also add action-first sharpening to `story_architect` and `dialog_writer` system prompts (they already have ACTION-FIRST MANDATE blocks, so add the sharpening as reinforcement):

For both `story_architect` and `dialog_writer`, add after their existing ACTION-FIRST section:

```python
"Show observable actions, not abstract psychology. Replace 'he felt betrayed' with "
"'he closed the folder and walked out.' Internal states must be externalized through "
"behavior, dialogue, or physical detail.\n\n"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestCreativeWritingSkillsIntegration -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py \
       backend/agents/blueprints/writers_room/workforce/story_architect/agent.py \
       backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py \
       backend/agents/blueprints/writers_room/workforce/character_designer/agent.py \
       backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: add creative writing skills to agent system prompts — bible consultation, continuity, action-first"
```

---

### Task 9: Bible Injection in Review Task Context

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

The creative reviewer also needs the bible in its task context for canon verification. The bible should be appended to the `step_plan` in `_propose_review_task`.

- [ ] **Step 1: Write test for bible in review task context**

Append to `backend/agents/tests/test_writers_room_story_bible.py`:

```python
@pytest.mark.django_db
class TestBibleInReviewContext:
    def test_review_task_includes_bible(self):
        from agents.models import Agent
        from projects.models import Department, Output, Project, Sprint

        project = Project.objects.create(name="Test", goal="Story")
        dept = Department.objects.create(
            project=project, name="WR", department_type="writers_room",
        )
        leader = Agent.objects.create(
            name="Showrunner",
            agent_type="leader",
            department=dept,
            is_leader=True,
            status="active",
            internal_state={
                "format_type": "standalone",
                "current_stage": "expose",
                "entry_detected": True,
            },
        )
        sprint = Sprint.objects.create(
            project=project, text="Write", status=Sprint.Status.RUNNING,
        )
        sprint.departments.add(dept)
        Output.objects.create(
            sprint=sprint,
            department=dept,
            label="story_bible",
            title="Story Bible",
            output_type="markdown",
            content="# Story Bible\n\n## Canon\n- Company: Hartmann Capital",
        )

        bp = WritersRoomLeaderBlueprint()
        config = {"locale": "de"}
        result = bp._propose_review_task(leader, "expose", config)

        step_plan = result["tasks"][0]["step_plan"]
        assert "Story Bible" in step_plan
        assert "Hartmann Capital" in step_plan
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestBibleInReviewContext -v`
Expected: FAIL — `_propose_review_task` doesn't include bible.

- [ ] **Step 3: Inject bible into _propose_review_task step_plan**

In `_propose_review_task` (line ~1507), after building `feedback_text` and before constructing the return dict, add:

```python
# Inject story bible for canon verification
bible_context = ""
bible_output = None
try:
    from projects.models import Output

    bible_output = Output.objects.filter(
        sprint=sprint,
        department=agent.department,
        label="story_bible",
    ).first()
except Exception:
    pass
if bible_output and bible_output.content:
    bible_context = f"\n\n## Story Bible (CANON — do not contradict)\n{bible_output.content}"
```

Then append `bible_context` to the `step_plan` in the return dict:

```python
"step_plan": (
    f"Stage: {stage}\n"
    f"Locale: {locale}\n"
    f"Quality threshold: {EXCELLENCE_THRESHOLD}/10\n\n"
    f"## Analyst Feedback Reports\n{feedback_text}\n\n"
    f"Score each dimension 1.0-10.0. Overall score = minimum of all dimensions.\n"
    f"After your review, call the submit_verdict tool with your verdict and score.\n\n"
    f"For CHANGES_REQUESTED: group fix instructions by creative agent."
    f"For WEAK_IDEA: explain what is fundamentally weak and why, but do not prescribe replacement."
    f"{bible_context}"
),
```

Note: `_propose_review_task` needs the sprint. It currently doesn't have it. Add `sprint = self._get_current_sprint(agent)` at the top of the method.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py::TestBibleInReviewContext -v`
Expected: PASS.

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py backend/agents/tests/test_writers_room_lead_writer.py backend/agents/tests/test_writers_room_feedback_blueprint.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_story_bible.py
git commit -m "feat: inject story bible into creative reviewer task context for canon verification"
```

---

### Task 10: Full Integration Test

**Files:**
- Test: `backend/agents/tests/test_writers_room_story_bible.py`

- [ ] **Step 1: Run the complete test file**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_story_bible.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Run the full writers room test suite**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_lead_writer.py backend/agents/tests/test_writers_room_feedback_blueprint.py backend/agents/tests/test_writers_room_ideation.py backend/agents/tests/test_writers_room_skills_commands.py backend/agents/tests/test_blueprints.py backend/agents/tests/test_authenticity_analyst.py -v`
Expected: All tests PASS (no regressions).

- [ ] **Step 3: Run linting**

Run: `cd /Users/christianpeters/the-agentic-company && ruff check backend/agents/blueprints/writers_room/ backend/agents/tests/test_writers_room_story_bible.py`
Expected: No errors.

- [ ] **Step 4: Final commit if any linting fixes were needed**

```bash
git add -A
git commit -m "fix: lint fixes for story bible implementation"
```

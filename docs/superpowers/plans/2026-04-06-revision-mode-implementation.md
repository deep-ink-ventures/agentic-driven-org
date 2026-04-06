# Revision Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On revision rounds (iteration > 0), agents output structured edits instead of full rewrites. Untouched sections stay byte-identical. Documents can be locked to prevent accidental consolidation.

**Architecture:** Add `is_locked` field to Document model. Add `_apply_revisions()` helper with three edit operations (replace, replace_section, replace_between). Modify `_propose_creative_tasks` and `_propose_lead_writer_task` to inject revision instructions on iteration > 0. Modify `_create_deliverable_and_research_docs` to apply revisions to existing docs instead of replacing them. Add structure requirements to CRAFT_DIRECTIVES.

**Tech Stack:** Django, Python (existing stack)

**Spec:** `docs/superpowers/specs/2026-04-06-revision-mode-design.md`

---

### Task 1: Add `is_locked` field to Document model + migration

**Files:**
- Modify: `backend/projects/models/document.py`
- Create: migration via `makemigrations`
- Modify: `backend/projects/tasks_consolidation.py` (3 consolidation functions)
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
class TestDocumentLocking:
    def test_document_has_is_locked_field(self):
        assert hasattr(Document, "is_locked")

    def test_is_locked_defaults_to_false(self):
        field = Document._meta.get_field("is_locked")
        assert field.default is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestDocumentLocking -v`
Expected: FAIL

- [ ] **Step 3: Add `is_locked` field**

In `backend/projects/models/document.py`, after the `is_archived` field (line 58), add:

```python
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked documents are protected from consolidation and archiving by automated processes.",
    )
```

- [ ] **Step 4: Generate migration**

Run: `cd backend && POSTGRES_PORT=5497 python manage.py makemigrations projects -n document_is_locked`

- [ ] **Step 5: Add consolidation lock guards**

In `backend/projects/tasks_consolidation.py`, add `is_locked=False` filter to all three consolidation functions:

In `consolidate_sprint_documents` (line 93-97), change:
```python
        docs = list(
            Document.objects.filter(
                department=department,
                sprint=sprint,
                is_archived=False,
                is_locked=False,
            )
```

In `consolidate_monthly_documents` (line 138-143), change:
```python
        docs = list(
            Document.objects.filter(
                department=department,
                is_archived=False,
                is_locked=False,
                created_at__lt=cutoff,
            ).order_by("created_at")
        )
```

Also update the query at lines 128-133 that finds departments with old docs:
```python
    departments_with_old_docs = (
        Document.objects.filter(
            is_archived=False,
            is_locked=False,
            created_at__lt=cutoff,
        )
```

In `consolidate_department_documents` (line 166), change:
```python
    active_docs = Document.objects.filter(department=department, is_archived=False, is_locked=False)
```

And the docs query at line 179:
```python
    docs = list(active_docs.order_by("created_at"))
```
(This already uses `active_docs` which now has `is_locked=False`, so no change needed for line 179.)

- [ ] **Step 6: Run tests**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestDocumentLocking -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/projects/models/document.py backend/projects/migrations/ backend/projects/tasks_consolidation.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat: add is_locked field to Document, consolidation respects lock

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Add `_apply_revisions()` and helpers to the leader blueprint

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
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
        assert result == content  # unchanged
        assert len(failed) == 1
        assert failed[0]["reason"] == "not_found"

    def test_replace_ambiguous(self, blueprint):
        content = "The cat sat. The cat sat. The dog ran."
        revisions = [{"type": "replace", "old_text": "The cat sat.", "new_text": "The cat slept."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert result == content  # unchanged — ambiguous
        assert len(failed) == 1
        assert "ambiguous" in failed[0]["reason"]

    def test_replace_section_basic(self, blueprint):
        content = "# Title\n\nIntro.\n\n## Section A\n\nOld content A.\n\n## Section B\n\nContent B."
        revisions = [{"type": "replace_section", "section": "## Section A", "new_content": "New content A."}]
        result, failed = blueprint._apply_revisions(content, revisions)
        assert "New content A." in result
        assert "Old content A." not in result
        assert "Content B." in result  # Section B untouched
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
        assert "Sub content A." not in result  # subsections replaced too
        assert "Other content." in result  # same-level section preserved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestApplyRevisions -v`
Expected: FAIL — `_apply_revisions` not found

- [ ] **Step 3: Implement `_apply_revisions` and helpers**

In `backend/agents/blueprints/writers_room/leader/agent.py`, add these methods to `WritersRoomLeaderBlueprint` (after `_get_current_sprint`, before `generate_task_proposal`):

```python
    # ── Revision application ───────────────────────────────────────────

    def _apply_revisions(self, document_content: str, revisions: list[dict]) -> tuple[str, list[dict]]:
        """Apply structured edits to a document.

        Returns (revised_content, failed_edits).
        Failed edits are skipped — the quality loop handles retry.
        """
        result = document_content
        failed = []

        for rev in revisions:
            rev_type = rev.get("type", "replace")

            if rev_type == "replace":
                old = rev.get("old_text", "")
                new = rev.get("new_text", "")
                if not old:
                    continue
                count = result.count(old)
                if count == 1:
                    result = result.replace(old, new, 1)
                elif count == 0:
                    failed.append({"text": old[:80], "reason": "not_found"})
                else:
                    failed.append({"text": old[:80], "reason": f"ambiguous ({count} matches)"})

            elif rev_type == "replace_section":
                header = rev.get("section", "")
                new_content = rev.get("new_content", "")
                result, ok = self._replace_section(result, header, new_content)
                if not ok:
                    failed.append({"text": header, "reason": "section_not_found"})

            elif rev_type == "replace_between":
                start = rev.get("start", "")
                end = rev.get("end", "")
                new_content = rev.get("new_content", "")
                result, ok = self._replace_between(result, start, end, new_content)
                if not ok:
                    failed.append({"text": f"{start[:40]}...{end[:40]}", "reason": "anchors_not_found"})

        return result, failed

    @staticmethod
    def _replace_section(content: str, header: str, new_content: str) -> tuple[str, bool]:
        """Replace content under a markdown header until the next same-level header."""
        if header not in content:
            return content, False

        # Determine header level (count leading #)
        level = len(header) - len(header.lstrip("#"))
        if level == 0:
            return content, False

        start_idx = content.index(header)
        after_header = start_idx + len(header)

        # Find next header of same or higher level (fewer or equal #)
        end_offset = len(content)
        remaining = content[after_header:]
        search_pos = 0
        for line in remaining.split("\n"):
            line_start = after_header + search_pos
            stripped = line.lstrip()
            if stripped.startswith("#") and search_pos > 0:  # skip first line (the header itself)
                line_level = len(stripped) - len(stripped.lstrip("#"))
                if line_level <= level and line_level > 0:
                    end_offset = line_start
                    break
            search_pos += len(line) + 1  # +1 for newline

        result = content[:start_idx] + header + "\n\n" + new_content + "\n\n" + content[end_offset:]
        return result, True

    @staticmethod
    def _replace_between(content: str, start: str, end: str, new_content: str) -> tuple[str, bool]:
        """Replace everything between two anchor texts (inclusive)."""
        if not start or not end:
            return content, False
        if content.count(start) != 1 or content.count(end) != 1:
            return content, False

        start_idx = content.index(start)
        end_idx = content.index(end, start_idx)
        end_idx += len(end)

        if start_idx >= end_idx:
            return content, False

        result = content[:start_idx] + new_content + content[end_idx:]
        return result, True
```

- [ ] **Step 4: Run tests**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestApplyRevisions -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): add _apply_revisions with replace, replace_section, replace_between

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Add structure requirements to CRAFT_DIRECTIVES

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
class TestStructureRequirements:
    def test_craft_directives_have_structure_info(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        for key, directive in CRAFT_DIRECTIVES.items():
            assert "## Document Structure" in directive, f"{key} missing structure requirements"

    def test_pitch_has_no_mandatory_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "flowing prose" in CRAFT_DIRECTIVES["write_pitch"].lower() or "no mandatory sections" in CRAFT_DIRECTIVES["write_pitch"].lower()

    def test_expose_requires_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        assert "##" in CRAFT_DIRECTIVES["write_expose"]

    def test_concept_requires_sections(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES

        directive = CRAFT_DIRECTIVES["write_concept"]
        assert "Story Engine" in directive
        assert "Characters" in directive
        assert "Episode" in directive
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStructureRequirements -v`
Expected: FAIL

- [ ] **Step 3: Add structure requirements to each CRAFT_DIRECTIVE**

In `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`, append a `## Document Structure` section to each craft directive string in the `CRAFT_DIRECTIVES` dict. Add before the `## Pitfalls to Avoid` section in each:

For `write_pitch`, add before pitfalls:
```python
        "## Document Structure\n"
        "The pitch is short (2-3 pages). Write as flowing prose with no mandatory sections. "
        "Natural paragraph breaks are sufficient.\n\n"
```

For `write_expose`, add before pitfalls:
```python
        "## Document Structure\n"
        "Structure the expose with markdown headers for major narrative movements. Use at minimum:\n"
        "- `## Premise` — logline and hook\n"
        "- `## Characters` — the ensemble with arcs\n"
        "- `## Story Arc` — three-movement architecture with turning points\n"
        "- `## Themes` — thematic argument\n"
        "Additional headers as needed for the story. These headers enable surgical revision in later rounds.\n\n"
```

For `write_treatment`, add before pitfalls:
```python
        "## Document Structure\n"
        "Structure the treatment with markdown headers for major beats and sequences. Use named sections like:\n"
        "- `## The Opening` — setup and inciting incident\n"
        "- `## The Rising Action` — progressive complications\n"
        "- `## The Midpoint Reversal` — the shift that redefines the story\n"
        "- `## The Crisis` — stakes at their highest\n"
        "- `## The Climax` — the final confrontation\n"
        "- `## The Resolution` — new equilibrium\n"
        "Name sections to match the story's actual content, not generic labels. "
        "These headers enable surgical revision in later rounds.\n\n"
```

For `write_concept`, add before pitfalls:
```python
        "## Document Structure\n"
        "Structure the concept with markdown headers for each bible component:\n"
        "- `## Story Engine` — the renewable conflict mechanism\n"
        "- `## Tone & Style` — tonal pillars and reference touchstones\n"
        "- `## World Rules` — what makes this world distinct\n"
        "- `## Characters` — the ensemble web\n"
        "- `## Saga Arc` — the multi-season journey\n"
        "- `## Season One` — the first season arc\n"
        "- `## Episode 1: [Title]`, `## Episode 2: [Title]`, etc. — per-episode overviews\n"
        "- `## Future Seasons` — where seasons 2+ go\n"
        "These headers enable surgical revision in later rounds.\n\n"
```

For `write_first_draft`, add before pitfalls:
```python
        "## Document Structure\n"
        "Structure depends on medium:\n"
        "- SCREENPLAY: Use standard screenplay format. Scenes are identified by sluglines "
        "(INT./EXT. LOCATION - TIME). Do NOT add markdown headers — use native format.\n"
        "- NOVEL/PROSE: Use chapter headers (`## Chapter 1: [Title]`).\n"
        "- STAGE PLAY: Use act and scene headers (`## Act I, Scene 1`).\n"
        "These structural markers enable surgical revision in later rounds.\n\n"
```

- [ ] **Step 4: Run tests**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStructureRequirements -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): add document structure requirements to CRAFT_DIRECTIVES

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Revision-aware document creation + locking

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` — `_create_stage_documents`, `_create_deliverable_and_research_docs`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
class TestRevisionAwareDocCreation:
    @pytest.fixture
    def leader_blueprint(self):
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        return WritersRoomLeaderBlueprint()

    @pytest.fixture
    def mock_leader_agent(self, db):
        from agents.models import Agent
        from projects.models import Department, Project

        project = Project.objects.create(name="Test", goal="Test story")
        dept = Department.objects.create(project=project, name="WR", department_type="writers_room")
        return Agent.objects.create(
            department=dept, name="Showrunner", agent_type="leader",
            is_leader=True, status="active", internal_state={},
        )

    @pytest.mark.django_db
    def test_new_documents_are_locked(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent, stage="pitch", version=1,
            doc_types=["stage_deliverable"], contents={"stage_deliverable": "The pitch"},
        )
        doc = Document.objects.filter(department=mock_leader_agent.department, doc_type="stage_deliverable").first()
        assert doc.is_locked is True

    @pytest.mark.django_db
    def test_archived_documents_are_unlocked(self, leader_blueprint, mock_leader_agent):
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent, stage="pitch", version=1,
            doc_types=["stage_deliverable"], contents={"stage_deliverable": "v1"},
        )
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent, stage="pitch", version=2,
            doc_types=["stage_deliverable"], contents={"stage_deliverable": "v2"},
        )
        archived = Document.objects.filter(
            department=mock_leader_agent.department, doc_type="stage_deliverable", is_archived=True
        ).first()
        assert archived.is_locked is False

    @pytest.mark.django_db
    def test_revision_json_applied_to_existing_doc(self, leader_blueprint, mock_leader_agent):
        """When task report is valid revision JSON, apply edits to existing doc."""
        import json

        # Create v1 document
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent, stage="pitch", version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "The old pitch content. This part stays."},
        )
        # Simulate revision JSON
        revision_json = json.dumps({
            "revisions": [
                {"type": "replace", "old_text": "The old pitch content.", "new_text": "The new pitch content."}
            ],
            "preserved": "Kept: This part stays.",
        })
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
        """When task report is plain prose (not JSON), use as full replacement."""
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent, stage="pitch", version=1,
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
        assert applied is False  # was not applied as revision, used as replacement
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestRevisionAwareDocCreation -v`
Expected: FAIL

- [ ] **Step 3: Update `_create_stage_documents` to lock new docs and unlock archived ones**

In `backend/agents/blueprints/writers_room/leader/agent.py`, modify `_create_stage_documents`:

```python
    def _create_stage_documents(self, agent, stage, version, doc_types, contents, sprint=None):
        """Create stage documents, archiving prior versions if they exist."""
        effective = self._get_effective_stage(agent, stage)
        stage_display = effective.replace("_", " ").title()
        label_map = {
            "stage_deliverable": "Deliverable",
            "stage_research": "Research & Notes",
            "stage_critique": "Critique",
        }

        for doc_type in doc_types:
            content = contents.get(doc_type, "")
            if not content:
                continue

            label = label_map.get(doc_type, doc_type)
            title = f"{stage_display} v{version} — {label}"

            existing = Document.objects.filter(
                department=agent.department,
                doc_type=doc_type,
                is_archived=False,
                title__startswith=f"{stage_display} v",
            ).first()

            new_doc = Document.objects.create(
                department=agent.department,
                doc_type=doc_type,
                title=title,
                content=content,
                sprint=sprint,
                is_locked=True,
            )

            if existing:
                existing.is_locked = False
                existing.is_archived = True
                existing.consolidated_into = new_doc
                existing.save(update_fields=["is_locked", "is_archived", "consolidated_into", "updated_at"])
```

- [ ] **Step 4: Add `_apply_revision_or_replace` helper**

Add to `WritersRoomLeaderBlueprint`:

```python
    def _apply_revision_or_replace(
        self, agent, doc_type: str, new_content: str, stage: str
    ) -> tuple[str, bool]:
        """Try to parse new_content as revision JSON and apply to existing doc.

        Returns (final_content, was_revision_applied).
        If new_content is not valid revision JSON, returns it as-is for full replacement.
        """
        # Try to parse as revision JSON
        try:
            data = json.loads(new_content)
            if isinstance(data, dict) and "revisions" in data and isinstance(data["revisions"], list):
                # It's revision format — find existing document and apply
                effective = self._get_effective_stage(agent, stage)
                stage_display = effective.replace("_", " ").title()
                existing_doc = Document.objects.filter(
                    department=agent.department,
                    doc_type=doc_type,
                    is_archived=False,
                    title__startswith=f"{stage_display} v",
                ).first()
                if existing_doc and existing_doc.content:
                    revised, failed = self._apply_revisions(existing_doc.content, data["revisions"])
                    if failed:
                        logger.warning(
                            "Writers Room: %d revision(s) failed for %s: %s",
                            len(failed),
                            doc_type,
                            failed,
                        )
                    return revised, True
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

        # Not revision format — return as-is for full replacement
        return new_content, False
```

- [ ] **Step 5: Update `_create_deliverable_and_research_docs` to use revision-aware creation**

Modify `_create_deliverable_and_research_docs` to apply revisions on iteration > 0. Replace the contents-building section:

```python
    def _create_deliverable_and_research_docs(self, agent, stage, sprint=None):
        """Create Deliverable and Research & Notes documents."""
        from agents.models import AgentTask

        internal_state = agent.internal_state or {}
        iteration = internal_state.get("stage_status", {}).get(stage, {}).get("iterations", 0)
        version = iteration + 1

        lead_writer_task = (
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type="lead_writer",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        raw_deliverable = lead_writer_task.report if lead_writer_task else ""

        effective_stage = self._get_effective_stage(agent, stage)
        creative_types = CREATIVE_MATRIX.get(effective_stage, [])
        creative_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=creative_types,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[: len(creative_types) * 2]
            .values_list("agent__agent_type", "agent__name", "report")
        )

        # Build research content — always full concatenation (creative agents may have
        # output revision JSON for their own sections, but we assemble the full doc)
        research_parts = []
        for agent_type, agent_name, report in creative_tasks:
            if report:
                # Try to apply revisions if this is a revision round
                if iteration > 0:
                    content, was_revision = self._apply_revision_or_replace(
                        agent, "stage_research", report, stage
                    )
                    # For research docs, if it was a revision, the content was already
                    # applied to the existing doc. But since we rebuild from agent reports,
                    # we use the raw report (the agent's full revised section).
                    # The revision format is only for the Lead Writer's deliverable.
                    research_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
                else:
                    research_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
        research_content = "\n\n---\n\n".join(research_parts)

        # Deliverable: apply revisions if iteration > 0
        if raw_deliverable and iteration > 0:
            deliverable_content, was_revision = self._apply_revision_or_replace(
                agent, "stage_deliverable", raw_deliverable, stage
            )
            if was_revision:
                logger.info("Writers Room: applied revision to stage deliverable for '%s' v%d", stage, version)
        else:
            deliverable_content = raw_deliverable

        contents = {}
        if deliverable_content:
            contents["stage_deliverable"] = deliverable_content
        if research_content:
            contents["stage_research"] = research_content

        if contents:
            self._create_stage_documents(
                agent=agent,
                stage=stage,
                version=version,
                doc_types=list(contents.keys()),
                contents=contents,
                sprint=sprint,
            )
```

- [ ] **Step 6: Run tests**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestRevisionAwareDocCreation -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): revision-aware doc creation with locking

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Inject revision instructions into task proposals

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` — `_propose_lead_writer_task`, `_propose_creative_tasks`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
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
        assert "revision" not in step_plan.lower() or "revisions" not in step_plan.lower()
        assert '"type"' not in step_plan

    def test_lead_writer_iteration_1_has_revision_instructions(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.internal_state = {
            "format_type": "standalone",
            "current_stage": "pitch",
            "stage_status": {"pitch": {"status": "creative_done", "iterations": 1}},
        }
        result = leader_blueprint._propose_lead_writer_task(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "revision" in step_plan.lower() or "revisions" in step_plan.lower()
        assert "replace" in step_plan.lower()
        assert "old_text" in step_plan or "old_text" in step_plan

    def test_creative_agents_iteration_0_no_revision(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.internal_state = {"stage_status": {"pitch": {"iterations": 0}}, "current_stage": "pitch"}
        mock_agent.get_config_value.return_value = None
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "revision JSON" not in step_plan

    def test_creative_agents_iteration_1_has_revision(self, leader_blueprint):
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = ["story_researcher"]
        mock_agent.internal_state = {"stage_status": {"pitch": {"iterations": 1}}, "current_stage": "pitch"}
        mock_agent.get_config_value.return_value = None
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = leader_blueprint._propose_creative_tasks(mock_agent, "pitch", {"locale": "en"})
        step_plan = result["tasks"][0]["step_plan"]
        assert "Critique" in step_plan or "critique" in step_plan
        assert "preserve" in step_plan.lower() or "revise only" in step_plan.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestRevisionInstructions -v`
Expected: FAIL

- [ ] **Step 3: Add revision instructions to `_propose_lead_writer_task`**

In `_propose_lead_writer_task`, after building `stage_display` and before the `return` statement, add iteration-aware step_plan:

```python
    def _propose_lead_writer_task(self, agent: Agent, stage: str, config: dict) -> dict:
        """Dispatch the lead_writer to synthesize creative fragments."""
        internal_state = agent.internal_state or {}
        format_type = internal_state.get("format_type", "standalone")
        locale = config.get("locale", "en")
        iteration = internal_state.get("stage_status", {}).get(stage, {}).get("iterations", 0)

        if stage == "pitch":
            command_name = "write_pitch"
        elif stage == "expose":
            command_name = "write_expose"
        elif stage == "treatment":
            command_name = "write_concept" if format_type == "series" else "write_treatment"
        elif stage == "first_draft":
            command_name = "write_first_draft"
        else:
            command_name = "write_pitch"

        stage_display = "concept" if (stage == "treatment" and format_type == "series") else stage

        if iteration == 0:
            step_plan = (
                f"Locale: {locale}\nFormat: {format_type}\nStage: {stage_display}\n\n"
                "Synthesize ALL creative agents' work from this round into a single cohesive "
                f"'{stage_display}' document. Consult department documents for all creative "
                "output and prior stage deliverables.\n\n"
                "CRITICAL: Do NOT invent new elements. Use the story_architect's structure, "
                "character_designer's ensemble, dialog_writer's voice work, and "
                "story_researcher's research exactly as provided.\n\n"
                f"Your output must be in {locale}."
            )
        else:
            # Determine available operations based on stage
            if stage == "pitch":
                ops_note = "Available operations: replace (surgical text edits)."
            elif stage == "first_draft":
                ops_note = (
                    "Available operations: replace (surgical text edits), "
                    "replace_between (replace passage between two anchor texts, inclusive)."
                )
            else:
                ops_note = (
                    "Available operations: replace (surgical text edits), "
                    "replace_section (replace everything under a markdown header)."
                )

            step_plan = (
                f"Locale: {locale}\nFormat: {format_type}\nStage: {stage_display}\n"
                f"Round: {iteration + 1} (REVISION)\n\n"
                "## REVISION MODE\n"
                "The current Stage Deliverable and the Critique are in the department documents. "
                "Your job is to REVISE the existing deliverable, NOT rewrite it.\n\n"
                "Output your changes as revision JSON:\n"
                "```json\n"
                '{\n'
                '  "revisions": [\n'
                '    {"type": "replace", "old_text": "exact text from document", '
                '"new_text": "revised text"},\n'
                '    {"type": "replace_section", "section": "## Section Header", '
                '"new_content": "new section content"},\n'
                '    {"type": "replace_between", "start": "anchor start", '
                '"end": "anchor end", "new_content": "new content"}\n'
                '  ],\n'
                '  "preserved": "Brief note on what was deliberately kept and why"\n'
                '}\n'
                "```\n\n"
                f"{ops_note}\n\n"
                "RULES:\n"
                "- Quote old_text EXACTLY from the existing document — character for character\n"
                "- Quote enough context for uniqueness (if old_text matches multiple times, the edit will fail)\n"
                "- For replace_section, use the exact markdown header from the document\n"
                "- For replace_between, quote unique start and end anchor passages\n"
                "- ONLY change what the Critique flagged. Everything else stays BYTE-IDENTICAL.\n"
                "- If the Critique praised a section, do NOT touch it.\n\n"
                "Read the Critique carefully. Address EVERY flagged issue. Preserve EVERYTHING praised.\n\n"
                f"Your output must be in {locale}."
            )

        return {
            "exec_summary": f"Stage '{stage_display}': Lead Writer synthesizes deliverable",
            "tasks": [
                {
                    "target_agent_type": "lead_writer",
                    "command_name": command_name,
                    "exec_summary": f"Write the {stage_display} — synthesize creative team output",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                }
            ],
            "_on_dispatch": {"set_status": "lead_writing", "stage": stage},
        }
```

- [ ] **Step 4: Add revision preamble to `_propose_creative_tasks`**

In `_propose_creative_tasks`, after building the `pitch_preamble` string (around line 783), add a revision preamble that gets prepended on revision rounds:

```python
            # Revision preamble for iteration > 0
            revision_preamble = ""
            current_iterations = internal_state.get("stage_status", {}).get(
                dispatch_stage, {}
            ).get("iterations", 0)
            if current_iterations > 0:
                revision_preamble = (
                    "## REVISION ROUND\n"
                    f"This is revision round {current_iterations + 1}. "
                    "Your previous output is in the Research & Notes document under your section header. "
                    "The Critique document lists what needs fixing.\n\n"
                    "REVISE ONLY what the Critique flagged. Preserve everything it praised or didn't mention. "
                    "Do NOT rewrite from scratch. If the Critique says your character work is strong but "
                    "the market positioning is weak, keep the character work EXACTLY as it was and fix "
                    "only the market positioning.\n\n"
                )
```

Then include it in the `step_plan` construction (around line 799-809):

```python
            task_data = {
                "target_agent_type": agent_type,
                "command_name": spec.get("command_name", ""),
                "exec_summary": spec["exec_summary"],
                "step_plan": (
                    f"Locale: {locale}\n{format_context}\n"
                    f"{revision_preamble}"
                    f"{pitch_preamble}"
                    f"{spec['step_plan']}\n\n"
                    f"FIDELITY CHECK (before submitting): Re-read the creator's pitch. "
                    f"Does your output preserve EVERY specific element they provided? "
                    f"If you introduced characters, conflicts, or structures the creator "
                    f"did NOT mention, ask yourself: did I copy this from a reference show? "
                    f"If yes, delete it and build from the creator's actual material instead.\n\n"
                    f"Your output must be in {locale}. This is non-negotiable."
                ),
                "depends_on_previous": previous_depends,
            }
```

- [ ] **Step 5: Run tests**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py::TestRevisionInstructions -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `cd backend && POSTGRES_PORT=5497 ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_skills_commands.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): inject revision instructions on iteration > 0

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Full test pass + lint

**Files:**
- Test: all writers room test files
- Lint: all modified files

- [ ] **Step 1: Run full writers room test suite**

Run: `cd backend && POSTGRES_PORT=5497 POSTGRES_USER=postgres POSTGRES_PASSWORD=secret POSTGRES_DB=core ../.venv/bin/python -m pytest agents/tests/test_writers_room_lead_writer.py agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_skills_commands.py -v`

- [ ] **Step 2: Fix any failures**

- [ ] **Step 3: Run lint on all modified files**

Run: `cd backend && ../.venv/bin/ruff check agents/blueprints/writers_room/ && ../.venv/bin/ruff format --check agents/blueprints/writers_room/`
Run: `cd backend && ../.venv/bin/ruff check projects/tasks_consolidation.py projects/models/document.py && ../.venv/bin/ruff format --check projects/tasks_consolidation.py projects/models/document.py`

- [ ] **Step 4: Check migration**

Run: `cd backend && POSTGRES_PORT=5497 POSTGRES_USER=postgres POSTGRES_PASSWORD=secret POSTGRES_DB=core python manage.py migrate --check`

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: test and lint fixes for revision mode

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

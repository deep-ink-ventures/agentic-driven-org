# Context Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a three-tier document consolidation system and remove all content truncations so agents work with full, fresh context.

**Architecture:** Leader agents write sprint progress documents after each task batch. Sprint lifecycle events and a monthly schedule trigger Claude-powered consolidation that merges older documents into topic-clustered summaries, archiving originals. A 500k-token volume safety net prevents runaway context growth.

**Tech Stack:** Django, Celery, Claude API (via existing `call_claude`), PostgreSQL migrations

---

### Task 1: Document Model — Add New Fields

**Files:**
- Modify: `backend/projects/models/document.py`
- Create: `backend/projects/migrations/0019_document_consolidation_fields.py` (auto-generated)
- Modify: `backend/projects/tests/test_models.py`

- [ ] **Step 1: Write the failing test for new Document fields**

In `backend/projects/tests/test_models.py`, add:

```python
class TestDocumentConsolidation:
    def test_document_has_consolidated_into_field(self, department):
        parent = Document.objects.create(
            title="Original",
            content="old content",
            department=department,
        )
        child = Document.objects.create(
            title="Consolidated",
            content="merged content",
            department=department,
            consolidated_into=parent,  # self-referential FK
        )
        assert child.consolidated_into == parent
        assert parent.consolidated_from.count() == 1

    def test_document_type_choices(self, department):
        doc = Document.objects.create(
            title="Sprint Progress",
            content="results",
            department=department,
            document_type="sprint_progress",
        )
        assert doc.document_type == "sprint_progress"

    def test_document_sprint_fk(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Write chapter 1",
            created_by=user,
        )
        sprint.departments.add(department)
        doc = Document.objects.create(
            title="Progress",
            content="done",
            department=department,
            sprint=sprint,
        )
        assert doc.sprint == sprint
        assert sprint.documents.count() == 1

    def test_consolidated_into_nullable(self, department):
        doc = Document.objects.create(
            title="Standalone",
            content="content",
            department=department,
        )
        assert doc.consolidated_into is None

    def test_document_type_default(self, department):
        doc = Document.objects.create(
            title="Test",
            content="content",
            department=department,
        )
        assert doc.document_type == "general"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest projects/tests/test_models.py::TestDocumentConsolidation -v`
Expected: FAIL — fields do not exist yet.

- [ ] **Step 3: Add fields to Document model**

In `backend/projects/models/document.py`, add these fields to the `Document` class and extend `DocType`:

```python
import uuid

from django.db import models


class Document(models.Model):
    class DocType(models.TextChoices):
        GENERAL = "general", "General"
        RESEARCH = "research", "Research"
        BRANDING = "branding", "Branding"
        STRATEGY = "strategy", "Strategy"
        CAMPAIGN = "campaign", "Campaign"
        VOICE_PROFILE = "voice_profile", "Voice Profile"
        CONCEPT = "concept", "Concept"
        SPRINT_PROGRESS = "sprint_progress", "Sprint Progress"
        SPRINT_SUMMARY = "sprint_summary", "Sprint Summary"
        MONTHLY_ARCHIVE = "monthly_archive", "Monthly Archive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, help_text="Document content in markdown")
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.GENERAL,
        db_index=True,
    )
    document_type = models.CharField(
        max_length=20,
        choices=[
            ("general", "General"),
            ("sprint_progress", "Sprint Progress"),
            ("sprint_summary", "Sprint Summary"),
            ("monthly_archive", "Monthly Archive"),
        ],
        default="general",
        db_index=True,
    )
    is_archived = models.BooleanField(default=False)
    consolidated_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consolidated_from",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    tags = models.ManyToManyField("projects.Tag", blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
```

- [ ] **Step 4: Generate and apply migration**

Run: `cd backend && python manage.py makemigrations projects -n document_consolidation_fields && python manage.py migrate`

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest projects/tests/test_models.py::TestDocumentConsolidation -v`
Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/models/document.py backend/projects/migrations/0019_document_consolidation_fields.py backend/projects/tests/test_models.py
git commit -m "feat: add consolidated_into, document_type, sprint FK to Document model"
```

---

### Task 2: Consolidation Celery Tasks

**Files:**
- Create: `backend/projects/tasks_consolidation.py`
- Modify: `backend/projects/tests/test_tasks.py`

- [ ] **Step 1: Write failing tests for consolidation tasks**

In `backend/projects/tests/test_tasks.py`, add:

```python
from unittest.mock import patch

from projects.models import Document, Sprint
from projects.tasks_consolidation import (
    consolidate_sprint_documents,
    consolidate_monthly_documents,
    consolidate_department_documents,
)


class TestConsolidateSprintDocuments:
    def test_merges_sprint_docs_into_summary(self, user, department):
        sprint = Sprint.objects.create(
            project=department.project,
            text="Write pilot",
            created_by=user,
        )
        sprint.departments.add(department)

        doc1 = Document.objects.create(
            title="Sprint Progress — Write pilot — Batch 1",
            content="Character analysis completed. Found three viable protagonists.",
            department=department,
            document_type="sprint_progress",
            sprint=sprint,
        )
        doc2 = Document.objects.create(
            title="Sprint Progress — Write pilot — Batch 2",
            content="Story outline drafted. Three-act structure with B-plot.",
            department=department,
            document_type="sprint_progress",
            sprint=sprint,
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Sprint Summary: Write pilot\n\nCharacter analysis identified three protagonists. "
                "Story outline uses three-act structure with B-plot.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_sprint_documents(str(sprint.id))

        # Originals archived
        doc1.refresh_from_db()
        doc2.refresh_from_db()
        assert doc1.is_archived is True
        assert doc2.is_archived is True

        # New summary created
        summary = Document.objects.filter(
            department=department,
            document_type="sprint_summary",
            sprint=sprint,
            is_archived=False,
        ).first()
        assert summary is not None
        assert "Sprint Summary" in summary.title
        assert doc1.consolidated_into == summary
        assert doc2.consolidated_into == summary

    def test_no_docs_does_nothing(self, user, department):
        sprint = Sprint.objects.create(
            project=department.project,
            text="Empty sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            consolidate_sprint_documents(str(sprint.id))
            mock_claude.assert_not_called()


class TestConsolidateMonthlyDocuments:
    def test_merges_old_docs_per_department(self, user, department):
        from django.utils import timezone
        from datetime import timedelta

        old_date = timezone.now() - timedelta(days=35)

        doc1 = Document.objects.create(
            title="Old research",
            content="Market analysis from last month.",
            department=department,
            document_type="sprint_summary",
        )
        Document.objects.filter(id=doc1.id).update(created_at=old_date)

        doc2 = Document.objects.create(
            title="Old findings",
            content="Competitor review from last month.",
            department=department,
            document_type="sprint_summary",
        )
        Document.objects.filter(id=doc2.id).update(created_at=old_date)

        # Recent doc should NOT be archived
        recent = Document.objects.create(
            title="Fresh doc",
            content="Just created.",
            department=department,
            document_type="sprint_progress",
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Monthly Archive\n\nMarket analysis and competitor review consolidated.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_monthly_documents()

        doc1.refresh_from_db()
        doc2.refresh_from_db()
        recent.refresh_from_db()
        assert doc1.is_archived is True
        assert doc2.is_archived is True
        assert recent.is_archived is False

        archive = Document.objects.filter(
            department=department,
            document_type="monthly_archive",
            is_archived=False,
        ).first()
        assert archive is not None


class TestConsolidateDepartmentDocuments:
    def test_triggers_when_over_threshold(self, department):
        # Create a doc with content that exceeds threshold when token-estimated
        big_content = "word " * 200000  # ~200k words ≈ ~266k tokens
        Document.objects.create(
            title="Huge doc 1",
            content=big_content,
            department=department,
        )
        Document.objects.create(
            title="Huge doc 2",
            content=big_content,
            department=department,
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            mock_claude.return_value = (
                "# Consolidated\n\nMerged content.",
                {"input_tokens": 100, "output_tokens": 50},
            )
            consolidate_department_documents(str(department.id))

        # Should have consolidated
        assert Document.objects.filter(department=department, is_archived=True).count() == 2

    def test_skips_when_under_threshold(self, department):
        Document.objects.create(
            title="Small doc",
            content="Just a few words.",
            department=department,
        )

        with patch("projects.tasks_consolidation.call_claude") as mock_claude:
            consolidate_department_documents(str(department.id))
            mock_claude.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest projects/tests/test_tasks.py::TestConsolidateSprintDocuments -v`
Expected: FAIL — module does not exist yet.

- [ ] **Step 3: Implement consolidation tasks**

Create `backend/projects/tasks_consolidation.py`:

```python
"""Document consolidation tasks.

Three-tier consolidation:
1. Sprint-end: merge all sprint progress docs into one summary per department.
2. Monthly: merge all docs older than 30 days into topic-clustered archives.
3. Volume: emergency consolidation when a department exceeds 500k tokens.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Sum, F
from django.db.models.functions import Length
from django.utils import timezone

from agents.claude_client import call_claude

logger = logging.getLogger(__name__)

# ~500k tokens ≈ ~1.5M characters (rough 1:3 ratio for English text)
VOLUME_THRESHOLD_CHARS = 1_500_000


def _consolidate_documents(documents, department, document_type, title_prefix, instruction):
    """Shared consolidation logic: Claude reads documents, produces a summary, archives originals."""
    if not documents:
        return None

    docs_text = ""
    for doc in documents:
        docs_text += f"\n\n--- [{doc.doc_type}] {doc.title} (created {doc.created_at.date()}) ---\n{doc.content}"

    system_prompt = (
        "You are a knowledge consolidator. Your job is to merge multiple documents into a comprehensive, "
        "well-organized summary. Preserve ALL meaningful detail — findings, decisions, artifacts, outcomes. "
        "Organize by topic. Drop only information that is clearly outdated or superseded by newer content. "
        "Write in markdown. Be thorough — this summary replaces the originals."
    )

    user_message = f"""{instruction}

## Department: {department.name}

## Documents to consolidate:
{docs_text}

Write the consolidated document now."""

    response, _usage = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=16384,
    )

    from projects.models import Document

    summary = Document.objects.create(
        title=f"{title_prefix} — {department.name} — {timezone.now().strftime('%Y-%m-%d')}",
        content=response,
        department=department,
        document_type=document_type,
        doc_type=Document.DocType.GENERAL,
    )

    # Archive originals and link them to the new summary
    for doc in documents:
        doc.is_archived = True
        doc.consolidated_into = summary
        doc.save(update_fields=["is_archived", "consolidated_into", "updated_at"])

    logger.info(
        "Consolidated %d documents into '%s' for department %s",
        len(documents),
        summary.title,
        department.name,
    )
    return summary


@shared_task
def consolidate_sprint_documents(sprint_id):
    """Merge all sprint progress documents into one summary per department."""
    from projects.models import Document, Sprint

    sprint = Sprint.objects.get(id=sprint_id)

    for department in sprint.departments.all():
        docs = list(
            Document.objects.filter(
                department=department,
                sprint=sprint,
                is_archived=False,
            )
            .exclude(document_type="sprint_summary")
            .order_by("created_at")
        )

        _consolidate_documents(
            documents=docs,
            department=department,
            document_type="sprint_summary",
            title_prefix=f"Sprint Summary: {sprint.text[:50]}",
            instruction=(
                f"Consolidate all progress documents from this sprint into one comprehensive summary.\n"
                f"Sprint instruction: {sprint.text}\n"
                f"Sprint status: {sprint.status}"
            ),
        )

        # Link the summary to the sprint
        summary = Document.objects.filter(
            department=department,
            document_type="sprint_summary",
            sprint__isnull=True,
            is_archived=False,
        ).order_by("-created_at").first()
        if summary:
            summary.sprint = sprint
            summary.save(update_fields=["sprint", "updated_at"])


@shared_task
def consolidate_monthly_documents():
    """Monthly: merge all non-archived documents older than 30 days per department."""
    from projects.models import Department, Document

    cutoff = timezone.now() - timedelta(days=30)

    departments_with_old_docs = (
        Document.objects.filter(
            is_archived=False,
            created_at__lt=cutoff,
        )
        .values_list("department_id", flat=True)
        .distinct()
    )

    for dept_id in departments_with_old_docs:
        department = Department.objects.get(id=dept_id)
        docs = list(
            Document.objects.filter(
                department=department,
                is_archived=False,
                created_at__lt=cutoff,
            ).order_by("created_at")
        )

        _consolidate_documents(
            documents=docs,
            department=department,
            document_type="monthly_archive",
            title_prefix="Monthly Archive",
            instruction=(
                "Consolidate these older documents into a comprehensive archive. "
                "Drop information that is clearly outdated or no longer relevant. "
                "Organize by topic. This archive represents the department's historical knowledge."
            ),
        )


@shared_task
def consolidate_department_documents(department_id):
    """Emergency consolidation when department context exceeds volume threshold."""
    from projects.models import Department, Document

    department = Department.objects.get(id=department_id)

    active_docs = Document.objects.filter(department=department, is_archived=False)
    total_chars = active_docs.aggregate(total=Sum(Length("content")))["total"] or 0

    if total_chars < VOLUME_THRESHOLD_CHARS:
        return

    logger.warning(
        "VOLUME_THRESHOLD department=%s chars=%d threshold=%d — triggering consolidation",
        department.name,
        total_chars,
        VOLUME_THRESHOLD_CHARS,
    )

    docs = list(active_docs.order_by("created_at"))

    _consolidate_documents(
        documents=docs,
        department=department,
        document_type="monthly_archive",
        title_prefix="Volume Consolidation",
        instruction=(
            "This department's context has grown too large. Consolidate ALL documents into a compact, "
            "topic-organized set. Preserve everything still relevant. Drop only clearly outdated information."
        ),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest projects/tests/test_tasks.py::TestConsolidateSprintDocuments projects/tests/test_tasks.py::TestConsolidateMonthlyDocuments projects/tests/test_tasks.py::TestConsolidateDepartmentDocuments -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/projects/tasks_consolidation.py backend/projects/tests/test_tasks.py
git commit -m "feat: add three-tier document consolidation celery tasks"
```

---

### Task 3: Wire Sprint Lifecycle to Consolidation via post_save Signal

**Files:**
- Create: `backend/projects/signals.py`
- Modify: `backend/projects/apps.py`
- Modify: `backend/projects/tests/test_sprints.py`

Single source of truth: a `post_save` signal on `Sprint` triggers consolidation whenever the sprint status changes to DONE or PAUSED, regardless of whether the change comes from the view or from leader code in `base.py`.

- [ ] **Step 1: Write failing test for sprint signal**

In `backend/projects/tests/test_sprints.py`, add:

```python
from unittest.mock import patch, MagicMock


class TestSprintConsolidationSignal:
    def test_sprint_done_triggers_consolidation(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.DONE
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_called_once_with(str(sprint.id))

    def test_sprint_paused_triggers_consolidation(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.PAUSED
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_called_once_with(str(sprint.id))

    def test_sprint_running_does_not_trigger(self, user, department):
        from projects.models import Sprint

        sprint = Sprint.objects.create(
            project=department.project,
            text="Test sprint",
            status=Sprint.Status.PAUSED,
            created_by=user,
        )
        sprint.departments.add(department)

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint.status = Sprint.Status.RUNNING
            sprint.save(update_fields=["status", "updated_at"])
            mock_task.delay.assert_not_called()

    def test_sprint_create_does_not_trigger(self, user, department):
        from projects.models import Sprint

        with patch("projects.signals.consolidate_sprint_documents") as mock_task:
            mock_task.delay = MagicMock()
            sprint = Sprint.objects.create(
                project=department.project,
                text="New sprint",
                created_by=user,
            )
            mock_task.delay.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest projects/tests/test_sprints.py::TestSprintConsolidationSignal -v`
Expected: FAIL — signal does not exist yet.

- [ ] **Step 3: Create the signal handler**

Create `backend/projects/signals.py`:

```python
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="projects.Sprint")
def trigger_sprint_consolidation(sender, instance, created, **kwargs):
    """Trigger document consolidation when a sprint is done or paused."""
    if created:
        return

    if instance.status in ("done", "paused"):
        from projects.tasks_consolidation import consolidate_sprint_documents

        consolidate_sprint_documents.delay(str(instance.id))
        logger.info(
            "Sprint %s status=%s — triggered document consolidation",
            instance.id,
            instance.status,
        )
```

- [ ] **Step 4: Register the signal in apps.py**

In `backend/projects/apps.py`, add the `ready()` method:

```python
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"

    def ready(self):
        import projects.signals  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest projects/tests/test_sprints.py::TestSprintConsolidationSignal -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/signals.py backend/projects/apps.py backend/projects/tests/test_sprints.py
git commit -m "feat: trigger document consolidation via post_save signal on Sprint"
```

---

### Task 4: Leader Document Creation (per batch)

**Files:**
- Modify: `backend/agents/blueprints/base.py:960-1103` (generate_sprint_proposal method)
- Modify: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write failing test for leader document creation**

In `backend/agents/tests/test_blueprints.py`, add:

```python
from unittest.mock import patch, MagicMock
from projects.models import Document, Sprint


class TestLeaderDocumentCreation:
    def test_leader_writes_progress_doc_before_planning(self, db, department, user):
        from agents.models import Agent, AgentTask

        sprint = Sprint.objects.create(
            project=department.project,
            text="Write pilot episode",
            created_by=user,
        )
        sprint.departments.add(department)

        leader = Agent.objects.create(
            name="Test Leader",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
        )

        # Create completed tasks with reports
        task1 = AgentTask.objects.create(
            agent=leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Analyze characters",
            report="Found three strong protagonist candidates with distinct arcs.",
        )
        task2 = AgentTask.objects.create(
            agent=leader,
            sprint=sprint,
            status=AgentTask.Status.DONE,
            exec_summary="Draft outline",
            report="Three-act structure with dual timelines established.",
        )

        # Count docs before
        docs_before = Document.objects.filter(department=department).count()

        # Mock call_claude to return a sprint proposal
        with patch("agents.blueprints.base.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"sprint_done": false, "exec_summary": "Next task", '
                '"tasks": [{"target_agent_type": "story_architect", '
                '"command_name": "write", "exec_summary": "Write act 1", '
                '"step_plan": "Draft the first act.", "depends_on_previous": false}]}',
                {"input_tokens": 100, "output_tokens": 50},
            )

            blueprint = leader.get_blueprint()
            result = blueprint.generate_sprint_proposal(leader)

        # A progress document should have been created
        progress_docs = Document.objects.filter(
            department=department,
            document_type="sprint_progress",
            sprint=sprint,
        )
        assert progress_docs.count() == 1
        doc = progress_docs.first()
        assert "Analyze characters" in doc.content or "protagonist" in doc.content
        assert doc.is_archived is False

    def test_no_progress_doc_when_no_completed_tasks(self, db, department, user):
        sprint = Sprint.objects.create(
            project=department.project,
            text="Fresh sprint",
            created_by=user,
        )
        sprint.departments.add(department)

        leader = Agent.objects.create(
            name="Test Leader",
            agent_type="leader",
            department=department,
            is_leader=True,
            status="active",
        )

        docs_before = Document.objects.filter(department=department).count()

        with patch("agents.blueprints.base.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"sprint_done": false, "exec_summary": "First task", '
                '"tasks": [{"target_agent_type": "story_architect", '
                '"command_name": "write", "exec_summary": "Start writing", '
                '"step_plan": "Begin.", "depends_on_previous": false}]}',
                {"input_tokens": 100, "output_tokens": 50},
            )

            blueprint = leader.get_blueprint()
            result = blueprint.generate_sprint_proposal(leader)

        # No progress doc when there are no completed tasks to summarize
        assert Document.objects.filter(department=department).count() == docs_before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestLeaderDocumentCreation -v`
Expected: FAIL — no document creation logic yet.

- [ ] **Step 3: Implement leader document creation in generate_sprint_proposal**

In `backend/agents/blueprints/base.py`, in the `generate_sprint_proposal()` method, after the `completed_tasks` query (around line 988-1001) and before the Claude call, add the progress document creation logic. Insert after `completed_text` is built:

```python
        # Write a progress document if there are completed tasks to capture
        if completed_tasks:
            self._write_sprint_progress_document(department, sprint, completed_tasks)
```

Then add this new method to the `BaseBlueprint` class (after `generate_sprint_proposal`):

```python
    def _write_sprint_progress_document(self, department, sprint, completed_tasks):
        """Write a sprint progress document capturing completed task results."""
        from projects.models import Document

        # Count existing progress docs for this sprint to determine batch number
        batch_num = (
            Document.objects.filter(
                department=department,
                sprint=sprint,
                document_type="sprint_progress",
            ).count()
            + 1
        )

        # Check if there are new tasks since the last progress doc
        last_progress = (
            Document.objects.filter(
                department=department,
                sprint=sprint,
                document_type="sprint_progress",
            )
            .order_by("-created_at")
            .first()
        )

        if last_progress:
            new_tasks = [
                (summary, report)
                for summary, report in completed_tasks
                if report  # Only tasks with reports
            ]
            # If no new reports since last doc, skip
            # (Simple heuristic: compare count of completed tasks vs what we've documented)
            existing_task_count = sum(
                1
                for line in (last_progress.content or "").split("\n")
                if line.startswith("## Task:")
            )
            if len(new_tasks) <= existing_task_count:
                return

        # Build document content from task reports
        content_parts = [f"# Sprint Progress — Batch {batch_num}\n"]
        content_parts.append(f"**Sprint:** {sprint.text}\n")
        content_parts.append(f"**Date:** {timezone.now().strftime('%Y-%m-%d %H:%M')}\n")

        for summary, report in completed_tasks:
            content_parts.append(f"\n## Task: {summary}\n")
            if report:
                content_parts.append(f"{report}\n")
            else:
                content_parts.append("*No report provided.*\n")

        Document.objects.create(
            title=f"Sprint Progress — {sprint.text[:50]} — Batch {batch_num}",
            content="\n".join(content_parts),
            department=department,
            document_type="sprint_progress",
            doc_type=Document.DocType.GENERAL,
            sprint=sprint,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestLeaderDocumentCreation -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_blueprints.py
git commit -m "feat: leader writes sprint progress document before planning next batch"
```

---

### Task 5: Monthly Consolidation via Celery Beat

**Files:**
- Modify: `backend/config/settings.py:151-177`
- Modify: `backend/projects/tasks.py:293-309`

- [ ] **Step 1: Add monthly consolidation to celery beat schedule**

In `backend/config/settings.py`, add to `CELERY_BEAT_SCHEDULE`:

```python
    "consolidate-monthly-documents": {
        "task": "projects.tasks_consolidation.consolidate_monthly_documents",
        "schedule": crontab(day_of_month="1", hour="3", minute="0"),  # 1st of month at 3am
    },
```

Add the import at the top of the celery beat section:

```python
from celery.schedules import crontab
```

- [ ] **Step 2: Update archive_stale_documents to defer to consolidation**

In `backend/projects/tasks.py`, replace the `archive_stale_documents` function. Since the monthly consolidation now handles archiving with proper consolidation, the daily task should only archive research docs that are between consolidation runs:

```python
@shared_task
def archive_stale_documents():
    """Daily: archive research documents older than 30 days.

    Note: This is a simple cleanup for research docs. Full consolidation
    (with Claude-powered merging) runs monthly via consolidate_monthly_documents.
    """
    from datetime import timedelta

    from django.utils import timezone

    from projects.models import Document

    cutoff = timezone.now() - timedelta(days=30)
    count = Document.objects.filter(
        doc_type=Document.DocType.RESEARCH,
        is_archived=False,
        created_at__lt=cutoff,
    ).update(is_archived=True)

    if count:
        logger.info("Archived %d stale research documents", count)
```

- [ ] **Step 3: Verify celery beat configuration loads**

Run: `cd backend && python -c "from config.settings import CELERY_BEAT_SCHEDULE; print(list(CELERY_BEAT_SCHEDULE.keys()))"`
Expected: Output includes `"consolidate-monthly-documents"`.

- [ ] **Step 4: Commit**

```bash
git add backend/config/settings.py backend/projects/tasks.py
git commit -m "feat: add monthly document consolidation to celery beat schedule"
```

---

### Task 6: Volume Safety Net in get_context()

**Files:**
- Modify: `backend/agents/blueprints/base.py:241-297`
- Modify: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write failing test for volume check**

In `backend/agents/tests/test_blueprints.py`, add:

```python
class TestVolumeThresholdCheck:
    def test_triggers_consolidation_when_over_threshold(self, db, department):
        from unittest.mock import patch

        # Create docs totaling over 1.5M chars
        big_content = "word " * 400000  # ~2M chars
        Document.objects.create(
            title="Huge doc",
            content=big_content,
            department=department,
        )

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="test",
            department=department,
            status="active",
        )

        with patch("agents.blueprints.base.consolidate_department_documents") as mock_task:
            mock_task.delay = MagicMock()
            blueprint = agent.get_blueprint()
            ctx = blueprint.get_context(agent)
            mock_task.delay.assert_called_once_with(str(department.id))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestVolumeThresholdCheck -v`
Expected: FAIL.

- [ ] **Step 3: Add volume check to get_context()**

In `backend/agents/blueprints/base.py`, at the beginning of `get_context()`, after the docs query, add a volume check:

```python
        # Volume safety net — trigger async consolidation if context is too large
        total_chars = sum(len(content) for _, content, _, _ in docs)
        if total_chars > 1_500_000:  # ~500k tokens
            from projects.tasks_consolidation import consolidate_department_documents

            consolidate_department_documents.delay(str(department.id))
            logger.warning(
                "VOLUME_THRESHOLD dept=%s chars=%d — async consolidation triggered",
                department.name,
                total_chars,
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestVolumeThresholdCheck -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_blueprints.py
git commit -m "feat: add 500k-token volume safety net to get_context()"
```

---

### Task 7: Remove Content Truncations — base.py

**Files:**
- Modify: `backend/agents/blueprints/base.py`
- Modify: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write test that full content is passed to agents**

In `backend/agents/tests/test_blueprints.py`, add:

```python
class TestNoTruncation:
    def test_document_content_not_truncated(self, db, department):
        long_content = "A" * 5000
        Document.objects.create(
            title="Long doc",
            content=long_content,
            department=department,
        )

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="test",
            department=department,
            status="active",
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_content in ctx["department_documents"]

    def test_report_not_truncated(self, db, department):
        from agents.models import AgentTask

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="test",
            department=department,
            status="active",
        )

        long_report = "B" * 5000
        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.DONE,
            exec_summary="Test task with long report",
            report=long_report,
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_report in ctx["own_recent_tasks"]

    def test_exec_summary_not_truncated(self, db, department):
        from agents.models import AgentTask

        agent = Agent.objects.create(
            name="Test Agent",
            agent_type="test",
            department=department,
            status="active",
        )

        long_summary = "C" * 200
        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.DONE,
            exec_summary=long_summary,
            report="Short report",
        )

        blueprint = agent.get_blueprint()
        ctx = blueprint.get_context(agent)
        assert long_summary in ctx["own_recent_tasks"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestNoTruncation -v`
Expected: FAIL — content is still truncated.

- [ ] **Step 3: Remove truncations in get_context()**

In `backend/agents/blueprints/base.py`, make these changes:

**Line 258** — change `{content[:3000]}` to `{content}`:
```python
            docs_text += f"\n\n--- [{doc_type}{age_str}] {title} ---\n{content}"
```

**Line 279** — change `{e[:100]}` to `{e}`:
```python
                task_lines = "\n".join(f"  - [{s}] {e}" for e, s in recent)
```

**Line 285** — change `{es[:100]}` to `{es}`:
```python
            own_text += f"\n  - [{st}] {es}"
```

**Line 287** — change `{rp[:200]}` to `{rp}`:
```python
                own_text += f"\n    Report: {rp}"
```

- [ ] **Step 4: Remove truncations in review/escalation flow**

**Line 533** — change `{creator_task.exec_summary[:60]}` to `{creator_task.exec_summary}`:
```python
                "exec_summary": f"Escalation: {round_num} review rounds on {creator_task.exec_summary}",
```

**Line 538** — change `{creator_task.exec_summary[:60]}` to `{creator_task.exec_summary}`:
```python
                        "exec_summary": f"Human review needed: exceeded {MAX_REVIEW_ROUNDS} rounds — {creator_task.exec_summary}",
```

**Line 545** — change `(creator_task.report or "")[:3000]` to `(creator_task.report or "")`:
```python
        report_snippet = creator_task.report or ""
```

**Line 555** — change `{creator_task.exec_summary[:80]}` to `{creator_task.exec_summary}`:
```python
            "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary}",
```

**Line 560** — change `{creator_task.exec_summary[:80]}` to `{creator_task.exec_summary}`:
```python
                    "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary}",
```

**Line 712** — change `(review_task.report or "")[:3000]` to `(review_task.report or "")`:
```python
        review_snippet = review_task.report or ""
```

**Line 716** — change `{recent_creator.exec_summary[:60]}` to `{recent_creator.exec_summary}`:
```python
            "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}: {recent_creator.exec_summary}",
```

**Line 721** — change `{recent_creator.exec_summary[:60]}` to `{recent_creator.exec_summary}`:
```python
                    "exec_summary": f"Fix review issues (score {score}/10): {recent_creator.exec_summary}",
```

**Line 921** — change `{task.exec_summary[:200]}` to `{task.exec_summary}`:
```python
                    step_plan=f"Review and assess. Original task: {task.exec_summary}",
```

- [ ] **Step 5: Remove truncations in generate_sprint_proposal()**

**Line 1000** — change `{report[:300]}` to `{report}`:
```python
                entry += f"\n  Result: {report}"
```

**Line 1009** — change `(src.extracted_text or "")[:500] or (src.raw_content or "")[:500]` to full content:
```python
            text = src.summary or src.extracted_text or src.raw_content or ""
```

**Line 1011** — change `{text[:400]}` to `{text}`:
```python
                source_context += f"\n- {src.original_filename or 'Attached file'}: {text}"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_blueprints.py::TestNoTruncation -v`
Expected: All 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_blueprints.py
git commit -m "fix: remove all content truncations in base.py agent context"
```

---

### Task 8: Remove Content Truncations — projects/tasks.py, prompts.py, output_serializer.py

**Files:**
- Modify: `backend/projects/tasks.py:472,754`
- Modify: `backend/projects/prompts.py:64-65`
- Modify: `backend/projects/serializers/output_serializer.py:43-50`

- [ ] **Step 1: Remove truncation in projects/tasks.py line 472**

Change:
```python
            leader_system_prompt = leader_bp.system_prompt[:3000] if hasattr(leader_bp, "system_prompt") else ""
```
To:
```python
            leader_system_prompt = leader_bp.system_prompt if hasattr(leader_bp, "system_prompt") else ""
```

- [ ] **Step 2: Remove truncation in projects/tasks.py line 754**

Change:
```python
            bp_system_prompt = bp.system_prompt[:2000] if hasattr(bp, "system_prompt") else ""
```
To:
```python
            bp_system_prompt = bp.system_prompt if hasattr(bp, "system_prompt") else ""
```

- [ ] **Step 3: Remove truncation in projects/prompts.py line 64-65**

Change:
```python
        if len(text) > 10000:
            text = text[:10000] + "\n\n[... truncated ...]"
```
To:
```python
        # No truncation — full source content is passed to Claude
```

(Remove both lines and replace with the comment. The `text` variable is already set above.)

- [ ] **Step 4: Remove truncation in output_serializer.py**

Change the `to_representation` method in `OutputListSerializer`:
```python
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Truncate content in list view to 500 chars
        if data.get("content") and len(data["content"]) > 500:
            data["content"] = data["content"][:500] + "..."
        # Never expose file_key directly
        data.pop("file_key", None)
        return data
```
To:
```python
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Never expose file_key directly
        data.pop("file_key", None)
        return data
```

- [ ] **Step 5: Run existing tests to verify nothing breaks**

Run: `cd backend && python -m pytest projects/tests/test_tasks.py projects/tests/test_prompts.py projects/tests/test_serializers.py -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/projects/tasks.py backend/projects/prompts.py backend/projects/serializers/output_serializer.py
git commit -m "fix: remove content truncations in project tasks, prompts, and output serializer"
```

---

### Task 9: Remove Content Truncations — Writers Room Leader

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:1022,1073,1178-1188`
- Modify: `backend/agents/blueprints/writers_room/leader/commands/plan_room.py:55`

- [ ] **Step 1: Remove truncation at line 1022**

Change:
```python
                feedback_text += f"\n\n## {agent_type}\n{report[:3000]}"
```
To:
```python
                feedback_text += f"\n\n## {agent_type}\n{report}"
```

- [ ] **Step 2: Remove truncation at line 1073**

Change:
```python
        review_snippet = (review_task.report or "")[:3000]
```
To:
```python
        review_snippet = review_task.report or ""
```

- [ ] **Step 3: Remove truncation at lines 1178-1188**

Change:
```python
        snippet = text[:2000]
        if len(text) > 2000:
            snippet += f"\n[... truncated, {len(text)} chars total ...]"
        sources_summary += f"\n### {name} ({s.source_type})\n{snippet}\n"
```
To:
```python
        sources_summary += f"\n### {name} ({s.source_type})\n{text}\n"
```

- [ ] **Step 4: Remove truncation in plan_room.py line 55**

Change:
```python
        "\n".join(f"- ({at}) {es[:150]}" for es, at, _ in completed) if completed else "No completed tasks yet."
```
To:
```python
        "\n".join(f"- ({at}) {es}" for es, at, _ in completed) if completed else "No completed tasks yet."
```

- [ ] **Step 5: Run writers room tests**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_skills_commands.py -v`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/blueprints/writers_room/leader/commands/plan_room.py
git commit -m "fix: remove content truncations in writers room leader"
```

---

### Task 10: Remove Content Truncations — Engineering Leader & Workforce

**Files:**
- Modify: `backend/agents/blueprints/engineering/leader/agent.py:266,283,312,317,324,779`
- Modify: `backend/agents/blueprints/engineering/workforce/backend_engineer/agent.py:205`
- Modify: `backend/agents/blueprints/engineering/workforce/frontend_engineer/agent.py:230`
- Modify: `backend/agents/blueprints/engineering/leader/commands/plan_sprint.py:56`

- [ ] **Step 1: Remove truncation at engineering leader line 266**

Change:
```python
            "\n".join(f"- [{st}] ({at}) {es[:120]}" for es, st, at, _ in active_tasks)
```
To:
```python
            "\n".join(f"- [{st}] ({at}) {es}" for es, st, at, _ in active_tasks)
```

- [ ] **Step 2: Remove truncation at line 283**

Change:
```python
                context_text += f"\n- {area}: {ctx.get('summary', '')[:150]}"
```
To:
```python
                context_text += f"\n- {area}: {ctx.get('summary', '')}"
```

- [ ] **Step 3: Remove truncation at lines 312, 317**

Change:
```python
                "exec_summary": f"Escalation: {round_num} review rounds on {impl_task.exec_summary[:60]}",
```
To:
```python
                "exec_summary": f"Escalation: {round_num} review rounds on {impl_task.exec_summary}",
```

Change:
```python
                        "exec_summary": f"Human review needed: {impl_task.exec_summary[:80]} — exceeded {MAX_REVIEW_ROUNDS} rounds",
```
To:
```python
                        "exec_summary": f"Human review needed: {impl_task.exec_summary} — exceeded {MAX_REVIEW_ROUNDS} rounds",
```

- [ ] **Step 4: Remove truncation at line 324**

Change:
```python
        impl_report_snippet = (impl_task.report or "")[:3000]
```
To:
```python
        impl_report_snippet = impl_task.report or ""
```

- [ ] **Step 5: Remove truncation at line 779**

Change:
```python
            "summary": summary[:1000],  # Cap length
```
To:
```python
            "summary": summary,
```

- [ ] **Step 6: Remove truncation in backend_engineer line 205**

Change:
```python
                    context_parts.append(f"--- {fp} ---\n{content[:3000]}")
```
To:
```python
                    context_parts.append(f"--- {fp} ---\n{content}")
```

- [ ] **Step 7: Remove truncation in frontend_engineer line 230**

Change:
```python
                    context_parts.append(f"--- {fp} ---\n{content[:3000]}")
```
To:
```python
                    context_parts.append(f"--- {fp} ---\n{content}")
```

- [ ] **Step 8: Remove truncation in plan_sprint.py line 56**

Change:
```python
    completed_text = "\n".join(f"- {es[:150]}" for es, _ in completed) if completed else "No completed tasks yet."
```
To:
```python
    completed_text = "\n".join(f"- {es}" for es, _ in completed) if completed else "No completed tasks yet."
```

- [ ] **Step 9: Run engineering tests**

Run: `cd backend && python -m pytest agents/tests/ -v`
Expected: All PASS.

- [ ] **Step 10: Commit**

```bash
git add backend/agents/blueprints/engineering/leader/agent.py backend/agents/blueprints/engineering/workforce/backend_engineer/agent.py backend/agents/blueprints/engineering/workforce/frontend_engineer/agent.py backend/agents/blueprints/engineering/leader/commands/plan_sprint.py
git commit -m "fix: remove content truncations in engineering leader and workforce agents"
```

---

### Task 11: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run complete test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All tests pass. Note any failures.

- [ ] **Step 2: Run migrations check**

Run: `cd backend && python manage.py makemigrations --check --dry-run`
Expected: "No changes detected" — all migrations are up to date.

- [ ] **Step 3: Verify no remaining problematic truncations**

Run: `cd backend && grep -rn '\[:3000\]\|[:2000]\|[:500]\|[:400]\|[:300]\|[:200]\|[:150]\|[:120]\|[:100]\|[:80]\|[:60]' agents/blueprints/ projects/tasks.py projects/prompts.py projects/serializers/output_serializer.py --include="*.py" | grep -v "test_\|\.pyc\|migrations/" | grep -v "str(e)\|error_message\|logger\.\|task_id\[:8\]\|file_paths\[:5\]\|resp.text\[:300\]\|response\[:200\]"`

Expected: No matches for content truncation patterns (only logging/error truncations should remain).

- [ ] **Step 4: Commit any fixes needed**

If any tests fail, fix and commit with appropriate message.

---

### Task 12: Frontend — Document History Tab (placeholder)

**Note:** This task creates the API endpoint. The frontend React component is a separate implementation effort that should follow frontend patterns established in the codebase.

**Files:**
- Create: `backend/projects/serializers/document_serializer.py`
- Create: `backend/projects/views/document_view.py`
- Modify: `backend/projects/urls.py`

- [ ] **Step 1: Write test for document list API with archive filter**

In `backend/projects/tests/test_views.py`, add:

```python
class TestDocumentListView:
    def test_list_active_documents(self, auth_client, department):
        Document.objects.create(title="Active", content="content", department=department)
        archived = Document.objects.create(title="Archived", content="old", department=department, is_archived=True)

        response = auth_client.get(
            f"/api/projects/{department.project.id}/departments/{department.id}/documents/"
        )
        assert response.status_code == 200
        titles = [d["title"] for d in response.data]
        assert "Active" in titles
        assert "Archived" not in titles

    def test_list_all_documents_with_show_archived(self, auth_client, department):
        Document.objects.create(title="Active", content="content", department=department)
        Document.objects.create(title="Archived", content="old", department=department, is_archived=True)

        response = auth_client.get(
            f"/api/projects/{department.project.id}/departments/{department.id}/documents/?show_archived=true"
        )
        assert response.status_code == 200
        titles = [d["title"] for d in response.data]
        assert "Active" in titles
        assert "Archived" in titles

    def test_archived_docs_include_consolidated_into(self, auth_client, department):
        summary = Document.objects.create(title="Summary", content="merged", department=department)
        archived = Document.objects.create(
            title="Original",
            content="old",
            department=department,
            is_archived=True,
            consolidated_into=summary,
        )

        response = auth_client.get(
            f"/api/projects/{department.project.id}/departments/{department.id}/documents/?show_archived=true"
        )
        assert response.status_code == 200
        original = next(d for d in response.data if d["title"] == "Original")
        assert original["consolidated_into"] == str(summary.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest projects/tests/test_views.py::TestDocumentListView -v`
Expected: FAIL — endpoint does not exist.

- [ ] **Step 3: Create document serializer**

Create `backend/projects/serializers/document_serializer.py`:

```python
from rest_framework import serializers

from projects.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    consolidated_into = serializers.UUIDField(source="consolidated_into_id", read_only=True, allow_null=True)
    consolidated_from_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "department",
            "doc_type",
            "document_type",
            "is_archived",
            "consolidated_into",
            "consolidated_from_count",
            "sprint",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_consolidated_from_count(self, obj) -> int:
        return obj.consolidated_from.count()
```

- [ ] **Step 4: Create document view**

Create `backend/projects/views/document_view.py`:

```python
from rest_framework import generics, permissions

from projects.models import Document
from projects.serializers.document_serializer import DocumentSerializer


class DocumentListView(generics.ListAPIView):
    """List documents for a department. Filters to active by default, ?show_archived=true for all."""

    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        department_id = self.kwargs["department_id"]
        qs = Document.objects.filter(department_id=department_id).order_by("-created_at")

        show_archived = self.request.query_params.get("show_archived", "").lower() == "true"
        if not show_archived:
            qs = qs.filter(is_archived=False)

        return qs
```

- [ ] **Step 5: Wire URL**

In `backend/projects/urls.py`, add the import and URL pattern:

```python
from projects.views.document_view import DocumentListView
```

Add to urlpatterns:
```python
    path(
        "<uuid:project_id>/departments/<uuid:department_id>/documents/",
        DocumentListView.as_view(),
        name="document-list",
    ),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest projects/tests/test_views.py::TestDocumentListView -v`
Expected: All 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/projects/serializers/document_serializer.py backend/projects/views/document_view.py backend/projects/urls.py backend/projects/tests/test_views.py
git commit -m "feat: add document list API with archive filter for document history"
```

---

### Task 13: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All tests pass.

- [ ] **Step 2: Verify migrations are clean**

Run: `cd backend && python manage.py showmigrations projects | tail -5`
Expected: All migrations applied.

- [ ] **Step 3: Verify no remaining content truncations**

Run a comprehensive search:
```bash
cd backend && grep -rn '\[:' agents/blueprints/base.py | grep -v "logger\.\|[:10]\|[:20]\|[:5]\|[:30]"
```
Expected: No content truncation matches remain.

- [ ] **Step 4: Final commit if needed**

If any fixes were required, commit them.

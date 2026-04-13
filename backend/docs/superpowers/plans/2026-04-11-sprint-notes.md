# Sprint Notes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users post notes (with optional attachments) on running sprints that get injected into every subsequent agent task's context.

**Architecture:** New `SprintNote` model with text + optional Source attachments. REST endpoint nested under sprints. Notes injected into `build_context_message` (workforce agents) and `generate_task_proposal` (leader). Frontend renders a comment thread in the Sprints tab with an input for posting.

**Tech Stack:** Django REST Framework, React/Next.js, existing Source upload pattern

---

### Task 1: SprintNote Model + Migration

**Files:**
- Create: `backend/projects/models/sprint_note.py`
- Modify: `backend/projects/models/__init__.py`

- [ ] **Step 1: Create the model**

Create `backend/projects/models/sprint_note.py`:

```python
import uuid

from django.conf import settings
from django.db import models


class SprintNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sprint_notes",
    )
    text = models.TextField(help_text="The note content")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on {self.sprint} by {self.user.email} — {self.text[:40]}"
```

- [ ] **Step 2: Register in models __init__**

In `backend/projects/models/__init__.py`, add:

```python
from .sprint_note import SprintNote
```

And add `"SprintNote"` to the `__all__` list.

- [ ] **Step 3: Create migration**

Run: `python manage.py makemigrations projects -n add_sprint_note`
Then: `python manage.py migrate`

- [ ] **Step 4: Commit**

```bash
git add projects/models/sprint_note.py projects/models/__init__.py projects/migrations/
git commit -m "feat: SprintNote model — user notes on sprints

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: API — Serializer + View + URL

**Files:**
- Create: `backend/projects/serializers/sprint_note_serializer.py`
- Create: `backend/projects/views/sprint_note_view.py`
- Modify: `backend/projects/views/__init__.py`
- Modify: `backend/projects/urls.py`
- Test: `backend/projects/tests/test_sprint_notes.py`

- [ ] **Step 1: Write tests**

Create `backend/projects/tests/test_sprint_notes.py`:

```python
"""Tests for Sprint Notes API."""

import pytest
from projects.models import Project, Department, Sprint, SprintNote, Source


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(email="test@test.com", password="pass")


@pytest.fixture
def authed_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test", goal="Test", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="writers_room", project=project)


@pytest.fixture
def sprint(project, department, user):
    s = Sprint.objects.create(project=project, text="Test sprint", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.mark.django_db
class TestSprintNoteAPI:
    def test_create_note(self, authed_client, project, sprint):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "Change the protagonist name to Kaya"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["text"] == "Change the protagonist name to Kaya"
        assert resp.data["user_email"] == "test@test.com"
        assert SprintNote.objects.filter(sprint=sprint).count() == 1

    def test_create_note_with_source_ids(self, authed_client, project, sprint, user):
        source = Source.objects.create(
            project=project,
            source_type="text",
            raw_content="Reference material",
            original_filename="ref.md",
            user=user,
        )
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "See attached reference", "source_ids": [str(source.id)]},
            format="json",
        )
        assert resp.status_code == 201
        note = SprintNote.objects.get(id=resp.data["id"])
        assert note.sources.count() == 1
        assert note.sources.first().id == source.id

    def test_list_notes(self, authed_client, project, sprint, user):
        SprintNote.objects.create(sprint=sprint, user=user, text="First note")
        SprintNote.objects.create(sprint=sprint, user=user, text="Second note")
        resp = authed_client.get(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 2
        assert resp.data[0]["text"] == "First note"
        assert resp.data[1]["text"] == "Second note"

    def test_list_notes_empty(self, authed_client, project, sprint):
        resp = authed_client.get(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
        )
        assert resp.status_code == 200
        assert len(resp.data) == 0

    def test_create_note_requires_text(self, authed_client, project, sprint):
        resp = authed_client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": ""},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_note_requires_auth(self, client, project, sprint):
        resp = client.post(
            f"/api/projects/{project.id}/sprints/{sprint.id}/notes/",
            {"text": "Anon note"},
            format="json",
        )
        assert resp.status_code in [401, 403]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/tests/test_sprint_notes.py -v`
Expected: FAIL (no URL, no view)

- [ ] **Step 3: Create serializer**

Create `backend/projects/serializers/sprint_note_serializer.py`:

```python
from rest_framework import serializers

from projects.models import SprintNote


class SprintNoteSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    sources = serializers.SerializerMethodField()

    class Meta:
        model = SprintNote
        fields = ["id", "text", "user_email", "source_ids", "sources", "created_at"]
        read_only_fields = ["id", "user_email", "created_at"]

    def get_sources(self, obj):
        return [
            {
                "id": str(s.id),
                "original_filename": s.original_filename,
                "source_type": s.source_type,
            }
            for s in obj.sources.all()
        ]

    def create(self, validated_data):
        validated_data.pop("source_ids", None)
        return super().create(validated_data)
```

- [ ] **Step 4: Create view**

Create `backend/projects/views/sprint_note_view.py`:

```python
from rest_framework import generics, permissions

from projects.models import Source, Sprint, SprintNote
from projects.serializers.sprint_note_serializer import SprintNoteSerializer


class SprintNoteListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SprintNoteSerializer

    def get_queryset(self):
        return SprintNote.objects.filter(
            sprint_id=self.kwargs["sprint_id"],
            sprint__project_id=self.kwargs["project_id"],
        ).select_related("user").prefetch_related("sources")

    def perform_create(self, serializer):
        note = serializer.save(
            sprint_id=self.kwargs["sprint_id"],
            user=self.request.user,
        )

        source_ids = serializer.validated_data.get("source_ids", [])
        if source_ids:
            sources = Source.objects.filter(
                id__in=source_ids,
                project_id=self.kwargs["project_id"],
            )
            note.sources.set(sources)
```

- [ ] **Step 5: Add sources M2M to SprintNote**

The serializer references `note.sources` — add the M2M field to the model. In `backend/projects/models/sprint_note.py`, add after the `text` field:

```python
    sources = models.ManyToManyField(
        "projects.Source",
        blank=True,
        related_name="sprint_notes",
    )
```

Run: `python manage.py makemigrations projects -n add_sources_to_sprint_note`
Then: `python manage.py migrate`

- [ ] **Step 6: Register view in __init__ and add URL**

In `backend/projects/views/__init__.py`, add the import:
```python
from projects.views.sprint_note_view import SprintNoteListCreateView
```

In `backend/projects/urls.py`, add after the sprint-reset path:
```python
    path(
        "projects/<uuid:project_id>/sprints/<uuid:sprint_id>/notes/",
        views.SprintNoteListCreateView.as_view(),
        name="sprint-notes",
    ),
```

- [ ] **Step 7: Run tests**

Run: `pytest projects/tests/test_sprint_notes.py -v`
Expected: All 6 pass

Run: `pytest projects/tests/ agents/tests/ -x -q`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add projects/serializers/sprint_note_serializer.py projects/views/sprint_note_view.py projects/views/__init__.py projects/urls.py projects/tests/test_sprint_notes.py projects/models/sprint_note.py projects/migrations/
git commit -m "feat: SprintNote API — create and list notes on sprints

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Context Injection — Agents See Sprint Notes

**Files:**
- Modify: `backend/agents/blueprints/base.py:359-409` (build_context_message + build_task_message)
- Modify: `backend/agents/blueprints/base.py:1176-1199` (leader generate_task_proposal user_message)
- Test: `backend/agents/tests/test_sprint_notes_context.py`

- [ ] **Step 1: Write tests**

Create `backend/agents/tests/test_sprint_notes_context.py`:

```python
"""Tests for sprint note injection into agent context."""

import pytest
from unittest.mock import MagicMock, patch

from agents.blueprints.base import WorkforceBlueprint
from agents.models import Agent, AgentTask
from projects.models import Department, Project, Sprint, SprintNote


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(email="test@test.com", password="pass")


@pytest.fixture
def project(user):
    return Project.objects.create(name="Test", goal="Test goal", owner=user)


@pytest.fixture
def department(project):
    return Department.objects.create(department_type="writers_room", project=project)


@pytest.fixture
def sprint(project, department, user):
    s = Sprint.objects.create(project=project, text="Write a pitch", created_by=user, status="running")
    s.departments.add(department)
    return s


@pytest.fixture
def agent(department):
    return Agent.objects.create(
        name="Test Agent",
        agent_type="test_agent",
        department=department,
        status="active",
    )


@pytest.fixture
def task(agent, sprint):
    return AgentTask.objects.create(
        agent=agent,
        sprint=sprint,
        exec_summary="Test task",
        step_plan="Do something",
        status="processing",
    )


@pytest.mark.django_db
class TestSprintNotesInContext:
    def test_notes_appear_in_task_message(self, agent, task, sprint, user):
        SprintNote.objects.create(sprint=sprint, user=user, text="Change the name to Kaya")
        SprintNote.objects.create(sprint=sprint, user=user, text="Make the ending ambiguous")

        bp = WorkforceBlueprint()
        bp._system_prompt = "Test"
        msg = bp.build_task_message(agent, task)

        assert "Change the name to Kaya" in msg
        assert "Make the ending ambiguous" in msg
        assert "User Notes" in msg

    def test_no_notes_section_when_empty(self, agent, task, sprint):
        bp = WorkforceBlueprint()
        bp._system_prompt = "Test"
        msg = bp.build_task_message(agent, task)

        assert "User Notes" not in msg

    def test_note_sources_appear(self, agent, task, sprint, user, project):
        from projects.models import Source
        source = Source.objects.create(
            project=project, source_type="text",
            raw_content="Reference doc content",
            original_filename="reference.md", user=user,
        )
        note = SprintNote.objects.create(sprint=sprint, user=user, text="See attached")
        note.sources.add(source)

        bp = WorkforceBlueprint()
        bp._system_prompt = "Test"
        msg = bp.build_task_message(agent, task)

        assert "reference.md" in msg
        assert "Reference doc content" in msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest agents/tests/test_sprint_notes_context.py -v`
Expected: FAIL (notes not in message)

- [ ] **Step 3: Add note fetching helper to BaseBlueprint**

In `backend/agents/blueprints/base.py`, add a method to `BaseBlueprint` (after `build_task_message`, around line 410):

```python
    @staticmethod
    def _format_sprint_notes(sprint) -> str:
        """Format sprint notes for injection into agent context."""
        if sprint is None:
            return ""

        from projects.models import SprintNote

        notes = list(
            SprintNote.objects.filter(sprint=sprint)
            .select_related("user")
            .prefetch_related("sources")
            .order_by("created_at")
        )
        if not notes:
            return ""

        parts = ["## User Notes\n"]
        for note in notes:
            timestamp = note.created_at.strftime("%Y-%m-%d %H:%M")
            parts.append(f"**[{timestamp}]** {note.text}")
            for src in note.sources.all():
                content = src.summary or src.extracted_text or src.raw_content or ""
                if content:
                    parts.append(f"  Attachment ({src.original_filename}): {content}")
        return "\n".join(parts)
```

- [ ] **Step 4: Inject notes into build_task_message**

In `backend/agents/blueprints/base.py`, modify `build_task_message` (around line 395):

Change from:
```python
    def build_task_message(self, agent: Agent, task: AgentTask, suffix: str = "") -> str:
        """Build a task execution message with user-controlled content wrapped in XML tags."""
        context_msg = self.build_context_message(agent)
        extra = f"\n\n{suffix}" if suffix else ""
        return f"""{context_msg}

# Task to Execute
<task_summary>
{task.exec_summary}
</task_summary>
<task_plan>
{task.step_plan}
</task_plan>

Execute this task now.{extra}"""
```

To:
```python
    def build_task_message(self, agent: Agent, task: AgentTask, suffix: str = "") -> str:
        """Build a task execution message with user-controlled content wrapped in XML tags."""
        context_msg = self.build_context_message(agent)
        extra = f"\n\n{suffix}" if suffix else ""

        sprint_notes = ""
        if task.sprint:
            notes_text = self._format_sprint_notes(task.sprint)
            if notes_text:
                sprint_notes = f"\n\n<user_notes>\n{notes_text}\n</user_notes>"

        return f"""{context_msg}{sprint_notes}

# Task to Execute
<task_summary>
{task.exec_summary}
</task_summary>
<task_plan>
{task.step_plan}
</task_plan>

Execute this task now.{extra}"""
```

- [ ] **Step 5: Inject notes into leader's generate_task_proposal**

In `backend/agents/blueprints/base.py`, in the `generate_task_proposal` method of `LeaderBlueprint` (around line 1176), find the `user_message` string and add sprint notes after "Sprint Context Files":

Change from:
```python
        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Sprint Instruction
{sprint.text}

## Sprint Context Files
{source_context or "None."}

## Leader Instructions
```

To:
```python
        notes_text = self._format_sprint_notes(sprint)

        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Sprint Instruction
{sprint.text}

## Sprint Context Files
{source_context or "None."}

{notes_text}

## Leader Instructions
```

- [ ] **Step 6: Run tests**

Run: `pytest agents/tests/test_sprint_notes_context.py -v`
Expected: All 3 pass

Run: `pytest agents/tests/ projects/tests/ -x -q`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/base.py agents/tests/test_sprint_notes_context.py
git commit -m "feat: inject sprint notes into agent context — leader + workforce

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Frontend — Notes Thread in Sprint Tab

**Files:**
- Create: `frontend/components/sprint-notes.tsx`
- Modify: `frontend/components/department-view.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Add types**

In `frontend/lib/types.ts`, add after the `Sprint` interface:

```typescript
export interface SprintNoteSource {
  id: string;
  original_filename: string;
  source_type: string;
}

export interface SprintNote {
  id: string;
  text: string;
  user_email: string;
  sources: SprintNoteSource[];
  created_at: string;
}
```

- [ ] **Step 2: Add API methods**

In `frontend/lib/api.ts`, add after the `updateSprint` method:

```typescript
  listSprintNotes: (projectId: string, sprintId: string) =>
    request<import("./types").SprintNote[]>(
      `/api/projects/${projectId}/sprints/${sprintId}/notes/`,
    ),

  createSprintNote: (projectId: string, sprintId: string, data: { text: string; source_ids?: string[] }) =>
    request<import("./types").SprintNote>(
      `/api/projects/${projectId}/sprints/${sprintId}/notes/`,
      { method: "POST", body: JSON.stringify(data) },
    ),
```

- [ ] **Step 3: Create SprintNotes component**

Create `frontend/components/sprint-notes.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SprintNote } from "@/lib/types";
import { Loader2, Paperclip, Send, X } from "lucide-react";

interface SprintNotesProps {
  projectId: string;
  sprintId: string;
  sprintStatus: string;
}

export function SprintNotes({ projectId, sprintId, sprintStatus }: SprintNotesProps) {
  const [notes, setNotes] = useState<SprintNote[]>([]);
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadNotes = useCallback(() => {
    api.listSprintNotes(projectId, sprintId).then(setNotes).catch(() => {});
  }, [projectId, sprintId]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  async function handleSubmit() {
    if (!text.trim()) return;
    setSubmitting(true);
    try {
      const sourceIds: string[] = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        const source = await api.uploadSource(projectId, formData);
        sourceIds.push(source.id);
      }

      await api.createSprintNote(projectId, sprintId, {
        text: text.trim(),
        source_ids: sourceIds.length > 0 ? sourceIds : undefined,
      });

      setText("");
      setFiles([]);
      loadNotes();
    } finally {
      setSubmitting(false);
    }
  }

  function formatTime(iso: string) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatDate(iso: string) {
    const d = new Date(iso);
    const today = new Date();
    if (d.toDateString() === today.toDateString()) return "Today";
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
    return d.toLocaleDateString();
  }

  // Group notes by date
  const grouped: Record<string, SprintNote[]> = {};
  for (const note of notes) {
    const dateKey = formatDate(note.created_at);
    if (!grouped[dateKey]) grouped[dateKey] = [];
    grouped[dateKey].push(note);
  }

  const isActive = sprintStatus === "running" || sprintStatus === "paused";

  return (
    <div className="mt-3">
      {/* Notes thread */}
      {notes.length > 0 && (
        <div className="space-y-3 mb-3">
          {Object.entries(grouped).map(([date, dateNotes]) => (
            <div key={date}>
              <div className="text-[9px] text-text-secondary/50 uppercase tracking-wider text-center mb-2">
                {date}
              </div>
              <div className="space-y-1.5">
                {dateNotes.map((note) => (
                  <div
                    key={note.id}
                    className="flex gap-2 px-2.5 py-2 rounded-lg bg-bg-input/50 border border-border/30"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-text-primary whitespace-pre-wrap">
                        {note.text}
                      </div>
                      {note.sources.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {note.sources.map((s) => (
                            <span
                              key={s.id}
                              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-bg-surface border border-border text-[9px] text-text-secondary"
                            >
                              <Paperclip className="h-2 w-2" />
                              {s.original_filename}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="text-[9px] text-text-secondary/40 mt-1">
                        {formatTime(note.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Input — only for active sprints */}
      {isActive && (
        <div className="flex gap-2 items-end">
          <div className="flex-1 rounded-lg border border-border bg-bg-input">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Add a note for the agents..."
              rows={1}
              className="w-full px-2.5 py-1.5 bg-transparent text-xs text-text-primary placeholder:text-text-secondary/40 resize-none focus:outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
              }}
            />
            {files.length > 0 && (
              <div className="flex flex-wrap gap-1 px-2.5 pb-1.5">
                {files.map((f, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-bg-surface border border-border text-[9px] text-text-secondary"
                  >
                    {f.name}
                    <button onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))} className="hover:text-flag-critical">
                      <X className="h-2 w-2" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 p-1.5 text-text-secondary hover:text-text-primary transition-colors"
            title="Attach file"
          >
            <Paperclip className="h-3.5 w-3.5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.txt,.md,.csv"
            onChange={(e) => {
              if (e.target.files) {
                setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
              }
            }}
          />
          <button
            onClick={handleSubmit}
            disabled={submitting || !text.trim()}
            className="shrink-0 p-1.5 rounded-lg bg-accent-violet/15 text-accent-violet hover:bg-accent-violet/25 disabled:opacity-30 transition-colors"
            title="Post note"
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Wire into department-view sprint section**

In `frontend/components/department-view.tsx`, add the import:
```typescript
import { SprintNotes } from "@/components/sprint-notes";
```

Find the sprint outputs section (the `{/* Sprint outputs */}` comment inside the expanded sprint card). After the outputs section closing `</div>` and before the sprint card's closing tags, add:

```tsx
                      {/* Sprint notes */}
                      <SprintNotes
                        projectId={projectId}
                        sprintId={sprint.id}
                        sprintStatus={sprint.status}
                      />
```

- [ ] **Step 5: Test in browser**

1. Navigate to a project with a running sprint
2. Expand the sprint in the Sprints tab
3. Note input appears at the bottom
4. Type a note and press Enter or click Send
5. Note appears in the thread with timestamp
6. Attach a file — chip appears, uploads on submit
7. Verify done sprints show notes read-only (no input)

- [ ] **Step 6: Commit**

```bash
git add frontend/components/sprint-notes.tsx frontend/components/department-view.tsx frontend/lib/api.ts frontend/lib/types.ts
git commit -m "feat: sprint notes UI — comment thread on sprints with attachments

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

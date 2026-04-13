# Progress from Sprint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users carry forward deliverables from completed sprints as source material when creating new sprints.

**Architecture:** Backend adds `progress_from_sprint_ids` to sprint creation — converts referenced sprint Outputs into Source objects. Frontend adds a sprint picker dialog to the SprintInput component. No agent pipeline changes — Sources flow into leader context via existing injection.

**Tech Stack:** Django REST Framework (backend), React/Next.js (frontend), existing api client + types

---

### Task 1: Backend — Serializer + View

**Files:**
- Modify: `backend/projects/serializers/sprint_serializer.py`
- Modify: `backend/projects/views/sprint_view.py:31-70` (perform_create)

- [ ] **Step 1: Write the failing test**

Add to `backend/projects/tests/test_sprints.py` inside `TestSprintListCreateView`:

```python
@patch("agents.tasks.create_next_leader_task")
def test_create_sprint_with_progress_from_sprint(self, mock_task, authed_client, project, department, user):
    """Outputs from a done sprint become Sources on the new sprint."""
    # Create a done sprint with outputs
    old_sprint = Sprint.objects.create(
        project=project, text="Old work", created_by=user, status="done"
    )
    old_sprint.departments.add(department)
    Output.objects.create(
        sprint=old_sprint,
        department=department,
        title="Pitch Deliverable",
        label="pitch:deliverable",
        output_type="markdown",
        content="# The Pitch\n\nThis is the pitch content.",
    )
    Output.objects.create(
        sprint=old_sprint,
        department=department,
        title="Research Notes",
        label="pitch:research",
        output_type="markdown",
        content="## Research\n\nMarket analysis here.",
    )

    resp = authed_client.post(
        f"/api/projects/{project.id}/sprints/",
        {
            "text": "Continue the work",
            "department_ids": [str(department.id)],
            "progress_from_sprint_ids": [str(old_sprint.id)],
        },
        format="json",
    )
    assert resp.status_code == 201
    new_sprint = Sprint.objects.get(id=resp.data["id"])

    # Should have created Source objects from the old sprint's outputs
    sources = list(new_sprint.sources.all())
    assert len(sources) == 2
    titles = {s.original_filename for s in sources}
    assert "Pitch Deliverable.md" in titles
    assert "Research Notes.md" in titles

    # Verify source content
    pitch_src = next(s for s in sources if "Pitch" in s.original_filename)
    assert pitch_src.source_type == "text"
    assert pitch_src.raw_content == "# The Pitch\n\nThis is the pitch content."
    assert pitch_src.extracted_text == pitch_src.raw_content
    assert pitch_src.project == project
    assert pitch_src.user == user


@patch("agents.tasks.create_next_leader_task")
def test_progress_from_sprint_skips_empty_outputs(self, mock_task, authed_client, project, department, user):
    """Outputs with no content or link/file type are skipped."""
    old_sprint = Sprint.objects.create(
        project=project, text="Old", created_by=user, status="done"
    )
    old_sprint.departments.add(department)
    Output.objects.create(
        sprint=old_sprint, department=department,
        title="Empty", label="empty", output_type="markdown", content="",
    )
    Output.objects.create(
        sprint=old_sprint, department=department,
        title="A Link", label="link", output_type="link", url="https://example.com",
    )

    resp = authed_client.post(
        f"/api/projects/{project.id}/sprints/",
        {
            "text": "New sprint",
            "department_ids": [str(department.id)],
            "progress_from_sprint_ids": [str(old_sprint.id)],
        },
        format="json",
    )
    assert resp.status_code == 201
    new_sprint = Sprint.objects.get(id=resp.data["id"])
    assert new_sprint.sources.count() == 0


@patch("agents.tasks.create_next_leader_task")
def test_progress_from_sprint_validates_project(self, mock_task, authed_client, project, department, user):
    """Sprints from other projects are rejected."""
    other_project = Project.objects.create(name="Other", goal="Other", owner=user)
    other_sprint = Sprint.objects.create(
        project=other_project, text="Other", created_by=user, status="done"
    )

    resp = authed_client.post(
        f"/api/projects/{project.id}/sprints/",
        {
            "text": "New sprint",
            "department_ids": [str(department.id)],
            "progress_from_sprint_ids": [str(other_sprint.id)],
        },
        format="json",
    )
    assert resp.status_code == 400


@patch("agents.tasks.create_next_leader_task")
def test_progress_from_sprint_validates_done_status(self, mock_task, authed_client, project, department, user):
    """Only done sprints can be referenced."""
    running_sprint = Sprint.objects.create(
        project=project, text="Still running", created_by=user, status="running"
    )
    running_sprint.departments.add(department)

    resp = authed_client.post(
        f"/api/projects/{project.id}/sprints/",
        {
            "text": "New sprint",
            "department_ids": [str(department.id)],
            "progress_from_sprint_ids": [str(running_sprint.id)],
        },
        format="json",
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest projects/tests/test_sprints.py::TestSprintListCreateView::test_create_sprint_with_progress_from_sprint -v`
Expected: FAIL (field not recognized)

- [ ] **Step 3: Add serializer field**

In `backend/projects/serializers/sprint_serializer.py`, add the field and pop it in create:

```python
class SprintSerializer(serializers.ModelSerializer):
    department_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
    )
    source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    progress_from_sprint_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
    )
    # ... rest unchanged ...

    class Meta:
        model = Sprint
        fields = [
            # ... existing fields ...
            "progress_from_sprint_ids",
        ]
        # ... rest unchanged ...

    def create(self, validated_data):
        validated_data.pop("department_ids", None)
        validated_data.pop("source_ids", None)
        validated_data.pop("progress_from_sprint_ids", None)
        return super().create(validated_data)
```

- [ ] **Step 4: Add view logic**

In `backend/projects/views/sprint_view.py`, in `perform_create`, after the `source_ids` block (line 56) and before `_broadcast_sprint` (line 58), add:

```python
        # Convert outputs from referenced done sprints into Sources
        progress_sprint_ids = serializer.validated_data.get("progress_from_sprint_ids", [])
        if progress_sprint_ids:
            from projects.models import Output

            # Validate: must be done sprints in same project
            valid_sprints = Sprint.objects.filter(
                id__in=progress_sprint_ids,
                project_id=self.kwargs["project_id"],
                status=Sprint.Status.DONE,
            )
            if valid_sprints.count() != len(progress_sprint_ids):
                from rest_framework.exceptions import ValidationError
                raise ValidationError(
                    {"progress_from_sprint_ids": "All referenced sprints must exist, belong to this project, and be done."}
                )

            outputs = Output.objects.filter(
                sprint__in=valid_sprints,
                output_type__in=[Output.OutputType.MARKDOWN, Output.OutputType.PLAINTEXT],
            ).exclude(content="")

            for output in outputs:
                Source.objects.create(
                    project_id=self.kwargs["project_id"],
                    source_type=Source.SourceType.TEXT,
                    original_filename=f"{output.title}.md",
                    raw_content=output.content,
                    extracted_text=output.content,
                    word_count=len(output.content.split()),
                    user=self.request.user,
                    sprint=sprint,
                )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest projects/tests/test_sprints.py::TestSprintListCreateView -v`
Expected: All tests PASS including the 4 new ones

- [ ] **Step 6: Run full test suite**

Run: `pytest projects/tests/ agents/tests/ -x -q`
Expected: All pass, no regressions

- [ ] **Step 7: Commit**

```bash
git add projects/serializers/sprint_serializer.py projects/views/sprint_view.py projects/tests/test_sprints.py
git commit -m "feat: progress_from_sprint_ids — carry forward sprint outputs as sources"
```

---

### Task 2: Frontend — Sprint Picker Dialog

**Files:**
- Create: `frontend/components/sprint-picker-dialog.tsx`

- [ ] **Step 1: Create the dialog component**

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Sprint } from "@/lib/types";
import { History, Search, X, FileText } from "lucide-react";

interface SprintPickerDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (sprints: Sprint[]) => void;
  projectId: string;
  departmentId?: string;
  alreadySelectedIds: Set<string>;
}

export function SprintPickerDialog({
  open,
  onClose,
  onConfirm,
  projectId,
  departmentId,
  alreadySelectedIds,
}: SprintPickerDialogProps) {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(alreadySelectedIds));

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setSelectedIds(new Set(alreadySelectedIds));
    api
      .listSprints(projectId, { status: "done", ...(departmentId ? { department: departmentId } : {}) })
      .then(setSprints)
      .catch(() => setSprints([]))
      .finally(() => setLoading(false));
  }, [open, projectId, departmentId, alreadySelectedIds]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    if (!search.trim()) return sprints;
    const q = search.toLowerCase();
    return sprints.filter(
      (s) =>
        s.text.toLowerCase().includes(q) ||
        s.departments.some((d) => d.display_name.toLowerCase().includes(q)),
    );
  }, [sprints, search]);

  // Group by department at project level
  const grouped = useMemo(() => {
    if (departmentId) return { "": filtered };
    const groups: Record<string, Sprint[]> = {};
    for (const s of filtered) {
      const deptName = s.departments.map((d) => d.display_name).join(", ") || "No department";
      if (!groups[deptName]) groups[deptName] = [];
      groups[deptName].push(s);
    }
    return groups;
  }, [filtered, departmentId]);

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleConfirm() {
    const selected = sprints.filter((s) => selectedIds.has(s.id));
    onConfirm(selected);
    onClose();
  }

  if (!open) return null;

  const outputCount = (s: Sprint) => s.outputs?.filter((o) => o.content).length ?? 0;

  function formatDate(iso: string) {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    const days = Math.floor(diff / 86400000);
    if (days === 0) return "today";
    if (days === 1) return "yesterday";
    if (days < 30) return `${days}d ago`;
    return d.toLocaleDateString();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg mx-4 rounded-xl border border-border bg-bg-surface shadow-2xl animate-in fade-in zoom-in-95 duration-150 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-accent-violet" />
            <h3 className="text-sm font-semibold text-text-heading">Progress from sprint</h3>
          </div>
          <button onClick={onClose} className="p-1 text-text-secondary hover:text-text-primary transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Search */}
        <div className="px-5 py-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-secondary/50" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sprints..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-border bg-bg-input text-xs text-text-primary placeholder:text-text-secondary/50 focus:outline-none focus:border-accent-violet/50"
            />
          </div>
        </div>

        {/* Sprint list */}
        <div className="flex-1 overflow-y-auto px-5 py-3 min-h-0">
          {loading ? (
            <div className="text-xs text-text-secondary text-center py-8">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="text-xs text-text-secondary text-center py-8">
              {sprints.length === 0 ? "No completed sprints yet" : "No sprints match your search"}
            </div>
          ) : (
            Object.entries(grouped).map(([group, groupSprints]) => (
              <div key={group}>
                {group && (
                  <div className="text-[10px] font-medium text-text-secondary uppercase tracking-wider mb-2 mt-3 first:mt-0">
                    {group}
                  </div>
                )}
                <div className="space-y-1.5">
                  {groupSprints.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => toggle(s.id)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                        selectedIds.has(s.id)
                          ? "bg-accent-violet/10 border-accent-violet/30"
                          : "bg-bg-input/50 border-border hover:border-accent-violet/20"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-text-primary truncate">{s.text}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-text-secondary">{formatDate(s.completed_at || s.updated_at)}</span>
                            {outputCount(s) > 0 && (
                              <span className="inline-flex items-center gap-0.5 text-[10px] text-text-secondary">
                                <FileText className="h-2.5 w-2.5" />
                                {outputCount(s)}
                              </span>
                            )}
                          </div>
                        </div>
                        <div
                          className={`shrink-0 mt-0.5 w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                            selectedIds.has(s.id)
                              ? "bg-accent-violet border-accent-violet"
                              : "border-border"
                          }`}
                        >
                          {selectedIds.has(s.id) && (
                            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-3">
          <span className="text-[10px] text-text-secondary">
            {selectedIds.size > 0 ? `${selectedIds.size} selected` : "Select sprints to carry forward"}
          </span>
          <button
            onClick={handleConfirm}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-accent-violet/15 text-accent-violet border border-accent-violet/30 hover:bg-accent-violet/25 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/sprint-picker-dialog.tsx
git commit -m "feat: SprintPickerDialog — select done sprints to carry forward"
```

---

### Task 3: Frontend — Wire into SprintInput

**Files:**
- Modify: `frontend/components/sprint-input.tsx`
- Modify: `frontend/lib/api.ts` (createSprint type)

- [ ] **Step 1: Update API client type**

In `frontend/lib/api.ts`, update the `createSprint` parameter type:

```typescript
createSprint: (projectId: string, data: {
  text: string;
  department_ids: string[];
  source_ids?: string[];
  progress_from_sprint_ids?: string[];
}) =>
```

- [ ] **Step 2: Update SprintInput**

In `frontend/components/sprint-input.tsx`:

Add imports:
```typescript
import { History } from "lucide-react";
import type { Sprint } from "@/lib/types";
import { SprintPickerDialog } from "@/components/sprint-picker-dialog";
```

Add state (after `const [showDropZone, setShowDropZone] = useState(false);`):
```typescript
const [selectedSprints, setSelectedSprints] = useState<Sprint[]>([]);
const [showSprintPicker, setShowSprintPicker] = useState(false);
```

Add helper to remove a selected sprint (after `removeFile`):
```typescript
function removeSprint(sprintId: string) {
  setSelectedSprints((prev) => prev.filter((s) => s.id !== sprintId));
}
```

Update `handleSubmit` — add `progress_from_sprint_ids` to the createSprint call:
```typescript
await api.createSprint(projectId, {
  text: text.trim(),
  department_ids: Array.from(selectedDeptIds),
  source_ids: sourceIds,
  progress_from_sprint_ids: selectedSprints.map((s) => s.id),
});
```

Also clear selectedSprints on submit success (after `setShowDropZone(false);`):
```typescript
setSelectedSprints([]);
```

Add sprint chips section — after the file chips `</div>` (line 166) and before the `{/* Department selector + submit */}` comment (line 168):
```tsx
{/* Sprint chips */}
{selectedSprints.length > 0 && (
  <div className="flex flex-wrap gap-1.5 px-3 pb-2">
    {selectedSprints.map((s) => (
      <span
        key={s.id}
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent-violet/10 border border-accent-violet/20 text-[10px] text-accent-violet"
      >
        <History className="h-2.5 w-2.5" />
        {s.text.length > 40 ? s.text.slice(0, 40) + "..." : s.text}
        <button onClick={() => removeSprint(s.id)} className="hover:text-flag-critical">
          <X className="h-2.5 w-2.5" />
        </button>
      </span>
    ))}
  </div>
)}
```

Add the "Progress from sprint" button — in the footer bar, between the department pills `</div>` (line 196) and the Start Sprint `<button>` (line 198), add:
```tsx
<button
  onClick={() => setShowSprintPicker(true)}
  className="shrink-0 p-1.5 text-text-secondary hover:text-accent-violet transition-colors"
  title="Progress from sprint"
>
  <History className="h-3.5 w-3.5" />
</button>
```

Add the dialog — right before the closing `</div>` of the component (line 207):
```tsx
<SprintPickerDialog
  open={showSprintPicker}
  onClose={() => setShowSprintPicker(false)}
  onConfirm={setSelectedSprints}
  projectId={projectId}
  departmentId={defaultDepartmentId}
  alreadySelectedIds={new Set(selectedSprints.map((s) => s.id))}
/>
```

- [ ] **Step 3: Test in browser**

1. Navigate to a project with completed sprints
2. Click the History icon in the sprint input footer
3. Dialog opens with done sprints, searchable
4. Select one or more — chips appear below textarea
5. Type a sprint instruction and submit
6. Verify in Django admin: new sprint has Source objects from the old sprint's outputs

- [ ] **Step 4: Commit**

```bash
git add frontend/components/sprint-input.tsx frontend/lib/api.ts
git commit -m "feat: wire sprint picker into SprintInput — progress from sprint"
```

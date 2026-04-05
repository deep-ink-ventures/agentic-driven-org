# Briefings Design Spec

**Date:** 2026-04-04
**Status:** Approved

---

## Goal

Add a briefing system that lets users give ad-hoc directives to their project or specific departments. Briefings are additive context that generate tasks alongside the normal workload (hourly commands, overarching goals). They stay active and keep generating tasks until archived.

---

## Data Model

### Briefing

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `project` | FK(Project) | Required |
| `department` | FK(Department, nullable) | null = project-level (cascades to all departments) |
| `title` | string (255) | Auto-generated from content or user-provided |
| `content` | text | The user's directive — free text |
| `status` | enum: `active`, `archived` | Default: `active` |
| `created_by` | FK(User) | |
| `created_at` | datetime | |
| `updated_at` | datetime | |

### Attachments

Reuse the existing `Source` model. Add a nullable FK:

```python
# On Source model
briefing = models.ForeignKey("Briefing", null=True, blank=True, on_delete=models.CASCADE, related_name="attachments")
```

Same extraction pipeline — PDF, DOCX, TXT, MD, CSV. Same 50MB limit. Extracted text is available to leaders via `source.extracted_text`.

### Task linkage

Add a nullable FK on `AgentTask`:

```python
briefing = models.ForeignKey("Briefing", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
```

This lets leaders know which briefing spawned a task and check if a briefing still needs more work.

---

## Behavior

### Creation

**Project-level** (`department=null`):
1. Briefing created
2. For each department in the project, the department's leader gets the briefing as additional context
3. Each leader independently decides if/how to act — some may produce tasks, others may determine nothing is relevant

**Department-level** (`department` set):
1. Briefing created
2. Only that department's leader receives it as context

### Context injection

Leaders' `build_context_message` and `generate_task_proposal` include active briefings:

```
# Active Briefings
## Briefing: "We have a promo at the hotel" (project-level, created 2h ago)
Content: We have a promo at the hotel next Friday. We need social media coverage,
email blasts, and the landing page updated with the promo details.

Attachments:
- promo-flyer.pdf (extracted text: ...)

## Briefing: "Add dark mode" (department-level, created 1d ago)
Content: Implement dark mode across all pages.
```

Briefings are additive — they appear alongside the project goal, department documents, and other existing context. They do not replace anything.

### Task generation loop

When a briefing-sourced task completes:
- **Continuous mode departments** (engineering): leader is immediately triggered to check if more work is needed for this briefing
- **Scheduled mode departments** (marketing): leader picks it up on the next beat cycle (hourly/daily)

The leader checks: is the briefing still `active`? Is there remaining work? If yes, propose next task. If the briefing's intent is fully addressed, the leader simply stops proposing tasks for it (no explicit "done" status — it naturally quiesces).

### Archiving

- User archives a briefing → status changes to `archived`
- All already-created tasks (queued, awaiting approval, awaiting dependencies, planned, processing) continue to completion
- No new tasks are generated for this briefing
- Leader's context no longer includes archived briefings

---

## API

### Endpoints

```
POST   /api/projects/{project_id}/briefings/              — create briefing
GET    /api/projects/{project_id}/briefings/               — list (filter: ?status=active&department=uuid)
GET    /api/projects/{project_id}/briefings/{id}/          — detail
PATCH  /api/projects/{project_id}/briefings/{id}/          — update (archive: {"status": "archived"})
POST   /api/projects/{project_id}/briefings/{id}/files/    — upload attachment
```

### Create briefing

```json
POST /api/projects/{project_id}/briefings/
{
    "content": "We have a promo at the hotel next Friday...",
    "title": "Hotel promo campaign",          // optional — auto-generated if omitted
    "department": "uuid-or-null"              // null = project-level
}
```

Response: serialized Briefing with attachments.

On creation:
- If project-level: for each department, trigger leader task proposal (respecting execution mode)
- If department-level: trigger that department's leader only

### Upload attachment

```json
POST /api/projects/{project_id}/briefings/{id}/files/
Content-Type: multipart/form-data
file: <binary>
```

Uses the same `Source` creation + extraction pipeline as project sources. Sets `source.briefing = briefing`.

### List briefings

```
GET /api/projects/{project_id}/briefings/?status=active&department=uuid
```

Returns briefings for the project. Filters:
- `status`: `active` (default) or `archived` or `all`
- `department`: filter by department UUID (includes project-level briefings that cascade)

### Serializer

```json
{
    "id": "uuid",
    "project": "uuid",
    "department": "uuid-or-null",
    "title": "Hotel promo campaign",
    "content": "We have a promo at the hotel...",
    "status": "active",
    "attachments": [
        {
            "id": "uuid",
            "original_filename": "promo-flyer.pdf",
            "file_format": "pdf",
            "file_size": 245000,
            "word_count": 1200
        }
    ],
    "task_count": 5,
    "created_by_email": "user@example.com",
    "created_at": "2026-04-04T10:00:00Z",
    "updated_at": "2026-04-04T10:00:00Z"
}
```

---

## Frontend

### Briefing button

- **Project level**: "New Briefing" button in the project page header area
- **Department level**: same button when viewing a specific department's section

### Creation modal

Opens a modal/sheet with:
- **Text area** — the directive (placeholder: "What should the team focus on?")
- **File upload zone** — drag-and-drop or click, same allowed types as sources (PDF, DOCX, TXT, MD, CSV), 50MB limit
- **Scope indicator** — shows "All departments" or specific department name based on context
- **Submit button**

Title is auto-generated from the first ~50 chars of content. User can edit it before submitting.

### Active briefings display

Small section on the project page — a row of pills/chips below the project header:

```
[Hotel promo campaign ×]  [Add dark mode ×]  [+ New Briefing]
```

Each pill shows:
- Title (truncated)
- Archive button (×) — archives with confirmation

Clicking a pill expands inline to show full content and attachment list.

### No separate task filtering

Tasks from briefings are just tasks. The `briefing` FK exists for leader context, not UI filtering. Tasks appear in the normal task list alongside everything else.

---

## Leader Integration

### Context gathering

In `build_context_message` (or the leader's task proposal methods), add:

```python
# Fetch active briefings for this department
briefings = Briefing.objects.filter(
    project=project,
    status="active",
).filter(
    Q(department=department) | Q(department__isnull=True)  # dept-specific + project-level
).prefetch_related("attachments")
```

Format each briefing with its content and extracted attachment text, append to the context message.

### Task creation

When a leader creates a task in response to a briefing, it sets `task.briefing = briefing`. This allows:
1. The leader to check how many tasks a briefing has already spawned
2. The continuous mode trigger to know a briefing-related task just completed
3. Future reporting on briefing activity

### Trigger on creation

```python
# In BriefingCreateView.perform_create():
if briefing.department:
    departments = [briefing.department]
else:
    departments = project.departments.all()

for dept in departments:
    leader = dept.agents.filter(is_leader=True, is_active=True).first()
    if leader:
        create_next_leader_task.apply_async(
            args=[str(leader.id)],
            countdown=dept_delay(dept),  # respects execution_mode
        )
```

---

## Migration

One migration:
1. Create `Briefing` model in `projects` app
2. Add `briefing` FK to `Source` (nullable)
3. Add `briefing` FK to `AgentTask` (nullable)

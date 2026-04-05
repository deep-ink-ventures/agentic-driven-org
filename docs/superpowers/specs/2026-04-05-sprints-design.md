# Sprints — Work Instruction System

**Date:** 2026-04-05
**Status:** Proposed

## Summary

Replace the "seed first task" admin action and continuous/scheduled execution modes with **Sprints** — user-defined work instructions that drive departments until their goal is met. Sprints are the primary way work gets initiated and controlled.

## Data Model

### Sprint (new model — `projects` app)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| project | FK → Project | |
| departments | M2M → Department | Multi-department support |
| text | TextField | The instruction text |
| status | CharField | `running` / `paused` / `done` |
| completion_summary | TextField, nullable | Filled when leader marks done |
| created_by | FK → User | |
| created_at | DateTimeField | auto_now_add |
| updated_at | DateTimeField | auto_now |
| completed_at | DateTimeField, nullable | Set when status → done |

### Source changes

- Add `sprint` FK (nullable) — files dropped with the sprint instruction become project Sources linked to the sprint.

### AgentTask changes

- Add `sprint` FK (nullable) — every task traces back to the sprint that spawned it.

## Removals

| What | Why |
|------|-----|
| `seed_first_task` admin action | Replaced by sprint creation |
| `execution_mode` config (continuous/scheduled) | All sprints are continuous by definition |
| `_trigger_continuous_mode()` | Replaced by simpler "has running sprints?" check |
| `min_delay_seconds` config | No longer needed |
| Briefing model (already removed) | Was removed earlier this session |

**What stays unchanged:**
- Beat-scheduled commands (hourly/daily) — independent of sprints
- Review ping-pong system — tasks just also carry `sprint` FK
- Task approval flow — `auto_approve` still controls whether tasks need human approval
- Writers room stage machine — still works inside `generate_task_proposal`, now gated by having a running sprint

## API Endpoints

### Sprint CRUD

```
POST   /api/projects/{project_id}/sprints/           — create sprint
GET    /api/projects/{project_id}/sprints/            — list (filter: status, department)
PATCH  /api/projects/{project_id}/sprints/{id}/       — update status
GET    /api/projects/{project_id}/sprints/{id}/       — detail (task count, progress)
```

### Sprint creation flow

1. Frontend uploads files as Sources via existing upload endpoint
2. POST to `/sprints/` with `{ text, department_ids, source_ids }`
3. Backend creates Sprint (status=running), links sources
4. For each department's active leader, calls `create_next_leader_task.delay(leader_id)`

### Suggestions

```
POST   /api/projects/{project_id}/sprints/suggest/
Body:  { department_ids: ["..."] }
Returns: { suggestions: ["...", "...", "..."] }
```

Calls Haiku with project goal, department context, recent completed tasks, and currently running sprints. Returns 3 short, actionable suggestions phrased as instructions.

## Leader Behavior Changes

### `generate_task_proposal` rewrite

1. Query `Sprint.objects.filter(departments=department, status="running")`
2. If no running sprints → return `None` (loop stops)
3. If multiple running sprints → pick the one with least recent activity (round-robin fairness)
4. For the chosen sprint: review completed tasks (via `sprint` FK), evaluate what's been done vs what the sprint text asks for
5. Propose subtasks with `sprint` FK set
6. After subtasks complete → leader re-evaluates: "what's still missing to fulfill this sprint?"

### `complete_sprint` tool

Leader can call this when it judges the sprint goal is met:
- Sets `sprint.status = "done"`
- Fills `sprint.completion_summary`
- Sets `sprint.completed_at`
- Broadcasts via WebSocket so navbar updates instantly

### Continuous loop simplification

After any task completes:
1. Look up the task's department
2. Check if department has running sprints
3. If yes → `create_next_leader_task.delay(leader_id)`
4. If no → do nothing (loop naturally stops)

No more `execution_mode` config. No more `min_delay_seconds`.

## Frontend Changes

### Task Queue — Sprint Input (top of Tasks tab)

Located at the top of the Tasks tab in department view:

1. **Suggestion chips** — 3 chips loaded on mount via `/sprints/suggest/`. Click populates the text input.
2. **Text input** — placeholder: "What should this department work on?"
   - Paperclip icon for attachments
   - Dragging a file onto the text box reveals expandable file drop zone
   - Dropped files appear as removable chips below the input
   - Supported formats: PDF, DOCX, TXT, MD, CSV (same as existing Source uploads)
3. **Department multi-select** — defaults to current department, can add others
4. **"Start Sprint" button** — gold accent, like existing CTAs
5. Divider, then existing task lanes below

### Sidebar — Sprints Section

Below the Departments section in the project sidebar:

- Section header: "Sprints"
- Lists running + paused sprints (done are hidden)
- Each sprint shows: truncated instruction text, department name(s), status indicator
  - Running: green dot (pulsing), green text
  - Paused: gray dot, dimmed text
- Click → popover with:
  - Sprint text (full)
  - Department(s) + created time
  - Pause/Resume toggle button
  - Done button

### Dashboard (project-level view)

Same input box + suggestions + department multi-select as department view, but:
- No pre-selected department — user must pick at least one
- Suggestions generated for selected departments

### Department View — Sprints Tab

New tab alongside Agents / Tasks / Config:
- Lists all sprints for this department (running, paused, done)
- Each shows: text, status, created date, task count
- Done sprints show completion_summary

### Settings — History Tab

New tab in project settings:
- All sprints across project (including done)
- Sortable by date, filterable by department/status
- Shows completion_summary for done sprints

## WebSocket Events

New event types on the `project_{project_id}` channel:

```json
{"type": "sprint.created", "sprint": {...}}
{"type": "sprint.updated", "sprint": {...}}
```

Sidebar and department views listen for these to update sprint lists in real-time.

## Suggestion System

**Model:** Claude Haiku (fast, cheap)

**Context provided:**
- Project goal
- Department names + descriptions (for selected departments)
- Department documents (titles + summaries, not full content)
- Recent completed tasks (last 10 per department)
- Currently running sprints (to avoid suggesting work already in progress)

**System prompt:** "You are a project strategist. Given the project goal and current state, suggest 3 high-impact actions that would move the project forward. Be specific and actionable. Don't suggest anything already in progress."

**Response:** 3 one-sentence suggestions phrased as instructions.

**Caching:** None — generated fresh on each page load.

## Migration Path

- Existing `AgentTask` rows get `sprint=NULL` (they predate sprints — that's fine)
- Existing `Source` rows get `sprint=NULL`
- `execution_mode` and `min_delay_seconds` config keys in department configs are ignored after the change (no migration needed — they're JSON fields, just unused)
- The `seed_first_task` admin action is removed from `AgentAdmin`
- No data migration needed — sprints are a new concept, old tasks just don't have one

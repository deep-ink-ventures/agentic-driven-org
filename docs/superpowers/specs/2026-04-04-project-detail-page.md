# Project Detail Page — Design Spec

## Layout

ScriptPulse-inspired sidebar + main area pattern.

```
┌──────────────────────────────────────────────────┐
│  NavBar                                          │
├────────────┬─────────────────────────────────────┤
│  Sidebar   │  Main Area                          │
│            │                                     │
│ [Dashboard]│  Dashboard mode:                    │
│            │  - Task queue (all departments)     │
│ Marketing  │  - Approve/reject inline            │
│ Engineering│                                     │
│ ...        │  Department mode:                   │
│            │  - Leader card + workforce grid     │
│            │  - Click agent → agent detail       │
│            │                                     │
│            │  Agent detail mode:                 │
│            │  - Tabs: Overview | Instructions    │
│            │          | Config                   │
│            │  - Back button → department view    │
│            │                                     │
└────────────┴─────────────────────────────────────┘
```

## Sidebar

- **Dashboard** button at top (like ScriptPulse's report button) — always visible, returns to task queue
- List of departments from the project
- Active department highlighted with gold accent
- Departments show name only (not agents)

## Main Area Views

### Dashboard (default)

Task queue showing ALL tasks across all departments, ordered by created_at desc.

**Task statuses shown:**
- `awaiting_approval` — prominent, with approve/reject buttons
- `planned` — shows scheduled_at time
- `queued` — shows "queued"
- `processing` — shows spinner
- `done` — shows completion time, collapsible report
- `failed` — shows error, retry option

**Task card (inline expandable):**
- Collapsed: status badge, agent name, exec_summary (truncated), timestamp
- Expanded: full exec_summary, step_plan, report (if done), error (if failed), token_usage cost
- Approve/Reject buttons on awaiting_approval tasks
- "Approve & auto-execute similar" option

### Department View

Click department in sidebar → main area shows:

- **Department header**: name, description
- **Leader card**: name, active status, pending task count
- **Workforce agents grid**: cards with name, type, tags, active/inactive, pending task count
- Click any agent card → agent detail

### Agent Detail

Click agent → main area shows:

- **Back button** → returns to department view
- **Agent header**: name, type badge, active toggle, tags
- **Three tabs:**

**Overview tab:**
- Description from blueprint
- Skills list (from blueprint)
- Commands list with schedule indicators (hourly/daily/on-demand)
- Recent tasks list (last 10)

**Instructions tab:**
- Editable markdown textarea
- Save button
- Displays current instructions or "No custom instructions" placeholder

**Config tab:**
- Form fields generated from `config_schema` (each key → labeled input)
- Auto-actions toggles (each scheduled command → on/off switch)
- Save button

## API Endpoints Needed

### New endpoints:

- `GET /api/projects/{id}/detail/` — full project with nested departments, agents (no tasks — too many)
- `GET /api/projects/{id}/tasks/` — paginated task list, filterable by status/agent
- `POST /api/projects/{id}/tasks/{task_id}/approve/` — approve a task
- `POST /api/projects/{id}/tasks/{task_id}/reject/` — reject a task
- `PATCH /api/agents/{id}/` — update agent instructions, config, auto_actions, is_active
- `GET /api/agents/{id}/blueprint/` — get blueprint info (skills, commands, description, config_schema)

### Serializers:

- `ProjectDetailSerializer` — project + nested departments + nested agents (no tasks)
- `AgentTaskSerializer` — task with agent name/type
- `AgentUpdateSerializer` — writable: instructions, config, auto_actions, is_active
- `BlueprintInfoSerializer` — read-only: skills, commands, description, tags, config_schema

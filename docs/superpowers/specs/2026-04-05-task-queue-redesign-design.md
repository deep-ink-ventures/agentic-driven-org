# Task Queue Redesign

## Overview

Replace the flat task list (`DashboardView`) with a reusable two-lane `<TaskQueue>` component. The same component is used on the project dashboard, department landing page, and agent detail tab — pre-filtered by scope.

## API

The existing `ProjectTaskListView` (`GET /api/projects/{project_id}/tasks/`) is extended with query params:

| Param | Type | Description |
|-------|------|-------------|
| `status` | comma-separated string | Filter by status (e.g. `awaiting_approval,queued`) |
| `department` | UUID | Filter by department |
| `agent` | UUID | Filter by agent |
| `limit` | int (default 25) | Page size |
| `before` | ISO timestamp | Cursor — return tasks created before this timestamp |

Response remains a flat `AgentTask[]` list. Adds an `X-Total-Count` response header with the total count matching the current filters (before pagination).

No new endpoints, models, or migrations.

### Three parallel calls per TaskQueue instance

1. **Lane 1 — Needs Attention:** `?status=awaiting_approval,queued,failed&limit=25`
2. **Lane 2 — In Progress:** `?status=processing,awaiting_dependencies&limit=25`
3. **Collapsed stack — Completed:** `?status=done&limit=25` (fetched on expand)

Each call can include `&department={id}` or `&agent={id}` depending on context.

## Frontend Component

### `<TaskQueue>`

Single reusable component in `frontend/components/task-queue.tsx`.

```tsx
<TaskQueue projectId={id} />                          // Dashboard
<TaskQueue projectId={id} department={deptId} />      // Department page
<TaskQueue projectId={id} agent={agentId} />          // Agent detail tab
```

### Layout

- **Two lanes side by side** at the top, each with header + count badge:
  - Left: "Needs Attention" — awaiting_approval, queued, failed
  - Right: "In Progress" — processing, awaiting_dependencies
- **Collapsed "Completed" stack** below the lanes — done tasks only, click to expand
- Each lane/stack has:
  - Count badge from `X-Total-Count` header
  - Status filter dropdown to narrow within that lane's statuses
  - "Load more" button when more tasks exist (cursor-based via `before` param)

### TaskCard

Existing `TaskCard` component moves to `task-queue.tsx`. No changes to its behavior:
- Expandable card with status badge
- Approve/reject actions for awaiting_approval tasks
- Editable step_plan and exec_summary before approval
- Markdown-rendered plan and report
- Token usage display
- Blocker info for awaiting_dependencies tasks

### Integration points

- **Dashboard:** `<TaskQueue>` replaces the current `DashboardView`
- **Department page:** `<TaskQueue>` rendered below the agent list
- **Agent detail:** New 4th tab "Tasks" alongside Overview / Instructions / Config

## File changes

| File | Change |
|------|--------|
| `frontend/components/task-queue.tsx` | New — `<TaskQueue>` + `<TaskCard>` (moved from page.tsx) |
| `frontend/app/(app)/project/[...path]/page.tsx` | Remove `DashboardView` + `TaskCard`, import `<TaskQueue>`, add to DashboardView/DepartmentView/AgentDetailView |
| `frontend/lib/api.ts` | Add a `getProjectTasksWithCount` method (or modify `getProjectTasks`) that returns `{ tasks: AgentTask[], totalCount: number }` by reading the `X-Total-Count` response header |
| `backend/agents/views/agent_task_view.py` | Add `status`, `department`, `agent`, `limit`, `before` filtering + `X-Total-Count` header |

## What's NOT in scope

- Search bar (deferred)
- Drag-and-drop between lanes
- WebSocket-driven live task updates to lanes (existing WS stays as-is)
- Any new backend models or migrations

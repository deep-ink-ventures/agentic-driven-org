# Stuck Task Recovery

## Problem

When a Celery worker dies mid-execution (OOM, deploy, restart), `execute_agent_task`'s except block never runs. The `AgentTask` stays in `processing` forever — no retry, no failure.

`recover_stuck_proposals` exists for `BootstrapProposal` but nothing equivalent exists for `AgentTask`.

## Design

### Periodic task: `recover_stuck_tasks`

- Location: `backend/agents/tasks.py`
- Runs every 15 minutes via celery beat
- Finds `AgentTask` records where `status = processing` and `started_at < now - 1 hour`
- Marks each as `failed` with `error_message = "Worker died — task was processing for over 1 hour without completing"`
- Sets `completed_at = now`
- Broadcasts the status change via WebSocket (same `_broadcast_task` helper used by `execute_agent_task`)
- Logs a warning per recovered task

### Retry endpoint: `POST /api/projects/{project_id}/tasks/{task_id}/retry/`

- Location: `backend/agents/views/agent_task_view.py` (new `TaskRetryView`)
- Only works on tasks with `status = failed`
- Resets the task: `status = queued`, clears `error_message`, `report`, `started_at`, `completed_at`
- Dispatches `execute_agent_task.delay(str(task_id))`
- Returns the updated serialized task
- URL registered in `backend/projects/urls.py` alongside approve/reject

### Frontend: Retry button on failed TaskCards

- Location: `frontend/components/task-queue.tsx` (TaskCard component)
- Failed tasks show a "Retry" button next to the error message, styled like the Approve button but with a refresh icon
- Calls `api.retryTask(projectId, taskId)`
- `retryTask` added to `frontend/lib/api.ts` — `POST /api/projects/{projectId}/tasks/${taskId}/retry/`
- On success, `handleTaskUpdate` receives the updated task with `status = queued`, which removes it from the "Needs Attention" lane (since queued is still in that lane, it stays but with updated status badge)

### Beat schedule entry

```python
"recover-stuck-tasks": {
    "task": "agents.tasks.recover_stuck_tasks",
    "schedule": 900,  # every 15 minutes
},
```

## File changes

| File | Change |
|------|--------|
| `backend/agents/tasks.py` | Add `recover_stuck_tasks` periodic task |
| `backend/config/settings.py` | Add beat schedule entry |
| `backend/agents/views/agent_task_view.py` | Add `TaskRetryView` |
| `backend/projects/urls.py` | Add retry URL pattern |
| `frontend/lib/api.ts` | Add `retryTask` method |
| `frontend/components/task-queue.tsx` | Add Retry button to failed TaskCards |

## Not in scope

- Retry count tracking or max retries — user decides when to retry
- Auto-retry — always marks failed, human clicks retry
- Configurable timeout — hardcoded 1 hour, change later if needed

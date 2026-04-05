# Stuck Task Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a periodic task that marks stuck processing tasks as failed, plus a retry endpoint and frontend button so users can re-queue failed tasks.

**Architecture:** A celery beat task (`recover_stuck_tasks`) runs every 15 minutes, finds `AgentTask` records stuck in `processing` for over 1 hour, and marks them `failed`. A new `TaskRetryView` endpoint lets users re-queue any failed task. The frontend `TaskCard` component gets a Retry button on failed tasks.

**Tech Stack:** Django REST Framework, Celery, React/Next.js, existing WebSocket broadcast.

---

### Task 1: Backend — `recover_stuck_tasks` periodic task

**Files:**
- Modify: `backend/agents/tasks.py` (add new task after line ~155)
- Modify: `backend/config/settings.py:149-172` (add beat schedule entry)
- Test: `backend/agents/tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_tasks.py`:

```python
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from agents.models import Agent, AgentTask
from agents.tasks import recover_stuck_tasks
from projects.models import Department, Project


@pytest.mark.django_db
class TestRecoverStuckTasks:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(email="stuck@test.com", password="pass")
        self.project = Project.objects.create(name="Test", goal="g", owner=self.user)
        self.project.members.add(self.user)
        self.dept = Department.objects.create(project=self.project, department_type="eng")
        self.agent = Agent.objects.create(name="Bot", agent_type="bot", department=self.dept)

    @patch("agents.tasks._broadcast_task")
    def test_marks_stuck_processing_tasks_as_failed(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Stuck task",
            started_at=timezone.now() - timedelta(hours=2),
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.FAILED
        assert "Worker died" in task.error_message
        assert task.completed_at is not None
        mock_broadcast.assert_called_once()

    @patch("agents.tasks._broadcast_task")
    def test_ignores_recent_processing_tasks(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="Recent task",
            started_at=timezone.now() - timedelta(minutes=30),
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.PROCESSING
        mock_broadcast.assert_not_called()

    @patch("agents.tasks._broadcast_task")
    def test_ignores_non_processing_tasks(self, mock_broadcast):
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.QUEUED,
            exec_summary="Queued task",
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED
        mock_broadcast.assert_not_called()

    @patch("agents.tasks._broadcast_task")
    def test_handles_processing_with_no_started_at(self, mock_broadcast):
        """Edge case: task in processing but started_at is null (shouldn't happen, but be safe)."""
        task = AgentTask.objects.create(
            agent=self.agent,
            status=AgentTask.Status.PROCESSING,
            exec_summary="No started_at",
            started_at=None,
        )
        recover_stuck_tasks()
        task.refresh_from_db()
        # Should be recovered since we can't know when it started
        assert task.status == AgentTask.Status.FAILED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest agents/tests/test_tasks.py::TestRecoverStuckTasks -v`
Expected: ImportError — `recover_stuck_tasks` doesn't exist yet.

- [ ] **Step 3: Implement `recover_stuck_tasks`**

Add to `backend/agents/tasks.py`, after the `_trigger_continuous_mode` function (around line 180):

```python
@shared_task
def recover_stuck_tasks():
    """
    Self-healing: find AgentTask records stuck in processing for >1 hour.
    Marks them failed so users can retry via the UI.
    Runs every 15 minutes via celery beat.
    """
    from datetime import timedelta

    from agents.models import AgentTask

    now = timezone.now()
    cutoff = now - timedelta(hours=1)

    stuck = AgentTask.objects.filter(
        status=AgentTask.Status.PROCESSING,
    ).filter(
        # started_at is null (shouldn't happen) OR started_at is older than cutoff
        models.Q(started_at__isnull=True) | models.Q(started_at__lt=cutoff),
    ).select_related("agent", "agent__department__project", "created_by_agent", "blocked_by")

    for task in stuck:
        logger.warning("Recovering stuck task %s (%s): %s", task.id, task.agent.name, task.exec_summary[:80])
        task.status = AgentTask.Status.FAILED
        task.error_message = "Worker died — task was processing for over 1 hour without completing"
        task.completed_at = now
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        _broadcast_task(task)
```

Also add `from django.db import models` to the imports at the top of the file (it's needed for `models.Q`).

- [ ] **Step 4: Add beat schedule entry**

In `backend/config/settings.py`, add to the `CELERY_BEAT_SCHEDULE` dict (after the `recover-stuck-proposals` entry):

```python
    "recover-stuck-tasks": {
        "task": "agents.tasks.recover_stuck_tasks",
        "schedule": 900,  # every 15 minutes
    },
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest agents/tests/test_tasks.py::TestRecoverStuckTasks -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/tasks.py backend/config/settings.py backend/agents/tests/test_tasks.py
git commit -m "feat: recover_stuck_tasks periodic task — marks stuck processing tasks as failed"
```

---

### Task 2: Backend — `TaskRetryView` endpoint

**Files:**
- Modify: `backend/agents/views/agent_task_view.py` (add new view after `TaskRejectView`, ~line 133)
- Modify: `backend/projects/urls.py` (add URL pattern)
- Test: `backend/agents/tests/test_views.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_views.py`, after the `TestTaskRejectView` class:

```python
@pytest.mark.django_db
class TestTaskRetryView:
    @patch("agents.tasks.execute_agent_task")
    def test_retry_requeues_failed_task(self, mock_exec, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Failed task",
            status=AgentTask.Status.FAILED,
            error_message="Worker died",
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 200
        task.refresh_from_db()
        assert task.status == AgentTask.Status.QUEUED
        assert task.error_message == ""
        assert task.report == ""
        assert task.started_at is None
        assert task.completed_at is None
        mock_exec.delay.assert_called_once_with(str(task.id))

    def test_retry_rejects_non_failed_task(self, authed_client, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Processing task",
            status=AgentTask.Status.PROCESSING,
        )
        resp = authed_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 400

    def test_retry_requires_membership(self, api_client, other_user, project, agent):
        task = AgentTask.objects.create(
            agent=agent,
            exec_summary="Failed task",
            status=AgentTask.Status.FAILED,
        )
        api_client.force_authenticate(user=other_user)
        resp = api_client.post(f"/api/projects/{project.id}/tasks/{task.id}/retry/")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest agents/tests/test_views.py::TestTaskRetryView -v`
Expected: FAIL — URL not found (404).

- [ ] **Step 3: Implement `TaskRetryView`**

Add to `backend/agents/views/agent_task_view.py`, after the `TaskRejectView` class:

```python
class TaskRetryView(APIView):
    """POST /api/projects/{project_id}/tasks/{task_id}/retry/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, task_id):
        task = get_object_or_404(
            AgentTask,
            id=task_id,
            agent__department__project_id=project_id,
            agent__department__project__members=request.user,
        )
        if task.status != AgentTask.Status.FAILED:
            return Response(
                {"error": f"Task is {task.status}, not failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from agents.tasks import execute_agent_task

        task.status = AgentTask.Status.QUEUED
        task.error_message = ""
        task.report = ""
        task.started_at = None
        task.completed_at = None
        task.save(update_fields=[
            "status", "error_message", "report",
            "started_at", "completed_at", "updated_at",
        ])

        execute_agent_task.delay(str(task.id))
        return Response(AgentTaskSerializer(task).data)
```

- [ ] **Step 4: Add URL pattern**

In `backend/projects/urls.py`, add after the `task-reject` path (line 20):

```python
    path(
        "projects/<uuid:project_id>/tasks/<uuid:task_id>/retry/",
        views_agents.TaskRetryView.as_view(),
        name="task-retry",
    ),
```

- [ ] **Step 5: Add timezone import to test file**

At the top of `backend/agents/tests/test_views.py`, add `from django.utils import timezone` to the imports if not already present.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest agents/tests/test_views.py::TestTaskRetryView -v`
Expected: All 3 tests PASS.

- [ ] **Step 7: Run full test suite to check for regressions**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest -q --tb=line 2>&1 | tail -5`
Expected: All tests pass, no regressions.

- [ ] **Step 8: Commit**

```bash
git add backend/agents/views/agent_task_view.py backend/projects/urls.py backend/agents/tests/test_views.py
git commit -m "feat: TaskRetryView — POST endpoint to re-queue failed tasks"
```

---

### Task 3: Frontend — Retry button and API method

**Files:**
- Modify: `frontend/lib/api.ts:201-202` (add `retryTask` after `rejectTask`)
- Modify: `frontend/components/task-queue.tsx:165-169` (add Retry button to failed tasks)

- [ ] **Step 1: Add `retryTask` to `api.ts`**

In `frontend/lib/api.ts`, add after the `rejectTask` method (after line 202):

```typescript
  retryTask: (projectId: string, taskId: string) =>
    request<import("./types").AgentTask>(`/api/projects/${projectId}/tasks/${taskId}/retry/`, { method: "POST" }),
```

- [ ] **Step 2: Add `RefreshCw` to lucide imports in `task-queue.tsx`**

In `frontend/components/task-queue.tsx`, add `RefreshCw` to the lucide-react import:

```tsx
import {
  Loader2,
  Check,
  X,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Pencil,
  Clock,
  Filter,
  RefreshCw,
} from "lucide-react";
```

- [ ] **Step 3: Add retry handler and button to `TaskCard`**

In `frontend/components/task-queue.tsx`, inside the `TaskCard` component:

First, add a `handleRetry` function after `handleReject` (around line 80):

```tsx
  async function handleRetry() {
    setActing(true);
    try {
      const updated = await api.retryTask(projectId, task.id);
      onUpdate(updated);
    } finally {
      setActing(false);
    }
  }
```

Then, find the error message display block (around line 165-169):

```tsx
          {task.error_message && (
            <div className="flex items-start gap-2 text-flag-critical text-xs p-2 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              {task.error_message}
            </div>
          )}
```

Replace it with:

```tsx
          {task.error_message && (
            <div className="flex items-start justify-between gap-2 text-flag-critical text-xs p-2 rounded-lg bg-flag-critical/10">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <span>{task.error_message}</span>
              </div>
              {task.status === "failed" && (
                <Button
                  size="sm"
                  onClick={handleRetry}
                  disabled={acting}
                  className="shrink-0 bg-accent-gold text-bg-primary hover:bg-accent-gold-hover text-xs h-6 px-2"
                >
                  <RefreshCw className="h-3 w-3 mr-1" /> Retry
                </Button>
              )}
            </div>
          )}
```

- [ ] **Step 4: Verify frontend build compiles**

Run: `cd frontend && npx next build 2>&1 | grep -E "error|Error|Compiled|Failed"`
Expected: `Compiled successfully` (type-check may show pre-existing issues but compilation succeeds).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/components/task-queue.tsx
git commit -m "feat: retry button on failed tasks — calls POST /retry/ endpoint"
```

# Task Queue Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat task list with a reusable two-lane `<TaskQueue>` component with cursor pagination, status filters, and count badges — used on dashboard, department page, and agent detail tab.

**Architecture:** Backend extends `ProjectTaskListView` with `status`, `department`, `agent`, `limit`, `before` query params and an `X-Total-Count` header. Frontend extracts a `<TaskQueue>` component that makes 3 parallel API calls (one per lane/stack), each independently paginated. The same component is rendered with different filter props on dashboard, department, and agent views.

**Tech Stack:** Django REST Framework (backend), Next.js + React + Tailwind (frontend), existing `api.ts` request helper.

---

### Task 1: Backend — Add filtering and pagination to ProjectTaskListView

**Files:**
- Modify: `backend/agents/views/agent_task_view.py:14-28`
- Test: `backend/agents/tests/test_views.py` (create if absent)

- [ ] **Step 1: Write the failing test for status filtering**

In `backend/agents/tests/test_views.py`:

```python
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from agents.models import Agent, AgentTask
from projects.models import Project, Department

User = get_user_model()


class ProjectTaskListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", email="t@t.com", password="pass")
        self.project = Project.objects.create(name="Test", slug="test", goal="g", owner=self.user)
        self.project.members.add(self.user)
        self.dept = Department.objects.create(project=self.project, department_type="engineering", display_name="Eng")
        self.agent = Agent.objects.create(name="Bot", agent_type="test_bot", department=self.dept)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = f"/api/projects/{self.project.id}/tasks/"

    def _create_task(self, status, **kwargs):
        return AgentTask.objects.create(agent=self.agent, status=status, exec_summary=f"Task {status}", **kwargs)

    def test_filter_by_status_single(self):
        self._create_task(AgentTask.Status.QUEUED)
        self._create_task(AgentTask.Status.DONE)
        resp = self.client.get(self.url, {"status": "queued"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["status"], "queued")

    def test_filter_by_status_comma_separated(self):
        self._create_task(AgentTask.Status.QUEUED)
        self._create_task(AgentTask.Status.AWAITING_APPROVAL)
        self._create_task(AgentTask.Status.DONE)
        resp = self.client.get(self.url, {"status": "queued,awaiting_approval"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_filter_by_department(self):
        dept2 = Department.objects.create(project=self.project, department_type="marketing", display_name="Mkt")
        agent2 = Agent.objects.create(name="Bot2", agent_type="test_bot2", department=dept2)
        self._create_task(AgentTask.Status.QUEUED)
        AgentTask.objects.create(agent=agent2, status=AgentTask.Status.QUEUED, exec_summary="Other dept")
        resp = self.client.get(self.url, {"department": str(self.dept.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_filter_by_agent(self):
        agent2 = Agent.objects.create(name="Bot2", agent_type="test_bot2", department=self.dept)
        self._create_task(AgentTask.Status.QUEUED)
        AgentTask.objects.create(agent=agent2, status=AgentTask.Status.QUEUED, exec_summary="Other agent")
        resp = self.client.get(self.url, {"agent": str(self.agent.id)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_limit_param(self):
        for i in range(5):
            self._create_task(AgentTask.Status.QUEUED)
        resp = self.client.get(self.url, {"limit": "2"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_before_cursor(self):
        t1 = self._create_task(AgentTask.Status.QUEUED)
        t2 = self._create_task(AgentTask.Status.QUEUED)
        # t2 is newer; asking for before=t2.created_at should return only t1
        resp = self.client.get(self.url, {"before": t2.created_at.isoformat()})
        self.assertEqual(resp.status_code, 200)
        ids = [t["id"] for t in resp.data]
        self.assertIn(str(t1.id), ids)
        self.assertNotIn(str(t2.id), ids)

    def test_x_total_count_header(self):
        for i in range(5):
            self._create_task(AgentTask.Status.QUEUED)
        resp = self.client.get(self.url, {"status": "queued", "limit": "2"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["X-Total-Count"], "5")
        self.assertEqual(len(resp.data), 2)

    def test_no_filters_returns_all(self):
        self._create_task(AgentTask.Status.QUEUED)
        self._create_task(AgentTask.Status.DONE)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test agents.tests.test_views -v 2`
Expected: Multiple failures — the view doesn't filter or paginate yet.

- [ ] **Step 3: Implement filtering and pagination**

Replace the `get_queryset` method and add `list` override in `backend/agents/views/agent_task_view.py`:

```python
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import AgentTask
from agents.serializers import AgentTaskSerializer
from projects.models import Project


class ProjectTaskListView(ListAPIView):
    """GET /api/projects/{project_id}/tasks/ — list tasks for a project.

    Query params:
        status   — comma-separated status filter (e.g. queued,awaiting_approval)
        department — UUID, filter by department
        agent    — UUID, filter by agent
        limit    — page size (default 25, max 100)
        before   — ISO timestamp cursor, return tasks created before this
    """
    serializer_class = AgentTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        qs = (
            AgentTask.objects.filter(
                agent__department__project_id=project_id,
                agent__department__project__members=self.request.user,
            )
            .select_related("agent", "created_by_agent")
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            qs = qs.filter(status__in=statuses)

        department = self.request.query_params.get("department")
        if department:
            qs = qs.filter(agent__department_id=department)

        agent = self.request.query_params.get("agent")
        if agent:
            qs = qs.filter(agent_id=agent)

        before = self.request.query_params.get("before")
        if before:
            dt = parse_datetime(before)
            if dt:
                qs = qs.filter(created_at__lt=dt)

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        total_count = queryset.count()

        limit = min(int(request.query_params.get("limit", 25)), 100)
        page = list(queryset[:limit])

        serializer = self.get_serializer(page, many=True)
        response = Response(serializer.data)
        response["X-Total-Count"] = str(total_count)
        response["Access-Control-Expose-Headers"] = "X-Total-Count"
        return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test agents.tests.test_views -v 2`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/views/agent_task_view.py backend/agents/tests/test_views.py
git commit -m "feat: add status/department/agent/cursor filtering to task list endpoint"
```

---

### Task 2: Frontend — Add `requestWithHeaders` helper and update `getProjectTasks`

**Files:**
- Modify: `frontend/lib/api.ts:19-60` (add new request helper), `frontend/lib/api.ts:126-148` (update getProjectTasks)
- Modify: `frontend/lib/types.ts` (add TaskPage type)

- [ ] **Step 1: Add `TaskPage` type to `types.ts`**

Add at the end of `frontend/lib/types.ts`:

```typescript
export interface TaskPage {
  tasks: AgentTask[];
  totalCount: number;
}
```

- [ ] **Step 2: Add `requestWithHeaders` function to `api.ts`**

After the existing `request` function (after line 60), add:

```typescript
async function requestWithHeaders<T>(path: string, options: RequestInit = {}): Promise<{ data: T; headers: Headers }> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
  }

  const doFetch = () =>
    fetch(url, { ...options, credentials: "include", headers });

  let res: Response;
  try {
    res = await doFetch();
  } catch {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (res.status === 503) {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return { data: undefined as T, headers: res.headers };
  return { data: await res.json(), headers: res.headers };
}
```

- [ ] **Step 3: Replace `getProjectTasks` to return `TaskPage`**

Replace the existing `getProjectTasks` method (lines 126-148) with:

```typescript
  getProjectTasks: async (
    projectId: string,
    params?: {
      status?: string;
      department?: string;
      agent?: string;
      limit?: number;
      before?: string;
    },
  ): Promise<import("./types").TaskPage> => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set("status", params.status);
    if (params?.department) sp.set("department", params.department);
    if (params?.agent) sp.set("agent", params.agent);
    if (params?.limit) sp.set("limit", String(params.limit));
    if (params?.before) sp.set("before", params.before);
    const qs = sp.toString();
    const { data, headers } = await requestWithHeaders<import("./types").AgentTask[]>(
      `/api/projects/${projectId}/tasks/${qs ? `?${qs}` : ""}`,
    );
    return {
      tasks: data,
      totalCount: parseInt(headers.get("X-Total-Count") || "0", 10),
    };
  },
```

- [ ] **Step 4: Fix callers of `getProjectTasks`**

In `frontend/app/(app)/project/[...path]/page.tsx` line 1095, the call `api.getProjectTasks(proj.id).then((t) => setTasks(t))` needs to unwrap `.tasks`:

```typescript
return api.getProjectTasks(proj.id).then((page) => setTasks(page.tasks));
```

- [ ] **Step 5: Verify build compiles**

Run: `cd frontend && npx next build`
Expected: Build succeeds with no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/types.ts frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: getProjectTasks returns TaskPage with totalCount from X-Total-Count header"
```

---

### Task 3: Frontend — Create `<TaskQueue>` component

**Files:**
- Create: `frontend/components/task-queue.tsx`
- Modify: `frontend/app/(app)/project/[...path]/page.tsx` (remove TaskCard + DashboardView, ~lines 49-319)

- [ ] **Step 1: Create `task-queue.tsx` with TaskCard moved from page.tsx**

Create `frontend/components/task-queue.tsx`. This file contains:
1. The `statusColors` map (moved from page.tsx lines 49-58)
2. The `TaskCard` component (moved from page.tsx lines 64-269, unchanged)
3. A new `TaskLane` sub-component
4. The main `TaskQueue` component

```tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { AgentTask } from "@/lib/types";
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
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/* ------------------------------------------------------------------ */
/*  Status badge colours                                              */
/* ------------------------------------------------------------------ */

const statusColors: Record<AgentTask["status"], string> = {
  awaiting_approval:
    "bg-accent-gold/15 text-accent-gold border-accent-gold/30",
  awaiting_dependencies: "bg-bg-surface text-text-secondary border-border",
  planned: "bg-bg-surface text-text-secondary border-border",
  queued: "bg-bg-surface text-text-secondary border-border",
  processing: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  done: "bg-flag-strength/15 text-flag-strength border-flag-strength/30",
  failed: "bg-flag-critical/15 text-flag-critical border-flag-critical/30",
};

/* ------------------------------------------------------------------ */
/*  TaskCard (moved from page.tsx — unchanged)                        */
/* ------------------------------------------------------------------ */

function TaskCard({
  task,
  projectId,
  onUpdate,
}: {
  task: AgentTask;
  projectId: string;
  onUpdate: (t: AgentTask) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [acting, setActing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [showPlan, setShowPlan] = useState(false);
  const [editedPlan, setEditedPlan] = useState(task.step_plan);
  const [editedSummary, setEditedSummary] = useState(task.exec_summary);

  const isApproval = task.status === "awaiting_approval";
  const hasEdits = editedPlan !== task.step_plan || editedSummary !== task.exec_summary;

  async function handleApprove() {
    setActing(true);
    try {
      const edits = hasEdits ? { step_plan: editedPlan, exec_summary: editedSummary } : undefined;
      const updated = await api.approveTask(projectId, task.id, edits);
      onUpdate(updated);
      setEditing(false);
    } finally {
      setActing(false);
    }
  }

  async function handleReject() {
    setActing(true);
    try {
      const updated = await api.rejectTask(projectId, task.id);
      onUpdate(updated);
    } finally {
      setActing(false);
    }
  }

  return (
    <div className="border border-border rounded-lg bg-bg-surface">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
      >
        <span
          className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full border ${statusColors[task.status]}`}
        >
          {task.status.replace("_", " ")}
        </span>
        <span className="text-xs text-text-secondary shrink-0">
          {task.agent_name}
        </span>
        <span className="text-sm text-text-primary truncate flex-1">
          {editing ? editedSummary : task.exec_summary}
        </span>
        <span className="text-xs text-text-secondary shrink-0">
          {new Date(task.created_at).toLocaleTimeString()}
        </span>
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 text-text-secondary" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
          {/* Summary — editable for approval tasks */}
          <div>
            <p className="text-xs text-text-secondary mb-1">Summary</p>
            {editing ? (
              <Input
                value={editedSummary}
                onChange={(e) => setEditedSummary(e.target.value)}
                className="bg-bg-input border-border text-text-primary text-sm"
              />
            ) : (
              <p className="text-sm text-text-primary">{task.exec_summary}</p>
            )}
          </div>

          {/* Plan — toggle visibility, editable for approval tasks */}
          {(task.step_plan || editing) && (
            <div>
              {!editing && (
                <button
                  onClick={() => setShowPlan(!showPlan)}
                  className="text-xs text-text-secondary hover:text-text-primary transition-colors flex items-center gap-1 mb-2"
                >
                  {showPlan ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {showPlan ? "Hide plan" : "Show plan"}
                </button>
              )}
              {(showPlan || editing) && (
                editing ? (
                  <textarea
                    value={editedPlan}
                    onChange={(e) => setEditedPlan(e.target.value)}
                    rows={Math.max(6, editedPlan.split("\n").length + 2)}
                    className="w-full rounded-lg border border-border bg-bg-input px-3 py-2 text-xs text-text-primary font-mono outline-none focus-visible:border-accent-gold focus-visible:ring-1 focus-visible:ring-accent-gold/50 resize-y"
                  />
                ) : (
                  <div
                    onClick={isApproval ? () => setEditing(true) : undefined}
                    className={`rounded-lg border border-dashed border-border p-3 text-sm text-text-primary max-w-none [&_p]:mb-2 [&_ul]:mb-2 [&_ol]:mb-2 [&_li]:mb-1 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&>*:last-child]:mb-0 ${isApproval ? "cursor-pointer hover:border-accent-gold/40 transition-colors" : ""}`}
                  >
                    <ReactMarkdown>{task.step_plan}</ReactMarkdown>
                  </div>
                )
              )}
            </div>
          )}

          {/* Report — read only */}
          {task.report && (
            <div>
              <p className="text-xs text-text-secondary mb-1">Report</p>
              <pre className="text-xs text-text-primary whitespace-pre-wrap bg-bg-input rounded-lg p-3 border border-border">
                {task.report}
              </pre>
            </div>
          )}
          {task.error_message && (
            <div className="flex items-start gap-2 text-flag-critical text-xs p-2 rounded-lg bg-flag-critical/10">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              {task.error_message}
            </div>
          )}
          {task.token_usage && (
            <p className="text-[10px] text-text-secondary">
              {task.token_usage.model} &middot;{" "}
              {task.token_usage.input_tokens}&rarr;
              {task.token_usage.output_tokens} tokens &middot; $
              {task.token_usage.cost_usd.toFixed(4)}
            </p>
          )}

          {/* Blocker info for awaiting_dependencies tasks */}
          {task.status === "awaiting_dependencies" && task.blocked_by_summary && (
            <div className="flex items-center gap-2 text-xs text-text-secondary p-2 rounded-lg bg-bg-input">
              <Clock className="h-3.5 w-3.5 shrink-0" />
              <span>Waiting on: {task.blocked_by_summary}</span>
            </div>
          )}

          {/* Actions for approval tasks */}
          {isApproval && (
            <div className="flex items-center gap-2 pt-1">
              {!editing ? (
                <>
                  <Button
                    size="sm"
                    onClick={handleApprove}
                    disabled={acting}
                    className="bg-flag-strength text-white hover:bg-flag-strength/90 text-xs h-8"
                  >
                    <Check className="h-3.5 w-3.5 mr-1" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditing(true)}
                    className="border-border text-text-secondary hover:text-text-primary text-xs h-8"
                  >
                    <Pencil className="h-3.5 w-3.5 mr-1" /> Edit
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleReject}
                    disabled={acting}
                    className="border-flag-critical/50 text-flag-critical hover:bg-flag-critical/10 text-xs h-8"
                  >
                    <X className="h-3.5 w-3.5 mr-1" /> Reject
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    size="sm"
                    onClick={handleApprove}
                    disabled={acting}
                    className="bg-flag-strength text-white hover:bg-flag-strength/90 text-xs h-8"
                  >
                    <Check className="h-3.5 w-3.5 mr-1" /> {hasEdits ? "Approve with edits" : "Approve"}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { setEditing(false); setEditedPlan(task.step_plan); setEditedSummary(task.exec_summary); }}
                    className="border-border text-text-secondary hover:text-text-primary text-xs h-8"
                  >
                    Cancel
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TaskLane                                                          */
/* ------------------------------------------------------------------ */

interface LaneConfig {
  title: string;
  statuses: string;
  collapsible?: boolean;
}

function TaskLane({
  config,
  projectId,
  department,
  agent,
}: {
  config: LaneConfig;
  projectId: string;
  department?: string;
  agent?: string;
}) {
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expanded, setExpanded] = useState(!config.collapsible);
  const [hasFetched, setHasFetched] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const statusOptions = config.statuses.split(",");
  const activeStatuses = statusFilter || config.statuses;

  const fetchTasks = useCallback(
    async (before?: string) => {
      const page = await api.getProjectTasks(projectId, {
        status: activeStatuses,
        department,
        agent,
        limit: 25,
        before,
      });
      return page;
    },
    [projectId, activeStatuses, department, agent],
  );

  // Defer fetch for collapsible lanes until first expand
  useEffect(() => {
    if (!expanded && !hasFetched) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setHasFetched(true);
    fetchTasks().then((page) => {
      setTasks(page.tasks);
      setTotalCount(page.totalCount);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [fetchTasks, expanded]);

  async function loadMore() {
    if (tasks.length === 0) return;
    setLoadingMore(true);
    try {
      const oldest = tasks[tasks.length - 1].created_at;
      const page = await fetchTasks(oldest);
      setTasks((prev) => [...prev, ...page.tasks]);
    } finally {
      setLoadingMore(false);
    }
  }

  function handleTaskUpdate(updated: AgentTask) {
    // If the task's status no longer belongs in this lane, remove it
    const laneStatuses = activeStatuses.split(",");
    if (!laneStatuses.includes(updated.status)) {
      setTasks((prev) => prev.filter((t) => t.id !== updated.id));
      setTotalCount((prev) => Math.max(0, prev - 1));
    } else {
      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    }
  }

  const hasMore = tasks.length < totalCount;

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={config.collapsible ? () => setExpanded(!expanded) : undefined}
          className={`flex items-center gap-2 ${config.collapsible ? "cursor-pointer hover:text-text-primary" : "cursor-default"}`}
        >
          {config.collapsible && (
            expanded
              ? <ChevronUp className="h-4 w-4 text-text-secondary" />
              : <ChevronDown className="h-4 w-4 text-text-secondary" />
          )}
          <h3 className="text-sm font-medium text-text-heading">{config.title}</h3>
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-bg-input border border-border text-text-secondary">
            {totalCount}
          </span>
        </button>

        {/* Status filter */}
        {statusOptions.length > 1 && expanded && (
          <div className="flex items-center gap-1">
            <Filter className="h-3 w-3 text-text-secondary" />
            <select
              value={statusFilter || ""}
              onChange={(e) => setStatusFilter(e.target.value || null)}
              className="text-xs bg-bg-input border border-border rounded px-1.5 py-0.5 text-text-secondary outline-none focus:border-accent-gold"
            >
              <option value="">All</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Task list */}
      {expanded && (
        <>
          {loading ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-4 w-4 text-text-secondary animate-spin" />
            </div>
          ) : tasks.length === 0 ? (
            <p className="text-text-secondary text-xs py-4 text-center">
              No tasks.
            </p>
          ) : (
            <div className="space-y-2">
              {tasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  projectId={projectId}
                  onUpdate={handleTaskUpdate}
                />
              ))}
              {hasMore && (
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="w-full text-xs text-text-secondary hover:text-text-primary py-2 transition-colors flex items-center justify-center gap-1"
                >
                  {loadingMore ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    `Load more (${totalCount - tasks.length} remaining)`
                  )}
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TaskQueue — main exported component                               */
/* ------------------------------------------------------------------ */

export function TaskQueue({
  projectId,
  department,
  agent,
}: {
  projectId: string;
  department?: string;
  agent?: string;
}) {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Task Queue</h2>

      {/* Two lanes side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <TaskLane
          config={{ title: "Needs Attention", statuses: "awaiting_approval,queued,failed" }}
          projectId={projectId}
          department={department}
          agent={agent}
        />
        <TaskLane
          config={{ title: "In Progress", statuses: "processing,awaiting_dependencies" }}
          projectId={projectId}
          department={department}
          agent={agent}
        />
      </div>

      {/* Collapsed completed stack */}
      <TaskLane
        config={{ title: "Completed", statuses: "done", collapsible: true }}
        projectId={projectId}
        department={department}
        agent={agent}
      />
    </div>
  );
}
```

- [ ] **Step 2: Remove `statusColors`, `TaskCard`, and `DashboardView` from page.tsx**

In `frontend/app/(app)/project/[...path]/page.tsx`:

1. Remove lines 45-319 (the `statusColors` const, `TaskCard` component, and `DashboardView` component).
2. Remove the `tasks` state and `setTasks` calls — TaskQueue manages its own data now.
3. Remove the unused imports that were only used by TaskCard/DashboardView: `Check`, `X`, `AlertCircle`, `Pencil`, `Clock` (keep any still used elsewhere in the file).
4. Remove `ReactMarkdown` import and `Input` import if no longer used in page.tsx.
5. Add import at top: `import { TaskQueue } from "@/components/task-queue";`

- [ ] **Step 3: Replace DashboardView usage with TaskQueue**

In the main area rendering (around line 1252 after removals), replace:

```tsx
{view === "dashboard" && (
  <DashboardView
    tasks={tasks}
    projectId={project.id}
    onTaskUpdate={handleTaskUpdate}
  />
)}
```

With:

```tsx
{view === "dashboard" && (
  <TaskQueue projectId={project.id} />
)}
```

Also remove the `handleTaskUpdate` function and `tasks` state (`useState<AgentTask[]>([])`) and the `api.getProjectTasks` call in the `load` callback since TaskQueue fetches its own data.

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npx next build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/task-queue.tsx frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: extract TaskQueue component with two-lane layout and cursor pagination"
```

---

### Task 4: Frontend — Add TaskQueue to DepartmentView and AgentDetailView

**Files:**
- Modify: `frontend/app/(app)/project/[...path]/page.tsx` (DepartmentView ~line 459, AgentDetailView ~line 824)

- [ ] **Step 1: Add TaskQueue to DepartmentView**

In the `DepartmentView` component, after the closing `</div>` of the available agents section (the `</div>` that closes the return's root `<div>`), add the TaskQueue just before the final closing tag:

```tsx
      {/* Department task queue */}
      <div className="mt-8">
        <TaskQueue projectId={projectId} department={dept.id} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add "Tasks" tab to AgentDetailView**

In the `AgentDetailView` component:

1. Change the `tab` state type to include "tasks":

```tsx
const [tab, setTab] = useState<"overview" | "instructions" | "config" | "tasks">("overview");
```

2. Add the Tasks tab to the `tabs` array (add `ListTodo` to the lucide imports in page.tsx):

```tsx
  const tabs = [
    { key: "overview" as const, label: "Overview", icon: FileText },
    { key: "tasks" as const, label: "Tasks", icon: ListTodo },
    { key: "instructions" as const, label: "Instructions", icon: Terminal },
    { key: "config" as const, label: "Config", icon: Settings2 },
  ];
```

3. Add the tab content after the config tab rendering:

```tsx
      {/* Tasks tab */}
      {tab === "tasks" && (
        <div className="flex-1 overflow-y-auto min-h-0">
          <TaskQueue projectId={projectId} agent={agent.id} />
        </div>
      )}
```

Note: `AgentDetailView` needs the `projectId` prop to actually be used. Check that it's passed through — it's in the component signature already (`projectId: string`) but not destructured in the current code. Verify and fix if needed.

- [ ] **Step 3: Add `ListTodo` to lucide imports**

At the top of page.tsx, in the lucide-react import, add `ListTodo`:

```tsx
import {
  Loader2,
  LayoutDashboard,
  ChevronLeft,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  ToggleLeft,
  ToggleRight,
  Save,
  FileText,
  Terminal,
  Settings2,
  Plus,
  ListTodo,
} from "lucide-react";
```

(Remove any icons no longer used after TaskCard extraction — `Check`, `X`, `AlertCircle`, `Pencil`, `Clock` — if they're not used elsewhere in page.tsx.)

- [ ] **Step 4: Verify build compiles**

Run: `cd frontend && npx next build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat: add TaskQueue to department page and agent detail Tasks tab"
```

---

### Task 5: Cleanup and verify end-to-end

**Files:**
- Verify: `backend/agents/views/agent_task_view.py`, `frontend/components/task-queue.tsx`, `frontend/app/(app)/project/[...path]/page.tsx`

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python manage.py test agents.tests.test_views -v 2`
Expected: All tests PASS.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npx next build`
Expected: Build succeeds with no errors.

- [ ] **Step 3: Verify no leftover references to old DashboardView**

Run: `grep -r "DashboardView\|handleTaskUpdate" frontend/` — should return nothing.
Run: `grep -r "statusColors" frontend/app/` — should return nothing (it's now in task-queue.tsx only).

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: cleanup after task queue redesign"
```

# WebSocket Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one-shot, silent-failure WebSocket connection with a reconnecting hook that logs every state transition.

**Architecture:** New `useProjectWebSocket` hook owns the full lifecycle (ticket fetch → connect → reconnect on failure). The existing inline WebSocket `useEffect` in the project page is replaced by a single hook call. Backend gets logging in the ticket auth and consumer layers.

**Tech Stack:** React hooks, browser WebSocket API, Django Channels, Python logging

**Spec:** `docs/superpowers/specs/2026-04-07-websocket-reliability-design.md`

---

### Task 1: Backend — Add logging to ticket auth

**Files:**
- Modify: `backend/config/ws_auth.py`

- [ ] **Step 1: Add logger and log ticket creation**

```python
# backend/config/ws_auth.py — full file rewrite
"""WebSocket authentication via one-time tickets."""
import logging
import uuid
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.core.cache import cache

logger = logging.getLogger(__name__)

TICKET_PREFIX = "ws_ticket:"
TICKET_TTL = 30

def create_ws_ticket(user_id) -> str:
    ticket = uuid.uuid4().hex
    cache.set(f"{TICKET_PREFIX}{ticket}", str(user_id), timeout=TICKET_TTL)
    logger.debug("WS ticket created: user=%s ticket=%s...", user_id, ticket[:8])
    return ticket

@database_sync_to_async
def consume_ticket(ticket: str):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    key = f"{TICKET_PREFIX}{ticket}"
    user_id = cache.get(key)
    if user_id is None:
        logger.warning("WS ticket not found or expired: %s...", ticket[:8])
        return None
    cache.delete(key)
    try:
        user = User.objects.get(pk=user_id)
        logger.debug("WS ticket consumed: user=%s ticket=%s...", user_id, ticket[:8])
        return user
    except User.DoesNotExist:
        logger.warning("WS ticket user not found: user_id=%s", user_id)
        return None

class TicketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        ticket = params.get("ticket", [None])[0]
        if ticket:
            user = await consume_ticket(ticket)
            if user:
                scope["user"] = user
                logger.debug("WS auth success: user=%s", user.pk)
            else:
                logger.warning("WS auth failed: ticket=%s...", ticket[:8])
        else:
            logger.debug("WS connection without ticket")
        return await super().__call__(scope, receive, send)
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

Run: `cd backend && python -m pytest config/tests/test_ws_auth_full.py -v`
Expected: All 7 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/config/ws_auth.py
git commit -m "feat(ws): add logging to ticket auth flow"
```

---

### Task 2: Backend — Add logging to WebSocket consumers

**Files:**
- Modify: `backend/projects/consumers.py`

- [ ] **Step 1: Add logger and connection logging to both consumers**

```python
# backend/projects/consumers.py — full file rewrite
"""WebSocket consumers for project real-time updates."""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


@database_sync_to_async
def is_project_member(user, project_id):
    from projects.models import Project

    return Project.objects.filter(id=project_id, members=user).exists()


class BootstrapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"bootstrap_{self.project_id}"

        user = self.scope.get("user")
        if not user or user.is_anonymous:
            logger.warning("BootstrapConsumer rejected: anonymous user, project=%s", self.project_id)
            await self.close()
            return

        if not await is_project_member(user, self.project_id):
            logger.warning("BootstrapConsumer rejected: user=%s not member of project=%s", user.pk, self.project_id)
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("BootstrapConsumer connected: project=%s user=%s", self.project_id, user.pk)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("BootstrapConsumer disconnected: project=%s code=%s", getattr(self, "project_id", "?"), close_code)

    async def bootstrap_status(self, event):
        """Send bootstrap status update to the client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "bootstrap.status",
                    "status": event.get("status"),
                    "proposal_id": event.get("proposal_id"),
                    "error_message": event.get("error_message"),
                    "phase": event.get("phase", ""),
                    "progress": event.get("progress", 0),
                    "events": event.get("events", []),
                }
            )
        )

    async def agent_status(self, event):
        """Send agent provisioning status update to the client."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "agent.status",
                    "agent_id": event.get("agent_id"),
                    "department_id": event.get("department_id"),
                    "status": event.get("status"),
                    "error_message": event.get("error_message", ""),
                }
            )
        )


class ProjectConsumer(AsyncWebsocketConsumer):
    """General-purpose project WebSocket — receives agent status, department status, etc."""

    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"project_{self.project_id}"

        user = self.scope.get("user")
        if not user or user.is_anonymous:
            logger.warning("ProjectConsumer rejected: anonymous user, project=%s", self.project_id)
            await self.close()
            return

        if not await is_project_member(user, self.project_id):
            logger.warning("ProjectConsumer rejected: user=%s not member of project=%s", user.pk, self.project_id)
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info("ProjectConsumer connected: project=%s user=%s", self.project_id, user.pk)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("ProjectConsumer disconnected: project=%s code=%s", getattr(self, "project_id", "?"), close_code)

    async def agent_status(self, event):
        """Forward agent provisioning status update."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "agent.status",
                    "agent_id": event.get("agent_id"),
                    "department_id": event.get("department_id"),
                    "status": event.get("status"),
                    "error_message": event.get("error_message", ""),
                }
            )
        )

    async def department_status(self, event):
        """Forward department configuration status update."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "department.status",
                    "department_id": event.get("department_id"),
                    "status": event.get("status"),
                    "phase": event.get("phase", ""),
                    "error_message": event.get("error_message", ""),
                }
            )
        )

    async def task_created(self, event):
        """Forward task created event."""
        await self.send(text_data=json.dumps({"type": "task.created", "task": event.get("task")}))

    async def task_updated(self, event):
        """Forward task updated event."""
        await self.send(text_data=json.dumps({"type": "task.updated", "task": event.get("task")}))

    async def sprint_created(self, event):
        """Forward sprint created event."""
        await self.send(text_data=json.dumps({"type": "sprint.created", "sprint": event.get("sprint")}))

    async def sprint_updated(self, event):
        """Forward sprint updated event."""
        await self.send(text_data=json.dumps({"type": "sprint.updated", "sprint": event.get("sprint")}))
```

- [ ] **Step 2: Run existing tests**

Run: `cd backend && python -m pytest config/tests/test_ws_auth_full.py -v`
Expected: All tests PASS (consumers aren't directly tested yet but imports should not break)

- [ ] **Step 3: Commit**

```bash
git add backend/projects/consumers.py
git commit -m "feat(ws): add logging to WebSocket consumers"
```

---

### Task 3: Frontend — Create `useProjectWebSocket` hook

**Files:**
- Create: `frontend/lib/useProjectWebSocket.ts`

- [ ] **Step 1: Create the hook**

```typescript
// frontend/lib/useProjectWebSocket.ts
"use client";

import { useEffect, useRef } from "react";
import { api } from "./api";

const WS_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

const MAX_RETRIES = 20;
const BACKOFF_CAP_MS = 30_000;

function backoffMs(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, BACKOFF_CAP_MS);
}

/**
 * Manages a reconnecting WebSocket connection for a project.
 * Fetches a fresh ticket on each connection attempt.
 * Logs every state transition to the console.
 */
export function useProjectWebSocket(
  projectId: string | null,
  onMessage: (data: Record<string, unknown>) => void,
): void {
  // Keep onMessage ref stable so reconnects use the latest handler
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!projectId) return;

    let ws: WebSocket | null = null;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const path = `/ws/project/${projectId}/`;

    async function connect() {
      if (stopped) return;

      console.log(`[WS] connecting to ${path}... (attempt ${attempt + 1}/${MAX_RETRIES})`);

      let ticket: string;
      try {
        const resp = await api.getWsTicket();
        ticket = resp.ticket;
      } catch (err) {
        console.warn(`[WS] ticket fetch failed:`, err);
        scheduleReconnect();
        return;
      }

      if (stopped) return;

      const url = `${WS_URL}${path}?ticket=${ticket}`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`[WS] connected to ${path}`);
        attempt = 0; // reset backoff on success
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = (event) => {
        if (stopped) return;
        console.warn(`[WS] disconnected (code: ${event.code}), scheduling reconnect`);
        ws = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — let onclose handle reconnect
      };
    }

    function scheduleReconnect() {
      if (stopped) return;
      attempt += 1;
      if (attempt > MAX_RETRIES) {
        console.error(`[WS] max retries (${MAX_RETRIES}) reached, giving up`);
        return;
      }
      const delay = backoffMs(attempt - 1);
      console.log(`[WS] reconnecting in ${delay}ms (attempt ${attempt}/${MAX_RETRIES})`);
      timer = setTimeout(connect, delay);
    }

    connect();

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (ws) {
        ws.onclose = null; // prevent reconnect on intentional close
        ws.close();
      }
      console.log(`[WS] cleanup for ${path}`);
    };
  }, [projectId]);
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit lib/useProjectWebSocket.ts 2>&1 | head -20`
Expected: No errors (or only unrelated pre-existing errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/useProjectWebSocket.ts
git commit -m "feat(ws): add useProjectWebSocket hook with reconnection and logging"
```

---

### Task 4: Frontend — Wire hook into project page and clean up old code

**Files:**
- Modify: `frontend/app/(app)/project/[...path]/page.tsx`
- Modify: `frontend/lib/ws.ts`

- [ ] **Step 1: Replace inline WebSocket effect with hook**

In `frontend/app/(app)/project/[...path]/page.tsx`:

Replace the import:
```typescript
// OLD
import { connectWs } from "@/lib/ws";
// NEW
import { useProjectWebSocket } from "@/lib/useProjectWebSocket";
```

Remove `wsRef`:
```typescript
// DELETE this line:
const wsRef = useRef<WebSocket | null>(null);
```

Replace the entire WebSocket `useEffect` (lines 126-202) with:

```typescript
  // WebSocket for real-time updates
  useProjectWebSocket(project?.id ?? null, (data) => {
    if (data.type === "task.created" || data.type === "task.updated") {
      const task = data.task as import("@/lib/types").AgentTask;
      setTaskWsEvent({ type: data.type, task });
      const agentId = task.agent;
      setProject((prev) => {
        if (!prev) return prev;
        const dept = prev.departments.find((d) => d.agents.some((a) => a.id === agentId));
        if (dept) {
          setActiveTasks((prevMap) => {
            const next = new Map(prevMap);
            const isActive = task.status === "processing" || task.status === "queued";
            const deptTasks = next.get(dept.id) || new Set<string>();
            const updated = new Set(deptTasks);
            if (isActive) {
              updated.add(task.id);
            } else {
              updated.delete(task.id);
            }
            if (updated.size > 0) {
              next.set(dept.id, updated);
            } else {
              next.delete(dept.id);
            }
            return next;
          });
        }
        return prev;
      });
    }
    if (data.type === "sprint.created" || data.type === "sprint.updated") {
      api.listSprints(project!.id, { status: "running,paused" }).then(setSprints).catch(() => {});
    }
    if (data.type === "agent.status") {
      const agentId = data.agent_id as string;
      const newStatus = data.status as string;
      setProject((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          departments: prev.departments.map((dept) => ({
            ...dept,
            agents: dept.agents.map((a) =>
              a.id === agentId ? { ...a, status: newStatus as AgentSummary["status"] } : a,
            ),
          })),
        };
      });
      setSelectedDept((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          agents: prev.agents.map((a) =>
            a.id === agentId ? { ...a, status: newStatus as AgentSummary["status"] } : a,
          ),
        };
      });
      setSelectedAgent((prev) => {
        if (!prev || prev.id !== agentId) return prev;
        return { ...prev, status: newStatus as AgentSummary["status"] };
      });
    }
  });
```

- [ ] **Step 2: Check if `connectWs` is used anywhere else**

Run: `cd frontend && grep -r "connectWs\|from.*ws.*import" --include="*.ts" --include="*.tsx" | grep -v node_modules | grep -v useProjectWebSocket`

If `connectWs` is only used in `page.tsx` (which we just replaced), proceed to step 3. If it's used elsewhere, keep `ws.ts` and just remove the `connectWs` function.

- [ ] **Step 3: Simplify `ws.ts`**

If `connectWs` is not used anywhere else, replace `frontend/lib/ws.ts` with:

```typescript
// frontend/lib/ws.ts
/**
 * WebSocket URL base — derived from API URL.
 * Used by useProjectWebSocket hook.
 */
export const WS_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://");
```

Then update `useProjectWebSocket.ts` to import `WS_URL` from `./ws` instead of computing it inline:

```typescript
// At top of useProjectWebSocket.ts, replace the WS_URL const with:
import { WS_URL } from "./ws";
```

- [ ] **Step 4: Verify the app compiles**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/ws.ts frontend/lib/useProjectWebSocket.ts frontend/app/\(app\)/project/\[...path\]/page.tsx
git commit -m "feat(ws): wire useProjectWebSocket hook, remove one-shot connectWs"
```

---

### Task 5: Manual smoke test

- [ ] **Step 1: Start the dev environment**

Run: `./start-dev.sh`

- [ ] **Step 2: Open browser console and navigate to a project page**

Look for:
```
[WS] connecting to /ws/project/{id}/... (attempt 1/20)
[WS] connected to /ws/project/{id}/
```

- [ ] **Step 3: Trigger a sprint and verify task updates arrive**

In the UI, start a sprint. Watch the browser console for:
```
[WS] message received: task.created
[WS] message received: task.updated
```

And verify the task queue in the UI updates without a page refresh.

- [ ] **Step 4: Test reconnection — restart the backend**

Kill the Django process (`pkill -f runserver`) and restart it. Watch the browser console for:
```
[WS] disconnected (code: 1006), scheduling reconnect
[WS] reconnecting in 1000ms (attempt 1/20)
[WS] connecting to /ws/project/{id}/... (attempt 1/20)
[WS] connected to /ws/project/{id}/
```

- [ ] **Step 5: Check backend logs for ticket auth flow**

In the Django/Daphne terminal output, look for:
```
WS ticket created: user=... ticket=abc12345...
WS ticket consumed: user=... ticket=abc12345...
ProjectConsumer connected: project=... user=...
```

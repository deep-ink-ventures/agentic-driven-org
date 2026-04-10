# WebSocket Reliability — Design Spec

## Problem

WebSocket connections for project task updates fail silently on initial connect. The connection logic lives inline in a page component with `.catch(() => {})` — no reconnection, no error visibility, no recovery. Users must refresh the page to see task updates.

## Root Cause

The `connectWs` function in `frontend/lib/ws.ts` is a one-shot fire-and-forget: fetch ticket, open socket, done. If any step fails — ticket fetch 401, WebSocket handshake timeout, server restart, network hiccup — the connection is dead with no retry and no indication to the developer.

## Solution

### 1. `useProjectWebSocket` hook — `frontend/lib/useProjectWebSocket.ts` (new file)

Single hook that owns the full WebSocket lifecycle for a project.

**Signature:**
```typescript
function useProjectWebSocket(
  projectId: string | null,
  onMessage: (data: Record<string, unknown>) => void,
): void
```

**Lifecycle:**
1. Wait for `projectId` to be non-null
2. Fetch a fresh ticket via `api.getWsTicket()`
3. Open WebSocket to `ws://.../ws/project/{id}/?ticket={ticket}`
4. On `onopen`: reset backoff, log success
5. On `onmessage`: parse JSON, call `onMessage`
6. On `onclose` / `onerror`: schedule reconnect from step 2

**Reconnection strategy:**
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, capped at 30s
- Reset backoff to 1s on successful connection (received `onopen`)
- Max 20 attempts before giving up
- Each reconnect fetches a NEW ticket (tickets are one-time-use, 30s TTL)

**Console logging (every state transition):**
```
[WS] connecting to /ws/project/abc-123/...
[WS] connected
[WS] message received: task.updated
[WS] disconnected (code: 1006), reconnecting in 2s (attempt 3/20)
[WS] ticket fetch failed: 401, reconnecting in 4s (attempt 4/20)
[WS] max retries reached, giving up
```

**Cleanup:** `useEffect` teardown closes the socket and cancels any pending reconnect timer.

### 2. Simplify `frontend/lib/ws.ts`

Strip `connectWs` down to a bare connection factory — no ticket fetching, no message handling:

```typescript
export function createWsUrl(path: string, ticket: string): string {
  return `${WS_URL}${path}?ticket=${ticket}`;
}
```

The hook handles everything else. `connectWs` can be removed or kept as a thin wrapper for other consumers if needed.

### 3. Update `frontend/app/(app)/project/[...path]/page.tsx`

Replace the 80-line inline `useEffect` WebSocket block (lines 126-202) with:

```typescript
useProjectWebSocket(project?.id ?? null, (data) => {
  // existing message handler logic (task.created, task.updated, etc.)
});
```

The message handler callback stays in the page component — it knows about `setProject`, `setTaskWsEvent`, etc. Only the connection lifecycle moves to the hook.

### 4. Backend logging — `backend/config/ws_auth.py`

Add logging to the ticket auth flow:

```python
logger.debug("WS ticket created for user=%s", user_id)
logger.debug("WS ticket consumed for user=%s", user_id)
logger.warning("WS ticket expired or not found: %s...", ticket[:8])
logger.warning("WS ticket user not found: %s", user_id)
```

This makes it possible to diagnose "ticket was created but never consumed" (connection never reached the server) vs. "ticket was consumed but connection was rejected" (auth check failed).

### 5. Backend logging — `backend/projects/consumers.py`

Add logging to consumer connect/disconnect:

```python
logger.info("ProjectConsumer connected: project=%s user=%s", self.project_id, user)
logger.warning("ProjectConsumer rejected: project=%s user=%s (not member)", self.project_id, user)
logger.warning("ProjectConsumer rejected: anonymous user")
logger.debug("ProjectConsumer disconnected: project=%s code=%s", self.project_id, close_code)
```

## Files Changed

| File | Change |
|------|--------|
| `frontend/lib/useProjectWebSocket.ts` | New — the entire lifecycle hook |
| `frontend/lib/ws.ts` | Simplify to URL builder only |
| `frontend/app/(app)/project/[...path]/page.tsx` | Replace inline WS effect with hook call |
| `backend/config/ws_auth.py` | Add debug/warning logging |
| `backend/projects/consumers.py` | Add info/warning/debug logging |

## Testing

**Frontend unit test** (`useProjectWebSocket.test.ts`):
- Mock WebSocket class
- Verify: connects on mount, calls onMessage on incoming data
- Verify: reconnects with backoff on close event
- Verify: fetches new ticket on each reconnect
- Verify: stops after max retries
- Verify: cleans up on unmount (closes socket, cancels timer)

**Backend tests** (existing test files):
- Verify ticket create → consume → expire flow (partially covered already)
- Add: verify expired ticket returns None
- Add: verify consumed ticket cannot be reused

## Out of Scope

- Visual connection indicator in UI (console logging only for now)
- Polling fallback
- Server-side heartbeat/ping-pong

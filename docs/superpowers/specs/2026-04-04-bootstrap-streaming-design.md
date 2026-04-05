# Bootstrap Streaming Progress — Design Spec

**Date:** 2026-04-04
**Status:** Approved

## Overview

Replace the blocking `call_claude()` in the bootstrap task with a streaming variant that broadcasts real-time semantic progress to the frontend via WebSocket. Users see department and agent names appearing as Claude generates them, plus a token-based progress bar.

## Current Flow

1. Celery task `bootstrap_project` calls `call_claude()` — blocks for 20-40s
2. Broadcasts static phase strings via `_broadcast_bootstrap()`: "Gathering sources" → "Building your project structure" → "Validating proposal"
3. Frontend step 4 shows a spinner + phase text. No progress indicator.

## New Flow

1. Celery task calls `stream_claude()` with an `on_progress` callback
2. As tokens stream in, the callback:
   - Scans accumulated text with regex for `"name": "..."` patterns (department and agent names)
   - Broadcasts each newly detected name via WebSocket
   - Broadcasts token progress percentage
3. Frontend step 4 shows:
   - Phase text (updates as new milestones detected)
   - Progress bar (token-based percentage)
   - Stacking event list: department and agent names appearing one by one with fade-in

## Backend Changes

### New function: `stream_claude()` in `agents/ai/claude_client.py`

```python
def stream_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
    on_progress: Callable[[str, int], None] | None = None,
) -> tuple[str, dict]:
```

- Uses `client.messages.stream()` instead of `client.messages.create()`
- Accumulates tokens into a text buffer
- Calls `on_progress(accumulated_text, output_tokens_so_far)` after each chunk
- Returns `(full_response_text, usage_dict)` — same interface as `call_claude()`

### Modified: `_broadcast_bootstrap()` in `projects/tasks.py`

Add optional `progress` (int, 0-100) and `events` (list of strings) fields to the WebSocket message. Backwards compatible — frontend ignores fields it doesn't know about.

### Modified: `bootstrap_project()` in `projects/tasks.py`

Replace:
```python
response, _usage = call_claude(...)
```

With a callback that:
1. Regex-scans accumulated text for `"name"\s*:\s*"([^"]+)"` patterns
2. Tracks which names have already been broadcast (dedup set)
3. Infers whether each name is a department or agent from surrounding JSON context (e.g. presence of `"department_type"` nearby = department, `"agent_type"` nearby = agent)
4. Broadcasts phase text like "Creating Engineering department" or "Adding Twitter Specialist"
5. Broadcasts progress as `int(output_tokens / max_tokens * 100)`
6. Broadcasts cumulative events list

## Frontend Changes

### Modified: step 4 in `create-project-wizard.tsx`

Current step 4 renders:
- Phase text
- Spinner
- "This may take a moment"

New step 4 renders:
- Phase text (from WebSocket, updates live)
- Progress bar (thin, uses `progress` field from WebSocket, 0-100%)
- Event list: each entry from `events` array, rendered as a stacking list with checkmark icon + fade-in animation
- Last event shows a dot/spinner instead of checkmark (currently in progress)

### WebSocket message shape (unchanged protocol, new fields)

```json
{
  "type": "bootstrap.status",
  "status": "processing",
  "proposal_id": "...",
  "phase": "Designing agent roles",
  "progress": 58,
  "events": [
    "Engineering department",
    "Head of Engineering",
    "Marketing department",
    "Head of Marketing",
    "Twitter Specialist"
  ]
}
```

## Files to modify

- `backend/agents/ai/claude_client.py` — add `stream_claude()`
- `backend/projects/tasks.py` — use `stream_claude()` with on_progress callback, add `progress`/`events` to `_broadcast_bootstrap()`
- `frontend/components/create-project-wizard.tsx` — update step 4 UI

## Out of scope

- Streaming for other Claude calls (agent tasks, etc.)
- Cancellation support
- Token cost display during streaming

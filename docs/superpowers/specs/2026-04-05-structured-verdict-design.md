# Structured Review Verdict via tool_use

**Date:** 2026-04-05
**Problem:** `parse_review_verdict` relies on regex matching a specific text format (`VERDICT: APPROVED (score: N.N/10)`). If Claude formats it differently, the fallback silently returns `("CHANGES_REQUESTED", 0.0)`, burning review rounds for no reason.
**Solution:** Use Claude's `tool_use` to force structured verdict output. The API validates the JSON schema, guaranteeing format correctness.

## Changes

### 1. `claude_client.py` — add `call_claude_with_tools`

New function alongside existing `call_claude`:

```python
def call_claude_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
) -> tuple[str, dict | None, dict]:
```

- Passes `tools` to `client.messages.create()`
- Iterates response content blocks: concatenates `text` blocks into the report string, extracts the first `tool_use` block's `input` as structured data
- Returns `(report_text, tool_input_or_None, usage_dict)`
- `call_claude` stays unchanged — non-review tasks are unaffected

### 2. `base.py` — verdict tool definition

Constant at module level:

```python
VERDICT_TOOL = {
    "name": "submit_verdict",
    "description": "Submit your review verdict. You MUST call this tool after completing your review.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["APPROVED", "CHANGES_REQUESTED"],
            },
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 10,
                "description": "Overall review score out of 10",
            },
        },
        "required": ["verdict", "score"],
    },
}
```

No `summary` field — the report text already contains the full review. Keep the tool minimal.

### 3. `WorkforceBlueprint.execute_task` — conditional tool injection

- If the blueprint has `review_dimensions` (non-empty list), call `call_claude_with_tools` with `[VERDICT_TOOL]` instead of `call_claude`
- If the tool response contains a `submit_verdict` call, store `review_verdict` and `review_score` on the task
- If Claude doesn't call the tool (edge case), fall back to `parse_review_verdict` on the report text and log a warning

### 3b. Writers room leader `_evaluate_feedback` — same tool

The writers room leader currently uses `call_claude` + `parse_json_response` to extract `overall_score` from a JSON response body (and also asks for a redundant VERDICT line). Switch to `call_claude_with_tools` with `[VERDICT_TOOL]`. The score comes from the tool call; the JSON body with `fix_tasks` stays in the text response and continues to be parsed with `parse_json_response`.

### 3c. Ecosystem analyst — drop custom JSON verdict

The ecosystem analyst currently returns its own JSON schema with `verdict` and `overall_score` fields. Replace the verdict/score portion with the `submit_verdict` tool. The rest of the JSON body (`entity_reviews`, `missing_categories`, etc.) stays as text output.

### 4. `AgentTask` model — persist verdict

Two new fields:

```python
review_verdict = models.CharField(max_length=20, blank=True)
review_score = models.FloatField(null=True, blank=True)
```

Migration adds these as nullable/blank fields — no data backfill needed.

### 5. `_evaluate_review_and_loop` — read from model first

Change the verdict source priority:
1. If `review_task.review_verdict` and `review_task.review_score is not None` — use stored values
2. Else — fall back to `parse_review_verdict(report)` (with warning log)

### 6. `parse_review_verdict` — add warning logging

Keep the function as-is but add `logger.warning` when the regex fails and fallback triggers. This makes fallback usage visible in logs.

### 7. Serializer + WebSocket + Admin

- Add `review_verdict` and `review_score` to `AgentTaskSerializer.fields`
- Add to `_broadcast_task` payload
- Add to admin `list_display` and `readonly_fields`

### 8. Reviewer system prompts — update instructions

All reviewer agents currently say "End your report with exactly one of these lines: VERDICT: ...". Update to:

> "After your review, call the `submit_verdict` tool with your verdict and score."

Remove the text-format VERDICT instructions from system prompts and task suffixes. The tool definition itself documents the expected input.

Affected files (all departments):
- `marketing/workforce/content_reviewer/agent.py` — system prompt + task suffix
- `sales/workforce/outreach_reviewer/agent.py` — system prompt + task suffix
- `community/workforce/partnership_reviewer/agent.py` — system prompt + task suffix
- `community/workforce/ecosystem_analyst/agent.py` — system prompt + task suffix (drop custom JSON verdict fields)
- `engineering/workforce/review_engineer/agent.py` — system prompt
- `engineering/leader/agent.py` — step_plan text in review chain
- `writers_room/leader/agent.py` — `_evaluate_feedback` prompt (drop VERDICT line, score comes from tool)
- Corresponding command description strings

## What does NOT change

- `call_claude` — unchanged, non-review tasks unaffected
- `stream_claude` — unchanged, not used for reviews
- Quality gate logic (`should_accept_review`, `_apply_quality_gate`) — unchanged, just reads score from a different source
- `EXCELLENCE_THRESHOLD`, `MAX_REVIEW_ROUNDS`, etc. — unchanged
- Review pair definitions in leader blueprints — unchanged
- Writers room `fix_tasks` JSON structure — still parsed from text response body
- Ecosystem analyst `entity_reviews`/`missing_categories` — still in text response body

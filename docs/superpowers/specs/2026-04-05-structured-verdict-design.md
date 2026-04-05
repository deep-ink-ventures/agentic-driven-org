# Structured Review Verdicts + Universal Review Pattern

**Date:** 2026-04-05

**Problem:** Two issues that are really one:

1. **Fragile verdict parsing.** `parse_review_verdict` relies on regex matching `VERDICT: APPROVED (score: N.N/10)`. If Claude formats it slightly differently, the fallback silently returns `("CHANGES_REQUESTED", 0.0)`, burning review rounds.

2. **Writers room doesn't follow the universal pattern.** Engineering, marketing, sales, and community all work the same way: leader dispatches → creators create → reviewers review → base class ping-pong. The writers room leader calls Claude directly for evaluation, bypasses `get_review_pairs()` and `_evaluate_review_and_loop`, and has its own custom evaluation logic. This is the only department that deviates.

**Solution:** One structured verdict mechanism (`submit_verdict` tool_use) in the base class, and refactor the writers room to use the same leader→creator→reviewer pattern as every other department.

## Part A: Structured Verdict via tool_use

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

### 3. `WorkforceBlueprint.execute_task` — inject verdict tool for reviewers

One call site in the base class handles all reviewers across all departments:

- If the blueprint has `review_dimensions` (non-empty list), call `call_claude_with_tools` with `[VERDICT_TOOL]` instead of `call_claude`
- Extract `review_verdict` and `review_score` from the tool call and store on the task
- If Claude doesn't call the tool (edge case), fall back to `parse_review_verdict` on the report text and log a warning

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

Remove text-format VERDICT instructions from all reviewer system prompts and task suffixes. The `submit_verdict` tool definition speaks for itself. Add a single line: "After your review, call the `submit_verdict` tool with your verdict and score."

Affected reviewer agents:
- `marketing/workforce/content_reviewer/agent.py`
- `sales/workforce/outreach_reviewer/agent.py`
- `community/workforce/partnership_reviewer/agent.py`
- `community/workforce/ecosystem_analyst/agent.py`
- `engineering/workforce/review_engineer/agent.py`
- `engineering/leader/agent.py` (VERDICT instructions in step_plan text)

## Part B: Writers Room — align with universal pattern

### Current state (violations)

The writers room leader:
- Does NOT define `get_review_pairs()`
- Calls Claude directly in `_evaluate_feedback()` and `_evaluate_ideation_feedback()` to score and route fixes
- Feedback agents produce reports but the leader consolidates and scores — the leader is acting as the reviewer

Every other department: leader dispatches, workforce creates, workforce reviews, base class ping-pongs.

### Target state

The writers room works like every other department. The only department-specific things are:
- Which agent types exist (creative agents + feedback agents)
- The stage pipeline and depth matrix (which agents work at which stage)
- Task dependencies (story_architect after story_researcher, etc.)

### 9. New workforce agent: `creative_reviewer`

A reviewer workforce agent that consolidates feedback reports and submits a verdict, same as `review_engineer` consolidates test/security/a11y reports in engineering.

- Lives at `writers_room/workforce/creative_reviewer/`
- Has `review_dimensions` matching the writers room scoring dimensions: `concept_fidelity`, `originality`, `market_fit`, `structure`, `character`, `dialogue`, `craft`, `feasibility`
- System prompt: given feedback from multiple analysts, score each dimension, overall = minimum, call `submit_verdict`
- Fix routing logic (which creative agent fixes which feedback flag) moves from the leader into the creative_reviewer's report text — the base class `_propose_fix_task` handles routing back

### 10. Writers room leader — define `get_review_pairs()`

Map each creative agent to the `creative_reviewer`:

```python
def get_review_pairs(self):
    return [
        {
            "creator": "story_researcher",
            "creator_fix_command": "research",  # or whatever the fix command is
            "reviewer": "creative_reviewer",
            "reviewer_command": "review-creative",
            "dimensions": ["concept_fidelity", "originality", "market_fit", ...],
        },
        {
            "creator": "story_architect",
            "creator_fix_command": "write",
            "reviewer": "creative_reviewer",
            "reviewer_command": "review-creative",
            "dimensions": [...],
        },
        # same for character_designer, dialog_writer
    ]
```

### 11. Writers room leader — remove custom evaluation

Delete `_evaluate_feedback()` and `_evaluate_ideation_feedback()`. The leader no longer calls Claude for evaluation. Instead:

- When creative agents complete work → leader dispatches feedback agents (existing `_propose_feedback_tasks`)
- When feedback agents complete → leader dispatches `creative_reviewer` to consolidate
- When `creative_reviewer` completes → base class `_evaluate_review_and_loop` handles the verdict, quality gate, and fix routing
- Leader only calls Claude for planning (what stage to advance to, what tasks to propose)

### 12. Stage pipeline — keep as leader orchestration

The stage pipeline (ideation → concept → logline → ... → revised_draft) stays in the leader. This is task ordering/dependency logic, not evaluation. The leader advances stages based on review outcomes, which now come through the standard ping-pong.

The depth matrix (which feedback agents at which stage) also stays — the leader uses it when dispatching feedback tasks. This is planning, not evaluation.

### 13. Ideation merging

The ideation stage has a special step: merging multiple concept pitches into one winner. This is creative work, not review. It should be a task dispatched to a creative agent (e.g. `story_architect` with a "merge-concepts" command), not a Claude call in the leader.

## What does NOT change

- `call_claude` — unchanged, non-review tasks unaffected
- `stream_claude` — unchanged, not used for reviews
- Quality gate logic (`should_accept_review`, `_apply_quality_gate`) — unchanged, reads score from model fields
- `EXCELLENCE_THRESHOLD`, `MAX_REVIEW_ROUNDS`, etc. — unchanged
- Review pair definitions in engineering, marketing, sales, community — unchanged
- Writers room creative agents and feedback agents — unchanged (just wired differently)
- Writers room stage pipeline and depth matrix — unchanged (stays in leader as planning logic)

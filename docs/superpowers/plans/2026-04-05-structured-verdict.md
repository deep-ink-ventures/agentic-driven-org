# Structured Review Verdicts + Writers Room Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fragile regex-based verdict parsing with Claude tool_use across all departments, and align the writers room to the universal leader→creator→reviewer pattern.

**Architecture:** Add `call_claude_with_tools` to the Claude client. Define a `VERDICT_TOOL` in the base class. `WorkforceBlueprint.execute_task` injects it for reviewers (those with `review_dimensions`). Persist verdict on `AgentTask`. Refactor writers room to use `get_review_pairs()` and `_check_review_trigger()` like every other department.

**Tech Stack:** Django, Celery, Anthropic Python SDK (tool_use), pytest

---

### Task 1: `call_claude_with_tools` in Claude client

**Files:**
- Modify: `backend/agents/ai/claude_client.py:34-75`
- Test: `backend/agents/tests/test_claude_client.py`

- [ ] **Step 1: Write failing tests for `call_claude_with_tools`**

```python
# In backend/agents/tests/test_claude_client.py

class TestCallClaudeWithTools:
    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_returns_text_and_tool_input(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Detailed review report..."

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "submit_verdict"
        tool_block.input = {"verdict": "APPROVED", "score": 9.5}

        mock_message = MagicMock()
        mock_message.content = [text_block, tool_block]
        mock_message.usage.input_tokens = 100
        mock_message.usage.output_tokens = 50

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        tools = [{"name": "submit_verdict", "input_schema": {}}]
        text, tool_input, usage = call_claude_with_tools(
            system_prompt="sys",
            user_message="msg",
            tools=tools,
        )

        assert text == "Detailed review report..."
        assert tool_input == {"verdict": "APPROVED", "score": 9.5}
        assert usage["input_tokens"] == 100
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["tools"] == tools

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_returns_none_when_no_tool_call(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Just text, no tool call"

        mock_message = MagicMock()
        mock_message.content = [text_block]
        mock_message.usage.input_tokens = 50
        mock_message.usage.output_tokens = 30

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        text, tool_input, usage = call_claude_with_tools(
            system_prompt="sys",
            user_message="msg",
            tools=[],
        )

        assert text == "Just text, no tool call"
        assert tool_input is None

    @patch("agents.ai.claude_client._client", None)
    @patch("agents.ai.claude_client.anthropic")
    def test_extracts_first_tool_use_only(self, mock_anthropic):
        from agents.ai.claude_client import call_claude_with_tools

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Report"

        tool1 = MagicMock()
        tool1.type = "tool_use"
        tool1.name = "submit_verdict"
        tool1.input = {"verdict": "APPROVED", "score": 9.7}

        tool2 = MagicMock()
        tool2.type = "tool_use"
        tool2.name = "other_tool"
        tool2.input = {"foo": "bar"}

        mock_message = MagicMock()
        mock_message.content = [text_block, tool1, tool2]
        mock_message.usage.input_tokens = 50
        mock_message.usage.output_tokens = 30

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client

        text, tool_input, usage = call_claude_with_tools(
            system_prompt="sys",
            user_message="msg",
            tools=[],
        )

        assert tool_input == {"verdict": "APPROVED", "score": 9.7}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_claude_client.py::TestCallClaudeWithTools -v`
Expected: FAIL — `ImportError: cannot import name 'call_claude_with_tools'`

- [ ] **Step 3: Implement `call_claude_with_tools`**

Add to `backend/agents/ai/claude_client.py` after the `call_claude` function:

```python
def call_claude_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[dict],
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 8192,
) -> tuple[str, dict | None, dict]:
    """
    Call Claude API with tools and return (response_text, tool_input_or_None, usage_dict).

    Concatenates text blocks into the report. Extracts the first tool_use block's
    input as structured data. Returns None for tool_input if no tool was called.
    """
    client = _get_client()

    logger.info(
        "Calling Claude with tools: model=%s, system_len=%d, msg_len=%d, tools=%d",
        model, len(system_prompt), len(user_message), len(tools),
    )

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        tools=tools,
    )

    response_text = ""
    tool_input = None
    for block in message.content:
        if block.type == "text":
            response_text += block.text
        elif block.type == "tool_use" and tool_input is None:
            tool_input = block.input

    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    from agents.ai.pricing import estimate_cost

    cost = estimate_cost(model, input_tokens, output_tokens)

    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }

    logger.info(
        "Claude response (tools): model=%s input=%d output=%d cost=$%.4f tool_called=%s",
        model, input_tokens, output_tokens, cost, tool_input is not None,
    )

    return response_text, tool_input, usage
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_claude_client.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/ai/claude_client.py backend/agents/tests/test_claude_client.py
git commit -m "feat: add call_claude_with_tools for structured tool_use responses"
```

---

### Task 2: `VERDICT_TOOL` constant and `AgentTask` model fields

**Files:**
- Modify: `backend/agents/blueprints/base.py:1-32`
- Modify: `backend/agents/models/agent_task.py`
- Modify: `backend/agents/serializers/agent_task_serializer.py`
- Modify: `backend/agents/admin/agent_task_admin.py`
- Modify: `backend/agents/tasks.py` (broadcast payload)
- Create: migration file (auto-generated)
- Test: `backend/agents/tests/test_models.py`

- [ ] **Step 1: Add `VERDICT_TOOL` constant to `base.py`**

Add after the existing constants (after line 20, before `parse_review_verdict`):

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

- [ ] **Step 2: Add model fields to `AgentTask`**

Add after `token_usage` field in `backend/agents/models/agent_task.py`:

```python
review_verdict = models.CharField(
    max_length=20,
    blank=True,
    help_text="Structured verdict from reviewer: APPROVED or CHANGES_REQUESTED",
)
review_score = models.FloatField(
    null=True,
    blank=True,
    help_text="Review score 0.0-10.0 from structured verdict",
)
```

- [ ] **Step 3: Generate and run migration**

Run: `cd backend && ./venv/bin/python manage.py makemigrations agents -n add_review_verdict_fields && ./venv/bin/python manage.py migrate`

- [ ] **Step 4: Add fields to serializer**

In `backend/agents/serializers/agent_task_serializer.py`, add `"review_verdict"` and `"review_score"` to the `fields` list (after `"error_message"`).

- [ ] **Step 5: Add fields to admin**

In `backend/agents/admin/agent_task_admin.py`:
- Add `"review_verdict"`, `"review_score"` to `list_display` (after `"auto_execute"`)
- Add `"review_verdict"`, `"review_score"` to `readonly_fields`
- Add to the "Results" fieldset: `{"fields": ("report", "error_message", "review_verdict", "review_score")}`

- [ ] **Step 6: Add fields to WebSocket broadcast**

In `backend/agents/tasks.py`, in the `_broadcast_task` function's task dict (after `"token_usage"`), add:

```python
"review_verdict": task.review_verdict,
"review_score": task.review_score,
```

- [ ] **Step 7: Write test for model fields**

Add to `backend/agents/tests/test_models.py`:

```python
class TestAgentTaskReviewFields:
    def test_review_fields_default_empty(self, db, user):
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(department_type="marketing", project=project)
        agent = Agent.objects.create(name="Rev", agent_type="content_reviewer", department=dept, status="active")
        task = AgentTask.objects.create(agent=agent, exec_summary="Test review")
        assert task.review_verdict == ""
        assert task.review_score is None

    def test_review_fields_persist(self, db, user):
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(department_type="marketing", project=project)
        agent = Agent.objects.create(name="Rev", agent_type="content_reviewer", department=dept, status="active")
        task = AgentTask.objects.create(
            agent=agent, exec_summary="Test review",
            review_verdict="APPROVED", review_score=9.5,
        )
        task.refresh_from_db()
        assert task.review_verdict == "APPROVED"
        assert task.review_score == 9.5
```

- [ ] **Step 8: Run tests**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_models.py::TestAgentTaskReviewFields -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/models/agent_task.py backend/agents/serializers/agent_task_serializer.py backend/agents/admin/agent_task_admin.py backend/agents/tasks.py backend/agents/migrations/ backend/agents/tests/test_models.py
git commit -m "feat: add VERDICT_TOOL constant and review_verdict/review_score fields on AgentTask"
```

---

### Task 3: Wire verdict tool into `WorkforceBlueprint.execute_task`

**Files:**
- Modify: `backend/agents/blueprints/base.py:402-427` (`WorkforceBlueprint.execute_task`)
- Modify: `backend/agents/blueprints/base.py:624-652` (`_evaluate_review_and_loop`)
- Modify: `backend/agents/blueprints/base.py:23-32` (`parse_review_verdict` — add warning)
- Modify: `backend/agents/blueprints/base.py:534-548` (`_propose_review_chain` — remove VERDICT text from step_plan)
- Test: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Write failing test for verdict tool injection**

Add to `backend/agents/tests/test_blueprints.py`:

```python
from unittest.mock import patch, MagicMock
from agents.blueprints.base import VERDICT_TOOL, parse_review_verdict


class TestVerdictToolInjection:
    """WorkforceBlueprint.execute_task injects VERDICT_TOOL for reviewers."""

    @patch("agents.blueprints.base.call_claude_with_tools")
    def test_reviewer_gets_verdict_tool(self, mock_call, db, user):
        """Agents with review_dimensions use call_claude_with_tools."""
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(department_type="marketing", project=project)
        agent = Agent.objects.create(
            name="Reviewer", agent_type="content_reviewer",
            department=dept, status="active",
        )
        task = AgentTask.objects.create(agent=agent, exec_summary="Review content")

        mock_call.return_value = (
            "Detailed review report",
            {"verdict": "APPROVED", "score": 9.7},
            {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        from agents.blueprints.marketing.workforce.content_reviewer import ContentReviewerBlueprint
        bp = ContentReviewerBlueprint()
        report = bp.execute_task(agent, task)

        assert report == "Detailed review report"
        task.refresh_from_db()
        assert task.review_verdict == "APPROVED"
        assert task.review_score == 9.7
        # Verify VERDICT_TOOL was passed
        call_kwargs = mock_call.call_args
        assert call_kwargs.kwargs.get("tools") == [VERDICT_TOOL] or VERDICT_TOOL in call_kwargs[1].get("tools", call_kwargs.kwargs.get("tools", []))

    @patch("agents.blueprints.base.call_claude")
    def test_non_reviewer_uses_regular_call(self, mock_call, db, user):
        """Agents without review_dimensions use regular call_claude."""
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(department_type="marketing", project=project)
        agent = Agent.objects.create(
            name="Twitter", agent_type="twitter",
            department=dept, status="active",
        )
        task = AgentTask.objects.create(agent=agent, exec_summary="Post tweet")

        mock_call.return_value = (
            "Tweet posted",
            {"model": "claude-sonnet-4-6", "input_tokens": 50, "output_tokens": 30, "cost_usd": 0.005},
        )

        from agents.blueprints.marketing.workforce.twitter import TwitterBlueprint
        bp = TwitterBlueprint()
        report = bp.execute_task(agent, task)

        assert report == "Tweet posted"
        task.refresh_from_db()
        assert task.review_verdict == ""
        assert task.review_score is None

    @patch("agents.blueprints.base.call_claude_with_tools")
    def test_fallback_when_tool_not_called(self, mock_call, db, user):
        """Falls back to parse_review_verdict when Claude doesn't call the tool."""
        project = Project.objects.create(name="Test", goal="Test", owner=user)
        dept = Department.objects.create(department_type="marketing", project=project)
        agent = Agent.objects.create(
            name="Reviewer", agent_type="content_reviewer",
            department=dept, status="active",
        )
        task = AgentTask.objects.create(agent=agent, exec_summary="Review content")

        mock_call.return_value = (
            "Review report\nVERDICT: CHANGES_REQUESTED (score: 7.5/10)",
            None,  # No tool call
            {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
        )

        from agents.blueprints.marketing.workforce.content_reviewer import ContentReviewerBlueprint
        bp = ContentReviewerBlueprint()
        report = bp.execute_task(agent, task)

        task.refresh_from_db()
        assert task.review_verdict == "CHANGES_REQUESTED"
        assert task.review_score == 7.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_blueprints.py::TestVerdictToolInjection -v`
Expected: FAIL

- [ ] **Step 3: Implement verdict tool injection in `WorkforceBlueprint.execute_task`**

Replace the `execute_task` method in `WorkforceBlueprint` (`base.py:402-427`):

```python
def execute_task(self, agent: Agent, task: AgentTask) -> str:
    """Execute a task by calling Claude and returning the response.

    Reviewers (agents with review_dimensions) get the VERDICT_TOOL injected
    so Claude returns a structured verdict. All other agents use regular call_claude.
    """
    suffix = self.get_task_suffix(agent, task)
    task_msg = self.build_task_message(agent, task, suffix=suffix)
    model = self.get_model(agent, task.command_name)
    max_tokens = self.get_max_tokens(agent, task)

    if self.review_dimensions:
        from agents.ai.claude_client import call_claude_with_tools

        kwargs = {
            "system_prompt": self.build_system_prompt(agent),
            "user_message": task_msg,
            "tools": [VERDICT_TOOL],
            "model": model,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response, tool_input, usage = call_claude_with_tools(**kwargs)
        task.token_usage = usage

        if tool_input and "verdict" in tool_input and "score" in tool_input:
            task.review_verdict = tool_input["verdict"]
            task.review_score = tool_input["score"]
        else:
            # Fallback: parse from text
            logger.warning(
                "VERDICT_TOOL_FALLBACK agent=%s task=%s — Claude did not call submit_verdict, falling back to text parsing",
                agent.name, task.id,
            )
            verdict, score = parse_review_verdict(response)
            task.review_verdict = verdict
            task.review_score = score

        task.save(update_fields=["token_usage", "review_verdict", "review_score"])
        return response

    from agents.ai.claude_client import call_claude

    kwargs = {
        "system_prompt": self.build_system_prompt(agent),
        "user_message": task_msg,
        "model": model,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    response, usage = call_claude(**kwargs)
    task.token_usage = usage
    task.save(update_fields=["token_usage"])

    return response
```

- [ ] **Step 4: Update `_evaluate_review_and_loop` to read from model fields first**

In `base.py`, replace lines 632-633:

```python
# Before:
report = review_task.report or ""
verdict, score = parse_review_verdict(report)

# After:
if review_task.review_verdict and review_task.review_score is not None:
    verdict = review_task.review_verdict
    score = review_task.review_score
else:
    report = review_task.report or ""
    verdict, score = parse_review_verdict(report)
    logger.warning(
        "VERDICT_FROM_TEXT agent=%s task=%s — no structured verdict, parsed from report text",
        review_task.agent.name, review_task.id,
    )
```

- [ ] **Step 5: Add warning logging to `parse_review_verdict` fallback path**

In `parse_review_verdict` (base.py:23-32), add logging when regex fails:

```python
def parse_review_verdict(report: str) -> tuple[str, float]:
    """Parse a review report for VERDICT line. Returns (verdict, score)."""
    match = re.search(r"VERDICT:\s*(APPROVED|CHANGES_REQUESTED)\s*\(score:\s*([\d.]+)/10\)", report)
    if match:
        return match.group(1), float(match.group(2))
    # Fallback: keyword detection
    logger.warning("VERDICT_REGEX_MISS — falling back to keyword detection")
    lower = report.lower()
    if "approved" in lower and "changes_requested" not in lower:
        return "APPROVED", EXCELLENCE_THRESHOLD
    return "CHANGES_REQUESTED", 0.0
```

- [ ] **Step 6: Remove VERDICT text instructions from `_propose_review_chain` step_plan**

In `base.py:541-548`, replace the step_plan:

```python
"step_plan": (
    f"Review round {round_num}. Quality threshold: {EXCELLENCE_THRESHOLD}/10.\n\n"
    f"Content to review:\n{report_snippet}\n\n"
    f"Score each dimension 1.0-10.0 (use decimals): {dims_text}.\n"
    f"Overall score = MINIMUM of all dimensions.\n\n"
    f"After your review, call the submit_verdict tool with your verdict and score."
),
```

- [ ] **Step 7: Run tests**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_blueprints.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_blueprints.py
git commit -m "feat: inject VERDICT_TOOL in WorkforceBlueprint.execute_task for reviewers"
```

---

### Task 4: Update reviewer system prompts — all departments

**Files:**
- Modify: `backend/agents/blueprints/marketing/workforce/content_reviewer/agent.py`
- Modify: `backend/agents/blueprints/sales/workforce/outreach_reviewer/agent.py`
- Modify: `backend/agents/blueprints/community/workforce/partnership_reviewer/agent.py`
- Modify: `backend/agents/blueprints/community/workforce/ecosystem_analyst/agent.py`
- Modify: `backend/agents/blueprints/engineering/workforce/review_engineer/agent.py`
- Modify: `backend/agents/blueprints/engineering/leader/agent.py`
- Modify: command description strings in corresponding `commands/` directories

For each reviewer agent, the change is the same pattern:

1. Remove "End your report with exactly one of these lines: VERDICT: ..." from system prompt
2. Remove VERDICT format instructions from `get_task_suffix`
3. Add: "After your review, call the `submit_verdict` tool with your verdict and score."
4. Remove VERDICT format from command descriptions

- [ ] **Step 1: Update `content_reviewer/agent.py`**

In the `system_prompt` property, replace lines 71-73:
```
End your report with exactly one of these lines:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)
```
With:
```
After your review, call the submit_verdict tool with your verdict and score.
```

In `get_task_suffix`, replace the "Verdict Rules" section (lines 98-103):
```
## Verdict Rules
The overall score is the MINIMUM of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: VERDICT: APPROVED (score: N.N/10)
- Score < {EXCELLENCE_THRESHOLD}: VERDICT: CHANGES_REQUESTED (score: N.N/10) with actionable feedback

End your report with exactly one VERDICT line.
```
With:
```
## Verdict
The overall score is the MINIMUM of all dimension scores.
After your review, call the submit_verdict tool with your verdict and score.
For CHANGES_REQUESTED, include actionable feedback in your report.
```

- [ ] **Step 2: Update `outreach_reviewer/agent.py`**

Same pattern: replace VERDICT text instructions in system prompt and `get_task_suffix` with tool instructions.

- [ ] **Step 3: Update `partnership_reviewer/agent.py`**

Same pattern.

- [ ] **Step 4: Update `ecosystem_analyst/agent.py`**

Replace the custom JSON verdict format in system prompt. Currently asks for:
```json
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    ...
}
```

Remove `verdict` and `overall_score` from the JSON schema. Add `review_dimensions` to the class:

```python
review_dimensions = [
    "coverage_completeness",
    "strategic_prioritization",
    "partnership_potential_accuracy",
]
```

Replace verdict instructions with: "After your review, call the submit_verdict tool with your verdict and score."

Keep the rest of the JSON schema (`entity_reviews`, `missing_categories`, `summary_feedback`, `report`) in the system prompt — that's the review content, not the verdict.

Update `get_task_suffix` similarly — replace "APPROVED" / "REVISION_NEEDED" text with tool instructions.

- [ ] **Step 5: Update `review_engineer/agent.py`**

Replace VERDICT text instructions in the system prompt (lines 125-127):
```
End your consolidated report with exactly one of:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)
```
With:
```
After your consolidated review, call the submit_verdict tool with your verdict and score.
```

- [ ] **Step 6: Update `engineering/leader/agent.py` step_plan text**

In `_propose_review_chain` (around line 422-430), replace the VERDICT instructions in the `step_plan` string:
```
## Verdict (REQUIRED)
- If overall score >= {EXCELLENCE_THRESHOLD}: **APPROVED** (score: N/10)
...
End your report with exactly one of these lines:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)
```
With:
```
## Verdict
After your review, call the submit_verdict tool with your verdict and score.
```

- [ ] **Step 7: Update command description strings**

In each reviewer's `commands/` directory, update the `description` parameter in the `@command` decorator to remove "Return VERDICT: APPROVED or CHANGES_REQUESTED" and replace with "Submit verdict via tool call."

Files:
- `marketing/workforce/content_reviewer/commands/review_content.py`
- `sales/workforce/outreach_reviewer/commands/review_outreach.py`
- `community/workforce/partnership_reviewer/commands/review_proposal.py`
- `community/workforce/ecosystem_analyst/commands/review_ecosystem.py`

- [ ] **Step 8: Run full test suite to verify no regressions**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add backend/agents/blueprints/
git commit -m "feat: replace VERDICT text instructions with submit_verdict tool across all reviewers"
```

---

### Task 5: Create `creative_reviewer` workforce agent for writers room

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`
- Create: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/commands/review_creative.py`
- Modify: `backend/agents/blueprints/__init__.py` (register in DEPARTMENTS)

- [ ] **Step 1: Create the `review_creative` command**

Create `backend/agents/blueprints/writers_room/workforce/creative_reviewer/commands/__init__.py`:

```python
from agents.blueprints.writers_room.workforce.creative_reviewer.commands.review_creative import review_creative

__all__ = ["review_creative"]
```

Create `backend/agents/blueprints/writers_room/workforce/creative_reviewer/commands/review_creative.py`:

```python
"""Creative reviewer command: consolidate feedback and score creative output."""

from agents.blueprints.base import command


@command(
    name="review-creative",
    description=(
        "Consolidate feedback from all analysts for a creative stage. "
        "Score each dimension 1-10, overall = minimum. "
        "Submit verdict via tool call."
    ),
    model="claude-sonnet-4-6",
)
def review_creative(self, agent) -> dict:
    return {
        "exec_summary": "Consolidate analyst feedback and score creative output",
        "step_plan": (
            "1. Read all analyst feedback reports for the current stage\n"
            "2. Score each dimension (concept fidelity, originality, market fit, structure, character, dialogue, craft, feasibility)\n"
            "3. Overall score = minimum of all scored dimensions\n"
            "4. Call submit_verdict tool with verdict and score\n"
            "5. For CHANGES_REQUESTED: include specific fix instructions grouped by which creative agent should address them"
        ),
    }
```

- [ ] **Step 2: Create the `creative_reviewer` blueprint**

Create `backend/agents/blueprints/writers_room/workforce/creative_reviewer/__init__.py`:

```python
from agents.blueprints.writers_room.workforce.creative_reviewer.agent import CreativeReviewerBlueprint

__all__ = ["CreativeReviewerBlueprint"]
```

Create `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`:

```python
"""Creative Reviewer — consolidates analyst feedback, scores quality, submits verdict.

Mirrors review_engineer in engineering: multiple specialist analysts feed into
one consolidator that produces a single structured verdict.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.writers_room.workforce.creative_reviewer.commands import review_creative

logger = logging.getLogger(__name__)


class CreativeReviewerBlueprint(WorkforceBlueprint):
    name = "Creative Reviewer"
    slug = "creative_reviewer"
    description = "Consolidates analyst feedback and scores creative output quality — the quality gate for the writers room"
    tags = ["review", "quality", "creative", "feedback"]
    review_dimensions = [
        "concept_fidelity",
        "originality",
        "market_fit",
        "structure",
        "character",
        "dialogue",
        "craft",
        "feasibility",
    ]
    skills = [
        {
            "name": "Feedback Consolidation",
            "description": "Synthesize reports from multiple specialist analysts into a single quality assessment",
        },
        {
            "name": "Fix Routing",
            "description": "Map specific issues to the creative agent best equipped to fix them",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are the Creative Reviewer for the Writers Room. Your job is to consolidate feedback from all analyst agents and produce a single quality verdict.

You receive reports from specialist analysts: market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst. Each flags issues by severity (critical/major/minor/strength).

REVIEW DIMENSIONS (score each 1.0-10.0, use decimals):

1. **Concept Fidelity** — Does the output honor the creator's original pitch? Are specific characters, conflicts, arcs preserved and developed (not replaced with generic alternatives)?
2. **Originality** — Is this genuinely original? Apply the Setting Swap Test: if you change the setting back to a referenced show's setting, is the story the same? If yes, score 1-3.
3. **Market Fit** — Commercial viability, positioning, audience appeal
4. **Structure** — Story architecture, beats, pacing, act breaks
5. **Character** — Consistency, arcs, motivation, relationships, voice
6. **Dialogue** — Voice, subtext, scene construction, exposition balance
7. **Craft** — Format conventions, technical quality, polish
8. **Feasibility** — Budget, cast-ability, production practicality

Only score dimensions that were analyzed by feedback agents this round.
Always score concept_fidelity and originality — they apply at every stage.

SCORING:
- Overall score = MINIMUM of all dimension scores
- The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold

After your review, call the submit_verdict tool with your verdict and score.

FIX ROUTING (for CHANGES_REQUESTED):
Group issues by which creative agent should fix them:
- market_analyst flags → story_researcher
- structure_analyst flags → story_architect
- character_analyst flags → character_designer
- dialogue_analyst flags → dialog_writer
- format_analyst flags → story_architect (structural) or dialog_writer (craft)
- production_analyst flags → most relevant creative agent
- concept_fidelity / originality flags → story_architect AND character_designer

Include specific fix instructions in your report so the review loop knows what to route."""

    review_creative = review_creative

    def get_task_suffix(self, agent, task):
        return f"""# REVIEW METHODOLOGY

Read all analyst feedback reports from the department's recent completed tasks.
Consolidate findings, score each dimension, and submit your verdict.

## Verdict
The overall score is the MINIMUM of all dimension scores.
After your review, call the submit_verdict tool with your verdict and score.
For CHANGES_REQUESTED, include specific fix instructions grouped by creative agent."""

    def get_max_tokens(self, agent, task):
        return 12000
```

- [ ] **Step 3: Register in `__init__.py`**

In `backend/agents/blueprints/__init__.py`, add `"creative_reviewer"` to `_writers_room_imports`:

```python
"creative_reviewer": ("agents.blueprints.writers_room.workforce.creative_reviewer", "CreativeReviewerBlueprint"),
```

- [ ] **Step 4: Run import check**

Run: `cd backend && ./venv/bin/python -c "from agents.blueprints.writers_room.workforce.creative_reviewer import CreativeReviewerBlueprint; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/creative_reviewer/ backend/agents/blueprints/__init__.py
git commit -m "feat: add creative_reviewer workforce agent for writers room"
```

---

### Task 6: Refactor writers room leader to use universal review pattern

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_blueprints.py`

This is the big task. The writers room leader needs to:
1. Define `get_review_pairs()`
2. Replace `_evaluate_feedback()` with `_check_review_trigger()` in the state machine
3. Delete `_evaluate_feedback()` and `_evaluate_ideation_feedback()`
4. Move ideation merging to a creative agent task

- [ ] **Step 1: Write failing test**

Add to `backend/agents/tests/test_blueprints.py`:

```python
class TestWritersRoomReviewPairs:
    def test_get_review_pairs_defined(self):
        from agents.blueprints.writers_room.leader import WritersRoomLeaderBlueprint
        bp = WritersRoomLeaderBlueprint()
        pairs = bp.get_review_pairs()
        assert len(pairs) > 0

        # All creative agents map to creative_reviewer
        reviewer_types = {p["reviewer"] for p in pairs}
        assert reviewer_types == {"creative_reviewer"}

        # All creative agents from CREATIVE_MATRIX are covered
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX
        all_creators = set()
        for agents in CREATIVE_MATRIX.values():
            all_creators.update(agents)
        pair_creators = {p["creator"] for p in pairs}
        assert all_creators == pair_creators

    def test_generate_task_proposal_uses_check_review_trigger(self, db, user):
        """After feedback completes, leader dispatches creative_reviewer via _check_review_trigger."""
        from agents.blueprints.writers_room.leader import WritersRoomLeaderBlueprint

        project = Project.objects.create(name="Test", goal="Write a screenplay", owner=user)
        dept = Department.objects.create(department_type="writers_room", project=project)
        leader = Agent.objects.create(
            name="Writers Room Leader", agent_type="leader",
            department=dept, is_leader=True, status="active",
            internal_state={
                "current_stage": "ideation",
                "stage_status": {"ideation": {"status": "feedback_done", "iterations": 0}},
            },
        )
        # Create creative_reviewer agent
        reviewer = Agent.objects.create(
            name="Creative Reviewer", agent_type="creative_reviewer",
            department=dept, status="active",
        )
        # Create a completed feedback task (market_analyst)
        analyst = Agent.objects.create(
            name="Market Analyst", agent_type="market_analyst",
            department=dept, status="active",
        )
        feedback_task = AgentTask.objects.create(
            agent=analyst, status=AgentTask.Status.DONE,
            exec_summary="Analyze ideation", report="Analysis report...",
        )

        bp = WritersRoomLeaderBlueprint()
        proposal = bp.generate_task_proposal(leader)

        # Should propose a creative_reviewer task
        assert proposal is not None
        tasks = proposal.get("tasks", [])
        reviewer_tasks = [t for t in tasks if t.get("target_agent_type") == "creative_reviewer"]
        assert len(reviewer_tasks) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_blueprints.py::TestWritersRoomReviewPairs -v`
Expected: FAIL

- [ ] **Step 3: Add `get_review_pairs()` to writers room leader**

In `backend/agents/blueprints/writers_room/leader/agent.py`, add the method to `WritersRoomLeaderBlueprint`:

```python
def get_review_pairs(self):
    # All creative agents route to the creative_reviewer
    all_creators = set()
    for agents in CREATIVE_MATRIX.values():
        all_creators.update(agents)

    # Map each creator to their fix command (from their blueprint's commands)
    fix_commands = {
        "story_researcher": "research",
        "story_architect": "write",
        "character_designer": "write",
        "dialog_writer": "write",
    }

    return [
        {
            "creator": creator,
            "creator_fix_command": fix_commands.get(creator, "write"),
            "reviewer": "creative_reviewer",
            "reviewer_command": "review-creative",
            "dimensions": [
                "concept_fidelity", "originality", "market_fit", "structure",
                "character", "dialogue", "craft", "feasibility",
            ],
        }
        for creator in sorted(all_creators)
    ]
```

- [ ] **Step 4: Refactor `generate_task_proposal` state machine**

The state machine currently has these transitions for feedback:

```
feedback_in_progress → feedback_done → _evaluate_feedback() → fix_in_progress / passed
```

Change to:

```
feedback_in_progress → feedback_done → _propose_consolidation_task() → review_in_progress
review_in_progress → (creative_reviewer completes) → _check_review_trigger() handles it
```

Replace the `feedback_done` and `feedback_in_progress` handlers in `generate_task_proposal`:

For `feedback_in_progress`: when no active tasks remain, set status to `feedback_done` and propose a `creative_reviewer` task.

For `feedback_done`: propose a `creative_reviewer` task (consolidation).

Add new status `review_in_progress`: when `creative_reviewer` completes, `_check_review_trigger()` handles the verdict automatically. If accepted → advance stage. If rejected → base class routes fix back to creator.

The key change: remove the `_evaluate_feedback` and `_evaluate_ideation_feedback` calls from the state machine. Replace with dispatching the `creative_reviewer` agent. The base class ping-pong takes over from there.

Replace the state machine section (approximately lines 297-344):

```python
# ── State machine ───────────────────────────────────────────────

# Check for review cycle triggers first (universal from base class)
review_result = self._check_review_trigger(agent)
if review_result:
    return review_result

if status == "not_started":
    return self._propose_creative_tasks(agent, current_stage, config)

if status == "writing_in_progress":
    logger.info("Writers Room: stage '%s' writing complete — advancing to feedback", current_stage)
    stage_status[current_stage]["status"] = "writing_done"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return self._propose_feedback_tasks(agent, current_stage, config)

if status == "writing_done":
    return self._propose_feedback_tasks(agent, current_stage, config)

if status == "feedback_in_progress":
    logger.info("Writers Room: stage '%s' feedback complete — dispatching creative reviewer", current_stage)
    stage_status[current_stage]["status"] = "feedback_done"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return self._propose_review_task(agent, current_stage, config)

if status == "feedback_done":
    return self._propose_review_task(agent, current_stage, config)

if status == "review_in_progress":
    # creative_reviewer completed — _check_review_trigger() above handles it
    # If we got here, the review was accepted → advance stage
    current_info["status"] = "passed"
    stage_status[current_stage] = current_info
    internal_state["stage_status"] = stage_status

    target_stage = config.get("target_stage", "revised_draft")
    next_stg = _next_stage(current_stage)
    if next_stg and STAGES.index(current_stage) < STAGES.index(target_stage):
        internal_state["current_stage"] = next_stg
        internal_state["current_iteration"] = 0
        logger.info("Writers Room: stage '%s' PASSED — advancing to '%s'", current_stage, next_stg)
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
        return self._propose_creative_tasks(agent, next_stg, config)

    logger.info("Writers Room: target stage '%s' PASSED — project complete", current_stage)
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return None

if status == "fix_in_progress":
    stage_status[current_stage]["status"] = "writing_done"
    stage_status[current_stage]["iterations"] = iteration + 1
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return self._propose_feedback_tasks(agent, current_stage, config)
```

- [ ] **Step 5: Add `_propose_review_task` method**

```python
def _propose_review_task(self, agent: Agent, stage: str, config: dict) -> dict:
    """Dispatch the creative_reviewer to consolidate analyst feedback."""
    locale = config.get("locale", "en")

    # Gather recent feedback reports for context
    from agents.models import AgentTask
    feedback_agent_types = [at for at, _ in FEEDBACK_MATRIX.get(stage, [])]
    recent_feedback = list(
        AgentTask.objects.filter(
            agent__department=agent.department,
            agent__agent_type__in=feedback_agent_types,
            status=AgentTask.Status.DONE,
        )
        .order_by("-completed_at")[: len(feedback_agent_types) * 2]
        .values_list("agent__agent_type", "report")
    )

    feedback_text = ""
    for agent_type, report in recent_feedback:
        if report:
            feedback_text += f"\n\n## {agent_type}\n{report[:3000]}"

    internal_state = agent.internal_state or {}
    stage_status = internal_state.get("stage_status", {})
    current_info = stage_status.get(stage, {"iterations": 0})
    current_info["status"] = "review_in_progress"
    stage_status[stage] = current_info
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    return {
        "exec_summary": f"Stage '{stage}': consolidate analyst feedback and score",
        "tasks": [
            {
                "target_agent_type": "creative_reviewer",
                "command_name": "review-creative",
                "exec_summary": f"Review stage '{stage}' — consolidate analyst feedback",
                "step_plan": (
                    f"Stage: {stage}\n"
                    f"Locale: {locale}\n"
                    f"Quality threshold: {EXCELLENCE_THRESHOLD}/10\n\n"
                    f"## Analyst Feedback Reports\n{feedback_text}\n\n"
                    f"Score each dimension 1.0-10.0. Overall score = minimum of all dimensions.\n"
                    f"After your review, call the submit_verdict tool with your verdict and score.\n\n"
                    f"For CHANGES_REQUESTED: group fix instructions by creative agent."
                ),
                "depends_on_previous": False,
            }
        ],
    }
```

- [ ] **Step 6: Delete `_evaluate_feedback` and `_evaluate_ideation_feedback`**

Remove the `_evaluate_feedback` method (approximately lines 609-836) and `_evaluate_ideation_feedback` method (approximately lines 838-927).

For ideation merging (previously in `_evaluate_ideation_feedback`): the creative_reviewer now handles ideation the same as any other stage. Concept merging becomes a separate creative task dispatched after the ideation stage passes review. Add to the stage advancement logic: when ideation passes, dispatch a `story_architect` task with command "write" and a step_plan that says "Merge the best elements from the approved concept pitches into a single unified concept."

- [ ] **Step 7: Remove the VERDICT text instructions from the leader system prompt**

Find and remove any VERDICT format instructions in the writers room leader's system prompt and any remaining evaluation-related prompt text.

- [ ] **Step 8: Override `_propose_fix_task` for writers-room-specific fix routing**

The base class `_propose_fix_task` routes fixes back to a single creator. The writers room needs to route different flags to different creative agents (per `FLAG_ROUTING`). Override `_propose_fix_task`:

```python
def _propose_fix_task(
    self, agent: Agent, review_task: AgentTask, score: float, round_num: int, polish_count: int
) -> dict | None:
    """Route fix tasks to specific creative agents based on flag routing."""
    from agents.ai.claude_client import parse_json_response

    # Try to extract fix routing from the review report
    report = review_task.report or ""

    # The creative_reviewer includes fix instructions grouped by agent in its report.
    # Route fixes to the creative agents mentioned.
    # Fallback: send to story_architect as the default creative agent.
    config = _get_merged_config(agent)
    locale = config.get("locale", "en")
    internal_state = agent.internal_state or {}
    current_stage = internal_state.get("current_stage", STAGES[0])

    stage_status = internal_state.get("stage_status", {})
    current_info = stage_status.get(current_stage, {"iterations": 0})
    current_info["status"] = "fix_in_progress"
    stage_status[current_stage] = current_info
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    review_snippet = report[:3000]
    polish_msg = f" (polish {polish_count}/{MAX_POLISH_ATTEMPTS})" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

    # Route to story_architect as primary fix agent (handles most structural issues)
    return {
        "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}",
        "tasks": [
            {
                "target_agent_type": "story_architect",
                "command_name": "write",
                "exec_summary": f"Fix review issues for stage '{current_stage}' (score {score}/10)",
                "step_plan": (
                    f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                    f"Review round: {round_num}. Locale: {locale}\n\n"
                    f"The creative reviewer has requested changes. Fix the issues below.\n\n"
                    f"## Review Report\n{review_snippet}\n\n"
                    f"Address every CHANGES_REQUESTED item. Focus on the weakest dimensions first."
                ),
                "depends_on_previous": False,
            }
        ],
    }
```

- [ ] **Step 9: Run tests**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_blueprints.py::TestWritersRoomReviewPairs -v`
Expected: All PASS

- [ ] **Step 10: Run full test suite**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/ -v`
Expected: All PASS (some writers room tests may need updates — see Task 7)

- [ ] **Step 11: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_blueprints.py
git commit -m "feat: refactor writers room to use universal review ping-pong pattern"
```

---

### Task 7: Fix writers room tests

**Files:**
- Modify: `backend/agents/tests/test_writers_room_ideation.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

The writers room refactor may break existing tests that mock `_evaluate_feedback` or test the old state machine transitions. Update them to reflect the new flow:

- `feedback_done` → dispatches `creative_reviewer` (not `_evaluate_feedback`)
- `review_in_progress` → new state
- No more direct Claude calls for evaluation in the leader

- [ ] **Step 1: Read existing writers room tests**

Read both test files to identify what needs updating.

- [ ] **Step 2: Update tests to match new state machine**

Replace any mocks of `_evaluate_feedback` or `_evaluate_ideation_feedback` with the new flow:
- `feedback_done` → `_propose_review_task` dispatches creative_reviewer
- `review_in_progress` → `_check_review_trigger` reads verdict from completed creative_reviewer task

- [ ] **Step 3: Run tests**

Run: `cd backend && ./venv/bin/python -m pytest agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_skills_commands.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/agents/tests/
git commit -m "test: update writers room tests for universal review pattern"
```

---

### Task 8: Full regression test + cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run full test suite**

Run: `cd backend && ./venv/bin/python -m pytest --tb=short -q`
Expected: All PASS

- [ ] **Step 2: Run migration check**

Run: `cd backend && ./venv/bin/python manage.py makemigrations --check --dry-run`
Expected: No new migrations needed

- [ ] **Step 3: Verify imports**

Run: `cd backend && ./venv/bin/python -c "from agents.blueprints import DEPARTMENTS; wr = DEPARTMENTS['writers_room']; print('creative_reviewer' in wr['workforce']); print(wr['leader'].get_review_pairs())"`
Expected: `True` followed by the review pairs list

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: final cleanup after structured verdict + writers room alignment"
```

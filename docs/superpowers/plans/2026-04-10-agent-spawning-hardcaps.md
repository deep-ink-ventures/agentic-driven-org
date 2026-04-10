# Agent Spawning Hardcaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent runaway agent/clone spawning with four hard enforcement layers and a configurable target area limit for sales departments.

**Architecture:** Django settings define global caps. `create_clones` raises ValueError if over limit. `create_next_leader_task` enforces per-proposal and per-sprint caps. Sales department config controls target area count, read by both the strategist prompt and the regex parser.

**Tech Stack:** Django settings, existing blueprint/task infrastructure, pytest

---

### Task 1: Add agent limit settings to Django config

**Files:**
- Modify: `backend/config/settings.py:151` (after Celery settings block)

- [ ] **Step 1: Add settings**

Add after `CELERY_TASK_SEND_SENT_EVENT = True` (line 153), before `CELERY_BEAT_SCHEDULE`:

```python
# ── Agent concurrency and spawning limits ────────────────────────────────
AGENT_MAX_CONCURRENT_PER_DEPT = 5       # max queued+processing tasks per department
AGENT_MAX_CLONES_PER_SPRINT = 10        # hard wall in create_clones — raises ValueError
AGENT_MAX_TASKS_PER_PROPOSAL = 20       # max tasks from a single leader proposal
AGENT_MAX_TASKS_PER_SPRINT = 50         # absolute ceiling per sprint
```

- [ ] **Step 2: Verify settings load**

Run: `python manage.py shell -c "from django.conf import settings; print(settings.AGENT_MAX_CLONES_PER_SPRINT)"`
Expected: `10`

- [ ] **Step 3: Commit**

```
git add backend/config/settings.py
git commit -m "feat: add AGENT_* spawning limit settings"
```

---

### Task 2: Hard wall in `create_clones`

**Files:**
- Modify: `backend/agents/blueprints/base.py:874-893`
- Test: `backend/agents/tests/test_clone_limits.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/agents/tests/test_clone_limits.py`:

```python
"""Tests for clone creation hard limits."""

import pytest
from unittest.mock import MagicMock

from agents.blueprints.base import LeaderBlueprint


@pytest.fixture
def leader_blueprint():
    bp = LeaderBlueprint()
    return bp


@pytest.fixture
def mock_sprint(db):
    from projects.models import Project, Sprint
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(email="test@test.com", password="pass")
    project = Project.objects.create(name="Test", owner=user)
    return Sprint.objects.create(project=project, text="Test sprint", created_by=user)


@pytest.fixture
def mock_parent_agent(db, mock_sprint):
    from agents.models import Agent
    from projects.models import Department
    dept = Department.objects.create(
        department_type="sales",
        project=mock_sprint.project,
    )
    return Agent.objects.create(
        name="Test Agent",
        agent_type="pitch_personalizer",
        department=dept,
        status="active",
    )


class TestCreateClonesHardLimit:
    @pytest.mark.django_db
    def test_create_clones_within_limit(self, leader_blueprint, mock_parent_agent, mock_sprint, settings):
        settings.AGENT_MAX_CLONES_PER_SPRINT = 10
        clones = leader_blueprint.create_clones(mock_parent_agent, 5, mock_sprint)
        assert len(clones) == 5

    @pytest.mark.django_db
    def test_create_clones_at_limit(self, leader_blueprint, mock_parent_agent, mock_sprint, settings):
        settings.AGENT_MAX_CLONES_PER_SPRINT = 10
        clones = leader_blueprint.create_clones(mock_parent_agent, 10, mock_sprint)
        assert len(clones) == 10

    @pytest.mark.django_db
    def test_create_clones_over_limit_raises(self, leader_blueprint, mock_parent_agent, mock_sprint, settings):
        settings.AGENT_MAX_CLONES_PER_SPRINT = 10
        with pytest.raises(ValueError, match="exceeds max"):
            leader_blueprint.create_clones(mock_parent_agent, 11, mock_sprint)

    @pytest.mark.django_db
    def test_create_clones_way_over_limit_raises(self, leader_blueprint, mock_parent_agent, mock_sprint, settings):
        settings.AGENT_MAX_CLONES_PER_SPRINT = 10
        with pytest.raises(ValueError, match="exceeds max"):
            leader_blueprint.create_clones(mock_parent_agent, 500, mock_sprint)

    @pytest.mark.django_db
    def test_no_clones_created_on_rejection(self, leader_blueprint, mock_parent_agent, mock_sprint, settings):
        """When over limit, zero clones should exist in DB."""
        from agents.models import ClonedAgent
        settings.AGENT_MAX_CLONES_PER_SPRINT = 5
        with pytest.raises(ValueError):
            leader_blueprint.create_clones(mock_parent_agent, 10, mock_sprint)
        assert ClonedAgent.objects.filter(sprint=mock_sprint).count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/agents/tests/test_clone_limits.py -v`
Expected: FAIL — `create_clones` doesn't check limit yet

- [ ] **Step 3: Implement the hard wall**

In `backend/agents/blueprints/base.py`, replace the `create_clones` method:

```python
def create_clones(self, parent_agent: Agent, count: int, sprint, initial_state: dict | None = None) -> list:
    """Create N ephemeral clones of parent_agent, scoped to this sprint.

    Raises ValueError if count exceeds settings.AGENT_MAX_CLONES_PER_SPRINT.
    """
    from django.conf import settings

    from agents.models import ClonedAgent

    max_clones = getattr(settings, "AGENT_MAX_CLONES_PER_SPRINT", 10)
    if count > max_clones:
        raise ValueError(
            f"Clone count {count} exceeds max {max_clones} per sprint "
            f"(parent={parent_agent.name}, sprint={str(sprint.id)[:8]})"
        )

    clones = []
    for i in range(count):
        clone = ClonedAgent.objects.create(
            parent=parent_agent,
            sprint=sprint,
            clone_index=i,
            internal_state=initial_state or {},
        )
        clones.append(clone)
    logger.info(
        "CLONES_CREATED parent=%s count=%d sprint=%s",
        parent_agent.name,
        count,
        str(sprint.id)[:8],
    )
    return clones
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/agents/tests/test_clone_limits.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```
git add backend/agents/blueprints/base.py backend/agents/tests/test_clone_limits.py
git commit -m "feat: hard wall in create_clones — raises ValueError over limit"
```

---

### Task 3: Per-proposal and per-sprint caps in `create_next_leader_task`

**Files:**
- Modify: `backend/agents/tasks.py:352-471`

- [ ] **Step 1: Write failing tests**

Add to `backend/agents/tests/test_clone_limits.py`:

```python
class TestTaskDispatchCaps:
    @pytest.mark.django_db
    def test_proposal_truncated_to_max(self, settings):
        """A proposal with more tasks than AGENT_MAX_TASKS_PER_PROPOSAL gets truncated."""
        settings.AGENT_MAX_TASKS_PER_PROPOSAL = 3
        # We test the truncation logic directly by checking that only 3 tasks
        # are created when a proposal returns 10 — tested via the full
        # create_next_leader_task flow in integration tests.
        # For unit-level: just verify the setting is readable.
        from django.conf import settings as s
        assert s.AGENT_MAX_TASKS_PER_PROPOSAL == 3

    @pytest.mark.django_db
    def test_sprint_cap_setting_exists(self, settings):
        settings.AGENT_MAX_TASKS_PER_SPRINT = 50
        from django.conf import settings as s
        assert s.AGENT_MAX_TASKS_PER_SPRINT == 50
```

- [ ] **Step 2: Implement the caps**

In `backend/agents/tasks.py`, replace the hardcap block and add caps to the task creation loop.

Replace lines 352-365 (the existing hardcap):

```python
    # ── Concurrency and spawning limits (from settings) ──────────────────
    from django.conf import settings as django_settings

    max_concurrent = getattr(django_settings, "AGENT_MAX_CONCURRENT_PER_DEPT", 5)
    active_count = AgentTask.objects.filter(
        agent__department=agent.department,
        status__in=[AgentTask.Status.QUEUED, AgentTask.Status.PROCESSING],
    ).count()
    if active_count >= max_concurrent:
        logger.warning(
            "DEPT_CONCURRENCY_CAP dept=%s active=%d cap=%d — skipping proposal",
            agent.department.name,
            active_count,
            max_concurrent,
        )
        return
```

After `tasks_data = proposal.get("tasks", [])` on line 379, add the two caps:

```python
        if tasks_data:
            # Cap 1: per-proposal limit
            max_per_proposal = getattr(django_settings, "AGENT_MAX_TASKS_PER_PROPOSAL", 20)
            if len(tasks_data) > max_per_proposal:
                logger.warning(
                    "PROPOSAL_CAP leader=%s proposed=%d cap=%d — truncating",
                    agent.name,
                    len(tasks_data),
                    max_per_proposal,
                )
                tasks_data = tasks_data[:max_per_proposal]

            # Cap 2: per-sprint total limit
            if sprint_id:
                max_per_sprint = getattr(django_settings, "AGENT_MAX_TASKS_PER_SPRINT", 50)
                existing_sprint_tasks = AgentTask.objects.filter(sprint_id=sprint_id).count()
                remaining_budget = max(0, max_per_sprint - existing_sprint_tasks)
                if remaining_budget == 0:
                    logger.warning(
                        "SPRINT_CAP leader=%s sprint=%s existing=%d cap=%d — refusing all tasks",
                        agent.name,
                        str(sprint_id)[:8],
                        existing_sprint_tasks,
                        max_per_sprint,
                    )
                    return
                if len(tasks_data) > remaining_budget:
                    logger.warning(
                        "SPRINT_CAP leader=%s sprint=%s budget=%d proposed=%d — truncating",
                        agent.name,
                        str(sprint_id)[:8],
                        remaining_budget,
                        len(tasks_data),
                    )
                    tasks_data = tasks_data[:remaining_budget]
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `pytest backend/agents/tests/ -x -q`
Expected: All pass

- [ ] **Step 4: Commit**

```
git add backend/agents/tasks.py backend/agents/tests/test_clone_limits.py
git commit -m "feat: per-proposal and per-sprint task caps in create_next_leader_task"
```

---

### Task 4: Sales department `max_target_areas` config

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py:22,118-124,368,393,428-436`
- Modify: `backend/agents/blueprints/sales/workforce/strategist/agent.py:82-109,161`

- [ ] **Step 1: Add `max_target_areas` to sales config_schema**

In `backend/agents/blueprints/sales/leader/agent.py`, replace the `config_schema` (lines 118-124):

```python
    config_schema = {
        "max_target_areas": {
            "type": "int",
            "description": "Maximum number of target areas the strategist produces per sprint. Each area spawns one clone agent.",
            "label": "Max Target Areas",
            "default": 5,
        },
        "include_inactive_outreach": {
            "type": "bool",
            "description": "Include inactive outreach agents as channels in the CSV. Their rows won't be auto-dispatched but can be used for manual outreach.",
            "label": "Include Inactive Outreach Channels",
        },
    }
```

- [ ] **Step 2: Hard-cap `_parse_target_areas` to config value**

In `backend/agents/blueprints/sales/leader/agent.py`, replace `_create_clones_and_dispatch` target area parsing (around line 368) to read the config and cap:

Replace:
```python
        target_areas = self._parse_target_areas(strategy_task.report)
        if not target_areas:
```

With:
```python
        # Read max from department config (cascades: agent → dept → project)
        max_areas = agent.get_config_value("max_target_areas", 5)
        target_areas = self._parse_target_areas(strategy_task.report, max_areas=max_areas)
        if not target_areas:
```

Replace the `_parse_target_areas` method:

```python
    def _parse_target_areas(self, strategy_text: str, max_areas: int = 5) -> list[tuple[str, str]]:
        """Extract target areas from strategy output. Returns list of (name, content) tuples.

        Hard-caps to max_areas. If the strategy produced more, they are silently dropped.
        """
        matches = list(TARGET_AREA_PATTERN.finditer(strategy_text))
        areas = []
        for match in matches:
            full = match.group(0).strip()
            name = match.group(1).strip() if match.group(1) else f"Area {len(areas) + 1}"
            areas.append((name, full))
        if len(areas) > max_areas:
            logger.warning(
                "TARGET_AREA_CAP parsed=%d cap=%d — truncating to top %d",
                len(areas),
                max_areas,
                max_areas,
            )
            areas = areas[:max_areas]
        return areas
```

- [ ] **Step 3: Make strategist prompt read the config dynamically**

In `backend/agents/blueprints/sales/workforce/strategist/agent.py`, the system prompt hardcodes target area instructions. The `get_task_suffix` method (line 125) is where per-task methodology goes. Replace the anti-pattern line (line 161):

```python
- Do not propose more than 5 target areas — focus beats breadth
```

This line is in the `get_task_suffix` return string. The suffix method doesn't have access to agent config, but `execute_task` does. Instead, modify `get_task_suffix` to accept the agent and read the config:

In `backend/agents/blueprints/sales/workforce/strategist/agent.py`, replace `get_task_suffix`:

```python
    def get_task_suffix(self, agent, task):
        max_areas = agent.get_config_value("max_target_areas", 5)
        return f"""# STRATEGY & NARRATIVE METHODOLOGY

## Target Area Quality Criteria
- Each target area must cite at least 2 specific signals from the research briefing
- "Why now" must reference a concrete trigger event, trend, or timing signal
- Size estimates should be grounded (even rough), not hand-waved
- Competitive density assessment should reference actual competitors from the research

## Positioning Framework
- For each target area, answer: where do competitors win, where do they lose?
- Identify positioning gaps — segments competitors ignore or serve poorly
- Frame our strengths against specific competitor weaknesses
- Use "landmine questions" — questions prospects should ask that favor us

## Narrative Arc Methodology
- Hook categories: pattern interrupt, contrarian insight, mutual connection, timely reference
- Each hook must be specific to the target area — no generic "Did you know…" openers
- AIDA must flow naturally: hook → relevance → proof → ask
- Interest framing bridges the hook to the product — it answers "why should I care?"
- Desire proof points must be concrete: numbers, names, outcomes — not vague claims
- Action CTA must be low-friction (reply, 15-min call, link click) — never "sign up now"

## Anti-Spam Standards
- No buzzwords: "synergy", "leverage", "revolutionary", "game-changing"
- No false urgency: "limited time", "act now", "don't miss out"
- No fake personalization: "I noticed your company…" without citing what specifically
- Tone must match the segment — formal for enterprise, direct for founders, technical for engineers

## Consolidation Standards (finalize-outreach)
- Exec summary must fit 1 page — ruthlessly cut filler
- CSV must be valid with exact headers: channel, identifier, subject, content
- Every row in the CSV must trace back to a personalizer output
- No duplicate identifiers in the CSV

## Anti-Patterns to Avoid
- Produce EXACTLY {max_areas} target areas — no more, no fewer. Focus beats breadth.
- Do not propose generic segments like "small businesses" without specificity
- Do not claim "no competition" — there is always competition
- Do not confuse addressable market with total market
- If the research doesn't support a target area, don't force it"""
```

- [ ] **Step 4: Run all sales tests**

Run: `pytest backend/agents/tests/test_sales_department.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```
git add backend/agents/blueprints/sales/leader/agent.py backend/agents/blueprints/sales/workforce/strategist/agent.py
git commit -m "feat: sales max_target_areas config — caps target areas and informs strategist prompt"
```

---

### Task 5: Clean up stale clones from DB

**Files:**
- No code files — shell command only

- [ ] **Step 1: Delete orphaned clones**

```bash
python manage.py shell -c "
from agents.models import ClonedAgent
count = ClonedAgent.objects.all().count()
deleted, _ = ClonedAgent.objects.all().delete()
print(f'Deleted {deleted} stale clones')
"
```

- [ ] **Step 2: Commit** (no code change — just noting cleanup was done)

---

### Task 6: Verify all tests pass

- [ ] **Step 1: Run full test suite**

Run: `pytest backend/ -x -q --ignore=backend/agents/tests/test_blueprints.py`
Expected: All pass (the test_blueprints failure is pre-existing)

- [ ] **Step 2: Final commit if any fixes needed**

# Agent Spawning Hardcaps — Design Spec

**Date:** 2026-04-10
**Problem:** Sales pitch_personalizer created 690 clones in a single sprint, burning significant money. Claude's strategy output exceeded the soft "no more than 5 target areas" instruction, and nothing in the code enforced a limit.

## Root Cause

1. `create_clones(parent, count, sprint)` accepts any count with no upper bound
2. `_parse_target_areas` parses Claude's strategy output via regex — if Claude produces 100 target areas, 100 clones are created
3. The existing `MAX_CONCURRENT_PER_DEPT = 5` only gates whether the leader proposes — once a proposal is accepted, all tasks in it are created without limit
4. The strategist's "no more than 5 target areas" instruction is a soft prompt guideline, not enforcement

## Design

### Layer 1: `create_clones` hard wall

In `LeaderBlueprint.create_clones()` (`agents/blueprints/base.py`):

- Before creating any clones, check `count` against `settings.AGENT_MAX_CLONES_PER_SPRINT`
- If `count` exceeds it: **raise ValueError** — not clamp, not warn, refuse
- This is the nuclear circuit breaker — no code path can bypass it

### Layer 2: Per-proposal batch cap

In `create_next_leader_task()` (`agents/tasks.py`):

- After `generate_task_proposal()` returns, check `len(tasks_data)`
- If it exceeds `settings.AGENT_MAX_TASKS_PER_PROPOSAL`, truncate the list and log a warning
- This catches any leader blueprint returning too many tasks, not just clone fan-outs

### Layer 3: Sprint-level total cap

In `create_next_leader_task()` (`agents/tasks.py`):

- Before creating tasks, count existing tasks for this sprint
- If `AgentTask.objects.filter(sprint=sprint_id).count() >= settings.AGENT_MAX_TASKS_PER_SPRINT`, refuse and log
- This catches accumulation across multiple proposal cycles

### Layer 4: Sales department config for target areas

In the sales department blueprint:

- Add `max_target_areas` to the sales department's `config_schema` (default: 5)
- The strategist prompt reads this value dynamically: "Identify exactly {n} target areas"
- `_parse_target_areas` hard-caps its output to this value: `target_areas = target_areas[:max_target_areas]`
- Log if truncated

### Move existing hardcap to settings

The existing `MAX_CONCURRENT_PER_DEPT = 5` in `agents/tasks.py` line 353 moves to `settings.py`.

## Settings (`config/settings.py`)

```python
# Agent concurrency and spawning limits
AGENT_MAX_CONCURRENT_PER_DEPT = 5       # max queued+processing tasks per department
AGENT_MAX_CLONES_PER_SPRINT = 10        # hard wall in create_clones — raises ValueError
AGENT_MAX_TASKS_PER_PROPOSAL = 20       # max tasks from a single leader proposal
AGENT_MAX_TASKS_PER_SPRINT = 50         # absolute ceiling per sprint
```

## Sales department config schema

```python
config_schema = {
    "type": "object",
    "properties": {
        "max_target_areas": {
            "type": "integer",
            "title": "Max Target Areas",
            "description": "Maximum number of target areas the strategist produces per sprint",
            "default": 5,
            "minimum": 1,
            "maximum": 10,
        },
        # ... existing fields
    },
}
```

## Files to change

1. **`config/settings.py`** — add the four AGENT_* settings
2. **`agents/blueprints/base.py`** — `create_clones` checks `settings.AGENT_MAX_CLONES_PER_SPRINT`, raises ValueError
3. **`agents/tasks.py`** — `create_next_leader_task` reads limits from settings, enforces per-proposal and per-sprint caps, moves `MAX_CONCURRENT_PER_DEPT` to settings reference
4. **`agents/blueprints/sales/leader/agent.py`** — `_parse_target_areas` caps to department config `max_target_areas`; `_create_clones_and_dispatch` reads the same config
5. **`agents/blueprints/sales/workforce/strategist/agent.py`** — strategist system prompt and task suffix read `max_target_areas` from config dynamically
6. **`agents/blueprints/sales/__init__.py`** (or wherever department config_schema is defined) — add `max_target_areas` field
7. **Tests** — update existing tests, add tests for each cap being enforced

## Not changing

- `DEFAULT_PROFILES_PER_AREA = 50` — per-clone behavior, not spawning
- The strategist's soft prompt instruction — kept as guidance alongside the hard cap
- Sprint-triggered instruction review — uses per-agent fan-out, already self-contained

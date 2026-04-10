# Mandatory Commands + Per-Command Approval

**Date:** 2026-04-07

## Problem

1. Tasks can be created without a `command_name` — the leader self-task fallback and scheduled commands path both omit it. Every task must explicitly call a command on an agent.
2. Auto-approve is all-or-nothing per agent (`auto_approve: bool`). Users need granular control — approve research but not email sending, for example.
3. Agent display names generated during provisioning are creative nonsense ("Dormitory Narrative Designer") instead of functional labels.

Item 3 was already fixed in this session — this spec covers items 1 and 2.

## Design

### Data Model: Agent

**Remove** `auto_approve: BooleanField`.

**Add** `enabled_commands: JSONField(default=dict)` — maps command slug to boolean:

```json
{"research_industry": true, "draft_strategy": false}
```

- Commands absent from the dict default to `false` (require approval).
- "Auto-approve all" in the UI reads the agent's blueprint commands and sets every key to `true`.
- "Revoke all" sets every key to `false` (or clears the dict).

**`is_action_enabled(command_name)`** becomes:

```python
def is_action_enabled(self, command_name: str) -> bool:
    return bool((self.enabled_commands or {}).get(command_name, False))
```

### Data Model: AgentTask

**`command_name`** becomes required: `blank=False`. Every task must specify which command it calls.

Model-level `clean()` validates:
1. `command_name` is non-empty.
2. `command_name` exists on the target agent's blueprint.

This is defense-in-depth — task creation code validates first, the model catches anything that slips through.

### Task Creation: Three Paths

**1. Leader multi-task path** (`create_next_leader_task`, multi-task branch):
- Already sets `command_name` from the leader's proposal.
- Add validation: check `command_name` exists on the target agent's blueprint. If invalid → create task as `FAILED` with error message and log warning.

**2. Scheduled commands path** (`run_scheduled_actions`):
- Bug: currently doesn't set `command_name` on the created task.
- Fix: set `command_name=cmd_name` on the AgentTask.

**3. Leader self-task fallback** (`create_next_leader_task`, single-task branch):
- **Delete entirely.** Leaders always delegate to workforce agents. If the leader has nothing to delegate, it returns `None` and no task is created.

### API Serializer

Extend the agent detail serializer to include `available_commands` derived from the blueprint:

```json
{
  "id": "...",
  "name": "Pitch Architect",
  "enabled_commands": {"design_storyline": true, "revise_storyline": false},
  "available_commands": [
    {"name": "design_storyline", "description": "Design the outreach storyline"},
    {"name": "revise_storyline", "description": "Revise storyline based on feedback"}
  ]
}
```

This lets the frontend render toggles for each command without hardcoding blueprint knowledge.

### Frontend: Agent Card

The "Auto" badge on the agent card stays. Behavior changes:
- Shows as active (violet) when ALL commands are enabled.
- Click toggles all commands on/off.
- During save: pulsating disabled state (same pattern as provisioning indicator).

### Frontend: Agent Detail View (Config Tab)

Replace the single auto-approve toggle with:
- **Header row**: "Auto-approve all" / "Revoke all" button with pulsating disabled state during save.
- **Command list**: Each command shows name, description, and an individual toggle. Each toggle saves immediately with pulsating disabled state.

### Migration

1. Add `enabled_commands: JSONField(default=dict)` to Agent.
2. Data migration: for agents with `auto_approve=True`, read their blueprint's commands and populate `enabled_commands` with all commands set to `True`. Agents with `auto_approve=False` get empty dict.
3. Backfill any existing `AgentTask` records with blank `command_name` — set a sensible default based on the agent's blueprint (first command) or leave as-is since historical tasks don't execute again.
4. Make `command_name` non-blank on AgentTask.
5. Remove `auto_approve` from Agent.

### Validation at Every Layer

| Layer | What | How |
|-------|------|-----|
| Leader prompt | Claude must propose valid command_name | Prompt includes available commands per agent |
| Task creation code | Validate command exists on blueprint | Check before `AgentTask.objects.create()`, fail visibly if invalid |
| AgentTask model | `clean()` rejects blank or invalid command_name | Defense-in-depth, catches bugs in new code paths |
| Approval flow | `is_action_enabled()` checks per-command | `enabled_commands.get(command_name, False)` |

### What This Does NOT Change

- How `execute_task` dispatches work — blueprints already route by `task.command_name`.
- Leader `generate_task_proposal` — leaders already propose commands for workforce agents. We just validate the output now.
- Review chains — these already use `command_name` for creator/reviewer pairing.
- Department-level config or config_schema — unrelated.

# Sprint Reset + Pipeline State Migration

**Date:** 2026-04-10
**Status:** Draft

## Summary

Move pipeline state from leader `internal_state` to a new `department_state` JSONField on the Sprint model. Add a "Reset Sprint" admin action that nukes all derived artifacts and restarts the pipeline from scratch. Scope: sales and writers room leaders only (engineering is a stub).

## Part 1: Sprint Model — `department_state` JSONField

New field on Sprint:

```python
department_state = JSONField(default=dict, blank=True)
```

Structure — keyed by department ID (string):

```python
{
    "dept-uuid-sales": {
        "pipeline_step": "research",
        "review_rounds": {"task-uuid": 2},
        "polish_attempts": {"task-uuid": 1},
        "active_review_key": "task-uuid"
    },
    "dept-uuid-writers-room": {
        "current_stage": "concept",
        "current_iteration": 0,
        "stage_status": {
            "concept": {"iterations": 2, "status": "passed"}
        },
        "format_type": "standalone",
        "terminal_stage": "treatment",
        "detection_reasoning": "...",
        "entry_detected": true
    }
}
```

Each department type stores whatever keys it needs. No schema enforcement — the leader blueprint owns the shape.

### Read/Write Pattern

Leaders currently do:
```python
# OLD — on leader.internal_state
internal_state = agent.internal_state or {}
pipeline_steps = internal_state.get("pipeline_steps", {})
current_step = pipeline_steps.get(sprint_id, None)
```

New pattern:
```python
# NEW — on sprint.department_state
dept_id = str(agent.department_id)
dept_state = sprint.department_state.get(dept_id, {})
current_step = dept_state.get("pipeline_step")
```

And for writes:
```python
# OLD
pipeline_steps[sprint_id] = next_step
internal_state["pipeline_steps"] = pipeline_steps
agent.internal_state = internal_state
agent.save(update_fields=["internal_state"])

# NEW
dept_state["pipeline_step"] = next_step
sprint.department_state[dept_id] = dept_state
sprint.save(update_fields=["department_state"])
```

### Helper on Sprint Model

Add convenience methods to Sprint:

```python
def get_department_state(self, department_id: str) -> dict:
    return self.department_state.get(str(department_id), {})

def set_department_state(self, department_id: str, state: dict):
    self.department_state[str(department_id)] = state
    self.save(update_fields=["department_state", "updated_at"])
```

### What Moves Where

**Sales leader — moves to `sprint.department_state[dept_id]`:**
- `pipeline_step` (was `internal_state["pipeline_steps"][sprint_id]`)

**Sales leader — stays on `leader.internal_state`:**
- Nothing sprint-specific remains. The `internal_state` becomes empty for sales leaders.

**Writers room leader — moves to `sprint.department_state[dept_id]`:**
- `current_stage`
- `current_iteration`
- `stage_status`
- `format_type`
- `terminal_stage`
- `detection_reasoning`
- `entry_detected`

**Writers room leader — stays on `leader.internal_state`:**
- Nothing sprint-specific remains.

**Review tracking (base class) — moves to `sprint.department_state[dept_id]`:**
- `review_rounds`
- `polish_attempts`
- `active_review_key`

The base class `_propose_review_chain`, `_apply_quality_gate`, `_evaluate_review_and_loop`, and `_check_review_trigger` all read/write these keys. They need to be updated to operate on `sprint.department_state` instead of `agent.internal_state`. This requires passing the sprint object into these methods (or resolving it from the task's sprint FK).

## Part 2: Reset Sprint Admin Action

Django admin action: "Reset and restart sprint"

### What it does

1. **Delete all AgentTask** for the sprint
2. **Delete all ClonedAgent** for the sprint
3. **Delete all Document** scoped to the sprint (`document.sprint == sprint`)
4. **Delete all Output** for the sprint
5. **Clear department_state:** `sprint.department_state = {}`
6. **Reset sprint fields:** `status = RUNNING`, `completion_summary = ""`, `completed_at = None`
7. **Trigger leader task chain** for each department via `create_next_leader_task.delay(leader.id)`

### Admin registration

Add to `SprintAdmin`:
```python
actions = ["reset_and_restart"]

@admin.action(description="Reset and restart sprint (deletes all tasks, docs, outputs)")
def reset_and_restart(self, request, queryset):
    for sprint in queryset:
        # ... delete + reset + trigger
    self.message_user(request, f"Reset {queryset.count()} sprint(s)")
```

### Safety

- Works on any sprint status (RUNNING, PAUSED, DONE)
- Confirmation via Django's built-in admin action confirmation page
- Logs the reset with counts of deleted objects

## What This Doesn't Touch

- **Engineering leader** — stub, not migrated
- **Community leader** — stub, not migrated
- **Marketing leader** — uses a different pattern, not migrated
- **Agent.internal_state field** — stays on the model, still used for non-sprint state (email briefings, send counts, etc.)
- **Frontend** — no changes needed, sprint state is backend-only

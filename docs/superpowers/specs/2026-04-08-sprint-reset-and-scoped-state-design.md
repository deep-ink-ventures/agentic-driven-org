# Sprint Reset Admin Action & Sprint-Scoped Agent State

**Date:** 2026-04-08
**Status:** Draft

## Problem

1. **No way to reset a sprint for testing.** Once a sprint runs, all generated artifacts (tasks, documents, outputs, agent state) persist. To re-test, you must manually delete records across multiple tables.

2. **Agent internal state is not sprint-scoped.** `Agent.internal_state` is a single JSONField shared across all sprints. When two sprints run concurrently on the same department, state like `stage_status`, `review_rounds`, and `active_review_key` collides. A second sprint overwrites the first sprint's progress tracking.

## Design

### 1. New Model: `AgentSprintState`

A per-agent, per-sprint state container. Holds all state that blueprints currently store in `Agent.internal_state` that is sprint-specific.

```python
class AgentSprintState(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="sprint_states",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="agent_states",
    )
    state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agent", "sprint"],
                name="one_state_per_agent_per_sprint",
            ),
        ]
```

**What moves to `AgentSprintState.state`:**
- `stage_status` — leader workflow stage tracking
- `review_rounds` — review loop counters
- `active_review_key` — current review chain pointer
- `polish_attempts` — polish iteration counters

**What stays on `Agent.internal_state`:**
- `pending_webhook_events` — not sprint-scoped, driven by external integrations
- Any future hourly-task or cron-style state

### 2. Blueprint State Access

Replace direct `agent.internal_state` reads/writes for sprint-scoped keys with a helper pattern:

```python
# In base blueprint or as a standalone helper:

def get_sprint_state(agent, sprint):
    """Get or create the AgentSprintState for this agent+sprint pair."""
    from agents.models import AgentSprintState
    obj, _ = AgentSprintState.objects.get_or_create(
        agent=agent, sprint=sprint,
    )
    return obj

def save_sprint_state(state_obj):
    """Save the sprint state object."""
    state_obj.save(update_fields=["state", "updated_at"])
```

All blueprint code that currently does:
```python
internal_state = agent.internal_state or {}
stage_status = internal_state.get("stage_status", {})
```

Becomes:
```python
sprint_state = get_sprint_state(agent, task.sprint)
stage_status = sprint_state.state.get("stage_status", {})
```

And saves become:
```python
sprint_state.state["stage_status"] = stage_status
save_sprint_state(sprint_state)
```

### 3. Admin Action: Reset Sprint

A Django admin action on the `SprintAdmin` that wipes all generated artifacts and resets the sprint to a fresh RUNNING state.

**What gets deleted:**
| Related model | Relationship | Action |
|---|---|---|
| `AgentTask` | `sprint.tasks` | Delete all |
| `Output` | `sprint.outputs` | Delete all (CASCADE anyway) |
| `Document` | `sprint.documents` | Delete all |
| `AgentSprintState` | `sprint.agent_states` | Delete all |

**What is preserved:**
| Data | Reason |
|---|---|
| `Sprint.text` | The work instruction — this IS the sprint |
| `Source` records | User-uploaded reference material for the sprint |
| `Sprint.departments` | The department assignment |

**What gets reset on the Sprint itself:**
- `status` → `RUNNING`
- `completion_summary` → `""`
- `completed_at` → `None`

**Admin action implementation:**

```python
@admin.action(description="Reset selected sprints (delete all tasks, docs, outputs, agent state)")
def reset_sprint(modeladmin, request, queryset):
    for sprint in queryset:
        sprint.tasks.all().delete()
        sprint.documents.all().delete()
        sprint.outputs.all().delete()
        sprint.agent_states.all().delete()
        sprint.status = Sprint.Status.RUNNING
        sprint.completion_summary = ""
        sprint.completed_at = None
        sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])
```

The action does NOT automatically re-trigger leader tasks. After resetting, you manually resume the sprint from the UI or re-trigger via the API.

### 4. Migration Path for Existing Blueprints

Every file that reads/writes `agent.internal_state` for sprint-scoped keys needs updating. The affected locations (from codebase grep):

- `backend/agents/blueprints/base.py` — `_start_review_loop`, `_evaluate_review_and_loop`, `_get_review_round_count` (review_rounds, active_review_key, polish_attempts)
- `backend/agents/tasks.py` — `_apply_on_dispatch_state` (stage_status)
- `backend/agents/blueprints/sales/leader/agent.py` — stage_status reads
- `backend/agents/blueprints/writers_room/leader/agent.py` — stage_status reads

Non-sprint state (e.g. `pending_webhook_events` in `backend/integrations/tasks.py` and `backend/integrations/webhooks/adapters/github.py`) remains on `Agent.internal_state` unchanged.

## Scope

- New model + migration for `AgentSprintState`
- Update all blueprint code to use sprint-scoped state
- Admin action on `SprintAdmin`
- Tests for the reset action and state scoping

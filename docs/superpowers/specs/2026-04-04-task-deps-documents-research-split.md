# Task Dependencies, Document Types & Two-Phase Research — Design Spec

## Overview

Three coupled features: task dependencies with auto-queue on resolve, document types with lifecycle management, and two-phase research with model split. Dependencies enable the research split, documents store the output.

## 1. Task Dependencies

### Model changes on AgentTask

- `command_name` CharField(max_length=100, blank=True) — references a command on the agent's blueprint. Used by auto_actions to decide approval vs auto-execute.
- `blocked_by` FK to AgentTask (null, blank, on_delete=SET_NULL) — this task can't run until the blocker completes.

### New status value

Add `AWAITING_DEPENDENCIES = "awaiting_dependencies", "Awaiting Dependencies"` to AgentTask.Status choices.

### Status flow

```
Task created with blocked_by set:
  → awaiting_dependencies (visible in queue with badge)

Blocker task completes (status=done):
  → Check agent.auto_actions.get(task.command_name):
    - True  → queued (auto-dispatch)
    - False → awaiting_approval (needs human review)
  → If proposed_exec_at is future → planned (scheduled)

Blocker task fails:
  → blocked task stays in awaiting_dependencies
  → User can manually unblock or the blocker can be retried
```

### Auto-unblock logic

In `execute_agent_task`, after setting status to `done`:

```python
# Unblock dependent tasks
dependents = AgentTask.objects.filter(blocked_by=task, status=AgentTask.Status.AWAITING_DEPENDENCIES)
for dep in dependents:
    if dep.agent.is_action_enabled(dep.command_name):
        dep.status = AgentTask.Status.QUEUED
        dep.save(update_fields=["status", "updated_at"])
        execute_agent_task.delay(str(dep.id))
    else:
        dep.status = AgentTask.Status.AWAITING_APPROVAL
        dep.save(update_fields=["status", "updated_at"])
```

### Leader creates chains

The leader's `create-priority-task` response format updated:

```json
{
  "exec_summary": "Research and engage screenwriting communities",
  "tasks": [
    {
      "target_agent_type": "web_researcher",
      "command_name": "research-gather",
      "exec_summary": "Search for active screenwriting communities",
      "step_plan": "..."
    },
    {
      "target_agent_type": "web_researcher",
      "command_name": "research-analyze",
      "exec_summary": "Analyze findings and produce strategic recommendations",
      "step_plan": "...",
      "depends_on_previous": true
    },
    {
      "target_agent_type": "twitter",
      "command_name": "place-content",
      "exec_summary": "Post strategic content based on research",
      "step_plan": "...",
      "depends_on_previous": true
    }
  ]
}
```

`create_next_leader_task` creates tasks in order, wiring `blocked_by` on tasks with `depends_on_previous: true`. The first task gets status based on `auto_actions`. Subsequent tasks get `awaiting_dependencies`.

### Frontend

- New status badge color for `awaiting_dependencies` — grey/dimmed with a link icon
- Task card shows "Waiting on: [blocker task summary]" when expanded
- No approve/reject buttons on `awaiting_dependencies` tasks

## 2. Document Types & Lifecycle

### Model changes on Document

- `doc_type` CharField(max_length=20, choices, default="general")
- `is_archived` BooleanField(default=False)

### Document type choices

```python
class DocType(models.TextChoices):
    GENERAL = "general", "General"
    RESEARCH = "research", "Research"
    BRANDING = "branding", "Branding"
    STRATEGY = "strategy", "Strategy"
    CAMPAIGN = "campaign", "Campaign"
```

### Behavior by type

| Type | Auto-archive | Context inclusion | Created by |
|------|-------------|-------------------|------------|
| general | Never | Always | Bootstrap, manual |
| research | After 30 days | Until archived | Web researcher |
| branding | Never | Always | Bootstrap |
| strategy | Never | Always | Leader, manual |
| campaign | When campaign tasks complete | Until archived | Leader |

### Beat task

`archive_stale_documents` runs daily:
- Archives `research` docs where `created_at` < 30 days ago
- Archives `campaign` docs where all related tasks are done/failed (future — needs campaign tracking)

### Context inclusion

`BaseBlueprint.get_context()` updated:
- Excludes `is_archived=True` docs
- Groups by type in the context message
- Shows age for research docs: `[research, 2 days ago]`

```
### Department Documents
<documents>
--- [branding] Brand Voice Guide ---
Professional but friendly tone...

--- [research, 2 days ago] Reddit Community Analysis ---
r/Screenwriting: 200K subscribers, 20-40 posts/day...
</documents>
```

### Web researcher stores as research type

Already partially done (stores as Document with "research" tag). Update to set `doc_type="research"`.

## 3. Two-Phase Research with Model Split

### Replace single research commands with gather/analyze pairs

**Old commands (removed):**
- `research-trends` (hourly)
- `research-competitors` (daily)
- `find-content-opportunities` (on-demand)

**New commands:**

`research-gather` (schedule matches old command, model=haiku):
- Calls web search service
- Sends raw results to Haiku: "Organize these search results. Extract key facts, URLs, relevance. Return structured JSON."
- Stores structured data in `task.report`
- Should auto-execute (cheap, just gathering)

`research-analyze` (no schedule — triggered as dependency, model=sonnet):
- Reads `blocked_by.report` (the raw gathered data)
- Sends to Sonnet: "Analyze in context of project goal. Produce strategic recommendations with angles."
- Stores analysis as `research` type document on the department
- Goes to `awaiting_approval` by default (you review before it becomes department knowledge)

### How they chain

When `research-gather` is scheduled (hourly/daily), it creates a `research-analyze` task as a dependent:

In the gather command's return or in the web researcher's `execute_task`:

After gather completes successfully, create the analyze task:
```python
AgentTask.objects.create(
    agent=agent,
    command_name="research-analyze",
    status=AgentTask.Status.AWAITING_DEPENDENCIES,
    blocked_by=gather_task,
    exec_summary=f"Analyze: {gather_task.exec_summary}",
    step_plan="Analyze the gathered research and produce strategic recommendations.",
)
```

The auto-unblock logic in `execute_agent_task` handles the rest.

### Web researcher execute_task update

`execute_task` checks `task.command_name`:
- `research-gather`: run web search, light Haiku analysis, return raw findings
- `research-analyze`: read `task.blocked_by.report`, deep Sonnet analysis, store as document
- Fallback (no command_name): current behavior for legacy tasks

## Migration

### Database migration
- AgentTask: add `command_name`, `blocked_by` fields
- AgentTask.Status: add `AWAITING_DEPENDENCIES` choice
- Document: add `doc_type`, `is_archived` fields

### Data migration
- Existing documents: set `doc_type="general"`
- Existing documents with tag "research": set `doc_type="research"`
- Existing tasks: `command_name` stays blank (legacy)

### Blueprint changes
- Web researcher: replace 3 commands with `research-gather` + `research-analyze`
- Leader `create-priority-task` prompt: updated to include `command_name` and `depends_on_previous` in task proposals
- `create_next_leader_task`: wire `blocked_by` based on `depends_on_previous`

### Beat schedule
- Add `archive-stale-documents` (daily)

## Scope

**In scope:**
- AgentTask: command_name, blocked_by, awaiting_dependencies status
- Auto-unblock on task completion
- Leader creates dependency chains
- Document: doc_type, is_archived
- Context excludes archived docs, groups by type
- Beat task for stale doc archival
- Web researcher gather/analyze split with model selection
- Frontend: awaiting_dependencies badge, blocker info

**Out of scope:**
- Multiple blockers (M2M) — start with single FK, extend later if needed
- Campaign-level document archival — needs campaign model first
- Frontend document management UI — use admin for now

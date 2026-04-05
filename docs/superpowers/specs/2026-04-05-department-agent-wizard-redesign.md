# Department & Agent Wizard Redesign

**Date:** 2026-04-05
**Status:** Approved

## Problem

The current department provisioning flow has three critical flaws:

1. **Claude silently drops agents.** When a department is added, Claude decides which workforce agents to provision. Essential feedback-loop agents (analysts in Writers Room, reviewers in Engineering) are regularly omitted without the user ever knowing they existed.
2. **No agent selection in the wizard.** Users can only pick departments, not agents within them. There is no visibility into what agents are available.
3. **No way to add agents after creation.** Departments are frozen after initial setup. If an agent was omitted, the only path is database manipulation.

The same problem exists in the bootstrap flow (`_apply_proposal`), which also lets Claude silently drop agents.

## Design Principles

- Claude recommends, the user decides
- Essential feedback loops are structurally protected
- Agent relationships are declared on the agents themselves, not on the department
- The user can always see what's available and add it

## 1. Blueprint Changes

### 1.1 New fields on `BaseBlueprint`

Two new optional fields:

```python
class BaseBlueprint:
    essential = False       # bool — always pre-selected for the department
    controls = None         # str | list[str] | None — auto-selected when controlled agent is selected
```

### 1.2 Agent relationship map

**Writers Room:**

| Agent | Mechanism |
|---|---|
| `market_analyst` | `controls = "story_researcher"` |
| `structure_analyst` | `controls = "story_architect"` |
| `character_analyst` | `controls = "character_designer"` |
| `dialogue_analyst` | `controls = "dialog_writer"` |
| `format_analyst` | `essential = True` |
| `production_analyst` | `essential = True` |

**Engineering:**

| Agent | Mechanism |
|---|---|
| `review_engineer` | `controls = ["backend_engineer", "frontend_engineer"]` |
| `test_engineer` | `controls = ["backend_engineer", "frontend_engineer"]` |
| `security_auditor` | `controls = ["backend_engineer", "frontend_engineer"]` |
| `accessibility_engineer` | `controls = "frontend_engineer"` |
| `ticket_manager` | `essential = True` |

### 1.3 Selection logic

Used by the frontend wizard, bootstrap, and Claude prompt:

1. Start with Claude's recommended agents
2. Add all agents with `essential = True`
3. For each selected agent, add any agent whose `controls` includes it
4. This is the pre-checked set. User can deselect anything, with warnings for essential/controller agents.

Inverse: deselecting a controlled agent should prompt whether to also deselect its controller.

### 1.4 New helper function

`get_workforce_metadata(department_type)` — returns all workforce agents with `essential`, `controls`, `name`, `description` for API and prompt use.

## 2. Data Model Changes

### 2.1 Agent status field

Replace `is_active: bool` with a proper status:

```python
class Agent(models.Model):
    class Status(models.TextChoices):
        PROVISIONING = "provisioning"
        ACTIVE = "active"
        INACTIVE = "inactive"
        FAILED = "failed"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROVISIONING)
```

**Migration:** `is_active=True` maps to `active`, `is_active=False` maps to `inactive`.

All code reading `is_active` updates to check `status`. This includes: queryset filters, admin, serializers, blueprint execution logic, task views, WebSocket broadcasts.

### 2.2 No model changes for blueprint metadata

`essential` and `controls` live on the Python blueprint classes, not in the database. They are exposed through API responses.

## 3. API Changes

### 3.1 Modified: `GET /api/projects/{project_id}/departments/available/`

Currently returns available department types with workforce lists. Changes:

- Adds a Claude recommendation call given the project context
- Response includes `recommended` flag per department and per agent
- Each agent includes `essential`, `controls`, and `recommended` fields

Response shape:

```json
{
  "departments": [
    {
      "department_type": "writers_room",
      "name": "Writers Room",
      "description": "AI-powered writers room...",
      "recommended": true,
      "config_schema": {},
      "workforce": [
        {
          "agent_type": "dialog_writer",
          "name": "Dialog Writer",
          "description": "...",
          "recommended": true,
          "essential": false,
          "controls": null
        },
        {
          "agent_type": "dialogue_analyst",
          "name": "Dialogue Analyst",
          "description": "...",
          "recommended": false,
          "essential": false,
          "controls": "dialog_writer"
        },
        {
          "agent_type": "format_analyst",
          "name": "Format Analyst",
          "description": "...",
          "recommended": false,
          "essential": true,
          "controls": null
        }
      ]
    }
  ]
}
```

Loading state: this endpoint will be slower due to the Claude call. Frontend shows a spinner while the wizard loads.

### 3.2 Modified: `POST /api/projects/{project_id}/departments/add/`

Request body changes to include explicit agent selections per department:

```json
{
  "departments": [
    {
      "department_type": "writers_room",
      "agents": ["dialog_writer", "dialogue_analyst", "story_architect",
                 "structure_analyst", "format_analyst", "production_analyst"]
    }
  ],
  "context": "optional text"
}
```

The `configure_new_department` task provisions exactly the user-selected agents. Claude generates tailored instructions and documents but cannot drop agents.

### 3.3 New: `POST /api/agents/add/`

For adding a single agent to an existing department after creation:

```json
{
  "department_id": "uuid",
  "agent_type": "character_analyst"
}
```

- Validates `agent_type` exists in the department's workforce blueprints
- Validates agent not already provisioned in that department
- Creates Agent with `status = "provisioning"`
- Kicks off async Claude call to generate tailored instructions
- Returns immediately with the agent record
- WebSocket event signals completion

## 4. Claude Prompt Changes

### 4.1 Recommendation prompt (new, for `GET /available/`)

Claude receives:
- Project name, goal, sources summary
- All available departments with all workforce agents
- `essential` and `controls` metadata per agent
- Existing departments already installed

Prompt instructs Claude to:
- Recommend departments that suit the project
- For each department, recommend which agents to activate
- Essential and controller agents will be auto-included by the system — focus recommendations on creative/production agents that fit the project

Claude returns:

```json
{
  "departments": ["writers_room", "marketing"],
  "agents": {
    "writers_room": ["story_researcher", "dialog_writer", "story_architect", "character_designer"],
    "marketing": ["twitter", "web_researcher"]
  }
}
```

The backend layers on essential + controls logic before sending to the frontend.

### 4.2 Provisioning prompt (modified `configure_new_department`)

Currently Claude decides which agents to create. Now it receives a fixed list of user-selected agents and only generates:
- Tailored instructions per agent
- Initial documents for the department

Claude no longer has the power to drop agents.

### 4.3 Single agent prompt (new, for `POST /api/agents/add/`)

Small Claude call: given project context + department context + existing agent instructions + target agent blueprint, generate tailored instructions for this one agent.

### 4.4 Bootstrap (`_apply_proposal`)

After applying Claude's proposed agents from the bootstrap proposal, run the selection logic: add any missing essential agents and any controller agents whose target was included. These get blueprint default instructions (a follow-up Claude call could refine them, but is not required).

## 5. Wizard Flow (Frontend)

### 5.1 Two-step wizard

**Step 1: Departments + Agents (combined)**
- All available departments listed as expandable cards
- Claude's recommended departments: pre-checked and expanded
- Non-recommended departments: unchecked and collapsed
- Checking a department expands it to show all its workforce agents
- Unchecking a department collapses it and deselects all its agents
- Within each expanded department:
  - All workforce agents listed with checkboxes
  - Pre-checked: Claude's recommendations + essential + controllers (per selection logic)
  - Essential agents show an "Essential" label
  - Controller agents show what they control, e.g. "Reviews Dialog Writer"
  - Deselecting an essential or controller agent shows inline warning: "This agent is part of the feedback loop. Removing it may reduce quality."
  - Deselecting a controlled agent prompts whether to also deselect its controller

**Step 2: Context**
- Optional textarea for additional instructions
- Submit button triggers provisioning

**Loading state:** Wizard opens with a spinner while `GET /available/` calls Claude for recommendations. Once loaded, all interaction is instant.

### 5.2 Department detail page — inline agent management

For adding agents to an existing department after creation:

- Below the active agents grid, a divider and "Available Agents" section
- Lists all blueprint agents for that department type that are NOT yet provisioned
- Each shows: name, description, relevant labels ("Essential", "Reviews Dialog Writer")
- An "Add" button per agent
- Clicking "Add":
  - Agent moves from "Available" to the active grid immediately
  - Renders in provisioning state: greyed out card with spinner/pulse, name visible, no config or actions
  - Backend creates Agent with `status = "provisioning"`, kicks off async Claude instruction generation
  - WebSocket event `agent.configured` transitions card to normal active state
  - On failure: card shows error state with "Retry" button
- If no unprovisioned agents remain, the "Available Agents" section is hidden

## 6. WebSocket Events

New agent-level events alongside existing `department.configured`:

- **`agent.provisioning`** — agent record created, instruction generation in progress
- **`agent.configured`** — agent ready, instructions generated, `status` set to `active`
- **`agent.failed`** — instruction generation failed, `status` set to `failed`

These use the existing broadcast infrastructure (`_broadcast_department` pattern in `tasks.py`).

## 7. Files Affected

### Backend
- `backend/agents/blueprints/base.py` — add `essential`, `controls` fields
- `backend/agents/blueprints/writers_room/workforce/*/agent.py` — set `essential`/`controls` per table above
- `backend/agents/blueprints/engineering/workforce/*/agent.py` — set `essential`/`controls` per table above
- `backend/agents/blueprints/__init__.py` — add `get_workforce_metadata()` helper
- `backend/agents/models/agent.py` — replace `is_active` with `status` field
- `backend/agents/migrations/` — new migration for `is_active` → `status`
- `backend/agents/serializers/` — update for `status` field
- `backend/agents/admin/` — update for `status` field
- `backend/agents/views/agent_view.py` — new `AddAgentView`
- `backend/agents/urls.py` — new route for add agent
- `backend/projects/views/add_department_view.py` — Claude recommendation call in `GET`, explicit agent selection in `POST`
- `backend/projects/views/bootstrap_view.py` — apply essential/controls logic in `_apply_proposal`
- `backend/projects/tasks.py` — modify `configure_new_department` to provision user-selected agents, new single-agent provisioning task
- `backend/projects/consumers.py` — agent-level WebSocket events

### Frontend
- `frontend/components/add-department-wizard.tsx` — full redesign: combined department+agent selection, loading state, warnings
- `frontend/app/(app)/project/[...path]/page.tsx` — department detail: available agents section, provisioning states
- `frontend/lib/api.ts` — updated API types and methods

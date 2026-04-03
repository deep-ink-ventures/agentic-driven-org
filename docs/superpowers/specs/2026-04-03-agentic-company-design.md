# The Agentic Company — Design Spec

## Overview

A Django-based platform where AI agents organized into departments work toward a project goal. Agents propose tasks, get human approval, and execute via Claude API + Playwright browser automation. Celery Beat drives the autonomous loop.

## Architecture

- **Backend:** Django 5.x + DRF + Celery/Beat + Redis + Postgres
- **ASGI:** Daphne + Django Channels (WebSockets for real-time task updates)
- **Auth:** allauth with Google OAuth, AllowList gating
- **AI:** Anthropic Claude API (claude-sonnet-4-6)
- **Browser Automation:** Playwright (installed on worker VM)
- **Frontend:** Django Admin initially, then Next.js (mirroring scriptpulse stack)
- **Deploy target:** Cloud Run for web, VM for Celery workers + Playwright

Reference architecture: `../scriptpulse` — celery/beat, daphne, allauth, allowlist, WebSocket ticket auth, sendgrid, docker-compose.

## Apps

### accounts

Lifted from scriptpulse. User model (UUID PK, email-only, no username), AllowList for signup gating, Google OAuth via allauth, custom adapters.

File structure:
```
accounts/
├── models/
│   ├── __init__.py
│   ├── user.py
│   └── allow_list.py
├── admin/
│   ├── __init__.py
│   ├── user_admin.py
│   └── allow_list_admin.py
├── adapter.py
├── migrations/
└── ...
```

### projects

Project hierarchy and knowledge base.

File structure:
```
projects/
├── models/
│   ├── __init__.py
│   ├── project.py
│   ├── department.py
│   ├── document.py
│   └── tag.py
├── admin/
│   ├── __init__.py
│   ├── project_admin.py
│   ├── department_admin.py
│   └── document_admin.py
├── migrations/
└── ...
```

### agents

Agent configuration, tasks, AI client, and agent blueprints.

File structure:
```
agents/
├── models/
│   ├── __init__.py
│   ├── agent.py
│   └── agent_task.py
├── admin/
│   ├── __init__.py
│   ├── agent_admin.py
│   └── agent_task_admin.py
├── ai/
│   ├── __init__.py
│   └── claude_client.py
├── blueprints/
│   ├── __init__.py          # registry, AGENT_TYPE_CHOICES
│   ├── base.py              # BaseBlueprint ABC
│   ├── twitter/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── skills.py
│   ├── reddit/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── skills.py
│   └── campaign/
│       ├── __init__.py
│       ├── agent.py
│       └── skills.py
├── tasks.py                 # Celery beat tasks + execute_agent_task
├── migrations/
└── ...
```

### integrations

Browser automation via Playwright. No models. Future: platform-specific API clients.

File structure:
```
integrations/
├── __init__.py
└── browser.py               # Playwright runner
```

## Data Models

### accounts.User

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| email | EmailField unique | |
| username | None | Removed from AbstractUser |
| is_staff, is_superuser | BooleanField | From AbstractUser |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

### accounts.AllowList

| Field | Type | Notes |
|-------|------|-------|
| email | EmailField unique | Lowercased on save |
| created_at | DateTimeField auto_now_add | |

### projects.Project

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| name | CharField | |
| goal | TextField | Markdown — the project's objective |
| owner | FK → User | |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

### projects.Department

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| name | CharField | e.g. "Social Media", "Engineering" |
| project | FK → Project | |
| created_at | DateTimeField auto_now_add | |

### projects.Tag

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| name | CharField unique | e.g. "branding-guidelines" |
| created_at | DateTimeField auto_now_add | |

### projects.Document

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| title | CharField | |
| content | TextField | Markdown |
| department | FK → Department | |
| tags | M2M → Tag | |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

### agents.Agent

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| name | CharField | Display name, e.g. "Our Twitter Guy" |
| agent_type | CharField choices | From blueprint registry: twitter, reddit, campaign |
| department | FK → Department | |
| superior | FK → self, null | Campaign agent is superior to twitter/reddit |
| instructions | TextField blank | User fine-tuning layered on blueprint prompts |
| config | JSONField default={} | Per-agent config (browser cookies, etc.) |
| auto_exec_hourly | BooleanField default=False | |
| is_active | BooleanField default=True | |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

The `agent_type` field maps to a blueprint package in `agents/blueprints/`. The blueprint defines system_prompt, hourly_prompt, task_generation_prompt, and skills. The `instructions` field appends user-specific tuning to the system prompt.

### agents.AgentTask

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | |
| agent | FK → Agent | |
| created_by_agent | FK → Agent, null | Set when a superior delegates |
| status | CharField | awaiting_approval, queued, processing, done, failed |
| auto_execute | BooleanField default=False | |
| exec_summary | TextField blank | Short description of what to do |
| step_plan | TextField blank | Detailed step-by-step plan |
| report | TextField blank | What was actually done |
| error_message | TextField blank | |
| started_at | DateTimeField null | |
| completed_at | DateTimeField null | |
| created_at | DateTimeField auto_now_add | |
| updated_at | DateTimeField auto_now | |

## Agent Blueprints

Each blueprint is a Python package under `agents/blueprints/`:

**base.py — BaseBlueprint ABC:**
- `name: str` — display name
- `slug: str` — matches agent_type choices
- `system_prompt: str` — agent persona and role
- `hourly_prompt: str` — what to do on hourly beat
- `task_generation_prompt: str` — how to propose new tasks
- `get_context(agent) → dict` — gathers project goal, department docs, sibling agents' recent tasks
- `execute_task(agent, task) → str` — runs the task via Claude + integrations, returns report text
- `generate_task_proposal(agent) → dict` — asks Claude to propose next task, returns {exec_summary, step_plan}

**skills.py per blueprint:**
Constants describing what the agent can do. Injected into system prompt. Not a model.

```python
SKILLS = [
    {"name": "Login to Twitter", "description": "Navigate to twitter.com and authenticate using stored session cookies"},
    {"name": "Post Tweet", "description": "Compose and post a tweet with optional media"},
]
```

**Initial blueprints:**
- `twitter/` — engage with tweets, post content, search trending topics
- `reddit/` — post to subreddits, comment on threads, browse relevant communities
- `campaign/` — create cross-platform campaigns, delegate tasks to subordinate agents (twitter, reddit)

## Execution Flow

### Celery Beat Schedule

1. **`agents.tasks.refill_approval_queue`** — every 60 seconds
   - For each active agent: count tasks with status=awaiting_approval
   - If < 5: call `blueprint.generate_task_proposal(agent)`
   - Claude returns exec_summary + step_plan
   - Create AgentTask with status=awaiting_approval, auto_execute=False

2. **`agents.tasks.execute_hourly_tasks`** — every 3600 seconds
   - For each active agent with auto_exec_hourly=True:
   - Create AgentTask from blueprint's hourly_prompt
   - Set auto_execute=True, status=queued
   - Dispatch `execute_agent_task.delay(task_id)`

### Task Approval (Django Admin)

- Admin lists tasks in awaiting_approval with exec_summary + step_plan
- Admin action "Approve selected tasks" → status=queued, dispatches execute_agent_task
- Admin action "Reject selected tasks" → status=failed with note

### Task Execution — `execute_agent_task` Celery task

1. Atomic guard: UPDATE status=processing WHERE status=queued (prevents double-exec)
2. Load agent + blueprint
3. Call `blueprint.execute_task(agent, task)`:
   a. Build context: project goal, department docs, recent sibling activity
   b. Call Claude with system_prompt + agent.instructions + task details + context
   c. Claude responds with actions
   d. Blueprint decides how to execute — some blueprints (twitter, reddit) use Playwright for browser actions, others (campaign) may only orchestrate subordinate tasks. Playwright is an agent-specific capability, not a universal execution step.
   e. Return report text
4. On success: status=done, fill report, set completed_at
5. On failure: status=failed, fill error_message

### Superior Delegation

When campaign blueprint executes, it may create AgentTasks on subordinate agents:
- `auto_execute=True` (campaign was already approved)
- `created_by_agent=campaign_agent`
- `status=queued`
- Immediately dispatched via `execute_agent_task.delay()`

## Integrations App

**browser.py** — wraps Playwright CLI for browser automation:
- `run_browser_action(action_type, params, agent_config) → result`
- Manages browser sessions using config from agent.config JSON (cookies, etc.)
- Playwright runs headless on the worker VM

## Infrastructure (from scriptpulse)

- **docker-compose.dev.yml:** Postgres + Redis only (backend runs locally)
- **docker-compose.yml:** Full stack — web (daphne), celery worker, celery beat, postgres, redis, frontend
- **config/settings.py:** Single settings file with env var overrides (like scriptpulse)
- **config/celery.py:** Standard Celery setup with autodiscover
- **config/asgi.py:** Daphne + Channels with ticket-based WebSocket auth
- **start-dev.sh:** Starts postgres/redis via docker, then django + celery + (later) frontend

## Admin UI

Rich Django admin as the initial interface:

- **ProjectAdmin:** inline departments
- **DepartmentAdmin:** inline documents, link to agents
- **AgentAdmin:** shows agent_type, department, superior, config editor, is_active toggle
- **AgentTaskAdmin:** list filterable by status/agent, approve/reject actions, read-only report field
- Dashboard-style: recent tasks, approval queue count per agent

## Scope for Initial Build

**In scope:**
- All models and admin
- Celery beat with both periodic tasks
- Claude AI integration (claude_client.py)
- Three blueprints (twitter, reddit, campaign) with real prompts
- Playwright integration (browser.py)
- accounts app (user, allowlist, google oauth) from scriptpulse
- WebSocket setup (for future real-time task updates)
- docker-compose for local dev
- start-dev.sh

**Out of scope (future iterations):**
- Next.js frontend
- Engineering department agents
- SendGrid email notifications
- Production deployment config
- REST API endpoints

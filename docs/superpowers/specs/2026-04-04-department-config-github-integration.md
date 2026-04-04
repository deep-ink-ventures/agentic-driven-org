# Department Config, Cascading Config & GitHub Integration — Design Spec

## Overview

Three coupled pieces: department-level config, cascading config lookup across agent → department → project, and GitHub integration service with webhooks. This is infrastructure for the engineering department (spec 2) but designed generically.

## 1. Department Config

### Model change on Department

Add `config` JSONField to Department:

```python
config = models.JSONField(default=dict, blank=True, help_text="Department-level config — cascades to agents")
```

### Department blueprint config_schema

Department blueprints (in `__init__.py`) declare `config_schema` — same dict format as agent blueprints:

```python
# blueprints/engineering/__init__.py
DEPARTMENT_NAME = "Engineering"
DEPARTMENT_DESCRIPTION = "..."
DEPARTMENT_CONFIG_SCHEMA = {
    "github_token": {"type": "str", "required": True, "label": "GitHub Token", "description": "Personal access token with repo + project management access"},
    "github_repos": {"type": "list", "required": True, "label": "Repositories", "description": "List of GitHub repos (owner/repo format)"},
    "github_webhook_secret": {"type": "str", "required": False, "label": "Webhook Secret", "description": "Auto-generated on bootstrap"},
}
```

### Validation

Department config validated against its blueprint's schema — same `jsonschema` pattern as agent and project config. The `DEPARTMENTS` registry entry includes a `config_schema` key.

### Admin + API

- Department admin shows config JSONField
- `DepartmentDetailSerializer` includes `config` and `config_schema`
- Frontend department view gets a config section (future — not in this spec)

## 2. Cascading Config Lookup

### Agent.get_config_value(key, default=None)

New method on Agent model:

```python
def get_config_value(self, key, default=None):
    """Look up config value: agent → department → project. Most specific wins."""
    # Agent level
    if key in self.config:
        return self.config[key]
    # Department level
    dept_config = self.department.config or {}
    if key in dept_config:
        return dept_config[key]
    # Project level
    project_config = self.department.project.config
    if project_config and project_config.config and key in project_config.config:
        return project_config.config[key]
    return default
```

### Effective config in serializer

`AgentSummarySerializer` gets `effective_config` and `config_source` fields:

```python
effective_config = SerializerMethodField()
config_source = SerializerMethodField()

def get_effective_config(self, obj):
    """Merged config: project → department → agent (agent wins)."""
    merged = {}
    pc = obj.department.project.config
    if pc and pc.config:
        merged.update(pc.config)
    if obj.department.config:
        merged.update(obj.department.config)
    merged.update(obj.config)
    return merged

def get_config_source(self, obj):
    """For each key, where it comes from: 'agent', 'department', 'project'."""
    sources = {}
    pc = obj.department.project.config
    if pc and pc.config:
        for k in pc.config:
            sources[k] = "project"
    if obj.department.config:
        for k in obj.department.config:
            sources[k] = "department"
    for k in obj.config:
        sources[k] = "agent"
    return sources
```

### Frontend config tab

- Shows all fields from the blueprint's `config_schema`
- For each field, shows the effective value
- If value is inherited (source = "department" or "project"), show as dimmed placeholder with a label like "from department" / "from project"
- User can type in the field to override at agent level
- Clearing an overridden field removes it from agent.config, falling back to inherited value

### Integration services use cascading

All integration services call `agent.get_config_value("key")` instead of `agent.config["key"]`. This means:
- `github_token` set on department → all engineering agents inherit it
- `reddit_username` set on project → all Reddit agents across departments inherit it
- An agent can override any inherited value

## 3. GitHub Integration Service

### New service: integrations/github_dev/service.py

Named `github_dev` to distinguish from the Google `gdrive` service. Provides:

```python
def get_client(token: str) -> object:
    """Get authenticated GitHub API client (PyGithub or requests-based)."""

def list_repos(token: str) -> list[dict]:
    """List repos accessible with this token."""

def create_project(token: str, repo: str, project_name: str, columns: list[str]) -> dict:
    """Create a GitHub Project (v2) with columns."""

def create_issue(token: str, repo: str, title: str, body: str, labels: list[str] = None) -> dict:
    """Create an issue in a repo."""

def create_pull_request(token: str, repo: str, title: str, body: str, head: str, base: str = "main") -> dict:
    """Create a PR."""

def dispatch_workflow(token: str, repo: str, workflow_file: str, ref: str, inputs: dict) -> dict:
    """Trigger a GitHub Actions workflow via workflow_dispatch."""

def get_workflow_run(token: str, repo: str, run_id: int) -> dict:
    """Get workflow run status and conclusion."""

def get_workflow_logs(token: str, repo: str, run_id: int) -> str:
    """Fetch workflow run logs."""

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""

def move_project_item(token: str, project_id: str, item_id: str, column: str) -> dict:
    """Move an item to a column in a GitHub Project."""
```

All functions are stateless — take the token as a parameter. The token comes from `agent.get_config_value("github_token")`.

### Dependency

Add `PyGithub` or use plain `requests` with the GitHub REST API. I recommend `requests` — it's already a dependency and we only need a few endpoints. No new package needed.

## 4. Webhook Endpoint

### URL

```
POST /api/projects/{project_id}/webhooks/github/
```

No auth header — GitHub webhooks use HMAC signature verification via `X-Hub-Signature-256` header.

### Flow

1. GitHub sends webhook event (workflow_run, pull_request, etc.)
2. Endpoint looks up the project, finds the engineering department
3. Reads `webhook_secret` from department config
4. Verifies HMAC signature
5. Parses event type and payload
6. For `workflow_run.completed`:
   - Finds tasks in `internal_state` that reference this `run_id`
   - Fetches logs via GitHub API
   - Stores logs in the task report
   - Unblocks dependent tasks
7. For `pull_request.closed` (merged):
   - Updates related task status

### Webhook view

```python
class GitHubWebhookView(APIView):
    permission_classes = [AllowAny]  # Auth via HMAC signature
    
    def post(self, request, project_id):
        # Verify signature
        # Parse event
        # Dispatch to handler
```

### Security

- HMAC-SHA256 signature verification — same as GitHub's standard webhook security
- Project-scoped — webhook URL contains project_id, secret is per-department
- Only processes events for projects the webhook was configured for
- Rate-limited to prevent abuse

## 5. Beat Task: monitor_github_workflows

### Cleanup/fallback beat

`monitor_github_workflows` runs every 5 minutes:

1. Finds all agents with `internal_state` containing `pending_github_runs`
2. For each pending run, checks status via GitHub API
3. If completed and no webhook was received (missed event), processes it:
   - Fetches logs
   - Stores in task report
   - Unblocks dependents
4. Cleans up runs older than 1 hour (stale)

### Agent internal_state format

```json
{
    "pending_github_runs": [
        {
            "run_id": 12345,
            "repo": "owner/repo",
            "task_id": "uuid",
            "created_at": "2026-04-04T10:00:00Z"
        }
    ]
}
```

## 6. DEPARTMENTS Registry Update

The `DEPARTMENTS` dict needs to support `config_schema` per department:

```python
DEPARTMENTS = {
    "marketing": {
        "name": "Marketing",
        "description": "...",
        "leader": MarketingLeaderBlueprint(),
        "workforce": {...},
        "config_schema": {},  # No department-level config needed
    },
    "engineering": {
        "name": "Engineering",
        "description": "...",
        "leader": EngineeringLeaderBlueprint(),
        "workforce": {...},
        "config_schema": {
            "github_token": {"type": "str", "required": True, "label": "GitHub Token", ...},
            "github_repos": {"type": "list", "required": True, "label": "Repositories", ...},
            "github_webhook_secret": {"type": "str", "required": False, "label": "Webhook Secret", ...},
        },
    },
}
```

Marketing gets an empty `config_schema` — backward compatible.

## Migration

- Department model: add `config` JSONField (default={})
- Agent model: add `get_config_value()` method (no migration)
- Agent serializer: add `effective_config`, `config_source`
- Integration: create `integrations/github_dev/service.py`
- Webhook: create `projects/views/webhook_view.py`
- Beat: add `monitor_github_workflows` to projects/tasks.py
- Registry: add `config_schema` to DEPARTMENTS entries
- Frontend: update config tab to show inherited values

## Scope

**In scope:**
- Department.config JSONField + config_schema in registry
- Cascading config lookup (agent → department → project)
- Effective config + source in serializer
- GitHub integration service (integrations/github_dev/service.py)
- Webhook endpoint with HMAC verification
- monitor_github_workflows beat task
- Frontend config tab shows inherited values

**Out of scope (spec 2):**
- Engineering department agents (leader, ticket manager, engineers, reviewer)
- Agent bootstrap commands (create project, set up webhooks)
- Claude Code GitHub Action workflow file
- PR management workflows

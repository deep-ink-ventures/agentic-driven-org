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

## 4. Generic Webhook System (in integrations/)

### Architecture

Webhooks are NOT hardwired to GitHub. Each integration that supports webhooks registers an adapter. The system is generic — `github` is just the first adapter.

### URL pattern

```
POST /api/webhooks/{integration_slug}/{project_id}/{webhook_secret}/
```

Examples:
- `POST /api/webhooks/github/abc123/hmac-secret-here/`
- `POST /api/webhooks/sendgrid/abc123/another-secret/`

The secret is in the URL — no database lookup needed for initial auth. The adapter then does its own verification (e.g. GitHub uses HMAC signature on the body, SendGrid uses basic auth).

### Webhook adapter interface

```
integrations/
├── webhooks/
│   ├── __init__.py          # adapter registry
│   ├── base.py              # BaseWebhookAdapter ABC
│   └── adapters/
│       ├── __init__.py
│       └── github.py        # GitHubWebhookAdapter
```

```python
# integrations/webhooks/base.py
class BaseWebhookAdapter(ABC):
    slug: str = ""
    
    @abstractmethod
    def verify(self, request, webhook_secret: str) -> bool:
        """Verify the webhook is authentic."""

    @abstractmethod
    def parse_event(self, request) -> dict:
        """Parse the webhook payload into a normalized event dict."""
        # Returns: {"event_type": "workflow_run.completed", "data": {...}}

    @abstractmethod
    def handle_event(self, project, event: dict) -> None:
        """Process the event — unblock tasks, store logs, etc."""
```

```python
# integrations/webhooks/adapters/github.py
class GitHubWebhookAdapter(BaseWebhookAdapter):
    slug = "github"
    
    def verify(self, request, webhook_secret):
        # HMAC-SHA256 signature verification via X-Hub-Signature-256
        
    def parse_event(self, request):
        # Parse X-GitHub-Event header + JSON body
        
    def handle_event(self, project, event):
        # workflow_run.completed → find pending tasks, fetch logs, unblock
        # pull_request.closed → update task status
```

### Adapter registry

```python
# integrations/webhooks/__init__.py
WEBHOOK_ADAPTERS = {}

def register_adapter(adapter_class):
    WEBHOOK_ADAPTERS[adapter_class.slug] = adapter_class()

def get_adapter(slug):
    return WEBHOOK_ADAPTERS.get(slug)
```

### Generic webhook view

Lives in `integrations/webhooks/views.py`:

```python
class WebhookReceiveView(APIView):
    permission_classes = [AllowAny]  # Auth via adapter.verify()
    
    def post(self, request, integration_slug, project_id, webhook_secret):
        adapter = get_adapter(integration_slug)
        if not adapter:
            return Response(status=404)
        if not adapter.verify(request, webhook_secret):
            return Response(status=403)
        event = adapter.parse_event(request)
        adapter.handle_event(project, event)
        return Response(status=200)
```

### URL routing

```python
# integrations/urls.py
urlpatterns = [
    path("webhooks/<slug:integration_slug>/<uuid:project_id>/<str:webhook_secret>/",
         WebhookReceiveView.as_view(), name="webhook-receive"),
]

# config/urls.py
path("api/", include("integrations.urls")),
```

### Security

- Webhook secret in URL — generated per-project per-integration, stored in department config
- Adapter-specific verification on top (HMAC for GitHub, etc.)
- No database lookup for initial routing — the URL itself contains everything needed

## 5. Beat Task: monitor_pending_webhooks

### Generic cleanup beat — not GitHub-specific

`monitor_pending_webhooks` runs every 5 minutes:

1. Finds all agents with `internal_state` containing `pending_webhook_events`
2. Groups by integration slug
3. For each integration, calls `adapter.check_pending(events)` — the adapter knows how to poll its service
4. If an event completed and no webhook was received, processes it
5. Cleans up events older than 1 hour

### Agent internal_state format (generic)

```json
{
    "pending_webhook_events": [
        {
            "integration": "github",
            "external_id": "12345",
            "repo": "owner/repo",
            "task_id": "uuid",
            "created_at": "2026-04-04T10:00:00Z"
        }
    ]
}
```

### Adapter check_pending method

```python
class BaseWebhookAdapter(ABC):
    # ... existing methods ...
    
    def check_pending(self, events: list[dict], config: dict) -> list[dict]:
        """Check pending events via polling. Returns completed events with results."""
        # Default: return empty (adapter doesn't support polling)
        return []
```

GitHub adapter implements this by calling `get_workflow_run()` for each pending run.

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
- Integration: create `integrations/webhooks/` (base, registry, views, github adapter)
- Integration: create `integrations/urls.py`
- Beat: add `monitor_pending_webhooks` to `integrations/tasks.py`
- Registry: add `config_schema` to DEPARTMENTS entries
- Frontend: update config tab to show inherited values

## Scope

**In scope:**
- Department.config JSONField + config_schema in registry
- Cascading config lookup (agent → department → project)
- Effective config + source in serializer
- GitHub integration service (integrations/github_dev/service.py)
- Generic webhook system in integrations/ (base adapter, registry, view, GitHub adapter)
- integrations/urls.py with webhook routing
- monitor_pending_webhooks beat task (generic, adapter-driven)
- Frontend config tab shows inherited values

**Out of scope (spec 2):**
- Engineering department agents (leader, ticket manager, engineers, reviewer)
- Agent bootstrap commands (create project, set up webhooks)
- Claude Code GitHub Action workflow file
- PR management workflows
- Additional webhook adapters (sendgrid, luma, etc.)

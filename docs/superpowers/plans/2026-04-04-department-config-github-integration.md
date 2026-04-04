# Department Config, Cascading Config & GitHub Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add department-level config with cascading lookup (agent → department → project), GitHub integration service, and generic webhook system with adapter pattern.

**Architecture:** Department model gets `config` JSONField. Agent gets `get_config_value()` cascading method. Webhook system lives in `integrations/webhooks/` with adapter pattern — `github` is the first adapter. Beat task monitors pending webhook events as fallback.

**Tech Stack:** Django, Celery, existing jsonschema validation, requests (for GitHub API)

---

## File Structure

```
backend/
├── projects/models/
│   └── department.py              (modify — add config JSONField)
├── agents/models/
│   └── agent.py                   (modify — add get_config_value)
├── agents/blueprints/
│   └── __init__.py                (modify — add config_schema to DEPARTMENTS)
├── projects/serializers/
│   └── project_detail_serializer.py (modify — add effective_config, config_source, dept config)
├── integrations/
│   ├── urls.py                    (create — webhook routing)
│   ├── tasks.py                   (create — monitor_pending_webhooks beat)
│   ├── github_dev/
│   │   ├── __init__.py            (create)
│   │   └── service.py             (create — GitHub API functions)
│   └── webhooks/
│       ├── __init__.py            (create — adapter registry)
│       ├── base.py                (create — BaseWebhookAdapter ABC)
│       ├── views.py               (create — WebhookReceiveView)
│       └── adapters/
│           ├── __init__.py        (create)
│           └── github.py          (create — GitHubWebhookAdapter)
├── config/
│   ├── urls.py                    (modify — include integrations.urls)
│   └── settings.py                (modify — add beat schedule)
└── frontend/
    ├── lib/types.ts               (modify — add effective_config, config_source)
    └── app/(app)/project/[...path]/page.tsx (modify — config tab inherited values)
```

---

### Task 1: Department model — add config JSONField

**Files:**
- Modify: `backend/projects/models/department.py`

- [ ] **Step 1: Add config field**

Add after `created_at`:

```python
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Department-level config — cascades to agents",
    )
```

- [ ] **Step 2: Run makemigrations and migrate**

```bash
cd backend && source venv/bin/activate && python manage.py makemigrations projects && python manage.py migrate
```

- [ ] **Step 3: Commit**

```bash
git add backend/projects/models/department.py backend/projects/migrations/
git commit -m "feat: Department.config JSONField for department-level configuration"
```

---

### Task 2: DEPARTMENTS registry — add config_schema

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`

- [ ] **Step 1: Add config_schema to marketing department**

Read the file. Add `"config_schema": {},` to the marketing department entry. This makes the format consistent — all departments declare their config schema.

```python
DEPARTMENTS = {
    "marketing": {
        "name": "Marketing",
        "description": "Full-stack marketing — research, social media, email campaigns, content coordination",
        "leader": MarketingLeaderBlueprint(),
        "workforce": {
            "web_researcher": WebResearcherBlueprint(),
            "luma_researcher": LumaResearcherBlueprint(),
            "reddit": RedditBlueprint(),
            "twitter": TwitterBlueprint(),
            "email_marketing": EmailMarketingBlueprint(),
        },
        "config_schema": {},
    },
}
```

Also add a helper function:

```python
def get_department_config_schema(department_type: str) -> dict:
    """Get the config JSON Schema for a department type."""
    dept = DEPARTMENTS.get(department_type)
    if not dept:
        return {}
    schema = dept.get("config_schema", {})
    if not schema:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    # Build JSON Schema from the simple dict format
    from agents.blueprints.base import BaseBlueprint
    properties = {}
    required = []
    for key, spec in schema.items():
        prop = {"description": spec.get("description", ""), "title": spec.get("label", key)}
        t = spec.get("type", "str")
        if t == "str":
            prop["type"] = "string"
        elif t == "list":
            prop["type"] = "array"
        elif t == "dict":
            prop["type"] = "object"
        properties[key] = prop
        if spec.get("required"):
            required.append(key)
    result = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        result["required"] = required
    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/__init__.py
git commit -m "feat: config_schema on DEPARTMENTS registry, get_department_config_schema helper"
```

---

### Task 3: Agent — cascading config lookup

**Files:**
- Modify: `backend/agents/models/agent.py`

- [ ] **Step 1: Add get_config_value method**

Add after `is_action_enabled`:

```python
    def get_config_value(self, key, default=None):
        """Look up config value with cascading: agent → department → project."""
        # Agent level (most specific)
        if key in self.config:
            return self.config[key]
        # Department level
        dept_config = self.department.config or {}
        if key in dept_config:
            return dept_config[key]
        # Project level (most general)
        project_config = self.department.project.config
        if project_config and project_config.config and key in project_config.config:
            return project_config.config[key]
        return default
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/models/agent.py
git commit -m "feat: Agent.get_config_value — cascading lookup agent → department → project"
```

---

### Task 4: Serializer — effective_config and config_source

**Files:**
- Modify: `backend/projects/serializers/project_detail_serializer.py`

- [ ] **Step 1: Add effective_config and config_source to AgentSummarySerializer**

Add fields:

```python
    effective_config = serializers.SerializerMethodField()
    config_source = serializers.SerializerMethodField()
```

Add to `fields` list.

Add methods:

```python
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

- [ ] **Step 2: Add config and config_schema to DepartmentDetailSerializer**

Add fields:

```python
    config = serializers.JSONField(read_only=True)
    config_schema = serializers.SerializerMethodField()
```

Add to `fields` list.

Add method:

```python
    def get_config_schema(self, obj):
        from agents.blueprints import get_department_config_schema
        return get_department_config_schema(obj.department_type)
```

- [ ] **Step 3: Commit**

```bash
git add backend/projects/serializers/project_detail_serializer.py
git commit -m "feat: effective_config + config_source on agents, config + config_schema on departments"
```

---

### Task 5: GitHub integration service

**Files:**
- Create: `backend/integrations/github_dev/__init__.py`
- Create: `backend/integrations/github_dev/service.py`

- [ ] **Step 1: Create service.py**

```python
"""
GitHub integration service.

Provides functions for interacting with GitHub repos, issues, PRs,
projects, and workflow dispatch. All functions are stateless — pass
the token as a parameter. Token comes from agent.get_config_value("github_token").
"""

import hashlib
import hmac
import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_repos(token: str) -> list[dict]:
    """List repos accessible with this token."""
    resp = requests.get(f"{BASE_URL}/user/repos", headers=_headers(token), params={"per_page": 100})
    resp.raise_for_status()
    return [{"full_name": r["full_name"], "private": r["private"], "url": r["html_url"]} for r in resp.json()]


def create_issue(token: str, repo: str, title: str, body: str, labels: list[str] | None = None) -> dict:
    """Create an issue in a repo. repo format: 'owner/repo'."""
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels
    resp = requests.post(f"{BASE_URL}/repos/{repo}/issues", headers=_headers(token), json=data)
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "url": r["html_url"], "id": r["id"]}


def create_pull_request(token: str, repo: str, title: str, body: str, head: str, base: str = "main") -> dict:
    """Create a PR."""
    data = {"title": title, "body": body, "head": head, "base": base}
    resp = requests.post(f"{BASE_URL}/repos/{repo}/pulls", headers=_headers(token), json=data)
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "url": r["html_url"], "id": r["id"]}


def dispatch_workflow(token: str, repo: str, workflow_file: str, ref: str = "main", inputs: dict | None = None) -> dict:
    """Trigger a GitHub Actions workflow via workflow_dispatch."""
    data = {"ref": ref}
    if inputs:
        data["inputs"] = inputs
    resp = requests.post(
        f"{BASE_URL}/repos/{repo}/actions/workflows/{workflow_file}/dispatches",
        headers=_headers(token),
        json=data,
    )
    resp.raise_for_status()
    return {"dispatched": True}


def get_workflow_run(token: str, repo: str, run_id: int) -> dict:
    """Get workflow run status and conclusion."""
    resp = requests.get(f"{BASE_URL}/repos/{repo}/actions/runs/{run_id}", headers=_headers(token))
    resp.raise_for_status()
    r = resp.json()
    return {"id": r["id"], "status": r["status"], "conclusion": r.get("conclusion"), "url": r["html_url"]}


def get_workflow_logs(token: str, repo: str, run_id: int) -> str:
    """Fetch workflow run logs. Returns log text or error message."""
    resp = requests.get(f"{BASE_URL}/repos/{repo}/actions/runs/{run_id}/logs", headers=_headers(token), allow_redirects=True)
    if resp.status_code == 200:
        return resp.text[:50000]  # Cap at 50K chars
    return f"[Failed to fetch logs: {resp.status_code}]"


def get_pr(token: str, repo: str, pr_number: int) -> dict:
    """Get PR details."""
    resp = requests.get(f"{BASE_URL}/repos/{repo}/pulls/{pr_number}", headers=_headers(token))
    resp.raise_for_status()
    r = resp.json()
    return {"number": r["number"], "state": r["state"], "merged": r.get("merged", False), "url": r["html_url"]}


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Create empty `__init__.py`.

- [ ] **Step 2: Commit**

```bash
git add backend/integrations/github_dev/
git commit -m "feat: GitHub integration service — repos, issues, PRs, workflows, webhook verification"
```

---

### Task 6: Generic webhook system

**Files:**
- Create: `backend/integrations/webhooks/__init__.py`
- Create: `backend/integrations/webhooks/base.py`
- Create: `backend/integrations/webhooks/views.py`
- Create: `backend/integrations/webhooks/adapters/__init__.py`
- Create: `backend/integrations/webhooks/adapters/github.py`
- Create: `backend/integrations/urls.py`
- Modify: `backend/config/urls.py`

- [ ] **Step 1: Create base.py — adapter ABC**

```python
"""Base webhook adapter interface."""
from abc import ABC, abstractmethod


class BaseWebhookAdapter(ABC):
    slug: str = ""

    @abstractmethod
    def verify(self, request, webhook_secret: str) -> bool:
        """Verify the webhook is authentic."""

    @abstractmethod
    def parse_event(self, request) -> dict:
        """Parse webhook payload into normalized event dict.
        Returns: {"event_type": "...", "data": {...}}
        """

    @abstractmethod
    def handle_event(self, project, event: dict) -> None:
        """Process the event — unblock tasks, store logs, etc."""

    def check_pending(self, events: list[dict], config: dict) -> list[dict]:
        """Check pending events via polling. Returns completed events with results.
        Default: no polling support.
        """
        return []
```

- [ ] **Step 2: Create webhooks/__init__.py — adapter registry**

```python
"""Webhook adapter registry."""

WEBHOOK_ADAPTERS: dict[str, "BaseWebhookAdapter"] = {}


def register_adapter(adapter_class):
    """Register a webhook adapter by its slug."""
    WEBHOOK_ADAPTERS[adapter_class.slug] = adapter_class()


def get_adapter(slug: str):
    """Get adapter instance by slug, or None."""
    return WEBHOOK_ADAPTERS.get(slug)


# Auto-register adapters
from integrations.webhooks.adapters.github import GitHubWebhookAdapter
register_adapter(GitHubWebhookAdapter)
```

- [ ] **Step 3: Create adapters/github.py**

```python
"""GitHub webhook adapter."""
import logging

from integrations.webhooks.base import BaseWebhookAdapter
from integrations.github_dev import service as github_service

logger = logging.getLogger(__name__)


class GitHubWebhookAdapter(BaseWebhookAdapter):
    slug = "github"

    def verify(self, request, webhook_secret: str) -> bool:
        signature = request.headers.get("X-Hub-Signature-256", "")
        return github_service.verify_webhook_signature(
            request.body, signature, webhook_secret,
        )

    def parse_event(self, request) -> dict:
        event_type = request.headers.get("X-GitHub-Event", "")
        action = request.data.get("action", "")
        return {
            "event_type": f"{event_type}.{action}" if action else event_type,
            "data": request.data,
        }

    def handle_event(self, project, event: dict) -> None:
        from agents.models import Agent, AgentTask

        event_type = event["event_type"]
        data = event["data"]

        if event_type == "workflow_run.completed":
            run_id = data.get("workflow_run", {}).get("id")
            if not run_id:
                return

            # Find agents with this pending run
            agents = Agent.objects.filter(
                department__project=project,
                internal_state__pending_webhook_events__contains=[{"external_id": str(run_id)}],
            )

            for agent in agents:
                pending = agent.internal_state.get("pending_webhook_events", [])
                for evt in pending:
                    if evt.get("external_id") == str(run_id) and evt.get("integration") == "github":
                        task_id = evt.get("task_id")
                        if task_id:
                            try:
                                task = AgentTask.objects.get(id=task_id)
                                # Fetch logs
                                token = agent.get_config_value("github_token")
                                repo = evt.get("repo", "")
                                if token and repo:
                                    logs = github_service.get_workflow_logs(token, repo, run_id)
                                    task.report = logs
                                    task.save(update_fields=["report", "updated_at"])

                                # Remove from pending
                                pending = [e for e in pending if e.get("external_id") != str(run_id)]
                                agent.internal_state["pending_webhook_events"] = pending
                                agent.save(update_fields=["internal_state"])

                                logger.info("GitHub webhook: processed run %s for task %s", run_id, task_id)
                            except AgentTask.DoesNotExist:
                                logger.warning("GitHub webhook: task %s not found", task_id)

    def check_pending(self, events: list[dict], config: dict) -> list[dict]:
        """Poll GitHub for pending workflow runs."""
        token = config.get("github_token")
        if not token:
            return []

        completed = []
        for evt in events:
            repo = evt.get("repo", "")
            run_id = evt.get("external_id")
            if not repo or not run_id:
                continue
            try:
                run = github_service.get_workflow_run(token, repo, int(run_id))
                if run["status"] == "completed":
                    logs = github_service.get_workflow_logs(token, repo, int(run_id))
                    completed.append({**evt, "result": logs, "conclusion": run["conclusion"]})
            except Exception:
                logger.exception("Failed to check GitHub run %s", run_id)

        return completed
```

Create empty `adapters/__init__.py`.

- [ ] **Step 4: Create views.py — generic webhook endpoint**

```python
"""Generic webhook receive endpoint."""
import logging

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.webhooks import get_adapter
from projects.models import Project

logger = logging.getLogger(__name__)


class WebhookReceiveView(APIView):
    """POST /api/webhooks/{integration_slug}/{project_id}/{webhook_secret}/"""
    permission_classes = [AllowAny]
    authentication_classes = []  # No Django auth — adapter handles verification

    def post(self, request, integration_slug, project_id, webhook_secret):
        adapter = get_adapter(integration_slug)
        if not adapter:
            return Response({"error": "Unknown integration"}, status=404)

        if not adapter.verify(request, webhook_secret):
            logger.warning("Webhook verification failed for %s/%s", integration_slug, project_id)
            return Response({"error": "Verification failed"}, status=403)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=404)

        event = adapter.parse_event(request)
        logger.info("Webhook received: %s %s for project %s", integration_slug, event["event_type"], project.name)

        try:
            adapter.handle_event(project, event)
        except Exception:
            logger.exception("Webhook handler failed for %s", integration_slug)

        return Response({"status": "ok"})
```

- [ ] **Step 5: Create integrations/urls.py**

```python
from django.urls import path
from integrations.webhooks.views import WebhookReceiveView

urlpatterns = [
    path(
        "webhooks/<slug:integration_slug>/<uuid:project_id>/<str:webhook_secret>/",
        WebhookReceiveView.as_view(),
        name="webhook-receive",
    ),
]
```

- [ ] **Step 6: Add to config/urls.py**

Read the file. Add after the agents.urls include:

```python
    path("api/", include("integrations.urls")),
```

- [ ] **Step 7: Commit**

```bash
git add backend/integrations/webhooks/ backend/integrations/urls.py backend/config/urls.py
git commit -m "feat: generic webhook system — adapter pattern, GitHub adapter, receive endpoint"
```

---

### Task 7: Beat task — monitor_pending_webhooks

**Files:**
- Create: `backend/integrations/tasks.py`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Create integrations/tasks.py**

```python
"""Integration beat tasks."""
import logging
from collections import defaultdict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def monitor_pending_webhooks():
    """
    Every 5 minutes: check for pending webhook events that may have been missed.
    Groups events by integration, calls adapter.check_pending() for each.
    """
    from datetime import timedelta
    from django.utils import timezone
    from agents.models import Agent, AgentTask
    from integrations.webhooks import get_adapter

    now = timezone.now()
    stale_cutoff = now - timedelta(hours=1)

    # Find all agents with pending webhook events
    agents = Agent.objects.exclude(internal_state={}).filter(
        internal_state__has_key="pending_webhook_events",
    )

    for agent in agents:
        pending = agent.internal_state.get("pending_webhook_events", [])
        if not pending:
            continue

        # Group by integration
        by_integration = defaultdict(list)
        for evt in pending:
            by_integration[evt.get("integration", "")].append(evt)

        updated = False
        remaining = []

        for integration_slug, events in by_integration.items():
            adapter = get_adapter(integration_slug)
            if not adapter:
                remaining.extend(events)
                continue

            # Build config from agent's cascading lookup
            config = {}
            for key in ["github_token", "github_repos"]:
                val = agent.get_config_value(key)
                if val:
                    config[key] = val

            completed = adapter.check_pending(events, config)
            completed_ids = {e.get("external_id") for e in completed}

            for evt in events:
                if evt.get("external_id") in completed_ids:
                    # Process completed event
                    task_id = evt.get("task_id")
                    result = next((c for c in completed if c.get("external_id") == evt.get("external_id")), {})
                    if task_id:
                        try:
                            task = AgentTask.objects.get(id=task_id)
                            if result.get("result"):
                                task.report = result["result"]
                                task.save(update_fields=["report", "updated_at"])
                            logger.info("Beat monitor: processed %s event %s for task %s",
                                        integration_slug, evt.get("external_id"), task_id)
                        except AgentTask.DoesNotExist:
                            pass
                    updated = True
                elif evt.get("created_at"):
                    # Check if stale
                    from django.utils.dateparse import parse_datetime
                    created = parse_datetime(evt["created_at"])
                    if created and created < stale_cutoff:
                        logger.warning("Beat monitor: stale %s event %s — removing", integration_slug, evt.get("external_id"))
                        updated = True
                    else:
                        remaining.append(evt)
                else:
                    remaining.append(evt)

        if updated:
            agent.internal_state["pending_webhook_events"] = remaining
            agent.save(update_fields=["internal_state"])
```

- [ ] **Step 2: Add to beat schedule**

In `backend/config/settings.py`, add to `CELERY_BEAT_SCHEDULE`:

```python
    "monitor-pending-webhooks": {
        "task": "integrations.tasks.monitor_pending_webhooks",
        "schedule": 300,  # every 5 minutes
    },
```

- [ ] **Step 3: Commit**

```bash
git add backend/integrations/tasks.py backend/config/settings.py
git commit -m "feat: monitor_pending_webhooks beat task — generic fallback for missed webhook events"
```

---

### Task 8: Frontend — config tab shows inherited values

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/app/(app)/project/[...path]/page.tsx`

- [ ] **Step 1: Update types**

Add to `AgentSummary` interface:

```typescript
  effective_config: Record<string, unknown>;
  config_source: Record<string, string>;
```

Add to `DepartmentDetail` interface:

```typescript
  config: Record<string, unknown>;
  config_schema: Record<string, unknown>;
```

- [ ] **Step 2: Update AgentConfigEditor**

In the config fields section, show the effective value as placeholder when the agent doesn't have its own value. Show source label for inherited values.

For each config field input, change the value and add a helper label:

```tsx
<Input
    value={
      config[key] == null
        ? ""
        : typeof config[key] === "string"
          ? (config[key] as string)
          : JSON.stringify(config[key])
    }
    placeholder={
      agent.effective_config[key] != null
        ? `${agent.effective_config[key]} (from ${agent.config_source[key] || "inherited"})`
        : spec.title || key
    }
    onChange={(e) => setConfig({ ...config, [key]: e.target.value })}
    className="bg-bg-input border-border text-text-primary text-xs font-mono"
/>
{agent.config_source[key] && agent.config_source[key] !== "agent" && !(key in config) && (
    <p className="text-[10px] text-accent-gold mt-0.5">
        Inherited from {agent.config_source[key]}
    </p>
)}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
cd ../backend && source venv/bin/activate && python manage.py check
```

- [ ] **Step 4: Commit**

```bash
git add frontend/ backend/
git commit -m "feat: config tab shows inherited values with source labels"
```

---

### Task 9: Verify

- [ ] **Step 1: Run tests**

```bash
cd backend && source venv/bin/activate && python -m pytest -q
```

- [ ] **Step 2: Django check**

```bash
python manage.py check
```

- [ ] **Step 3: Celery discovers tasks**

```bash
celery -A config worker --loglevel=info
```

Should discover: `monitor_pending_webhooks` + all existing tasks.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete department config, cascading config, GitHub integration, webhook system"
```

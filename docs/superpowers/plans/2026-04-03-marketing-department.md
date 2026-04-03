# Marketing Department Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the social_media department with a comprehensive marketing department — 5 workforce agents, leader, 6 integration services.

**Architecture:** Three phases: (1) restructure integrations into service folders, (2) build the marketing department blueprints, (3) migrate from social_media and update registry/tests. Each integration is a service.py with a clean interface. Agents call services, never touch APIs or secrets.

**Tech Stack:** Django, Celery, existing Claude AI client, Playwright (via service), SendGrid API, Google APIs

---

## Phase 1: Integration Services

### Task 1: Restructure integrations into service folders

**Files:**
- Delete: `backend/integrations/browser.py`
- Delete: `backend/integrations/google.py`
- Create: `backend/integrations/playwright/__init__.py`
- Create: `backend/integrations/playwright/service.py`
- Create: `backend/integrations/websearch/__init__.py`
- Create: `backend/integrations/websearch/service.py`
- Create: `backend/integrations/sendgrid/__init__.py`
- Create: `backend/integrations/sendgrid/service.py`
- Create: `backend/integrations/gmail/__init__.py`
- Create: `backend/integrations/gmail/service.py`
- Create: `backend/integrations/gdrive/__init__.py`
- Create: `backend/integrations/gdrive/service.py`
- Create: `backend/integrations/luma/__init__.py`
- Create: `backend/integrations/luma/service.py`

- [ ] **Step 1: Create playwright/service.py**

```python
"""
Playwright browser automation service.

Used by agents that interact with web platforms (Twitter, Reddit, Lu.ma).
The underlying automation tool is configured per deployment.
"""

import json
import logging

logger = logging.getLogger(__name__)


def run_action(action_type: str, params: dict, agent_config: dict) -> dict:
    """
    Execute a browser action.

    Args:
        action_type: e.g. "navigate", "click", "type", "post", "reply"
        params: Action-specific parameters
        agent_config: Agent's config (browser cookies, session data)

    Returns:
        dict with "success" bool and "result" or "error"
    """
    logger.info("Playwright action: %s params=%s", action_type, json.dumps(params)[:200])

    try:
        logger.info("Would execute: %s", action_type)
        return {"success": True, "result": f"Executed {action_type}", "action_type": action_type}
    except Exception as e:
        logger.exception("Playwright action failed: %s", action_type)
        return {"success": False, "error": str(e)}
```

Create empty `playwright/__init__.py`.

- [ ] **Step 2: Create websearch/service.py**

```python
"""
Web search service.

Wraps web search for consistency. All agents that need to search the web
call this service rather than implementing search themselves.
"""

import logging

logger = logging.getLogger(__name__)


def search(query: str, num_results: int = 10) -> list[dict]:
    """
    Search the web.

    Args:
        query: Search query string
        num_results: Max results to return

    Returns:
        list of dicts: [{title, url, snippet}]
    """
    logger.info("Web search: query='%s', num_results=%d", query, num_results)

    # Stub: will be implemented with actual search API or Claude's built-in search
    return []
```

Create empty `websearch/__init__.py`.

- [ ] **Step 3: Create sendgrid/service.py**

```python
"""
SendGrid email service.

Handles email campaign sending and analytics via the SendGrid API.
Secrets are read from agent.config — never passed by the agent blueprint.
"""

import logging

logger = logging.getLogger(__name__)


def send_campaign(api_key: str, from_email: str, to_list_id: str, subject: str, html_body: str) -> dict:
    """
    Send an email campaign via SendGrid.

    Args:
        api_key: SendGrid API key (from agent.config)
        from_email: Sender email address
        to_list_id: SendGrid contact list ID
        subject: Email subject line
        html_body: Email body as HTML

    Returns:
        dict with "success" bool and "campaign_id" or "error"
    """
    logger.info("SendGrid send_campaign: from=%s, list=%s, subject='%s'", from_email, to_list_id, subject[:50])

    # Stub: actual implementation will use sendgrid Python SDK
    return {"success": True, "campaign_id": "stub", "from": from_email, "to_list": to_list_id}


def get_campaign_stats(api_key: str, campaign_id: str) -> dict:
    """
    Get campaign performance statistics.

    Returns:
        dict with "success", "opens", "clicks", "unsubscribes", "bounces"
    """
    logger.info("SendGrid get_campaign_stats: campaign=%s", campaign_id)

    return {"success": True, "opens": 0, "clicks": 0, "unsubscribes": 0, "bounces": 0}


def list_contacts(api_key: str, list_id: str) -> dict:
    """
    List contacts in a SendGrid mailing list.

    Returns:
        dict with "success", "count", "contacts" list
    """
    logger.info("SendGrid list_contacts: list=%s", list_id)

    return {"success": True, "count": 0, "contacts": []}
```

Create empty `sendgrid/__init__.py`.

- [ ] **Step 4: Create gmail/service.py**

```python
"""
Gmail service via Google Workspace API.

Secrets are read from ProjectConfig.google_credentials.
"""

import logging

logger = logging.getLogger(__name__)


def _get_config(project):
    config = project.config
    if not config or not config.google_email:
        return None, None
    return config.google_email, config.google_credentials


def send_email(project, to: str, subject: str, body: str) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("Gmail send: from=%s to=%s subject='%s'", email, to, subject[:50])
    return {"success": True, "message_id": "stub", "from": email, "to": to}


def read_emails(project, query: str = "", max_results: int = 10) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("Gmail read: account=%s query='%s'", email, query)
    return {"success": True, "emails": []}
```

Create empty `gmail/__init__.py`.

- [ ] **Step 5: Create gdrive/service.py**

```python
"""
Google Drive service via Google Workspace API.

Secrets are read from ProjectConfig.google_credentials.
"""

import logging

logger = logging.getLogger(__name__)


def _get_config(project):
    config = project.config
    if not config or not config.google_email:
        return None, None
    return config.google_email, config.google_credentials


def list_files(project, folder_id: str = "root", max_results: int = 20) -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("GDrive list: account=%s folder=%s", email, folder_id)
    return {"success": True, "files": []}


def upload_file(project, name: str, content: bytes, folder_id: str = "root") -> dict:
    email, credentials = _get_config(project)
    if not email:
        return {"success": False, "error": "No Google config on project"}

    logger.info("GDrive upload: account=%s name=%s folder=%s", email, name, folder_id)
    return {"success": True, "file_id": "stub"}
```

Create empty `gdrive/__init__.py`.

- [ ] **Step 6: Create luma/service.py**

```python
"""
Lu.ma event platform service.

Queries Lu.ma calendars for upcoming events. Uses Playwright internally
for browser automation since Lu.ma has no public API worth using.
"""

import logging

logger = logging.getLogger(__name__)


def query_events(calendar_urls: list[str], days_ahead: int = 30) -> list[dict]:
    """
    Query Lu.ma calendars for upcoming events.

    Args:
        calendar_urls: List of Lu.ma calendar URLs to scan
        days_ahead: How far ahead to look

    Returns:
        list of dicts: [{title, url, date, description, speakers}]
    """
    logger.info("Lu.ma query_events: %d calendars, %d days ahead", len(calendar_urls), days_ahead)

    # Stub: will use playwright service internally to browse Lu.ma
    return []


def get_event_details(event_url: str) -> dict:
    """
    Get detailed information about a specific Lu.ma event.

    Returns:
        dict with title, date, description, speakers, attendee_count, location
    """
    logger.info("Lu.ma get_event_details: %s", event_url)

    return {"success": True, "title": "", "date": "", "description": "", "speakers": [], "attendee_count": 0}
```

Create empty `luma/__init__.py`.

- [ ] **Step 7: Delete old files and update any imports**

```bash
rm backend/integrations/browser.py backend/integrations/google.py
```

Update any existing code that imports from old locations. Search for:
- `from integrations.browser import` → `from integrations.playwright.service import`
- `from integrations.google import` → split into gmail/gdrive as needed

The twitter and reddit agent.py files import `from integrations.browser import run_browser_action` — these will be replaced in Phase 2, so for now just ensure the old files are gone and nothing else imports them.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: restructure integrations into service folders (playwright, websearch, sendgrid, gmail, gdrive, luma)"
```

---

## Phase 2: Marketing Department Blueprints

### Task 2: Marketing department — leader blueprint

**Files:**
- Create: `backend/agents/blueprints/marketing/__init__.py`
- Create: `backend/agents/blueprints/marketing/leader/__init__.py`
- Create: `backend/agents/blueprints/marketing/leader/agent.py`
- Create: `backend/agents/blueprints/marketing/leader/skills/__init__.py`
- Create: `backend/agents/blueprints/marketing/leader/skills/analyze_performance.py`
- Create: `backend/agents/blueprints/marketing/leader/skills/design_campaigns.py`
- Create: `backend/agents/blueprints/marketing/leader/skills/content_calendar.py`
- Create: `backend/agents/blueprints/marketing/leader/skills/prioritize_tasks.py`
- Create: `backend/agents/blueprints/marketing/leader/commands/__init__.py`
- Create: `backend/agents/blueprints/marketing/leader/commands/create_priority_task.py`
- Create: `backend/agents/blueprints/marketing/leader/commands/create_campaign.py`
- Create: `backend/agents/blueprints/marketing/leader/commands/create_content_calendar.py`
- Create: `backend/agents/blueprints/marketing/leader/commands/analyze_performance.py`
- Create: `backend/agents/blueprints/marketing/workforce/__init__.py`

- [ ] **Step 1: Create marketing/__init__.py**

```python
"""Marketing department blueprint."""

DEPARTMENT_NAME = "Marketing"
DEPARTMENT_DESCRIPTION = "Full-stack marketing — research, social media, email campaigns, content coordination"
```

- [ ] **Step 2: Create leader skills (4 files)**

Each skill file follows the pattern: `NAME = "..."` and `DESCRIPTION = "..."`.

`skills/__init__.py` — same auto-discovery pattern as existing:
```python
"""Marketing leader skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`skills/analyze_performance.py`:
```python
NAME = "Analyze Performance"
DESCRIPTION = "Compile reports from all agents, identify what's working, flag underperformers, suggest strategy adjustments"
```

`skills/design_campaigns.py`:
```python
NAME = "Design Campaigns"
DESCRIPTION = "Create multi-channel campaigns with consistent branding, timing, and channel-appropriate messaging"
```

`skills/content_calendar.py`:
```python
NAME = "Content Calendar"
DESCRIPTION = "Plan coordinated content across all channels with day-by-day schedule and specific briefs"
```

`skills/prioritize_tasks.py`:
```python
NAME = "Prioritize Tasks"
DESCRIPTION = "Analyze workforce activity and propose the highest-value next action based on project goals and ROI"
```

- [ ] **Step 3: Create leader commands (4 files)**

`commands/__init__.py`:
```python
"""Marketing leader commands registry."""
from .create_priority_task import create_priority_task
from .create_campaign import create_campaign
from .create_content_calendar import create_content_calendar
from .analyze_performance import analyze_performance

ALL_COMMANDS = [create_priority_task, create_campaign, create_content_calendar, analyze_performance]
```

`commands/create_priority_task.py` — adapted from social_media leader but with awareness of all 5 workforce types:
```python
"""Leader command: propose the highest-value next task for any workforce agent."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-priority-task", description="Propose the highest-value next task for a workforce agent", schedule="hourly")
def create_priority_task(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude
    from agents.models import AgentTask

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("id", "name", "agent_type")
    )
    if not workforce:
        return {"exec_summary": "No workforce agents in department", "step_plan": ""}

    workforce_desc = "\n".join(f"- {name} ({atype})" for _, name, atype in workforce)

    awaiting_by_agent = {}
    for wid, wname, wtype in workforce:
        count = AgentTask.objects.filter(agent_id=wid, status=AgentTask.Status.AWAITING_APPROVAL).count()
        awaiting_by_agent[wname] = count

    awaiting_text = "\n".join(f"- {name}: {count} tasks awaiting" for name, count in awaiting_by_agent.items())

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Current Approval Queue
{awaiting_text}

# Task
Propose the single highest-value task for one of the workforce agents above. Consider:
- Recent research findings (web researcher, lu.ma researcher)
- Current campaign status and messaging
- Engagement metrics and timing
- Project goal alignment

Include clear branding and tone instructions in the task. Specify timing if relevant.

Respond with JSON:
{{
    "target_agent_type": "one of: web_researcher, luma_researcher, reddit, twitter, email_marketing",
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan with branding/tone guidance"
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        data = json.loads(response)
        return {
            "target_agent_type": data.get("target_agent_type"),
            "exec_summary": data.get("exec_summary", "Priority task"),
            "step_plan": data.get("step_plan", response),
        }
    except (json.JSONDecodeError, KeyError):
        return {"exec_summary": "Priority task", "step_plan": response}
```

`commands/create_campaign.py`:
```python
"""Leader command: design a multi-channel campaign."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-campaign", description="Design a multi-channel campaign with coordinated tasks for workforce agents")
def create_campaign(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("name", "agent_type")
    )
    workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task
Design a multi-channel marketing campaign for this project. Create specific, coordinated tasks for the workforce agents.

For each task include:
- Clear branding and tone instructions
- Channel-appropriate messaging (professional for email, value-add for Reddit, engaging for Twitter)
- Specific timing (stagger across channels for maximum impact)
- What to link to and what angle to take

Also schedule a follow-up review task for yourself 30 days from now to assess campaign performance.

Respond with JSON:
{{
    "campaign_name": "Name of the campaign",
    "campaign_summary": "Brief strategy and rationale",
    "tasks": [
        {{
            "target_agent_type": "web_researcher",
            "exec_summary": "Research task for campaign preparation",
            "step_plan": "Detailed steps",
            "auto_execute": true
        }},
        {{
            "target_agent_type": "twitter",
            "exec_summary": "Twitter task with timing and messaging",
            "step_plan": "Detailed steps with branding guidance",
            "proposed_exec_at": "ISO datetime or null for immediate"
        }}
    ],
    "follow_up": {{
        "exec_summary": "Review campaign performance and adjust strategy",
        "days_from_now": 30
    }}
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        data = json.loads(response)
        return {
            "campaign_name": data.get("campaign_name", "Campaign"),
            "campaign_summary": data.get("campaign_summary", response),
            "tasks": data.get("tasks", []),
            "follow_up": data.get("follow_up"),
        }
    except (json.JSONDecodeError, KeyError):
        return {"campaign_name": "Campaign", "campaign_summary": response, "tasks": []}
```

`commands/create_content_calendar.py`:
```python
"""Leader command: plan a week of coordinated content."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-content-calendar", description="Plan a week of coordinated content across all channels")
def create_content_calendar(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("name", "agent_type")
    )
    workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task
Create a content calendar for the next 7 days. For each day, specify what each active agent should do.

Consider:
- Optimal posting times per channel
- Consistent messaging across channels
- Mix of content types (engagement, original content, research)
- Current campaign priorities

Respond with JSON:
{{
    "calendar_summary": "Overview of the week's strategy",
    "days": [
        {{
            "day": "Monday",
            "tasks": [
                {{
                    "target_agent_type": "twitter",
                    "exec_summary": "What to post",
                    "step_plan": "Detailed brief with tone/branding",
                    "proposed_exec_at": "ISO datetime"
                }}
            ]
        }}
    ]
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        data = json.loads(response)
        return {
            "calendar_summary": data.get("calendar_summary", response),
            "days": data.get("days", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {"calendar_summary": response, "days": []}
```

`commands/analyze_performance.py`:
```python
"""Leader command: compile performance reports from all agents."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="analyze-performance", description="Compile reports from all agents, identify what's working, adjust strategy")
def analyze_performance(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Task
Analyze the department's recent performance based on all agents' task reports. Identify:
1. What campaigns/content performed well and why
2. What underperformed and what to change
3. Strategic recommendations for next period
4. Specific tasks to create for improvement

Respond with JSON:
{{
    "performance_summary": "Overview of department performance",
    "wins": ["What worked well"],
    "issues": ["What needs improvement"],
    "recommendations": ["Strategic suggestions"],
    "proposed_tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "Task to improve performance",
            "step_plan": "Detailed steps"
        }}
    ]
}}"""

    response = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
    )

    try:
        return json.loads(response)
    except (json.JSONDecodeError, KeyError):
        return {"performance_summary": response, "wins": [], "issues": [], "recommendations": [], "proposed_tasks": []}
```

- [ ] **Step 4: Create leader/agent.py**

```python
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from django.utils import timezone

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.marketing.leader.skills import format_skills
from agents.blueprints.marketing.leader.commands import (
    create_priority_task,
    create_campaign,
    create_content_calendar,
    analyze_performance,
)

logger = logging.getLogger(__name__)


class MarketingLeaderBlueprint(LeaderBlueprint):
    name = "Marketing Leader"
    slug = "leader"
    description = "Marketing department leader — orchestrates campaigns, coordinates research and execution across all channels"
    tags = ["leadership", "strategy", "campaigns", "coordination", "marketing"]

    @property
    def system_prompt(self) -> str:
        return """You are the marketing department leader. You orchestrate multi-channel marketing campaigns by coordinating your workforce agents: Web Researcher, Lu.ma Researcher, Reddit Specialist, Twitter Specialist, and Email Marketing Specialist.

Your core responsibilities:
1. Gather intelligence from research agents before making campaign decisions
2. Design campaigns with consistent branding, tone, and timing across all channels
3. Create tasks with clear instructions about messaging, angle, and what to link to
4. Schedule follow-up tasks to revisit campaigns and adjust strategy
5. Monitor performance and reallocate effort to what's working

You don't post directly — you create tasks for your workforce. Each task you create should include:
- Clear branding and tone guidance
- Channel-appropriate messaging
- Specific timing recommendations
- What angle to take and what to drive traffic toward

When creating campaigns, stagger content across channels for maximum impact. Research first, then execute."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    create_priority_task = create_priority_task
    create_campaign = create_campaign
    create_content_calendar = create_content_calendar
    analyze_performance = analyze_performance

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel, AgentTask as TaskModel

        workforce = list(
            agent.department.agents.filter(is_active=True, is_leader=False)
            .values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        delegation_suffix = f"""# Workforce Agents
{workforce_desc}

If this task involves delegating work to workforce agents, include delegated_tasks in your response.
If this task should be revisited later, include a follow_up with days_from_now.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed steps with branding/tone guidance",
            "auto_execute": false,
            "proposed_exec_at": "ISO datetime or null"
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 30
    }},
    "report": "Summary of what was decided and why"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=delegation_suffix)

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)
            follow_up = data.get("follow_up")

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department,
                    is_active=True,
                    is_leader=False,
                )
                agents_by_type = {a.agent_type: a for a in workforce_agents}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = agents_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active workforce agent of type %s", target_type)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED if dt.get("auto_execute") else TaskModel.Status.AWAITING_APPROVAL,
                        auto_execute=bool(dt.get("auto_execute")),
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )

                    if dt.get("auto_execute"):
                        from agents.tasks import execute_agent_task
                        execute_agent_task.delay(str(sub_task.id))

                    logger.info("Leader delegated task %s to %s", sub_task.id, target_agent.name)

            # Schedule follow-up if requested
            if follow_up and follow_up.get("days_from_now"):
                days = follow_up["days_from_now"]
                TaskModel.objects.create(
                    agent=agent,
                    status=TaskModel.Status.AWAITING_APPROVAL,
                    exec_summary=follow_up.get("exec_summary", f"Follow-up in {days} days"),
                    step_plan=f"Review and assess. Original task: {task.exec_summary[:200]}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )
                logger.info("Leader scheduled follow-up in %d days", days)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.create_priority_task(agent)
```

Create `leader/__init__.py`:
```python
from .agent import MarketingLeaderBlueprint

__all__ = ["MarketingLeaderBlueprint"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/marketing/leader/ backend/agents/blueprints/marketing/__init__.py backend/agents/blueprints/marketing/workforce/__init__.py
git commit -m "feat: marketing department leader blueprint with 4 commands"
```

---

### Task 3: Marketing workforce — web_researcher + luma_researcher

**Files:** Create the full skill/command/agent structure for both research agents.

- [ ] **Step 1: Create web_researcher blueprint**

Follow the established pattern. Agent uses `integrations.websearch.service`. No config needed.

`agent.py` system prompt emphasizes: return structured findings with URLs, relevance scores, and suggested angles. Connect findings to project goal.

Skills: `search_trends.py`, `research_competitors.py`, `find_opportunities.py`
Commands: `research_trends.py` (hourly), `research_competitors.py` (daily), `find_content_opportunities.py` (on-demand)

Tags: `["research", "intelligence", "trends"]`

Commands return `{exec_summary, step_plan}` — the actual web search happens in `execute_task` which calls `websearch.service.search()`.

- [ ] **Step 2: Create luma_researcher blueprint**

Agent uses `integrations.luma.service`. Config: `{"calendar_urls": [...]}`.

Skills: `query_calendars.py`, `extract_event_details.py`, `identify_opportunities.py`
Commands: `scan_events.py` (daily), `find_opportunities.py` (on-demand)

Tags: `["research", "events", "networking"]`

`execute_task` reads `agent.config["calendar_urls"]` and calls `luma.service.query_events()`.

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/marketing/workforce/web_researcher/ backend/agents/blueprints/marketing/workforce/luma_researcher/
git commit -m "feat: web_researcher and luma_researcher workforce agents"
```

---

### Task 4: Marketing workforce — reddit + twitter (strategic placement)

**Files:** Create full blueprint packages for both social agents.

- [ ] **Step 1: Create reddit blueprint**

Agent uses `integrations.playwright.service`. Config: `{"reddit_username": "...", "reddit_session": "..."}`.

Tags: `["social-media", "reddit", "placement", "brand-visibility"]`

Skills: `find_trending_posts.py`, `strategic_placement.py`, `monitor_mentions.py`
Commands:
- `place_content.py` (hourly) — find ONE high-performing post, add ONE strategic comment that angles toward the project. No discussions, no replies to replies.
- `post_content.py` (daily) — share one valuable piece of content in an appropriate subreddit.
- `monitor_mentions.py` (on-demand)

System prompt MUST include these hard rules:
```
ENGAGEMENT RULES — NON-NEGOTIABLE:
- NEVER engage in discussions or answer questions
- NEVER reply to replies on your own posts
- ONE post per trending thread, then move on
- Content must provide genuine value while strategically angling toward the project
- Check internal_state.last_post_at per subreddit — minimum 4 hours between posts in same subreddit
- All placements must align with current campaign messaging from department documents
```

`execute_task` calls `playwright.service.run_action()` and updates `agent.internal_state` with posting timestamps.

- [ ] **Step 2: Create twitter blueprint**

Same pattern as reddit but for Twitter. Config: `{"twitter_session": "..."}`.

Tags: `["social-media", "twitter", "placement", "content-creation"]`

Skills: `find_trending_tweets.py`, `strategic_placement.py`, `post_content.py`
Commands:
- `place_content.py` (hourly) — find trending tweet, add ONE strategic reply/quote tweet.
- `post_content.py` (daily) — post one original tweet at optimal time.
- `search_trends.py` (on-demand)

Same engagement rules as reddit but Twitter-specific (no reply chains, no threads in response).

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/marketing/workforce/reddit/ backend/agents/blueprints/marketing/workforce/twitter/
git commit -m "feat: reddit and twitter workforce agents with strategic placement rules"
```

---

### Task 5: Marketing workforce — email_marketing

**Files:** Create full blueprint package.

- [ ] **Step 1: Create email_marketing blueprint**

Agent uses `integrations.sendgrid.service`. Config: `{"sendgrid_api_key": "...", "default_from_email": "...", "mailing_lists": {"newsletter": "list-id", "leads": "list-id"}}`.

Tags: `["email", "campaigns", "outreach", "nurture"]`

Skills: `design_campaigns.py`, `segment_audience.py`, `schedule_sends.py`, `analyze_performance.py`
Commands:
- `check_campaign_performance.py` (daily) — calls `sendgrid.service.get_campaign_stats()`
- `draft_campaign.py` (on-demand) — creates campaign draft with A/B subject lines. ALWAYS creates task as `awaiting_approval`.
- `send_campaign.py` (on-demand) — calls `sendgrid.service.send_campaign()`. Only runs after explicit approval.

System prompt MUST include:
```
EMAIL SAFETY RULES — NON-NEGOTIABLE:
- NEVER send emails without explicit human approval
- Draft commands ALWAYS create tasks in awaiting_approval status
- Track last_campaign_sent_at in internal_state — minimum 3 days between campaigns to same list
- Track emails_sent_this_week in internal_state
- All campaigns MUST include unsubscribe link
- Subject lines MUST include 2-3 A/B options
- Optimal send times: Tuesday/Thursday 10am local time
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/marketing/workforce/email_marketing/
git commit -m "feat: email_marketing workforce agent with safety rules"
```

---

## Phase 3: Migration & Wiring

### Task 6: Update registry, delete social_media, migration

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`
- Delete: `backend/agents/blueprints/social_media/` (entire directory)
- Create: `backend/projects/migrations/0005_...` (rename social_media → marketing)

- [ ] **Step 1: Replace blueprints/__init__.py**

```python
"""
Blueprint registry.

Departments and their agents are defined by the folder structure:
  blueprints/<department_type>/leader/
  blueprints/<department_type>/workforce/<agent_type>/
"""

from agents.blueprints.marketing.leader import MarketingLeaderBlueprint
from agents.blueprints.marketing.workforce.web_researcher import WebResearcherBlueprint
from agents.blueprints.marketing.workforce.luma_researcher import LumaResearcherBlueprint
from agents.blueprints.marketing.workforce.reddit import RedditBlueprint
from agents.blueprints.marketing.workforce.twitter import TwitterBlueprint
from agents.blueprints.marketing.workforce.email_marketing import EmailMarketingBlueprint

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
    },
}

DEPARTMENT_TYPE_CHOICES = [
    (slug, dept["name"]) for slug, dept in DEPARTMENTS.items()
]

AGENT_TYPE_CHOICES = [("leader", "Department Leader")]
for dept in DEPARTMENTS.values():
    for slug, bp in dept["workforce"].items():
        if (slug, bp.name) not in AGENT_TYPE_CHOICES:
            AGENT_TYPE_CHOICES.append((slug, bp.name))

WORKFORCE_TYPE_CHOICES = [c for c in AGENT_TYPE_CHOICES if c[0] != "leader"]


def get_department(department_type: str) -> dict:
    dept = DEPARTMENTS.get(department_type)
    if dept is None:
        raise ValueError(f"Unknown department type: {department_type}")
    return dept


def get_blueprint(agent_type: str, department_type: str | None = None):
    if agent_type == "leader":
        if department_type is None:
            raise ValueError("department_type required for leader blueprint lookup")
        dept = get_department(department_type)
        return dept["leader"]

    if department_type:
        dept = get_department(department_type)
        bp = dept["workforce"].get(agent_type)
        if bp is None:
            raise ValueError(f"Agent type '{agent_type}' not available in department '{department_type}'")
        return bp

    for dept in DEPARTMENTS.values():
        bp = dept["workforce"].get(agent_type)
        if bp is not None:
            return bp

    raise ValueError(f"Unknown agent type: {agent_type}")


def get_workforce_for_department(department_type: str) -> dict:
    dept = get_department(department_type)
    return dept["workforce"]
```

- [ ] **Step 2: Delete social_media directory**

```bash
rm -rf backend/agents/blueprints/social_media/
```

- [ ] **Step 3: Create data migration**

Create `backend/projects/migrations/0005_social_media_to_marketing.py`:

```python
"""Rename department_type social_media -> marketing."""

from django.db import migrations


def forwards(apps, schema_editor):
    Department = apps.get_model("projects", "Department")
    Department.objects.filter(department_type="social_media").update(department_type="marketing")


def backwards(apps, schema_editor):
    Department = apps.get_model("projects", "Department")
    Department.objects.filter(department_type="marketing").update(department_type="social_media")


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0004_department_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
```

- [ ] **Step 4: Update Department model default**

In `backend/projects/models/department.py`, change `default="social_media"` to `default="marketing"`.

- [ ] **Step 5: Run migration**

```bash
cd backend && source venv/bin/activate && python manage.py migrate
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: replace social_media with marketing department, update registry, data migration"
```

---

### Task 7: Update tests

**Files:**
- Modify: `backend/agents/tests/test_blueprints.py`
- Modify: `backend/agents/tests/test_models.py`
- Modify: `backend/agents/tests/test_tasks.py`
- Modify: `backend/projects/tests/test_prompts.py`

- [ ] **Step 1: Update all test fixtures and assertions**

Key changes across all test files:
- `department_type="social_media"` → `department_type="marketing"`
- `agent_type="twitter"` stays (twitter is still a valid type in marketing)
- Import paths: `agents.blueprints.social_media.workforce.twitter...` → `agents.blueprints.marketing.workforce.twitter...`
- Blueprint registry tests: verify `DEPARTMENTS["marketing"]` exists, contains all 5 workforce types
- `AGENT_TYPE_CHOICES` now includes `web_researcher`, `luma_researcher`, `email_marketing` in addition to `twitter`, `reddit`
- `WORKFORCE_TYPE_CHOICES` excludes leader, includes all 5

- [ ] **Step 2: Run tests and fix any remaining failures**

```bash
python -m pytest -x -q
```

Fix any import errors or assertion mismatches.

- [ ] **Step 3: Commit**

```bash
git add backend/agents/tests/ backend/projects/tests/
git commit -m "test: update all tests for marketing department migration"
```

---

### Task 8: Update bootstrap prompt for marketing department

**Files:**
- Modify: `backend/projects/prompts.py` — update prompt rules (no more "campaign agent" references)
- Modify: `backend/projects/tasks.py` — verify department info is passed correctly

- [ ] **Step 1: Update bootstrap system prompt**

In `BOOTSTRAP_SYSTEM_PROMPT`, update rule 8 from "Leaders are auto-created" to also mention the marketing-specific agent types.

- [ ] **Step 2: Run full test suite**

```bash
python -m pytest -q
```

- [ ] **Step 3: Run Django check + Celery discovery**

```bash
python manage.py check
celery -A config worker --loglevel=info  # verify 3 tasks discovered
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete marketing department — 5 workforce agents, leader, 6 integration services"
```

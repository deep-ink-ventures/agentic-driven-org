# Leader/Workforce Agent Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the agent hierarchy (superior FK) with a leader/workforce model where each department has exactly one leader agent that proposes and delegates tasks, and workforce agents that only execute.

**Architecture:** Remove `superior` FK from Agent, add `is_leader` boolean with unique constraint per department. Leader blueprint has commands (Python methods with metadata). When a leader task is approved (queued), it auto-triggers a new `create-priority-task` command to propose the next task — self-perpetuating chain. Remove campaign blueprint (campaign becomes a leader command). Remove `refill_approval_queue` beat task.

**Tech Stack:** Django, Celery, existing Claude AI client

---

## File Structure

```
backend/agents/
├── models/
│   ├── agent.py              (modify — remove superior, add is_leader + constraint)
│   └── agent_task.py         (modify — approve() triggers leader chain)
├── admin/
│   ├── agent_admin.py        (modify — show is_leader, remove superior)
│   └── agent_task_admin.py   (no change)
├── blueprints/
│   ├── __init__.py           (modify — remove campaign, add leader)
│   ├── base.py               (modify — split into WorkforceBlueprint + LeaderBlueprint, add command system)
│   ├── leader/
│   │   ├── __init__.py       (create)
│   │   ├── agent.py          (create — LeaderBlueprint with commands)
│   │   ├── skills.py         (create)
│   │   └── commands.py       (create — create_priority_task, create_campaign)
│   ├── twitter/
│   │   ├── agent.py          (modify — extend WorkforceBlueprint, remove generate_task_proposal)
│   │   └── skills.py         (no change)
│   ├── reddit/
│   │   ├── agent.py          (modify — extend WorkforceBlueprint, remove generate_task_proposal)
│   │   └── skills.py         (no change)
│   └── campaign/             (DELETE entire directory)
├── tasks.py                  (modify — remove refill_approval_queue, add create_next_leader_task)
└── migrations/

backend/config/
└── settings.py               (modify — remove refill-approval-queue from beat)

backend/projects/admin/
└── bootstrap_proposal_admin.py (modify — auto-create leader per department)
```

---

### Task 1: Agent Model — Remove superior, Add is_leader

**Files:**
- Modify: `backend/agents/models/agent.py`

- [ ] **Step 1: Replace agent.py**

Replace the entire file `backend/agents/models/agent.py`:

```python
import uuid

from django.db import models


class Agent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Display name, e.g. 'Our Twitter Guy'")
    agent_type = models.CharField(
        max_length=50,
        help_text="Blueprint type — determines the agent's behavior",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="agents",
    )
    is_leader = models.BooleanField(
        default=False,
        help_text="Leader agent for the department. Creates and delegates tasks to workforce agents.",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Custom instructions layered on top of the blueprint prompts",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-agent config (browser cookies, API keys, etc.)",
    )
    auto_exec_hourly = models.BooleanField(
        default=False,
        help_text="Whether this agent auto-executes hourly tasks",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "-is_leader", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department"],
                condition=models.Q(is_leader=True),
                name="unique_leader_per_department",
            ),
        ]

    def get_blueprint(self):
        from agents.blueprints import get_blueprint
        return get_blueprint(self.agent_type)

    def __str__(self):
        leader_tag = " [LEADER]" if self.is_leader else ""
        return f"{self.name} ({self.agent_type}){leader_tag}"
```

- [ ] **Step 2: Run makemigrations**

Run:
```bash
cd /Users/christianpeters/the-agentic-company/backend && source venv/bin/activate && python manage.py makemigrations agents
```

This will generate a migration that:
- Removes the `superior` field
- Adds the `is_leader` field
- Adds the unique constraint

- [ ] **Step 3: Run migrate**

Run:
```bash
python manage.py migrate
```

- [ ] **Step 4: Commit**

```bash
git add backend/agents/models/agent.py backend/agents/migrations/
git commit -m "refactor: replace superior FK with is_leader + unique constraint per department"
```

---

### Task 2: Blueprint Base — Split into Leader and Workforce

**Files:**
- Modify: `backend/agents/blueprints/base.py`

- [ ] **Step 1: Replace base.py**

Replace the entire file `backend/agents/blueprints/base.py`:

```python
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

logger = logging.getLogger(__name__)


# ── Command decorator ────────────────────────────────────────────────────────


_command_registry: dict[str, dict] = {}


def command(name: str, description: str):
    """Decorator to register a method as a blueprint command."""
    def decorator(func):
        func._command_meta = {"name": name, "description": description}
        return func
    return decorator


# ── Base Blueprint ───────────────────────────────────────────────────────────


class BaseBlueprint(ABC):
    """Abstract base for all blueprints (leader and workforce)."""

    name: str = ""
    slug: str = ""
    description: str = ""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona, role, and capabilities."""

    @property
    @abstractmethod
    def skills_description(self) -> str:
        """Formatted skills text injected into system prompt."""

    def get_commands(self) -> list[dict]:
        """Return list of registered commands on this blueprint."""
        commands = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and hasattr(attr, "_command_meta"):
                commands.append(attr._command_meta)
        return commands

    def run_command(self, command_name: str, agent: "Agent", **kwargs):
        """Run a named command on this blueprint."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and hasattr(attr, "_command_meta"):
                if attr._command_meta["name"] == command_name:
                    return attr(agent, **kwargs)
        raise ValueError(f"Unknown command: {command_name}")

    def get_context(self, agent: "Agent") -> dict:
        """Gather context with prefetched queries to avoid N+1."""
        from agents.models import AgentTask

        department = agent.department
        project = department.project

        docs = list(department.documents.values_list("title", "content"))
        docs_text = ""
        for title, content in docs:
            docs_text += f"\n\n--- {title} ---\n{content[:3000]}"

        sibling_ids = list(
            department.agents.exclude(id=agent.id)
            .filter(is_active=True)
            .values_list("id", "name", "agent_type")
        )
        sibling_text = ""
        if sibling_ids:
            sib_id_list = [s[0] for s in sibling_ids]
            all_sib_tasks = list(
                AgentTask.objects.filter(agent_id__in=sib_id_list)
                .order_by("agent_id", "-created_at")
                .values_list("agent_id", "exec_summary", "status")
            )
            tasks_by_agent = defaultdict(list)
            for aid, es, st in all_sib_tasks:
                if len(tasks_by_agent[aid]) < 5:
                    tasks_by_agent[aid].append((es, st))

            for sib_id, sib_name, sib_type in sibling_ids:
                recent = tasks_by_agent.get(sib_id, [])
                if recent:
                    task_lines = "\n".join(f"  - [{s}] {e[:100]}" for e, s in recent)
                    sibling_text += f"\n\n{sib_name} ({sib_type}) recent tasks:\n{task_lines}"

        own_recent = list(
            agent.tasks.order_by("-created_at")[:10]
            .values_list("exec_summary", "status", "report")
        )
        own_text = ""
        for es, st, rp in own_recent:
            own_text += f"\n  - [{st}] {es[:100]}"
            if rp:
                own_text += f"\n    Report: {rp[:200]}"

        return {
            "project_name": project.name,
            "project_goal": project.goal,
            "department_name": department.name,
            "department_documents": docs_text,
            "sibling_agents": sibling_text,
            "own_recent_tasks": own_text,
            "agent_instructions": agent.instructions,
        }

    def build_system_prompt(self, agent: "Agent") -> str:
        parts = [self.system_prompt]
        parts.append(f"\n\n## Your Skills\n{self.skills_description}")
        if agent.instructions:
            parts.append(f"\n\n## Additional Instructions\n{agent.instructions}")
        return "".join(parts)

    def build_context_message(self, agent: "Agent") -> str:
        ctx = self.get_context(agent)
        return f"""# Context

## Project: {ctx['project_name']}
**Goal:** {ctx['project_goal']}

## Department: {ctx['department_name']}

### Department Documents
{ctx['department_documents'] or 'No documents yet.'}

### Other Agents in Department
{ctx['sibling_agents'] or 'No other agents.'}

### Your Recent Tasks
{ctx['own_recent_tasks'] or 'No tasks yet.'}"""


# ── Workforce Blueprint ──────────────────────────────────────────────────────


class WorkforceBlueprint(BaseBlueprint):
    """Base for workforce agents (twitter, reddit, etc.). Execute tasks only."""

    @property
    @abstractmethod
    def hourly_prompt(self) -> str:
        """What to do on the hourly beat."""

    @abstractmethod
    def execute_task(self, agent: "Agent", task: "AgentTask") -> str:
        """Execute a task. Returns the report text."""


# ── Leader Blueprint ─────────────────────────────────────────────────────────


class LeaderBlueprint(BaseBlueprint):
    """Base for department leader agents. Proposes and delegates tasks."""

    @abstractmethod
    def execute_task(self, agent: "Agent", task: "AgentTask") -> str:
        """Execute a task. Returns the report text."""

    @abstractmethod
    def generate_task_proposal(self, agent: "Agent") -> dict:
        """Propose the next highest-value task. Returns {exec_summary, step_plan, target_agent_type (optional)}."""
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/blueprints/base.py
git commit -m "refactor: split base into WorkforceBlueprint + LeaderBlueprint with command system"
```

---

### Task 3: Leader Blueprint Package

**Files:**
- Create: `backend/agents/blueprints/leader/__init__.py`
- Create: `backend/agents/blueprints/leader/skills.py`
- Create: `backend/agents/blueprints/leader/commands.py`
- Create: `backend/agents/blueprints/leader/agent.py`

- [ ] **Step 1: Create leader/skills.py**

```python
SKILLS = [
    {"name": "Analyze Department Activity", "description": "Review all workforce agents' recent tasks, successes, and failures to identify gaps and opportunities"},
    {"name": "Create Priority Tasks", "description": "Propose the highest-value next task for workforce agents based on project goals and current state"},
    {"name": "Create Campaign", "description": "Design a cross-platform campaign and create coordinated tasks for multiple workforce agents"},
    {"name": "Delegate Tasks", "description": "Create specific tasks for workforce agents with clear exec summaries and step plans"},
]


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

- [ ] **Step 2: Create leader/commands.py**

```python
"""
Leader commands — Python methods registered as commands via the @command decorator.
These are the actions a leader agent can perform.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-priority-task", description="Propose the highest-value next task for a workforce agent")
def create_priority_task(self, agent: Agent) -> dict:
    """Ask Claude to propose the next highest-value task for the department's workforce."""
    from agents.ai.claude_client import call_claude
    from agents.models import AgentTask

    # Get workforce agents in this department
    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("id", "name", "agent_type")
    )
    if not workforce:
        return {"exec_summary": "No workforce agents in department", "step_plan": ""}

    workforce_desc = "\n".join(f"- {name} ({atype})" for _, name, atype in workforce)

    # Check existing awaiting tasks per workforce agent
    awaiting_by_agent = {}
    for wid, wname, wtype in workforce:
        count = AgentTask.objects.filter(agent_id=wid, status=AgentTask.Status.AWAITING_APPROVAL).count()
        awaiting_by_agent[wname] = count

    awaiting_text = "\n".join(f"- {name}: {count} tasks awaiting approval" for name, count in awaiting_by_agent.items())

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Current Approval Queue
{awaiting_text}

# Task
Propose the single highest-value task for one of the workforce agents above. Consider the project goal, department documents, recent activity, and what each agent is already working on.

Respond with JSON:
{{
    "target_agent_type": "twitter or reddit (which workforce agent should do this)",
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan"
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


@command(name="create-campaign", description="Design a cross-platform campaign with coordinated tasks for workforce agents")
def create_campaign(self, agent: Agent) -> dict:
    """Ask Claude to design a campaign and generate tasks for multiple workforce agents."""
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
Design a cross-platform campaign for this project. Create specific, coordinated tasks for the workforce agents listed above.

Respond with JSON:
{{
    "campaign_name": "Name of the campaign",
    "campaign_summary": "Brief campaign description and rationale",
    "tasks": [
        {{
            "target_agent_type": "twitter",
            "exec_summary": "What this agent should do for the campaign",
            "step_plan": "Detailed steps"
        }},
        {{
            "target_agent_type": "reddit",
            "exec_summary": "What this agent should do for the campaign",
            "step_plan": "Detailed steps"
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
            "campaign_name": data.get("campaign_name", "Campaign"),
            "campaign_summary": data.get("campaign_summary", response),
            "tasks": data.get("tasks", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {"campaign_name": "Campaign", "campaign_summary": response, "tasks": []}
```

- [ ] **Step 3: Create leader/agent.py**

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.leader.skills import format_skills
from agents.blueprints.leader import commands

logger = logging.getLogger(__name__)


class DepartmentLeaderBlueprint(LeaderBlueprint):
    name = "Department Leader"
    slug = "leader"
    description = "Department leader — proposes priority tasks and campaigns, delegates to workforce agents"

    @property
    def system_prompt(self) -> str:
        return """You are the department leader agent. Your role is to analyze the project's goals, department context, and workforce agent capabilities to determine the highest-value actions.

You don't execute tasks directly on platforms — you create and delegate tasks to your workforce agents (Twitter, Reddit, etc.).

Your core responsibilities:
1. Propose the single most impactful next task for the department
2. Design cross-platform campaigns when opportunities arise
3. Ensure workforce agents are aligned with the project goal
4. Monitor department activity and adjust strategy

Always consider the project goal, department documents (branding guidelines, etc.), and what the workforce has been doing recently."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands.py
    create_priority_task = commands.create_priority_task
    create_campaign = commands.create_campaign

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Execute a leader task — this delegates to workforce agents."""
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel, AgentTask as TaskModel

        context_msg = self.build_context_message(agent)
        workforce = list(
            agent.department.agents.filter(is_active=True, is_leader=False)
            .values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        task_msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task. If it involves delegating work to workforce agents, include delegated_tasks in your response.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "twitter or reddit",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed steps"
        }}
    ],
    "report": "Summary of what was decided and why"
}}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)

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
                        logger.warning("No active workforce agent of type %s in department %s", target_type, agent.department.name)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED,
                        auto_execute=True,
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )
                    from agents.tasks import execute_agent_task
                    execute_agent_task.delay(str(sub_task.id))
                    logger.info("Leader delegated task %s to %s", sub_task.id, target_agent.name)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        """Use the create-priority-task command to propose the next task."""
        return self.create_priority_task(agent)
```

- [ ] **Step 4: Create leader/__init__.py**

```python
from .agent import DepartmentLeaderBlueprint

__all__ = ["DepartmentLeaderBlueprint"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/leader/
git commit -m "feat: leader blueprint with create-priority-task and create-campaign commands"
```

---

### Task 4: Refactor Twitter & Reddit to WorkforceBlueprint, Remove Campaign

**Files:**
- Modify: `backend/agents/blueprints/twitter/agent.py`
- Modify: `backend/agents/blueprints/reddit/agent.py`
- Delete: `backend/agents/blueprints/campaign/` (entire directory)
- Modify: `backend/agents/blueprints/__init__.py`

- [ ] **Step 1: Replace twitter/agent.py**

Replace the entire file `backend/agents/blueprints/twitter/agent.py`:

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.twitter.skills import format_skills

logger = logging.getLogger(__name__)


class TwitterBlueprint(WorkforceBlueprint):
    name = "Twitter Agent"
    slug = "twitter"
    description = "Manages Twitter/X presence — engagement, posting, trend monitoring"

    @property
    def system_prompt(self) -> str:
        return """You are a Twitter/X social media agent. Your role is to grow the project's presence on Twitter/X through strategic engagement and content creation.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "tweet", "content": "...", "hashtags": ["..."]},
        {"type": "reply", "target_url": "...", "content": "..."},
        {"type": "retweet", "target_url": "..."},
        {"type": "like", "target_url": "..."},
        {"type": "search", "query": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with the project's branding guidelines and voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly engagement routine:
1. Search for 10 relevant high-impact tweets in the project's domain
2. Engage authentically with the best ones (like, reply, retweet)
3. If appropriate, post one original tweet that adds value

Focus on building genuine connections, not spam. Quality over quantity."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. Respond with your actions JSON and report."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.browser import run_browser_action
                run_browser_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response
```

- [ ] **Step 2: Replace reddit/agent.py**

Replace the entire file `backend/agents/blueprints/reddit/agent.py`:

```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.reddit.skills import format_skills

logger = logging.getLogger(__name__)


class RedditBlueprint(WorkforceBlueprint):
    name = "Reddit Agent"
    slug = "reddit"
    description = "Manages Reddit presence — posting, commenting, community engagement"

    @property
    def system_prompt(self) -> str:
        return """You are a Reddit social media agent. Your role is to build the project's presence on Reddit through valuable contributions to relevant communities.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing.

Reddit values authenticity and hates spam. Your contributions must be genuinely helpful and add value to discussions. Never be overtly promotional.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "post", "subreddit": "...", "title": "...", "content": "..."},
        {"type": "comment", "target_url": "...", "content": "..."},
        {"type": "search", "query": "...", "subreddit": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with subreddit rules and the project's voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly Reddit engagement routine:
1. Browse 3-5 relevant subreddits for discussions where you can add value
2. Leave 2-3 thoughtful, helpful comments on active threads
3. If there's a good opportunity, create one valuable post

Focus on being a genuine community member. Provide value first, brand visibility follows naturally."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. Respond with your actions JSON and report."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.browser import run_browser_action
                run_browser_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response
```

- [ ] **Step 3: Delete campaign blueprint directory**

Run:
```bash
rm -rf backend/agents/blueprints/campaign/
```

- [ ] **Step 4: Replace blueprints/__init__.py**

Replace the entire file `backend/agents/blueprints/__init__.py`:

```python
"""Blueprint registry."""

from agents.blueprints.leader import DepartmentLeaderBlueprint
from agents.blueprints.twitter import TwitterBlueprint
from agents.blueprints.reddit import RedditBlueprint

_REGISTRY = {
    "leader": DepartmentLeaderBlueprint(),
    "twitter": TwitterBlueprint(),
    "reddit": RedditBlueprint(),
}

AGENT_TYPE_CHOICES = [(slug, bp.name) for slug, bp in _REGISTRY.items()]

# Workforce types only — used by bootstrap prompt and leader commands
WORKFORCE_TYPE_CHOICES = [
    (slug, bp.name) for slug, bp in _REGISTRY.items()
    if slug != "leader"
]


def get_blueprint(agent_type: str):
    bp = _REGISTRY.get(agent_type)
    if bp is None:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return bp
```

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/
git commit -m "refactor: twitter/reddit extend WorkforceBlueprint, remove campaign, add leader to registry"
```

---

### Task 5: AgentTask.approve() — Self-perpetuating Leader Chain

**Files:**
- Modify: `backend/agents/models/agent_task.py`

- [ ] **Step 1: Replace agent_task.py**

Replace the entire file `backend/agents/models/agent_task.py`:

```python
import uuid

from django.db import models
from django.utils import timezone


class AgentTask(models.Model):
    class Status(models.TextChoices):
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    created_by_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_tasks",
        help_text="Set when the department leader delegates this task",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AWAITING_APPROVAL,
        db_index=True,
    )
    auto_execute = models.BooleanField(default=False)
    exec_summary = models.TextField(blank=True, help_text="Short description of what to do")
    step_plan = models.TextField(blank=True, help_text="Detailed step-by-step plan")
    report = models.TextField(blank=True, help_text="What was actually done")
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def approve(self):
        """Approve task: queue for execution. If this is a leader task, auto-propose the next one."""
        if self.status != self.Status.AWAITING_APPROVAL:
            return False
        self.status = self.Status.QUEUED
        self.save(update_fields=["status", "updated_at"])

        # Dispatch execution
        from agents.tasks import execute_agent_task
        execute_agent_task.delay(str(self.id))

        # Self-perpetuating chain: if this is a leader task, create the next proposal
        if self.agent.is_leader:
            from agents.tasks import create_next_leader_task
            create_next_leader_task.delay(str(self.agent.id))

        return True

    def __str__(self):
        return f"[{self.get_status_display()}] {self.agent.name}: {self.exec_summary[:60]}"
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/models/agent_task.py
git commit -m "feat: approve() triggers self-perpetuating leader chain on queue"
```

---

### Task 6: Celery Tasks — Remove refill, Add create_next_leader_task

**Files:**
- Modify: `backend/agents/tasks.py`
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Replace agents/tasks.py**

Replace the entire file `backend/agents/tasks.py`:

```python
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def execute_hourly_tasks():
    """
    Every hour: for each active workforce agent with auto_exec_hourly=True,
    create and execute a task from the hourly prompt.
    """
    from agents.models import Agent, AgentTask
    from agents.blueprints.base import WorkforceBlueprint

    agents = Agent.objects.filter(
        is_active=True,
        auto_exec_hourly=True,
        is_leader=False,
    ).select_related("department__project")

    for agent in agents:
        try:
            blueprint = agent.get_blueprint()
            if not isinstance(blueprint, WorkforceBlueprint):
                continue

            task = AgentTask.objects.create(
                agent=agent,
                status=AgentTask.Status.QUEUED,
                auto_execute=True,
                exec_summary=f"Hourly task: {blueprint.hourly_prompt[:100]}",
                step_plan=blueprint.hourly_prompt,
            )
            execute_agent_task.delay(str(task.id))
            logger.info("Created hourly task for %s: %s", agent.name, task.id)

        except Exception as e:
            logger.exception("Failed to create hourly task for %s: %s", agent.name, e)


@shared_task(bind=True, max_retries=0)
def execute_agent_task(self, task_id: str):
    """
    Execute a single agent task. Called when tasks are approved or auto-dispatched.
    Uses atomic guard to prevent double execution.
    """
    from agents.models import AgentTask

    updated = AgentTask.objects.filter(
        id=task_id,
        status=AgentTask.Status.QUEUED,
    ).update(
        status=AgentTask.Status.PROCESSING,
        started_at=timezone.now(),
    )

    if updated == 0:
        current = AgentTask.objects.filter(id=task_id).values_list("status", flat=True).first()
        logger.warning("Task %s not queued (status=%s) — skipping", task_id, current)
        return

    task = AgentTask.objects.select_related(
        "agent__department__project",
    ).get(id=task_id)

    try:
        blueprint = task.agent.get_blueprint()
        report = blueprint.execute_task(task.agent, task)

        task.status = AgentTask.Status.DONE
        task.report = report
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "report", "completed_at", "updated_at"])

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task.status = AgentTask.Status.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])


@shared_task
def create_next_leader_task(leader_agent_id: str):
    """
    Self-perpetuating chain: when a leader task is approved, this creates
    the next priority task proposal. Called from AgentTask.approve().
    """
    from agents.models import Agent, AgentTask
    from agents.blueprints.base import LeaderBlueprint

    try:
        agent = Agent.objects.select_related("department__project").get(
            id=leader_agent_id,
            is_leader=True,
            is_active=True,
        )
    except Agent.DoesNotExist:
        logger.warning("Leader agent %s not found or inactive", leader_agent_id)
        return

    blueprint = agent.get_blueprint()
    if not isinstance(blueprint, LeaderBlueprint):
        logger.warning("Agent %s is not a leader blueprint", agent.name)
        return

    try:
        proposal = blueprint.generate_task_proposal(agent)

        # Create the task on the target workforce agent if specified
        target_type = proposal.get("target_agent_type")
        if target_type:
            target_agent = Agent.objects.filter(
                department=agent.department,
                agent_type=target_type,
                is_active=True,
                is_leader=False,
            ).first()
            if target_agent:
                AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=AgentTask.Status.AWAITING_APPROVAL,
                    auto_execute=False,
                    exec_summary=proposal.get("exec_summary", "Priority task"),
                    step_plan=proposal.get("step_plan", ""),
                )
                logger.info("Leader %s proposed task for %s: %s", agent.name, target_agent.name, proposal.get("exec_summary", "")[:80])
                return

        # Fallback: create as a leader task if no target specified
        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            auto_execute=False,
            exec_summary=proposal.get("exec_summary", "Leader task"),
            step_plan=proposal.get("step_plan", ""),
        )
        logger.info("Leader %s proposed own task: %s", agent.name, proposal.get("exec_summary", "")[:80])

    except Exception as e:
        logger.exception("Failed to create next leader task for %s: %s", agent.name, e)
```

- [ ] **Step 2: Update settings.py — remove refill-approval-queue from beat**

In `backend/config/settings.py`, replace the CELERY_BEAT_SCHEDULE block:

```python
CELERY_BEAT_SCHEDULE = {
    "execute-hourly-tasks": {
        "task": "agents.tasks.execute_hourly_tasks",
        "schedule": 3600,
    },
}
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/tasks.py backend/config/settings.py
git commit -m "refactor: remove refill_approval_queue, add create_next_leader_task chain"
```

---

### Task 7: Admin Updates & Bootstrap — Auto-create Leader

**Files:**
- Modify: `backend/agents/admin/agent_admin.py`
- Modify: `backend/projects/admin/bootstrap_proposal_admin.py`

- [ ] **Step 1: Replace agent_admin.py**

Replace the entire file `backend/agents/admin/agent_admin.py`:

```python
from django.contrib import admin

from agents.models import Agent, AgentTask


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    fk_name = "agent"
    extra = 0
    fields = ("status", "exec_summary", "auto_execute", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True
    max_num = 10


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "department", "is_leader", "auto_exec_hourly", "is_active")
    list_filter = ("agent_type", "is_active", "is_leader", "auto_exec_hourly", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "-is_leader", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "is_leader")}),
        ("Configuration", {"fields": ("instructions", "config", "auto_exec_hourly", "is_active")}),
    )
    inlines = [AgentTaskInline]
    actions = ["seed_first_task"]

    @admin.action(description="Seed first leader task — kick off the chain")
    def seed_first_task(self, request, queryset):
        """For leader agents: create the first priority task proposal to start the chain."""
        from agents.tasks import create_next_leader_task

        seeded = 0
        for agent in queryset.filter(is_leader=True, is_active=True):
            create_next_leader_task.delay(str(agent.id))
            seeded += 1
        self.message_user(request, f"Seeded first task for {seeded} leader(s).")
```

- [ ] **Step 2: Replace bootstrap_proposal_admin.py**

Replace the entire file `backend/projects/admin/bootstrap_proposal_admin.py`:

```python
import json
import logging

from django.contrib import admin
from django.utils.html import format_html

from projects.models import BootstrapProposal, Department, Document, Tag
from agents.models import Agent
from agents.blueprints import _REGISTRY

logger = logging.getLogger(__name__)


@admin.register(BootstrapProposal)
class BootstrapProposalAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("project__name",)
    readonly_fields = ("id", "project", "proposal_formatted", "token_usage", "error_message", "created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "status")}),
        ("Proposal", {"fields": ("proposal_formatted",)}),
        ("Debug", {"fields": ("error_message", "token_usage")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    actions = ["approve_and_apply", "reject_proposal"]

    @admin.display(description="Proposal (formatted)")
    def proposal_formatted(self, obj):
        if not obj.proposal:
            return "—"
        return format_html("<pre style='max-height:600px;overflow:auto'>{}</pre>", json.dumps(obj.proposal, indent=2))

    @admin.action(description="Approve & Apply — create departments, agents, documents")
    def approve_and_apply(self, request, queryset):
        for proposal in queryset.filter(status=BootstrapProposal.Status.PROPOSED):
            try:
                self._apply_proposal(proposal)
                proposal.status = BootstrapProposal.Status.APPROVED
                proposal.save(update_fields=["status", "updated_at"])
                self.message_user(request, f"Applied bootstrap for {proposal.project.name}")
            except Exception as e:
                logger.exception("Failed to apply bootstrap: %s", e)
                self.message_user(request, f"Failed to apply for {proposal.project.name}: {e}", level="error")

    @admin.action(description="Reject proposal")
    def reject_proposal(self, request, queryset):
        count = queryset.filter(status=BootstrapProposal.Status.PROPOSED).update(
            status=BootstrapProposal.Status.FAILED,
            error_message="Rejected by admin",
        )
        self.message_user(request, f"{count} proposal(s) rejected.")

    def _apply_proposal(self, proposal):
        """Create departments, leader + workforce agents, and documents from the proposal JSON."""
        project = proposal.project
        data = proposal.proposal
        if not data or "departments" not in data:
            raise ValueError("Invalid proposal — missing departments")

        for dept_data in data["departments"]:
            department, _ = Department.objects.get_or_create(
                project=project,
                name=dept_data["name"],
            )

            # Create documents
            for doc_data in dept_data.get("documents", []):
                doc = Document.objects.create(
                    title=doc_data["title"],
                    content=doc_data.get("content", ""),
                    department=department,
                )
                for tag_name in doc_data.get("tags", []):
                    tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                    doc.tags.add(tag)

            # Auto-create leader agent if department doesn't have one
            if not department.agents.filter(is_leader=True).exists():
                Agent.objects.create(
                    name=f"{department.name} Leader",
                    agent_type="leader",
                    department=department,
                    is_leader=True,
                    instructions=f"Lead the {department.name} department for project: {project.name}. Goal: {project.goal[:200]}",
                )

            # Create workforce agents (only valid non-leader blueprint types)
            for agent_data in dept_data.get("agents", []):
                agent_type = agent_data["agent_type"]
                if agent_type not in _REGISTRY or agent_type == "leader":
                    logger.warning("Skipping invalid agent_type '%s' in bootstrap proposal", agent_type)
                    continue
                Agent.objects.create(
                    name=agent_data["name"],
                    agent_type=agent_type,
                    department=department,
                    is_leader=False,
                    instructions=agent_data.get("instructions", ""),
                    auto_exec_hourly=agent_data.get("auto_exec_hourly", False),
                )
```

- [ ] **Step 3: Update bootstrap prompt to exclude leader from available types**

In `backend/projects/tasks.py`, change the available_types construction. Find this line:

```python
        available_types = [
            {"slug": slug, "name": bp.name, "description": bp.description}
            for slug, bp in _REGISTRY.items()
        ]
```

Replace with:

```python
        from agents.blueprints import WORKFORCE_TYPE_CHOICES
        available_types = [
            {"slug": slug, "name": bp.name, "description": bp.description}
            for slug, bp in _REGISTRY.items()
            if slug != "leader"
        ]
```

- [ ] **Step 4: Commit**

```bash
git add backend/agents/admin/agent_admin.py backend/projects/admin/bootstrap_proposal_admin.py backend/projects/tasks.py
git commit -m "feat: admin updates — leader auto-creation, seed-first-task action, bootstrap excludes leader"
```

---

### Task 8: Verify — Makemigrations, Migrate, System Check

- [ ] **Step 1: Run makemigrations (if needed)**

Run:
```bash
cd /Users/christianpeters/the-agentic-company/backend && source venv/bin/activate && python manage.py makemigrations agents
```

- [ ] **Step 2: Run migrate**

Run:
```bash
python manage.py migrate
```

- [ ] **Step 3: Run system check**

Run:
```bash
python manage.py check
```

Expected: System check identified no issues.

- [ ] **Step 4: Test Celery discovers tasks**

Run:
```bash
celery -A config worker --loglevel=info &
sleep 4 && kill %1
```

Expected: Tasks list shows `agents.tasks.execute_hourly_tasks`, `agents.tasks.execute_agent_task`, `agents.tasks.create_next_leader_task`. Does NOT show `refill_approval_queue`.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "refactor: complete leader/workforce agent restructure"
```

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


def command(name: str, description: str, schedule: str | None = None):
    """
    Decorator to register a method as a blueprint command.

    Args:
        name: Command name (e.g. "engage-tweets")
        description: Human-readable description
        schedule: "hourly", "daily", or None (on-demand only)
    """
    def decorator(func):
        func._command_meta = {"name": name, "description": description, "schedule": schedule}
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

    def get_scheduled_commands(self, schedule: str) -> list[dict]:
        """Return commands matching the given schedule type."""
        return [c for c in self.get_commands() if c.get("schedule") == schedule]

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

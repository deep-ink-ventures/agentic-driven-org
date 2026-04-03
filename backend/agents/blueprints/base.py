from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

logger = logging.getLogger(__name__)


class BaseBlueprint(ABC):
    name: str = ""
    slug: str = ""
    description: str = ""

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona, role, and capabilities."""

    @property
    @abstractmethod
    def hourly_prompt(self) -> str:
        """What to do on the hourly beat."""

    @property
    @abstractmethod
    def task_generation_prompt(self) -> str:
        """How to propose new tasks for the approval queue."""

    @property
    @abstractmethod
    def skills_description(self) -> str:
        """Formatted skills text injected into system prompt."""

    def get_context(self, agent: Agent) -> dict:
        department = agent.department
        project = department.project

        docs = list(department.documents.values_list("title", "content"))
        docs_text = ""
        for title, content in docs:
            docs_text += f"\n\n--- {title} ---\n{content[:3000]}"

        siblings = list(
            department.agents.exclude(id=agent.id)
            .filter(is_active=True)
            .values_list("name", "agent_type")
        )
        sibling_text = ""
        for sib_name, sib_type in siblings:
            from agents.models import AgentTask
            recent = list(
                AgentTask.objects.filter(
                    agent__name=sib_name,
                    agent__department=department,
                ).order_by("-created_at")[:5]
                .values_list("exec_summary", "status")
            )
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

    def build_system_prompt(self, agent: Agent) -> str:
        parts = [self.system_prompt]
        parts.append(f"\n\n## Your Skills\n{self.skills_description}")
        if agent.instructions:
            parts.append(f"\n\n## Additional Instructions\n{agent.instructions}")
        return "".join(parts)

    def build_context_message(self, agent: Agent) -> str:
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

    @abstractmethod
    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Execute a task. Returns the report text."""

    @abstractmethod
    def generate_task_proposal(self, agent: Agent) -> dict:
        """Propose the next highest-value task. Returns {exec_summary, step_plan}."""

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


def command(name: str, description: str, schedule: str | None = None, model: str | None = None):
    """
    Decorator to register a method as a blueprint command.

    Args:
        name: Command name (e.g. "engage-tweets")
        description: Human-readable description
        schedule: "hourly", "daily", or None (on-demand only)
        model: Override model for this command (e.g. "claude-haiku-4-5")
    """
    def decorator(func):
        func._command_meta = {"name": name, "description": description, "schedule": schedule, "model": model}
        return func
    return decorator


# ── Base Blueprint ───────────────────────────────────────────────────────────


class BaseBlueprint(ABC):
    """Abstract base for all blueprints (leader and workforce)."""

    name: str = ""
    slug: str = ""
    description: str = ""
    tags: list[str] = []
    default_model: str = "claude-sonnet-4-6"
    config_schema: dict[str, dict] = {}  # {"key": {"type": "str", "required": bool, "description": "..."}}

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona, role, and capabilities."""

    @property
    @abstractmethod
    def skills_description(self) -> str:
        """Formatted skills text injected into system prompt."""

    def get_bootstrap_command(self, agent: "Agent") -> dict | None:
        """
        Return a bootstrap task dict for this agent, or None to skip.

        Called when an agent is first created or needs initialization.
        Override in blueprint subclasses to set up required state,
        create initial tasks, or verify config.

        Returns:
            dict with {exec_summary, step_plan} if bootstrap is needed, None otherwise.
        """
        return None

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

    def get_model(self, agent: "Agent", command_name: str | None = None) -> str:
        """Resolve model: command model -> agent.config['model'] -> blueprint default_model."""
        # 1. Command-specific model
        if command_name:
            for cmd in self.get_commands():
                if cmd["name"] == command_name and cmd.get("model"):
                    return cmd["model"]
        # 2. Agent-level override
        model = agent.config.get("model")
        if model:
            return model
        # 3. Blueprint default
        return self.default_model

    def validate_config(self, config: dict) -> list[str]:
        """Validate agent config against this blueprint's JSON Schema. Returns list of error strings."""
        from jsonschema import validate, ValidationError as JsonSchemaError
        schema = self.get_config_json_schema()
        try:
            validate(instance=config, schema=schema)
            return []
        except JsonSchemaError as e:
            return [e.message]

    def get_config_json_schema(self) -> dict:
        """
        Build a JSON Schema from config_schema declarations.
        Blueprints declare config_schema as a simple dict; this converts it
        to a proper JSON Schema for validation and frontend form generation.
        """
        properties = {}
        required = []
        for key, spec in self.config_schema.items():
            prop: dict = {
                "description": spec.get("description", ""),
                "title": spec.get("label", key),
            }
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
        schema: dict = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    def validate_auto_actions(self, auto_actions: dict) -> list[str]:
        """Validate auto_actions as {command_name: bool} with only valid scheduled commands as keys."""
        from jsonschema import validate, ValidationError as JsonSchemaError
        schema = self.get_auto_actions_json_schema()
        try:
            validate(instance=auto_actions, schema=schema)
            return []
        except JsonSchemaError as e:
            return [e.message]

    def get_auto_actions_json_schema(self) -> dict:
        """Build a JSON Schema for auto_actions based on this blueprint's scheduled commands."""
        valid_commands = {c["name"] for c in self.get_commands() if c.get("schedule")}
        properties = {name: {"type": "boolean"} for name in valid_commands}
        return {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }

    def get_available_commands_description(self) -> str:
        """Format available commands for inclusion in context messages."""
        cmds = self.get_commands()
        if not cmds:
            return "No commands available."
        lines = []
        for c in cmds:
            schedule = f" [{c['schedule']}]" if c.get("schedule") else " [on-demand]"
            lines.append(f"- {c['name']}{schedule}: {c['description']}")
        return "\n".join(lines)

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
        parts.append(f"\n\n## Your Commands\n{self.get_available_commands_description()}")
        if agent.instructions:
            # Wrap user-controlled content in XML tags so Claude treats it as data, not instructions
            parts.append(f"\n\n## Additional Instructions\n<user_instructions>\n{agent.instructions}\n</user_instructions>")
        return "".join(parts)

    def build_context_message(self, agent: "Agent") -> str:
        ctx = self.get_context(agent)
        # All user-controlled content wrapped in XML tags to mitigate prompt injection.
        # Claude is trained to treat content inside XML tags as data rather than instructions.
        return f"""# Context

## Project: {ctx['project_name']}
<project_goal>
{ctx['project_goal']}
</project_goal>

## Department: {ctx['department_name']}

### Department Documents
<documents>
{ctx['department_documents'] or 'No documents yet.'}
</documents>

### Other Agents in Department
<sibling_activity>
{ctx['sibling_agents'] or 'No other agents.'}
</sibling_activity>

### Your Recent Tasks
<own_activity>
{ctx['own_recent_tasks'] or 'No tasks yet.'}
</own_activity>"""

    def build_task_message(self, agent: "Agent", task: "AgentTask", suffix: str = "") -> str:
        """Build a task execution message with user-controlled content wrapped in XML tags."""
        context_msg = self.build_context_message(agent)
        extra = f"\n\n{suffix}" if suffix else ""
        return f"""{context_msg}

# Task to Execute
<task_summary>
{task.exec_summary}
</task_summary>
<task_plan>
{task.step_plan}
</task_plan>

Execute this task now.{extra}"""


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

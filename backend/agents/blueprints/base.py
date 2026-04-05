from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

# ── Universal quality standards ─────────────────────────────────────────────
# These apply to ALL departments. Quality is not configurable.

EXCELLENCE_THRESHOLD = 9.5  # Score needed to pass review
NEAR_EXCELLENCE_THRESHOLD = 9.0  # Score at which we start counting "polish" attempts
MAX_POLISH_ATTEMPTS = 3  # After reaching 9.0, max attempts to reach 9.5 before accepting
MAX_REVIEW_ROUNDS = 5  # Hard cap before human escalation


def parse_review_verdict(report: str) -> tuple[str, float]:
    """Parse a review report for VERDICT line. Returns (verdict, score)."""
    match = re.search(r"VERDICT:\s*(APPROVED|CHANGES_REQUESTED)\s*\(score:\s*([\d.]+)/10\)", report)
    if match:
        return match.group(1), float(match.group(2))
    # Fallback: keyword detection
    lower = report.lower()
    if "approved" in lower and "changes_requested" not in lower:
        return "APPROVED", EXCELLENCE_THRESHOLD
    return "CHANGES_REQUESTED", 0.0


def should_accept_review(score: float, round_num: int, polish_attempts: int) -> bool:
    """Decide whether to accept a review score.

    - score >= 9.5 → always accept (excellence)
    - score >= 9.0 and polish_attempts >= 3 → accept (diminishing returns)
    - otherwise → another round
    """
    return score >= EXCELLENCE_THRESHOLD or (
        score >= NEAR_EXCELLENCE_THRESHOLD and polish_attempts >= MAX_POLISH_ATTEMPTS
    )


logger = logging.getLogger(__name__)


# ── Command decorator ────────────────────────────────────────────────────────


_command_registry: dict[str, dict] = {}


def command(
    name: str, description: str, schedule: str | None = None, model: str | None = None, max_tokens: int | None = None
):
    """
    Decorator to register a method as a blueprint command.

    Args:
        name: Command name (e.g. "engage-tweets")
        description: Human-readable description
        schedule: "hourly", "daily", or None (on-demand only)
        model: Override model for this command (e.g. "claude-haiku-4-5")
        max_tokens: Override max output tokens for this command
    """

    def decorator(func):
        func._command_meta = {
            "name": name,
            "description": description,
            "schedule": schedule,
            "model": model,
            "max_tokens": max_tokens,
        }
        return func

    return decorator


# ── Base Blueprint ───────────────────────────────────────────────────────────


class BaseBlueprint(ABC):
    """Abstract base for all blueprints (leader and workforce)."""

    name: str = ""
    slug: str = ""
    description: str = ""
    tags: list[str] = []
    skills: list[dict] = []  # [{"name": "...", "description": "..."}]
    outputs: list[str] = []  # metadata: what persistent artifacts this agent produces
    default_model: str = "claude-sonnet-4-6"
    config_schema: dict[str, dict] = {}  # {"key": {"type": "str", "required": bool, "description": "..."}}
    essential: bool = False  # always pre-selected when department is added
    controls: str | list[str] | None = None  # auto-selected when controlled agent is selected

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The agent's persona, role, and capabilities."""

    @property
    def skills_description(self) -> str:
        """Formatted skills text injected into system prompt.

        Default reads from the ``skills`` class attribute.
        """
        return self.format_skills()

    def format_skills(self) -> str:
        """Format the skills list attribute into markdown bullet points."""
        if not self.skills:
            return "No special skills."
        return "\n".join(f"- **{s['name']}**: {s['description']}" for s in self.skills)

    def get_bootstrap_command(self, agent: Agent) -> dict | None:
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

    def run_command(self, command_name: str, agent: Agent, **kwargs):
        """Run a named command on this blueprint."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and hasattr(attr, "_command_meta") and attr._command_meta["name"] == command_name:
                return attr(agent, **kwargs)
        raise ValueError(f"Unknown command: {command_name}")

    def get_model(self, agent: Agent, command_name: str | None = None) -> str:
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
        from jsonschema import ValidationError as JsonSchemaError
        from jsonschema import validate

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

    def get_context(self, agent: Agent) -> dict:
        """Gather context with prefetched queries to avoid N+1."""
        from agents.models import AgentTask

        department = agent.department
        project = department.project

        # Department documents — exclude archived, include type and age
        docs = list(
            department.documents.filter(is_archived=False).values_list("title", "content", "doc_type", "created_at")
        )
        docs_text = ""
        for title, content, doc_type, created_at in docs:
            from django.utils import timezone

            age = (timezone.now() - created_at).days
            age_str = f", {age}d ago" if doc_type == "research" else ""
            docs_text += f"\n\n--- [{doc_type}{age_str}] {title} ---\n{content[:3000]}"

        sibling_ids = list(
            department.agents.exclude(id=agent.id).filter(status="active").values_list("id", "name", "agent_type")
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

        own_recent = list(agent.tasks.order_by("-created_at")[:10].values_list("exec_summary", "status", "report"))
        own_text = ""
        for es, st, rp in own_recent:
            own_text += f"\n  - [{st}] {es[:100]}"
            if rp:
                own_text += f"\n    Report: {rp[:200]}"

        # Active briefings for this department (department-specific + project-level)
        from django.db.models import Q
        from django.utils import timezone as tz

        from projects.models import Briefing

        briefings = list(
            Briefing.objects.filter(
                project=project,
                status="active",
            )
            .filter(Q(department=department) | Q(department__isnull=True))
            .prefetch_related("attachments")
            .order_by("-created_at")
        )
        briefings_text = ""
        if briefings:
            for b in briefings:
                age = tz.now() - b.created_at
                if age.days > 0:
                    age_str = f"{age.days}d ago"
                else:
                    hours = age.seconds // 3600
                    age_str = f"{hours}h ago" if hours > 0 else "just now"
                scope = "department-level" if b.department else "project-level"
                briefings_text += f'\n\n## "{b.title}" ({scope}, created {age_str})\nContent: {b.content}'
                attachments = list(b.attachments.all())
                if attachments:
                    briefings_text += "\nAttachments:"
                    for att in attachments:
                        snippet = att.extracted_text[:500] if att.extracted_text else "(not yet extracted)"
                        briefings_text += f"\n- {att.original_filename}: {snippet}"

        return {
            "project_name": project.name,
            "project_goal": project.goal,
            "department_name": department.name,
            "department_documents": docs_text,
            "sibling_agents": sibling_text,
            "own_recent_tasks": own_text,
            "agent_instructions": agent.instructions,
            "active_briefings": briefings_text,
        }

    def build_system_prompt(self, agent: Agent) -> str:
        parts = [self.system_prompt]
        parts.append(f"\n\n## Your Skills\n{self.skills_description}")
        parts.append(f"\n\n## Your Commands\n{self.get_available_commands_description()}")
        if agent.instructions:
            # Wrap user-controlled content in XML tags so Claude treats it as data, not instructions
            parts.append(
                f"\n\n## Additional Instructions\n<user_instructions>\n{agent.instructions}\n</user_instructions>"
            )
        return "".join(parts)

    def build_context_message(self, agent: Agent) -> str:
        ctx = self.get_context(agent)
        # All user-controlled content wrapped in XML tags to mitigate prompt injection.
        # Claude is trained to treat content inside XML tags as data rather than instructions.
        briefings_section = ""
        if ctx.get("active_briefings"):
            briefings_section = f"""

### Active Briefings
<briefings>
{ctx["active_briefings"]}
</briefings>"""

        return f"""# Context

## Project: {ctx["project_name"]}
<project_goal>
{ctx["project_goal"]}
</project_goal>

## Department: {ctx["department_name"]}

### Department Documents
<documents>
{ctx["department_documents"] or "No documents yet."}
</documents>{briefings_section}

### Other Agents in Department
<sibling_activity>
{ctx["sibling_agents"] or "No other agents."}
</sibling_activity>

### Your Recent Tasks
<own_activity>
{ctx["own_recent_tasks"] or "No tasks yet."}
</own_activity>"""

    def build_task_message(self, agent: Agent, task: AgentTask, suffix: str = "") -> str:
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
    """Base for workforce agents (twitter, reddit, etc.). Execute tasks only.

    Default execute_task: build task message → call Claude → return response.
    Override get_task_suffix() for per-agent methodology instructions.
    Override get_max_tokens() for per-agent token limits.
    Override execute_task() only for agents with integrations or special dispatch.
    """

    review_dimensions: list[str] = []

    def get_task_suffix(self, agent: Agent, task: AgentTask) -> str:
        """Return extra instructions appended to the task message.

        Override for methodology-specific instructions (e.g. review criteria,
        research methodology). Default: empty string.
        """
        return ""

    def get_max_tokens(self, agent: Agent, task: AgentTask) -> int | None:
        """Return max output tokens for this task, or None for default."""
        return None

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Execute a task by calling Claude and returning the response.

        This default handles the common pattern used by ~20 agents.
        Override only for agents with external integrations (Playwright,
        GitHub, SendGrid) or command-dispatch logic.
        """
        from agents.ai.claude_client import call_claude

        suffix = self.get_task_suffix(agent, task)
        task_msg = self.build_task_message(agent, task, suffix=suffix)

        kwargs = {
            "system_prompt": self.build_system_prompt(agent),
            "user_message": task_msg,
            "model": self.get_model(agent, task.command_name),
        }
        max_tokens = self.get_max_tokens(agent, task)
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response, usage = call_claude(**kwargs)
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response


# ── Leader Blueprint ─────────────────────────────────────────────────────────


class LeaderBlueprint(BaseBlueprint):
    """Base for department leader agents. Proposes and delegates tasks."""

    # ── Declarative review ping-pong ────────────────────────────────────
    #
    # Subclasses define get_review_pairs() to declare creator→reviewer flows.
    # The base class handles all review logic: triggering, scoring, looping, fixing.

    def get_review_pairs(self) -> list[dict]:
        """Define creator→reviewer ping-pong pairs.

        Override in subclasses to enable automatic review loops.
        Each pair describes one flow: when creator finishes, reviewer checks quality.

        Returns list of dicts:
        {
            "creator": "agent_type",           # who creates content
            "creator_fix_command": "cmd",       # command for revision tasks
            "reviewer": "agent_type",           # who reviews (final quality gate)
            "reviewer_command": "cmd",          # command for review tasks
            "dimensions": ["dim1", "dim2"],     # scoring dimensions for the reviewer
        }

        For complex review chains (e.g. parallel reviewers → consolidator),
        override _propose_review_chain() instead.
        """
        return []

    def _get_creator_types(self) -> set[str]:
        """Derive creator types from review pairs."""
        return {p["creator"] for p in self.get_review_pairs()}

    def _get_reviewer_types(self) -> set[str]:
        """Derive reviewer types from review pairs."""
        return {p["reviewer"] for p in self.get_review_pairs()}

    def _get_pair_for_creator(self, creator_type: str) -> dict | None:
        """Find the review pair for a given creator type."""
        for pair in self.get_review_pairs():
            if pair["creator"] == creator_type:
                return pair
        return None

    def _get_pair_for_reviewer(self, reviewer_type: str) -> dict | None:
        """Find the review pair for a given reviewer type."""
        for pair in self.get_review_pairs():
            if pair["reviewer"] == reviewer_type:
                return pair
        return None

    def _propose_review_chain(self, agent: Agent, creator_task: AgentTask, workforce_types: set) -> dict | None:
        """Build a review chain after a creator task completes.

        Default implementation: simple 1:1 creator→reviewer from get_review_pairs().
        Override for complex patterns (e.g., parallel reviewers → consolidator).
        """
        pair = self._get_pair_for_creator(creator_task.agent.agent_type)
        if not pair or pair["reviewer"] not in workforce_types:
            return None

        # Track review round and active chain key
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        task_key = str(creator_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        internal_state["review_rounds"] = review_rounds
        internal_state["active_review_key"] = task_key  # so _evaluate_review_and_loop can find it
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        if round_num > MAX_REVIEW_ROUNDS:
            return {
                "exec_summary": f"Escalation: {round_num} review rounds on {creator_task.exec_summary[:60]}",
                "tasks": [
                    {
                        "target_agent_type": pair["creator"],
                        "command_name": pair["creator_fix_command"],
                        "exec_summary": f"Human review needed: exceeded {MAX_REVIEW_ROUNDS} rounds — {creator_task.exec_summary[:60]}",
                        "step_plan": f"This task has gone through {round_num} review rounds without reaching quality threshold ({EXCELLENCE_THRESHOLD}/10). A human needs to step in.",
                        "depends_on_previous": False,
                    }
                ],
            }

        report_snippet = (creator_task.report or "")[:3000]
        # Read dimensions from reviewer blueprint (single source of truth),
        # falling back to pair definition for backwards compatibility
        from agents.blueprints import get_blueprint

        reviewer_bp = get_blueprint(pair["reviewer"], agent.department.department_type)
        dims = reviewer_bp.review_dimensions or pair.get("dimensions", [])
        dims_text = ", ".join(dims)

        return {
            "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary[:80]}",
            "tasks": [
                {
                    "target_agent_type": pair["reviewer"],
                    "command_name": pair["reviewer_command"],
                    "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary[:80]}",
                    "step_plan": (
                        f"Review round {round_num}. Quality threshold: {EXCELLENCE_THRESHOLD}/10.\n\n"
                        f"Content to review:\n{report_snippet}\n\n"
                        f"Score each dimension 1.0-10.0 (use decimals): {dims_text}.\n"
                        f"Overall score = MINIMUM of all dimensions.\n\n"
                        f"End with exactly one of:\n"
                        f"VERDICT: APPROVED (score: N.N/10)\n"
                        f"VERDICT: CHANGES_REQUESTED (score: N.N/10)"
                    ),
                    "depends_on_previous": False,
                }
            ],
        }

    def _apply_quality_gate(self, agent: Agent, score: float, stage_key: str) -> tuple[bool, int, int]:
        """Apply universal quality scoring logic.

        Tracks polish attempts and evaluates acceptance.
        Returns (accepted, polish_count, round_num).

        Args:
            agent: The leader agent (state is stored on it).
            score: The review score (0.0-10.0).
            stage_key: Key to track this review chain in internal_state.
        """
        internal_state = agent.internal_state or {}
        review_rounds = internal_state.get("review_rounds", {})
        polish_attempts_map = internal_state.get("polish_attempts", {})

        round_num = review_rounds.get(stage_key, 1)

        # Update polish attempts counter (count attempts after reaching 9.0)
        polish_count = polish_attempts_map.get(stage_key, 0)
        if score >= NEAR_EXCELLENCE_THRESHOLD:
            polish_count += 1
            polish_attempts_map[stage_key] = polish_count

        logger.info(
            "Quality gate: score %.1f/10, round %d, polish %d/%d (key=%s)",
            score,
            round_num,
            polish_count,
            MAX_POLISH_ATTEMPTS,
            stage_key,
        )

        accepted = should_accept_review(score, round_num, polish_count)

        if accepted:
            # Clear tracking for this key
            review_rounds.pop(stage_key, None)
            polish_attempts_map.pop(stage_key, None)
            internal_state["review_rounds"] = review_rounds
            internal_state["polish_attempts"] = polish_attempts_map
            internal_state.pop("active_review_key", None)
            if score < EXCELLENCE_THRESHOLD:
                logger.info(
                    "Accepting score %.1f/10 after %d polish attempts (diminishing returns)",
                    score,
                    polish_count,
                )
        else:
            # Persist polish tracking
            internal_state["polish_attempts"] = polish_attempts_map

        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
        return accepted, polish_count, round_num

    def _evaluate_review_and_loop(self, agent: Agent, review_task: AgentTask, workforce_types: set) -> dict | None:
        """After a reviewer completes, evaluate score and loop back if needed.

        Universal logic using shared quality constants:
        - score >= 9.5 → always accept (excellence)
        - score >= 9.0 and polish_attempts >= 3 → accept (diminishing returns)
        - otherwise → create fix task back to the original creator
        """
        report = review_task.report or ""
        verdict, score = parse_review_verdict(report)

        # Find the task key: use stored active_review_key (set when review chain starts)
        internal_state = agent.internal_state or {}
        task_key = internal_state.get("active_review_key")
        if not task_key:
            review_rounds = internal_state.get("review_rounds", {})
            for key in review_rounds:
                task_key = key
                break
        if not task_key:
            task_key = str(review_task.id)

        accepted, polish_count, round_num = self._apply_quality_gate(agent, score, task_key)

        if accepted:
            return None  # Approved — fall through to standard proposal

        # Find the original creator and route fix back
        return self._propose_fix_task(agent, review_task, score, round_num, polish_count)

    def _propose_fix_task(
        self, agent: Agent, review_task: AgentTask, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """Create a fix task routed back to the original creator agent.

        Override in subclasses for custom fix routing (e.g., writers room routes
        specific flags to specific creative agents).
        """
        from agents.models import AgentTask as TaskModel

        creator_types = self._get_creator_types()
        if not creator_types:
            return None

        # Find the most recent completed creator task
        recent_creator = (
            TaskModel.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=list(creator_types),
                status=TaskModel.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if not recent_creator:
            return None

        creator_type = recent_creator.agent.agent_type
        pair = self._get_pair_for_creator(creator_type)
        fix_command = pair["creator_fix_command"] if pair else "implement"

        review_snippet = (review_task.report or "")[:3000]
        polish_msg = f" (polish {polish_count}/{MAX_POLISH_ATTEMPTS})" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

        return {
            "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}: {recent_creator.exec_summary[:60]}",
            "tasks": [
                {
                    "target_agent_type": creator_type,
                    "command_name": fix_command,
                    "exec_summary": f"Fix review issues (score {score}/10): {recent_creator.exec_summary[:60]}",
                    "step_plan": (
                        f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                        f"Review round: {round_num}. Polish attempts: {polish_count}/{MAX_POLISH_ATTEMPTS}.\n\n"
                        f"The reviewer has requested changes. Fix the issues below to reach "
                        f"the quality threshold. Focus on the weakest dimensions first.\n\n"
                        f"## Review Report\n{review_snippet}\n\n"
                        f"Address every CHANGES_REQUESTED item. After fixing, the review chain "
                        f"runs again automatically."
                    ),
                    "depends_on_previous": False,
                }
            ],
        }

    def _check_review_trigger(self, agent: Agent) -> dict | None:
        """Check if the last completed task should trigger a review chain or loop.

        Call this from generate_task_proposal() to handle review ping-pong.
        Returns a task proposal dict, or None to proceed with normal proposal logic.
        """
        creator_types = self._get_creator_types()
        reviewer_types = self._get_reviewer_types()
        if not creator_types and not reviewer_types:
            return None

        from agents.models import AgentTask as TaskModel

        workforce_types = set(
            agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
        )

        last_completed = (
            TaskModel.objects.filter(
                agent__department=agent.department,
                status=TaskModel.Status.DONE,
            )
            .order_by("-completed_at")
            .select_related("agent", "created_by_agent")
            .first()
        )
        if not last_completed:
            return None

        last_type = last_completed.agent.agent_type

        # Creator just finished → propose review chain
        if last_type in creator_types:
            review_proposal = self._propose_review_chain(agent, last_completed, workforce_types)
            if review_proposal:
                return review_proposal

        # Reviewer just finished → evaluate and maybe loop back
        if last_type in reviewer_types and last_completed.report:
            loop_proposal = self._evaluate_review_and_loop(agent, last_completed, workforce_types)
            if loop_proposal:
                return loop_proposal

        return None

    # ── Leader delegation (shared execute_task) ───────────────────────

    def _get_delegation_context(self, agent: Agent) -> str:
        """Return extra context text for the delegation prompt.

        Override to add department-specific context (e.g., file locks, stage info).
        Inserted between the workforce list and the JSON schema.
        """
        return ""

    def _get_delegation_schema_extras(self) -> str:
        """Return extra fields for the delegation JSON schema.

        Override to add department-specific fields (e.g., file_paths, follow_up).
        """
        return ""

    def _on_subtask_created(self, agent: Agent, sub_task: AgentTask, delegation_data: dict) -> None:
        """Hook called after each delegated subtask is created.

        Override for post-creation logic (e.g., file lock claiming).
        """

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Execute a leader task by calling Claude and processing delegated subtasks.

        This default handles the common delegation pattern used by all leaders.
        Customize via hooks: _get_delegation_context, _get_delegation_schema_extras,
        _on_subtask_created.
        """
        import json

        from agents.ai.claude_client import call_claude, parse_json_response
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask as TaskModel

        workforce = list(
            agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        extra_context = self._get_delegation_context(agent)
        if extra_context:
            extra_context = f"\n{extra_context}\n"

        extra_schema = self._get_delegation_schema_extras()

        delegation_suffix = f"""# Workforce Agents
{workforce_desc}
{extra_context}
If this task involves delegating work to workforce agents, include delegated_tasks in your response.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed steps",
            "auto_execute": false{extra_schema}
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 7
    }},
    "report": "Summary of what was decided and why"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=delegation_suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response) if response.strip().startswith("{") else None
            if not data:
                data = parse_json_response(response)
            if not data:
                return response

            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department,
                    status="active",
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
                        status=TaskModel.Status.QUEUED
                        if dt.get("auto_execute")
                        else TaskModel.Status.AWAITING_APPROVAL,
                        auto_execute=bool(dt.get("auto_execute")),
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )

                    self._on_subtask_created(agent, sub_task, dt)

                    if dt.get("auto_execute"):
                        from agents.tasks import execute_agent_task

                        execute_agent_task.delay(str(sub_task.id))

                    logger.info("Leader delegated task %s to %s", sub_task.id, target_agent.name)

            # Schedule follow-up if requested
            follow_up = data.get("follow_up")
            if follow_up and follow_up.get("days_from_now"):
                from datetime import timedelta

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

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """
        Propose the next highest-value task by asking Claude to assess and plan.

        Uses project goal, department documents, completed tasks, and available agents
        to determine what to do next. Subclasses can override for domain-specific logic.
        """
        import json
        import logging

        from agents.ai.claude_client import call_claude, parse_json_response

        logger = logging.getLogger(__name__)

        department = agent.department
        project = department.project

        # Gather available workforce agents
        workforce = Agent.objects.filter(
            department=department,
            is_leader=False,
            status=Agent.Status.ACTIVE,
        )
        if not workforce.exists():
            return None

        agents_desc = []
        for a in workforce:
            bp = a.get_blueprint()
            cmds = bp.get_commands() if bp else []
            cmd_names = [c["name"] for c in cmds]
            agents_desc.append(
                {
                    "agent_type": a.agent_type,
                    "name": a.name,
                    "description": bp.description if bp else "",
                    "commands": cmd_names,
                }
            )

        # Gather recent completed tasks
        completed_tasks = list(
            AgentTask.objects.filter(
                agent__department=department,
                status__in=["completed", "processing"],
            )
            .order_by("-created_at")
            .values_list("exec_summary", flat=True)[:20]
        )

        # Gather department documents
        from projects.models import Document

        docs = list(Document.objects.filter(department=department).values_list("title", flat=True)[:20])

        # Get locale
        locale = agent.get_config_value("locale") or "en"

        system_prompt = f"""You are a department leader deciding the next highest-value task for your team.

You MUST respond with valid JSON only. No markdown fences, no explanation.

## Your Process
1. ASSESS: Where does the project stand? What has been done? What's missing?
2. GOAL: What does the project need most right now to move forward?
3. IMPACT: Which agent and action would create the most value right now?
4. PLAN: Write a detailed, actionable task plan for that agent.

## Rules
- Propose ONE task at a time (or a small chain of dependent tasks if they form a logical unit)
- Each task must target a specific agent by agent_type
- Each task must have a specific command_name from that agent's available commands
- The step_plan must be detailed enough that the agent can work autonomously
- Reference specific project details — characters, themes, goals, constraints
- All output in {locale}

## Response JSON Schema
{{
    "exec_summary": "Brief description of what this task achieves",
    "tasks": [
        {{
            "target_agent_type": "agent_type_slug",
            "command_name": "command_name",
            "exec_summary": "What this specific agent should deliver",
            "step_plan": "Detailed, actionable instructions for the agent...",
            "depends_on_previous": false
        }}
    ]
}}"""

        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Leader Instructions
{agent.instructions or "No specific instructions."}

## Available Agents
{json.dumps(agents_desc, indent=2)}

## Completed / In-Progress Tasks
{json.dumps(completed_tasks) if completed_tasks else "None yet — this is the first task."}

## Department Documents
{json.dumps(docs) if docs else "None yet."}

What is the single most impactful next action for this department?"""

        try:
            response, _usage = call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4096,
            )
            result = parse_json_response(response)
            if result:
                return result
            logger.warning("Leader %s: failed to parse task proposal from Claude", agent.name)
        except Exception as e:
            logger.exception("Leader %s: Claude call failed for task proposal: %s", agent.name, e)

        return None

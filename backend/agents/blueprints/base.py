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

VERDICT_TOOL = {
    "name": "submit_verdict",
    "description": "Submit your review verdict. You MUST call this tool after completing your review.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["APPROVED", "CHANGES_REQUESTED"],
            },
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 10,
                "description": "Overall review score out of 10",
            },
        },
        "required": ["verdict", "score"],
    },
}


def parse_review_verdict(report: str) -> tuple[str, float]:
    """Parse a review report for VERDICT line. Returns (verdict, score)."""
    match = re.search(r"VERDICT:\s*(APPROVED|CHANGES_REQUESTED)\s*\(score:\s*([\d.]+)/10\)", report)
    if match:
        return match.group(1), float(match.group(2))
    # Fallback: keyword detection
    logger.warning("VERDICT_REGEX_MISS — falling back to keyword detection")
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

_format_checker = None


def _get_format_checker():
    """Lazy-init a jsonschema FormatChecker with email validation."""
    global _format_checker
    if _format_checker is None:
        from jsonschema import FormatChecker

        _format_checker = FormatChecker()

        @_format_checker.checks("email", raises=ValueError)
        def check_email(value):
            if not isinstance(value, str) or "@" not in value or "." not in value.split("@")[-1]:
                raise ValueError(f"'{value}' is not a valid email address")
            return True

    return _format_checker


# ── Command decorator ────────────────────────────────────────────────────────


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
    default_model: str = "claude-opus-4-6"
    config_schema: dict[str, dict] = {}  # {"key": {"type": "str", "required": bool, "description": "..."}}
    uses_web_search: bool = False  # whether this agent needs web search tools at runtime
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
            validate(
                instance=config,
                schema=schema,
                format_checker=_get_format_checker(),
            )
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
            if t == "email":
                prop["type"] = "string"
                prop["format"] = "email"
            elif t == "str":
                prop["type"] = "string"
            elif t == "int":
                prop["type"] = "integer"
            elif t == "bool":
                prop["type"] = "boolean"
            elif t == "list":
                prop["type"] = "array"
            elif t == "dict":
                prop["type"] = "object"
            if "default" in spec:
                prop["default"] = spec["default"]
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

        # Volume safety net — trigger async consolidation if context is too large
        total_chars = sum(len(content) for _, content, _, _ in docs)
        if total_chars > 1_500_000:  # ~500k tokens
            consolidate_department_documents.delay(str(department.id))
            logger.warning(
                "VOLUME_THRESHOLD dept=%s chars=%d — async consolidation triggered",
                department.name,
                total_chars,
            )

        docs_text = ""
        for title, content, doc_type, created_at in docs:
            from django.utils import timezone

            age = (timezone.now() - created_at).days
            age_str = f", {age}d ago" if doc_type == "research" else ""
            docs_text += f"\n\n--- [{doc_type}{age_str}] {title} ---\n{content}"

        sibling_ids = list(
            department.agents.exclude(id=agent.id).filter(status="active").values_list("id", "name", "agent_type")
        )
        sibling_text = ""
        if sibling_ids:
            sib_id_list = [s[0] for s in sibling_ids]
            # Include reports from completed sibling tasks so agents see each other's output
            all_sib_tasks = list(
                AgentTask.objects.filter(agent_id__in=sib_id_list)
                .order_by("agent_id", "-created_at")
                .values_list("agent_id", "exec_summary", "status", "report")
            )
            tasks_by_agent = defaultdict(list)
            for aid, es, st, rp in all_sib_tasks:
                if len(tasks_by_agent[aid]) < 5:
                    tasks_by_agent[aid].append((es, st, rp))

            for sib_id, sib_name, sib_type in sibling_ids:
                recent = tasks_by_agent.get(sib_id, [])
                if recent:
                    task_lines = ""
                    for es, st, rp in recent:
                        task_lines += f"\n  - [{st}] {es}"
                        if rp and st == "done":
                            task_lines += f"\n    Report: {rp}"
                    sibling_text += f"\n\n{sib_name} ({sib_type}) recent tasks:{task_lines}"

        own_recent = list(agent.tasks.order_by("-created_at")[:10].values_list("exec_summary", "status", "report"))
        own_text = ""
        for es, st, rp in own_recent:
            own_text += f"\n  - [{st}] {es}"
            if rp:
                own_text += f"\n    Report: {rp}"

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
        return f"""# Context

## Project: {ctx["project_name"]}

### CREATOR'S ORIGINAL PITCH — PRIMARY CREATIVE DIRECTIVE
The following is the creator's own pitch. Every specific element they mention — characters,
conflicts, settings, arcs, relationships, references, tone — is a BINDING creative directive.
Your job is to BUILD ON these specifics, not replace them with generic alternatives or elements
borrowed from reference shows. When the creator references existing shows, they mean
"play in this league of quality and ambition" — NOT "copy their plot, characters, or structure."

<project_goal>
{ctx["project_goal"]}
</project_goal>

## Department: {ctx["department_name"]}

### Department Documents
<documents>
{ctx["department_documents"] or "No documents yet."}
</documents>

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

        sprint_notes = ""
        if task.sprint:
            notes_text = self._format_sprint_notes(task.sprint)
            if notes_text:
                sprint_notes = f"\n\n<user_notes>\n{notes_text}\n</user_notes>"

        return f"""{context_msg}{sprint_notes}

# Task to Execute
<task_summary>
{task.exec_summary}
</task_summary>
<task_plan>
{task.step_plan}
</task_plan>

Execute this task now.{extra}"""

    @staticmethod
    def _format_sprint_notes(sprint) -> str:
        """Format sprint notes for injection into agent context."""
        if sprint is None:
            return ""

        from projects.models import SprintNote

        notes = list(
            SprintNote.objects.filter(sprint=sprint)
            .select_related("user")
            .prefetch_related("sources")
            .order_by("created_at")
        )
        if not notes:
            return ""

        parts = ["## User Notes\n"]
        for note in notes:
            timestamp = note.created_at.strftime("%Y-%m-%d %H:%M")
            parts.append(f"**[{timestamp}]** {note.text}")
            for src in note.sources.all():
                content = src.summary or src.extracted_text or src.raw_content or ""
                if content:
                    parts.append(f"  Attachment ({src.original_filename}): {content}")
        return "\n".join(parts)


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
        Reviewer agents (with review_dimensions) get VERDICT_TOOL injected.
        Override only for agents with external integrations (Playwright,
        GitHub, SendGrid) or command-dispatch logic.
        """
        suffix = self.get_task_suffix(agent, task)
        task_msg = self.build_task_message(agent, task, suffix=suffix)
        model = self.get_model(agent, task.command_name)
        max_tokens = self.get_max_tokens(agent, task)

        if self.review_dimensions:
            from agents.ai.claude_client import call_claude_with_tools

            kwargs = {
                "system_prompt": self.build_system_prompt(agent),
                "user_message": task_msg,
                "tools": [VERDICT_TOOL],
                "model": model,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response, tool_input, usage = call_claude_with_tools(**kwargs)
            task.token_usage = usage

            if tool_input and "verdict" in tool_input and "score" in tool_input:
                task.review_verdict = tool_input["verdict"]
                task.review_score = tool_input["score"]
            else:
                logger.warning(
                    "VERDICT_TOOL_FALLBACK agent=%s task=%s — Claude did not call submit_verdict",
                    agent.name,
                    task.id,
                )
                verdict, score = parse_review_verdict(response)
                task.review_verdict = verdict
                task.review_score = score

            task.save(update_fields=["token_usage", "review_verdict", "review_score"])
            return response

        from agents.ai.claude_client import call_claude

        kwargs = {
            "system_prompt": self.build_system_prompt(agent),
            "user_message": task_msg,
            "model": model,
        }
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
        if not pair:
            return None
        if pair["reviewer"] not in workforce_types:
            logger.warning(
                "REVIEW_SKIPPED dept=%s creator=%s — reviewer %s is not active, work passes without review",
                agent.department.name,
                creator_task.agent.agent_type,
                pair["reviewer"],
            )
            return None

        # Track review round and active chain key on sprint.department_state
        sprint = creator_task.sprint
        if not sprint:
            logger.warning("REVIEW_NO_SPRINT task=%s — cannot track review state", creator_task.id)
            return None

        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        review_rounds = dept_state.get("review_rounds", {})
        task_key = str(creator_task.id)
        round_num = review_rounds.get(task_key, 0) + 1
        review_rounds[task_key] = round_num
        dept_state["review_rounds"] = review_rounds
        dept_state["active_review_key"] = task_key  # so _evaluate_review_and_loop can find it
        sprint.set_department_state(dept_id, dept_state)

        if round_num > MAX_REVIEW_ROUNDS:
            logger.warning(
                "REVIEW_ESCALATION dept=%s rounds=%d max=%d task=%s",
                agent.department.name,
                round_num,
                MAX_REVIEW_ROUNDS,
                creator_task.exec_summary[:60],
            )
            return {
                "exec_summary": f"Escalation: {round_num} review rounds on {creator_task.exec_summary}",
                "tasks": [
                    {
                        "target_agent_type": pair["creator"],
                        "command_name": pair["creator_fix_command"],
                        "exec_summary": f"Human review needed: exceeded {MAX_REVIEW_ROUNDS} rounds — {creator_task.exec_summary}",
                        "step_plan": f"This task has gone through {round_num} review rounds without reaching quality threshold ({EXCELLENCE_THRESHOLD}/10). A human needs to step in.",
                        "depends_on_previous": False,
                    }
                ],
            }

        report_snippet = creator_task.report or ""
        # Read dimensions from reviewer blueprint (single source of truth),
        # falling back to pair definition for backwards compatibility
        from agents.blueprints import get_blueprint

        reviewer_bp = get_blueprint(pair["reviewer"], agent.department.department_type)
        dims = reviewer_bp.review_dimensions or pair.get("dimensions", [])
        dims_text = ", ".join(dims)

        return {
            "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary}",
            "tasks": [
                {
                    "target_agent_type": pair["reviewer"],
                    "command_name": pair["reviewer_command"],
                    "exec_summary": f"Review (round {round_num}): {creator_task.exec_summary}",
                    "step_plan": (
                        f"Review round {round_num}. Quality threshold: {EXCELLENCE_THRESHOLD}/10.\n\n"
                        f"Content to review:\n{report_snippet}\n\n"
                        f"Score each dimension 1.0-10.0 (use decimals): {dims_text}.\n"
                        f"Overall score = MINIMUM of all dimensions.\n\n"
                        f"After your review, call the submit_verdict tool with your verdict and score."
                    ),
                    "depends_on_previous": False,
                }
            ],
        }

    def _apply_quality_gate(self, agent: Agent, sprint, score: float, stage_key: str) -> tuple[bool, int, int]:
        """Apply universal quality scoring logic.

        Tracks polish attempts and evaluates acceptance.
        Returns (accepted, polish_count, round_num).

        Args:
            agent: The leader agent.
            sprint: The Sprint instance (state is stored on sprint.department_state).
            score: The review score (0.0-10.0).
            stage_key: Key to track this review chain in department_state.
        """
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id) if sprint else {}
        review_rounds = dept_state.get("review_rounds", {})
        polish_attempts_map = dept_state.get("polish_attempts", {})

        round_num = review_rounds.get(stage_key, 1)

        # Update polish attempts counter (count attempts after reaching 9.0)
        polish_count = polish_attempts_map.get(stage_key, 0)
        if score >= NEAR_EXCELLENCE_THRESHOLD:
            polish_count += 1
            polish_attempts_map[stage_key] = polish_count

        dept_name = agent.department.name if hasattr(agent, "department") else "?"
        logger.info(
            "REVIEW_DECISION dept=%s agent=%s score=%.1f/10 round=%d polish=%d/%d key=%s",
            dept_name,
            agent.name,
            score,
            round_num,
            polish_count,
            MAX_POLISH_ATTEMPTS,
            stage_key,
        )

        accepted = should_accept_review(score, round_num, polish_count)

        if accepted:
            reason = "excellence" if score >= EXCELLENCE_THRESHOLD else f"diminishing_returns (polish={polish_count})"
            logger.info(
                "REVIEW_ACCEPTED dept=%s score=%.1f/10 reason=%s key=%s",
                dept_name,
                score,
                reason,
                stage_key,
            )
            # Clear tracking for this key
            review_rounds.pop(stage_key, None)
            polish_attempts_map.pop(stage_key, None)
            dept_state["review_rounds"] = review_rounds
            dept_state["polish_attempts"] = polish_attempts_map
            dept_state.pop("active_review_key", None)
        else:
            gap = EXCELLENCE_THRESHOLD - score
            logger.info(
                "REVIEW_REJECTED dept=%s score=%.1f/10 gap=%.1f round=%d key=%s",
                dept_name,
                score,
                gap,
                round_num,
                stage_key,
            )
            # Persist polish tracking
            dept_state["polish_attempts"] = polish_attempts_map

        if sprint:
            sprint.set_department_state(dept_id, dept_state)
        return accepted, polish_count, round_num

    def _evaluate_review_and_loop(self, agent: Agent, review_task: AgentTask, workforce_types: set) -> dict | None:
        """After a reviewer completes, evaluate score and loop back if needed.

        Universal logic using shared quality constants:
        - score >= 9.5 → always accept (excellence)
        - score >= 9.0 and polish_attempts >= 3 → accept (diminishing returns)
        - otherwise → create fix task back to the original creator
        """
        if review_task.review_verdict and review_task.review_score is not None:
            verdict = review_task.review_verdict
            score = review_task.review_score
        else:
            report = review_task.report or ""
            verdict, score = parse_review_verdict(report)
            logger.warning(
                "VERDICT_FROM_TEXT agent=%s task=%s — no structured verdict, parsed from report text",
                review_task.agent.name,
                review_task.id,
            )

        # Find the task key: use stored active_review_key (set when review chain starts)
        sprint = review_task.sprint
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id) if sprint else {}
        task_key = dept_state.get("active_review_key")
        if not task_key:
            review_rounds = dept_state.get("review_rounds", {})
            for key in review_rounds:
                task_key = key
                break
        if not task_key:
            task_key = str(review_task.id)

        accepted, polish_count, round_num = self._apply_quality_gate(agent, sprint, score, task_key)

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

        review_snippet = review_task.report or ""
        polish_msg = f" (polish {polish_count}/{MAX_POLISH_ATTEMPTS})" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

        return {
            "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}: {recent_creator.exec_summary}",
            "tasks": [
                {
                    "target_agent_type": creator_type,
                    "command_name": fix_command,
                    "exec_summary": f"Fix review issues (score {score}/10): {recent_creator.exec_summary}",
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
            logger.info(
                "REVIEW_TRIGGER dept=%s creator=%s task=%s",
                agent.department.name,
                last_type,
                last_completed.exec_summary[:60],
            )
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

    # ── Clone lifecycle helpers ─────────────────────────────────────────

    def create_clones(self, parent_agent: Agent, count: int, sprint, initial_state: dict | None = None) -> list:
        """Create N ephemeral clones of parent_agent, scoped to this sprint."""
        from django.conf import settings

        from agents.models import ClonedAgent

        max_clones = getattr(settings, "AGENT_MAX_CLONES_PER_SPRINT", 10)
        if count > max_clones:
            raise ValueError(
                f"create_clones count={count} exceeds max {max_clones} "
                f"for parent={parent_agent.name} sprint={sprint.id}"
            )

        clones = []
        for i in range(count):
            clone = ClonedAgent.objects.create(
                parent=parent_agent,
                sprint=sprint,
                clone_index=i,
                internal_state=initial_state or {},
            )
            clones.append(clone)
        logger.info(
            "CLONES_CREATED parent=%s count=%d sprint=%s",
            parent_agent.name,
            count,
            str(sprint.id)[:8],
        )
        return clones

    def destroy_sprint_clones(self, sprint) -> int:
        """Delete all clones for a sprint. Returns count deleted."""
        from agents.models import ClonedAgent

        count, _ = ClonedAgent.objects.filter(sprint=sprint).delete()
        if count:
            logger.info("CLONES_DESTROYED count=%d sprint=%s", count, str(sprint.id)[:8])
        return count

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
                    step_plan=f"Review and assess. Original task: {task.exec_summary}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )
                logger.info("Leader scheduled follow-up in %d days", days)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """
        Propose the next task by examining running sprints for this department.

        Picks the sprint with least recent activity (round-robin fairness),
        reviews what's been done, and proposes subtasks to advance it.
        Returns None if no running sprints exist.
        """
        import json
        import logging

        from agents.ai.claude_client import call_claude, parse_json_response

        logger = logging.getLogger(__name__)

        department = agent.department
        project = department.project

        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        running_sprints = list(
            Sprint.objects.filter(
                departments=department,
                status=Sprint.Status.RUNNING,
            )
            .prefetch_related("sources")
            .order_by("updated_at")
        )

        if not running_sprints:
            return None

        sprint = running_sprints[0]

        workforce = AgentModel.objects.filter(
            department=department,
            is_leader=False,
            status=AgentModel.Status.ACTIVE,
        )
        if not workforce.exists():
            return None

        # Filter out orphaned reviewers whose creator pair is not active
        active_types = set(workforce.values_list("agent_type", flat=True))
        orphaned_reviewers = set()
        for pair in self.get_review_pairs():
            if pair["creator"] not in active_types and pair["reviewer"] in active_types:
                orphaned_reviewers.add(pair["reviewer"])
                logger.info(
                    "ORPHANED_REVIEWER dept=%s reviewer=%s — creator %s is not active, excluding from task proposals",
                    department.name,
                    pair["reviewer"],
                    pair["creator"],
                )

        agents_desc = []
        for a in workforce:
            if a.agent_type in orphaned_reviewers:
                continue
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

        completed_tasks = list(
            AgentTask.objects.filter(
                sprint=sprint,
                status__in=[AgentTask.Status.DONE, AgentTask.Status.PROCESSING],
            )
            .order_by("-created_at")
            .values_list("exec_summary", "report")[:20]
        )
        completed_text = []
        for summary, report in completed_tasks:
            entry = summary
            if report:
                entry += f"\n  Result: {report}"
            completed_text.append(entry)

        # Write a progress document if there are completed tasks to capture
        if completed_tasks:
            self._write_sprint_progress_document(department, sprint, completed_tasks)

        from projects.models import Document

        docs = list(Document.objects.filter(department=department).values_list("title", flat=True)[:20])

        source_context = ""
        for src in sprint.sources.all()[:5]:
            text = src.summary or src.extracted_text or src.raw_content or ""
            if text:
                source_context += f"\n- {src.original_filename or 'Attached file'}: {text}"

        locale = agent.get_config_value("locale") or "en"

        system_prompt = f"""You are a department leader advancing a specific work instruction (sprint).

You MUST respond with valid JSON only. No markdown fences, no explanation.

## Your Process
1. READ the sprint instruction carefully — this is what the user wants done.
2. REVIEW what has been completed so far for this sprint.
3. ASSESS: What's still missing? What would move this sprint closest to completion?
4. PROPOSE: The most impactful next task(s) to advance the sprint.
5. COMPLETE: If the sprint goal has been fully met with excellence, set "sprint_done" to true.

## Rules
- Every task MUST advance the sprint instruction. Do not invent unrelated work.
- Propose ONE task (or a small chain if they form a logical unit).
- Each task must target a specific agent by agent_type with a specific command_name.
- The step_plan must be detailed — reference specific project details, characters, themes, goals.
- All output in {locale}.
- If you believe the sprint is COMPLETE (goal fully met), set "sprint_done": true and provide "completion_summary".

## Response JSON Schema
{{{{
    "sprint_done": false,
    "completion_summary": "",
    "exec_summary": "Brief description of what this task achieves",
    "tasks": [
        {{{{
            "target_agent_type": "agent_type_slug",
            "command_name": "command_name",
            "exec_summary": "What this specific agent should deliver",
            "step_plan": "Detailed, actionable instructions for the agent...",
            "depends_on_previous": false
        }}}}
    ]
}}}}"""

        notes_text = self._format_sprint_notes(sprint)

        user_message = f"""# Project: {project.name}

## Project Goal
{project.goal or "No goal set."}

## Sprint Instruction
{sprint.text}

## Sprint Context Files
{source_context or "None."}

{notes_text}

## Leader Instructions
{agent.instructions or "No specific instructions."}

## Available Agents
{json.dumps(agents_desc, indent=2)}

## Work Completed So Far (for this sprint)
{json.dumps(completed_text) if completed_text else "Nothing yet — this sprint just started."}

## Department Documents
{json.dumps(docs) if docs else "None yet."}

What is the next step to advance this sprint toward completion?"""

        try:
            response, _usage = call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=4096,
            )
            result = parse_json_response(response)
            if not result:
                logger.warning("Leader %s: failed to parse sprint proposal", agent.name)
                return None

            if result.get("sprint_done"):
                sprint.status = Sprint.Status.DONE
                sprint.completion_summary = result.get("completion_summary", "Sprint completed.")
                sprint.completed_at = timezone.now()
                sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

                from projects.views.sprint_view import _broadcast_sprint

                _broadcast_sprint(sprint, "sprint.updated")
                logger.info("Leader %s declared sprint done: %s", agent.name, sprint.text[:60])
                return None

            result["_sprint_id"] = str(sprint.id)
            return result

        except Exception as e:
            logger.exception("Leader %s: sprint proposal failed: %s", agent.name, e)
            return None

    def _write_sprint_progress_document(self, department, sprint, completed_tasks):
        """Write a sprint progress document capturing completed task results."""
        from projects.models import Document

        batch_num = (
            Document.objects.filter(
                department=department,
                sprint=sprint,
                document_type="sprint_progress",
            ).count()
            + 1
        )

        last_progress = (
            Document.objects.filter(
                department=department,
                sprint=sprint,
                document_type="sprint_progress",
            )
            .order_by("-created_at")
            .first()
        )

        if last_progress:
            new_tasks = [(summary, report) for summary, report in completed_tasks if report]
            existing_task_count = sum(
                1 for line in (last_progress.content or "").split("\n") if line.startswith("## Task:")
            )
            if len(new_tasks) <= existing_task_count:
                return

        content_parts = [f"# Sprint Progress — Batch {batch_num}\n"]
        content_parts.append(f"**Sprint:** {sprint.text}\n")

        from django.utils import timezone

        content_parts.append(f"**Date:** {timezone.now().strftime('%Y-%m-%d %H:%M')}\n")

        for summary, report in completed_tasks:
            content_parts.append(f"\n## Task: {summary}\n")
            if report:
                content_parts.append(f"{report}\n")
            else:
                content_parts.append("*No report provided.*\n")

        Document.objects.create(
            title=f"Sprint Progress — {sprint.text[:50]} — Batch {batch_num}",
            content="\n".join(content_parts),
            department=department,
            document_type="sprint_progress",
            doc_type=Document.DocType.GENERAL,
            sprint=sprint,
        )


# ── Deferred import — placed here to avoid circular imports ─────────────────
# projects.tasks_consolidation imports from agents.ai, so importing at the top
# of this module would create a cycle. Importing at the bottom (after all class
# definitions) is safe and puts the name in the module namespace for patching.
from projects.tasks_consolidation import consolidate_department_documents  # noqa: E402

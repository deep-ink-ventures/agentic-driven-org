from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import (
    EXCELLENCE_THRESHOLD,
    NEAR_EXCELLENCE_THRESHOLD,
    LeaderBlueprint,
)

logger = logging.getLogger(__name__)

# ── Pipeline definition ────────────────────────────────────────────────────

DEFAULT_PROFILES_PER_AREA = 50

PIPELINE_STEPS = [
    "research",
    "strategy",
    "personalization",  # fan-out step — N clones, one per target area
    "finalize",  # strategist consolidation → exec summary + CSV
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "research": "researcher",
    "strategy": "strategist",
    "personalization": "pitch_personalizer",  # clones
    "finalize": "strategist",
    "qa_review": "sales_qa",
    "dispatch": None,  # outreach agents
}

STEP_TO_COMMAND = {
    "research": "research-industry",
    "strategy": "draft-strategy",
    "personalization": "personalize-pitches",
    "finalize": "finalize-outreach",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}

# Maps QA dimensions to agent types for cascade fix routing
DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "strategist",
    "profile_accuracy": "strategist",
    "pitch_personalization": "strategist",
}

# Revision commands per agent (used when QA routes fixes)
AGENT_FIX_COMMANDS = {
    "researcher": "research-industry",
    "strategist": "revise-strategy",
}

CHAIN_ORDER = [
    "researcher",
    "strategist",
]

# Context injection: which prior steps feed into each step
STEP_CONTEXT_SOURCES = {
    "research": [],
    "strategy": ["research"],
    "personalization": ["research", "strategy"],
    "finalize": ["personalization"],
    "qa_review": ["research", "strategy", "finalize"],
    "dispatch": ["finalize"],
}

TARGET_AREA_PATTERN = re.compile(
    r"###\s*Target\s*Area\s*\d+[:\s]*(.*?)(?=###\s*Target\s*Area\s*\d+|###\s*Priority\s*Ranking|###\s*Risks|$)",
    re.DOTALL | re.IGNORECASE,
)


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Head of Sales"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates a fan-out pipeline from industry research "
        "through personalized outreach with QA feedback loop"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "orchestration"]
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the sales pipeline: research → strategy → personalization (fan-out) → "
                "finalize → QA → outreach dispatch"
            ),
        },
        {
            "name": "QA Cascade Routing",
            "description": (
                "Route QA failures to the earliest failing agent in the chain. "
                "Re-run from that point forward, not just the last step."
            ),
        },
        {
            "name": "Outreach Discovery",
            "description": (
                "Discover available outreach channels by querying agents with outreach=True. "
                "Pass channel list to strategist for assignment."
            ),
        },
    ]
    config_schema = {
        "max_target_areas": {
            "type": "int",
            "description": "Maximum number of target areas the strategist produces per sprint. Each area spawns one clone agent.",
            "label": "Max Target Areas",
            "default": 5,
        },
        "include_inactive_outreach": {
            "type": "bool",
            "description": "Include inactive outreach agents as channels in the CSV. Their rows won't be auto-dispatched but can be used for manual outreach.",
            "label": "Include Inactive Outreach Channels",
            "default": False,
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are the Head of Sales. You orchestrate a pipeline of specialized agents to produce personalized outreach campaigns.

YOUR PIPELINE:
1. researcher: Industry research, competitive intel, market trends (web search, cheap model)
2. strategist: Draft thesis with 3-5 target areas, narrative arc, outreach storyline
3. pitch_personalizer (fan-out): N clones, one per target area — each finds profiles and personalizes pitches
4. strategist (finalize): Consolidate clone outputs into exec summary + CSV
5. sales_qa: Multi-dimensional quality review of the entire pipeline
6. Outreach dispatch: Send approved pitches via available outreach agents

OUTREACH DISCOVERY:
Query your department for agents with outreach=True to discover available channels.
Pass the list to the strategist so it can assign channels in the strategy.

You don't write pitches or do research directly — you create tasks for your workforce."""

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
        # Find the active sprint
        from projects.models import Sprint

        department = agent.department
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
        dept_id = str(department.id)

        # 3. Determine current pipeline step from sprint state
        dept_state = sprint.get_department_state(dept_id)
        current_step = dept_state.get("pipeline_step")

        if current_step is None:
            current_step = "research"
            dept_state["pipeline_step"] = current_step
            sprint.set_department_state(dept_id, dept_state)

        # 4. Route to appropriate handler
        if current_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if current_step == "personalization":
            return self._handle_personalization_step(agent, sprint)

        # Linear steps: research, strategy, finalize, qa_review
        return self._handle_linear_step(agent, sprint, current_step)

    def _handle_linear_step(self, agent: Agent, sprint, current_step: str) -> dict | None:
        """Handle a linear (non-fan-out) pipeline step."""
        from agents.models import AgentTask

        department = agent.department
        step_agent_type = STEP_TO_AGENT.get(current_step)
        step_command = STEP_TO_COMMAND.get(current_step)

        if not step_agent_type:
            return None

        step_done = AgentTask.objects.filter(
            sprint=sprint,
            agent__agent_type=step_agent_type,
            agent__department=department,
            command_name=step_command,
            status=AgentTask.Status.DONE,
        ).exists()

        if not step_done:
            # Check if task is already in progress or queued
            step_active = AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=step_agent_type,
                agent__department=department,
                command_name=step_command,
                status__in=[
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.QUEUED,
                    AgentTask.Status.AWAITING_APPROVAL,
                    AgentTask.Status.PLANNED,
                ],
            ).exists()

            if step_active:
                return None  # Wait for it

            # Propose this step's task
            return self._propose_step_task(agent, sprint, current_step)

        # Step is done — persist document if applicable, then advance
        self._persist_step_document(agent, sprint, current_step)
        return self._advance_to_next_step(agent, sprint, current_step)

    def _handle_personalization_step(self, agent: Agent, sprint) -> dict | None:
        """Handle the personalization fan-out/join step."""
        from agents.models import AgentTask, ClonedAgent

        department = agent.department

        # Check if clones exist yet
        clone_count = ClonedAgent.objects.filter(
            sprint=sprint,
            parent__agent_type="pitch_personalizer",
            parent__department=department,
        ).count()

        if clone_count == 0:
            # Need to create clones — parse target areas from strategy output
            return self._create_clones_and_dispatch(agent, sprint)

        # Clones exist — check if all clone tasks are done.
        # Primary query: tasks linked via cloned_agent FK.
        clone_tasks = AgentTask.objects.filter(
            sprint=sprint,
            cloned_agent__sprint=sprint,
            command_name="personalize-pitches",
        )
        # Fallback: tasks may exist without cloned_agent FK set (legacy key mismatch).
        if not clone_tasks.exists():
            clone_tasks = AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="pitch_personalizer",
                agent__department=department,
                command_name="personalize-pitches",
            )

        if not clone_tasks.exists():
            # Clones exist but tasks not yet created (race condition — another worker
            # returned the proposal but tasks.py hasn't committed the AgentTasks yet).
            # Wait for the tasks to appear rather than creating duplicate clones.
            return None

        pending = clone_tasks.exclude(status=AgentTask.Status.DONE)
        if pending.exists():
            return None  # Wait for all clones to finish

        # All clones done — advance to finalize
        return self._advance_to_next_step(agent, sprint, "personalization")

    def _create_clones_and_dispatch(self, agent: Agent, sprint) -> dict | None:
        """Parse target areas from strategy output, create clones, and dispatch tasks."""
        from agents.models import AgentTask

        department = agent.department

        # Get strategy output
        strategy_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=department,
                command_name="draft-strategy",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        if not strategy_task or not strategy_task.report:
            logger.warning("SALES_NO_STRATEGY dept=%s — cannot fan out without strategy", department.name)
            return None

        max_areas = agent.get_config_value("max_target_areas", 5)
        target_areas = self._parse_target_areas(strategy_task.report, max_areas=max_areas)
        if not target_areas:
            logger.warning("SALES_NO_TARGET_AREAS dept=%s — no target areas found in strategy", department.name)
            return None

        # Get research output for context
        research_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="researcher",
                agent__department=department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        research_context = research_task.report if research_task and research_task.report else ""

        # Find parent agent
        parent = department.agents.filter(agent_type="pitch_personalizer", status="active").first()
        if not parent:
            logger.warning("SALES_NO_PERSONALIZER dept=%s", department.name)
            return None

        # Create clones
        clones = self.create_clones(
            parent,
            len(target_areas),
            sprint,
            initial_state={"target_count": DEFAULT_PROFILES_PER_AREA},
        )

        # Build tasks
        tasks = []
        for i, (area_name, area_content) in enumerate(target_areas):
            clone = clones[i]
            step_plan = (
                f"## Sprint Instruction\n{sprint.text}\n\n"
                f"## Research Output\n{research_context}\n\n"
                f"## Strategy Output\n{strategy_task.report}\n\n"
                f"## Your Target Area\n### {area_name}\n{area_content}\n\n"
                f"Find {DEFAULT_PROFILES_PER_AREA} profiles for this target area and personalize pitches for each."
            )
            tasks.append(
                {
                    "target_agent_type": "pitch_personalizer",
                    "command_name": "personalize-pitches",
                    "exec_summary": f"Personalize pitches — {area_name.strip()}",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                    "_cloned_agent_id": str(clone.id),
                }
            )

        return {
            "exec_summary": f"Fan-out personalization — {len(target_areas)} target areas",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _parse_target_areas(self, strategy_text: str, max_areas: int = 5) -> list[tuple[str, str]]:
        """Extract target areas from strategy output. Returns list of (name, content) tuples.

        Hard-caps to max_areas. If the strategy produced more, they are silently dropped.
        """
        matches = list(TARGET_AREA_PATTERN.finditer(strategy_text))
        areas = []
        for match in matches:
            full = match.group(0).strip()
            name = match.group(1).strip() if match.group(1) else f"Area {len(areas) + 1}"
            areas.append((name, full))
        if len(areas) > max_areas:
            logger.warning(
                "TARGET_AREA_CAP parsed=%d cap=%d — truncating to top %d",
                len(areas),
                max_areas,
                max_areas,
            )
            areas = areas[:max_areas]
        return areas

    def _advance_to_next_step(self, agent: Agent, sprint, current_step: str) -> dict | None:
        """Advance from current_step to the next pipeline step."""
        step_idx = PIPELINE_STEPS.index(current_step)
        if step_idx + 1 >= len(PIPELINE_STEPS):
            return None

        # After finalize completes, assemble CSV from personalizer outputs (code, not LLM)
        if current_step == "finalize":
            self._assemble_csv_output(agent, sprint)

        next_step = PIPELINE_STEPS[step_idx + 1]
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        dept_state["pipeline_step"] = next_step
        sprint.set_department_state(dept_id, dept_state)

        if next_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if next_step == "personalization":
            return self._handle_personalization_step(agent, sprint)

        return self._propose_step_task(agent, sprint, next_step)

    def _assemble_csv_output(self, agent: Agent, sprint) -> None:
        """Assemble CSV from personalizer clone outputs — no LLM needed.

        Personalizer reports use structured markdown:
          ## Pitch for [Name] — [Company]
          **Identifier:** email@example.com
          **Outreach channel:** email_outreach
          ### Personalized Pitch
          **Subject:** ...
          **Body:**
          ... pitch text ...
          ---

        We also try ```csv blocks as a fallback.
        """
        import csv
        import io

        from agents.models import AgentTask
        from projects.models import Output

        clone_tasks = AgentTask.objects.filter(
            sprint=sprint,
            cloned_agent__sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.DONE,
        )

        rows = []
        for task in clone_tasks:
            if not task.report:
                continue
            report = task.report

            # Strategy 1: parse structured markdown pitch payloads
            rows.extend(self._extract_pitches_from_markdown(report))

            # Strategy 2 (fallback): look for ```csv blocks
            if not rows:
                csv_blocks = re.findall(r"```csv\s*\n(.*?)```", report, re.DOTALL)
                for block in csv_blocks:
                    reader = csv.DictReader(io.StringIO(block.strip()))
                    for row in reader:
                        if row.get("identifier"):
                            rows.append(row)

        if not rows:
            logger.warning("No pitch payloads extracted from personalizer outputs for sprint %s", sprint.id)
            return

        # Deduplicate by identifier
        seen = set()
        unique_rows = []
        for row in rows:
            ident = row.get("identifier", "").strip().lower()
            if ident and ident not in seen:
                seen.add(ident)
                unique_rows.append(row)

        # Write CSV output
        output_buffer = io.StringIO()
        fieldnames = ["channel", "identifier", "subject", "content"]
        writer = csv.DictWriter(output_buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in unique_rows:
            writer.writerow(row)

        csv_content = output_buffer.getvalue()

        Output.objects.update_or_create(
            sprint=sprint,
            department=agent.department,
            label="outreach_csv",
            defaults={
                "title": f"Outreach CSV — {len(unique_rows)} prospects",
                "output_type": Output.OutputType.PLAINTEXT,
                "content": csv_content,
            },
        )
        logger.info("Assembled outreach CSV: %d rows for sprint %s", len(unique_rows), sprint.id)

    @staticmethod
    def _extract_pitches_from_markdown(report: str) -> list[dict]:
        """Extract pitch payloads from personalizer markdown output."""
        pitches = []

        # Split on pitch headers: ## Pitch for ...
        sections = re.split(r"(?=^## Pitch for )", report, flags=re.MULTILINE)

        for section in sections:
            if not section.startswith("## Pitch for"):
                continue

            # Extract identifier (email, LinkedIn, etc.)
            ident_match = re.search(r"\*\*Identifier:\*\*\s*(.+?)(?:\n|$)", section)
            if not ident_match:
                continue
            identifier = ident_match.group(1).strip()

            # Extract channel
            channel_match = re.search(r"\*\*Outreach channel:\*\*\s*(.+?)(?:\n|$)", section)
            channel = channel_match.group(1).strip() if channel_match else "email"

            # Extract subject
            subject_match = re.search(r"\*\*Subject:\*\*\s*(.+?)(?:\n|$)", section)
            subject = subject_match.group(1).strip() if subject_match else ""

            # Extract body — text after **Body:** until next ## or ---
            body_match = re.search(
                r"\*\*Body:\*\*\s*\n(.*?)(?=\n---|\n## |\n### Personalization|\Z)",
                section,
                re.DOTALL,
            )
            content = body_match.group(1).strip() if body_match else ""

            if identifier and (subject or content):
                pitches.append(
                    {
                        "channel": channel,
                        "identifier": identifier,
                        "subject": subject,
                        "content": content,
                    }
                )

        return pitches

    def _handle_dispatch_step(self, agent: Agent, sprint) -> dict | None:
        """Handle the dispatch step — send to outreach agents or finalize sprint."""
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        department = agent.department
        # All outreach agents (active + inactive) — inactive ones are skipped
        # at dispatch but their CSV rows remain in the output for manual use.
        all_outreach = list(department.agents.filter(outreach=True))
        active_outreach = [a for a in all_outreach if a.status == AgentModel.Status.ACTIVE]
        inactive_outreach = [a for a in all_outreach if a.status != AgentModel.Status.ACTIVE]

        if not all_outreach:
            logger.warning("SALES_NO_OUTREACH dept=%s — no outreach agents available", department.name)
            return None

        if inactive_outreach:
            skipped = ", ".join(f"{a.name} ({a.agent_type})" for a in inactive_outreach)
            logger.info(
                "SALES_OUTREACH_SKIPPED dept=%s inactive=%s — CSV rows preserved for manual dispatch",
                department.name,
                skipped,
            )

        # Only track tasks for active outreach agents
        if not active_outreach:
            # No active agents — write output and complete (all channels are manual)
            self._write_sprint_output(agent, sprint)
            self.destroy_sprint_clones(sprint)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = (
                "Sales pipeline complete — all outreach channels inactive, CSV ready for manual dispatch."
            )
            sprint.completed_at = timezone.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

            from projects.views.sprint_view import _broadcast_sprint

            _broadcast_sprint(sprint, "sprint.updated")
            logger.info("SALES_SPRINT_DONE dept=%s (manual dispatch) sprint=%s", department.name, sprint.text[:60])
            return None

        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__in=active_outreach,
            command_name="send-outreach",
        )
        pending = outreach_tasks.exclude(status=AgentTask.Status.DONE)

        if outreach_tasks.exists() and not pending.exists():
            # All active agents dispatched — write output and mark sprint done
            self._write_sprint_output(agent, sprint)
            self.destroy_sprint_clones(sprint)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = "Sales pipeline complete — outreach dispatched."
            sprint.completed_at = timezone.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

            from projects.views.sprint_view import _broadcast_sprint

            _broadcast_sprint(sprint, "sprint.updated")
            logger.info("SALES_SPRINT_DONE dept=%s sprint=%s", department.name, sprint.text[:60])
            return None

        if not outreach_tasks.exists():
            return self._propose_dispatch_tasks(agent, sprint, active_outreach)

        # Some still running — wait
        return None

    def _propose_step_task(self, agent: Agent, sprint, step: str) -> dict:
        """Propose a task for a specific pipeline step, injecting context from prior steps."""
        from agents.models import AgentTask

        agent_type = STEP_TO_AGENT[step]
        command_name = STEP_TO_COMMAND[step]

        # Gather context from prior steps
        context_parts = []
        source_steps = STEP_CONTEXT_SOURCES.get(step, [])
        for src_step in source_steps:
            if src_step == "personalization":
                # Gather all clone task outputs
                clone_tasks = AgentTask.objects.filter(
                    sprint=sprint,
                    cloned_agent__sprint=sprint,
                    command_name="personalize-pitches",
                    status=AgentTask.Status.DONE,
                ).select_related("cloned_agent")
                for ct in clone_tasks:
                    label = f"Personalizer Clone {ct.cloned_agent.clone_index}" if ct.cloned_agent else "Personalizer"
                    if ct.report:
                        context_parts.append(f"## {label} Output\n{ct.report}")
            else:
                src_agent_type = STEP_TO_AGENT[src_step]
                src_command = STEP_TO_COMMAND[src_step]
                src_task = (
                    AgentTask.objects.filter(
                        sprint=sprint,
                        agent__agent_type=src_agent_type,
                        agent__department=agent.department,
                        command_name=src_command,
                        status=AgentTask.Status.DONE,
                    )
                    .order_by("-completed_at")
                    .first()
                )
                if src_task and src_task.report:
                    step_label = src_step.replace("_", " ").title()
                    context_parts.append(f"## {step_label} Output\n{src_task.report}")

        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        # For strategy step, inject available outreach agents
        extra_context = ""
        if step == "strategy":
            outreach_qs = agent.department.agents.filter(outreach=True)
            if not agent.get_config_value("include_inactive_outreach", False):
                outreach_qs = outreach_qs.filter(status="active")
            outreach_agents = list(outreach_qs.values_list("agent_type", "name"))
            if outreach_agents:
                agents_list = ", ".join(f"{name} ({atype})" for atype, name in outreach_agents)
                extra_context = f"\n\n## Available Outreach Channels\nAvailable channels for assignment: {agents_list}"

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}"
            f"{extra_context}\n\n"
            f"Execute your command based on the above context."
        )

        tasks = [
            {
                "target_agent_type": agent_type,
                "command_name": command_name,
                "exec_summary": f"Sales pipeline — {step.replace('_', ' ')}",
                "step_plan": step_plan,
                "depends_on_previous": False,
            },
        ]

        # During QA review, also dispatch authenticity analyst if available
        if step == "qa_review":
            active_types = set(
                agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
            )
            if "authenticity_analyst" in active_types:
                tasks.append(
                    {
                        "target_agent_type": "authenticity_analyst",
                        "command_name": "analyze",
                        "exec_summary": "Authenticity check — detect AI-generated patterns in pitches",
                        "step_plan": (
                            f"## Personalized Pitches to Analyze\n{context_text}\n\n"
                            f"Analyze the personalized pitch texts for AI-generated patterns. "
                            f"Focus on: linguistic tells, voice flattening across pitches, "
                            f"cliche/default patterns, and coherence. Each pitch should read "
                            f"as genuinely human-written, not template-generated."
                        ),
                        "depends_on_previous": False,
                    }
                )

        return {
            "exec_summary": f"Sales pipeline step: {step.replace('_', ' ')}",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _propose_dispatch_tasks(self, agent: Agent, sprint, outreach_agents) -> dict:
        """Propose outreach tasks — one per outreach agent with assigned pitches."""
        from agents.models import AgentTask

        # Get finalize output (from strategist finalize-outreach command)
        finalize_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=agent.department,
                command_name="finalize-outreach",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        pitch_output = finalize_task.report if finalize_task else "No pitch payloads available."

        tasks = []
        for outreach_agent in outreach_agents:
            tasks.append(
                {
                    "target_agent_type": outreach_agent.agent_type,
                    "command_name": "send-outreach",
                    "exec_summary": f"Send outreach emails via {outreach_agent.name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Approved Pitch Payloads\n{pitch_output}\n\n"
                        f"Send all pitches assigned to your channel ({outreach_agent.agent_type})."
                    ),
                    "depends_on_previous": False,
                }
            )

        return {
            "exec_summary": "Dispatch approved pitches to outreach agents",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _propose_fix_task(
        self, agent: Agent, review_task: AgentTask, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """Override: route QA fixes to the earliest failing agent in the chain."""
        report = review_task.report or ""

        earliest_failing = self._find_earliest_failing_agent(report, score)

        if earliest_failing is None:
            earliest_failing = "strategist"

        fix_command = AGENT_FIX_COMMANDS.get(earliest_failing, "revise-strategy")
        polish_msg = f" (polish {polish_count}/3)" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

        return {
            "exec_summary": (
                f"Fix {earliest_failing.replace('_', ' ')} issues "
                f"(score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}"
            ),
            "tasks": [
                {
                    "target_agent_type": earliest_failing,
                    "command_name": fix_command,
                    "exec_summary": (f"Fix QA issues — {earliest_failing.replace('_', ' ')} " f"(score {score}/10)"),
                    "step_plan": (
                        f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                        f"Review round: {round_num}. Polish attempts: {polish_count}/3.\n\n"
                        f"The QA specialist has flagged issues. Fix the problems below.\n\n"
                        f"## QA Report\n{report}\n\n"
                        f"Address the issues in your area. After fixing, the pipeline "
                        f"continues from your output forward."
                    ),
                    "depends_on_previous": False,
                },
            ],
        }

    def _find_earliest_failing_agent(self, report: str, overall_score: float) -> str | None:
        """Parse QA report for per-dimension scores, return earliest failing agent."""
        failing_agents = []

        for dimension, agent_type in DIMENSION_TO_AGENT.items():
            patterns = [
                rf"{dimension}[:\s—\-]+(\d+\.?\d*)\s*/?\s*10?",
                rf"{dimension}.*?(\d+\.?\d*)/10",
                rf"{dimension}.*?score[:\s]+(\d+\.?\d*)",
            ]
            for pattern in patterns:
                match = re.search(pattern, report, re.IGNORECASE)
                if match:
                    dim_score = float(match.group(1))
                    if dim_score < EXCELLENCE_THRESHOLD:
                        failing_agents.append(agent_type)
                    break

        if not failing_agents:
            return None

        for agent_type in CHAIN_ORDER:
            if agent_type in failing_agents:
                return agent_type

        return failing_agents[0]

    def _persist_step_document(self, agent: Agent, sprint, step: str) -> None:
        """Persist research and strategy outputs as Department Documents."""
        from agents.models import AgentTask
        from projects.models import Document

        doc_types = {
            "research": (Document.DocType.RESEARCH, "Industry Research Briefing"),
            "strategy": (Document.DocType.STRATEGY, "Target Area Strategy"),
        }
        if step not in doc_types:
            return

        doc_type, title_prefix = doc_types[step]
        agent_type = STEP_TO_AGENT[step]

        task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=agent_type,
                agent__department=agent.department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if not task or not task.report:
            return

        existing = Document.objects.filter(
            department=agent.department,
            doc_type=doc_type,
            sprint=sprint,
        ).first()

        if existing:
            existing.content = task.report
            existing.save(update_fields=["content", "updated_at"])
        else:
            Document.objects.create(
                title=f"{title_prefix} — {sprint.text[:50]}",
                content=task.report,
                department=agent.department,
                doc_type=doc_type,
                sprint=sprint,
            )

    def _write_sprint_output(self, agent: Agent, sprint) -> None:
        """Write the sprint Output when outreach dispatch completes."""
        from agents.models import AgentTask
        from projects.models import Output

        if Output.objects.filter(sprint=sprint, department=agent.department).exists():
            return

        # Write exec summary from finalize step
        finalize_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=agent.department,
                agent__agent_type="strategist",
                command_name="finalize-outreach",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if finalize_task and finalize_task.report:
            Output.objects.create(
                sprint=sprint,
                department=agent.department,
                title=f"Executive Summary — {sprint.text[:80]}",
                label="exec-summary",
                output_type=Output.OutputType.MARKDOWN,
                content=finalize_task.report,
            )

        # Write outreach delivery reports
        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__department=agent.department,
            agent__outreach=True,
            status=AgentTask.Status.DONE,
        )

        report_parts = ["# Sales Outreach — Sprint Output\n"]
        for task in outreach_tasks:
            report_parts.append(f"## {task.agent.name}\n{task.report or 'No report.'}\n")

        Output.objects.create(
            sprint=sprint,
            department=agent.department,
            title=f"Sales Outreach — {sprint.text[:80]}",
            label="outreach",
            output_type=Output.OutputType.MARKDOWN,
            content="\n".join(report_parts),
        )

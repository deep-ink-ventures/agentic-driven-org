from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import (
    LeaderBlueprint,
)

logger = logging.getLogger(__name__)

# ── Pipeline definition ────────────────────────────────────────────────────

DEFAULT_PROSPECTS_PER_AREA = 10

PIPELINE_STEPS = [
    "ideation",
    "discovery",  # fan-out — 1 researcher clone per target area
    "prospect_gate",  # authenticity_analyst verifies prospect lists
    "copywriting",  # fan-out — 1 personalizer clone per area
    "copy_gate",  # authenticity_analyst verifies pitches
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "ideation": "strategist",
    "discovery": "researcher",
    "prospect_gate": "authenticity_analyst",
    "copywriting": "pitch_personalizer",
    "copy_gate": "authenticity_analyst",
    "qa_review": "sales_qa",
    "dispatch": None,
}

STEP_TO_COMMAND = {
    "ideation": "identify-targets",
    "discovery": "discover-prospects",
    "prospect_gate": "verify-prospects",
    "copywriting": "write-pitches",
    "copy_gate": "verify-pitches",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}

FAN_OUT_STEPS = {
    "discovery": {
        "agent_type": "researcher",
        "command": "discover-prospects",
        "source_step": "ideation",
        "source_command": "identify-targets",
    },
    "copywriting": {
        "agent_type": "pitch_personalizer",
        "command": "write-pitches",
        "source_step": "ideation",
        "source_command": "identify-targets",
    },
}

STEP_CONTEXT_SOURCES = {
    "ideation": [],
    "discovery": ["ideation"],
    "prospect_gate": ["discovery"],
    "copywriting": ["ideation", "discovery", "prospect_gate"],
    "copy_gate": ["copywriting"],
    "qa_review": ["ideation", "prospect_gate", "copywriting", "copy_gate"],
    "dispatch": ["copywriting"],
}

TARGET_AREA_PATTERN = re.compile(
    r"###\s*Target\s*Area\s*\d+[:\s]*(.*?)(?=###\s*Target\s*Area\s*\d+|###\s*Priority\s*Ranking|###\s*Risks|$)",
    re.DOTALL | re.IGNORECASE,
)


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Head of Sales"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates a multiplier-first pipeline from "
        "ideation through verified prospect discovery, copywriting, and outreach dispatch"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "orchestration"]
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the multiplier-first sales pipeline: ideation → discovery (fan-out) → "
                "prospect gate → copywriting (fan-out) → copy gate → QA → dispatch"
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
            "description": "Include inactive outreach agents as channels. Their rows won't be auto-dispatched but can be used for manual outreach.",
            "label": "Include Inactive Outreach Channels",
            "default": False,
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are the Head of Sales. You orchestrate a multiplier-first pipeline of specialized agents to produce verified, personalized B2B outreach campaigns.

YOUR PIPELINE:
1. strategist (ideation): Identify 3-5 multiplier target areas — organizations and individuals who control many bookings
2. researcher (discovery, fan-out): N clones, one per target area — web-search for real decision-makers at multiplier orgs
3. authenticity_analyst (prospect gate): Verify all discovered prospects are real — audit citations, flag fabrication
4. pitch_personalizer (copywriting, fan-out): N clones, one per area — B2B partnership copywriting from verified prospect data only
5. authenticity_analyst (copy gate): Verify pitches don't fabricate claims — audit against verified prospect data
6. sales_qa (QA review): Multi-dimensional quality review of the entire pipeline
7. Outreach dispatch: Send approved pitches via available outreach agents

CORE PRINCIPLE:
Sales targets multiplier gatekeepers — organizations and individuals who control many bookings. One deal = 10-50+ recurring bookings.

You don't write pitches or do research directly — you create tasks for your workforce."""

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
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

        # Determine current pipeline step from sprint state
        dept_state = sprint.get_department_state(dept_id)
        current_step = dept_state.get("pipeline_step")

        if current_step is None:
            current_step = "ideation"
            dept_state["pipeline_step"] = current_step
            sprint.set_department_state(dept_id, dept_state)

        # Route to appropriate handler
        if current_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if current_step in FAN_OUT_STEPS:
            return self._handle_fan_out_step(agent, sprint, current_step)

        # Linear steps: ideation, prospect_gate, copy_gate, qa_review
        return self._handle_linear_step(agent, sprint, current_step)

    def _handle_linear_step(self, agent: Agent, sprint, current_step: str) -> dict | None:
        """Handle a linear (non-fan-out) pipeline step."""
        from agents.models import AgentTask

        department = agent.department
        step_agent_type = STEP_TO_AGENT.get(current_step)

        if not step_agent_type:
            return None

        # After a QA loop-back, only count tasks created after the loop-back as "done".
        # Otherwise old completed tasks from previous rounds trick the step-done check.
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        since = dept_state.get("qa_loopback_at")

        task_qs = AgentTask.objects.filter(
            sprint=sprint,
            agent__agent_type=step_agent_type,
            agent__department=department,
        )
        if since:
            from django.utils.dateparse import parse_datetime as _parse_dt

            dt = _parse_dt(since)
            if dt:
                task_qs = task_qs.filter(created_at__gte=dt)

        step_done = task_qs.filter(status=AgentTask.Status.DONE).exists()

        if not step_done:
            step_active = task_qs.filter(
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

        # QA review quality gate: only advance if score meets threshold
        if current_step == "qa_review":
            review_task = (
                AgentTask.objects.filter(
                    sprint=sprint,
                    agent__agent_type="sales_qa",
                    agent__department=department,
                    command_name="review-pipeline",
                    status=AgentTask.Status.DONE,
                )
                .order_by("-completed_at")
                .first()
            )
            if review_task and review_task.review_score is not None:
                accepted, polish_count, round_num = self._apply_quality_gate(
                    agent,
                    sprint,
                    review_task.review_score,
                    "sales_qa",
                )
                if not accepted:
                    logger.info(
                        "Sales QA: score %.1f — looping back to ideation (round %d)",
                        review_task.review_score,
                        round_num,
                    )
                    return self._loop_back_from_qa(agent, sprint, review_task, round_num)

        # Step is done — persist document if applicable, then advance
        self._persist_step_document(agent, sprint, current_step)
        return self._advance_to_next_step(agent, sprint, current_step)

    def _handle_fan_out_step(self, agent: Agent, sprint, step: str) -> dict | None:
        """Handle a fan-out pipeline step (discovery or copywriting)."""
        from agents.models import AgentTask, ClonedAgent

        department = agent.department
        fan_config = FAN_OUT_STEPS[step]
        agent_type = fan_config["agent_type"]
        command = fan_config["command"]

        # Check if clones exist yet
        clone_count = ClonedAgent.objects.filter(
            sprint=sprint,
            parent__agent_type=agent_type,
            parent__department=department,
        ).count()

        if clone_count == 0:
            # Need to create clones — parse target areas from ideation output
            return self._create_fan_out_tasks(agent, sprint, step)

        # Clones exist — check if all clone tasks are done.
        # Primary query: tasks linked via cloned_agent FK.
        clone_tasks = AgentTask.objects.filter(
            sprint=sprint,
            cloned_agent__sprint=sprint,
            command_name=command,
        )
        # Fallback: tasks may exist without cloned_agent FK set (legacy key mismatch).
        if not clone_tasks.exists():
            clone_tasks = AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=agent_type,
                agent__department=department,
                command_name=command,
            )

        if not clone_tasks.exists():
            # Clones exist but tasks not yet created (race condition — another worker
            # returned the proposal but tasks.py hasn't committed the AgentTasks yet).
            # Wait for the tasks to appear rather than creating duplicate clones.
            return None

        pending = clone_tasks.exclude(status=AgentTask.Status.DONE)
        if pending.exists():
            return None  # Wait for all clones to finish

        # All clones done — advance to next step
        return self._advance_to_next_step(agent, sprint, step)

    def _create_fan_out_tasks(self, agent: Agent, sprint, step: str) -> dict | None:
        """Parse target areas from ideation output, create clones, and dispatch tasks."""
        from agents.models import AgentTask

        department = agent.department
        fan_config = FAN_OUT_STEPS[step]
        agent_type = fan_config["agent_type"]
        command = fan_config["command"]
        source_command = fan_config["source_command"]

        # Get ideation output
        ideation_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=department,
                command_name=source_command,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        if not ideation_task or not ideation_task.report:
            logger.warning("SALES_NO_IDEATION dept=%s — cannot fan out without ideation output", department.name)
            return None

        max_areas = agent.get_config_value("max_target_areas", 5)
        target_areas = self._parse_target_areas(ideation_task.report, max_areas=max_areas)
        if not target_areas:
            logger.warning("SALES_NO_TARGET_AREAS dept=%s — no target areas found in ideation", department.name)
            return None

        # Find parent agent
        parent = department.agents.filter(agent_type=agent_type, status="active").first()
        if not parent:
            logger.warning("SALES_NO_PARENT_%s dept=%s", agent_type.upper(), department.name)
            return None

        # Create clones
        clones = self.create_clones(
            parent,
            len(target_areas),
            sprint,
            initial_state={"target_count": DEFAULT_PROSPECTS_PER_AREA},
        )

        # Gather context from prior steps
        context_parts = self._gather_step_context(agent, sprint, step)
        context_text = "\n\n".join(context_parts) if context_parts else ""

        # Build tasks
        tasks = []
        for i, (area_name, area_content) in enumerate(target_areas):
            clone = clones[i]

            if step == "discovery":
                instruction = (
                    f"Find up to {DEFAULT_PROSPECTS_PER_AREA} verified prospects for this target area. "
                    f"Every prospect must cite a real source. Zero fabrication."
                )
            else:  # copywriting
                instruction = (
                    "Write personalized B2B partnership pitches using ONLY the passed verified prospects. "
                    "Do not invent new prospects or fabricate claims."
                )

            step_plan = (
                f"## Sprint Instruction\n{sprint.text}\n\n" f"{context_text}\n\n"
                if context_text
                else f"## Sprint Instruction\n{sprint.text}\n\n"
            )
            step_plan += f"## Your Target Area\n### {area_name}\n{area_content}\n\n" f"{instruction}"

            tasks.append(
                {
                    "target_agent_type": agent_type,
                    "command_name": command,
                    "exec_summary": f"{step.replace('_', ' ').title()} — {area_name.strip()}",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                    "_cloned_agent_id": str(clone.id),
                }
            )

        return {
            "exec_summary": f"Fan-out {step} — {len(target_areas)} target areas",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _gather_step_context(self, agent: Agent, sprint, step: str) -> list[str]:
        """Gather context from prior pipeline steps."""
        from agents.models import AgentTask

        context_parts = []
        source_steps = STEP_CONTEXT_SOURCES.get(step, [])
        for src_step in source_steps:
            if src_step in FAN_OUT_STEPS:
                # Gather all clone outputs
                fan_config = FAN_OUT_STEPS[src_step]
                clone_tasks = AgentTask.objects.filter(
                    sprint=sprint,
                    cloned_agent__sprint=sprint,
                    command_name=fan_config["command"],
                    status=AgentTask.Status.DONE,
                ).select_related("cloned_agent")
                for ct in clone_tasks:
                    label = (
                        f"{src_step.title()} Clone {ct.cloned_agent.clone_index}"
                        if ct.cloned_agent
                        else src_step.title()
                    )
                    if ct.report:
                        context_parts.append(f"## {label} Output\n{ct.report}")
            else:
                src_agent_type = STEP_TO_AGENT.get(src_step)
                src_command = STEP_TO_COMMAND.get(src_step)
                if not src_agent_type or not src_command:
                    continue
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
        return context_parts

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

    def _loop_back_from_qa(self, agent, sprint, review_task, round_num) -> dict:
        """QA score too low — loop back to ideation."""
        dept_id = str(agent.department_id)
        from django.utils import timezone as tz

        dept_state = sprint.get_department_state(dept_id)
        dept_state["pipeline_step"] = "ideation"
        dept_state["qa_loopback_at"] = tz.now().isoformat()
        sprint.set_department_state(dept_id, dept_state)

        return self._propose_step_task(agent, sprint, "ideation")

    def _advance_to_next_step(self, agent: Agent, sprint, current_step: str) -> dict | None:
        """Advance from current_step to the next pipeline step."""
        step_idx = PIPELINE_STEPS.index(current_step)
        if step_idx + 1 >= len(PIPELINE_STEPS):
            return None

        next_step = PIPELINE_STEPS[step_idx + 1]
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        dept_state["pipeline_step"] = next_step
        sprint.set_department_state(dept_id, dept_state)

        if next_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if next_step in FAN_OUT_STEPS:
            return self._handle_fan_out_step(agent, sprint, next_step)

        return self._propose_step_task(agent, sprint, next_step)

    def _handle_dispatch_step(self, agent: Agent, sprint) -> dict | None:
        """Handle the dispatch step — send to outreach agents or finalize sprint."""
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        department = agent.department
        # All outreach agents (active + inactive) — inactive ones are skipped
        # at dispatch but their rows remain in the output for manual use.
        all_outreach = list(department.agents.filter(outreach=True))
        active_outreach = [a for a in all_outreach if a.status == AgentModel.Status.ACTIVE]
        inactive_outreach = [a for a in all_outreach if a.status != AgentModel.Status.ACTIVE]

        if not all_outreach:
            logger.warning("SALES_NO_OUTREACH dept=%s — no outreach agents available", department.name)
            return None

        if inactive_outreach:
            skipped = ", ".join(f"{a.name} ({a.agent_type})" for a in inactive_outreach)
            logger.info(
                "SALES_OUTREACH_SKIPPED dept=%s inactive=%s — rows preserved for manual dispatch",
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
                "Sales pipeline complete — all outreach channels inactive, ready for manual dispatch."
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
        agent_type = STEP_TO_AGENT[step]
        command_name = STEP_TO_COMMAND[step]

        context_parts = self._gather_step_context(agent, sprint, step)
        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}\n\n"
            f"Execute your command based on the above context."
        )

        return {
            "exec_summary": f"Sales pipeline step: {step.replace('_', ' ')}",
            "_sprint_id": str(sprint.id),
            "tasks": [
                {
                    "target_agent_type": agent_type,
                    "command_name": command_name,
                    "exec_summary": f"Sales pipeline — {step.replace('_', ' ')}",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                },
            ],
        }

    def _propose_dispatch_tasks(self, agent: Agent, sprint, outreach_agents) -> dict:
        """Propose outreach tasks — one per outreach agent with approved pitches."""
        context_parts = self._gather_step_context(agent, sprint, "dispatch")
        context_text = "\n\n".join(context_parts) if context_parts else "No pitch payloads available."

        tasks = []
        for outreach_agent in outreach_agents:
            tasks.append(
                {
                    "target_agent_type": outreach_agent.agent_type,
                    "command_name": "send-outreach",
                    "exec_summary": f"Send outreach via {outreach_agent.name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Approved Pitch Payloads\n{context_text}\n\n"
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

    def _persist_step_document(self, agent: Agent, sprint, step: str) -> None:
        """Persist ideation output as a Department Document."""
        from agents.models import AgentTask
        from projects.models import Document

        doc_types = {
            "ideation": (Document.DocType.STRATEGY, "Multiplier Target Areas"),
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

        # Write campaign strategy from ideation step
        ideation_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=agent.department,
                agent__agent_type="strategist",
                command_name="identify-targets",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if ideation_task and ideation_task.report:
            Output.objects.create(
                sprint=sprint,
                department=agent.department,
                title=f"Campaign Strategy — {sprint.text[:80]}",
                label="campaign-strategy",
                output_type=Output.OutputType.MARKDOWN,
                content=ideation_task.report,
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

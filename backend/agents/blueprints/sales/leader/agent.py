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

PIPELINE_STEPS = [
    "research",
    "strategy",
    "pitch_design",
    "profile_selection",
    "personalization",
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "research": "researcher",
    "strategy": "strategist",
    "pitch_design": "pitch_architect",
    "profile_selection": "profile_selector",
    "personalization": "pitch_personalizer",
    "qa_review": "sales_qa",
    "dispatch": None,  # dispatches to all outreach agents
}

STEP_TO_COMMAND = {
    "research": "research-industry",
    "strategy": "draft-strategy",
    "pitch_design": "design-storyline",
    "profile_selection": "select-profiles",
    "personalization": "personalize-pitches",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}

# Maps QA dimensions to agent types for cascade fix routing
DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "pitch_architect",
    "profile_accuracy": "profile_selector",
    "pitch_personalization": "pitch_personalizer",
}

# Revision commands per agent (used when QA routes fixes)
AGENT_FIX_COMMANDS = {
    "researcher": "research-industry",
    "strategist": "revise-strategy",
    "pitch_architect": "revise-storyline",
    "profile_selector": "revise-profiles",
    "pitch_personalizer": "revise-pitches",
}

CHAIN_ORDER = [
    "researcher",
    "strategist",
    "pitch_architect",
    "profile_selector",
    "pitch_personalizer",
]

# Context injection: which prior steps feed into each step
STEP_CONTEXT_SOURCES = {
    "research": [],
    "strategy": ["research"],
    "pitch_design": ["research", "strategy"],
    "profile_selection": ["strategy"],
    "personalization": ["pitch_design", "profile_selection"],
    "qa_review": ["research", "strategy", "pitch_design", "profile_selection", "personalization"],
    "dispatch": ["personalization"],
}


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Head of Sales"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates a 7-agent pipeline from industry research "
        "through personalized outreach with QA feedback loop"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "orchestration"]
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the sequential sales pipeline: research → strategy → pitch design → "
                "profile selection → personalization → QA → outreach dispatch"
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
                "Pass channel list to personalizer for assignment."
            ),
        },
    ]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "pitch_personalizer",
                "creator_fix_command": "revise-pitches",
                "reviewer": "sales_qa",
                "reviewer_command": "review-pipeline",
                "dimensions": [
                    "research_accuracy",
                    "strategy_quality",
                    "storyline_effectiveness",
                    "profile_accuracy",
                    "pitch_personalization",
                ],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the Head of Sales. You orchestrate a pipeline of specialized agents to produce personalized outreach campaigns.

YOUR PIPELINE (sequential — each step feeds the next):
1. researcher: Industry research, competitive intel, market trends (web search, cheap model)
2. strategist: Draft thesis with 3-5 target areas based on research
3. pitch_architect: Design the outreach storyline and narrative arc
4. profile_selector: Compile concrete persons to outreach to per target area (web search)
5. pitch_personalizer: Personalize the storyline for each person, assign outreach channel
6. sales_qa: Multi-dimensional quality review of the entire pipeline
7. Outreach dispatch: Send approved pitches via available outreach agents

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When the pitch_personalizer completes, the system automatically routes to sales_qa.
- Score >= 9.5/10 → approved, dispatch to outreach
- Score >= 9.0 after 3 polish attempts → accept (diminishing returns)
- Score < threshold → system routes fix to the earliest failing agent in the chain
Do NOT manually create review tasks — the system handles the loop.

OUTREACH DISCOVERY:
Query your department for agents with outreach=True to discover available channels.
Pass the list to the pitch_personalizer so it can assign channels per person.

You don't write pitches or do research directly — you create tasks for your workforce."""

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
        # 1. Check for review cycle triggers first (base class handles QA ping-pong)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result

        # 2. Find the active sprint
        from agents.models import AgentTask
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
        sprint_id = str(sprint.id)

        # 3. Determine current pipeline step
        internal_state = agent.internal_state or {}
        pipeline_steps = internal_state.get("pipeline_steps", {})
        current_step = pipeline_steps.get(sprint_id, None)

        if current_step is None:
            current_step = "research"
            pipeline_steps[sprint_id] = current_step
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

        # 4. Check if current step is done
        step_agent_type = STEP_TO_AGENT.get(current_step)
        step_command = STEP_TO_COMMAND.get(current_step)

        if current_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint, sprint_id, internal_state, pipeline_steps)

        # For non-dispatch steps, check if the step's task is done
        if step_agent_type:
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

            step_idx = PIPELINE_STEPS.index(current_step)
            if step_idx + 1 < len(PIPELINE_STEPS):
                next_step = PIPELINE_STEPS[step_idx + 1]
                pipeline_steps[sprint_id] = next_step
                internal_state["pipeline_steps"] = pipeline_steps
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])

                if next_step == "dispatch":
                    return self._handle_dispatch_step(agent, sprint, sprint_id, internal_state, pipeline_steps)

                return self._propose_step_task(agent, sprint, next_step)

        return None

    def _handle_dispatch_step(
        self, agent: Agent, sprint, sprint_id: str, internal_state: dict, pipeline_steps: dict
    ) -> dict | None:
        """Handle the dispatch step — send to outreach agents or finalize sprint."""
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        department = agent.department
        outreach_agents = list(department.agents.filter(outreach=True, status=AgentModel.Status.ACTIVE))
        if not outreach_agents:
            logger.warning("SALES_NO_OUTREACH dept=%s — no outreach agents available", department.name)
            return None

        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__in=outreach_agents,
            command_name="send-outreach",
        )
        pending = outreach_tasks.exclude(status=AgentTask.Status.DONE)

        if outreach_tasks.exists() and not pending.exists():
            # All dispatched — write output and mark sprint done
            self._write_sprint_output(agent, sprint)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = "Sales pipeline complete — outreach dispatched."
            sprint.completed_at = timezone.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

            from projects.views.sprint_view import _broadcast_sprint

            _broadcast_sprint(sprint, "sprint.updated")
            logger.info("SALES_SPRINT_DONE dept=%s sprint=%s", department.name, sprint.text[:60])

            # Clean up pipeline state
            pipeline_steps.pop(sprint_id, None)
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return None

        if not outreach_tasks.exists():
            return self._propose_dispatch_tasks(agent, sprint, outreach_agents)

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
            src_agent_type = STEP_TO_AGENT[src_step]
            src_task = (
                AgentTask.objects.filter(
                    sprint=sprint,
                    agent__agent_type=src_agent_type,
                    agent__department=agent.department,
                    status=AgentTask.Status.DONE,
                )
                .order_by("-completed_at")
                .first()
            )
            if src_task and src_task.report:
                step_label = src_step.replace("_", " ").title()
                context_parts.append(f"## {step_label} Output\n{src_task.report}")

        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        # For personalization step, inject outreach agents list
        extra_context = ""
        if step == "personalization":
            outreach_agents = list(
                agent.department.agents.filter(outreach=True, status="active").values_list("agent_type", "name")
            )
            if outreach_agents:
                agents_list = ", ".join(f"{name} ({atype})" for atype, name in outreach_agents)
                extra_context = f"\n\n## Available Outreach Channels\n" f"Assign each pitch to one of: {agents_list}"

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}"
            f"{extra_context}\n\n"
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
        """Propose outreach tasks — one per outreach agent with assigned pitches."""
        from agents.models import AgentTask

        personalizer_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="pitch_personalizer",
                agent__department=agent.department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        pitch_output = personalizer_task.report if personalizer_task else "No pitch payloads available."

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
            earliest_failing = "pitch_personalizer"

        fix_command = AGENT_FIX_COMMANDS.get(earliest_failing, "revise-pitches")
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

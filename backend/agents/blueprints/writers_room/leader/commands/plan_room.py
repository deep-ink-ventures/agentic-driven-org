"""Leader command: plan the writers room — assess state and assign next round of work."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="plan-room",
    description="Assess project state, determine current stage, assign creative or feedback tasks for the ping-pong loop",
    schedule="daily",
    model="claude-sonnet-4-6",
)
def plan_room(self, agent: Agent) -> dict | None:
    """
    Daily planning command. Evaluates the full state of the writers room
    and proposes the next batch of work via generate_task_proposal.
    """
    from agents.ai.claude_client import call_claude, parse_json_response
    from agents.models import AgentTask

    department = agent.department
    internal_state = agent.internal_state or {}
    stage_status = internal_state.get("stage_status", {})
    current_stage = internal_state.get("current_stage", "pitch")
    terminal_stage = internal_state.get("terminal_stage", "treatment")
    format_type = internal_state.get("format_type", "standalone")

    # Merge config
    config = {
        **(department.project.config or {}),
        **(department.config or {}),
        **(agent.config or {}),
    }
    locale = config.get("locale", "en")

    # Gather completed work
    completed = list(
        AgentTask.objects.filter(
            agent__department=department,
            status=AgentTask.Status.DONE,
        )
        .order_by("-completed_at")[:30]
        .values_list("exec_summary", "agent__agent_type", "report")
    )
    completed_text = "\n".join(f"- ({at}) {es}" for es, at, _ in completed) if completed else "No completed tasks yet."

    # Gather active work
    active = list(
        AgentTask.objects.filter(
            agent__department=department,
            status__in=[
                AgentTask.Status.PROCESSING,
                AgentTask.Status.QUEUED,
                AgentTask.Status.PROCESSING,
                AgentTask.Status.AWAITING_APPROVAL,
            ],
        ).values_list("exec_summary", "status", "agent__agent_type")
    )
    active_text = "\n".join(f"- [{st}] ({at}) {es}" for es, st, at in active) if active else "No active tasks."

    # Workforce agents
    workforce = list(agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type"))
    workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

    context_msg = self.build_context_message(agent)

    msg = f"""{context_msg}

# Writers Room State
Current stage: {current_stage}
Terminal stage: {terminal_stage}
Format type: {format_type}
Locale: {locale}
Stage status: {json.dumps(stage_status, indent=2)}

# 4-Stage Pipeline
The pipeline runs: pitch → expose → treatment → first_draft
The terminal_stage determines where the pipeline stops (set when the sprint was created).

# Workforce Agents
{workforce_desc}

The team includes a **lead_writer** who synthesizes the creative team's output into a
single cohesive stage deliverable after each round of creative writing is complete.
Feedback agents then critique that synthesized deliverable.

# Completed Work
{completed_text}

# Active Work
{active_text}

# Task
Assess the writers room state. What should happen next?

Consider:
1. If active work is in progress, report status and wait.
2. If a stage needs creative agents to write, assign them.
3. Once creative writing is done, assign the lead_writer to synthesize a deliverable.
4. Once the lead_writer deliverable exists, assign feedback agents to critique it.
5. If feedback has been received, evaluate whether the stage passes.
6. If we've reached terminal_stage with passing scores, report completion.

For any new work, specify tasks with target_agent_type matching the workforce.

Respond with JSON:
{{
    "assessment": "Brief status assessment",
    "recommendation": "What should happen next",
    "tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "What to do",
            "step_plan": "Detailed steps",
            "depends_on_previous": false
        }}
    ]
}}"""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="plan-room"),
    )

    data = parse_json_response(response)
    if not data:
        logger.warning("Failed to parse plan-room response: %s", response[:300])
        return None

    tasks = data.get("tasks", [])
    if not tasks:
        return {
            "exec_summary": data.get("assessment", "Writers room status check"),
            "step_plan": data.get("recommendation", "No action needed."),
        }

    return {
        "exec_summary": data.get("assessment", f"Writers room: plan for stage '{current_stage}'"),
        "tasks": tasks,
    }

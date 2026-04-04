"""Leader command: propose the highest-value initiative for the department's workforce."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="create-priority-task", description="Propose the highest-value initiative — may involve one or multiple agents", schedule="hourly")
def create_priority_task(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude
    from agents.models import AgentTask

    workforce = list(
        agent.department.agents.filter(is_active=True, is_leader=False)
        .values_list("id", "name", "agent_type")
    )
    if not workforce:
        return None

    workforce_desc = "\n".join(f"- {name} ({atype})" for _, name, atype in workforce)

    awaiting_by_agent = {}
    for wid, wname, wtype in workforce:
        count = AgentTask.objects.filter(agent_id=wid, status=AgentTask.Status.AWAITING_APPROVAL).count()
        awaiting_by_agent[wname] = count

    awaiting_text = "\n".join(f"- {name}: {count} tasks awaiting" for name, count in awaiting_by_agent.items())

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Workforce Agents
{workforce_desc}

# Current Approval Queue
{awaiting_text}

# Task
Propose the single highest-value initiative for this department. This may involve one agent or multiple agents working together.

Consider:
- Recent research findings (web researcher, lu.ma researcher)
- Current campaign status and messaging
- Engagement metrics and timing
- Project goal alignment

For each agent that should be involved, create a task with clear branding and tone instructions. If only one agent is needed, that's fine too.

Respond with JSON:
{{
    "exec_summary": "One-line description of the initiative",
    "tasks": [
        {{
            "target_agent_type": "agent type from the list above",
            "exec_summary": "What this agent should do",
            "step_plan": "Detailed step-by-step plan with branding/tone guidance"
        }}
    ]
}}"""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="create-priority-task"),
    )

    try:
        data = json.loads(response)
        tasks = data.get("tasks", [])
        if not tasks:
            return None
        # Return the first task for the chain, but include all tasks
        # The caller (create_next_leader_task) will create tasks for each
        return {
            "exec_summary": data.get("exec_summary", "Priority initiative"),
            "tasks": tasks,
        }
    except (json.JSONDecodeError, KeyError):
        logger.warning("Failed to parse create-priority-task response: %s", response[:200])
        return None

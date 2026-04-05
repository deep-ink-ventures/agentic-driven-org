"""Leader command: propose the highest-value initiative for the department's workforce."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="create-priority-task",
    description="Propose the highest-value initiative — may involve one or multiple agents",
    schedule="hourly",
)
def create_priority_task(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude
    from agents.models import AgentTask

    workforce = list(
        agent.department.agents.filter(status="active", is_leader=False).values_list("id", "name", "agent_type")
    )
    if not workforce:
        return None

    workforce_desc = ""
    for _wid, wname, wtype in workforce:
        workforce_desc += f"- {wname} ({wtype})"
        try:
            from agents.blueprints import get_blueprint

            bp = get_blueprint(wtype, agent.department.department_type)
            cmds = bp.get_commands()
            if cmds:
                cmd_names = ", ".join(c["name"] for c in cmds)
                workforce_desc += f"\n  Commands: {cmd_names}"
        except Exception:  # noqa: BLE001, S110
            pass
        workforce_desc += "\n"

    awaiting_by_agent = {}
    for wid, wname, _wtype in workforce:
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
            "command_name": "specific command to invoke (from the agent's commands list)",
            "exec_summary": "What this agent should do",
            "step_plan": "Detailed step-by-step plan with branding/tone guidance",
            "depends_on_previous": false
        }}
    ]
}}

IMPORTANT:
- Set depends_on_previous to true if this task needs the previous task's results.
- For research, always create research-gather first, then research-analyze with depends_on_previous: true.
- Use the exact command names from each agent's commands list."""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="create-priority-task"),
    )

    from agents.ai.claude_client import parse_json_response

    data = parse_json_response(response)
    if not data:
        logger.warning("Failed to parse create-priority-task response: %s", response[:200])
        return None
    tasks = data.get("tasks", [])
    if not tasks:
        return None
    return {
        "exec_summary": data.get("exec_summary", "Priority initiative"),
        "tasks": tasks,
    }

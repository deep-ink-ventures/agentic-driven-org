"""Leader command: compile performance reports from all agents."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(name="analyze-performance", description="Compile reports from all agents, identify what's working, adjust strategy")
def analyze_performance(self, agent: Agent) -> dict:
    from agents.ai.claude_client import call_claude

    context_msg = self.build_context_message(agent)
    msg = f"""{context_msg}

# Task
Analyze the department's recent performance based on all agents' task reports. Identify:
1. What campaigns/content performed well and why
2. What underperformed and what to change
3. Strategic recommendations for next period
4. Specific tasks to create for improvement

Respond with JSON:
{{
    "performance_summary": "Overview of department performance",
    "wins": ["What worked well"],
    "issues": ["What needs improvement"],
    "recommendations": ["Strategic suggestions"],
    "proposed_tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "Task to improve performance",
            "step_plan": "Detailed steps"
        }}
    ]
}}"""

    response, _usage = call_claude(
        system_prompt=self.build_system_prompt(agent),
        user_message=msg,
        model=self.get_model(agent, command_name="analyze-performance"),
    )

    try:
        return json.loads(response)
    except (json.JSONDecodeError, KeyError):
        return {"performance_summary": response, "wins": [], "issues": [], "recommendations": [], "proposed_tasks": []}

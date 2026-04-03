from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.twitter.skills import format_skills

logger = logging.getLogger(__name__)


class TwitterBlueprint(BaseBlueprint):
    name = "Twitter Agent"
    slug = "twitter"
    description = "Manages Twitter/X presence — engagement, posting, trend monitoring"

    @property
    def system_prompt(self) -> str:
        return """You are a Twitter/X social media agent. Your role is to grow the project's presence on Twitter/X through strategic engagement and content creation.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing. You coordinate with the campaign agent when campaigns are active.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "tweet", "content": "...", "hashtags": ["..."]},
        {"type": "reply", "target_url": "...", "content": "..."},
        {"type": "retweet", "target_url": "..."},
        {"type": "like", "target_url": "..."},
        {"type": "search", "query": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with the project's branding guidelines and voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly engagement routine:
1. Search for 10 relevant high-impact tweets in the project's domain
2. Engage authentically with the best ones (like, reply, retweet)
3. If appropriate, post one original tweet that adds value

Focus on building genuine connections, not spam. Quality over quantity."""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and your recent work, propose the single highest-value task you could do next on Twitter/X.

Consider:
- What content gaps exist?
- Are there trending topics to capitalize on?
- Is there engagement to follow up on?
- Are there campaign tasks that need Twitter support?

Respond with JSON:
{
    "exec_summary": "One-line description of the task",
    "step_plan": "Detailed step-by-step plan of what you will do"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        task_msg = f"""{context_msg}

# Task to Execute
**Summary:** {task.exec_summary}
**Plan:** {task.step_plan}

Execute this task now. Respond with your actions JSON and report."""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
        )

        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.browser import run_browser_action
                run_browser_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        from agents.ai.claude_client import call_claude

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Task Proposal Request
{self.task_generation_prompt}"""

        response = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
        )

        try:
            data = json.loads(response)
            return {
                "exec_summary": data.get("exec_summary", "Twitter engagement task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {"exec_summary": "Twitter engagement task", "step_plan": response}

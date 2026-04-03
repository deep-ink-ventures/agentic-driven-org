from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import BaseBlueprint
from agents.blueprints.reddit.skills import format_skills

logger = logging.getLogger(__name__)


class RedditBlueprint(BaseBlueprint):
    name = "Reddit Agent"
    slug = "reddit"
    description = "Manages Reddit presence — posting, commenting, community engagement"

    @property
    def system_prompt(self) -> str:
        return """You are a Reddit social media agent. Your role is to build the project's presence on Reddit through valuable contributions to relevant communities.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing. You coordinate with the campaign agent when campaigns are active.

Reddit values authenticity and hates spam. Your contributions must be genuinely helpful and add value to discussions. Never be overtly promotional.

When executing tasks, respond with a JSON object containing your actions:
{
    "actions": [
        {"type": "post", "subreddit": "...", "title": "...", "content": "..."},
        {"type": "comment", "target_url": "...", "content": "..."},
        {"type": "search", "query": "...", "subreddit": "..."}
    ],
    "report": "Summary of what was done and why"
}

Always align your content with subreddit rules and the project's voice."""

    @property
    def hourly_prompt(self) -> str:
        return """Perform your hourly Reddit engagement routine:
1. Browse 3-5 relevant subreddits for discussions where you can add value
2. Leave 2-3 thoughtful, helpful comments on active threads
3. If there's a good opportunity, create one valuable post

Focus on being a genuine community member. Provide value first, brand visibility follows naturally."""

    @property
    def task_generation_prompt(self) -> str:
        return """Based on the current project context, department activity, and your recent work, propose the single highest-value task you could do next on Reddit.

Consider:
- Which subreddits have active discussions you can contribute to?
- Is there original content worth sharing?
- Are there questions in the community you can answer with expertise?
- Are there campaign tasks that need Reddit support?

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
                "exec_summary": data.get("exec_summary", "Reddit engagement task"),
                "step_plan": data.get("step_plan", response),
            }
        except (json.JSONDecodeError, KeyError):
            return {"exec_summary": "Reddit engagement task", "step_plan": response}

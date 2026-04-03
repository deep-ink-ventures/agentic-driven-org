from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint, command
from agents.blueprints.social_media.workforce.reddit.skills import format_skills

logger = logging.getLogger(__name__)


class RedditBlueprint(WorkforceBlueprint):
    name = "Reddit Agent"
    slug = "reddit"
    description = "Manages Reddit presence — posting, commenting, community engagement"

    @property
    def system_prompt(self) -> str:
        return """You are a Reddit social media agent. Your role is to build the project's presence on Reddit through valuable contributions to relevant communities.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing.

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
    def skills_description(self) -> str:
        return format_skills()

    @command(name="engage-subreddits", description="Browse and engage in relevant subreddit discussions", schedule="hourly")
    def engage_subreddits(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Browse relevant subreddits and engage in valuable discussions",
            "step_plan": "1. Browse 3-5 relevant subreddits\n2. Find discussions where we can add value\n3. Leave 2-3 thoughtful comments\n4. Focus on genuine community participation",
        }

    @command(name="post-content", description="Create a valuable post in a relevant subreddit", schedule="daily")
    def post_content(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Create and post valuable content in a relevant subreddit",
            "step_plan": "1. Identify the best subreddit for the content\n2. Review subreddit rules\n3. Draft a post that provides genuine value\n4. Post and monitor responses",
        }

    @command(name="monitor-mentions", description="Search Reddit for brand or project mentions", schedule=None)
    def monitor_mentions(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Search Reddit for mentions of the project, brand, or relevant keywords",
            "step_plan": "1. Search for brand mentions\n2. Search for relevant keyword discussions\n3. Report findings and engagement opportunities",
        }

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

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.social_media.workforce.reddit.skills import format_skills
from agents.blueprints.social_media.workforce.reddit.commands import engage_subreddits, post_content, monitor_mentions

logger = logging.getLogger(__name__)


class RedditBlueprint(WorkforceBlueprint):
    name = "Reddit Agent"
    slug = "reddit"
    description = "Manages Reddit presence — posting, commenting, community engagement"
    tags = ["social-media", "reddit", "community", "content-creation"]

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

    # Register commands
    engage_subreddits = engage_subreddits
    post_content = post_content
    monitor_mentions = monitor_mentions

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        task_msg = self.build_task_message(agent, task, suffix="Respond with your actions JSON and report.")

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

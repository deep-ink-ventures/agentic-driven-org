from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint, command
from agents.blueprints.social_media.workforce.twitter.skills import format_skills

logger = logging.getLogger(__name__)


class TwitterBlueprint(WorkforceBlueprint):
    name = "Twitter Agent"
    slug = "twitter"
    description = "Manages Twitter/X presence — engagement, posting, trend monitoring"

    @property
    def system_prompt(self) -> str:
        return """You are a Twitter/X social media agent. Your role is to grow the project's presence on Twitter/X through strategic engagement and content creation.

You operate within a department and are aware of your project's goals, branding guidelines, and what other agents in your department are doing.

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
    def skills_description(self) -> str:
        return format_skills()

    @command(name="engage-tweets", description="Find and engage with relevant high-impact tweets", schedule="hourly")
    def engage_tweets(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Engage with relevant high-impact tweets in the project's domain",
            "step_plan": "1. Search for trending and relevant tweets\n2. Identify 10 high-impact tweets\n3. Engage authentically (like, reply, retweet)\n4. Focus on building genuine connections",
        }

    @command(name="post-content", description="Create and post original tweet content", schedule="daily")
    def post_content(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Create and post an original tweet aligned with project goals",
            "step_plan": "1. Review project goals and branding guidelines\n2. Check recent posts to avoid repetition\n3. Draft a tweet that adds value to the audience\n4. Post with relevant hashtags",
        }

    @command(name="search-trends", description="Search for trending topics in the project's domain", schedule=None)
    def search_trends(self, agent: Agent) -> dict:
        return {
            "exec_summary": "Search Twitter for trending topics relevant to the project",
            "step_plan": "1. Search trending hashtags and topics\n2. Identify opportunities for engagement or content\n3. Report findings",
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

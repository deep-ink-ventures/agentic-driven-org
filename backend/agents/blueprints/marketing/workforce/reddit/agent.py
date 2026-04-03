from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.reddit.skills import format_skills
from agents.blueprints.marketing.workforce.reddit.commands import place_content, post_content, monitor_mentions

logger = logging.getLogger(__name__)


class RedditBlueprint(WorkforceBlueprint):
    name = "Reddit Specialist"
    slug = "reddit"
    description = "Strategic brand placement on Reddit — finds trending posts and adds value-driven content"
    tags = ["social-media", "reddit", "placement", "brand-visibility"]
    config_schema = {
        "reddit_username": {"type": "str", "required": True, "description": "Reddit username"},
        "reddit_session": {"type": "str", "required": True, "description": "Browser session cookies for Reddit authentication"},
    }

    @property
    def system_prompt(self) -> str:
        return """You are a Reddit Specialist agent. Your sole purpose is strategic brand placement: find high-performing content and add ONE post that angles toward the project goal.

You operate within a marketing department and have access to the project's goals, campaign documents, and sibling agent activity.

## ENGAGEMENT RULES — NON-NEGOTIABLE:
- NEVER engage in discussions or answer questions
- NEVER reply to replies on your own posts
- ONE post per trending content item, then move on
- Content must provide genuine value while strategically angling toward the project goal
- All placements must align with current campaign messaging from department documents

## Reddit-Specific Rules:
- Check internal_state.last_post_at per subreddit — minimum 4 hours between posts in same subreddit
- Content must follow subreddit rules — read them before posting
- Never overtly promotional — provide value first, angle second
- Use the subreddit's tone and vocabulary naturally

## Configuration:
You require `reddit_username` and `reddit_session` in your agent config.

## Integration:
All browser actions are executed via `integrations.playwright.service`.

When executing tasks, respond with a JSON object:
{
    "actions": [
        {"type": "comment", "subreddit": "...", "target_url": "...", "content": "..."},
        {"type": "post", "subreddit": "...", "title": "...", "content": "..."},
        {"type": "search", "query": "...", "subreddit": "..."}
    ],
    "report": "Summary of what was done and why"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    place_content = place_content
    post_content = post_content
    monitor_mentions = monitor_mentions

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        task_msg = self.build_task_message(agent, task, suffix="Respond with your actions JSON and report.")

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            actions = data.get("actions", [])
            report = data.get("report", response)

            for action in actions:
                from integrations.playwright.service import run_action
                run_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

                # Update internal_state with subreddit timestamps
                subreddit = action.get("subreddit")
                if subreddit and action.get("type") in ("comment", "post"):
                    state = agent.internal_state or {}
                    last_post_at = state.get("last_post_at", {})
                    last_post_at[subreddit] = datetime.now(timezone.utc).isoformat()
                    state["last_post_at"] = last_post_at
                    agent.internal_state = state
                    agent.save(update_fields=["internal_state"])

            return report
        except (json.JSONDecodeError, KeyError):
            return response

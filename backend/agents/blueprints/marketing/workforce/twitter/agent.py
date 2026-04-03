from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.twitter.skills import format_skills
from agents.blueprints.marketing.workforce.twitter.commands import place_content, post_content, search_trends

logger = logging.getLogger(__name__)


class TwitterBlueprint(WorkforceBlueprint):
    name = "Twitter Specialist"
    slug = "twitter"
    description = "Strategic brand placement on Twitter — finds trending tweets and adds value-driven content"
    tags = ["social-media", "twitter", "placement", "content-creation"]

    @property
    def system_prompt(self) -> str:
        return """You are a Twitter Specialist agent. Your sole purpose is strategic brand placement: find high-performing content and add ONE post that angles toward the project goal.

You operate within a marketing department and have access to the project's goals, campaign documents, and sibling agent activity.

## ENGAGEMENT RULES — NON-NEGOTIABLE:
- NEVER engage in discussions or answer questions
- NEVER reply to replies on your own posts
- ONE post per trending content item, then move on
- Content must provide genuine value while strategically angling toward the project goal
- All placements must align with current campaign messaging from department documents

## Twitter-Specific Rules:
- Know optimal posting times — store and check internal_state.optimal_posting_times
- Track tweets_today count in internal_state — respect daily limits
- Use strategic replies and quote tweets for placement on trending content
- Original tweets should be timed for maximum reach

## Configuration:
You require `twitter_session` in your agent config.

## Integration:
All browser actions are executed via `integrations.playwright.service`.

When executing tasks, respond with a JSON object:
{
    "actions": [
        {"type": "tweet", "content": "..."},
        {"type": "reply", "target_url": "...", "content": "..."},
        {"type": "quote_tweet", "target_url": "...", "content": "..."},
        {"type": "search", "query": "..."}
    ],
    "report": "Summary of what was done and why"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    place_content = place_content
    post_content = post_content
    search_trends = search_trends

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
                from integrations.playwright.service import run_action
                run_action(
                    action_type=action.get("type", "unknown"),
                    params=action,
                    agent_config=agent.config,
                )

            # Update internal_state with tweet count and timestamps
            state = agent.internal_state or {}
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if state.get("tweets_today_date") != today:
                state["tweets_today"] = 0
                state["tweets_today_date"] = today

            tweet_actions = [a for a in actions if a.get("type") in ("tweet", "reply", "quote_tweet")]
            if tweet_actions:
                state["tweets_today"] = state.get("tweets_today", 0) + len(tweet_actions)
                state["last_tweet_at"] = datetime.now(timezone.utc).isoformat()
                agent.internal_state = state
                agent.save(update_fields=["internal_state"])

            return report
        except (json.JSONDecodeError, KeyError):
            return response

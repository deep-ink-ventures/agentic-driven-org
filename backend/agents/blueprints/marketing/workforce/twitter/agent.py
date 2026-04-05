from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.twitter.commands import place_content, post_content, search_trends
from agents.blueprints.marketing.workforce.twitter.skills import format_skills

logger = logging.getLogger(__name__)


class TwitterBlueprint(WorkforceBlueprint):
    name = "Twitter Specialist"
    slug = "twitter"
    description = "Strategic brand placement on Twitter — finds trending tweets and adds value-driven content"
    tags = ["social-media", "twitter", "placement", "content-creation"]
    config_schema = {
        "twitter_session": {
            "type": "str",
            "required": True,
            "label": "Twitter Session",
            "description": "Browser session cookies for Twitter authentication",
        },
    }

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

        suffix = (
            "# EXECUTION METHODOLOGY\n\n"
            "## Strategy Alignment\n"
            "Before composing any content, review department documents for active campaign messaging, "
            "tone guidelines, and target audience. Every tweet must serve both the conversation AND the "
            "campaign objective.\n\n"
            "## Safety & Rate Limits\n"
            "- Check internal_state.tweets_today — respect daily posting limits\n"
            "- Check internal_state.optimal_posting_times — post within high-engagement windows when possible\n"
            "- ONE post per trending item, then move on. No follow-up engagement.\n"
            "- Never engage in discussions or answer questions on replies\n\n"
            "## Audience Awareness\n"
            "- Identify who is engaging with the target tweet (followers, influencers, bots)\n"
            "- Match the register of the conversation — professional threads get professional replies\n"
            "- Provide genuine value (insight, data, perspective) before angling toward the project\n\n"
            "## Measurable Outcomes\n"
            "Track and report: tweets posted (count), target tweet engagement level, "
            "placement type (reply vs quote tweet), and alignment score with campaign goals.\n\n"
            "Respond with your actions JSON and report."
        )
        task_msg = self.build_task_message(agent, task, suffix=suffix)

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

            # Update internal_state with tweet count and timestamps
            state = agent.internal_state or {}
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            if state.get("tweets_today_date") != today:
                state["tweets_today"] = 0
                state["tweets_today_date"] = today

            tweet_actions = [a for a in actions if a.get("type") in ("tweet", "reply", "quote_tweet")]
            if tweet_actions:
                state["tweets_today"] = state.get("tweets_today", 0) + len(tweet_actions)
                state["last_tweet_at"] = datetime.now(UTC).isoformat()
                agent.internal_state = state
                agent.save(update_fields=["internal_state"])

            return report
        except (json.JSONDecodeError, KeyError):
            return response

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.marketing.workforce.reddit.commands import monitor_mentions, place_content, post_content

logger = logging.getLogger(__name__)


class RedditBlueprint(WorkforceBlueprint):
    name = "Reddit Specialist"
    slug = "reddit"
    description = "Strategic brand placement on Reddit — finds trending posts and adds value-driven content"
    tags = ["social-media", "reddit", "placement", "brand-visibility"]
    skills = [
        {
            "name": "Strategic Placement",
            "description": "Add one well-crafted post on trending content that angles toward the project goal",
        },
        {
            "name": "Find Trending Posts",
            "description": "Identify high-performing posts in relevant subreddits for strategic placement",
        },
        {"name": "Monitor Mentions", "description": "Search Reddit for brand, project, or keyword mentions"},
    ]
    config_schema = {
        "reddit_username": {
            "type": "str",
            "required": True,
            "label": "Reddit Username",
            "description": "Your Reddit account username",
        },
        "reddit_session": {
            "type": "str",
            "required": True,
            "label": "Reddit Session",
            "description": "Browser session cookies for Reddit authentication",
        },
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

    # Register commands
    place_content = place_content
    post_content = post_content
    monitor_mentions = monitor_mentions

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = (
            "# EXECUTION METHODOLOGY\n\n"
            "## Strategy Alignment\n"
            "Before composing any content, review department documents for active campaign messaging, "
            "tone guidelines, and target audience. Every comment or post must serve both the subreddit "
            "community AND the campaign objective.\n\n"
            "## Safety & Cooldown Rules\n"
            "- Check internal_state.last_post_at per subreddit — enforce 4-hour minimum between posts\n"
            "- Read subreddit rules before posting — violations get accounts banned\n"
            "- ONE comment per trending post, then move on. Never reply to replies.\n"
            "- Never overtly promotional — provide value first, angle second\n\n"
            "## Subreddit Culture Adaptation\n"
            "- Study the top posts and comments in the target subreddit to match tone\n"
            "- Use the community's vocabulary and formatting conventions naturally\n"
            "- Lead with genuine insight, experience, or data before any project mention\n"
            "- Respect the unwritten norms: lurk-to-post ratio, self-promotion limits, flair requirements\n\n"
            "## Measurable Outcomes\n"
            "Track and report: subreddits engaged, post/comment type, target thread engagement level, "
            "cooldown status per subreddit, and alignment score with campaign goals.\n\n"
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

                # Update internal_state with subreddit timestamps
                subreddit = action.get("subreddit")
                if subreddit and action.get("type") in ("comment", "post"):
                    state = agent.internal_state or {}
                    last_post_at = state.get("last_post_at", {})
                    last_post_at[subreddit] = datetime.now(UTC).isoformat()
                    state["last_post_at"] = last_post_at
                    agent.internal_state = state
                    agent.save(update_fields=["internal_state"])

            return report
        except (json.JSONDecodeError, KeyError):
            return response

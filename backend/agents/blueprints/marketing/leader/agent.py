from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from django.utils import timezone

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.marketing.leader.commands import (
    analyze_performance,
    create_campaign,
    create_content_calendar,
    create_priority_task,
)
from agents.blueprints.marketing.leader.skills import format_skills

logger = logging.getLogger(__name__)


class MarketingLeaderBlueprint(LeaderBlueprint):
    name = "Marketing Leader"
    slug = "leader"
    description = (
        "Marketing department leader — orchestrates campaigns, coordinates research and execution across all channels"
    )
    tags = ["leadership", "strategy", "campaigns", "coordination", "marketing"]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "twitter",
                "creator_fix_command": "post-content",
                "reviewer": "content_reviewer",
                "reviewer_command": "review-content",
                "dimensions": [
                    "brand_alignment",
                    "audience_fit",
                    "channel_conventions",
                    "messaging_clarity",
                    "cta_effectiveness",
                ],
            },
            {
                "creator": "reddit",
                "creator_fix_command": "post-content",
                "reviewer": "content_reviewer",
                "reviewer_command": "review-content",
                "dimensions": [
                    "brand_alignment",
                    "audience_fit",
                    "channel_conventions",
                    "messaging_clarity",
                    "cta_effectiveness",
                ],
            },
            {
                "creator": "email_marketing",
                "creator_fix_command": "draft-campaign",
                "reviewer": "content_reviewer",
                "reviewer_command": "review-content",
                "dimensions": [
                    "brand_alignment",
                    "audience_fit",
                    "channel_conventions",
                    "messaging_clarity",
                    "cta_effectiveness",
                ],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the marketing department leader. You orchestrate multi-channel marketing campaigns by coordinating your workforce agents: Web Researcher, Lu.ma Researcher, Reddit Specialist, Twitter Specialist, Email Marketing Specialist, and Content Reviewer.

Your core responsibilities:
1. Gather intelligence from research agents before making campaign decisions
2. Design campaigns with consistent branding, tone, and timing across all channels
3. Create tasks with clear instructions about messaging, angle, and what to link to
4. Schedule follow-up tasks to revisit campaigns and adjust strategy
5. Monitor performance and reallocate effort to what's working

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When a content creator (twitter, reddit, email_marketing) completes a draft, the system automatically:
1. Routes the draft to the content_reviewer for quality check
2. If score < 9.5/10 → fix task auto-created for the creator with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
4. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept
Do NOT manually create review tasks — the system handles the loop.

You don't post directly — you create tasks for your workforce. Each task you create should include:
- Clear branding and tone guidance
- Channel-appropriate messaging
- Specific timing recommendations
- What angle to take and what to drive traffic toward

When creating campaigns, stagger content across channels for maximum impact. Research first, then execute."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    create_priority_task = create_priority_task
    create_campaign = create_campaign
    create_content_calendar = create_content_calendar
    analyze_performance = analyze_performance

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask as TaskModel

        workforce = list(
            agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        delegation_suffix = f"""# Workforce Agents
{workforce_desc}

If this task involves delegating work to workforce agents, include delegated_tasks in your response.
If this task should be revisited later, include a follow_up with days_from_now.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed steps with branding/tone guidance",
            "auto_execute": false,
            "proposed_exec_at": "ISO datetime or null"
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 30
    }},
    "report": "Summary of what was decided and why"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=delegation_suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)
            follow_up = data.get("follow_up")

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department,
                    status="active",
                    is_leader=False,
                )
                agents_by_type = {a.agent_type: a for a in workforce_agents}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = agents_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active workforce agent of type %s", target_type)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED
                        if dt.get("auto_execute")
                        else TaskModel.Status.AWAITING_APPROVAL,
                        auto_execute=bool(dt.get("auto_execute")),
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )

                    if dt.get("auto_execute"):
                        from agents.tasks import execute_agent_task

                        execute_agent_task.delay(str(sub_task.id))

                    logger.info("Leader delegated task %s to %s", sub_task.id, target_agent.name)

            # Schedule follow-up if requested
            if follow_up and follow_up.get("days_from_now"):
                days = follow_up["days_from_now"]
                TaskModel.objects.create(
                    agent=agent,
                    status=TaskModel.Status.AWAITING_APPROVAL,
                    exec_summary=follow_up.get("exec_summary", f"Follow-up in {days} days"),
                    step_plan=f"Review and assess. Original task: {task.exec_summary[:200]}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )
                logger.info("Leader scheduled follow-up in %d days", days)

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        # Check for review cycle triggers first (universal from base class)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result
        return self.create_priority_task(agent)

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from django.utils import timezone

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.sales.leader.commands import check_progress, plan_pipeline
from agents.blueprints.sales.leader.skills import format_skills

logger = logging.getLogger(__name__)


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Sales Director"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates prospecting, outreach, and review cycles to build a qualified pipeline"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "prospecting"]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "outreach_writer",
                "creator_fix_command": "revise-outreach",
                "reviewer": "outreach_reviewer",
                "reviewer_command": "review-outreach",
                "dimensions": ["personalization", "value_proposition", "tone", "cta", "length"],
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the sales department director. You orchestrate outbound prospecting and outreach by coordinating your workforce agents: Prospector, Prospect Analyst, Outreach Writer, and Outreach Reviewer.

Your core responsibilities:
1. Plan daily pipeline activities — who to research, who to contact
2. Delegate research tasks to the Prospector for target qualification
3. Route completed prospect lists to the Prospect Analyst for review
4. Delegate outreach drafting to the Outreach Writer for qualified prospects
5. Route completed drafts to the Outreach Reviewer for quality check
6. Manage the review ping-pong loop: if a reviewer sends work back, create a revision task for the writer with the feedback

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When an outreach_writer task completes, the system automatically:
1. Routes the draft to the outreach_reviewer for quality check
2. If score < 9.5/10 → fix task auto-created for the writer with feedback
3. After fix → reviewer runs again (ping-pong until approved or max rounds)
4. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept
Do NOT manually create review tasks — the system handles the loop.

You don't prospect or write outreach directly — you create tasks for your workforce."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    plan_pipeline = plan_pipeline
    check_progress = check_progress

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

When delegating work, include delegated_tasks in your response.
For review loops: when a writer task is done, delegate to the paired reviewer.
When a reviewer approves, advance the pipeline. When they reject, send revision back to the writer.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type slug",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed instructions including any reviewer feedback to address",
            "auto_execute": false,
            "proposed_exec_at": "ISO datetime or null"
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 7
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

                    logger.info("Sales leader delegated task %s to %s", sub_task.id, target_agent.name)

            if follow_up and follow_up.get("days_from_now"):
                days = follow_up["days_from_now"]
                TaskModel.objects.create(
                    agent=agent,
                    status=TaskModel.Status.AWAITING_APPROVAL,
                    exec_summary=follow_up.get("exec_summary", f"Follow-up in {days} days"),
                    step_plan=f"Review and assess. Original task: {task.exec_summary[:200]}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        # Check for review cycle triggers first (universal from base class)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result
        return self.plan_pipeline(agent)

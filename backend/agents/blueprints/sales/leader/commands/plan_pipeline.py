"""Sales leader command: daily pipeline planning."""

from agents.blueprints.base import command


@command(
    name="plan-pipeline",
    description=(
        "Daily pipeline review that assesses current prospects, identifies the highest-value targets to pursue, "
        "and delegates research tasks to the Prospector and outreach tasks to the Outreach Writer. Monitors "
        "review loop status and triggers reviewer tasks for completed drafts. Advances pipeline stages when "
        "reviewers approve work."
    ),
    schedule="daily",
    model="claude-sonnet-4-6",
)
def plan_pipeline(self, agent) -> dict:
    return {
        "exec_summary": "Review pipeline and plan today's prospecting and outreach activities",
        "step_plan": (
            "1. Review current pipeline state — prospects in each stage\n"
            "2. Identify highest-value targets to research or contact today\n"
            "3. Create research tasks for Prospector on new targets\n"
            "4. Create outreach tasks for Outreach Writer on researched prospects\n"
            "5. Route completed drafts to reviewers for quality check"
        ),
    }

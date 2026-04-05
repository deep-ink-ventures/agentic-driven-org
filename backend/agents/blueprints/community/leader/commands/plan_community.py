"""Community leader command: weekly ecosystem and partnership planning."""

from agents.blueprints.base import command


@command(
    name="plan-community",
    description=(
        "Weekly planning that maps ecosystem state, identifies new partnership categories, "
        "and prioritizes relationship targets. Delegates research to Ecosystem Researcher "
        "and proposal drafting to Partnership Writer. Triggers review cycles for completed work."
    ),
    schedule="weekly",
    model="claude-sonnet-4-6",
)
def plan_community(self, agent) -> dict:
    return {
        "exec_summary": "Plan this week's ecosystem research and partnership outreach",
        "step_plan": (
            "1. Review current ecosystem map and active partnerships\n"
            "2. Identify new categories or targets to research\n"
            "3. Create research tasks for Ecosystem Researcher\n"
            "4. Create proposal tasks for Partnership Writer on researched targets\n"
            "5. Route completed work to reviewers"
        ),
    }

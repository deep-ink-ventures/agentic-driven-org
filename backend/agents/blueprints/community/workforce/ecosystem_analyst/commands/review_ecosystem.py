"""Ecosystem analyst command: review ecosystem research quality."""

from agents.blueprints.base import command


@command(
    name="review-ecosystem",
    description=(
        "Review ecosystem research for completeness, strategic prioritization, and missed "
        "opportunities. Score each entity on partnership potential. Submit verdict via tool call."
    ),
    model="claude-sonnet-4-6",
)
def review_ecosystem(self, agent) -> dict:
    return {
        "exec_summary": "Review ecosystem research for quality and completeness",
        "step_plan": (
            "1. Evaluate coverage — are obvious entities missing?\n"
            "2. Check strategic prioritization\n"
            "3. Assess partnership potential scores\n"
            "4. Return verdict with specific feedback"
        ),
    }

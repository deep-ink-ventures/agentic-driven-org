"""Prospect analyst command: review prospect list quality."""

from agents.blueprints.base import command


@command(
    name="review-prospects",
    description=(
        "Review a prospect list for quality, relevance, and strategic fit. Score each prospect on "
        "completeness and actionability. Identify gaps and weak qualifications. Return verdict: "
        "approved (with scores) or revision_needed (with specific feedback per prospect)."
    ),
    model="claude-sonnet-4-6",
)
def review_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Review prospect list quality and strategic fit",
        "step_plan": (
            "1. Evaluate each prospect for completeness\n"
            "2. Score qualification rigor\n"
            "3. Identify gaps and missing information\n"
            "4. Return verdict with specific feedback"
        ),
    }

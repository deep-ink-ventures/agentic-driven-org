"""Outreach reviewer command: review outreach draft quality."""

from agents.blueprints.base import command


@command(
    name="review-outreach",
    description=(
        "Review an outreach draft for personalization depth, value proposition clarity, "
        "professional tone, appropriate length, and clear CTA. Return verdict: approved or "
        "revision_needed with line-level feedback."
    ),
    model="claude-sonnet-4-6",
)
def review_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Review outreach draft for quality and effectiveness",
        "step_plan": (
            "1. Check personalization — are specific prospect details referenced?\n"
            "2. Evaluate value proposition — is it framed in their terms?\n"
            "3. Assess tone — professional, confident, not pushy?\n"
            "4. Check CTA — specific and low-friction?\n"
            "5. Return verdict with specific feedback"
        ),
    }

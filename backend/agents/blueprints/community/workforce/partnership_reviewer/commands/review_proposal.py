"""Partnership reviewer command: review partnership proposal quality."""

from agents.blueprints.base import command


@command(
    name="review-proposal",
    description=(
        "Review a partnership proposal for mutual value clarity, professional tone, "
        "specificity, realistic structure, and clear next steps. Submit verdict via tool call."
    ),
    model="claude-opus-4-6",
)
def review_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Review partnership proposal for quality and effectiveness",
        "step_plan": (
            "1. Check mutual value — is it genuinely win-win?\n"
            "2. Assess specificity — concrete actions or vague language?\n"
            "3. Evaluate tone — professional and collaborative?\n"
            "4. Check next steps — clear and low-friction?\n"
            "5. Return verdict with specific feedback"
        ),
    }

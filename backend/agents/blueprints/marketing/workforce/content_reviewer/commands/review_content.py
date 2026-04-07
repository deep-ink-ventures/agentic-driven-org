"""Content reviewer command: review marketing content quality."""

from agents.blueprints.base import command


@command(
    name="review-content",
    description=(
        "Review a marketing content draft (tweet, Reddit post, email campaign) for brand alignment, "
        "audience fit, channel conventions, messaging clarity, and call-to-action effectiveness. "
        "Score each dimension 1-10, overall = minimum. Threshold: 9.5/10. "
        "Submit verdict via tool call."
    ),
    model="claude-opus-4-6",
)
def review_content(self, agent) -> dict:
    return {
        "exec_summary": "Review marketing content draft for quality and brand alignment",
        "step_plan": (
            "1. Check brand alignment — does tone, voice, and messaging match the project brand?\n"
            "2. Evaluate audience fit — is the content written for the right audience on this channel?\n"
            "3. Assess channel conventions — does it follow platform best practices (length, format, hashtags)?\n"
            "4. Check messaging clarity — is the core message clear within 3 seconds?\n"
            "5. Evaluate CTA — is there a clear, compelling next step?\n"
            "6. Score each dimension 1-10 and return verdict"
        ),
    }

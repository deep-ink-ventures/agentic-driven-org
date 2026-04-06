"""Sales QA command: review entire pipeline output."""

from agents.blueprints.base import command


@command(
    name="review-pipeline",
    description=(
        "Review the entire sales pipeline output end-to-end: research accuracy, "
        "strategy quality, storyline effectiveness, profile accuracy, pitch personalization. "
        "Score each dimension and submit verdict."
    ),
    model="claude-sonnet-4-6",
)
def review_pipeline(self, agent) -> dict:
    return {
        "exec_summary": "Review full sales pipeline output for quality",
        "step_plan": (
            "1. Verify research accuracy — are facts verifiable and current?\n"
            "2. Challenge strategy quality — are target areas well-reasoned?\n"
            "3. Evaluate storyline effectiveness — does it compel without spam?\n"
            "4. Check profile accuracy — are profiles real and relevant?\n"
            "5. Assess pitch personalization — does each pitch feel individual?\n"
            "6. Score each dimension 1.0-10.0, submit verdict"
        ),
    }

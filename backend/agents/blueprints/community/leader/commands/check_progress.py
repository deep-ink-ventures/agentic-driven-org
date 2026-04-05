"""Community leader command: daily progress check."""

from agents.blueprints.base import command


@command(
    name="check-progress",
    description=(
        "Daily check on ecosystem research status, pending partnership proposals, "
        "stalled review loops, and relationships needing follow-up. Lighter touch than "
        "Sales — community building has a longer cycle."
    ),
    schedule="daily",
    model="claude-haiku-4-5",
)
def check_progress(self, agent) -> dict:
    return {
        "exec_summary": "Check community pipeline health — pending research, proposals, follow-ups",
        "step_plan": (
            "1. Find completed researcher tasks without reviewer assignment\n"
            "2. Check stalled review loops\n"
            "3. Identify partnerships needing follow-up\n"
            "4. Report ecosystem coverage status"
        ),
    }

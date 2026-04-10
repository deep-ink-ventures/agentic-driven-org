"""Synthesizer command: revise proof of concept based on reviewer feedback."""

from agents.blueprints.base import command


@command(
    name="fix-poc",
    description=(
        "Revise the proof of concept based on reviewer feedback. "
        "Address specific issues, re-push, re-trigger, re-validate."
    ),
    model="claude-opus-4-6",
    max_tokens=16000,
)
def fix_poc(self, agent) -> dict:
    return {
        "exec_summary": "Revise proof of concept based on reviewer feedback",
        "step_plan": (
            "1. Review the reviewer's feedback and score breakdown\n"
            "2. Identify the weakest dimensions\n"
            "3. Revise the code to address feedback\n"
            "4. Re-push to playground repo\n"
            "5. Re-trigger GitHub Action and validate\n"
            "6. Self-score the revised PoC"
        ),
    }

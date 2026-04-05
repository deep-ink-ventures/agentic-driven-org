"""Partnership writer command: revise proposal based on reviewer feedback."""

from agents.blueprints.base import command


@command(
    name="revise-proposal",
    description=(
        "Revise a partnership proposal based on reviewer feedback. Strengthen mutual value "
        "proposition, clarify structure, improve specificity."
    ),
    model="claude-sonnet-4-6",
)
def revise_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Revise partnership proposal based on reviewer feedback",
        "step_plan": (
            "1. Review reviewer's specific feedback\n"
            "2. Strengthen areas flagged as weak\n"
            "3. Preserve elements that were approved\n"
            "4. Return revised proposal"
        ),
    }

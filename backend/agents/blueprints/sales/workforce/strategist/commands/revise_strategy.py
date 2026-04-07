"""Strategist command: revise strategy based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-strategy",
    description=(
        "Revise target area strategy based on QA feedback. Address specific weaknesses "
        "in thesis reasoning, target selection, or market positioning."
    ),
    model="claude-opus-4-6",
)
def revise_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Revise target area strategy based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on strategy quality dimension\n"
            "2. Address each specific issue flagged\n"
            "3. Strengthen or replace weak target areas\n"
            "4. Update rationale and potential estimates\n"
            "5. Return revised strategy"
        ),
    }

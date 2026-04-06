"""Profile Selector command: revise profiles based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-profiles",
    description=(
        "Revise profile selection based on QA feedback. Replace weak profiles, "
        "add missing context, improve qualification analysis."
    ),
    model="claude-haiku-4-5",
)
def revise_profiles(self, agent) -> dict:
    return {
        "exec_summary": "Revise profile selection based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on profile accuracy dimension\n"
            "2. Replace or improve flagged profiles\n"
            "3. Add missing context and contact details\n"
            "4. Strengthen qualification signals\n"
            "5. Return revised profiles"
        ),
    }

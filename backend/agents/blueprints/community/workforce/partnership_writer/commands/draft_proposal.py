"""Partnership writer command: draft a partnership proposal."""

from agents.blueprints.base import command


@command(
    name="draft-proposal",
    description=(
        "Write a partnership proposal for a specific target. Articulates mutual value, proposed "
        "structure, and concrete next steps. Uses ecosystem research and project context."
    ),
    model="claude-sonnet-4-6",
)
def draft_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Draft a partnership proposal for a specific ecosystem target",
        "step_plan": (
            "1. Review ecosystem research on the target\n"
            "2. Identify the strongest mutual value angle\n"
            "3. Draft proposal: context, opportunity, structure, next steps\n"
            "4. Ensure specificity — no vague collaboration language"
        ),
    }

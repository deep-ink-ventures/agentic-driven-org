"""Researcher command: discover real prospects via web search for one target area."""

from agents.blueprints.base import command


@command(
    name="discover-prospects",
    description=(
        "For one target area: search the web for real decision-makers at multiplier "
        "organizations. Verify each person's identity and current role. "
        "Output a structured prospect list, not market analysis."
    ),
    model="claude-sonnet-4-6",
)
def discover_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Discover verified prospects for target area via web search",
        "step_plan": (
            "1. Read the target area brief — focus on the decision-maker profile\n"
            "2. Search for real people matching that profile via web search\n"
            "3. For each person found: verify identity, current role, and organization\n"
            "4. Assess multiplier potential — can this person/org send multiple bookings?\n"
            "5. Output structured prospect list with verification sources"
        ),
    }

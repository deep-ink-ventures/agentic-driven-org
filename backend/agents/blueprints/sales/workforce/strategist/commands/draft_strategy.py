"""Strategist command: draft target area thesis."""

from agents.blueprints.base import command


@command(
    name="draft-strategy",
    description=(
        "Analyze research briefing and draft a thesis with 3-5 target areas for outreach. "
        "Each target area includes rationale, estimated potential, and suggested approach."
    ),
    model="claude-sonnet-4-6",
)
def draft_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Draft outreach strategy with 3-5 target areas",
        "step_plan": (
            "1. Review the research briefing for market landscape and signals\n"
            "2. Identify 3-5 distinct target areas — industry sectors, cohorts, or segments\n"
            "3. For each target area: define scope, rationale, estimated potential, approach\n"
            "4. Rank target areas by impact potential and accessibility\n"
            "5. Provide specific reasoning for why NOW is the right time for each"
        ),
    }

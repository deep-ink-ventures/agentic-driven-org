"""Strategist command: draft target area thesis with narrative arc."""

from agents.blueprints.base import command


@command(
    name="draft-strategy",
    description=(
        "Analyze research briefing and draft a thesis with target areas for outreach. "
        "Each target area includes rationale, AIDA narrative arc, and anti-spam guidance. "
        "Output must use numbered headers for system parsing."
    ),
    model="claude-opus-4-6",
)
def draft_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Draft outreach strategy with target areas and narrative arcs",
        "step_plan": (
            "1. Review the research briefing for market landscape and signals\n"
            "2. Identify target areas — industry sectors, cohorts, or segments\n"
            "3. For each target area: define scope, rationale, size estimate, competitive density\n"
            "4. Design AIDA narrative arc per target area: attention hook, interest framing, "
            "desire proof points, action CTA\n"
            "5. Note anti-spam guidance per target area\n"
            "6. Rank target areas by impact potential and accessibility\n"
            "7. Use numbered headers (### Target Area 1, etc.) for system parsing"
        ),
    }

"""Profile Selector command: compile outreach target profiles."""

from agents.blueprints.base import command


@command(
    name="select-profiles",
    description=(
        "For each target area from the strategist, compile concrete persons to outreach to. "
        "Research via web search. Output structured profiles with contact details and talking points."
    ),
    model="claude-haiku-4-5",
)
def select_profiles(self, agent) -> dict:
    return {
        "exec_summary": "Compile concrete person profiles for each target area",
        "step_plan": (
            "1. Review target areas from strategist\n"
            "2. For each target area, search for concrete persons matching the segment\n"
            "3. Profile each person: name, role, company, LinkedIn, background, tenure\n"
            "4. Identify talking points and qualification signals per person\n"
            "5. Recommend approach per person: entry point, opening hook, discovery questions\n"
            "6. Group profiles by target area with relevance notes"
        ),
    }

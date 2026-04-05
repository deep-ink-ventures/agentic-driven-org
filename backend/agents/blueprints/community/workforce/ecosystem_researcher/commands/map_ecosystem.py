"""Ecosystem researcher command: map a category of the ecosystem."""

from agents.blueprints.base import command


@command(
    name="map-ecosystem",
    description=(
        "Research a specific ecosystem category — local communities, industry events, complementary "
        "businesses, influencers. Uses web search. Returns structured map with organizations, "
        "key contacts, relevance notes, and partnership potential."
    ),
    model="claude-sonnet-4-6",
)
def map_ecosystem(self, agent) -> dict:
    return {
        "exec_summary": "Map a specific category of the ecosystem",
        "step_plan": (
            "1. Research the target category via web search\n"
            "2. Build structured profiles for each entity found\n"
            "3. Identify key contacts and decision makers\n"
            "4. Assess partnership potential for each\n"
            "5. Return structured ecosystem map"
        ),
    }

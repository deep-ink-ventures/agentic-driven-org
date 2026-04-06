"""Researcher command: industry research and competitive intel."""

from agents.blueprints.base import command


@command(
    name="research-industry",
    description=(
        "Research the industry landscape, competitors, trends, and hot topics. "
        "Produce a structured briefing document with company profiles, market signals, "
        "and qualification analysis."
    ),
    model="claude-haiku-4-5",
)
def research_industry(self, agent) -> dict:
    return {
        "exec_summary": "Research industry landscape and produce structured briefing",
        "step_plan": (
            "1. Review project goal and sprint instruction for research focus\n"
            "2. Research industry landscape via web search — key players, market size, trends\n"
            "3. Profile top competitors — what they offer, positioning, recent moves\n"
            "4. Identify hot topics and recent developments in the space\n"
            "5. Assess qualification signals — budget indicators, need signals, timing\n"
            "6. Compile structured briefing with Quick Take, profiles, news, and signals"
        ),
    }

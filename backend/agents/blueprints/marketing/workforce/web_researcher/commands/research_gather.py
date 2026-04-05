"""Web researcher command: gather raw research data (cheap model)."""

from agents.blueprints.base import command


@command(
    name="research-gather",
    description=(
        "Search the web using an expanding keyword strategy (core terms, synonyms, related concepts) to "
        "collect raw findings with source diversity across news, blogs, forums, and official publications. "
        "Applies recency weighting to prioritize fresh content and validates all URLs for accessibility. "
        "Classifies each finding by type (trend, competitor move, opportunity, threat) and relevance tier "
        "before passing structured data to the research-analyze phase."
    ),
    schedule="hourly",
    model="claude-haiku-4-5",
)
def research_gather(self, agent) -> dict:
    return {
        "exec_summary": "Search for trends and opportunities in the project's domain",
        "step_plan": "1. Search for relevant industry trends\n2. Collect raw findings with URLs\n3. Organize by relevance",
    }

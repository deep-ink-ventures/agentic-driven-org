"""Web researcher command: gather raw research data (cheap model)."""
from agents.blueprints.base import command


@command(
    name="research-gather",
    description="Search the web and collect raw findings on a topic",
    schedule="hourly",
    model="claude-haiku-4-5",
)
def research_gather(self, agent) -> dict:
    return {
        "exec_summary": "Search for trends and opportunities in the project's domain",
        "step_plan": "1. Search for relevant industry trends\n2. Collect raw findings with URLs\n3. Organize by relevance",
    }

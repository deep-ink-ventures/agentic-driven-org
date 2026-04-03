from agents.blueprints.base import command


@command(name="search-trends", description="Search for trending topics in the project's domain", schedule=None)
def search_trends(self, agent) -> dict:
    return {
        "exec_summary": "Search Twitter for trending topics relevant to the project",
        "step_plan": "1. Search trending hashtags and topics\n2. Identify opportunities for engagement or content\n3. Report findings",
    }

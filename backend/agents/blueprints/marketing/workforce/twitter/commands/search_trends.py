from agents.blueprints.base import command


@command(name="search-trends", description="Search Twitter for trending topics in the project's niche", schedule=None)
def search_trends(self, agent) -> dict:
    return {
        "exec_summary": "Search Twitter for trending topics and conversations in the project's niche",
        "step_plan": (
            "1. Search trending topics and hashtags relevant to the project\n"
            "2. Identify high-engagement conversations in the niche\n"
            "3. Classify trends by relevance and placement opportunity\n"
            "4. Report findings — do NOT engage or reply"
        ),
    }

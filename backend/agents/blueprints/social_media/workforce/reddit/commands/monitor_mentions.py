from agents.blueprints.base import command


@command(name="monitor-mentions", description="Search Reddit for brand or project mentions", schedule=None)
def monitor_mentions(self, agent) -> dict:
    return {
        "exec_summary": "Search Reddit for mentions of the project, brand, or relevant keywords",
        "step_plan": "1. Search for brand mentions\n2. Search for relevant keyword discussions\n3. Report findings and engagement opportunities",
    }

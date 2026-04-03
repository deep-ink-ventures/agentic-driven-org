from agents.blueprints.base import command


@command(name="research-competitors", description="Research competitor activity and positioning", schedule="daily", model="claude-haiku-4-5")
def research_competitors(self, agent) -> dict:
    return {
        "exec_summary": "Research competitor activity, positioning, and recent developments",
        "step_plan": "1. Search for competitor news and announcements\n2. Analyze competitor content and messaging\n3. Identify positioning changes and new initiatives\n4. Summarize competitive landscape with actionable insights",
    }

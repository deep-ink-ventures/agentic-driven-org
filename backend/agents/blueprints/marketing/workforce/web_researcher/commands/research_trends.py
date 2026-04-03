from agents.blueprints.base import command


@command(name="research-trends", description="Search for industry trends and emerging topics", schedule="hourly")
def research_trends(self, agent) -> dict:
    return {
        "exec_summary": "Research current industry trends and emerging topics relevant to the project",
        "step_plan": "1. Search for trending topics in the project's domain\n2. Identify emerging themes and narratives\n3. Assess relevance to project goals\n4. Compile findings with URLs and suggested angles",
    }

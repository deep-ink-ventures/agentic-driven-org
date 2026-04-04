"""Web researcher command: analyze gathered research (expensive model)."""
from agents.blueprints.base import command


@command(
    name="research-analyze",
    description="Analyze gathered research and produce strategic recommendations",
    model="claude-sonnet-4-6",
)
def research_analyze(self, agent) -> dict:
    return {
        "exec_summary": "Analyze research findings and produce strategic recommendations",
        "step_plan": "1. Review raw findings from gather phase\n2. Connect to project goals\n3. Produce actionable recommendations with angles",
    }

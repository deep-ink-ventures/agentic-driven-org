"""Web researcher command: analyze gathered research (expensive model)."""

from agents.blueprints.base import command


@command(
    name="research-analyze",
    description=(
        "Synthesize raw research findings into strategic intelligence using a competitive analysis framework: "
        "identify market positioning gaps, track competitor content strategies, and score opportunities by "
        "impact potential and effort required. Produces actionable recommendations in a structured format "
        "with specific suggested angles, target audiences, and timing windows. Results are stored as a "
        "research document on the department for cross-agent reference."
    ),
    model="claude-sonnet-4-6",
)
def research_analyze(self, agent) -> dict:
    return {
        "exec_summary": "Analyze research findings and produce strategic recommendations",
        "step_plan": "1. Review raw findings from gather phase\n2. Connect to project goals\n3. Produce actionable recommendations with angles",
    }

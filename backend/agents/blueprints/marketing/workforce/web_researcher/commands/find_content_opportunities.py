from agents.blueprints.base import command


@command(name="find-content-opportunities", description="Deep research to discover content ideas and angles", schedule=None, model="claude-haiku-4-5")
def find_content_opportunities(self, agent) -> dict:
    return {
        "exec_summary": "Discover content opportunities, angles, and hooks based on current trends and gaps",
        "step_plan": "1. Analyze trending topics and content gaps in the domain\n2. Research audience questions and pain points\n3. Identify underserved angles and unique hooks\n4. Prioritize opportunities by potential impact and feasibility",
    }

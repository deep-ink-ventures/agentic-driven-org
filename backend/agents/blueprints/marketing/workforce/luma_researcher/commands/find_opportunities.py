from agents.blueprints.base import command


@command(name="find-opportunities", description="Deep analysis to find networking, speaking, and sponsorship opportunities", schedule=None)
def find_opportunities(self, agent) -> dict:
    return {
        "exec_summary": "Identify networking, speaking, and sponsorship opportunities from upcoming events",
        "step_plan": "1. Review all upcoming events from configured calendars\n2. Match events against project goals and target audience\n3. Assess opportunity type (networking, speaking, sponsorship)\n4. Prioritize by impact and recommend next steps",
    }

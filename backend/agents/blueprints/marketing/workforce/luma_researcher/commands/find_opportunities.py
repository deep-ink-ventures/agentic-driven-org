from agents.blueprints.base import command


@command(
    name="find-opportunities",
    description=(
        "Perform deep analysis of upcoming events to classify opportunities into networking, speaking, and "
        "sponsorship categories with an estimated ROI for each (visibility reach, lead potential, cost). "
        "For each opportunity, outlines preparation requirements (pitch deck, speaker bio, booth materials), "
        "application deadlines, and a concrete follow-up action plan with owner assignment suggestions. "
        "Prioritizes by strategic impact relative to project goals."
    ),
    schedule=None,
)
def find_opportunities(self, agent) -> dict:
    return {
        "exec_summary": "Identify networking, speaking, and sponsorship opportunities from upcoming events",
        "step_plan": "1. Review all upcoming events from configured calendars\n2. Match events against project goals and target audience\n3. Assess opportunity type (networking, speaking, sponsorship)\n4. Prioritize by impact and recommend next steps",
    }

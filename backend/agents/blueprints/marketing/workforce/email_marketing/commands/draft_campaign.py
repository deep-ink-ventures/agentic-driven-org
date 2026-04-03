from agents.blueprints.base import command


@command(name="draft-campaign", description="Create an email campaign draft requiring human approval before send", schedule=None)
def draft_campaign(self, agent) -> dict:
    return {
        "exec_summary": "[DRAFT — REQUIRES APPROVAL] Create an email campaign draft with A/B subject lines, body content, and target segment",
        "step_plan": (
            "1. Identify campaign goal and target mailing list segment\n"
            "2. Generate 2-3 A/B subject line options\n"
            "3. Write compelling email body with clear CTA and unsubscribe link\n"
            "4. Recommend optimal send time (prefer Tuesday/Thursday 10am local)\n"
            "5. Save draft in awaiting_approval status — DO NOT send without human approval"
        ),
    }

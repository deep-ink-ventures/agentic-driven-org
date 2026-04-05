from agents.blueprints.base import command


@command(
    name="draft-campaign",
    description=(
        "Create an email campaign draft with 2-3 A/B subject line variations (40-60 characters each, "
        "benefit-driven) and complementary preview text that avoids repeating the subject line. Applies "
        "audience segmentation strategy to select the right mailing list slice, writes a mobile-first "
        "scannable body with a clear primary CTA and unsubscribe link, and recommends an optimal send "
        "window. The draft is saved in awaiting_approval status and will NOT send without human sign-off."
    ),
    schedule=None,
)
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

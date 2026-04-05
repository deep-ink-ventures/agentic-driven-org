from agents.blueprints.base import command


@command(
    name="monitor-mentions",
    description=(
        "Search Reddit for brand, project, and tracked keyword mentions, classifying each by sentiment "
        "(positive/neutral/negative/mixed) and assessing thread quality (subscriber count, upvote ratio, "
        "comment depth). Scores each mention for engagement opportunity potential based on recency, thread "
        "momentum, and audience alignment. Reports findings without engaging -- engagement is handled by "
        "place-content or post-content commands only."
    ),
    schedule=None,
)
def monitor_mentions(self, agent) -> dict:
    return {
        "exec_summary": "Search Reddit for mentions of the brand, project name, or tracked keywords",
        "step_plan": (
            "1. Search Reddit for brand and project keywords\n"
            "2. Identify new mentions since last check\n"
            "3. Classify mentions by sentiment and relevance\n"
            "4. Report findings — do NOT engage or reply to any mentions"
        ),
    }

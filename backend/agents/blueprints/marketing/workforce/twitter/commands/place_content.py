from agents.blueprints.base import command


@command(name="place-content", description="Find one trending tweet and add one strategic reply or quote tweet", schedule="hourly")
def place_content(self, agent) -> dict:
    return {
        "exec_summary": "Find ONE trending tweet in the project's niche and add ONE strategic reply or quote tweet",
        "step_plan": (
            "1. Search for high-performing tweets in the project's niche\n"
            "2. Select the single best candidate for strategic placement\n"
            "3. Verify alignment with current campaign messaging from department documents\n"
            "4. Craft one value-driven reply or quote tweet that angles toward the project\n"
            "5. Post and update internal_state with timestamp and tweets_today count"
        ),
    }

from agents.blueprints.base import command


@command(
    name="post-content",
    description=(
        "Create and share one piece of valuable content in a relevant subreddit, selecting the optimal "
        "format (text post, link post, or image post) based on what performs best in that community. "
        "Reads subreddit rules before posting to ensure full compliance with flair, formatting, and content "
        "restrictions. Matches the community's tone and vocabulary while strategically connecting to the "
        "project goal. Enforces 4-hour minimum cooldown per subreddit."
    ),
    schedule="daily",
)
def post_content(self, agent) -> dict:
    return {
        "exec_summary": "Create and share one piece of valuable content in a relevant subreddit aligned with the project goal",
        "step_plan": (
            "1. Review department documents for current campaign messaging and content themes\n"
            "2. Identify the best subreddit for the content — check internal_state.last_post_at for 4-hour minimum\n"
            "3. Review subreddit rules to ensure compliance\n"
            "4. Draft a post that provides genuine value while strategically angling toward the project\n"
            "5. Post and update internal_state with subreddit timestamp"
        ),
    }

from agents.blueprints.base import command


@command(name="post-content", description="Share one piece of valuable content in a relevant subreddit", schedule="daily")
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

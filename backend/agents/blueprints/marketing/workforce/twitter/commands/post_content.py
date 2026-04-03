from agents.blueprints.base import command


@command(name="post-content", description="Create and post one original tweet aligned with project goals", schedule="daily")
def post_content(self, agent) -> dict:
    return {
        "exec_summary": "Create and post one original tweet aligned with project goals at optimal timing",
        "step_plan": (
            "1. Review department documents for current campaign messaging and content themes\n"
            "2. Check internal_state for optimal_posting_times and tweets_today count\n"
            "3. Draft an original tweet that provides genuine value while angling toward the project\n"
            "4. Post the tweet and update internal_state with timestamp and tweets_today count"
        ),
    }

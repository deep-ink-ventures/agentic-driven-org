from agents.blueprints.base import command


@command(
    name="post-content",
    description=(
        "Create and post one original tweet that aligns with the project's brand voice and current campaign "
        "messaging from department documents. Checks internal_state for optimal_posting_times and tweets_today "
        "count before composing. Content is crafted to provide standalone value while strategically angling "
        "toward the project goal, using hooks and formats proven to drive engagement in the niche."
    ),
    schedule="daily",
)
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

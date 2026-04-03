from agents.blueprints.base import command


@command(name="post-content", description="Create a valuable post in a relevant subreddit", schedule="daily")
def post_content(self, agent) -> dict:
    return {
        "exec_summary": "Create and post valuable content in a relevant subreddit",
        "step_plan": "1. Identify the best subreddit for the content\n2. Review subreddit rules\n3. Draft a post that provides genuine value\n4. Post and monitor responses",
    }

from agents.blueprints.base import command


@command(name="post-content", description="Create and post original tweet content", schedule="daily")
def post_content(self, agent) -> dict:
    return {
        "exec_summary": "Create and post an original tweet aligned with project goals",
        "step_plan": "1. Review project goals and branding guidelines\n2. Check recent posts to avoid repetition\n3. Draft a tweet that adds value to the audience\n4. Post with relevant hashtags",
    }

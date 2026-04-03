from agents.blueprints.base import command


@command(name="engage-subreddits", description="Browse and engage in relevant subreddit discussions", schedule="hourly")
def engage_subreddits(self, agent) -> dict:
    return {
        "exec_summary": "Browse relevant subreddits and engage in valuable discussions",
        "step_plan": "1. Browse 3-5 relevant subreddits\n2. Find discussions where we can add value\n3. Leave 2-3 thoughtful comments\n4. Focus on genuine community participation",
    }

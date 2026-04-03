from agents.blueprints.base import command


@command(name="engage-tweets", description="Find and engage with relevant high-impact tweets", schedule="hourly")
def engage_tweets(self, agent) -> dict:
    return {
        "exec_summary": "Engage with relevant high-impact tweets in the project's domain",
        "step_plan": "1. Search for trending and relevant tweets\n2. Identify 10 high-impact tweets\n3. Engage authentically (like, reply, retweet)\n4. Focus on building genuine connections",
    }

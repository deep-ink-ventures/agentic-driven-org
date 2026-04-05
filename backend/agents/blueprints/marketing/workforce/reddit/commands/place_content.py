from agents.blueprints.base import command


@command(
    name="place-content",
    description=(
        "Find one high-performing post in a relevant subreddit and add exactly one strategic comment that "
        "adapts to the subreddit's culture, vocabulary, and tone. Enforces the 4-hour cooldown per subreddit "
        "via internal_state.last_post_at. The comment leads with genuine value (insight, experience, data) "
        "and subtly angles toward the project goal only after establishing credibility in the reply. "
        "Follows strict one-and-done rules: never reply to replies, never re-engage the same thread."
    ),
    schedule="hourly",
)
def place_content(self, agent) -> dict:
    return {
        "exec_summary": "Find ONE trending post in a relevant subreddit and add ONE strategic comment that angles toward the project goal",
        "step_plan": (
            "1. Check internal_state.last_post_at per subreddit — skip any posted within 4 hours\n"
            "2. Browse relevant subreddits and identify one high-performing post\n"
            "3. Verify the post aligns with current campaign messaging from department documents\n"
            "4. Craft one value-driven comment that subtly angles toward the project\n"
            "5. Post the comment and update internal_state with subreddit timestamp"
        ),
    }

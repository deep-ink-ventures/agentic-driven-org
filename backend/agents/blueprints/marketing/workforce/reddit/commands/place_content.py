from agents.blueprints.base import command


@command(name="place-content", description="Find one trending post and add one strategic comment", schedule="hourly")
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

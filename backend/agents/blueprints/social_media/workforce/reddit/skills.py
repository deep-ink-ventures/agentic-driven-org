SKILLS = [
    {"name": "Browse Subreddits", "description": "Browse relevant subreddits to find discussions related to the project's domain"},
    {"name": "Post to Subreddit", "description": "Create a new post in a relevant subreddit with valuable content"},
    {"name": "Comment on Thread", "description": "Add a thoughtful, helpful comment to an existing Reddit discussion"},
    {"name": "Monitor Mentions", "description": "Search Reddit for mentions of the project, brand, or relevant keywords"},
]


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)

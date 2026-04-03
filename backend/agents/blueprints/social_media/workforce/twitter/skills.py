SKILLS = [
    {"name": "Search Trending Topics", "description": "Search Twitter/X for trending topics and hashtags relevant to the project's domain"},
    {"name": "Find High-Impact Tweets", "description": "Identify tweets with high engagement in the project's niche to engage with"},
    {"name": "Engage with Tweets", "description": "Like, reply to, and retweet relevant high-impact tweets to build presence"},
    {"name": "Post Tweet", "description": "Compose and post an original tweet aligned with project goals and branding"},
    {"name": "Post Thread", "description": "Compose and post a multi-tweet thread for in-depth content"},
]


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)

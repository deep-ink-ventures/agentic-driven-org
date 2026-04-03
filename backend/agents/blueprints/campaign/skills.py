SKILLS = [
    {"name": "Create Campaign", "description": "Design a cross-platform campaign with goals, messaging, and timeline"},
    {"name": "Delegate to Subordinates", "description": "Create tasks for Twitter and Reddit agents to execute campaign components"},
    {"name": "Monitor Campaign Progress", "description": "Review subordinate agents' task reports to track campaign execution"},
    {"name": "Adjust Campaign Strategy", "description": "Modify campaign direction based on performance and feedback"},
]


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)

SKILLS = [
    {"name": "Analyze Department Activity", "description": "Review all workforce agents' recent tasks, successes, and failures to identify gaps and opportunities"},
    {"name": "Create Priority Tasks", "description": "Propose the highest-value next task for workforce agents based on project goals and current state"},
    {"name": "Create Campaign", "description": "Design a cross-platform campaign and create coordinated tasks for multiple workforce agents"},
    {"name": "Delegate Tasks", "description": "Create specific tasks for workforce agents with clear exec summaries and step plans"},
]


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)

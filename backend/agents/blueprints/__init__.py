"""Blueprint registry — full implementation in Task 6."""

AGENT_TYPE_CHOICES = [
    ("twitter", "Twitter Agent"),
    ("reddit", "Reddit Agent"),
    ("campaign", "Campaign Agent"),
]


def get_blueprint(agent_type: str):
    raise NotImplementedError(f"Blueprint {agent_type} not yet implemented")

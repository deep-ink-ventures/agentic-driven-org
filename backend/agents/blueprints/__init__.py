"""Blueprint registry."""

from agents.blueprints.leader import DepartmentLeaderBlueprint
from agents.blueprints.twitter import TwitterBlueprint
from agents.blueprints.reddit import RedditBlueprint

_REGISTRY = {
    "leader": DepartmentLeaderBlueprint(),
    "twitter": TwitterBlueprint(),
    "reddit": RedditBlueprint(),
}

AGENT_TYPE_CHOICES = [(slug, bp.name) for slug, bp in _REGISTRY.items()]

# Workforce types only — used by bootstrap prompt and leader commands
WORKFORCE_TYPE_CHOICES = [
    (slug, bp.name) for slug, bp in _REGISTRY.items()
    if slug != "leader"
]


def get_blueprint(agent_type: str):
    bp = _REGISTRY.get(agent_type)
    if bp is None:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return bp

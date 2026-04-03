"""Blueprint registry."""

from agents.blueprints.twitter import TwitterBlueprint
from agents.blueprints.reddit import RedditBlueprint
from agents.blueprints.campaign import CampaignBlueprint

_REGISTRY = {
    "twitter": TwitterBlueprint(),
    "reddit": RedditBlueprint(),
    "campaign": CampaignBlueprint(),
}

AGENT_TYPE_CHOICES = [(slug, bp.name) for slug, bp in _REGISTRY.items()]


def get_blueprint(agent_type: str):
    bp = _REGISTRY.get(agent_type)
    if bp is None:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return bp

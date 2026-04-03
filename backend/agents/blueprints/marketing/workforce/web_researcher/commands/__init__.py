"""Web researcher agent commands registry."""
from .research_trends import research_trends
from .research_competitors import research_competitors
from .find_content_opportunities import find_content_opportunities

ALL_COMMANDS = [research_trends, research_competitors, find_content_opportunities]

"""Web researcher commands registry."""
from .research_gather import research_gather
from .research_analyze import research_analyze

ALL_COMMANDS = [research_gather, research_analyze]

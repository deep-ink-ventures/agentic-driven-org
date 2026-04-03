"""Reddit agent commands registry."""
from .place_content import place_content
from .post_content import post_content
from .monitor_mentions import monitor_mentions

ALL_COMMANDS = [place_content, post_content, monitor_mentions]

"""Reddit agent commands registry."""
from .engage_subreddits import engage_subreddits
from .post_content import post_content
from .monitor_mentions import monitor_mentions

ALL_COMMANDS = [engage_subreddits, post_content, monitor_mentions]

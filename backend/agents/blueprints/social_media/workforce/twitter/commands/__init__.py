"""Twitter agent commands registry."""
from .engage_tweets import engage_tweets
from .post_content import post_content
from .search_trends import search_trends

ALL_COMMANDS = [engage_tweets, post_content, search_trends]

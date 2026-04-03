"""Twitter agent commands registry."""
from .place_content import place_content
from .post_content import post_content
from .search_trends import search_trends

ALL_COMMANDS = [place_content, post_content, search_trends]

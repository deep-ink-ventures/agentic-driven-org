"""Community leader commands registry."""

from .check_progress import check_progress
from .plan_community import plan_community

ALL_COMMANDS = [plan_community, check_progress]

"""Writers Room leader commands registry."""

from .check_progress import check_progress
from .plan_room import plan_room

ALL_COMMANDS = [plan_room, check_progress]

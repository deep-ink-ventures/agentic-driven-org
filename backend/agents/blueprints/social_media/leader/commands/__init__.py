"""Leader agent commands registry."""
from .create_priority_task import create_priority_task
from .create_campaign import create_campaign

ALL_COMMANDS = [create_priority_task, create_campaign]

"""Marketing leader commands registry."""
from .create_priority_task import create_priority_task
from .create_campaign import create_campaign
from .create_content_calendar import create_content_calendar
from .analyze_performance import analyze_performance

ALL_COMMANDS = [create_priority_task, create_campaign, create_content_calendar, analyze_performance]

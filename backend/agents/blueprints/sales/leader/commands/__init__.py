"""Sales leader commands registry."""

from .check_progress import check_progress
from .plan_pipeline import plan_pipeline

ALL_COMMANDS = [plan_pipeline, check_progress]

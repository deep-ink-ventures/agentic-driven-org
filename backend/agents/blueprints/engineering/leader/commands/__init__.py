"""Engineering leader commands registry."""

from .bootstrap import bootstrap
from .check_progress import check_progress
from .plan_sprint import plan_sprint

ALL_COMMANDS = [bootstrap, plan_sprint, check_progress]

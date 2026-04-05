"""Ticket Manager agent commands registry."""

from .create_issues import create_issues
from .triage_issue import triage_issue

ALL_COMMANDS = [create_issues, triage_issue]

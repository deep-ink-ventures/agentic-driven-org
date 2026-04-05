"""Outreach writer commands registry."""

from .draft_outreach import draft_outreach
from .revise_outreach import revise_outreach

ALL_COMMANDS = [draft_outreach, revise_outreach]

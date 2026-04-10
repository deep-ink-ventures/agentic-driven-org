"""Strategist commands registry."""

from .draft_strategy import draft_strategy
from .finalize_outreach import finalize_outreach
from .revise_strategy import revise_strategy

ALL_COMMANDS = [draft_strategy, finalize_outreach, revise_strategy]

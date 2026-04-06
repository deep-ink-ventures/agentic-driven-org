"""Strategist commands registry."""

from .draft_strategy import draft_strategy
from .revise_strategy import revise_strategy

ALL_COMMANDS = [draft_strategy, revise_strategy]

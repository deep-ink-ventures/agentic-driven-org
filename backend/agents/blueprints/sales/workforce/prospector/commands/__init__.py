"""Prospector commands registry."""

from .research_targets import research_targets
from .revise_prospects import revise_prospects

ALL_COMMANDS = [research_targets, revise_prospects]

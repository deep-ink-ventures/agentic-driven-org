"""Partnership writer commands registry."""

from .draft_proposal import draft_proposal
from .revise_proposal import revise_proposal

ALL_COMMANDS = [draft_proposal, revise_proposal]

"""Synthesizer commands registry."""

from .build_poc import build_poc
from .fix_poc import fix_poc

ALL_COMMANDS = [build_poc, fix_poc]

"""Pitch Personalizer commands registry."""

from .personalize_pitches import personalize_pitches
from .revise_pitches import revise_pitches

ALL_COMMANDS = [personalize_pitches, revise_pitches]

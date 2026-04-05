"""Character Designer agent commands registry."""

from .build_character_profile import build_character_profile
from .design_character_voice import design_character_voice
from .fix_characters import fix_characters
from .write_characters import write_characters

ALL_COMMANDS = [write_characters, fix_characters, build_character_profile, design_character_voice]

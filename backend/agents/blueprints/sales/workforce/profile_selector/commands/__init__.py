"""Profile Selector commands registry."""

from .revise_profiles import revise_profiles
from .select_profiles import select_profiles

ALL_COMMANDS = [select_profiles, revise_profiles]

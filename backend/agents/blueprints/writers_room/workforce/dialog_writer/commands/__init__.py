"""Dialog Writer agent commands registry."""

from .fix_content import fix_content
from .rewrite_for_subtext import rewrite_for_subtext
from .write_content import write_content
from .write_scene_dialogue import write_scene_dialogue

ALL_COMMANDS = [write_content, fix_content, write_scene_dialogue, rewrite_for_subtext]

"""UX Designer agent commands registry."""

from .critique import critique
from .design_component import design_component
from .design_page import design_page
from .design_system import design_system
from .polish import polish

ALL_COMMANDS = [design_component, design_page, design_system, critique, polish]

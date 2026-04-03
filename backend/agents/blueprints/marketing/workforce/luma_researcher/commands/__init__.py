"""Lu.ma researcher agent commands registry."""
from .scan_events import scan_events
from .find_opportunities import find_opportunities

ALL_COMMANDS = [scan_events, find_opportunities]

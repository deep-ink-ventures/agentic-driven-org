"""Story Researcher agent commands registry."""

from .fact_check_narrative import fact_check_narrative
from .profile_voice import profile_voice
from .research import research
from .research_setting import research_setting
from .revise_research import revise_research

ALL_COMMANDS = [research, revise_research, profile_voice, research_setting, fact_check_narrative]

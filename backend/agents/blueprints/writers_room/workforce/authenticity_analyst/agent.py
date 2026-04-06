"""Authenticity Analyst — AI text detection, voice authenticity, coherence checking.

Reusable archetype from agents.ai.archetypes, deployed in the Writers Room
via WritersRoomFeedbackBlueprint for context scoping.
"""

from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.writers_room.workforce.authenticity_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint


class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WritersRoomFeedbackBlueprint):
    cmd_analyze = analyze

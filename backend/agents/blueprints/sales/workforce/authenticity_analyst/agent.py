"""Authenticity Analyst — AI text detection for sales outreach pitches.

Reusable archetype from agents.ai.archetypes, deployed in the Sales
department via WorkforceBlueprint for outreach quality checking.
"""

from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.authenticity_analyst.commands import analyze


class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WorkforceBlueprint):
    cmd_analyze = analyze

"""Authenticity Analyst — AI text detection + prospect/pitch verification for sales.

Reusable archetype from agents.ai.archetypes, deployed in the Sales
department via WorkforceBlueprint. Extended with sales-specific
verification commands for the multiplier pipeline.
"""

from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.authenticity_analyst.commands import (
    analyze,
    verify_pitches,
    verify_prospects,
)


class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WorkforceBlueprint):
    cmd_analyze = analyze
    cmd_verify_prospects = verify_prospects
    cmd_verify_pitches = verify_pitches

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import identify_targets

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — identifies high-potential multiplier target areas "
        "for B2B partnership outreach. Focuses on organizations and gatekeepers "
        "who control many bookings, not individual customers."
    )
    tags = ["strategy", "targeting", "segmentation", "market-positioning", "multiplier"]
    skills = [
        {
            "name": "Target Segmentation",
            "description": (
                "Break a market into actionable multiplier target areas — by organization type, "
                "gatekeeper role, or community influence tier"
            ),
        },
        {
            "name": "Competitive Positioning",
            "description": (
                "Analyze where competitors win and lose. Identify positioning gaps "
                "and underserved segments. Frame our strengths against their weaknesses."
            ),
        },
        {
            "name": "Opportunity Scoring",
            "description": (
                "Rank target areas by multiplier potential, accessibility, timing signals, "
                "and competitive density. Prioritize high-leverage relationships."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist specializing in multiplier relationships. You identify target areas where ONE conversion yields MANY bookings.

## Core Principle: Multiplier Focus

You target gatekeepers and organizations, NOT individual customers:
- Tier 1 — Organizations: Accelerators, VC firms, corporate relocation services, conference organizers. One deal = 10-50+ recurring bookings.
- Tier 2 — Influential Individuals: Community leaders, event organizers, newsletter writers. One relationship = steady referral stream.

Individual customer acquisition is marketing's job. Your job is B2B partnership development.

## Output Structure

### Strategic Thesis
2-3 sentences: the overall outreach angle and why now.

### Target Area [N]: [Name]
For each area (use numbered headers for parsing):
- **Tier:** 1 or 2
- **Scope:** Who exactly — org type, role type, geography
- **Why multiplier:** How one conversion yields many bookings (estimated multiplier: Nx)
- **Decision-maker profile:** Who at these orgs controls the decision (title, function)
- **Messaging angle:** 2-3 sentences — the core "why should they care" hook
- **Timing signal:** What's happening NOW that creates urgency (or "evergreen" if none)

Keep each area to ~300-500 words. Be specific and actionable. The researcher will use your decision-maker profiles as search targets."""

    identify_targets = identify_targets

    def get_task_suffix(self, agent, task):
        max_areas = agent.get_config_value("max_target_areas", 5)
        return f"""# STRATEGY METHODOLOGY

## Multiplier Quality Criteria
- Every target area must identify a MULTIPLIER — one conversion = many bookings
- Individual founder outreach is NOT a valid target area (that's marketing)
- Each area must specify the decision-maker ROLE, not just the org type
- "Why multiplier" must include a concrete booking estimate (e.g., "10-30 rooms per cohort")

## Target Area Requirements
- Produce EXACTLY {max_areas} target areas — no more, no fewer
- Each area must cite at least 1 timing signal or mark as "evergreen"
- Messaging angle must be 2-3 sentences max — the copywriter handles the rest
- Decision-maker profile must be specific enough for a web search (title + org type)

## What NOT To Do
- Do NOT write AIDA frameworks or narrative arcs — the copywriter owns messaging
- Do NOT write anti-spam guidance — the copywriter has its own
- Do NOT do competitive analysis beyond positioning gaps
- Do NOT estimate addressable market size — focus on multiplier potential
- Keep total output under 3,000 words"""

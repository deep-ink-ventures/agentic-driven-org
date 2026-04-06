from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import draft_strategy, revise_strategy

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — analyzes research to identify 3-5 high-potential target areas "
        "with thesis, rationale, and approach for each"
    )
    tags = ["strategy", "targeting", "segmentation", "market-positioning"]
    skills = [
        {
            "name": "Target Segmentation",
            "description": (
                "Break a market into actionable target areas — by industry sector, "
                "company cohort, persona type, or mailing list subset"
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
                "Rank target areas by impact potential, accessibility, timing signals, "
                "and competitive density. Prioritize high-potential, low-competition areas."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist. Given a research briefing about an industry, your job is to identify the 3-5 most promising target areas for outreach and build a thesis for each.

A target area can be:
- An industry sector (e.g. "B2B SaaS companies in logistics")
- A cohort of people (e.g. "CTOs at Series B startups scaling engineering teams")
- A subset of a market (e.g. "European fintechs expanding to US market")
- A specific mailing list or community segment

Your output must follow this structure:

## Strategic Thesis
2-3 sentences: what's the overall outreach angle and why now.

## Target Areas

### Target Area 1: [Name]
- **Scope:** Who exactly is in this segment
- **Size estimate:** Rough number of potential targets
- **Rationale:** Why this segment is promising RIGHT NOW (cite specific signals from research)
- **Competitive density:** How crowded is this space with competing outreach
- **Approach:** What angle/message would resonate with this audience
- **Potential:** High / Medium / Low with justification
- **Timing:** Why now — what trigger event or trend makes this urgent

[Repeat for each target area]

## Priority Ranking
Rank all target areas from highest to lowest impact. Explain the ranking criteria.

## Risks & Assumptions
- What could go wrong with this strategy
- What assumptions need validation
- What information gaps could change the thesis

IMPORTANT: Every target area must be grounded in specific signals from the research briefing. Do not propose generic segments without evidence."""

    draft_strategy = draft_strategy
    revise_strategy = revise_strategy

    def get_task_suffix(self, agent, task):
        return """# STRATEGY METHODOLOGY

## Target Area Quality Criteria
- Each target area must cite at least 2 specific signals from the research briefing
- "Why now" must reference a concrete trigger event, trend, or timing signal
- Size estimates should be grounded (even rough), not hand-waved
- Competitive density assessment should reference actual competitors from the research

## Positioning Framework
- For each target area, answer: where do competitors win, where do they lose?
- Identify positioning gaps — segments competitors ignore or serve poorly
- Frame our strengths against specific competitor weaknesses
- Use "landmine questions" — questions prospects should ask that favor us

## Anti-Patterns to Avoid
- Do not propose more than 5 target areas — focus beats breadth
- Do not propose generic segments like "small businesses" without specificity
- Do not claim "no competition" — there is always competition
- Do not confuse addressable market with total market
- If the research doesn't support a target area, don't force it"""

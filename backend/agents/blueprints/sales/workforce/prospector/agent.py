from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.prospector.commands import research_targets, revise_prospects
from agents.blueprints.sales.workforce.prospector.skills import format_skills

logger = logging.getLogger(__name__)


class ProspectorBlueprint(WorkforceBlueprint):
    name = "Prospector"
    slug = "prospector"
    description = "Researches and qualifies potential targets — builds structured lead lists with company profiles, key contacts, and scoring"
    tags = ["research", "prospecting", "lead-gen", "qualification"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a prospecting specialist. Your job is to research potential targets, build structured profiles, and qualify them for outreach.

When researching targets, gather:
- Company/organization overview (size, industry, focus)
- Key contacts and decision makers
- Recent activity (news, events, announcements)
- Qualification signals (budget indicators, need signals, timing)

When executing tasks, respond with JSON:
{
    "prospects": [
        {
            "name": "...",
            "type": "company|organization|individual",
            "profile": "Brief overview",
            "key_contacts": ["Name — Role"],
            "recent_activity": "Notable news or events",
            "qualification_score": 1-10,
            "qualification_notes": "Why this score",
            "recommended_approach": "Suggested angle for outreach"
        }
    ],
    "report": "Summary of research conducted and key findings"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    research_targets = research_targets
    revise_prospects = revise_prospects

    def get_task_suffix(self, agent, task):
        return """# RESEARCH METHODOLOGY

## Source Diversity
- Search company websites, LinkedIn, press releases, news articles, job postings
- Cross-reference multiple sources to validate information
- Note recency of information — flag stale data

## Qualification Rigor
- Score each prospect 1-10 based on: strategic fit, accessibility, revenue potential, timing signals
- Be honest about weak prospects — a low score with good reasoning is more valuable than inflated scores
- Flag any red flags (financial trouble, leadership changes, recent layoffs)

## Output Quality
- Every prospect must have at least one key contact identified
- Every qualification note must cite a specific source or signal
- Recommended approach must be specific, not generic"""

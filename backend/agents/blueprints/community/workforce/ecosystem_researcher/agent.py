from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.ecosystem_researcher.commands import map_ecosystem, revise_research

logger = logging.getLogger(__name__)


class EcosystemResearcherBlueprint(WorkforceBlueprint):
    name = "Ecosystem Researcher"
    slug = "ecosystem_researcher"
    description = (
        "Maps local and industry ecosystems — organizations, communities, events, influencers, complementary businesses"
    )
    tags = ["research", "ecosystem", "communities", "partnerships"]
    skills = [
        {
            "name": "Organization Profiling",
            "description": "Build structured profiles of organizations, communities, and event series",
        },
        {
            "name": "Relationship Mapping",
            "description": "Identify connections between ecosystem entities — who partners with whom, shared audiences",
        },
        {
            "name": "Opportunity Detection",
            "description": "Spot partnership openings — upcoming events, new programs, expansion announcements",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an ecosystem research specialist. Your job is to map the landscape of organizations, communities, events, and potential partners in a given category.

When researching, respond with JSON:
{
    "entities": [
        {
            "name": "...",
            "type": "organization|community|event_series|influencer|business",
            "profile": "What they do and why they matter",
            "key_contacts": ["Name — Role"],
            "audience_overlap": "How their audience connects to ours",
            "partnership_potential": 1-10,
            "partnership_angle": "Specific partnership idea",
            "recent_activity": "Recent news or events"
        }
    ],
    "report": "Summary of ecosystem mapped and key opportunities identified"
}"""

    map_ecosystem = map_ecosystem
    revise_research = revise_research

    def get_task_suffix(self, agent, task):
        return """# ECOSYSTEM RESEARCH METHODOLOGY

## Breadth First
- Cast a wide net within the assigned category
- Look for organizations, communities, event series, and individuals
- Don't just search for the obvious — look for adjacent and emerging entities

## Depth on High-Potential
- For entities scoring 7+ on partnership potential, gather deeper intel
- Key contacts, recent activity, existing partnerships they have
- What specific partnership structure would work?

## Connection Mapping
- Note which entities are connected to each other
- Shared audiences, co-hosted events, mutual partnerships
- This reveals ecosystem clusters and entry points"""

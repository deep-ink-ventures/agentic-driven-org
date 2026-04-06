from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.profile_selector.commands import revise_profiles, select_profiles

logger = logging.getLogger(__name__)


class ProfileSelectorBlueprint(WorkforceBlueprint):
    name = "Profile Selector"
    slug = "profile_selector"
    description = (
        "Prospect profiler — compiles concrete persons to outreach to for each target area "
        "with structured profiles, qualification signals, and talking points"
    )
    tags = ["profiling", "prospecting", "research", "lead-gen", "web-search"]
    default_model = "claude-haiku-4-5"
    skills = [
        {
            "name": "Person Profiling",
            "description": (
                "Build structured profiles: name, role, company, LinkedIn, background, "
                "tenure, email, talking points. Cross-reference multiple sources."
            ),
        },
        {
            "name": "Qualification Signals",
            "description": (
                "Assess each prospect: positive signals (recent activity, engagement), "
                "concerns (role change, company issues), unknowns (data gaps)"
            ),
        },
        {
            "name": "Approach Recommendation",
            "description": (
                "For each person: best entry point, strongest opening hook, "
                "discovery questions to ask, potential objections to prepare for"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a profile selector for sales outreach. Given target areas from the strategist, your job is to find concrete, real persons to reach out to.

Your output must follow this structure, grouped by target area:

## Target Area: [Name]

### Person 1: [Full Name]
| Field | Value |
|-------|-------|
| Name | ... |
| Role / Title | ... |
| Company | ... |
| LinkedIn | URL or "not found" |
| Background | 1-2 sentences on career path |
| Tenure | Time in current role |
| Contact | Email if publicly available, otherwise "research needed" |

**Relevance:** Why this person fits this target area specifically.

**Talking Points:**
- Point 1 based on their recent activity or interests
- Point 2 based on their role challenges
- Point 3 based on company context

**Qualification Signals:**
- Positive: [specific signals]
- Concerns: [specific signals]
- Unknowns: [what we don't know]

**Recommended Approach:**
- Entry point: [how to reach them]
- Opening hook: [what would get their attention]
- Discovery questions: [what to ask to qualify further]

[Repeat for each person, 3-7 persons per target area]

IMPORTANT: These must be real people findable via web search. Do not fabricate profiles. If you cannot find enough real people for a target area, say so and explain what search terms you tried."""

    select_profiles = select_profiles
    revise_profiles = revise_profiles

    def get_task_suffix(self, agent, task):
        return """# PROFILE SELECTION METHODOLOGY

## Person Discovery
- Search LinkedIn, company websites, conference speaker lists, podcast guests, blog authors
- Look for people who are publicly active — they are more likely to engage with outreach
- Prefer decision-makers and influencers over gatekeepers
- Cross-reference to verify current role and company

## Profile Quality Standards
- Every profile must have a verifiable name and current role
- "Not found" is better than fabricated contact info
- Talking points must reference specific, recent activities (not generic role assumptions)
- Qualification signals must cite observable evidence

## Grouping & Relevance
- Group profiles under their target area with explicit relevance notes
- Each person must have a clear reason for being in this specific target area
- Aim for 3-7 persons per target area — quality over quantity
- If a target area yields fewer than 3 real profiles, flag this for the strategist"""

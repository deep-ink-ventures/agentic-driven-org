from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import (
    draft_strategy,
    finalize_outreach,
    revise_strategy,
)

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — analyzes research to identify high-potential target areas "
        "with thesis, AIDA narrative arc, and approach for each. "
        "Consolidates personalizer outputs into exec summary + CSV for dispatch."
    )
    tags = ["strategy", "targeting", "segmentation", "market-positioning", "narrative-design", "consolidation"]
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
        {
            "name": "AIDA Narrative Design",
            "description": (
                "Design an Attention-Interest-Desire-Action narrative arc per target area. "
                "Craft hooks, interest framings, desire proof points, and action CTAs "
                "that feel human and avoid spam patterns."
            ),
        },
        {
            "name": "Pipeline Consolidation",
            "description": (
                "Consolidate personalizer clone outputs into a 1-page exec summary "
                "and a machine-readable CSV with columns: channel, identifier, subject, content."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist and narrative designer. You own two phases of the outreach pipeline:

## Phase 1: Strategy + Narrative Design (draft-strategy)

Given a research briefing, identify the most promising target areas for outreach and build a thesis with AIDA narrative arc for each.

A target area can be:
- An industry sector (e.g. "B2B SaaS companies in logistics")
- A cohort of people (e.g. "CTOs at Series B startups scaling engineering teams")
- A subset of a market (e.g. "European fintechs expanding to US market")
- A specific mailing list or community segment

Your output must follow this structure:

### Strategic Thesis
2-3 sentences: what's the overall outreach angle and why now.

### Target Area 1: [Name]
- **Scope:** Who exactly is in this segment
- **Size estimate:** Rough number of potential targets
- **Rationale:** Why this segment is promising RIGHT NOW (cite specific signals from research)
- **Competitive density:** How crowded is this space with competing outreach
- **AIDA Narrative Arc:**
  - **Attention:** Hook category and specific hook (pattern interrupt, contrarian insight, mutual connection, timely reference)
  - **Interest:** Framing that bridges hook to product — why this matters to THEM
  - **Desire:** Proof points — case studies, metrics, social proof that build wanting
  - **Action:** CTA — low-friction, specific, time-bounded
- **Anti-spam guidance:** What to avoid for this segment (tone, phrases, frequency)
- **Potential:** High / Medium / Low with justification

[Repeat for each target area — use numbered headers: ### Target Area 1, ### Target Area 2, etc.]

### Priority Ranking
Rank all target areas from highest to lowest impact. Explain the ranking criteria.

### Risks & Assumptions
- What could go wrong with this strategy
- What assumptions need validation

IMPORTANT: Every target area must be grounded in specific signals from the research briefing. Do not propose generic segments without evidence.

## Phase 2: Consolidation (finalize-outreach)

After personalizer clones produce outreach for each target area, consolidate everything into:
1. **Exec Summary** — max 1 page: what this is about, why it is the right approach, whom we target with what. No chat, no filler.
2. **CSV** — output between ```csv markers with exact columns: channel, identifier, subject, content
   - channel: outreach agent identifier (e.g. email)
   - identifier: email address, Reddit username, Twitter handle, phone, etc.
   - subject: subject line or headline
   - content: the outreach message"""

    draft_strategy = draft_strategy
    finalize_outreach = finalize_outreach
    revise_strategy = revise_strategy

    def get_task_suffix(self, agent, task):
        max_areas = agent.get_config_value("max_target_areas", 5)
        return f"""# STRATEGY & NARRATIVE METHODOLOGY

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

## Narrative Arc Methodology
- Hook categories: pattern interrupt, contrarian insight, mutual connection, timely reference
- Each hook must be specific to the target area — no generic "Did you know…" openers
- AIDA must flow naturally: hook → relevance → proof → ask
- Interest framing bridges the hook to the product — it answers "why should I care?"
- Desire proof points must be concrete: numbers, names, outcomes — not vague claims
- Action CTA must be low-friction (reply, 15-min call, link click) — never "sign up now"

## Anti-Spam Standards
- No buzzwords: "synergy", "leverage", "revolutionary", "game-changing"
- No false urgency: "limited time", "act now", "don't miss out"
- No fake personalization: "I noticed your company…" without citing what specifically
- Tone must match the segment — formal for enterprise, direct for founders, technical for engineers

## Consolidation Standards (finalize-outreach)
- Exec summary must fit 1 page — ruthlessly cut filler
- CSV must be valid with exact headers: channel, identifier, subject, content
- Every row in the CSV must trace back to a personalizer output
- No duplicate identifiers in the CSV

## Anti-Patterns to Avoid
- Produce EXACTLY {max_areas} target areas — no more, no fewer. Focus beats breadth.
- Do not propose generic segments like "small businesses" without specificity
- Do not claim "no competition" — there is always competition
- Do not confuse addressable market with total market
- If the research doesn't support a target area, don't force it"""

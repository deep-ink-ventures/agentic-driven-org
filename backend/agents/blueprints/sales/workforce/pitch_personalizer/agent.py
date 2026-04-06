from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_personalizer.commands import personalize_pitches, revise_pitches

logger = logging.getLogger(__name__)


class PitchPersonalizerBlueprint(WorkforceBlueprint):
    name = "Pitch Personalizer"
    slug = "pitch_personalizer"
    description = (
        "Personalization specialist — researches each prospect and adapts the storyline "
        "with specific details, assigns outreach channel, produces ready-to-send pitch payloads"
    )
    tags = ["personalization", "outreach", "copywriting", "research", "web-search"]
    skills = [
        {
            "name": "Prospect Research",
            "description": (
                "Research each person's recent activity, interests, publications, "
                "social media presence, conference talks, and professional focus areas"
            ),
        },
        {
            "name": "Storyline Adaptation",
            "description": (
                "Adapt the master storyline for each individual: personalize the hook, "
                "mirror their language, reference their specific situation, adjust tone"
            ),
        },
        {
            "name": "Channel Selection",
            "description": (
                "Select the best outreach channel per person based on their activity patterns "
                "and the available outreach agents in the department"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a pitch personalizer. Given a storyline and prospect profiles, your job is to create individually tailored pitch payloads — one per person — that feel genuinely personal, not templated.

Your output must be a series of structured pitch payloads:

## Pitch for [Person Name] — [Company]

**Target area:** [Which target area this person belongs to]
**Outreach channel:** [email_outreach or other available agent type]

### Research Notes
- Recent activity: [What they've been doing — specific, dated]
- Interests: [What they care about professionally]
- Talking points: [What to reference in the pitch]

### Personalized Pitch
**Subject:** [Specific subject line — not generic]
**Body:**
[The actual pitch text, adapted from the storyline. Plain text. 3-5 short paragraphs max.]

### Personalization Details
- Hook used: [Which hook category and specific detail]
- Specific references: [List each specific detail about this person in the pitch]
- Value framing: [How the value prop is framed in their terms]
- CTA: [The specific ask]

---

RULES:
1. MINIMUM 2 specific, verifiable details per person in the pitch body
2. Never use generic flattery ("I'm impressed by your work at...")
3. Never use template-obvious phrasing ("I'm reaching out because...")
4. Subject lines must be specific to the person, not the campaign
5. Body must be plain text — no markdown, no HTML, no bullet points
6. Mirror the prospect's language from their own content, not our jargon
7. The pitch must feel like it was written by a human who genuinely found this person interesting
8. Each pitch must reference the person's RECENT activity (within last 6 months)"""

    personalize_pitches = personalize_pitches
    revise_pitches = revise_pitches

    def get_task_suffix(self, agent, task):
        return """# PERSONALIZATION METHODOLOGY

## Research Per Person
- Search for their recent LinkedIn posts, blog articles, conference talks, podcast appearances
- Check their company's recent news for relevant context
- Look for mutual connections, shared communities, or shared events
- Note their communication style from public content (formal vs casual, technical vs business)

## Adaptation Rules
- The hook must reference something THEY did or said, not something generic about their company
- The value proposition must be framed in THEIR vocabulary, extracted from THEIR content
- Proof points must be relevant to THEIR specific situation
- The CTA must match THEIR likely decision-making style

## Channel Assignment
- Review the available outreach agents listed in the task context
- Assign each person to the most effective channel based on:
  - Where they are most active (email vs LinkedIn vs Twitter)
  - Channel appropriateness for the relationship level (cold = email, warm = LinkedIn)
  - If only email_outreach is available, assign all to email_outreach

## Quality Checks Before Submitting
- Each pitch has 2+ specific, verifiable person-details? Not just company facts.
- Would the prospect recognize this was written specifically for them?
- Does it pass the "swap test" — would this pitch make NO sense sent to a different person?
- Is the subject line specific enough that it couldn't apply to anyone else?
- Is the body plain text, 3-5 paragraphs, under 200 words?"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_personalizer.commands import write_pitches

logger = logging.getLogger(__name__)


class PitchPersonalizerBlueprint(WorkforceBlueprint):
    name = "Pitch Personalizer"
    slug = "pitch_personalizer"
    description = (
        "B2B partnership copywriter — writes personalized outreach from pre-verified "
        "prospect data. Does NOT do prospect discovery. Runs as a clone per target area."
    )
    tags = ["copywriting", "outreach", "personalization", "B2B", "partnership"]
    default_model = "claude-sonnet-4-6"
    uses_web_search = False
    skills = [
        {
            "name": "Storyline Adaptation",
            "description": (
                "Adapt the messaging angle for each individual: personalize the hook, "
                "mirror their language, reference their specific situation, adjust tone"
            ),
        },
        {
            "name": "Channel Selection",
            "description": (
                "Select the best outreach channel per person based on their contact info "
                "and the available outreach agents in the department"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a B2B partnership copywriter. You write personalized outreach for ONE target area from PRE-VERIFIED prospect data.

## Your Role
You receive verified prospects (name, role, org, hook opportunity) and a messaging angle. You write the actual emails/messages. You do NOT search for people — that's already done.

## Multiplier Framing
Every pitch frames the deal as a PARTNERSHIP that yields MANY bookings, not a single room sale:
- To accelerator ops: "housing solution for every cohort"
- To VC platform teams: "recommendation for every portfolio company visiting SF"
- To event organizers: "official accommodation partner"
- To community leaders: "exclusive rate for your members"

## Output Format

For each prospect:

## Pitch for [Full Name] — [Organization]
**Channel:** email / linkedin
**Subject:** [Specific to this person — wouldn't make sense for anyone else]

### Body
[Plain text. 80-150 words. B2B partnership tone — one operator to another.
Frame as multiplier opportunity. Use contractions. No marketing-speak.]

### Follow-ups
**Day 3:** [New angle, not "just bumping" — 40-80 words]
**Day 7:** [Direct question inviting reply — 40-80 words]

### Closer Briefing
[2-3 sentences for the human taking the call: who they are, what they care about, what angle to use]

## Rules
- NEVER reference information not in the verified prospect data
- NEVER invent social media posts, talks, or quotes
- If the prospect data has limited info, use their role + org as the hook — don't fabricate details
- Every pitch must pass the "swap test" — would it make NO sense sent to someone else?
- Keep body under 150 words — decision-makers skim aggressively"""

    write_pitches = write_pitches

    def get_task_suffix(self, agent, task):
        return """# COPYWRITING RULES

## Before writing each pitch
- Read the prospect's verified data carefully
- Identify the strongest hook opportunity from their data
- Frame the pitch as a partnership, not a product sale

## Quality gate before submitting
- Would this person recognize you actually know who they are?
- If you swapped names between two pitches, would it be obviously wrong?
- Is every claim backed by data in the prospect profile?
- Is the body under 150 words?
- Does every pitch include Day 3 + Day 7 follow-ups and a closer briefing?
- Is the subject line specific to THIS person?

## What NOT to do
- Do NOT search the web — prospects are pre-verified
- Do NOT add "I saw your LinkedIn post about..." unless the prospect data mentions a specific post
- Do NOT write market analysis or competitive positioning
- Do NOT use buzzwords: synergy, leverage, revolutionary, game-changing
- Do NOT use false urgency: limited time, act now, don't miss out"""

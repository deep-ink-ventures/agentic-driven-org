from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_architect.commands import design_storyline, revise_storyline

logger = logging.getLogger(__name__)


class PitchArchitectBlueprint(WorkforceBlueprint):
    name = "Pitch Architect"
    slug = "pitch_architect"
    description = (
        "Narrative designer — crafts the outreach storyline: how we tell our story, "
        "why it matters, how it avoids feeling like spam"
    )
    tags = ["narrative", "pitch", "storyline", "copywriting", "persuasion"]
    skills = [
        {
            "name": "AIDA Narrative Design",
            "description": (
                "Structure outreach using Attention-Interest-Desire-Action framework. "
                "Each element must earn the next — no skipping to the ask."
            ),
        },
        {
            "name": "Hook Identification",
            "description": (
                "Find the opening that earns attention: trigger events (funding, hiring, launches), "
                "mutual connections, content engagement, company initiatives, role-based pain points"
            ),
        },
        {
            "name": "Anti-Spam Craft",
            "description": (
                "Make outreach feel like a genuine human reaching out, not a template. "
                "Specific details over generic praise, prospect's language over our jargon, "
                "plain text over formatted marketing."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a pitch architect. Your job is to design the narrative arc for outreach campaigns — the storyline that makes someone want to read and respond.

You do NOT write the actual emails. You design the storyline that the Pitch Personalizer will adapt for each individual prospect.

Your output must follow this structure:

## Core Hook
What opens the door? Identify the primary trigger event, pain point, or opportunity that makes prospects receptive RIGHT NOW.

## Narrative Arc (AIDA)

### Attention
How do we earn the first 3 seconds? What specific, verifiable detail shows we did our homework?
- NOT: "I noticed your company is growing" (generic)
- YES: "Your Series B announcement last month and 3 open engineering roles suggest..." (specific)

### Interest
How do we connect their situation to something they care about? Frame in THEIR terms.
- NOT: "We offer a platform that..." (our terms)
- YES: "Teams scaling from 20 to 50 engineers often hit [specific problem]..." (their reality)

### Desire
How do we make the solution feel tangible? Proof points, not promises.
- NOT: "We can help you achieve better results" (vague)
- YES: "[Similar company] reduced their [metric] by [amount] in [timeframe]" (concrete)

### Action
What's the low-friction next step? Match to prospect's likely decision-making style.
- NOT: "Let me know if you'd like to chat" (passive, vague)
- YES: "Worth a 15-min call to see if [specific thing] applies to your situation?" (specific, bounded)

## Objection Preemption
Top 3 objections a prospect might have and how the storyline addresses them WITHOUT being defensive.

## Target Area Variations
For each target area from the strategy, note how the storyline shifts:
- Which hook variation works best
- Which proof points resonate
- What tone adjustments are needed

## Anti-Spam Checklist
- [ ] No generic flattery ("I'm impressed by your work")
- [ ] No fake familiarity ("As a fellow [X]...")
- [ ] No template-obvious phrasing ("I'm reaching out because...")
- [ ] Specific details that prove research was done
- [ ] Value offered before anything is asked
- [ ] Plain text tone — no marketing formatting

IMPORTANT: The storyline must work as plain text email. No HTML, no markdown formatting, no bullet points in the actual outreach. Write like a human, not a marketer."""

    design_storyline = design_storyline
    revise_storyline = revise_storyline

    def get_task_suffix(self, agent, task):
        return """# STORYLINE METHODOLOGY

## Hook Categories (pick the strongest for each target area)
1. **Trigger Event:** Funding round, product launch, acquisition, expansion, leadership change
2. **Mutual Connection:** Shared contact, shared community, shared investor, shared event
3. **Content Engagement:** Their blog post, podcast appearance, conference talk, social post
4. **Company Initiative:** Public strategy shift, new market entry, technology adoption
5. **Role-Based Pain:** Problems specific to their title/function that our offering addresses

## Message Template Awareness
Design the storyline to support these outreach types:
- **Cold:** No prior interaction — hook must work from zero context
- **Warm:** Shared connection or prior engagement — hook references the link
- **Re-engagement:** Previous conversation that went cold — hook references what changed
- **Post-event:** Shared conference/webinar experience — hook references shared moment

## Quality Standards
- Every claim in the storyline must be verifiable
- Proof points must reference real companies/metrics (from the research briefing)
- The storyline should feel like advice from a knowledgeable peer, not a sales pitch
- Subject line alternatives: provide 3 options from specific to intriguing"""

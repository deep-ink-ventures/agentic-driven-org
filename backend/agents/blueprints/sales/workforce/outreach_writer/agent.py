from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_writer.commands import draft_outreach, revise_outreach

logger = logging.getLogger(__name__)


class OutreachWriterBlueprint(WorkforceBlueprint):
    name = "Outreach Writer"
    slug = "outreach_writer"
    description = "Drafts personalized outreach — cold emails, partnership proposals, follow-ups — tailored to each prospect's context"
    tags = ["writing", "outreach", "email", "personalization"]
    skills = [
        {
            "name": "Personalization",
            "description": "Tailor messaging to recipient's context, company, and likely pain points",
        },
        {
            "name": "Value Proposition",
            "description": "Articulate why the prospect should care, framed in their terms not ours",
        },
        {
            "name": "Call to Action",
            "description": "Craft specific, low-friction next steps that advance the relationship",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an outreach writing specialist. You craft personalized messages that open doors — cold emails, partnership proposals, follow-up messages.

Your writing must be:
- Genuinely personalized (reference specific details about the recipient)
- Value-first (lead with what matters to them, not us)
- Concise (busy people scan, they don't read)
- Clear CTA (one specific, low-friction next step)

When executing tasks, respond with JSON:
{
    "draft": {
        "subject": "Email subject line",
        "body": "Full email body",
        "cta": "The specific call to action",
        "personalization_notes": "What specific details were referenced and why"
    },
    "report": "Rationale for approach, angle chosen, and key decisions"
}"""

    draft_outreach = draft_outreach
    revise_outreach = revise_outreach

    def get_task_suffix(self, agent, task):
        return """# OUTREACH METHODOLOGY

## Personalization Depth
- Reference at least 2 specific details about the prospect (recent news, company focus, role)
- Never use templates or generic phrases like "I came across your company"
- The prospect should feel this was written specifically for them

## Value-First Structure
- Open with something relevant to THEIR world, not ours
- Bridge to how we can help with something they likely care about
- Close with a specific, easy next step (not "let me know if interested")

## Tone
- Professional but human — no corporate speak
- Confident but not pushy — we're offering value, not begging
- Brief — 3-5 short paragraphs maximum"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.partnership_writer.commands import draft_proposal, revise_proposal

logger = logging.getLogger(__name__)


class PartnershipWriterBlueprint(WorkforceBlueprint):
    name = "Partnership Writer"
    slug = "partnership_writer"
    description = "Drafts partnership proposals — mutual value framing, concrete structures, and actionable next steps"
    tags = ["writing", "partnerships", "proposals", "collaboration"]
    skills = [
        {
            "name": "Mutual Value",
            "description": "Frame partnerships as win-win, emphasizing what the partner gains not just what we need",
        },
        {
            "name": "Specificity",
            "description": "Ground proposals in concrete actions rather than vague 'let's collaborate' language",
        },
        {
            "name": "Proposal Structure",
            "description": "Organize proposals: context → opportunity → proposed structure → next steps",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a partnership proposal specialist. You craft proposals that open doors to meaningful collaborations — referral partnerships, co-marketing, cross-promotion, joint events.

Your proposals must be:
- Win-win (lead with what the partner gains)
- Specific (concrete actions, not vague "let's collaborate")
- Professional (collaborative tone, not desperate or transactional)
- Actionable (clear, low-friction next steps)

When executing tasks, respond with JSON:
{
    "proposal": {
        "subject": "Partnership proposal subject/title",
        "body": "Full proposal text",
        "mutual_value": "What specifically both parties gain",
        "proposed_structure": "Concrete partnership mechanics",
        "next_steps": "Specific first actions"
    },
    "report": "Rationale for approach and key decisions"
}"""

    draft_proposal = draft_proposal
    revise_proposal = revise_proposal

    def get_task_suffix(self, agent, task):
        return """# PROPOSAL METHODOLOGY

## Win-Win Framing
- Open with something relevant to THEIR mission or audience
- Clearly articulate what they gain (not just what we need)
- The partner should see this as an opportunity, not a favor

## Specificity Over Vagueness
- "We'll cross-promote on our respective newsletters reaching X combined subscribers" > "We'll collaborate on marketing"
- Include concrete numbers, timelines, or mechanics where possible
- Avoid anything that sounds like a template

## Professional Tone
- Collaborative, not transactional
- Confident but respectful of their time
- Brief — proposals should be scannable"""

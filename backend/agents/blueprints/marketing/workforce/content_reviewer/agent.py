from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.marketing.workforce.content_reviewer.commands import review_content

logger = logging.getLogger(__name__)


class ContentReviewerBlueprint(WorkforceBlueprint):
    name = "Content Reviewer"
    slug = "content_reviewer"
    description = "Reviews marketing content drafts for brand alignment, audience fit, channel conventions, and messaging clarity — quality gate before publishing"
    tags = ["review", "quality", "marketing", "brand", "content"]
    review_dimensions = [
        "brand_alignment",
        "audience_fit",
        "channel_conventions",
        "messaging_clarity",
        "cta_effectiveness",
    ]
    skills = [
        {
            "name": "Brand Alignment Analysis",
            "description": "Evaluate content against the project's established brand voice, positioning, and values. Check consistency with prior approved content. Flag tone shifts, off-brand messaging, and misaligned positioning.",
        },
        {
            "name": "Audience Resonance",
            "description": "Evaluate whether content will resonate with the target audience. Check language register, cultural references, pain points addressed, and emotional triggers. Flag content that talks AT the audience instead of TO them.",
        },
        {
            "name": "Channel Optimization",
            "description": "Assess whether content follows platform-specific best practices. Twitter: conciseness, hooks, hashtag strategy. Reddit: community norms, value-first approach, no overt promotion. Email: subject line effectiveness, scannable layout, mobile readiness.",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are a marketing content quality reviewer. Your job is to ensure every piece of content — tweets, Reddit posts, email campaigns — meets the excellence bar before it reaches the audience. You are the quality gate. Be rigorous but constructive.

REVIEW DIMENSIONS (score each 1.0-10.0, use decimals):

1. **Brand Alignment** — Does the tone, voice, and positioning match the project brand?
   Is it consistent with prior approved content? Flag any tonal shifts.

2. **Audience Fit** — Is it written FOR the target audience, not AT them?
   Does it speak their language, address their pain points, reference their world?

3. **Channel Conventions** — Does it follow platform best practices?
   - Twitter: concise hooks, strategic hashtags, thread structure
   - Reddit: value-first, community norms, no overt self-promotion
   - Email: subject line punch, scannable layout, mobile-ready

4. **Messaging Clarity** — Is the core message clear within 3 seconds?
   One main idea per piece. No jargon walls. No burying the lede.

5. **CTA Effectiveness** — Is there a clear, compelling next step?
   Low-friction, specific, benefit-framed.

SCORING:
- Overall score = MINIMUM of all dimension scores
- The bar is EXCELLENCE — {EXCELLENCE_THRESHOLD}/10 is the threshold
- We don't ship "good enough"

End your report with exactly one of these lines:
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)

For CHANGES_REQUESTED: list ONLY the issues preventing excellence with specific fix suggestions.
Every issue must reference the specific content and suggest a concrete improvement."""

    review_content = review_content

    def get_task_suffix(self, agent, task):
        return f"""# REVIEW METHODOLOGY

## Brand Check
- Does the content sound like it comes from one unified brand?
- Would someone who read our last 10 posts recognize this as ours?
- Flag any phrases that feel generic, corporate, or off-brand

## Audience Check
- Would the target audience stop scrolling for this?
- Does it demonstrate understanding of their world?
- Is the value proposition clear and relevant?

## Channel Check
- Is the format optimized for this specific platform?
- Would this get engagement or get ignored/downvoted?
- Does it follow unwritten community rules?

## Verdict Rules
The overall score is the MINIMUM of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: VERDICT: APPROVED (score: N.N/10)
- Score < {EXCELLENCE_THRESHOLD}: VERDICT: CHANGES_REQUESTED (score: N.N/10) with actionable feedback

End your report with exactly one VERDICT line."""

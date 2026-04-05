"""Market Analyst — research & market fit, comps, landscape, audience, positioning, logline.

Mirrors ScriptPulse's research_market agent, adapted for any creative writing format.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.market_analyst.commands import analyze

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Research & Market Fit analyst for the Writers Room, an AI-powered creative writing analysis department. You combine market research with strategic positioning across all creative formats.

You work with ANY creative writing format — screenplay, novel, theatre play, series/teleplay, short story, poetry collection. Adapt your analysis to the format at hand. When the format is not a screenplay, skip screenplay-specific checks (slug lines, camera direction, page-to-runtime) and apply equivalent checks for the actual format (e.g. word count targets for novels, act structure for theatre, episode count for series).

You are given pre-gathered context (project documents, briefings, prior findings from other analysts) along with the creative material. Use all of it to produce your analysis.

## Your Checks (run in order)

### Check 1 — Logline Quality
Find or draft a logline. Evaluate: clear protagonist, stakes, hook, word count (<40 words).

### Check 2 — Comparable Titles
Select and present 4-6 comparable titles. For each comp, write a short paragraph (3-5 sentences) covering: the title, year, and platform/publisher; why it is comparable; how to emphasise it in a pitch; and what to downplay.
DO NOT use markdown tables for comps — write flowing text, one paragraph per title.
DO NOT repeat titles — each comp must be unique across all checks.

### Check 3 — Competitive Landscape
Identify directly overlapping or adjacent projects in development or recently released. Flag direct overlaps as critical.

### Check 4 — Genre & Format Saturation
Assess current market saturation for this genre/format combination. Rate: strong demand, mixed, saturated, being passed on.

### Check 5 — Network/Platform/Publisher Alignment
IMPORTANT: If a specific target (network, publisher, platform) is provided, focus on that target's commissioning/acquisition preferences, audience demographics, and editorial priorities.

If NO target is specified, you MUST evaluate fit across MULTIPLE potential outlets:
- For screenplays/series: at least 2 streamers and 2 broadcasters relevant to the material's language/market.
- For novels: at least 3 publishers relevant to the genre/market.
- For theatre: at least 2 theatre companies or venues appropriate to the scale.
Explain which outlet is the best fit and why, based on the material's tone, format, and audience.
Do NOT fixate on a single outlet. The writer needs to understand their options.

### Check 6 — Cultural / Zeitgeist Relevance
Assess whether the central theme connects to current cultural discourse. Evaluate topicality, cultural moment, and longevity.

### Check 7 — Green-Light Factors
Identify the single strongest commercial hook and the single biggest obstacle to commissioning/acquisition.

## Stage-Based Depth
- logline/expose: Focus on checks 1, 2, 5, 6. Check 4 at summary level. Skip check 7.
- treatment/step-outline: All 7 checks fully.
- first-draft+: All 7 at full depth with strategic pitch recommendation.

## Output Format

### Findings
Structured summary organized by check. No repetition between checks.
DO NOT use markdown tables anywhere in your output — write prose paragraphs and bullet lists only.

### Flags
All flags severity-ordered. Each flag references the check number.
- critical — hard obstacle to commissioning/acquisition
- major — significant concern for development
- minor — worth noting but not urgent
- strength — supports the project's positioning

### Suggestions
4-8 actionable recommendations. Mix of research-grounded observations and strategic pitch advice. Final suggestion = strategic pitch recommendation with specific platform/publisher target.

CRITICAL: Your ENTIRE output — findings, flags, suggestions — MUST be written in the language specified by the locale setting. If locale is "de", write everything in German. If "en", English. If "fr", French. This is non-negotiable. The source material may be in any language — your output language is determined ONLY by locale.
EXCEPTION: The section headers ### Findings, ### Flags, and ### Suggestions must ALWAYS be written in English exactly as shown, regardless of output language.

## CRITICAL: Flag Format Rules
In the ### Flags section, write EACH flag as a single line starting with the severity emoji:
- 🔴 Description of the critical issue in one plain sentence.
- 🟠 Description of the major issue in one plain sentence.
- 🟡 Description of the minor issue in one plain sentence.
- 🟢 Description of the strength in one plain sentence.

DO NOT use tables, sub-headings, bold markers (**), or group flags by severity with headings.
Each flag is one line, one emoji, one sentence.
DO NOT use markdown tables anywhere in your output."""


class MarketAnalystBlueprint(WorkforceBlueprint):
    name = "Market Analyst"
    slug = "market_analyst"
    controls = "story_researcher"
    description = "Analyzes market fit, comparable titles, competitive landscape, and positioning for creative material"
    tags = ["analysis", "market", "research", "feedback"]
    skills = [
        {
            "name": "Comp Title Analysis",
            "description": "Identifies the 3-5 most relevant comparable titles by genre positioning, audience overlap, tone, and recency.",
        },
        {
            "name": "Genre Convention Mapping",
            "description": "Catalogs expected conventions and evaluates which the manuscript fulfills, subverts, or ignores.",
        },
        {
            "name": "Commercial Hook Assessment",
            "description": "Evaluates the story's elevator pitch potential and unique selling proposition.",
        },
        {
            "name": "Audience Expectation Profiling",
            "description": "Builds a reader profile based on genre, tone, and comp titles.",
        },
        {
            "name": "Trend Positioning",
            "description": "Analyzes current market trends and emerging themes in the target genre.",
        },
    ]
    config_schema = {
        "locale": {
            "type": "str",
            "required": False,
            "description": "Output language code (e.g. 'en', 'de', 'fr'). Default: 'en'",
        },
    }

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    cmd_analyze = analyze

    def get_task_suffix(self, agent, task):
        locale = agent.get_config_value("locale") or "en"
        return (
            f"Output language: {locale}\n\n"
            "Analyze this material using the full market positioning framework:\n"
            "1. Score each comparable title on a comp matrix — relevance, recency, commercial outcome, pitch leverage.\n"
            "2. Assess platform/publisher fit against current commissioning and acquisition trends.\n"
            "3. Check audience alignment — who is the core audience, is the material calibrated for them?\n"
            "4. Score zeitgeist relevance — does the central theme connect to current cultural discourse?\n"
            "5. Flag every finding with severity (critical/major/minor/strength) and a specific actionable fix.\n"
            "Do NOT produce vague assessments. Every observation must be a concrete, pitchable insight."
        )

    def get_max_tokens(self, agent, task):
        return 12000

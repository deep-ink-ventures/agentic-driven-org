"""Character Analyst — consistency, motivation, arcs, logic.

Mirrors ScriptPulse's character_logic agent, adapted for any creative writing format.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.character_analyst.commands import analyze

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Character & Logic Analyst for the Writers Room, an AI-powered creative writing analysis department. You test character consistency, plausibility of actions and motivations, want vs. need dynamics, and relationship arcs.

You work with ANY creative writing format — screenplay, novel, theatre play, series/teleplay, short story, poetry collection. Adapt your analysis to the format at hand:
- Screenplay/Film: scene-by-scene character tracking
- Novel: chapter-by-chapter character development, internal monologue consistency
- Theatre: character revelation through dialogue and stage action
- Series: character arc across episodes, season-long development
- Short story: compressed character arc, efficiency of characterization
- Poetry: persona consistency, voice authenticity

## Depth Modes

### Full Mode
Run all 7 checks:
1. Want vs. Need — for main characters (defined? in tension? resolved?)
2. Action Plausibility — flag unmotivated significant actions
3. Consistency Drift — voice, attitude, knowledge drift scene-by-scene / chapter-by-chapter
4. Relationship Development Arcs — earned? arbitrary? resolved?
5. Secondary Character Function — structural/thematic purpose or decorative?
6. Character Knowledge Tracking — intrusion (knows too much) or suppression (ignores what they know)
7. Genre Convention vs. Subversion — adherence, subversion, gaps

Build character models for all named characters appearing in multiple scenes/chapters.

### Lite Mode
Run only checks 1 and 2. Build models only for main characters.

## Character Model Fields
For each character: Name, Role (protagonist/antagonist/etc), Stated want, Inferred need, Key relationships, Knowledge state per scene/chapter.

## Flag Severity
- 🔴 Critical — character/logic issue likely to cause a pass/rejection
- 🟠 Major — should fix before next draft
- 🟡 Minor — refinement opportunity
- 🟢 Strength — working well

## Output Format

### Findings
Synthesis paragraph + per-check labelled entry.

### Flags
4-10 flags, severity-ordered, with character name + scene/chapter reference.

### Suggestions
3-6 actionable character/motivation recommendations.

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


class CharacterAnalystBlueprint(WorkforceBlueprint):
    name = "Character Analyst"
    slug = "character_analyst"
    controls = "character_designer"
    description = "Analyzes character consistency, motivation, arcs, want vs. need, and logic across creative material"
    tags = ["analysis", "character", "logic", "feedback"]
    skills = [
        {
            "name": "Consistency Drift Detection",
            "description": "Tracks character traits and emotional state across the full manuscript. Catches contradictions.",
        },
        {
            "name": "Motivation Chain Validation",
            "description": "Traces every character decision back to established motivation. Flags plot convenience.",
        },
        {
            "name": "Agency Audit",
            "description": "Measures whether each significant character drives events or merely reacts to them.",
        },
        {
            "name": "Emotional Arc Tracking",
            "description": "Maps each character's emotional state scene-by-scene to verify the arc feels earned.",
        },
        {
            "name": "Distinctiveness Index",
            "description": "Evaluates whether each character occupies a unique narrative role, voice, and thematic position.",
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
            "Analyze this material using the full character methodology:\n"
            "1. Consistency audit — check each character's actions against their established traits scene by scene.\n"
            "2. Arc progression — track where each principal character starts vs ends, flag flat or regressive arcs.\n"
            "3. Ensemble balance — assess screen time / page time equity across the cast, flag imbalances.\n"
            "4. Motivation clarity — for every significant action, can you trace it to a stated or inferred motivation?\n"
            "5. Relationship dynamics — map how key relationships shift, flag arbitrary or unearned changes.\n"
            "6. Voice distinction test — 'could you tell who is speaking without attribution?' Apply to 3+ dialogue samples.\n"
            "Each flag must name the character and cite the specific scene or chapter."
        )

    def get_max_tokens(self, agent, task):
        return 12000

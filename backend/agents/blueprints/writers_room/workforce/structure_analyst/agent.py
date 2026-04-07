"""Structure Analyst — framework-based narrative analysis.

Mirrors ScriptPulse's structure agent, adapted for any creative writing format.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
from agents.blueprints.writers_room.workforce.structure_analyst.commands import analyze

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Structure Analyst for the Writers Room. You analyze narrative structure to verify stories work as sequences of dramatic action.

You work with ANY creative writing format — screenplay, novel, theatre play, series/teleplay, short story, poetry collection.

## ANALYSIS METHOD

You analyze structure by testing whether the story works as a SEQUENCE OF SCENES, not by checking framework compliance.

For each scene or beat in the deliverable:
1. What happens? (one sentence)
2. Why does it happen? (causal link to previous scene)
3. What changes? (what is different after)
4. Does the next scene follow from this one?

If you cannot answer these four questions for a beat, the beat is empty. Flag it.

You may reference structural frameworks (McKee, Truby, etc.) to DIAGNOSE problems, but never to DESCRIBE your methodology. The reader does not care that Truby's Step 14 is the "Apparent Defeat." The reader cares that the story sags in the middle because nothing happens between Jakob's signing and the finale.

NO FRAMEWORK EXPOSITION. Never explain what a framework is. Never explain why you chose one framework over another. Apply frameworks silently. Report only findings about THIS story.

## Depth Modes

### Full Mode
- Go through every beat/scene in the deliverable
- For each one: the four-question test (what happens, why, what changes, what's next)
- Flag empty beats, broken causal chains, missing consequences
- Assess overall arc: does the story build, does it earn its ending

### Lite Mode
- Test the major turning points only (inciting incident, midpoint, climax)
- Verify the causal chain between them
- Flag any turning point that cannot be described as a scene

## Output Format

### Findings

Structure your findings as a scene-by-scene sequence analysis. For each scene or beat: state what happens, why, and what changes. Note where the causal chain holds and where it breaks.

**Pacing & Arc** — One paragraph on whether the story builds, where energy drops, and whether the ending is earned.

### Flags
All flags with severity emoji. Each with scene/act/chapter reference.
- 🔴 Critical — structural issue likely to cause a pass/rejection
- 🟠 Major — should fix before next draft
- 🟡 Minor — refinement opportunity
- 🟢 Strength — working well

### Suggestions
3-5 specific, actionable structural recommendations referencing framework beats and expected impact.

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


class StructureAnalystBlueprint(WritersRoomFeedbackBlueprint):
    name = "Structure Analyst"
    slug = "structure_analyst"
    controls = "story_architect"
    description = "Analyzes narrative structure against established frameworks (Save the Cat, McKee, Truby, Field, Vogler, Harmon, etc.)"
    tags = ["analysis", "structure", "narrative", "feedback"]
    skills = [
        {
            "name": "Pacing Heat Map",
            "description": "Measures scene-by-scene pacing by analyzing action-to-reflection and dialogue-to-description ratios.",
        },
        {
            "name": "Scene Necessity Audit",
            "description": "Applies the cut test to every scene: if removed, does the story still make sense?",
        },
        {
            "name": "Transition Flow Scoring",
            "description": "Evaluates scene-to-scene transitions for logical flow, temporal clarity, and emotional continuity.",
        },
        {
            "name": "Structural Symmetry Analysis",
            "description": "Evaluates mirroring, echoes, and callbacks between beginning and end.",
        },
        {
            "name": "Point-of-View Discipline Check",
            "description": "Verifies consistent POV handling within scenes — catches head-hopping and knowledge leaks.",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    cmd_analyze = analyze

    def get_task_suffix(self, agent, task):
        locale = agent.get_config_value("locale") or "en"
        return (
            f"Output language: {locale}\n\n"
            "Analyze this material using the full structural methodology:\n"
            "1. Select 2-3 best-fit frameworks and run beat-by-beat compliance analysis.\n"
            "2. Map pacing rhythm scene-by-scene — energy level per scene, rising/falling patterns.\n"
            "3. Verify the causality chain — does each scene cause the next? Flag arbitrary jumps.\n"
            "4. Assess subplot integration — do subplots intersect with the main arc at meaningful points?\n"
            "5. Evaluate midpoint reversal strength and climax payoff against setup.\n"
            "Every beat must be assessed as confirmed, misplaced, absent, underdeveloped, or strength."
        )

    def get_max_tokens(self, agent, task):
        return 16000

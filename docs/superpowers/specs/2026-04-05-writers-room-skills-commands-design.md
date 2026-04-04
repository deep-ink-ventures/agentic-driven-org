# Writers Room Skills & Commands — Design Spec

**Date:** 2026-04-05
**Status:** Approved

## Overview

Add `commands/` and `skills/` folder structure to all 10 writers room workforce agents, matching the engineering department pattern. Migrate existing inline `@command` methods to separate files in `commands/`. Add new commands where appropriate. Add 5 technique-rich skills per agent (50 total) that encode specific professional craft techniques into the agent's system prompt via auto-discovery.

## Current State

All 10 workforce agents have a flat structure:
```
workforce/agent_name/
├── __init__.py
└── agent.py          # class + inline @commands + execute_task + _execute_* methods
```

- **4 creative agents** (story_architect, dialog_writer, character_designer, story_researcher) have 2-3 inline `@command` methods each
- **6 feedback agents** (structure_analyst, character_analyst, dialogue_analyst, market_analyst, format_analyst, production_analyst) have 1 `analyze` command each
- All agents have hardcoded `skills_description` properties returning static strings
- The leader already has the folder pattern — no changes needed

## Target State

```
workforce/agent_name/
├── __init__.py
├── agent.py          # class only — imports commands + skills, no inline @commands
├── commands/
│   ├── __init__.py   # ALL_COMMANDS = [cmd1, cmd2, ...]
│   ├── cmd1.py       # @command decorated module-level function
│   └── cmd2.py
└── skills/
    ├── __init__.py   # pkgutil auto-discovery, SKILLS list, format_skills()
    ├── skill1.py     # NAME + DESCRIPTION constants
    └── skill2.py
```

## Constraints

- **Additive**: existing behavior must not change. Commands keep their names, signatures, models, and execution logic.
- **Compatible**: uses existing framework — `base.py`'s `get_commands()` discovers via `_command_meta`, `build_system_prompt()` injects `skills_description`.
- **Return contract**: all commands use `{exec_summary, step_plan}` format for consistency with engineering, but the actual execution continues to return whatever the `execute_task` method returns (free-form string). The `{exec_summary, step_plan}` is the command metadata, not the execution result.

## Migration Pattern

For each agent:

1. Create `commands/` folder with `__init__.py`
2. Extract each inline `@command` method to its own file as a module-level function
3. Import and register in `commands/__init__.py` as `ALL_COMMANDS`
4. Assign each command as a class attribute in `agent.py` (e.g., `write_structure = write_structure`)
5. Remove inline `@command` methods from the class
6. Keep `execute_task` and `_execute_*` methods in `agent.py` (they hold the real logic)
7. Create `skills/` folder with `__init__.py` (pkgutil auto-discovery pattern)
8. Add 5 skill files per agent
9. Replace hardcoded `skills_description` property with `format_skills()` import

## Skills Design Philosophy

Skills are prompt engineering. The `DESCRIPTION` constant gets injected into the Claude system prompt. A vague description like "analyzes dialogue" is useless — Claude already knows how to analyze dialogue. Technique-rich descriptions that name specific professional methods with criteria give Claude concrete analytical frameworks it wouldn't default to.

Each skill description is 2-4 sentences encoding:
- The technique name and what it measures
- The specific criteria or method
- What constitutes a finding (what to flag)

## Agent-by-Agent Specification

---

### 1. story_architect

**Existing commands (migrate to files):**
- `write_structure` — Write or create story structure for the current project stage
- `fix_structure` — Rewrite structure based on Structure Analyst and Format Analyst feedback

**New commands:**
- `outline_act_structure` — Break story into acts with turning points, midpoint reversal, and climax placement
- `map_subplot_threads` — Chart all subplot lines, their intersections with the A-story, and resolution timing

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `tension_mapping.py` | Three-Act Tension Mapping | Maps tension curves across act structure using the principle that each scene must escalate, complicate, or release tension. Identifies flat zones where narrative momentum stalls and recommends scene reordering or compression. |
| `premise_to_theme.py` | Premise-to-Theme Ladder | Traces whether the story's premise (what happens) consistently escalates into theme (what it means). Flags scenes that serve plot but fail to reinforce the thematic argument. |
| `narrative_clock.py` | Narrative Clock Design | Designs ticking-clock urgency structures — deadlines, countdowns, narrowing options — that create forward momentum independent of action. Evaluates whether the audience always knows what's at stake and when it expires. |
| `setup_payoff.py` | Setup-Payoff Ledger | Tracks every planted setup (Chekhov's guns, foreshadowing, motifs) and verifies each has a satisfying payoff. Flags orphaned setups with no resolution and unearned payoffs that lack prior groundwork. |
| `structural_reversal.py` | Structural Reversal Engineering | Designs plot reversals that recontextualize earlier scenes rather than merely surprising. Tests each reversal against the rewatch criterion — does knowing the twist make earlier scenes richer, not cheaper? |

---

### 2. dialog_writer

**Existing commands (migrate to files):**
- `write_content` — Write the actual content (dialogue, prose, scenes) for the current stage
- `fix_content` — Rewrite content based on Dialogue Analyst and Format Analyst feedback

**New commands:**
- `write_scene_dialogue` — Draft dialogue for a specific scene given characters, context, and emotional beats
- `rewrite_for_subtext` — Take existing dialogue and layer in subtext, power dynamics, and unspoken meaning

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `subtext_layering.py` | Subtext Layering | Writes dialogue where characters never say what they actually mean. Encodes wants, fears, and power dynamics beneath surface conversation using deflection, topic changes, over-specificity, and conspicuous avoidance. |
| `voice_fingerprinting.py` | Voice Fingerprinting | Gives each character a unique speech pattern through vocabulary range, sentence length distribution, verbal tics, cultural references, and comfort with silence. Two characters should never be interchangeable on the page. |
| `conflict_escalation.py` | Conflict Escalation Rhythm | Structures dialogue exchanges as micro-negotiations where each line shifts the power balance. Maps the give-and-take rhythm so conversations build rather than circle, with clear beats where control transfers. |
| `exposition_laundering.py` | Exposition Laundering | Buries necessary information inside character conflict, discovery, or emotional reaction so it never reads as the author explaining. Tests each expository line against: would this character say this to this person in this moment? |
| `silence_scripting.py` | Silence and Non-Verbal Scripting | Writes the pauses, interruptions, trailing-off, and action lines between dialogue that carry as much meaning as words. Designs moments where what isn't said is the scene's real content. |

---

### 3. character_designer

**Existing commands (migrate to files):**
- `write_characters` — Design and develop the character ensemble for the current stage
- `fix_characters` — Revise characters based on Character Analyst feedback flags

**New commands:**
- `build_character_profile` — Generate deep character profile from concept sketch: psychology, contradictions, arc trajectory
- `design_character_voice` — Create a voice guide for a character: speech patterns, vocabulary, rhetorical habits

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `wound_want_need.py` | Wound-Want-Need Triangle | Designs characters from the inside out: the wound (past damage that shaped them), the want (conscious goal driven by the wound), and the need (unconscious truth they must accept). Every character decision traces back to this triangle. |
| `contradiction_mapping.py` | Contradiction Mapping | Builds characters with deliberate internal contradictions — a pacifist with a violent temper, a generous person who hoards information. Maps which contradiction surfaces in which context, making characters unpredictable yet coherent. |
| `pressure_testing.py` | Behavioral Pressure Testing | Stress-tests characters by placing them in scenarios that force impossible choices between their values. Reveals whether the character has genuine depth or collapses into archetype under pressure. |
| `relationship_web.py` | Relationship Web Dynamics | Maps every character relationship as a power dynamic with history, debt, and tension. Identifies redundant relationships (two characters serving the same narrative function) and missing relationships (tensions that have no embodiment). |
| `arc_milestones.py` | Arc Milestone Design | Plots character transformation as concrete behavioral changes, not abstract growth. Defines the specific moment the character acts differently than they would have in act one, and engineers the causal chain that makes the change earned. |

---

### 4. story_researcher

**Existing commands (migrate to files):**
- `research` — Market research, comps, positioning, zeitgeist, and platform requirements
- `revise_research` — Update research based on Market Analyst feedback flags
- `profile_voice` — Analyze source material and produce a structured voice profile

**New commands:**
- `research_setting` — Deep-dive research into a time period, location, or subculture for authenticity
- `fact_check_narrative` — Verify factual claims, timelines, and technical details in a manuscript

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `lived_detail.py` | Lived-Detail Extraction | Researches not just facts but the sensory, social, and emotional texture of a setting. Focuses on what people ate, complained about, misunderstood, and took for granted — the mundane details that make fiction feel inhabited rather than researched. |
| `anachronism_detection.py` | Anachronism Detection | Cross-references language, technology, social norms, and material culture against the story's time period. Catches not just obvious anachronisms but subtle ones — attitudes, idioms, and assumptions that belong to the writer's era, not the character's. |
| `expert_scaffolding.py` | Expert Knowledge Scaffolding | Translates domain expertise (medical, legal, military, scientific) into character-appropriate dialogue and behavior. Ensures specialists sound like specialists without turning scenes into lectures. |
| `cultural_sensitivity.py` | Cultural Sensitivity Audit | Evaluates portrayals of cultures, communities, and identities for accuracy, nuance, and potential harm. Flags stereotypes, monolithic portrayals, and missing context while suggesting specific improvements grounded in primary sources. |
| `world_consistency.py` | World-Building Consistency Check | Maintains an internal logic ledger for fictional worlds: rules of magic, political structures, economic systems, geography. Catches violations where the story contradicts its own established rules. |

---

### 5. structure_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for narrative structure against established frameworks

**No new commands** — the analyze command covers the analyst's scope.

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `pacing_heatmap.py` | Pacing Heat Map | Measures scene-by-scene pacing by analyzing the ratio of action to reflection, dialogue to description, and scene length variance. Produces a narrative rhythm profile that shows where the story rushes, drags, or breathes. |
| `scene_necessity.py` | Scene Necessity Audit | Applies the cut test to every scene: if removed, does the story still make sense? Scenes that pass the cut test without consequence are flagged for elimination or combination. Every scene must turn at least one value. |
| `structural_symmetry.py` | Structural Symmetry Analysis | Evaluates whether the story's structure has intentional mirroring, echoes, and callbacks between beginning and end, setup and payoff sections. Identifies asymmetries that feel like oversights rather than artistic choices. |
| `pov_discipline.py` | Point-of-View Discipline Check | Verifies consistent POV handling within scenes — catches head-hopping, knowledge leaks where a character knows something they shouldn't, and perspective breaks that pull the reader out of immersion. |
| `transition_scoring.py` | Transition Flow Scoring | Evaluates scene-to-scene transitions for logical flow, temporal clarity, and emotional continuity. Flags jarring jumps that disorient the reader and smooth transitions that accidentally flatten dramatic contrast. |

---

### 6. character_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for character consistency, motivation, and logic

**No new commands.**

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `motivation_chain.py` | Motivation Chain Validation | Traces every character decision back to established motivation. Flags actions that serve plot convenience rather than character truth — the idiot plot detector where characters act stupidly because the story needs them to. |
| `consistency_drift.py` | Consistency Drift Detection | Tracks character traits, knowledge, and emotional state across the full manuscript. Catches moments where a character forgets an established skill, relationship, or trauma because the author did. |
| `agency_audit.py` | Agency Audit | Measures whether each significant character drives events or merely reacts to them. Flags protagonists who are passive passengers in their own story and supporting characters who exist only to deliver information or create problems. |
| `distinctiveness_index.py` | Distinctiveness Index | Evaluates whether each character occupies a unique narrative role, voice, and thematic position. Identifies characters who could be merged without story loss and ensemble gaps where a missing perspective would enrich the narrative. |
| `emotional_arc.py` | Emotional Arc Tracking | Maps each character's emotional state scene-by-scene to verify the arc feels earned. Flags emotional jumps that skip necessary intermediate states — characters who go from grief to acceptance without anger, or from strangers to lovers without trust. |

---

### 7. dialogue_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for dialogue quality and scene construction

**No new commands.**

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `subtext_density.py` | Subtext Density Test | Measures the ratio of surface meaning to underlying meaning in dialogue exchanges. Flags lines where characters say exactly what they mean with no subtext as opportunities for layered writing. |
| `voice_distinctiveness.py` | Voice Distinctiveness Scoring | Covers all dialogue with character names removed and evaluates whether each speaker remains identifiable from speech patterns alone. Scores on vocabulary, rhythm, directness, and rhetorical habits. |
| `information_control.py` | Information Control Analysis | Evaluates who knows what in each conversation and whether characters appropriately protect, reveal, or trade information based on their goals. Catches scenes where characters share information they have no motivation to share. |
| `on_the_nose.py` | On-the-Nose Detection | Identifies dialogue where characters explicitly state theme, emotion, or backstory that should be conveyed through behavior, implication, or conflict. Flags lines that function as author-to-audience communication rather than character-to-character. |
| `power_dynamic.py` | Power Dynamic Mapping | Analyzes status shifts within each dialogue exchange — who's winning, who's losing, where control transfers. Flags conversations with no status movement (static exchanges that could be cut) and those with unrealistic power shifts. |

---

### 8. market_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for market fit, comps, and positioning

**No new commands.**

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `comp_title.py` | Comp Title Analysis | Identifies the 3-5 most relevant comparable titles by analyzing genre positioning, audience overlap, tone, and recency. Evaluates what each comp signals to agents, editors, and readers, and whether the combination positions the manuscript accurately. |
| `genre_convention.py` | Genre Convention Mapping | Catalogs the expected conventions of the target genre and subgenre, then evaluates which conventions the manuscript fulfills, subverts, or ignores. Flags missing conventions that readers will expect and subversions that need to be more intentional. |
| `audience_profiling.py` | Audience Expectation Profiling | Builds a reader profile based on genre, tone, and comp titles: what this audience wants, what they won't tolerate, what delights them. Evaluates the manuscript against these expectations with specific examples. |
| `commercial_hook.py` | Commercial Hook Assessment | Evaluates the story's elevator pitch potential: can the core premise be communicated in one compelling sentence? Identifies the unique selling proposition and tests whether it's distinctive enough to stand out in a crowded market. |
| `trend_positioning.py` | Trend Positioning | Analyzes current market trends, emerging themes, and reader appetite shifts in the target genre. Evaluates whether the manuscript is ahead of, riding, or behind current trends, and what positioning adjustments could improve timing. |

---

### 9. format_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for formatting conventions and craft quality

**No new commands.**

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `manuscript_standards.py` | Manuscript Standards Compliance | Validates formatting against industry-standard submission guidelines: margins, font, spacing, headers, page breaks, scene breaks, chapter headings. Catches formatting that signals amateur status to agents and editors. |
| `typographical_consistency.py` | Typographical Consistency Audit | Checks for consistent handling of em dashes vs en dashes, ellipsis style, quotation mark usage, number formatting, and italicization rules throughout the manuscript. Inconsistency suggests carelessness to professional readers. |
| `scene_break_logic.py` | Scene Break and Chapter Logic | Evaluates whether scene breaks and chapter breaks are placed for maximum dramatic effect. Flags chapters that end on flat notes rather than hooks, and scene breaks that interrupt momentum rather than compress time. |
| `dialogue_punctuation.py` | Dialogue Punctuation and Attribution | Verifies correct dialogue punctuation, tag usage, and attribution clarity. Catches creative but incorrect punctuation, missing beats between speakers, and attribution patterns that slow reading pace. |
| `whitespace_balance.py` | Whitespace and Density Balance | Analyzes the visual rhythm of the page: ratio of dialogue to description, paragraph length variation, and whitespace distribution. Flags pages that are visually intimidating walls of text or choppy fragments that lack substance. |

---

### 10. production_analyst

**Existing commands (migrate to files):**
- `analyze` (currently `cmd_analyze`) — Analyze creative material for production/publishing feasibility

**No new commands.**

**Skills (5):**

| File | NAME | DESCRIPTION |
|------|------|-------------|
| `submission_readiness.py` | Submission Package Readiness | Evaluates whether the manuscript meets the complete submission requirements: query letter, synopsis, sample pages, and full manuscript formatting. Identifies gaps and weak elements that would cause form rejections. |
| `adaptation_potential.py` | Rights and Adaptation Potential | Assesses the story's potential for adaptation across media: film, TV, audio, games, translation. Identifies elements that translate well across formats and those that are medium-specific, informing rights strategy. |
| `production_complexity.py` | Production Complexity Scoring | For scripts and screenplays, evaluates practical production requirements: location count, cast size, VFX needs, period-specific requirements. Flags scenes with high production cost that could be simplified without story loss. |
| `revision_prioritization.py` | Revision Prioritization Matrix | After all analyst feedback is collected, synthesizes findings into a prioritized revision plan. Categorizes issues by severity (story-breaking, quality-reducing, polish-level) and effort (quick fix, moderate rework, structural overhaul). |
| `publication_timeline.py` | Publication Timeline Planning | Maps the realistic path from current manuscript state to publication: remaining revision rounds, beta reader feedback, professional editing stages, submission timeline, and market timing considerations. |

---

## Files to Create

**Per agent (10 agents × pattern):**
- `commands/__init__.py` — command registry with `ALL_COMMANDS`
- `commands/<cmd_name>.py` — one file per command (existing + new)
- `skills/__init__.py` — pkgutil auto-discovery (identical boilerplate across all agents)
- `skills/<skill_name>.py` — one file per skill (5 per agent)

**Total new files:** ~130 files (10 agents × ~13 files each)

## Files to Modify

- 10 `agent.py` files — remove inline `@command` methods, replace `skills_description` property with `format_skills()` import, add command class attributes

## Boilerplate Templates

### skills/__init__.py (identical for all agents)
```python
"""[Agent Name] agent skills registry."""

import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

### skills/<skill_name>.py (example)
```python
NAME = "Three-Act Tension Mapping"
DESCRIPTION = (
    "Maps tension curves across act structure using the principle that each scene "
    "must escalate, complicate, or release tension. Identifies flat zones where "
    "narrative momentum stalls and recommends scene reordering or compression."
)
```

### commands/__init__.py (example for story_architect)
```python
"""Story Architect agent commands registry."""

from .fix_structure import fix_structure
from .map_subplot_threads import map_subplot_threads
from .outline_act_structure import outline_act_structure
from .write_structure import write_structure

ALL_COMMANDS = [write_structure, fix_structure, outline_act_structure, map_subplot_threads]
```

### commands/<cmd_name>.py (example — migrated existing command)
```python
"""Story Architect command: write story structure for current project stage."""

from agents.blueprints.base import command


@command(
    name="write_structure",
    description="Write or create story structure for the current project stage",
    model="claude-sonnet-4-6",
)
def write_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

### commands/<cmd_name>.py (example — new command)
```python
"""Story Architect command: break story into acts with turning points."""

from agents.blueprints.base import command


@command(
    name="outline_act_structure",
    description="Break story into acts with turning points, midpoint reversal, and climax placement",
    model="claude-sonnet-4-6",
)
def outline_act_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

## What Does NOT Change

- System prompts (the large SYSTEM_PROMPT strings) — untouched
- `execute_task` methods and all `_execute_*` methods — stay in `agent.py`
- `_get_voice_constraint` helper — stays in `agent.py`
- Command names, descriptions, and model assignments
- The `@command` decorator and its metadata contract
- `base.py` framework code — no changes needed
- Leader agent — already has the folder pattern

## Out of Scope

- New execution logic for new commands (they dispatch via `execute_task` like existing commands; the `_execute_*` methods for new commands will be added in the implementation plan)
- Changes to the leader agent
- Changes to `base.py` or the framework
- Refactoring system prompts

# Writers Room Ideation & Smart Entry — Design Spec

**Date:** 2026-04-05
**Status:** Approved

## Overview

Add a smart entry-detection step and two new pre-logline stages (`ideation` and `concept`) to the writers room pipeline. The leader analyzes what the user provides — from "write me a blockbuster" to a full draft — and starts the pipeline at the right stage. When starting from nothing, the agents research the market, generate competing concepts, run feedback on all of them, merge the best elements, and refine before entering the existing logline-to-revised-draft pipeline.

## Problem

The current pipeline hard-starts at `logline` and assumes the user arrives with a concrete story idea + source material. This breaks for:

- "Write me a blockbuster" (no idea at all)
- "Something about AI and consciousness" (vague theme, not a story)
- A user who uploads a finished treatment (pipeline wastes time on logline/expose)
- Series concepts (Serienkonzept) that arrive with a bible + pilot outline
- Filmreihe concepts that need installment strategy

## Solution

### Entry Detection

A one-shot Claude call by the leader on the first `generate_task_proposal` invocation. Runs exactly once, stored as `entry_detected: true` in `internal_state`.

**Input:** project goal, source material summaries (from Sources), existing config values (target_format, genre, tone, target_platform).

**Output JSON:**
```json
{
  "detected_format": "series",
  "detected_stage": "ideation",
  "format_confidence": "high",
  "reasoning": "Goal is vague with no source material...",
  "recommended_config": {
    "target_format": "film",
    "genre": "thriller"
  }
}
```

**Stage detection rules:**
- No story idea at all → `ideation`
- Vague idea / premise / concept sketch → `concept`
- Logline exists → `logline` (gets feedback)
- Expose / pitch document → `expose`
- Treatment / Serienkonzept / series bible → `treatment`
- Step outline / beat sheet → `step_outline`
- Full draft / screenplay / manuscript → `first_draft`
- Draft with revision notes → `revised_draft`

**Format detection** covers: film, series (Serienkonzept), limited series, Filmreihe, novel, theatre, short story. Must understand German-language industry terms alongside English.

**Config auto-fill:** if the user didn't set `target_format`, `genre`, or `tone`, the detector recommends values. Stored in `internal_state` as defaults (not written to agent config — that's user-controlled). Pipeline reads from internal_state, user can override via config at any time.

### New Stage: ideation

Only entered when entry detection finds no concrete story idea.

**Creative phase (sequential, 2 agents):**

1. `story_researcher` runs `research` with ideation-focused framing: what's underserved, what audiences want, trending themes/genres, what's being passed on. Uses whatever vague goal exists as a lens.

2. `story_architect` runs new `generate_concepts` command — receives the research brief, generates 3-5 competing concepts. Each concept is a structured pitch:
   - Working title
   - Premise (2-3 sentences)
   - Format recommendation (film / series / limited series / Filmreihe)
   - Genre and tone
   - Target audience
   - Zeitgeist hook (why this works now)

   Output is a single document with all concepts clearly separated.

**Feedback phase (parallel):**

```python
"ideation": [
    ("market_analyst", "full"),
    ("structure_analyst", "lite"),
    ("production_analyst", "lite"),
]
```

Market analyst evaluates commercial viability of each concept. Structure analyst does quick dramatic potential check. Production analyst flags obvious feasibility issues.

**Merge phase (leader, special evaluation):**

Instead of the normal pass/fail, the leader gets an ideation-specific evaluation prompt:
- Rank all concepts based on feedback
- Pick the winner
- Identify strong elements from runners-up that strengthen the winner
- Produce one merged/refined concept

The merged concept is stored as a Document (doc_type `concept`) on the department.

If feedback is universally negative (all concepts get critical flags), the loop repeats — story_architect generates new concepts informed by what failed.

### New Stage: concept

Entered either from ideation (merged winner) or directly from entry detection (user brought a vague idea).

**Creative phase (sequential, 3 agents):**

1. `story_researcher` runs `research` — focused on this specific concept. Comps, positioning, audience, platform fit. If format isn't set, addresses "is this a film or series?" with evidence.

2. `story_architect` runs new `develop_concept` command — builds concept into a structured foundation:
   - Dramatic premise and central conflict
   - World/setting
   - Tonal compass
   - Format recommendation with rationale (if not user-set)
   - For series: season arc shape, episode count suggestion, pilot hook
   - For Filmreihe: installment strategy, franchise potential

3. `character_designer` runs `write_characters` — at concept depth (stage-adaptive output already handles this: protagonist + key relationship at early stages).

**Feedback phase (parallel):**

```python
"concept": [
    ("market_analyst", "full"),
    ("structure_analyst", "lite"),
    ("character_analyst", "lite"),
    ("production_analyst", "lite"),
]
```

**Normal pass/fail loop.** Same mechanism as all other stages. On pass, advance to `logline`.

## Changes to Existing Code

### leader/agent.py

**STAGES:**
```python
STAGES = ["ideation", "concept", "logline", "expose", "treatment", "step_outline", "first_draft", "revised_draft"]
```

**CREATIVE_MATRIX additions:**
```python
"ideation": ["story_researcher", "story_architect"],
"concept": ["story_researcher", "story_architect", "character_designer"],
```

**FEEDBACK_MATRIX additions:**
```python
"ideation": [
    ("market_analyst", "full"),
    ("structure_analyst", "lite"),
    ("production_analyst", "lite"),
],
"concept": [
    ("market_analyst", "full"),
    ("structure_analyst", "lite"),
    ("character_analyst", "lite"),
    ("production_analyst", "lite"),
],
```

**FLAG_ROUTING** — no changes. Existing routing covers all feedback→creative mappings.

**generate_task_proposal:**
- On first call (no `current_stage`): run entry detection instead of defaulting to `STAGES[0]`
- Entry detection sets `current_stage` to the detected stage
- Rest of state machine unchanged

**_propose_creative_tasks:**
- For `ideation` stage: story_architect task gets "generate 3-5 concepts" framing via command_name `generate_concepts`
- For `concept` stage: story_architect task uses `develop_concept` command
- All other stages: unchanged

**_evaluate_feedback:**
- For `ideation` stage: merge evaluation instead of pass/fail. Stores merged concept as Document, advances to `concept`.
- All other stages: unchanged

**New method: _run_entry_detection(agent):**
- Gathers goal, sources, config
- Calls Claude with entry detection prompt
- Sets `current_stage`, stores recommended config in `internal_state`
- Returns the detected stage

### story_architect

**New commands (2 files in commands/):**

`generate_concepts` — Generate 3-5 competing concept pitches based on market research and project goal. Each pitch includes working title, premise, format recommendation, genre, tone, target audience, and zeitgeist hook.

`develop_concept` — Develop a chosen concept into a structured foundation: dramatic premise, central conflict, world/setting, tonal compass, format recommendation. Series-aware: includes season arc, episode count, pilot hook for series formats. Filmreihe-aware: includes installment strategy and franchise potential.

**Modified:**
- `commands/__init__.py` — register 2 new commands
- `agent.py` — add `_execute_generate_concepts` and `_execute_develop_concept` methods, update `execute_task` routing

### New Document Type

Add `concept` to the Document model's `doc_type` choices (alongside existing `voice_profile`). Used to store the merged concept from ideation and the developed concept from concept stage.

## What Stays Untouched

- All 6 analyst agents — no changes
- dialog_writer, character_designer, story_researcher — existing commands/skills unchanged
- base.py framework
- All stages from logline onward — pipeline, matrices, routing all preserved
- The feedback loop mechanism
- Voice profiling gate in `_propose_creative_tasks`
- Frontend (this is a backend-only change — the stage names are already dynamic in the UI)

## Out of Scope

- Web search integration (agents use Claude's training knowledge)
- User-facing stage picker UI
- Multiple concurrent concept tracks (one pipeline at a time)
- Interactive concept refinement with user input mid-ideation (user can always manually create tasks)

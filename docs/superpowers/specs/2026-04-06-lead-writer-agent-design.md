# Lead Writer Agent & Writers Room Pipeline Refactor

**Date:** 2026-04-06
**Status:** Approved
**Scope:** Writers Room department only — base class untouched

## Overview

Introduce a Lead Writer workforce agent that synthesizes creative agents' fragments into cohesive stage deliverables. Refactor the writers room pipeline from 8 stages to 4, add three persistent documents per feedback round with archive-and-link versioning, and simplify the fix routing.

## Problem

Currently, creative agents (story_researcher, story_architect, character_designer, dialog_writer) each produce fragments — research briefs, concept structures, character sheets, dialogue samples. Nobody synthesizes these into a single cohesive document. The user gets useful fragments but never the actual deliverable they asked for (e.g., a Serienkonzept). Additionally, valuable detailed research (e.g., key historical figures, world-building details) gets lost as task reports rotate out of the 5-task context window or get summarized by the consolidation mechanism.

## Stage Pipeline

### New Stages

Replace the current 8 stages (`ideation → concept → logline → expose → treatment → step_outline → first_draft → revised_draft`) with 4:

```python
STAGES = ["pitch", "expose", "treatment", "first_draft"]
```

### Format Detection

The Head Of (WritersRoomLeaderBlueprint) determines format type and terminal stage from the sprint text on first invocation. This is an LLM call — Claude reads the sprint text in whatever language and returns format_type and terminal_stage. No keyword matching.

- **Series path:** Pitch → Exposé → Concept (stage 3 uses `write_concept` skill instead of `write_treatment`) → done
- **Standalone path:** Pitch → Exposé → Treatment → First Draft (or stops earlier depending on sprint intent)

Stored in `internal_state["format_type"]` (`standalone` | `series`) and `internal_state["terminal_stage"]`.

### Stage Descriptions

1. **Pitch** (2-3 pages): Logline, world settings, characters, central conflict. Proves the story is worth telling, characters have depth, establishes tonality.

2. **Exposé** (5-10 pages): Expands on the pitch. Main arc, establishing side arcs, brief character bios, summary of core narrative arc. For series: covers the first season / first batch. Bird's-eye view with beginning, middle, end.

3. **Treatment** (standalone, 20-40+ pages) / **Concept** (series, 15-25 pages):
   - Treatment: The full story told in prose. Scene-level detail, subtext, progressive complications. Reads like a short story.
   - Concept: The series bible. Story engine, world rules, character ensemble dynamics, saga arc, season one breakdown, episode overviews, future season sketches.

4. **First Draft** (standalone only): The actual screenplay, manuscript, or play script. Standalone only — for series, individual episode drafts are a separate concern.

## The Lead Writer Agent

New workforce agent at `writers_room/workforce/lead_writer/agent.py`.

### Role

Synthesizes all creative agents' fragments into the actual stage deliverable. Does not invent — it integrates. The creative agents are the idea generators; the Lead Writer is the prose craftsman who assembles their work into a cohesive document.

**Key principle:** The Lead Writer does NOT alter what the creative agents came up with. It does not rewrite characters, change structure, or invent new elements. It weaves fragments together, adding connective tissue, consistent voice, and narrative flow.

### Blueprint

```python
class LeadWriterBlueprint(WorkforceBlueprint):
    name = "Lead Writer"
    slug = "lead_writer"
    description = "Synthesizes creative team output into cohesive stage deliverables"
    tags = ["creative", "writers-room", "synthesis", "prose"]
```

### 5 Commands (Skills)

#### `write_pitch`
**Output:** 2-3 page pitch document.

Craft directives:
- Open with logline — protagonist defined by contradiction not name, inciting incident, central conflict, stakes
- Establish protagonist through want vs need gap
- Ground the world in one evocative, specific detail that also conveys tone
- Central conflict as engine — inexhaustible dynamic, not a single event
- Prose tone ENACTS the story's tone (comedy pitch is amusing, horror pitch induces unease)
- End with stakes escalation
- For series: convey the story engine (renewable conflict mechanism)
- For standalone: imply the complete arc without revealing resolution

Integration mandate: Build exclusively from creative agents' fragments. Do not invent new characters, conflicts, or world elements.

Pitfalls: Abstract thematic language, name-dropping before reader cares, including subplots, tone mismatch.

#### `write_expose`
**Output:** 5-10 page exposé.

Craft directives:
- Restate logline with more specificity
- Character introductions through arc — starting situation, want, need, weakness, destination. Show transformation, not trait catalogs.
- Three-movement architecture: Setup, Confrontation, Resolution
- Mark five turning points: Inciting Incident, Act I break, Midpoint, Act II break, Climax
- Sustain tonal throughline across all pages
- Thematic argument visible in arc of events, not stated didactically
- MUST reveal complete story including resolution
- For series: first season arc in detail, sketch saga arc, demonstrate engine renewability
- For standalone: complete story arc

Integration mandate: story_architect's structure is skeleton, character_designer's arcs are character material, story_researcher's world details ground prose.

Pitfalls: Withholding ending, subplot overload, character as catalog, losing chronological clarity, underdeveloped antagonism.

#### `write_treatment`
**Output:** 20-40+ pages. Standalone only.

Craft directives:
- Present tense, third person, scene by scene
- Every scene turns a value — something changes positive to negative or vice versa
- Convey character subtext, NOT dialogue. Describe emotional undercurrents, never write actual dialogue lines.
- Progressive complications escalate relentlessly — the middle is where treatments die
- Prose carries voice and tone of the intended work
- World and atmosphere as force shaping the story, not wallpaper
- Full character arcs traceable: weakness/need → desire → opponent → plan → battle → self-revelation → new equilibrium
- Give climax and resolution proportional space

Integration mandate: story_architect's beats are scene map, character_designer's psychology drives subtext, story_researcher's world details are sensory texture, dialog_writer's tonal work informs prose voice.

Pitfalls: Writing dialogue, scene-by-scene monotony, neglecting Act II, camera directions, forgetting tone.

#### `write_concept`
**Output:** 15-25 pages. Series only.

Craft directives:
- Creator's statement — why this story needs to exist (from project goal)
- STORY ENGINE first and prominently — the renewable mechanism generating conflict. One sentence or it's not ready.
- Tonal pillars: 3-5 specific adjectives, enacted in prose
- World rules: social codes, hierarchies, power structures. For speculative fiction: magic systems, technology, politics.
- Character ensemble as WEB of relationships — not isolated profiles. Each character = different approach to thematic question. Backstory as unexploded ordnance.
- Saga arc: protagonist's journey across entire run. Series-level inciting incident, midpoint, climax.
- Season one breakdown: inciting incident, midpoint, climax. A/B story interweave. Character arcs.
- Episode overviews (1-3 paragraphs each): show VARIETY and THROUGHLINE. Engine visible in each.
- Future seasons: 1-2 paragraphs each. Prove intended destination, not endless repetition.

Integration mandate: story_researcher's world-building is factual foundation, story_architect's saga structure is arc blueprint, character_designer's ensemble dynamics are relationship web, dialog_writer's voice work informs tonal pillars.

Pitfalls: No clear engine, character catalogs without dynamics, vague thematic statements, same-shape episode overviews, neglecting sustainability.

#### `write_first_draft`
**Output:** Full-length piece. Standalone only.

Craft directives:
- The treatment told us ABOUT the story. The first draft IS the story.
- Must be COMPLETE, not perfect.
- For screenplay: scene headings, visual action lines, centered dialogue. Think in images.
- For prose manuscript: consistent POV, narrative voice present, deliberate scene vs summary, use interior life.
- For stage play: dialogue-dominant, minimal stage directions, embrace theatrical constraints, read aloud.
- Universal: every scene dramatizes conflict, distinct character voices, exposition woven into conflict, enter late / leave early.

Integration mandate: treatment is scene map, character_designer's voice profiles drive speech, dialog_writer's sensibility informs dialogue.

Pitfalls: On-the-nose dialogue, exposition dumps, identical character voices, overwriting directions, deviating from treatment structure.

## State Machine

### New States

7 states replacing the current 6:

```
not_started
  → creative_writing       (creative agents write fragments in parallel)
    → lead_writing          (lead_writer synthesizes deliverable)
      → feedback            (feedback agents critique the deliverable)
        → review            (creative_reviewer scores)
          → PASSED → [create/archive docs] → advance to next stage
          → FAILED → [create/archive docs] → back to creative_writing
```

### State Transitions in `generate_task_proposal()`

| State | Condition | Action |
|---|---|---|
| `not_started` | Stage begins | Dispatch creative agents per CREATIVE_MATRIX → set `creative_writing` |
| `creative_writing` | No active tasks | Dispatch lead_writer with appropriate `write_*` command → set `lead_writing` |
| `lead_writing` | No active tasks | Create/archive Deliverable + Research & Notes docs. Dispatch feedback agents per FEEDBACK_MATRIX → set `feedback` |
| `feedback` | No active tasks | Dispatch creative_reviewer to consolidate scores → set `review` |
| `review` | Passed | Create/archive Critique doc. Advance to next stage → set `not_started` |
| `review` | Failed | Create/archive Critique doc. Increment iteration → set `creative_writing` |

### Key Differences from Current

1. `lead_writing` state is new — inserted between creative writing and feedback
2. Feedback agents critique the Lead Writer's deliverable, not individual fragments
3. On failure, loop resets to `creative_writing` — everyone rewrites with Critique in context
4. `_propose_review_chain` still returns `None`
5. `depends_on_previous` chains lead_writer after creative agents
6. FLAG_ROUTING removed — replaced by whole-team revision with Critique document

### Unchanged from Base Class

- `_apply_quality_gate()` — untouched
- `_evaluate_review_and_loop()` — untouched
- `should_accept_review()` — untouched
- `_on_dispatch` mechanism — untouched
- `MAX_REVIEW_ROUNDS` / `MAX_POLISH_ATTEMPTS` — untouched
- Sprint gating — untouched
- Active task check — untouched

## Three Documents Per Round

### Document Types

Three new `DocType` choices on `Document` model:

```python
STAGE_DELIVERABLE = "stage_deliverable", "Stage Deliverable"
STAGE_RESEARCH = "stage_research", "Stage Research & Notes"
STAGE_CRITIQUE = "stage_critique", "Stage Critique"
```

### Documents Created

| Document | doc_type | Content Source | Purpose |
|---|---|---|---|
| Deliverable | `stage_deliverable` | Lead Writer's task report | The actual pitch / exposé / treatment / concept |
| Research & Notes | `stage_research` | All creative agents' task reports concatenated, full and unsummarized | Preserves detailed research, character logic, dialogue experiments |
| Critique | `stage_critique` | All feedback agents' reports + creative_reviewer's verdict | What critics found, scored, flagged |

### Naming Convention

```
Pitch v1 — Deliverable
Pitch v1 — Research & Notes
Pitch v1 — Critique
```

### Archive-and-Link Pattern

On subsequent rounds after failed review:

```
Pitch v1 — Deliverable       → is_archived=True, consolidated_into → Pitch v2 — Deliverable
Pitch v1 — Research & Notes  → is_archived=True, consolidated_into → Pitch v2 — Research & Notes
Pitch v1 — Critique          → is_archived=True, consolidated_into → Pitch v2 — Critique
```

Uses existing `Document.is_archived` and `Document.consolidated_into` fields. On v1, no prior doc exists — the archive step is simply skipped (query returns None, if-block doesn't execute).

### When Documents Are Created

| Moment | Documents |
|---|---|
| `lead_writing` completes → before dispatching feedback | Deliverable + Research & Notes |
| `review` completes (pass or fail) | Critique |

### Context Management

`get_context()` at `base.py:250` filters `is_archived=False` — agents only see the latest version. Archived versions remain in DB, linked via `consolidated_into`, queryable if needed. Context growth is controlled since old versions are archived.

## Matrices

### Creative Matrix

Lead Writer is NOT in the creative matrix — dispatched separately via state machine.

```python
CREATIVE_MATRIX = {
    "pitch": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "expose": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "treatment": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "concept": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "first_draft": ["story_architect", "character_designer", "dialog_writer"],
}
```

### Feedback Matrix

```python
FEEDBACK_MATRIX = {
    "pitch": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("character_analyst", "lite"),
    ],
    "expose": [
        ("market_analyst", "full"),
        ("structure_analyst", "full"),
        ("character_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "treatment": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("production_analyst", "full"),
        ("market_analyst", "lite"),
    ],
    "concept": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("market_analyst", "full"),
        ("production_analyst", "full"),
    ],
    "first_draft": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("format_analyst", "full"),
        ("production_analyst", "lite"),
        ("market_analyst", "lite"),
    ],
}
```

### FLAG_ROUTING

Removed. On failed review, state resets to `creative_writing`. All agents get the Critique document via department documents context.

### Review Pairs

Single pair — creative_reviewer reviews the Lead Writer's deliverable:

```python
def get_review_pairs(self):
    return [{
        "creator": "lead_writer",
        "creator_fix_command": "write",
        "reviewer": "creative_reviewer",
        "reviewer_command": "review-creative",
        "dimensions": [
            "concept_fidelity", "originality", "market_fit",
            "structure", "character", "dialogue", "craft", "feasibility",
        ],
    }]
```

## Voice Profile Gate

Unchanged. `_propose_creative_tasks()` checks for voice profile document before allowing creative work. Triggered on stage `pitch` (first stage). Runs voice profiling via story_researcher if source material exists but no profile yet.

## Files Affected

| Change | File |
|---|---|
| New lead_writer blueprint + 5 skills | New: `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py` |
| New stage pipeline + state machine | `backend/agents/blueprints/writers_room/leader/agent.py` |
| Format detection | `backend/agents/blueprints/writers_room/leader/agent.py` |
| Document creation helper | `backend/agents/blueprints/writers_room/leader/agent.py` |
| New DocType choices | `backend/projects/models/document.py` |
| Updated matrices + task specs | `backend/agents/blueprints/writers_room/leader/agent.py` |
| Simplified fix routing | `backend/agents/blueprints/writers_room/leader/agent.py` |
| Updated system prompt | `backend/agents/blueprints/writers_room/leader/agent.py` |
| Blueprint registry entry | `backend/agents/blueprints/writers_room/workforce/__init__.py` |
| **Base class (`base.py`)** | **Untouched** |

# Story Bible — Persistent Canon Tracking for the Writers Room

**Date:** 2026-04-10
**Status:** Spec — approved, not yet implemented

## Problem

Every agent task is stateless. No persistent record tracks characters, locations, timeline, or established facts. Each agent re-reads all prior task reports from scratch and can hallucinate, contradict, or silently drop established decisions.

Specific failures:

- Character decisions established in pitch get dropped in treatment
- Agents invent details that contradict prior deliverables
- Voice profiles produced by story_researcher are analytical, not operational — no agent can follow them mechanically
- No diff of what changed between stages
- No way to reject dramatically weak ideas before they pollute the pipeline

## Design Decisions

- **Storage:** Output model with `label="story_bible"`, one per sprint per department. No new models, no migrations.
- **Ownership:** Writers room leader owns the bible — generation, storage, injection, update. Nothing moves to base.py.
- **Timing:** Bible generates after each stage deliverable passes its gate, before advancing to the next stage.
- **Canonical format:** Markdown, rendered from structured JSON. Single source of truth in the Output — no dual storage in internal_state.
- **Schema:** Domain-specific to the writers room. Defined as `STORY_BIBLE_SCHEMA` on the writers room leader.
- **Canon verification:** Lives on the creative reviewer, not the authenticity analyst. The analyst stays focused on AI detection.
- **Idea rejection:** Also lives on the creative reviewer. A new "WEAK_IDEA" verdict triggers fresh ideation, not revision of the same material.

## Bible Content Structure

Structured markdown with `[ESTABLISHED]` (dramatized in a deliverable) and `[TBD]` (mentioned but not yet dramatized) tags. These tags are internal tracking — deliverables themselves are always complete, ready to send, no TBDs.

Sections:

- **Characters** — name, role, status, key decisions, relationships, voice directives
- **Timeline** — when, what, source, established/tbd status
- **Canon Facts** — non-negotiable established facts. Contradicting these is a critical failure.
- **World Rules** — constraints that govern the story world (who has access to what, how institutions operate, what's never shown)
- **Stage Changelog** — per stage transition: what was added, changed, dropped

## Bible Generation

The leader calls `call_claude_structured` with `STORY_BIBLE_SCHEMA` after a stage passes.

**Input:**
- Previous bible (if any)
- Current stage deliverable
- Voice profile Document
- Stage name

**Prompt instructions (from SCORE + Novarrium research):**
- Extract every fact established in the deliverable — be exhaustive
- Identify what changed from the previous bible
- Flag anything dropped (present in prior bible but contradicted or absent)
- Populate the changelog
- Flip `tbd` items to `established` when they appear dramatized in the deliverable
- Flag `tbd` items that should have been resolved by this stage but weren't

**Output:** Structured JSON conforming to `STORY_BIBLE_SCHEMA`, rendered to markdown by `_render_story_bible()`, stored via `Output.update_or_create`.

### STORY_BIBLE_SCHEMA

```python
STORY_BIBLE_SCHEMA = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "relationships": {"type": "array", "items": {"type": "string"}},
                    "voice_directives": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "when": {"type": "string"},
                    "what": {"type": "string"},
                    "source": {"type": "string"},
                    "status": {"type": "string", "enum": ["established", "tbd"]},
                },
            },
        },
        "canon_facts": {"type": "array", "items": {"type": "string"}},
        "world_rules": {"type": "array", "items": {"type": "string"}},
        "changelog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transition": {"type": "string"},
                    "added": {"type": "array", "items": {"type": "string"}},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "dropped": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}
```

## Context Injection

The bible is injected into every creative task's context via `_get_delegation_context()` on the writers room leader:

```
## Story Bible (CANON — do not contradict)
{bible_output.content}
```

Agents that receive the bible: story_architect, character_designer, dialog_writer, lead_writer, creative_reviewer.

Agents that do not: story_researcher (produces research that feeds into the bible, does not consume it), authenticity_analyst (AI detection only).

## Creative Writing Skills Integration

Operational instructions drawn from external research, added to agent system prompts:

### Action-First Sharpening (RainLib visual-first principle)

**Agents:** lead_writer, dialog_writer, story_architect

"Show observable actions, not abstract psychology. Replace 'Jakob felt betrayed' with 'Jakob closed the folder and walked out.' Replace 'She was nervous' with 'She checked her phone three times in a minute.' Internal states must be externalized through behavior, dialogue, or physical detail."

### Pre-Writing Bible Consultation (cw-prose-writing)

**Agents:** story_architect, character_designer, dialog_writer, lead_writer

"Before writing any scene, check: (1) Are all characters consistent with bible key decisions? (2) Do relationships match? (3) Does the setting respect world rules? (4) Does the timeline fit?"

### Continuity Protocol (RainLib + SCORE)

**Agents:** lead_writer

"Before synthesizing creative team output into a deliverable: list every character mentioned. Cross-reference each against the bible. Flag any contradiction before writing. Resolve contradictions in favor of the bible."

### Voice as Directives (cw-style-skill-creator)

**Agents:** story_researcher

Voice profiles must be operational directives, not analytical descriptions. Each directive is one line a writer can follow mechanically. Include example phrases in the original language.

## Creative Reviewer Enhancement

Two new responsibilities added to the creative reviewer:

### Canon Verification

When a story bible is present in context:

- Every character's behavior checked against bible key decisions and relationships
- Every scene checked against world rules and timeline
- Dialogue checked against voice directives
- Contradiction with `[ESTABLISHED]` items = critical failure
- `[TBD]` items may be freely developed but must be internally consistent

### Dramatic Weakness Detection (Idea Rejection)

Evaluates dramatic quality, not just consistency:

- **Logical threshold:** Does the cause-effect chain hold? Would a smart character make this decision given what they know? Plot-convenient stupidity = rejection.
- **Stakes calibration:** Proportional to the stage. Pitch needs existential stakes for the protagonist. Expose needs escalation. Treatment needs no scene without consequence. First draft needs every page to matter.
- **Dramatic economy:** If a subplot could be cut without the main arc collapsing, it's weak.

**Scope scaling by stage:**
- Pitch/expose: full storylines, character arcs, central conflicts
- Treatment/concept: scene sequences, subplot arcs, turning points
- First draft: individual scenes, dialogue decisions, specific beats

### WEAK_IDEA Verdict

A new verdict type distinct from CHANGES_REQUESTED. Signals that the direction is wrong, not the execution. Feedback says what's weak and why but does not prescribe the replacement. The pipeline loops back to creative tasks for a fresh take — not revision of the same material.

## Voice Profile Reform

The story_researcher's `profile_voice` command changes output format:

**Before (analytical):**
> "Jakob's speech patterns are characterized by directness and brevity. He tends to avoid conditional language."

**After (directive):**
> - Short declarative sentences. Never apologizes.
> - Avoids subjunctive ("would", "could"). States intent as fact.
> - Speaks about people as assets. "Was bringt er uns?"
> - Never uses "ich finde" or "vielleicht". Says "Das machen wir" or "Das machen wir nicht."

The voice profile Document continues to exist as its own artifact. The bible's voice section is the operational copy that agents consume. When the leader generates the bible, the voice profile Document is included as input — Claude incorporates its directives into each character's voice section.

## Changes by File

### Writers Room Leader (`leader/agent.py`)

- New `STORY_BIBLE_SCHEMA` constant
- New method `_update_story_bible(agent, sprint, stage)` — reads current bible from Output, reads deliverable, reads voice profile, calls `call_claude_structured`, renders, stores
- New method `_render_story_bible(data: dict) -> str` — JSON to markdown
- Bible generation triggered in stage transition after `passed`, before advancing to next stage
- `_get_delegation_context()` injects bible into creative task contexts

### Creative Reviewer (`workforce/creative_reviewer/agent.py`)

- Canon verification against bible's established items
- Dramatic weakness detection (logical threshold, stakes, dramatic economy)
- New WEAK_IDEA verdict type
- Bible injected into reviewer context

### Story Researcher (`story_researcher/agent.py`)

- `profile_voice` system prompt changed: directives not descriptions

### Lead Writer (`lead_writer/agent.py`)

- System prompt: continuity protocol (cross-reference bible before synthesizing)
- System prompt: action-first sharpening

### Story Architect, Character Designer, Dialog Writer

- System prompt: pre-writing bible consultation
- Story architect, dialog writer: action-first sharpening

### Leader State Machine

- `_propose_fix_task()` distinguishes CHANGES_REQUESTED (revision loop) from WEAK_IDEA (re-ideation loop)

## Not Touched

- Base blueprint (`base.py`) — nothing moves to base level
- Authenticity analyst — stays AI detection only
- Output model — no schema changes
- No new models, no migrations

## Not In Scope

- Cross-sprint bible merging (each sprint has its own)
- Bible editing UI (view-only, like other outputs)
- Automated NLP fact extraction (bible is Claude-generated)
- Multi-department bible sharing (each department maintains its own)

# Story Bible — Persistent State Tracking via Sprint Output

**Date:** 2026-04-07
**Status:** Design — not yet implemented

## Problem

Every agent task is stateless. There's no persistent structured record of characters, locations, timeline, or established facts. Each agent re-reads all prior task reports from scratch and can hallucinate, contradict, or silently drop established decisions.

Specific failures this causes:

- Character decisions established in pitch get dropped in treatment
- Agents invent details that contradict what was already written
- Voice profiles produced by story_researcher are never consumed as operational instructions
- No diff of what changed between stages — no way to catch regressions
- Authenticity analyst checks quality but can't fact-check against the story's own canon

## Research — What Others Do

### Creative Writing Skills (haowjy/creative-writing-skills)

- **cw-prose-writing**: Before writing, discover and load style guides + character profiles + location wikis + timelines. Our agents don't do this.
- **cw-style-skill-creator**: Extract voice from samples as directive instructions ("When writing X, do Y") not descriptive analysis. Our voice profiles are analytical, not operational.
- **cw-brainstorming**: Preserve vagueness, allow contradictions, tag AI suggestions vs author ideas. Relevant for early stages where the bible should mark things as `[TBD]` vs `[ESTABLISHED]`.

### Scriptwriter Skill (RainLib)

- **Continuity protocols**: Episode history review and character state verification between episodes. We have nothing like this.
- **Visual-first principle**: "Describe observable actions, not abstract psychology." Sharper version of our ACTION-FIRST mandate.

### SCORE Framework (academic, arxiv 2503.23512)

- **Dynamic State Tracking**: Monitor characters/objects via structured state, not prose. Track who knows what, who is where, what has changed.
- **Post-generation consistency verification**: After generating content, verify against extracted facts.
- **Hybrid retrieval**: TF-IDF + semantic similarity for finding relevant canon when generating. Achieves 23.6% higher coherence and 41.8% fewer hallucinations vs baseline.

### Novarrium Logic-Locking (commercial)

- Automatic fact extraction from every chapter
- Relevance-weighted fact injection into generation prompts
- Post-generation consistency verification against established facts

## Design

### Storage: Reuse Sprint Output

The Output model already supports `update_or_create` with a unique `(sprint, department, label)` constraint. The story bible is another Output:

```python
Output.objects.update_or_create(
    sprint=sprint,
    department=agent.department,
    label="story_bible",
    defaults={
        "title": "Story Bible",
        "output_type": "markdown",
        "content": bible_content,
    },
)
```

This means:
- One story bible per sprint per department (same constraint as deliverables)
- Updated in-place after each stage completes — accumulates, never resets
- Visible in the UI alongside other sprint outputs (deliverable, critique, research)
- No new models, no migrations

### Content Structure

The story bible is structured markdown with clear sections. Each section has items marked as `[ESTABLISHED]` (written in a deliverable) or `[TBD]` (mentioned but not yet dramatized):

```markdown
# Story Bible — Stadt als Beute

## Characters

### Jakob Hartmann
- **Role:** CEO, eldest brother, public face
- **Status:** active protagonist [ESTABLISHED]
- **Key Decisions:**
  - Signed Friedrichshain acquisition (pitch) [ESTABLISHED]
  - Fired CFO after due diligence leak (expose) [ESTABLISHED]
- **Relationships:**
  - Felix (younger brother) — resentful, excluded from board [ESTABLISHED]
  - Katrin (ex-wife) — holds shares, leverages access [TBD]
- **Voice Directives:**
  - Short declarative sentences. Never apologizes.
  - Avoids subjunctive ("would", "could"). States intent as fact.
  - Speaks about people as assets. "Was bringt er uns?"

### Felix Hartmann
- **Role:** Middle brother, shadow operator
- ...

## Timeline

| When | What | Source |
|------|------|--------|
| Pre-series | IPO of internet company, €2.3B exit | pitch [ESTABLISHED] |
| Ep1 | First property acquisition, Friedrichshain block | pitch [ESTABLISHED] |
| Ep2 | Bezirksamt blocks permit | expose [ESTABLISHED] |
| Ep3 | WohnGut eG insolvency filing | expose [TBD] |

## Established Facts (Canon)

These are non-negotiable. Any deliverable contradicting these is a bug.

- Company name: Hartmann Capital GmbH & Co. KG
- Office: Potsdamer Platz, 14th floor penthouse
- The Genossenschaft is called "WohnGut eG"
- Florian-Schmidt-analog character name: Torsten Falk
- Bezirksamt operates 9-16 Uhr — no evening scenes there

## World Rules

- No character has direct access to the Bürgermeister
- All property deals require Bezirksamt Genehmigung (plot mechanism)
- The brothers' internet company is never named — referred to as "das Imperium"
- Berlin Senate is backdrop, never foreground — no scenes inside the Senat

## Stage Changelog

### Pitch → Expose
- Added: Felix's side deal with WohnGut board member
- Changed: Katrin from neutral ex-wife to active antagonist with board seat
- Dropped: Nothing
```

### How It Gets Written

The **lead writer** produces the story bible after writing each stage deliverable. This is a second `call_claude_structured` call with a JSON schema:

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

The structured JSON is then rendered to markdown and stored as the Output content. Structured data is also stored in the leader's `internal_state["story_bible"]` for programmatic access.

### How Agents Consume It

**Leader injects it into every creative task's context:**

```python
# In _propose_creative_tasks / _propose_lead_writer_task
bible_output = Output.objects.filter(
    sprint=sprint, department=agent.department, label="story_bible"
).first()

if bible_output:
    step_plan += f"\n\n## Story Bible (CANON — do not contradict)\n{bible_output.content}"
```

**What each agent does with it:**

| Agent | How it uses the story bible |
|-------|---------------------------|
| **story_architect** | Structure must align with established timeline. New scenes must fit world rules. |
| **character_designer** | Characters must match established decisions and relationships. Voice directives are binding. |
| **dialog_writer** | Voice directives are the primary constraint. Every line must pass the "would this character say this?" test against the bible. |
| **lead_writer** | Reads the bible before synthesizing. Updates it after writing. Produces the changelog. |
| **authenticity_analyst** | Checks deliverable against canon facts and world rules. Any contradiction = critical failure. |
| **story_researcher** | Voice profile output format changes to directives ("When writing X, do Y") that feed into the bible's voice section. |

### Authenticity Analyst Enhancement

The authenticity analyst gets a new check — **CANON VERIFICATION**:

```
CHECK: CANON VERIFICATION (if story bible provided)
For every character mentioned in the deliverable:
  - Does their behavior match established decisions?
  - Do their relationships match the bible?
  - Does dialogue match voice directives?

For every scene:
  - Does it respect world rules?
  - Does it fit the established timeline?
  - Are there new facts that should be added to canon?

Any contradiction with [ESTABLISHED] items = critical failure (score 0).
[TBD] items may be freely developed — but must be internally consistent.
```

### Voice Profile Reform

The story_researcher's `profile_voice` command currently produces analytical output like:

> "Jakob's speech patterns are characterized by directness and brevity. He tends to avoid conditional language."

This changes to **directive output** that goes directly into the story bible:

> - Short declarative sentences. Never apologizes.
> - Avoids subjunctive ("would", "could"). States intent as fact.
> - Speaks about people as assets. "Was bringt er uns?"
> - Never uses "ich finde" or "vielleicht". Says "Das machen wir" or "Das machen wir nicht."

The lead writer copies these verbatim into the story bible's voice section for each character.

## What Changes in the Codebase

### Writers Room Leader (`leader/agent.py`)

1. After `_create_stage_documents` / deliverable writing, call `_update_story_bible(agent, sprint, stage)`
2. New method `_update_story_bible`: reads current bible from Output, reads new deliverable, calls `call_claude_structured` with STORY_BIBLE_SCHEMA to produce updated bible, writes Output
3. Inject bible into every creative task context via step_plan

### Lead Writer (`lead_writer/agent.py`)

1. System prompt addition: "After writing the stage deliverable, you will also be asked to update the Story Bible."
2. New command or task suffix for bible update

### Authenticity Analyst (`authenticity_analyst/agent.py` — writers room)

1. Add CANON VERIFICATION check to the 7-check methodology
2. Only active when story bible is provided in context

### Story Researcher (`story_researcher/agent.py`)

1. `profile_voice` output format changes from analytical to directive
2. System prompt update: "Voice profiles must be DIRECTIVES, not descriptions"

### Base Context Injection

No changes to base.py — the leader controls what goes into step_plan per department.

## Not In Scope

- Cross-sprint bible merging (each sprint has its own bible)
- Bible editing UI (view-only for now, like other outputs)
- Automated fact extraction from prose (bible is Claude-generated, not NLP-extracted)
- Multi-department bible sharing (each department maintains its own)

## Dependencies

- Sprint Output model already exists — no migration needed
- `call_claude_structured` already exists — used for bible generation
- Leader's `_update_sprint_output` already handles the Output CRUD pattern

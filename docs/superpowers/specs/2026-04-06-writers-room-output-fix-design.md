# Writers Room Output Fix — Design Spec

**Date:** 2026-04-06

## Goal

Fix three bugs in the writers room sprint cycle:

1. Revision patches are never applied because the lead_writer outputs prose + JSON and `json.loads` fails
2. Feedback agents critique raw creative work (dialogue scenes, character profiles) instead of the deliverable
3. Sprint output shows only the deliverable — critique and research are not surfaced

---

## Root Causes

**Bug 1 — Lead writer produces prose + JSON in revision mode**
`_apply_revision_or_replace` calls `json.loads(report)` which fails when the model prefixes its JSON with an explanation. The fallback saves the raw report as the deliverable.

**Bug 2 — Feedback agents see all sibling task reports**
`get_context()` injects every sibling agent's recent task reports. Feedback agents see dialogue scenes, character profiles, etc. and critique those instead of the stage deliverable.

**Bug 3 — Single Output record per sprint**
`_update_sprint_output` creates one `Output` per `(sprint, department)`. Critique and research documents exist as `Document` objects but are never mirrored into `Output`.

---

## Design

### Fix 1 — Lead writer revision prompt

In `lead_writer/agent.py`, the revision mode instructions are updated to require clean JSON output only:

> "Output ONLY the JSON revision object. No preamble, no explanation, no prose. Start your response with `{` and end with `}`."

`json.loads` then works without modification.

### Fix 2 — WritersRoomFeedbackBlueprint

New base class `WritersRoomFeedbackBlueprint` in `backend/agents/blueprints/writers_room/workforce/base.py`.

Overrides `get_context()` relative to the default `WorkforceBlueprint`:

- **Removed:** sibling task reports
- **Kept:** project goal, agent's own recent tasks
- **Kept:** department documents (the `stage_deliverable` is already in here)
- **Added:** a clear label on the context so the agent knows it is reading the synthesized deliverable, not raw fragments

All six feedback agent blueprints (market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst) and the creative_reviewer inherit from `WritersRoomFeedbackBlueprint` instead of `WorkforceBlueprint`.

### Fix 3 — Three Output records

**Model change:** unique constraint on `Output` changes from `(sprint, department)` to `(sprint, department, label)`. One migration.

**Label convention:** `{stage}:{type}` — e.g. `expose:deliverable`, `expose:critique`, `expose:research`.

**Leader changes in `leader/agent.py`:**

- `_update_sprint_output(agent, sprint, stage, content)` gains a `output_type` parameter (`"deliverable"`, `"critique"`, `"research"`). Label becomes `f"{effective_stage}:{output_type}"`.
- `_create_deliverable_and_research_docs` calls `_update_sprint_output` twice: once for `deliverable`, once for `research`.
- `_create_critique_doc` calls `_update_sprint_output` once for `critique`.

**Lead writer revision hint:**

One sentence added to revision instructions: "If the critique praises material not yet present in the deliverable, check the stage research document — it contains the raw creative work. You may incorporate it if it serves the story, but the creative decision is yours."

### Fix 4 — Frontend

The department view already renders output rows. With three `Output` records per sprint it renders three rows. No layout changes — same component, more data.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py` | Revision prompt: output JSON only |
| `backend/agents/blueprints/writers_room/workforce/base.py` | New `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py` | Inherit from `WritersRoomFeedbackBlueprint` |
| `backend/agents/blueprints/writers_room/leader/agent.py` | 3 Output records, `output_type` param |
| `backend/projects/models/output.py` | Unique constraint update |
| Migration | `(sprint, department, label)` unique constraint |
| `frontend/components/department-view.tsx` | Render all output rows (no layout change) |

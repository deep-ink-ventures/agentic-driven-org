# Section-Based Revision for Lead Writer

**Date:** 2026-04-14
**Status:** Approved
**Problem:** JSON-based revision mechanism is fundamentally broken — German typographic quotes break parsing, double-encoding from structured output, truncation at token limits, character-level repair keeps failing on new edge cases. Every round hits a new parsing failure.

## Design

### Round 1 (synthesis)
Unchanged — lead writer outputs full deliverable as prose via `call_claude`.

### Round 2+ (revision)
Lead writer receives the critique and outputs ONLY the sections it revised, as plain prose under their original markdown headers. The pipeline replaces matching sections in the existing deliverable. Everything else stays byte-identical.

### Matching rule
A "section" = a markdown header (`##`, `###`, etc.) and everything below it until the next header of equal or higher level. The pipeline finds the header in the existing deliverable by exact string match and replaces the content block.

### Pitch stage (no headers)
If the deliverable has no markdown headers, or the lead writer's output contains no headers, the entire output replaces the entire deliverable. Pitch = one logical section = full rewrite.

### Step plan for revision rounds
```
## REVISION MODE
The current Stage Deliverable and the Critique are in the department documents.
Your job is to REVISE the existing deliverable.

OUTPUT ONLY the sections you changed, under their EXACT original markdown headers.
Sections you don't output stay unchanged. Write complete section content — not diffs,
not instructions, not JSON.

If the deliverable has no section headers, output the full revised document.
```

### New method
`_apply_section_updates(existing: str, revised_output: str) -> str` on WritersRoomLeaderBlueprint:
- Parse headers from `revised_output`
- For each header found in `existing`, replace the section content
- If header NOT found in existing, append at the end (never drop content)
- If no headers in `revised_output`, return `revised_output` as-is (full replacement)

### Delete
- `REVISION_SCHEMA` on LeadWriterBlueprint
- `call_claude_structured` path in `_execute_write`
- `_try_parse_revision_json` method
- `_repair_json_quotes` method
- `_looks_like_revision_json` method
- `_apply_revisions` method (replace/replace_section/replace_between)
- `_apply_revision_or_replace` method
- `_replace_section` static method (replaced by new `_apply_section_updates`)
- `_replace_between` static method
- `_strip_code_fences` static method
- All JSON-related revision instructions in `_propose_lead_writer_task`
- Double-encoding unwrap code in lead_writer and leader

### Error handling
- Header not found in existing doc: log warning, append section at end (never drop)
- No headers in revision output: full document replacement (safe for pitch)
- Empty revision output: keep existing deliverable, log error

### Files changed
1. `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py` — remove REVISION_SCHEMA, structured output path, revert to plain call_claude for all rounds
2. `backend/agents/blueprints/writers_room/leader/agent.py` — delete JSON parsing/repair methods, replace `_apply_revision_or_replace` with `_apply_section_updates`, rewrite revision step_plan
3. `backend/agents/tests/test_writers_room_state_machine.py` — update revision mode tests

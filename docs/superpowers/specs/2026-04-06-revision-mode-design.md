# Revision Mode: Surgical Edits Instead of Full Rewrites

**Date:** 2026-04-06
**Status:** Approved
**Scope:** Writers Room department only — base class untouched
**Depends on:** Lead Writer agent spec (2026-04-06-lead-writer-agent-design.md)

## Problem

On revision rounds (iteration > 0), all agents rewrite their entire output from scratch. This causes:

1. **Subtle drift** — the LLM "improves" prose that should be preserved, changing word choices, rhythm, and voice
2. **Loss of praised material** — sections the critique explicitly praised get rewritten anyway
3. **Inefficiency** — a 30-page treatment re-output for 2 changed paragraphs
4. **Presentation risk** — if the user shows the document to humans between rounds, subtle changes to "approved" sections are unacceptable

## Solution

On revision rounds, agents output **structured edits** instead of full documents. A `_apply_revisions()` helper applies edits to the existing document. Untouched sections are **byte-identical** — never processed by the LLM.

## Revision Format

Agents on revision rounds output JSON with a list of edits:

```json
{
  "revisions": [
    {
      "type": "replace",
      "old_text": "exact text to find",
      "new_text": "replacement text"
    },
    {
      "type": "replace_section",
      "section": "## Act II",
      "new_content": "rewritten section content"
    },
    {
      "type": "replace_between",
      "start": "unique start anchor text",
      "end": "unique end anchor text",
      "new_content": "replacement for everything between start and end inclusive"
    }
  ],
  "preserved": "Brief note on what was deliberately kept unchanged and why"
}
```

### Three Edit Operations

| Operation | Use case | How it works |
|---|---|---|
| `replace` | Surgical — a line, a paragraph, a passage | Find exact `old_text`, replace with `new_text`. Must match exactly once. |
| `replace_section` | Section-level — rewrite everything under a header | Find `section` header, replace all content until next same-level header (or end of document). |
| `replace_between` | Passage-level without headers — scenes in screenplays, sequences in prose | Find `start` anchor, find `end` anchor after it, replace everything between (inclusive). Both anchors must match exactly once. |

### Safety Rules

- `replace`: `old_text` must match exactly **once**. 0 matches = "not_found" (skip). 2+ matches = "ambiguous" (skip).
- `replace_section`: header must match exactly once. Content between this header and the next same-level header is replaced.
- `replace_between`: both `start` and `end` must match exactly once, and `start` must appear before `end`. Otherwise skip.
- Failed edits are logged with the reason. No retry loop — the quality gate handles it (unfixed issues get flagged again next round).

### When Each Round Type Applies

| Round | Agent behavior |
|---|---|
| `iteration == 0` (first round) | Write from scratch — full output as today |
| `iteration > 0` (revision round) | Output structured edits in revision JSON format |

## Per-Stage Structure Requirements

The Lead Writer's craft directives require structured sections so that `replace_section` has addressable targets. The structure format depends on the stage.

### Pitch (2-3 pages)

- **Structure:** Flowing prose, no mandatory sections
- **Available operations:** `replace` only (document is short enough)

### Expose (5-10 pages)

- **Structure:** Markdown sections for major narrative movements
- **Required headers:** At minimum: `## Premise`, `## Characters`, `## Story Arc`, `## Themes`
- **Available operations:** `replace`, `replace_section`

### Treatment (20-40+ pages, standalone)

- **Structure:** Markdown sections for major beats/sequences
- **Required headers:** Named sequences like `## The Opening`, `## The Inciting Incident`, `## The Midpoint Reversal`, `## The Climax`, etc.
- **Available operations:** `replace`, `replace_section`

### Concept / Series Bible (15-25 pages, series)

- **Structure:** Markdown sections for bible components
- **Required headers:** `## Story Engine`, `## Tone & Style`, `## World Rules`, `## Characters`, `## Saga Arc`, `## Season One`, `## Episode 1`, `## Episode 2`, ..., `## Future Seasons`
- **Available operations:** `replace`, `replace_section`

### First Draft — Screenplay

- **Structure:** Standard screenplay format (sluglines, action, dialogue). No markdown headers — uses native format.
- **Available operations:** `replace`, `replace_between` (targeting slugline + first action line as unique anchors)
- **Note:** Sluglines alone (e.g. `INT. BANK LOBBY - DAY`) may not be unique. The agent quotes slugline + opening action line for uniqueness.

### First Draft — Novel/Prose

- **Structure:** Chapters as markdown headers (`## Chapter 1: ...`)
- **Available operations:** `replace`, `replace_section`

### First Draft — Stage Play

- **Structure:** Acts and scenes as markdown headers (`## Act I, Scene 1`)
- **Available operations:** `replace`, `replace_section`

## Implementation: `_apply_revisions()`

New method on `WritersRoomLeaderBlueprint`:

```python
def _apply_revisions(self, document_content: str, revisions: list[dict]) -> tuple[str, list[dict]]:
    """Apply structured edits to a document.

    Returns (revised_content, failed_edits).
    Failed edits are skipped, not retried — the quality loop handles retry.
    """
    result = document_content
    failed = []

    for rev in revisions:
        rev_type = rev.get("type", "replace")

        if rev_type == "replace":
            old = rev.get("old_text", "")
            new = rev.get("new_text", "")
            count = result.count(old)
            if count == 1:
                result = result.replace(old, new, 1)
            elif count == 0:
                failed.append({"text": old[:80], "reason": "not_found"})
            else:
                failed.append({"text": old[:80], "reason": f"ambiguous ({count} matches)"})

        elif rev_type == "replace_section":
            header = rev.get("section", "")
            new_content = rev.get("new_content", "")
            # Find header, replace until next same-level header or EOF
            result, ok = self._replace_section(result, header, new_content)
            if not ok:
                failed.append({"text": header, "reason": "section_not_found"})

        elif rev_type == "replace_between":
            start = rev.get("start", "")
            end = rev.get("end", "")
            new_content = rev.get("new_content", "")
            result, ok = self._replace_between(result, start, end, new_content)
            if not ok:
                failed.append({"text": f"{start[:40]}...{end[:40]}", "reason": "anchors_not_found"})

    return result, failed
```

### Helper: `_replace_section()`

```python
@staticmethod
def _replace_section(content: str, header: str, new_content: str) -> tuple[str, bool]:
    """Replace content under a markdown header until the next same-level header."""
    if header not in content:
        return content, False

    # Determine header level (count leading #)
    level = len(header) - len(header.lstrip("#"))

    start_idx = content.index(header)
    after_header = start_idx + len(header)

    # Find next header of same or higher level
    lines = content[after_header:].split("\n")
    end_offset = len(content)  # default: to end of document
    current_pos = after_header
    for line in lines:
        current_pos += len(line) + 1  # +1 for newline
        stripped = line.lstrip()
        if stripped.startswith("#"):
            line_level = len(stripped) - len(stripped.lstrip("#"))
            if line_level <= level:
                end_offset = current_pos - len(line) - 1
                break

    result = content[:start_idx] + header + "\n\n" + new_content + "\n\n" + content[end_offset:]
    return result, True
```

### Helper: `_replace_between()`

```python
@staticmethod
def _replace_between(content: str, start: str, end: str, new_content: str) -> tuple[str, bool]:
    """Replace everything between two anchor texts (inclusive)."""
    if content.count(start) != 1 or content.count(end) != 1:
        return content, False

    start_idx = content.index(start)
    end_idx = content.index(end, start_idx)
    end_idx += len(end)

    if start_idx >= end_idx:
        return content, False

    result = content[:start_idx] + new_content + content[end_idx:]
    return result, True
```

## Integration with Existing Flow

### Where revision mode activates

In `_propose_lead_writer_task()` and `_propose_creative_tasks()`:
- Check `iterations` from `stage_status[current_stage]`
- If `iterations > 0`: add revision instructions to the `step_plan`, specifying available operations and referencing the existing document
- If `iterations == 0`: use current write-from-scratch instructions (no change)

### Where revisions are applied

In `_create_deliverable_and_research_docs()` and `_create_critique_doc()`:
- If `iterations > 0`: parse the agent's task report as JSON revision format
- Apply revisions to the existing (non-archived) document content using `_apply_revisions()`
- Log any failed edits
- Create new document version with the revised content
- Archive old version with `consolidated_into` link

If the task report is not valid JSON (agent wrote prose instead of revision format), fall back to treating it as a full replacement — same as iteration 0. This ensures the system never breaks even if the agent doesn't follow the revision format.

### For creative agents on revision rounds

Each creative agent's "previous output" is their section in the Research & Notes document. The revision instructions tell them:
- "Your previous output is in the Research & Notes document under your section header"
- "The Critique document lists what needs fixing"
- "Output revision JSON with edits to YOUR section only"
- "Preserve everything the critique praised"

### For the Lead Writer on revision rounds

- "The current deliverable is the Stage Deliverable document"
- "The Critique document lists what needs fixing"
- "Output revision JSON with edits to the deliverable"
- "Available operations for this stage: [replace, replace_section] (or [replace, replace_between] for screenplay)"
- "Untouched sections must remain BYTE-IDENTICAL"

## Error Handling

| Scenario | Behavior |
|---|---|
| Agent outputs valid revision JSON | Apply edits, log failures, create new document version |
| Agent outputs prose instead of JSON | Treat as full replacement (iteration 0 behavior) — logged as warning |
| Edit `old_text` not found | Skip edit, log "not_found" |
| Edit `old_text` ambiguous (2+ matches) | Skip edit, log "ambiguous" |
| Section header not found | Skip edit, log "section_not_found" |
| `replace_between` anchors not found or out of order | Skip edit, log "anchors_not_found" |
| All edits fail | Document unchanged, quality gate flags same issues next round |

## What Changes

| Change | File | Touches base? |
|---|---|---|
| `_apply_revisions()` + helpers | `leader/agent.py` | No |
| Revision instructions in `_propose_lead_writer_task()` | `leader/agent.py` | No |
| Revision instructions in `_propose_creative_tasks()` | `leader/agent.py` | No |
| Revision-aware document creation in `_create_deliverable_and_research_docs()` | `leader/agent.py` | No |
| Structure requirements added to `CRAFT_DIRECTIVES` | `lead_writer/agent.py` | No |
| Tests | `test_writers_room_lead_writer.py` | No |

**Base class: untouched.**

## What Does NOT Change

- Iteration 0 (first round) behavior — completely unchanged
- Quality gate scoring — untouched
- Document archive-and-link pattern — same mechanism, just applies revisions before creating new version
- State machine transitions — unchanged
- Feedback agent behavior — unchanged (they critique the deliverable regardless of how it was produced)

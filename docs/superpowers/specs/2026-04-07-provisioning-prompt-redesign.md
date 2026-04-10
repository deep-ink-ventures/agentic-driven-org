# Provisioning Prompt Redesign

## Problem

Agent provisioning generates per-agent "instructions" that are prepended to every task. The current prompt asks Claude to write role descriptions ("define what this agent owns and delivers", "set the quality bar") which duplicates what the system prompt already provides. The result is generic job descriptions instead of useful project context.

Additionally, the system prompt was truncated to 2000 chars for long-prompt agents (authenticity analyst, dialogue analyst), causing empty or broken instructions. Agents were set to ACTIVE with empty instructions.

## Design

### What changes

**File:** `projects/tasks.py`, function `provision_single_agent`

**System prompt** changes to: project briefing writer that focuses on what the agent needs to know about THIS project, not the agent's role.

**User message "Your Task" section** changes to:

- Write a project briefing (1-2 substantial paragraphs, not 3-5)
- Tell the agent what it needs to know about THIS project — characters, setting, conflicts, tone, moral register, pitfalls
- Focus on aspects most relevant to this agent type's craft
- Written in the project locale
- Explicitly: do NOT describe the agent's role, responsibilities, or quality bar — the system prompt handles that

**Examples** update:

- Bad: "Du recherchierst marktrelevante Grundlagen fur die Serie."
- Good: "Das Projekt ist eine 8-teilige Prestige-Serie uber drei Bruder, die nach ihrem Tech-IPO in den Berliner Immobilienmarkt einsteigen. Der moralische Register ist zynisch — alle Figuren handeln egoistisch, keine wird rehabilitiert. Der zentrale Mechanismus ist burokratische Ermessensmacht ohne Gesetzesbruch. Dein Fokus: Bad Banks (ZDF/Arte) als direkter Marktbeweis fur den unbesetzten Slot, Succession und Industry als tonale Comps, die sofort qualifiziert werden mussen."

### What doesn't change

- Architecture: per-agent Celery task, `call_claude`, `parse_json_response`
- JSON schema: `{"instructions": "...", "name": "..."}`
- Full system prompt passed as context (truncation already removed)
- Empty-instructions guard already in place (raises ValueError, triggers retry)

### Already applied (earlier in this session)

1. Truncation removed — full system prompt passed to provisioning call
2. Empty-instructions guard — agent not set ACTIVE if instructions are empty, raises ValueError to trigger retry

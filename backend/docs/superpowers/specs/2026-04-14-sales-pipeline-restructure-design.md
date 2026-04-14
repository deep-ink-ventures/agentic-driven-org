# Sales Pipeline Restructure — Multiplier-First Architecture

**Date:** 2026-04-14
**Status:** Approved
**Problem:** The sales pipeline is built backwards. It starts with abstract market analysis (28K researcher report) and elaborate strategy frameworks (32K strategist output), then dumps prospect discovery AND copywriting onto the personalizer. Result: 25 total prospects found instead of 250, half questionable, massive token waste, and output that conflates individual customer outreach with B2B partnership development.

## Core Design Principle

**Sales targets multiplier gatekeepers — organizations and individuals who control many bookings. Marketing targets individual customers.** This distinction is architectural, not just a prompt hint. Every pipeline step enforces it.

### Multiplier Tiers
- **Tier 1 — Organizations:** Accelerators, VC firms, corporate relocation services, conference organizers. One deal = 10-50+ recurring bookings.
- **Tier 2 — Influential Individuals:** Community leaders, event organizers, newsletter writers. One relationship = steady referral stream.

## Pipeline

Old: `research → strategy → personalization(×N) → finalize → qa_review → dispatch`
New: `ideation → discovery(×N) → prospect_gate → copywriting(×N) → copy_gate → qa_review → dispatch`

| Step | Agent | Command | Fan-out? | Model | Purpose |
|---|---|---|---|---|---|
| `ideation` | strategist | `identify-targets` | No | sonnet | Propose multiplier target areas with tier structure |
| `discovery` | researcher | `discover-prospects` | Yes, 1 clone per area | sonnet | Web-search for real decision-makers at multiplier orgs |
| `prospect_gate` | authenticity_analyst | `verify-prospects` | No | sonnet | Independent verification that prospects are real |
| `copywriting` | pitch_personalizer | `write-pitches` | Yes, 1 clone per area | sonnet | B2B partnership copywriting from verified prospect data |
| `copy_gate` | authenticity_analyst | `verify-pitches` | No | sonnet | Verify pitches don't fabricate claims |
| `qa_review` | sales_qa | `review-pipeline` | No | sonnet | Quality + strategy review |
| `dispatch` | (special handling) | `send-outreach` | No | sonnet | Send approved outreach |

### Context Flow Between Steps

```python
STEP_CONTEXT_SOURCES = {
    "ideation":       [],
    "discovery":      ["ideation"],
    "prospect_gate":  ["discovery"],
    "copywriting":    ["ideation", "discovery", "prospect_gate"],
    "copy_gate":      ["copywriting"],
    "qa_review":      ["ideation", "prospect_gate", "copywriting", "copy_gate"],
    "dispatch":       ["copywriting"],
}
```

## Strategist — `identify-targets`

Reads sprint goal + project context. Produces 3-5 multiplier target areas, ~300-500 words each, ~3K total.

Output format per area:
```
### Target Area [N]: [Name]
**Tier:** 1 or 2
**Scope:** Who exactly — org type, role type, geography
**Why multiplier:** How one conversion yields many bookings (estimated multiplier: Nx)
**Decision-maker profile:** Who at these orgs controls the decision (title, function)
**Messaging angle:** 2-3 sentences — the core "why should they care" hook
**Timing signal:** What's happening NOW that creates urgency (or "evergreen" if none)
```

Replaces: `draft-strategy` (32K AIDA frameworks).
Delete: `draft-strategy`, `revise-strategy`, `finalize-outreach` commands. System prompt rewritten for multiplier ideation. Skills list updated: remove "AIDA Narrative Design", "Pipeline Consolidation"; keep "Target Segmentation", "Competitive Positioning", "Opportunity Scoring".

## Researcher — `discover-prospects`

Each clone receives one target area brief. Uses web search to find real decision-makers. No market analysis, no competitive landscape, no prose.

Output format per prospect:
```
## Prospect [N]: [Full Name] — [Organization]
**Role:** [Verified current title]
**Organization:** [Name + what they do]
**Multiplier potential:** [Why this person/org can send multiple bookings]
**Verification:** [Search term used + source that confirms identity/role]
**Contact:** [Verified email, LinkedIn URL, or "not found"]
**Hook opportunity:** [1-2 sentences connecting them to our offer]
```

Target: 10 verified prospects per area. Zero fabrication — every prospect cites the search result. Fewer than 10 is acceptable; padding is not.

Replaces: `research-industry` (28K market overview).
Delete: `research-industry` command. System prompt rewritten for prospect discovery. Skills list updated: replace "Market Intelligence" with "Prospect Discovery"; keep "Company Profiling", "Qualification Analysis".

## Authenticity Gates

Same agent (`authenticity_analyst`), two new commands.

### `verify-prospects` (prospect_gate)
Runs once after all researcher clones complete. Reads all clone outputs.
- For each prospect: does the cited source support the claimed identity/role?
- Flags vague verification ("LinkedIn search" vs specific URL)
- Flags potentially outdated prospects (left role, org shut down)
- Output: pass/fail per prospect with reasoning
- Does NOT re-search — audits citations only

After this gate, the leader **strips failed prospects** from the data flowing to the personalizer. Personalizer only receives verified prospects.

### `verify-pitches` (copy_gate)
Runs once after all personalizer clones complete. Reads all clone outputs.
- For each pitch: does it reference claims not in the verified prospect data?
- Flags invented social media posts, conference talks, quotes
- Flags misattributed roles or orgs
- Output: pass/fail per pitch with specific issues

## Pitch Personalizer — `write-pitches`

Pure B2B copywriting. Receives pre-verified prospects + target area brief. No web search.

Input per clone: target area brief (~400 words) + verified prospect list + sprint instruction.

Output format per prospect:
```
## Pitch for [Full Name] — [Organization]
**Channel:** email / linkedin
**Subject:** [Specific to this person]

### Body
[80-150 words. B2B partnership tone. Frames deal as multiplier opportunity.]

### Follow-ups
**Day 3:** [New angle, 40-80 words]
**Day 7:** [Direct question, 40-80 words]

### Closer Briefing
[2-3 sentences for the human taking the call]
```

Changes: `uses_web_search = False`. Remove "Person Discovery" and "Prospect Research" skills. Keep "Storyline Adaptation" and "Channel Selection". Rename command from `personalize-pitches` to `write-pitches`.

## Leader Orchestration

### New Constants
```python
DEFAULT_PROSPECTS_PER_AREA = 10

PIPELINE_STEPS = [
    "ideation",
    "discovery",
    "prospect_gate",
    "copywriting",
    "copy_gate",
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "ideation": "strategist",
    "discovery": "researcher",
    "prospect_gate": "authenticity_analyst",
    "copywriting": "pitch_personalizer",
    "copy_gate": "authenticity_analyst",
    "qa_review": "sales_qa",
    "dispatch": None,
}

STEP_TO_COMMAND = {
    "ideation": "identify-targets",
    "discovery": "discover-prospects",
    "prospect_gate": "verify-prospects",
    "copywriting": "write-pitches",
    "copy_gate": "verify-pitches",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}
```

### Fan-out Handling
Both `discovery` and `copywriting` are fan-out steps. Generalize the current `_handle_personalization_step` / `_create_clones_and_dispatch` pattern into a reusable fan-out handler that:
1. Parses target areas from the preceding step's output
2. Creates clones of the appropriate agent type
3. Dispatches one task per clone with the area-specific context
4. Waits for all clones to complete before advancing

### Gate Handling
`prospect_gate` and `copy_gate` are linear steps with special context injection: they receive ALL clone outputs from the preceding fan-out step (same as how `finalize` currently gathers clone outputs). After `prospect_gate`, the leader parses the pass/fail output and builds a filtered prospect list (only passed prospects) which is injected into each `copywriting` clone's step_plan context. The filtering is done in the leader's `_build_step_context` method — no new storage mechanism needed.

### Existing Sprint Compatibility
Sprints mid-pipeline with old step names (`research`, `strategy`, `personalization`, `finalize`) will not be recognized by the new pipeline constants. Any in-progress sales sprints must complete or be reset before deploying this change.

### Delete
- `_handle_personalization_step` — replaced by generalized fan-out handler
- `_create_clones_and_dispatch` — replaced by generalized version
- `finalize` step and all handling
- `DIMENSION_TO_AGENT` (QA cascade routing)
- `AGENT_FIX_COMMANDS`
- `CHAIN_ORDER`

## Files Changed

1. `backend/agents/blueprints/sales/leader/agent.py` — pipeline constants, handlers, context flow, fan-out generalization
2. `backend/agents/blueprints/sales/workforce/researcher/agent.py` — new system prompt, skills
3. `backend/agents/blueprints/sales/workforce/researcher/commands/` — delete `research_industry.py`, add `discover_prospects.py`
4. `backend/agents/blueprints/sales/workforce/strategist/agent.py` — new system prompt, skills
5. `backend/agents/blueprints/sales/workforce/strategist/commands/` — delete `draft_strategy.py`, `revise_strategy.py`, `finalize_outreach.py`; add `identify_targets.py`
6. `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py` — new system prompt, skills, `uses_web_search = False`
7. `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/` — delete `personalize_pitches.py`, `revise_pitches.py`; add `write_pitches.py`
8. `backend/agents/blueprints/sales/workforce/authenticity_analyst/agent.py` — add `verify-prospects`, `verify-pitches` commands
9. `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/` — add `verify_prospects.py`, `verify_pitches.py`
10. `backend/agents/blueprints/sales/workforce/sales_qa/` — prompt update for multiplier pipeline review

## Cost Estimate

All steps on sonnet ($3/$15 per M tokens).
- Old pipeline: ~$15-25 per sprint (opus strategy + 5 personalizer clones doing discovery + copywriting)
- New pipeline: ~$3-6 per sprint (all sonnet, cleaner handoffs, less redundant context)

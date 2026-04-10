# Sales Pipeline Redesign — Fan-Out Personalizers + Strategist Consolidation

**Date:** 2026-04-10
**Status:** Draft

## Summary

Redesign the sales department pipeline to fan out personalization work across N cloned agents (one per target area), merge the strategist and pitch_architect into a single agent, merge profile_selector into pitch_personalizer, and add a strategist consolidation step that produces a machine-readable CSV for dispatch.

## New Pipeline

```
1. researcher              → research-industry
2. strategist              → draft-strategy  (thesis + target areas + narrative arcs)
3. N × cloned personalizers → personalize-pitches  (parallel, one per target area)
   [batch loop: re-invoke clones below target profile count]
   [join: wait for all N to hit target]
4. strategist              → finalize-outreach  (exec summary + CSV)
5. sales_qa + authenticity_analyst → review-pipeline  (parallel)
   [QA loop: fail → researcher or strategist → re-run from there]
6. leader filters CSV      → N × outreach agents → send-outreach  (parallel)
   [join: wait for all → sprint DONE, destroy clones]
```

**Agents removed:** pitch_architect (merged into strategist), profile_selector (merged into pitch_personalizer).

**Workforce after redesign:** researcher, strategist, pitch_personalizer, sales_qa, authenticity_analyst, email_outreach (6 agents + leader, down from 8 + leader).

## ClonedAgent Model

New model — not a subclass of Agent. Lightweight proxy that inherits everything from its parent except state.

```
ClonedAgent
  parent          FK → Agent            # blueprint, instructions, config come from here
  sprint          FK → Sprint           # scoped to this sprint's lifetime
  clone_index     IntegerField          # 0, 1, 2... for identification
  internal_state  JSONField, default={}  # own working state
  created_at      DateTimeField, auto
```

### AgentTask Change

New nullable FK on AgentTask:

```
cloned_agent    FK → ClonedAgent, null=True, blank=True
```

When `cloned_agent` is set, task execution uses `cloned_agent.parent.get_blueprint()` for blueprint resolution and `cloned_agent.internal_state` for state. Existing tasks with `cloned_agent=None` are unaffected.

### Lifecycle

- **Created** by leader when fan-out step begins (after strategist completes draft-strategy).
- **Destroyed** on sprint completion — same cleanup step where pipeline state is cleared.
- Clones do not survive across sprints.

### Base Class Helpers (LeaderBlueprint)

```python
create_clones(parent_agent: Agent, count: int, sprint: Sprint) -> list[ClonedAgent]
destroy_sprint_clones(sprint: Sprint) -> None  # bulk delete
```

Available to any leader blueprint (sales, writers room, future departments).

## Strategist Redesign

Absorbs pitch_architect. Three commands:

### `draft-strategy`

- **Input:** researcher output + available outreach channels (leader injects list of `outreach=True` agent types)
- **Output:** thesis, 3-5 target areas each containing:
  - Target area name and rationale
  - Narrative arc (AIDA structure, absorbed from pitch_architect)
  - Anti-spam guidance
- **Constraint:** target areas must be in a parseable structure (numbered sections or JSON block) so the leader can count them and slice per clone.

### `finalize-outreach`

- **Input:** all N clone outputs (one report per target area)
- **Produces two outputs:**
  1. **Exec Summary** — max 1 page. What this is about, why it is the right approach, whom we target with what. No chat, no filler, no lengthy explanation.
  2. **CSV** — machine-readable, columns:
     - `channel`: outreach agent identifier (e.g., `email`)
     - `identifier`: email address, Reddit username, Twitter handle, phone, etc.
     - `subject`: subject line or headline
     - `content`: the outreach message
- Both persisted as Output objects with labels `exec-summary` (MARKDOWN) and `outreach-csv` (PLAINTEXT).

### `revise-strategy`

- **Input:** QA report with failure details
- **Decides:** revise strategy/storyline, or re-invoke specific personalizer clones with targeted QA feedback
- Leader re-enters the pipeline from wherever the strategist directs

## Pitch Personalizer Redesign

Absorbs profile_selector. Two commands:

### `personalize-pitches`

- **Input:** one target area slice from the strategist (rationale, narrative arc, anti-spam guidance) + researcher output
- **Job:** find concrete people via web search for this target area, then personalize the storyline per person
- **Output per person:** name, identifier, channel assignment, subject line, pitch content, personalization notes
- **Constraint:** output must be structured so strategist's finalize-outreach can aggregate across all clones

### `revise-pitches`

- **Input:** QA feedback routed through strategist
- **Job:** revise specific pitches or find replacement profiles

### Clone Behavior

Each clone receives only its assigned target area, not the full list. The leader slices the strategist's draft-strategy output and briefs each clone with its slice + the full researcher output.

## QA Cascade & Fix Routing

### Dimension Mapping

| Dimension | Routes to |
|---|---|
| research_accuracy | researcher |
| strategy_quality | strategist |
| storyline_effectiveness | strategist |
| profile_accuracy | strategist |
| pitch_personalization | strategist |

Everything below researcher routes to strategist. The cascade chain simplifies from 5 agents to 2: `["researcher", "strategist"]`.

### Fix Flow

1. QA flags issues → leader routes to earliest failing agent in chain (researcher or strategist)
2. If researcher: researcher re-runs research-industry, pipeline continues from there
3. If strategist: leader dispatches `revise-strategy` to strategist with QA report. The strategist's Claude call decides what to fix (it has full context from finalize-outreach). Its report indicates the action taken:
   - Revised strategy/storyline itself → leader re-runs clones → finalize-outreach → QA again
   - Targeted feedback for specific areas → leader re-runs affected clones → finalize-outreach → QA again
4. Leader handles clone re-creation for re-runs (destroy old clones, create fresh ones)
5. Thresholds unchanged: 9.5 auto-accept, 9.0 after 3 polish rounds, max 5 review rounds

## Dispatch

Leader parses the CSV from finalize-outreach. Groups rows by `channel` column. For each unique channel, dispatches a task to the matching outreach agent with only that agent's rows.

**Task payload per outreach agent:**
- Filtered CSV slice (rows where `channel` matches this agent's type)
- Exec summary for context
- Command: `send-outreach`

**Channel mismatch is a bug, not an edge case.** The strategist knows available channels (injected by leader at draft-strategy). Personalizers assign from that list. QA validates before dispatch. If a channel has no matching agent at dispatch time, raise a hard error.

**Sprint completion:** when all outreach tasks DONE → leader writes Outputs, marks sprint DONE, destroys clones.

## Context Injection (Updated)

Which prior steps feed into each step:

| Step | Receives output from |
|---|---|
| research | (sprint instruction only) |
| strategy | research |
| personalization (clones) | research + one target area slice from strategy |
| finalize-outreach | all clone outputs |
| qa_review | research, strategy, finalize-outreach (exec summary + CSV) |
| dispatch | finalize-outreach CSV (filtered) |

## Pipeline Constants (Updated)

```python
PIPELINE_STEPS = [
    "research",
    "strategy",
    "personalization",   # fan-out step
    "finalize",          # strategist consolidation
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "research": "researcher",
    "strategy": "strategist",
    "personalization": "pitch_personalizer",  # clones
    "finalize": "strategist",
    "qa_review": "sales_qa",
    "dispatch": None,  # outreach agents
}

STEP_TO_COMMAND = {
    "research": "research-industry",
    "strategy": "draft-strategy",
    "personalization": "personalize-pitches",
    "finalize": "finalize-outreach",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}

DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "strategist",
    "profile_accuracy": "strategist",
    "pitch_personalization": "strategist",
}

CHAIN_ORDER = ["researcher", "strategist"]
```

## Scaling to 1000+ Outreaches

Target: ~1000 outreach messages per sprint. A single Claude call can comfortably find and personalize 20-50 profiles. The pipeline scales through two mechanisms working together.

### More Target Areas

The strategist is not limited to 3-5 target areas. For high-volume sprints, the strategist should produce 10-20 narrower target areas (e.g., "fintech CFOs in DACH" rather than "fintech executives"). More areas → more clones → more parallelism. The leader creates one clone per area regardless of count.

### Batching Within Clones

Each clone has a **target profile count** set by the leader (derived from sprint instruction or a default). The clone's `personalize-pitches` command produces a batch of profiles. The leader checks the clone's cumulative output count:

- If below target → re-invoke the clone with `personalize-pitches` again, passing its prior output so it doesn't duplicate profiles
- If at or above target → mark clone as done

This gives an inner loop per clone:

```
Clone created (target: 50 profiles)
  → personalize-pitches (batch 1: 25 profiles found)
  → personalize-pitches (batch 2: 30 more profiles, cumulative 55) ✓ done
```

### Numbers Example

Sprint targets 1000 outreaches:
- Strategist produces 20 target areas → 20 clones
- Each clone targets 50 profiles, averaging 2-3 batches
- All clones run in parallel
- Strategist consolidates 1000 rows into CSV

### Leader Orchestration for Batching

The fan-out step becomes a fan-out + batch loop:

1. Leader creates N clones with `target_count` stored in each clone's `internal_state`
2. Leader dispatches `personalize-pitches` to all clones in parallel
3. On each poll: for each clone, check cumulative profile count in completed task reports
4. If clone below target and hasn't errored → dispatch another `personalize-pitches` batch
5. If all clones at target → advance to finalize-outreach

### Default Target

If the sprint instruction doesn't specify a volume, default to 50 profiles per target area. The strategist's target area count (5-20) then determines total volume (250-1000).

## What This Doesn't Touch

- **Writers room** — no changes. Shared clone infrastructure is available but not used yet.
- **Review loop mechanics in base.py** — thresholds, polish counts, max rounds unchanged. Only the sales leader's `_propose_fix_task` and dimension mapping change.
- **Agent provisioning** — existing agents are provisioned as before via Claude. Clones skip provisioning entirely (FK to parent).
- **Frontend** — cloned agents are ephemeral backend-only. No UI changes required for this spec.

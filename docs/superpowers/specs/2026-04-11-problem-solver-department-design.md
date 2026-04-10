# Problem Solver Department — Design Spec

**Date:** 2026-04-11
**Status:** Draft

## Overview

A department that takes a stated problem and finds solutions through first-principles decomposition, cross-domain ideation, parallel hypothesis testing, and validated proof-of-concept synthesis. Heavy bias toward mathematical modelling, statistical pattern establishment, and computational solutions.

The pipeline is iterative: if ideation is weak, the department explores new fields rather than polishing a bad idea. Up to 10 rounds before giving up.

## Department Registration

- **Slug:** `problem_solver`
- **Name:** Problem Solver
- **Description:** First-principles problem decomposition, cross-domain ideation, parallel hypothesis testing, and validated proof-of-concept synthesis — biased toward mathematical modelling, statistical patterns, and computational solutions.

### Config Schema

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `github_playground_repo` | str | Yes | Full URL of the playground repo for PoC execution, e.g. `https://github.com/org/playground` |
| `github_token` | str | Yes | PAT with repo + workflow permissions for the playground repo |

The `github_token` can cascade from project-level config if the Engineering department already set one.

## Agent Roster

Five agent types plus the leader:

| Agent | Type Slug | Role | Essential |
|-------|-----------|------|-----------|
| First Principle Thinker | `leader` | Decomposes problem, defines definition of done, rejects invalid problems, orchestrates pipeline | Yes (leader) |
| Out-of-Box Thinker | `out_of_box_thinker` | Proposes 5 cross-domain fields via bisociation methodology | Yes |
| Playground | `playground` | Explores one assigned field, produces hypothesis + pseudocode sketch, scores 1-10 | Yes |
| Synthesizer | `synthesizer` | Builds PoC against DoD for high-scoring hypotheses (8+), executes via GitHub Actions | Yes |
| Reviewer | `reviewer` | Independent quality gate, scores Synthesizer output against DoD | Yes |

## Commands

| Agent | Command | Description |
|-------|---------|-------------|
| FPT (leader) | `decompose_problem` | Break problem into actors/dynamics/variants, define DoD, or reject as invalid |
| Out-of-Box Thinker | `propose_fields` | Propose 5 cross-domain fields via bisociation methodology |
| Playground | `explore_field` | Explore assigned field, produce hypothesis + pseudocode sketch, score 1-10 |
| Synthesizer | `build_poc` | Build PoC, push to playground repo, trigger GitHub Action, validate against DoD |
| Synthesizer | `fix_poc` | Revise PoC based on reviewer feedback |
| Reviewer | `review_solution` | Score Synthesizer output against DoD, independent quality gate |

## Pipeline Flow

### Per-Round Execution

```
Round N:
  FPT (leader)
    Round 1: decompose problem -> actors, dynamics, DoD
    Round 2+: feed back previous round results + reviewer notes
    Invalid problem? -> end sprint immediately
        |
        v
  Out-of-Box Thinker
    Receives: decomposition + DoD + previous round feedback
    Produces 5 fields:
      2 same-domain (e.g. two math subfields)
      2 associated-domain (e.g. chemistry + biology)
      1 random-associative (e.g. wine presses for printing)
    Round 2+: must propose NEW fields, not repeat prior rounds
        |
        | 5 parallel tasks
        v
  Playground x5 (parallel, one per field)
    Each receives one field + the problem decomposition + DoD
    Produces: hypothesis + pseudocode sketch
    Self-scores 1-10
        |
        | scores 8+ only
        v
  Synthesizer (one per 8+ hypothesis)
    Pushes PoC code to playground repo
    Triggers GitHub Action via dispatch_workflow
    Reads back results, validates against DoD
    Max 5 no-progress tries or 10 total tries
    Self-scores 1-10
        |
        v
  Reviewer (independent)
    Scores each Synthesizer output against DoD
    Uses standard quality gate:
      Score < 9.0 -> loop (new round, Out-of-Box gets feedback)
      Score >= 9.0, polish < 3 -> loop for polish
      Score >= 9.5 OR polish >= 3 at 9.0+ -> ACCEPT
        |
        v
  Output document written
  Max 10 rounds total
```

### Round Iteration Logic

The iteration wraps the entire department output, not just the Synthesizer:

- If no Playground result hits 8+, the round produced no Synthesizer work. The Out-of-Box Thinker gets feedback on what didn't work and proposes 5 new fields next round.
- If Playground results hit 8+ but the Synthesizer/Reviewer cycle doesn't reach acceptance, the feedback flows back to the Out-of-Box Thinker for new field proposals.
- Dead-end rounds are not wasted — they eliminate territory and inform the next Out-of-Box proposal.

### Termination Conditions

1. **Solved:** Reviewer accepts a Synthesizer output (score >= 9.5 or 9.0+ after 3 polish rounds). Sprint marked done with solution output.
2. **Invalid problem:** FPT determines no falsifiable DoD is possible. Sprint marked done with rejection output.
3. **Exhausted:** 10 rounds completed without acceptance. Sprint marked done with best-attempt output.

## Legitimacy Gate

The Reviewer must reject any solution that is not genuinely innovative. Specifically, the following are illegitimate approaches and must score 0 on `dod_validation`:

- **Brute force / random search** — randomly trying combinations until one works is not a solution, it's a lottery
- **Hardcoded results** — embedding the expected answer in the code and "discovering" it is fraud
- **Trivial lookup** — if the answer is already publicly known and the PoC just retrieves it, no insight was generated
- **Overfitting to the DoD** — engineering the PoC to pass the specific DoD checks without the underlying approach actually working in general

A legitimate solution must demonstrate a **causal chain of insight**: the cross-domain field provided a structural analogy or principle that, when applied to the problem, produces the result for an identifiable reason. The Reviewer must be able to articulate *why* the approach works, not just *that* it passes.

This gate applies before any scoring. If the Reviewer determines the approach is illegitimate, the verdict is `CHANGES_REQUESTED` with score 0 and feedback explaining why the approach doesn't qualify.

## Review Pair Declaration

```python
def get_review_pairs(self):
    return [{
        "creator": "synthesizer",
        "creator_fix_command": "fix_poc",
        "reviewer": "reviewer",
        "reviewer_command": "review_solution",
        "dimensions": [
            "legitimacy",          # Is this a genuine insight, not brute force/hardcoded/trivial? (0 = instant reject)
            "dod_validation",      # Does the PoC actually meet the definition of done?
            "mathematical_rigor",  # Is the approach mathematically sound?
            "reproducibility",     # Can the result be reproduced independently?
            "insight_novelty",     # How novel is the cross-domain insight?
        ],
    }]
```

The standard `_check_review_trigger` / `_evaluate_review_and_loop` base class methods handle the Reviewer <-> Synthesizer ping-pong. The EXCELLENCE_THRESHOLD (9.5), NEAR_EXCELLENCE_THRESHOLD (9.0), and MAX_POLISH_ATTEMPTS (3) constants from `base.py` apply.

## Leader State Management

The FPT leader tracks round progression in `sprint.department_state`:

```python
{
    "round": 3,
    "max_rounds": 10,
    "decomposition": {
        "actors": ["..."],
        "dynamics": ["..."],
        "definition_of_done": "...",
        "math_bias": "..."
    },
    "round_history": [
        {
            "round": 1,
            "fields_proposed": ["topology", "fluid_dynamics", "..."],
            "playground_scores": {"topology": 4, "fluid_dynamics": 8, "...": "..."},
            "synthesizer_invoked_for": ["fluid_dynamics"],
            "reviewer_score": 7.5,
            "feedback": "..."
        }
    ],
    "status": "running"  # or "solved", "invalid_problem", "exhausted"
}
```

This history feeds back into the Out-of-Box Thinker each round so it does not repeat fields and learns from what scored well or poorly.

## Problem Rejection

If the FPT determines the problem has no clear, falsifiable definition of done (e.g. "solve climate change"), it:

1. Sets `status: "invalid_problem"` in department_state
2. Writes an Output with label `"rejection"` explaining why — what's missing, what would make it solvable
3. Marks the sprint as done with a completion summary

This is a first-class outcome, not a failure. The FPT's job is to filter unsolvable problems before burning compute on ideation.

## Output Documents

Each round that produces a Synthesizer result writes an Output with label `"solution_round_N"` and `output_type: MARKDOWN`.

The final accepted output gets label `"solution"` and contains:

1. **Executive summary** — the approach in 2-3 sentences
2. **Approach explanation** — paragraphs making the cross-domain insight understandable
3. **PoC results** — what was tried against the DoD, with actual results from GitHub Actions

## GitHub Actions Sandbox

The Synthesizer uses the existing `integrations.github_dev.service` module:

1. **Parse repo:** Extract `org/name` from the full URL (e.g. `https://github.com/org/playground` -> `org/playground`)
2. **Push code:** Create/update files in the playground repo via GitHub API (contents endpoint)
3. **Trigger workflow:** `dispatch_workflow(token, "org/playground", "poc.yml", inputs={"problem_id": "...", "round": "N"})`
4. **Read results:** Poll workflow run status, fetch artifacts/logs for validation

The playground repo must have a `poc.yml` workflow that:
- Accepts `problem_id` and `round` as inputs
- Sets up the execution environment (Python, Node, etc. as needed)
- Runs the pushed PoC code
- Uploads results as workflow artifacts

The Synthesizer parses the artifacts to validate against the DoD.

## Agent System Prompts

### First Principle Thinker (Leader)

Core persona: Rigorous analytical thinker with heavy bias toward mathematical and computational solutions. Follows Aristotelian first-principles methodology — decompose to irreducible truths, discard conventions, reconstruct from fundamentals.

Key behaviors:
- List all assumptions about the problem explicitly
- Challenge each: physical law, mathematical truth, convention, or unknown?
- Discard conventions, keep only laws and verified data
- Define a falsifiable, measurable definition of done
- Reject problems that cannot have a clear DoD

### Out-of-Box Thinker

Core persona: Cross-domain innovator using bisociation (Koestler), lateral thinking (de Bono), and analogical reasoning across fields.

Key behaviors:
- Mandatory cross-domain search before proposing
- Forced bisociation — combine frames that don't normally intersect
- Provocation step — generate one deliberately absurd inversion, mine it for real insight
- Categorize proposals: 2 same-domain, 2 associated-domain, 1 random-associative
- Never repeat fields from prior rounds (receives round_history)

### Playground

Core persona: Hypothesis explorer. Takes one assigned field and the problem decomposition, finds applications from that field that could generate insight.

Key behaviors:
- Study the assigned field's core principles
- Map structural similarities to the problem
- Produce a clear hypothesis: "Here's how [concept from field X] maps onto the problem"
- Produce a pseudocode sketch of how the approach would work algorithmically
- Score honestly on 1-10 scale (1: dead end, 5: interesting but probably nothing, 10: one-in-a-generation insight)

### Synthesizer

Core persona: Builder. Takes a high-scoring hypothesis + pseudocode sketch and turns it into working code that validates against the DoD.

Key behaviors:
- Translate pseudocode into executable code
- Push to playground repo, trigger GitHub Action
- Parse results, compare to DoD criteria
- Iterate up to 5 no-progress tries or 10 total
- Self-score 1-10 (1: failed, 10: perfectly solved the DoD)

### Reviewer

Core persona: Independent evaluator. Scores Synthesizer output against the DoD without anchoring on the Synthesizer's self-score.

Key behaviors:
- First check legitimacy: is this brute force, hardcoded, trivial lookup, or overfitted? If yes, score 0 and reject immediately
- Require a causal chain of insight: the reviewer must be able to articulate *why* the approach works, not just *that* it passes
- Score each dimension independently: legitimacy, dod_validation, mathematical_rigor, reproducibility, insight_novelty
- Overall score = minimum of all dimensions (legitimacy = 0 means overall = 0)
- Provide actionable feedback for what would improve the score
- Call submit_verdict tool with verdict and score

## Folder Structure

```
backend/agents/blueprints/problem_solver/
  __init__.py
  leader/
    __init__.py
    agent.py              # ProblemSolverLeaderBlueprint
  workforce/
    out_of_box_thinker/
      __init__.py
      agent.py            # OutOfBoxThinkerBlueprint
    playground/
      __init__.py
      agent.py            # PlaygroundBlueprint
    synthesizer/
      __init__.py
      agent.py            # SynthesizerBlueprint
    reviewer/
      __init__.py
      agent.py            # ReviewerBlueprint
```

## Registration in `__init__.py`

Follows the lazy-import pattern used by Engineering, Writers Room, Sales, and Community:

```python
try:
    from agents.blueprints.problem_solver.leader import ProblemSolverLeaderBlueprint
except ImportError:
    ProblemSolverLeaderBlueprint = None

_problem_solver_workforce = {}
_problem_solver_imports = {
    "out_of_box_thinker": ("agents.blueprints.problem_solver.workforce.out_of_box_thinker", "OutOfBoxThinkerBlueprint"),
    "playground": ("agents.blueprints.problem_solver.workforce.playground", "PlaygroundBlueprint"),
    "synthesizer": ("agents.blueprints.problem_solver.workforce.synthesizer", "SynthesizerBlueprint"),
    "reviewer": ("agents.blueprints.problem_solver.workforce.reviewer", "ReviewerBlueprint"),
}
# ... standard lazy import loop ...

if ProblemSolverLeaderBlueprint is not None:
    _problem_solver_leader = ProblemSolverLeaderBlueprint()
    DEPARTMENTS["problem_solver"] = {
        "name": "Problem Solver",
        "description": "First-principles problem decomposition, cross-domain ideation, parallel hypothesis testing, and validated proof-of-concept synthesis",
        "leader": _problem_solver_leader,
        "workforce": _problem_solver_workforce,
        "config_schema": _problem_solver_leader.config_schema,
    }
```

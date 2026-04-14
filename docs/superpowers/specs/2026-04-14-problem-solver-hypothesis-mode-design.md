# Problem Solver — Hypothesis Mode Design Spec

**Date:** 2026-04-14
**Status:** Draft
**Extends:** `2026-04-11-problem-solver-department-design.md`

## Overview

Generalize the Problem Solver department to handle hypotheses alongside problems. The pipeline architecture (decompose → ideate → explore → synthesize → review) is unchanged. The generalization is in language, framing, and agent behavior — driven by a `mode` flag that the First Principle Thinker sets during intake classification.

A hypothesis like "I think there are correlations between tweets and Bitcoin price" should work — including vague ones where the agent must figure out which domains to look at, who the relevant actors are, what data sources exist, and how to test the claim rigorously.

## Design Approach

**Dual-mode First Principle Thinker.** The leader detects whether the input is a problem or a hypothesis and switches behavior. Problem mode is completely unchanged. Hypothesis mode adapts the pipeline at every stage. The mode is persisted in `dept_state["mode"]` and all downstream agents receive it as context.

## Mode Detection

The First Principle Thinker keeps the single `decompose-problem` command. Its system prompt adds: "First, determine if this is a problem to solve or a hypothesis to test." The LLM classifies based on the input and returns `"mode": "problem"` or `"mode": "hypothesis"` in its JSON response. No heuristic regex — the LLM handles ambiguity.

- "Optimize routing in a network" → problem mode → existing behavior
- "I think tweets correlate with Bitcoin price" → hypothesis mode → new behavior
- "Can social media sentiment predict stock movements?" → hypothesis mode

## Hypothesis Refinement

In hypothesis mode, the First Principle Thinker's decomposition output changes structure. Instead of `actors / dynamics / variants / definition_of_done`, it produces:

```python
{
    "mode": "hypothesis",
    "original_claim": "I think there are correlations between tweets and bitcoin",
    "sub_hypotheses": [
        {
            "id": "H1",
            "claim": "Tweets from accounts with >10M followers mentioning Bitcoin correlate with >2% price movement within 4 hours",
            "testable_prediction": "Statistically significant abnormal returns in a 4h window following qualifying tweets",
            "null_hypothesis": "Tweet timing and Bitcoin price movements are independent",
            "success_criteria": "p < 0.05 with Bonferroni correction on out-of-sample data",
            "failure_criteria": "p >= 0.05 or effect size < 0.5%"
        },
        {
            "id": "H2",
            "claim": "...",
            # ...
        },
        {
            "id": "H3",
            "claim": "...",
            # ...
        }
    ],
    "data_requirements": [
        "Tweet timestamps + text from high-follower accounts",
        "BTC price at 1-minute granularity"
    ],
    "data_sources": ["Twitter/X API", "CoinGecko or Binance API"],
    "confounders_to_control": [
        "General market trends",
        "News events",
        "Regulatory announcements"
    ],
    "status": "running"
}
```

Key properties:

- **3 sub-hypotheses per round** — each with a claim, testable prediction, null hypothesis, and explicit success/failure criteria.
- **Data requirements and sources** identified upfront so the Out-of-Box Thinker and Playground know what's available.
- **Confounders** surfaced early — the Playground must address them.
- **Round 2+** generates 3 NEW sub-hypotheses informed by what was tested and what the data revealed in prior rounds.

## Pipeline Flow — Hypothesis Mode

```
Round N (max 5):
  First Principle Thinker
    Round 1: Classify input → hypothesis mode. Refine into 3 sub-hypotheses + data requirements.
    Round 2+: Review prior round results. Generate 3 NEW sub-hypotheses informed by
              what was tested, what was falsified, and any unexpected patterns in the data.

  Out-of-Box Thinker
    Receives: 3 sub-hypotheses + data requirements + prior round history
    For EACH sub-hypothesis, proposes an investigation angle:
      - Domain and methodology (e.g., "event study from financial economics")
      - Specific actors to investigate (e.g., "Elon Musk, Michael Saylor, CZ")
      - Data sources to use (e.g., "Twitter API filtered by follower count > 10M")
      - Confounders to control for
    Output: 3 investigation angles (one per sub-hypothesis)

  Playground x3 (parallel, one per sub-hypothesis + investigation angle)
    Each receives: one sub-hypothesis + its investigation angle + data requirements
    Produces: methodology sketch with data acquisition plan + pseudocode
    Actively considers falsification — "what would disprove this?"
    Scores 1-10 based on methodological promise, NOT confirmation bias

  Synthesizer (one per 8+ scorer)
    Builds PoC that includes data fetching code
    Injects credentials from config into GitHub Action workflow inputs
    Pushes to playground repo using branch_prefix, triggers GitHub Action
    Reports results honestly — negative results are valid
    Each completed Synthesizer output → its own Output document

  Reviewer
    Validates methodology, statistical rigor, confounder handling
    A well-conducted study that FALSIFIES a sub-hypothesis can score 9.0+
    Falsification with sound methodology = accepted result
```

### Key Structural Differences from Problem Mode

- **3 parallel Playground agents** instead of 5
- **Out-of-Box Thinker proposes investigation angles** (domain + actors + data + method) rather than abstract cross-domain fields
- **Each tested sub-hypothesis produces its own Output document** — validated, falsified, or inconclusive
- **Falsification is a first-class accepted outcome** if methodology is sound

## Agent Behavior Adaptations

All agents receive `dept_state["mode"]` as context. In problem mode, behavior is completely unchanged.

### First Principle Thinker (Leader)

System prompt addition for hypothesis mode:

- Classify input as problem or hypothesis
- For hypotheses: refine vague claims into 3 specific testable sub-hypotheses
- Identify open dimensions in vague hypotheses (WHO? WHAT metric? WHAT timeframe? WHAT magnitude?)
- Generate sub-hypotheses with claim, testable prediction, null hypothesis, and success/failure criteria
- Identify data requirements, data sources, and confounders
- Round 2+: generate 3 NEW sub-hypotheses informed by prior round results

### Out-of-Box Thinker

System prompt addition for hypothesis mode:

- Instead of "propose 5 cross-domain fields via bisociation," becomes "for each of the 3 sub-hypotheses, propose the best investigation angle"
- Each angle must include: domain and methodology, specific actors/sources to investigate, data sources to use, confounders to control for
- Still uses cross-domain thinking but grounded in concrete actors and data rather than abstract fields

### Playground

System prompt addition for hypothesis mode:

- Falsification duty: "Your job is NOT to confirm the hypothesis. Your job is to design a methodology that can HONESTLY test it."
- Must consider: "What would disprove this? What confounders could explain a spurious correlation?"
- Must include a data acquisition plan in the pseudocode sketch
- Score based on methodological rigor, not how likely confirmation seems

### Synthesizer

System prompt addition for hypothesis mode:

- PoC code must include data fetching using APIs from data requirements
- Read credentials from `data_source_credentials` config, inject as workflow inputs
- Use `branch_prefix` config for branch names: `{branch_prefix}/round-{N}-H{M}`
- Report results honestly — a clean negative result is a valid deliverable, not a failure

### Reviewer

System prompt addition for hypothesis mode:

- Falsification with sound methodology is a valid accepted result
- `dod_validation` means "did the PoC properly test the sub-hypothesis?" not "did it confirm it?"
- A rigorous study showing p=0.8 (no correlation) can score 9.5 if the methodology is bulletproof
- Check for: statistical rigor, confounder handling, sample size adequacy, out-of-sample validation

## Config Schema

Grows from 2 fields to 4:

```python
config_schema = {
    "github_playground_repo": {
        "type": "str",
        "required": True,
        "description": "Full URL of the GitHub playground repository for PoC validation",
    },
    "github_token": {
        "type": "str",
        "required": True,
        "description": "GitHub Personal Access Token with repo + workflow permissions",
    },
    "branch_prefix": {
        "type": "str",
        "required": False,
        "description": "Branch prefix for this department instance, e.g. 'elon-btc' produces branches like elon-btc/round-1-H1. Defaults to 'ps-{sprint_id}' if not set.",
    },
    "data_source_credentials": {
        "type": "dict",
        "required": False,
        "description": "API keys for data sources, keyed by source name. Injected into GitHub Action workflow inputs.",
    },
}
```

### Credential Flow

1. User configures `data_source_credentials: {"twitter_api_key": "...", "binance_api_key": "..."}`
2. First Principle Thinker lists data requirements and possible sources in the refinement
3. Playground includes data acquisition in its pseudocode sketch, referencing available credentials by key name
4. Synthesizer generates PoC code that reads credentials from environment variables, passes them as workflow `inputs` when dispatching the GitHub Action
5. The playground repo's `poc.yml` workflow maps those inputs to env vars for the running code
6. If a needed credential is not configured, Synthesizer falls back to public data sources or reports the sub-hypothesis can't be tested without it

### Frontend: Key/Value Pair Input

The PWA's `ConfigFields` component (`frontend/components/config-fields.tsx`) currently handles boolean (toggle), integer (number input), and string (text input). A `dict` type case must be added — a dynamic list of key/value rows with add/remove buttons — to support `data_source_credentials`.

## Output Documents

Every sub-hypothesis that completes the Synthesizer/Reviewer cycle produces its own Output document, regardless of whether it was validated or falsified:

- **Label:** `hypothesis_round_{N}_H{M}` — e.g., `hypothesis_round_1_H2`
- **Title:** The sub-hypothesis claim in plain language
- **Output type:** `MARKDOWN`
- **Content:**
  - Sub-hypothesis tested (claim + null hypothesis)
  - Methodology used (domain, method, data sources)
  - Data period and sample size
  - Statistical results (p-value, effect size, confidence interval)
  - Conclusion: **validated**, **falsified**, or **inconclusive**
  - Raw data summary or link to GitHub Action artifacts

### Final Outputs

- **Validation:** If any sub-hypothesis is accepted by Reviewer with score 9.0+, a final `"solution"` Output is written summarizing the finding. Other sub-hypothesis Outputs from the same round are kept — they're valuable context.
- **Falsification:** If all 5 rounds complete without validation, a final `"falsification_report"` Output summarizes everything tested, the aggregate evidence, and the conclusion that the hypothesis is likely false. This is a first-class deliverable, not a failure message.

## Termination Conditions

Four possible outcomes in hypothesis mode:

| Outcome | Condition | Sprint Status | Output Label |
|---------|-----------|---------------|--------------|
| **Solved** | Reviewer accepts a sub-hypothesis with score 9.0+ | `DONE` | `solution` |
| **Falsified** | 5 rounds completed, all sub-hypotheses properly tested but none validated | `DONE` | `falsification_report` |
| **Invalid hypothesis** | First Principle Thinker determines hypothesis is untestable (no data, unfalsifiable, circular) | `DONE` | `rejection` |
| **Exhausted** | 5 rounds completed, approaches kept failing to execute (code errors, data unavailable, weak methodology) | `DONE` | Best-attempt summary |

Key distinction: **falsified** = we tested rigorously and found nothing. **Exhausted** = we couldn't get the tests to run properly.

Boundary rule: if ANY sub-hypothesis across all rounds was properly tested through the Synthesizer/Reviewer cycle (regardless of outcome), the overall result is **falsified** — we did test, we got results. **Exhausted** only applies if NO sub-hypothesis ever completed the full cycle (all failed at Playground scoring, code execution, or data acquisition).

## Department State — Hypothesis Mode

```python
{
    "mode": "hypothesis",
    "round": 3,
    "original_claim": "I think there are correlations between tweets and bitcoin",
    "sub_hypotheses_current": [
        {"id": "H7", "claim": "...", "status": "testing"},
        {"id": "H8", "claim": "...", "status": "falsified"},
        {"id": "H9", "claim": "...", "status": "testing"}
    ],
    "round_history": [
        {
            "round": 1,
            "sub_hypotheses": [
                {"id": "H1", "claim": "...", "playground_score": 9, "result": "falsified"},
                {"id": "H2", "claim": "...", "playground_score": 6, "result": "low_score"},
                {"id": "H3", "claim": "...", "playground_score": 8, "result": "falsified"}
            ],
            "feedback": "H1 and H3 were properly tested but showed no significant correlation. H2 methodology was weak."
        },
        {
            "round": 2,
            "sub_hypotheses": [
                {"id": "H4", "claim": "...", "playground_score": 7, "result": "low_score"},
                {"id": "H5", "claim": "...", "playground_score": 8, "result": "inconclusive"},
                {"id": "H6", "claim": "...", "playground_score": 9, "result": "falsified"}
            ],
            "feedback": "H5 had insufficient data for the time period. H6 disproved volume correlation."
        }
    ],
    "status": "running"
}
```

## Global Alignment: MAX_ROUNDS

The current `MAX_ROUNDS = 10` in `leader/agent.py` is incorrect. The global standard is `MAX_REVIEW_ROUNDS = 5` in `base.py`. This spec aligns the Problem Solver to the global 5-round cap regardless of mode.

## Model Assignments and Cost

| Agent | Command | Model | Rationale |
|-------|---------|-------|-----------|
| First Principle Thinker | `decompose-problem` | `claude-opus-4-6` | Hardest reasoning — classify input, refine vague claims into testable sub-hypotheses |
| Out-of-Box Thinker | `propose-fields` | `claude-opus-4-6` | Creative cross-domain thinking, choosing investigation angles with concrete actors/sources |
| Playground | `explore-field` | `claude-opus-4-6` | Cross-domain reasoning + honest self-scoring + falsification thinking. Weak output = wasted round |
| Synthesizer | `build-poc` | `claude-sonnet-4-6` | Code generation + data fetching — Sonnet excels, no deep reasoning needed |
| Synthesizer | `fix-poc` | `claude-sonnet-4-6` | Code fixes based on reviewer feedback |
| Reviewer | `review-solution` | `claude-opus-4-6` | Independent quality gate — must catch subtle methodological flaws |

### Cost Estimates

Per-call costs (Opus: $15/$75 per M input/output. Sonnet: $3/$15 per M input/output):

| Agent | Input tokens | Output tokens | Cost/call |
|-------|-------------|---------------|-----------|
| First Principle Thinker | ~8K | ~3K | ~$0.35 |
| Out-of-Box Thinker | ~8K | ~3K | ~$0.35 |
| Playground (x3) | ~8K | ~3K | ~$0.35 each |
| Synthesizer | ~8K | ~4K | ~$0.08 |
| Synthesizer fix | ~8K | ~4K | ~$0.08 |
| Reviewer | ~8K | ~2K | ~$0.27 |

Per-round cost (assuming 2 sub-hypotheses score 8+, 1 fix cycle each): **~$2.61**

| Scenario | Rounds | Estimated cost |
|----------|--------|----------------|
| Best case (solved round 1) | 1 | ~$2.61 |
| Average (solved round 3) | 3 | ~$7.83 |
| Worst case (5 rounds) | 5 | ~$13.05 |

Costs grow slightly per round as round history accumulates in context.

## Files Changed

| File | Change |
|------|--------|
| `problem_solver/leader/agent.py` | `MAX_ROUNDS = 10` → 5. System prompt: add hypothesis mode. `execute_task`: parse hypothesis refinement. `generate_task_proposal`: adapt all stages for 3-agent parallelism in hypothesis mode, write per-sub-hypothesis Outputs, add `falsified` termination. Config schema: add `branch_prefix` and `data_source_credentials`. |
| `problem_solver/leader/commands/decompose_problem.py` | Update description and step_plan to cover both modes. |
| `problem_solver/workforce/out_of_box_thinker/agent.py` | System prompt: add hypothesis mode — propose 3 investigation angles (domain + method + actors + data sources). |
| `problem_solver/workforce/playground/agent.py` | System prompt: add falsification duty, data acquisition plan requirement. |
| `problem_solver/workforce/synthesizer/agent.py` | System prompt: data fetching code, credential injection, `branch_prefix` for branches, honest negative results. Model: `claude-opus-4-6` → `claude-sonnet-4-6` for `build-poc` and `fix-poc`. |
| `problem_solver/workforce/reviewer/agent.py` | System prompt: falsification with sound methodology is a valid accepted result. |
| `frontend/components/config-fields.tsx` | Add `dict` type handling — key/value pair input with add/remove rows. |
| `backend/agents/tests/test_problem_solver.py` | Add hypothesis mode tests: refinement, 3-agent parallelism, falsified termination, Output per sub-hypothesis. |
| Spec doc (`2026-04-11-problem-solver-department-design.md`) | Cross-reference this spec. |

No new files, no new agents, no new commands. Department name and slug stay as `problem_solver`.

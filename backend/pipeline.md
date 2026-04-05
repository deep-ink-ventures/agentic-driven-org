# Blueprint Architecture Pipeline

Systematic improvements to generalize department logic. Each item is independent and lands as its own commit with tests.

## Status Legend
- **DONE** — Implemented and tested
- **PARTIAL** — Started but incomplete
- **TODO** — Not started

---

## 1. Default `execute_task` on WorkforceBlueprint [DONE]

**Problem:** ~20 workforce agents have identical `execute_task`: call Claude, return response. Each reimplements the same 10-line method. Sales (4 agents), Community (4 agents), writers room analysts (6 agents), content_reviewer, and several others all do:
```python
def execute_task(self, agent, task):
    response, usage = call_claude(system_prompt=..., user_message=..., model=...)
    task.token_usage = usage
    task.save(update_fields=["token_usage"])
    return response
```

**Solution:** Make this the default on `WorkforceBlueprint.execute_task()`. Agents with integrations (Playwright, GitHub, SendGrid) override. Everyone else deletes their execute_task.

**Impact:** Eliminates ~20 identical overrides. New agents get correct behavior for free.

---

## 2. Leader delegation helper on LeaderBlueprint [DONE]

**Problem:** Marketing, Sales, Community leaders have 95% identical `execute_task` methods (build workforce desc → call Claude → parse delegated_tasks → create subtasks → schedule follow-ups). Engineering's is similar but adds file locking. ~60 lines copy-pasted 4 times.

**Solution:** Extract `_execute_delegation_task(agent, task, extra_suffix="", follow_up_days=None)` on `LeaderBlueprint`. Each leader calls it, optionally passing extras. Engineering adds its lock context via an override hook.

**Impact:** 4× copy-paste → 1 implementation. New leaders get delegation for free.

---

## 3. Review dimensions as single source of truth [DONE]

**Problem:** Scoring dimensions are hardcoded in 3 places per reviewer:
1. `get_review_pairs()` on the leader
2. The reviewer's system prompt
3. The reviewer's execute_task suffix

Adding a dimension requires 3 edits. They can drift.

**Solution:** Add `review_dimensions: list[str]` on reviewer blueprints. Leader's `_propose_review_chain` reads them from the blueprint. Reviewer's system prompt generates from them. One source of truth.

**Impact:** Eliminates drift risk. Makes adding dimensions a 1-line change.

---

## 4. Writers room `_evaluate_feedback` duplicates base class logic [DONE]

**Problem:** `_evaluate_feedback` in the writers room leader is a 150-line method that reimplements what `_evaluate_review_and_loop` already does:
- Ask Claude to score
- Parse the score
- Track polish attempts
- Call `should_accept_review()`
- Route fixes back or advance

The only writers-room-specific parts are: (a) gathering feedback from multiple analysts, (b) asking Claude to produce a consolidated score from multiple reports, (c) routing fixes via FLAG_ROUTING.

The stage pipeline (STAGES, CREATIVE_MATRIX, FEEDBACK_MATRIX, state machine) is legitimately different and should stay. But the quality evaluation inside it should reuse the base class.

**Solution:** Split `_evaluate_feedback` into:
- **Gathering + consolidation** (writers-room-specific): collect reports, ask Claude to score
- **Accept/reject decision** (universal): call `_evaluate_review_and_loop` or a shared helper with the score
- **Fix routing** (writers-room-specific): use FLAG_ROUTING to create fix tasks

Extract a `_evaluate_score_and_route(agent, score, stage_key, fix_proposal_fn)` helper that the base class and writers room both use.

**Impact:** Eliminates the duplicated scoring/polish/acceptance logic. Writers room keeps its orchestration but shares the quality gate.

---

## 5. Pipeline department pattern (Sales ≈ Community) [DONE]

**Problem:** Sales and Community are structural clones:
- researcher → analyst → writer → reviewer
- Same leader execute_task
- Same review pair structure
- Same generate_task_proposal pattern (delegate to a planning command)
- Only content domain differs

If we add "HR", "Legal", or "PR" departments, each will be another clone.

**Solution:** Consider whether sales/community leaders can share a `PipelineLeaderBlueprint` base that provides:
- The common execute_task delegation pattern (covered by #2)
- A `generate_task_proposal` that calls a configurable planning command
- Standard review pair wiring from workforce metadata

After items 1 and 2 landed, sales and community leaders naturally resolved to ~20 lines each: system prompt + get_review_pairs + commands + generate_task_proposal (4 lines). No separate base class needed — they're just thin config on top of LeaderBlueprint.

**Impact:** Prevents clone drift. New pipeline departments are trivial to add.

---

## 6. Kill skills/ boilerplate [DONE]

**Problem:** Every agent has a `skills/` directory with identical `__init__.py` boilerplate (pkgutil iteration). Skills are just static NAME/DESCRIPTION strings injected into the system prompt. They're not callable, not composable, not discoverable at runtime.

37 agents × 3 files each = ~111 files of boilerplate for what amounts to extra lines in the system prompt.

**Solution:** Move skill descriptions into command descriptions or the system prompt directly. The `@command` decorator already has a `description` field — enrich those. Delete `skills/` directories. Remove `skills_description` from `BaseBlueprint`.

**Alternative:** If skills should remain separate from commands (because they describe *capabilities* not *actions*), consolidate into a single `SKILLS` class attribute on the blueprint — a list of dicts, no file I/O.

**Impact:** Eliminates ~111 boilerplate files. Simpler agent structure.

---

## 7. Command validation at import time [N/A]

**Problem:** No enforcement that a registered command has a corresponding execution path. A command could be registered via `@command` but never wired into `execute_task`'s dispatch logic.

**Solution:** Skipped — commands are methods on the class (inherently validated). The default `execute_task` on WorkforceBlueprint means most agents no longer have custom dispatch logic. No real wiring risk remains.

**Impact:** N/A.

---

## 8. Output declarations [DONE]

**Problem:** Some agents produce persistent artifacts (Documents, GitHub issues) but this is buried in execute_task. No way for the leader or UI to know what an agent produces.

**Solution:** Added `outputs: list[str] = []` on `BaseBlueprint`. Set on web_researcher (`["document"]`), story_researcher (`["document"]`), and ticket_manager (`["github_issue"]`). Metadata only — doesn't change execution. Leaders and UI can use it to understand agent capabilities.

**Impact:** Self-describing agents. Low risk, low effort.

---

## Already resolved

### Universal quality scoring [DONE]
- `EXCELLENCE_THRESHOLD = 9.5`, `NEAR_EXCELLENCE_THRESHOLD = 9.0`, `MAX_POLISH_ATTEMPTS = 3`, `MAX_REVIEW_ROUNDS = 5`
- `parse_review_verdict()`, `should_accept_review()` in base.py
- All reviewer agents emit VERDICT format

### Declarative `get_review_pairs()` [DONE]
- Leaders define creator→reviewer flows declaratively
- Base class handles triggering, scoring, polish tracking, fix routing, escalation
- Engineering overrides `_propose_review_chain` for parallel reviewers
- Marketing, Sales, Community use default 1:1 implementation

### Marketing content_reviewer agent [DONE]
- New agent reviewing tweets, posts, email campaigns
- Wired into marketing review pairs

### Active review key tracking [DONE]
- `active_review_key` in internal_state for reliable chain lookup
- Prevents fragile dict-iteration task_key resolution

### EXCELLENCE_THRESHOLD not hardcoded [DONE]
- All reviewers use the constant, not literal 9.5

### review_engineer MAX_REVIEW_ROUNDS renamed [DONE]
- Local constant renamed to `MAX_PR_REVIEW_ROUNDS` to avoid shadowing

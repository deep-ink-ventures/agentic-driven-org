# Context Management: Document Lifecycle & Consolidation

**Date:** 2026-04-05
**Status:** Draft

## Problem

Agents receive all non-archived department documents as context. As projects age, documents accumulate — stale information contradicts newer findings, irrelevant context drowns the signal, and token costs grow with every task. Sources and documents are also truncated throughout the codebase, cutting information agents need.

## Principles

1. **No truncation.** Content created for agents must be read in full. If context grows too large, reduce the number of documents — never cut their content short.
2. **Knowledge persists.** Task results must survive beyond the sprint that produced them. The leader writes findings into department documents so all agents benefit.
3. **Context stays bounded.** Three tiers of consolidation keep active documents compact regardless of project age.
4. **Full history available.** Archived documents remain accessible through the UI. Nothing is deleted.

## Design

### 1. Leader Document Creation (per task batch)

When a batch of workforce tasks completes and the leader is triggered to plan next work, the leader first writes a document before planning.

**Changed flow in `_trigger_next_sprint_work()`:**

1. Workforce tasks complete, leader triggered (existing).
2. Leader creates a "Sprint Progress" document capturing:
   - What tasks were assigned and to whom.
   - Detailed results from each task's report (full content).
   - Key decisions, findings, and artifacts produced.
   - What remains open or unresolved.
3. Document saved to the department with `document_type=sprint_progress` and linked to the sprint.
4. Leader plans the next batch (existing). The new document now exists in department context for all agents.

**Naming:** `Sprint Progress — {sprint.text[:50]} — Batch {N}`

### 2. Sprint-End Consolidation

When a sprint transitions to `DONE` or `PAUSED` in `SprintDetailView.perform_update()`:

1. Fire celery task `consolidate_sprint_documents`.
2. Collect all documents tagged with this sprint in the department.
3. Claude reads them all and produces one comprehensive sprint summary per department, organized by topic.
4. The summary preserves all meaningful detail — findings, decisions, artifacts, outcomes. For paused sprints, the summary notes it is a pause point.
5. Original per-batch documents are archived (`is_archived=True`) with `consolidated_into` pointing to the new summary.
6. Summary document tagged `sprint_summary`.

### 3. Monthly Consolidation

A celery beat task runs on the 1st of each month:

1. For each department across all projects, find all non-archived documents older than 30 days.
2. Claude reads them and produces topic-clustered consolidated documents per department.
3. Claude drops information that is no longer true or relevant — this is the staleness cleanup.
4. Originals archived with `consolidated_into` pointing to their replacement.
5. Consolidated documents tagged `monthly_archive`.

After this runs, a department's active context contains at most: current sprint documents, recent sprint summaries (under 30 days old), and one set of monthly archive documents.

### 4. Volume Safety Net

A token threshold of **500k tokens** per department acts as a circuit breaker.

- Before building agent context in `get_context()`, estimate total token count of active department documents.
- If the threshold is exceeded, fire `consolidate_department_documents` asynchronously (same logic as monthly consolidation).
- Log a warning. The current agent still gets its context — the next invocation benefits from the cleanup.
- Under normal operation, sprint-end and monthly consolidation should keep departments well below this limit.

### 5. Truncation Removal

Remove all content truncations that cut information agents receive. The consolidation system manages context size — truncation must not.

**Must remove (~30 instances):**

| File | Line(s) | What is truncated |
|---|---|---|
| `base.py` | 258 | Document content `[:3000]` |
| `base.py` | 279 | Sibling exec_summary `[:100]` |
| `base.py` | 285 | Own exec_summary `[:100]` |
| `base.py` | 287 | Task report `[:200]` |
| `base.py` | 530, 533, 538 | Review/escalation exec_summary `[:60]` |
| `base.py` | 545 | Review report `[:3000]` |
| `base.py` | 555, 560 | Review task exec_summary `[:80]` |
| `base.py` | 712 | Review feedback `[:3000]` |
| `base.py` | 716, 721 | Fix task exec_summary `[:60]` |
| `base.py` | 773 | Completed task exec_summary `[:60]` |
| `base.py` | 921 | Original task exec_summary `[:200]` |
| `base.py` | 1000 | Task report `[:300]` |
| `base.py` | 1009 | Source text `[:500]` |
| `base.py` | 1011 | Source context `[:400]` |
| `projects/tasks.py` | 472 | Leader system_prompt `[:3000]` |
| `projects/tasks.py` | 754 | Blueprint system_prompt `[:2000]` |
| `projects/prompts.py` | 65 | Source extraction `[:10000]` |
| `output_serializer.py` | 47 | Output content `[:500]` |
| `writers_room/leader/agent.py` | 1022 | Feedback report `[:3000]` |
| `writers_room/leader/agent.py` | 1073 | Review snippet `[:3000]` |
| `writers_room/leader/agent.py` | 1185 | Text processed `[:2000]` |
| `engineering/leader/agent.py` | 266 | Active task exec_summary `[:120]` |
| `engineering/leader/agent.py` | 283 | Context summary `[:150]` |
| `engineering/leader/agent.py` | 312, 317 | Task exec_summary `[:60-80]` |
| `engineering/leader/agent.py` | 324 | Implementation report `[:3000]` |
| `engineering/leader/agent.py` | 779 | Area summary `[:1000]` |
| `engineering/workforce/backend_engineer` | 205 | File content `[:3000]` |
| `engineering/workforce/frontend_engineer` | 230 | File content `[:3000]` |
| `plan_room.py` | 55 | Task exec_summary `[:150]` |
| `plan_sprint.py` | 56 | Task exec_summary `[:150]` |

**Kept as-is (reviewed and accepted):**

| Location | Truncation | Reason |
|---|---|---|
| `base.py:282` | `[:10]` recent tasks queryset | Pagination |
| `base.py:994` | `[:20]` recent tasks queryset | Pagination |
| `base.py:1005` | `[:20]` department documents | Pagination |
| `base.py:1008` | `[:5]` sprint sources | Pagination |
| `plan_room.py:51` | `[:30]` completed tasks | Pagination |
| `plan_sprint.py:53` | `[:20]` completed tasks | Pagination |
| `engineering/workforce:194,219` | `file_paths[:5]` | Limits file count |
| `tasks.py:149,209,328,350` | `exec_summary[:80]` | Python log messages only |
| `tasks.py:225,250,252,570,571` | Error strings `[:200-1000]` | Error handling |
| `tasks.py:154` | `str(e)[:500]` | Error handling |
| `engineering/leader:169` | `task_id[:8]` | UUID display |
| `engineering/leader:888` | `resp.text[:300]` | Error logging |
| `writers_room/leader:1215` | `response[:200]` | Error logging |

### 6. Data Model Changes

**Document model additions:**

- `consolidated_into` — nullable self-referential FK. Points to the document that replaced this one during consolidation.
- `document_type` — choices: `general`, `sprint_progress`, `sprint_summary`, `monthly_archive`. Default: `general`.
- `sprint` — nullable FK to Sprint. Links progress documents and summaries to their sprint.

### 7. Frontend: Document History

A new "Document History" tab in project settings.

- **Default view:** active documents only (filtered by `is_archived=False`).
- **Toggle:** "Show archived" reveals the full history.
- Archived documents grouped by what they were consolidated into.
- Users can drill into any archived original from the consolidated document.

No documents are shown in the department view today. This tab is entirely new UI.

## New Celery Tasks

| Task | Trigger | What it does |
|---|---|---|
| Leader document creation | `_trigger_next_sprint_work()` | Leader writes sprint progress document before planning next batch |
| `consolidate_sprint_documents` | Sprint status → DONE or PAUSED | Merges all sprint documents into one summary per department |
| `consolidate_monthly_documents` | Celery beat, 1st of each month | Merges all documents older than 30 days into topic-clustered docs |
| `consolidate_department_documents` | Volume threshold exceeded (500k tokens) | Emergency consolidation, same logic as monthly |

## Context Composition After All Consolidations

At any point, an agent's department context contains at most:

1. Current sprint progress documents (from the active sprint).
2. Recent sprint summaries (under 30 days old).
3. Monthly archive documents (one set per month of historical context, with stale content removed).
4. General documents from bootstrap (until they age into monthly consolidation).

This keeps context bounded and fresh regardless of project age.

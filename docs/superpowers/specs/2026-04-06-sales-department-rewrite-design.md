# Sales Department Rewrite — Design Spec

**Date:** 2026-04-06
**Status:** Draft
**Scope:** Complete rewrite of `backend/agents/blueprints/sales/`

---

## Overview

Replace the current sales department (flat 2-pair flow with gaps) with a 7-agent linear pipeline that takes a project from industry research through personalized outreach. Single sprint cycle, sequential chain, with a QA feedback loop that cascades re-runs from the earliest failing agent.

**One base change required:** Add `outreach` boolean field to Agent model. Everything else lives in the sales blueprints folder.

---

## Architecture

### Pipeline Chain

```
Researcher → Strategist → Pitch Architect → Profile Selector → Pitch Personalizer → Sales QA → Outreach Dispatch
```

Each agent's output feeds the next. The leader tracks progress via `internal_state["pipeline_step"]` per sprint. No formal stage matrix (unlike writers room) — just sequential task proposal.

### QA Feedback Loop

- Sales QA scores 5 dimensions, each mapped to a specific agent
- On failure: identify earliest failing dimension → re-run from that agent forward
- Quality gates use base thresholds: 9.5 excellence, 9.0 near-excellence with 3 polish attempts
- Max 5 review rounds before human escalation

### Outreach Discovery

- `outreach=True` on Agent model instances (not blueprints)
- Leader queries `department.agents.filter(outreach=True, status="active")`
- Passes available channels to pitch_personalizer so it assigns the best channel per person
- Starting with email_outreach only; new channels = new agent with `outreach=True`
- Outreach agents send for real; existing task approval flow (`AWAITING_APPROVAL` → approve) controls the gate

---

## Directory Structure

```
backend/agents/blueprints/sales/
├── __init__.py                    # Blueprint registry entry
├── leader/
│   ├── __init__.py
│   └── agent.py                   # SalesLeaderBlueprint
└── workforce/
    ├── __init__.py
    ├── researcher/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       └── research_industry.py
    ├── strategist/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       ├── draft_strategy.py
    │       └── revise_strategy.py
    ├── pitch_architect/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       ├── design_storyline.py
    │       └── revise_storyline.py
    ├── profile_selector/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       ├── select_profiles.py
    │       └── revise_profiles.py
    ├── pitch_personalizer/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       ├── personalize_pitches.py
    │       └── revise_pitches.py
    ├── sales_qa/
    │   ├── __init__.py
    │   ├── agent.py
    │   └── commands/
    │       └── review_pipeline.py
    └── email_outreach/
        ├── __init__.py
        ├── agent.py
        └── commands/
            └── send_outreach.py
```

---

## Leader State Machine

### Pipeline Steps

```python
PIPELINE_STEPS = [
    "research",           # → researcher
    "strategy",           # → strategist
    "pitch_design",       # → pitch_architect
    "profile_selection",  # → profile_selector
    "personalization",    # → pitch_personalizer
    "qa_review",          # → sales_qa (review pair)
    "dispatch",           # → outreach agents
]
```

### generate_task_proposal Logic

1. Call `_check_review_trigger()` first — base class handles QA ping-pong
2. If no review pending, read `internal_state["pipeline_step"][sprint_id]`
3. Check if current step's task is done (query completed tasks for sprint + step)
4. If done → advance to next step, propose task for that step's agent
5. If no step yet → start at `"research"`
6. At `"dispatch"` step: collect personalized pitches, discover outreach agents, propose one task per outreach agent with assigned pitches
7. After dispatch completes → write sprint Output, mark sprint done

### Review Pair Declaration

```python
def get_review_pairs(self):
    return [{
        "creator": "pitch_personalizer",
        "creator_fix_command": "revise-pitches",
        "reviewer": "sales_qa",
        "reviewer_command": "review-pipeline",
        "dimensions": [
            "research_accuracy",
            "strategy_quality",
            "storyline_effectiveness",
            "profile_accuracy",
            "pitch_personalization",
        ],
    }]
```

### QA Cascade Fix Routing

Override `_propose_fix_task` to route fixes to the earliest failing agent:

```python
DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "pitch_architect",
    "profile_accuracy": "profile_selector",
    "pitch_personalization": "pitch_personalizer",
}

CHAIN_ORDER = [
    "researcher", "strategist", "pitch_architect",
    "profile_selector", "pitch_personalizer",
]
```

The override:
1. Reads per-dimension scores from the QA review report
2. Finds all dimensions below threshold
3. Maps to agents via `DIMENSION_TO_AGENT`
4. Finds earliest in `CHAIN_ORDER`
5. Proposes fix task for that agent with QA feedback
6. After fix, leader's normal `generate_task_proposal` continues the chain from there

---

## Agent Specifications

### Researcher (`researcher`)

**Role:** Industry research, competitive intel, trends, hot topics via live web search.

**Model:** `claude-haiku-4-5` (cheap, research-heavy)

**Skills:** `web_search`

**Commands:**
- `research-industry` — Given project context + sprint instruction, produce a structured industry briefing

**Source material (from knowledge-work-plugins `account-research`):**
- Company profiling structure: name, website, industry, size, headquarters, founded, funding, revenue
- Research output format: Quick Take, Company Profile, What They Do, Recent News, Hiring Signals, Key People, Qualification Signals, Recommended Approach
- Research variations: company research, person research, competitor research
- Systematic intel gathering methodology with qualification signals (positive, concerns, unknowns)

**Output:** Task report + Department Document (`doc_type=RESEARCH`) for institutional persistence across sprints.

---

### Strategist (`strategist`)

**Role:** Draft thesis on 3-5 target areas for outreach based on research.

**Commands:**
- `draft-strategy` — Read researcher's briefing, project goal, instructions. Output: 3-5 target areas with name, description, rationale, estimated potential, suggested approach
- `revise-strategy` — Revision based on QA feedback

**Source material (from knowledge-work-plugins `competitive-intelligence`):**
- Market positioning frameworks and comparison matrices
- Where-they-win/lose analysis methodology
- Landmine question methodology for competitive positioning
- Target segmentation: industry sector, cohort of people, mailing list subset

**Output:** Task report + Department Document (`doc_type=STRATEGY`) for institutional persistence.

---

### Pitch Architect (`pitch_architect`)

**Role:** Craft the narrative arc — how we tell our story, why it matters, why someone would care, how it avoids feeling like spam.

**Commands:**
- `design-storyline` — Read strategy + research. Output: storyline with hook, narrative arc, value proposition framing, objection preemption
- `revise-storyline` — Revision based on QA feedback

**Source material (from knowledge-work-plugins `draft-outreach`):**
- AIDA email structure (Attention, Interest, Desire, Action)
- Hook identification categories: trigger events, mutual connections, content engagement, company initiatives, role-based pain points
- Anti-spam principles: plain text, no markdown, specific details over templates, prospect's language
- Message templates awareness: cold, warm, re-engagement, post-event (for storyline variety)

**Output:** Task report.

---

### Profile Selector (`profile_selector`)

**Role:** For each target area, compile concrete persons to outreach to.

**Model:** `claude-haiku-4-5` (research-heavy, cheap)

**Skills:** `web_search`

**Commands:**
- `select-profiles` — For each target area from strategist, find concrete persons. Output per person: name, role, company, LinkedIn, relevance to target area, background, tenure, talking points, contact info if available
- `revise-profiles` — Revision based on QA feedback

**Source material (from knowledge-work-plugins `account-research`):**
- Key People profiling: LinkedIn, background, tenure, email, talking points per person
- Qualification Signals: positive signals, concerns, unknowns per prospect
- Recommended Approach per person: entry point, opening hook, discovery questions

**Output:** Task report.

---

### Pitch Personalizer (`pitch_personalizer`)

**Role:** Research each person, adapt the storyline for them, assign best outreach channel.

**Skills:** `web_search`

**Commands:**
- `personalize-pitches` — For each profile: research recent activity/interests/publications, adapt storyline, select outreach channel from available agents. Output: one personalized pitch per person with channel assignment
- `revise-pitches` — The fix command for the QA loop (also used when QA routes fixes here directly)

**Source material (from knowledge-work-plugins `draft-outreach` + `create-an-asset`):**
- Personalization methodology: minimum 2 specific details per person, never generic
- Prospect language mirroring from `create-an-asset`: use their exact words for pain points
- Message templates: cold (trigger event hook), warm (mutual connection), re-engagement (previous interaction), post-event (shared experience)
- Subject line alternatives and follow-up sequence structure
- Format-specific adaptation based on channel capabilities

**Input includes:** Available outreach agents list from leader (queried via `department.agents.filter(outreach=True)`)

**Output:** Task report with structured pitch payloads (one per person, each tagged with target outreach agent type).

---

### Sales QA (`sales_qa`)

**Role:** Multi-dimensional quality gate reviewing the entire pipeline output.

**Essential:** `True` (always provisioned)

**Review dimensions:**
- `research_accuracy` — Is the industry research factually correct, current, and comprehensive?
- `strategy_quality` — Are target areas well-reasoned, differentiated, and actionable?
- `storyline_effectiveness` — Does the narrative compel without feeling like spam? Is the hook genuine?
- `profile_accuracy` — Are profiles real, relevant, correctly matched to target areas?
- `pitch_personalization` — Does each pitch feel individually crafted? Are specific details genuine?

**Commands:**
- `review-pipeline` — Review all pipeline outputs end-to-end. Score each dimension 1.0-10.0. Overall score = minimum of all dimensions. Call `submit_verdict` tool.

**Source material (drawn from all knowledge-work-plugins sales skills as review criteria):**
- From `account-research`: verify research follows systematic methodology, qualification signals are grounded
- From `draft-outreach`: verify AIDA structure, hooks are specific not templated, personalization has 2+ real details
- From `competitive-intelligence`: verify competitive positioning is honest, differentiators are real
- Anti-pattern detection: generic flattery, fake familiarity, template-obvious phrasing, unverifiable claims

**Output:** Task report with per-dimension scores + verdict via `submit_verdict` tool.

---

### Email Outreach (`email_outreach`)

**Role:** Format and send personalized emails.

**Commands:**
- `send-outreach` — Takes personalized pitch payloads, formats as emails, sends via configured channel

**Source material (from knowledge-work-plugins `draft-outreach`):**
- Email style guidelines: plain text only, no markdown, no HTML
- Subject line best practices: short, specific, no clickbait
- Follow-up sequence structure: timing, escalation, breakup email
- Company configuration: sender name, title, value props, proof points, CTA options, tone

**Config:** Agent config holds sending mechanism details (e.g., Gmail integration settings)

**Outreach flag:** `outreach=True` set on agent instance during provisioning.

**Output:** Task report logging what was sent to whom.

---

## Context Passing Between Agents

The leader's `generate_task_proposal` reads completed task reports for the current sprint and injects relevant prior outputs into each task's `step_plan`:

| Step | Gets injected context from |
|------|---------------------------|
| researcher | Project goal, sprint instruction, sprint sources |
| strategist | Researcher's report |
| pitch_architect | Researcher's report + strategist's report |
| profile_selector | Strategist's report (target areas) |
| pitch_personalizer | Pitch architect's report (storyline) + profile selector's report (persons) + available outreach agents list |
| sales_qa | All prior reports (full pipeline review) |
| outreach dispatch | Pitch personalizer's report (pitch payloads) |

---

## Output & Document Strategy

**Persistent documents (survive across sprints):**
- Researcher creates Document (`doc_type=RESEARCH`) — industry briefing
- Strategist creates Document (`doc_type=STRATEGY`) — target area thesis

**Sprint Output:**
- Created by leader when outreach dispatch completes
- `output_type=MARKDOWN`
- Content: summary of target areas, number of pitches sent, channels used, personalization highlights
- Individual pitch details live in outreach agent task reports

---

## Base Change: Agent Model

**File:** `backend/agents/models/agent.py`

Add:
```python
outreach = models.BooleanField(
    default=False,
    help_text="Whether this agent handles outreach delivery (email, LinkedIn, etc.)"
)
```

Plus migration. No other base changes required.

---

## Blueprint Registry

Update `backend/agents/blueprints/__init__.py` to register the new sales department with all 8 agents (1 leader + 7 workforce).

---

## What's NOT in Scope

- LinkedIn, Twitter, or other outreach agents (future — just add new agent with `outreach=True`)
- CRM integration (future — would enhance researcher and profile_selector)
- Meeting/call prep flows (future — could add call_prep agent using knowledge-work `call-prep` skill)
- Pipeline dashboards or daily briefings (future — could add scheduled leader command using `daily-briefing` skill)
- Changes to base.py (all department logic uses existing hooks)

# Sales & Community Departments Design

## Overview

Two new generic departments for revenue acquisition: **Sales** (daily outbound prospecting and outreach) and **Community & Partnerships** (weekly ecosystem mapping and relationship building). Both use writer/reviewer pairs that ping-pong via tasks until quality threshold is met.

These are generic departments — no business-specific logic in the blueprints. Domain specificity comes from project goal + source documents + agent instructions.

## Department 1: Sales

**Purpose:** Proactively identify, research, and pursue revenue opportunities through outbound prospecting and personalized outreach.

**Cadence:** Daily pipeline planning, hourly progress checks.

### Leader: Sales Director

**Blueprint:** `SalesLeaderBlueprint`
**Slug:** `sales_director`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `plan-pipeline` (daily, Sonnet) — Reviews current pipeline state (prospects, outreach drafts, follow-ups due). Identifies highest-value targets to pursue. Delegates research tasks to Prospector and outreach tasks to Outreach Writer. Triggers review cycles.
- `check-progress` (hourly, Haiku) — Lightweight health check. Detects stalled review loops, overdue follow-ups, agents with no active tasks. Escalates blockers.

**Skills:**
- `pipeline_management` — Track prospects through stages: identified → researched → contacted → negotiating → closed
- `target_prioritization` — Score targets by strategic fit, revenue potential, and reachability
- `review_orchestration` — Manage writer/reviewer ping-pong loops, enforce quality thresholds

**Delegation pattern:**
1. `plan-pipeline` proposes tasks for Prospector (research targets) and Outreach Writer (draft outreach)
2. When a Prospector task completes, leader auto-creates a Prospect Analyst review task
3. If analyst scores below threshold → leader creates revision task back to Prospector with feedback
4. Same loop for Outreach Writer → Outreach Reviewer
5. When reviewer approves → leader creates follow-up task or marks pipeline stage advanced

### Workforce Agent: Prospector

**Blueprint:** `ProspectorBlueprint`
**Slug:** `prospector`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `research-targets` (on-demand, Sonnet) — Research and qualify potential targets based on leader's criteria. Uses web search to gather company info, key contacts, recent activity. Returns structured lead list with qualification notes.
- `revise-prospects` (on-demand, Sonnet) — Refine a prospect list based on analyst feedback. Address specific gaps, re-research flagged entries, add missing context.

**Skills:**
- `company_profiling` — Build structured profiles: size, industry, key contacts, recent news, decision makers
- `qualification_scoring` — Assess fit based on configurable criteria (budget signals, need indicators, timing)
- `web_intelligence` — Extract actionable intelligence from public sources (websites, LinkedIn, press releases, job postings)

### Workforce Agent: Prospect Analyst

**Blueprint:** `ProspectAnalystBlueprint`
**Slug:** `prospect_analyst`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `review-prospects` (on-demand, Sonnet) — Review a prospect list for quality, relevance, and strategic fit. Score each prospect. Identify gaps, weak qualifications, missing context. Return verdict: approved (with scores) or revision-needed (with specific feedback per prospect).

**Skills:**
- `quality_scoring` — Score prospects on completeness, relevance, and actionability (1-10 scale)
- `gap_detection` — Identify missing information that would be needed before outreach
- `strategic_fit` — Assess alignment with project goals and target market

### Workforce Agent: Outreach Writer

**Blueprint:** `OutreachWriterBlueprint`
**Slug:** `outreach_writer`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `draft-outreach` (on-demand, Sonnet) — Write personalized outreach for a specific prospect. Uses prospect research, project positioning, and target context. Produces email/message draft with subject line, body, and call to action.
- `revise-outreach` (on-demand, Sonnet) — Revise a draft based on reviewer feedback. Address specific issues: tone, personalization depth, value prop clarity, CTA strength.

**Skills:**
- `personalization` — Tailor messaging to recipient's context, company, and likely pain points
- `value_proposition` — Articulate why the prospect should care, framed in their terms
- `call_to_action` — Craft specific, low-friction next steps that advance the relationship

### Workforce Agent: Outreach Reviewer

**Blueprint:** `OutreachReviewerBlueprint`
**Slug:** `outreach_reviewer`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `review-outreach` (on-demand, Sonnet) — Review an outreach draft against quality criteria: personalization depth, value proposition clarity, professional tone, appropriate length, clear CTA, no generic filler. Return verdict: approved or revision-needed with line-level feedback.

**Skills:**
- `tone_analysis` — Assess professional tone, confidence without pushiness, authenticity
- `personalization_depth` — Check that messaging references specific prospect details, not generic templates
- `effectiveness_scoring` — Score likelihood of response based on outreach best practices

---

## Department 2: Community & Partnerships

**Purpose:** Build ecosystem relationships, cross-promotion opportunities, and strategic partnerships that create sustainable inbound channels.

**Cadence:** Weekly community planning, daily progress checks.

### Leader: Community Director

**Blueprint:** `CommunityLeaderBlueprint`
**Slug:** `community_director`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `plan-community` (weekly, Sonnet) — Map current ecosystem state, identify new partnership categories, prioritize relationship targets. Delegates research to Ecosystem Researcher and proposal drafting to Partnership Writer. Triggers review cycles.
- `check-progress` (daily, Haiku) — Track active partnerships, pending proposals, stalled review loops. Flag relationships that need follow-up.

**Skills:**
- `ecosystem_mapping` — Categorize and track organizations, communities, events, and influencers by relevance and relationship stage
- `partnership_strategy` — Identify mutually beneficial partnership structures (referrals, co-marketing, cross-promotion, bundled offerings)
- `review_orchestration` — Manage writer/reviewer ping-pong loops for partnership proposals

**Delegation pattern:**
Same ping-pong as Sales:
1. `plan-community` creates research tasks for Ecosystem Researcher
2. Completed research → leader creates Ecosystem Analyst review task
3. Analyst feedback loop until approved
4. Approved ecosystem map → leader creates Partnership Writer tasks for top targets
5. Drafts → Partnership Reviewer loop until approved

### Workforce Agent: Ecosystem Researcher

**Blueprint:** `EcosystemResearcherBlueprint`
**Slug:** `ecosystem_researcher`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `map-ecosystem` (on-demand, Sonnet) — Research a specific ecosystem category (e.g., "local tech communities", "industry events", "complementary businesses"). Uses web search. Returns structured map with organizations, key contacts, relevance notes, partnership potential.
- `revise-research` (on-demand, Sonnet) — Refine ecosystem research based on analyst feedback. Fill gaps, re-assess flagged entries, explore missed categories.

**Skills:**
- `organization_profiling` — Build structured profiles of organizations, communities, and event series
- `relationship_mapping` — Identify connections between ecosystem entities (who partners with whom, shared audiences)
- `opportunity_detection` — Spot partnership openings (upcoming events, new programs, expansion announcements)

### Workforce Agent: Ecosystem Analyst

**Blueprint:** `EcosystemAnalystBlueprint`
**Slug:** `ecosystem_analyst`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `review-ecosystem` (on-demand, Sonnet) — Review ecosystem research for completeness, strategic prioritization, and missed opportunities. Score each entity on partnership potential. Return verdict: approved or revision-needed with specific feedback.

**Skills:**
- `strategic_prioritization` — Rank ecosystem entities by reach, alignment, and effort-to-engage
- `gap_analysis` — Identify ecosystem categories or entities that should have been included but weren't
- `competitive_landscape` — Assess whether competitors already have relationships with identified entities

### Workforce Agent: Partnership Writer

**Blueprint:** `PartnershipWriterBlueprint`
**Slug:** `partnership_writer`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `draft-proposal` (on-demand, Sonnet) — Write a partnership proposal for a specific target. Articulates mutual value, proposed structure, concrete next steps. Uses ecosystem research and project context.
- `revise-proposal` (on-demand, Sonnet) — Revise a proposal based on reviewer feedback. Strengthen mutual value prop, clarify structure, improve specificity.

**Skills:**
- `mutual_value` — Frame partnerships as win-win, emphasizing what the partner gains
- `proposal_structure` — Organize proposals: context → opportunity → proposed structure → next steps
- `specificity` — Ground proposals in concrete actions rather than vague "let's collaborate"

### Workforce Agent: Partnership Reviewer

**Blueprint:** `PartnershipReviewerBlueprint`
**Slug:** `partnership_reviewer`
**Default model:** `claude-sonnet-4-6`

**Commands:**
- `review-proposal` (on-demand, Sonnet) — Review a partnership proposal for mutual value clarity, professional tone, specificity, realistic structure, and clear next steps. Return verdict: approved or revision-needed with specific feedback.

**Skills:**
- `value_balance` — Ensure the proposal isn't one-sided — partner must see clear benefit
- `professionalism` — Check tone is collaborative, not desperate or transactional
- `actionability` — Verify proposed next steps are concrete and low-friction

---

## Ping-Pong Review Pattern (Both Departments)

The review loop is orchestrated by the leader, not hard-coded in workforce agents:

1. **Writer completes task** → task marked `done`
2. **Leader's `check-progress`** detects completed writer task → creates review task for paired reviewer, referencing the writer's report
3. **Reviewer completes review** → returns verdict in report:
   - `{"verdict": "approved", "score": 8, "notes": "..."}` → leader advances pipeline
   - `{"verdict": "revision_needed", "score": 5, "feedback": "..."}` → leader creates revision task for writer with feedback attached
4. **Writer revises** → reviewer reviews again → loop until approved or max 3 rounds (then leader escalates to human)

The leader manages this by reading the reviewer's report JSON and deciding the next action. No special infrastructure needed — it's all task delegation.

## Registration

Both departments must be registered in `backend/agents/blueprints/__init__.py` following the existing pattern:
- Import leader blueprints directly
- Import workforce blueprints via lazy `_workforce_imports` dict
- Add to `DEPARTMENT_REGISTRY` and `BLUEPRINT_REGISTRY`

## File Structure

```
backend/agents/blueprints/sales/
├── __init__.py
├── leader/
│   ├── __init__.py
│   ├── agent.py (SalesLeaderBlueprint)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── plan_pipeline.py
│   │   └── check_progress.py
│   └── skills/
│       ├── __init__.py
│       ├── pipeline_management.py
│       ├── target_prioritization.py
│       └── review_orchestration.py
└── workforce/
    ├── __init__.py
    ├── prospector/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (research_targets.py, revise_prospects.py)
    │   └── skills/ (company_profiling.py, qualification_scoring.py, web_intelligence.py)
    ├── prospect_analyst/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (review_prospects.py)
    │   └── skills/ (quality_scoring.py, gap_detection.py, strategic_fit.py)
    ├── outreach_writer/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (draft_outreach.py, revise_outreach.py)
    │   └── skills/ (personalization.py, value_proposition.py, call_to_action.py)
    └── outreach_reviewer/
        ├── __init__.py
        ├── agent.py
        ├── commands/ (review_outreach.py)
        └── skills/ (tone_analysis.py, personalization_depth.py, effectiveness_scoring.py)

backend/agents/blueprints/community/
├── __init__.py
├── leader/
│   ├── __init__.py
│   ├── agent.py (CommunityLeaderBlueprint)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── plan_community.py
│   │   └── check_progress.py
│   └── skills/
│       ├── __init__.py
│       ├── ecosystem_mapping.py
│       ├── partnership_strategy.py
│       └── review_orchestration.py
└── workforce/
    ├── __init__.py
    ├── ecosystem_researcher/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (map_ecosystem.py, revise_research.py)
    │   └── skills/ (organization_profiling.py, relationship_mapping.py, opportunity_detection.py)
    ├── ecosystem_analyst/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (review_ecosystem.py)
    │   └── skills/ (strategic_prioritization.py, gap_analysis.py, competitive_landscape.py)
    ├── partnership_writer/
    │   ├── __init__.py
    │   ├── agent.py
    │   ├── commands/ (draft_proposal.py, revise_proposal.py)
    │   └── skills/ (mutual_value.py, proposal_structure.py, specificity.py)
    └── partnership_reviewer/
        ├── __init__.py
        ├── agent.py
        ├── commands/ (review_proposal.py)
        └── skills/ (value_balance.py, professionalism.py, actionability.py)
```

## What's NOT in scope

- Hotel-specific logic — departments are generic, project goal provides context
- CRM integration — tasks and reports serve as the pipeline tracker
- Email sending — outreach drafts are produced as task reports, not sent automatically
- Financial tracking — no deal value or revenue attribution

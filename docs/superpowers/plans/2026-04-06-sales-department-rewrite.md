# Sales Department Rewrite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current flat sales department with a 7-agent linear pipeline (research → strategy → pitch → profiles → personalization → QA → outreach) with cascade QA feedback loop.

**Architecture:** Leader state machine tracks pipeline steps per sprint. Single review pair (pitch_personalizer → sales_qa) with override `_propose_fix_task` that routes QA failures to the earliest failing agent in the chain. Outreach agents discovered via `outreach=True` flag on Agent model.

**Tech Stack:** Django, Celery, Claude API, existing blueprint base classes (LeaderBlueprint, WorkforceBlueprint)

**Spec:** `docs/superpowers/specs/2026-04-06-sales-department-rewrite-design.md`

**Scope note:** All work is in `backend/agents/blueprints/sales/` except Task 1 (Agent model migration). The blueprint registry (`backend/agents/blueprints/__init__.py`) is updated in the final task.

---

## File Structure

### Files to Create (new sales department)
- `backend/agents/blueprints/sales/__init__.py` — empty (already exists)
- `backend/agents/blueprints/sales/leader/__init__.py` — exports SalesLeaderBlueprint
- `backend/agents/blueprints/sales/leader/agent.py` — leader with pipeline state machine
- `backend/agents/blueprints/sales/workforce/__init__.py` — empty (already exists)
- `backend/agents/blueprints/sales/workforce/researcher/__init__.py`
- `backend/agents/blueprints/sales/workforce/researcher/agent.py`
- `backend/agents/blueprints/sales/workforce/researcher/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/researcher/commands/research_industry.py`
- `backend/agents/blueprints/sales/workforce/strategist/__init__.py`
- `backend/agents/blueprints/sales/workforce/strategist/agent.py`
- `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`
- `backend/agents/blueprints/sales/workforce/strategist/commands/revise_strategy.py`
- `backend/agents/blueprints/sales/workforce/pitch_architect/__init__.py`
- `backend/agents/blueprints/sales/workforce/pitch_architect/agent.py`
- `backend/agents/blueprints/sales/workforce/pitch_architect/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/pitch_architect/commands/design_storyline.py`
- `backend/agents/blueprints/sales/workforce/pitch_architect/commands/revise_storyline.py`
- `backend/agents/blueprints/sales/workforce/profile_selector/__init__.py`
- `backend/agents/blueprints/sales/workforce/profile_selector/agent.py`
- `backend/agents/blueprints/sales/workforce/profile_selector/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/profile_selector/commands/select_profiles.py`
- `backend/agents/blueprints/sales/workforce/profile_selector/commands/revise_profiles.py`
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/__init__.py`
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/revise_pitches.py`
- `backend/agents/blueprints/sales/workforce/sales_qa/__init__.py`
- `backend/agents/blueprints/sales/workforce/sales_qa/agent.py`
- `backend/agents/blueprints/sales/workforce/sales_qa/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/sales_qa/commands/review_pipeline.py`
- `backend/agents/blueprints/sales/workforce/email_outreach/__init__.py`
- `backend/agents/blueprints/sales/workforce/email_outreach/agent.py`
- `backend/agents/blueprints/sales/workforce/email_outreach/commands/__init__.py`
- `backend/agents/blueprints/sales/workforce/email_outreach/commands/send_outreach.py`

### Files to Modify
- `backend/agents/models/agent.py` — add `outreach` BooleanField
- `backend/agents/blueprints/__init__.py` — update sales registry with new agents

### Files to Delete
- `backend/agents/blueprints/sales/workforce/prospector/` (entire directory)
- `backend/agents/blueprints/sales/workforce/prospect_analyst/` (entire directory)
- `backend/agents/blueprints/sales/workforce/outreach_writer/` (entire directory)
- `backend/agents/blueprints/sales/workforce/outreach_reviewer/` (entire directory)
- `backend/agents/blueprints/sales/leader/commands/` (entire directory — leader no longer uses commands)

---

## Task 1: Add `outreach` Field to Agent Model

**Files:**
- Modify: `backend/agents/models/agent.py:36` (after `auto_approve`)
- Create: migration via `makemigrations`

This is the only task that touches files outside `backend/agents/blueprints/sales/`.

- [ ] **Step 1: Add the field**

In `backend/agents/models/agent.py`, add after the `auto_approve` field (line 38):

```python
    outreach = models.BooleanField(
        default=False,
        help_text="Whether this agent handles outreach delivery (email, LinkedIn, etc.)",
    )
```

- [ ] **Step 2: Generate migration**

Run: `cd backend && python manage.py makemigrations agents -n add_agent_outreach_field`

Expected: `Migrations for 'agents': agents/migrations/NNNN_add_agent_outreach_field.py`

- [ ] **Step 3: Apply migration**

Run: `cd backend && python manage.py migrate agents`

Expected: `Applying agents.NNNN_add_agent_outreach_field... OK`

- [ ] **Step 4: Commit**

```bash
git add backend/agents/models/agent.py backend/agents/migrations/*add_agent_outreach*
git commit -m "feat(agents): add outreach boolean field to Agent model"
```

---

## Task 2: Delete Old Sales Workforce Agents

**Files:**
- Delete: `backend/agents/blueprints/sales/workforce/prospector/`
- Delete: `backend/agents/blueprints/sales/workforce/prospect_analyst/`
- Delete: `backend/agents/blueprints/sales/workforce/outreach_writer/`
- Delete: `backend/agents/blueprints/sales/workforce/outreach_reviewer/`
- Delete: `backend/agents/blueprints/sales/leader/commands/`

- [ ] **Step 1: Delete old workforce agents and leader commands**

```bash
rm -rf backend/agents/blueprints/sales/workforce/prospector
rm -rf backend/agents/blueprints/sales/workforce/prospect_analyst
rm -rf backend/agents/blueprints/sales/workforce/outreach_writer
rm -rf backend/agents/blueprints/sales/workforce/outreach_reviewer
rm -rf backend/agents/blueprints/sales/leader/commands
```

- [ ] **Step 2: Commit**

```bash
git add -A backend/agents/blueprints/sales/workforce/ backend/agents/blueprints/sales/leader/commands/
git commit -m "chore(sales): remove old sales workforce agents and leader commands"
```

---

## Task 3: Researcher Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/researcher/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/researcher/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/researcher/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/researcher/commands/research_industry.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/researcher/commands
```

- [ ] **Step 2: Create command file**

Create `backend/agents/blueprints/sales/workforce/researcher/commands/research_industry.py`:

```python
"""Researcher command: industry research and competitive intel."""

from agents.blueprints.base import command


@command(
    name="research-industry",
    description=(
        "Research the industry landscape, competitors, trends, and hot topics. "
        "Produce a structured briefing document with company profiles, market signals, "
        "and qualification analysis."
    ),
    model="claude-haiku-4-5",
)
def research_industry(self, agent) -> dict:
    return {
        "exec_summary": "Research industry landscape and produce structured briefing",
        "step_plan": (
            "1. Review project goal and sprint instruction for research focus\n"
            "2. Research industry landscape via web search — key players, market size, trends\n"
            "3. Profile top competitors — what they offer, positioning, recent moves\n"
            "4. Identify hot topics and recent developments in the space\n"
            "5. Assess qualification signals — budget indicators, need signals, timing\n"
            "6. Compile structured briefing with Quick Take, profiles, news, and signals"
        ),
    }
```

- [ ] **Step 3: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/researcher/commands/__init__.py`:

```python
"""Researcher commands registry."""

from .research_industry import research_industry

ALL_COMMANDS = [research_industry]
```

- [ ] **Step 4: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/researcher/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.researcher.commands import research_industry

logger = logging.getLogger(__name__)


class ResearcherBlueprint(WorkforceBlueprint):
    name = "Sales Researcher"
    slug = "researcher"
    description = (
        "Industry research specialist — competitive intel, market trends, "
        "company profiling, and qualification analysis via live web search"
    )
    tags = ["research", "industry", "competitive-intel", "trends", "web-search"]
    default_model = "claude-haiku-4-5"
    skills = [
        {
            "name": "Company Profiling",
            "description": (
                "Build structured profiles: name, website, industry, size, headquarters, "
                "founded, funding, revenue. Cross-reference multiple sources."
            ),
        },
        {
            "name": "Market Intelligence",
            "description": (
                "Track industry trends, hot topics, recent developments, hiring signals, "
                "and competitive moves from public sources"
            ),
        },
        {
            "name": "Qualification Analysis",
            "description": (
                "Assess targets with qualification signals: positive signals (growth, funding, "
                "hiring), concerns (layoffs, leadership changes), unknowns (data gaps)"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales research specialist. Your job is to research an industry landscape and produce a structured briefing that the sales team can act on.

Your output must follow this structure:

## Quick Take
2-3 sentences: who the key players are and what the best approach looks like.

## Industry Overview
- Market size and growth trajectory
- Key segments and their dynamics
- Dominant players and emerging challengers

## Competitor Profiles
For each major competitor:
| Field | Value |
|-------|-------|
| Name | ... |
| Website | ... |
| Industry | ... |
| Size | ... |
| Headquarters | ... |
| Founded | ... |
| Funding / Revenue | ... |

**What They Do:** 1-2 sentence description.
**Recent News:** What happened recently and why it matters for our outreach.
**Hiring Signals:** Open roles and what they indicate about growth direction.

## Hot Topics & Trends
- What is currently discussed in this industry
- Recent developments that create outreach opportunities
- Emerging needs or pain points

## Qualification Signals
- **Positive:** Growth indicators, funding, hiring, expansion
- **Concerns:** Layoffs, leadership changes, financial trouble
- **Unknowns:** Data gaps that need follow-up

## Recommended Approach
- Best entry points for outreach
- Timing considerations
- What angles resonate in this market right now

IMPORTANT: Use web search to gather current, real data. Do not fabricate company profiles or news. If information is unavailable, say so explicitly."""

    research_industry = research_industry

    def get_task_suffix(self, agent, task):
        return """# RESEARCH METHODOLOGY

## Source Diversity
- Search company websites, LinkedIn, press releases, news articles, job postings, industry reports
- Cross-reference multiple sources to validate information
- Note recency of information — flag anything older than 6 months
- Prioritize primary sources over aggregator summaries

## Research Output Standards
- Every company profile must have verifiable data points
- Every trend claim must cite a specific source or signal
- Hiring signals should reference actual job postings or announcements
- Qualification signals must distinguish facts from inferences

## Anti-Patterns to Avoid
- Do not fabricate company details or revenue figures
- Do not present speculation as fact — label uncertainty explicitly
- Do not pad thin research with generic industry boilerplate
- If a search returns no results, say "no data found" rather than guessing"""
```

- [ ] **Step 5: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/researcher/__init__.py`:

```python
from .agent import ResearcherBlueprint

__all__ = ["ResearcherBlueprint"]
```

Note: The researcher persists its output as a Department Document (`doc_type=RESEARCH`). This is handled by the leader in `_propose_step_task` — after the researcher's task completes, the leader creates the document from the task report before advancing to the next step. See Task 10 for implementation.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/researcher/
git commit -m "feat(sales): add researcher agent with industry research command"
```

---

## Task 4: Strategist Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/strategist/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/strategist/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`
- Create: `backend/agents/blueprints/sales/workforce/strategist/commands/revise_strategy.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/strategist/commands
```

- [ ] **Step 2: Create draft_strategy command**

Create `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`:

```python
"""Strategist command: draft target area thesis."""

from agents.blueprints.base import command


@command(
    name="draft-strategy",
    description=(
        "Analyze research briefing and draft a thesis with 3-5 target areas for outreach. "
        "Each target area includes rationale, estimated potential, and suggested approach."
    ),
    model="claude-sonnet-4-6",
)
def draft_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Draft outreach strategy with 3-5 target areas",
        "step_plan": (
            "1. Review the research briefing for market landscape and signals\n"
            "2. Identify 3-5 distinct target areas — industry sectors, cohorts, or segments\n"
            "3. For each target area: define scope, rationale, estimated potential, approach\n"
            "4. Rank target areas by impact potential and accessibility\n"
            "5. Provide specific reasoning for why NOW is the right time for each"
        ),
    }
```

- [ ] **Step 3: Create revise_strategy command**

Create `backend/agents/blueprints/sales/workforce/strategist/commands/revise_strategy.py`:

```python
"""Strategist command: revise strategy based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-strategy",
    description=(
        "Revise target area strategy based on QA feedback. Address specific weaknesses "
        "in thesis reasoning, target selection, or market positioning."
    ),
    model="claude-sonnet-4-6",
)
def revise_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Revise target area strategy based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on strategy quality dimension\n"
            "2. Address each specific issue flagged\n"
            "3. Strengthen or replace weak target areas\n"
            "4. Update rationale and potential estimates\n"
            "5. Return revised strategy"
        ),
    }
```

- [ ] **Step 4: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`:

```python
"""Strategist commands registry."""

from .draft_strategy import draft_strategy
from .revise_strategy import revise_strategy

ALL_COMMANDS = [draft_strategy, revise_strategy]
```

- [ ] **Step 5: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/strategist/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import draft_strategy, revise_strategy

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — analyzes research to identify 3-5 high-potential target areas "
        "with thesis, rationale, and approach for each"
    )
    tags = ["strategy", "targeting", "segmentation", "market-positioning"]
    skills = [
        {
            "name": "Target Segmentation",
            "description": (
                "Break a market into actionable target areas — by industry sector, "
                "company cohort, persona type, or mailing list subset"
            ),
        },
        {
            "name": "Competitive Positioning",
            "description": (
                "Analyze where competitors win and lose. Identify positioning gaps "
                "and underserved segments. Frame our strengths against their weaknesses."
            ),
        },
        {
            "name": "Opportunity Scoring",
            "description": (
                "Rank target areas by impact potential, accessibility, timing signals, "
                "and competitive density. Prioritize high-potential, low-competition areas."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist. Given a research briefing about an industry, your job is to identify the 3-5 most promising target areas for outreach and build a thesis for each.

A target area can be:
- An industry sector (e.g. "B2B SaaS companies in logistics")
- A cohort of people (e.g. "CTOs at Series B startups scaling engineering teams")
- A subset of a market (e.g. "European fintechs expanding to US market")
- A specific mailing list or community segment

Your output must follow this structure:

## Strategic Thesis
2-3 sentences: what's the overall outreach angle and why now.

## Target Areas

### Target Area 1: [Name]
- **Scope:** Who exactly is in this segment
- **Size estimate:** Rough number of potential targets
- **Rationale:** Why this segment is promising RIGHT NOW (cite specific signals from research)
- **Competitive density:** How crowded is this space with competing outreach
- **Approach:** What angle/message would resonate with this audience
- **Potential:** High / Medium / Low with justification
- **Timing:** Why now — what trigger event or trend makes this urgent

[Repeat for each target area]

## Priority Ranking
Rank all target areas from highest to lowest impact. Explain the ranking criteria.

## Risks & Assumptions
- What could go wrong with this strategy
- What assumptions need validation
- What information gaps could change the thesis

IMPORTANT: Every target area must be grounded in specific signals from the research briefing. Do not propose generic segments without evidence."""

    draft_strategy = draft_strategy
    revise_strategy = revise_strategy

    def get_task_suffix(self, agent, task):
        return """# STRATEGY METHODOLOGY

## Target Area Quality Criteria
- Each target area must cite at least 2 specific signals from the research briefing
- "Why now" must reference a concrete trigger event, trend, or timing signal
- Size estimates should be grounded (even rough), not hand-waved
- Competitive density assessment should reference actual competitors from the research

## Positioning Framework
- For each target area, answer: where do competitors win, where do they lose?
- Identify positioning gaps — segments competitors ignore or serve poorly
- Frame our strengths against specific competitor weaknesses
- Use "landmine questions" — questions prospects should ask that favor us

## Anti-Patterns to Avoid
- Do not propose more than 5 target areas — focus beats breadth
- Do not propose generic segments like "small businesses" without specificity
- Do not claim "no competition" — there is always competition
- Do not confuse addressable market with total market
- If the research doesn't support a target area, don't force it"""
```

- [ ] **Step 6: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/strategist/__init__.py`:

```python
from .agent import StrategistBlueprint

__all__ = ["StrategistBlueprint"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/strategist/
git commit -m "feat(sales): add strategist agent with draft/revise strategy commands"
```

---

## Task 5: Pitch Architect Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/pitch_architect/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_architect/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_architect/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_architect/commands/design_storyline.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_architect/commands/revise_storyline.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/pitch_architect/commands
```

- [ ] **Step 2: Create design_storyline command**

Create `backend/agents/blueprints/sales/workforce/pitch_architect/commands/design_storyline.py`:

```python
"""Pitch Architect command: design the outreach storyline."""

from agents.blueprints.base import command


@command(
    name="design-storyline",
    description=(
        "Craft the narrative arc for outreach — how we tell our story, why it matters, "
        "why someone would care, and how it avoids feeling like spam."
    ),
    model="claude-sonnet-4-6",
)
def design_storyline(self, agent) -> dict:
    return {
        "exec_summary": "Design the outreach storyline and narrative arc",
        "step_plan": (
            "1. Review research briefing and strategy for context\n"
            "2. Identify the core hook — what trigger event or pain point opens the door\n"
            "3. Design the narrative arc using AIDA structure\n"
            "4. Craft the value proposition framing in prospect terms\n"
            "5. Build objection preemption into the storyline\n"
            "6. Create variations for different target areas"
        ),
    }
```

- [ ] **Step 3: Create revise_storyline command**

Create `backend/agents/blueprints/sales/workforce/pitch_architect/commands/revise_storyline.py`:

```python
"""Pitch Architect command: revise storyline based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-storyline",
    description=(
        "Revise the outreach storyline based on QA feedback. Strengthen hooks, "
        "sharpen value proposition, improve anti-spam qualities."
    ),
    model="claude-sonnet-4-6",
)
def revise_storyline(self, agent) -> dict:
    return {
        "exec_summary": "Revise outreach storyline based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on storyline effectiveness dimension\n"
            "2. Address each specific issue flagged\n"
            "3. Strengthen hooks and value proposition\n"
            "4. Improve anti-spam qualities\n"
            "5. Return revised storyline"
        ),
    }
```

- [ ] **Step 4: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/pitch_architect/commands/__init__.py`:

```python
"""Pitch Architect commands registry."""

from .design_storyline import design_storyline
from .revise_storyline import revise_storyline

ALL_COMMANDS = [design_storyline, revise_storyline]
```

- [ ] **Step 5: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/pitch_architect/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_architect.commands import design_storyline, revise_storyline

logger = logging.getLogger(__name__)


class PitchArchitectBlueprint(WorkforceBlueprint):
    name = "Pitch Architect"
    slug = "pitch_architect"
    description = (
        "Narrative designer — crafts the outreach storyline: how we tell our story, "
        "why it matters, how it avoids feeling like spam"
    )
    tags = ["narrative", "pitch", "storyline", "copywriting", "persuasion"]
    skills = [
        {
            "name": "AIDA Narrative Design",
            "description": (
                "Structure outreach using Attention-Interest-Desire-Action framework. "
                "Each element must earn the next — no skipping to the ask."
            ),
        },
        {
            "name": "Hook Identification",
            "description": (
                "Find the opening that earns attention: trigger events (funding, hiring, launches), "
                "mutual connections, content engagement, company initiatives, role-based pain points"
            ),
        },
        {
            "name": "Anti-Spam Craft",
            "description": (
                "Make outreach feel like a genuine human reaching out, not a template. "
                "Specific details over generic praise, prospect's language over our jargon, "
                "plain text over formatted marketing."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a pitch architect. Your job is to design the narrative arc for outreach campaigns — the storyline that makes someone want to read and respond.

You do NOT write the actual emails. You design the storyline that the Pitch Personalizer will adapt for each individual prospect.

Your output must follow this structure:

## Core Hook
What opens the door? Identify the primary trigger event, pain point, or opportunity that makes prospects receptive RIGHT NOW.

## Narrative Arc (AIDA)

### Attention
How do we earn the first 3 seconds? What specific, verifiable detail shows we did our homework?
- NOT: "I noticed your company is growing" (generic)
- YES: "Your Series B announcement last month and 3 open engineering roles suggest..." (specific)

### Interest
How do we connect their situation to something they care about? Frame in THEIR terms.
- NOT: "We offer a platform that..." (our terms)
- YES: "Teams scaling from 20 to 50 engineers often hit [specific problem]..." (their reality)

### Desire
How do we make the solution feel tangible? Proof points, not promises.
- NOT: "We can help you achieve better results" (vague)
- YES: "[Similar company] reduced their [metric] by [amount] in [timeframe]" (concrete)

### Action
What's the low-friction next step? Match to prospect's likely decision-making style.
- NOT: "Let me know if you'd like to chat" (passive, vague)
- YES: "Worth a 15-min call to see if [specific thing] applies to your situation?" (specific, bounded)

## Objection Preemption
Top 3 objections a prospect might have and how the storyline addresses them WITHOUT being defensive.

## Target Area Variations
For each target area from the strategy, note how the storyline shifts:
- Which hook variation works best
- Which proof points resonate
- What tone adjustments are needed

## Anti-Spam Checklist
- [ ] No generic flattery ("I'm impressed by your work")
- [ ] No fake familiarity ("As a fellow [X]...")
- [ ] No template-obvious phrasing ("I'm reaching out because...")
- [ ] Specific details that prove research was done
- [ ] Value offered before anything is asked
- [ ] Plain text tone — no marketing formatting

IMPORTANT: The storyline must work as plain text email. No HTML, no markdown formatting, no bullet points in the actual outreach. Write like a human, not a marketer."""

    design_storyline = design_storyline
    revise_storyline = revise_storyline

    def get_task_suffix(self, agent, task):
        return """# STORYLINE METHODOLOGY

## Hook Categories (pick the strongest for each target area)
1. **Trigger Event:** Funding round, product launch, acquisition, expansion, leadership change
2. **Mutual Connection:** Shared contact, shared community, shared investor, shared event
3. **Content Engagement:** Their blog post, podcast appearance, conference talk, social post
4. **Company Initiative:** Public strategy shift, new market entry, technology adoption
5. **Role-Based Pain:** Problems specific to their title/function that our offering addresses

## Message Template Awareness
Design the storyline to support these outreach types:
- **Cold:** No prior interaction — hook must work from zero context
- **Warm:** Shared connection or prior engagement — hook references the link
- **Re-engagement:** Previous conversation that went cold — hook references what changed
- **Post-event:** Shared conference/webinar experience — hook references shared moment

## Quality Standards
- Every claim in the storyline must be verifiable
- Proof points must reference real companies/metrics (from the research briefing)
- The storyline should feel like advice from a knowledgeable peer, not a sales pitch
- Subject line alternatives: provide 3 options from specific to intriguing"""
```

- [ ] **Step 6: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/pitch_architect/__init__.py`:

```python
from .agent import PitchArchitectBlueprint

__all__ = ["PitchArchitectBlueprint"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/pitch_architect/
git commit -m "feat(sales): add pitch architect agent with storyline design commands"
```

---

## Task 6: Profile Selector Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/profile_selector/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/profile_selector/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/profile_selector/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/profile_selector/commands/select_profiles.py`
- Create: `backend/agents/blueprints/sales/workforce/profile_selector/commands/revise_profiles.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/profile_selector/commands
```

- [ ] **Step 2: Create select_profiles command**

Create `backend/agents/blueprints/sales/workforce/profile_selector/commands/select_profiles.py`:

```python
"""Profile Selector command: compile outreach target profiles."""

from agents.blueprints.base import command


@command(
    name="select-profiles",
    description=(
        "For each target area from the strategist, compile concrete persons to outreach to. "
        "Research via web search. Output structured profiles with contact details and talking points."
    ),
    model="claude-haiku-4-5",
)
def select_profiles(self, agent) -> dict:
    return {
        "exec_summary": "Compile concrete person profiles for each target area",
        "step_plan": (
            "1. Review target areas from strategist\n"
            "2. For each target area, search for concrete persons matching the segment\n"
            "3. Profile each person: name, role, company, LinkedIn, background, tenure\n"
            "4. Identify talking points and qualification signals per person\n"
            "5. Recommend approach per person: entry point, opening hook, discovery questions\n"
            "6. Group profiles by target area with relevance notes"
        ),
    }
```

- [ ] **Step 3: Create revise_profiles command**

Create `backend/agents/blueprints/sales/workforce/profile_selector/commands/revise_profiles.py`:

```python
"""Profile Selector command: revise profiles based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-profiles",
    description=(
        "Revise profile selection based on QA feedback. Replace weak profiles, "
        "add missing context, improve qualification analysis."
    ),
    model="claude-haiku-4-5",
)
def revise_profiles(self, agent) -> dict:
    return {
        "exec_summary": "Revise profile selection based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on profile accuracy dimension\n"
            "2. Replace or improve flagged profiles\n"
            "3. Add missing context and contact details\n"
            "4. Strengthen qualification signals\n"
            "5. Return revised profiles"
        ),
    }
```

- [ ] **Step 4: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/profile_selector/commands/__init__.py`:

```python
"""Profile Selector commands registry."""

from .revise_profiles import revise_profiles
from .select_profiles import select_profiles

ALL_COMMANDS = [select_profiles, revise_profiles]
```

- [ ] **Step 5: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/profile_selector/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.profile_selector.commands import revise_profiles, select_profiles

logger = logging.getLogger(__name__)


class ProfileSelectorBlueprint(WorkforceBlueprint):
    name = "Profile Selector"
    slug = "profile_selector"
    description = (
        "Prospect profiler — compiles concrete persons to outreach to for each target area "
        "with structured profiles, qualification signals, and talking points"
    )
    tags = ["profiling", "prospecting", "research", "lead-gen", "web-search"]
    default_model = "claude-haiku-4-5"
    skills = [
        {
            "name": "Person Profiling",
            "description": (
                "Build structured profiles: name, role, company, LinkedIn, background, "
                "tenure, email, talking points. Cross-reference multiple sources."
            ),
        },
        {
            "name": "Qualification Signals",
            "description": (
                "Assess each prospect: positive signals (recent activity, engagement), "
                "concerns (role change, company issues), unknowns (data gaps)"
            ),
        },
        {
            "name": "Approach Recommendation",
            "description": (
                "For each person: best entry point, strongest opening hook, "
                "discovery questions to ask, potential objections to prepare for"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a profile selector for sales outreach. Given target areas from the strategist, your job is to find concrete, real persons to reach out to.

Your output must follow this structure, grouped by target area:

## Target Area: [Name]

### Person 1: [Full Name]
| Field | Value |
|-------|-------|
| Name | ... |
| Role / Title | ... |
| Company | ... |
| LinkedIn | URL or "not found" |
| Background | 1-2 sentences on career path |
| Tenure | Time in current role |
| Contact | Email if publicly available, otherwise "research needed" |

**Relevance:** Why this person fits this target area specifically.

**Talking Points:**
- Point 1 based on their recent activity or interests
- Point 2 based on their role challenges
- Point 3 based on company context

**Qualification Signals:**
- Positive: [specific signals]
- Concerns: [specific signals]
- Unknowns: [what we don't know]

**Recommended Approach:**
- Entry point: [how to reach them]
- Opening hook: [what would get their attention]
- Discovery questions: [what to ask to qualify further]

[Repeat for each person, 3-7 persons per target area]

IMPORTANT: These must be real people findable via web search. Do not fabricate profiles. If you cannot find enough real people for a target area, say so and explain what search terms you tried."""

    select_profiles = select_profiles
    revise_profiles = revise_profiles

    def get_task_suffix(self, agent, task):
        return """# PROFILE SELECTION METHODOLOGY

## Person Discovery
- Search LinkedIn, company websites, conference speaker lists, podcast guests, blog authors
- Look for people who are publicly active — they are more likely to engage with outreach
- Prefer decision-makers and influencers over gatekeepers
- Cross-reference to verify current role and company

## Profile Quality Standards
- Every profile must have a verifiable name and current role
- "Not found" is better than fabricated contact info
- Talking points must reference specific, recent activities (not generic role assumptions)
- Qualification signals must cite observable evidence

## Grouping & Relevance
- Group profiles under their target area with explicit relevance notes
- Each person must have a clear reason for being in this specific target area
- Aim for 3-7 persons per target area — quality over quantity
- If a target area yields fewer than 3 real profiles, flag this for the strategist"""
```

- [ ] **Step 6: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/profile_selector/__init__.py`:

```python
from .agent import ProfileSelectorBlueprint

__all__ = ["ProfileSelectorBlueprint"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/profile_selector/
git commit -m "feat(sales): add profile selector agent with select/revise commands"
```

---

## Task 7: Pitch Personalizer Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/revise_pitches.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/pitch_personalizer/commands
```

- [ ] **Step 2: Create personalize_pitches command**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`:

```python
"""Pitch Personalizer command: personalize pitches for each prospect."""

from agents.blueprints.base import command


@command(
    name="personalize-pitches",
    description=(
        "For each prospect profile, research the person, adapt the storyline for them, "
        "and assign the best outreach channel from available agents."
    ),
    model="claude-sonnet-4-6",
)
def personalize_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Personalize pitches for each prospect profile",
        "step_plan": (
            "1. Review the storyline from the pitch architect\n"
            "2. Review the profiles from the profile selector\n"
            "3. For each person: research their recent activity, interests, publications\n"
            "4. Adapt the storyline hook, value proposition, and CTA for this specific person\n"
            "5. Select the best outreach channel from available agents\n"
            "6. Output one structured pitch payload per person"
        ),
    }
```

- [ ] **Step 3: Create revise_pitches command**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/revise_pitches.py`:

```python
"""Pitch Personalizer command: revise pitches based on QA feedback."""

from agents.blueprints.base import command


@command(
    name="revise-pitches",
    description=(
        "Revise personalized pitches based on QA feedback. Deepen personalization, "
        "strengthen hooks, fix any generic or template-obvious elements."
    ),
    model="claude-sonnet-4-6",
)
def revise_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Revise personalized pitches based on QA feedback",
        "step_plan": (
            "1. Review QA feedback on pitch personalization dimension\n"
            "2. Identify which pitches were flagged and why\n"
            "3. Deepen personalization with additional research\n"
            "4. Strengthen hooks and value propositions\n"
            "5. Return revised pitch payloads"
        ),
    }
```

- [ ] **Step 4: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/__init__.py`:

```python
"""Pitch Personalizer commands registry."""

from .personalize_pitches import personalize_pitches
from .revise_pitches import revise_pitches

ALL_COMMANDS = [personalize_pitches, revise_pitches]
```

- [ ] **Step 5: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_personalizer.commands import personalize_pitches, revise_pitches

logger = logging.getLogger(__name__)


class PitchPersonalizerBlueprint(WorkforceBlueprint):
    name = "Pitch Personalizer"
    slug = "pitch_personalizer"
    description = (
        "Personalization specialist — researches each prospect and adapts the storyline "
        "with specific details, assigns outreach channel, produces ready-to-send pitch payloads"
    )
    tags = ["personalization", "outreach", "copywriting", "research", "web-search"]
    skills = [
        {
            "name": "Prospect Research",
            "description": (
                "Research each person's recent activity, interests, publications, "
                "social media presence, conference talks, and professional focus areas"
            ),
        },
        {
            "name": "Storyline Adaptation",
            "description": (
                "Adapt the master storyline for each individual: personalize the hook, "
                "mirror their language, reference their specific situation, adjust tone"
            ),
        },
        {
            "name": "Channel Selection",
            "description": (
                "Select the best outreach channel per person based on their activity patterns "
                "and the available outreach agents in the department"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a pitch personalizer. Given a storyline and prospect profiles, your job is to create individually tailored pitch payloads — one per person — that feel genuinely personal, not templated.

Your output must be a series of structured pitch payloads:

## Pitch for [Person Name] — [Company]

**Target area:** [Which target area this person belongs to]
**Outreach channel:** [email_outreach or other available agent type]

### Research Notes
- Recent activity: [What they've been doing — specific, dated]
- Interests: [What they care about professionally]
- Talking points: [What to reference in the pitch]

### Personalized Pitch
**Subject:** [Specific subject line — not generic]
**Body:**
[The actual pitch text, adapted from the storyline. Plain text. 3-5 short paragraphs max.]

### Personalization Details
- Hook used: [Which hook category and specific detail]
- Specific references: [List each specific detail about this person in the pitch]
- Value framing: [How the value prop is framed in their terms]
- CTA: [The specific ask]

---

RULES:
1. MINIMUM 2 specific, verifiable details per person in the pitch body
2. Never use generic flattery ("I'm impressed by your work at...")
3. Never use template-obvious phrasing ("I'm reaching out because...")
4. Subject lines must be specific to the person, not the campaign
5. Body must be plain text — no markdown, no HTML, no bullet points
6. Mirror the prospect's language from their own content, not our jargon
7. The pitch must feel like it was written by a human who genuinely found this person interesting
8. Each pitch must reference the person's RECENT activity (within last 6 months)"""

    personalize_pitches = personalize_pitches
    revise_pitches = revise_pitches

    def get_task_suffix(self, agent, task):
        return """# PERSONALIZATION METHODOLOGY

## Research Per Person
- Search for their recent LinkedIn posts, blog articles, conference talks, podcast appearances
- Check their company's recent news for relevant context
- Look for mutual connections, shared communities, or shared events
- Note their communication style from public content (formal vs casual, technical vs business)

## Adaptation Rules
- The hook must reference something THEY did or said, not something generic about their company
- The value proposition must be framed in THEIR vocabulary, extracted from THEIR content
- Proof points must be relevant to THEIR specific situation
- The CTA must match THEIR likely decision-making style

## Channel Assignment
- Review the available outreach agents listed in the task context
- Assign each person to the most effective channel based on:
  - Where they are most active (email vs LinkedIn vs Twitter)
  - Channel appropriateness for the relationship level (cold = email, warm = LinkedIn)
  - If only email_outreach is available, assign all to email_outreach

## Quality Checks Before Submitting
- Each pitch has 2+ specific, verifiable person-details? Not just company facts.
- Would the prospect recognize this was written specifically for them?
- Does it pass the "swap test" — would this pitch make NO sense sent to a different person?
- Is the subject line specific enough that it couldn't apply to anyone else?
- Is the body plain text, 3-5 paragraphs, under 200 words?"""
```

- [ ] **Step 6: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/__init__.py`:

```python
from .agent import PitchPersonalizerBlueprint

__all__ = ["PitchPersonalizerBlueprint"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/pitch_personalizer/
git commit -m "feat(sales): add pitch personalizer agent with personalize/revise commands"
```

---

## Task 8: Sales QA Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/sales_qa/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/sales_qa/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/sales_qa/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/sales_qa/commands/review_pipeline.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/sales_qa/commands
```

- [ ] **Step 2: Create review_pipeline command**

Create `backend/agents/blueprints/sales/workforce/sales_qa/commands/review_pipeline.py`:

```python
"""Sales QA command: review entire pipeline output."""

from agents.blueprints.base import command


@command(
    name="review-pipeline",
    description=(
        "Review the entire sales pipeline output end-to-end: research accuracy, "
        "strategy quality, storyline effectiveness, profile accuracy, pitch personalization. "
        "Score each dimension and submit verdict."
    ),
    model="claude-sonnet-4-6",
)
def review_pipeline(self, agent) -> dict:
    return {
        "exec_summary": "Review full sales pipeline output for quality",
        "step_plan": (
            "1. Verify research accuracy — are facts verifiable and current?\n"
            "2. Challenge strategy quality — are target areas well-reasoned?\n"
            "3. Evaluate storyline effectiveness — does it compel without spam?\n"
            "4. Check profile accuracy — are profiles real and relevant?\n"
            "5. Assess pitch personalization — does each pitch feel individual?\n"
            "6. Score each dimension 1.0-10.0, submit verdict"
        ),
    }
```

- [ ] **Step 3: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/sales_qa/commands/__init__.py`:

```python
"""Sales QA commands registry."""

from .review_pipeline import review_pipeline

ALL_COMMANDS = [review_pipeline]
```

- [ ] **Step 4: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/sales_qa/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import EXCELLENCE_THRESHOLD, WorkforceBlueprint
from agents.blueprints.sales.workforce.sales_qa.commands import review_pipeline

logger = logging.getLogger(__name__)


class SalesQaBlueprint(WorkforceBlueprint):
    name = "Sales QA Specialist"
    slug = "sales_qa"
    description = (
        "Quality gate for the sales pipeline — reviews research, strategy, storyline, "
        "profiles, and personalized pitches across 5 dimensions"
    )
    tags = ["review", "quality", "qa", "sales", "verification"]
    essential = True
    review_dimensions = [
        "research_accuracy",
        "strategy_quality",
        "storyline_effectiveness",
        "profile_accuracy",
        "pitch_personalization",
    ]
    skills = [
        {
            "name": "Research Verification",
            "description": (
                "Cross-check research claims against available sources. Flag fabricated "
                "company details, outdated news, or unverifiable qualification signals."
            ),
        },
        {
            "name": "Strategy Challenge",
            "description": (
                "Stress-test target area thesis: is the rationale grounded in evidence? "
                "Are segments genuinely distinct? Is competitive density honestly assessed?"
            ),
        },
        {
            "name": "Anti-Spam Detection",
            "description": (
                "Detect template-obvious phrasing, generic flattery, fake familiarity, "
                "unverifiable claims, and marketing tone in pitch personalization."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are the sales pipeline quality specialist. You review the ENTIRE pipeline output — from research through personalized pitches — and score 5 dimensions.

You are the last line of defense before outreach goes to real people. Be rigorous.

## Scoring Dimensions (1.0-10.0 each, use decimals)

### research_accuracy
- Are company profiles factually verifiable?
- Is the market intelligence current (within 6 months)?
- Are qualification signals grounded in observable evidence?
- Are there any fabricated or unverifiable claims?

### strategy_quality
- Are target areas genuinely distinct and well-scoped?
- Does each target area cite specific evidence from the research?
- Is the "why now" grounded in a real trigger event or trend?
- Is competitive density honestly assessed?

### storyline_effectiveness
- Does the narrative follow AIDA structure coherently?
- Is the hook based on a real trigger event, not generic?
- Does it feel like genuine outreach, not a sales template?
- Would a busy prospect read past the first sentence?

### profile_accuracy
- Are these real, findable people (not fabricated)?
- Are roles and companies current?
- Do talking points reference specific, recent activities?
- Are qualification signals per person grounded in evidence?

### pitch_personalization
- Does each pitch have 2+ specific, verifiable person-details?
- Would the prospect recognize this was written for them specifically?
- Does it pass the "swap test" — would it make NO sense sent to someone else?
- Is it plain text, conversational tone, under 200 words?
- Are subject lines specific to the person, not the campaign?

## Scoring Rules
- Overall score = MINIMUM of all dimension scores
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with specific, actionable feedback per dimension

For CHANGES_REQUESTED, you MUST:
1. List the specific issues per dimension
2. Provide concrete fix suggestions
3. Score each dimension individually so the system knows which agent to route fixes to

After your review, call the submit_verdict tool with your verdict and overall score."""

    review_pipeline = review_pipeline

    def get_task_suffix(self, agent, task):
        return f"""# QA REVIEW METHODOLOGY

## Per-Dimension Review

### research_accuracy
- Cross-reference at least 2 company claims against the research content
- Check dates on news items — anything older than 6 months should be flagged
- Verify that qualification signals cite specific evidence, not generic assumptions
- Flag any claims that look fabricated (perfect data with no gaps is suspicious)

### strategy_quality
- Each target area must cite at least 2 specific signals from the research
- "Why now" must reference a concrete event, not "the market is growing"
- Challenge whether segments are genuinely distinct or just different labels for the same audience
- Check that competitive density is honestly assessed (claims of "no competition" are always wrong)

### storyline_effectiveness
- Read the storyline as if you're the prospect — would you keep reading?
- Check that hooks reference verifiable details, not generic compliments
- Verify AIDA flow: each section must earn the next
- Flag any marketing jargon or template-obvious phrases

### profile_accuracy
- Spot-check 2-3 profiles: do the names, roles, and companies seem real?
- Check that talking points reference specific recent activities, not role assumptions
- Verify that contact information (if provided) seems plausible
- Flag any profiles that look fabricated (too perfect, no gaps)

### pitch_personalization
- Count specific person-details per pitch — minimum 2 required
- Run the "swap test": could this pitch be sent to someone else? If yes, it fails.
- Check that subject lines are person-specific, not campaign-generic
- Verify plain text format: no markdown, no HTML, no bullet points
- Check word count: 3-5 paragraphs, under 200 words

## Verdict Rules
The overall score is the MINIMUM of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with per-dimension feedback

After your review, call the submit_verdict tool with your verdict and overall score."""
```

- [ ] **Step 5: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/sales_qa/__init__.py`:

```python
from .agent import SalesQaBlueprint

__all__ = ["SalesQaBlueprint"]
```

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/sales_qa/
git commit -m "feat(sales): add sales QA agent with 5-dimension pipeline review"
```

---

## Task 9: Email Outreach Agent

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/email_outreach/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/email_outreach/agent.py`
- Create: `backend/agents/blueprints/sales/workforce/email_outreach/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/email_outreach/commands/send_outreach.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/email_outreach/commands
```

- [ ] **Step 2: Create send_outreach command**

Create `backend/agents/blueprints/sales/workforce/email_outreach/commands/send_outreach.py`:

```python
"""Email Outreach command: format and send personalized emails."""

from agents.blueprints.base import command


@command(
    name="send-outreach",
    description=(
        "Take personalized pitch payloads, format as plain text emails, "
        "and send via configured email channel."
    ),
    model="claude-sonnet-4-6",
)
def send_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Format and send personalized outreach emails",
        "step_plan": (
            "1. Review the personalized pitch payloads assigned to email outreach\n"
            "2. Format each pitch as a plain text email with subject line\n"
            "3. Verify all emails follow style guidelines (plain text, no markdown)\n"
            "4. Send each email via configured channel\n"
            "5. Log what was sent to whom with timestamps"
        ),
    }
```

- [ ] **Step 3: Create commands __init__**

Create `backend/agents/blueprints/sales/workforce/email_outreach/commands/__init__.py`:

```python
"""Email Outreach commands registry."""

from .send_outreach import send_outreach

ALL_COMMANDS = [send_outreach]
```

- [ ] **Step 4: Create agent blueprint**

Create `backend/agents/blueprints/sales/workforce/email_outreach/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.email_outreach.commands import send_outreach

logger = logging.getLogger(__name__)


class EmailOutreachBlueprint(WorkforceBlueprint):
    name = "Email Outreach"
    slug = "email_outreach"
    description = (
        "Email delivery specialist — formats personalized pitch payloads as plain text emails "
        "and sends via configured email channel"
    )
    tags = ["outreach", "email", "delivery", "sending"]
    skills = [
        {
            "name": "Email Formatting",
            "description": (
                "Format pitch payloads as professional plain text emails. "
                "No HTML, no markdown, no formatting — just clean text that looks human-written."
            ),
        },
        {
            "name": "Delivery Management",
            "description": (
                "Send emails via configured channel, log delivery status, "
                "handle errors gracefully, report what was sent to whom."
            ),
        },
    ]
    config_schema = {
        "sender_name": {
            "type": "str",
            "description": "Name to display as email sender",
            "label": "Sender Name",
        },
        "sender_title": {
            "type": "str",
            "description": "Title/role for email signature",
            "label": "Sender Title",
        },
    }

    @property
    def system_prompt(self) -> str:
        return """You are an email outreach delivery agent. You take personalized pitch payloads and send them as emails.

Your job is formatting and delivery — the pitch content has already been written and QA-approved. Do NOT rewrite the pitches. Format them as clean plain text emails and send.

## Email Format Rules
- Plain text ONLY — no HTML, no markdown, no bullet points, no bold/italic
- Subject line: use the one from the pitch payload exactly
- Body: the pitch text, followed by a simple signature
- Signature: [sender_name] / [sender_title] (from your config)
- No images, no links (unless specifically in the pitch payload), no tracking pixels
- Line length: wrap at 72 characters for readability

## Sending Rules
- Send one email at a time, not bulk
- Log each send: recipient, subject, timestamp, status
- If sending fails, log the error and continue with remaining emails
- Never modify the pitch content — you are a delivery agent, not an editor

## Report Format
After sending, produce a delivery report:

| Recipient | Subject | Status | Timestamp |
|-----------|---------|--------|-----------|
| name@email | Subject line | sent/failed | ISO timestamp |

Total: X sent, Y failed

If any sends failed, include error details."""

    send_outreach = send_outreach

    def get_task_suffix(self, agent, task):
        return """# EMAIL DELIVERY METHODOLOGY

## Pre-Send Checklist
- Verify each pitch payload has: recipient name, email, subject, body
- Verify subject line is person-specific (not a generic campaign subject)
- Verify body is plain text (no markdown artifacts like ** or ## or - bullets)
- Verify body is under 200 words
- Verify signature is properly formatted

## Sending
- Use the configured email channel (Gmail API, SendGrid, etc.)
- Send one at a time with a brief pause between sends
- Capture delivery status for each email

## Post-Send
- Produce the delivery report table
- Flag any emails that bounced or failed
- Note any recipients where email address was missing or invalid"""
```

- [ ] **Step 5: Create package __init__**

Create `backend/agents/blueprints/sales/workforce/email_outreach/__init__.py`:

```python
from .agent import EmailOutreachBlueprint

__all__ = ["EmailOutreachBlueprint"]
```

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/email_outreach/
git commit -m "feat(sales): add email outreach agent with send command"
```

---

## Task 10: Sales Leader — Pipeline State Machine

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/__init__.py`
- Rewrite: `backend/agents/blueprints/sales/leader/agent.py`

This is the core orchestration logic — the leader's `generate_task_proposal` with the pipeline state machine and QA cascade fix routing.

- [ ] **Step 1: Rewrite the leader agent**

Rewrite `backend/agents/blueprints/sales/leader/agent.py`:

```python
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import (
    EXCELLENCE_THRESHOLD,
    NEAR_EXCELLENCE_THRESHOLD,
    LeaderBlueprint,
)

logger = logging.getLogger(__name__)

# ── Pipeline definition ────────────────────────────────────────────────────

PIPELINE_STEPS = [
    "research",
    "strategy",
    "pitch_design",
    "profile_selection",
    "personalization",
    "qa_review",
    "dispatch",
]

STEP_TO_AGENT = {
    "research": "researcher",
    "strategy": "strategist",
    "pitch_design": "pitch_architect",
    "profile_selection": "profile_selector",
    "personalization": "pitch_personalizer",
    "qa_review": "sales_qa",
    "dispatch": None,  # dispatches to all outreach agents
}

STEP_TO_COMMAND = {
    "research": "research-industry",
    "strategy": "draft-strategy",
    "pitch_design": "design-storyline",
    "profile_selection": "select-profiles",
    "personalization": "personalize-pitches",
    "qa_review": "review-pipeline",
    "dispatch": "send-outreach",
}

# Maps QA dimensions to agent types for cascade fix routing
DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "pitch_architect",
    "profile_accuracy": "profile_selector",
    "pitch_personalization": "pitch_personalizer",
}

# Revision commands per agent (used when QA routes fixes)
AGENT_FIX_COMMANDS = {
    "researcher": "research-industry",
    "strategist": "revise-strategy",
    "pitch_architect": "revise-storyline",
    "profile_selector": "revise-profiles",
    "pitch_personalizer": "revise-pitches",
}

CHAIN_ORDER = [
    "researcher",
    "strategist",
    "pitch_architect",
    "profile_selector",
    "pitch_personalizer",
]

# Context injection: which prior steps feed into each step
STEP_CONTEXT_SOURCES = {
    "research": [],
    "strategy": ["research"],
    "pitch_design": ["research", "strategy"],
    "profile_selection": ["strategy"],
    "personalization": ["pitch_design", "profile_selection"],
    "qa_review": ["research", "strategy", "pitch_design", "profile_selection", "personalization"],
    "dispatch": ["personalization"],
}


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Head of Sales"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates a 7-agent pipeline from industry research "
        "through personalized outreach with QA feedback loop"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "orchestration"]
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the sequential sales pipeline: research → strategy → pitch design → "
                "profile selection → personalization → QA → outreach dispatch"
            ),
        },
        {
            "name": "QA Cascade Routing",
            "description": (
                "Route QA failures to the earliest failing agent in the chain. "
                "Re-run from that point forward, not just the last step."
            ),
        },
        {
            "name": "Outreach Discovery",
            "description": (
                "Discover available outreach channels by querying agents with outreach=True. "
                "Pass channel list to personalizer for assignment."
            ),
        },
    ]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
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
            },
        ]

    @property
    def system_prompt(self) -> str:
        return """You are the Head of Sales. You orchestrate a pipeline of specialized agents to produce personalized outreach campaigns.

YOUR PIPELINE (sequential — each step feeds the next):
1. researcher: Industry research, competitive intel, market trends (web search, cheap model)
2. strategist: Draft thesis with 3-5 target areas based on research
3. pitch_architect: Design the outreach storyline and narrative arc
4. profile_selector: Compile concrete persons to outreach to per target area (web search)
5. pitch_personalizer: Personalize the storyline for each person, assign outreach channel
6. sales_qa: Multi-dimensional quality review of the entire pipeline
7. Outreach dispatch: Send approved pitches via available outreach agents

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
When the pitch_personalizer completes, the system automatically routes to sales_qa.
- Score >= 9.5/10 → approved, dispatch to outreach
- Score >= 9.0 after 3 polish attempts → accept (diminishing returns)
- Score < threshold → system routes fix to the earliest failing agent in the chain
Do NOT manually create review tasks — the system handles the loop.

OUTREACH DISCOVERY:
Query your department for agents with outreach=True to discover available channels.
Pass the list to the pitch_personalizer so it can assign channels per person.

You don't write pitches or do research directly — you create tasks for your workforce."""

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
        # 1. Check for review cycle triggers first (base class handles QA ping-pong)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result

        # 2. Find the active sprint
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        department = agent.department
        running_sprints = list(
            Sprint.objects.filter(
                departments=department,
                status=Sprint.Status.RUNNING,
            )
            .prefetch_related("sources")
            .order_by("updated_at")
        )
        if not running_sprints:
            return None

        sprint = running_sprints[0]
        sprint_id = str(sprint.id)

        # 3. Determine current pipeline step
        internal_state = agent.internal_state or {}
        pipeline_steps = internal_state.get("pipeline_steps", {})
        current_step = pipeline_steps.get(sprint_id, None)

        if current_step is None:
            # Fresh sprint — start at research
            current_step = "research"
            pipeline_steps[sprint_id] = current_step
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

        # 4. Check if current step is done
        step_agent_type = STEP_TO_AGENT.get(current_step)
        step_command = STEP_TO_COMMAND.get(current_step)

        if current_step == "dispatch":
            # Check if all outreach tasks for this sprint are done
            outreach_agents = list(
                department.agents.filter(outreach=True, status=AgentModel.Status.ACTIVE)
            )
            if not outreach_agents:
                logger.warning("SALES_NO_OUTREACH dept=%s — no outreach agents available", department.name)
                return None

            outreach_tasks = AgentTask.objects.filter(
                sprint=sprint,
                agent__in=outreach_agents,
                command_name="send-outreach",
            )
            pending = outreach_tasks.exclude(status=AgentTask.Status.DONE)
            if outreach_tasks.exists() and not pending.exists():
                # All dispatched — write output and mark sprint done
                self._write_sprint_output(agent, sprint)
                sprint.status = Sprint.Status.DONE
                sprint.completion_summary = "Sales pipeline complete — outreach dispatched."
                sprint.completed_at = timezone.now()
                sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

                from projects.views.sprint_view import _broadcast_sprint

                _broadcast_sprint(sprint, "sprint.updated")
                logger.info("SALES_SPRINT_DONE dept=%s sprint=%s", department.name, sprint.text[:60])

                # Clean up pipeline state
                pipeline_steps.pop(sprint_id, None)
                internal_state["pipeline_steps"] = pipeline_steps
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])
                return None

            if not outreach_tasks.exists():
                # Need to dispatch — propose outreach tasks
                return self._propose_dispatch_tasks(agent, sprint, outreach_agents)

            # Some still running — wait
            return None

        # For non-dispatch steps, check if the step's task is done
        if step_agent_type:
            step_done = AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=step_agent_type,
                agent__department=department,
                command_name=step_command,
                status=AgentTask.Status.DONE,
            ).exists()

            if not step_done:
                # Check if task is already in progress or queued
                step_active = AgentTask.objects.filter(
                    sprint=sprint,
                    agent__agent_type=step_agent_type,
                    agent__department=department,
                    command_name=step_command,
                    status__in=[
                        AgentTask.Status.PROCESSING,
                        AgentTask.Status.QUEUED,
                        AgentTask.Status.AWAITING_APPROVAL,
                        AgentTask.Status.PLANNED,
                    ],
                ).exists()

                if step_active:
                    return None  # Wait for it

                # Propose this step's task
                return self._propose_step_task(agent, sprint, current_step)

            # Step is done — persist document if applicable, then advance
            self._persist_step_document(agent, sprint, current_step)

            step_idx = PIPELINE_STEPS.index(current_step)
            if step_idx + 1 < len(PIPELINE_STEPS):
                next_step = PIPELINE_STEPS[step_idx + 1]
                pipeline_steps[sprint_id] = next_step
                internal_state["pipeline_steps"] = pipeline_steps
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])

                if next_step == "dispatch":
                    outreach_agents = list(
                        department.agents.filter(outreach=True, status=AgentModel.Status.ACTIVE)
                    )
                    if outreach_agents:
                        return self._propose_dispatch_tasks(agent, sprint, outreach_agents)
                    logger.warning("SALES_NO_OUTREACH dept=%s", department.name)
                    return None

                return self._propose_step_task(agent, sprint, next_step)

        return None

    def _propose_step_task(self, agent: Agent, sprint, step: str) -> dict:
        """Propose a task for a specific pipeline step, injecting context from prior steps."""
        from agents.models import AgentTask

        agent_type = STEP_TO_AGENT[step]
        command_name = STEP_TO_COMMAND[step]

        # Gather context from prior steps
        context_parts = []
        source_steps = STEP_CONTEXT_SOURCES.get(step, [])
        for src_step in source_steps:
            src_agent_type = STEP_TO_AGENT[src_step]
            src_task = (
                AgentTask.objects.filter(
                    sprint=sprint,
                    agent__agent_type=src_agent_type,
                    agent__department=agent.department,
                    status=AgentTask.Status.DONE,
                )
                .order_by("-completed_at")
                .first()
            )
            if src_task and src_task.report:
                step_label = src_step.replace("_", " ").title()
                context_parts.append(f"## {step_label} Output\n{src_task.report}")

        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        # For personalization step, inject outreach agents list
        extra_context = ""
        if step == "personalization":
            outreach_agents = list(
                agent.department.agents.filter(
                    outreach=True, status="active"
                ).values_list("agent_type", "name")
            )
            if outreach_agents:
                agents_list = ", ".join(f"{name} ({atype})" for atype, name in outreach_agents)
                extra_context = f"\n\n## Available Outreach Channels\nAssign each pitch to one of: {agents_list}"

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}"
            f"{extra_context}\n\n"
            f"Execute your command based on the above context."
        )

        return {
            "exec_summary": f"Sales pipeline step: {step.replace('_', ' ')}",
            "_sprint_id": str(sprint.id),
            "tasks": [
                {
                    "target_agent_type": agent_type,
                    "command_name": command_name,
                    "exec_summary": f"Sales pipeline — {step.replace('_', ' ')}",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                },
            ],
        }

    def _propose_dispatch_tasks(self, agent: Agent, sprint, outreach_agents) -> dict:
        """Propose outreach tasks — one per outreach agent with assigned pitches."""
        from agents.models import AgentTask

        # Get the personalizer's output
        personalizer_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="pitch_personalizer",
                agent__department=agent.department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        pitch_output = personalizer_task.report if personalizer_task else "No pitch payloads available."

        tasks = []
        for outreach_agent in outreach_agents:
            tasks.append(
                {
                    "target_agent_type": outreach_agent.agent_type,
                    "command_name": "send-outreach",
                    "exec_summary": f"Send outreach emails via {outreach_agent.name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Approved Pitch Payloads\n{pitch_output}\n\n"
                        f"Send all pitches assigned to your channel ({outreach_agent.agent_type})."
                    ),
                    "depends_on_previous": False,
                }
            )

        return {
            "exec_summary": "Dispatch approved pitches to outreach agents",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _propose_fix_task(
        self, agent: Agent, review_task: AgentTask, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """Override: route QA fixes to the earliest failing agent in the chain.

        Instead of always looping back to pitch_personalizer (the declared "creator"),
        parse per-dimension scores from the QA report and find the earliest failing agent.
        """
        report = review_task.report or ""

        # Try to extract per-dimension scores from the review report
        earliest_failing = self._find_earliest_failing_agent(report, score)

        if earliest_failing is None:
            # Fallback: route to pitch_personalizer (the declared creator)
            earliest_failing = "pitch_personalizer"

        fix_command = AGENT_FIX_COMMANDS.get(earliest_failing, "revise-pitches")
        polish_msg = (
            f" (polish {polish_count}/{3})"
            if score >= NEAR_EXCELLENCE_THRESHOLD
            else ""
        )

        return {
            "exec_summary": (
                f"Fix {earliest_failing.replace('_', ' ')} issues "
                f"(score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}"
            ),
            "tasks": [
                {
                    "target_agent_type": earliest_failing,
                    "command_name": fix_command,
                    "exec_summary": (
                        f"Fix QA issues — {earliest_failing.replace('_', ' ')} "
                        f"(score {score}/10)"
                    ),
                    "step_plan": (
                        f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                        f"Review round: {round_num}. Polish attempts: {polish_count}/3.\n\n"
                        f"The QA specialist has flagged issues. Fix the problems below.\n\n"
                        f"## QA Report\n{report}\n\n"
                        f"Address the issues in your area. After fixing, the pipeline "
                        f"continues from your output forward."
                    ),
                    "depends_on_previous": False,
                },
            ],
        }

    def _find_earliest_failing_agent(self, report: str, overall_score: float) -> str | None:
        """Parse QA report for per-dimension scores, return earliest failing agent."""
        failing_agents = []

        for dimension, agent_type in DIMENSION_TO_AGENT.items():
            # Try to find score patterns like "research_accuracy: 7.5" or "research_accuracy — 7.5/10"
            patterns = [
                rf"{dimension}[:\s—\-]+(\d+\.?\d*)\s*/?\s*10?",
                rf"{dimension}.*?(\d+\.?\d*)/10",
                rf"{dimension}.*?score[:\s]+(\d+\.?\d*)",
            ]
            for pattern in patterns:
                match = re.search(pattern, report, re.IGNORECASE)
                if match:
                    dim_score = float(match.group(1))
                    if dim_score < EXCELLENCE_THRESHOLD:
                        failing_agents.append(agent_type)
                    break

        if not failing_agents:
            return None

        # Return the earliest in chain order
        for agent_type in CHAIN_ORDER:
            if agent_type in failing_agents:
                return agent_type

        return failing_agents[0]

    def _persist_step_document(self, agent: Agent, sprint, step: str) -> None:
        """Persist research and strategy outputs as Department Documents."""
        from agents.models import AgentTask
        from projects.models import Document

        doc_types = {
            "research": (Document.DocType.RESEARCH, "Industry Research Briefing"),
            "strategy": (Document.DocType.STRATEGY, "Target Area Strategy"),
        }
        if step not in doc_types:
            return

        doc_type, title_prefix = doc_types[step]
        agent_type = STEP_TO_AGENT[step]

        task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=agent_type,
                agent__department=agent.department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if not task or not task.report:
            return

        # Update existing or create new
        existing = Document.objects.filter(
            department=agent.department,
            doc_type=doc_type,
            sprint=sprint,
        ).first()

        if existing:
            existing.content = task.report
            existing.save(update_fields=["content", "updated_at"])
        else:
            Document.objects.create(
                title=f"{title_prefix} — {sprint.text[:50]}",
                content=task.report,
                department=agent.department,
                doc_type=doc_type,
                sprint=sprint,
            )

    def _write_sprint_output(self, agent: Agent, sprint) -> None:
        """Write the sprint Output when outreach dispatch completes."""
        from agents.models import AgentTask
        from projects.models import Output

        # Check if output already exists
        if Output.objects.filter(sprint=sprint, department=agent.department).exists():
            return

        # Gather summary from outreach task reports
        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__department=agent.department,
            agent__outreach=True,
            status=AgentTask.Status.DONE,
        )

        report_parts = ["# Sales Outreach — Sprint Output\n"]
        for task in outreach_tasks:
            report_parts.append(f"## {task.agent.name}\n{task.report or 'No report.'}\n")

        Output.objects.create(
            sprint=sprint,
            department=agent.department,
            title=f"Sales Outreach — {sprint.text[:80]}",
            label="outreach",
            output_type=Output.OutputType.MARKDOWN,
            content="\n".join(report_parts),
        )
```

- [ ] **Step 2: Update leader __init__**

The `backend/agents/blueprints/sales/leader/__init__.py` already exports `SalesLeaderBlueprint` and should still work. Verify it contains:

```python
from .agent import SalesLeaderBlueprint

__all__ = ["SalesLeaderBlueprint"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/sales/leader/
git commit -m "feat(sales): rewrite leader with pipeline state machine and QA cascade routing"
```

---

## Task 11: Update Blueprint Registry

**Files:**
- Modify: `backend/agents/blueprints/__init__.py:116-145` (sales section)

- [ ] **Step 1: Replace the sales registration block**

In `backend/agents/blueprints/__init__.py`, replace the entire `# ── Sales ──` section (lines 116-145) with:

```python
# ── Sales ───────────────────────────────────────────────────────────────────

try:
    from agents.blueprints.sales.leader import SalesLeaderBlueprint
except ImportError:
    SalesLeaderBlueprint = None

_sales_workforce = {}
_sales_imports = {
    "researcher": ("agents.blueprints.sales.workforce.researcher", "ResearcherBlueprint"),
    "strategist": ("agents.blueprints.sales.workforce.strategist", "StrategistBlueprint"),
    "pitch_architect": ("agents.blueprints.sales.workforce.pitch_architect", "PitchArchitectBlueprint"),
    "profile_selector": ("agents.blueprints.sales.workforce.profile_selector", "ProfileSelectorBlueprint"),
    "pitch_personalizer": ("agents.blueprints.sales.workforce.pitch_personalizer", "PitchPersonalizerBlueprint"),
    "sales_qa": ("agents.blueprints.sales.workforce.sales_qa", "SalesQaBlueprint"),
    "email_outreach": ("agents.blueprints.sales.workforce.email_outreach", "EmailOutreachBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _sales_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _sales_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if SalesLeaderBlueprint is not None:
    _sales_leader = SalesLeaderBlueprint()
    DEPARTMENTS["sales"] = {
        "name": "Sales",
        "description": (
            "Outbound sales pipeline — industry research, target strategy, pitch design, "
            "prospect profiling, personalized outreach with QA review loops"
        ),
        "leader": _sales_leader,
        "workforce": _sales_workforce,
        "config_schema": _sales_leader.config_schema,
    }
```

- [ ] **Step 2: Verify imports load**

Run: `cd backend && python -c "from agents.blueprints import DEPARTMENTS; print(list(DEPARTMENTS['sales']['workforce'].keys()))"`

Expected: `['researcher', 'strategist', 'pitch_architect', 'profile_selector', 'pitch_personalizer', 'sales_qa', 'email_outreach']`

- [ ] **Step 3: Commit**

```bash
git add backend/agents/blueprints/__init__.py
git commit -m "feat(sales): update blueprint registry with new 7-agent sales workforce"
```

---

## Task 12: Smoke Test — Full Import Chain

Verify the entire department loads without errors.

- [ ] **Step 1: Test full import and blueprint resolution**

Run:
```bash
cd backend && python -c "
from agents.blueprints import DEPARTMENTS, get_blueprint

dept = DEPARTMENTS['sales']
print(f'Leader: {dept[\"leader\"].name}')
print(f'Workforce: {len(dept[\"workforce\"])} agents')
for slug, bp in dept['workforce'].items():
    print(f'  {slug}: {bp.name} (model={bp.default_model})')
    cmds = bp.get_commands()
    print(f'    commands: {[c[\"name\"] for c in cmds]}')
    if hasattr(bp, 'review_dimensions') and bp.review_dimensions:
        print(f'    review_dimensions: {bp.review_dimensions}')

# Test review pairs
leader = dept['leader']
pairs = leader.get_review_pairs()
print(f'Review pairs: {len(pairs)}')
for p in pairs:
    print(f'  {p[\"creator\"]} -> {p[\"reviewer\"]} (dims: {p[\"dimensions\"]})')
"
```

Expected output:
```
Leader: Head of Sales
Workforce: 7 agents
  researcher: Sales Researcher (model=claude-haiku-4-5)
    commands: ['research-industry']
  strategist: Sales Strategist (model=claude-sonnet-4-6)
    commands: ['draft-strategy', 'revise-strategy']
  pitch_architect: Pitch Architect (model=claude-sonnet-4-6)
    commands: ['design-storyline', 'revise-storyline']
  profile_selector: Profile Selector (model=claude-haiku-4-5)
    commands: ['select-profiles', 'revise-profiles']
  pitch_personalizer: Pitch Personalizer (model=claude-sonnet-4-6)
    commands: ['personalize-pitches', 'revise-pitches']
  sales_qa: Sales QA Specialist (model=claude-sonnet-4-6)
    commands: ['review-pipeline']
    review_dimensions: ['research_accuracy', 'strategy_quality', 'storyline_effectiveness', 'profile_accuracy', 'pitch_personalization']
  email_outreach: Email Outreach (model=claude-sonnet-4-6)
    commands: ['send-outreach']
Review pairs: 1
  pitch_personalizer -> sales_qa (dims: ['research_accuracy', 'strategy_quality', 'storyline_effectiveness', 'profile_accuracy', 'pitch_personalization'])
```

- [ ] **Step 2: Test leader state machine constants are consistent**

Run:
```bash
cd backend && python -c "
from agents.blueprints.sales.leader.agent import (
    PIPELINE_STEPS, STEP_TO_AGENT, STEP_TO_COMMAND,
    DIMENSION_TO_AGENT, AGENT_FIX_COMMANDS, CHAIN_ORDER,
    STEP_CONTEXT_SOURCES,
)

# Verify all steps have agent and command mappings
for step in PIPELINE_STEPS:
    assert step in STEP_TO_AGENT, f'Missing STEP_TO_AGENT for {step}'
    assert step in STEP_TO_COMMAND, f'Missing STEP_TO_COMMAND for {step}'
    assert step in STEP_CONTEXT_SOURCES, f'Missing STEP_CONTEXT_SOURCES for {step}'

# Verify all dimensions map to agents in CHAIN_ORDER
for dim, agent_type in DIMENSION_TO_AGENT.items():
    assert agent_type in CHAIN_ORDER, f'{agent_type} not in CHAIN_ORDER'
    assert agent_type in AGENT_FIX_COMMANDS, f'{agent_type} not in AGENT_FIX_COMMANDS'

print('All constants consistent.')
"
```

Expected: `All constants consistent.`

- [ ] **Step 3: Commit (if any fixes were needed)**

```bash
git add backend/agents/blueprints/sales/
git commit -m "fix(sales): address any issues found in smoke test"
```

---

## Summary

| Task | What | Scope |
|------|------|-------|
| 1 | Add `outreach` field to Agent model | **Outside sales folder** (only base change) |
| 2 | Delete old workforce agents | sales/ cleanup |
| 3 | Researcher agent | sales/workforce/researcher/ |
| 4 | Strategist agent | sales/workforce/strategist/ |
| 5 | Pitch Architect agent | sales/workforce/pitch_architect/ |
| 6 | Profile Selector agent | sales/workforce/profile_selector/ |
| 7 | Pitch Personalizer agent | sales/workforce/pitch_personalizer/ |
| 8 | Sales QA agent | sales/workforce/sales_qa/ |
| 9 | Email Outreach agent | sales/workforce/email_outreach/ |
| 10 | Leader state machine | sales/leader/ |
| 11 | Blueprint registry update | blueprints/__init__.py |
| 12 | Smoke test | Verification |

Tasks 3-9 are independent and can be parallelized. Task 10 depends on tasks 3-9 (needs agent imports). Task 11 depends on all prior tasks. Task 12 is final verification.

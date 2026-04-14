# Sales Pipeline Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the sales department pipeline from market-analysis-first to multiplier-focused prospect-discovery-first architecture.

**Architecture:** Replace 6-step pipeline (research → strategy → personalization(×N) → finalize → qa_review → dispatch) with 7-step pipeline (ideation → discovery(×N) → prospect_gate → copywriting(×N) → copy_gate → qa_review → dispatch). Fan-out moves to researcher level. Two authenticity gates verify prospect data and pitch quality independently.

**Tech Stack:** Django, Python 3.12, pytest, Anthropic Claude API (sonnet)

**Spec:** `backend/docs/superpowers/specs/2026-04-14-sales-pipeline-restructure-design.md`

---

### Task 1: Strategist — New `identify-targets` Command + Agent Rewrite

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/strategist/commands/identify_targets.py`
- Modify: `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`
- Modify: `backend/agents/blueprints/sales/workforce/strategist/agent.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestStrategistRestructured:
    def test_has_identify_targets_command(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "identify-targets" in commands

    def test_no_old_commands(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "draft-strategy" not in commands
        assert "revise-strategy" not in commands
        assert "finalize-outreach" not in commands

    def test_system_prompt_mentions_multiplier(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        assert "multiplier" in bp.system_prompt.lower()

    def test_system_prompt_no_aida(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        assert "AIDA" not in bp.system_prompt

    def test_identify_targets_uses_sonnet(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        commands = bp.get_commands()
        cmd = next(c for c in commands if c["name"] == "identify-targets")
        assert cmd["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestStrategistRestructured -v`
Expected: FAIL — class/command doesn't exist yet

- [ ] **Step 3: Create `identify_targets.py` command**

Create `backend/agents/blueprints/sales/workforce/strategist/commands/identify_targets.py`:

```python
"""Strategist command: identify multiplier target areas."""

from agents.blueprints.base import command


@command(
    name="identify-targets",
    description=(
        "Identify 3-5 multiplier target areas for outreach. Each area targets "
        "organizations or influential individuals who control many bookings, "
        "not individual customers."
    ),
    model="claude-sonnet-4-6",
    max_tokens=4096,
)
def identify_targets(self, agent) -> dict:
    return {
        "exec_summary": "Identify multiplier target areas for outreach campaign",
        "step_plan": (
            "1. Read the sprint instruction and project goal\n"
            "2. Identify 3-5 target areas focused on MULTIPLIER relationships:\n"
            "   - Tier 1: Organizations (accelerators, VC firms, corporate programs) — one deal = many bookings\n"
            "   - Tier 2: Influential individuals (community leaders, event organizers) — one relationship = referral stream\n"
            "3. For each area: define scope, decision-maker profile, messaging angle, timing signal\n"
            "4. Use numbered headers (### Target Area 1, etc.) for system parsing\n"
            "5. Keep each area to ~300-500 words. Total output ~3K max."
        ),
    }
```

- [ ] **Step 4: Rewrite strategist agent**

Replace contents of `backend/agents/blueprints/sales/workforce/strategist/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import identify_targets

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — identifies high-potential multiplier target areas "
        "for B2B partnership outreach. Focuses on organizations and gatekeepers "
        "who control many bookings, not individual customers."
    )
    tags = ["strategy", "targeting", "segmentation", "market-positioning", "multiplier"]
    skills = [
        {
            "name": "Target Segmentation",
            "description": (
                "Break a market into actionable multiplier target areas — by organization type, "
                "gatekeeper role, or community influence tier"
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
                "Rank target areas by multiplier potential, accessibility, timing signals, "
                "and competitive density. Prioritize high-leverage relationships."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist specializing in multiplier relationships. You identify target areas where ONE conversion yields MANY bookings.

## Core Principle: Multiplier Focus

You target gatekeepers and organizations, NOT individual customers:
- Tier 1 — Organizations: Accelerators, VC firms, corporate relocation services, conference organizers. One deal = 10-50+ recurring bookings.
- Tier 2 — Influential Individuals: Community leaders, event organizers, newsletter writers. One relationship = steady referral stream.

Individual customer acquisition is marketing's job. Your job is B2B partnership development.

## Output Structure

### Strategic Thesis
2-3 sentences: the overall outreach angle and why now.

### Target Area [N]: [Name]
For each area (use numbered headers for parsing):
- **Tier:** 1 or 2
- **Scope:** Who exactly — org type, role type, geography
- **Why multiplier:** How one conversion yields many bookings (estimated multiplier: Nx)
- **Decision-maker profile:** Who at these orgs controls the decision (title, function)
- **Messaging angle:** 2-3 sentences — the core "why should they care" hook
- **Timing signal:** What's happening NOW that creates urgency (or "evergreen" if none)

Keep each area to ~300-500 words. Be specific and actionable. The researcher will use your decision-maker profiles as search targets."""

    identify_targets = identify_targets

    def get_task_suffix(self, agent, task):
        max_areas = agent.get_config_value("max_target_areas", 5)
        return f"""# STRATEGY METHODOLOGY

## Multiplier Quality Criteria
- Every target area must identify a MULTIPLIER — one conversion = many bookings
- Individual founder outreach is NOT a valid target area (that's marketing)
- Each area must specify the decision-maker ROLE, not just the org type
- "Why multiplier" must include a concrete booking estimate (e.g., "10-30 rooms per cohort")

## Target Area Requirements
- Produce EXACTLY {max_areas} target areas — no more, no fewer
- Each area must cite at least 1 timing signal or mark as "evergreen"
- Messaging angle must be 2-3 sentences max — the copywriter handles the rest
- Decision-maker profile must be specific enough for a web search (title + org type)

## What NOT To Do
- Do NOT write AIDA frameworks or narrative arcs — the copywriter owns messaging
- Do NOT write anti-spam guidance — the copywriter has its own
- Do NOT do competitive analysis beyond positioning gaps
- Do NOT estimate addressable market size — focus on multiplier potential
- Keep total output under 3,000 words"""
```

- [ ] **Step 5: Update strategist commands `__init__.py`**

Replace contents of `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`:

```python
"""Strategist commands registry."""

from .identify_targets import identify_targets

ALL_COMMANDS = [identify_targets]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestStrategistRestructured -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/workforce/strategist/
git add agents/tests/test_sales_department.py
git commit -m "feat(sales): rewrite strategist for multiplier target identification"
```

---

### Task 2: Researcher — New `discover-prospects` Command + Agent Rewrite

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/researcher/commands/discover_prospects.py`
- Modify: `backend/agents/blueprints/sales/workforce/researcher/commands/__init__.py`
- Modify: `backend/agents/blueprints/sales/workforce/researcher/agent.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestResearcherRestructured:
    def test_has_discover_prospects_command(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "discover-prospects" in commands

    def test_no_old_commands(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "research-industry" not in commands

    def test_system_prompt_mentions_prospect_discovery(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        assert "prospect" in bp.system_prompt.lower()

    def test_system_prompt_no_market_intel(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        assert "market size" not in bp.system_prompt.lower()

    def test_discover_prospects_uses_sonnet(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        commands = bp.get_commands()
        cmd = next(c for c in commands if c["name"] == "discover-prospects")
        assert cmd["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestResearcherRestructured -v`
Expected: FAIL

- [ ] **Step 3: Create `discover_prospects.py` command**

Create `backend/agents/blueprints/sales/workforce/researcher/commands/discover_prospects.py`:

```python
"""Researcher command: discover real prospects via web search for one target area."""

from agents.blueprints.base import command


@command(
    name="discover-prospects",
    description=(
        "For one target area: search the web for real decision-makers at multiplier "
        "organizations. Verify each person's identity and current role. "
        "Output a structured prospect list, not market analysis."
    ),
    model="claude-sonnet-4-6",
)
def discover_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Discover verified prospects for target area via web search",
        "step_plan": (
            "1. Read the target area brief — focus on the decision-maker profile\n"
            "2. Search for real people matching that profile via web search\n"
            "3. For each person found: verify identity, current role, and organization\n"
            "4. Assess multiplier potential — can this person/org send multiple bookings?\n"
            "5. Output structured prospect list with verification sources"
        ),
    }
```

- [ ] **Step 4: Rewrite researcher agent**

Replace contents of `backend/agents/blueprints/sales/workforce/researcher/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.researcher.commands import discover_prospects

logger = logging.getLogger(__name__)


class ResearcherBlueprint(WorkforceBlueprint):
    name = "Sales Researcher"
    slug = "researcher"
    description = (
        "Prospect discovery specialist — finds real decision-makers at multiplier "
        "organizations via web search. Verifies identity, role, and contact info. "
        "Runs as a clone per target area."
    )
    tags = ["research", "prospecting", "discovery", "web-search", "verification"]
    default_model = "claude-sonnet-4-6"
    uses_web_search = True
    skills = [
        {
            "name": "Prospect Discovery",
            "description": (
                "Find real people via web search: LinkedIn profiles, company team pages, "
                "conference speaker lists, podcast guests, blog authors. Verify each person "
                "is real and currently in the claimed role."
            ),
        },
        {
            "name": "Company Profiling",
            "description": (
                "Build structured profiles: name, website, industry, size, headquarters, "
                "founded, funding, revenue. Cross-reference multiple sources."
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
        return """You are a prospect discovery specialist. You find REAL decision-makers at multiplier organizations via web search.

## ZERO FABRICATION POLICY — THE #1 RULE

You will be FIRED for fabricating prospect profiles. Every person, every detail must come from an actual web search result.

WHAT FABRICATION LOOKS LIKE (all have happened and destroyed real campaigns):
- Inventing a person's name and guessing their role
- Putting a real person at the wrong company or in the wrong role
- Guessing someone's email format (sarah@company.com)
- Citing a conference talk or blog post that doesn't exist

WHAT TO DO INSTEAD:
- Search for real people. If you find 4 verified prospects instead of 10, output 4.
- For each person: cite the EXACT search result that confirms they exist and hold this role
- If you can't find their email: write "email not found — contact via LinkedIn"
- "No verified prospects found — searched [terms]" is a VALID and RESPECTED output

4 real prospects >> 10 fabricated ones that destroy credibility.

## Output Format

For each VERIFIED prospect:

## Prospect [N]: [Full Name] — [Organization]
**Role:** [Verified current title — from their LinkedIn or company page]
**Organization:** [Name + what they do]
**Multiplier potential:** [Why this person/org can send multiple bookings]
**Verification:** [Search term used + source that confirms identity/role]
**Contact:** [Verified email, LinkedIn URL, or "not found"]
**Hook opportunity:** [1-2 sentences connecting them to our offer]

## What You Do NOT Do
- No market analysis or competitive landscape
- No industry overviews or trend reports
- No AIDA frameworks or messaging strategies
- No prose — just structured prospect data
- No pitch writing — the copywriter handles that"""

    discover_prospects = discover_prospects

    def get_task_suffix(self, agent, task):
        return """# PROSPECT DISCOVERY RULES

## Every prospect needs verification
- "Role: Head of Operations" → which search result confirmed this? Cite it.
- "Organization: TechStars SF" → did you find their website? Is the program active?
- If you can't verify a person's current role: skip them, don't guess.

## What to do when search returns nothing
- Write "No verified prospects found — searched: [your search terms]"
- Do NOT fill the gap with plausible guesses
- Try alternative search strategies before giving up (company team pages, LinkedIn, event speakers)

## People and organizations
- Only profile people you found in search results
- Do not invent names, titles, or organizational affiliations
- If a person's LinkedIn is outdated (>1 year): flag as "role may be outdated"
- If an org's website is down: "Could not verify — website not found"

## Contact information
- Only include emails you found in search results or on official pages
- NEVER guess email formats (firstname@company.com)
- LinkedIn profile URL is always acceptable as contact
- "Contact not found" is valid — don't fabricate

The sales team will send real emails to these people. Fabricated data = emails to wrong people = destroyed credibility."""
```

- [ ] **Step 5: Update researcher commands `__init__.py`**

Replace contents of `backend/agents/blueprints/sales/workforce/researcher/commands/__init__.py`:

```python
"""Researcher commands registry."""

from .discover_prospects import discover_prospects

ALL_COMMANDS = [discover_prospects]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestResearcherRestructured -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/workforce/researcher/
git add agents/tests/test_sales_department.py
git commit -m "feat(sales): rewrite researcher for prospect discovery"
```

---

### Task 3: Authenticity Analyst — New `verify-prospects` + `verify-pitches` Commands

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/verify_prospects.py`
- Create: `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/verify_pitches.py`
- Modify: `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/__init__.py`
- Modify: `backend/agents/blueprints/sales/workforce/authenticity_analyst/agent.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestAuthenticityAnalystRestructured:
    def test_has_verify_prospects_command(self):
        from agents.blueprints.sales.workforce.authenticity_analyst.agent import AuthenticityAnalystBlueprint
        bp = AuthenticityAnalystBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "verify-prospects" in commands

    def test_has_verify_pitches_command(self):
        from agents.blueprints.sales.workforce.authenticity_analyst.agent import AuthenticityAnalystBlueprint
        bp = AuthenticityAnalystBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "verify-pitches" in commands

    def test_still_has_analyze_command(self):
        """analyze command stays for writers room usage."""
        from agents.blueprints.sales.workforce.authenticity_analyst.agent import AuthenticityAnalystBlueprint
        bp = AuthenticityAnalystBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "analyze" in commands

    def test_verify_commands_use_sonnet(self):
        from agents.blueprints.sales.workforce.authenticity_analyst.agent import AuthenticityAnalystBlueprint
        bp = AuthenticityAnalystBlueprint()
        commands = bp.get_commands()
        for cmd in commands:
            if cmd["name"] in ("verify-prospects", "verify-pitches"):
                assert cmd["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestAuthenticityAnalystRestructured -v`
Expected: FAIL

- [ ] **Step 3: Create `verify_prospects.py` command**

Create `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/verify_prospects.py`:

```python
"""Authenticity Analyst command: verify prospect list from researcher clones."""

from agents.blueprints.base import command


@command(
    name="verify-prospects",
    description=(
        "Audit researcher prospect lists for fabrication. For each prospect, verify that "
        "the cited source supports the claimed identity and role. Output pass/fail per prospect."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def verify_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Verify prospect lists from researcher clones",
        "step_plan": (
            "1. Read all researcher clone outputs\n"
            "2. For each prospect: does the cited verification source support the claimed identity/role?\n"
            "3. Flag prospects with vague verification (e.g., 'LinkedIn search' vs specific URL)\n"
            "4. Flag prospects that may be outdated (left role, org shut down)\n"
            "5. Output PASS or FAIL per prospect with reasoning\n"
            "6. Do NOT re-search — audit citations only"
        ),
    }
```

- [ ] **Step 4: Create `verify_pitches.py` command**

Create `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/verify_pitches.py`:

```python
"""Authenticity Analyst command: verify pitch content against prospect data."""

from agents.blueprints.base import command


@command(
    name="verify-pitches",
    description=(
        "Audit personalized pitches for fabricated claims. For each pitch, verify that "
        "all references are supported by the verified prospect data. Flag invented "
        "social media posts, conference talks, or misattributed roles."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def verify_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Verify pitch content against verified prospect data",
        "step_plan": (
            "1. Read all personalizer clone outputs\n"
            "2. For each pitch: does it reference claims not in the verified prospect data?\n"
            "3. Flag pitches that invent social media posts, conference talks, or quotes\n"
            "4. Flag pitches that misattribute the prospect's role or organization\n"
            "5. Output PASS or FAIL per pitch with specific issues"
        ),
    }
```

- [ ] **Step 5: Update authenticity analyst agent and `__init__.py`**

Replace contents of `backend/agents/blueprints/sales/workforce/authenticity_analyst/commands/__init__.py`:

```python
from .analyze import analyze as analyze
from .verify_pitches import verify_pitches as verify_pitches
from .verify_prospects import verify_prospects as verify_prospects
```

Replace contents of `backend/agents/blueprints/sales/workforce/authenticity_analyst/agent.py`:

```python
"""Authenticity Analyst — AI text detection + prospect/pitch verification for sales.

Reusable archetype from agents.ai.archetypes, deployed in the Sales
department via WorkforceBlueprint. Extended with sales-specific
verification commands for the multiplier pipeline.
"""

from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.authenticity_analyst.commands import (
    analyze,
    verify_pitches,
    verify_prospects,
)


class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WorkforceBlueprint):
    cmd_analyze = analyze
    cmd_verify_prospects = verify_prospects
    cmd_verify_pitches = verify_pitches
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestAuthenticityAnalystRestructured -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/workforce/authenticity_analyst/
git add agents/tests/test_sales_department.py
git commit -m "feat(sales): add verify-prospects and verify-pitches to authenticity analyst"
```

---

### Task 4: Personalizer — New `write-pitches` Command + Agent Rewrite

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/write_pitches.py`
- Modify: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/__init__.py`
- Modify: `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestPersonalizerRestructured:
    def test_has_write_pitches_command(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "write-pitches" in commands

    def test_no_old_commands(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        commands = {c["name"] for c in bp.get_commands()}
        assert "personalize-pitches" not in commands
        assert "revise-pitches" not in commands

    def test_no_web_search(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        assert bp.uses_web_search is False

    def test_system_prompt_b2b_focus(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        assert "B2B" in bp.system_prompt or "partnership" in bp.system_prompt.lower()

    def test_system_prompt_no_discovery(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        assert "find real people" not in bp.system_prompt.lower()
        assert "search for" not in bp.system_prompt.lower()

    def test_write_pitches_uses_sonnet(self):
        from agents.blueprints.sales.workforce.pitch_personalizer.agent import PitchPersonalizerBlueprint
        bp = PitchPersonalizerBlueprint()
        commands = bp.get_commands()
        cmd = next(c for c in commands if c["name"] == "write-pitches")
        assert cmd["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestPersonalizerRestructured -v`
Expected: FAIL

- [ ] **Step 3: Create `write_pitches.py` command**

Create `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/write_pitches.py`:

```python
"""Pitch Personalizer command: write B2B partnership pitches from verified prospect data."""

from agents.blueprints.base import command


@command(
    name="write-pitches",
    description=(
        "Write personalized B2B partnership pitches for verified prospects in one target area. "
        "Prospects are pre-verified — no web search needed. Pure copywriting."
    ),
    model="claude-sonnet-4-6",
)
def write_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Write personalized pitches for verified prospects",
        "step_plan": (
            "1. Read the target area brief and messaging angle\n"
            "2. Read the verified prospect list\n"
            "3. For each prospect: adapt the messaging angle using their specific details\n"
            "4. Write subject line, body (80-150 words), follow-ups, and closer briefing\n"
            "5. Frame every pitch as a B2B partnership opportunity, not a room booking"
        ),
    }
```

- [ ] **Step 4: Rewrite personalizer agent**

Replace contents of `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.pitch_personalizer.commands import write_pitches

logger = logging.getLogger(__name__)


class PitchPersonalizerBlueprint(WorkforceBlueprint):
    name = "Pitch Personalizer"
    slug = "pitch_personalizer"
    description = (
        "B2B partnership copywriter — writes personalized outreach from pre-verified "
        "prospect data. Does NOT do prospect discovery. Runs as a clone per target area."
    )
    tags = ["copywriting", "outreach", "personalization", "B2B", "partnership"]
    default_model = "claude-sonnet-4-6"
    uses_web_search = False
    skills = [
        {
            "name": "Storyline Adaptation",
            "description": (
                "Adapt the messaging angle for each individual: personalize the hook, "
                "mirror their language, reference their specific situation, adjust tone"
            ),
        },
        {
            "name": "Channel Selection",
            "description": (
                "Select the best outreach channel per person based on their contact info "
                "and the available outreach agents in the department"
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a B2B partnership copywriter. You write personalized outreach for ONE target area from PRE-VERIFIED prospect data.

## Your Role
You receive verified prospects (name, role, org, hook opportunity) and a messaging angle. You write the actual emails/messages. You do NOT search for people — that's already done.

## Multiplier Framing
Every pitch frames the deal as a PARTNERSHIP that yields MANY bookings, not a single room sale:
- To accelerator ops: "housing solution for every cohort"
- To VC platform teams: "recommendation for every portfolio company visiting SF"
- To event organizers: "official accommodation partner"
- To community leaders: "exclusive rate for your members"

## Output Format

For each prospect:

## Pitch for [Full Name] — [Organization]
**Channel:** email / linkedin
**Subject:** [Specific to this person — wouldn't make sense for anyone else]

### Body
[Plain text. 80-150 words. B2B partnership tone — one operator to another.
Frame as multiplier opportunity. Use contractions. No marketing-speak.]

### Follow-ups
**Day 3:** [New angle, not "just bumping" — 40-80 words]
**Day 7:** [Direct question inviting reply — 40-80 words]

### Closer Briefing
[2-3 sentences for the human taking the call: who they are, what they care about, what angle to use]

## Rules
- NEVER reference information not in the verified prospect data
- NEVER invent social media posts, talks, or quotes
- If the prospect data has limited info, use their role + org as the hook — don't fabricate details
- Every pitch must pass the "swap test" — would it make NO sense sent to someone else?
- Keep body under 150 words — decision-makers skim aggressively"""

    write_pitches = write_pitches

    def get_task_suffix(self, agent, task):
        return """# COPYWRITING RULES

## Before writing each pitch
- Read the prospect's verified data carefully
- Identify the strongest hook opportunity from their data
- Frame the pitch as a partnership, not a product sale

## Quality gate before submitting
- Would this person recognize you actually know who they are?
- If you swapped names between two pitches, would it be obviously wrong?
- Is every claim backed by data in the prospect profile?
- Is the body under 150 words?
- Does every pitch include Day 3 + Day 7 follow-ups and a closer briefing?
- Is the subject line specific to THIS person?

## What NOT to do
- Do NOT search the web — prospects are pre-verified
- Do NOT add "I saw your LinkedIn post about..." unless the prospect data mentions a specific post
- Do NOT write market analysis or competitive positioning
- Do NOT use buzzwords: synergy, leverage, revolutionary, game-changing
- Do NOT use false urgency: limited time, act now, don't miss out"""
```

- [ ] **Step 5: Update personalizer commands `__init__.py`**

Replace contents of `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/__init__.py`:

```python
"""Pitch Personalizer commands registry."""

from .write_pitches import write_pitches

ALL_COMMANDS = [write_pitches]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestPersonalizerRestructured -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/workforce/pitch_personalizer/
git add agents/tests/test_sales_department.py
git commit -m "feat(sales): rewrite personalizer as B2B copywriter without web search"
```

---

### Task 5: Sales QA — Prompt Update for Multiplier Pipeline

**Files:**
- Modify: `backend/agents/blueprints/sales/workforce/sales_qa/agent.py`
- Modify: `backend/agents/blueprints/sales/workforce/sales_qa/commands/review_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestSalesQaRestructured:
    def test_system_prompt_mentions_multiplier(self):
        from agents.blueprints.sales.workforce.sales_qa.agent import SalesQaBlueprint
        bp = SalesQaBlueprint()
        assert "multiplier" in bp.system_prompt.lower()

    def test_review_dimensions_updated(self):
        from agents.blueprints.sales.workforce.sales_qa.agent import SalesQaBlueprint
        bp = SalesQaBlueprint()
        assert "prospect_verification" in bp.review_dimensions
        assert "multiplier_strategy" in bp.review_dimensions
        # Old dimensions removed
        assert "storyline_effectiveness" not in bp.review_dimensions
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestSalesQaRestructured -v`
Expected: FAIL

- [ ] **Step 3: Update Sales QA agent**

Edit `backend/agents/blueprints/sales/workforce/sales_qa/agent.py` — replace `review_dimensions` and `system_prompt`:

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
        "Quality gate for the multiplier sales pipeline — reviews target identification, "
        "prospect verification, pitch quality, and multiplier strategy coherence"
    )
    tags = ["review", "quality", "qa", "sales", "verification"]
    essential = True
    review_dimensions = [
        "multiplier_strategy",
        "prospect_verification",
        "pitch_quality",
        "pipeline_coherence",
    ]
    skills = [
        {
            "name": "Multiplier Validation",
            "description": (
                "Verify that target areas genuinely represent multiplier relationships — "
                "one conversion yields many bookings. Flag individual-customer targeting."
            ),
        },
        {
            "name": "Prospect Audit",
            "description": (
                "Cross-check prospect data against verification sources. "
                "Flag fabricated profiles, outdated roles, or weak verification."
            ),
        },
        {
            "name": "Pitch Quality Review",
            "description": (
                "Evaluate pitches for B2B partnership tone, personalization depth, "
                "and absence of fabricated claims. Run swap test on each pitch."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return f"""You are the sales pipeline quality specialist. You review the ENTIRE multiplier pipeline output — from target identification through B2B partnership pitches — and score 4 dimensions.

You are the last line of defense before outreach goes to real people. Be rigorous.

## Core Check: Is This Actually Multiplier-Focused?

The #1 failure mode is the pipeline drifting back to individual customer outreach. Every target area must represent a MULTIPLIER relationship where one conversion yields many bookings. If you see pitches to individual founders (not org decision-makers), that's a structural failure.

## Scoring Dimensions (1.0-10.0 each, use decimals)

### multiplier_strategy
- Does each target area represent a genuine multiplier (one deal = many bookings)?
- Are decision-maker profiles specific enough (title + org type, not vague)?
- Is the estimated multiplier realistic (not inflated)?
- Would individual customer outreach belong in marketing instead?

### prospect_verification
- Are prospects real, findable people with cited verification sources?
- Are roles and organizations current?
- Did the authenticity gate pass them? Were any flagged?
- Are there enough verified prospects per area (target: 10)?

### pitch_quality
- Does each pitch frame the deal as a B2B partnership, not a room booking?
- Does it pass the swap test (specific to THIS person)?
- Is it under 150 words with B2B tone?
- Are follow-ups included with distinct angles?
- Does it reference ONLY verified prospect data (no fabricated details)?

### pipeline_coherence
- Does the flow make sense: target areas → prospects → pitches?
- Are the pitches consistent with the messaging angles from ideation?
- Did the authenticity gates catch issues, or were problems missed?
- Is the overall campaign coherent and ready for a human to review?

## Scoring Rules
- Overall score = AVERAGE of all dimension scores
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with specific, actionable feedback per dimension

After your review, call the submit_verdict tool with your verdict and overall score."""

    review_pipeline = review_pipeline

    def get_task_suffix(self, agent, task):
        return f"""# QA REVIEW METHODOLOGY

## Per-Dimension Review

### multiplier_strategy
- For each target area: is the multiplier REAL? "VC platform teams" = real multiplier (they recommend to portfolio companies). "Individual YC founders" = NOT a multiplier (that's marketing).
- Check that decision-maker profiles are actionable — "Head of Housing Partnerships at YC" is good, "YC founder" is wrong.

### prospect_verification
- Spot-check 2-3 prospects per area: do verification citations seem credible?
- Look for red flags: all prospects from the same source, all with perfect data, or generic LinkedIn descriptions.
- Check that the authenticity gate's pass/fail was applied correctly.

### pitch_quality
- Run the swap test on 2-3 pitches: swap names between two pitches — is it obviously wrong? If not, personalization failed.
- Check that pitches frame partnerships, not room bookings. "Book a room" = fail. "Housing solution for your cohort" = pass.
- Verify word count: body should be 80-150 words.

### pipeline_coherence
- Read the pipeline end-to-end: do target areas flow logically into prospects into pitches?
- Check for contradictions between the strategist's messaging angle and the copywriter's actual pitch.
- Verify that gate outputs were respected (failed prospects stripped, flagged pitches noted).

## Verdict
Overall score = AVERAGE of all dimension scores.
- Score >= {EXCELLENCE_THRESHOLD}: APPROVED
- Score < {EXCELLENCE_THRESHOLD}: CHANGES_REQUESTED with per-dimension feedback

After your review, call the submit_verdict tool with your verdict and overall score."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestSalesQaRestructured -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/blueprints/sales/workforce/sales_qa/
git add agents/tests/test_sales_department.py
git commit -m "feat(sales): update sales QA for multiplier pipeline review"
```

---

### Task 6: Leader — Pipeline Constants and State Machine Routing

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py`

This task updates the constants and `generate_task_proposal` routing. The next tasks handle fan-out and gate logic.

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestLeaderRestructuredConstants:
    def test_pipeline_steps(self):
        from agents.blueprints.sales.leader.agent import PIPELINE_STEPS
        assert PIPELINE_STEPS == [
            "ideation",
            "discovery",
            "prospect_gate",
            "copywriting",
            "copy_gate",
            "qa_review",
            "dispatch",
        ]

    def test_all_steps_have_agent_mapping(self):
        from agents.blueprints.sales.leader.agent import PIPELINE_STEPS, STEP_TO_AGENT
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_AGENT

    def test_all_steps_have_command_mapping(self):
        from agents.blueprints.sales.leader.agent import PIPELINE_STEPS, STEP_TO_COMMAND
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_COMMAND

    def test_all_steps_have_context_sources(self):
        from agents.blueprints.sales.leader.agent import PIPELINE_STEPS, STEP_CONTEXT_SOURCES
        for step in PIPELINE_STEPS:
            assert step in STEP_CONTEXT_SOURCES

    def test_discovery_fans_out_researcher(self):
        from agents.blueprints.sales.leader.agent import STEP_TO_AGENT
        assert STEP_TO_AGENT["discovery"] == "researcher"

    def test_copywriting_fans_out_personalizer(self):
        from agents.blueprints.sales.leader.agent import STEP_TO_AGENT
        assert STEP_TO_AGENT["copywriting"] == "pitch_personalizer"

    def test_gates_use_authenticity_analyst(self):
        from agents.blueprints.sales.leader.agent import STEP_TO_AGENT
        assert STEP_TO_AGENT["prospect_gate"] == "authenticity_analyst"
        assert STEP_TO_AGENT["copy_gate"] == "authenticity_analyst"

    def test_default_prospects_per_area(self):
        from agents.blueprints.sales.leader.agent import DEFAULT_PROSPECTS_PER_AREA
        assert DEFAULT_PROSPECTS_PER_AREA == 10

    def test_no_old_constants(self):
        import agents.blueprints.sales.leader.agent as mod
        assert not hasattr(mod, "DEFAULT_PROFILES_PER_AREA")
        assert not hasattr(mod, "DIMENSION_TO_AGENT")
        assert not hasattr(mod, "AGENT_FIX_COMMANDS")
        assert not hasattr(mod, "CHAIN_ORDER")

    def test_fan_out_steps(self):
        from agents.blueprints.sales.leader.agent import FAN_OUT_STEPS
        assert "discovery" in FAN_OUT_STEPS
        assert "copywriting" in FAN_OUT_STEPS

    def test_fan_out_config(self):
        from agents.blueprints.sales.leader.agent import FAN_OUT_STEPS
        assert FAN_OUT_STEPS["discovery"]["agent_type"] == "researcher"
        assert FAN_OUT_STEPS["discovery"]["command"] == "discover-prospects"
        assert FAN_OUT_STEPS["copywriting"]["agent_type"] == "pitch_personalizer"
        assert FAN_OUT_STEPS["copywriting"]["command"] == "write-pitches"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderRestructuredConstants -v`
Expected: FAIL

- [ ] **Step 3: Update leader constants**

In `backend/agents/blueprints/sales/leader/agent.py`, replace the constants section (lines 20-79) with:

```python
# ── Pipeline definition ────────────────────────────────────────────────────

DEFAULT_PROSPECTS_PER_AREA = 10

PIPELINE_STEPS = [
    "ideation",
    "discovery",        # fan-out — 1 researcher clone per target area
    "prospect_gate",    # authenticity_analyst verifies prospect lists
    "copywriting",      # fan-out — 1 personalizer clone per area
    "copy_gate",        # authenticity_analyst verifies pitches
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

# Fan-out step configuration — which steps spawn clones
FAN_OUT_STEPS = {
    "discovery": {
        "agent_type": "researcher",
        "command": "discover-prospects",
        "source_step": "ideation",
        "source_command": "identify-targets",
    },
    "copywriting": {
        "agent_type": "pitch_personalizer",
        "command": "write-pitches",
        "source_step": "ideation",
        "source_command": "identify-targets",
    },
}

# Context injection: which prior steps feed into each step
STEP_CONTEXT_SOURCES = {
    "ideation": [],
    "discovery": ["ideation"],
    "prospect_gate": ["discovery"],
    "copywriting": ["ideation", "discovery", "prospect_gate"],
    "copy_gate": ["copywriting"],
    "qa_review": ["ideation", "prospect_gate", "copywriting", "copy_gate"],
    "dispatch": ["copywriting"],
}
```

- [ ] **Step 4: Update `generate_task_proposal` routing**

Replace the `generate_task_proposal` method body with:

```python
    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
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
        dept_id = str(department.id)

        dept_state = sprint.get_department_state(dept_id)
        current_step = dept_state.get("pipeline_step")

        if current_step is None:
            current_step = "ideation"
            dept_state["pipeline_step"] = current_step
            sprint.set_department_state(dept_id, dept_state)

        if current_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if current_step in FAN_OUT_STEPS:
            return self._handle_fan_out_step(agent, sprint, current_step)

        # Linear steps: ideation, prospect_gate, copy_gate, qa_review
        return self._handle_linear_step(agent, sprint, current_step)
```

- [ ] **Step 5: Update the leader system prompt and description**

Replace the system prompt and skills:

```python
    @property
    def system_prompt(self) -> str:
        return """You are the Head of Sales. You orchestrate a multiplier-first pipeline of specialized agents to produce B2B partnership outreach campaigns.

YOUR PIPELINE:
1. strategist (ideation): Identify 3-5 multiplier target areas — orgs/gatekeepers who control many bookings
2. researcher (discovery, fan-out): N clones discover real decision-makers via web search, one per target area
3. authenticity_analyst (prospect gate): Verify all discovered prospects are real
4. pitch_personalizer (copywriting, fan-out): N clones write B2B partnership pitches from verified data
5. authenticity_analyst (copy gate): Verify pitches don't fabricate claims
6. sales_qa: Quality review of the entire pipeline
7. Outreach dispatch: Send approved pitches via available outreach agents

CORE PRINCIPLE: Sales targets MULTIPLIER relationships — one conversion = many bookings.
Individual customer acquisition is marketing's job.

You don't write pitches or do research directly — you create tasks for your workforce."""
```

Update skills list:

```python
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the multiplier sales pipeline: ideation → discovery (fan-out) → "
                "prospect gate → copywriting (fan-out) → copy gate → QA → dispatch"
            ),
        },
        {
            "name": "Outreach Discovery",
            "description": (
                "Discover available outreach channels by querying agents with outreach=True. "
                "Pass channel list to strategist for assignment."
            ),
        },
    ]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderRestructuredConstants -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/leader/agent.py agents/tests/test_sales_department.py
git commit -m "feat(sales): update leader pipeline constants and routing for multiplier architecture"
```

---

### Task 7: Leader — Generalized Fan-Out Handler

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/agents/tests/test_sales_department.py`:

```python
class TestLeaderFanOut:
    """Test the generalized fan-out handler for discovery and copywriting steps."""

    @pytest.fixture
    def leader_bp(self):
        from agents.blueprints.sales.leader.agent import SalesLeaderBlueprint
        return SalesLeaderBlueprint()

    def test_parse_target_areas_from_ideation(self, leader_bp):
        """Target area parsing works with the new identify-targets format."""
        report = (
            "### Strategic Thesis\nSome thesis.\n\n"
            "### Target Area 1: Accelerator Ops Teams\n"
            "**Tier:** 1\n**Scope:** SF accelerator programs\n\n"
            "### Target Area 2: VC Platform Teams\n"
            "**Tier:** 1\n**Scope:** Early-stage VC firms\n\n"
            "### Target Area 3: Event Housing Partners\n"
            "**Tier:** 2\n**Scope:** SF tech event organizers\n"
        )
        areas = leader_bp._parse_target_areas(report, max_areas=5)
        assert len(areas) == 3
        assert areas[0][0] == "Accelerator Ops Teams"
        assert areas[1][0] == "VC Platform Teams"
        assert areas[2][0] == "Event Housing Partners"

    def test_fan_out_creates_clones_for_discovery(self, leader_bp, sprint, workforce, department):
        """Discovery fan-out creates researcher clones and tasks."""
        from agents.models import AgentTask

        dept_id = str(department.id)
        sprint.set_department_state(dept_id, {"pipeline_step": "discovery"})

        # Create a completed ideation task
        strategist = department.agents.get(agent_type="strategist")
        AgentTask.objects.create(
            agent=strategist,
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Accelerator Ops\n"
                "**Tier:** 1\n**Scope:** SF accelerators\n\n"
                "### Target Area 2: VC Platform\n"
                "**Tier:** 1\n**Scope:** Early-stage VCs\n"
            ),
        )

        leader = department.agents.get(is_leader=True)
        proposal = leader_bp.generate_task_proposal(leader)
        assert proposal is not None
        assert len(proposal["tasks"]) == 2
        assert proposal["tasks"][0]["command_name"] == "discover-prospects"
        assert proposal["tasks"][0]["target_agent_type"] == "researcher"

    def test_fan_out_creates_clones_for_copywriting(self, leader_bp, sprint, workforce, department):
        """Copywriting fan-out creates personalizer clones and tasks."""
        from agents.models import AgentTask

        dept_id = str(department.id)
        sprint.set_department_state(dept_id, {"pipeline_step": "copywriting"})

        # Create completed ideation task (for target area parsing)
        strategist = department.agents.get(agent_type="strategist")
        AgentTask.objects.create(
            agent=strategist,
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Accelerator Ops\n"
                "**Tier:** 1\n**Scope:** SF accelerators\n\n"
                "### Target Area 2: VC Platform\n"
                "**Tier:** 1\n**Scope:** Early-stage VCs\n"
            ),
        )

        # Create completed prospect_gate task (verified prospects)
        auth = department.agents.get(agent_type="authenticity_analyst")
        AgentTask.objects.create(
            agent=auth,
            sprint=sprint,
            command_name="verify-prospects",
            status=AgentTask.Status.DONE,
            report="## Area 1\nAll 5 prospects PASS.\n## Area 2\nAll 4 prospects PASS.",
        )

        leader = department.agents.get(is_leader=True)
        proposal = leader_bp.generate_task_proposal(leader)
        assert proposal is not None
        assert len(proposal["tasks"]) == 2
        assert proposal["tasks"][0]["command_name"] == "write-pitches"
        assert proposal["tasks"][0]["target_agent_type"] == "pitch_personalizer"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderFanOut -v`
Expected: FAIL — `_handle_fan_out_step` doesn't exist yet

- [ ] **Step 3: Implement `_handle_fan_out_step`**

Replace `_handle_personalization_step` and `_create_clones_and_dispatch` with a generalized fan-out handler in `backend/agents/blueprints/sales/leader/agent.py`:

```python
    def _handle_fan_out_step(self, agent: Agent, sprint, step: str) -> dict | None:
        """Handle a fan-out pipeline step (discovery or copywriting)."""
        from agents.models import AgentTask, ClonedAgent

        department = agent.department
        config = FAN_OUT_STEPS[step]
        agent_type = config["agent_type"]
        command = config["command"]

        # Check if clones exist yet
        clone_count = ClonedAgent.objects.filter(
            sprint=sprint,
            parent__agent_type=agent_type,
            parent__department=department,
        ).count()

        if clone_count == 0:
            return self._create_fan_out_tasks(agent, sprint, step)

        # Clones exist — check if all clone tasks are done.
        clone_tasks = AgentTask.objects.filter(
            sprint=sprint,
            cloned_agent__sprint=sprint,
            command_name=command,
        )
        if not clone_tasks.exists():
            clone_tasks = AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=agent_type,
                agent__department=department,
                command_name=command,
            )

        if not clone_tasks.exists():
            return None  # Wait for tasks to appear

        pending = clone_tasks.exclude(status=AgentTask.Status.DONE)
        if pending.exists():
            return None  # Wait for all clones to finish

        return self._advance_to_next_step(agent, sprint, step)

    def _create_fan_out_tasks(self, agent: Agent, sprint, step: str) -> dict | None:
        """Parse target areas and create clone tasks for a fan-out step."""
        from agents.models import AgentTask

        department = agent.department
        config = FAN_OUT_STEPS[step]
        agent_type = config["agent_type"]
        command = config["command"]
        source_command = config["source_command"]

        # Get ideation output (always the source for target area parsing)
        ideation_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=department,
                command_name=source_command,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        if not ideation_task or not ideation_task.report:
            logger.warning("SALES_NO_IDEATION dept=%s — cannot fan out without target areas", department.name)
            return None

        max_areas = agent.get_config_value("max_target_areas", 5)
        target_areas = self._parse_target_areas(ideation_task.report, max_areas=max_areas)
        if not target_areas:
            logger.warning("SALES_NO_TARGET_AREAS dept=%s — no target areas found", department.name)
            return None

        # Find parent agent
        parent = department.agents.filter(agent_type=agent_type, status="active").first()
        if not parent:
            logger.warning("SALES_NO_AGENT dept=%s type=%s", department.name, agent_type)
            return None

        # Create clones
        clones = self.create_clones(
            parent,
            len(target_areas),
            sprint,
            initial_state={"target_count": DEFAULT_PROSPECTS_PER_AREA},
        )

        # Build context for each clone
        context_parts = self._gather_step_context(agent, sprint, step)
        context_text = "\n\n".join(context_parts) if context_parts else ""

        tasks = []
        for i, (area_name, area_content) in enumerate(target_areas):
            clone = clones[i]
            step_plan = (
                f"## Sprint Instruction\n{sprint.text}\n\n"
                f"## Prior Pipeline Output\n{context_text}\n\n"
                f"## Your Target Area\n### {area_name}\n{area_content}\n\n"
            )
            if step == "discovery":
                step_plan += (
                    f"Find up to {DEFAULT_PROSPECTS_PER_AREA} verified decision-makers "
                    f"for this target area. Focus on the decision-maker profile above."
                )
            elif step == "copywriting":
                step_plan += (
                    "Write personalized B2B partnership pitches for each verified prospect "
                    "in your target area. The prospect data and verification gate results "
                    "are in the Prior Pipeline Output above. Use ONLY prospects that PASSED "
                    "the verification gate — skip any marked FAIL. No web search."
                )

            tasks.append(
                {
                    "target_agent_type": agent_type,
                    "command_name": command,
                    "exec_summary": f"{step.replace('_', ' ').title()} — {area_name.strip()}",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                    "_cloned_agent_id": str(clone.id),
                }
            )

        return {
            "exec_summary": f"Fan-out {step} — {len(target_areas)} target areas",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }
```

- [ ] **Step 4: Implement `_gather_step_context` helper**

Add this method to the leader class:

```python
    def _gather_step_context(self, agent: Agent, sprint, step: str) -> list[str]:
        """Gather context from prior pipeline steps for injection into task plans."""
        from agents.models import AgentTask

        context_parts = []
        source_steps = STEP_CONTEXT_SOURCES.get(step, [])

        for src_step in source_steps:
            if src_step in FAN_OUT_STEPS:
                # Gather all clone task outputs for fan-out steps
                fan_config = FAN_OUT_STEPS[src_step]
                clone_tasks = AgentTask.objects.filter(
                    sprint=sprint,
                    cloned_agent__sprint=sprint,
                    command_name=fan_config["command"],
                    status=AgentTask.Status.DONE,
                ).select_related("cloned_agent")
                for ct in clone_tasks:
                    label = f"{src_step.title()} Clone {ct.cloned_agent.clone_index}" if ct.cloned_agent else src_step.title()
                    if ct.report:
                        context_parts.append(f"## {label} Output\n{ct.report}")
            else:
                src_agent_type = STEP_TO_AGENT.get(src_step)
                src_command = STEP_TO_COMMAND.get(src_step)
                if not src_agent_type or not src_command:
                    continue
                src_task = (
                    AgentTask.objects.filter(
                        sprint=sprint,
                        agent__agent_type=src_agent_type,
                        agent__department=agent.department,
                        command_name=src_command,
                        status=AgentTask.Status.DONE,
                    )
                    .order_by("-completed_at")
                    .first()
                )
                if src_task and src_task.report:
                    step_label = src_step.replace("_", " ").title()
                    context_parts.append(f"## {step_label} Output\n{src_task.report}")

        return context_parts
```

- [ ] **Step 5: Update `_propose_step_task` to use `_gather_step_context`**

Replace the context-gathering code in `_propose_step_task` with:

```python
    def _propose_step_task(self, agent: Agent, sprint, step: str) -> dict:
        """Propose a task for a specific pipeline step, injecting context from prior steps."""
        agent_type = STEP_TO_AGENT[step]
        command_name = STEP_TO_COMMAND[step]

        context_parts = self._gather_step_context(agent, sprint, step)
        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}\n\n"
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
```

- [ ] **Step 6: Update `_advance_to_next_step`**

Replace with:

```python
    def _advance_to_next_step(self, agent: Agent, sprint, current_step: str) -> dict | None:
        """Advance from current_step to the next pipeline step."""
        step_idx = PIPELINE_STEPS.index(current_step)
        if step_idx + 1 >= len(PIPELINE_STEPS):
            return None

        next_step = PIPELINE_STEPS[step_idx + 1]
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        dept_state["pipeline_step"] = next_step
        sprint.set_department_state(dept_id, dept_state)

        if next_step == "dispatch":
            return self._handle_dispatch_step(agent, sprint)

        if next_step in FAN_OUT_STEPS:
            return self._handle_fan_out_step(agent, sprint, next_step)

        return self._propose_step_task(agent, sprint, next_step)
```

- [ ] **Step 7: Update `_handle_linear_step` — remove old QA cascade, update step check**

In `_handle_linear_step`, update the QA quality gate section. Replace the `_loop_back_from_qa` call with a simpler version that just marks the sprint as needing revision:

```python
    def _loop_back_from_qa(self, agent, sprint, review_task, round_num) -> dict:
        """QA score too low — loop back to ideation."""
        dept_id = str(agent.department_id)
        from django.utils import timezone as tz

        dept_state = sprint.get_department_state(dept_id)
        dept_state["pipeline_step"] = "ideation"
        dept_state["qa_loopback_at"] = tz.now().isoformat()
        sprint.set_department_state(dept_id, dept_state)

        return self._propose_step_task(agent, sprint, "ideation")
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderFanOut -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add agents/blueprints/sales/leader/agent.py agents/tests/test_sales_department.py
git commit -m "feat(sales): implement generalized fan-out handler for discovery and copywriting"
```

---

### Task 8: Leader — Cleanup and Dispatch Update

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py`

- [ ] **Step 1: Remove old methods**

Delete these methods from the leader class:
- `_handle_personalization_step` (replaced by `_handle_fan_out_step`)
- `_create_clones_and_dispatch` (replaced by `_create_fan_out_tasks`)
- `_find_earliest_failing_agent` (QA cascade removed)
- `_propose_fix_task` (QA cascade removed)
- `_assemble_csv_output` (finalize step removed)
- `_extract_pitches_from_markdown` (finalize step removed)

- [ ] **Step 2: Update `_persist_step_document` for new step names**

```python
    def _persist_step_document(self, agent: Agent, sprint, step: str) -> None:
        """Persist step outputs as Department Documents."""
        from agents.models import AgentTask
        from projects.models import Document

        doc_types = {
            "ideation": (Document.DocType.STRATEGY, "Multiplier Target Areas"),
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
```

- [ ] **Step 3: Update `_propose_dispatch_tasks` to read from copywriting output**

```python
    def _propose_dispatch_tasks(self, agent: Agent, sprint, outreach_agents) -> dict:
        """Propose outreach tasks — one per outreach agent with assigned pitches."""
        context_parts = self._gather_step_context(agent, sprint, "dispatch")
        context_text = "\n\n".join(context_parts) if context_parts else "No pitch payloads available."

        tasks = []
        for outreach_agent in outreach_agents:
            tasks.append(
                {
                    "target_agent_type": outreach_agent.agent_type,
                    "command_name": "send-outreach",
                    "exec_summary": f"Send outreach via {outreach_agent.name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Approved Pitch Payloads\n{context_text}\n\n"
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
```

- [ ] **Step 4: Update `_write_sprint_output` to read from copywriting clones**

```python
    def _write_sprint_output(self, agent: Agent, sprint) -> None:
        """Write the sprint Output when outreach dispatch completes."""
        from agents.models import AgentTask
        from projects.models import Output

        if Output.objects.filter(sprint=sprint, department=agent.department).exists():
            return

        # Write ideation summary as the main output
        ideation_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__department=agent.department,
                agent__agent_type="strategist",
                command_name="identify-targets",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if ideation_task and ideation_task.report:
            Output.objects.create(
                sprint=sprint,
                department=agent.department,
                title=f"Campaign Strategy — {sprint.text[:80]}",
                label="campaign-strategy",
                output_type=Output.OutputType.MARKDOWN,
                content=ideation_task.report,
            )

        # Write outreach delivery reports
        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__department=agent.department,
            agent__outreach=True,
            status=AgentTask.Status.DONE,
        )
        for ot in outreach_tasks:
            if ot.report:
                Output.objects.create(
                    sprint=sprint,
                    department=agent.department,
                    title=f"Outreach Report — {ot.agent.name}",
                    label=f"outreach-{ot.agent.agent_type}",
                    output_type=Output.OutputType.MARKDOWN,
                    content=ot.report,
                )
```

- [ ] **Step 5: Remove unused imports**

Remove `csv`, `io` imports from the leader if no longer used. Remove references to old constants.

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: New tests PASS, some old tests will FAIL (they reference old constants/methods — updated in Task 9)

- [ ] **Step 7: Commit**

```bash
git add agents/blueprints/sales/leader/agent.py
git commit -m "feat(sales): clean up leader — remove old methods, update dispatch and output"
```

---

### Task 9: Update Test Suite

**Files:**
- Modify: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Remove or update tests for old constants**

Delete or update these test classes:
- `TestLeaderConstants` — replace with `TestLeaderRestructuredConstants` (already written)
- `TestFanOutPersonalization` — replace with `TestLeaderFanOut` (already written)
- `TestQACascadeRouting` — delete entirely (QA cascade removed)
- `TestStrategistExpanded` — replace with `TestStrategistRestructured` (already written)
- `TestPersonalizerExpanded` — replace with `TestPersonalizerRestructured` (already written)

- [ ] **Step 2: Update `TestSalesRegistry` for new command set**

```python
class TestSalesRegistry:
    def test_sales_department_registered(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        assert "sales" in DEPARTMENT_REGISTRY

    def test_sales_has_6_workforce_agents(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        assert len(DEPARTMENT_REGISTRY["sales"]["workforce"]) == 6

    def test_sales_workforce_slugs(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        slugs = {bp.slug for bp in DEPARTMENT_REGISTRY["sales"]["workforce"]}
        assert slugs == {
            "researcher",
            "strategist",
            "pitch_personalizer",
            "sales_qa",
            "authenticity_analyst",
            "email_outreach",
        }

    def test_leader_is_head_of_sales(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        leader = DEPARTMENT_REGISTRY["sales"]["leader"]
        assert leader.slug == "leader"
        assert leader.name == "Head of Sales"

    def test_all_agents_resolve_via_get_blueprint(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        dept = DEPARTMENT_REGISTRY["sales"]
        assert dept["leader"] is not None
        for bp in dept["workforce"]:
            assert bp.get_commands() is not None
```

- [ ] **Step 3: Update `TestSalesBlueprintProperties`**

```python
class TestSalesBlueprintProperties:
    def test_researcher_uses_sonnet(self):
        from agents.blueprints.sales.workforce.researcher.agent import ResearcherBlueprint
        bp = ResearcherBlueprint()
        assert bp.default_model == "claude-sonnet-4-6"

    def test_identify_targets_uses_sonnet(self):
        from agents.blueprints.sales.workforce.strategist.agent import StrategistBlueprint
        bp = StrategistBlueprint()
        commands = bp.get_commands()
        cmd = next(c for c in commands if c["name"] == "identify-targets")
        assert cmd["model"] == "claude-sonnet-4-6"

    def test_sales_qa_is_essential(self):
        from agents.blueprints.sales.workforce.sales_qa.agent import SalesQaBlueprint
        bp = SalesQaBlueprint()
        assert bp.essential is True

    def test_sales_qa_has_4_review_dimensions(self):
        from agents.blueprints.sales.workforce.sales_qa.agent import SalesQaBlueprint
        bp = SalesQaBlueprint()
        assert len(bp.review_dimensions) == 4
        assert "multiplier_strategy" in bp.review_dimensions
        assert "prospect_verification" in bp.review_dimensions
        assert "pitch_quality" in bp.review_dimensions
        assert "pipeline_coherence" in bp.review_dimensions

    def test_each_agent_has_commands(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        for bp in DEPARTMENT_REGISTRY["sales"]["workforce"]:
            commands = bp.get_commands()
            assert len(commands) > 0, f"{bp.slug} has no commands"

    def test_each_agent_has_system_prompt(self):
        from agents.blueprints.registry import DEPARTMENT_REGISTRY
        for bp in DEPARTMENT_REGISTRY["sales"]["workforce"]:
            assert bp.system_prompt, f"{bp.slug} has no system prompt"
```

- [ ] **Step 4: Update `TestLeaderStateMachine` for new pipeline**

```python
class TestLeaderStateMachine:
    def test_starts_at_ideation(self, leader, sprint, workforce):
        proposal = leader.get_blueprint().generate_task_proposal(leader)
        assert proposal is not None
        assert proposal["tasks"][0]["command_name"] == "identify-targets"

    def test_advances_to_discovery(self, leader, sprint, workforce):
        from agents.models import AgentTask
        dept_id = str(leader.department_id)
        sprint.set_department_state(dept_id, {"pipeline_step": "ideation"})

        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report="### Target Area 1: Test Area\n**Tier:** 1\n**Scope:** Test\n",
            completed_at=timezone.now(),
        )

        proposal = leader.get_blueprint().generate_task_proposal(leader)
        state = sprint.get_department_state(dept_id)
        assert state["pipeline_step"] == "discovery"

    def test_returns_none_without_sprints(self, leader, workforce):
        proposal = leader.get_blueprint().generate_task_proposal(leader)
        assert proposal is None

    def test_waits_for_active_task(self, leader, sprint, workforce):
        from agents.models import AgentTask
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.PROCESSING,
        )
        proposal = leader.get_blueprint().generate_task_proposal(leader)
        assert proposal is None
```

- [ ] **Step 5: Update `TestDocumentPersistence`**

```python
class TestDocumentPersistence:
    def test_ideation_creates_document(self, leader, sprint, workforce):
        from agents.models import AgentTask
        from projects.models import Document

        dept_id = str(leader.department_id)
        sprint.set_department_state(dept_id, {"pipeline_step": "ideation"})

        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="identify-targets",
            status=AgentTask.Status.DONE,
            report="### Target Area 1: Test\n**Tier:** 1\n",
            completed_at=timezone.now(),
        )

        leader.get_blueprint().generate_task_proposal(leader)
        assert Document.objects.filter(
            department=leader.department,
            doc_type=Document.DocType.STRATEGY,
        ).exists()
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add agents/tests/test_sales_department.py
git commit -m "test(sales): update test suite for multiplier pipeline restructure"
```

---

### Task 10: Delete Old Command Files

**Files:**
- Delete: `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`
- Delete: `backend/agents/blueprints/sales/workforce/strategist/commands/revise_strategy.py`
- Delete: `backend/agents/blueprints/sales/workforce/strategist/commands/finalize_outreach.py`
- Delete: `backend/agents/blueprints/sales/workforce/researcher/commands/research_industry.py`
- Delete: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`
- Delete: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/revise_pitches.py`

- [ ] **Step 1: Verify no imports reference old files**

Run: `cd /Users/christianpeters/the-agentic-company/backend && grep -r "draft_strategy\|revise_strategy\|finalize_outreach\|research_industry\|personalize_pitches\|revise_pitches" agents/ --include="*.py" | grep -v "test_\|__pycache__\|\.pyc"`

Expected: No matches (all imports already updated in Tasks 1-4)

- [ ] **Step 2: Delete old files**

```bash
cd /Users/christianpeters/the-agentic-company/backend
rm agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py
rm agents/blueprints/sales/workforce/strategist/commands/revise_strategy.py
rm agents/blueprints/sales/workforce/strategist/commands/finalize_outreach.py
rm agents/blueprints/sales/workforce/researcher/commands/research_industry.py
rm agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py
rm agents/blueprints/sales/workforce/pitch_personalizer/commands/revise_pitches.py
```

- [ ] **Step 3: Run full test suite to verify nothing broke**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: ALL PASS

- [ ] **Step 4: Run broader test suite**

Run: `cd /Users/christianpeters/the-agentic-company/backend && python -m pytest agents/tests/ -v --timeout=30`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add -A agents/blueprints/sales/
git commit -m "chore(sales): delete old command files from pre-restructure pipeline"
```

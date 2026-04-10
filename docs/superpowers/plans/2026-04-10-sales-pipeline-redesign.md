# Sales Pipeline Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the sales pipeline to fan out personalization across N cloned agents per target area, merge strategist + pitch_architect, merge profile_selector + pitch_personalizer, and add strategist consolidation producing exec summary + CSV for dispatch.

**Architecture:** New `ClonedAgent` model with FK to parent Agent, scoped to sprint lifetime. Leader state machine gains fan-out/join/batch steps. Strategist absorbs pitch_architect (AIDA narrative). Pitch personalizer absorbs profile_selector (web search profiling). Two agents deleted, two commands added (finalize-outreach, revised personalize-pitches).

**Tech Stack:** Django models, pytest, existing blueprint/command pattern

---

## File Structure

### New files
- `backend/agents/models/cloned_agent.py` — ClonedAgent model
- `backend/agents/migrations/0021_cloned_agent.py` — migration (auto-generated)
- `backend/agents/blueprints/sales/workforce/strategist/commands/finalize_outreach.py` — new command

### Modified files
- `backend/agents/models/__init__.py` — export ClonedAgent
- `backend/agents/models/agent_task.py` — add nullable FK to ClonedAgent
- `backend/agents/blueprints/base.py` — add `create_clones()` / `destroy_sprint_clones()` helpers on LeaderBlueprint
- `backend/agents/blueprints/sales/leader/agent.py` — rewrite pipeline constants, state machine, fan-out/join logic
- `backend/agents/blueprints/sales/workforce/strategist/agent.py` — absorb pitch_architect prompts, add finalize-outreach command
- `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py` — export finalize_outreach
- `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py` — expand to include storyline design
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py` — absorb profile_selector prompts, expand personalize-pitches
- `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py` — update step_plan
- `backend/agents/blueprints/sales/workforce/sales_qa/agent.py` — update review dimensions (collapse to 3)
- `backend/agents/blueprints/__init__.py` — remove pitch_architect and profile_selector from registry
- `backend/agents/tests/test_sales_department.py` — rewrite tests for new pipeline

### Deleted files
- `backend/agents/blueprints/sales/workforce/pitch_architect/` — entire directory
- `backend/agents/blueprints/sales/workforce/profile_selector/` — entire directory

---

### Task 1: ClonedAgent Model + Migration

**Files:**
- Create: `backend/agents/models/cloned_agent.py`
- Modify: `backend/agents/models/__init__.py`
- Modify: `backend/agents/models/agent_task.py`
- Test: `backend/agents/tests/test_sales_department.py` (new section at top)

- [ ] **Step 1: Write failing tests for ClonedAgent**

Add a new test class at the end of `test_sales_department.py`:

```python
# ── ClonedAgent Model ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestClonedAgent:
    def test_create_clone(self, department, workforce, sprint):
        from agents.models import ClonedAgent

        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(
            parent=parent,
            sprint=sprint,
            clone_index=0,
        )
        assert clone.parent == parent
        assert clone.sprint == sprint
        assert clone.clone_index == 0
        assert clone.internal_state == {}

    def test_clone_resolves_parent_blueprint(self, department, workforce, sprint):
        from agents.models import ClonedAgent

        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        bp = clone.parent.get_blueprint()
        assert bp.slug == "pitch_personalizer"

    def test_clone_destroyed_with_sprint_helper(self, leader, department, workforce, sprint):
        from agents.models import ClonedAgent

        parent = workforce["pitch_personalizer"]
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 2

        ClonedAgent.objects.filter(sprint=sprint).delete()
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_task_can_reference_clone(self, department, workforce, sprint):
        from agents.models import ClonedAgent

        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        task = AgentTask.objects.create(
            agent=parent,
            sprint=sprint,
            command_name="personalize-pitches",
            status=AgentTask.Status.QUEUED,
            cloned_agent=clone,
        )
        assert task.cloned_agent == clone
        assert task.cloned_agent.parent == parent

    def test_task_without_clone_is_fine(self, department, workforce, sprint):
        task = AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.QUEUED,
        )
        assert task.cloned_agent is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestClonedAgent -v`
Expected: ImportError — ClonedAgent does not exist yet.

- [ ] **Step 3: Create ClonedAgent model**

Create `backend/agents/models/cloned_agent.py`:

```python
import uuid

from django.db import models


class ClonedAgent(models.Model):
    """Ephemeral clone of an Agent — same blueprint, own state, scoped to one sprint."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="clones",
        help_text="The agent this clone inherits blueprint/instructions/config from",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="cloned_agents",
        help_text="Sprint this clone is scoped to — destroyed when sprint completes",
    )
    clone_index = models.IntegerField(
        help_text="0-based index for identification within a fan-out batch",
    )
    internal_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Clone-specific working state (target_count, cumulative profiles, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sprint", "parent", "clone_index"]

    def __str__(self):
        return f"Clone #{self.clone_index} of {self.parent.name} (sprint {self.sprint_id})"
```

- [ ] **Step 4: Add cloned_agent FK to AgentTask**

In `backend/agents/models/agent_task.py`, add after the `blocked_by` field (line ~49):

```python
    cloned_agent = models.ForeignKey(
        "agents.ClonedAgent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text="If set, this task runs on behalf of a cloned agent instance.",
    )
```

- [ ] **Step 5: Update models __init__.py**

In `backend/agents/models/__init__.py`:

```python
from .agent import Agent
from .agent_task import AgentTask
from .cloned_agent import ClonedAgent

__all__ = ["Agent", "AgentTask", "ClonedAgent"]
```

- [ ] **Step 6: Generate and run migration**

Run: `cd backend && python manage.py makemigrations agents --name cloned_agent`
Then: `cd backend && python manage.py migrate`

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestClonedAgent -v`
Expected: All 5 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/agents/models/cloned_agent.py backend/agents/models/__init__.py backend/agents/models/agent_task.py backend/agents/migrations/
git commit -m "feat: add ClonedAgent model with FK on AgentTask for fan-out pipeline"
```

---

### Task 2: LeaderBlueprint Clone Helpers

**Files:**
- Modify: `backend/agents/blueprints/base.py:473` (LeaderBlueprint class)
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write failing tests for clone helpers**

Add to `test_sales_department.py`, new import at top: `from agents.models import ClonedAgent`

```python
@pytest.mark.django_db
class TestLeaderCloneHelpers:
    def test_create_clones(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clones = bp.create_clones(parent, 3, sprint)
        assert len(clones) == 3
        assert all(c.parent == parent for c in clones)
        assert [c.clone_index for c in clones] == [0, 1, 2]
        assert all(c.sprint == sprint for c in clones)

    def test_destroy_sprint_clones(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        bp.create_clones(parent, 3, sprint)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 3

        bp.destroy_sprint_clones(sprint)
        assert ClonedAgent.objects.filter(sprint=sprint).count() == 0

    def test_create_clones_with_initial_state(self, leader, workforce, sprint):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]
        clones = bp.create_clones(parent, 2, sprint, initial_state={"target_count": 50})
        assert all(c.internal_state == {"target_count": 50} for c in clones)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderCloneHelpers -v`
Expected: AttributeError — `create_clones` not found on LeaderBlueprint.

- [ ] **Step 3: Add clone helpers to LeaderBlueprint**

In `backend/agents/blueprints/base.py`, add these methods to the `LeaderBlueprint` class, after the `_check_review_trigger` method (around line 828):

```python
    # ── Clone lifecycle helpers ─────────────────────────────────────────

    def create_clones(
        self, parent_agent: Agent, count: int, sprint, initial_state: dict | None = None
    ) -> list:
        """Create N ephemeral clones of parent_agent, scoped to this sprint."""
        from agents.models import ClonedAgent

        clones = []
        for i in range(count):
            clone = ClonedAgent.objects.create(
                parent=parent_agent,
                sprint=sprint,
                clone_index=i,
                internal_state=initial_state or {},
            )
            clones.append(clone)
        logger.info(
            "CLONES_CREATED parent=%s count=%d sprint=%s",
            parent_agent.name,
            count,
            str(sprint.id)[:8],
        )
        return clones

    def destroy_sprint_clones(self, sprint) -> int:
        """Delete all clones for a sprint. Returns count deleted."""
        from agents.models import ClonedAgent

        count, _ = ClonedAgent.objects.filter(sprint=sprint).delete()
        if count:
            logger.info("CLONES_DESTROYED count=%d sprint=%s", count, str(sprint.id)[:8])
        return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderCloneHelpers -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/base.py backend/agents/tests/test_sales_department.py
git commit -m "feat: add create_clones/destroy_sprint_clones helpers on LeaderBlueprint"
```

---

### Task 3: Strategist Absorbs Pitch Architect

**Files:**
- Modify: `backend/agents/blueprints/sales/workforce/strategist/agent.py`
- Modify: `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`
- Create: `backend/agents/blueprints/sales/workforce/strategist/commands/finalize_outreach.py`
- Modify: `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write failing tests for expanded strategist**

Update existing tests and add new ones. First, update the expected commands in `TestSalesBlueprintProperties.test_each_agent_has_commands`:

```python
        expected = {
            "researcher": ["research-industry"],
            "strategist": ["draft-strategy", "finalize-outreach", "revise-strategy"],
            "pitch_personalizer": ["personalize-pitches", "revise-pitches"],
            "sales_qa": ["review-pipeline"],
            "email_outreach": ["send-outreach"],
        }
```

Add a new test class:

```python
class TestStrategistExpanded:
    def test_system_prompt_includes_narrative_design(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "narrative arc" in prompt.lower() or "aida" in prompt.lower()

    def test_system_prompt_includes_target_areas(self):
        bp = get_blueprint("strategist", "sales")
        prompt = bp.system_prompt
        assert "target area" in prompt.lower()

    def test_has_finalize_outreach_command(self):
        bp = get_blueprint("strategist", "sales")
        cmd_names = [c["name"] for c in bp.get_commands()]
        assert "finalize-outreach" in cmd_names

    def test_finalize_outreach_mentions_csv(self):
        bp = get_blueprint("strategist", "sales")
        for cmd in bp.get_commands():
            if cmd["name"] == "finalize-outreach":
                assert "csv" in cmd["description"].lower() or "CSV" in cmd["description"]
                break
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestStrategistExpanded -v -x`
Expected: FAIL — finalize-outreach command doesn't exist yet.

- [ ] **Step 3: Create finalize_outreach command**

Create `backend/agents/blueprints/sales/workforce/strategist/commands/finalize_outreach.py`:

```python
"""Strategist command: consolidate clone outputs into exec summary + CSV."""

from agents.blueprints.base import command


@command(
    name="finalize-outreach",
    description=(
        "Consolidate all personalizer outputs into two deliverables: "
        "a 1-page exec summary and a machine-readable CSV with columns: "
        "channel, identifier, subject, content."
    ),
    model="claude-opus-4-6",
    max_tokens=16384,
)
def finalize_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Consolidate personalizer outputs into exec summary + CSV",
        "step_plan": (
            "1. Review all personalizer clone outputs — one per target area\n"
            "2. Write Exec Summary: max 1 page — what this is about, why it is the right approach, "
            "whom we target with what. No chat, no filler.\n"
            "3. Write CSV output with columns: channel, identifier, subject, content\n"
            "   - channel: outreach agent identifier (e.g. email)\n"
            "   - identifier: email address, Reddit username, Twitter handle, phone, etc.\n"
            "   - subject: subject line or headline\n"
            "   - content: the outreach message\n"
            "4. Output both documents clearly separated with headers"
        ),
    }
```

- [ ] **Step 4: Update strategist commands __init__.py**

Read current file first, then update `backend/agents/blueprints/sales/workforce/strategist/commands/__init__.py`:

```python
from .draft_strategy import draft_strategy
from .finalize_outreach import finalize_outreach
from .revise_strategy import revise_strategy

__all__ = ["draft_strategy", "finalize_outreach", "revise_strategy"]
```

- [ ] **Step 5: Update strategist agent.py — absorb pitch architect**

Rewrite `backend/agents/blueprints/sales/workforce/strategist/agent.py`. The system prompt expands to include AIDA narrative design (from pitch_architect), the finalize-outreach command is registered, and the task suffix merges pitch_architect's methodology:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.strategist.commands import (
    draft_strategy,
    finalize_outreach,
    revise_strategy,
)

logger = logging.getLogger(__name__)


class StrategistBlueprint(WorkforceBlueprint):
    name = "Sales Strategist"
    slug = "strategist"
    description = (
        "Outreach strategist — analyzes research to identify target areas with thesis, "
        "rationale, narrative arc, and approach for each. Consolidates pipeline output "
        "into exec summary and CSV for dispatch."
    )
    tags = ["strategy", "targeting", "segmentation", "narrative", "pitch", "consolidation"]
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
            "name": "AIDA Narrative Design",
            "description": (
                "Structure outreach using Attention-Interest-Desire-Action framework. "
                "Each element must earn the next — no skipping to the ask."
            ),
        },
        {
            "name": "Anti-Spam Craft",
            "description": (
                "Make outreach feel like a genuine human reaching out, not a template. "
                "Specific details over generic praise, prospect's language over our jargon."
            ),
        },
        {
            "name": "Pipeline Consolidation",
            "description": (
                "Aggregate outputs from multiple personalizer clones into a unified "
                "exec summary and structured CSV for outreach dispatch."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a sales strategist and narrative designer. You have two phases:

## PHASE 1: Strategy + Storyline (draft-strategy command)

Given a research briefing, identify target areas and design the outreach narrative for each.

A target area can be:
- An industry sector (e.g. "B2B SaaS companies in logistics")
- A cohort of people (e.g. "CTOs at Series B startups scaling engineering teams")
- A subset of a market (e.g. "European fintechs expanding to US market")

Your output must follow this structure:

### Strategic Thesis
2-3 sentences: the overall outreach angle and why now.

### Target Areas

For each target area:
- **Name:** Descriptive label
- **Scope:** Who exactly is in this segment
- **Size estimate:** Rough number of potential targets
- **Rationale:** Why this segment is promising RIGHT NOW (cite specific research signals)
- **Competitive density:** How crowded is this space
- **Narrative Arc (AIDA):**
  - Attention: What opens the door? Specific trigger event or detail.
  - Interest: How we connect to what they care about, in THEIR terms.
  - Desire: Tangible proof points — real companies, real metrics.
  - Action: Low-friction next step matching their decision-making style.
- **Hook type:** Trigger event / mutual connection / content engagement / company initiative / role-based pain
- **Anti-spam notes:** What to avoid, what tone to use for this audience
- **Potential:** High / Medium / Low with justification

### Priority Ranking
Rank all target areas. Explain criteria.

### Risks & Assumptions
What could go wrong, what needs validation.

IMPORTANT: Target areas must be parseable — use numbered headers (### Target Area 1, ### Target Area 2, etc.) so the system can slice them for parallel processing.

## PHASE 2: Consolidation (finalize-outreach command)

After personalizer clones produce outreach for each target area, you consolidate:

1. **Exec Summary** — max 1 page. What this is about, why it is the right approach, whom we target with what. No chat, no filler, no lengthy explanation. Crisp.

2. **CSV Output** — machine-readable, with these exact column headers:
   channel,identifier,subject,content

   - channel: outreach agent identifier (e.g. "email")
   - identifier: email address, Reddit username, Twitter handle, phone, etc.
   - subject: subject line or headline
   - content: the outreach message

Output the CSV block between ```csv and ``` markers.

SCOPE: In Phase 1, you identify WHO to target, WHY, and design the NARRATIVE. In Phase 2, you consolidate. You do NOT find individual prospects or write individual pitches — personalizer clones handle that."""

    draft_strategy = draft_strategy
    finalize_outreach = finalize_outreach
    revise_strategy = revise_strategy

    def get_task_suffix(self, agent, task):
        return """# STRATEGY & NARRATIVE METHODOLOGY

## Target Area Quality Criteria
- Each target area must cite at least 2 specific signals from the research briefing
- "Why now" must reference a concrete trigger event, trend, or timing signal
- Size estimates should be grounded (even rough), not hand-waved
- Competitive density assessment should reference actual competitors from the research

## Positioning Framework
- For each target area: where do competitors win, where do they lose?
- Identify positioning gaps — segments competitors ignore or serve poorly
- Frame our strengths against specific competitor weaknesses

## Narrative Arc per Target Area
- Hook must reference a real trigger event or verifiable detail — NOT generic flattery
- Interest must use the PROSPECT'S vocabulary, not our jargon
- Desire must cite real proof points (companies, metrics, timeframes)
- Action must be low-friction, bounded, specific
- Each section must earn the next

## Anti-Spam Standards
- No generic flattery ("I'm impressed by your work")
- No fake familiarity ("As a fellow X...")
- No template-obvious phrasing ("I'm reaching out because...")
- Specific details that prove research was done
- Value offered before anything is asked
- Plain text tone — no marketing formatting

## Anti-Patterns
- Do not propose more than 20 target areas — focus beats breadth
- Do not propose generic segments without specificity
- Do not claim "no competition" — there is always competition
- If the research doesn't support a target area, don't force it

## Consolidation Standards (finalize-outreach)
- Exec summary must fit on 1 page — no padding, no filler
- CSV must be valid CSV with exact column headers: channel,identifier,subject,content
- Every row must have all 4 columns populated
- Content column must contain the actual message, not a reference"""
```

- [ ] **Step 6: Update draft_strategy command**

Update `backend/agents/blueprints/sales/workforce/strategist/commands/draft_strategy.py`:

```python
"""Strategist command: draft target area thesis with narrative arc."""

from agents.blueprints.base import command


@command(
    name="draft-strategy",
    description=(
        "Analyze research briefing and draft a thesis with target areas for outreach. "
        "Each target area includes rationale, AIDA narrative arc, and anti-spam guidance. "
        "Output must use numbered headers for system parsing."
    ),
    model="claude-opus-4-6",
)
def draft_strategy(self, agent) -> dict:
    return {
        "exec_summary": "Draft outreach strategy with target areas and narrative arcs",
        "step_plan": (
            "1. Review the research briefing for market landscape and signals\n"
            "2. Identify target areas — industry sectors, cohorts, or segments\n"
            "3. For each target area: define scope, rationale, size estimate, competitive density\n"
            "4. Design AIDA narrative arc per target area: attention hook, interest framing, "
            "desire proof points, action CTA\n"
            "5. Note anti-spam guidance per target area\n"
            "6. Rank target areas by impact potential and accessibility\n"
            "7. Use numbered headers (### Target Area 1, etc.) for system parsing"
        ),
    }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestStrategistExpanded -v`
Expected: All 4 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/strategist/
git commit -m "feat: strategist absorbs pitch_architect — AIDA narrative + finalize-outreach command"
```

---

### Task 4: Pitch Personalizer Absorbs Profile Selector

**Files:**
- Modify: `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`
- Modify: `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write failing tests for expanded personalizer**

```python
class TestPersonalizerExpanded:
    def test_system_prompt_includes_profile_finding(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        prompt = bp.system_prompt
        assert "find" in prompt.lower() or "search" in prompt.lower() or "discover" in prompt.lower()

    def test_uses_web_search(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.uses_web_search is True

    def test_uses_haiku_model(self):
        bp = get_blueprint("pitch_personalizer", "sales")
        assert bp.default_model == "claude-haiku-4-5"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestPersonalizerExpanded -v`
Expected: FAIL — `uses_web_search` is False and model is opus, not haiku.

- [ ] **Step 3: Update pitch_personalizer blueprint**

Rewrite `backend/agents/blueprints/sales/workforce/pitch_personalizer/agent.py`:

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
        "Profile finder and personalization specialist — discovers real prospects via web search, "
        "then adapts the storyline with specific details for each person"
    )
    tags = ["profiling", "personalization", "outreach", "research", "web-search"]
    default_model = "claude-haiku-4-5"
    uses_web_search = True
    skills = [
        {
            "name": "Person Discovery",
            "description": (
                "Find real, verifiable people via web search — LinkedIn, company sites, "
                "conference speakers, podcast guests, blog authors. Cross-reference sources."
            ),
        },
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
                "Adapt the narrative arc for each individual: personalize the hook, "
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
        return """You are a pitch personalizer. For ONE target area, you:
1. Find real people to reach out to via web search
2. Research each person's background and recent activity
3. Adapt the storyline for each person with specific details
4. Assign an outreach channel

## Step 1: Find Prospects
Search for real people matching the target area. Look at:
- LinkedIn profiles, company websites, conference speaker lists
- Podcast guests, blog authors, social media active users
- Prefer decision-makers and influencers over gatekeepers
- Prefer people who are publicly active — they engage with outreach

## Step 2: Profile Each Person
For each person found:
- Name, role, company
- LinkedIn URL or "not found"
- Recent activity (within 6 months)
- Qualification signals (positive, concerns, unknowns)

## Step 3: Personalize the Pitch
For each person, adapt the target area's narrative arc:

**Subject:** Person-specific subject line
**Body:** Plain text, 3-5 short paragraphs, under 200 words.
**Channel:** Assign from available outreach agents.

## Output Structure

For each person:

### [Person Name] — [Company]
- **Identifier:** email address (or handle for non-email channels)
- **Channel:** [assigned outreach agent type]
- **Subject:** [person-specific subject line]
- **Pitch:**
[Plain text pitch body]
- **Personalization notes:** [which specific details were used and why]

RULES:
1. MINIMUM 2 specific, verifiable details per person in the pitch body
2. Never use generic flattery or template-obvious phrasing
3. Subject lines must be specific to the person, not the campaign
4. Body must be plain text — no markdown, no HTML, no bullet points
5. Each pitch must reference the person's RECENT activity (within 6 months)
6. These must be REAL people findable via web search — do not fabricate profiles
7. If you cannot find enough real people, say so and explain what you tried"""

    personalize_pitches = personalize_pitches
    revise_pitches = revise_pitches

    def get_task_suffix(self, agent, task):
        return """# PERSONALIZATION METHODOLOGY

## Person Discovery
- Search LinkedIn, company websites, conference speaker lists, podcast guests, blog authors
- Look for people who are publicly active — they are more likely to engage
- Prefer decision-makers and influencers over gatekeepers
- Cross-reference to verify current role and company
- Aim for the target count specified — quality over quantity, but hit the number

## Research Per Person
- Search for their recent LinkedIn posts, blog articles, conference talks
- Check their company's recent news for relevant context
- Look for mutual connections, shared communities, or shared events
- Note their communication style from public content

## Adaptation Rules
- The hook must reference something THEY did or said
- The value proposition must be framed in THEIR vocabulary
- Proof points must be relevant to THEIR specific situation
- The CTA must match THEIR likely decision-making style

## Channel Assignment
- Review the available outreach agents listed in the task context
- Assign each person to the most effective channel
- If only email is available, assign all to email

## Quality Checks
- Each pitch has 2+ specific, verifiable person-details?
- Would the prospect recognize this was written specifically for them?
- Does it pass the "swap test"?
- Is the subject line specific enough?
- Is the body plain text, 3-5 paragraphs, under 200 words?"""
```

- [ ] **Step 4: Update personalize_pitches command**

Update `backend/agents/blueprints/sales/workforce/pitch_personalizer/commands/personalize_pitches.py`:

```python
"""Pitch Personalizer command: find profiles and personalize pitches for one target area."""

from agents.blueprints.base import command


@command(
    name="personalize-pitches",
    description=(
        "For one target area: find real prospects via web search, research each person, "
        "adapt the storyline, and assign outreach channels."
    ),
    model="claude-haiku-4-5",
)
def personalize_pitches(self, agent) -> dict:
    return {
        "exec_summary": "Find profiles and personalize pitches for target area",
        "step_plan": (
            "1. Review the target area brief and narrative arc\n"
            "2. Search for real people matching this target area via web search\n"
            "3. For each person: verify identity, research recent activity\n"
            "4. Adapt the storyline hook, value prop, and CTA for each person\n"
            "5. Assign outreach channel from available agents\n"
            "6. Output structured pitch payloads"
        ),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestPersonalizerExpanded -v`
Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/pitch_personalizer/
git commit -m "feat: pitch_personalizer absorbs profile_selector — web search + profiling"
```

---

### Task 5: Remove Pitch Architect and Profile Selector

**Files:**
- Delete: `backend/agents/blueprints/sales/workforce/pitch_architect/` (entire directory)
- Delete: `backend/agents/blueprints/sales/workforce/profile_selector/` (entire directory)
- Modify: `backend/agents/blueprints/__init__.py`
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Update registry — remove from __init__.py**

In `backend/agents/blueprints/__init__.py`, update the `_sales_imports` dict (lines 130-142). Remove `pitch_architect` and `profile_selector`:

```python
_sales_imports = {
    "researcher": ("agents.blueprints.sales.workforce.researcher", "ResearcherBlueprint"),
    "strategist": ("agents.blueprints.sales.workforce.strategist", "StrategistBlueprint"),
    "pitch_personalizer": ("agents.blueprints.sales.workforce.pitch_personalizer", "PitchPersonalizerBlueprint"),
    "sales_qa": ("agents.blueprints.sales.workforce.sales_qa", "SalesQaBlueprint"),
    "authenticity_analyst": (
        "agents.blueprints.sales.workforce.authenticity_analyst",
        "AuthenticityAnalystBlueprint",
    ),
    "email_outreach": ("agents.blueprints.sales.workforce.email_outreach", "EmailOutreachBlueprint"),
}
```

Also update the DEPARTMENTS description (line ~150):

```python
        "description": (
            "Outbound sales pipeline — industry research, target strategy with narrative design, "
            "parallel personalization via cloned agents, QA review loops, CSV-driven dispatch"
        ),
```

- [ ] **Step 2: Update test fixtures and assertions**

In `test_sales_department.py`:

Update `workforce` fixture — remove pitch_architect and profile_selector:

```python
@pytest.fixture
def workforce(department):
    """Create all workforce agents for the sales department."""
    agents = {}
    for slug in [
        "researcher",
        "strategist",
        "pitch_personalizer",
        "sales_qa",
        "email_outreach",
    ]:
        agents[slug] = Agent.objects.create(
            name=f"Test {slug}",
            agent_type=slug,
            department=department,
            status="active",
            outreach=(slug == "email_outreach"),
        )
    return agents
```

Update `TestSalesRegistry.test_sales_has_8_workforce_agents` → rename to `test_sales_has_6_workforce_agents`:

```python
    def test_sales_has_6_workforce_agents(self):
        dept = DEPARTMENTS["sales"]
        assert len(dept["workforce"]) == 6
```

Update `TestSalesRegistry.test_sales_workforce_slugs`:

```python
    def test_sales_workforce_slugs(self):
        slugs = set(DEPARTMENTS["sales"]["workforce"].keys())
        assert slugs == {
            "researcher",
            "strategist",
            "pitch_personalizer",
            "sales_qa",
            "authenticity_analyst",
            "email_outreach",
        }
```

Update `TestSalesBlueprintProperties`:

Remove `test_profile_selector_uses_haiku` test entirely.

Update `test_other_agents_use_sonnet` — remove pitch_architect and profile_selector:

```python
    def test_other_agents_use_sonnet(self):
        for slug in ["strategist", "sales_qa"]:
            bp = get_blueprint(slug, "sales")
            assert bp.default_model == "claude-opus-4-6", f"{slug} should use opus"
```

Update `test_non_reviewer_agents_have_no_dimensions` — remove pitch_architect and profile_selector:

```python
    def test_non_reviewer_agents_have_no_dimensions(self):
        for slug in ["researcher", "strategist", "pitch_personalizer"]:
            bp = get_blueprint(slug, "sales")
            assert bp.review_dimensions == [], f"{slug} should have no review_dimensions"
```

Update `test_each_agent_has_task_suffix` — remove pitch_architect and profile_selector:

```python
    def test_each_agent_has_task_suffix(self):
        for slug in [
            "researcher",
            "strategist",
            "pitch_personalizer",
            "sales_qa",
        ]:
```

- [ ] **Step 3: Delete pitch_architect and profile_selector directories**

```bash
rm -rf backend/agents/blueprints/sales/workforce/pitch_architect
rm -rf backend/agents/blueprints/sales/workforce/profile_selector
```

- [ ] **Step 4: Run all sales tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v -x`
Expected: Tests that reference old agents fail. Fix any remaining references.

- [ ] **Step 5: Fix any remaining test failures**

Update any remaining test references to pitch_architect or profile_selector. The `TestLeaderConstants` tests will fail because the pipeline constants still reference old agents — that's expected, we'll fix those in Task 6.

- [ ] **Step 6: Commit**

```bash
git add -A backend/agents/blueprints/sales/workforce/pitch_architect backend/agents/blueprints/sales/workforce/profile_selector backend/agents/blueprints/__init__.py backend/agents/tests/test_sales_department.py
git commit -m "feat: remove pitch_architect and profile_selector — absorbed into strategist and personalizer"
```

---

### Task 6: Rewrite Leader State Machine

**Files:**
- Modify: `backend/agents/blueprints/sales/leader/agent.py` (full rewrite)
- Test: `backend/agents/tests/test_sales_department.py`

This is the largest task. The leader's pipeline constants, state machine, and helper methods all change.

- [ ] **Step 1: Write failing tests for new pipeline**

Replace `TestLeaderConstants`, `TestSalesReviewPairs`, and `TestLeaderStateMachine` in `test_sales_department.py`. Also update imports at top of file:

Update the imports block at the top of the test file:

```python
from agents.blueprints.sales.leader.agent import (
    AGENT_FIX_COMMANDS,
    CHAIN_ORDER,
    DIMENSION_TO_AGENT,
    PIPELINE_STEPS,
    STEP_CONTEXT_SOURCES,
    STEP_TO_AGENT,
    STEP_TO_COMMAND,
    SalesLeaderBlueprint,
)
from agents.models import Agent, AgentTask, ClonedAgent
```

Replace the constant tests:

```python
class TestLeaderConstants:
    def test_pipeline_steps(self):
        assert PIPELINE_STEPS == [
            "research",
            "strategy",
            "personalization",
            "finalize",
            "qa_review",
            "dispatch",
        ]

    def test_all_steps_have_agent_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_AGENT

    def test_all_steps_have_command_mapping(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_TO_COMMAND

    def test_all_steps_have_context_sources(self):
        for step in PIPELINE_STEPS:
            assert step in STEP_CONTEXT_SOURCES

    def test_all_dimensions_map_to_chain_agents(self):
        for dim, agent_type in DIMENSION_TO_AGENT.items():
            assert agent_type in CHAIN_ORDER, f"{dim} maps to {agent_type} not in CHAIN_ORDER"
            assert agent_type in AGENT_FIX_COMMANDS, f"{agent_type} not in AGENT_FIX_COMMANDS"

    def test_chain_order_is_researcher_then_strategist(self):
        assert CHAIN_ORDER == ["researcher", "strategist"]

    def test_personalization_step_maps_to_personalizer(self):
        assert STEP_TO_AGENT["personalization"] == "pitch_personalizer"

    def test_finalize_step_maps_to_strategist(self):
        assert STEP_TO_AGENT["finalize"] == "strategist"

    def test_finalize_command_is_finalize_outreach(self):
        assert STEP_TO_COMMAND["finalize"] == "finalize-outreach"
```

Replace review pairs tests:

```python
class TestSalesReviewPairs:
    def test_has_one_review_pair(self):
        bp = SalesLeaderBlueprint()
        pairs = bp.get_review_pairs()
        assert len(pairs) == 1

    def test_creator_is_strategist(self):
        bp = SalesLeaderBlueprint()
        pair = bp.get_review_pairs()[0]
        assert pair["creator"] == "strategist"
        assert pair["creator_fix_command"] == "revise-strategy"

    def test_reviewer_is_sales_qa(self):
        bp = SalesLeaderBlueprint()
        pair = bp.get_review_pairs()[0]
        assert pair["reviewer"] == "sales_qa"
        assert pair["reviewer_command"] == "review-pipeline"
```

Replace state machine tests:

```python
@pytest.mark.django_db
class TestLeaderStateMachine:
    def test_starts_at_research(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "researcher"
        assert result["tasks"][0]["command_name"] == "research-industry"

    def test_advances_to_strategy(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Industry briefing here.",
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "research"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "draft-strategy"

    def test_strategy_context_includes_research(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Fintech is booming. Key players: Stripe, Plaid.",
        )
        result = bp._propose_step_task(leader, sprint, "strategy")
        step_plan = result["tasks"][0]["step_plan"]
        assert "Fintech is booming" in step_plan

    def test_strategy_context_includes_outreach_channels(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.DONE,
            report="Research output.",
        )
        result = bp._propose_step_task(leader, sprint, "strategy")
        step_plan = result["tasks"][0]["step_plan"]
        assert "email_outreach" in step_plan or "email" in step_plan

    def test_returns_none_without_sprints(self, leader, workforce):
        bp = SalesLeaderBlueprint()
        result = bp.generate_task_proposal(leader)
        assert result is None

    def test_waits_for_active_task(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        AgentTask.objects.create(
            agent=workforce["researcher"],
            sprint=sprint,
            command_name="research-industry",
            status=AgentTask.Status.PROCESSING,
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "research"}}
        leader.save(update_fields=["internal_state"])
        result = bp.generate_task_proposal(leader)
        assert result is None
```

Add fan-out tests:

```python
@pytest.mark.django_db
class TestFanOutPersonalization:
    def test_creates_clones_after_strategy(self, leader, sprint, workforce):
        """After strategy completes, leader creates clones and dispatches tasks."""
        bp = SalesLeaderBlueprint()

        # Strategy done with 3 target areas
        AgentTask.objects.create(
            agent=workforce["strategist"],
            sprint=sprint,
            command_name="draft-strategy",
            status=AgentTask.Status.DONE,
            report=(
                "### Target Area 1: Fintech CTOs\nDetails...\n\n"
                "### Target Area 2: SaaS Founders\nDetails...\n\n"
                "### Target Area 3: DevOps Leads\nDetails...\n"
            ),
        )
        leader.internal_state = {"pipeline_steps": {str(sprint.id): "strategy"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is not None
        # Should propose N tasks for N target areas
        assert len(result["tasks"]) == 3
        assert all(t["target_agent_type"] == "pitch_personalizer" for t in result["tasks"])
        assert all(t["command_name"] == "personalize-pitches" for t in result["tasks"])

        # Clones should be created
        clones = ClonedAgent.objects.filter(sprint=sprint)
        assert clones.count() == 3

    def test_waits_for_all_clones_before_finalize(self, leader, sprint, workforce):
        """Leader only advances to finalize when ALL clone tasks are done."""
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]

        # Create 2 clones
        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)

        # One done, one still processing
        AgentTask.objects.create(
            agent=parent, sprint=sprint, command_name="personalize-pitches",
            status=AgentTask.Status.DONE, report="Clone 0 output.", cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent, sprint=sprint, command_name="personalize-pitches",
            status=AgentTask.Status.PROCESSING, cloned_agent=clone1,
        )

        leader.internal_state = {"pipeline_steps": {str(sprint.id): "personalization"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is None  # Still waiting

    def test_advances_to_finalize_when_all_clones_done(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        parent = workforce["pitch_personalizer"]

        clone0 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)
        clone1 = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=1)

        AgentTask.objects.create(
            agent=parent, sprint=sprint, command_name="personalize-pitches",
            status=AgentTask.Status.DONE, report="Clone 0 output.", cloned_agent=clone0,
        )
        AgentTask.objects.create(
            agent=parent, sprint=sprint, command_name="personalize-pitches",
            status=AgentTask.Status.DONE, report="Clone 1 output.", cloned_agent=clone1,
        )

        leader.internal_state = {"pipeline_steps": {str(sprint.id): "personalization"}}
        leader.save(update_fields=["internal_state"])

        result = bp.generate_task_proposal(leader)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "finalize-outreach"
        # Context should include both clone outputs
        step_plan = result["tasks"][0]["step_plan"]
        assert "Clone 0 output" in step_plan
        assert "Clone 1 output" in step_plan
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestLeaderConstants agents/tests/test_sales_department.py::TestLeaderStateMachine agents/tests/test_sales_department.py::TestFanOutPersonalization -v -x`
Expected: FAIL — pipeline constants don't match yet.

- [ ] **Step 3: Rewrite the leader blueprint**

Rewrite `backend/agents/blueprints/sales/leader/agent.py`:

```python
from __future__ import annotations

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
    "personalization",  # fan-out step — N clones, one per target area
    "finalize",         # strategist consolidation → exec summary + CSV
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

# Maps QA dimensions to agent types for cascade fix routing
# Everything below researcher routes to strategist
DIMENSION_TO_AGENT = {
    "research_accuracy": "researcher",
    "strategy_quality": "strategist",
    "storyline_effectiveness": "strategist",
    "profile_accuracy": "strategist",
    "pitch_personalization": "strategist",
}

# Revision commands per agent (used when QA routes fixes)
AGENT_FIX_COMMANDS = {
    "researcher": "research-industry",
    "strategist": "revise-strategy",
}

CHAIN_ORDER = [
    "researcher",
    "strategist",
]

# Context injection: which prior steps feed into each step
STEP_CONTEXT_SOURCES = {
    "research": [],
    "strategy": ["research"],
    "personalization": ["research", "strategy"],  # each clone gets research + its target area slice
    "finalize": ["personalization"],  # all clone outputs
    "qa_review": ["research", "strategy", "finalize"],
    "dispatch": ["finalize"],
}

# Regex to parse target areas from strategist output
TARGET_AREA_PATTERN = re.compile(
    r"###\s*Target\s*Area\s*\d+[:\s]*(.*?)(?=###\s*Target\s*Area\s*\d+|###\s*Priority\s*Ranking|###\s*Risks|$)",
    re.DOTALL | re.IGNORECASE,
)

DEFAULT_PROFILES_PER_AREA = 50


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Head of Sales"
    slug = "leader"
    description = (
        "Sales department leader — orchestrates a fan-out pipeline from industry research "
        "through parallel personalization with QA feedback loop and CSV-driven dispatch"
    )
    tags = ["leadership", "strategy", "sales", "pipeline", "orchestration"]
    skills = [
        {
            "name": "Pipeline Orchestration",
            "description": (
                "Manage the sales pipeline: research → strategy → fan-out personalization → "
                "strategist consolidation → QA → CSV dispatch"
            ),
        },
        {
            "name": "QA Cascade Routing",
            "description": (
                "Route QA failures to the earliest failing agent: researcher or strategist. "
                "Strategist decides whether to revise strategy or re-invoke clones."
            ),
        },
        {
            "name": "Clone Lifecycle",
            "description": (
                "Create N cloned personalizer agents per target area, manage batch loops "
                "for profile count targets, destroy clones on sprint completion."
            ),
        },
    ]
    config_schema = {}

    def get_review_pairs(self):
        return [
            {
                "creator": "strategist",
                "creator_fix_command": "revise-strategy",
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

YOUR PIPELINE:
1. researcher: Industry research, competitive intel, market trends (web search)
2. strategist: Draft thesis with target areas + AIDA narrative arc per area
3. N × pitch_personalizer clones: One per target area — find profiles + personalize pitches (parallel)
4. strategist (finalize-outreach): Consolidate all clone outputs into exec summary + CSV
5. sales_qa: Multi-dimensional quality review of the entire pipeline
6. Outreach dispatch: Filter CSV by channel, send via matching outreach agents

REVIEW CHAIN (AUTOMATIC — do not manually manage reviews):
After strategist finalize-outreach completes, the system routes to sales_qa.
- Score >= 9.5/10 → approved, dispatch outreach
- Score >= 9.0 after 3 polish attempts → accept (diminishing returns)
- Score < threshold → route fix to researcher or strategist

CLONE LIFECYCLE:
- After strategist draft-strategy, parse target areas and create N clones
- Each clone runs personalize-pitches for its target area
- When all clones complete, advance to finalize-outreach
- Clones are destroyed when sprint completes

You don't write pitches or do research directly — you create tasks for your workforce."""

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """Pipeline state machine — proposes next step in the sales chain."""
        # 1. Check for review cycle triggers first
        review_result = self._check_review_trigger(agent)
        if review_result:
            return review_result

        # 2. Find the active sprint
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
            current_step = "research"
            pipeline_steps[sprint_id] = current_step
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

        # 4. Route to step-specific handler
        if current_step == "personalization":
            return self._handle_personalization_step(
                agent, sprint, sprint_id, internal_state, pipeline_steps
            )
        if current_step == "dispatch":
            return self._handle_dispatch_step(
                agent, sprint, sprint_id, internal_state, pipeline_steps
            )

        # 5. Handle linear steps (research, strategy, finalize, qa_review)
        return self._handle_linear_step(
            agent, sprint, sprint_id, internal_state, pipeline_steps, current_step
        )

    def _handle_linear_step(
        self, agent, sprint, sprint_id, internal_state, pipeline_steps, current_step
    ) -> dict | None:
        """Handle a linear (non-fan-out) pipeline step."""
        from agents.models import AgentTask

        step_agent_type = STEP_TO_AGENT.get(current_step)
        step_command = STEP_TO_COMMAND.get(current_step)
        department = agent.department

        if not step_agent_type:
            return None

        step_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type=step_agent_type,
                agent__department=department,
                command_name=step_command,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        # For qa_review: DONE + CHANGES_REQUESTED means review loop handles it
        if (
            step_task
            and current_step == "qa_review"
            and step_task.review_verdict == "CHANGES_REQUESTED"
        ):
            return None

        if not step_task:
            # Check if already in progress
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
                return None

            return self._propose_step_task(agent, sprint, current_step)

        # Step done — persist document if applicable, then advance
        self._persist_step_document(agent, sprint, current_step)
        return self._advance_pipeline(
            agent, sprint, sprint_id, internal_state, pipeline_steps, current_step
        )

    def _advance_pipeline(
        self, agent, sprint, sprint_id, internal_state, pipeline_steps, current_step
    ) -> dict | None:
        """Advance to the next pipeline step."""
        step_idx = PIPELINE_STEPS.index(current_step)
        if step_idx + 1 >= len(PIPELINE_STEPS):
            return None

        next_step = PIPELINE_STEPS[step_idx + 1]
        pipeline_steps[sprint_id] = next_step
        internal_state["pipeline_steps"] = pipeline_steps
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        if next_step == "personalization":
            return self._handle_personalization_step(
                agent, sprint, sprint_id, internal_state, pipeline_steps
            )
        if next_step == "dispatch":
            return self._handle_dispatch_step(
                agent, sprint, sprint_id, internal_state, pipeline_steps
            )

        return self._propose_step_task(agent, sprint, next_step)

    # ── Fan-out: personalization ───────────────────────────────────────

    def _handle_personalization_step(
        self, agent, sprint, sprint_id, internal_state, pipeline_steps
    ) -> dict | None:
        """Handle the fan-out personalization step — create clones, dispatch, join."""
        from agents.models import AgentTask, ClonedAgent

        department = agent.department
        clones = list(ClonedAgent.objects.filter(sprint=sprint, parent__department=department))

        if not clones:
            # First entry — parse target areas and create clones
            return self._create_clones_and_dispatch(agent, sprint, sprint_id, internal_state, pipeline_steps)

        # Check if all clone tasks are done
        clone_tasks = AgentTask.objects.filter(
            sprint=sprint,
            cloned_agent__in=clones,
            command_name="personalize-pitches",
        )
        done_tasks = clone_tasks.filter(status=AgentTask.Status.DONE)
        active_tasks = clone_tasks.filter(
            status__in=[
                AgentTask.Status.PROCESSING,
                AgentTask.Status.QUEUED,
                AgentTask.Status.AWAITING_APPROVAL,
                AgentTask.Status.PLANNED,
            ]
        )

        if active_tasks.exists():
            return None  # Still running

        if done_tasks.count() >= len(clones):
            # All done — advance to finalize
            return self._advance_pipeline(
                agent, sprint, sprint_id, internal_state, pipeline_steps, "personalization"
            )

        # Some clones have no task yet (shouldn't happen normally, but handle it)
        clones_with_tasks = set(clone_tasks.values_list("cloned_agent_id", flat=True))
        unassigned = [c for c in clones if c.id not in clones_with_tasks]
        if unassigned:
            return self._dispatch_clone_tasks(agent, sprint, unassigned)

        return None

    def _create_clones_and_dispatch(
        self, agent, sprint, sprint_id, internal_state, pipeline_steps
    ) -> dict | None:
        """Parse target areas from strategy, create clones, dispatch tasks."""
        from agents.models import AgentTask

        department = agent.department

        strategy_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=department,
                command_name="draft-strategy",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        if not strategy_task or not strategy_task.report:
            logger.warning("SALES_NO_STRATEGY sprint=%s — cannot create clones", sprint_id[:8])
            return None

        # Parse target areas
        target_areas = self._parse_target_areas(strategy_task.report)
        if not target_areas:
            logger.warning(
                "SALES_NO_TARGET_AREAS sprint=%s — could not parse target areas from strategy",
                sprint_id[:8],
            )
            return None

        # Get research output for context injection
        research_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="researcher",
                agent__department=department,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        research_output = research_task.report if research_task else "No research output."

        # Get available outreach channels
        outreach_agents = list(
            department.agents.filter(outreach=True, status="active").values_list("agent_type", "name")
        )
        channels_text = ", ".join(f"{name} ({atype})" for atype, name in outreach_agents) if outreach_agents else "email"

        # Create clones
        personalizer = department.agents.filter(agent_type="pitch_personalizer", status="active").first()
        if not personalizer:
            logger.warning("SALES_NO_PERSONALIZER sprint=%s", sprint_id[:8])
            return None

        clones = self.create_clones(
            personalizer,
            len(target_areas),
            sprint,
            initial_state={"target_count": DEFAULT_PROFILES_PER_AREA},
        )

        # Build tasks — one per clone with its target area slice
        tasks = []
        for clone, (area_name, area_content) in zip(clones, target_areas):
            tasks.append(
                {
                    "target_agent_type": "pitch_personalizer",
                    "command_name": "personalize-pitches",
                    "exec_summary": f"Personalize pitches — {area_name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Research Output\n{research_output}\n\n"
                        f"## Your Target Area\n{area_content}\n\n"
                        f"## Available Outreach Channels\n{channels_text}\n\n"
                        f"Find real prospects for this target area and personalize pitches for each."
                    ),
                    "depends_on_previous": False,
                    "_cloned_agent_id": str(clone.id),
                }
            )

        return {
            "exec_summary": f"Fan-out personalization — {len(target_areas)} target areas",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _dispatch_clone_tasks(self, agent, sprint, clones) -> dict:
        """Dispatch tasks for clones that don't have one yet."""
        tasks = []
        for clone in clones:
            tasks.append(
                {
                    "target_agent_type": "pitch_personalizer",
                    "command_name": "personalize-pitches",
                    "exec_summary": f"Personalize pitches — clone {clone.clone_index}",
                    "step_plan": "Execute personalization for your assigned target area.",
                    "depends_on_previous": False,
                    "_cloned_agent_id": str(clone.id),
                }
            )
        return {
            "exec_summary": f"Dispatch {len(clones)} remaining clone tasks",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    def _parse_target_areas(self, strategy_report: str) -> list[tuple[str, str]]:
        """Parse target areas from strategy report. Returns [(name, full_content), ...]."""
        matches = list(TARGET_AREA_PATTERN.finditer(strategy_report))
        if not matches:
            return []

        areas = []
        for match in matches:
            name = match.group(1).strip().split("\n")[0].strip()
            content = match.group(0).strip()
            if name:
                areas.append((name, content))
        return areas

    # ── Finalize step context ──────────────────────────────────────────

    def _propose_step_task(self, agent: Agent, sprint, step: str) -> dict:
        """Propose a task for a specific pipeline step, injecting context from prior steps."""
        from agents.models import AgentTask, ClonedAgent

        agent_type = STEP_TO_AGENT[step]
        command_name = STEP_TO_COMMAND[step]

        # Gather context from prior steps
        context_parts = []
        source_steps = STEP_CONTEXT_SOURCES.get(step, [])

        for src_step in source_steps:
            if src_step == "personalization":
                # Gather all clone outputs
                clone_tasks = AgentTask.objects.filter(
                    sprint=sprint,
                    cloned_agent__sprint=sprint,
                    command_name="personalize-pitches",
                    status=AgentTask.Status.DONE,
                ).select_related("cloned_agent")

                for ct in clone_tasks:
                    label = f"Personalizer Clone {ct.cloned_agent.clone_index}" if ct.cloned_agent else "Personalizer"
                    if ct.report:
                        context_parts.append(f"## {label} Output\n{ct.report}")
            else:
                src_agent_type = STEP_TO_AGENT[src_step]
                src_command = STEP_TO_COMMAND[src_step]
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

        context_text = "\n\n".join(context_parts) if context_parts else "No prior step output yet."

        # For strategy step, inject outreach channels
        extra_context = ""
        if step == "strategy":
            outreach_agents = list(
                agent.department.agents.filter(outreach=True, status="active").values_list("agent_type", "name")
            )
            if outreach_agents:
                agents_list = ", ".join(f"{name} ({atype})" for atype, name in outreach_agents)
                extra_context = f"\n\n## Available Outreach Channels\nAvailable channels for assignment: {agents_list}"

        step_plan = (
            f"## Sprint Instruction\n{sprint.text}\n\n"
            f"## Prior Pipeline Output\n{context_text}"
            f"{extra_context}\n\n"
            f"Execute your command based on the above context."
        )

        tasks = [
            {
                "target_agent_type": agent_type,
                "command_name": command_name,
                "exec_summary": f"Sales pipeline — {step.replace('_', ' ')}",
                "step_plan": step_plan,
                "depends_on_previous": False,
            },
        ]

        # During QA review, also dispatch authenticity analyst if available
        if step == "qa_review":
            active_types = set(
                agent.department.agents.filter(
                    status="active", is_leader=False
                ).values_list("agent_type", flat=True)
            )
            if "authenticity_analyst" in active_types:
                tasks.append(
                    {
                        "target_agent_type": "authenticity_analyst",
                        "command_name": "analyze",
                        "exec_summary": "Authenticity check — detect AI-generated patterns",
                        "step_plan": (
                            f"## Pipeline Output to Analyze\n{context_text}\n\n"
                            f"Analyze the personalized pitch texts for AI-generated patterns. "
                            f"Focus on: linguistic tells, voice flattening, cliche patterns."
                        ),
                        "depends_on_previous": False,
                    }
                )

        return {
            "exec_summary": f"Sales pipeline step: {step.replace('_', ' ')}",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    # ── Dispatch ───────────────────────────────────────────────────────

    def _handle_dispatch_step(
        self, agent: Agent, sprint, sprint_id: str, internal_state: dict, pipeline_steps: dict
    ) -> dict | None:
        """Handle the dispatch step — parse CSV, filter by channel, send to outreach agents."""
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask
        from projects.models import Sprint

        department = agent.department
        outreach_agents = list(department.agents.filter(outreach=True, status=AgentModel.Status.ACTIVE))
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
            # All dispatched — write outputs and mark sprint done
            self._write_sprint_output(agent, sprint)
            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = "Sales pipeline complete — outreach dispatched."
            sprint.completed_at = timezone.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

            from projects.views.sprint_view import _broadcast_sprint

            _broadcast_sprint(sprint, "sprint.updated")
            logger.info("SALES_SPRINT_DONE dept=%s sprint=%s", department.name, sprint.text[:60])

            # Clean up
            pipeline_steps.pop(sprint_id, None)
            internal_state["pipeline_steps"] = pipeline_steps
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            self.destroy_sprint_clones(sprint)
            return None

        if not outreach_tasks.exists():
            return self._propose_dispatch_tasks(agent, sprint, outreach_agents)

        return None

    def _propose_dispatch_tasks(self, agent: Agent, sprint, outreach_agents) -> dict:
        """Propose outreach tasks — parse CSV, filter by channel, one task per agent."""
        from agents.models import AgentTask

        # Get the finalize-outreach output (contains exec summary + CSV)
        finalize_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=agent.department,
                command_name="finalize-outreach",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        finalize_output = finalize_task.report if finalize_task else "No finalize output."

        tasks = []
        for outreach_agent in outreach_agents:
            tasks.append(
                {
                    "target_agent_type": outreach_agent.agent_type,
                    "command_name": "send-outreach",
                    "exec_summary": f"Send outreach via {outreach_agent.name}",
                    "step_plan": (
                        f"## Sprint Instruction\n{sprint.text}\n\n"
                        f"## Approved Pipeline Output\n{finalize_output}\n\n"
                        f"Send all pitches assigned to your channel ({outreach_agent.agent_type}). "
                        f"The CSV contains rows with channel, identifier, subject, content. "
                        f"Filter for rows where channel matches your agent type and send each one."
                    ),
                    "depends_on_previous": False,
                }
            )

        return {
            "exec_summary": "Dispatch approved pitches to outreach agents",
            "_sprint_id": str(sprint.id),
            "tasks": tasks,
        }

    # ── QA cascade ─────────────────────────────────────────────────────

    def _propose_fix_task(
        self, agent: Agent, review_task: AgentTask, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """Override: route QA fixes to earliest failing agent (researcher or strategist)."""
        report = review_task.report or ""

        earliest_failing = self._find_earliest_failing_agent(report, score)

        if earliest_failing is None:
            earliest_failing = "strategist"

        fix_command = AGENT_FIX_COMMANDS.get(earliest_failing, "revise-strategy")
        polish_msg = f" (polish {polish_count}/3)" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

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
                        f"Address the issues in your area. If personalization clones need "
                        f"to re-run, indicate which target areas need revision in your output."
                    ),
                    "depends_on_previous": False,
                },
            ],
        }

    def _find_earliest_failing_agent(self, report: str, overall_score: float) -> str | None:
        """Parse QA report for per-dimension scores, return earliest failing agent."""
        failing_agents = []

        for dimension, agent_type in DIMENSION_TO_AGENT.items():
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

        for agent_type in CHAIN_ORDER:
            if agent_type in failing_agents:
                return agent_type

        return failing_agents[0]

    # ── Document & output persistence ──────────────────────────────────

    def _persist_step_document(self, agent: Agent, sprint, step: str) -> None:
        """Persist research and strategy outputs as Department Documents."""
        from agents.models import AgentTask
        from projects.models import Document

        doc_types = {
            "research": (Document.DocType.RESEARCH, "Industry Research Briefing"),
            "strategy": (Document.DocType.STRATEGY, "Target Area Strategy & Narrative"),
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

    def _write_sprint_output(self, agent: Agent, sprint) -> None:
        """Write sprint Outputs — exec summary + CSV + delivery reports."""
        from agents.models import AgentTask
        from projects.models import Output

        # Exec summary output
        finalize_task = (
            AgentTask.objects.filter(
                sprint=sprint,
                agent__agent_type="strategist",
                agent__department=agent.department,
                command_name="finalize-outreach",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )

        if finalize_task and finalize_task.report:
            # Try to extract exec summary and CSV from the report
            report = finalize_task.report

            if not Output.objects.filter(
                sprint=sprint, department=agent.department, label="exec-summary"
            ).exists():
                Output.objects.create(
                    sprint=sprint,
                    department=agent.department,
                    title=f"Exec Summary — {sprint.text[:80]}",
                    label="exec-summary",
                    output_type=Output.OutputType.MARKDOWN,
                    content=report,
                    created_by_task=finalize_task,
                )

        # Delivery reports from outreach agents
        outreach_tasks = AgentTask.objects.filter(
            sprint=sprint,
            agent__department=agent.department,
            agent__outreach=True,
            status=AgentTask.Status.DONE,
        )

        if not Output.objects.filter(
            sprint=sprint, department=agent.department, label="outreach"
        ).exists():
            report_parts = ["# Sales Outreach — Delivery Report\n"]
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v -x`
Expected: All tests PASS including new fan-out tests.

- [ ] **Step 5: Fix any remaining test failures**

Address any import errors, fixture mismatches, or assertion failures. The QA cascade tests need updating too — update `TestQACascadeRouting`:

```python
@pytest.mark.django_db
class TestQACascadeRouting:
    def test_find_earliest_failing_agent_researcher(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 7.5/10\nstrategy_quality: 9.5/10\nstoryline_effectiveness: 9.5/10\nprofile_accuracy: 9.5/10\npitch_personalization: 9.5/10"
        result = bp._find_earliest_failing_agent(report, 7.5)
        assert result == "researcher"

    def test_find_earliest_failing_agent_strategist(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 9.5/10\nstrategy_quality: 7.0/10\nstoryline_effectiveness: 9.5/10\nprofile_accuracy: 8.0/10\npitch_personalization: 9.5/10"
        result = bp._find_earliest_failing_agent(report, 7.0)
        assert result == "strategist"

    def test_find_earliest_failing_agent_returns_none_when_all_pass(self, leader):
        bp = SalesLeaderBlueprint()
        report = "research_accuracy: 9.5/10\nstrategy_quality: 9.5/10"
        result = bp._find_earliest_failing_agent(report, 9.5)
        assert result is None

    def test_propose_fix_task_routes_to_earliest(self, leader, sprint, workforce):
        bp = SalesLeaderBlueprint()
        review_task = AgentTask.objects.create(
            agent=workforce["sales_qa"],
            sprint=sprint,
            command_name="review-pipeline",
            status=AgentTask.Status.DONE,
            report="research_accuracy: 7.0/10\nstrategy_quality: 9.5/10\nstoryline_effectiveness: 9.5/10\nprofile_accuracy: 9.5/10\npitch_personalization: 9.5/10",
            review_verdict="CHANGES_REQUESTED",
            review_score=7.0,
        )
        result = bp._propose_fix_task(leader, review_task, 7.0, 1, 0)
        assert result is not None
        assert result["tasks"][0]["target_agent_type"] == "researcher"
        assert result["tasks"][0]["command_name"] == "research-industry"

    def test_propose_fix_task_fallback_to_strategist(self, leader, sprint, workforce):
        """When no dimension scores can be parsed, falls back to strategist."""
        bp = SalesLeaderBlueprint()
        review_task = AgentTask.objects.create(
            agent=workforce["sales_qa"],
            sprint=sprint,
            command_name="review-pipeline",
            status=AgentTask.Status.DONE,
            report="Needs improvement overall.",
            review_verdict="CHANGES_REQUESTED",
            review_score=8.0,
        )
        result = bp._propose_fix_task(leader, review_task, 8.0, 1, 0)
        assert result["tasks"][0]["target_agent_type"] == "strategist"
        assert result["tasks"][0]["command_name"] == "revise-strategy"
```

Also update `TestDocumentPersistence.test_other_steps_dont_create_documents` — change `"pitch_design"` to `"personalization"`:

```python
    def test_other_steps_dont_create_documents(self, leader, sprint, workforce):
        from projects.models import Document
        bp = SalesLeaderBlueprint()
        count_before = Document.objects.count()
        bp._persist_step_document(leader, sprint, "personalization")
        assert Document.objects.count() == count_before
```

- [ ] **Step 6: Run full test suite**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/sales/leader/agent.py backend/agents/tests/test_sales_department.py
git commit -m "feat: rewrite sales leader — fan-out clones, strategist consolidation, CSV dispatch"
```

---

### Task 7: Wire ClonedAgent FK in Task Creation

**Files:**
- Modify: `backend/agents/tasks.py:407-416`
- Test: `backend/agents/tests/test_sales_department.py`

The `create_next_leader_task` function in `tasks.py` creates `AgentTask` objects from proposal dicts but doesn't handle the `_cloned_agent_id` field that the leader's fan-out puts in task proposals.

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.django_db
class TestClonedAgentTaskCreation:
    def test_clone_task_has_cloned_agent_fk(self, leader, sprint, workforce):
        """When leader proposes a task with _cloned_agent_id, the FK is set."""
        from agents.models import ClonedAgent

        parent = workforce["pitch_personalizer"]
        clone = ClonedAgent.objects.create(parent=parent, sprint=sprint, clone_index=0)

        # Simulate what create_next_leader_task does
        task = AgentTask.objects.create(
            agent=parent,
            created_by_agent=leader,
            status=AgentTask.Status.AWAITING_APPROVAL,
            command_name="personalize-pitches",
            sprint=sprint,
            exec_summary="Test clone task",
            cloned_agent=clone,
        )
        task.refresh_from_db()
        assert task.cloned_agent_id == clone.id
```

- [ ] **Step 2: Run test to verify it passes**

This test should already pass since the FK exists from Task 1. The real change is in `tasks.py`.

- [ ] **Step 3: Modify task creation in tasks.py**

In `backend/agents/tasks.py`, around line 407-416 where `AgentTask.objects.create(...)` is called, add the `cloned_agent` field:

Find this block:
```python
                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    sprint_id=sprint_id,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                )
```

Replace with:
```python
                # Resolve cloned_agent FK if provided by fan-out proposals
                cloned_agent_id = task_data.get("_cloned_agent_id")
                cloned_agent = None
                if cloned_agent_id:
                    from agents.models import ClonedAgent
                    cloned_agent = ClonedAgent.objects.filter(id=cloned_agent_id).first()

                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    sprint_id=sprint_id,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                    cloned_agent=cloned_agent,
                )
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v -x`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/tasks.py backend/agents/tests/test_sales_department.py
git commit -m "feat: wire cloned_agent FK in leader task creation"
```

---

### Task 8: Verify Sales QA Dimensions

**Files:**
- Modify: `backend/agents/blueprints/sales/workforce/sales_qa/agent.py`
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write failing test**

Update `TestSalesBlueprintProperties.test_sales_qa_has_5_review_dimensions`:

```python
    def test_sales_qa_has_5_review_dimensions(self):
        bp = get_blueprint("sales_qa", "sales")
        assert bp.review_dimensions == [
            "research_accuracy",
            "strategy_quality",
            "storyline_effectiveness",
            "profile_accuracy",
            "pitch_personalization",
        ]
```

This test actually stays the same — QA still scores 5 dimensions, just the routing changed. No changes needed to the QA blueprint itself. The dimension names are the same; only the DIMENSION_TO_AGENT mapping in the leader changed.

- [ ] **Step 2: Verify QA tests still pass**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v -k "qa" `
Expected: All QA tests PASS.

- [ ] **Step 3: Commit (if any changes)**

Only commit if changes were needed. Otherwise skip.

---

### Task 9: Integration Test — Target Area Parsing

**Files:**
- Test: `backend/agents/tests/test_sales_department.py`

- [ ] **Step 1: Write integration test for target area parsing**

```python
@pytest.mark.django_db
class TestTargetAreaParsing:
    def test_parse_3_target_areas(self):
        bp = SalesLeaderBlueprint()
        report = (
            "## Strategic Thesis\nSome thesis here.\n\n"
            "### Target Area 1: Fintech CTOs\nScope: CFOs at fintech...\nRationale: Growing market...\n\n"
            "### Target Area 2: SaaS Founders\nScope: Series A founders...\nRationale: Scaling needs...\n\n"
            "### Target Area 3: DevOps Leads\nScope: Platform engineering...\nRationale: Cloud migration...\n\n"
            "### Priority Ranking\n1. Fintech CTOs\n2. SaaS Founders\n3. DevOps Leads\n"
        )
        areas = bp._parse_target_areas(report)
        assert len(areas) == 3
        assert areas[0][0] == "Fintech CTOs"
        assert areas[1][0] == "SaaS Founders"
        assert areas[2][0] == "DevOps Leads"
        assert "Growing market" in areas[0][1]

    def test_parse_empty_report(self):
        bp = SalesLeaderBlueprint()
        areas = bp._parse_target_areas("")
        assert areas == []

    def test_parse_no_target_areas(self):
        bp = SalesLeaderBlueprint()
        areas = bp._parse_target_areas("Just some text without target areas.")
        assert areas == []
```

- [ ] **Step 2: Run the test**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py::TestTargetAreaParsing -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/agents/tests/test_sales_department.py
git commit -m "test: integration tests for target area parsing and full pipeline"
```

---

### Task 10: Not Included — Batch Loop for Scaling

The spec describes re-invoking clones that haven't hit their target profile count. This is an optimization layer on top of the fan-out/join that can be added after the base pipeline is working and tested end-to-end. The base pipeline creates clones, each produces profiles in one pass, and the strategist consolidates. If volume is insufficient, the batch loop can be added as a follow-up task without changing the pipeline shape.

---

### Task 11: Run Full Test Suite + Cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run the complete sales test suite**

Run: `cd backend && python -m pytest agents/tests/test_sales_department.py -v`
Expected: All tests PASS.

- [ ] **Step 2: Run full project test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: No regressions.

- [ ] **Step 3: Verify deleted directories are gone**

```bash
ls backend/agents/blueprints/sales/workforce/pitch_architect 2>&1 || echo "DELETED OK"
ls backend/agents/blueprints/sales/workforce/profile_selector 2>&1 || echo "DELETED OK"
```

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git status
# Only commit if there are changes
```

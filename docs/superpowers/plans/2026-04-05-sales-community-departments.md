# Sales & Community Departments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new generic departments (Sales + Community & Partnerships) with writer/reviewer pairs and ping-pong quality loops.

**Architecture:** Each department follows the existing blueprint pattern: leader + workforce agents, each with commands and skills. Both departments are registered in `__init__.py` using the lazy import pattern. The leader orchestrates writer→reviewer ping-pong loops via task delegation.

**Tech Stack:** Django, existing blueprint base classes (`LeaderBlueprint`, `WorkforceBlueprint`), `@command` decorator, `call_claude`, skill auto-discovery.

**Important patterns to follow (from existing codebase):**
- Skills are just `NAME = "..."` / `DESCRIPTION = "..."` files, auto-discovered by `skills/__init__.py`
- Commands use `@command(name=..., description=..., schedule=..., model=...)` and return `{"exec_summary": ..., "step_plan": ...}`
- Leader `execute_task()` calls Claude, parses JSON with `delegated_tasks` and `follow_up`, creates `AgentTask` records
- Workforce `execute_task()` calls Claude with methodology suffix, returns report string
- `__init__.py` files export the blueprint class

---

### Task 1: Sales Department — Leader (Sales Director)

**Files:**
- Create: `backend/agents/blueprints/sales/__init__.py`
- Create: `backend/agents/blueprints/sales/leader/__init__.py`
- Create: `backend/agents/blueprints/sales/leader/agent.py`
- Create: `backend/agents/blueprints/sales/leader/commands/__init__.py`
- Create: `backend/agents/blueprints/sales/leader/commands/plan_pipeline.py`
- Create: `backend/agents/blueprints/sales/leader/commands/check_progress.py`
- Create: `backend/agents/blueprints/sales/leader/skills/__init__.py`
- Create: `backend/agents/blueprints/sales/leader/skills/pipeline_management.py`
- Create: `backend/agents/blueprints/sales/leader/skills/target_prioritization.py`
- Create: `backend/agents/blueprints/sales/leader/skills/review_orchestration.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/leader/{commands,skills}
```

- [ ] **Step 2: Create `sales/__init__.py`**

```python
```

(Empty file — department init is just a package marker.)

- [ ] **Step 3: Create `sales/leader/__init__.py`**

```python
from .agent import SalesLeaderBlueprint

__all__ = ["SalesLeaderBlueprint"]
```

- [ ] **Step 4: Create skills files**

`sales/leader/skills/__init__.py`:
```python
"""Sales leader skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`sales/leader/skills/pipeline_management.py`:
```python
NAME = "Pipeline Management"
DESCRIPTION = "Track prospects through stages: identified → researched → contacted → negotiating → closed"
```

`sales/leader/skills/target_prioritization.py`:
```python
NAME = "Target Prioritization"
DESCRIPTION = "Score and rank targets by strategic fit, revenue potential, and reachability"
```

`sales/leader/skills/review_orchestration.py`:
```python
NAME = "Review Orchestration"
DESCRIPTION = "Manage writer/reviewer ping-pong loops — route drafts to reviewers, route feedback to writers, enforce quality thresholds"
```

- [ ] **Step 5: Create command files**

`sales/leader/commands/__init__.py`:
```python
"""Sales leader commands registry."""
from .plan_pipeline import plan_pipeline
from .check_progress import check_progress

ALL_COMMANDS = [plan_pipeline, check_progress]
```

`sales/leader/commands/plan_pipeline.py`:
```python
"""Sales leader command: daily pipeline planning."""
from agents.blueprints.base import command


@command(
    name="plan-pipeline",
    description=(
        "Daily pipeline review that assesses current prospects, identifies the highest-value targets to pursue, "
        "and delegates research tasks to the Prospector and outreach tasks to the Outreach Writer. Monitors "
        "review loop status and triggers reviewer tasks for completed drafts. Advances pipeline stages when "
        "reviewers approve work."
    ),
    schedule="daily",
    model="claude-sonnet-4-6",
)
def plan_pipeline(self, agent) -> dict:
    return {
        "exec_summary": "Review pipeline and plan today's prospecting and outreach activities",
        "step_plan": (
            "1. Review current pipeline state — prospects in each stage\n"
            "2. Identify highest-value targets to research or contact today\n"
            "3. Create research tasks for Prospector on new targets\n"
            "4. Create outreach tasks for Outreach Writer on researched prospects\n"
            "5. Route completed drafts to reviewers for quality check"
        ),
    }
```

`sales/leader/commands/check_progress.py`:
```python
"""Sales leader command: hourly progress check."""
from agents.blueprints.base import command


@command(
    name="check-progress",
    description=(
        "Hourly health check monitoring stalled review loops, overdue follow-ups, and idle agents. "
        "Detects completed writer tasks that need reviewer assignment, stalled tasks older than 3 hours, "
        "and review loops exceeding 3 rounds. Escalates blockers to the leader for intervention."
    ),
    schedule="hourly",
    model="claude-haiku-4-5",
)
def check_progress(self, agent) -> dict:
    return {
        "exec_summary": "Check pipeline health — stalled tasks, pending reviews, idle agents",
        "step_plan": (
            "1. Find completed writer tasks without reviewer assignment\n"
            "2. Detect stalled tasks (processing > 3h)\n"
            "3. Check review loops exceeding 3 rounds\n"
            "4. Report pipeline counts by stage"
        ),
    }
```

- [ ] **Step 6: Create leader agent**

`sales/leader/agent.py`:
```python
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from django.utils import timezone

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.sales.leader.commands import plan_pipeline, check_progress
from agents.blueprints.sales.leader.skills import format_skills

logger = logging.getLogger(__name__)


class SalesLeaderBlueprint(LeaderBlueprint):
    name = "Sales Director"
    slug = "leader"
    description = "Sales department leader — orchestrates prospecting, outreach, and review cycles to build a qualified pipeline"
    tags = ["leadership", "strategy", "sales", "pipeline", "prospecting"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are the sales department director. You orchestrate outbound prospecting and outreach by coordinating your workforce agents: Prospector, Prospect Analyst, Outreach Writer, and Outreach Reviewer.

Your core responsibilities:
1. Plan daily pipeline activities — who to research, who to contact
2. Delegate research tasks to the Prospector for target qualification
3. Route completed prospect lists to the Prospect Analyst for review
4. Delegate outreach drafting to the Outreach Writer for qualified prospects
5. Route completed drafts to the Outreach Reviewer for quality check
6. Manage the review ping-pong loop: if a reviewer sends work back, create a revision task for the writer with the feedback

Review loop rules:
- When a writer task completes, create a review task for the paired reviewer
- If the reviewer's verdict is "revision_needed", create a revision task back to the writer with the reviewer's feedback
- If the reviewer's verdict is "approved", advance the pipeline stage
- Maximum 3 review rounds — after that, escalate to human approval

You don't prospect or write outreach directly — you create tasks for your workforce."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands
    plan_pipeline = plan_pipeline
    check_progress = check_progress

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask as TaskModel

        workforce = list(
            agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        delegation_suffix = f"""# Workforce Agents
{workforce_desc}

When delegating work, include delegated_tasks in your response.
For review loops: when a writer task is done, delegate to the paired reviewer.
When a reviewer approves, advance the pipeline. When they reject, send revision back to the writer.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type slug",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed instructions including any reviewer feedback to address",
            "auto_execute": false,
            "proposed_exec_at": "ISO datetime or null"
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 7
    }},
    "report": "Summary of what was decided and why"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=delegation_suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)
            follow_up = data.get("follow_up")

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department, status="active", is_leader=False,
                )
                agents_by_type = {a.agent_type: a for a in workforce_agents}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = agents_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active workforce agent of type %s", target_type)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED if dt.get("auto_execute") else TaskModel.Status.AWAITING_APPROVAL,
                        auto_execute=bool(dt.get("auto_execute")),
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )

                    if dt.get("auto_execute"):
                        from agents.tasks import execute_agent_task
                        execute_agent_task.delay(str(sub_task.id))

                    logger.info("Sales leader delegated task %s to %s", sub_task.id, target_agent.name)

            if follow_up and follow_up.get("days_from_now"):
                days = follow_up["days_from_now"]
                TaskModel.objects.create(
                    agent=agent,
                    status=TaskModel.Status.AWAITING_APPROVAL,
                    exec_summary=follow_up.get("exec_summary", f"Follow-up in {days} days"),
                    step_plan=f"Review and assess. Original task: {task.exec_summary[:200]}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.plan_pipeline(agent)
```

- [ ] **Step 7: Verify imports work**

Run: `cd backend && source ../venv312/bin/activate && python -c "from agents.blueprints.sales.leader import SalesLeaderBlueprint; print(SalesLeaderBlueprint().name)"`
Expected: `Sales Director`

- [ ] **Step 8: Commit**

```bash
git add backend/agents/blueprints/sales/
git commit -m "feat(sales): add Sales Director leader blueprint with pipeline planning"
```

---

### Task 2: Sales Department — Prospector + Prospect Analyst (writer/reviewer pair)

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/__init__.py`
- Create: `backend/agents/blueprints/sales/workforce/prospector/` (full agent structure)
- Create: `backend/agents/blueprints/sales/workforce/prospect_analyst/` (full agent structure)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/prospector/{commands,skills}
mkdir -p backend/agents/blueprints/sales/workforce/prospect_analyst/{commands,skills}
```

- [ ] **Step 2: Create `workforce/__init__.py`**

```python
```

(Empty package marker.)

- [ ] **Step 3: Create Prospector agent**

`workforce/prospector/__init__.py`:
```python
from .agent import ProspectorBlueprint

__all__ = ["ProspectorBlueprint"]
```

`workforce/prospector/skills/__init__.py`:
```python
"""Prospector skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`workforce/prospector/skills/company_profiling.py`:
```python
NAME = "Company Profiling"
DESCRIPTION = "Build structured profiles: size, industry, key contacts, recent news, decision makers"
```

`workforce/prospector/skills/qualification_scoring.py`:
```python
NAME = "Qualification Scoring"
DESCRIPTION = "Assess prospect fit based on configurable criteria — budget signals, need indicators, timing"
```

`workforce/prospector/skills/web_intelligence.py`:
```python
NAME = "Web Intelligence"
DESCRIPTION = "Extract actionable intelligence from public sources — websites, press releases, job postings, social media"
```

`workforce/prospector/commands/__init__.py`:
```python
"""Prospector commands registry."""
from .research_targets import research_targets
from .revise_prospects import revise_prospects

ALL_COMMANDS = [research_targets, revise_prospects]
```

`workforce/prospector/commands/research_targets.py`:
```python
"""Prospector command: research and qualify targets."""
from agents.blueprints.base import command


@command(
    name="research-targets",
    description=(
        "Research and qualify potential targets based on the leader's criteria. Uses web search to gather "
        "company info, key contacts, and recent activity. Returns a structured lead list with qualification "
        "notes and scoring for each prospect."
    ),
    model="claude-sonnet-4-6",
)
def research_targets(self, agent) -> dict:
    return {
        "exec_summary": "Research and qualify a batch of prospect targets",
        "step_plan": (
            "1. Review target criteria from task instructions\n"
            "2. Research each target via web search\n"
            "3. Build structured profiles with key contacts\n"
            "4. Score each prospect on qualification criteria\n"
            "5. Return ranked list with research notes"
        ),
    }
```

`workforce/prospector/commands/revise_prospects.py`:
```python
"""Prospector command: revise prospect list based on analyst feedback."""
from agents.blueprints.base import command


@command(
    name="revise-prospects",
    description=(
        "Refine a prospect list based on analyst feedback. Address specific gaps flagged in the review, "
        "re-research weak entries, add missing context, and improve qualification scoring."
    ),
    model="claude-sonnet-4-6",
)
def revise_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Revise prospect list based on analyst feedback",
        "step_plan": (
            "1. Review analyst feedback on each flagged prospect\n"
            "2. Re-research entries with gaps\n"
            "3. Add missing context and contacts\n"
            "4. Update qualification scores\n"
            "5. Return revised list"
        ),
    }
```

`workforce/prospector/agent.py`:
```python
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.prospector.commands import research_targets, revise_prospects
from agents.blueprints.sales.workforce.prospector.skills import format_skills

logger = logging.getLogger(__name__)


class ProspectorBlueprint(WorkforceBlueprint):
    name = "Prospector"
    slug = "prospector"
    description = "Researches and qualifies potential targets — builds structured lead lists with company profiles, key contacts, and scoring"
    tags = ["research", "prospecting", "lead-gen", "qualification"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a prospecting specialist. Your job is to research potential targets, build structured profiles, and qualify them for outreach.

When researching targets, gather:
- Company/organization overview (size, industry, focus)
- Key contacts and decision makers
- Recent activity (news, events, announcements)
- Qualification signals (budget indicators, need signals, timing)

When executing tasks, respond with JSON:
{
    "prospects": [
        {
            "name": "...",
            "type": "company|organization|individual",
            "profile": "Brief overview",
            "key_contacts": ["Name — Role"],
            "recent_activity": "Notable news or events",
            "qualification_score": 1-10,
            "qualification_notes": "Why this score",
            "recommended_approach": "Suggested angle for outreach"
        }
    ],
    "report": "Summary of research conducted and key findings"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    research_targets = research_targets
    revise_prospects = revise_prospects

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# RESEARCH METHODOLOGY

## Source Diversity
- Search company websites, LinkedIn, press releases, news articles, job postings
- Cross-reference multiple sources to validate information
- Note recency of information — flag stale data

## Qualification Rigor
- Score each prospect 1-10 based on: strategic fit, accessibility, revenue potential, timing signals
- Be honest about weak prospects — a low score with good reasoning is more valuable than inflated scores
- Flag any red flags (financial trouble, leadership changes, recent layoffs)

## Output Quality
- Every prospect must have at least one key contact identified
- Every qualification note must cite a specific source or signal
- Recommended approach must be specific, not generic"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 4: Create Prospect Analyst agent**

`workforce/prospect_analyst/__init__.py`:
```python
from .agent import ProspectAnalystBlueprint

__all__ = ["ProspectAnalystBlueprint"]
```

`workforce/prospect_analyst/skills/__init__.py`:
```python
"""Prospect analyst skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`workforce/prospect_analyst/skills/quality_scoring.py`:
```python
NAME = "Quality Scoring"
DESCRIPTION = "Score prospect lists on completeness, relevance, and actionability (1-10 scale)"
```

`workforce/prospect_analyst/skills/gap_detection.py`:
```python
NAME = "Gap Detection"
DESCRIPTION = "Identify missing information that would be needed before outreach can proceed"
```

`workforce/prospect_analyst/skills/strategic_fit.py`:
```python
NAME = "Strategic Fit"
DESCRIPTION = "Assess alignment between prospects and the project's goals and target market"
```

`workforce/prospect_analyst/commands/__init__.py`:
```python
"""Prospect analyst commands registry."""
from .review_prospects import review_prospects

ALL_COMMANDS = [review_prospects]
```

`workforce/prospect_analyst/commands/review_prospects.py`:
```python
"""Prospect analyst command: review prospect list quality."""
from agents.blueprints.base import command


@command(
    name="review-prospects",
    description=(
        "Review a prospect list for quality, relevance, and strategic fit. Score each prospect on "
        "completeness and actionability. Identify gaps and weak qualifications. Return verdict: "
        "approved (with scores) or revision_needed (with specific feedback per prospect)."
    ),
    model="claude-sonnet-4-6",
)
def review_prospects(self, agent) -> dict:
    return {
        "exec_summary": "Review prospect list quality and strategic fit",
        "step_plan": (
            "1. Evaluate each prospect for completeness\n"
            "2. Score qualification rigor\n"
            "3. Identify gaps and missing information\n"
            "4. Return verdict with specific feedback"
        ),
    }
```

`workforce/prospect_analyst/agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.prospect_analyst.commands import review_prospects
from agents.blueprints.sales.workforce.prospect_analyst.skills import format_skills

logger = logging.getLogger(__name__)


class ProspectAnalystBlueprint(WorkforceBlueprint):
    name = "Prospect Analyst"
    slug = "prospect_analyst"
    description = "Reviews prospect lists for quality, relevance, and strategic fit — scores and returns verdict with specific feedback"
    tags = ["review", "analysis", "quality", "prospects"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a prospect quality analyst. Your job is to review prospect lists produced by the Prospector and ensure they meet quality standards before outreach begins.

You are the quality gate — be rigorous but constructive. Your feedback should be specific enough that the Prospector can act on it without guessing.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "prospect_reviews": [
        {
            "prospect_name": "...",
            "score": 1-10,
            "issues": ["Missing key contact", "Qualification score seems inflated"],
            "recommendation": "keep|revise|drop"
        }
    ],
    "summary_feedback": "Overall assessment and priority improvements needed",
    "report": "Detailed review summary"
}

Approve threshold: overall score >= 7 and no prospect has critical gaps."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_prospects = review_prospects

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Completeness Check
- Every prospect must have: name, type, profile, at least one key contact, qualification score with reasoning
- Flag any prospects with placeholder or generic information
- Check that recommended approaches are specific, not boilerplate

## Strategic Alignment
- Verify prospects match the project's stated goals and target market
- Flag prospects that seem off-strategy, even if well-researched
- Prioritize prospects with clear timing signals (upcoming events, recent funding, expansion)

## Verdict Rules
- Score >= 7 with no critical gaps: APPROVED
- Score < 7 OR any critical gaps: REVISION_NEEDED with specific feedback
- Be specific in feedback — "improve qualification" is useless, "Company X missing budget signals — check their recent funding rounds" is actionable"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 5: Verify imports**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints.sales.workforce.prospector import ProspectorBlueprint
from agents.blueprints.sales.workforce.prospect_analyst import ProspectAnalystBlueprint
print(ProspectorBlueprint().name, ProspectAnalystBlueprint().name)
"
```
Expected: `Prospector Prospect Analyst`

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/prospector/ backend/agents/blueprints/sales/workforce/prospect_analyst/ backend/agents/blueprints/sales/workforce/__init__.py
git commit -m "feat(sales): add Prospector + Prospect Analyst (writer/reviewer pair)"
```

---

### Task 3: Sales Department — Outreach Writer + Outreach Reviewer (writer/reviewer pair)

**Files:**
- Create: `backend/agents/blueprints/sales/workforce/outreach_writer/` (full agent structure)
- Create: `backend/agents/blueprints/sales/workforce/outreach_reviewer/` (full agent structure)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/sales/workforce/outreach_writer/{commands,skills}
mkdir -p backend/agents/blueprints/sales/workforce/outreach_reviewer/{commands,skills}
```

- [ ] **Step 2: Create Outreach Writer agent**

`workforce/outreach_writer/__init__.py`:
```python
from .agent import OutreachWriterBlueprint

__all__ = ["OutreachWriterBlueprint"]
```

`workforce/outreach_writer/skills/__init__.py`: (same auto-discovery pattern as above)
```python
"""Outreach writer skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`workforce/outreach_writer/skills/personalization.py`:
```python
NAME = "Personalization"
DESCRIPTION = "Tailor messaging to recipient's context, company, and likely pain points"
```

`workforce/outreach_writer/skills/value_proposition.py`:
```python
NAME = "Value Proposition"
DESCRIPTION = "Articulate why the prospect should care, framed in their terms not ours"
```

`workforce/outreach_writer/skills/call_to_action.py`:
```python
NAME = "Call to Action"
DESCRIPTION = "Craft specific, low-friction next steps that advance the relationship"
```

`workforce/outreach_writer/commands/__init__.py`:
```python
"""Outreach writer commands registry."""
from .draft_outreach import draft_outreach
from .revise_outreach import revise_outreach

ALL_COMMANDS = [draft_outreach, revise_outreach]
```

`workforce/outreach_writer/commands/draft_outreach.py`:
```python
"""Outreach writer command: draft personalized outreach."""
from agents.blueprints.base import command


@command(
    name="draft-outreach",
    description=(
        "Write personalized outreach for a specific prospect. Uses prospect research and project "
        "positioning to produce an email or message draft with subject line, body, and call to action."
    ),
    model="claude-sonnet-4-6",
)
def draft_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Draft personalized outreach for a qualified prospect",
        "step_plan": (
            "1. Review prospect research and qualification notes\n"
            "2. Identify the strongest angle for outreach\n"
            "3. Draft subject line, body, and CTA\n"
            "4. Ensure personalization references specific prospect details"
        ),
    }
```

`workforce/outreach_writer/commands/revise_outreach.py`:
```python
"""Outreach writer command: revise outreach based on reviewer feedback."""
from agents.blueprints.base import command


@command(
    name="revise-outreach",
    description=(
        "Revise an outreach draft based on reviewer feedback. Address specific issues: "
        "tone, personalization depth, value prop clarity, CTA strength."
    ),
    model="claude-sonnet-4-6",
)
def revise_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Revise outreach draft based on reviewer feedback",
        "step_plan": (
            "1. Review reviewer's specific feedback points\n"
            "2. Address each issue in the revised draft\n"
            "3. Strengthen weak areas while preserving strong elements\n"
            "4. Return revised draft"
        ),
    }
```

`workforce/outreach_writer/agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_writer.commands import draft_outreach, revise_outreach
from agents.blueprints.sales.workforce.outreach_writer.skills import format_skills

logger = logging.getLogger(__name__)


class OutreachWriterBlueprint(WorkforceBlueprint):
    name = "Outreach Writer"
    slug = "outreach_writer"
    description = "Drafts personalized outreach — cold emails, partnership proposals, follow-ups — tailored to each prospect's context"
    tags = ["writing", "outreach", "email", "personalization"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an outreach writing specialist. You craft personalized messages that open doors — cold emails, partnership proposals, follow-up messages.

Your writing must be:
- Genuinely personalized (reference specific details about the recipient)
- Value-first (lead with what matters to them, not us)
- Concise (busy people scan, they don't read)
- Clear CTA (one specific, low-friction next step)

When executing tasks, respond with JSON:
{
    "draft": {
        "subject": "Email subject line",
        "body": "Full email body",
        "cta": "The specific call to action",
        "personalization_notes": "What specific details were referenced and why"
    },
    "report": "Rationale for approach, angle chosen, and key decisions"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    draft_outreach = draft_outreach
    revise_outreach = revise_outreach

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# OUTREACH METHODOLOGY

## Personalization Depth
- Reference at least 2 specific details about the prospect (recent news, company focus, role)
- Never use templates or generic phrases like "I came across your company"
- The prospect should feel this was written specifically for them

## Value-First Structure
- Open with something relevant to THEIR world, not ours
- Bridge to how we can help with something they likely care about
- Close with a specific, easy next step (not "let me know if interested")

## Tone
- Professional but human — no corporate speak
- Confident but not pushy — we're offering value, not begging
- Brief — 3-5 short paragraphs maximum"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 3: Create Outreach Reviewer agent**

`workforce/outreach_reviewer/__init__.py`:
```python
from .agent import OutreachReviewerBlueprint

__all__ = ["OutreachReviewerBlueprint"]
```

`workforce/outreach_reviewer/skills/__init__.py`: (same auto-discovery pattern)
```python
"""Outreach reviewer skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`workforce/outreach_reviewer/skills/tone_analysis.py`:
```python
NAME = "Tone Analysis"
DESCRIPTION = "Assess professional tone — confidence without pushiness, authenticity without informality"
```

`workforce/outreach_reviewer/skills/personalization_depth.py`:
```python
NAME = "Personalization Depth"
DESCRIPTION = "Check that messaging references specific prospect details, not generic templates"
```

`workforce/outreach_reviewer/skills/effectiveness_scoring.py`:
```python
NAME = "Effectiveness Scoring"
DESCRIPTION = "Score likelihood of response based on outreach best practices — subject line, opening, CTA strength"
```

`workforce/outreach_reviewer/commands/__init__.py`:
```python
"""Outreach reviewer commands registry."""
from .review_outreach import review_outreach

ALL_COMMANDS = [review_outreach]
```

`workforce/outreach_reviewer/commands/review_outreach.py`:
```python
"""Outreach reviewer command: review outreach draft quality."""
from agents.blueprints.base import command


@command(
    name="review-outreach",
    description=(
        "Review an outreach draft for personalization depth, value proposition clarity, "
        "professional tone, appropriate length, and clear CTA. Return verdict: approved or "
        "revision_needed with line-level feedback."
    ),
    model="claude-sonnet-4-6",
)
def review_outreach(self, agent) -> dict:
    return {
        "exec_summary": "Review outreach draft for quality and effectiveness",
        "step_plan": (
            "1. Check personalization — are specific prospect details referenced?\n"
            "2. Evaluate value proposition — is it framed in their terms?\n"
            "3. Assess tone — professional, confident, not pushy?\n"
            "4. Check CTA — specific and low-friction?\n"
            "5. Return verdict with specific feedback"
        ),
    }
```

`workforce/outreach_reviewer/agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.sales.workforce.outreach_reviewer.commands import review_outreach
from agents.blueprints.sales.workforce.outreach_reviewer.skills import format_skills

logger = logging.getLogger(__name__)


class OutreachReviewerBlueprint(WorkforceBlueprint):
    name = "Outreach Reviewer"
    slug = "outreach_reviewer"
    description = "Reviews outreach drafts for personalization, tone, value prop clarity, and CTA effectiveness — quality gate before sending"
    tags = ["review", "quality", "outreach", "editing"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an outreach quality reviewer. Your job is to ensure every outreach draft meets the bar before it reaches a prospect. You are the quality gate — be rigorous but constructive.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "review": {
        "personalization": {"score": 1-10, "feedback": "..."},
        "value_proposition": {"score": 1-10, "feedback": "..."},
        "tone": {"score": 1-10, "feedback": "..."},
        "cta": {"score": 1-10, "feedback": "..."},
        "length": {"score": 1-10, "feedback": "..."}
    },
    "line_feedback": ["Specific issue with specific suggestion"],
    "report": "Overall assessment and priority improvements"
}

Approve threshold: overall score >= 7 and no dimension below 5."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_outreach = review_outreach

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Personalization Check
- Does the draft reference at least 2 specific details about the prospect?
- Would the prospect feel this was written specifically for them?
- Flag any generic phrases that could apply to anyone

## Value Proposition
- Is the value framed in the prospect's terms, not ours?
- Is it clear what's in it for them?
- Is the connection between their situation and our offering logical?

## Tone & CTA
- Professional but human? No corporate jargon?
- CTA is specific and low-friction? (Not "let me know if interested")
- Length appropriate? (3-5 short paragraphs max)

## Verdict Rules
- Score >= 7 with no dimension below 5: APPROVED
- Otherwise: REVISION_NEEDED with actionable, specific feedback"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 4: Verify imports**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints.sales.workforce.outreach_writer import OutreachWriterBlueprint
from agents.blueprints.sales.workforce.outreach_reviewer import OutreachReviewerBlueprint
print(OutreachWriterBlueprint().name, OutreachReviewerBlueprint().name)
"
```
Expected: `Outreach Writer Outreach Reviewer`

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/sales/workforce/outreach_writer/ backend/agents/blueprints/sales/workforce/outreach_reviewer/
git commit -m "feat(sales): add Outreach Writer + Outreach Reviewer (writer/reviewer pair)"
```

---

### Task 4: Sales Department — Registration

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`

- [ ] **Step 1: Register Sales department**

In `backend/agents/blueprints/__init__.py`, add after the Engineering section (after line 116):

```python
# ── Sales ───────────────────────────────────────────────────────────────────

try:
    from agents.blueprints.sales.leader import SalesLeaderBlueprint
except ImportError:
    SalesLeaderBlueprint = None

_sales_workforce = {}
_sales_imports = {
    "prospector": ("agents.blueprints.sales.workforce.prospector", "ProspectorBlueprint"),
    "prospect_analyst": ("agents.blueprints.sales.workforce.prospect_analyst", "ProspectAnalystBlueprint"),
    "outreach_writer": ("agents.blueprints.sales.workforce.outreach_writer", "OutreachWriterBlueprint"),
    "outreach_reviewer": ("agents.blueprints.sales.workforce.outreach_reviewer", "OutreachReviewerBlueprint"),
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
        "description": "Outbound prospecting and outreach — target research, qualification, personalized outreach with quality review loops",
        "execution_mode": "scheduled",
        "min_delay_seconds": 0,
        "leader": _sales_leader,
        "workforce": _sales_workforce,
        "config_schema": _sales_leader.config_schema,
    }
```

- [ ] **Step 2: Verify registration**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints import DEPARTMENTS
dept = DEPARTMENTS['sales']
print(dept['name'], '—', len(dept['workforce']), 'agents')
for slug, bp in dept['workforce'].items():
    print(f'  {slug}: {bp.name}')
"
```
Expected:
```
Sales — 4 agents
  prospector: Prospector
  prospect_analyst: Prospect Analyst
  outreach_writer: Outreach Writer
  outreach_reviewer: Outreach Reviewer
```

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest -q --tb=line 2>&1 | tail -5`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/agents/blueprints/__init__.py
git commit -m "feat(sales): register Sales department in blueprint registry"
```

---

### Task 5: Community Department — Leader (Community Director)

**Files:**
- Create: `backend/agents/blueprints/community/__init__.py`
- Create: `backend/agents/blueprints/community/leader/` (full structure)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/community/leader/{commands,skills}
```

- [ ] **Step 2: Create all files**

Follow the exact same pattern as Task 1 (Sales leader), with these differences:

`community/__init__.py`: empty

`community/leader/__init__.py`:
```python
from .agent import CommunityLeaderBlueprint

__all__ = ["CommunityLeaderBlueprint"]
```

`community/leader/skills/__init__.py`: (same auto-discovery pattern)
```python
"""Community leader skills registry."""
import importlib
import pkgutil

SKILLS = []

for _importer, modname, _ispkg in pkgutil.iter_modules(__path__):
    mod = importlib.import_module(f".{modname}", __package__)
    if hasattr(mod, "NAME") and hasattr(mod, "DESCRIPTION"):
        SKILLS.append({"name": mod.NAME, "description": mod.DESCRIPTION})


def format_skills() -> str:
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILLS)
```

`community/leader/skills/ecosystem_mapping.py`:
```python
NAME = "Ecosystem Mapping"
DESCRIPTION = "Categorize and track organizations, communities, events, and influencers by relevance and relationship stage"
```

`community/leader/skills/partnership_strategy.py`:
```python
NAME = "Partnership Strategy"
DESCRIPTION = "Identify mutually beneficial partnership structures — referrals, co-marketing, cross-promotion, bundled offerings"
```

`community/leader/skills/review_orchestration.py`:
```python
NAME = "Review Orchestration"
DESCRIPTION = "Manage writer/reviewer ping-pong loops for partnership proposals — route drafts to reviewers, route feedback to writers"
```

`community/leader/commands/__init__.py`:
```python
"""Community leader commands registry."""
from .plan_community import plan_community
from .check_progress import check_progress

ALL_COMMANDS = [plan_community, check_progress]
```

`community/leader/commands/plan_community.py`:
```python
"""Community leader command: weekly ecosystem and partnership planning."""
from agents.blueprints.base import command


@command(
    name="plan-community",
    description=(
        "Weekly planning that maps ecosystem state, identifies new partnership categories, "
        "and prioritizes relationship targets. Delegates research to Ecosystem Researcher "
        "and proposal drafting to Partnership Writer. Triggers review cycles for completed work."
    ),
    schedule="weekly",
    model="claude-sonnet-4-6",
)
def plan_community(self, agent) -> dict:
    return {
        "exec_summary": "Plan this week's ecosystem research and partnership outreach",
        "step_plan": (
            "1. Review current ecosystem map and active partnerships\n"
            "2. Identify new categories or targets to research\n"
            "3. Create research tasks for Ecosystem Researcher\n"
            "4. Create proposal tasks for Partnership Writer on researched targets\n"
            "5. Route completed work to reviewers"
        ),
    }
```

`community/leader/commands/check_progress.py`:
```python
"""Community leader command: daily progress check."""
from agents.blueprints.base import command


@command(
    name="check-progress",
    description=(
        "Daily check on ecosystem research status, pending partnership proposals, "
        "stalled review loops, and relationships needing follow-up. Lighter touch than "
        "Sales — community building has a longer cycle."
    ),
    schedule="daily",
    model="claude-haiku-4-5",
)
def check_progress(self, agent) -> dict:
    return {
        "exec_summary": "Check community pipeline health — pending research, proposals, follow-ups",
        "step_plan": (
            "1. Find completed researcher tasks without reviewer assignment\n"
            "2. Check stalled review loops\n"
            "3. Identify partnerships needing follow-up\n"
            "4. Report ecosystem coverage status"
        ),
    }
```

`community/leader/agent.py`:
```python
from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from django.utils import timezone

from agents.blueprints.base import LeaderBlueprint
from agents.blueprints.community.leader.commands import plan_community, check_progress
from agents.blueprints.community.leader.skills import format_skills

logger = logging.getLogger(__name__)


class CommunityLeaderBlueprint(LeaderBlueprint):
    name = "Community Director"
    slug = "leader"
    description = "Community & partnerships leader — orchestrates ecosystem research, partnership proposals, and relationship building"
    tags = ["leadership", "strategy", "community", "partnerships", "ecosystem"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are the community & partnerships director. You build ecosystem relationships by coordinating your workforce agents: Ecosystem Researcher, Ecosystem Analyst, Partnership Writer, and Partnership Reviewer.

Your core responsibilities:
1. Plan weekly ecosystem research — what categories and targets to investigate
2. Delegate research tasks to the Ecosystem Researcher
3. Route completed research to the Ecosystem Analyst for review
4. Delegate partnership proposal drafting to the Partnership Writer for promising targets
5. Route completed proposals to the Partnership Reviewer for quality check
6. Manage the review ping-pong loop: if a reviewer sends work back, create a revision task with feedback

Review loop rules:
- When a writer task completes, create a review task for the paired reviewer
- If the reviewer's verdict is "revision_needed", create a revision task back to the writer with the reviewer's feedback
- If the reviewer's verdict is "approved", mark the relationship as ready for outreach
- Maximum 3 review rounds — after that, escalate to human

Community building is slower than sales — weekly planning, daily checks. Focus on quality relationships over volume."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    plan_community = plan_community
    check_progress = check_progress

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude
        from agents.models import Agent as AgentModel
        from agents.models import AgentTask as TaskModel

        workforce = list(
            agent.department.agents.filter(status="active", is_leader=False).values_list("name", "agent_type")
        )
        workforce_desc = "\n".join(f"- {name} ({atype})" for name, atype in workforce)

        delegation_suffix = f"""# Workforce Agents
{workforce_desc}

When delegating work, include delegated_tasks in your response.
For review loops: when a writer task is done, delegate to the paired reviewer.
When a reviewer approves, advance the relationship stage. When they reject, send revision back to the writer.

Respond with JSON:
{{
    "delegated_tasks": [
        {{
            "target_agent_type": "agent type slug",
            "exec_summary": "What the agent should do",
            "step_plan": "Detailed instructions including any reviewer feedback to address",
            "auto_execute": false,
            "proposed_exec_at": "ISO datetime or null"
        }}
    ],
    "follow_up": {{
        "exec_summary": "What to revisit",
        "days_from_now": 14
    }},
    "report": "Summary of what was decided and why"
}}"""

        task_msg = self.build_task_message(agent, task, suffix=delegation_suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        try:
            data = json.loads(response)
            delegated = data.get("delegated_tasks", [])
            report = data.get("report", response)
            follow_up = data.get("follow_up")

            if delegated:
                workforce_agents = AgentModel.objects.filter(
                    department=agent.department, status="active", is_leader=False,
                )
                agents_by_type = {a.agent_type: a for a in workforce_agents}

                for dt in delegated:
                    target_type = dt.get("target_agent_type")
                    target_agent = agents_by_type.get(target_type)
                    if not target_agent:
                        logger.warning("No active workforce agent of type %s", target_type)
                        continue

                    sub_task = TaskModel.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=TaskModel.Status.QUEUED if dt.get("auto_execute") else TaskModel.Status.AWAITING_APPROVAL,
                        auto_execute=bool(dt.get("auto_execute")),
                        exec_summary=dt.get("exec_summary", "Delegated task"),
                        step_plan=dt.get("step_plan", ""),
                    )

                    if dt.get("auto_execute"):
                        from agents.tasks import execute_agent_task
                        execute_agent_task.delay(str(sub_task.id))

                    logger.info("Community leader delegated task %s to %s", sub_task.id, target_agent.name)

            if follow_up and follow_up.get("days_from_now"):
                days = follow_up["days_from_now"]
                TaskModel.objects.create(
                    agent=agent,
                    status=TaskModel.Status.AWAITING_APPROVAL,
                    exec_summary=follow_up.get("exec_summary", f"Follow-up in {days} days"),
                    step_plan=f"Review and assess. Original task: {task.exec_summary[:200]}",
                    proposed_exec_at=timezone.now() + timedelta(days=days),
                )

            return report
        except (json.JSONDecodeError, KeyError):
            return response

    def generate_task_proposal(self, agent: Agent) -> dict:
        return self.plan_community(agent)
```

- [ ] **Step 3: Verify imports**

```bash
cd backend && source ../venv312/bin/activate && python -c "from agents.blueprints.community.leader import CommunityLeaderBlueprint; print(CommunityLeaderBlueprint().name)"
```
Expected: `Community Director`

- [ ] **Step 4: Commit**

```bash
git add backend/agents/blueprints/community/
git commit -m "feat(community): add Community Director leader blueprint with weekly planning"
```

---

### Task 6: Community Department — Ecosystem Researcher + Ecosystem Analyst

**Files:**
- Create: `backend/agents/blueprints/community/workforce/__init__.py`
- Create: `backend/agents/blueprints/community/workforce/ecosystem_researcher/` (full structure)
- Create: `backend/agents/blueprints/community/workforce/ecosystem_analyst/` (full structure)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p backend/agents/blueprints/community/workforce/ecosystem_researcher/{commands,skills}
mkdir -p backend/agents/blueprints/community/workforce/ecosystem_analyst/{commands,skills}
```

- [ ] **Step 2: Create `workforce/__init__.py`**

```python
```

- [ ] **Step 3: Create Ecosystem Researcher**

Follow the Prospector pattern. Key differences:

`ecosystem_researcher/__init__.py`:
```python
from .agent import EcosystemResearcherBlueprint

__all__ = ["EcosystemResearcherBlueprint"]
```

Skills: `organization_profiling.py`, `relationship_mapping.py`, `opportunity_detection.py`
```python
# organization_profiling.py
NAME = "Organization Profiling"
DESCRIPTION = "Build structured profiles of organizations, communities, and event series"

# relationship_mapping.py
NAME = "Relationship Mapping"
DESCRIPTION = "Identify connections between ecosystem entities — who partners with whom, shared audiences"

# opportunity_detection.py
NAME = "Opportunity Detection"
DESCRIPTION = "Spot partnership openings — upcoming events, new programs, expansion announcements"
```

Commands: `map_ecosystem.py`, `revise_research.py`

`commands/__init__.py`:
```python
"""Ecosystem researcher commands registry."""
from .map_ecosystem import map_ecosystem
from .revise_research import revise_research

ALL_COMMANDS = [map_ecosystem, revise_research]
```

`commands/map_ecosystem.py`:
```python
"""Ecosystem researcher command: map a category of the ecosystem."""
from agents.blueprints.base import command


@command(
    name="map-ecosystem",
    description=(
        "Research a specific ecosystem category — local communities, industry events, complementary "
        "businesses, influencers. Uses web search. Returns structured map with organizations, "
        "key contacts, relevance notes, and partnership potential."
    ),
    model="claude-sonnet-4-6",
)
def map_ecosystem(self, agent) -> dict:
    return {
        "exec_summary": "Map a specific category of the ecosystem",
        "step_plan": (
            "1. Research the target category via web search\n"
            "2. Build structured profiles for each entity found\n"
            "3. Identify key contacts and decision makers\n"
            "4. Assess partnership potential for each\n"
            "5. Return structured ecosystem map"
        ),
    }
```

`commands/revise_research.py`:
```python
"""Ecosystem researcher command: revise research based on analyst feedback."""
from agents.blueprints.base import command


@command(
    name="revise-research",
    description=(
        "Refine ecosystem research based on analyst feedback. Fill gaps, re-assess flagged "
        "entries, explore missed categories or entities."
    ),
    model="claude-sonnet-4-6",
)
def revise_research(self, agent) -> dict:
    return {
        "exec_summary": "Revise ecosystem research based on analyst feedback",
        "step_plan": (
            "1. Review analyst feedback on gaps and issues\n"
            "2. Re-research flagged entities\n"
            "3. Explore missed categories\n"
            "4. Return revised ecosystem map"
        ),
    }
```

`agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.ecosystem_researcher.commands import map_ecosystem, revise_research
from agents.blueprints.community.workforce.ecosystem_researcher.skills import format_skills

logger = logging.getLogger(__name__)


class EcosystemResearcherBlueprint(WorkforceBlueprint):
    name = "Ecosystem Researcher"
    slug = "ecosystem_researcher"
    description = "Maps local and industry ecosystems — organizations, communities, events, influencers, complementary businesses"
    tags = ["research", "ecosystem", "communities", "partnerships"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an ecosystem research specialist. Your job is to map the landscape of organizations, communities, events, and potential partners in a given category.

When researching, respond with JSON:
{
    "entities": [
        {
            "name": "...",
            "type": "organization|community|event_series|influencer|business",
            "profile": "What they do and why they matter",
            "key_contacts": ["Name — Role"],
            "audience_overlap": "How their audience connects to ours",
            "partnership_potential": 1-10,
            "partnership_angle": "Specific partnership idea",
            "recent_activity": "Recent news or events"
        }
    ],
    "report": "Summary of ecosystem mapped and key opportunities identified"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    map_ecosystem = map_ecosystem
    revise_research = revise_research

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# ECOSYSTEM RESEARCH METHODOLOGY

## Breadth First
- Cast a wide net within the assigned category
- Look for organizations, communities, event series, and individuals
- Don't just search for the obvious — look for adjacent and emerging entities

## Depth on High-Potential
- For entities scoring 7+ on partnership potential, gather deeper intel
- Key contacts, recent activity, existing partnerships they have
- What specific partnership structure would work?

## Connection Mapping
- Note which entities are connected to each other
- Shared audiences, co-hosted events, mutual partnerships
- This reveals ecosystem clusters and entry points"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 4: Create Ecosystem Analyst**

`ecosystem_analyst/__init__.py`:
```python
from .agent import EcosystemAnalystBlueprint

__all__ = ["EcosystemAnalystBlueprint"]
```

Skills: `strategic_prioritization.py`, `gap_analysis.py`, `competitive_landscape.py`
```python
# strategic_prioritization.py
NAME = "Strategic Prioritization"
DESCRIPTION = "Rank ecosystem entities by reach, alignment, and effort-to-engage"

# gap_analysis.py
NAME = "Gap Analysis"
DESCRIPTION = "Identify ecosystem categories or entities that should have been included but weren't"

# competitive_landscape.py
NAME = "Competitive Landscape"
DESCRIPTION = "Assess whether competitors already have relationships with identified entities"
```

Commands: `review_ecosystem.py`

`commands/__init__.py`:
```python
"""Ecosystem analyst commands registry."""
from .review_ecosystem import review_ecosystem

ALL_COMMANDS = [review_ecosystem]
```

`commands/review_ecosystem.py`:
```python
"""Ecosystem analyst command: review ecosystem research quality."""
from agents.blueprints.base import command


@command(
    name="review-ecosystem",
    description=(
        "Review ecosystem research for completeness, strategic prioritization, and missed "
        "opportunities. Score each entity on partnership potential. Return verdict: approved "
        "or revision_needed with specific feedback."
    ),
    model="claude-sonnet-4-6",
)
def review_ecosystem(self, agent) -> dict:
    return {
        "exec_summary": "Review ecosystem research for quality and completeness",
        "step_plan": (
            "1. Evaluate coverage — are obvious entities missing?\n"
            "2. Check strategic prioritization\n"
            "3. Assess partnership potential scores\n"
            "4. Return verdict with specific feedback"
        ),
    }
```

`agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.ecosystem_analyst.commands import review_ecosystem
from agents.blueprints.community.workforce.ecosystem_analyst.skills import format_skills

logger = logging.getLogger(__name__)


class EcosystemAnalystBlueprint(WorkforceBlueprint):
    name = "Ecosystem Analyst"
    slug = "ecosystem_analyst"
    description = "Reviews ecosystem research for completeness, strategic fit, and missed opportunities — quality gate before partnership outreach"
    tags = ["review", "analysis", "ecosystem", "strategy"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are an ecosystem quality analyst. Your job is to review ecosystem research and ensure the map is comprehensive and strategically sound before partnership proposals begin.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "entity_reviews": [
        {
            "entity_name": "...",
            "score": 1-10,
            "issues": ["Missing partnership angle", "Audience overlap unclear"],
            "recommendation": "keep|revise|drop"
        }
    ],
    "missing_categories": ["Categories or entities that should have been researched"],
    "summary_feedback": "Overall assessment and priority improvements",
    "report": "Detailed review summary"
}

Approve threshold: overall score >= 7 and no critical gaps in coverage."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_ecosystem = review_ecosystem

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Coverage Check
- Are the obvious entities in this category represented?
- Are there adjacent categories that should have been explored?
- Is there geographic or demographic coverage that's missing?

## Strategic Assessment
- Do the partnership potential scores make sense given the project goals?
- Are there high-potential entities that were overlooked?
- Are any low-potential entities over-scored?

## Verdict Rules
- Score >= 7 with no major coverage gaps: APPROVED
- Otherwise: REVISION_NEEDED with specific feedback on what to add or fix"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 5: Create skills `__init__.py` files** (same auto-discovery pattern for both)

- [ ] **Step 6: Verify imports**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints.community.workforce.ecosystem_researcher import EcosystemResearcherBlueprint
from agents.blueprints.community.workforce.ecosystem_analyst import EcosystemAnalystBlueprint
print(EcosystemResearcherBlueprint().name, EcosystemAnalystBlueprint().name)
"
```

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/community/workforce/
git commit -m "feat(community): add Ecosystem Researcher + Ecosystem Analyst (writer/reviewer pair)"
```

---

### Task 7: Community Department — Partnership Writer + Partnership Reviewer

**Files:**
- Create: `backend/agents/blueprints/community/workforce/partnership_writer/` (full structure)
- Create: `backend/agents/blueprints/community/workforce/partnership_reviewer/` (full structure)

Follow the exact same pattern as Task 3 (Outreach Writer/Reviewer), with these differences:

- [ ] **Step 1: Create directory structure and all files**

Partnership Writer:
- Slug: `partnership_writer`
- Commands: `draft-proposal`, `revise-proposal`
- Skills: `mutual_value`, `proposal_structure`, `specificity`
- System prompt focuses on partnership proposals (mutual value, concrete structure, next steps)
- Methodology emphasizes win-win framing, specificity over vague collaboration

Partnership Reviewer:
- Slug: `partnership_reviewer`
- Commands: `review-proposal`
- Skills: `value_balance`, `professionalism`, `actionability`
- System prompt focuses on reviewing partnership proposals
- Review criteria: mutual value clarity, professional tone, realistic structure, clear next steps

`partnership_writer/__init__.py`:
```python
from .agent import PartnershipWriterBlueprint

__all__ = ["PartnershipWriterBlueprint"]
```

`partnership_writer/skills/mutual_value.py`:
```python
NAME = "Mutual Value"
DESCRIPTION = "Frame partnerships as win-win, emphasizing what the partner gains not just what we need"
```

`partnership_writer/skills/proposal_structure.py`:
```python
NAME = "Proposal Structure"
DESCRIPTION = "Organize proposals: context → opportunity → proposed structure → next steps"
```

`partnership_writer/skills/specificity.py`:
```python
NAME = "Specificity"
DESCRIPTION = "Ground proposals in concrete actions rather than vague 'let's collaborate' language"
```

`partnership_writer/commands/__init__.py`:
```python
"""Partnership writer commands registry."""
from .draft_proposal import draft_proposal
from .revise_proposal import revise_proposal

ALL_COMMANDS = [draft_proposal, revise_proposal]
```

`partnership_writer/commands/draft_proposal.py`:
```python
"""Partnership writer command: draft a partnership proposal."""
from agents.blueprints.base import command


@command(
    name="draft-proposal",
    description=(
        "Write a partnership proposal for a specific target. Articulates mutual value, proposed "
        "structure, and concrete next steps. Uses ecosystem research and project context."
    ),
    model="claude-sonnet-4-6",
)
def draft_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Draft a partnership proposal for a specific ecosystem target",
        "step_plan": (
            "1. Review ecosystem research on the target\n"
            "2. Identify the strongest mutual value angle\n"
            "3. Draft proposal: context, opportunity, structure, next steps\n"
            "4. Ensure specificity — no vague collaboration language"
        ),
    }
```

`partnership_writer/commands/revise_proposal.py`:
```python
"""Partnership writer command: revise proposal based on reviewer feedback."""
from agents.blueprints.base import command


@command(
    name="revise-proposal",
    description=(
        "Revise a partnership proposal based on reviewer feedback. Strengthen mutual value "
        "proposition, clarify structure, improve specificity."
    ),
    model="claude-sonnet-4-6",
)
def revise_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Revise partnership proposal based on reviewer feedback",
        "step_plan": (
            "1. Review reviewer's specific feedback\n"
            "2. Strengthen areas flagged as weak\n"
            "3. Preserve elements that were approved\n"
            "4. Return revised proposal"
        ),
    }
```

`partnership_writer/agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.partnership_writer.commands import draft_proposal, revise_proposal
from agents.blueprints.community.workforce.partnership_writer.skills import format_skills

logger = logging.getLogger(__name__)


class PartnershipWriterBlueprint(WorkforceBlueprint):
    name = "Partnership Writer"
    slug = "partnership_writer"
    description = "Drafts partnership proposals — mutual value framing, concrete structures, and actionable next steps"
    tags = ["writing", "partnerships", "proposals", "collaboration"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a partnership proposal specialist. You craft proposals that open doors to meaningful collaborations — referral partnerships, co-marketing, cross-promotion, joint events.

Your proposals must be:
- Win-win (lead with what the partner gains)
- Specific (concrete actions, not vague "let's collaborate")
- Professional (collaborative tone, not desperate or transactional)
- Actionable (clear, low-friction next steps)

When executing tasks, respond with JSON:
{
    "proposal": {
        "subject": "Partnership proposal subject/title",
        "body": "Full proposal text",
        "mutual_value": "What specifically both parties gain",
        "proposed_structure": "Concrete partnership mechanics",
        "next_steps": "Specific first actions"
    },
    "report": "Rationale for approach and key decisions"
}"""

    @property
    def skills_description(self) -> str:
        return format_skills()

    draft_proposal = draft_proposal
    revise_proposal = revise_proposal

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# PROPOSAL METHODOLOGY

## Win-Win Framing
- Open with something relevant to THEIR mission or audience
- Clearly articulate what they gain (not just what we need)
- The partner should see this as an opportunity, not a favor

## Specificity Over Vagueness
- "We'll cross-promote on our respective newsletters reaching X combined subscribers" > "We'll collaborate on marketing"
- Include concrete numbers, timelines, or mechanics where possible
- Avoid anything that sounds like a template

## Professional Tone
- Collaborative, not transactional
- Confident but respectful of their time
- Brief — proposals should be scannable"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

`partnership_reviewer/__init__.py`:
```python
from .agent import PartnershipReviewerBlueprint

__all__ = ["PartnershipReviewerBlueprint"]
```

`partnership_reviewer/skills/value_balance.py`:
```python
NAME = "Value Balance"
DESCRIPTION = "Ensure proposals aren't one-sided — the partner must see clear, specific benefit"
```

`partnership_reviewer/skills/professionalism.py`:
```python
NAME = "Professionalism"
DESCRIPTION = "Check tone is collaborative and confident, not desperate or transactional"
```

`partnership_reviewer/skills/actionability.py`:
```python
NAME = "Actionability"
DESCRIPTION = "Verify proposed next steps are concrete and low-friction for both parties"
```

`partnership_reviewer/commands/__init__.py`:
```python
"""Partnership reviewer commands registry."""
from .review_proposal import review_proposal

ALL_COMMANDS = [review_proposal]
```

`partnership_reviewer/commands/review_proposal.py`:
```python
"""Partnership reviewer command: review partnership proposal quality."""
from agents.blueprints.base import command


@command(
    name="review-proposal",
    description=(
        "Review a partnership proposal for mutual value clarity, professional tone, "
        "specificity, realistic structure, and clear next steps. Return verdict: approved "
        "or revision_needed with specific feedback."
    ),
    model="claude-sonnet-4-6",
)
def review_proposal(self, agent) -> dict:
    return {
        "exec_summary": "Review partnership proposal for quality and effectiveness",
        "step_plan": (
            "1. Check mutual value — is it genuinely win-win?\n"
            "2. Assess specificity — concrete actions or vague language?\n"
            "3. Evaluate tone — professional and collaborative?\n"
            "4. Check next steps — clear and low-friction?\n"
            "5. Return verdict with specific feedback"
        ),
    }
```

`partnership_reviewer/agent.py`:
```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.community.workforce.partnership_reviewer.commands import review_proposal
from agents.blueprints.community.workforce.partnership_reviewer.skills import format_skills

logger = logging.getLogger(__name__)


class PartnershipReviewerBlueprint(WorkforceBlueprint):
    name = "Partnership Reviewer"
    slug = "partnership_reviewer"
    description = "Reviews partnership proposals for mutual value, tone, specificity, and actionability — quality gate before outreach"
    tags = ["review", "quality", "partnerships", "editing"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are a partnership proposal reviewer. Your job is to ensure every proposal meets the quality bar before it's sent to a potential partner. Be rigorous but constructive.

When reviewing, respond with JSON:
{
    "verdict": "approved" or "revision_needed",
    "overall_score": 1-10,
    "review": {
        "mutual_value": {"score": 1-10, "feedback": "..."},
        "specificity": {"score": 1-10, "feedback": "..."},
        "tone": {"score": 1-10, "feedback": "..."},
        "structure": {"score": 1-10, "feedback": "..."},
        "next_steps": {"score": 1-10, "feedback": "..."}
    },
    "line_feedback": ["Specific issue with specific suggestion"],
    "report": "Overall assessment and priority improvements"
}

Approve threshold: overall score >= 7 and no dimension below 5."""

    @property
    def skills_description(self) -> str:
        return format_skills()

    review_proposal = review_proposal

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        from agents.ai.claude_client import call_claude

        suffix = """# REVIEW METHODOLOGY

## Value Balance
- Is the partner's benefit clearly articulated?
- Would the partner see this as an opportunity or a favor?
- Is the value exchange roughly balanced?

## Specificity
- Are concrete mechanics described (not just "we'll collaborate")?
- Are there numbers, timelines, or measurable outcomes?
- Would the partner know exactly what we're proposing?

## Tone & Next Steps
- Professional and collaborative? Not desperate or salesy?
- Next steps are specific and low-friction?
- The proposal is scannable? (Busy people don't read long proposals)

## Verdict Rules
- Score >= 7 with no dimension below 5: APPROVED
- Otherwise: REVISION_NEEDED with actionable feedback"""

        task_msg = self.build_task_message(agent, task, suffix=suffix)

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 2: Create skills `__init__.py` files** for both agents (same auto-discovery pattern)

- [ ] **Step 3: Verify imports**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints.community.workforce.partnership_writer import PartnershipWriterBlueprint
from agents.blueprints.community.workforce.partnership_reviewer import PartnershipReviewerBlueprint
print(PartnershipWriterBlueprint().name, PartnershipReviewerBlueprint().name)
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/agents/blueprints/community/workforce/partnership_writer/ backend/agents/blueprints/community/workforce/partnership_reviewer/
git commit -m "feat(community): add Partnership Writer + Partnership Reviewer (writer/reviewer pair)"
```

---

### Task 8: Community Department — Registration + Final Verification

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`

- [ ] **Step 1: Register Community department**

In `backend/agents/blueprints/__init__.py`, add after the Sales section:

```python
# ── Community & Partnerships ────────────────────────────────────────────────

try:
    from agents.blueprints.community.leader import CommunityLeaderBlueprint
except ImportError:
    CommunityLeaderBlueprint = None

_community_workforce = {}
_community_imports = {
    "ecosystem_researcher": ("agents.blueprints.community.workforce.ecosystem_researcher", "EcosystemResearcherBlueprint"),
    "ecosystem_analyst": ("agents.blueprints.community.workforce.ecosystem_analyst", "EcosystemAnalystBlueprint"),
    "partnership_writer": ("agents.blueprints.community.workforce.partnership_writer", "PartnershipWriterBlueprint"),
    "partnership_reviewer": ("agents.blueprints.community.workforce.partnership_reviewer", "PartnershipReviewerBlueprint"),
}
for _slug, (_mod_path, _cls_name) in _community_imports.items():
    try:
        _mod = importlib.import_module(_mod_path)
        _community_workforce[_slug] = getattr(_mod, _cls_name)()
    except (ImportError, AttributeError):
        pass

if CommunityLeaderBlueprint is not None:
    _community_leader = CommunityLeaderBlueprint()
    DEPARTMENTS["community"] = {
        "name": "Community & Partnerships",
        "description": "Ecosystem mapping and partnership development — research communities, propose collaborations, build relationships with quality review loops",
        "execution_mode": "scheduled",
        "min_delay_seconds": 0,
        "leader": _community_leader,
        "workforce": _community_workforce,
        "config_schema": _community_leader.config_schema,
    }
```

- [ ] **Step 2: Verify both departments registered**

```bash
cd backend && source ../venv312/bin/activate && python -c "
from agents.blueprints import DEPARTMENTS
for slug in ['sales', 'community']:
    dept = DEPARTMENTS[slug]
    print(f'{dept[\"name\"]} — {len(dept[\"workforce\"])} agents')
    for s, bp in dept['workforce'].items():
        print(f'  {s}: {bp.name}')
"
```
Expected:
```
Sales — 4 agents
  prospector: Prospector
  prospect_analyst: Prospect Analyst
  outreach_writer: Outreach Writer
  outreach_reviewer: Outreach Reviewer
Community & Partnerships — 4 agents
  ecosystem_researcher: Ecosystem Researcher
  ecosystem_analyst: Ecosystem Analyst
  partnership_writer: Partnership Writer
  partnership_reviewer: Partnership Reviewer
```

- [ ] **Step 3: Run full test suite**

Run: `cd backend && source ../venv312/bin/activate && python -m pytest -q --tb=line 2>&1 | tail -5`
Expected: All tests pass, no regressions.

- [ ] **Step 4: Commit**

```bash
git add backend/agents/blueprints/__init__.py
git commit -m "feat(community): register Community & Partnerships department in blueprint registry"
```

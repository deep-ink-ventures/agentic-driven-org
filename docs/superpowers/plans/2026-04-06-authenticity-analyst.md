# Authenticity Analyst — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI authenticity/coherence analyst as a reusable archetype mixin, deployed first in the Writers Room.

**Architecture:** Archetype mixin in `agents/ai/archetypes/` provides prompt, skills, task suffix, max tokens, and command. Writers Room concrete class combines the mixin with `WritersRoomFeedbackBlueprint` via multiple inheritance. Mixin goes first in MRO so its `system_prompt` property takes precedence over the base's placeholder. CreativeReviewer gets `authenticity` as a 9th review dimension.

**Tech Stack:** Django, Python, pytest

---

### File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/agents/ai/archetypes/__init__.py` | Create | Package init |
| `backend/agents/ai/archetypes/authenticity_analyst.py` | Create | Mixin class: prompt, skills, suffix, max_tokens, cmd_analyze |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/__init__.py` | Create | Package init |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py` | Create | Concrete class (one-liner) |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/__init__.py` | Create | Package init |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/analyze.py` | Create | Command boilerplate, imports description from archetype |
| `backend/agents/blueprints/__init__.py` | Modify | Add to `_writers_room_imports` |
| `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py` | Modify | Add 9th dimension + fix routing |
| `backend/agents/tests/test_authenticity_analyst.py` | Create | All tests |

---

### Task 1: Create the archetype mixin

**Files:**
- Create: `backend/agents/ai/archetypes/__init__.py`
- Create: `backend/agents/ai/archetypes/authenticity_analyst.py`
- Test: `backend/agents/tests/test_authenticity_analyst.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/agents/tests/test_authenticity_analyst.py`:

```python
"""Tests for AuthenticityAnalystMixin and Writers Room integration."""
from unittest.mock import MagicMock

import pytest


class TestAuthenticityAnalystMixin:
    def test_mixin_exists(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        assert AuthenticityAnalystMixin is not None

    def test_mixin_is_not_blueprint_subclass(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        from agents.blueprints.base import BaseBlueprint
        assert not issubclass(AuthenticityAnalystMixin, BaseBlueprint)

    def test_mixin_has_system_prompt_property(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        prompt = bp.system_prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_system_prompt_contains_five_checks(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        prompt = Concrete().system_prompt
        assert "Linguistic Tells" in prompt
        assert "Voice Flattening" in prompt
        assert "Cliche" in prompt or "Cliché" in prompt
        assert "Coherence" in prompt
        assert "Overall Authenticity" in prompt

    def test_get_task_suffix_includes_locale(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        agent = MagicMock()
        agent.get_config_value.return_value = "de"
        task = MagicMock()

        suffix = bp.get_task_suffix(agent, task)
        assert "Output language: de" in suffix

    def test_get_max_tokens(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        class Concrete(AuthenticityAnalystMixin):
            pass

        bp = Concrete()
        assert bp.get_max_tokens(MagicMock(), MagicMock()) == 8000

    def test_mixin_has_slug(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        assert AuthenticityAnalystMixin.slug == "authenticity_analyst"

    def test_command_description_exported(self):
        from agents.ai.archetypes.authenticity_analyst import COMMAND_DESCRIPTION
        assert isinstance(COMMAND_DESCRIPTION, str)
        assert "authenticity" in COMMAND_DESCRIPTION.lower() or "coherence" in COMMAND_DESCRIPTION.lower()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py -v
```

Expected: FAIL — `agents.ai.archetypes.authenticity_analyst` does not exist.

- [ ] **Step 3: Create `backend/agents/ai/archetypes/__init__.py`**

```python
```

(Empty file — just a package marker.)

- [ ] **Step 4: Create `backend/agents/ai/archetypes/authenticity_analyst.py`**

```python
"""Authenticity Analyst archetype — reusable mixin for AI-generated text detection.

Provides the full agent definition (prompt, skills, task suffix, max tokens)
without any department-specific behavior. Concrete agents in each department
combine their department base class with this mixin.

Usage:
    class AuthenticityAnalystBlueprint(DeptFeedbackBase, AuthenticityAnalystMixin):
        pass
"""

SYSTEM_PROMPT = """\
You are the Authenticity Analyst, a specialist in detecting AI-generated text patterns and assessing whether creative writing reads as genuinely human. You analyze material for linguistic tells, voice authenticity, cliche density, and coherence.

You work with ANY creative writing format — screenplay, novel, theatre, series, short story, poetry. Adapt your analysis to the format at hand.

## Check 1 — Linguistic Tells
Scan for patterns that signal AI generation:
- Hedging phrases: "it's important to note", "it's worth mentioning", "interestingly", "notably"
- List-mania: content organized as bullet lists or numbered points where prose is expected
- Symmetrical paragraph structures: every paragraph the same length, same rhythm, same pattern
- Filler transitions: "moreover", "furthermore", "additionally", "in conclusion", "that said"
- Balanced hedging: "on the one hand / on the other hand" in creative text
- Adverb clustering: "deeply", "profoundly", "incredibly", "remarkably" used as emphasis crutches
- Summary sentences: paragraphs that end by restating what they just said
- Exhaustive enumeration: listing every possibility instead of choosing the most vivid one

Flag each instance with a direct quote and page/scene/chapter reference.

## Check 2 — Voice Flattening
Detect convergence toward a single neutral register:
- Do all characters speak the same way? Compare vocabulary, sentence length, rhythm across 3+ characters
- Does the narrator's voice match the story's tone, or does it default to "informative explainer"?
- Are there passages where the voice shifts to a more formal/academic register for no narrative reason?
- Compare voice against the author's pitch/goal — is the intended tone preserved?
- Does dialogue sound like a helpful assistant explaining things rather than humans talking?
- Are characters' speech patterns interchangeable? Would removing attribution tags make speakers indistinguishable?

## Check 3 — Cliche & Default Patterns
Flag AI-typical creative defaults:
- Physical cliche: "a chill ran down her spine", "heart pounded in her chest", "eyes widened", "breath caught"
- Emotional shorthand: "little did she know", "the weight of the world", "a mix of emotions", "couldn't help but smile"
- Setting cliche: "the city that never sleeps", "a deafening silence", "the air was thick with tension"
- Plot convenience: characters conveniently overhearing, discovering exactly the right clue at the right moment
- Metaphor recycling: same metaphor family used repeatedly without awareness
- Emotional telling: "She felt a wave of sadness wash over her" instead of showing through action
- Thematic statements delivered directly through dialogue rather than emerging from action

## Check 4 — Coherence & Hallucination
The most critical check. Does the text actually make sense?
- Logical consistency: do events follow causally, or do things happen because they sound dramatic?
- World-rule adherence: are established rules (magic systems, tech level, social norms) respected across scenes?
- Factual grounding: are real-world references accurate, or plausible-sounding nonsense?
- Temporal coherence: does the timeline track, or do sequences contradict each other?
- Spatial coherence: are characters where they should be? Do locations stay consistent?
- Semantic density: is every sentence carrying meaning, or are there passages of beautiful emptiness?
- "Remove this paragraph" test: if you remove a paragraph and nothing is lost, flag it as filler
- Character knowledge: do characters act on information they shouldn't have, or forget things they should know?
- Motivation continuity: do character decisions follow from established motivations, or shift to serve the plot?

## Check 5 — Overall Authenticity Verdict
Synthesize: would a professional reader suspect this was AI-generated? What specific passages break the illusion? What works and feels genuinely human? Rate the overall authenticity on a spectrum from "obviously AI" to "indistinguishable from a skilled human author."

## Depth Modes

### Full Mode
Run all 5 checks with per-scene/chapter detail and quoted evidence for every flag.

### Lite Mode
Run checks 1 and 4 only (linguistic tells + coherence). Focus on the 5 most egregious instances and overall verdict.

## Output Format

### Findings

Structure your findings with a labelled section for EACH check:

**1. Linguistic Tells** — summarize patterns found with quoted examples.
**2. Voice Flattening** — character voice comparison, narrator assessment.
**3. Cliche & Defaults** — categorized instances with quotes.
**4. Coherence & Hallucination** — logical, temporal, semantic issues.
**5. Overall Authenticity Verdict** — synthesis and professional reader assessment.

This per-check structure is MANDATORY in full mode.

### Flags
All flags with severity emoji. Each with scene/page/chapter reference and quoted evidence.
- 🔴 Critical — passage is incoherent or reads as obvious AI output
- 🟠 Major — significant voice flattening, cliche clustering, or coherence gap
- 🟡 Minor — isolated linguistic tell or single cliche
- 🟢 Strength — passage that feels genuinely human and distinctive

### Suggestions
3-5 specific, actionable recommendations for improving authenticity. Reference the specific check and passage.

CRITICAL: Your ENTIRE output — findings, flags, suggestions — MUST be written in the language specified by the locale setting. If locale is "de", write everything in German. If "en", English. If "fr", French. This is non-negotiable. The source material may be in any language — your output language is determined ONLY by locale.
EXCEPTION: The section headers ### Findings, ### Flags, and ### Suggestions must ALWAYS be written in English exactly as shown, regardless of output language.

## CRITICAL: Flag Format Rules
In the ### Flags section, write EACH flag as a single line starting with the severity emoji:
- 🔴 Description of the critical issue in one plain sentence with quoted evidence.
- 🟠 Description of the major issue in one plain sentence with quoted evidence.
- 🟡 Description of the minor issue in one plain sentence with quoted evidence.
- 🟢 Description of the strength in one plain sentence with quoted evidence.

DO NOT use tables, sub-headings, bold markers (**), or group flags by severity with headings.
Each flag is one line, one emoji, one sentence.
DO NOT use markdown tables anywhere in your output.

IMPORTANT: Only flag issues the WRITING can address. Do NOT flag external business factors — those are outside the writers room scope."""

COMMAND_DESCRIPTION = (
    "Run AI authenticity analysis: linguistic tell detection, voice flattening assessment, "
    "cliche and default pattern scanning, coherence and hallucination checking, and overall "
    "authenticity verdict. Flags passages that read as AI-generated and highlights genuinely "
    "human writing."
)

TASK_SUFFIX_TEMPLATE = (
    "Analyze this material using the full authenticity methodology:\n"
    "1. Linguistic tells — scan every paragraph for hedging, list-mania, symmetrical structures, "
    "filler transitions, adverb clustering. Quote each instance.\n"
    "2. Voice flattening — compare 3+ character voices, assess narrator register, check tone "
    "against the creator's pitch.\n"
    "3. Cliche and defaults — flag physical cliches, emotional shorthand, setting cliches, "
    "plot conveniences, metaphor recycling. Quote each.\n"
    "4. Coherence and hallucination — verify logical consistency, world-rule adherence, factual "
    "grounding, temporal/spatial coherence, semantic density. Apply the remove-this-paragraph test.\n"
    "5. Overall verdict — would a professional reader suspect AI generation? Which passages "
    "break the illusion, which feel human?\n"
    "Every flag must quote the specific line or passage as evidence."
)


class AuthenticityAnalystMixin:
    """Reusable mixin providing the Authenticity Analyst agent definition.

    Combine with a department-specific feedback base class:

        class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WritersRoomFeedbackBlueprint):
            pass

    Mixin must come FIRST in MRO so its system_prompt property takes
    precedence over any placeholder in the department base.
    """

    name = "Authenticity Analyst"
    slug = "authenticity_analyst"
    description = "Detects AI-generated text patterns, voice flattening, cliche density, and coherence hallucination"
    tags = ["analysis", "authenticity", "ai-detection", "coherence", "feedback"]
    skills = [
        {
            "name": "Linguistic Tell Detection",
            "description": "Identifies hedging, list-mania, symmetrical structures, filler transitions, and other AI generation markers.",
        },
        {
            "name": "Voice Authenticity Scoring",
            "description": "Compares character voices and narrator register against the author's intended tone.",
        },
        {
            "name": "Coherence Verification",
            "description": "Tests logical, temporal, and spatial consistency; flags hallucinated or meaningless passages.",
        },
        {
            "name": "Cliche Pattern Scanning",
            "description": "Detects AI-typical creative defaults: physical cliches, emotional shorthand, metaphor recycling.",
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def get_task_suffix(self, agent, task):
        locale = agent.get_config_value("locale") or "en"
        return f"Output language: {locale}\n\n{TASK_SUFFIX_TEMPLATE}"

    def get_max_tokens(self, agent, task):
        return 8000
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py::TestAuthenticityAnalystMixin -v
```

Expected: PASS all 8 tests.

- [ ] **Step 6: Commit**

```bash
git add backend/agents/ai/archetypes/__init__.py backend/agents/ai/archetypes/authenticity_analyst.py backend/agents/tests/test_authenticity_analyst.py
git commit -m "feat: add AuthenticityAnalystMixin archetype for AI text detection"
```

---

### Task 2: Create the Writers Room concrete agent

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py`
- Create: `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/analyze.py`
- Test: `backend/agents/tests/test_authenticity_analyst.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/agents/tests/test_authenticity_analyst.py`:

```python
class TestWritersRoomAuthenticityAnalyst:
    def test_blueprint_exists(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        assert AuthenticityAnalystBlueprint is not None

    def test_inherits_feedback_blueprint(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        assert issubclass(AuthenticityAnalystBlueprint, WritersRoomFeedbackBlueprint)

    def test_inherits_mixin(self):
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        assert issubclass(AuthenticityAnalystBlueprint, AuthenticityAnalystMixin)

    def test_system_prompt_comes_from_mixin(self):
        from agents.ai.archetypes.authenticity_analyst import SYSTEM_PROMPT
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        bp = AuthenticityAnalystBlueprint()
        assert bp.system_prompt == SYSTEM_PROMPT

    def test_get_context_strips_sibling_reports(self):
        from unittest.mock import patch
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )

        bp = AuthenticityAnalystBlueprint()
        fake_ctx = {
            "project_name": "Test",
            "project_goal": "Write a show",
            "department_name": "Writers Room",
            "department_documents": "--- [stage_deliverable] Expose v1 ---\ncontent",
            "sibling_agents": "## dialogue_writer\n  - [done] Write scenes\n    Report: long dialogue",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch("agents.blueprints.base.WorkforceBlueprint.get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "long dialogue" not in ctx["sibling_agents"]
        assert "Stage Deliverable" in ctx["sibling_agents"]

    def test_has_analyze_command(self):
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
            AuthenticityAnalystBlueprint,
        )
        bp = AuthenticityAnalystBlueprint()
        commands = bp.get_commands()
        command_names = [c["name"] for c in commands]
        assert "analyze" in command_names
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py::TestWritersRoomAuthenticityAnalyst -v
```

Expected: FAIL — module does not exist.

- [ ] **Step 3: Create package init files**

Create `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/__init__.py`:

```python
```

Create `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/__init__.py`:

```python
from agents.blueprints.writers_room.workforce.authenticity_analyst.commands import analyze
```

- [ ] **Step 4: Create `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/analyze.py`**

```python
"""Authenticity Analyst command: analyze AI authenticity and coherence."""

from agents.ai.archetypes.authenticity_analyst import COMMAND_DESCRIPTION
from agents.blueprints.base import command


@command(
    name="analyze",
    description=COMMAND_DESCRIPTION,
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 5: Create `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py`**

```python
"""Authenticity Analyst — AI text detection, voice authenticity, coherence checking.

Reusable archetype from agents.ai.archetypes, deployed in the Writers Room
via WritersRoomFeedbackBlueprint for context scoping.
"""

from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.writers_room.workforce.authenticity_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint


class AuthenticityAnalystBlueprint(AuthenticityAnalystMixin, WritersRoomFeedbackBlueprint):
    cmd_analyze = analyze
```

Note: mixin comes FIRST in MRO so its `system_prompt` property takes precedence over `WritersRoomFeedbackBlueprint`'s placeholder. `cmd_analyze` is set here because command binding is per-blueprint, not per-archetype.

- [ ] **Step 6: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py -v
```

Expected: PASS all tests (both TestAuthenticityAnalystMixin and TestWritersRoomAuthenticityAnalyst).

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/authenticity_analyst/ backend/agents/tests/test_authenticity_analyst.py
git commit -m "feat(writers-room): add AuthenticityAnalystBlueprint using archetype mixin"
```

---

### Task 3: Register agent and update CreativeReviewer

**Files:**
- Modify: `backend/agents/blueprints/__init__.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`
- Test: `backend/agents/tests/test_authenticity_analyst.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/agents/tests/test_authenticity_analyst.py`:

```python
class TestRegistration:
    def test_get_blueprint_returns_instance(self):
        from agents.blueprints import get_blueprint
        from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin

        bp = get_blueprint("authenticity_analyst", "writers_room")
        assert isinstance(bp, AuthenticityAnalystMixin)

    def test_in_workforce_metadata(self):
        from agents.blueprints import get_workforce_metadata

        metadata = get_workforce_metadata("writers_room")
        slugs = [m["agent_type"] for m in metadata]
        assert "authenticity_analyst" in slugs


class TestCreativeReviewerAuthenticityDimension:
    def test_review_dimensions_includes_authenticity(self):
        from agents.blueprints.writers_room.workforce.creative_reviewer.agent import (
            CreativeReviewerBlueprint,
        )
        bp = CreativeReviewerBlueprint()
        assert "authenticity" in bp.review_dimensions

    def test_system_prompt_mentions_authenticity(self):
        from agents.blueprints.writers_room.workforce.creative_reviewer.agent import (
            CreativeReviewerBlueprint,
        )
        bp = CreativeReviewerBlueprint()
        assert "Authenticity" in bp.system_prompt

    def test_fix_routing_mentions_authenticity(self):
        from agents.blueprints.writers_room.workforce.creative_reviewer.agent import (
            CreativeReviewerBlueprint,
        )
        bp = CreativeReviewerBlueprint()
        assert "authenticity_analyst" in bp.system_prompt
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py::TestRegistration agents/tests/test_authenticity_analyst.py::TestCreativeReviewerAuthenticityDimension -v
```

Expected: FAIL — not registered, review_dimensions missing `authenticity`.

- [ ] **Step 3: Register in `backend/agents/blueprints/__init__.py`**

Find the `_writers_room_imports` dict (around line 74). Add after the `"creative_reviewer"` entry:

```python
    "authenticity_analyst": ("agents.blueprints.writers_room.workforce.authenticity_analyst.agent", "AuthenticityAnalystBlueprint"),
```

- [ ] **Step 4: Update CreativeReviewer `review_dimensions`**

In `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`, find:

```python
    review_dimensions = [
        "concept_fidelity",
        "originality",
        "market_fit",
        "structure",
        "character",
        "dialogue",
        "craft",
        "feasibility",
    ]
```

Replace with:

```python
    review_dimensions = [
        "concept_fidelity",
        "originality",
        "market_fit",
        "structure",
        "character",
        "dialogue",
        "craft",
        "feasibility",
        "authenticity",
    ]
```

- [ ] **Step 5: Update CreativeReviewer system prompt — add dimension 9**

In the same file, find the system prompt string. After the line:

```
8. **Feasibility** — Budget, cast-ability, production practicality
```

Add:

```
9. **Authenticity** — Does the text read as genuinely human? AI linguistic tells, voice flattening, cliche density, coherence/hallucination.
```

- [ ] **Step 6: Update CreativeReviewer system prompt — add fix routing**

In the same system prompt, find the fix routing section. After:

```
- concept_fidelity / originality flags → story_architect AND character_designer
```

Add:

```
- authenticity_analyst flags → lead_writer (voice/cliche issues) or story_architect (coherence/logic issues)
```

- [ ] **Step 7: Update CreativeReviewer system prompt — add analyst to the list**

In the system prompt, find:

```
You receive reports from specialist analysts: market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst.
```

Replace with:

```
You receive reports from specialist analysts: market_analyst, structure_analyst, character_analyst, dialogue_analyst, format_analyst, production_analyst, authenticity_analyst.
```

- [ ] **Step 8: Run tests to confirm they pass**

```bash
cd backend && python -m pytest agents/tests/test_authenticity_analyst.py -v
```

Expected: PASS all tests.

- [ ] **Step 9: Run the full test suite for regressions**

```bash
cd backend && python -m pytest agents/tests/ projects/tests/ -v --tb=short
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add backend/agents/blueprints/__init__.py backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py backend/agents/tests/test_authenticity_analyst.py
git commit -m "feat(writers-room): register authenticity_analyst, add 9th review dimension to CreativeReviewer"
```

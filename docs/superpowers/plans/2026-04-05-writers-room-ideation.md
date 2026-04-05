# Writers Room Ideation & Smart Entry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add smart entry detection and two pre-logline stages (ideation, concept) so the writers room can start from any input — from "write me a blockbuster" to a finished draft.

**Architecture:** Entry detection is a one-shot Claude call on first pipeline invocation that classifies input and picks the right starting stage. Ideation generates competing concepts, feedback agents score them, leader merges the best. Concept stage refines the winner into a foundation for the logline stage. Two new story_architect commands (`generate_concepts`, `develop_concept`) and ideation-specific evaluation logic in the leader.

**Tech Stack:** Python 3.12, Django, existing blueprint framework, Claude API via `call_claude`

**Spec:** `docs/superpowers/specs/2026-04-05-writers-room-ideation-design.md`

---

## File Structure

### Modified
- `backend/agents/blueprints/writers_room/leader/agent.py` — STAGES, matrices, entry detection, ideation-specific evaluation
- `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py` — new execute methods, updated routing
- `backend/agents/blueprints/writers_room/workforce/story_architect/commands/__init__.py` — register new commands
- `backend/projects/models/document.py` — add `concept` and `voice_profile` to DocType choices

### Created
- `backend/agents/blueprints/writers_room/workforce/story_architect/commands/generate_concepts.py`
- `backend/agents/blueprints/writers_room/workforce/story_architect/commands/develop_concept.py`
- `backend/projects/migrations/NNNN_add_concept_voice_profile_doc_types.py` (auto-generated)

### Tests
- `backend/agents/tests/test_writers_room_ideation.py`

---

## Task 1: Add `concept` and `voice_profile` to Document DocType choices

**Files:**
- Modify: `backend/projects/models/document.py:7-11`
- Create: migration (auto-generated)
- Test: `backend/agents/tests/test_writers_room_ideation.py`

- [ ] **Step 1: Write the test**

Create `backend/agents/tests/test_writers_room_ideation.py`:

```python
"""Tests for writers room ideation & smart entry."""

import pytest

from projects.models import Document


class TestDocumentDocTypes:
    def test_concept_doc_type_exists(self):
        assert "concept" in [choice[0] for choice in Document.DocType.choices]

    def test_voice_profile_doc_type_exists(self):
        assert "voice_profile" in [choice[0] for choice in Document.DocType.choices]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header -x`
Expected: FAIL — `concept` and `voice_profile` not in DocType choices

- [ ] **Step 3: Add doc types to Document model**

In `backend/projects/models/document.py`, replace the `DocType` class:

```python
    class DocType(models.TextChoices):
        GENERAL = "general", "General"
        RESEARCH = "research", "Research"
        BRANDING = "branding", "Branding"
        STRATEGY = "strategy", "Strategy"
        CAMPAIGN = "campaign", "Campaign"
        VOICE_PROFILE = "voice_profile", "Voice Profile"
        CONCEPT = "concept", "Concept"
```

- [ ] **Step 4: Generate and apply migration**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python manage.py makemigrations projects -n add_concept_voice_profile_doc_types --settings=config.settings`
Then: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python manage.py migrate --settings=config.settings`

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header -x`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/projects/models/document.py backend/projects/migrations/ backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat: add concept and voice_profile to Document.DocType"
```

---

## Task 2: story_architect — generate_concepts and develop_concept commands

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/generate_concepts.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/develop_concept.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/__init__.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`
- Modify: `backend/agents/tests/test_writers_room_ideation.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_ideation.py`:

```python
from agents.blueprints import get_blueprint


class TestStoryArchitectIdeationCommands:
    def test_generate_concepts_command_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "generate_concepts" in cmds

    def test_develop_concept_command_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "develop_concept" in cmds

    def test_generate_concepts_metadata(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["generate_concepts"]["model"] == "claude-sonnet-4-6"

    def test_develop_concept_metadata(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["develop_concept"]["model"] == "claude-sonnet-4-6"

    def test_existing_commands_still_registered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_structure" in cmds
        assert "fix_structure" in cmds
        assert "outline_act_structure" in cmds
        assert "map_subplot_threads" in cmds
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py::TestStoryArchitectIdeationCommands -v --no-header -x`
Expected: FAIL — `generate_concepts` not found

- [ ] **Step 3: Create generate_concepts command**

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/generate_concepts.py`:

```python
"""Story Architect command: generate competing concept pitches for ideation."""

from agents.blueprints.base import command


@command(
    name="generate_concepts",
    description="Generate 3-5 competing concept pitches based on market research and project goal",
    model="claude-sonnet-4-6",
)
def generate_concepts(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create develop_concept command**

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/develop_concept.py`:

```python
"""Story Architect command: develop a chosen concept into a structured foundation."""

from agents.blueprints.base import command


@command(
    name="develop_concept",
    description="Develop a concept into a structured foundation: premise, conflict, world, format recommendation, series/franchise strategy",
    model="claude-sonnet-4-6",
)
def develop_concept(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 5: Update commands __init__.py**

Replace `backend/agents/blueprints/writers_room/workforce/story_architect/commands/__init__.py`:

```python
"""Story Architect agent commands registry."""

from .develop_concept import develop_concept
from .fix_structure import fix_structure
from .generate_concepts import generate_concepts
from .map_subplot_threads import map_subplot_threads
from .outline_act_structure import outline_act_structure
from .write_structure import write_structure

ALL_COMMANDS = [
    write_structure,
    fix_structure,
    outline_act_structure,
    map_subplot_threads,
    generate_concepts,
    develop_concept,
]
```

- [ ] **Step 6: Update story_architect agent.py — imports and command registration**

In `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`, update the imports:

```python
from agents.blueprints.writers_room.workforce.story_architect.commands import (
    develop_concept,
    fix_structure,
    generate_concepts,
    map_subplot_threads,
    outline_act_structure,
    write_structure,
)
```

Add two new class attributes after the existing command assignments:

```python
    # Register commands from commands/ folder
    write_structure = write_structure
    fix_structure = fix_structure
    outline_act_structure = outline_act_structure
    map_subplot_threads = map_subplot_threads
    generate_concepts = generate_concepts
    develop_concept = develop_concept
```

- [ ] **Step 7: Update story_architect execute_task routing**

In `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`, replace the `execute_task` method:

```python
    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "fix_structure":
            return self._execute_fix_structure(agent, task)
        if task.command_name == "generate_concepts":
            return self._execute_generate_concepts(agent, task)
        if task.command_name == "develop_concept":
            return self._execute_develop_concept(agent, task)
        return self._execute_write_structure(agent, task)
```

- [ ] **Step 8: Add _execute_generate_concepts method**

Add to `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`, after `_execute_fix_structure`:

```python
    def _execute_generate_concepts(self, agent: Agent, task: AgentTask) -> str:
        """Generate 3-5 competing concept pitches for the ideation stage."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "You are in the IDEATION stage. The Story Researcher has completed market "
            "research (included in the task plan above). Based on that research and "
            "the project goal, generate 3-5 COMPETING concept pitches.\n\n"
            "For EACH concept, provide:\n\n"
            "## Concept N: [Working Title]\n"
            "- **Premise:** 2-3 sentences describing the story\n"
            "- **Format:** Film / Series (N episodes) / Limited Series / Filmreihe (N installments)\n"
            "- **Genre:** Primary genre + subgenre\n"
            "- **Tone:** e.g. dark prestige, light comedy, satirical, lyrical\n"
            "- **Target Audience:** Who watches/reads this\n"
            "- **Zeitgeist Hook:** Why this works NOW — what cultural moment does it tap into\n"
            "- **Dramatic Engine:** What drives the story forward episode after episode / act after act\n"
            "- **Unique Angle:** What makes this different from the comps\n\n"
            "Make the concepts DIVERSE — vary genre, format, tone, and audience across "
            "the pitches. Do not generate 5 variations of the same idea. Each concept "
            "should be a genuinely different creative direction.\n\n"
            "If the project goal is vague (e.g. 'write me a blockbuster'), use the "
            "market research to identify underserved opportunities and pitch into those gaps."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "generate_concepts"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 9: Add _execute_develop_concept method**

Add to `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`, after `_execute_generate_concepts`:

```python
    def _execute_develop_concept(self, agent: Agent, task: AgentTask) -> str:
        """Develop a chosen concept into a structured foundation."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "You are in the CONCEPT stage. A concept has been selected (included in "
            "the task plan above, possibly merged from multiple pitches). Develop it "
            "into a structured creative foundation.\n\n"
            "Your output must include:\n\n"
            "## Dramatic Premise\n"
            "The core dramatic question and central conflict in 2-3 sentences.\n\n"
            "## World & Setting\n"
            "Where and when. The rules of this world. What makes it specific.\n\n"
            "## Tonal Compass\n"
            "Reference points for tone. What this feels like. What it does NOT feel like.\n\n"
            "## Format Recommendation\n"
            "Film / Series / Limited Series / Filmreihe — with rationale. If the user "
            "has already set a target format, honor it and explain why it works.\n"
            "- For Series: season arc shape, suggested episode count, pilot hook, "
            "what makes this a series (not just a long movie)\n"
            "- For Filmreihe: installment strategy, what connects them, franchise potential\n"
            "- For Film: why this is a single story, not a series\n\n"
            "## Protagonist Sketch\n"
            "Who drives this story. Want, need, wound, contradiction — in brief.\n\n"
            "## Central Relationship\n"
            "The most important relationship and its trajectory.\n\n"
            "## Why Now\n"
            "The cultural moment this taps into. Why audiences need this story right now.\n\n"
            "This is a FOUNDATION document — it feeds the logline stage. Be specific "
            "enough that someone could write a compelling logline from this alone."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "develop_concept"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response
```

- [ ] **Step 10: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py backend/agents/tests/test_writers_room_skills_commands.py::TestStoryArchitectSkillsAndCommands -v --no-header -x`
Expected: All PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/story_architect/ backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat(writers-room): story_architect generate_concepts + develop_concept commands"
```

---

## Task 3: Leader — update STAGES, matrices, and add entry detection

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:16-79` (STAGES, matrices)
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:289-310` (generate_task_proposal)
- Modify: `backend/agents/tests/test_writers_room_ideation.py`

- [ ] **Step 1: Add tests for stages and entry detection**

Append to `backend/agents/tests/test_writers_room_ideation.py`:

```python
from unittest.mock import patch, MagicMock


class TestStagesAndMatrices:
    def test_stages_include_ideation_and_concept(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        assert STAGES[0] == "ideation"
        assert STAGES[1] == "concept"
        assert STAGES[2] == "logline"

    def test_creative_matrix_has_ideation(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "ideation" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["ideation"]
        assert "story_architect" in CREATIVE_MATRIX["ideation"]

    def test_creative_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        assert "concept" in CREATIVE_MATRIX
        assert "story_researcher" in CREATIVE_MATRIX["concept"]
        assert "story_architect" in CREATIVE_MATRIX["concept"]
        assert "character_designer" in CREATIVE_MATRIX["concept"]

    def test_feedback_matrix_has_ideation(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "ideation" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["ideation"]]
        assert "market_analyst" in agents

    def test_feedback_matrix_has_concept(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        assert "concept" in FEEDBACK_MATRIX
        agents = [a for a, _ in FEEDBACK_MATRIX["concept"]]
        assert "market_analyst" in agents
        assert "character_analyst" in agents


class TestEntryDetection:
    def test_run_entry_detection_returns_stage(self):
        from agents.blueprints.writers_room.leader.agent import _run_entry_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Write me a blockbuster"
        mock_agent.department.project.sources.all.return_value = []
        mock_agent.internal_state = {}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"detected_stage": "ideation", "detected_format": "film", '
                '"format_confidence": "medium", "reasoning": "Vague goal", '
                '"recommended_config": {"target_format": "film"}}',
                {"model": "claude-sonnet-4-6", "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01},
            )
            result = _run_entry_detection(mock_agent)

        assert result == "ideation"
        # Check internal_state was updated
        state = mock_agent.internal_state
        assert state["entry_detected"] is True
        assert state["detected_format"] == "film"

    def test_run_entry_detection_with_draft_material(self):
        from agents.blueprints.writers_room.leader.agent import _run_entry_detection

        mock_agent = MagicMock()
        mock_agent.department.project.goal = "Polish my screenplay"
        mock_source = MagicMock()
        mock_source.extracted_text = "FADE IN: INT. APARTMENT - NIGHT..." * 100
        mock_source.original_filename = "my_screenplay.pdf"
        mock_source.source_type = "file"
        mock_agent.department.project.sources.all.return_value = [mock_source]
        mock_agent.internal_state = {}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.call_claude") as mock_claude:
            mock_claude.return_value = (
                '{"detected_stage": "first_draft", "detected_format": "film", '
                '"format_confidence": "high", "reasoning": "Full screenplay uploaded", '
                '"recommended_config": {"target_format": "film", "genre": "drama"}}',
                {"model": "claude-sonnet-4-6", "input_tokens": 200, "output_tokens": 50, "cost_usd": 0.02},
            )
            result = _run_entry_detection(mock_agent)

        assert result == "first_draft"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py::TestStagesAndMatrices -v --no-header -x`
Expected: FAIL — STAGES[0] is still "logline"

- [ ] **Step 3: Update STAGES list**

In `backend/agents/blueprints/writers_room/leader/agent.py`, replace line 18:

```python
STAGES = ["ideation", "concept", "logline", "expose", "treatment", "step_outline", "first_draft", "revised_draft"]
```

- [ ] **Step 4: Add ideation and concept to FEEDBACK_MATRIX**

In `backend/agents/blueprints/writers_room/leader/agent.py`, add at the beginning of the FEEDBACK_MATRIX dict (before `"logline"`):

```python
FEEDBACK_MATRIX: dict[str, list[tuple[str, str]]] = {
    "ideation": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "concept": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("character_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "logline": [
```

- [ ] **Step 5: Add ideation and concept to CREATIVE_MATRIX**

In `backend/agents/blueprints/writers_room/leader/agent.py`, add at the beginning of the CREATIVE_MATRIX dict (before `"logline"`):

```python
CREATIVE_MATRIX: dict[str, list[str]] = {
    "ideation": ["story_researcher", "story_architect"],
    "concept": ["story_researcher", "story_architect", "character_designer"],
    "logline": ["story_researcher", "dialog_writer"],
```

- [ ] **Step 6: Add _run_entry_detection function**

Add this as a module-level function at the bottom of `backend/agents/blueprints/writers_room/leader/agent.py`, after `_get_merged_config`:

```python
ENTRY_DETECTION_PROMPT = """\
You are the showrunner of a professional writers room. Analyze the project input to determine where the creative pipeline should start.

## Project Goal
{goal}

## Source Material
{sources_summary}

## Existing Config
{config_summary}

## Stage Options (earliest to latest)
- ideation: No concrete story idea. Just a vague theme, genre preference, or "write me something good."
- concept: A rough idea or premise exists but needs development. e.g. "a thriller about a cop who discovers his partner is a serial killer"
- logline: A logline or clear story concept exists, ready for structural work
- expose: An expose, pitch document, or series bible is provided
- treatment: A treatment, Serienkonzept, or detailed narrative outline is provided
- step_outline: A step outline or beat sheet exists
- first_draft: A complete draft (screenplay, manuscript, etc.) is provided
- revised_draft: A draft with revision notes or previous feedback is provided

## Format Detection
Identify the format from the material. Understand German industry terms:
- Serienkonzept = series concept/bible
- Filmreihe = film series / franchise (multiple connected films)
- Drehbuch = screenplay
- Expose/Exposé = pitch document
- Treatment = detailed narrative outline

## Rules
- Pick the EARLIEST stage that matches the material quality. If someone uploaded a weak treatment, start at treatment — feedback agents will catch the weaknesses.
- If NO story idea is present at all, pick ideation.
- If a vague idea exists but no developed concept, pick concept.
- Only skip stages if the material genuinely covers them.

Respond with JSON only:
{
    "detected_stage": "stage_name",
    "detected_format": "film|series|limited_series|filmreihe|novel|theatre|short_story",
    "format_confidence": "high|medium|low",
    "reasoning": "Brief explanation of why this stage was chosen",
    "recommended_config": {
        "target_format": "...",
        "genre": "...",
        "tone": "..."
    }
}

Only include keys in recommended_config that you can confidently infer. Omit keys you're unsure about."""


def _run_entry_detection(agent) -> str:
    """
    One-shot Claude call to classify project input and determine the starting stage.
    Runs exactly once — stores result in internal_state.
    Returns the detected stage name.
    """
    from agents.ai.claude_client import call_claude, parse_json_response
    from projects.models import Source

    project = agent.department.project
    goal = project.goal or "No goal specified"

    # Gather source summaries
    sources = Source.objects.filter(project=project)
    sources_summary = ""
    for s in sources:
        text = s.extracted_text or s.raw_content or ""
        if not text:
            continue
        name = s.original_filename or s.url or "Text input"
        snippet = text[:2000]
        if len(text) > 2000:
            snippet += f"\n[... truncated, {len(text)} chars total ...]"
        sources_summary += f"\n### {name} ({s.source_type})\n{snippet}\n"

    if not sources_summary:
        sources_summary = "No source material uploaded."

    # Gather existing config
    config = _get_merged_config(agent)
    config_keys = ["target_format", "genre", "tone", "target_platform", "locale"]
    config_summary = "\n".join(
        f"- {k}: {config[k]}" for k in config_keys if config.get(k)
    )
    if not config_summary:
        config_summary = "No config set."

    prompt = ENTRY_DETECTION_PROMPT.format(
        goal=goal,
        sources_summary=sources_summary,
        config_summary=config_summary,
    )

    response, _usage = call_claude(
        system_prompt="You are a project classification system. Respond with JSON only.",
        user_message=prompt,
        model="claude-sonnet-4-6",
        max_tokens=1024,
    )

    data = parse_json_response(response)
    if not data or "detected_stage" not in data:
        logger.warning("Entry detection failed to parse, defaulting to ideation: %s", response[:200])
        return "ideation"

    detected_stage = data["detected_stage"]
    if detected_stage not in STAGES:
        logger.warning("Entry detection returned unknown stage '%s', defaulting to ideation", detected_stage)
        detected_stage = "ideation"

    # Store detection results in internal_state
    internal_state = agent.internal_state or {}
    internal_state["entry_detected"] = True
    internal_state["detected_format"] = data.get("detected_format", "")
    internal_state["detection_reasoning"] = data.get("reasoning", "")

    # Store recommended config values (user can override via config)
    recommended = data.get("recommended_config", {})
    if recommended:
        internal_state["recommended_config"] = recommended

    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    logger.info(
        "Writers Room entry detection: stage=%s format=%s reason=%s",
        detected_stage,
        data.get("detected_format"),
        data.get("reasoning", "")[:100],
    )

    return detected_stage
```

- [ ] **Step 7: Update generate_task_proposal to use entry detection**

In `backend/agents/blueprints/writers_room/leader/agent.py`, in the `generate_task_proposal` method, replace the block at lines 301-310 (the "Initialize stage state if needed" block):

```python
        # Initialize stage state if needed
        current_stage = internal_state.get("current_stage")
        if not current_stage:
            # First invocation — run entry detection
            if not internal_state.get("entry_detected"):
                detected_stage = _run_entry_detection(agent)
                # Re-read internal_state since _run_entry_detection saved it
                internal_state = agent.internal_state or {}
            else:
                detected_stage = STAGES[0]

            current_stage = detected_stage
            internal_state["current_stage"] = current_stage
            internal_state["stage_status"] = {}
            internal_state["current_iteration"] = 0
            internal_state["max_iterations"] = 10
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
```

- [ ] **Step 8: Add call_claude import at the top of leader/agent.py**

Add this import inside `_run_entry_detection` (it's already there as a local import — no change needed at module level since the function uses local imports).

Actually, verify that `call_claude` and `parse_json_response` are already imported locally inside `_evaluate_feedback` (line 583). The same pattern is used in `_run_entry_detection`. No module-level import needed.

- [ ] **Step 9: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header -x`
Expected: All PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat(writers-room): smart entry detection + ideation/concept stages in pipeline"
```

---

## Task 4: Leader — ideation-specific creative task framing

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` (`_propose_creative_tasks`)
- Modify: `backend/agents/tests/test_writers_room_ideation.py`

- [ ] **Step 1: Add test**

Append to `backend/agents/tests/test_writers_room_ideation.py`:

```python
class TestIdeationCreativeTaskFraming:
    def test_ideation_stage_uses_generate_concepts_command(self):
        """When stage is ideation, story_architect task should use generate_concepts command."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            ("Researcher", "story_researcher"),
            ("Architect", "story_architect"),
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        # Mock Document.objects to skip voice profiling gate
        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "ideation", {"locale": "en"})

        tasks = result["tasks"]
        architect_task = next((t for t in tasks if t["target_agent_type"] == "story_architect"), None)
        assert architect_task is not None
        assert architect_task.get("command_name") == "generate_concepts"

    def test_concept_stage_uses_develop_concept_command(self):
        """When stage is concept, story_architect task should use develop_concept command."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            ("Researcher", "story_researcher"),
            ("Architect", "story_architect"),
            ("Character", "character_designer"),
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "concept", {"locale": "en"})

        tasks = result["tasks"]
        architect_task = next((t for t in tasks if t["target_agent_type"] == "story_architect"), None)
        assert architect_task is not None
        assert architect_task.get("command_name") == "develop_concept"

    def test_logline_stage_unchanged(self):
        """Logline stage should NOT use ideation commands."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.agents.filter.return_value.values_list.return_value = [
            ("Researcher", "story_researcher"),
            ("Writer", "dialog_writer"),
        ]
        mock_agent.internal_state = {"stage_status": {}}
        mock_agent.get_config_value.return_value = None

        with patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:
            mock_doc.objects.filter.return_value.exists.return_value = True
            result = bp._propose_creative_tasks(mock_agent, "logline", {"locale": "en"})

        tasks = result["tasks"]
        for t in tasks:
            assert t.get("command_name") is None or t["command_name"] not in ("generate_concepts", "develop_concept")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py::TestIdeationCreativeTaskFraming -v --no-header -x`
Expected: FAIL — no `command_name` on ideation tasks yet

- [ ] **Step 3: Modify _propose_creative_tasks**

In `backend/agents/blueprints/writers_room/leader/agent.py`, in `_propose_creative_tasks`, find the loop that builds tasks (around line 486-506). Replace the task-building loop:

```python
        tasks = []
        previous_depends = False
        for agent_type in creative_agents:
            task_data = {
                "target_agent_type": agent_type,
                "exec_summary": f"Write {stage} content ({agent_type})",
                "step_plan": (
                    f"Stage: {stage}\n"
                    f"Locale: {locale}\n"
                    f"{format_context}\n"
                    f"Write your contribution for the '{stage}' stage of this project. "
                    f"Consult department documents for existing material and briefings for the project brief.\n\n"
                    f"Your output must be in {locale}. This is non-negotiable."
                ),
                "depends_on_previous": previous_depends,
            }

            # Ideation/concept: use specific commands for story_architect
            if stage == "ideation" and agent_type == "story_architect":
                task_data["command_name"] = "generate_concepts"
                task_data["exec_summary"] = "Generate 3-5 competing concept pitches"
                task_data["step_plan"] = (
                    f"Stage: ideation\n"
                    f"Locale: {locale}\n"
                    f"{format_context}\n"
                    f"Based on the Story Researcher's market analysis and the project goal, "
                    f"generate 3-5 diverse, competing concept pitches. Each must have a "
                    f"working title, premise, format recommendation, genre, tone, target "
                    f"audience, and zeitgeist hook.\n\n"
                    f"Consult department documents for the research brief.\n\n"
                    f"Your output must be in {locale}."
                )
            elif stage == "concept" and agent_type == "story_architect":
                task_data["command_name"] = "develop_concept"
                task_data["exec_summary"] = "Develop concept into structured foundation"
                task_data["step_plan"] = (
                    f"Stage: concept\n"
                    f"Locale: {locale}\n"
                    f"{format_context}\n"
                    f"Develop the selected concept into a structured creative foundation. "
                    f"Include dramatic premise, world/setting, tonal compass, format "
                    f"recommendation, protagonist sketch, and central relationship.\n\n"
                    f"Consult department documents for the concept and research.\n\n"
                    f"Your output must be in {locale}."
                )

            tasks.append(task_data)
            # After story_researcher, subsequent agents should wait for research
            if agent_type == "story_researcher":
                previous_depends = True
```

- [ ] **Step 4: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header -x`
Expected: All PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat(writers-room): ideation/concept-specific creative task framing"
```

---

## Task 5: Leader — ideation-specific feedback evaluation (merge logic)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` (`_evaluate_feedback`)
- Modify: `backend/agents/tests/test_writers_room_ideation.py`

- [ ] **Step 1: Add test**

Append to `backend/agents/tests/test_writers_room_ideation.py`:

```python
@pytest.mark.django_db
class TestIdeationMergeEvaluation:
    def test_ideation_evaluation_stores_merged_concept(self, db):
        """Ideation feedback evaluation should store merged concept as Document."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_agent = MagicMock()
        mock_agent.department.id = "dept-123"
        mock_agent.department.project.id = "proj-123"
        mock_agent.internal_state = {
            "current_stage": "ideation",
            "stage_status": {"ideation": {"status": "feedback_done", "iterations": 0}},
        }

        # Mock AgentTask queryset for feedback gathering
        mock_feedback = [
            ("market_analyst", "Concept 2 strongest commercial hook. Concept 4 best zeitgeist angle.", "Analyze"),
            ("structure_analyst", "Concept 2 has solid dramatic engine.", "Analyze"),
        ]

        with patch("agents.blueprints.writers_room.leader.agent.AgentTask") as mock_task_cls, \
             patch("agents.blueprints.writers_room.leader.agent.call_claude") as mock_claude, \
             patch("agents.blueprints.writers_room.leader.agent.parse_json_response") as mock_parse, \
             patch("agents.blueprints.writers_room.leader.agent.Document") as mock_doc:

            mock_task_cls.objects.filter.return_value.order_by.return_value.__getitem__.return_value.values_list.return_value = mock_feedback
            mock_parse.return_value = {
                "merged_concept": "A thriller about...",
                "reasoning": "Concept 2 had the best premise, merged with Concept 4's zeitgeist hook",
                "winner": "Concept 2",
                "elements_merged": ["Concept 4 zeitgeist angle", "Concept 1 setting"],
            }

            result = bp._evaluate_feedback(mock_agent, "ideation", {"locale": "en"}, 2)

        # Should have created a Document with the merged concept
        mock_doc.objects.update_or_create.assert_called_once()
        call_kwargs = mock_doc.objects.update_or_create.call_args
        assert call_kwargs[1]["defaults"]["doc_type"] == "concept"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py::TestIdeationMergeEvaluation -v --no-header -x`
Expected: FAIL

- [ ] **Step 3: Add ideation merge logic to _evaluate_feedback**

In `backend/agents/blueprints/writers_room/leader/agent.py`, in `_evaluate_feedback`, add an early return for ideation stage. Insert right after the `feedback_text` is built (after the loop at ~line 606), before the existing `context_msg = self.build_context_message(agent)` line:

```python
        # ── Special handling: ideation stage uses merge evaluation ──────
        if stage == "ideation":
            return self._evaluate_ideation_feedback(
                agent, stage, config, quality_threshold, feedback_text
            )
```

Then add the new method after `_evaluate_feedback`:

```python
    def _evaluate_ideation_feedback(
        self,
        agent: Agent,
        stage: str,
        config: dict,
        quality_threshold: int,
        feedback_text: str,
    ) -> dict | None:
        """
        Special evaluation for ideation stage: rank concepts, merge best elements,
        store merged concept as Document, advance to concept stage.
        """
        from agents.ai.claude_client import call_claude, parse_json_response
        from projects.models import Document

        locale = config.get("locale", "en")

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Evaluate Ideation Concepts

## Feedback from Analysts
{feedback_text}

# Task
You are evaluating 3-5 competing concept pitches that were scored by feedback agents.

1. RANK all concepts based on the feedback (commercial viability, dramatic potential, feasibility)
2. PICK the winner — the concept with the strongest foundation
3. IDENTIFY strong elements from the runners-up that could strengthen the winner
4. PRODUCE one merged concept that combines the best of all pitches

If ALL concepts received 🔴 critical flags with no redeeming qualities, return:
{{"all_failed": true, "reasoning": "..."}}

Otherwise, return:
{{
    "all_failed": false,
    "winner": "Concept N title",
    "reasoning": "Why this concept won and what was merged",
    "elements_merged": ["Element from Concept X", "Element from Concept Y"],
    "merged_concept": "The complete merged concept description — 2-4 paragraphs covering premise, format, genre, tone, audience, and zeitgeist hook. Written in {locale}."
}}"""

        response, _usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
            model=self.get_model(agent, command_name="check-progress"),
        )

        data = parse_json_response(response)
        if not data:
            logger.warning("Writers Room: failed to parse ideation evaluation: %s", response[:300])
            return None

        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})

        if data.get("all_failed"):
            # All concepts failed — loop: re-run ideation with feedback context
            current_info["status"] = "not_started"
            current_info["iterations"] = current_info.get("iterations", 0) + 1
            stage_status[stage] = current_info
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            logger.info("Writers Room: all ideation concepts failed, re-running ideation")
            return self._propose_creative_tasks(agent, stage, config)

        # Store merged concept as Document
        merged_text = data.get("merged_concept", "")
        if merged_text:
            Document.objects.update_or_create(
                department=agent.department,
                title="Merged Concept",
                defaults={
                    "content": merged_text,
                    "doc_type": "concept",
                },
            )

        # Mark ideation as passed, advance to concept
        current_info["status"] = "passed"
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        internal_state["current_stage"] = "concept"
        internal_state["current_iteration"] = 0
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        logger.info("Writers Room: ideation PASSED — merged concept stored, advancing to concept stage")
        return self._propose_creative_tasks(agent, "concept", config)
```

- [ ] **Step 4: Add Document import at the top of _propose_creative_tasks**

The `Document` import is already present as a local import in `_propose_creative_tasks` (line 404). Add it also in `_evaluate_ideation_feedback` (done in the code above as a local import). No module-level changes needed.

- [ ] **Step 5: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header -x`
Expected: All PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat(writers-room): ideation merge evaluation — rank concepts, merge best, store Document"
```

---

## Task 6: Full regression test

**Files:**
- Test: `backend/agents/tests/test_writers_room_ideation.py`
- Test: `backend/agents/tests/test_writers_room_skills_commands.py`
- Test: `backend/agents/tests/test_blueprints.py`

- [ ] **Step 1: Run ideation tests**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_ideation.py -v --no-header`
Expected: All PASS

- [ ] **Step 2: Run skills/commands tests (regression)**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header`
Expected: 32 tests PASS

- [ ] **Step 3: Run blueprint tests (regression)**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/agents/tests/test_blueprints.py -v --no-header`
Expected: All PASS (31 pass, possibly 1 DB lock error from parallel worktree — not a real failure)

- [ ] **Step 4: Run full backend test suite**

Run: `cd /Users/christianpeters/the-agentic-company && backend/venv/bin/python -m pytest backend/ -v --no-header -x`
Expected: All PASS

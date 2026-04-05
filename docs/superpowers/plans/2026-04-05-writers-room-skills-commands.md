# Writers Room Skills & Commands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `commands/` and `skills/` folder structure to all 10 writers room workforce agents — migrate inline commands, add technique-rich skills.

**Architecture:** Extract inline `@command` methods from each agent's `agent.py` into separate files under `commands/`. Create `skills/` folders with auto-discovered skill modules (NAME + DESCRIPTION constants). Each agent gets 5 skills encoding professional craft techniques. Uses existing framework — no changes to `base.py`.

**Tech Stack:** Python 3.12, Django, existing blueprint framework (`@command` decorator, `pkgutil` auto-discovery)

**Spec:** `docs/superpowers/specs/2026-04-05-writers-room-skills-commands-design.md`

---

## Task 1: story_architect — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/write_structure.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/fix_structure.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/outline_act_structure.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/commands/map_subplot_threads.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/tension_mapping.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/premise_to_theme.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/narrative_clock.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/setup_payoff.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_architect/skills/structural_reversal.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`
- Test: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Create the test file**

Create `backend/agents/tests/test_writers_room_skills_commands.py` with tests for story_architect:

```python
"""Tests for writers room workforce skills and commands folder structure."""

import pytest

from agents.blueprints import get_blueprint


class TestStoryArchitectSkillsAndCommands:
    """Verify story_architect has commands in files and auto-discovered skills."""

    def test_commands_discovered(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_structure" in names
        assert "fix_structure" in names
        assert "outline_act_structure" in names
        assert "map_subplot_threads" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("story_architect", "writers_room")
        skills = bp.skills_description
        assert "Three-Act Tension Mapping" in skills
        assert "Premise-to-Theme Ladder" in skills
        assert "Narrative Clock Design" in skills
        assert "Setup-Payoff Ledger" in skills
        assert "Structural Reversal Engineering" in skills

    def test_skills_format(self):
        bp = get_blueprint("story_architect", "writers_room")
        skills = bp.skills_description
        # Each skill should be a markdown bullet with bold name
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")

    def test_command_metadata_preserved(self):
        bp = get_blueprint("story_architect", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["write_structure"]["model"] == "claude-sonnet-4-6"
        assert cmds["fix_structure"]["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: FAIL — `outline_act_structure` not found in commands, skills still hardcoded

- [ ] **Step 3: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/__init__.py`:

```python
"""Story Architect agent commands registry."""

from .fix_structure import fix_structure
from .map_subplot_threads import map_subplot_threads
from .outline_act_structure import outline_act_structure
from .write_structure import write_structure

ALL_COMMANDS = [write_structure, fix_structure, outline_act_structure, map_subplot_threads]
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/write_structure.py`:

```python
"""Story Architect command: write story structure for current project stage."""

from agents.blueprints.base import command


@command(
    name="write_structure",
    description="Write or create story structure for the current project stage",
    model="claude-sonnet-4-6",
)
def write_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/fix_structure.py`:

```python
"""Story Architect command: rewrite structure based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_structure",
    description="Rewrite structure based on Structure Analyst and Format Analyst feedback",
    model="claude-sonnet-4-6",
)
def fix_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/outline_act_structure.py`:

```python
"""Story Architect command: break story into acts with turning points."""

from agents.blueprints.base import command


@command(
    name="outline_act_structure",
    description="Break story into acts with turning points, midpoint reversal, and climax placement",
    model="claude-sonnet-4-6",
)
def outline_act_structure(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/commands/map_subplot_threads.py`:

```python
"""Story Architect command: chart subplot lines and intersections."""

from agents.blueprints.base import command


@command(
    name="map_subplot_threads",
    description="Chart all subplot lines, their intersections with the A-story, and resolution timing",
    model="claude-sonnet-4-6",
)
def map_subplot_threads(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/__init__.py`:

```python
"""Story Architect agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/tension_mapping.py`:

```python
NAME = "Three-Act Tension Mapping"
DESCRIPTION = (
    "Maps tension curves across act structure using the principle that each scene "
    "must escalate, complicate, or release tension. Identifies flat zones where "
    "narrative momentum stalls and recommends scene reordering or compression."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/premise_to_theme.py`:

```python
NAME = "Premise-to-Theme Ladder"
DESCRIPTION = (
    "Traces whether the story's premise (what happens) consistently escalates into "
    "theme (what it means). Flags scenes that serve plot but fail to reinforce the "
    "thematic argument."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/narrative_clock.py`:

```python
NAME = "Narrative Clock Design"
DESCRIPTION = (
    "Designs ticking-clock urgency structures — deadlines, countdowns, narrowing "
    "options — that create forward momentum independent of action. Evaluates whether "
    "the audience always knows what's at stake and when it expires."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/setup_payoff.py`:

```python
NAME = "Setup-Payoff Ledger"
DESCRIPTION = (
    "Tracks every planted setup (Chekhov's guns, foreshadowing, motifs) and verifies "
    "each has a satisfying payoff. Flags orphaned setups with no resolution and "
    "unearned payoffs that lack prior groundwork."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_architect/skills/structural_reversal.py`:

```python
NAME = "Structural Reversal Engineering"
DESCRIPTION = (
    "Designs plot reversals that recontextualize earlier scenes rather than merely "
    "surprising. Tests each reversal against the rewatch criterion — does knowing "
    "the twist make earlier scenes richer, not cheaper?"
)
```

- [ ] **Step 5: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`:

1. Remove the two inline `@command` methods (`write_structure` and `fix_structure`)
2. Add imports for commands and skills
3. Assign commands as class attributes
4. Replace `skills_description` property with `format_skills()` call

The imports section becomes:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.story_architect.commands import (
    fix_structure,
    map_subplot_threads,
    outline_act_structure,
    write_structure,
)
from agents.blueprints.writers_room.workforce.story_architect.skills import format_skills

logger = logging.getLogger(__name__)
```

Remove the `command` import from `agents.blueprints.base` (no longer needed).

The class gets command assignments and updated skills property:

```python
class StoryArchitectBlueprint(WorkforceBlueprint):
    name = "Story Architect"
    slug = "story_architect"
    description = "Master of narrative structure -- builds story frameworks across all formats and stages"
    tags = ["writers-room", "structure", "story", "beats", "architecture"]
    config_schema = {
        "locale": {
            "type": "str",
            "required": False,
            "label": "Output Language",
            "description": "ISO locale for all creative output (e.g. 'en', 'de', 'fr'). Defaults to 'en'.",
        },
    }

    @property
    def system_prompt(self) -> str:
        return (
            # ... UNCHANGED — keep the entire existing system_prompt string ...
        )

    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands/ folder
    write_structure = write_structure
    fix_structure = fix_structure
    outline_act_structure = outline_act_structure
    map_subplot_threads = map_subplot_threads

    # ... rest of agent.py unchanged: _get_voice_constraint, execute_task,
    # _execute_write_structure, _execute_fix_structure ...
```

**Critical:** The `execute_task` method and all `_execute_*` methods stay in `agent.py` unchanged. Only the inline `@command` decorated stubs and the `skills_description` property change.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: 4 tests PASS

- [ ] **Step 7: Run full blueprint test suite for regression**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_blueprints.py -v --no-header -x`
Expected: All existing tests PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/story_architect/commands/ backend/agents/blueprints/writers_room/workforce/story_architect/skills/ backend/agents/blueprints/writers_room/workforce/story_architect/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): story_architect commands + skills folders"
```

---

## Task 2: dialog_writer — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/write_content.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/fix_content.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/write_scene_dialogue.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/rewrite_for_subtext.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/subtext_layering.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/voice_fingerprinting.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/conflict_escalation.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/exposition_laundering.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/silence_scripting.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests for dialog_writer**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestDialogWriterSkillsAndCommands:
    """Verify dialog_writer has commands in files and auto-discovered skills."""

    def test_commands_discovered(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_content" in names
        assert "fix_content" in names
        assert "write_scene_dialogue" in names
        assert "rewrite_for_subtext" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        skills = bp.skills_description
        assert "Subtext Layering" in skills
        assert "Voice Fingerprinting" in skills
        assert "Conflict Escalation Rhythm" in skills
        assert "Exposition Laundering" in skills
        assert "Silence and Non-Verbal Scripting" in skills

    def test_skills_format(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")

    def test_command_metadata_preserved(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        assert cmds["write_content"]["model"] == "claude-sonnet-4-6"
        assert cmds["fix_content"]["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py::TestDialogWriterSkillsAndCommands -v --no-header -x`
Expected: FAIL

- [ ] **Step 3: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/__init__.py`:

```python
"""Dialog Writer agent commands registry."""

from .fix_content import fix_content
from .rewrite_for_subtext import rewrite_for_subtext
from .write_content import write_content
from .write_scene_dialogue import write_scene_dialogue

ALL_COMMANDS = [write_content, fix_content, write_scene_dialogue, rewrite_for_subtext]
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/write_content.py`:

```python
"""Dialog Writer command: write content for current stage."""

from agents.blueprints.base import command


@command(
    name="write_content",
    description="Write the actual content (dialogue, prose, scenes) for the current stage",
    model="claude-sonnet-4-6",
)
def write_content(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/fix_content.py`:

```python
"""Dialog Writer command: rewrite content based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_content",
    description="Rewrite content based on Dialogue Analyst and Format Analyst feedback",
    model="claude-sonnet-4-6",
)
def fix_content(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/write_scene_dialogue.py`:

```python
"""Dialog Writer command: draft dialogue for a specific scene."""

from agents.blueprints.base import command


@command(
    name="write_scene_dialogue",
    description="Draft dialogue for a specific scene given characters, context, and emotional beats",
    model="claude-sonnet-4-6",
)
def write_scene_dialogue(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/rewrite_for_subtext.py`:

```python
"""Dialog Writer command: layer subtext into existing dialogue."""

from agents.blueprints.base import command


@command(
    name="rewrite_for_subtext",
    description="Take existing dialogue and layer in subtext, power dynamics, and unspoken meaning",
    model="claude-sonnet-4-6",
)
def rewrite_for_subtext(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/__init__.py`:

```python
"""Dialog Writer agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/subtext_layering.py`:

```python
NAME = "Subtext Layering"
DESCRIPTION = (
    "Writes dialogue where characters never say what they actually mean. Encodes "
    "wants, fears, and power dynamics beneath surface conversation using deflection, "
    "topic changes, over-specificity, and conspicuous avoidance."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/voice_fingerprinting.py`:

```python
NAME = "Voice Fingerprinting"
DESCRIPTION = (
    "Gives each character a unique speech pattern through vocabulary range, sentence "
    "length distribution, verbal tics, cultural references, and comfort with silence. "
    "Two characters should never be interchangeable on the page."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/conflict_escalation.py`:

```python
NAME = "Conflict Escalation Rhythm"
DESCRIPTION = (
    "Structures dialogue exchanges as micro-negotiations where each line shifts the "
    "power balance. Maps the give-and-take rhythm so conversations build rather than "
    "circle, with clear beats where control transfers."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/exposition_laundering.py`:

```python
NAME = "Exposition Laundering"
DESCRIPTION = (
    "Buries necessary information inside character conflict, discovery, or emotional "
    "reaction so it never reads as the author explaining. Tests each expository line "
    "against: would this character say this to this person in this moment?"
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/silence_scripting.py`:

```python
NAME = "Silence and Non-Verbal Scripting"
DESCRIPTION = (
    "Writes the pauses, interruptions, trailing-off, and action lines between dialogue "
    "that carry as much meaning as words. Designs moments where what isn't said is the "
    "scene's real content."
)
```

- [ ] **Step 5: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`:

Replace imports:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.dialog_writer.commands import (
    fix_content,
    rewrite_for_subtext,
    write_content,
    write_scene_dialogue,
)
from agents.blueprints.writers_room.workforce.dialog_writer.skills import format_skills

logger = logging.getLogger(__name__)
```

Remove inline `@command` methods (`write_content`, `fix_content`).

Add class attributes and update `skills_description`:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands/ folder
    write_content = write_content
    fix_content = fix_content
    write_scene_dialogue = write_scene_dialogue
    rewrite_for_subtext = rewrite_for_subtext
```

Keep all `_get_voice_constraint`, `execute_task`, `_execute_write_content`, `_execute_fix_content` methods unchanged.

- [ ] **Step 6: Run tests**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS (story_architect + dialog_writer)

- [ ] **Step 7: Commit**

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/dialog_writer/commands/ backend/agents/blueprints/writers_room/workforce/dialog_writer/skills/ backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): dialog_writer commands + skills folders"
```

---

## Task 3: character_designer — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/commands/write_characters.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/commands/fix_characters.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/commands/build_character_profile.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/commands/design_character_voice.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/wound_want_need.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/contradiction_mapping.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/pressure_testing.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/relationship_web.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_designer/skills/arc_milestones.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestCharacterDesignerSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("character_designer", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "write_characters" in names
        assert "fix_characters" in names
        assert "build_character_profile" in names
        assert "design_character_voice" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("character_designer", "writers_room")
        skills = bp.skills_description
        assert "Wound-Want-Need Triangle" in skills
        assert "Contradiction Mapping" in skills
        assert "Behavioral Pressure Testing" in skills
        assert "Relationship Web Dynamics" in skills
        assert "Arc Milestone Design" in skills

    def test_skills_format(self):
        bp = get_blueprint("character_designer", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py::TestCharacterDesignerSkillsAndCommands -v --no-header -x`
Expected: FAIL

- [ ] **Step 3: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/character_designer/commands/__init__.py`:

```python
"""Character Designer agent commands registry."""

from .build_character_profile import build_character_profile
from .design_character_voice import design_character_voice
from .fix_characters import fix_characters
from .write_characters import write_characters

ALL_COMMANDS = [write_characters, fix_characters, build_character_profile, design_character_voice]
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/commands/write_characters.py`:

```python
"""Character Designer command: design character ensemble for current stage."""

from agents.blueprints.base import command


@command(
    name="write_characters",
    description="Design and develop the character ensemble for the current stage",
    model="claude-sonnet-4-6",
)
def write_characters(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/commands/fix_characters.py`:

```python
"""Character Designer command: revise characters based on analyst feedback."""

from agents.blueprints.base import command


@command(
    name="fix_characters",
    description="Revise characters based on Character Analyst feedback flags",
    model="claude-sonnet-4-6",
)
def fix_characters(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/commands/build_character_profile.py`:

```python
"""Character Designer command: generate deep character profile from concept."""

from agents.blueprints.base import command


@command(
    name="build_character_profile",
    description="Generate deep character profile from concept sketch: psychology, contradictions, arc trajectory",
    model="claude-sonnet-4-6",
)
def build_character_profile(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/commands/design_character_voice.py`:

```python
"""Character Designer command: create voice guide for a character."""

from agents.blueprints.base import command


@command(
    name="design_character_voice",
    description="Create a voice guide for a character: speech patterns, vocabulary, rhetorical habits",
    model="claude-sonnet-4-6",
)
def design_character_voice(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/__init__.py`:

```python
"""Character Designer agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/wound_want_need.py`:

```python
NAME = "Wound-Want-Need Triangle"
DESCRIPTION = (
    "Designs characters from the inside out: the wound (past damage that shaped them), "
    "the want (conscious goal driven by the wound), and the need (unconscious truth "
    "they must accept). Every character decision traces back to this triangle."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/contradiction_mapping.py`:

```python
NAME = "Contradiction Mapping"
DESCRIPTION = (
    "Builds characters with deliberate internal contradictions — a pacifist with a "
    "violent temper, a generous person who hoards information. Maps which contradiction "
    "surfaces in which context, making characters unpredictable yet coherent."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/pressure_testing.py`:

```python
NAME = "Behavioral Pressure Testing"
DESCRIPTION = (
    "Stress-tests characters by placing them in scenarios that force impossible choices "
    "between their values. Reveals whether the character has genuine depth or collapses "
    "into archetype under pressure."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/relationship_web.py`:

```python
NAME = "Relationship Web Dynamics"
DESCRIPTION = (
    "Maps every character relationship as a power dynamic with history, debt, and "
    "tension. Identifies redundant relationships (two characters serving the same "
    "narrative function) and missing relationships (tensions that have no embodiment)."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_designer/skills/arc_milestones.py`:

```python
NAME = "Arc Milestone Design"
DESCRIPTION = (
    "Plots character transformation as concrete behavioral changes, not abstract growth. "
    "Defines the specific moment the character acts differently than they would have in "
    "act one, and engineers the causal chain that makes the change earned."
)
```

- [ ] **Step 5: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py`:

Replace imports:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.character_designer.commands import (
    build_character_profile,
    design_character_voice,
    fix_characters,
    write_characters,
)
from agents.blueprints.writers_room.workforce.character_designer.skills import format_skills

logger = logging.getLogger(__name__)
```

Remove inline `@command` methods. Add class attributes and update `skills_description`:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands/ folder
    write_characters = write_characters
    fix_characters = fix_characters
    build_character_profile = build_character_profile
    design_character_voice = design_character_voice
```

Keep all `_get_voice_constraint`, `execute_task`, `_execute_write_characters`, `_execute_fix_characters` methods unchanged.

- [ ] **Step 6: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/character_designer/commands/ backend/agents/blueprints/writers_room/workforce/character_designer/skills/ backend/agents/blueprints/writers_room/workforce/character_designer/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): character_designer commands + skills folders"
```

---

## Task 4: story_researcher — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/research.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/revise_research.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/profile_voice.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/research_setting.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/fact_check_narrative.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/lived_detail.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/anachronism_detection.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/expert_scaffolding.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/cultural_sensitivity.py`
- Create: `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/world_consistency.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestStoryResearcherSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("story_researcher", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "research" in names
        assert "revise_research" in names
        assert "profile_voice" in names
        assert "research_setting" in names
        assert "fact_check_narrative" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("story_researcher", "writers_room")
        skills = bp.skills_description
        assert "Lived-Detail Extraction" in skills
        assert "Anachronism Detection" in skills
        assert "Expert Knowledge Scaffolding" in skills
        assert "Cultural Sensitivity Audit" in skills
        assert "World-Building Consistency Check" in skills

    def test_skills_format(self):
        bp = get_blueprint("story_researcher", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py::TestStoryResearcherSkillsAndCommands -v --no-header -x`
Expected: FAIL

- [ ] **Step 3: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/__init__.py`:

```python
"""Story Researcher agent commands registry."""

from .fact_check_narrative import fact_check_narrative
from .profile_voice import profile_voice
from .research import research
from .research_setting import research_setting
from .revise_research import revise_research

ALL_COMMANDS = [research, revise_research, profile_voice, research_setting, fact_check_narrative]
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/research.py`:

```python
"""Story Researcher command: market research and positioning."""

from agents.blueprints.base import command


@command(
    name="research",
    description="Market research, comps, positioning, zeitgeist, and platform requirements for the project",
    model="claude-sonnet-4-6",
)
def research(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/revise_research.py`:

```python
"""Story Researcher command: update research based on feedback."""

from agents.blueprints.base import command


@command(
    name="revise_research",
    description="Update research based on Market Analyst feedback flags",
    model="claude-sonnet-4-6",
)
def revise_research(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/profile_voice.py`:

```python
"""Story Researcher command: analyze source material for voice profile."""

from agents.blueprints.base import command


@command(
    name="profile_voice",
    description="Analyze uploaded source material and produce a structured voice profile for the writing team",
    model="claude-sonnet-4-6",
)
def profile_voice(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/research_setting.py`:

```python
"""Story Researcher command: deep-dive setting research."""

from agents.blueprints.base import command


@command(
    name="research_setting",
    description="Deep-dive research into a time period, location, or subculture for authenticity",
    model="claude-sonnet-4-6",
)
def research_setting(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/commands/fact_check_narrative.py`:

```python
"""Story Researcher command: verify factual claims in manuscript."""

from agents.blueprints.base import command


@command(
    name="fact_check_narrative",
    description="Verify factual claims, timelines, and technical details in a manuscript",
    model="claude-sonnet-4-6",
)
def fact_check_narrative(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/__init__.py`:

```python
"""Story Researcher agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/lived_detail.py`:

```python
NAME = "Lived-Detail Extraction"
DESCRIPTION = (
    "Researches not just facts but the sensory, social, and emotional texture of a "
    "setting. Focuses on what people ate, complained about, misunderstood, and took "
    "for granted — the mundane details that make fiction feel inhabited rather than "
    "researched."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/anachronism_detection.py`:

```python
NAME = "Anachronism Detection"
DESCRIPTION = (
    "Cross-references language, technology, social norms, and material culture against "
    "the story's time period. Catches not just obvious anachronisms but subtle ones — "
    "attitudes, idioms, and assumptions that belong to the writer's era, not the "
    "character's."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/expert_scaffolding.py`:

```python
NAME = "Expert Knowledge Scaffolding"
DESCRIPTION = (
    "Translates domain expertise (medical, legal, military, scientific) into "
    "character-appropriate dialogue and behavior. Ensures specialists sound like "
    "specialists without turning scenes into lectures."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/cultural_sensitivity.py`:

```python
NAME = "Cultural Sensitivity Audit"
DESCRIPTION = (
    "Evaluates portrayals of cultures, communities, and identities for accuracy, "
    "nuance, and potential harm. Flags stereotypes, monolithic portrayals, and missing "
    "context while suggesting specific improvements grounded in primary sources."
)
```

Create `backend/agents/blueprints/writers_room/workforce/story_researcher/skills/world_consistency.py`:

```python
NAME = "World-Building Consistency Check"
DESCRIPTION = (
    "Maintains an internal logic ledger for fictional worlds: rules of magic, political "
    "structures, economic systems, geography. Catches violations where the story "
    "contradicts its own established rules."
)
```

- [ ] **Step 5: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`:

Replace imports:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.story_researcher.commands import (
    fact_check_narrative,
    profile_voice,
    research,
    research_setting,
    revise_research,
)
from agents.blueprints.writers_room.workforce.story_researcher.skills import format_skills

logger = logging.getLogger(__name__)
```

Remove inline `@command` methods. Add class attributes and update `skills_description`:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands/ folder
    research = research
    revise_research = revise_research
    profile_voice = profile_voice
    research_setting = research_setting
    fact_check_narrative = fact_check_narrative
```

Keep `_get_voice_constraint`, `execute_task`, `_execute_research`, `_execute_revise_research`, `_execute_profile_voice` unchanged.

- [ ] **Step 6: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/story_researcher/commands/ backend/agents/blueprints/writers_room/workforce/story_researcher/skills/ backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): story_researcher commands + skills folders"
```

---

## Task 5: structure_analyst — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/pacing_heatmap.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/scene_necessity.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/structural_symmetry.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/pov_discipline.py`
- Create: `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/transition_scoring.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestStructureAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        skills = bp.skills_description
        assert "Pacing Heat Map" in skills
        assert "Scene Necessity Audit" in skills
        assert "Structural Symmetry Analysis" in skills
        assert "Point-of-View Discipline Check" in skills
        assert "Transition Flow Scoring" in skills

    def test_skills_format(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/commands/__init__.py`:

```python
"""Structure Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/commands/analyze.py`:

```python
"""Structure Analyst command: analyze narrative structure."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for narrative structure against established frameworks",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 3: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/__init__.py`:

```python
"""Structure Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/pacing_heatmap.py`:

```python
NAME = "Pacing Heat Map"
DESCRIPTION = (
    "Measures scene-by-scene pacing by analyzing the ratio of action to reflection, "
    "dialogue to description, and scene length variance. Produces a narrative rhythm "
    "profile that shows where the story rushes, drags, or breathes."
)
```

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/scene_necessity.py`:

```python
NAME = "Scene Necessity Audit"
DESCRIPTION = (
    "Applies the cut test to every scene: if removed, does the story still make sense? "
    "Scenes that pass the cut test without consequence are flagged for elimination or "
    "combination. Every scene must turn at least one value."
)
```

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/structural_symmetry.py`:

```python
NAME = "Structural Symmetry Analysis"
DESCRIPTION = (
    "Evaluates whether the story's structure has intentional mirroring, echoes, and "
    "callbacks between beginning and end, setup and payoff sections. Identifies "
    "asymmetries that feel like oversights rather than artistic choices."
)
```

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/pov_discipline.py`:

```python
NAME = "Point-of-View Discipline Check"
DESCRIPTION = (
    "Verifies consistent POV handling within scenes — catches head-hopping, knowledge "
    "leaks where a character knows something they shouldn't, and perspective breaks "
    "that pull the reader out of immersion."
)
```

Create `backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/transition_scoring.py`:

```python
NAME = "Transition Flow Scoring"
DESCRIPTION = (
    "Evaluates scene-to-scene transitions for logical flow, temporal clarity, and "
    "emotional continuity. Flags jarring jumps that disorient the reader and smooth "
    "transitions that accidentally flatten dramatic contrast."
)
```

- [ ] **Step 4: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`:

Replace imports (remove `command` from base import):

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.structure_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.structure_analyst.skills import format_skills
```

Remove the inline `cmd_analyze` method. Add class attribute and update skills:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    # Register commands from commands/ folder
    cmd_analyze = analyze
```

**Note:** The class attribute is named `cmd_analyze` to match the original method name that `dir(self)` discovers. Keep `execute_task` unchanged.

- [ ] **Step 5: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/structure_analyst/commands/ backend/agents/blueprints/writers_room/workforce/structure_analyst/skills/ backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): structure_analyst commands + skills folders"
```

---

## Task 6: character_analyst — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/motivation_chain.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/consistency_drift.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/agency_audit.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/distinctiveness_index.py`
- Create: `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/emotional_arc.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestCharacterAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("character_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("character_analyst", "writers_room")
        skills = bp.skills_description
        assert "Motivation Chain Validation" in skills
        assert "Consistency Drift Detection" in skills
        assert "Agency Audit" in skills
        assert "Distinctiveness Index" in skills
        assert "Emotional Arc Tracking" in skills

    def test_skills_format(self):
        bp = get_blueprint("character_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/commands/__init__.py`:

```python
"""Character Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/commands/analyze.py`:

```python
"""Character Analyst command: analyze character consistency and logic."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for character consistency, motivation, and logic",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 3: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/__init__.py`:

```python
"""Character Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/motivation_chain.py`:

```python
NAME = "Motivation Chain Validation"
DESCRIPTION = (
    "Traces every character decision back to established motivation. Flags actions that "
    "serve plot convenience rather than character truth — the idiot plot detector where "
    "characters act stupidly because the story needs them to."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/consistency_drift.py`:

```python
NAME = "Consistency Drift Detection"
DESCRIPTION = (
    "Tracks character traits, knowledge, and emotional state across the full manuscript. "
    "Catches moments where a character forgets an established skill, relationship, or "
    "trauma because the author did."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/agency_audit.py`:

```python
NAME = "Agency Audit"
DESCRIPTION = (
    "Measures whether each significant character drives events or merely reacts to them. "
    "Flags protagonists who are passive passengers in their own story and supporting "
    "characters who exist only to deliver information or create problems."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/distinctiveness_index.py`:

```python
NAME = "Distinctiveness Index"
DESCRIPTION = (
    "Evaluates whether each character occupies a unique narrative role, voice, and "
    "thematic position. Identifies characters who could be merged without story loss "
    "and ensemble gaps where a missing perspective would enrich the narrative."
)
```

Create `backend/agents/blueprints/writers_room/workforce/character_analyst/skills/emotional_arc.py`:

```python
NAME = "Emotional Arc Tracking"
DESCRIPTION = (
    "Maps each character's emotional state scene-by-scene to verify the arc feels "
    "earned. Flags emotional jumps that skip necessary intermediate states — characters "
    "who go from grief to acceptance without anger, or from strangers to lovers without "
    "trust."
)
```

- [ ] **Step 4: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`:

Replace imports:

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.character_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.character_analyst.skills import format_skills
```

Remove inline `cmd_analyze`. Add:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    cmd_analyze = analyze
```

Keep `execute_task` unchanged.

- [ ] **Step 5: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/character_analyst/commands/ backend/agents/blueprints/writers_room/workforce/character_analyst/skills/ backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): character_analyst commands + skills folders"
```

---

## Task 7: dialogue_analyst ��� commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/subtext_density.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/voice_distinctiveness.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/information_control.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/on_the_nose.py`
- Create: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/power_dynamic.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestDialogueAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        skills = bp.skills_description
        assert "Subtext Density Test" in skills
        assert "Voice Distinctiveness Scoring" in skills
        assert "Information Control Analysis" in skills
        assert "On-the-Nose Detection" in skills
        assert "Power Dynamic Mapping" in skills

    def test_skills_format(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands directory and files**

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/commands/__init__.py`:

```python
"""Dialogue Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/commands/analyze.py`:

```python
"""Dialogue Analyst command: analyze dialogue quality and scene construction."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for dialogue quality and scene construction",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 3: Create skills directory and files**

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/__init__.py`:

```python
"""Dialogue Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/subtext_density.py`:

```python
NAME = "Subtext Density Test"
DESCRIPTION = (
    "Measures the ratio of surface meaning to underlying meaning in dialogue exchanges. "
    "Flags lines where characters say exactly what they mean with no subtext as "
    "opportunities for layered writing."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/voice_distinctiveness.py`:

```python
NAME = "Voice Distinctiveness Scoring"
DESCRIPTION = (
    "Covers all dialogue with character names removed and evaluates whether each "
    "speaker remains identifiable from speech patterns alone. Scores on vocabulary, "
    "rhythm, directness, and rhetorical habits."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/information_control.py`:

```python
NAME = "Information Control Analysis"
DESCRIPTION = (
    "Evaluates who knows what in each conversation and whether characters appropriately "
    "protect, reveal, or trade information based on their goals. Catches scenes where "
    "characters share information they have no motivation to share."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/on_the_nose.py`:

```python
NAME = "On-the-Nose Detection"
DESCRIPTION = (
    "Identifies dialogue where characters explicitly state theme, emotion, or backstory "
    "that should be conveyed through behavior, implication, or conflict. Flags lines "
    "that function as author-to-audience communication rather than character-to-character."
)
```

Create `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/power_dynamic.py`:

```python
NAME = "Power Dynamic Mapping"
DESCRIPTION = (
    "Analyzes status shifts within each dialogue exchange — who's winning, who's losing, "
    "where control transfers. Flags conversations with no status movement (static "
    "exchanges that could be cut) and those with unrealistic power shifts."
)
```

- [ ] **Step 4: Modify agent.py**

In `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`:

Replace imports:

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.dialogue_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.dialogue_analyst.skills import format_skills
```

Remove inline `cmd_analyze`. Add:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    cmd_analyze = analyze
```

Keep `_get_voice_constraint` and `execute_task` unchanged.

- [ ] **Step 5: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/dialogue_analyst/commands/ backend/agents/blueprints/writers_room/workforce/dialogue_analyst/skills/ backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): dialogue_analyst commands + skills folders"
```

---

## Task 8: market_analyst — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/comp_title.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/genre_convention.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/audience_profiling.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/commercial_hook.py`
- Create: `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/trend_positioning.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestMarketAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("market_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("market_analyst", "writers_room")
        skills = bp.skills_description
        assert "Comp Title Analysis" in skills
        assert "Genre Convention Mapping" in skills
        assert "Audience Expectation Profiling" in skills
        assert "Commercial Hook Assessment" in skills
        assert "Trend Positioning" in skills

    def test_skills_format(self):
        bp = get_blueprint("market_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands, skills, modify agent.py**

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/commands/__init__.py`:

```python
"""Market Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/commands/analyze.py`:

```python
"""Market Analyst command: analyze market fit and positioning."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for market fit, comps, and positioning",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/__init__.py`:

```python
"""Market Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/comp_title.py`:

```python
NAME = "Comp Title Analysis"
DESCRIPTION = (
    "Identifies the 3-5 most relevant comparable titles by analyzing genre positioning, "
    "audience overlap, tone, and recency. Evaluates what each comp signals to agents, "
    "editors, and readers, and whether the combination positions the manuscript accurately."
)
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/genre_convention.py`:

```python
NAME = "Genre Convention Mapping"
DESCRIPTION = (
    "Catalogs the expected conventions of the target genre and subgenre, then evaluates "
    "which conventions the manuscript fulfills, subverts, or ignores. Flags missing "
    "conventions that readers will expect and subversions that need to be more intentional."
)
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/audience_profiling.py`:

```python
NAME = "Audience Expectation Profiling"
DESCRIPTION = (
    "Builds a reader profile based on genre, tone, and comp titles: what this audience "
    "wants, what they won't tolerate, what delights them. Evaluates the manuscript "
    "against these expectations with specific examples."
)
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/commercial_hook.py`:

```python
NAME = "Commercial Hook Assessment"
DESCRIPTION = (
    "Evaluates the story's elevator pitch potential: can the core premise be communicated "
    "in one compelling sentence? Identifies the unique selling proposition and tests "
    "whether it's distinctive enough to stand out in a crowded market."
)
```

Create `backend/agents/blueprints/writers_room/workforce/market_analyst/skills/trend_positioning.py`:

```python
NAME = "Trend Positioning"
DESCRIPTION = (
    "Analyzes current market trends, emerging themes, and reader appetite shifts in the "
    "target genre. Evaluates whether the manuscript is ahead of, riding, or behind "
    "current trends, and what positioning adjustments could improve timing."
)
```

Modify `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py` — same pattern:

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.market_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.market_analyst.skills import format_skills
```

Remove inline `cmd_analyze`. Add:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    cmd_analyze = analyze
```

- [ ] **Step 3: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/market_analyst/commands/ backend/agents/blueprints/writers_room/workforce/market_analyst/skills/ backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): market_analyst commands + skills folders"
```

---

## Task 9: format_analyst — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/manuscript_standards.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/typographical_consistency.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/scene_break_logic.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/dialogue_punctuation.py`
- Create: `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/whitespace_balance.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestFormatAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("format_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("format_analyst", "writers_room")
        skills = bp.skills_description
        assert "Manuscript Standards Compliance" in skills
        assert "Typographical Consistency Audit" in skills
        assert "Scene Break and Chapter Logic" in skills
        assert "Dialogue Punctuation and Attribution" in skills
        assert "Whitespace and Density Balance" in skills

    def test_skills_format(self):
        bp = get_blueprint("format_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands, skills, modify agent.py**

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/commands/__init__.py`:

```python
"""Format Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/commands/analyze.py`:

```python
"""Format Analyst command: analyze formatting and craft quality."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for formatting conventions and craft quality",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/__init__.py`:

```python
"""Format Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/manuscript_standards.py`:

```python
NAME = "Manuscript Standards Compliance"
DESCRIPTION = (
    "Validates formatting against industry-standard submission guidelines: margins, "
    "font, spacing, headers, page breaks, scene breaks, chapter headings. Catches "
    "formatting that signals amateur status to agents and editors."
)
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/typographical_consistency.py`:

```python
NAME = "Typographical Consistency Audit"
DESCRIPTION = (
    "Checks for consistent handling of em dashes vs en dashes, ellipsis style, "
    "quotation mark usage, number formatting, and italicization rules throughout the "
    "manuscript. Inconsistency suggests carelessness to professional readers."
)
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/scene_break_logic.py`:

```python
NAME = "Scene Break and Chapter Logic"
DESCRIPTION = (
    "Evaluates whether scene breaks and chapter breaks are placed for maximum dramatic "
    "effect. Flags chapters that end on flat notes rather than hooks, and scene breaks "
    "that interrupt momentum rather than compress time."
)
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/dialogue_punctuation.py`:

```python
NAME = "Dialogue Punctuation and Attribution"
DESCRIPTION = (
    "Verifies correct dialogue punctuation, tag usage, and attribution clarity. Catches "
    "creative but incorrect punctuation, missing beats between speakers, and attribution "
    "patterns that slow reading pace."
)
```

Create `backend/agents/blueprints/writers_room/workforce/format_analyst/skills/whitespace_balance.py`:

```python
NAME = "Whitespace and Density Balance"
DESCRIPTION = (
    "Analyzes the visual rhythm of the page: ratio of dialogue to description, paragraph "
    "length variation, and whitespace distribution. Flags pages that are visually "
    "intimidating walls of text or choppy fragments that lack substance."
)
```

Modify `backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py`:

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.format_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.format_analyst.skills import format_skills
```

Remove inline `cmd_analyze`. Add:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    cmd_analyze = analyze
```

- [ ] **Step 3: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/format_analyst/commands/ backend/agents/blueprints/writers_room/workforce/format_analyst/skills/ backend/agents/blueprints/writers_room/workforce/format_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): format_analyst commands + skills folders"
```

---

## Task 10: production_analyst — commands and skills

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/commands/analyze.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/submission_readiness.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/adaptation_potential.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/production_complexity.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/revision_prioritization.py`
- Create: `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/publication_timeline.py`
- Modify: `backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py`
- Modify: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Add tests**

Append to `backend/agents/tests/test_writers_room_skills_commands.py`:

```python
class TestProductionAnalystSkillsAndCommands:
    def test_commands_discovered(self):
        bp = get_blueprint("production_analyst", "writers_room")
        cmds = bp.get_commands()
        names = {c["name"] for c in cmds}
        assert "analyze" in names

    def test_skills_description_contains_technique_names(self):
        bp = get_blueprint("production_analyst", "writers_room")
        skills = bp.skills_description
        assert "Submission Package Readiness" in skills
        assert "Rights and Adaptation Potential" in skills
        assert "Production Complexity Scoring" in skills
        assert "Revision Prioritization Matrix" in skills
        assert "Publication Timeline Planning" in skills

    def test_skills_format(self):
        bp = get_blueprint("production_analyst", "writers_room")
        skills = bp.skills_description
        lines = [l for l in skills.strip().split("\n") if l.strip()]
        assert len(lines) == 5
        for line in lines:
            assert line.startswith("- **")
```

- [ ] **Step 2: Create commands, skills, modify agent.py**

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/commands/__init__.py`:

```python
"""Production Analyst agent commands registry."""

from .analyze import analyze

ALL_COMMANDS = [analyze]
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/commands/analyze.py`:

```python
"""Production Analyst command: analyze production feasibility."""

from agents.blueprints.base import command


@command(
    name="analyze",
    description="Analyze creative material for production/publishing feasibility",
    model="claude-sonnet-4-6",
)
def analyze(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/__init__.py`:

```python
"""Production Analyst agent skills registry."""

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

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/submission_readiness.py`:

```python
NAME = "Submission Package Readiness"
DESCRIPTION = (
    "Evaluates whether the manuscript meets the complete submission requirements: query "
    "letter, synopsis, sample pages, and full manuscript formatting. Identifies gaps and "
    "weak elements that would cause form rejections."
)
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/adaptation_potential.py`:

```python
NAME = "Rights and Adaptation Potential"
DESCRIPTION = (
    "Assesses the story's potential for adaptation across media: film, TV, audio, games, "
    "translation. Identifies elements that translate well across formats and those that "
    "are medium-specific, informing rights strategy."
)
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/production_complexity.py`:

```python
NAME = "Production Complexity Scoring"
DESCRIPTION = (
    "For scripts and screenplays, evaluates practical production requirements: location "
    "count, cast size, VFX needs, period-specific requirements. Flags scenes with high "
    "production cost that could be simplified without story loss."
)
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/revision_prioritization.py`:

```python
NAME = "Revision Prioritization Matrix"
DESCRIPTION = (
    "After all analyst feedback is collected, synthesizes findings into a prioritized "
    "revision plan. Categorizes issues by severity (story-breaking, quality-reducing, "
    "polish-level) and effort (quick fix, moderate rework, structural overhaul)."
)
```

Create `backend/agents/blueprints/writers_room/workforce/production_analyst/skills/publication_timeline.py`:

```python
NAME = "Publication Timeline Planning"
DESCRIPTION = (
    "Maps the realistic path from current manuscript state to publication: remaining "
    "revision rounds, beta reader feedback, professional editing stages, submission "
    "timeline, and market timing considerations."
)
```

Modify `backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py`:

```python
from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.production_analyst.commands import analyze
from agents.blueprints.writers_room.workforce.production_analyst.skills import format_skills
```

Remove inline `cmd_analyze`. Add:

```python
    @property
    def skills_description(self) -> str:
        return format_skills()

    cmd_analyze = analyze
```

- [ ] **Step 3: Run tests and commit**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header -x`
Expected: All tests PASS

```bash
cd /Users/christianpeters/the-agentic-company
git add backend/agents/blueprints/writers_room/workforce/production_analyst/commands/ backend/agents/blueprints/writers_room/workforce/production_analyst/skills/ backend/agents/blueprints/writers_room/workforce/production_analyst/agent.py backend/agents/tests/test_writers_room_skills_commands.py
git commit -m "feat(writers-room): production_analyst commands + skills folders"
```

---

## Task 11: Full regression test

**Files:**
- Test: `backend/agents/tests/test_blueprints.py`
- Test: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Run all writers room tests**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_writers_room_skills_commands.py -v --no-header`
Expected: 30 tests PASS (3 tests × 10 agents)

- [ ] **Step 2: Run full blueprint test suite**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/agents/tests/test_blueprints.py -v --no-header`
Expected: All existing tests PASS — no regressions

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/christianpeters/the-agentic-company && python -m pytest backend/ -v --no-header -x`
Expected: All tests PASS

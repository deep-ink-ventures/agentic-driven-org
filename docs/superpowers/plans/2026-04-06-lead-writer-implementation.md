# Lead Writer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a Lead Writer workforce agent and refactor the writers room pipeline from 8 stages to 4, with three persistent documents per feedback round.

**Architecture:** New `lead_writer` workforce blueprint with 5 commands. Rewrite `WritersRoomLeaderBlueprint` state machine, stages, matrices, and task specs. Add 3 new `DocType` choices and a document creation helper with archive-and-link versioning. Base class (`base.py`) untouched.

**Tech Stack:** Django, Python, Celery (existing stack)

**Spec:** `docs/superpowers/specs/2026-04-06-lead-writer-agent-design.md`

---

### Task 1: Add new DocType choices + migration

**Files:**
- Modify: `backend/projects/models/document.py:7-18` (DocType choices)
- Create: `backend/projects/migrations/0020_document_stage_doc_types.py`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/agents/tests/test_writers_room_lead_writer.py
"""Tests for Lead Writer agent and writers room pipeline refactor."""

from projects.models import Document


class TestStageDocTypes:
    def test_stage_deliverable_doc_type_exists(self):
        assert "stage_deliverable" in [c[0] for c in Document.DocType.choices]

    def test_stage_research_doc_type_exists(self):
        assert "stage_research" in [c[0] for c in Document.DocType.choices]

    def test_stage_critique_doc_type_exists(self):
        assert "stage_critique" in [c[0] for c in Document.DocType.choices]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStageDocTypes -v`
Expected: FAIL — `stage_deliverable` not in choices

- [ ] **Step 3: Add the three new DocType choices**

In `backend/projects/models/document.py`, add to the `DocType` class after `MONTHLY_ARCHIVE`:

```python
STAGE_DELIVERABLE = "stage_deliverable", "Stage Deliverable"
STAGE_RESEARCH = "stage_research", "Stage Research & Notes"
STAGE_CRITIQUE = "stage_critique", "Stage Critique"
```

- [ ] **Step 4: Generate and verify migration**

Run: `cd backend && python manage.py makemigrations projects -n document_stage_doc_types`
Expected: Migration created altering `doc_type` field choices

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStageDocTypes -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/projects/models/document.py backend/projects/migrations/0020_document_stage_doc_types.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): add stage_deliverable, stage_research, stage_critique DocTypes"
```

---

### Task 2: Create the Lead Writer blueprint + 5 commands

**Files:**
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/__init__.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_pitch.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_expose.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_treatment.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_concept.py`
- Create: `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_first_draft.py`
- Modify: `backend/agents/blueprints/__init__.py:74-86` (registry)
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
from agents.blueprints import get_blueprint


class TestLeadWriterBlueprint:
    def test_blueprint_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        assert bp is not None
        assert bp.name == "Lead Writer"
        assert bp.slug == "lead_writer"

    def test_write_pitch_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_pitch" in cmds

    def test_write_expose_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_expose" in cmds

    def test_write_treatment_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_treatment" in cmds

    def test_write_concept_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_concept" in cmds

    def test_write_first_draft_command_registered(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"] for c in bp.get_commands()}
        assert "write_first_draft" in cmds

    def test_all_commands_use_sonnet(self):
        bp = get_blueprint("lead_writer", "writers_room")
        cmds = {c["name"]: c for c in bp.get_commands()}
        for name in ["write_pitch", "write_expose", "write_treatment", "write_concept", "write_first_draft"]:
            assert cmds[name]["model"] == "claude-sonnet-4-6", f"{name} should use claude-sonnet-4-6"

    def test_system_prompt_contains_key_principles(self):
        bp = get_blueprint("lead_writer", "writers_room")
        prompt = bp.system_prompt
        assert "synthesize" in prompt.lower() or "synthesis" in prompt.lower()
        assert "do not invent" in prompt.lower() or "not alter" in prompt.lower()

    def test_skills_defined(self):
        bp = get_blueprint("lead_writer", "writers_room")
        assert len(bp.skills) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestLeadWriterBlueprint -v`
Expected: FAIL — blueprint not found

- [ ] **Step 3: Create the 5 command files**

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/__init__.py`:

```python
"""Lead Writer commands registry."""

from .write_concept import write_concept
from .write_expose import write_expose
from .write_first_draft import write_first_draft
from .write_pitch import write_pitch
from .write_treatment import write_treatment

ALL_COMMANDS = [write_pitch, write_expose, write_treatment, write_concept, write_first_draft]
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_pitch.py`:

```python
"""Lead Writer command: write the pitch document."""

from agents.blueprints.base import command


@command(
    name="write_pitch",
    description=(
        "Synthesize creative agents' fragments into a 2-3 page pitch document. "
        "Logline, world, characters, central conflict, tonality. Proves the story "
        "is worth telling. For series: conveys the story engine. For standalone: "
        "implies the complete arc."
    ),
    model="claude-sonnet-4-6",
    max_tokens=8192,
)
def write_pitch(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_expose.py`:

```python
"""Lead Writer command: write the expose document."""

from agents.blueprints.base import command


@command(
    name="write_expose",
    description=(
        "Synthesize creative agents' fragments into a 5-10 page expose. "
        "Three-movement architecture with marked turning points, character arcs "
        "showing transformation, sustained tonal throughline. Must reveal complete "
        "story including resolution."
    ),
    model="claude-sonnet-4-6",
    max_tokens=16384,
)
def write_expose(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_treatment.py`:

```python
"""Lead Writer command: write the treatment (standalone only)."""

from agents.blueprints.base import command


@command(
    name="write_treatment",
    description=(
        "Synthesize creative agents' fragments into a 20-40+ page treatment. "
        "Present tense, third person, scene by scene. Every scene turns a value. "
        "Subtext over dialogue. Progressive complications build relentlessly. "
        "Standalone works only (movie, play, book)."
    ),
    model="claude-sonnet-4-6",
    max_tokens=32768,
)
def write_treatment(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_concept.py`:

```python
"""Lead Writer command: write the series concept/bible."""

from agents.blueprints.base import command


@command(
    name="write_concept",
    description=(
        "Synthesize creative agents' fragments into a 15-25 page series concept/bible. "
        "Story engine, world rules, character ensemble as relationship web, saga arc, "
        "season one breakdown, episode overviews, future season sketches. "
        "Series works only (TV, film series, audio drama series)."
    ),
    model="claude-sonnet-4-6",
    max_tokens=32768,
)
def write_concept(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/commands/write_first_draft.py`:

```python
"""Lead Writer command: write the first draft (standalone only)."""

from agents.blueprints.base import command


@command(
    name="write_first_draft",
    description=(
        "Synthesize creative agents' fragments and the treatment into a full first draft. "
        "The actual screenplay, manuscript, or play script. Must be complete, not perfect. "
        "Medium-specific formatting. Standalone works only."
    ),
    model="claude-sonnet-4-6",
    max_tokens=65536,
)
def write_first_draft(self, agent, **kwargs):
    pass  # Dispatched via execute_task
```

- [ ] **Step 4: Create the Lead Writer blueprint**

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/__init__.py`:

```python
from .agent import LeadWriterBlueprint

__all__ = ["LeadWriterBlueprint"]
```

Create `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.lead_writer.commands import (
    write_concept,
    write_expose,
    write_first_draft,
    write_pitch,
    write_treatment,
)

logger = logging.getLogger(__name__)

# ── Stage-specific craft directives ──────────────────────────────────────────

CRAFT_DIRECTIVES = {
    "write_pitch": (
        "You are writing the PITCH — 2-3 pages that prove this story is worth telling.\n\n"
        "## Craft Directives\n"
        "- Open with the logline: protagonist defined by contradiction (not name), "
        "inciting incident, central conflict, stakes — one sentence, max two, under 50 words\n"
        "- Establish the protagonist through the gap between who they appear to be and who they are "
        "(want vs need)\n"
        "- Ground the world in one evocative, specific detail that also conveys tone\n"
        "- Present the central conflict as an ENGINE — an inexhaustible dynamic, not a single event\n"
        "- The prose tone of this pitch must ENACT the story's tone. A comedy pitch is amusing. "
        "A horror pitch induces unease. A tragedy carries gravity. Never describe tone — demonstrate it.\n"
        "- End with stakes escalation — what the protagonist loses if they fail, and why that loss "
        "is devastating\n"
        "- For series: convey the story engine — the renewable conflict mechanism that generates "
        "episodes, not just the pilot story\n"
        "- For standalone: imply the complete arc — beginning, middle, end — without revealing "
        "the resolution\n\n"
        "## Pitfalls to Avoid\n"
        "- Abstract thematic language ('a story about love and loss') instead of concrete specifics\n"
        "- Name-dropping characters before the reader has reason to care — use sharp descriptors first\n"
        "- Including subplots — the pitch has room for the A-story only\n"
        "- Tone mismatch — flat corporate prose for a wild, anarchic story\n"
        "- Describing the ending in full — pitch documents should leave the reader wanting resolution\n"
    ),
    "write_expose": (
        "You are writing the EXPOSE — 5-10 pages providing a bird's-eye view of the complete story.\n\n"
        "## Craft Directives\n"
        "- Restate the logline and premise with more specificity than the pitch\n"
        "- Introduce each major character through their ARC: starting situation, want, need, "
        "weakness, where they end up. Show transformation, not trait catalogs.\n"
        "- Present three-movement architecture: Setup (inciting incident, entry into conflict), "
        "Confrontation (rising complications, midpoint shift, tightening antagonism), "
        "Resolution (crisis, climax, self-revelation, new equilibrium)\n"
        "- Mark the five turning points explicitly: Inciting Incident, Act I break, Midpoint, "
        "Act II break (All Is Lost), Climax\n"
        "- Sustain tonal throughline across ALL pages — most exposes fail by starting with voice "
        "and devolving into dry summary by page 4\n"
        "- The thematic argument must be visible in the arc of events, not stated didactically\n"
        "- Unlike the pitch, the expose MUST reveal the complete story including resolution — "
        "decision-makers need to see you can land the plane\n"
        "- For series: cover the first season arc in detail, sketch the saga arc, demonstrate "
        "the story engine's renewability\n"
        "- For standalone: cover the complete story arc\n\n"
        "## Pitfalls to Avoid\n"
        "- Withholding the ending out of misplaced suspense\n"
        "- Subplot overload — room for A-story and one B-story at most\n"
        "- Character as catalog — listing traits instead of showing how traits create conflict\n"
        "- Losing chronological clarity\n"
        "- Underdeveloped antagonism\n"
    ),
    "write_treatment": (
        "You are writing the TREATMENT — 20-40+ pages. The full story told in prose. "
        "Standalone works only (movie, play, book).\n\n"
        "## Craft Directives\n"
        "- Write in present tense, third person, scene by scene\n"
        "- Every scene must TURN A VALUE — something changes from positive to negative or vice versa. "
        "If nothing turns, the scene does not belong.\n"
        "- Convey character SUBTEXT, not dialogue. Describe what characters talk about, their "
        "emotional undercurrents, the gap between what they say and what they mean. Never write "
        "actual dialogue lines.\n"
        "- Progressive complications must escalate relentlessly — each obstacle worse than the last, "
        "each failure raising the stakes. The middle is where treatments die; do not let it sag.\n"
        "- The prose must carry the voice and tone of the intended work. A treatment for a comedy "
        "reads with wit. A treatment for horror reads with dread.\n"
        "- World and atmosphere as a force that shapes the story, not wallpaper. Sensory details "
        "that establish mood.\n"
        "- Full character arcs traceable: weakness/need -> desire -> opponent -> plan -> battle -> "
        "self-revelation -> new equilibrium\n"
        "- Give the climax and resolution proportional space — rushed endings are the most "
        "expensive mistake\n\n"
        "## Pitfalls to Avoid\n"
        "- Writing dialogue — the treatment is not a scriptment\n"
        "- Scene-by-scene monotony ('Then... Next... Then...')\n"
        "- Neglecting Act II — the progressive complications must build\n"
        "- Including camera directions or technical language\n"
        "- Forgetting tone — letting the prose go flat\n"
    ),
    "write_concept": (
        "You are writing the SERIES CONCEPT / BIBLE — 15-25 pages. The master reference "
        "document for a continuing narrative. Series works only.\n\n"
        "## Craft Directives\n"
        "- Open with creator's statement — why this story needs to exist (from the project goal)\n"
        "- Define the STORY ENGINE first and prominently — the renewable mechanism that generates "
        "conflict episode after episode, season after season. If you cannot articulate it in one "
        "sentence, the concept is not ready. The engine is a SITUATION that naturally produces "
        "stories, not a single plot.\n"
        "- Tonal pillars: 3-5 specific adjectives that define the emotional register, enacted in "
        "the prose, not just listed\n"
        "- World rules: what the audience needs to know about this world that differs from our own — "
        "social codes, hierarchies, power structures, unwritten rules. For speculative fiction: "
        "magic systems, technology, politics.\n"
        "- Character ensemble as a WEB of relationships — alliances, rivalries, dependencies, "
        "romantic tensions. Not isolated profiles. Each character embodies a different approach to "
        "the series' thematic question. Backstory presented as unexploded ordnance — past events "
        "that create present-tense conflict.\n"
        "- Saga arc: where does the protagonist begin and end across the entire run? Series-level "
        "inciting incident, midpoint, climax. How does the thematic argument deepen across seasons?\n"
        "- Season one breakdown: season-level inciting incident, midpoint, climax. How A-story and "
        "B-story interweave. Character arcs for the season.\n"
        "- Episode overviews (1-3 paragraphs each): must show VARIETY (different facets, character "
        "combinations, tonal registers) AND THROUGHLINE (season arc progresses in every episode). "
        "Each overview makes the engine visible.\n"
        "- Future seasons: 1-2 paragraphs each showing where seasons 2, 3+ take characters. Prove "
        "the series has an intended destination, not endless repetition.\n\n"
        "## Pitfalls to Avoid\n"
        "- No clear engine — the single most common failure\n"
        "- Character catalogs without dynamics\n"
        "- Vague thematic statements ('explores identity')\n"
        "- Episode overviews that are all the same shape\n"
        "- Neglecting sustainability — proving Season 1 is necessary but not sufficient\n"
        "- Over-building world at the expense of character and story\n"
    ),
    "write_first_draft": (
        "You are writing the FIRST DRAFT — the actual screenplay, manuscript, or play script. "
        "Standalone works only.\n\n"
        "## Craft Directives\n"
        "- The treatment told us ABOUT the story. The first draft IS the story. Prose becomes "
        "dialogue. Summary becomes dramatized scene. Subtext must now emerge from action and "
        "speech, not author narration.\n"
        "- The first draft must be COMPLETE, not perfect. Get it down. Every scene from the "
        "treatment rendered in the target medium's format.\n"
        "- For SCREENPLAY: scene headings (INT./EXT., location, time). Action lines: present "
        "tense, visual, minimal — only what the camera sees and microphone hears. Dialogue with "
        "character name centered. Think in images. Show, don't tell.\n"
        "- For PROSE MANUSCRIPT: establish and maintain point of view. Narrative voice — rhythm, "
        "vocabulary, sensibility — must be present even if imperfect. Deliberate scene vs summary "
        "choices. Use the medium's superpower: interior life, thoughts, memory, sensory experience.\n"
        "- For STAGE PLAY: dialogue-dominant. Stage directions minimal and essential — do not "
        "choreograph actors. Embrace theatrical constraints (limited locations, no quick cuts) as "
        "creative opportunities. Read every line aloud — theater is heard.\n"
        "- UNIVERSAL: every scene dramatizes conflict. Characters speak in distinct voices — cover "
        "the name and you should still know who's talking. Exposition woven into conflict, never "
        "dumped. Enter scenes late, leave early.\n\n"
        "## Pitfalls to Avoid\n"
        "- On-the-nose dialogue — characters saying exactly what they mean\n"
        "- Exposition dumps — characters explaining plot to each other\n"
        "- Identical character voices — everyone sounds the same\n"
        "- Overwriting action/stage directions\n"
        "- Deviating from the treatment's structure\n"
    ),
}

# ── Integration mandate (appended to all craft directives) ───────────────────

INTEGRATION_MANDATE = (
    "\n## Integration Mandate\n"
    "Build EXCLUSIVELY from the creative agents' fragments in the department documents and "
    "sibling task reports. Use the story_architect's structure, the character_designer's ensemble, "
    "the dialog_writer's voice work, and the story_researcher's research. Do NOT invent new "
    "characters, conflicts, world elements, or plot points. Your job is synthesis and prose craft, "
    "not ideation. If you find gaps, flag them — do not fill them with your own inventions.\n\n"
    "FIDELITY CHECK (before submitting): Re-read the creator's pitch in <project_goal>. "
    "Does your output preserve EVERY specific element they provided? If you introduced anything "
    "the creator did NOT mention, delete it.\n"
)

ANTI_AI_RULES = (
    "\nANTI-AI WRITING RULES (MANDATORY):\n"
    "Your writing must sound human-authored. NEVER use:\n"
    '- "A testament to", "it\'s worth noting", "delve into", "nuanced", '
    '"tapestry", "multifaceted"\n'
    '- "In a world where...", "little did they know", '
    '"sent shivers down their spine"\n'
    '- "The silence was deafening", "time stood still", '
    '"a rollercoaster of emotions"\n'
    "- Perfect parallel sentence structures (if you write three sentences with "
    "the same rhythm, break the pattern)\n"
    '- On-the-nose emotional statements ("I feel sad about what happened")\n'
    "- Perfectly balanced pros-and-cons reasoning in dialogue\n\n"
    "INSTEAD:\n"
    "- Write messy, specific, surprising details over clean generic ones\n"
    "- Vary sentence length dramatically — a 3-word sentence after a 30-word one\n"
    "- Use the voice profile from the Story Researcher as your north star\n"
)


class LeadWriterBlueprint(WorkforceBlueprint):
    name = "Lead Writer"
    slug = "lead_writer"
    description = (
        "Synthesizes creative team output into cohesive stage deliverables — "
        "pitches, exposes, treatments, series concepts, and first drafts"
    )
    tags = ["creative", "writers-room", "synthesis", "prose", "lead-writer"]
    skills = [
        {
            "name": "Narrative Synthesis",
            "description": (
                "Weaves fragments from multiple creative agents into a single cohesive "
                "document with consistent voice, narrative flow, and structural integrity."
            ),
        },
        {
            "name": "Tonal Enactment",
            "description": (
                "Writes prose whose tone DEMONSTRATES the story's genre and mood rather "
                "than describing it. A comedy pitch is amusing; a horror treatment induces dread."
            ),
        },
        {
            "name": "Structural Architecture",
            "description": (
                "Commands three-movement architecture, turning points, progressive complications, "
                "and scene-level value changes across any format and length."
            ),
        },
        {
            "name": "Format Adaptation",
            "description": (
                "Adapts output to any medium — screenplay, novel, theatre, audio drama, series — "
                "respecting each format's conventions and constraints."
            ),
        },
        {
            "name": "Integration Without Invention",
            "description": (
                "Synthesizes the work of story researchers, architects, character designers, "
                "and dialog writers without altering their creative decisions. Adds connective "
                "tissue and prose craft, not new ideas."
            ),
        },
    ]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Lead Writer in a professional writers room. You are the prose "
            "craftsman who synthesizes the creative team's work into the actual deliverable "
            "document — the pitch, expose, treatment, concept, or draft that the project "
            "exists to produce.\n\n"
            "## Your Role\n"
            "You do NOT invent. You INTEGRATE. The creative agents generate the ideas:\n"
            "- Story Researcher provides market context, world-building details, real-world grounding\n"
            "- Story Architect provides structural backbone — beats, acts, turning points, saga arcs\n"
            "- Character Designer provides the ensemble — psychology, relationships, arcs, voices\n"
            "- Dialog Writer provides tonal sensibility, voice fingerprinting, dialogue craft\n\n"
            "Your job is to weave all of this into ONE COHESIVE DOCUMENT that reads as a single "
            "unified vision, not a collage of committee reports. You add connective tissue, "
            "consistent voice, and narrative flow. You do NOT alter the characters they created, "
            "the structure they proposed, or the world they built. If you find gaps or "
            "contradictions in their work, flag them — do not silently fill them with your own "
            "inventions.\n\n"
            "## Craft Principles\n"
            "- Every word earns its place. Zero abstraction — specific, concrete, vivid.\n"
            "- Tone is demonstrated, not described. The document's prose enacts the story's genre.\n"
            "- Characters are defined by contradiction and action, not demographic attributes.\n"
            "- Narrative momentum — every paragraph earns the next.\n"
            "- The reader must feel the story's unique personality. If your document could describe "
            "a hundred different stories, it describes none.\n\n"
            "## Fidelity to the Creator's Vision\n"
            "The project goal contains the creator's specific intent. Honor every character, "
            "conflict, arc, and reference they specified. Add depth and texture — never "
            "subtract specificity or replace their vision with generic alternatives.\n\n"
            "## Anti-Derivative Rule\n"
            "Referenced shows/books are quality benchmarks, not templates. Write something "
            "original that stands alongside them.\n\n"
            "CRITICAL: Your ENTIRE output MUST be written in the language specified by the "
            'locale setting. If locale is "de", write everything in German. If "en", write '
            'in English. This is non-negotiable.\n'
            + ANTI_AI_RULES
        )

    # ── Register commands ────────────────────────────────────────────────
    write_pitch = write_pitch
    write_expose = write_expose
    write_treatment = write_treatment
    write_concept = write_concept
    write_first_draft = write_first_draft

    def _get_voice_constraint(self, agent: Agent) -> str:
        """Fetch Voice DNA and return it as an inviolable constraint block."""
        try:
            from projects.models import Document

            voice_doc = (
                Document.objects.filter(
                    department=agent.department,
                    doc_type="voice_profile",
                    is_archived=False,
                )
                .order_by("-created_at")
                .first()
            )
            if voice_doc and voice_doc.content:
                return (
                    "\n\n## VOICE DNA -- INVIOLABLE CONSTRAINT\n"
                    "The following voice profile was extracted from the original author's material.\n"
                    "You MUST write in this voice. This is not a suggestion -- it is law.\n\n"
                    f"{voice_doc.content}\n"
                )
        except Exception:
            logger.exception("Failed to fetch voice profile")
        return ""

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Route to the appropriate craft directive based on command name."""
        command_name = task.command_name or "write_pitch"
        craft = CRAFT_DIRECTIVES.get(command_name, CRAFT_DIRECTIVES["write_pitch"])
        return self._execute_write(agent, task, craft)

    def _execute_write(self, agent: Agent, task: AgentTask, craft_directive: str) -> str:
        """Execute a writing task with the given craft directive."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            f"{craft_directive}"
            f"{INTEGRATION_MANDATE}"
            f"\nYour output must be in {locale}. This is non-negotiable."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, task.command_name or "write_pitch"),
            max_tokens=self._get_max_tokens(task.command_name),
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _get_max_tokens(self, command_name: str | None) -> int:
        """Return max_tokens based on expected output length per stage."""
        return {
            "write_pitch": 8192,
            "write_expose": 16384,
            "write_treatment": 32768,
            "write_concept": 32768,
            "write_first_draft": 65536,
        }.get(command_name or "write_pitch", 16384)
```

- [ ] **Step 5: Register the Lead Writer in the blueprint registry**

In `backend/agents/blueprints/__init__.py`, add `lead_writer` to the `_writers_room_imports` dict (after the `creative_reviewer` line):

```python
    "lead_writer": ("agents.blueprints.writers_room.workforce.lead_writer", "LeadWriterBlueprint"),
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestLeadWriterBlueprint -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/agents/blueprints/writers_room/workforce/lead_writer/ backend/agents/blueprints/__init__.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): add Lead Writer blueprint with 5 stage-specific commands"
```

---

### Task 3: Rewrite stages, matrices, and format detection

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:25-99` (STAGES, CREATIVE_MATRIX, FEEDBACK_MATRIX, FLAG_ROUTING)
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py:1094-1228` (_run_entry_detection, ENTRY_DETECTION_PROMPT)
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
class TestNewStagesAndMatrices:
    def test_stages_are_four(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        assert STAGES == ["pitch", "expose", "treatment", "first_draft"]

    def test_creative_matrix_all_stages(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        for stage in ["pitch", "expose", "treatment", "concept", "first_draft"]:
            assert stage in CREATIVE_MATRIX, f"Missing creative matrix for {stage}"

    def test_creative_matrix_excludes_lead_writer(self):
        from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX

        for stage, agents in CREATIVE_MATRIX.items():
            assert "lead_writer" not in agents, f"lead_writer should not be in CREATIVE_MATRIX[{stage}]"

    def test_feedback_matrix_all_stages(self):
        from agents.blueprints.writers_room.leader.agent import FEEDBACK_MATRIX

        for stage in ["pitch", "expose", "treatment", "concept", "first_draft"]:
            assert stage in FEEDBACK_MATRIX, f"Missing feedback matrix for {stage}"

    def test_flag_routing_removed(self):
        """FLAG_ROUTING should no longer exist — replaced by whole-team revision."""
        import agents.blueprints.writers_room.leader.agent as mod

        assert not hasattr(mod, "FLAG_ROUTING"), "FLAG_ROUTING should be removed"

    def test_old_stages_removed(self):
        from agents.blueprints.writers_room.leader.agent import STAGES

        for old in ["ideation", "concept", "logline", "step_outline", "revised_draft"]:
            assert old not in STAGES, f"Old stage '{old}' should not be in STAGES"


class TestFormatDetection:
    def test_format_detection_prompt_exists(self):
        from agents.blueprints.writers_room.leader.agent import FORMAT_DETECTION_PROMPT

        assert "format_type" in FORMAT_DETECTION_PROMPT
        assert "terminal_stage" in FORMAT_DETECTION_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestNewStagesAndMatrices -v`
Expected: FAIL — STAGES still has 8 entries

- [ ] **Step 3: Replace STAGES, matrices, and remove FLAG_ROUTING**

In `backend/agents/blueprints/writers_room/leader/agent.py`, replace the constants (lines 25-99):

```python
# ── Stage pipeline ──────────────────────────────────────────────────────────

STAGES = ["pitch", "expose", "treatment", "first_draft"]

# ── Creative matrix: which CREATIVE agents write fragments at which stage ───
# Note: lead_writer is NOT here — dispatched separately via state machine.
# "concept" is a virtual stage (series path) that uses the same pipeline position as "treatment".

CREATIVE_MATRIX: dict[str, list[str]] = {
    "pitch": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "expose": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "treatment": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "concept": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "first_draft": ["story_architect", "character_designer", "dialog_writer"],
}

# ── Feedback matrix: which FEEDBACK agents analyze at which stage ───────────

FEEDBACK_MATRIX: dict[str, list[tuple[str, str]]] = {
    "pitch": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("character_analyst", "lite"),
    ],
    "expose": [
        ("market_analyst", "full"),
        ("structure_analyst", "full"),
        ("character_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "treatment": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("production_analyst", "full"),
        ("market_analyst", "lite"),
    ],
    "concept": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("market_analyst", "full"),
        ("production_analyst", "full"),
    ],
    "first_draft": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("format_analyst", "full"),
        ("production_analyst", "lite"),
        ("market_analyst", "lite"),
    ],
}
```

Remove the `FLAG_ROUTING` dict entirely (lines 93-99 in the original).

- [ ] **Step 4: Replace entry detection with format detection**

Replace `ENTRY_DETECTION_PROMPT` and `_run_entry_detection` with:

```python
FORMAT_DETECTION_PROMPT = """\
You are the showrunner of a professional writers room. Analyze the sprint text and project input to determine:
1. Whether this is a standalone piece or a series
2. What the terminal stage should be

## Sprint Text
{sprint_text}

## Project Goal
{goal}

## Source Material
{sources_summary}

## Rules
- Determine format_type from the sprint text. The user says what they want: "Write a series concept", "Schreib mir ein Treatment", "I want a screenplay", etc. Understand ANY language.
- standalone = movie, play, book, Hörspiel (single piece), short story, etc.
- series = TV series, Filmreihe, Serie, Hörspielserie, web series, etc.
- terminal_stage depends on what the user asked for:
  - If they want a pitch/logline only → "pitch"
  - If they want an expose → "expose"
  - If they want a treatment (standalone) → "treatment"
  - If they want a series concept/bible/Serienkonzept → "concept"
  - If they want a screenplay/manuscript/first draft → "first_draft"
  - If unclear, default to the natural terminal: "concept" for series, "treatment" for standalone
- entry_stage: where to START the pipeline based on existing material:
  - If no existing material → "pitch"
  - If a pitch/logline already exists → "expose"
  - If an expose exists → "treatment" (or "concept" for series)
  - If a treatment/concept exists → "first_draft"

Respond with JSON only:
{{
    "format_type": "standalone|series",
    "terminal_stage": "pitch|expose|treatment|concept|first_draft",
    "entry_stage": "pitch|expose|treatment|first_draft",
    "reasoning": "Brief explanation"
}}"""


def _run_format_detection(agent, sprint_text: str) -> dict:
    """
    Classify the sprint to determine format type, terminal stage, and entry point.
    Returns dict with format_type, terminal_stage, entry_stage.
    """
    project = agent.department.project
    goal = project.goal or "No goal specified"

    # Gather source summaries
    sources = project.sources.all()
    sources_summary = ""
    for s in sources:
        text = s.extracted_text or s.raw_content or ""
        if not text:
            continue
        name = s.original_filename or s.url or "Text input"
        sources_summary += f"\n### {name} ({s.source_type})\n{text[:2000]}\n"

    if not sources_summary:
        sources_summary = "No source material uploaded."

    prompt = FORMAT_DETECTION_PROMPT.format(
        sprint_text=sprint_text,
        goal=goal,
        sources_summary=sources_summary,
    )

    response, _usage = call_claude(
        system_prompt="You are a project classification system. Respond with JSON only.",
        user_message=prompt,
        model="claude-sonnet-4-6",
        max_tokens=1024,
    )

    data = parse_json_response(response)
    if not data or "format_type" not in data:
        logger.warning("Format detection failed to parse, defaulting: %s", response[:200])
        return {"format_type": "standalone", "terminal_stage": "treatment", "entry_stage": "pitch"}

    result = {
        "format_type": data.get("format_type", "standalone"),
        "terminal_stage": data.get("terminal_stage", "treatment"),
        "entry_stage": data.get("entry_stage", "pitch"),
        "reasoning": data.get("reasoning", ""),
    }

    # Validate terminal_stage
    valid_terminals = {"pitch", "expose", "treatment", "concept", "first_draft"}
    if result["terminal_stage"] not in valid_terminals:
        result["terminal_stage"] = "concept" if result["format_type"] == "series" else "treatment"

    # Validate entry_stage
    if result["entry_stage"] not in [s for s in STAGES]:
        result["entry_stage"] = "pitch"

    # Store in internal_state
    internal_state = agent.internal_state or {}
    internal_state["format_type"] = result["format_type"]
    internal_state["terminal_stage"] = result["terminal_stage"]
    internal_state["detection_reasoning"] = result["reasoning"]
    internal_state["entry_detected"] = True
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    logger.info(
        "Writers Room format detection: format=%s terminal=%s entry=%s reason=%s",
        result["format_type"],
        result["terminal_stage"],
        result["entry_stage"],
        result["reasoning"][:100],
    )

    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestNewStagesAndMatrices agents/tests/test_writers_room_lead_writer.py::TestFormatDetection -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py
git commit -m "feat(writers-room): replace 8-stage pipeline with 4 stages + format detection"
```

---

### Task 4: Rewrite the state machine in generate_task_proposal()

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py` — `generate_task_proposal()`, `_propose_creative_tasks()`, `_propose_feedback_tasks()`, `_propose_review_task()`, `_propose_fix_task()`, new `_propose_lead_writer_task()`, new `_create_stage_document()`
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`

This is the largest task. The state machine, document creation helper, and all proposal methods need rewriting.

- [ ] **Step 1: Write the failing tests for the state machine**

Append to `backend/agents/tests/test_writers_room_lead_writer.py`:

```python
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def leader_blueprint():
    from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint
    return WritersRoomLeaderBlueprint()


@pytest.fixture
def mock_leader_agent(db):
    """Create a minimal leader agent with department and project for state machine tests."""
    from projects.models import Project, Department, Sprint
    from agents.models import Agent

    project = Project.objects.create(name="Test Project", goal="A test story about brothers")
    dept = Department.objects.create(
        project=project,
        name="Writers Room",
        department_type="writers_room",
    )
    leader = Agent.objects.create(
        department=dept,
        name="Showrunner",
        agent_type="leader",
        is_leader=True,
        status="active",
        internal_state={},
    )
    # Create workforce agents
    for agent_type in [
        "story_researcher", "story_architect", "character_designer",
        "dialog_writer", "lead_writer", "market_analyst", "structure_analyst",
        "character_analyst", "creative_reviewer",
    ]:
        Agent.objects.create(
            department=dept,
            name=agent_type.replace("_", " ").title(),
            agent_type=agent_type,
            is_leader=False,
            status="active",
        )
    sprint = Sprint.objects.create(
        text="Write a series concept for a banking scandal drama",
        status=Sprint.Status.RUNNING,
    )
    sprint.departments.add(dept)
    return leader


class TestStateMachine:
    @pytest.mark.django_db
    @patch("agents.blueprints.writers_room.leader.agent._run_format_detection")
    def test_not_started_dispatches_creative_agents(self, mock_detect, leader_blueprint, mock_leader_agent):
        mock_detect.return_value = {
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_stage": "pitch",
        }
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        assert "tasks" in proposal
        # Should dispatch creative agents, not lead_writer
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "lead_writer" not in agent_types
        assert "story_researcher" in agent_types or "story_architect" in agent_types

    @pytest.mark.django_db
    def test_creative_writing_done_dispatches_lead_writer(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "creative_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])

        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert agent_types == ["lead_writer"]

    @pytest.mark.django_db
    def test_lead_writing_done_dispatches_feedback(self, leader_blueprint, mock_leader_agent):
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])

        with patch.object(leader_blueprint, "_create_stage_documents"):
            proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "lead_writer" not in agent_types
        # Should be feedback agents
        assert any(a in agent_types for a in ["market_analyst", "structure_analyst", "character_analyst"])


class TestDocumentCreation:
    @pytest.mark.django_db
    def test_create_stage_documents_v1_no_archive(self, leader_blueprint, mock_leader_agent):
        """First round creates documents without archiving anything."""
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable", "stage_research"],
            contents={"stage_deliverable": "The pitch", "stage_research": "Research notes"},
        )
        docs = Document.objects.filter(
            department=mock_leader_agent.department,
            is_archived=False,
        )
        assert docs.filter(doc_type="stage_deliverable").count() == 1
        assert docs.filter(doc_type="stage_research").count() == 1

    @pytest.mark.django_db
    def test_create_stage_documents_v2_archives_v1(self, leader_blueprint, mock_leader_agent):
        """Second round archives v1 and links to v2."""
        # Create v1
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=1,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Pitch v1"},
        )
        # Create v2
        leader_blueprint._create_stage_documents(
            agent=mock_leader_agent,
            stage="pitch",
            version=2,
            doc_types=["stage_deliverable"],
            contents={"stage_deliverable": "Pitch v2"},
        )
        all_docs = Document.objects.filter(
            department=mock_leader_agent.department,
            doc_type="stage_deliverable",
        )
        assert all_docs.count() == 2
        archived = all_docs.filter(is_archived=True).first()
        active = all_docs.filter(is_archived=False).first()
        assert archived is not None
        assert active is not None
        assert archived.consolidated_into == active
        assert "v1" in archived.title
        assert "v2" in active.title
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStateMachine -v`
Expected: FAIL — state machine doesn't handle new states yet

- [ ] **Step 3: Implement `_create_stage_documents` helper**

Add this method to `WritersRoomLeaderBlueprint`:

```python
def _create_stage_documents(
    self, agent, stage: str, version: int, doc_types: list[str], contents: dict[str, str],
    sprint=None,
):
    """Create stage documents, archiving prior versions if they exist.

    Args:
        agent: The leader agent.
        stage: Stage name (e.g. "pitch").
        version: Version number (1, 2, ...).
        doc_types: List of doc_type strings to create.
        contents: Dict mapping doc_type to content string.
        sprint: Optional sprint to link documents to.
    """
    stage_display = stage.replace("_", " ").title()
    label_map = {
        "stage_deliverable": "Deliverable",
        "stage_research": "Research & Notes",
        "stage_critique": "Critique",
    }

    for doc_type in doc_types:
        content = contents.get(doc_type, "")
        if not content:
            continue

        label = label_map.get(doc_type, doc_type)
        title = f"{stage_display} v{version} — {label}"

        # Archive existing non-archived doc of same type and stage
        existing = Document.objects.filter(
            department=agent.department,
            doc_type=doc_type,
            is_archived=False,
            title__startswith=f"{stage_display} v",
        ).first()

        new_doc = Document.objects.create(
            department=agent.department,
            doc_type=doc_type,
            title=title,
            content=content,
            sprint=sprint,
        )

        if existing:
            existing.is_archived = True
            existing.consolidated_into = new_doc
            existing.save(update_fields=["is_archived", "consolidated_into", "updated_at"])
```

- [ ] **Step 4: Implement `_propose_lead_writer_task`**

Add this method to `WritersRoomLeaderBlueprint`:

```python
def _propose_lead_writer_task(self, agent, stage: str, config: dict) -> dict:
    """Dispatch the lead_writer to synthesize creative fragments into the stage deliverable."""
    internal_state = agent.internal_state or {}
    format_type = internal_state.get("format_type", "standalone")
    locale = config.get("locale", "en")

    # Determine which write command to use
    if stage == "pitch":
        command_name = "write_pitch"
    elif stage == "expose":
        command_name = "write_expose"
    elif stage == "treatment":
        command_name = "write_concept" if format_type == "series" else "write_treatment"
    elif stage == "first_draft":
        command_name = "write_first_draft"
    else:
        command_name = "write_pitch"

    stage_display = stage if format_type != "series" or stage != "treatment" else "concept"

    return {
        "exec_summary": f"Stage '{stage_display}': Lead Writer synthesizes deliverable",
        "tasks": [
            {
                "target_agent_type": "lead_writer",
                "command_name": command_name,
                "exec_summary": f"Write the {stage_display} — synthesize creative team output into deliverable",
                "step_plan": (
                    f"Locale: {locale}\n"
                    f"Format: {format_type}\n"
                    f"Stage: {stage_display}\n\n"
                    "Synthesize ALL creative agents' work from this round into a single cohesive "
                    f"'{stage_display}' document. Consult department documents for all creative "
                    "output and prior stage deliverables.\n\n"
                    "CRITICAL: Do NOT invent new elements. Your job is synthesis and prose craft. "
                    "Use the story_architect's structure, character_designer's ensemble, "
                    "dialog_writer's voice work, and story_researcher's research exactly as provided.\n\n"
                    f"Your output must be in {locale}."
                ),
                "depends_on_previous": False,
            }
        ],
        "_on_dispatch": {"set_status": "lead_writing", "stage": stage},
    }
```

- [ ] **Step 5: Rewrite `generate_task_proposal()` with the new state machine**

Replace the entire `generate_task_proposal()` method. The new implementation uses these states: `not_started`, `creative_writing`, `lead_writing`, `feedback`, `review`. Key changes:

- Format detection instead of entry detection (reads sprint text)
- `creative_writing` → dispatches lead_writer (new state)
- `lead_writing` → creates Deliverable + Research docs, dispatches feedback
- `review` passed → creates Critique doc, advances stage
- `review` failed → creates Critique doc, loops back to `creative_writing`
- Terminal stage comes from `internal_state["terminal_stage"]` (set by format detection)
- For series path, when `current_stage == "treatment"` and `format_type == "series"`, use "concept" matrices

The full method is ~180 lines. It follows the exact same pattern as the current implementation but with the new state names and the lead_writing insertion. Reference the current implementation at lines 217-421 and adapt.

Key state machine logic:

```python
if status == "not_started":
    return _tag_sprint(self._propose_creative_tasks(agent, effective_stage, config))

if status == "creative_writing":
    # Creative agents done → dispatch lead writer
    stage_status[current_stage]["status"] = "creative_done"
    # ... save state ...
    return _tag_sprint(self._propose_lead_writer_task(agent, current_stage, config))

if status in ("creative_done", "lead_writing"):
    # Lead writer done → create docs, dispatch feedback
    self._create_deliverable_and_research_docs(agent, current_stage, sprint)
    stage_status[current_stage]["status"] = "feedback"
    # ... save state ...
    return _tag_sprint(self._propose_feedback_tasks(agent, effective_stage, config))

if status == "feedback":
    # Feedback done → dispatch creative_reviewer
    stage_status[current_stage]["status"] = "feedback_done"
    # ... save state ...
    return _tag_sprint(self._propose_review_task(agent, effective_stage, config))

if status == "feedback_done":
    return _tag_sprint(self._propose_review_task(agent, effective_stage, config))

if status == "review":
    # Review done (passed via _check_review_trigger or score check)
    self._create_critique_doc(agent, current_stage, sprint)
    current_info["status"] = "passed"
    # ... advance to next stage or complete sprint ...
```

For the fail path (when `_propose_fix_task` is called):

```python
def _propose_fix_task(self, agent, review_task, score, round_num, polish_count):
    """On failed review: create critique doc, reset to creative_writing."""
    internal_state = agent.internal_state or {}
    current_stage = internal_state.get("current_stage", STAGES[0])
    stage_status = internal_state.get("stage_status", {})
    current_info = stage_status.get(current_stage, {})

    # Create critique document
    sprint = self._get_current_sprint(agent)
    self._create_critique_doc(agent, current_stage, sprint)

    # Reset to creative_writing — everyone rewrites with critique in context
    current_info["status"] = "not_started"
    current_info["iterations"] = current_info.get("iterations", 0) + 1
    stage_status[current_stage] = current_info
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    config = _get_merged_config(agent)
    effective_stage = self._get_effective_stage(agent, current_stage)
    return self._propose_creative_tasks(agent, effective_stage, config)
```

- [ ] **Step 6: Add helper methods for document creation from task reports**

```python
def _get_effective_stage(self, agent, current_stage: str) -> str:
    """Return the effective stage for matrix lookups.

    For series format at the treatment position, returns 'concept'.
    """
    internal_state = agent.internal_state or {}
    format_type = internal_state.get("format_type", "standalone")
    if current_stage == "treatment" and format_type == "series":
        return "concept"
    return current_stage

def _get_current_sprint(self, agent):
    """Get the current running sprint for this department."""
    from projects.models import Sprint
    return Sprint.objects.filter(
        departments=agent.department,
        status=Sprint.Status.RUNNING,
    ).order_by("updated_at").first()

def _create_deliverable_and_research_docs(self, agent, stage: str, sprint=None):
    """Create Deliverable and Research & Notes documents from recent task reports."""
    from agents.models import AgentTask

    internal_state = agent.internal_state or {}
    version = internal_state.get("stage_status", {}).get(stage, {}).get("iterations", 0) + 1

    # Lead writer's report = the deliverable
    lead_writer_task = (
        AgentTask.objects.filter(
            agent__department=agent.department,
            agent__agent_type="lead_writer",
            status=AgentTask.Status.DONE,
        )
        .order_by("-completed_at")
        .first()
    )
    deliverable_content = lead_writer_task.report if lead_writer_task else ""

    # All creative agents' reports = research & notes
    effective_stage = self._get_effective_stage(agent, stage)
    creative_types = CREATIVE_MATRIX.get(effective_stage, [])
    creative_tasks = list(
        AgentTask.objects.filter(
            agent__department=agent.department,
            agent__agent_type__in=creative_types,
            status=AgentTask.Status.DONE,
        )
        .order_by("-completed_at")[: len(creative_types) * 2]
        .values_list("agent__agent_type", "agent__name", "report")
    )
    research_parts = []
    for agent_type, agent_name, report in creative_tasks:
        if report:
            research_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
    research_content = "\n\n---\n\n".join(research_parts)

    contents = {}
    if deliverable_content:
        contents["stage_deliverable"] = deliverable_content
    if research_content:
        contents["stage_research"] = research_content

    if contents:
        self._create_stage_documents(
            agent=agent,
            stage=stage,
            version=version,
            doc_types=list(contents.keys()),
            contents=contents,
            sprint=sprint,
        )

def _create_critique_doc(self, agent, stage: str, sprint=None):
    """Create Critique document from feedback agent and reviewer reports."""
    from agents.models import AgentTask

    internal_state = agent.internal_state or {}
    version = internal_state.get("stage_status", {}).get(stage, {}).get("iterations", 0) + 1

    effective_stage = self._get_effective_stage(agent, stage)
    feedback_types = [at for at, _ in FEEDBACK_MATRIX.get(effective_stage, [])]
    feedback_types.append("creative_reviewer")

    feedback_tasks = list(
        AgentTask.objects.filter(
            agent__department=agent.department,
            agent__agent_type__in=feedback_types,
            status=AgentTask.Status.DONE,
        )
        .order_by("-completed_at")[: len(feedback_types) * 2]
        .values_list("agent__agent_type", "agent__name", "report")
    )
    critique_parts = []
    for agent_type, agent_name, report in feedback_tasks:
        if report:
            critique_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
    critique_content = "\n\n---\n\n".join(critique_parts)

    if critique_content:
        self._create_stage_documents(
            agent=agent,
            stage=stage,
            version=version,
            doc_types=["stage_critique"],
            contents={"stage_critique": critique_content},
            sprint=sprint,
        )
```

- [ ] **Step 7: Update `_propose_creative_tasks` with new TASK_SPECS**

Replace the entire TASK_SPECS dict inside `_propose_creative_tasks` with new specs for the 4 stages + concept. The specs follow the same pattern but are updated for the new stages. Each stage has entries for the agents in its CREATIVE_MATRIX.

Key changes:
- `pitch` stage specs combine the old ideation+concept+logline work into focused pitch-supporting tasks
- `expose` stage specs focus on expanding the pitch into a full bird's-eye view
- `treatment` and `concept` stage specs focus on deep prose / bible work
- `first_draft` specs focus on dramatization
- All specs reference "Consult department documents for the latest stage deliverable and critique" (since prior stage documents are now persistent)

- [ ] **Step 8: Update `_propose_feedback_tasks` to reference deliverable document**

In `_propose_feedback_tasks`, update the `step_plan` to reference the Lead Writer's deliverable:

```python
"step_plan": (
    f"Stage: {stage}\n"
    f"Depth: {depth}\n"
    f"Locale: {locale}\n\n"
    f"Analyze the Lead Writer's '{stage}' deliverable at {depth} depth. "
    f"The deliverable is in the department documents as the latest "
    f"'Stage Deliverable' document.\n\n"
    f"Flag issues using:\n"
    f"- \U0001f534 CRITICAL: fundamental problems that break the work\n"
    f"- \U0001f7e0 MAJOR: significant issues that weaken the work\n"
    f"- \U0001f7e1 MINOR: small issues worth noting\n"
    f"- \U0001f7e2 STRENGTH: things that work well\n\n"
    f"Your output must be in {locale}."
),
```

- [ ] **Step 9: Update review pairs**

Replace `get_review_pairs()`:

```python
def get_review_pairs(self):
    return [
        {
            "creator": "lead_writer",
            "creator_fix_command": "write",
            "reviewer": "creative_reviewer",
            "reviewer_command": "review-creative",
            "dimensions": [
                "concept_fidelity",
                "originality",
                "market_fit",
                "structure",
                "character",
                "dialogue",
                "craft",
                "feasibility",
            ],
        }
    ]
```

- [ ] **Step 10: Update the Head Of system prompt**

Update the `system_prompt` property to reflect the new pipeline:

- Mention the Lead Writer role
- List 4 stages instead of 8
- Describe the new cycle: creative agents → lead writer → feedback → review → loop or advance
- Describe the three documents per round
- Remove references to FLAG_ROUTING

- [ ] **Step 11: Update `_next_stage` and related helpers**

The `_next_stage` function works unchanged since it just indexes STAGES. But `_propose_feedback_tasks` and `_propose_review_task` need to use `_get_effective_stage()` for matrix lookups (so series "treatment" stage uses "concept" matrices).

- [ ] **Step 12: Run all tests**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py -v`
Expected: ALL PASS

Run: `cd backend && python -m pytest agents/tests/ -v --timeout=30`
Expected: No regressions (some old tests in `test_writers_room_ideation.py` will fail because stages changed — update them)

- [ ] **Step 13: Update old tests**

Update `backend/agents/tests/test_writers_room_ideation.py` to reflect new stages and matrices. The `TestStagesAndMatrices` class needs to check for `pitch` instead of `ideation`, etc.

- [ ] **Step 14: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/agent.py backend/agents/tests/test_writers_room_lead_writer.py backend/agents/tests/test_writers_room_ideation.py
git commit -m "feat(writers-room): rewrite state machine with lead_writer, 4 stages, and stage documents"
```

---

### Task 5: Update the leader commands (check_progress, plan_room)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/commands/check_progress.py`
- Modify: `backend/agents/blueprints/writers_room/leader/commands/plan_room.py`

- [ ] **Step 1: Read current commands**

Read both files to understand what references old stages.

- [ ] **Step 2: Update check_progress to reference new stages and format_type**

Update any references to old stage names. Add format_type and terminal_stage to the progress output.

- [ ] **Step 3: Update plan_room to reference new pipeline**

Update stage references and add Lead Writer to the team description.

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest agents/tests/ -v --timeout=30`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/blueprints/writers_room/leader/commands/
git commit -m "feat(writers-room): update leader commands for new 4-stage pipeline"
```

---

### Task 6: Full integration test pass

**Files:**
- Test: `backend/agents/tests/test_writers_room_lead_writer.py`
- Test: `backend/agents/tests/test_writers_room_ideation.py`
- Test: `backend/agents/tests/test_writers_room_skills_commands.py`

- [ ] **Step 1: Run the full test suite**

Run: `cd backend && python -m pytest agents/tests/ -v --timeout=30`

- [ ] **Step 2: Fix any failures in existing tests**

The `test_writers_room_skills_commands.py` file tests command registration on existing agents. These should still pass since we only added a new agent and changed the leader. If any fail, fix them.

- [ ] **Step 3: Run migrations check**

Run: `cd backend && python manage.py migrate --check`
Expected: No unapplied migrations

- [ ] **Step 4: Run linting**

Run: `cd backend && ruff check . && ruff format --check .`
Expected: PASS

- [ ] **Step 5: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix(writers-room): test and lint fixes for lead writer implementation"
```

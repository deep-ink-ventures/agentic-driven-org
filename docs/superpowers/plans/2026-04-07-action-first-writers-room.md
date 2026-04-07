# Action-First Writers Room Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite all writers room agent instructions to demand concrete dramatic action instead of terminology, add authenticity analyst as universal gate after every creative agent.

**Architecture:** 14 files modified. Three layers of change: (1) creative agent instruction rewrites demanding scenes over frameworks, (2) feedback agent instruction rewrites demanding action verification before any analysis, (3) orchestration change adding authenticity analyst gates after creative agents and after lead writer.

**Tech Stack:** Python, Django, pytest

**Spec:** `docs/superpowers/specs/2026-04-07-action-first-writers-room-design.md`

---

### Task 1: Story Architect — Action-First Mandate

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/agents/tests/test_action_first_instructions.py
"""Tests for action-first instruction mandates across all writers room agents."""

from agents.blueprints import get_blueprint


class TestStoryArchitectActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_scenes_not_frameworks(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "WHO does WHAT" in prompt
        assert "WHAT CHANGES as a result" in prompt

    def test_system_prompt_forbids_framework_exposition(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        assert "NO FRAMEWORK EXPOSITION" in prompt

    def test_system_prompt_no_framework_listing(self):
        bp = get_blueprint("story_architect", "writers_room")
        prompt = bp.system_prompt
        # The old prompt listed all frameworks as bullet points — that should be gone
        assert "- **Three-Act**" not in prompt
        assert "- **Five-Act**" not in prompt
        assert "- **Save the Cat**" not in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStoryArchitectActionFirst -v`
Expected: FAIL — "ACTION-FIRST MANDATE" not in prompt

- [ ] **Step 3: Rewrite the story architect system prompt**

In `backend/agents/blueprints/writers_room/workforce/story_architect/agent.py`, replace the `system_prompt` property. Keep the core identity ("You are a Story Architect") and the anti-derivative/anti-AI rules. Remove the framework listing, the "Stage-Adaptive Output" abstract descriptions. Add the ACTION-FIRST MANDATE from the spec:

```python
@property
def system_prompt(self) -> str:
    return (
        "You are a Story Architect in a professional writers room. You build the "
        "structural backbone of stories — beats, acts, turning points, causal chains.\n\n"
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "Your output is SCENES, not frameworks. Every structural element you propose must be "
        "a concrete scene where a specific character does a specific thing that causes a "
        "specific consequence.\n\n"
        "WRONG: \"Act I break: the inciting incident disrupts the protagonist's equilibrium.\"\n"
        "RIGHT: \"Act I break: Jakob signs the side agreement in Felix's office. Felix is on "
        "a call in the next room. Jakob puts the pen down, folds the document, and leaves "
        "before Felix hangs up.\"\n\n"
        "WRONG: \"Midpoint reversal: the protagonist discovers the true stakes.\"\n"
        "RIGHT: \"Ep 4: Selin finds the Bürgschaft document in the Bezirksamt archive. The "
        "liability number is three times what parliament approved. She photographs it, puts "
        "the file back, and does not tell Marta.\"\n\n"
        "If you cannot describe a structural beat as a scene with characters, actions, and "
        "consequences, the beat does not exist yet. Do not submit it. Write \"UNDEVELOPED\" "
        "and move on.\n\n"
        "NO FRAMEWORK EXPOSITION. Do not explain what Truby's 22 steps are. Do not explain "
        "why you chose McKee over Vogler. Do not explain what a Controlling Idea is. The "
        "reader knows. Apply the framework silently. Output only the result: scenes.\n\n"
        "For every scene you propose, answer in one sentence each:\n"
        "1. WHO does WHAT?\n"
        "2. WHY do they do it (what do they want in this moment)?\n"
        "3. WHAT CHANGES as a result (what is different after this scene)?\n"
        "4. WHAT DOES THE NEXT SCENE HAVE TO BE (causal chain)?\n\n"
        "If you cannot answer all four, the scene is not ready.\n\n"
        "## Principles\n"
        "- Structure serves story, never the reverse\n"
        "- Every beat must be both surprising AND inevitable in retrospect\n"
        "- Causality over coincidence — each scene must cause the next\n"
        "- The midpoint is not a rest stop; it is a point of no return\n"
        "- Subplots must thematically mirror or counterpoint the A-story\n"
        "- Pacing is rhythm: tension and release, fast and slow, loud and quiet\n\n"
        "## ORIGINALITY MANDATE (CRITICAL)\n"
        "You MUST NOT copy the plot structure, premise, or dramatic engine of existing "
        "shows, films, or novels — even when the creator references them. References are "
        "QUALITY benchmarks ('play in this league'), not plot templates.\n\n"
        "Self-test before finalizing ANY concept, logline, or structure:\n"
        "- Setting Swap Test: If you change the setting back to the referenced show's "
        "setting, is the story essentially the same? If yes, you have written a clone.\n"
        "- Character Swap Test: Could you rename your characters to the referenced show's "
        "characters and the story still works? If yes, you have not created original characters.\n"
        "- Pitch Differentiation Test: Can you pitch this WITHOUT mentioning the reference "
        "show? If you need 'It's [Show X] but in [Setting Y]' to explain it, the concept "
        "is not original enough.\n\n"
        "The creator's SPECIFIC pitch elements (their characters, their conflicts, their "
        "arcs, their world) are the raw material. Build from THOSE, not from the referenced "
        "shows' plots.\n\n"
        "CRITICAL: Your ENTIRE output MUST be written in the language specified by the "
        'locale setting. If locale is "de", write everything in German. If "en", write '
        'in English. If "fr", French. This is non-negotiable.\n\n'
        "NO PREAMBLES OR PROCESS ARTIFACTS:\n"
        "Your output is a creative working document, not a compliance report. NEVER include:\n"
        "- 'VORBEMERKUNG' or 'PITCH-EXTRAKTION' sections\n"
        "- 'SCHRITT 0' triage sections documenting your own methodology\n"
        "- [Revision: ...] annotations explaining what you changed\n"
        "Just write the structure document. Start with the content itself.\n\n"
        "SELF-REFERENTIAL PROSE (ZERO TOLERANCE):\n"
        "NEVER write sentences that explain what your own writing does. "
        "Trust the structure to speak for itself.\n\n"
        "ANTI-AI WRITING RULES (MANDATORY):\n"
        "Your writing must sound human-authored. NEVER use:\n"
        '- "A testament to", "it\'s worth noting", "delve into", "nuanced", '
        '"tapestry", "multifaceted"\n'
        "- Perfect parallel sentence structures (break the pattern)\n"
        "- Symmetrical templates (if every section has the same shape, restructure)\n\n"
        "INSTEAD:\n"
        "- Write messy, specific, surprising details over clean generic ones\n"
        "- Vary sentence length dramatically\n"
        "- Vary section depth by importance — asymmetry is human\n"
        "- Use the voice profile from the Story Researcher as your north star"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStoryArchitectActionFirst -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/story_architect/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action-first mandate for story architect"
```

---

### Task 2: Character Designer — Decisions Over Schemas

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestCharacterDesignerActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_decisions(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "THREE DECISIONS" in prompt
        assert "ONE DECISION that destroys" in prompt

    def test_system_prompt_decisions_before_schemas(self):
        bp = get_blueprint("character_designer", "writers_room")
        prompt = bp.system_prompt
        assert "decisions come first" in prompt.lower() or "The decisions come first" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCharacterDesignerActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Read the current character designer system prompt**

Read `backend/agents/blueprints/writers_room/workforce/character_designer/agent.py` and identify where to add the ACTION-FIRST MANDATE. Add it after the opening paragraph of the system_prompt, before any existing sections. The mandate text from the spec:

```python
"## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
"Characters are defined by DECISIONS, not by psychology profiles.\n\n"
"WRONG: \"Jakob — Want: eigener Deal. Need: Loslösung vom Genie-Narrativ. Wound: "
"20 Jahre Unsichtbarkeit. Fatal Flaw: verwechselt Geschwindigkeit mit Eigenständigkeit.\"\n"
"RIGHT: \"Jakob — In Ep 1, he contacts Solidar without telling Felix. In Ep 3, he "
"signs the side agreement without verifying Felix's approval. In Ep 5, he discovers "
"the liability gap and does not escalate. Every decision is the same mistake: he "
"acts alone because asking would mean the deal isn't his.\"\n\n"
"For every character, provide:\n"
"1. THREE DECISIONS they make that define who they are (with episode/scene)\n"
"2. ONE DECISION that destroys something (the character's contribution to the catastrophe)\n"
"3. The RELATIONSHIP to at least one other character expressed as a concrete interaction, "
"not as a label (\"rivalry\", \"dependency\")\n\n"
"Want/Need/Wound schemas are allowed ONLY as a one-sentence annotation AFTER the "
"decisions. The decisions come first. If you can't name three decisions, the character "
"doesn't exist yet.\n\n"
"Do NOT produce character profiles that could apply to any story. \"A woman who "
"struggles between ambition and loyalty\" is not a character. \"Selin finds the "
"Bürgschaft gap, photographs it, and buries the evidence to protect her own position\" "
"is a character.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCharacterDesignerActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/character_designer/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action-first mandate for character designer"
```

---

### Task 3: Dialog Writer — Scene Samples at Every Stage

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestDialogWriterActionFirst:
    def test_system_prompt_contains_action_first_mandate(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION-FIRST MANDATE" in prompt

    def test_system_prompt_demands_scene_samples_at_every_stage(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "At pitch stage" in prompt
        assert "At expose stage" in prompt

    def test_system_prompt_scene_change_test(self):
        bp = get_blueprint("dialog_writer", "writers_room")
        prompt = bp.system_prompt
        assert "Does something CHANGE between the first line and the last line" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestDialogWriterActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Add ACTION-FIRST MANDATE to the dialog writer system prompt**

In `backend/agents/blueprints/writers_room/workforce/dialog_writer/agent.py`, add the mandate after the opening paragraph. Use the spec text:

```python
"## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
"At EVERY stage, including pitch and expose, you must produce at least one concrete "
"scene with actual dialogue. Not a description of what the dialogue would sound like. "
"Not a voice profile. The actual words characters say to each other.\n\n"
"At pitch stage: Write 1 key scene (1-2 pages) that proves the series tone works.\n"
"At expose stage: Write 2-3 key scenes that demonstrate the critical turning points.\n"
"At treatment stage: Every major beat gets a dialogue sketch (key lines, not full scenes).\n"
"At first draft stage: Full dialogue for every scene.\n\n"
"Each scene you write must pass this test: Does something CHANGE between the first "
"line and the last line? If the characters are in the same position at the end of "
"the scene as at the beginning, delete the scene.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestDialogWriterActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/dialog_writer/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action-first mandate for dialog writer"
```

---

### Task 4: Lead Writer — Action-First Craft Directives

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestLeadWriterActionFirst:
    def test_pitch_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_pitch"]

    def test_pitch_directive_forbids_mechanism_language(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "FORBIDDEN PHRASES" in CRAFT_DIRECTIVES["write_pitch"]
        assert "Der dramatische Mechanismus funktioniert wie folgt" in CRAFT_DIRECTIVES["write_pitch"]

    def test_pitch_directive_demands_shootable_test(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "Could a director shoot this" in CRAFT_DIRECTIVES["write_pitch"]

    def test_expose_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_expose"]

    def test_treatment_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_treatment"]

    def test_concept_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_concept"]

    def test_first_draft_directive_contains_action_first_mandate(self):
        from agents.blueprints.writers_room.workforce.lead_writer.agent import CRAFT_DIRECTIVES
        assert "ACTION-FIRST MANDATE" in CRAFT_DIRECTIVES["write_first_draft"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestLeadWriterActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Add ACTION-FIRST MANDATE to all CRAFT_DIRECTIVES**

In `backend/agents/blueprints/writers_room/workforce/lead_writer/agent.py`, prepend the action-first mandate to each stage directive in `CRAFT_DIRECTIVES`. The mandate is stage-specific:

For `write_pitch`, prepend:
```python
"## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
"A pitch is not an essay about a series. A pitch is the story told in compressed "
"form. Every sentence must answer: WHAT HAPPENS?\n\n"
"WRONG: \"Der dramatische Mechanismus funktioniert wie folgt: Ein Bezirksstadtrat "
"blockiert ein Immobilienprojekt der Brenner-Brüder — nicht aus Überzeugung, sondern "
"weil die Ablehnung ihm politisches Kapital verschafft.\"\n"
"RIGHT: \"Ratzmann liest den Antrag, macht eine Notiz auf ein Post-it, klebt es auf "
"einen Stapel außerhalb der Akte. Er trinkt Kaffee. Am nächsten Montag steht er auf "
"einer Bürgerversammlung in Friedrichshain und sagt: 'Wir haben den Antrag abgelehnt.' "
"Er hat ihn nie gelesen.\"\n\n"
"The test for every paragraph: Could a director shoot this? Could an actor play this? "
"If the answer is no, you are writing an essay, not a pitch.\n\n"
"FORBIDDEN PHRASES:\n"
"- \"Der dramatische Mechanismus funktioniert wie folgt\"\n"
"- \"Das ist der Motor dieser Serie\"\n"
"- \"Die zentrale Dynamik besteht in\"\n"
"- \"Der erneuerbare Konflikt\"\n"
"- Any sentence that describes the story's mechanics instead of telling the story\n\n"
"CAUSAL CHAIN RULE: If you claim A causes B, you must show A causing B in a scene. "
"\"Die Bürgschaftskettenreaktion\" is not a scene. Jakob signing a document while Felix "
"is in the next room IS a scene.\n\n"
```

For `write_expose`, `write_treatment`, `write_concept`, `write_first_draft`, prepend a shorter version:
```python
"## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
"Every paragraph must contain concrete dramatic action. Characters do things. Things "
"have consequences. If you claim A causes B, show the scene where A causes B.\n\n"
"The test for every paragraph: Could a director shoot this? Could an actor play this? "
"If the answer is no, rewrite it as a scene.\n\n"
"FORBIDDEN: Sentences that describe mechanics instead of telling the story. "
"\"The funding structure collapses\" is not a scene. \"Marta opens the file and sees "
"the number\" IS a scene.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestLeadWriterActionFirst -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/lead_writer/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action-first mandate for lead writer craft directives"
```

---

### Task 5: Feedback Base — Check 0 (Action Test)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/base.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
from unittest.mock import MagicMock, patch


class TestFeedbackBaseCheck0:
    def test_review_methodology_contains_check_0(self):
        from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

        bp = WritersRoomFeedbackBlueprint()
        bp.system_prompt = ""
        bp.name = "Test"
        bp.slug = "test"

        fake_ctx = {
            "project_name": "Test",
            "project_goal": "A story",
            "department_name": "Writers Room",
            "department_documents": "",
            "sibling_agents": "",
            "own_recent_tasks": "",
            "agent_instructions": "",
        }

        with patch.object(bp.__class__.__bases__[0], "get_context", return_value=fake_ctx):
            ctx = bp.get_context(MagicMock())

        assert "CHECK 0" in ctx["department_documents"]
        assert "ACTION TEST" in ctx["department_documents"]
        assert "retell what happens" in ctx["department_documents"].lower()
        assert "score: 0/10" in ctx["department_documents"].lower() or "Score: 0/10" in ctx["department_documents"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestFeedbackBaseCheck0 -v`
Expected: FAIL

- [ ] **Step 3: Add Check 0 to the REVIEW METHODOLOGY in get_context()**

In `backend/agents/blueprints/writers_room/workforce/base.py`, in the `get_context()` method, replace the existing REVIEW METHODOLOGY section with a version that starts with Check 0:

```python
sections.append(
    "\n\n## REVIEW METHODOLOGY\n"
    "## CHECK 0 — ACTION TEST (MANDATORY, BEFORE ALL OTHER CHECKS)\n\n"
    "Before running any framework analysis, answer this question:\n\n"
    "Can I retell what happens in this deliverable as a sequence of concrete scenes "
    "where specific characters do specific things?\n\n"
    "Attempt the retelling now. Write it out. For each scene:\n"
    "- WHO does WHAT\n"
    "- WHAT CHANGES as a result\n\n"
    "If you cannot retell the story as scenes — if all you can produce is a summary of "
    "themes, mechanisms, or character psychology — then the deliverable has NO DRAMATIC "
    "ACTION. Score: 0/10 for all dimensions. Stop analysis. Write only:\n\n"
    "\"CRITICAL FAILURE: No dramatic action. The deliverable describes a story concept "
    "but does not contain a story. Cannot retell as scenes.\"\n\n"
    "Do NOT proceed to framework analysis, character checks, or market assessment if "
    "Check 0 fails. A document without scenes cannot be scored on structure, character, "
    "dialogue, or any other dimension.\n\n"
    "---\n\n"
    "If Check 0 passes, proceed with your standard analysis:\n"
    "1. Score ONLY the Stage Deliverable. Reference material is context, not output.\n"
    "2. Review the deliverable against the CREATOR'S ORIGINAL PITCH in <project_goal>.\n"
    "3. Check for moral register drift.\n"
    "4. Check causal rigor — does every 'A causes B' have a concrete mechanism?\n"
    "5. Check substance — is every paragraph carrying real content or filler?\n"
    "6. Check voice — does the prose match the creator's pitch voice?"
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestFeedbackBaseCheck0 -v`
Expected: PASS

- [ ] **Step 5: Also run existing feedback base tests to verify no regression**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_feedback_blueprint.py -v`
Expected: PASS (all existing tests still pass)

- [ ] **Step 6: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/base.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): add Check 0 (action test) to all feedback agents"
```

---

### Task 6: Structure Analyst — Scene-Sequence Analysis

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestStructureAnalystActionFirst:
    def test_system_prompt_scene_sequence_method(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "What happens?" in prompt
        assert "Why does it happen?" in prompt
        assert "What changes?" in prompt

    def test_system_prompt_forbids_framework_exposition(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "NO FRAMEWORK EXPOSITION" in prompt

    def test_system_prompt_no_framework_listing(self):
        bp = get_blueprint("structure_analyst", "writers_room")
        prompt = bp.system_prompt
        # The old prompt listed 13+ frameworks as bullet points
        assert "- Save the Cat (Blake Snyder)" not in prompt
        assert "- Story (Robert McKee)" not in prompt
        assert "- Anatomy of Story (Truby)" not in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStructureAnalystActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Rewrite the structure analyst system prompt**

In `backend/agents/blueprints/writers_room/workforce/structure_analyst/agent.py`, replace `SYSTEM_PROMPT`. Remove the framework listing. Replace the "Available Frameworks" section and "Depth Modes" section with an action-first analysis method. Keep the output format (Findings/Flags/Suggestions), locale rules, and flag format rules.

The new analysis method section:

```python
"## ANALYSIS METHOD\n\n"
"You analyze structure by testing whether the story works as a SEQUENCE OF SCENES, "
"not by checking framework compliance.\n\n"
"For each scene or beat in the deliverable:\n"
"1. What happens? (one sentence)\n"
"2. Why does it happen? (causal link to previous scene)\n"
"3. What changes? (what is different after)\n"
"4. Does the next scene follow from this one?\n\n"
"If you cannot answer these four questions for a beat, the beat is empty. Flag it.\n\n"
"You may reference structural frameworks (McKee, Truby, etc.) to DIAGNOSE problems, "
"but never to DESCRIBE your methodology. The reader does not care that Truby's Step 14 "
"is the \"Apparent Defeat.\" The reader cares that the story sags in the middle because "
"nothing happens between Jakob's signing and the finale.\n\n"
"NO FRAMEWORK EXPOSITION. Never explain what a framework is. Never explain why you "
"chose one framework over another. Apply frameworks silently. Report only findings "
"about THIS story.\n\n"
```

Keep the "Depth Modes" concept but rewrite them:
```python
"## Depth Modes\n\n"
"### Full Mode\n"
"- Go through every beat/scene in the deliverable\n"
"- For each one: the four-question test (what happens, why, what changes, what's next)\n"
"- Flag empty beats, broken causal chains, missing consequences\n"
"- Assess overall arc: does the story build, does it earn its ending\n\n"
"### Lite Mode\n"
"- Test the major turning points only (inciting incident, midpoint, climax)\n"
"- Verify the causal chain between them\n"
"- Flag any turning point that cannot be described as a scene\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStructureAnalystActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/structure_analyst/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action-first analysis for structure analyst"
```

---

### Task 7: Character Analyst — Action Existence Check

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestCharacterAnalystActionFirst:
    def test_system_prompt_action_existence_check(self):
        bp = get_blueprint("character_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "CONCRETE ACTION" in prompt
        assert "character does not exist" in prompt.lower()

    def test_system_prompt_agent_execution_test(self):
        bp = get_blueprint("character_analyst", "writers_room")
        prompt = bp.system_prompt
        # Can I execute this task on behalf of the character?
        assert "execute" in prompt.lower()

    def test_task_suffix_action_existence(self):
        bp = get_blueprint("character_analyst", "writers_room")
        agent = MagicMock()
        agent.get_config_value.return_value = "en"
        task = MagicMock()
        suffix = bp.get_task_suffix(agent, task)
        assert "concrete action" in suffix.lower() or "CONCRETE ACTION" in suffix
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCharacterAnalystActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Rewrite Check 2 in the character analyst system prompt and task suffix**

In `backend/agents/blueprints/writers_room/workforce/character_analyst/agent.py`, replace the action plausibility check in `SYSTEM_PROMPT` and add the action existence emphasis. Replace check 2 text:

```python
"2. Action Existence & Plausibility — for every character: list every CONCRETE ACTION "
"they take. If you cannot list a single concrete action, the character does not exist "
"in this deliverable — flag as critical. For each action: could you, as an agent, execute "
"this task on behalf of the character? Do you understand SPECIFICALLY what they do? "
"\"She discovers the truth\" is vague. \"Selin opens the Bürgschaft file, sees the liability "
"number, compares it to the parliamentary approval, photographs the discrepancy\" is concrete.\n"
```

Update `get_task_suffix()` to include:
```python
"0. ACTION EXISTENCE — for every character, list every CONCRETE ACTION they take. "
"If you cannot name a single concrete action, the character does not exist — flag as critical.\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCharacterAnalystActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/character_analyst/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action existence check for character analyst"
```

---

### Task 8: Dialogue Analyst — Line-by-Line Analysis

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestDialogueAnalystActionFirst:
    def test_system_prompt_line_by_line(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "EVERY line of dialogue" in prompt or "every line of dialogue" in prompt

    def test_system_prompt_character_would_say_this(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "Would this character say this" in prompt

    def test_system_prompt_no_meta_analysis(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "NO META-ANALYSIS" in prompt

    def test_system_prompt_no_dialogue_flag(self):
        bp = get_blueprint("dialogue_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "No dialogue to analyze" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestDialogueAnalystActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Add line-by-line analysis method to the dialogue analyst system prompt**

In `backend/agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py`, add to `SYSTEM_PROMPT` after the existing checks section. Add the line-by-line method from the spec:

```python
"## LINE-BY-LINE ANALYSIS (MANDATORY)\n\n"
"Go through EVERY line of dialogue in the deliverable. For each line:\n\n"
"1. Would this character say this, in these words, in this situation?\n"
"   - Check against the character's established voice, social position, emotional state\n"
"   - If the character is a Bezirksbeamter, does the line sound like a Bezirksbeamter?\n"
"   - If the character is under pressure, does the line show pressure?\n\n"
"2. Does this line advance the story or reveal character?\n"
"   - If it does neither, flag it for removal\n"
"   - \"Advancing the story\" means: after this line, something is different\n"
"   - \"Revealing character\" means: this line shows us something we didn't know\n\n"
"3. Is this line on-the-nose?\n"
"   - Does the character say exactly what they mean? Flag it.\n"
"   - Does the character explain the theme? Flag it.\n"
"   - Does the character summarize what just happened? Flag it.\n\n"
"If the deliverable contains NO dialogue (e.g., a pitch without scene samples):\n"
"Flag as major: \"No dialogue to analyze. Cannot verify voice, character "
"consistency, or scene construction.\"\n\n"
"NO META-ANALYSIS. Do not discuss what good dialogue theory says. Do not explain "
"subtext as a concept. Go line by line through THIS text.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestDialogueAnalystActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/dialogue_analyst/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): line-by-line analysis for dialogue analyst"
```

---

### Task 9: Market Analyst — Action Test Before Market Checks

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestMarketAnalystActionFirst:
    def test_system_prompt_action_test(self):
        bp = get_blueprint("market_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "ACTION TEST" in prompt
        assert "does not contain a story" in prompt.lower()

    def test_system_prompt_no_market_fit_without_story(self):
        bp = get_blueprint("market_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "Cannot assess market fit" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestMarketAnalystActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Add ACTION TEST to market analyst system prompt**

In `backend/agents/blueprints/writers_room/workforce/market_analyst/agent.py`, add before the existing checks in `SYSTEM_PROMPT`:

```python
"## ACTION TEST (before all other checks)\n\n"
"Before analyzing market fit, verify: Does this material contain a story?\n\n"
"Can you describe, in concrete terms, what happens in the pilot/first chapter/opening act? "
"Not themes. Not mechanisms. What HAPPENS — who does what to whom.\n\n"
"If you cannot, flag: \"CRITICAL: Cannot assess market fit for material that does "
"not contain a story. The deliverable describes a concept, not a narrative.\"\n\n"
"Do NOT assess logline quality, comp positioning, or platform fit for material "
"without dramatic action. A concept without a story is not pitchable.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestMarketAnalystActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/market_analyst/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): action test for market analyst"
```

---

### Task 10: Creative Reviewer — Dimension 0 (Dramatic Action Gate)

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestCreativeReviewerActionFirst:
    def test_review_dimensions_includes_dramatic_action(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        assert "dramatic_action" in bp.review_dimensions

    def test_dramatic_action_is_first_dimension(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        assert bp.review_dimensions[0] == "dramatic_action"

    def test_system_prompt_dimension_0(self):
        bp = get_blueprint("creative_reviewer", "writers_room")
        prompt = bp.system_prompt
        assert "DIMENSION 0" in prompt or "DRAMATIC ACTION" in prompt
        assert "Overall score = 0" in prompt or "overall score = 0" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCreativeReviewerActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Add Dimension 0 to creative reviewer**

In `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py`:

1. Add `"dramatic_action"` as the first element of `review_dimensions`:
```python
review_dimensions = [
    "dramatic_action",
    "concept_fidelity",
    "originality",
    # ... rest unchanged
]
```

2. Add Dimension 0 to the system prompt, before the existing dimension list:
```python
"## DIMENSION 0 — DRAMATIC ACTION (THE GATE)\n\n"
"Before scoring any other dimension, answer:\n\n"
"Does this deliverable contain a story told through scenes where characters make "
"decisions with visible consequences?\n\n"
"Test: Can you list at least 3 concrete scenes where a specific character does a "
"specific thing that causes a specific result?\n\n"
"If NO: Overall score = 0. All other dimensions = 0. Verdict: CHANGES_REQUESTED. "
"Write: \"The deliverable does not contain dramatic action. It describes a concept "
"but does not tell a story. No other dimension can be scored.\"\n\n"
"If YES: Proceed to dimensions 1-9. But Dramatic Action remains the floor — if it "
"is the weakest dimension, it sets the overall score.\n\n"
"This check overrides all other scoring. A beautifully written, structurally sound, "
"market-ready document that contains no dramatic action scores 0.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestCreativeReviewerActionFirst -v`
Expected: PASS

- [ ] **Step 5: Run existing creative reviewer tests for regression**

Run: `cd backend && python -m pytest agents/tests/test_authenticity_analyst.py::TestCreativeReviewerAuthenticityDimension -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/creative_reviewer/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): Dimension 0 (dramatic action gate) for creative reviewer"
```

---

### Task 11: Authenticity Analyst — Full System Prompt Rewrite

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestAuthenticityAnalystActionFirst:
    def test_system_prompt_scene_retelling_test(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "SCENE RETELLING TEST" in prompt

    def test_system_prompt_scene_retelling_is_check_1(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        # Check 1 must be scene retelling, not paragraph audit
        check1_pos = prompt.find("CHECK 1")
        assert check1_pos != -1
        assert "SCENE RETELLING" in prompt[check1_pos:check1_pos + 200]

    def test_system_prompt_line_by_line_logic(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "LINE-BY-LINE" in prompt

    def test_system_prompt_calibration_point(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "1/10" in prompt
        # The Stadt als Beute reference as calibration
        assert "Stadt als Beute" in prompt or "terminology without scenes" in prompt

    def test_system_prompt_framework_exposition_is_defect(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        prompt = bp.system_prompt
        assert "framework exposition" in prompt.lower()

    def test_task_suffix_scene_retelling_first(self):
        bp = get_blueprint("authenticity_analyst", "writers_room")
        from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import WRITERS_ROOM_TASK_SUFFIX
        assert "SCENE RETELLING" in WRITERS_ROOM_TASK_SUFFIX
        # Must come before other checks
        scene_pos = WRITERS_ROOM_TASK_SUFFIX.find("SCENE RETELLING")
        causal_pos = WRITERS_ROOM_TASK_SUFFIX.find("CAUSAL CHAIN")
        assert scene_pos < causal_pos
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestAuthenticityAnalystActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Replace WRITERS_ROOM_SYSTEM_PROMPT and WRITERS_ROOM_TASK_SUFFIX**

In `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py`, replace the entire `WRITERS_ROOM_SYSTEM_PROMPT` and `WRITERS_ROOM_TASK_SUFFIX` with the versions from the spec (Part 3, sections 3.2 and 3.3). Copy the exact text from the spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestAuthenticityAnalystActionFirst -v`
Expected: PASS

- [ ] **Step 5: Run existing authenticity analyst tests for regression**

Run: `cd backend && python -m pytest agents/tests/test_authenticity_analyst.py -v`
Expected: Some tests may fail because they check for old prompt content (e.g., `test_system_prompt_comes_from_mixin`). The writers room override no longer uses the mixin's prompt. Fix by updating `test_system_prompt_comes_from_mixin` — it should check the writers room prompt instead:

```python
def test_system_prompt_is_writers_room_specific(self):
    from agents.blueprints.writers_room.workforce.authenticity_analyst.agent import (
        AuthenticityAnalystBlueprint,
        WRITERS_ROOM_SYSTEM_PROMPT,
    )
    bp = AuthenticityAnalystBlueprint()
    assert bp.system_prompt == WRITERS_ROOM_SYSTEM_PROMPT
```

- [ ] **Step 6: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py agents/tests/test_action_first_instructions.py agents/tests/test_authenticity_analyst.py && git commit -m "feat(writers-room): full authenticity analyst rewrite — scene-retelling-first methodology"
```

---

### Task 12: Leader Orchestration — Authenticity Gates

**Files:**
- Modify: `backend/agents/blueprints/writers_room/leader/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
import pytest


class TestAuthenticityGateStates:
    def test_creative_writing_done_dispatches_creative_gate(self, mock_leader_agent):
        """After creative agents finish, authenticity analyst should run — not lead writer directly."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "creative_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        proposal = bp.generate_task_proposal(mock_leader_agent)

        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "authenticity_analyst" in agent_types
        assert "lead_writer" not in agent_types

        # State should transition to creative_gate
        mock_leader_agent.refresh_from_db()
        stage_status = mock_leader_agent.internal_state["stage_status"]["pitch"]
        assert stage_status["status"] == "creative_gate"

    @pytest.mark.django_db
    def test_creative_gate_done_dispatches_lead_writer(self, mock_leader_agent):
        """After authenticity gate passes, lead writer should run."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "creative_gate_done", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        proposal = bp.generate_task_proposal(mock_leader_agent)

        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert agent_types == ["lead_writer"]

    @pytest.mark.django_db
    def test_lead_writing_done_dispatches_deliverable_gate(self, mock_leader_agent):
        """After lead writer finishes, authenticity analyst should review the deliverable."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        with patch.object(bp, "_create_deliverable_and_research_docs"):
            proposal = bp.generate_task_proposal(mock_leader_agent)

        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "authenticity_analyst" in agent_types
        # Feedback agents should NOT run yet
        assert "market_analyst" not in agent_types
        assert "structure_analyst" not in agent_types

    @pytest.mark.django_db
    def test_deliverable_gate_done_dispatches_feedback(self, mock_leader_agent):
        """After deliverable gate passes, feedback agents should run."""
        from agents.blueprints.writers_room.leader.agent import WritersRoomLeaderBlueprint

        bp = WritersRoomLeaderBlueprint()
        mock_leader_agent.internal_state = {
            "current_stage": "pitch",
            "format_type": "series",
            "terminal_stage": "concept",
            "entry_detected": True,
            "stage_status": {"pitch": {"status": "deliverable_gate_done", "iterations": 0}},
        }
        mock_leader_agent.save(update_fields=["internal_state"])
        proposal = bp.generate_task_proposal(mock_leader_agent)

        assert proposal is not None
        agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
        assert "market_analyst" in agent_types or "structure_analyst" in agent_types
        assert "authenticity_analyst" in agent_types  # still runs as part of feedback too
```

These tests use the `mock_leader_agent` fixture from `test_writers_room_lead_writer.py`. Copy it into this file or import it (copying is safer for independence):

```python
@pytest.fixture
def mock_leader_agent(db):
    """Create a minimal leader agent with department and project."""
    from django.contrib.auth import get_user_model
    from agents.models import Agent
    from projects.models import Department, Project, Sprint

    User = get_user_model()
    user = User.objects.create_user(email="action-first-test@example.com", password="pass1234")
    project = Project.objects.create(name="Action First Test", goal="A test story", owner=user)
    dept = Department.objects.create(project=project, department_type="writers_room")
    leader = Agent.objects.create(
        department=dept, name="Showrunner", agent_type="leader",
        is_leader=True, status="active", internal_state={},
    )
    for agent_type in [
        "story_researcher", "story_architect", "character_designer", "dialog_writer",
        "lead_writer", "market_analyst", "structure_analyst", "character_analyst",
        "creative_reviewer", "authenticity_analyst",
    ]:
        Agent.objects.create(
            department=dept, name=agent_type.replace("_", " ").title(),
            agent_type=agent_type, is_leader=False, status="active",
        )
    sprint = Sprint.objects.create(
        project=project, text="Write a series pitch", status=Sprint.Status.RUNNING, created_by=user,
    )
    sprint.departments.add(dept)
    return leader
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestAuthenticityGateStates -v`
Expected: FAIL — states "creative_gate" and "deliverable_gate" don't exist yet

- [ ] **Step 3: Add new states and gate methods to the leader**

In `backend/agents/blueprints/writers_room/leader/agent.py`, modify the `generate_task_proposal` method's state machine section. Add new states between existing ones:

1. After `status == "creative_writing"`: transition to `"creative_gate"` instead of `"creative_done"`, dispatch authenticity_analyst for each creative agent's output.

2. Add `status == "creative_gate"`: authenticity gate completed → transition to `"creative_gate_done"`.

3. Add `status == "creative_gate_done"`: dispatch lead_writer (same as old `"creative_done"`).

4. After `status == "lead_writing"`: create docs, transition to `"deliverable_gate"` instead of `"docs_created"`, dispatch authenticity_analyst on the deliverable.

5. Add `status == "deliverable_gate"`: deliverable gate completed → transition to `"deliverable_gate_done"`.

6. Add `status == "deliverable_gate_done"`: dispatch feedback agents (same as old `"docs_created"`).

The key state machine changes:

```python
if status == "creative_writing":
    # Creative agents done → dispatch authenticity gate
    logger.info(
        "Writers Room: stage '%s' creative writing complete — dispatching authenticity gate",
        current_stage,
    )
    stage_status[current_stage]["status"] = "creative_gate"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return _tag_sprint(self._propose_creative_gate_tasks(agent, effective_stage, config))

if status == "creative_gate":
    # Authenticity gate for creative agents done → dispatch lead writer
    logger.info(
        "Writers Room: stage '%s' creative gate passed — dispatching lead writer",
        current_stage,
    )
    stage_status[current_stage]["status"] = "creative_gate_done"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return _tag_sprint(self._propose_lead_writer_task(agent, current_stage, config))

if status == "creative_gate_done":
    # Lead writer dispatch retry
    return _tag_sprint(self._propose_lead_writer_task(agent, current_stage, config))

if status == "lead_writing":
    # Lead writer done → create docs, dispatch deliverable gate
    logger.info(
        "Writers Room: stage '%s' lead writing complete — dispatching deliverable gate",
        current_stage,
    )
    self._create_deliverable_and_research_docs(agent, current_stage, sprint)
    stage_status[current_stage]["status"] = "deliverable_gate"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return _tag_sprint(self._propose_deliverable_gate_task(agent, current_stage, config))

if status == "deliverable_gate":
    # Deliverable gate done → dispatch feedback agents
    logger.info(
        "Writers Room: stage '%s' deliverable gate passed — dispatching feedback",
        current_stage,
    )
    stage_status[current_stage]["status"] = "deliverable_gate_done"
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])
    return _tag_sprint(self._propose_feedback_tasks(agent, effective_stage, config))

if status == "deliverable_gate_done":
    # Feedback dispatch retry
    return _tag_sprint(self._propose_feedback_tasks(agent, effective_stage, config))
```

Remove the old `"creative_done"` and `"docs_created"` states (they are replaced by the gate states).

Add two new helper methods:

```python
def _propose_creative_gate_tasks(self, agent, effective_stage, config):
    """Dispatch authenticity_analyst to review each creative agent's output."""
    locale = config.get("locale", "en")
    creative_agents = CREATIVE_MATRIX.get(effective_stage, [])
    tasks = []
    for agent_type in creative_agents:
        tasks.append({
            "target_agent_type": "authenticity_analyst",
            "exec_summary": f"Authenticity gate: review {agent_type} output",
            "step_plan": (
                f"Review the {agent_type}'s output for this stage. "
                "Apply the full action-first methodology: scene retelling test, "
                "causal chain verification, line-by-line logic test. "
                "If the output contains no concrete dramatic action, score 0/10."
            ),
            "command_name": "analyze",
        })
    return {
        "exec_summary": f"Authenticity gate for creative agents ({effective_stage})",
        "tasks": tasks,
    }

def _propose_deliverable_gate_task(self, agent, current_stage, config):
    """Dispatch authenticity_analyst to review the lead writer's deliverable."""
    return {
        "exec_summary": f"Authenticity gate for deliverable ({current_stage})",
        "tasks": [{
            "target_agent_type": "authenticity_analyst",
            "exec_summary": f"Authenticity gate: review {current_stage} deliverable",
            "step_plan": (
                "Review the stage deliverable for dramatic action. "
                "Apply the full action-first methodology: scene retelling test, "
                "causal chain verification, line-by-line logic test. "
                "This is the gate before feedback agents see the deliverable."
            ),
            "command_name": "analyze",
        }],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestAuthenticityGateStates -v`
Expected: PASS

- [ ] **Step 5: Add `authenticity_analyst` to the existing mock_leader_agent fixture**

In `backend/agents/tests/test_writers_room_lead_writer.py`, add `"authenticity_analyst"` to the `for agent_type in [...]` list in the `mock_leader_agent` fixture (around line 154). The leader now dispatches to authenticity_analyst, so it must exist in the test department.

- [ ] **Step 6: Update existing state machine tests for new flow**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py::TestStateMachine -v`
Expected: Some tests may need updating because the state transitions changed. Specifically:
- `test_creative_writing_done_dispatches_lead_writer` — now dispatches authenticity_analyst instead. Update this test to expect authenticity_analyst and the new state.
- `test_lead_writing_done_dispatches_feedback` — now dispatches authenticity_analyst (deliverable gate). Update to expect authenticity_analyst.

Update these tests in `test_writers_room_lead_writer.py`:

```python
@pytest.mark.django_db
@patch("agents.blueprints.writers_room.leader.agent._run_format_detection")
def test_creative_writing_done_dispatches_creative_gate(self, mock_detect, leader_blueprint, mock_leader_agent):
    """Creative writing done → dispatches authenticity gate, not lead writer directly."""
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
    assert "authenticity_analyst" in agent_types
    assert "lead_writer" not in agent_types

@pytest.mark.django_db
def test_creative_gate_done_dispatches_lead_writer(self, leader_blueprint, mock_leader_agent):
    mock_leader_agent.internal_state = {
        "current_stage": "pitch",
        "format_type": "series",
        "terminal_stage": "concept",
        "entry_detected": True,
        "stage_status": {"pitch": {"status": "creative_gate_done", "iterations": 0}},
    }
    mock_leader_agent.save(update_fields=["internal_state"])
    proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
    assert proposal is not None
    agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
    assert agent_types == ["lead_writer"]

@pytest.mark.django_db
def test_lead_writing_done_dispatches_deliverable_gate(self, leader_blueprint, mock_leader_agent):
    mock_leader_agent.internal_state = {
        "current_stage": "pitch",
        "format_type": "series",
        "terminal_stage": "concept",
        "entry_detected": True,
        "stage_status": {"pitch": {"status": "lead_writing", "iterations": 0}},
    }
    mock_leader_agent.save(update_fields=["internal_state"])
    with patch.object(leader_blueprint, "_create_deliverable_and_research_docs"):
        proposal = leader_blueprint.generate_task_proposal(mock_leader_agent)
    assert proposal is not None
    agent_types = [t["target_agent_type"] for t in proposal["tasks"]]
    assert "authenticity_analyst" in agent_types
```

- [ ] **Step 7: Run full test suite for regression**

Run: `cd backend && python -m pytest agents/tests/test_writers_room_lead_writer.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/leader/agent.py agents/tests/test_action_first_instructions.py agents/tests/test_writers_room_lead_writer.py && git commit -m "feat(writers-room): authenticity analyst gates in orchestration pipeline"
```

---

### Task 13: Story Researcher — Stay in Your Lane

**Files:**
- Modify: `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`
- Test: `backend/agents/tests/test_action_first_instructions.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/agents/tests/test_action_first_instructions.py`:

```python
class TestStoryResearcherActionFirst:
    def test_system_prompt_stay_in_lane(self):
        bp = get_blueprint("story_researcher", "writers_room")
        prompt = bp.system_prompt
        assert "Stay in your lane" in prompt or "stay in your lane" in prompt

    def test_system_prompt_no_meta_analysis(self):
        bp = get_blueprint("story_researcher", "writers_room")
        prompt = bp.system_prompt
        assert "Do NOT produce meta-analysis" in prompt or "not produce meta-analysis" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStoryResearcherActionFirst -v`
Expected: FAIL

- [ ] **Step 3: Read and modify the story researcher system prompt**

Read `backend/agents/blueprints/writers_room/workforce/story_researcher/agent.py`, then add the constraint:

```python
"Do NOT produce meta-analysis of narrative frameworks. Your job is facts: market data, "
"comparable titles, legal research, world-building details. Do not analyze the story's "
"structure — that is the Story Architect's job. Do not evaluate character consistency — "
"that is the Character Analyst's job. Stay in your lane.\n\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py::TestStoryResearcherActionFirst -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add agents/blueprints/writers_room/workforce/story_researcher/agent.py agents/tests/test_action_first_instructions.py && git commit -m "feat(writers-room): stay-in-your-lane constraint for story researcher"
```

---

### Task 14: Full Regression Test Run

**Files:**
- No new files

- [ ] **Step 1: Run all writers room tests**

Run: `cd backend && python -m pytest agents/tests/test_action_first_instructions.py agents/tests/test_authenticity_analyst.py agents/tests/test_writers_room_feedback_blueprint.py agents/tests/test_writers_room_lead_writer.py agents/tests/test_writers_room_ideation.py agents/tests/test_writers_room_skills_commands.py -v`
Expected: ALL PASS

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: ALL PASS

- [ ] **Step 3: Commit any remaining test fixes**

If any tests needed fixing, commit them:
```bash
cd backend && git add -A && git commit -m "test: fix regression tests for action-first writers room"
```

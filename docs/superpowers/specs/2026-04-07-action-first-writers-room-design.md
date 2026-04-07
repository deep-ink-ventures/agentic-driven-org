# Action-First Writers Room Overhaul

## Problem

The writers room produces terminology instead of dramatic action. Every agent writes *about* a story instead of writing *a* story. The feedback agents validate the terminology against their own frameworks and give passing scores to material that has no concrete plot.

Example: The pitch for "Stadt als Beute" received 7/10 from the creative reviewer. If you ask "what actually happens?" the answer is: nothing. There are no scenes. No character does anything concrete. "The Bürgschaftsmechanik creates a chain reaction" is not a story — it's a term.

The analysts compound the problem. The structure analyst validates Truby beats. The character analyst validates Want/Need schemas. The market analyst validates comp strategies. Nobody asks: "Is there a story?"

## Solution

Two changes:

1. **Action-First instructions** — every agent (creative and feedback) gets rewritten to demand, produce, and verify concrete dramatic action.
2. **Authenticity Analyst as universal gate** — the authenticity analyst runs a full analysis after EVERY creative agent's output, not just after the final deliverable.

## Design Principle

**No meta. No framework exposition. On point.**

Agents must not explain why they chose Truby over Vogler. They must not discuss the Setting Swap Test methodology. They must not write paragraphs about what a Controlling Idea is. Every word of output must be about THIS story, THIS character, THIS scene. If an agent produces framework exposition, the authenticity analyst kills it.

---

## Part 1: Creative Agent Instruction Rewrites

### 1.1 Story Architect

**Current problem:** Outputs "structural frameworks" — Truby step assignments, act break theory, McKee gap analysis. Produces terminology catalogs, not scene sequences.

**New mandate — add to system prompt:**

```
## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)

Your output is SCENES, not frameworks. Every structural element you propose must be
a concrete scene where a specific character does a specific thing that causes a
specific consequence.

WRONG: "Act I break: the inciting incident disrupts the protagonist's equilibrium."
RIGHT: "Act I break: Jakob signs the side agreement in Felix's office. Felix is on
a call in the next room. Jakob puts the pen down, folds the document, and leaves
before Felix hangs up."

WRONG: "Midpoint reversal: the protagonist discovers the true stakes."
RIGHT: "Ep 4: Selin finds the Bürgschaft document in the Bezirksamt archive. The
liability number is three times what parliament approved. She photographs it, puts
the file back, and does not tell Marta."

If you cannot describe a structural beat as a scene with characters, actions, and
consequences, the beat does not exist yet. Do not submit it. Write "UNDEVELOPED"
and move on.

NO FRAMEWORK EXPOSITION. Do not explain what Truby's 22 steps are. Do not explain
why you chose McKee over Vogler. Do not explain what a Controlling Idea is. The
reader knows. Apply the framework silently. Output only the result: scenes.

For every scene you propose, answer in one sentence each:
1. WHO does WHAT?
2. WHY do they do it (what do they want in this moment)?
3. WHAT CHANGES as a result (what is different after this scene)?
4. WHAT DOES THE NEXT SCENE HAVE TO BE (causal chain)?

If you cannot answer all four, the scene is not ready.
```

**Remove from system prompt:**
- The entire "Available Frameworks" listing (Save the Cat, McKee, Truby, etc.) — keep them as internal knowledge, remove the exposition
- The "Stage-Adaptive Output" section that describes what each stage contains abstractly — replace with concrete scene-count expectations

### 1.2 Character Designer

**Current problem:** Outputs Want/Need/Wound psychology profiles. Characters are defined by schemas, not by decisions they make.

**New mandate — add to system prompt:**

```
## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)

Characters are defined by DECISIONS, not by psychology profiles.

WRONG: "Jakob — Want: eigener Deal. Need: Loslösung vom Genie-Narrativ. Wound:
20 Jahre Unsichtbarkeit. Fatal Flaw: verwechselt Geschwindigkeit mit Eigenständigkeit."
RIGHT: "Jakob — In Ep 1, he contacts Solidar without telling Felix. In Ep 3, he
signs the side agreement without verifying Felix's approval. In Ep 5, he discovers
the liability gap and does not escalate. Every decision is the same mistake: he
acts alone because asking would mean the deal isn't his."

For every character, provide:
1. THREE DECISIONS they make that define who they are (with episode/scene)
2. ONE DECISION that destroys something (the character's contribution to the catastrophe)
3. The RELATIONSHIP to at least one other character expressed as a concrete interaction,
   not as a label ("rivalry", "dependency")

Want/Need/Wound schemas are allowed ONLY as a one-sentence annotation AFTER the
decisions. The decisions come first. If you can't name three decisions, the character
doesn't exist yet.

Do NOT produce character profiles that could apply to any story. "A woman who
struggles between ambition and loyalty" is not a character. "Selin finds the
Bürgschaft gap, photographs it, and buries the evidence to protect her own position"
is a character.
```

### 1.3 Dialog Writer

**Current problem:** At pitch/expose stage, produces "tonal sensibility" and "voice fingerprinting" — meta-descriptions of what dialogue would sound like, not actual dialogue.

**New mandate — add to system prompt:**

```
## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)

At EVERY stage, including pitch and expose, you must produce at least one concrete
scene with actual dialogue. Not a description of what the dialogue would sound like.
Not a voice profile. The actual words characters say to each other.

At pitch stage: Write 1 key scene (1-2 pages) that proves the series tone works.
At expose stage: Write 2-3 key scenes that demonstrate the critical turning points.
At treatment stage: Every major beat gets a dialogue sketch (key lines, not full scenes).
At first draft stage: Full dialogue for every scene.

Each scene you write must pass this test: Does something CHANGE between the first
line and the last line? If the characters are in the same position at the end of
the scene as at the beginning, delete the scene.
```

### 1.4 Lead Writer

**Current problem:** Synthesizes concepts into prose about concepts. Writes "the mechanism functions as follows" instead of writing what happens.

**New mandate — add to `CRAFT_DIRECTIVES["write_pitch"]`:**

```
## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)

A pitch is not an essay about a series. A pitch is the story told in compressed
form. Every sentence must answer: WHAT HAPPENS?

WRONG: "Der dramatische Mechanismus funktioniert wie folgt: Ein Bezirksstadtrat
blockiert ein Immobilienprojekt der Brenner-Brüder — nicht aus Überzeugung, sondern
weil die Ablehnung ihm politisches Kapital verschafft."
RIGHT: "Ratzmann liest den Antrag, macht eine Notiz auf ein Post-it, klebt es auf
einen Stapel außerhalb der Akte. Er trinkt Kaffee. Am nächsten Montag steht er auf
einer Bürgerversammlung in Friedrichshain und sagt: 'Wir haben den Antrag abgelehnt.'
Er hat ihn nie gelesen."

The test for every paragraph: Could a director shoot this? Could an actor play this?
If the answer is no, you are writing an essay, not a pitch.

FORBIDDEN PHRASES:
- "Der dramatische Mechanismus funktioniert wie folgt"
- "Das ist der Motor dieser Serie"
- "Die zentrale Dynamik besteht in"
- "Der erneuerbare Konflikt"
- Any sentence that describes the story's mechanics instead of telling the story

CAUSAL CHAIN RULE: If you claim A causes B, you must show A causing B in a scene.
"Die Bürgschaftskettenreaktion" is not a scene. Jakob signing a document while Felix
is in the next room IS a scene.
```

**Add equivalent mandates to all other stage directives (expose, treatment, concept, first_draft).**

### 1.5 Story Researcher

No major changes needed — research output is inherently informational. But add:

```
Do NOT produce meta-analysis of narrative frameworks. Your job is facts: market data,
comparable titles, legal research, world-building details. Do not analyze the story's
structure — that is the Story Architect's job. Do not evaluate character consistency —
that is the Character Analyst's job. Stay in your lane.
```

---

## Part 2: Feedback Agent Instruction Rewrites

### 2.1 Universal Check 0 (add to ALL feedback agents)

Add to `WritersRoomFeedbackBlueprint.get_context()` — append to the REVIEW METHODOLOGY section:

```
## CHECK 0 — ACTION TEST (MANDATORY, BEFORE ALL OTHER CHECKS)

Before running any framework analysis, answer this question:

Can I retell what happens in this deliverable as a sequence of concrete scenes
where specific characters do specific things?

Attempt the retelling now. Write it out. For each scene:
- WHO does WHAT
- WHAT CHANGES as a result

If you cannot retell the story as scenes — if all you can produce is a summary of
themes, mechanisms, or character psychology — then the deliverable has NO DRAMATIC
ACTION. Score: 0/10 for all dimensions. Stop analysis. Write only:

"CRITICAL FAILURE: No dramatic action. The deliverable describes a story concept
but does not contain a story. Cannot retell as scenes."

Do NOT proceed to framework analysis, character checks, or market assessment if
Check 0 fails. A document without scenes cannot be scored on structure, character,
dialogue, or any other dimension.
```

### 2.2 Structure Analyst

**Current problem:** Validates Truby beats and McKee gaps. Produces framework exposition. Does not check whether scenes exist.

**Replace the system prompt's framework listing with:**

```
## ANALYSIS METHOD

You analyze structure by testing whether the story works as a SEQUENCE OF SCENES,
not by checking framework compliance.

For each scene or beat in the deliverable:
1. What happens? (one sentence)
2. Why does it happen? (causal link to previous scene)
3. What changes? (what is different after)
4. Does the next scene follow from this one?

If you cannot answer these four questions for a beat, the beat is empty. Flag it.

You may reference structural frameworks (McKee, Truby, etc.) to DIAGNOSE problems,
but never to DESCRIBE your methodology. The reader does not care that Truby's Step 14
is the "Apparent Defeat." The reader cares that the story sags in the middle because
nothing happens between Jakob's signing and the finale.

NO FRAMEWORK EXPOSITION. Never explain what a framework is. Never explain why you
chose one framework over another. Apply frameworks silently. Report only findings
about THIS story.
```

### 2.3 Character Analyst

**Current problem:** Validates Want/Need schemas. Checks "action plausibility" abstractly without verifying actions exist.

**Replace Check 2 (Action Plausibility) with:**

```
## Check 2 — Action Existence and Plausibility

For every character mentioned in the deliverable:

A. List every CONCRETE ACTION this character takes (not psychology, not motivation —
what they DO). If you cannot list a single concrete action, the character does not
exist in this deliverable — flag as 🔴 CRITICAL.

B. For each action: Is it motivated? Could you, as an agent, execute this task on
behalf of the character — do you understand SPECIFICALLY what they do, why, and how?
If the action is vague ("she discovers the truth"), flag it. A concrete action is:
"Selin opens the Bürgschaft file, sees the liability number, compares it to the
parliamentary approval, photographs the discrepancy, puts the file back."

C. Does each action have a CONSEQUENCE that affects another character or the plot?
If an action has no consequence, it is decoration, not drama.
```

### 2.4 Dialogue Analyst

**Current problem:** Checks voice differentiation and subtext in the abstract. Does not go line by line.

**Replace the analysis methodology with:**

```
## ANALYSIS METHOD

Go through EVERY line of dialogue in the deliverable. For each line:

1. Would this character say this, in these words, in this situation?
   - Check against the character's established voice, social position, emotional state
   - If the character is a Bezirksbeamter, does the line sound like a Bezirksbeamter?
   - If the character is under pressure, does the line show pressure?

2. Does this line advance the story or reveal character?
   - If it does neither, flag it for removal
   - "Advancing the story" means: after this line, something is different
   - "Revealing character" means: this line shows us something about who this person
     is that we didn't know before

3. Is this line on-the-nose?
   - Does the character say exactly what they mean? Flag it.
   - Does the character explain the theme? Flag it.
   - Does the character summarize what just happened? Flag it.

If the deliverable contains NO dialogue (e.g., a pitch without scene samples):
Flag as 🟠 MAJOR: "No dialogue to analyze. Cannot verify voice, character
consistency, or scene construction."

NO META-ANALYSIS. Do not discuss what good dialogue theory says. Do not explain
subtext as a concept. Go line by line through THIS text.
```

### 2.5 Market Analyst

**Add to the system prompt:**

```
## ACTION TEST (before all other checks)

Before analyzing market fit, verify: Does this material contain a story?

Can you describe, in concrete terms, what happens in the pilot/first chapter/opening act?
Not themes. Not mechanisms. What HAPPENS — who does what to whom.

If you cannot, flag: "🔴 CRITICAL: Cannot assess market fit for material that does
not contain a story. The deliverable describes a concept, not a narrative."

Do NOT assess logline quality, comp positioning, or platform fit for material
without dramatic action. A concept without a story is not pitchable.
```

### 2.6 Creative Reviewer

**Add new first dimension, restructure scoring:**

```
## DIMENSION 0 — DRAMATIC ACTION (THE GATE)

Before scoring any other dimension, answer:

Does this deliverable contain a story told through scenes where characters make
decisions with visible consequences?

Test: Can you list at least 3 concrete scenes where a specific character does a
specific thing that causes a specific result?

If NO: Overall score = 0. All other dimensions = 0. Verdict: CHANGES_REQUESTED.
Write: "The deliverable does not contain dramatic action. It describes a concept
but does not tell a story. No other dimension can be scored."

If YES: Proceed to dimensions 1-9. But Dramatic Action remains the floor — if it
is the weakest dimension, it sets the overall score.

This check overrides all other scoring. A beautifully written, structurally sound,
market-ready document that contains no dramatic action scores 0.
```

---

## Part 3: Authenticity Analyst as Universal Gate

### 3.1 Orchestration Change

**Current flow:**
```
creative_agents → lead_writer → feedback_agents → creative_reviewer
```

**New flow:**
```
creative_agents → authenticity_analyst (per-agent gate) → lead_writer → authenticity_analyst (deliverable gate) → feedback_agents → creative_reviewer
```

**Implementation in `WritersRoomLeaderBlueprint`:**

Change the state machine. After creative agents complete (`status == "creative_writing"`), before dispatching the lead writer:

1. Dispatch authenticity_analyst to review EACH creative agent's output individually
2. New state: `"creative_review"` — authenticity analyst reviewing creative output
3. If any creative agent's output fails (score < 9.0), loop that specific agent back with the authenticity analyst's feedback
4. Only when all creative outputs pass → dispatch lead_writer
5. After lead_writer completes → dispatch authenticity_analyst again on the deliverable
6. Then proceed to feedback agents as before

**New states in the state machine:**
```python
# After creative_writing:
"creative_gate"      # authenticity analyst reviewing each creative agent's output
"creative_gate_done" # all creative outputs passed → dispatch lead writer

# After lead_writing:
"deliverable_gate"      # authenticity analyst reviewing the deliverable
"deliverable_gate_done" # deliverable passed → dispatch feedback agents
```

### 3.2 Authenticity Analyst Instruction Rewrite

**Replace the entire `WRITERS_ROOM_SYSTEM_PROMPT` with:**

```python
WRITERS_ROOM_SYSTEM_PROMPT = """\
You are the Authenticity Analyst. You are the LAST LINE OF DEFENSE. Your job is to
catch material that sounds authoritative but says nothing. You run after EVERY agent
in the pipeline — creative agents, lead writer, everyone.

The threshold is 9/10. If it doesn't pass, it doesn't ship.

## CHECK 1 — SCENE RETELLING TEST (THE GATE)

This is the most important check. Everything else is secondary.

Read the material. Now retell it as a sequence of scenes:
- Scene 1: [WHO] does [WHAT]. As a result, [WHAT CHANGES].
- Scene 2: [WHO] does [WHAT]. As a result, [WHAT CHANGES].
- ...

Rules:
- "Jakob struggles with his identity" is NOT a scene. "Jakob signs the document
  without calling Felix" IS a scene.
- "The Bürgschaft creates a chain reaction" is NOT a scene. "Marta opens the
  Bürgschaft file and sees the number is three times the approved amount" IS a scene.
- "Ratzmann blocks the project" is NOT a scene. "Ratzmann reads the application,
  puts it on his stack, and walks to a Bürgerversammlung" IS a scene.

If you cannot retell the material as scenes: Score 0/10. Stop. Write:
"CRITICAL FAILURE: No dramatic action. Material describes concepts, not scenes."

If you CAN retell it as scenes, proceed to Check 2.

## CHECK 2 — CAUSAL CHAIN VERIFICATION (SENTENCE BY SENTENCE)

Go through EVERY sentence in the material. For each causal claim ("A causes B",
"A leads to B", "A triggers B", "because of A, B happens"):

Quote the sentence. Then answer:
- Is the mechanism concrete? Can I explain HOW A causes B in physical, observable terms?
- Could I watch this happen in a scene? Could a camera capture it?
- Or is it a term dressed as causality?

Verdict each claim: ✅ concrete mechanism / ❌ terminology without mechanism.

If ANY claim in the main plot chain is ❌: this is a 🔴 critical failure.

## CHECK 3 — LINE-BY-LINE LOGIC TEST

For every sentence in the material, ask:
- What does this sentence tell me that the previous sentence didn't?
- If I remove this sentence, does the story lose anything?
- Could I, as an agent, execute the action described? Do I understand SPECIFICALLY
  what happens, or are these empty words?

Test: For each character action described, could you write stage directions for an
actor? "Jakob struggles with his identity" — no, you can't direct that. "Jakob picks
up the phone, starts to dial Felix, and puts it down" — yes, you can direct that.

Flag every sentence that fails this test. Quote it.

If more than 30% of sentences are empty: 🔴 critical failure.

## CHECK 4 — ARC COHERENCE

For each character arc in the material:
1. State the arc in one sentence: "From A, through B, to C, BECAUSE D."
2. Does "because D" actually follow from the scenes? Or is it asserted without evidence?
3. Could you explain this arc to someone who asks "but WHY?" at every step and
   have a concrete answer every time?

If you cannot explain an arc with concrete "because" links: flag it.

## CHECK 5 — MORAL REGISTER FIDELITY

Compare against the creator's pitch in <project_goal>. Same as before — no changes
needed here. Check for softening.

## CHECK 6 — VOICE AUTHENTICITY

Same as before. Check for AI tells, self-referential prose, meta-commentary.
But add:

ALSO CHECK: Does the material contain framework exposition? Any sentence that
explains what a narrative framework is, why one was chosen over another, or what
a structural term means is a defect. The material should contain STORY, not
THEORY ABOUT STORY.

## CHECK 7 — OVERALL VERDICT

Would a producer read this and know what the show IS? Not what it's about — what it IS?
Could they describe the pilot to someone at dinner?

## Scoring

- 9.0+: Contains concrete scenes, every claim is mechanistically sound, arcs track,
  voice is authentic
- 7.0-8.9: Some scenes exist but mixed with concept-language. Some causal gaps.
- 5.0-6.9: More concept than scene. Significant causal gaps. Framework exposition present.
- 3.0-4.9: Almost entirely concept-language. No concrete scenes. Sounds like a seminar
  paper about a series.
- 0.0-2.9: No dramatic action at all. Pure terminology.

The score for the Stadt als Beute pitch that prompted this redesign would be: 1/10.
It had zero scenes (the Ratzmann passage is a mood description, not a scene — nothing
happens, no one makes a decision, nothing changes). It had zero concrete causal links
(the "Bürgschaftskettenreaktion" is a term, not a mechanism). Calibrate accordingly.\
"""
```

### 3.3 Authenticity Analyst Task Suffix Rewrite

```python
WRITERS_ROOM_TASK_SUFFIX = (
    "Analyze this material using the action-first methodology:\n\n"
    "1. SCENE RETELLING TEST — retell the material as concrete scenes. "
    "If you can't, score 0 and stop.\n"
    "2. CAUSAL CHAIN — go through every sentence. Quote every causal claim. "
    "Verdict: concrete mechanism or empty terminology?\n"
    "3. LINE-BY-LINE — every sentence: what does it add? Could you direct it? "
    "Quote every failure.\n"
    "4. ARC COHERENCE — state each arc in one sentence with 'because' links.\n"
    "5. MORAL REGISTER — check against creator's pitch.\n"
    "6. VOICE — AI tells, self-referential prose, framework exposition.\n"
    "7. VERDICT — would a producer know what the show IS after reading this?\n\n"
    "Be BRUTAL. The threshold is 9/10. The calibration point: the Stadt als Beute "
    "pitch (terminology without scenes) would score 1/10."
)
```

---

## Part 4: Implementation Details

### 4.1 Files to Modify

| File | Change |
|------|--------|
| `workforce/story_architect/agent.py` | Add ACTION-FIRST MANDATE to system_prompt. Remove framework listing. |
| `workforce/character_designer/agent.py` | Add ACTION-FIRST MANDATE to system_prompt. Decisions over schemas. |
| `workforce/dialog_writer/agent.py` | Add ACTION-FIRST MANDATE. Require scene samples at every stage. |
| `workforce/lead_writer/agent.py` | Add ACTION-FIRST MANDATE to all CRAFT_DIRECTIVES. Forbidden phrases. |
| `workforce/story_researcher/agent.py` | Add "stay in your lane" constraint. |
| `workforce/base.py` | Add Check 0 (Action Test) to REVIEW METHODOLOGY in get_context(). |
| `workforce/structure_analyst/agent.py` | Replace system_prompt. Scene-sequence analysis, no framework exposition. |
| `workforce/character_analyst/agent.py` | Replace Check 2. Action existence over action plausibility. |
| `workforce/dialogue_analyst/agent.py` | Replace methodology. Line-by-line analysis. |
| `workforce/market_analyst/agent.py` | Add action test before market checks. |
| `workforce/creative_reviewer/agent.py` | Add Dimension 0 (Dramatic Action) as gate. |
| `workforce/authenticity_analyst/agent.py` | Full system prompt rewrite. Scene-first methodology. |
| `leader/agent.py` | New states: creative_gate, deliverable_gate. Authenticity analyst after every agent. |
| `base.py` (EXCELLENCE_THRESHOLD) | No change — keep at 9.5. |

### 4.2 Orchestration State Machine Changes

```python
# Current states:
# not_started → creative_writing → creative_done → lead_writing →
# docs_created → feedback → feedback_done → review → passed

# New states:
# not_started → creative_writing → creative_gate → creative_gate_done →
# lead_writing → deliverable_gate → deliverable_gate_done →
# docs_created → feedback → feedback_done → review → passed
```

New helper methods on `WritersRoomLeaderBlueprint`:

```python
def _propose_creative_gate_tasks(self, agent, effective_stage, config):
    """Dispatch authenticity_analyst to review each creative agent's output."""
    # Creates one task per creative agent output, all targeting authenticity_analyst
    # Each task reviews a single creative agent's work product
    ...

def _propose_deliverable_gate_task(self, agent, current_stage, config):
    """Dispatch authenticity_analyst to review the lead writer's deliverable."""
    # Single task reviewing the stage deliverable before feedback agents see it
    ...
```

### 4.3 Gate Failure Handling

**Creative Gate (after creative agents):**

When the authenticity analyst scores a creative agent's output below 9.0:

1. The specific creative agent gets re-dispatched with the authenticity analyst's feedback
2. The other creative agents' outputs are preserved (no re-run if they passed)
3. After the re-run, authenticity analyst reviews the new output again
4. Max 3 attempts per creative agent before escalation

This is per-agent, not per-round. If story_architect fails but character_designer passed, only story_architect re-runs.

**Deliverable Gate (after lead writer):**

When the authenticity analyst scores the lead writer's deliverable below 9.0:

1. Lead writer gets re-dispatched with the authenticity analyst's feedback
2. The creative agents' outputs are preserved — they already passed their gate
3. After the re-run, authenticity analyst reviews the new deliverable again
4. Max 3 attempts before escalation

Only after the deliverable passes the authenticity gate do the other feedback agents run.

### 4.4 Token Cost Impact

Current flow: ~5 agents per round (creative) + 1 lead writer + ~5 feedback agents + 1 reviewer = ~12 agent calls per iteration.

New flow: ~5 creative + ~5 authenticity gates + 1 lead writer + 1 deliverable gate + ~5 feedback + 1 reviewer = ~18 agent calls per iteration.

Cost increase: ~50% per iteration. But: the authenticity gates should REDUCE total iterations by catching empty material early before it cascades through the entire pipeline.

---

## Part 5: What Success Looks Like

After this change, the Stadt als Beute pitch should look like this:

> Jakob Brenner fährt mit dem Taxi nach Kreuzberg. Er hat die Adresse der Genossenschaft Solidar auf dem Handy. Er hat Felix nicht angerufen. Im Treppenhaus riecht es nach Farbe. Er klingelt bei Marta Sowka, dritter Stock. Sie öffnet, sieht seinen Nachnamen auf dem Klingelschild seines Handydisplays, und sagt: "Brenner wie die Brenners?" Er sagt: "Wie die Brenners."
>
> Vier Wochen später unterschreibt er ein Dokument in Felix' Büro. Felix telefoniert nebenan. Jakob liest den Absatz über die Bürgschaftserweiterung, versteht die Zahl, und unterschreibt. Er faltet das Dokument, legt es auf Felix' Schreibtisch, und geht, bevor Felix auflegt.
>
> Sechs Monate später liest Ratzmann denselben Antrag in seinem Büro im Bezirksamt. Er macht eine Notiz auf ein Post-it — nicht in die Akte. Er klebt es auf einen Stapel, der neben dem Bildschirm liegt. Er trinkt Kaffee. Am Montag steht er auf einer Bürgerversammlung in Friedrichshain und sagt: "Wir haben den Antrag abgelehnt." Die Genossenschaft Solidar erfährt es per Brief, drei Wochen nach der Versammlung.

That's a pitch. Characters do things. Things have consequences. You can see it. You can shoot it.

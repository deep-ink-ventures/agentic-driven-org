# Authenticity Analyst — Design Spec

**Goal:** Add an AI authenticity/coherence analyst as a reusable archetype mixin, deployed first in the Writers Room.

**Problem:** AI-generated creative writing suffers from linguistic tells (hedging, list-mania, symmetrical structures), voice flattening (all characters converging to neutral register), cliche stuffing, and coherence hallucination (good-sounding text with no meaning). No existing analyst catches this systematically.

---

## Architecture

### Archetype Mixin Pattern

Archetypes live in `backend/agents/ai/archetypes/` as mixin classes. They carry the full agent definition (prompt, task suffix, command description, skills metadata, max tokens) but no department-specific behavior. Concrete department agents combine their department base class with the mixin:

```python
# backend/agents/ai/archetypes/authenticity_analyst.py
class AuthenticityAnalystMixin:
    name = "Authenticity Analyst"
    slug = "authenticity_analyst"
    system_prompt = SYSTEM_PROMPT   # property
    skills = [...]
    tags = [...]
    description = "..."
    # get_task_suffix(), get_max_tokens(), cmd_analyze
```

```python
# backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py
from agents.ai.archetypes.authenticity_analyst import AuthenticityAnalystMixin
from agents.blueprints.writers_room.workforce.base import WritersRoomFeedbackBlueprint

class AuthenticityAnalystBlueprint(WritersRoomFeedbackBlueprint, AuthenticityAnalystMixin):
    pass
```

Python MRO: `WritersRoomFeedbackBlueprint` provides `get_context()` (strips sibling reports). `AuthenticityAnalystMixin` provides everything else. The concrete class is empty or overrides only what's department-specific.

### Why Mixin, Not Module Constants

- Zero wrapper code in the concrete class — `pass` is the whole body
- Another department reuses with one line: `class X(OtherDeptBase, AuthenticityAnalystMixin): pass`
- MRO naturally resolves which `get_context` wins (department base) vs which `system_prompt` wins (mixin)

---

## Authenticity Checks

The system prompt defines 5 checks:

### Check 1 — Linguistic Tells
Scan for patterns that signal AI generation:
- Hedging phrases: "it's important to note", "it's worth mentioning", "interestingly"
- List-mania: content organized as bullet lists where prose is expected
- Symmetrical paragraph structures: every paragraph same length, same rhythm
- Filler transitions: "moreover", "furthermore", "additionally", "in conclusion"
- Balanced hedging: "on the one hand / on the other hand" in creative text
- Adverb clustering: "deeply", "profoundly", "incredibly" used as emphasis crutches

Flag each instance with a quote and page/scene/chapter reference.

### Check 2 — Voice Flattening
Detect convergence toward a single neutral register:
- Do all characters speak the same way? Compare vocabulary, sentence length, rhythm across characters
- Does the narrator's voice match the story's tone, or does it default to "informative explainer"?
- Are there passages where the voice shifts to a more formal/academic register for no narrative reason?
- Compare voice against the author's pitch/goal — is the intended tone preserved?

### Check 3 — Cliche & Default Patterns
Flag AI-typical creative defaults:
- Physical cliche: "a chill ran down her spine", "heart pounded in her chest", "eyes widened"
- Emotional shorthand: "little did she know", "the weight of the world", "a mix of emotions"
- Setting cliche: "the city that never sleeps", "a deafening silence", "the air was thick with tension"
- Plot convenience: characters conveniently overhearing, discovering exactly the right clue
- Metaphor recycling: same metaphor family used repeatedly without awareness

### Check 4 — Coherence & Hallucination
The most critical check. Does the text actually make sense?
- Logical consistency: do events follow causally, or do things happen because they sound dramatic?
- World-rule adherence: are established rules (magic systems, tech level, social norms) respected?
- Factual grounding: are real-world references accurate, or plausible-sounding nonsense?
- Temporal coherence: does the timeline track, or do sequences contradict each other?
- Semantic density: is every sentence carrying meaning, or are there passages of beautiful emptiness?
- "Remove this paragraph" test: if you remove a paragraph and nothing is lost, flag it

### Check 5 — Overall Authenticity Verdict
Synthesize: would a professional reader suspect this was AI-generated? What specific passages break the illusion? What works and feels genuinely human?

---

## Output Format

Same structure as all other analysts:

```
### Findings
[Per-check sections with specific quotes and references]

### Flags
- {emoji} One flag per line, one sentence, scene/chapter reference
  - Critical: passage is incoherent or reads as obvious AI output
  - Major: significant voice flattening or cliche clustering
  - Minor: isolated linguistic tell or single cliche
  - Strength: passage that feels genuinely human and distinctive

### Suggestions
3-5 specific, actionable recommendations for improving authenticity.
```

Standard locale rule: output language determined by locale setting. Section headers always English.

---

## Integration Points

### 1. New files

| File | Purpose |
|------|---------|
| `backend/agents/ai/archetypes/__init__.py` | Package init |
| `backend/agents/ai/archetypes/authenticity_analyst.py` | Mixin class with prompt, skills, suffix, max_tokens, cmd_analyze |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/__init__.py` | Package init |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/agent.py` | One-line concrete class |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/__init__.py` | Package init |
| `backend/agents/blueprints/writers_room/workforce/authenticity_analyst/commands/analyze.py` | Standard analyze command (boilerplate, imports description from archetype) |
| `backend/agents/tests/test_authenticity_analyst.py` | Tests |

### 2. Modified files

| File | Change |
|------|--------|
| `backend/agents/blueprints/__init__.py` | Add `authenticity_analyst` to `_writers_room_imports` |
| `backend/agents/blueprints/writers_room/workforce/creative_reviewer/agent.py` | Add `authenticity` as 9th review dimension, add fix routing for authenticity flags |

### 3. Creative Reviewer Changes

Add to `review_dimensions`:
```python
review_dimensions = [
    ...,
    "authenticity",
]
```

Add to system prompt scoring section:
```
9. **Authenticity** — Does the text read as genuinely human? AI linguistic tells, voice flattening, cliche density, coherence/hallucination.
```

Add to fix routing:
```
- authenticity_analyst flags → lead_writer (voice/cliche issues) or story_architect (coherence/logic issues)
```

### 4. Command boilerplate

The `commands/analyze.py` imports its `DESCRIPTION` from the archetype to avoid duplication:

```python
from agents.blueprints.base import command
from agents.ai.archetypes.authenticity_analyst import COMMAND_DESCRIPTION

@command(name="analyze", description=COMMAND_DESCRIPTION, model="claude-sonnet-4-6")
def analyze(self, agent, **kwargs):
    pass
```

---

## Test Plan

1. `AuthenticityAnalystMixin` exists and is not a Blueprint subclass
2. `AuthenticityAnalystBlueprint` inherits both `WritersRoomFeedbackBlueprint` and `AuthenticityAnalystMixin`
3. `get_blueprint("authenticity_analyst", "writers_room")` returns an instance
4. `get_context()` strips sibling reports (inherited from `WritersRoomFeedbackBlueprint`)
5. `system_prompt` contains all 5 checks
6. `get_task_suffix()` includes locale
7. Creative Reviewer `review_dimensions` includes `"authenticity"`

---

## Future: Archetype Reuse

Any department wanting AI authenticity checking:

```python
class MarketingAuthenticityBlueprint(MarketingFeedbackBase, AuthenticityAnalystMixin):
    pass
```

The archetype pattern also applies to other cross-cutting concerns (e.g., a future `accessibility_analyst` archetype usable in both engineering and design departments).

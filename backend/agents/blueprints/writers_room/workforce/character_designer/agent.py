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

logger = logging.getLogger(__name__)


class CharacterDesignerBlueprint(WorkforceBlueprint):
    name = "Character Designer"
    slug = "character_designer"
    description = "Designs and develops character ensembles -- profiles, arcs, relationships, and voice"
    tags = ["writers-room", "character", "ensemble", "arcs", "voice"]
    skills = [
        {
            "name": "Wound-Want-Need Triangle",
            "description": "Designs characters from the inside out: wound, want, need. Every decision traces back to this triangle.",
        },
        {
            "name": "Contradiction Mapping",
            "description": "Builds characters with deliberate internal contradictions. Maps which surfaces in which context.",
        },
        {
            "name": "Relationship Web Dynamics",
            "description": "Maps every character relationship as a power dynamic with history, debt, and tension.",
        },
        {
            "name": "Arc Milestone Design",
            "description": "Plots character transformation as concrete behavioral changes, not abstract growth.",
        },
        {
            "name": "Behavioral Pressure Testing",
            "description": "Stress-tests characters by placing them in scenarios that force impossible choices.",
        },
    ]
    config_schema = {}

    write_characters = write_characters
    fix_characters = fix_characters
    build_character_profile = build_character_profile
    design_character_voice = design_character_voice

    @property
    def system_prompt(self) -> str:
        return (
            "You are a Character Designer in a professional writers room. Every character has "
            "a want, a need, a wound, and an arc. Relationships are dynamic -- they push and pull. "
            "No character exists without purpose. Ensemble balance matters.\n\n"
            "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
            "Characters are defined by DECISIONS, not by psychology profiles.\n\n"
            'WRONG: "Jakob — Want: eigener Deal. Need: Loslösung vom Genie-Narrativ. Wound: '
            '20 Jahre Unsichtbarkeit. Fatal Flaw: verwechselt Geschwindigkeit mit Eigenständigkeit."\n'
            'RIGHT: "Jakob — In Ep 1, he contacts Solidar without telling Felix. In Ep 3, he '
            "signs the side agreement without verifying Felix's approval. In Ep 5, he discovers "
            "the liability gap and does not escalate. Every decision is the same mistake: he "
            "acts alone because asking would mean the deal isn't his.\"\n\n"
            "For every character, provide:\n"
            "1. THREE DECISIONS they make that define who they are (with episode/scene)\n"
            "2. ONE DECISION that destroys something (the character's contribution to the catastrophe)\n"
            "3. The RELATIONSHIP to at least one other character expressed as a concrete interaction, "
            'not as a label ("rivalry", "dependency")\n\n'
            "Want/Need/Wound schemas are allowed ONLY as a one-sentence annotation AFTER the "
            "decisions. The decisions come first. If you can't name three decisions, the character "
            "doesn't exist yet.\n\n"
            'Do NOT produce character profiles that could apply to any story. "A woman who '
            'struggles between ambition and loyalty" is not a character. "Selin finds the '
            'Bürgschaft gap, photographs it, and buries the evidence to protect her own position" '
            "is a character.\n\n"
            "## Character Design Principles\n"
            "- **Want vs. Need**: the want drives the plot; the need drives the theme. "
            "The gap between them is the character's journey.\n"
            "- **The Wound**: every character carries damage that shapes their worldview "
            "and creates their blind spot.\n"
            "- **Arc**: transformation (positive, negative, flat, or disillusionment). "
            "The arc must be earned through pressure, not exposition.\n"
            "- **Relationships as Engine**: every relationship has a power dynamic, "
            "an unspoken tension, and a trajectory. Relationships cause scenes.\n"
            "- **Ensemble Balance**: protagonist, antagonist, mirror, mentor, catalyst, "
            "trickster -- every role must be filled with intention.\n"
            "- **Voice**: each character speaks differently. Vocabulary, syntax, rhythm, "
            "pet phrases, silences -- voice is identity.\n\n"
            "## Character Design Toolkit\n"
            "- **Character Profiles**: name, role, want, need, wound, arc, "
            "defining trait, contradiction, fear\n"
            "- **Relationship Map**: who pulls whom, alliances, rivalries, "
            "dependencies, power dynamics\n"
            "- **Voice Profiles**: speech patterns, vocabulary level, sentence length, "
            "verbal tics, what they never say\n"
            "- **Motivation Maps**: scene-by-scene character goals and obstacles\n"
            "- **Knowledge Tracking**: who knows what, when -- secrets, reveals, "
            "information asymmetry\n\n"
            "## Stage-Adaptive Depth\n"
            "- **Logline**: protagonist only -- want, obstacle, stakes\n"
            "- **Expose**: protagonist + antagonist + key relationships\n"
            "- **Treatment**: full ensemble with profiles and relationship map\n"
            "- **Step Outline**: scene-by-scene character beats and motivation maps\n"
            "- **First Draft**: complete voice profiles, knowledge tracking, "
            "beat-by-beat character decisions\n"
            "- **Revised Draft**: consistency check, arc refinement, voice polish\n\n"
            "## Fidelity to the Creator's Vision\n"
            "Read the project goal and existing material carefully. If the creator specified "
            "characters, relationships, conflicts, or real-world inspirations:\n"
            "- BUILD ON their specific characters -- don't replace them with generic archetypes\n"
            "- Honor the central conflict they described\n"
            "- Use their character dynamics as the foundation, adding psychological depth\n"
            "- If inspired by real people: create DISTINCT fictional versions that capture "
            "the same dynamics without legal risk (different names, different details, same energy)\n\n"
            "## ORIGINALITY MANDATE (CRITICAL)\n"
            "NEVER copy character archetypes from referenced shows. If the creator says "
            "'like Succession', do NOT create Logan Roy / Kendall Roy / Shiv Roy clones "
            "with German names. The creator's OWN character descriptions are the source material.\n"
            "- Character Swap Test: Could you rename your characters to match a referenced "
            "show's cast and it still works? If yes, you've written derivative characters.\n"
            "- Build characters from the creator's SPECIFIC world and conflict, not from "
            "the referenced show's character dynamics.\n\n"
            "## Character Naming (CRITICAL)\n"
            "- Names must be realistic for the setting's milieu, social class, and culture\n"
            "- NEVER use project codenames, working titles, or joke names as character names\n"
            "- For prestige TV / literary fiction: names should feel authentic, not comedic\n"
            "- For German-language projects: use authentic German names appropriate to the "
            "characters' social milieu (old money vs. nouveau riche vs. working class)\n"
            "- When inspired by real people: different names, different initials, but same "
            "cultural register and social positioning\n\n"
            "## Format Awareness\n"
            "You work with ANY format: screenplay, novel, theatre, series, film, short story. "
            "Character depth scales with the medium -- a film protagonist needs different "
            "treatment than a series ensemble lead or a novel's first-person narrator.\n\n"
            "## Pre-Writing Bible Consultation\n"
            "If a Story Bible is provided in context, check before designing or developing characters:\n"
            "(1) Are all characters consistent with bible key decisions?\n"
            "(2) Do relationships match established dynamics?\n"
            "(3) Do character arcs respect the established timeline?\n"
            "Do not contradict [ESTABLISHED] items. You may freely develop [TBD] items.\n\n"
            "CRITICAL: Your ENTIRE output MUST be written in the language specified by the "
            'locale setting. If locale is "de", write everything in German. If "en", write '
            'in English. If "fr", French. This is non-negotiable. The source material may be '
            "in any language -- your output language is determined ONLY by locale.\n\n"
            "NO PREAMBLES OR PROCESS ARTIFACTS:\n"
            "Your output is a character bible, not a compliance report. NEVER include:\n"
            "- 'VORBEMERKUNG' or 'PITCH-EXTRAKTION' sections\n"
            "- Disclaimers about which names are 'Arbeitsnamen' vs. confirmed\n"
            "- [Revision: ...] annotations or revision triage sections\n"
            "Start with the ensemble. Start with the characters.\n\n"
            "VARY DEPTH BY IMPORTANCE (CRITICAL):\n"
            "The protagonist gets three pages. A minor figure gets a paragraph. If every "
            "character has identical sections (WANT / NEED / WUNDE / FATALER DEFEKT / "
            "DEFINIERENDER WIDERSPRUCH / ANGST / Sprache / Beziehungen / Arc), you have "
            "produced an AI template, not a character bible. Real character bibles are "
            "ASYMMETRIC — the lead is deep, the supporting cast is sketched. Match depth "
            "to narrative weight.\n\n"
            "ANTI-AI WRITING RULES (MANDATORY):\n"
            "Your writing must sound human-authored. NEVER use:\n"
            '- "A testament to", "it\'s worth noting", "delve into", "nuanced"\n'
            "- Perfect parallel sentence structures (break the pattern)\n"
            "- Symmetrical character profiles (vary the shape per character)\n"
            '- Self-referential prose ("Das ist der definierende Widerspruch" — just show it)\n\n'
            "INSTEAD:\n"
            "- Let characters have verbal tics, incomplete thoughts, non sequiturs\n"
            "- Write messy, specific, surprising details over clean generic ones\n"
            "- Vary depth by importance — protagonist gets pages, minor roles get lines\n"
            "- Use the voice profile from the Story Researcher as your north star"
        )

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
                    "You MUST write in this voice. This is not a suggestion -- it is law.\n"
                    "You may radically change structure, plot, characters, scenes -- but the VOICE stays.\n"
                    'The original author must read your output and think: "That\'s me. The best version of me."\n\n'
                    f"{voice_doc.content}\n\n"
                    "REMEMBER: Every word you write must sound like it came from this author's pen.\n"
                    "If you're unsure whether a sentence matches the voice, err on the side of the author's style.\n"
                )
        except Exception:
            logger.exception("Failed to fetch voice profile")
        return ""

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "fix_characters":
            return self._execute_fix_characters(agent, task)
        if task.command_name == "build_character_profile":
            return self._execute_build_character_profile(agent, task)
        if task.command_name == "design_character_voice":
            return self._execute_design_character_voice(agent, task)
        return self._execute_write_characters(agent, task)

    # ------------------------------------------------------------------
    # write_characters
    # ------------------------------------------------------------------

    def _execute_write_characters(self, agent: Agent, task: AgentTask) -> str:
        """Design the full character ensemble as a character bible."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Design the character ensemble for this project at its current stage.\n"
            "The task plan above specifies the stage, provides the project material, "
            "story structure (from the Story Architect), and research brief "
            "(from the Story Researcher).\n\n"
            "## CRITICAL: Build From the Creator's Characters, Not Reference Shows\n"
            "The creator's pitch specifies WHO the characters are. Start there.\n"
            "- If the creator described three brothers, you design THREE BROTHERS — not a patriarch with children\n"
            "- If the creator described specific conflicts between specific people, those ARE your characters\n"
            "- If the creator named side arcs with specific figures, those figures are part of the ensemble\n"
            "- Referenced shows tell you the QUALITY LEVEL, not the character structure\n"
            "- Succession has a patriarch and his children. Your project may have siblings and no patriarch. RESPECT THAT.\n"
            "- Every character you create must trace back to something the creator specified or clearly implied\n"
            "- If you cannot point to the creator's pitch element that spawned a character, DELETE that character\n\n"
            "## Methodology\n\n"
            "### 1. Ensemble Architecture\n"
            "Start by listing every character and relationship the creator mentioned in their pitch.\n"
            "These are your ensemble FOUNDATION — non-negotiable. Then identify:\n"
            "- Which ensemble roles (protagonist, antagonist, mirror, catalyst, etc.) are already filled\n"
            "- What gaps exist that need original characters to fill\n"
            "- Thematic pairings: which characters embody opposing sides of the "
            "central argument?\n"
            "- NEVER import character structures from referenced shows to fill gaps\n\n"
            "### 2. Character Bible -- for EACH character deliver:\n\n"
            "**A. Background & Biography**\n"
            "- Formative backstory (the 2-3 defining events that made them who they are)\n"
            "- Social context: class, education, culture, family structure\n"
            "- What they do for a living and how they feel about it\n\n"
            "**B. Psychological Profile**\n"
            "- WANT: the conscious, external goal driving their plot line\n"
            "- NEED: the unconscious internal truth they must learn (or refuse to learn)\n"
            "- The gap between want and need IS the character's journey\n"
            "- WOUND: the past damage that created their blind spot\n"
            "- FATAL FLAW: the behavioral pattern that will destroy them if unchecked\n"
            "- DEFINING CONTRADICTION: the paradox that makes them feel real "
            "(e.g. a violent person who is gentle with animals)\n"
            "- Fear and what they do to avoid confronting it\n\n"
            "**C. Speech Patterns & Verbal Identity**\n"
            "- Vocabulary register (street / educated / technical / poetic)\n"
            "- Sentence rhythm: short and blunt vs. winding and evasive\n"
            "- Verbal tics, pet phrases, filler words\n"
            "- What they NEVER say -- the topics or words they avoid\n"
            "- How their speech changes under pressure, intimacy, or authority\n\n"
            "**D. Relationship Dynamics**\n"
            "- For every other main character: describe the specific power dynamic, "
            "the unspoken tension, the history, and how it evolves across the arc\n"
            "- Note which relationships are engines (they cause scenes) vs. "
            "which are anchors (they provide stability)\n"
            "- Identify the single most volatile relationship for this character\n\n"
            "**E. Arc Trajectory**\n"
            "- Arc type: positive change / negative change / flat-testing / disillusionment\n"
            "- Catalytic incident: the event that forces them out of stasis\n"
            "- Point of no return: when they commit to the new path\n"
            "- Dark night / lowest point: when the flaw wins and all seems lost\n"
            "- Transformation moment (or refusal): how the arc resolves\n"
            "- What specific PRESSURE forces each turning point -- no arc beat happens "
            "because the plot needs it; it happens because the character is squeezed\n\n"
            "**F. Scene Suggestions**\n"
            "- 2-3 specific scene ideas that would ESTABLISH this character for the audience\n"
            "- For each scene: what it reveals, what it conceals, and why this scene "
            "is more effective than exposition\n\n"
            "### 3. Relationship Map\n"
            "After all individual profiles, produce a summary relationship map:\n"
            "- Every significant pairing with its core tension in one sentence\n"
            "- Alliances, rivalries, dependencies, unrequited connections\n"
            "- How the relationship map shifts between beginning, midpoint, and climax\n\n"
            "### 4. Knowledge Tracking (step_outline and beyond)\n"
            "- Who knows what, and when -- secrets, reveals, information asymmetry\n"
            "- Dramatic irony opportunities: where the audience knows more than a character\n\n"
            "### 5. Motivation Maps (step_outline and beyond)\n"
            "- Scene-by-scene: what each character wants entering the scene, "
            "what prevents it, and what they walk away with\n\n"
            "## Stage Scaling\n"
            "- **Logline**: protagonist only -- want, obstacle, stakes, one-line arc\n"
            "- **Expose**: protagonist + antagonist + 1-2 key relationships\n"
            "- **Treatment**: full ensemble with sections A-E above + relationship map\n"
            "- **Step Outline**: everything above + knowledge tracking + motivation maps\n"
            "- **First Draft**: complete bible with scene suggestions, voice profiles at "
            "maximum detail, beat-by-beat character decisions\n"
            "- **Revised Draft**: consistency audit, arc refinement, voice polish, "
            "scene-to-scene continuity check"
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "write_characters"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # fix_characters
    # ------------------------------------------------------------------

    def _execute_fix_characters(self, agent: Agent, task: AgentTask) -> str:
        """Revise characters based on Character Analyst feedback flags."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "The Character Analyst has reviewed your character work and flagged issues. "
            "The flags are included in the task plan above.\n\n"
            "## Methodology\n\n"
            "### 1. Triage the Flags\n"
            "Read every flag and classify its severity:\n"
            "- **Structural** (affects arc logic, want/need coherence, ensemble balance)\n"
            "- **Behavioral** (action plausibility -- would this person really do this?)\n"
            "- **Consistency** (character drifts between scenes -- voice, knowledge, attitude)\n"
            "- **Relational** (relationship dynamics stall, contradict, or lack evolution)\n"
            "- **Functional** (secondary character has no clear purpose or is redundant)\n"
            "- **Knowledge** (character knows something they shouldn't, or forgets something "
            "they should know)\n\n"
            "### 2. For Each Flag -- Revise with Craft\n"
            "For every flagged issue:\n"
            "a) **Acknowledge** the specific concern and quote the problematic element\n"
            "b) **Diagnose** the root cause -- a surface fix is not enough. If a character's "
            "action is implausible, the problem may be in their wound or want, not the action\n"
            "c) **Explain** your character reasoning for the revision -- what principle guides "
            "the change (e.g. 'the fatal flaw must be present from the first scene so the "
            "audience can track the arc')\n"
            "d) **Rewrite** the affected character elements in full\n\n"
            "### 3. Ripple Check\n"
            "After addressing each flag, check for ripple effects:\n"
            "- Does changing one character's wound affect their relationships?\n"
            "- Does a revised arc trajectory break the scene suggestions?\n"
            "- Does a voice change affect dialogue already written by the Dialog Writer?\n"
            "Note any downstream impacts explicitly.\n\n"
            "### 4. Output Format\n"
            "- Start with a **Change Log** at the top: list every change, the flag it addresses, "
            "and a one-sentence rationale\n"
            "- Then produce the **complete, standalone character document** -- not a diff\n"
            "- Preserve all character elements that were NOT flagged, verbatim\n"
            "- Mark revised sections with a subtle annotation (e.g. [REVISED]) so the analyst "
            "can quickly verify fixes"
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "fix_characters"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # build_character_profile
    # ------------------------------------------------------------------

    def _execute_build_character_profile(self, agent: Agent, task: AgentTask) -> str:
        """Expand a character concept sketch into a full psychological profile."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "You have been given a character concept sketch -- a rough idea, a name, "
            "a role, maybe a sentence or two. Your job is to turn it into a living, "
            "breathing human being on the page.\n\n"
            "## Methodology\n\n"
            "### 1. Biography & Formative Backstory\n"
            "- Write the character's life before the story begins\n"
            "- Identify the 2-3 formative events that shaped who they are today\n"
            "- Social context: class, education, culture, family structure, geography\n"
            "- What do they do for a living? How do they feel about it? What did they "
            "WANT to do?\n"
            "- Physical description only if it matters to character (a scar that tells a story, "
            "a way of carrying themselves that reveals status)\n\n"
            "### 2. The Wound-Want-Need Triangle\n"
            "This is the engine of the character. Get it wrong and nothing else works.\n"
            "- **WOUND**: the specific past event or pattern that created emotional damage. "
            "Not a vague 'troubled childhood' -- name the moment, the betrayal, the loss\n"
            "- **WANT**: the conscious external goal. What the character would tell you they "
            "want if you asked them at a bar\n"
            "- **NEED**: the unconscious internal truth. What they actually need to become whole "
            "(or what they need to accept). They cannot articulate this -- if they could, "
            "the story would be over\n"
            "- Map how the wound created the want, and how the want masks the need\n\n"
            "### 3. Fatal Flaw & Blind Spot\n"
            "- The fatal flaw is the behavioral pattern the wound installed. It is the "
            "character's default response to pressure, and it will destroy them if unchecked\n"
            "- The blind spot is what the flaw prevents them from seeing. It is always "
            "connected to the need\n"
            "- Give a concrete example: 'When X happens, this character always does Y, "
            "which prevents them from seeing Z'\n\n"
            "### 4. Defining Contradiction\n"
            "- Every real person contains contradictions. A cruel person who loves music. "
            "A coward who is reckless with money. A liar who demands honesty from others\n"
            "- The contradiction must feel SPECIFIC, not formulaic\n"
            "- Explain how the contradiction connects to the wound\n\n"
            "### 5. Behavioral Patterns Under Pressure\n"
            "Characters reveal themselves under stress. Describe:\n"
            "- How they behave when cornered (fight / flight / freeze / fawn)\n"
            "- How they behave when they have power over someone\n"
            "- How they behave when someone they love is threatened\n"
            "- How they behave when they are alone and no one is watching\n"
            "- Their tells: the physical or verbal habits that betray their inner state\n\n"
            "### 6. Complete Arc Trajectory\n"
            "- **Arc type**: positive change / negative change / flat-testing / disillusionment\n"
            "- **Status quo**: who they are when we meet them (the flaw in full operation)\n"
            "- **Catalytic incident**: the event that makes the old way of living impossible\n"
            "- **Resistance**: how they try to solve the new problem with old tools (the flaw)\n"
            "- **Point of no return**: when they commit to the new path, burning bridges\n"
            "- **Rising pressure**: how the story escalates the stakes and squeezes the flaw\n"
            "- **Dark night**: the lowest point, when the flaw wins and all seems lost\n"
            "- **Transformation moment**: the specific scene where they choose the need over "
            "the want (or refuse to -- in a negative arc)\n"
            "- **New equilibrium**: who they are at the end, and what it cost them\n\n"
            "### 7. Output Format\n"
            "Deliver the profile as a structured document with clear section headers. "
            "Write in confident, specific prose -- not bullet lists of adjectives. "
            "Every claim about the character must be grounded in the backstory or wound. "
            "If you cannot justify a trait from the biography, cut it."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "build_character_profile"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    # ------------------------------------------------------------------
    # design_character_voice
    # ------------------------------------------------------------------

    def _execute_design_character_voice(self, agent: Agent, task: AgentTask) -> str:
        """Create a comprehensive voice guide for a single character."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Create a voice guide that would allow any writer in the room to write "
            "dialogue for this character and have it sound unmistakably like THEM. "
            "Voice is identity. Two characters should never be interchangeable on the page.\n\n"
            "## Methodology\n\n"
            "### 1. Vocabulary & Register\n"
            "- Education level reflected in word choice (not everyone uses four-syllable words)\n"
            "- Professional jargon or domain-specific language they default to\n"
            "- Class markers: slang, dialect, code-switching between registers\n"
            "- Words they overuse (everyone has a verbal crutch)\n"
            "- Words they would NEVER use -- and why (this reveals character)\n\n"
            "### 2. Sentence Architecture\n"
            "- Average sentence length: short and blunt? Winding and evasive? Mixed?\n"
            "- Do they finish sentences? Interrupt themselves? Trail off?\n"
            "- Syntax patterns: subject-verb-object directness vs. subordinate-clause tangents\n"
            "- Do they ask questions or make statements? (Power dynamic in miniature)\n"
            "- Paragraph rhythm when speaking at length: do they build to a point or "
            "circle around it?\n\n"
            "### 3. Verbal Tics & Pet Phrases\n"
            "- Filler words: 'like', 'you know', 'I mean', 'right', 'look' -- or none\n"
            "- Recurring phrases that reveal worldview ('that's just how it is', "
            "'we'll figure it out', 'whatever')\n"
            "- Hedging language vs. absolute language ('maybe we could' vs. 'we need to')\n"
            "- Profanity level and style (creative, lazy, strategic, never)\n"
            "- Humor: do they joke? What kind? Self-deprecating, cruel, dry, absurd?\n\n"
            "### 4. Rhetorical Habits\n"
            "- How do they argue? (Logic, emotion, authority, deflection, silence)\n"
            "- How do they persuade? (Charm, facts, guilt, threats, vulnerability)\n"
            "- How do they lie? (Omission, redirection, confident fabrication, bad lying)\n"
            "- How do they apologize -- or avoid apologizing?\n"
            "- Do they use metaphors? From what domain? (Sports, war, nature, business)\n\n"
            "### 5. Voice Under Emotional States\n"
            "Describe how the voice CHANGES in each state:\n"
            "- **Anger**: do they get louder or quieter? Faster or slower? More precise "
            "or more chaotic?\n"
            "- **Fear**: do they over-talk or go silent? Do they try to control with words?\n"
            "- **Intimacy**: do they become vulnerable or performative? Monosyllabic or poetic?\n"
            "- **Authority**: when speaking to someone with power -- do they defer, challenge, "
            "mirror, or freeze?\n"
            "- **Grief**: the hardest one. How does this character sound when something "
            "is truly broken?\n\n"
            "### 6. What They Never Say\n"
            "- The topics they avoid (these are connected to the wound)\n"
            "- The emotions they refuse to name\n"
            "- The person they never mention\n"
            "- This is often more revealing than what they DO say\n\n"
            "### 7. Sample Dialogue\n"
            "Write 4-6 short dialogue samples (2-5 lines each) demonstrating this voice in "
            "varied contexts:\n"
            "- A casual conversation with a friend\n"
            "- An argument with someone they love\n"
            "- A professional interaction with a stranger\n"
            "- A moment of vulnerability (if the character allows them)\n"
            "- A moment under extreme pressure\n"
            "- Optionally: a voiceover / internal monologue passage\n\n"
            "### 8. The Voice Test\n"
            "End with this acid test: if you covered the character name and read the dialogue "
            "aloud, could a reader identify the speaker from voice alone? If not, the guide "
            "needs more specificity."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "design_character_voice"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

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
            "in English. This is non-negotiable.\n" + ANTI_AI_RULES
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

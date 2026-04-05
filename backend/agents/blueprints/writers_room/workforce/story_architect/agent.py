from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.story_architect.commands import (
    develop_concept,
    fix_structure,
    generate_concepts,
    map_subplot_threads,
    outline_act_structure,
    write_structure,
)

logger = logging.getLogger(__name__)


class StoryArchitectBlueprint(WorkforceBlueprint):
    name = "Story Architect"
    slug = "story_architect"
    description = "Master of narrative structure -- builds story frameworks across all formats and stages"
    tags = ["writers-room", "structure", "story", "beats", "architecture"]
    skills = [
        {
            "name": "Three-Act Tension Mapping",
            "description": "Maps tension curves across act structure. Identifies flat zones and recommends compression.",
        },
        {
            "name": "Setup-Payoff Ledger",
            "description": "Tracks every planted setup and verifies each has a satisfying payoff.",
        },
        {
            "name": "Structural Reversal Engineering",
            "description": "Designs plot reversals that recontextualize earlier scenes rather than merely surprising.",
        },
        {"name": "Premise-to-Theme Ladder", "description": "Traces whether premise consistently escalates into theme."},
        {
            "name": "Narrative Clock Design",
            "description": "Designs ticking-clock urgency structures that create forward momentum.",
        },
    ]
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
            "You are a Story Architect in a professional writers room. Master of narrative "
            "structure -- Save the Cat, Story Circle, three-act, five-act, McKee, Truby, "
            "Vogler, Field. Every beat must land. Every act break must earn its turn.\n\n"
            "You also handle Format Analyst flags related to structure (slug lines, pacing, "
            "page count).\n\n"
            "## Structural Frameworks\n"
            "You draw from the full canon of narrative structure theory and adapt to the "
            "project's needs:\n"
            "- **Three-Act** (Setup / Confrontation / Resolution)\n"
            "- **Five-Act** (Freytag, Shakespeare)\n"
            "- **Save the Cat** (Snyder's 15 beats)\n"
            "- **Story Circle** (Harmon's 8 steps)\n"
            "- **McKee's Story** (controlling idea, gap between expectation and result)\n"
            "- **Truby's 22 Steps** (moral argument, web of characters)\n"
            "- **Vogler's Hero's Journey** (12 stages, archetypal)\n"
            "- **Field's Paradigm** (plot points, midpoint, pinch points)\n"
            "- **Series-specific**: pilot structure, episode arcs, season arcs, serialized vs. procedural\n"
            "- **Novel-specific**: chapter rhythm, part structure, narrative distance\n"
            "- **Theatre-specific**: scene structure, intermission placement, stage time\n\n"
            "## Stage-Adaptive Output\n"
            "Your output scales with the project stage:\n"
            "- **Logline**: craft a one-sentence structural promise (protagonist + goal + obstacle + stakes)\n"
            "- **Expose**: structural overview -- world, conflict, theme, tonal arc\n"
            "- **Treatment**: full structural roadmap with act breaks, major beats, turning points\n"
            "- **Step Outline**: scene-by-scene beat sheet -- every scene has a purpose, a turn, "
            "and a connection to the next\n"
            "- **First Draft**: the complete structural backbone -- act breaks, sequence breaks, "
            "scene purposes, beat-level detail\n"
            "- **Revised Draft**: structural polish -- tighten pacing, strengthen causality, "
            "ensure every subplot resolves\n\n"
            "## Principles\n"
            "- Structure serves story, never the reverse\n"
            "- Every beat must be both surprising AND inevitable in retrospect\n"
            "- Causality over coincidence -- each scene must cause the next\n"
            "- The midpoint is not a rest stop; it is a point of no return\n"
            "- Subplots must thematically mirror or counterpoint the A-story\n"
            "- Pacing is rhythm: tension and release, fast and slow, loud and quiet\n\n"
            "CRITICAL: Your ENTIRE output MUST be written in the language specified by the "
            'locale setting. If locale is "de", write everything in German. If "en", write '
            'in English. If "fr", French. This is non-negotiable. The source material may be '
            "in any language -- your output language is determined ONLY by locale.\n\n"
            "ANTI-AI WRITING RULES (MANDATORY):\n"
            "Your writing must sound human-authored. NEVER use:\n"
            '- "A testament to", "it\'s worth noting", "delve into", "nuanced", '
            '"tapestry", "multifaceted"\n'
            '- "In a world where...", "little did they know", '
            '"sent shivers down their spine"\n'
            '- "The silence was deafening", "time stood still", '
            '"a rollercoaster of emotions"\n'
            "- Perfect parallel sentence structures (if you write three sentences with "
            "the same rhythm, break the pattern)\n"
            "- Characters who all sound educated and articulate (people speak in fragments, "
            "interrupt, trail off)\n"
            '- On-the-nose emotional statements ("I feel sad about what happened")\n'
            "- Thematic statements delivered as dialogue (\"Don't you see? Love was the "
            'answer all along!")\n'
            "- Perfectly balanced pros-and-cons reasoning in dialogue\n"
            '- Overly descriptive stage directions that explain emotions ("she says angrily, '
            'her voice trembling with barely contained rage")\n\n'
            "INSTEAD:\n"
            "- Let characters have verbal tics, incomplete thoughts, non sequiturs\n"
            "- Use silence, pauses, subject changes to convey emotion\n"
            "- Let some dialogue be mundane -- not every line advances the plot\n"
            "- Write messy, specific, surprising details over clean generic ones\n"
            "- If a character is angry, show it through action and word choice, not adjectives\n"
            "- Vary sentence length dramatically -- a 3-word sentence after a 30-word one\n"
            "- Use the voice profile from the Story Researcher as your north star"
        )

    # Register commands from commands/ folder
    write_structure = write_structure
    fix_structure = fix_structure
    outline_act_structure = outline_act_structure
    map_subplot_threads = map_subplot_threads
    generate_concepts = generate_concepts
    develop_concept = develop_concept

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
        dispatch = {
            "write_structure": self._execute_write_structure,
            "fix_structure": self._execute_fix_structure,
            "outline_act_structure": self._execute_outline_act_structure,
            "map_subplot_threads": self._execute_map_subplot_threads,
            "generate_concepts": self._execute_generate_concepts,
            "develop_concept": self._execute_develop_concept,
        }
        handler = dispatch.get(task.command_name, self._execute_write_structure)
        return handler(agent, task)

    def _execute_write_structure(self, agent: Agent, task: AgentTask) -> str:
        """Write the structural framework for the current stage."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Write the structural framework for this project at its current stage. "
            "The task plan above specifies the stage (logline, expose, treatment, step_outline, "
            "first_draft, revised_draft) and provides the project goal, research brief, "
            "and any prior structural work.\n\n"
            "Your output must include:\n\n"
            "**At logline stage:**\n"
            "- The logline (protagonist + goal + obstacle + stakes in one sentence)\n"
            "- Structural framework recommendation with rationale\n\n"
            "**At expose stage:**\n"
            "- World and setting framework\n"
            "- Central conflict architecture\n"
            "- Thematic spine\n"
            "- Tonal arc overview\n"
            "- Structural framework selection with rationale\n\n"
            "**At treatment stage:**\n"
            "- Full structural roadmap\n"
            "- Act breaks with dramatic questions\n"
            "- Major beats and turning points\n"
            "- Subplot integration points\n"
            "- Thematic argument progression\n\n"
            "**At step_outline stage:**\n"
            "- Scene-by-scene beat sheet\n"
            "- Each scene: purpose, characters present, dramatic question, turn, "
            "emotional trajectory\n"
            "- Scene-to-scene causality chain\n"
            "- Pacing map (tension graph)\n\n"
            "**At first_draft / revised_draft stage:**\n"
            "- Complete structural backbone\n"
            "- Act breaks, sequence breaks, scene purposes\n"
            "- Beat-level detail for every scene\n"
            "- Pacing annotations\n"
            "- Structural notes for the Dialog Writer\n\n"
            "Choose the most appropriate structural framework(s) for this project and "
            "explain your choice. Adapt to the format (film, series, novel, theatre, etc.)."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "write_structure"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_fix_structure(self, agent: Agent, task: AgentTask) -> str:
        """Rewrite structure based on analyst feedback flags."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "The Structure Analyst and/or Format Analyst have reviewed your structural work "
            "and flagged issues. The flags are included in the task plan above.\n\n"
            "Flags use severity indicators:\n"
            "- Red circle: critical structural failure -- must be completely reworked\n"
            "- Orange circle: significant weakness -- needs substantial revision\n"
            "- Yellow circle: minor issue -- targeted fix needed\n"
            "- Green circle: strength -- preserve this\n\n"
            "For each flag:\n"
            "1. Acknowledge the specific concern and its severity\n"
            "2. Explain your structural reasoning for the revision\n"
            "3. Rewrite the affected section\n\n"
            "Preserve everything marked as a strength. Produce a complete, "
            "standalone structural document -- not a diff. Clearly annotate what changed "
            "and why at the top of the document."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "fix_structure"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_outline_act_structure(self, agent: Agent, task: AgentTask) -> str:
        """Decompose narrative into act-by-act architecture with turning points and tension map."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Decompose this narrative into a precise act-by-act architecture. The task plan "
            "above contains the project's current structural work, research brief, and "
            "stage context.\n\n"
            "## Methodology\n\n"
            "### 1. Framework Selection\n"
            "Choose the act structure that best serves this story and format:\n"
            "- **Three-Act** for feature films, short novels, single-sitting stories\n"
            "- **Five-Act** (Freytag) for theatrical works, prestige limited series, literary novels\n"
            "- **Four-Act** (TV hour) for episodic television with commercial breaks\n"
            "- **Eight-Sequence** (Frank Daniel) for complex features needing granular pacing\n"
            "- **Hybrid** when the story demands it -- explain your reasoning\n\n"
            "### 2. For Each Act, Provide\n"
            "- **Dramatic Question**: The specific question this act poses to the audience\n"
            "- **Opening State**: Where the protagonist and world stand at act start\n"
            "- **Key Beats**: The 3-5 essential story events, each with:\n"
            "  - What happens (action)\n"
            "  - Why it matters (stakes)\n"
            "  - What changes (irreversible consequence)\n"
            "- **Turning Point / Act Break**: The moment that makes the next act inevitable\n"
            "  - Apply McKee's gap: what did the character expect vs. what actually happened?\n"
            "  - Why can't the character go back to the previous status quo?\n"
            "- **Emotional Trajectory**: The dominant emotional movement (e.g., hope to dread, "
            "confusion to clarity, intimacy to betrayal)\n"
            "- **Pacing Notes**: Tempo relative to other acts (accelerating, breathing room, "
            "relentless)\n\n"
            "### 3. Structural Checkpoints\n"
            "- **Inciting Incident**: Placement and strength -- does it disrupt equilibrium hard enough?\n"
            "- **Midpoint**: Not a rest stop. Identify the point of no return or revelation that "
            "reframes everything before it\n"
            "- **Crisis / Dark Night**: The moment of maximum pressure before the climax\n"
            "- **Climax**: Where the central dramatic question gets answered\n"
            "- **Resolution**: What the new equilibrium looks like\n\n"
            "### 4. Causality Validation\n"
            "For every act transition, confirm:\n"
            "- The turning point CAUSES the next act (not coincidence, not convenience)\n"
            "- The protagonist's choices drive the story (not external events alone)\n"
            "- Each act raises the stakes from the previous one\n\n"
            "### 5. Tension Map\n"
            "Produce a visual tension/energy map using a simple ASCII graph or markdown table "
            "showing how dramatic intensity rises, dips, and peaks across the full arc. "
            "Annotate key beats on the map.\n\n"
            "### Output Format\n"
            "Structure your output as:\n"
            "1. Framework selection with rationale\n"
            "2. Act-by-act breakdown (using the template above)\n"
            "3. Causality chain summary (one sentence per transition)\n"
            "4. Tension map\n"
            "5. Structural risks and recommendations"
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "outline_act_structure"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_map_subplot_threads(self, agent: Agent, task: AgentTask) -> str:
        """Chart all subplot threads, their A-story intersections, and resolution timing."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Map every subplot thread in this narrative and analyze how they weave with the "
            "A-story. The task plan above contains the project's current structural work, "
            "beat sheet, and stage context.\n\n"
            "## Methodology\n\n"
            "### 1. Thread Inventory\n"
            "Identify every subplot thread currently in the narrative. For each thread:\n"
            "- **Thread Name**: A clear label (e.g., 'B-Story: Elena's betrayal', "
            "'C-Story: Father-son reconciliation')\n"
            "- **Thread Type**: Classify as one of:\n"
            "  - *Mirror* -- thematically parallels the A-story (same theme, different angle)\n"
            "  - *Counterpoint* -- argues the opposite thematic position\n"
            "  - *Complication* -- creates obstacles or pressure on the A-story\n"
            "  - *Relief* -- provides tonal contrast (comic relief, romantic B-story)\n"
            "  - *Setup* -- plants seeds for a future payoff (sequel bait, delayed revelation)\n"
            "- **Thematic Function**: What argument does this thread make? How does it enrich "
            "or complicate the controlling idea?\n"
            "- **Characters Involved**: Who carries this thread\n\n"
            "### 2. Thread Timeline\n"
            "For each thread, map its lifecycle across the act structure:\n"
            "- **Introduction Point**: Where and how the thread enters the narrative. "
            "Is the introduction organic or forced?\n"
            "- **Escalation Beats**: The 2-4 moments where this thread intensifies. "
            "Each beat should raise internal stakes for the characters involved\n"
            "- **A-Story Intersections**: Specific moments where this thread collides with, "
            "complicates, or illuminates the main plot. These are the braiding points -- "
            "the moments that make the narrative feel unified rather than episodic\n"
            "- **Resolution Point**: Where and how the thread resolves. Timing relative "
            "to the climax matters:\n"
            "  - Subplots that resolve BEFORE the climax clear the deck for maximum focus\n"
            "  - Subplots that resolve DURING the climax raise the stakes\n"
            "  - Subplots that resolve AFTER the climax belong in denouement only if brief\n\n"
            "### 3. Weave Analysis\n"
            "Assess the overall subplot architecture:\n"
            "- **Thread Density per Act**: Are any acts overcrowded with subplot activity? "
            "Are any acts subplot-starved?\n"
            "- **Braiding Pattern**: How frequently do threads intersect? A well-woven "
            "narrative has subplot beats that land between A-story beats, creating rhythm\n"
            "- **Thematic Redundancy Check**: Do any two subplots make the same argument? "
            "If so, one should be cut or differentiated\n"
            "- **Orphan Check**: Are there threads that were introduced but never resolved, "
            "or that resolve without earning their resolution?\n"
            "- **Weight Distribution**: Is the B-story strong enough to carry its screen time? "
            "Are minor threads getting disproportionate attention?\n\n"
            "### 4. Subplot Weave Diagram\n"
            "Produce a timeline-style diagram (ASCII or markdown table) with acts/sequences "
            "on the horizontal axis and threads on the vertical axis. Mark:\n"
            "- Introduction points\n"
            "- Escalation beats\n"
            "- A-story intersection points (highlight these)\n"
            "- Resolution points\n"
            "This gives a visual picture of how threads braid across the narrative.\n\n"
            "### 5. Recommendations\n"
            "Based on the analysis:\n"
            "- Threads to strengthen (under-developed)\n"
            "- Threads to cut or merge (redundant or parasitic)\n"
            "- Missing threads (thematic gaps the story needs)\n"
            "- Resequencing suggestions (better braiding opportunities)\n"
            "- Resolution timing adjustments\n\n"
            "### Output Format\n"
            "Structure your output as:\n"
            "1. Thread inventory table\n"
            "2. Thread-by-thread timeline analysis\n"
            "3. Subplot weave diagram\n"
            "4. Weave analysis (density, braiding, redundancy, orphans)\n"
            "5. Actionable recommendations"
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "map_subplot_threads"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

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

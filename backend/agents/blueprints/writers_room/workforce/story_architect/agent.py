from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.writers_room.workforce.base import WritersRoomCreativeBlueprint
from agents.blueprints.writers_room.workforce.story_architect.commands import (
    develop_concept,
    fix_structure,
    generate_concepts,
    map_subplot_threads,
    outline_act_structure,
    write_structure,
)

logger = logging.getLogger(__name__)


class StoryArchitectBlueprint(WritersRoomCreativeBlueprint):
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
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return (
            "You are a Story Architect in a professional writers room. You build the "
            "structural backbone of stories — beats, acts, turning points, causal chains.\n\n"
            "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
            "Your output is SCENES, not frameworks. Every structural element you propose must be "
            "a concrete scene where a specific character does a specific thing that causes a "
            "specific consequence.\n\n"
            'WRONG: "Act I break: the inciting incident disrupts the protagonist\'s equilibrium."\n'
            "RIGHT: \"Act I break: Jakob signs the side agreement in Felix's office. Felix is on "
            "a call in the next room. Jakob puts the pen down, folds the document, and leaves "
            'before Felix hangs up."\n\n'
            'WRONG: "Midpoint reversal: the protagonist discovers the true stakes."\n'
            'RIGHT: "Ep 4: Selin finds the Bürgschaft document in the Bezirksamt archive. The '
            "liability number is three times what parliament approved. She photographs it, puts "
            'the file back, and does not tell Marta."\n\n'
            "If you cannot describe a structural beat as a scene with characters, actions, and "
            'consequences, the beat does not exist yet. Do not submit it. Write "UNDEVELOPED" '
            "and move on.\n\n"
            "Show observable actions, not abstract psychology. Replace 'he felt betrayed' with "
            "'he closed the folder and walked out.' Internal states must be externalized through "
            "behavior, dialogue, or physical detail.\n\n"
            "## FORMAT DISCIPLINE\n\n"
            "You are a STRUCTURAL agent. You output beat sheets, not prose. Each scene gets "
            "EXACTLY the four answers (who/why/changes/next) — one sentence each. No atmosphere, "
            "no interior decoration, no coffee descriptions, no novelistic prose. That is the "
            "Dialog Writer's and Lead Writer's job.\n\n"
            "WRONG (too verbose):\n"
            '"Kessler steht in seiner Küche und macht Kaffee. French Press, fair-trade, '
            'handgemahlen. Er lebt allein. Die Wohnung ist ordentlich..."\n'
            "RIGHT (structural):\n"
            '"Kessler prepares his speech for the Green party conference, positioning himself '
            'as the anti-Brenner candidate."\n\n'
            "Each scene: 4 lines max (WHO/WHY/CHANGES/NEXT). Save the prose for the writers.\n\n"
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
            "## Pre-Writing Bible Consultation\n"
            "If a Story Bible is provided in context, check before writing any scene:\n"
            "(1) Are all characters consistent with bible key decisions?\n"
            "(2) Do relationships match?\n"
            "(3) Does the setting respect world rules?\n"
            "(4) Does the timeline fit?\n"
            "Do not invent facts that contradict [ESTABLISHED] items. "
            "You may freely develop [TBD] items.\n\n"
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
        # On revision rounds, use base class which respects the step_plan's
        # targeted improvement instructions instead of the full creative suffix.
        if task.step_plan and "REVISION ROUND" in task.step_plan:
            return super().execute_task(agent, task)

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
            "## CRITICAL: Pitch hierarchy and causal rigor\n\n"
            "1. **Respect the creator's hierarchy.** The pitch defines what is CENTRAL and what "
            "is a SIDE ARC / SUBPLOT. Do not promote subplots to the dramatic center. If the "
            "creator says 'the story of three brothers', the brothers are the center — not the "
            "bureaucracy, not the institution, not the market.\n\n"
            "2. **Distinguish creator-stated vs. your inference.** When you extract elements "
            "from the pitch, clearly separate what the creator explicitly wrote from what you "
            "are inferring or extrapolating. Never label your own inferences as 'binding' — "
            "only the creator's explicit words are binding.\n\n"
            "3. **Causal chains must be mechanistically plausible.** When you construct plot "
            "mechanics — especially financial, legal, or institutional chains — you must explain "
            "the ACTUAL MECHANISM. 'X undermines Y because both tap the same funding source' is "
            "a claim that needs a concrete explanation: WHICH funding source? WHY can't both "
            "coexist? WHAT is the specific mechanism of interference? If you cannot explain the "
            "mechanism in concrete terms, you are producing a buzzword, not a plot point. Every "
            "causal link in a chain reaction must survive the question 'but WHY does A cause B, "
            "specifically?'\n\n"
            "4. **Your recommendations are strong suggestions, not binding directives.** Only the "
            "creator's pitch is binding. Frame your structural choices as reasoned recommendations "
            "with rationale, not as mandates.\n\n"
            "5. **Character motivations must match the pitch's moral register.** If the creator "
            "describes characters as selfish, corrupt, or power-driven, do not soften them into "
            "'well-meaning people who accidentally cause harm'. Preserve the creator's moral "
            "characterization.\n\n"
            "## STAGE-SPECIFIC SCOPE (CRITICAL — DO NOT EXCEED)\n\n"
            "**At pitch stage:**\n"
            "- Logline (one sentence)\n"
            "- Dramatic premise (one paragraph: who are these people, what do they want, "
            "why does it collide)\n"
            "- The causal chain that drives the story (the domino sequence, 5-8 steps max)\n"
            "- The ending (one paragraph: what happens, who loses, what's the final image)\n"
            "- TOTAL LENGTH: 2-4 pages MAX. This is a pitch, not a treatment.\n"
            "- DO NOT write per-episode breakdowns. DO NOT write scene-by-scene beats.\n"
            "- Show the ENGINE and the DESTINATION. The episodes come later.\n\n"
            "**At expose stage:**\n"
            "- World and setting (1 page)\n"
            "- Character ensemble with key decisions (1-2 pages)\n"
            "- Season arc: beginning, middle, end with major turning points (2-3 pages)\n"
            "- Episode overview: one paragraph per episode, not scene-by-scene\n\n"
            "**At treatment/concept stage:**\n"
            "- Full structural roadmap with act breaks\n"
            "- Per-episode beat sheets (this is where scene-by-scene detail belongs)\n"
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

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "write_structure"),
            max_tokens=32768,
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

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
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

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
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

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
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
            "## CRITICAL: Honor the Pitch\n"
            "Read the project goal carefully. If the creator has provided SPECIFIC elements — "
            "characters, conflicts, settings, real-world inspirations, side arcs, references, "
            "tone direction, target platform — these are CREATIVE DIRECTIVES, not suggestions.\n\n"
            "- PRESERVE every specific element the creator mentioned\n"
            "- BUILD ON their vision — add depth, texture, structural intelligence\n"
            "- NEVER replace their central conflict with a generic one\n"
            "- NEVER reduce their specific characters to stock archetypes\n"
            "- Each concept should be a different EXECUTION of the creator's vision, "
            "not a different vision entirely\n"
            "- Vary structure, format approach, tonal emphasis, and narrative strategy — "
            "NOT the core premise the creator gave you\n\n"
            "If the project goal is vague (e.g. 'write me a blockbuster'), THEN and ONLY THEN "
            "use the market research to identify underserved opportunities and pitch into "
            "genuinely diverse creative directions.\n\n"
            "## ANTI-DERIVATIVE RULE\n"
            "When the creator references existing shows (e.g. 'like Succession', 'Industry-style'), "
            "these are TONAL and QUALITY references — not plot templates.\n"
            "- DO NOT copy the referenced show's plot structure, character archetypes, or premise\n"
            "- DO capture the referenced show's ambition, complexity, and audience sophistication\n"
            "- The creator is saying 'this is the league I'm playing in', not 'clone this'\n"
            "- Build something ORIGINAL that would air alongside those shows, not imitate them\n\n"
            "## Character Naming (Prestige TV / Literary)\n"
            "- Names must be realistic for the setting and milieu\n"
            "- NEVER use project codenames, working titles, or joke names as character names\n"
            "- For German-language projects: use authentic German names appropriate to the "
            "social class, region, and era of the characters\n"
            "- For projects inspired by real people: create DISTINCT fictional names that avoid "
            "lawsuit risk while capturing the milieu (e.g. different initials, different etymology, "
            "but same cultural register)\n\n"
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
            "Each concept should feel like it could ONLY come from THIS creator's pitch. "
            "If a concept could have been generated without reading the project goal, it's wrong."
        )

        suffix += self._get_voice_constraint(agent)

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
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
            "## CRITICAL: Fidelity to the Creator's Vision\n"
            "The project goal and merged concept contain the creator's specific intent. "
            "Your job is to DEVELOP their vision with structural intelligence, not to "
            "replace it with something more generic or 'safe'.\n"
            "- Preserve every character, conflict, arc, and reference the creator specified\n"
            "- Add structural depth and dramatic texture — don't subtract specificity\n"
            "- If the creator named specific real-world inspirations, build the fictional "
            "world to reflect those dynamics authentically\n"
            "- The central conflict the creator described IS the central conflict — don't "
            "substitute a more conventional one\n"
            "- If the creator described brothers, don't turn them into a patriarch's children. "
            "If they described a specific power dynamic, don't replace it with a different one "
            "from a reference show. The STRUCTURE of their characters is sacred.\n\n"
            "## Character Naming\n"
            "- All character names must be realistic for the setting's milieu and social class\n"
            "- NEVER use project codenames or working titles as character names\n"
            "- For projects inspired by real people: create distinct fictional names that "
            "capture the same cultural register without legal risk\n\n"
            "## Anti-Derivative Rule\n"
            "Referenced shows are quality benchmarks, not plot templates. Build something "
            "original that stands alongside them, don't clone their structure.\n\n"
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

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=self.get_model(agent, "develop_concept"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.writers_room.workforce.base import WritersRoomCreativeBlueprint
from agents.blueprints.writers_room.workforce.lead_writer.commands import (
    write_concept,
    write_expose,
    write_first_draft,
    write_pitch,
    write_treatment,
)

logger = logging.getLogger(__name__)

# ── Industry-standard format specifications per stage ────────────────────────
#
# These define the STRUCTURE of each deliverable — what sections, what order,
# what formatting. Injected alongside CRAFT_DIRECTIVES so the lead writer
# knows both WHAT to write and HOW to structure it. Also shared with the
# creative_reviewer for format compliance scoring.

FORMAT_SPECS = {
    "write_pitch": (
        "## DOCUMENT FORMAT — PITCH\n\n"
        "The pitch is 2-4 pages of flowing prose. The text must stand on its own — "
        "no heavy decoration, but the formatting signals professionalism and care.\n\n"
        "### Required Structure (in this order)\n\n"
        "1. **Title Block** — Working title, author name, format (Series/Film/Novel/Play/etc.), "
        "genre. Clean, minimal. No logos or graphics.\n\n"
        "2. **Logline** — Formatted as a standalone quote/epigraph at the top of the document, "
        "set apart from the body text:\n"
        "   ```\n"
        '   > "A protagonist defined by contradiction faces an inciting incident,\n'
        '   > triggering a central conflict with devastating stakes."\n'
        "   ```\n"
        "   One sentence, maximum two. Under 50 words. The protagonist is defined by their "
        "contradiction (want vs. need), NOT by name. The logline is the first thing the reader "
        "sees after the title — it must hook instantly.\n\n"
        "3. **Opening Image** — The very first paragraph after the logline drops the reader "
        "into a concrete scene. Not description — action. A character doing something in a "
        "specific place. This is the proof that you can write.\n\n"
        "4. **The World** — One paragraph that grounds the setting through a specific, evocative "
        "detail that simultaneously conveys tone. The detail must be particular to THIS story — "
        "not a generic establishing shot.\n\n"
        "5. **The Story** — The A-story told in compressed, present-tense prose. Every sentence "
        "answers 'what happens?' For series: the pilot story PLUS the engine that generates "
        "future episodes. For standalone: beginning through climax (withhold the resolution — "
        "leave the reader wanting).\n\n"
        "6. **The Characters** — 2-4 sentences per major character, introduced through their "
        "defining contradiction, not biography. Each character earns their mention through "
        "their role in the central conflict.\n\n"
        "7. **The Stakes** — The final paragraph. What the protagonist loses if they fail, "
        "and why that loss is devastating. This is the last thing the reader sits with.\n\n"
        "### Formatting Notes\n"
        "- No mandatory section headers in the body — flowing prose with natural paragraph "
        "breaks is the correct register for a pitch\n"
        "- The logline stands alone as a blockquote/epigraph, visually separated\n"
        "- Use an em-dash (—) for parenthetical asides, not brackets or parentheses\n"
        "- One line break between paragraphs, no indentation\n"
        "- If a sentence can be cut without losing information, cut it\n\n"
        "### What Does NOT Belong\n"
        "Subplots. Episode guides. Production budgets. Platform targets. Thematic essays. "
        "Character backstory beyond what serves the pitch. Meta-commentary about the project. "
        "Section titles like 'Theme' or 'Target Audience'.\n"
    ),
    "write_expose": (
        "## DOCUMENT FORMAT — EXPOSÉ\n\n"
        "The exposé is 5-12 pages. Unlike the pitch, it uses markdown headers — these "
        "signal structure to the reader and enable surgical revision in later rounds.\n\n"
        "### Required Sections (in this order)\n\n"
        "**Title + Logline** — Title block followed by the logline as blockquote (same format "
        "as the pitch). Below it, 2-3 sentences expanding the premise.\n\n"
        "**## Premise** — The dramatic situation expanded: who, where, when, what's at stake, "
        "what makes this world unique. Written as narrative prose, not a list. ~0.5 page.\n\n"
        "**## Characters** — Each major character through their ARC, not their biography: "
        "starting state → want → need → transformation → endpoint. Write each as a short "
        "narrative paragraph, not a bullet list. For series: where they are at season start "
        "and season end. 1-2 pages.\n\n"
        "**## Story** — Three-movement architecture told as flowing narrative. Mark five "
        "turning points — not as labels, but woven into the prose with enough emphasis that "
        "the reader can't miss them:\n"
        "  - Inciting Incident\n"
        "  - Act I Break (point of no return)\n"
        "  - Midpoint (the story redefines itself)\n"
        "  - All Is Lost (lowest point)\n"
        "  - Climax\n"
        "For series: the Season 1 arc told in full. 2-4 pages. The ending IS revealed — "
        "unlike the pitch, the exposé proves you can land the plane.\n\n"
        "**## Tone & Style** — How the story feels. Not a list of adjectives — a paragraph "
        "whose own prose demonstrates the tone. Name 2-3 comparable works as quality register "
        "touchstones (not plot sources). ~0.5 page.\n\n"
        "**## Themes** — The thematic argument visible in the arc of events, not stated "
        "didactically. 'The show argues that...' is wrong. 'When Victor chooses the foundation "
        "over the board seat, the show's position crystallizes' is right. ~0.5 page.\n\n"
        "### Series Addendum (append if format=series)\n\n"
        "**## Story Engine** — The renewable conflict mechanism in one sentence, followed by "
        "a paragraph demonstrating how it generates varied episodes. This is the single most "
        "important paragraph in a series exposé.\n\n"
        "**## Season Arc** — Season-level inciting incident, midpoint, climax. How A-story "
        "and B-story interweave. 0.5-1 page.\n\n"
        "**## Future Seasons** — Where seasons 2-3+ take the characters and story. Not "
        "detailed episode guides — proof of longevity. 0.5 page.\n\n"
        "### Formatting Notes\n"
        "- Markdown `##` headers for each section — mandatory\n"
        "- Present tense throughout\n"
        "- Em-dash for parenthetical asides\n"
        "- Characters introduced with their name in **bold** on first mention\n"
        "- Turning points in the Story section emphasized with **bold** or set as their own "
        "short paragraph\n\n"
        "### What Does NOT Belong\n"
        "Episode-by-episode breakdowns (that's the concept/bible). Dialogue. Camera directions. "
        "Production notes. Platform targets.\n"
    ),
    "write_treatment": (
        "## DOCUMENT FORMAT — TREATMENT\n\n"
        "The treatment is 15-40 pages. The full story told scene-by-scene in prose. "
        "A director or producer reads this and knows the film/play/book.\n\n"
        "### Required Structure\n\n"
        "**Title + Logline** — Title block followed by the logline as blockquote.\n\n"
        "**The Story** — Scene-by-scene, present tense, third person. Structured with "
        "named markdown headers for major narrative beats — NOT generic labels like "
        "'Act I', but story-specific names that convey content:\n"
        "  - `## The Auction` not `## Act I, Scene 3`\n"
        "  - `## The Night of the Broadcast` not `## Midpoint`\n"
        "  - `## What the Ledger Shows` not `## The Revelation`\n\n"
        "At minimum, the treatment must contain sections covering:\n"
        "  - The Opening / Setup / Inciting Incident\n"
        "  - Rising Action / Progressive Complications\n"
        "  - The Midpoint Reversal\n"
        "  - The Crisis\n"
        "  - The Climax\n"
        "  - The Resolution / New Equilibrium\n\n"
        "Each section header is a `##` markdown header. Sub-beats within a section may "
        "use `###` if needed, but avoid over-nesting.\n\n"
        "### Formatting Notes\n"
        "- Present tense, third person throughout\n"
        "- No dialogue — describe what characters discuss using indirect speech and subtext. "
        "'She tells him the deal is off. He says nothing, pours another drink.' NOT: "
        "'She says: \"The deal is off.\"'\n"
        "- Characters introduced with their name in **bold** on first mention\n"
        "- Scene breaks within a section: use a centered `---` horizontal rule\n"
        "- Sensory details and atmosphere are not decoration — they carry tone\n"
        "- The prose voice must match the genre: a comedy treatment reads with wit, "
        "a thriller with tension, a drama with gravity\n\n"
        "### What Does NOT Belong\n"
        "Dialogue in direct speech. Camera directions. Technical language. Thematic essays "
        "between scenes. Author commentary.\n"
    ),
    "write_concept": (
        "## DOCUMENT FORMAT — SERIES CONCEPT / BIBLE\n\n"
        "The series concept is 12-25 pages. The master reference document that everyone "
        "working on the show reads.\n\n"
        "### Required Sections (in this order)\n\n"
        "**Title Block** — Title, author, format (e.g., 'Prestige Drama Series · 8 Episodes · "
        "50 Minutes'), genre.\n\n"
        "**Logline** — As blockquote/epigraph, same format as the pitch.\n\n"
        "**## Creator's Statement** — Why this story needs to exist. Written in first person "
        "from the creator's perspective (derived from the project goal). Personal, passionate, "
        "specific. Not a thematic essay — a declaration. 0.5 page.\n\n"
        "**## Story Engine** — The renewable conflict mechanism. One sentence in **bold**, "
        "followed by a paragraph demonstrating how it generates varied episodes. This is the "
        "most important paragraph in the document — it answers 'why is this a series and not "
        "a film?' Place it prominently, early. 0.5 page.\n\n"
        "**## Tone & Style** — 3-5 tonal pillars enacted in the prose, not listed. Name "
        "reference touchstones with specificity: not 'like Breaking Bad' but 'Breaking Bad's "
        "patience with silence, its willingness to let a scene breathe past the point of "
        "comfort.' 0.5-1 page.\n\n"
        "**## World Rules** — What the audience needs to know about this world that differs "
        "from ours. Social codes, hierarchies, power structures, unwritten rules. For "
        "speculative fiction: magic systems, technology, politics. Written as discoverable "
        "narrative, not an encyclopedia entry. 0.5-1 page.\n\n"
        "**## Characters** — The ensemble as a WEB of relationships, not isolated profiles. "
        "Alliances, rivalries, dependencies, romantic tensions. Each character embodies a "
        "different approach to the series' thematic question. Backstory presented as unexploded "
        "ordnance — past events that create present-tense conflict. For each character:\n"
        "  - Name in **bold** as sub-header (`### Character Name`)\n"
        "  - 1-2 paragraphs: who they are through what they DO, not psychological profile\n"
        "  - Their relationship to at least one other character, stated as a concrete dynamic\n"
        "  2-4 pages total.\n\n"
        "**## Saga Arc** — The multi-season journey. Where does the protagonist begin and "
        "end across the entire run? Series-level inciting incident, midpoint, climax. How "
        "the thematic argument deepens across seasons. 0.5-1 page.\n\n"
        "**## Season One** — Season-level inciting incident, midpoint, climax. How A-story "
        "and B-story interweave. Character arcs for the season. 1-2 pages.\n\n"
        "**## Episode Guide** — Each episode as a sub-section (`### Episode 1: [Title]`). "
        "1-3 paragraphs per episode. Each must show:\n"
        "  - VARIETY: different facets, character combinations, tonal registers\n"
        "  - THROUGHLINE: season arc progresses in every episode\n"
        "  - The engine at work: each overview makes the story engine visible\n"
        "  3-6 pages total.\n\n"
        "**## Future Seasons** — 1-2 paragraphs per future season showing where characters "
        "and story go. Proves the series has a destination, not endless repetition. 0.5-1 page.\n\n"
        "### Formatting Notes\n"
        "- Markdown `##` for major sections, `###` for character names and episode titles\n"
        "- The Story Engine sentence in **bold**\n"
        "- Characters introduced with **bold** name on first mention throughout\n"
        "- Episode titles should be evocative, not generic ('The Groundbreaking' not 'Episode 3')\n"
        "- Use `---` horizontal rules between major sections for visual breathing room\n\n"
        "### What Does NOT Belong\n"
        "Full scene-by-scene breakdowns (that's the treatment). Dialogue. Camera directions. "
        "Casting suggestions. Budget estimates. Platform targets.\n"
    ),
    "write_first_draft": (
        "## DOCUMENT FORMAT — FIRST DRAFT\n\n"
        "The first draft is the actual work in its intended medium's native format. "
        "Format depends entirely on medium.\n\n"
        "### Screenplay (Film or TV Pilot)\n"
        "- Standard screenplay format: Courier 12pt, standard margins\n"
        "- Scene headings (sluglines): `INT./EXT. LOCATION - TIME` in ALL CAPS\n"
        "- Six elements only: Scene Heading, Action, Character Name, Parenthetical, "
        "Dialogue, Transition\n"
        "- Action lines: present tense, visual, minimal — only what camera sees and "
        "microphone hears\n"
        "- Character names CAPITALIZED on first appearance in action lines\n"
        "- 1 page ≈ 1 minute of screen time\n"
        "- Feature film: 90-120 pages. TV pilot: 30-60 pages depending on format\n"
        "- NO markdown headers — use native screenplay format\n\n"
        "### Novel / Prose Manuscript\n"
        "- Chapter headers: `## Chapter 1: [Title]`\n"
        "- 12pt serif font implied (Times New Roman equivalent)\n"
        "- Establish and maintain point of view consistently\n"
        "- Narrative voice — rhythm, vocabulary, sensibility — present even if imperfect\n"
        "- Deliberate scene vs. summary choices\n"
        "- Use the medium's superpower: interior life, thoughts, memory, sensory experience\n"
        "- Target word count per genre (literary fiction: 70-100k, thriller: 80-100k, "
        "YA: 50-80k)\n\n"
        "### Stage Play\n"
        "- Act and scene headers: `## Act I, Scene 1`\n"
        "- Character names in ALL CAPS flush left\n"
        "- Dialogue single-spaced below character name\n"
        "- Stage directions in italics and parentheses, minimal and essential\n"
        "- Embrace theatrical constraints: limited locations, no quick cuts\n"
        "- Read every line aloud — theatre is heard\n\n"
        "### Audio Drama / Podcast Script\n"
        "- Scene headers with location and atmosphere notes\n"
        "- SFX: and MUSIC: cues on their own lines, CAPITALIZED\n"
        "- NARRATOR: sections for non-dialogue narration\n"
        "- Character names CAPITALIZED before each dialogue block\n"
        "- Sound design notes in brackets: [footsteps on gravel, door creaks]\n\n"
        "### Universal Rules (all media)\n"
        "- Every scene dramatizes conflict\n"
        "- Characters speak in distinct voices — cover the name and you should still "
        "know who's talking\n"
        "- Exposition woven into conflict, never dumped\n"
        "- Enter scenes late, leave early\n"
        "- The first draft must be COMPLETE, not perfect — get it down\n"
    ),
}

# ── Stage-specific craft directives ──────────────────────────────────────────

CRAFT_DIRECTIVES = {
    "write_pitch": (
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "A pitch is not an essay about a series. A pitch is the story told in compressed "
        "form. Every sentence must answer: WHAT HAPPENS?\n\n"
        'WRONG: "Der dramatische Mechanismus funktioniert wie folgt: Ein Bezirksstadtrat '
        "blockiert ein Immobilienprojekt der Brenner-Brüder — nicht aus Überzeugung, sondern "
        'weil die Ablehnung ihm politisches Kapital verschafft."\n'
        'RIGHT: "Ratzmann liest den Antrag, macht eine Notiz auf ein Post-it, klebt es auf '
        "einen Stapel außerhalb der Akte. Er trinkt Kaffee. Am nächsten Montag steht er auf "
        "einer Bürgerversammlung in Friedrichshain und sagt: 'Wir haben den Antrag abgelehnt.' "
        'Er hat ihn nie gelesen."\n\n'
        "The test for every paragraph: Could a director shoot this? Could an actor play this? "
        "If the answer is no, you are writing an essay, not a pitch.\n\n"
        "FORBIDDEN PHRASES:\n"
        '- "Der dramatische Mechanismus funktioniert wie folgt"\n'
        '- "Das ist der Motor dieser Serie"\n'
        '- "Die zentrale Dynamik besteht in"\n'
        '- "Der erneuerbare Konflikt"\n'
        "- Any sentence that describes the story's mechanics instead of telling the story\n\n"
        "CAUSAL CHAIN RULE: If you claim A causes B, you must show A causing B in a scene. "
        '"Die Bürgschaftskettenreaktion" is not a scene. Jakob signing a document while Felix '
        "is in the next room IS a scene.\n\n"
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
        "## Document Structure\n"
        "The pitch is short (2-3 pages). Write as flowing prose with no mandatory sections. "
        "Natural paragraph breaks are sufficient.\n\n"
        "## Pitfalls to Avoid\n"
        "- Abstract thematic language ('a story about love and loss') instead of concrete specifics\n"
        "- Name-dropping characters before the reader has reason to care — use sharp descriptors first\n"
        "- Including subplots — the pitch has room for the A-story only\n"
        "- Tone mismatch — flat corporate prose for a wild, anarchic story\n"
        "- Describing the ending in full — pitch documents should leave the reader wanting resolution\n"
    ),
    "write_expose": (
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "Every paragraph must contain concrete dramatic action. Characters do things. Things "
        "have consequences. If you claim A causes B, show the scene where A causes B.\n\n"
        "The test for every paragraph: Could a director shoot this? Could an actor play this? "
        "If the answer is no, rewrite it as a scene.\n\n"
        "FORBIDDEN: Sentences that describe mechanics instead of telling the story. "
        '"The funding structure collapses" is not a scene. "Marta opens the file and sees '
        'the number" IS a scene.\n\n'
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
        "## Document Structure\n"
        "Structure the expose with markdown headers for major narrative movements. Use at minimum:\n"
        "- `## Premise` — logline and hook\n"
        "- `## Characters` — the ensemble with arcs\n"
        "- `## Story Arc` — three-movement architecture with turning points\n"
        "- `## Themes` — thematic argument\n"
        "Additional headers as needed. These headers enable surgical revision in later rounds.\n\n"
        "## Pitfalls to Avoid\n"
        "- Withholding the ending out of misplaced suspense\n"
        "- Subplot overload — room for A-story and one B-story at most\n"
        "- Character as catalog — listing traits instead of showing how traits create conflict\n"
        "- Losing chronological clarity\n"
        "- Underdeveloped antagonism\n"
    ),
    "write_treatment": (
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "Every paragraph must contain concrete dramatic action. Characters do things. Things "
        "have consequences. If you claim A causes B, show the scene where A causes B.\n\n"
        "The test for every paragraph: Could a director shoot this? Could an actor play this? "
        "If the answer is no, rewrite it as a scene.\n\n"
        "FORBIDDEN: Sentences that describe mechanics instead of telling the story. "
        '"The funding structure collapses" is not a scene. "Marta opens the file and sees '
        'the number" IS a scene.\n\n'
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
        "## Document Structure\n"
        "Structure the treatment with markdown headers for major beats and sequences. Use named sections like:\n"
        "- `## The Opening` — setup and inciting incident\n"
        "- `## The Rising Action` — progressive complications\n"
        "- `## The Midpoint Reversal` — the shift that redefines the story\n"
        "- `## The Crisis` — stakes at their highest\n"
        "- `## The Climax` — the final confrontation\n"
        "- `## The Resolution` — new equilibrium\n"
        "Name sections to match the story's actual content, not generic labels. "
        "These headers enable surgical revision in later rounds.\n\n"
        "## Pitfalls to Avoid\n"
        "- Writing dialogue — the treatment is not a scriptment\n"
        "- Scene-by-scene monotony ('Then... Next... Then...')\n"
        "- Neglecting Act II — the progressive complications must build\n"
        "- Including camera directions or technical language\n"
        "- Forgetting tone — letting the prose go flat\n"
    ),
    "write_concept": (
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "Every paragraph must contain concrete dramatic action. Characters do things. Things "
        "have consequences. If you claim A causes B, show the scene where A causes B.\n\n"
        "The test for every paragraph: Could a director shoot this? Could an actor play this? "
        "If the answer is no, rewrite it as a scene.\n\n"
        "FORBIDDEN: Sentences that describe mechanics instead of telling the story. "
        '"The funding structure collapses" is not a scene. "Marta opens the file and sees '
        'the number" IS a scene.\n\n'
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
        "## Document Structure\n"
        "Structure the concept with markdown headers for each bible component:\n"
        "- `## Story Engine` — the renewable conflict mechanism\n"
        "- `## Tone & Style` — tonal pillars and reference touchstones\n"
        "- `## World Rules` — what makes this world distinct\n"
        "- `## Characters` — the ensemble web\n"
        "- `## Saga Arc` — the multi-season journey\n"
        "- `## Season One` — the first season arc\n"
        "- `## Episode 1: [Title]`, `## Episode 2: [Title]`, etc. — per-episode overviews\n"
        "- `## Future Seasons` — where seasons 2+ go\n"
        "These headers enable surgical revision in later rounds.\n\n"
        "## Pitfalls to Avoid\n"
        "- No clear engine — the single most common failure\n"
        "- Character catalogs without dynamics\n"
        "- Vague thematic statements ('explores identity')\n"
        "- Episode overviews that are all the same shape\n"
        "- Neglecting sustainability — proving Season 1 is necessary but not sufficient\n"
        "- Over-building world at the expense of character and story\n"
    ),
    "write_first_draft": (
        "## ACTION-FIRST MANDATE (OVERRIDES ALL OTHER INSTRUCTIONS)\n\n"
        "Every paragraph must contain concrete dramatic action. Characters do things. Things "
        "have consequences. If you claim A causes B, show the scene where A causes B.\n\n"
        "The test for every paragraph: Could a director shoot this? Could an actor play this? "
        "If the answer is no, rewrite it as a scene.\n\n"
        "FORBIDDEN: Sentences that describe mechanics instead of telling the story. "
        '"The funding structure collapses" is not a scene. "Marta opens the file and sees '
        'the number" IS a scene.\n\n'
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
        "## Document Structure\n"
        "Structure depends on medium:\n"
        "- SCREENPLAY: Use standard screenplay format. Scenes are identified by sluglines "
        "(INT./EXT. LOCATION - TIME). Do NOT add markdown headers — use native format.\n"
        "- NOVEL/PROSE: Use chapter headers (`## Chapter 1: [Title]`).\n"
        "- STAGE PLAY: Use act and scene headers (`## Act I, Scene 1`).\n"
        "These structural markers enable surgical revision in later rounds.\n\n"
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
    "Use the creative agents' fragments (structure, ensemble, voice work, research) as INPUT, "
    "but the CREATOR'S ORIGINAL PITCH in <project_goal> is your primary authority. If an agent's "
    "output drifts from the pitch — softens the moral register, promotes a subplot to the center, "
    "adds causal claims without concrete mechanisms, or introduces elements the creator never "
    "mentioned — discard the drift. Go back to the pitch.\n\n"
    "Do NOT invent new characters, conflicts, world elements, or plot points. Your job is "
    "synthesis and prose craft, not ideation. If you find gaps, flag them — do not fill them "
    "with your own inventions.\n\n"
    "## Voice Fidelity\n"
    "Your prose voice must match the CREATOR'S voice from the pitch, not a generic literary "
    "register. Read the pitch text carefully: its sentence rhythm, vocabulary, directness, and "
    "attitude ARE the target voice. If the creator writes short, blunt, cynical sentences — "
    "you write short, blunt, cynical sentences. Do not 'elevate' their voice into Feuilleton "
    "prose. Do not write longer, more elaborate, more literary sentences than the creator does. "
    "The creator's pitch is the voice benchmark. Match it.\n\n"
    "## Moral Register\n"
    "If the creator describes characters as corrupt, selfish, cynical, or power-hungry — write "
    "them that way. Do NOT soften them into 'people who believe they are doing the right thing' "
    "or 'well-meaning actors who accidentally cause harm.' The creator chose their moral register "
    "deliberately. Preserve it.\n\n"
    "## Causal Claims\n"
    "If you describe a causal chain (A causes B), you must explain the actual mechanism in "
    "concrete terms. 'The funding sources overlap' is not an explanation. WHICH funding source? "
    "WHY can't both projects coexist? HOW does one interfere with the other? If you cannot "
    "explain the mechanism, cut the claim.\n\n"
    "## Platform / Distribution\n"
    "Do NOT include specific platform targets (e.g., 'developed for Sky Deutschland') in the "
    "deliverable. The pitch deck goes to many parties. The creator decides pitch strategy.\n\n"
    "FIDELITY CHECK (before submitting): Re-read the creator's pitch in <project_goal>. "
    "Does your output preserve EVERY specific element they provided? Does it preserve their "
    "TONE and MORAL REGISTER? If you introduced anything the creator did NOT mention, delete it. "
    "If you softened their characters, harden them back.\n"
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
    "SELF-REFERENTIAL PROSE — THE WORST AI TELL (ZERO TOLERANCE):\n"
    "NEVER write a sentence that explains what the previous sentence does, means, or "
    "achieves. NEVER comment on your own craft. NEVER tell the reader how to interpret "
    "an image, gesture, or moment. Examples of what to NEVER write:\n"
    '- "Das ist zwölf Jahre in einem Satz." (author applauding their own metaphor)\n'
    '- "Das ist der Motor dieser Serie." (explaining what the scene just showed)\n'
    '- "Das ist nicht Unaufmerksamkeit." (telling the reader what they already understood)\n'
    '- "Das ist das Gefährlichste an ihr." (evaluating your own character for the reader)\n'
    "If a gesture, image, or moment works — it works WITHOUT you explaining it. If it "
    "doesn't work without explanation, the gesture is too weak. Fix the gesture, don't "
    "add commentary. Trust the reader. Trust the image. Shut up after the image lands.\n\n"
    "NO META-COMMENTARY IN THE DELIVERABLE:\n"
    "The deliverable is a creative document, not a process log. NEVER include:\n"
    "- Preambles listing what the creator said vs. what you inferred\n"
    "- [Revision: ...] annotations explaining what you changed and why\n"
    "- Sections titled 'Vorbemerkung', 'Pitch-Extraktion', or 'Revisionsnachweis'\n"
    "- Self-referential positioning ('Was dieses Tonmuster zeigt: ...')\n"
    "The deliverable speaks for itself. No footnotes. No process artifacts.\n\n"
    "INSTEAD:\n"
    "- Write messy, specific, surprising details over clean generic ones\n"
    "- Vary sentence length dramatically — a 3-word sentence after a 30-word one\n"
    "- Use the voice profile from the Story Researcher as your north star\n"
    "- End on the image. Not on the explanation of the image.\n"
)


class LeadWriterBlueprint(WritersRoomCreativeBlueprint):
    """Lead writer gets deliverable + full critique + voice profile.

    Inherits WritersRoomCreativeBlueprint's filtered context (no research notes,
    no sibling reports) but overrides critique filtering to keep the full critique
    — the lead writer needs all analyst feedback for revisions.
    """

    default_model = "claude-opus-4-6"
    source_privileged = True  # sees important + minor sources
    # Lead writer sees all analyst feedback + creative agents' research output
    _skip_critique_filter = True
    _include_research = True
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
            "\n## Continuity Protocol\n"
            "Before synthesizing creative team output into a deliverable: list every character "
            "mentioned in the creative team's output. Cross-reference each against the Story Bible "
            "(if provided in context). Flag any contradiction before writing. Resolve contradictions "
            "in favor of the bible — it is canon.\n\n"
            "## Action-First Sharpening\n"
            "Show observable actions, not abstract psychology. Replace 'Jakob felt betrayed' with "
            "'Jakob closed the folder and walked out.' Replace 'She was nervous' with 'She checked "
            "her phone three times in a minute.' Internal states must be externalized through "
            "behavior, dialogue, or physical detail.\n\n"
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
        # No voice profile available — derive voice from the pitch itself
        return (
            "\n\n## VOICE CONSTRAINT (no voice profile available)\n"
            "No formal voice profile has been created yet. Derive your writing voice "
            "DIRECTLY from the creator's pitch text in <project_goal>. Study the pitch's "
            "sentence length, rhythm, vocabulary, directness, and attitude. Write in THAT "
            "voice — not in a more literary, more elaborate, or more polished register. "
            "The creator's raw pitch voice is the target. Match it, do not 'improve' it.\n"
        )

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        """Route to the appropriate craft directive based on command name."""
        command_name = task.command_name or "write_pitch"
        craft = CRAFT_DIRECTIVES.get(command_name, CRAFT_DIRECTIVES["write_pitch"])
        format_spec = FORMAT_SPECS.get(command_name, FORMAT_SPECS["write_pitch"])
        return self._execute_write(agent, task, craft, format_spec)

    def _execute_write(self, agent: Agent, task: AgentTask, craft_directive: str, format_spec: str) -> str:
        """Execute a writing task with the given craft and format directives."""
        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            f"{format_spec}\n\n"
            f"{craft_directive}"
            f"{INTEGRATION_MANDATE}"
            f"\nYour output must be in {locale}. This is non-negotiable."
        )

        suffix += self._get_voice_constraint(agent)

        cache_context, task_msg = self.build_task_message(agent, task, suffix=suffix)
        model = self.get_model(agent, task.command_name or "write_pitch")
        max_tokens = self._get_max_tokens(task.command_name)

        from agents.ai.claude_client import call_claude

        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            cache_context=cache_context,
            model=model,
            max_tokens=max_tokens,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _get_max_tokens(self, command_name: str | None) -> int:
        """Return max_tokens based on expected output length per stage."""
        return {
            "write_pitch": 16384,
            "write_expose": 16384,
            "write_treatment": 32768,
            "write_concept": 32768,
            "write_first_draft": 65536,
        }.get(command_name or "write_pitch", 16384)

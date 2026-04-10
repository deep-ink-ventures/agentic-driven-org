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

logger = logging.getLogger(__name__)


class StoryResearcherBlueprint(WorkforceBlueprint):
    name = "Story Researcher"
    slug = "story_researcher"
    description = "Researches market trends, comps, platform appetites, audience demographics, and cultural zeitgeist to inform creative decisions"
    tags = ["writers-room", "research", "market", "comps", "zeitgeist"]
    skills = [
        {
            "name": "Lived-Detail Extraction",
            "description": "Researches the sensory, social, and emotional texture of a setting — what people ate, complained about, took for granted.",
        },
        {
            "name": "World-Building Consistency Check",
            "description": "Maintains an internal logic ledger for fictional worlds. Catches rule violations.",
        },
        {
            "name": "Cultural Sensitivity Audit",
            "description": "Evaluates portrayals of cultures and identities for accuracy, nuance, and potential harm.",
        },
        {
            "name": "Expert Knowledge Scaffolding",
            "description": "Translates domain expertise into character-appropriate dialogue and behavior.",
        },
        {
            "name": "Anachronism Detection",
            "description": "Cross-references language, technology, and social norms against the story's time period.",
        },
    ]
    outputs = ["document"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return (
            "You are a Story Researcher in a professional writers room. You research market "
            "trends, comparable titles, platform appetites, audience demographics, and cultural "
            "zeitgeist. Your research directly informs creative decisions.\n\n"
            "You are format-agnostic: you work on screenplays, novels, theatre, series, film, "
            "short stories, podcasts, games, or any narrative format. Adapt your research lens "
            "to the format and medium.\n\n"
            "## Research Methodology\n"
            "- Comparable titles: identify 3-7 comps across medium, genre, tone, and theme. "
            "Analyze what worked, what didn't, and why.\n"
            "- Market positioning: where does this project sit in the current landscape? "
            "What's oversaturated, what's underserved?\n"
            "- Platform/publisher appetite: what are buyers, streamers, publishers, or "
            "producers actively looking for right now?\n"
            "- Audience demographics: who is the primary audience? Secondary? "
            "What are their consumption patterns?\n"
            "- Cultural zeitgeist: what conversations, movements, or anxieties does this "
            "project tap into? Timeliness matters.\n"
            "- Format requirements: page counts, episode lengths, act structures, "
            "word counts expected by the target market.\n\n"
            "## Output Format\n"
            "Structure your research as a brief with clear sections. Use markdown. "
            "Be specific -- name titles, cite trends, quote data where possible. "
            "Every finding must connect back to actionable creative guidance.\n\n"
            "Do NOT produce meta-analysis of narrative frameworks. Your job is facts: market data, "
            "comparable titles, legal research, world-building details. Do not analyze the story's "
            "structure — that is the Story Architect's job. Do not evaluate character consistency — "
            "that is the Character Analyst's job. Stay in your lane.\n\n"
            "Voice profiles must be DIRECTIVES, not descriptions. Write instructions that a "
            "writer can follow mechanically. Each directive is one line. Include example phrases "
            "in the original language.\n\n"
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

    research = research
    revise_research = revise_research
    profile_voice = profile_voice
    research_setting = research_setting
    fact_check_narrative = fact_check_narrative

    def execute_task(self, agent: Agent, task: AgentTask) -> str:
        if task.command_name == "revise_research":
            return self._execute_revise_research(agent, task)
        if task.command_name == "profile_voice":
            return self._execute_profile_voice(agent, task)
        if task.command_name == "research_setting":
            return self._execute_research_setting(agent, task)
        if task.command_name == "fact_check_narrative":
            return self._execute_fact_check(agent, task)
        return self._execute_research(agent, task)

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

    def _execute_research(self, agent: Agent, task: AgentTask) -> str:
        """Conduct initial market research based on project material and goal."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "# RESEARCH BRIEF — Full Market & Creative Analysis\n\n"
            "Produce a comprehensive research brief using the methodology below. "
            "Every section must contain SPECIFIC examples — no generic statements.\n\n"
            "## Section 1: Comparable Titles (3-7 comps)\n"
            "For EACH comp, provide:\n"
            "- **Title** (year, format, platform/publisher)\n"
            "- **Why it's a comp** — which specific element connects to our project (theme, tone, setting, structure, audience)\n"
            "- **What worked** — the creative/commercial decision that made it successful\n"
            "- **What didn't** — where it lost audience, critical reception, or commercial momentum\n"
            "- **Lesson for us** — one specific, actionable takeaway\n\n"
            "Include comps across: (a) same genre/tone, (b) same setting/milieu, (c) same structural ambition, "
            "(d) same target audience. At least one comp should be a CAUTIONARY tale — a project that tried similar and failed.\n\n"
            "## Section 2: Market Positioning Map\n"
            "- **Landscape** — what's currently oversaturated in this genre/format? What's underserved?\n"
            "- **White space** — where is the opening? Why hasn't someone filled it?\n"
            "- **Positioning statement** — one sentence: 'This project is [X] for people who loved [Y] but wanted [Z]'\n"
            "- **Differentiation** — the 2-3 elements that make this project uncopyable\n\n"
            "## Section 3: Platform/Publisher Appetite\n"
            "- **Tier 1 targets** — which specific platforms/publishers/studios are buying this type of content RIGHT NOW?\n"
            "- **Recent acquisitions** — name 2-3 recent deals in adjacent space with deal terms if known\n"
            "- **Buyer psychology** — what's the pitch meeting framing that gets a 'yes'?\n"
            "- **Red flags** — what would make a buyer pass despite liking the concept?\n\n"
            "## Section 4: Audience Profile\n"
            "- **Primary audience** — demographics, psychographics, consumption habits\n"
            "- **Secondary audience** — who else watches/reads this and why?\n"
            "- **Discovery path** — how does this audience FIND new content? (algorithms, critics, word of mouth, social)\n"
            "- **Retention drivers** — what keeps them watching/reading past episode 3 / chapter 5?\n\n"
            "## Section 5: Cultural Zeitgeist\n"
            "- **Current conversations** — what societal anxieties, debates, or movements does this project speak to?\n"
            "- **Timeliness window** — is this a 'now or never' concept, or evergreen?\n"
            "- **Cultural risk** — what could make this project feel tone-deaf or dated by release?\n\n"
            "## Section 6: Format & Structure Requirements\n"
            "- **Industry standard** — expected length, episode count, page count for this format/platform\n"
            "- **Structural conventions** — what audiences expect from this genre's structure\n"
            "- **Innovation opportunity** — where can we break convention and get rewarded for it?\n\n"
            "## Section 7: Creative Implications (MOST IMPORTANT)\n"
            "Synthesize all research into 5-10 specific creative directives for the writing team. Each must be:\n"
            "- Grounded in a finding from sections 1-6\n"
            "- Specific enough to act on (not 'make it compelling' but 'the pilot must establish the power hierarchy in scene 1')\n"
            "- Framed as 'DO this' not 'consider this'\n\n"
            "Be concrete. Name names. Cite specifics. Vague research is useless research."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "research"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_revise_research(self, agent: Agent, task: AgentTask) -> str:
        """Revise research based on Market Analyst feedback flags."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "The Market Analyst has reviewed your research and flagged issues. "
            "The flags and suggestions are included in the task plan above.\n\n"
            "For each flag:\n"
            "1. Acknowledge the specific concern\n"
            "2. Address it with updated research, corrected analysis, or additional data\n"
            "3. Explain what changed and why\n\n"
            "Produce an UPDATED research brief. Preserve all sections that were not flagged. "
            "Clearly mark revised sections with a note on what changed. "
            "The output should be a complete, standalone research brief -- not a diff."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "revise_research"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_profile_voice(self, agent: Agent, task: AgentTask) -> str:
        """Analyze source material and produce a structured voice profile."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        voice_system = (
            self.system_prompt + "\n\n"
            "VOICE DNA ANALYSIS — DIRECTIVE OUTPUT:\n"
            "You are producing a VOICE DNA profile — not vague descriptions, but OPERATIONAL "
            "DIRECTIVES that a writer can follow mechanically to reproduce this voice.\n\n"
            "The author's voice is SACRED. Structure, plot, characters can be radically changed — "
            "but the writing style, rhythm, humor, tone must be preserved. The original author "
            "should read output written in their voice and think: 'that's me — the best version of me.'\n\n"
            "RULES FOR VOICE DNA:\n"
            "1. Every pattern claim MUST be backed by 2-3 EXACT QUOTES from the source material.\n"
            "2. Not paraphrases. Not summaries. EXACT quotes, in quotation marks.\n"
            "3. Be surgical: 'average sentence length ~8 words' not 'short sentences'.\n"
            "4. The WHAT THIS VOICE IS NOT section is as important as what it IS.\n"
            "5. The VOICE COMMANDMENTS must be DIRECTIVES — instructions a writer follows "
            "mechanically. 'When writing dialogue, never exceed 15 words per line' not "
            "'the dialogue tends to be brief'.\n"
            "6. If humor is absent, say so explicitly — do not invent humor patterns.\n"
            "7. If dialogue is absent from the source, note that and skip the dialogue section.\n"
            "8. Voice profiles are DIRECTIVES, not descriptions. Write instructions: "
            "'Short declarative sentences. Never apologize.' not "
            "'The speech patterns are characterized by directness.'"
        )

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Analyze the uploaded source material and produce a VOICE DNA profile. "
            "This profile will be used as an INVIOLABLE constraint by all creative agents "
            "in the writers room. Every word they write must sound like it came from this "
            "author's pen.\n\n"
            "Structure your output EXACTLY as follows:\n\n"
            "## VOICE DNA -- [Title/Author]\n\n"
            "### Signature Patterns\n"
            "[2-3 sentences describing the overall voice]\n\n"
            "### Sentence Rhythm\n"
            "Pattern: [description]\n"
            "Examples from source:\n"
            '- "[exact quote from source material]"\n'
            '- "[exact quote]"\n'
            '- "[exact quote]"\n\n'
            "### Vocabulary & Register\n"
            "Pattern: [description]\n"
            "Examples:\n"
            '- "[exact quote showing vocabulary choice]"\n'
            '- "[exact quote]"\n\n'
            "### Humor & Wit\n"
            "Pattern: [description -- or 'None/absent' if serious tone]\n"
            "Examples:\n"
            '- "[exact quote showing humor delivery]"\n\n'
            "### Dialogue Voice\n"
            "Pattern: [description]\n"
            "Examples:\n"
            '- "[exact dialogue exchange from source]"\n'
            '- "[exact dialogue exchange]"\n\n'
            "### Emotional Temperature\n"
            "Pattern: [description]\n"
            "Examples:\n"
            '- "[exact quote showing how emotion is conveyed]"\n\n'
            "### Distinctive Tics\n"
            "- [recurring motif, phrase, structural habit with example]\n"
            "- [another]\n\n"
            "### WHAT THIS VOICE IS NOT\n"
            "- NOT [specific anti-pattern with example of what would violate it]\n"
            "- NOT [another]\n"
            "- NOT [another]\n\n"
            "### VOICE COMMANDMENTS (for creative agents)\n"
            "1. [specific rule derived from the above, e.g., 'Never use more than 15 words "
            "in a dialogue line -- this author writes in fragments']\n"
            "2. [another]\n"
            "3. [another]\n"
            "4. [another]\n"
            "5. [another]\n\n"
            "CRITICAL: Extract REAL examples from the source text. Not made-up examples. "
            "Actual quotes. Every pattern claim must have evidence."
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=voice_system,
            user_message=task_msg,
            model=self.get_model(agent, "profile_voice"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        # Store the voice profile as a Document on the department
        try:
            from projects.models import Document

            dept = agent.department
            if dept:
                Document.objects.update_or_create(
                    department=dept,
                    title="Voice Profile",
                    defaults={
                        "content": response,
                        "doc_type": "voice_profile",
                    },
                )
                logger.info("Stored voice profile as Document on department %s", dept.id)
        except Exception:
            logger.exception("Failed to store voice profile as Document")

        return response

    def _execute_research_setting(self, agent: Agent, task: AgentTask) -> str:
        """Deep-dive research into the project's world, setting, and real-world context."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "# WORLD & SETTING RESEARCH — Deep Authenticity Dive\n\n"
            "Research the project's world in depth. Your goal: give the writing team enough "
            "real-world texture that every scene SMELLS like the actual place and time.\n\n"
            "## Section 1: Geography & Physical World\n"
            "- **Specific locations** — real neighborhoods, streets, buildings, landmarks that matter\n"
            "- **Sensory texture** — what does this world look, sound, smell like? Season-specific details\n"
            "- **Movement patterns** — how do people get around? What's the commute? Where do they eat, drink, meet?\n"
            "- **Status markers** — what signals wealth, power, belonging in this milieu? (addresses, cars, clothes, schools)\n\n"
            "## Section 2: Power Structures & Institutions\n"
            "- **Formal power** — government, corporations, institutions and how they actually operate (not how they claim to)\n"
            "- **Informal power** — who really decides things? Backdoor channels, old-boy networks, favor economies\n"
            "- **Money flow** — how is wealth created, moved, hidden in this world? Follow the money.\n"
            "- **Legal grey zones** — what's technically illegal but everyone does? What's the enforcement reality?\n\n"
            "## Section 3: Social Dynamics & Hierarchies\n"
            "- **Class markers** — how do insiders distinguish each other? Language, behavior, knowledge\n"
            "- **Entry barriers** — how does someone break into this world? What are the initiation rituals?\n"
            "- **Insider language** — jargon, euphemisms, code words specific to this milieu\n"
            "- **Taboos & unwritten rules** — what can't you say/do? What gets you expelled?\n\n"
            "## Section 4: Historical Context & Real Events\n"
            "- **Key events** — real historical moments that shaped this world (scandals, crashes, reforms)\n"
            "- **Timeline** — chronology of relevant real events that can inspire plot points\n"
            "- **Real figures** — public figures whose stories parallel or inspire characters (for fictionalization)\n"
            "- **Ongoing tensions** — unresolved conflicts, pending changes, ticking clocks in this world\n\n"
            "## Section 5: Cultural Texture\n"
            "- **Media consumption** — what do people in this world read, watch, listen to?\n"
            "- **Social rituals** — parties, meetings, negotiations — how do they actually happen?\n"
            "- **Humor & irony** — what's funny to insiders? What's the self-image vs. reality gap?\n"
            "- **Generational splits** — how do old guard vs. new arrivals differ in values, methods, style?\n\n"
            "## Section 6: Creative Implications\n"
            "Synthesize into specific guidance for the writing team:\n"
            "- 5-10 scene-ready details that would make a draft feel authentic\n"
            "- 3-5 conflict opportunities rooted in real tensions\n"
            "- Character archetypes that ACTUALLY exist in this world (not stereotypes)\n"
            "- Dialogue texture — how people in this world actually talk\n\n"
            "Be SPECIFIC. Name real places, real events, real dynamics. "
            "Generic 'research' like 'Berlin is a diverse city' is worthless."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "research_setting"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_fact_check(self, agent: Agent, task: AgentTask) -> str:
        """Verify factual claims, timelines, and technical details in a manuscript."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "# FACT CHECK — Narrative Verification Report\n\n"
            "Review the manuscript material and verify all factual claims. "
            "This is NOT a creative review — it's a forensic accuracy check.\n\n"
            "## Methodology\n"
            "For each claim, categorize and verify:\n\n"
            "### Category 1: Historical Claims\n"
            "- Dates, events, sequences — did this happen when/how described?\n"
            "- Historical figures — are referenced actions/quotes accurate?\n"
            "- Period details — technology, fashion, language appropriate to the era?\n\n"
            "### Category 2: Technical/Professional Claims\n"
            "- Industry processes — does the described procedure actually work this way?\n"
            "- Legal/financial mechanics — are contracts, deals, regulations described correctly?\n"
            "- Professional behavior — would someone in this role actually do/say this?\n\n"
            "### Category 3: Geographic/Cultural Claims\n"
            "- Locations — do described places exist? Are distances, travel times realistic?\n"
            "- Cultural practices — are customs, social dynamics, language patterns accurate?\n"
            "- Local knowledge — would a local recognize this as authentic or as an outsider's guess?\n\n"
            "### Category 4: Internal Consistency\n"
            "- Timeline — do events within the narrative follow a consistent chronology?\n"
            "- Character knowledge — does a character know something they shouldn't yet?\n"
            "- Established rules — does the narrative contradict its own earlier claims?\n\n"
            "## Output Format\n"
            "For EACH finding:\n"
            "- **Claim**: [exact quote or paraphrase from manuscript]\n"
            "- **Category**: [Historical / Technical / Geographic / Internal]\n"
            "- **Verdict**: ✅ Accurate | ⚠️ Partially accurate | ❌ Inaccurate | ❓ Unverifiable\n"
            "- **Evidence**: [what the actual fact is, with source if possible]\n"
            "- **Impact**: [how important is this — would a knowledgeable reader notice?]\n"
            "- **Fix suggestion**: [specific correction if needed]\n\n"
            "End with a **Summary** section: overall accuracy assessment, "
            "most critical fixes needed, and areas where additional research is recommended."
        )

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "fact_check_narrative"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

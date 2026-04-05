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
from agents.blueprints.writers_room.workforce.character_designer.skills import format_skills

logger = logging.getLogger(__name__)


class CharacterDesignerBlueprint(WorkforceBlueprint):
    name = "Character Designer"
    slug = "character_designer"
    description = "Designs and develops character ensembles -- profiles, arcs, relationships, and voice"
    tags = ["writers-room", "character", "ensemble", "arcs", "voice"]
    config_schema = {
        "locale": {
            "type": "str",
            "required": False,
            "label": "Output Language",
            "description": "ISO locale for all creative output (e.g. 'en', 'de', 'fr'). Defaults to 'en'.",
        },
    }

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
            "## Format Awareness\n"
            "You work with ANY format: screenplay, novel, theatre, series, film, short story. "
            "Character depth scales with the medium -- a film protagonist needs different "
            "treatment than a series ensemble lead or a novel's first-person narrator.\n\n"
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

    @property
    def skills_description(self) -> str:
        return format_skills()

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
        return self._execute_write_characters(agent, task)

    def _execute_write_characters(self, agent: Agent, task: AgentTask) -> str:
        """Design the character ensemble based on stage, material, and structure."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "Design the character ensemble for this project at its current stage. "
            "The task plan above specifies the stage, provides the project material, "
            "story structure (from the Story Architect), and research brief "
            "(from the Story Researcher).\n\n"
            "Your output must include (depth scales with stage):\n\n"
            "**Character Profiles** -- for each character:\n"
            "- Name and role in the ensemble\n"
            "- Want (external goal driving the plot)\n"
            "- Need (internal truth they must learn)\n"
            "- Wound (past damage shaping their worldview)\n"
            "- Arc (transformation trajectory: positive/negative/flat/disillusionment)\n"
            "- Defining trait and contradiction\n"
            "- Fear and blind spot\n\n"
            "**Relationship Map:**\n"
            "- Key relationships with power dynamics\n"
            "- Alliances, rivalries, dependencies\n"
            "- How relationships evolve across the arc\n\n"
            "**Voice Profiles** (at treatment stage and beyond):\n"
            "- Speech patterns and vocabulary level\n"
            "- Sentence rhythm (short/clipped vs. flowing/verbose)\n"
            "- Verbal tics, pet phrases, what they avoid saying\n"
            "- How their voice changes under pressure\n\n"
            "**Motivation Maps** (at step_outline and beyond):\n"
            "- Scene-by-scene character goals\n"
            "- What each character wants in each scene and what prevents it\n\n"
            "Scale depth to the stage. At logline, focus only on the protagonist. "
            "At first_draft, deliver the full toolkit."
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

    def _execute_fix_characters(self, agent: Agent, task: AgentTask) -> str:
        """Revise characters based on Character Analyst feedback flags."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "The Character Analyst has reviewed your character work and flagged issues. "
            "The flags are included in the task plan above.\n\n"
            "Character Analyst flags cover:\n"
            "- Want vs. Need clarity and tension\n"
            "- Action plausibility (would this character really do this?)\n"
            "- Consistency drift across scenes\n"
            "- Relationship arc progression\n"
            "- Secondary character function and distinctiveness\n"
            "- Knowledge tracking errors (character knows something they shouldn't)\n\n"
            "For each flag:\n"
            "1. Acknowledge the specific concern\n"
            "2. Explain your character reasoning for the revision\n"
            "3. Rewrite the affected character elements\n\n"
            "Preserve all character elements that were not flagged. Produce a complete, "
            "standalone character document -- not a diff. Annotate what changed and why "
            "at the top of the document."
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

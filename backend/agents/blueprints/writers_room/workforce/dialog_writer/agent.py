from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent, AgentTask

from agents.blueprints.base import WorkforceBlueprint
from agents.blueprints.writers_room.workforce.dialog_writer.commands import (
    fix_content,
    rewrite_for_subtext,
    write_content,
    write_scene_dialogue,
)
from agents.blueprints.writers_room.workforce.dialog_writer.skills import format_skills

logger = logging.getLogger(__name__)


class DialogWriterBlueprint(WorkforceBlueprint):
    name = "Dialog Writer"
    slug = "dialog_writer"
    description = "Writes the actual content -- dialogue, prose, scenes -- for every stage and format"
    tags = ["writers-room", "dialog", "writing", "content", "scenes", "prose"]
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
            "You are a Dialog Writer in a professional writers room. You write the actual "
            "content -- the words on the page. Every line serves character, story, or both. "
            "Subtext over text. Each character sounds distinct. Genre tone is sacred. "
            "Show, don't tell.\n\n"
            "## Writing Principles\n"
            "- **Subtext**: what characters mean is rarely what they say. The gap between "
            "surface and truth is where drama lives.\n"
            "- **Voice Differentiation**: cover the character names and you should still "
            "know who is speaking. Vocabulary, rhythm, syntax, and silence are all tools.\n"
            "- **Exposition**: never have characters tell each other things they both know. "
            "Exposition is earned through conflict, not convenience.\n"
            "- **Scene Craft**: every scene enters late and exits early. Every scene has a "
            "turn. If nothing changes, the scene doesn't exist.\n"
            "- **Genre Tone**: comedy has different sentence rhythms than thriller. "
            "Horror uses different silences than romance. Respect the genre contract.\n"
            "- **Show, Don't Tell**: action reveals character. Behavior over description. "
            "Specific over general. Concrete over abstract.\n"
            "- **Rhythm**: vary sentence length. Short sentences punch. Longer sentences "
            "build tension, carry emotion, and create the rolling momentum that pulls "
            "a reader forward. Then stop.\n\n"
            "## Format Mastery\n"
            "You handle ANY format and adapt your craft accordingly:\n"
            "- **Screenplay**: proper format (slug lines, action lines, dialogue blocks). "
            "No unfilmables. No camera direction unless you're also the director. "
            "Action lines are lean, visual, present tense.\n"
            "- **Novel/Prose**: narrative voice, interiority, sensory detail, "
            "paragraph rhythm, chapter pacing.\n"
            "- **Theatre**: stage directions that serve actors, dialogue that fills a space, "
            "the architecture of a scene that plays live.\n"
            "- **Teleplay/Series**: cold opens, act breaks for commercials, episode rhythm, "
            "the balance between standalone and serialized.\n\n"
            "## Stage-Adaptive Output\n"
            "- **Logline**: craft a single sentence that sells -- protagonist, goal, "
            "obstacle, stakes, tone.\n"
            "- **Expose**: write the full expose narrative -- the pitch document that "
            "makes someone want to read the whole thing.\n"
            "- **Treatment**: write the full treatment -- present tense, visual, "
            "emotionally engaging. This is the movie on paper.\n"
            "- **Step Outline**: write scene-by-scene with dialogue snippets that "
            "establish voice and key moments.\n"
            "- **First Draft**: write the FULL draft. Complete dialogue, complete scenes, "
            "complete narrative. This is the real thing.\n"
            "- **Revised Draft**: polish pass. Tighten dialogue, sharpen scenes, "
            "deepen subtext, fix pacing.\n\n"
            "## Collaboration\n"
            "You build on the work of your colleagues:\n"
            "- Story Researcher provides market context and audience expectations\n"
            "- Story Architect provides the structural backbone -- beats, acts, turns\n"
            "- Character Designer provides character profiles, voice guides, "
            "and relationship dynamics\n"
            "Your job is to bring all of it to life on the page.\n\n"
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

    write_content = write_content
    fix_content = fix_content
    write_scene_dialogue = write_scene_dialogue
    rewrite_for_subtext = rewrite_for_subtext

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
        if task.command_name == "fix_content":
            return self._execute_fix_content(agent, task)
        if task.command_name == "write_scene_dialogue":
            return self._execute_write_scene_dialogue(agent, task)
        if task.command_name == "rewrite_for_subtext":
            return self._execute_rewrite_for_subtext(agent, task)
        return self._execute_write_content(agent, task)

    def _execute_write_content(self, agent: Agent, task: AgentTask) -> str:
        """Write the actual content for the current stage."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "You are the primary writing agent. Write the actual content for this project "
            "at its current stage. The task plan above specifies the stage and provides:\n"
            "- The project goal and material\n"
            "- The story structure (from Story Architect)\n"
            "- The character ensemble (from Character Designer)\n"
            "- The research brief (from Story Researcher)\n\n"
            "Your output depends on the stage:\n\n"
            "**Logline:** Craft a single compelling sentence. It must contain the protagonist, "
            "their goal, the central obstacle, and the stakes. It must convey tone and genre. "
            "It must make someone want to know what happens next.\n\n"
            "**Expose:** Write the full expose document. Present tense. Engaging narrative voice. "
            "Cover the world, the characters, the central conflict, the thematic argument, "
            "and the emotional trajectory. This is the document that sells the project.\n\n"
            "**Treatment:** Write the full treatment narrative. Present tense, visual, "
            "emotionally specific. Every major scene is here. Key dialogue moments are sketched. "
            "The reader should feel like they've watched the movie or read the book.\n\n"
            "**Step Outline:** Write scene-by-scene. Each scene has a heading, the characters "
            "present, the dramatic purpose, and 2-4 lines of key dialogue that establish voice "
            "and capture the essential moments.\n\n"
            "**First Draft:** Write the FULL draft. Complete scenes. Complete dialogue. "
            "Complete action/prose. This is not a summary -- this is the actual content. "
            "Follow the structure from the Story Architect. Honor the voices from the "
            "Character Designer. Respect the format conventions.\n\n"
            "**Revised Draft:** Polish pass over the existing draft. Tighten dialogue -- "
            "cut every word that doesn't earn its place. Sharpen scenes -- enter later, "
            "exit earlier. Deepen subtext. Fix pacing issues. This should read as a "
            "significant quality improvement over the first draft.\n\n"
            "Write the actual content now. Not notes about content. Not a plan. The content itself."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "write_content"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

    def _execute_fix_content(self, agent: Agent, task: AgentTask) -> str:
        """Rewrite content based on Dialogue Analyst and Format Analyst feedback."""
        from agents.ai.claude_client import call_claude

        locale = agent.get_config_value("locale") or "en"

        suffix = (
            f"OUTPUT LANGUAGE: {locale}\n\n"
            "The Dialogue Analyst and/or Format Analyst have reviewed your content "
            "and flagged issues. The flags are included in the task plan above.\n\n"
            "Dialogue Analyst flags cover:\n"
            "- Voice differentiation (characters sounding too similar)\n"
            "- On-the-nose dialogue (saying what they mean instead of subtext)\n"
            "- Exposition dumps (characters telling each other things they know)\n"
            "- Rhythm issues (monotonous sentence patterns, no variation)\n"
            "- Scene endings (weak buttons, missed opportunities)\n\n"
            "Format Analyst flags cover:\n"
            "- Unfilmables (describing what can't be shown on screen)\n"
            "- Camera direction in spec scripts\n"
            "- Action line craft (too long, too vague, not visual)\n"
            "- Slug line formatting\n"
            "- Page count / word count issues\n"
            "- Format convention violations\n\n"
            "For each flag:\n"
            "1. Acknowledge the specific concern\n"
            "2. Rewrite the affected passage, scene, or dialogue\n"
            "3. Briefly note what changed and why\n\n"
            "Preserve everything that works. Produce the complete, rewritten content -- "
            "not a diff, not notes, but the actual revised scenes and dialogue. "
            "Annotate a brief change log at the top of the document."
        )

        suffix += self._get_voice_constraint(agent)

        task_msg = self.build_task_message(agent, task, suffix=suffix)
        response, usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=task_msg,
            model=self.get_model(agent, "fix_content"),
            max_tokens=16384,
        )
        task.token_usage = usage
        task.save(update_fields=["token_usage"])

        return response

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.ai.claude_client import call_claude, parse_json_response
from agents.blueprints.base import (
    EXCELLENCE_THRESHOLD,
    MAX_POLISH_ATTEMPTS,
    MAX_REVIEW_ROUNDS,
    NEAR_EXCELLENCE_THRESHOLD,
    LeaderBlueprint,
)
from agents.blueprints.writers_room.leader.commands import check_progress, plan_room
from projects.models import Document

logger = logging.getLogger(__name__)

# ── Stage pipeline ──────────────────────────────────────────────────────────

STAGES = ["ideation", "concept", "logline", "expose", "treatment", "step_outline", "first_draft", "revised_draft"]

# ── Depth matrix: which FEEDBACK agents run at which stage ──────────────────

FEEDBACK_MATRIX: dict[str, list[tuple[str, str]]] = {
    "ideation": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "concept": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("character_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "logline": [
        ("market_analyst", "full"),
        ("production_analyst", "lite"),
    ],
    "expose": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "treatment": [
        ("market_analyst", "full"),
        ("structure_analyst", "full"),
        ("character_analyst", "lite"),
        ("production_analyst", "full"),
    ],
    "step_outline": [
        ("market_analyst", "lite"),
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("production_analyst", "full"),
    ],
    "first_draft": [
        ("market_analyst", "lite"),
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("production_analyst", "full"),
    ],
    "revised_draft": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("format_analyst", "full"),
        ("production_analyst", "lite"),
    ],
}

# ── Creative matrix: which CREATIVE agents write at which stage ─────────────

CREATIVE_MATRIX: dict[str, list[str]] = {
    "ideation": ["story_researcher", "story_architect"],
    "concept": ["story_researcher", "story_architect", "character_designer"],
    "logline": ["story_researcher", "dialog_writer"],
    "expose": ["story_researcher", "story_architect", "dialog_writer"],
    "treatment": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "step_outline": ["story_architect", "character_designer", "dialog_writer"],
    "first_draft": ["story_architect", "character_designer", "dialog_writer"],
    "revised_draft": ["story_architect", "character_designer", "dialog_writer"],
}

# ── Flag routing: which creative agent fixes which feedback ─────────────────

FLAG_ROUTING: dict[str, str] = {
    "market_analyst": "story_researcher",
    "structure_analyst": "story_architect",
    "character_analyst": "character_designer",
    "dialogue_analyst": "dialog_writer",
    # format_analyst and production_analyst are context-dependent — resolved in code
}


class WritersRoomLeaderBlueprint(LeaderBlueprint):
    name = "Writers Room Showrunner"
    slug = "leader"
    description = "Writers Room showrunner — orchestrates creative/feedback ping-pong loop across stages from logline to revised draft"
    tags = ["leadership", "writers-room", "orchestration", "screenplay", "novel", "creative-writing"]
    config_schema = {}

    @property
    def system_prompt(self) -> str:
        return """You are the Showrunner of a professional writers room. You orchestrate a creative team and a feedback team in a disciplined ping-pong loop.

CREATIVE TEAM (they write):
- story_researcher: market research, comps, positioning
- story_architect: story structure, beats, act breaks
- character_designer: character arcs, relationships, voices
- dialog_writer: actual content writing, dialogue, scenes

FEEDBACK TEAM (they analyze — mirrors professional script coverage):
- market_analyst: market fit, comps, platform alignment, zeitgeist
- structure_analyst: framework-based structural analysis (Save the Cat, McKee, etc.)
- character_analyst: character consistency, arcs, motivation, relationships
- dialogue_analyst: voice, subtext, scene construction, exposition
- format_analyst: craft conventions, formatting, pacing
- production_analyst: budget, cast-ability, feasibility, IP potential

THE LOOP:
1. Assign creative agents to write content for current stage
2. When writing is done, assign feedback agents to analyze (per depth matrix)
3. Feedback is scored 1-10 per dimension. Overall score = minimum dimension.
4. Excellence threshold: 9.5/10. Below that → route specific flags to creative agents for fixes.
5. After reaching 9.0, max 3 polish attempts to reach 9.5, then accept (diminishing returns).
6. Creative agent rewrites addressing specific flags → feedback agents re-analyze
7. When score meets threshold → advance to next stage
8. Repeat until target stage is reached with passing scores

DEPTH MATRIX (which feedback agents at which stage):
- logline: market_analyst(full), production_analyst(lite)
- expose: market_analyst(full), structure_analyst(lite), production_analyst(lite)
- treatment: market_analyst(full), structure_analyst(full), character_analyst(lite), production_analyst(full)
- step_outline: market_analyst(lite), structure_analyst(full), character_analyst(full), production_analyst(full)
- first_draft: market_analyst(lite), structure_analyst(full), character_analyst(full), dialogue_analyst(full), production_analyst(full)
- revised_draft: structure_analyst(full), character_analyst(full), dialogue_analyst(full), format_analyst(full), production_analyst(lite)

STAGE PIPELINE: logline \u2192 expose \u2192 treatment \u2192 step_outline \u2192 first_draft \u2192 revised_draft

FLAG ROUTING (which creative agent fixes which feedback):
- market_analyst flags \u2192 story_researcher
- structure_analyst flags \u2192 story_architect
- character_analyst flags \u2192 character_designer
- dialogue_analyst flags \u2192 dialog_writer
- format_analyst flags \u2192 story_architect (structural) or dialog_writer (craft/dialogue)
- production_analyst flags \u2192 relevant creative agent based on flag content

LOCALE: All agents output in the configured locale. This is non-negotiable."""

    # ── Register commands ────────────────────────────────────────────────
    plan_room = plan_room
    check_progress = check_progress

    # ── Review pairs (universal pattern) ───────────────────────────────

    def get_review_pairs(self):
        all_creators = set()
        for agents in CREATIVE_MATRIX.values():
            all_creators.update(agents)

        fix_commands = {
            "story_researcher": "research",
            "story_architect": "write",
            "character_designer": "write",
            "dialog_writer": "write",
        }

        return [
            {
                "creator": creator,
                "creator_fix_command": fix_commands.get(creator, "write"),
                "reviewer": "creative_reviewer",
                "reviewer_command": "review-creative",
                "dimensions": [
                    "concept_fidelity",
                    "originality",
                    "market_fit",
                    "structure",
                    "character",
                    "dialogue",
                    "craft",
                    "feasibility",
                ],
            }
            for creator in sorted(all_creators)
        ]

    def _propose_review_chain(self, agent, creator_task, workforce_types):
        """Override: writers room does NOT do direct creator->reviewer chains.

        Instead, feedback agents analyze first, then creative_reviewer consolidates.
        The state machine handles this via feedback_in_progress -> _propose_review_task.
        """
        return None

    # ── Task execution (uses base class delegation with stage context) ──

    def _get_delegation_context(self, agent):
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_stage = internal_state.get("current_stage", STAGES[0])
        return (
            f"# Current Stage: {current_stage}\n"
            f"# Stage Status: {json.dumps(stage_status, indent=2)}\n"
            f"# Quality: Excellence threshold {EXCELLENCE_THRESHOLD}/10 (minimum dimension score)"
        )

    # ── Task proposal (called by beat/continuous mode) ───────────────────

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """
        Core orchestration: determine what needs to happen next in the
        ping-pong loop and propose the appropriate task(s).
        """
        from agents.models import AgentTask

        # Gate on running sprints — no sprints, no work
        from projects.models import Sprint

        running_sprints = Sprint.objects.filter(
            departments=agent.department,
            status=Sprint.Status.RUNNING,
        )
        if not running_sprints.exists():
            return None

        # Use the least recently touched sprint for context
        sprint = running_sprints.order_by("updated_at").first()

        def _tag_sprint(result):
            """Tag proposal with sprint ID for task creation."""
            if result and isinstance(result, dict):
                result["_sprint_id"] = str(sprint.id)
            return result

        internal_state = agent.internal_state or {}
        config = _get_merged_config(agent)
        target_stage = config.get("target_stage", "revised_draft")

        # Initialize stage state if needed
        current_stage = internal_state.get("current_stage")
        if not current_stage:
            # First invocation — run entry detection
            if not internal_state.get("entry_detected"):
                detected_stage = _run_entry_detection(agent)
                # Re-read internal_state since _run_entry_detection saved it
                internal_state = agent.internal_state or {}
            else:
                detected_stage = STAGES[0]

            current_stage = detected_stage
            internal_state["current_stage"] = current_stage
            internal_state["stage_status"] = {}
            internal_state["current_iteration"] = 0
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(current_stage, {})

        # Safety check: if we've completed target stage, we're done
        if current_info.get("status") == "passed":
            next_stage = _next_stage(current_stage)
            if not next_stage or STAGES.index(current_stage) >= STAGES.index(target_stage):
                logger.info("Writers Room: target stage '%s' reached with passing scores — done", target_stage)
                return None
            # Advance to next stage
            current_stage = next_stage
            internal_state["current_stage"] = current_stage
            internal_state["current_iteration"] = 0
            current_info = stage_status.get(current_stage, {})
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

        # Check for active tasks in the department
        active_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                status__in=[
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.QUEUED,
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.AWAITING_APPROVAL,
                    AgentTask.Status.AWAITING_DEPENDENCIES,
                    AgentTask.Status.PLANNED,
                ],
            ).values_list("exec_summary", "status", "agent__agent_type", "agent__name")
        )
        if active_tasks:
            # Work is in progress — don't propose new tasks
            return None

        status = current_info.get("status", "not_started")
        iteration = current_info.get("iterations", 0)

        # Safety cap — uses universal MAX_REVIEW_ROUNDS
        if iteration >= MAX_REVIEW_ROUNDS:
            logger.warning(
                "Writers Room: stage '%s' hit max iterations (%d) — escalating",
                current_stage,
                MAX_REVIEW_ROUNDS,
            )
            return _tag_sprint(
                {
                    "exec_summary": f"ESCALATION: Stage '{current_stage}' reached {MAX_REVIEW_ROUNDS} iterations without passing",
                    "tasks": [
                        {
                            "target_agent_type": "leader",
                            "exec_summary": f"Stage '{current_stage}' has iterated {MAX_REVIEW_ROUNDS} times without passing quality gates. Review feedback history and decide next steps.",
                            "step_plan": "Review the feedback history for this stage. Determine if the quality threshold should be adjusted, the approach needs to change, or human intervention is needed.",
                        }
                    ],
                }
            )

        # Check for review cycle triggers first (universal from base class)
        review_result = self._check_review_trigger(agent)
        if review_result:
            return _tag_sprint(review_result)

        # ── State machine ───────────────────────────────────────────────

        if status == "not_started":
            # Step 1: Assign creative agents to write
            return _tag_sprint(self._propose_creative_tasks(agent, current_stage, config))

        if status == "writing_in_progress":
            # All creative tasks completed (no active tasks remain) -> advance
            logger.info("Writers Room: stage '%s' writing complete — advancing to feedback", current_stage)
            stage_status[current_stage]["status"] = "writing_done"
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return _tag_sprint(self._propose_feedback_tasks(agent, current_stage, config))

        if status == "writing_done":
            # Step 3: Assign feedback agents to analyze
            return _tag_sprint(self._propose_feedback_tasks(agent, current_stage, config))

        if status == "feedback_in_progress":
            # All feedback tasks completed -> dispatch creative_reviewer to consolidate
            logger.info("Writers Room: stage '%s' feedback complete — dispatching review", current_stage)
            stage_status[current_stage]["status"] = "feedback_done"
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return _tag_sprint(self._propose_review_task(agent, current_stage, config))

        if status == "feedback_done":
            # Dispatch creative_reviewer to consolidate analyst feedback
            return _tag_sprint(self._propose_review_task(agent, current_stage, config))

        if status == "review_in_progress":
            # creative_reviewer completed and _check_review_trigger accepted it
            # (if it was rejected, _check_review_trigger returned a fix proposal above)
            current_info["status"] = "passed"
            stage_status[current_stage] = current_info
            internal_state["stage_status"] = stage_status

            target_stage = config.get("target_stage", "revised_draft")
            next_stg = _next_stage(current_stage)
            if next_stg and STAGES.index(current_stage) < STAGES.index(target_stage):
                internal_state["current_stage"] = next_stg
                internal_state["current_iteration"] = 0
                logger.info("Writers Room: stage '%s' PASSED — advancing to '%s'", current_stage, next_stg)
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])
                return _tag_sprint(self._propose_creative_tasks(agent, next_stg, config))

            logger.info("Writers Room: target stage '%s' PASSED — project complete", current_stage)
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return None

        if status == "fix_in_progress":
            # After fixes, re-run feedback
            stage_status[current_stage]["status"] = "writing_done"
            stage_status[current_stage]["iterations"] = iteration + 1
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return _tag_sprint(self._propose_feedback_tasks(agent, current_stage, config))

        # Fallback: if status is unknown, start fresh
        logger.warning("Writers Room: unknown stage status '%s' for '%s', resetting", status, current_stage)
        stage_status[current_stage] = {"status": "not_started", "iterations": 0}
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
        return _tag_sprint(self._propose_creative_tasks(agent, current_stage, config))

    # ── Creative task proposal ──────────────────────────────────────────

    def _propose_creative_tasks(self, agent: Agent, stage: str, config: dict) -> dict:
        """Create writing tasks for the current stage's creative agents."""
        # ── Voice profiling gate ────────────────────────────────────────
        # Before any creative writing begins, ensure a Voice DNA profile exists.
        # If source material is uploaded but no voice profile has been created,
        # the FIRST task must be voice profiling via story_researcher.
        has_voice_profile = Document.objects.filter(
            department=agent.department,
            doc_type="voice_profile",
            is_archived=False,
        ).exists()

        if not has_voice_profile:
            # Check if there is source material (documents)
            has_source_material = (
                Document.objects.filter(
                    department=agent.department,
                    is_archived=False,
                )
                .exclude(doc_type="voice_profile")
                .exists()
            )
            if has_source_material:
                locale = config.get("locale", "en")
                internal_state = agent.internal_state or {}
                stage_status = internal_state.get("stage_status", {})
                current_info = stage_status.get(stage, {"iterations": 0})
                current_info["status"] = "writing_in_progress"
                stage_status[stage] = current_info
                internal_state["stage_status"] = stage_status
                agent.internal_state = internal_state
                agent.save(update_fields=["internal_state"])

                return {
                    "exec_summary": f"Stage '{stage}': voice profiling must run before creative writing begins",
                    "tasks": [
                        {
                            "target_agent_type": "story_researcher",
                            "command_name": "profile_voice",
                            "exec_summary": "Extract Voice DNA from source material before creative work begins",
                            "step_plan": (
                                f"Locale: {locale}\n\n"
                                "Analyze ALL uploaded source material and produce a comprehensive "
                                "VOICE DNA profile. This profile will be used as an INVIOLABLE "
                                "constraint by all creative agents. The original author's voice is "
                                "sacred -- it must be preserved through all rewrites.\n\n"
                                "Consult department documents for the "
                                "source material."
                            ),
                            "depends_on_previous": False,
                        },
                    ],
                    "on_completion": {"set_status": "not_started", "stage": stage},
                }

        # Filter to only active agents in this department
        active_types = set(
            agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
        )
        creative_agents = [a for a in CREATIVE_MATRIX.get(stage, []) if a in active_types]

        if not creative_agents:
            logger.warning("Writers Room: no active creative agents for stage '%s' — skipping", stage)
            # Advance past this stage since there's nobody to write
            internal_state = agent.internal_state or {}
            stage_status = internal_state.get("stage_status", {})
            stage_status[stage] = {"status": "passed", "iterations": 0}
            internal_state["stage_status"] = stage_status
            next_stg = _next_stage(stage)
            if next_stg:
                internal_state["current_stage"] = next_stg
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return self._propose_creative_tasks(agent, next_stg, config) if next_stg else None

        locale = config.get("locale", "en")
        target_format = config.get("target_format", "")
        target_platform = config.get("target_platform", "")
        genre = config.get("genre", "")
        tone = config.get("tone", "")

        format_context = ""
        if target_format:
            format_context += f"Format: {target_format}\n"
        if target_platform:
            format_context += f"Platform: {target_platform}\n"
        if genre:
            format_context += f"Genre: {genre}\n"
        if tone:
            format_context += f"Tone: {tone}\n"

        # ── Build command-specific task plans per stage/agent ──────────
        TASK_SPECS: dict[str, dict[str, dict]] = {
            "ideation": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Market research, comps, and positioning analysis",
                    "step_plan": (
                        "Research the competitive landscape for this project. Analyze:\n"
                        "1. Comparable titles — what worked, what didn't, and why\n"
                        "2. Market positioning — where does this project sit? What's oversaturated vs. underserved?\n"
                        "3. Platform appetite — what are Netflix, HBO, etc. buying right now?\n"
                        "4. Zeitgeist hooks — what cultural currents can this project ride?\n"
                        "5. Audience demographics — who watches this, and what do they want?\n\n"
                        "Ground everything in the project goal and source materials. "
                        "Consult department documents for context."
                    ),
                },
                "story_architect": {
                    "command_name": "generate_concepts",
                    "exec_summary": "Generate 3-5 competing concept pitches",
                    "step_plan": (
                        "Based on the Story Researcher's market analysis and the project goal, "
                        "generate 3-5 diverse, competing concept pitches. Each must have:\n"
                        "- Working title\n- Premise (2-3 sentences)\n- Format recommendation\n"
                        "- Genre and tone\n- Target audience\n- Zeitgeist hook\n"
                        "- Why this concept would get greenlit NOW\n\n"
                        "Consult department documents for the research brief."
                    ),
                },
            },
            "concept": {
                "story_researcher": {
                    "command_name": "research_setting",
                    "exec_summary": "Deep research on the project's world, setting, and real-world context",
                    "step_plan": (
                        "Now that the concept direction is set, research the WORLD of this project in depth:\n"
                        "1. The real-world context the story draws from — people, places, events, power structures\n"
                        "2. Milieu-specific details that make the setting feel authentic\n"
                        "3. Social dynamics, hierarchies, and unwritten rules of this world\n"
                        "4. Historical parallels and real events that can inspire plot arcs\n"
                        "5. Cultural texture — language, habits, status markers, insider knowledge\n\n"
                        "This research will be used by the character designer and story architect. "
                        "Be specific. Name real neighborhoods, institutions, subcultures. "
                        "Consult project goal and source materials for direction."
                    ),
                },
                "story_architect": {
                    "command_name": "develop_concept",
                    "exec_summary": "Develop concept into structured creative foundation",
                    "step_plan": (
                        "Develop the selected concept into a structured creative foundation:\n"
                        "1. Dramatic premise — the core tension that drives every episode\n"
                        "2. World and setting — specific, vivid, grounded in the researcher's work\n"
                        "3. Tonal compass — reference shows, what to emulate and what to avoid\n"
                        "4. Format recommendation — episode count, length, structure\n"
                        "5. Protagonist sketch — who are we following, what do they want, what's in their way\n"
                        "6. Central relationship — the engine of the show\n"
                        "7. Thematic spine — what is this show really ABOUT beneath the plot\n\n"
                        "Consult department documents for research and concept pitches."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Design the core ensemble — protagonists, antagonists, key relationships",
                    "step_plan": (
                        "Design the core character ensemble for this project:\n"
                        "1. Each protagonist — background, motivation, fatal flaw, arc trajectory\n"
                        "2. Key antagonists — what they want, why they're formidable\n"
                        "3. Relationship map — who conflicts with whom, what alliances shift\n"
                        "4. Supporting cast — functional roles in the story, distinct voices\n"
                        "5. Character dynamics that create scenes — what happens when X meets Y\n\n"
                        "Ground every character in the project's world. Use the researcher's setting work. "
                        "Characters must feel like they BELONG in this specific milieu. "
                        "Consult department documents for concept and research."
                    ),
                },
            },
            "logline": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Analyze comparable loglines and distill what makes them sell",
                    "step_plan": (
                        "Research loglines of comparable projects in this genre/format space:\n"
                        "1. Collect 10-15 loglines from successful comparable titles — greenlit shows, sold specs\n"
                        "2. Analyze the anatomy: what structural patterns work? (irony, stakes, hook, world)\n"
                        "3. Identify the 'package pitch' elements — what makes a buyer read past the logline?\n"
                        "4. Distill the project's unique selling proposition vs. the competitive landscape\n"
                        "5. Flag positioning risks — what sounds too similar to existing titles?\n\n"
                        "Output a brief (1-2 pages) with your findings, specific examples, and a recommendation "
                        "for what this project's logline MUST accomplish to stand out. "
                        "Consult department documents for concept and character work."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Craft 3-5 logline variants — tight, hooky, sellable",
                    "step_plan": (
                        "Using the concept, characters, and the researcher's logline analysis, "
                        "write 3-5 logline variants for this project. Each logline must:\n"
                        "1. Be ONE sentence, max two — under 50 words\n"
                        "2. Contain: protagonist + flaw, inciting incident, central conflict, stakes\n"
                        "3. Convey tone and genre without naming them\n"
                        "4. Create irony or a compelling contradiction\n"
                        "5. Make the reader ask 'what happens next?'\n\n"
                        "After the variants, write a brief rationale for each — why this angle, what it emphasizes, "
                        "what it sacrifices. Recommend your top pick. "
                        "Consult department documents for concept, characters, and research."
                    ),
                },
            },
            "expose": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Research story world details and thematic depth for the exposé",
                    "step_plan": (
                        "Deepen the research foundation for the exposé stage:\n"
                        "1. Verify and expand world-building details — are locations, institutions, power structures specific enough?\n"
                        "2. Research thematic parallels — real-world events, social dynamics that mirror the story's themes\n"
                        "3. Identify narrative opportunities from real research — surprising facts, contradictions, ironies\n"
                        "4. Check character backstories against real-world plausibility\n"
                        "5. Surface details that will make the exposé feel grounded and authoritative\n\n"
                        "Consult department documents for all prior stage outputs."
                    ),
                },
                "story_architect": {
                    "command_name": "write",
                    "exec_summary": "Write the exposé — 3-5 page narrative overview of the entire project",
                    "step_plan": (
                        "Write the exposé (Exposé) — a 3-5 page compelling narrative summary:\n"
                        "1. Opening hook — drop us into the world and protagonist's situation\n"
                        "2. Act structure — setup, escalation, climax, resolution (broad strokes)\n"
                        "3. Character arcs — how do the main characters change?\n"
                        "4. World and tone — make the reader FEEL the show, not just understand it\n"
                        "5. The promise of the series — why does this sustain multiple seasons?\n"
                        "6. Emotional throughline — what's the journey the AUDIENCE goes on?\n\n"
                        "This is a SELLING document. It must read like a page-turner, not a summary. "
                        "Every paragraph should make the reader want the next one. "
                        "Consult department documents for concept, characters, logline, and research."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Write 2-3 key dialogue samples that establish voice and tone",
                    "step_plan": (
                        "Write 2-3 short dialogue scenes (each 1-2 pages) that showcase this project's voice:\n"
                        "1. A scene that establishes the protagonist's voice and worldview\n"
                        "2. A scene of conflict between two central characters — the core dynamic\n"
                        "3. (Optional) A scene that demonstrates the show's tonal range — humor within drama, or vice versa\n\n"
                        "These are PROOF-OF-CONCEPT scenes, not plot-advancing. They answer: 'What does this show SOUND like?'\n"
                        "Each character must have a distinct speech pattern, vocabulary, rhythm. "
                        "Consult department documents for characters, concept, and tone references."
                    ),
                },
            },
            "treatment": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Fact-check and deepen research for treatment-level detail",
                    "step_plan": (
                        "Provide treatment-level research support:\n"
                        "1. Verify all real-world references in the exposé — locations, institutions, cultural details\n"
                        "2. Research episode-level story opportunities — real events, seasonal rhythms, milieu specifics\n"
                        "3. Identify potential plot engines from real-world dynamics (legal, financial, political)\n"
                        "4. Provide texture for B-plots — what subcultures, side worlds, parallel stories exist?\n"
                        "5. Flag any research gaps that would undermine credibility at treatment level\n\n"
                        "Consult department documents for all prior outputs."
                    ),
                },
                "story_architect": {
                    "command_name": "write",
                    "exec_summary": "Write the treatment — episode-by-episode story architecture",
                    "step_plan": (
                        "Write the treatment — a detailed narrative breakdown of the season:\n"
                        "1. Season arc — the macro story from premiere to finale\n"
                        "2. Episode-by-episode breakdown (1-2 paragraphs each) — what happens, what changes, what's at stake\n"
                        "3. A/B/C plot weaving — how storylines intersect and build on each other\n"
                        "4. Act breaks and cliffhangers — what pulls viewers into the next episode?\n"
                        "5. Midseason shift — what reversal or revelation redefines the show at the midpoint?\n"
                        "6. Finale setup — how does everything converge?\n\n"
                        "This must read as a story, not a list. Each episode summary should feel inevitable yet surprising. "
                        "Consult department documents for exposé, characters, and research."
                    ),
                },
                "character_designer": {
                    "command_name": "write",
                    "exec_summary": "Write detailed character arcs mapped to the episode structure",
                    "step_plan": (
                        "Map each major character's arc across the treatment's episode structure:\n"
                        "1. Per character: emotional state at premiere, key turning points, state at finale\n"
                        "2. Relationship evolution — how do key dynamics shift episode by episode?\n"
                        "3. Character reveals — when does the audience learn key backstory? When do characters learn about each other?\n"
                        "4. Internal vs. external conflict — how do they diverge and reconnect?\n"
                        "5. Supporting cast arcs — who rises, who falls, who surprises?\n\n"
                        "Integrate tightly with the story architect's episode breakdown. "
                        "Consult department documents for treatment, exposé, and prior character work."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Write signature dialogue moments for key treatment beats",
                    "step_plan": (
                        "Write dialogue for 4-6 pivotal moments identified in the treatment:\n"
                        "1. The pilot's hook scene — first impression of protagonist and world\n"
                        "2. The central relationship's defining confrontation\n"
                        "3. The midseason revelation/reversal — the scene where everything changes\n"
                        "4. A quiet character moment — vulnerability, humor, or intimacy\n"
                        "5-6. Key scenes that showcase tonal range and secondary characters\n\n"
                        "Each scene should be 1-3 pages. Focus on subtext — what's NOT said matters as much as what is. "
                        "Consult department documents for treatment, characters, and voice profile."
                    ),
                },
            },
            "step_outline": {
                "story_architect": {
                    "command_name": "write",
                    "exec_summary": "Write the step outline — scene-by-scene breakdown of the pilot",
                    "step_plan": (
                        "Write the step outline (Szenenplan) for the pilot episode:\n"
                        "1. Scene-by-scene breakdown — each scene gets: location, characters present, what happens, what changes\n"
                        "2. Scene purpose — every scene must advance plot, reveal character, or build world (ideally two of three)\n"
                        "3. Act structure — clear act breaks with escalating tension\n"
                        "4. Pacing — vary scene length, intensity, and type (dialogue, action, montage)\n"
                        "5. The cold open — what image/moment hooks the audience before titles?\n"
                        "6. The final scene — what question does the pilot leave ringing?\n\n"
                        "Be specific about blocking and visual storytelling, not just dialogue beats. "
                        "Consult department documents for treatment, characters, and research."
                    ),
                },
                "character_designer": {
                    "command_name": "write",
                    "exec_summary": "Detail character behavior and dynamics for each pilot scene",
                    "step_plan": (
                        "For each scene in the step outline, specify character dynamics:\n"
                        "1. What does each character WANT in this scene? What are they hiding?\n"
                        "2. Power dynamics — who has leverage, who's performing, who's authentic?\n"
                        "3. Body language and behavioral tells — how does each character's physicality express their state?\n"
                        "4. Introduction moments — how does the audience MEET each character for the first time?\n"
                        "5. Relationship signals — what do scenes between characters establish about their history?\n\n"
                        "This is the bridge between character bibles and actual screenplay behavior. "
                        "Consult department documents for step outline, characters, and treatment."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Write dialogue sketches for every scene in the step outline",
                    "step_plan": (
                        "Write dialogue sketches for each scene in the step outline:\n"
                        "1. Key lines — the lines that DEFINE each scene (not full dialogue, but the crucial exchanges)\n"
                        "2. Voice consistency — ensure each character sounds distinct and consistent with their profile\n"
                        "3. Subtext notes — what's the unspoken tension beneath the dialogue?\n"
                        "4. Exposition management — where does necessary information land naturally?\n"
                        "5. Scene endings — the last line of each scene should propel into the next\n\n"
                        "These are sketches, not final dialogue — but they should capture the MUSIC of each scene. "
                        "Consult department documents for step outline, characters, and voice profile."
                    ),
                },
            },
            "first_draft": {
                "story_architect": {
                    "command_name": "write",
                    "exec_summary": "Write the first draft screenplay — full pilot script",
                    "step_plan": (
                        "Write the complete first draft of the pilot screenplay:\n"
                        "1. Professional screenplay format — slug lines, action, dialogue, parentheticals\n"
                        "2. Follow the step outline's scene structure — but improve where inspiration strikes\n"
                        "3. Action lines — visual, cinematic, economical. Show don't tell.\n"
                        "4. Dialogue — integrate the dialog writer's sketches but make them flow as real conversation\n"
                        "5. Pacing — the read should move. If a scene feels slow, cut or compress.\n"
                        "6. Target length — 45-60 pages for a drama pilot\n\n"
                        "This is a WRITER'S draft — prioritize voice, energy, and specificity over polish. "
                        "Consult department documents for step outline, dialogue sketches, and all prior work."
                    ),
                },
                "character_designer": {
                    "command_name": "write",
                    "exec_summary": "Review and enhance character consistency across the full draft",
                    "step_plan": (
                        "Review the first draft for character integrity:\n"
                        "1. Voice audit — does each character sound distinct throughout? Flag any blending.\n"
                        "2. Motivation check — does every character action follow from established wants/needs?\n"
                        "3. Arc tracking — are the pilot's character arcs landing? Where do they stall?\n"
                        "4. Introduction effectiveness — do characters make strong first impressions?\n"
                        "5. Write enhanced versions of any scenes where characters feel generic or inconsistent\n\n"
                        "Output: specific scene rewrites and notes, not general feedback. "
                        "Consult department documents for the first draft, character profiles, and step outline."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Dialogue polish pass — sharpen every exchange in the first draft",
                    "step_plan": (
                        "Do a full dialogue polish pass on the first draft:\n"
                        "1. Cut flab — remove any line that doesn't earn its place\n"
                        "2. Sharpen wit — punch up where the tone allows it\n"
                        "3. Deepen subtext — where are characters saying exactly what they mean? Fix that.\n"
                        "4. Rhythm — vary sentence length, use fragments, interruptions, overlaps\n"
                        "5. Signature lines — does the pilot have 3-5 lines people would quote?\n"
                        "6. Exposition surgery — is backstory delivered naturally or in clunky speeches?\n\n"
                        "Output the full dialogue-polished draft. Mark changes from the original. "
                        "Consult department documents for the first draft, voice profile, and characters."
                    ),
                },
            },
            "revised_draft": {
                "story_architect": {
                    "command_name": "write",
                    "exec_summary": "Structural revision — tighten the pilot's architecture",
                    "step_plan": (
                        "Revise the draft focusing on structural integrity:\n"
                        "1. Does the cold open hook within 2 pages? If not, restructure.\n"
                        "2. Act breaks — are they landing with sufficient impact? Rewrite weak ones.\n"
                        "3. Pacing analysis — where does the script drag? Cut or compress ruthlessly.\n"
                        "4. Scene necessity — does every scene pass the 'what happens if I cut this?' test?\n"
                        "5. Setup/payoff — are all planted elements paying off? Are payoffs properly set up?\n"
                        "6. Ending — does the final scene leave the audience NEEDING episode 2?\n\n"
                        "Output the structurally revised full draft. "
                        "Consult department documents for the first draft, all feedback, and review notes."
                    ),
                },
                "character_designer": {
                    "command_name": "write",
                    "exec_summary": "Final character pass — ensure arcs and voices are airtight",
                    "step_plan": (
                        "Final character integrity pass on the revised draft:\n"
                        "1. Arc completion — does every major character's pilot arc resolve satisfyingly?\n"
                        "2. Ensemble balance — does any character dominate or disappear? Adjust.\n"
                        "3. Relationship clarity — is the central dynamic undeniably compelling?\n"
                        "4. Backstory integration — is character history revealed through action, not exposition?\n"
                        "5. Consistency — scan for any contradictions with established character profiles\n\n"
                        "Output specific rewrites for any scenes that need character work. "
                        "Consult department documents for revised draft, all character work, and feedback."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write",
                    "exec_summary": "Final dialogue pass — production-ready polish",
                    "step_plan": (
                        "Final dialogue polish for the revised draft:\n"
                        "1. Read every line aloud (mentally) — does it sound like a human being talking?\n"
                        "2. Character voice final check — cover the character names, can you tell who's speaking?\n"
                        "3. Trim ruthlessly — if a scene works with fewer lines, use fewer lines\n"
                        "4. Silence — are there moments where NO dialogue is more powerful? Mark them.\n"
                        "5. The quotable test — does this script have moments that stick?\n"
                        "6. Consistency with voice profile — does the dialogue honor the source material's DNA?\n\n"
                        "Output the final polished draft. "
                        "Consult department documents for revised draft, voice profile, and all feedback."
                    ),
                },
            },
        }

        tasks = []
        previous_depends = False
        for agent_type in creative_agents:
            spec = TASK_SPECS.get(stage, {}).get(agent_type)
            if not spec:
                raise ValueError(
                    f"No TASK_SPECS entry for stage '{stage}', agent '{agent_type}'. "
                    f"Every CREATIVE_MATRIX entry must have a corresponding TASK_SPECS entry."
                )
            pitch_preamble = (
                "STEP 0 — PITCH EXTRACTION (mandatory before any creative work):\n"
                "Read the CREATOR'S ORIGINAL PITCH in <project_goal> above. List the specific "
                "elements the creator provided: their characters, their conflicts, their world, "
                "their arcs, their side plots, their tone direction. These are YOUR raw material.\n"
                "Referenced shows (e.g. 'like Succession', 'Industry-style') are QUALITY "
                "benchmarks — they tell you the league, NOT the plot. Do NOT borrow characters, "
                "family structures, premises, or dramatic engines from referenced shows.\n"
                "If the creator said 'three brothers', you write three brothers — not a patriarch "
                "with sons and daughters. If they described a specific conflict, that IS the "
                "central conflict — do not substitute a more conventional one.\n\n"
            )
            task_data = {
                "target_agent_type": agent_type,
                "command_name": spec.get("command_name", ""),
                "exec_summary": spec["exec_summary"],
                "step_plan": (
                    f"Locale: {locale}\n{format_context}\n"
                    f"{pitch_preamble}"
                    f"{spec['step_plan']}\n\n"
                    f"FIDELITY CHECK (before submitting): Re-read the creator's pitch. "
                    f"Does your output preserve EVERY specific element they provided? "
                    f"If you introduced characters, conflicts, or structures the creator "
                    f"did NOT mention, ask yourself: did I copy this from a reference show? "
                    f"If yes, delete it and build from the creator's actual material instead.\n\n"
                    f"Your output must be in {locale}. This is non-negotiable."
                ),
                "depends_on_previous": previous_depends,
            }

            tasks.append(task_data)
            if agent_type == "story_researcher":
                previous_depends = True

        # Update stage status
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        current_info["status"] = "writing_in_progress"
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        return {
            "exec_summary": f"Stage '{stage}': assign creative agents to write",
            "tasks": tasks,
            "on_completion": {"set_status": "writing_done", "stage": stage},
        }

    # ── Feedback task proposal ──────────────────────────────────────────

    def _propose_feedback_tasks(self, agent: Agent, stage: str, config: dict) -> dict:
        """Create feedback/analysis tasks per the depth matrix.

        Skips feedback agents that are inactive, or whose controlled creative
        agent is inactive (no point reviewing work that wasn't produced).
        """
        from agents.blueprints import get_workforce_for_department

        feedback_agents = FEEDBACK_MATRIX.get(stage, [])
        locale = config.get("locale", "en")

        # Active agents in this department
        active_types = set(
            agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
        )

        # Build controls map: feedback_agent_type → creative_agent_type it reviews
        workforce = get_workforce_for_department(agent.department.department_type)
        controls_map: dict[str, str | None] = {}
        for slug, bp in workforce.items():
            ctrl = getattr(bp, "controls", None)
            if ctrl:
                controls_map[slug] = ctrl if isinstance(ctrl, str) else ctrl[0]

        tasks = []
        for agent_type, depth in feedback_agents:
            # Skip if the feedback agent itself is inactive
            if agent_type not in active_types:
                logger.info("Writers Room: skipping inactive feedback agent '%s'", agent_type)
                continue
            # Skip if the creative agent this reviewer controls is inactive
            controlled = controls_map.get(agent_type)
            if controlled and controlled not in active_types:
                logger.info(
                    "Writers Room: skipping feedback agent '%s' — its target '%s' is inactive",
                    agent_type,
                    controlled,
                )
                continue

            tasks.append(
                {
                    "target_agent_type": agent_type,
                    "exec_summary": f"Analyze {stage} content ({agent_type}, depth={depth})",
                    "step_plan": (
                        f"Stage: {stage}\n"
                        f"Depth: {depth}\n"
                        f"Locale: {locale}\n\n"
                        f"Analyze the current '{stage}' content at {depth} depth. "
                        f"Consult department documents for the latest creative output.\n\n"
                        f"Flag issues using:\n"
                        f"- \U0001f534 CRITICAL: fundamental problems that break the work\n"
                        f"- \U0001f7e0 MAJOR: significant issues that weaken the work\n"
                        f"- \U0001f7e1 MINOR: small issues worth noting\n"
                        f"- \U0001f7e2 STRENGTH: things that work well\n\n"
                        f"Your output must be in {locale}."
                    ),
                    "depends_on_previous": False,  # Feedback agents run in parallel
                }
            )

        if not tasks:
            # All feedback agents skipped — pass the stage without review
            logger.warning("Writers Room: no active feedback agents for stage '%s' — passing without review", stage)
            internal_state = agent.internal_state or {}
            stage_status = internal_state.get("stage_status", {})
            current_info = stage_status.get(stage, {"iterations": 0})
            current_info["status"] = "passed"
            stage_status[stage] = current_info
            internal_state["stage_status"] = stage_status
            next_stg = _next_stage(stage)
            target_stage = config.get("target_stage", "revised_draft")
            if next_stg and STAGES.index(stage) < STAGES.index(target_stage):
                internal_state["current_stage"] = next_stg
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            if next_stg and STAGES.index(stage) < STAGES.index(target_stage):
                return self._propose_creative_tasks(agent, next_stg, config)
            return None

        # Update stage status
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        current_info["status"] = "feedback_in_progress"
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        return {
            "exec_summary": f"Stage '{stage}': assign feedback agents to analyze",
            "tasks": tasks,
            "on_completion": {"set_status": "feedback_done", "stage": stage},
        }

    # ── Review task proposal (dispatch creative_reviewer) ────────────

    def _propose_review_task(self, agent: Agent, stage: str, config: dict) -> dict:
        """Dispatch the creative_reviewer to consolidate analyst feedback."""
        locale = config.get("locale", "en")

        from agents.models import AgentTask

        feedback_agent_types = [at for at, _ in FEEDBACK_MATRIX.get(stage, [])]
        recent_feedback = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=feedback_agent_types,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[: len(feedback_agent_types) * 2]
            .values_list("agent__agent_type", "report")
        )

        feedback_text = ""
        for agent_type, report in recent_feedback:
            if report:
                feedback_text += f"\n\n## {agent_type}\n{report}"

        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        current_info["status"] = "review_in_progress"
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        return {
            "exec_summary": f"Stage '{stage}': consolidate analyst feedback and score",
            "tasks": [
                {
                    "target_agent_type": "creative_reviewer",
                    "command_name": "review-creative",
                    "exec_summary": f"Review stage '{stage}' — consolidate analyst feedback",
                    "step_plan": (
                        f"Stage: {stage}\n"
                        f"Locale: {locale}\n"
                        f"Quality threshold: {EXCELLENCE_THRESHOLD}/10\n\n"
                        f"## Analyst Feedback Reports\n{feedback_text}\n\n"
                        f"Score each dimension 1.0-10.0. Overall score = minimum of all dimensions.\n"
                        f"After your review, call the submit_verdict tool with your verdict and score.\n\n"
                        f"For CHANGES_REQUESTED: group fix instructions by creative agent."
                    ),
                    "depends_on_previous": False,
                }
            ],
        }

    # ── Fix task override (writers-room-specific routing) ──────────────

    def _propose_fix_task(
        self, agent: Agent, review_task, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """Route fix tasks to creative agents and track stage status."""
        config = _get_merged_config(agent)
        locale = config.get("locale", "en")
        internal_state = agent.internal_state or {}
        current_stage = internal_state.get("current_stage", STAGES[0])

        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(current_stage, {"iterations": 0})
        current_info["status"] = "fix_in_progress"
        stage_status[current_stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        review_snippet = review_task.report or ""
        polish_msg = f" (polish {polish_count}/{MAX_POLISH_ATTEMPTS})" if score >= NEAR_EXCELLENCE_THRESHOLD else ""

        return {
            "exec_summary": f"Fix review issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}",
            "tasks": [
                {
                    "target_agent_type": "story_architect",
                    "command_name": "write",
                    "exec_summary": f"Fix review issues for stage '{current_stage}' (score {score}/10)",
                    "step_plan": (
                        f"Current quality score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                        f"Review round: {round_num}. Locale: {locale}\n\n"
                        f"The creative reviewer has requested changes. Fix the issues below.\n\n"
                        f"## Review Report\n{review_snippet}\n\n"
                        f"Address every CHANGES_REQUESTED item. Focus on the weakest dimensions first."
                    ),
                    "depends_on_previous": False,
                }
            ],
        }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _next_stage(current: str) -> str | None:
    """Return the next stage in the pipeline, or None if at the end."""
    try:
        idx = STAGES.index(current)
        return STAGES[idx + 1] if idx + 1 < len(STAGES) else None
    except ValueError:
        return None


def _get_merged_config(agent: Agent) -> dict:
    """Merge project -> department -> agent config."""
    project_config = agent.department.project.config or {}
    dept_config = agent.department.config or {}
    agent_config = agent.config or {}
    return {**project_config, **dept_config, **agent_config}


ENTRY_DETECTION_PROMPT = """\
You are the showrunner of a professional writers room. Analyze the project input to determine where the creative pipeline should start.

## Project Goal
{goal}

## Source Material
{sources_summary}

## Existing Config
{config_summary}

## Stage Options (earliest to latest)
- ideation: No concrete story idea. Just a vague theme, genre preference, or "write me something good."
- concept: A rough idea or premise exists but needs development. e.g. "a thriller about a cop who discovers his partner is a serial killer"
- logline: A logline or clear story concept exists, ready for structural work
- expose: An expose, pitch document, or series bible is provided
- treatment: A treatment, Serienkonzept, or detailed narrative outline is provided
- step_outline: A step outline or beat sheet exists
- first_draft: A complete draft (screenplay, manuscript, etc.) is provided
- revised_draft: A draft with revision notes or previous feedback is provided

## Format Detection
Identify the format from the material. Understand German industry terms:
- Serienkonzept = series concept/bible
- Filmreihe = film series / franchise (multiple connected films)
- Drehbuch = screenplay
- Expose/Exposé = pitch document
- Treatment = detailed narrative outline

## Rules
- Pick the EARLIEST stage that matches the material quality. If someone uploaded a weak treatment, start at treatment — feedback agents will catch the weaknesses.
- If NO story idea is present at all, pick ideation.
- If a vague idea exists but no developed concept, pick concept.
- Only skip stages if the material genuinely covers them.

Respond with JSON only:
{{
    "detected_stage": "stage_name",
    "detected_format": "film|series|limited_series|filmreihe|novel|theatre|short_story",
    "format_confidence": "high|medium|low",
    "reasoning": "Brief explanation of why this stage was chosen",
    "recommended_config": {{
        "target_format": "...",
        "genre": "...",
        "tone": "..."
    }}
}}

Only include keys in recommended_config that you can confidently infer. Omit keys you're unsure about."""


def _run_entry_detection(agent) -> str:
    """
    One-shot Claude call to classify project input and determine the starting stage.
    Runs exactly once — stores result in internal_state.
    Returns the detected stage name.
    """
    project = agent.department.project
    goal = project.goal or "No goal specified"

    # Gather source summaries
    sources = project.sources.all()
    sources_summary = ""
    for s in sources:
        text = s.extracted_text or s.raw_content or ""
        if not text:
            continue
        name = s.original_filename or s.url or "Text input"
        sources_summary += f"\n### {name} ({s.source_type})\n{text}\n"

    if not sources_summary:
        sources_summary = "No source material uploaded."

    # Gather existing config
    config = _get_merged_config(agent)
    config_keys = ["target_format", "genre", "tone", "target_platform", "locale"]
    config_summary = "\n".join(f"- {k}: {config[k]}" for k in config_keys if config.get(k))
    if not config_summary:
        config_summary = "No config set."

    prompt = ENTRY_DETECTION_PROMPT.format(
        goal=goal,
        sources_summary=sources_summary,
        config_summary=config_summary,
    )

    response, _usage = call_claude(
        system_prompt="You are a project classification system. Respond with JSON only.",
        user_message=prompt,
        model="claude-sonnet-4-6",
        max_tokens=1024,
    )

    data = parse_json_response(response)
    if not data or "detected_stage" not in data:
        logger.warning("Entry detection failed to parse, defaulting to ideation: %s", response[:200])
        return "ideation"

    detected_stage = data["detected_stage"]
    if detected_stage not in STAGES:
        logger.warning("Entry detection returned unknown stage '%s', defaulting to ideation", detected_stage)
        detected_stage = "ideation"

    # Store detection results in internal_state
    internal_state = agent.internal_state or {}
    internal_state["entry_detected"] = True
    internal_state["detected_format"] = data.get("detected_format", "")
    internal_state["detection_reasoning"] = data.get("reasoning", "")

    # Store recommended config values (user can override via config)
    recommended = data.get("recommended_config", {})
    if recommended:
        internal_state["recommended_config"] = recommended

    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    logger.info(
        "Writers Room entry detection: stage=%s format=%s reason=%s",
        detected_stage,
        data.get("detected_format"),
        data.get("reasoning", "")[:100],
    )

    return detected_stage

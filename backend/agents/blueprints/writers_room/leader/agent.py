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
    config_schema = {
        "target_stage": {
            "type": "str",
            "required": False,
            "label": "Target Stage",
            "description": "Final stage: logline, expose, treatment, step_outline, first_draft, revised_draft (default: revised_draft)",
        },
        "target_format": {
            "type": "str",
            "required": False,
            "label": "Format",
            "description": "screenplay, novel, theatre, series, film, short_story",
        },
        "target_platform": {
            "type": "str",
            "required": False,
            "label": "Platform",
            "description": "netflix, hbo, bbc, film, indie, theatre, publisher, etc.",
        },
        "genre": {
            "type": "str",
            "required": False,
            "label": "Genre",
            "description": "drama, comedy, thriller, horror, sci-fi, etc.",
        },
        "tone": {
            "type": "str",
            "required": False,
            "label": "Tone",
            "description": "dark, light, prestige, pulp, literary, etc.",
        },
        "locale": {
            "type": "str",
            "required": False,
            "label": "Language",
            "description": "Output language code: en, de, fr, es, etc. (default: en)",
        },
    }

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
            return {
                "exec_summary": f"ESCALATION: Stage '{current_stage}' reached {MAX_REVIEW_ROUNDS} iterations without passing",
                "tasks": [
                    {
                        "target_agent_type": "leader",
                        "exec_summary": f"Stage '{current_stage}' has iterated {MAX_REVIEW_ROUNDS} times without passing quality gates. Review feedback history and decide next steps.",
                        "step_plan": "Review the feedback history for this stage. Determine if the quality threshold should be adjusted, the approach needs to change, or human intervention is needed.",
                    }
                ],
            }

        # ── State machine ───────────────────────────────────────────────

        if status == "not_started":
            # Step 1: Assign creative agents to write
            return self._propose_creative_tasks(agent, current_stage, config)

        if status == "writing_done":
            # Step 3: Assign feedback agents to analyze
            return self._propose_feedback_tasks(agent, current_stage, config)

        if status == "feedback_done":
            # Step 4/5: Check feedback results and decide
            return self._evaluate_feedback(agent, current_stage, config)

        if status == "fix_in_progress":
            # After fixes, re-run feedback
            stage_status[current_stage]["status"] = "writing_done"
            stage_status[current_stage]["iterations"] = iteration + 1
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            return self._propose_feedback_tasks(agent, current_stage, config)

        # Fallback: if status is unknown, start fresh
        logger.warning("Writers Room: unknown stage status '%s' for '%s', resetting", status, current_stage)
        stage_status[current_stage] = {"status": "not_started", "iterations": 0}
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
        return self._propose_creative_tasks(agent, current_stage, config)

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
            # Check if there is source material (documents or briefings with attachments)
            has_source_material = (
                Document.objects.filter(
                    department=agent.department,
                    is_archived=False,
                )
                .exclude(doc_type="voice_profile")
                .exists()
            )
            if not has_source_material:
                # Also check for project-level briefings with attachments
                from projects.models import Briefing

                has_source_material = (
                    Briefing.objects.filter(
                        project=agent.department.project,
                        status="active",
                    )
                    .exclude(content="")
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
                                "Consult department documents and briefing attachments for the "
                                "source material."
                            ),
                            "depends_on_previous": False,
                        },
                    ],
                    "on_completion": {"set_status": "not_started", "stage": stage},
                }

        creative_agents = CREATIVE_MATRIX.get(stage, [])
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
                        "Consult department documents and briefings for context."
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
        }

        tasks = []
        previous_depends = False
        for agent_type in creative_agents:
            spec = TASK_SPECS.get(stage, {}).get(agent_type)
            if spec:
                task_data = {
                    "target_agent_type": agent_type,
                    "command_name": spec.get("command_name", ""),
                    "exec_summary": spec["exec_summary"],
                    "step_plan": (
                        f"Locale: {locale}\n{format_context}\n"
                        f"{spec['step_plan']}\n\n"
                        f"Your output must be in {locale}. This is non-negotiable."
                    ),
                    "depends_on_previous": previous_depends,
                }
            else:
                # Fallback for stages without specific specs
                task_data = {
                    "target_agent_type": agent_type,
                    "exec_summary": f"Write {stage} content ({agent_type})",
                    "step_plan": (
                        f"Stage: {stage}\nLocale: {locale}\n{format_context}\n"
                        f"Write your contribution for the '{stage}' stage of this project. "
                        f"Consult department documents for existing material and briefings for the project brief.\n\n"
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
        """Create feedback/analysis tasks per the depth matrix."""
        feedback_agents = FEEDBACK_MATRIX.get(stage, [])
        locale = config.get("locale", "en")

        tasks = []
        for agent_type, depth in feedback_agents:
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

    # ── Evaluate feedback and decide: pass, fix, or advance ─────────────

    def _evaluate_feedback(
        self,
        agent: Agent,
        stage: str,
        config: dict,
    ) -> dict | None:
        """
        Parse recent feedback task reports, score quality, decide whether to
        pass the stage or route fixes back to creative agents.

        Uses universal quality scoring:
        - score >= 9.5 → pass (excellence)
        - score >= 9.0 and polish_attempts >= 3 → pass (diminishing returns)
        - otherwise → route fixes back
        """
        from agents.ai.claude_client import call_claude, parse_json_response
        from agents.models import AgentTask

        # Gather feedback reports from this stage
        feedback_agent_types = [at for at, _ in FEEDBACK_MATRIX.get(stage, [])]
        recent_feedback = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=feedback_agent_types,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[: len(feedback_agent_types) * 2]
            .values_list("agent__agent_type", "report", "exec_summary")
        )

        if not recent_feedback:
            logger.warning("Writers Room: no feedback found for stage '%s'", stage)
            return None

        # Build feedback summary for Claude to parse
        feedback_text = ""
        for agent_type, report, _summary in recent_feedback:
            if report:
                feedback_text += f"\n\n## {agent_type}\n{report[:3000]}"

        # ── Special handling: ideation stage uses merge evaluation ──────
        if stage == "ideation":
            return self._evaluate_ideation_feedback(agent, stage, config, feedback_text)

        # Track polish attempts for this stage
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        polish_attempts = current_info.get("polish_attempts", 0)
        iteration = current_info.get("iterations", 0)

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Evaluate Feedback for Stage: {stage}

## Quality Standard
Excellence threshold: {EXCELLENCE_THRESHOLD}/10. The overall score is the MINIMUM of all dimension scores.
An implementation is only as strong as its weakest dimension.

## Feedback Reports
{feedback_text}

# Task
Evaluate the quality of the current stage output based on ALL analyst feedback.

## Scoring (REQUIRED)
Score each dimension 1.0-10.0 (use decimals — 8.5, 9.0, 9.5 etc.):
- **Market fit**: Commercial viability, positioning, audience appeal
- **Structure**: Story architecture, beats, pacing, act breaks
- **Character**: Consistency, arcs, motivation, relationships, voice
- **Dialogue**: Voice, subtext, scene construction, exposition balance
- **Craft**: Format conventions, technical quality, polish
- **Feasibility**: Budget, cast-ability, production practicality

Only score dimensions that were analyzed by feedback agents this round.
Compute the **overall score** as the MINIMUM of all scored dimensions.

## Fix routing (if score < {EXCELLENCE_THRESHOLD})
Group issues by which creative agent should fix them:
- market_analyst flags → story_researcher
- structure_analyst flags → story_architect
- character_analyst flags → character_designer
- dialogue_analyst flags → dialog_writer
- format_analyst flags → story_architect (structural) or dialog_writer (craft)
- production_analyst flags → most relevant creative agent

Respond with JSON:
{{
    "scores": {{
        "market_fit": 0.0,
        "structure": 0.0,
        "character": 0.0,
        "dialogue": 0.0,
        "craft": 0.0,
        "feasibility": 0.0
    }},
    "overall_score": 0.0,
    "summary": "Brief evaluation summary",
    "fix_tasks": [
        {{
            "target_agent_type": "creative agent type",
            "flags_from": "feedback agent type",
            "flags": ["list of specific issues to address"],
            "exec_summary": "What to fix",
            "step_plan": "Detailed fix instructions"
        }}
    ]
}}

VERDICT LINE (REQUIRED — must be the last line):
VERDICT: APPROVED (score: N.N/10)
VERDICT: CHANGES_REQUESTED (score: N.N/10)"""

        response, _usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
            model=self.get_model(agent, command_name="check-progress"),
        )

        data = parse_json_response(response)
        if not data:
            logger.warning("Writers Room: failed to parse feedback evaluation: %s", response[:300])
            return None

        score = float(data.get("overall_score", 0.0))

        # Use shared quality gate (tracks polish, evaluates acceptance)
        # We use a stage-scoped key so each stage has independent tracking
        stage_key = f"wr_{stage}"
        # Seed review_rounds so _apply_quality_gate sees the iteration count
        internal_state.setdefault("review_rounds", {})[stage_key] = iteration
        internal_state.setdefault("polish_attempts", {})[stage_key] = polish_attempts
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        accepted, polish_count, _round_num = self._apply_quality_gate(agent, score, stage_key)

        # Re-read internal_state since _apply_quality_gate saved it
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": iteration})

        if accepted:
            # Stage passed — mark and advance
            current_info["status"] = "passed"
            current_info["polish_attempts"] = 0  # reset for next stage
            stage_status[stage] = current_info
            internal_state["stage_status"] = stage_status

            # Advance to next stage if not at target
            target_stage = config.get("target_stage", "revised_draft")
            next_stage = _next_stage(stage)
            if next_stage and STAGES.index(stage) < STAGES.index(target_stage):
                internal_state["current_stage"] = next_stage
                internal_state["current_iteration"] = 0
                logger.info("Writers Room: stage '%s' PASSED (%.1f/10) — advancing to '%s'", stage, score, next_stage)
            else:
                logger.info("Writers Room: target stage '%s' PASSED (%.1f/10) — project complete", stage, score)

            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])

            if next_stage and STAGES.index(stage) < STAGES.index(target_stage):
                return self._propose_creative_tasks(agent, next_stage, config)
            return None  # Done

        # Score below threshold — route fixes
        fix_tasks = data.get("fix_tasks", [])
        if not fix_tasks:
            logger.warning("Writers Room: score %.1f below threshold but no fix_tasks returned", score)
            return None

        current_info["status"] = "fix_in_progress"
        current_info["iterations"] = iteration + 1
        current_info["polish_attempts"] = polish_count
        current_info["last_score"] = score
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        locale = config.get("locale", "en")
        polish_msg = f" (polish {polish_attempts}/{MAX_POLISH_ATTEMPTS})" if score >= NEAR_EXCELLENCE_THRESHOLD else ""
        tasks = []
        for ft in fix_tasks:
            tasks.append(
                {
                    "target_agent_type": ft["target_agent_type"],
                    "exec_summary": ft.get("exec_summary", f"Fix issues from {ft.get('flags_from', 'analyst')}"),
                    "step_plan": (
                        f"Stage: {stage}\n"
                        f"Locale: {locale}\n"
                        f"Current score: {score}/10. Target: {EXCELLENCE_THRESHOLD}/10.\n"
                        f"Issues from: {ft.get('flags_from', 'analyst')}\n\n"
                        f"Address these specific issues:\n"
                        + "\n".join(f"- {flag}" for flag in ft.get("flags", []))
                        + f"\n\n{ft.get('step_plan', '')}\n\n"
                        f"Rewrite your contribution addressing ALL flagged issues. "
                        f"Focus on the weakest dimensions first. "
                        f"Preserve everything that was not flagged. "
                        f"Output must be in {locale}."
                    ),
                    "depends_on_previous": False,
                }
            )

        return {
            "exec_summary": f"Stage '{stage}': fix issues (score {score}/10, need {EXCELLENCE_THRESHOLD}){polish_msg}",
            "tasks": tasks,
            "on_completion": {"set_status": "fix_in_progress", "stage": stage},
        }

    def _evaluate_ideation_feedback(
        self,
        agent: Agent,
        stage: str,
        config: dict,
        feedback_text: str,
    ) -> dict | None:
        """
        Special evaluation for ideation stage: rank concepts, merge best elements,
        store merged concept as Document, advance to concept stage.
        """
        locale = config.get("locale", "en")

        context_msg = self.build_context_message(agent)
        msg = f"""{context_msg}

# Evaluate Ideation Concepts

## Feedback from Analysts
{feedback_text}

# Task
You are evaluating 3-5 competing concept pitches that were scored by feedback agents.

1. RANK all concepts based on the feedback (commercial viability, dramatic potential, feasibility)
2. PICK the winner — the concept with the strongest foundation
3. IDENTIFY strong elements from the runners-up that could strengthen the winner
4. PRODUCE one merged concept that combines the best of all pitches

If ALL concepts received critical flags with no redeeming qualities, return:
{{"all_failed": true, "reasoning": "..."}}

Otherwise, return:
{{
    "all_failed": false,
    "winner": "Concept N title",
    "reasoning": "Why this concept won and what was merged",
    "elements_merged": ["Element from Concept X", "Element from Concept Y"],
    "merged_concept": "The complete merged concept description — 2-4 paragraphs covering premise, format, genre, tone, audience, and zeitgeist hook. Written in {locale}."
}}"""

        response, _usage = call_claude(
            system_prompt=self.build_system_prompt(agent),
            user_message=msg,
            model=self.get_model(agent, command_name="check-progress"),
        )

        data = parse_json_response(response)
        if not data:
            logger.warning("Writers Room: failed to parse ideation evaluation: %s", response[:300])
            return None

        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})

        if data.get("all_failed"):
            # All concepts failed — loop: re-run ideation with feedback context
            current_info["status"] = "not_started"
            current_info["iterations"] = current_info.get("iterations", 0) + 1
            stage_status[stage] = current_info
            internal_state["stage_status"] = stage_status
            agent.internal_state = internal_state
            agent.save(update_fields=["internal_state"])
            logger.info("Writers Room: all ideation concepts failed, re-running ideation")
            return self._propose_creative_tasks(agent, stage, config)

        # Store merged concept as Document
        merged_text = data.get("merged_concept", "")
        if merged_text:
            Document.objects.update_or_create(
                department=agent.department,
                title="Merged Concept",
                defaults={
                    "content": merged_text,
                    "doc_type": "concept",
                },
            )

        # Mark ideation as passed, advance to concept
        current_info["status"] = "passed"
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        internal_state["current_stage"] = "concept"
        internal_state["current_iteration"] = 0
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])

        logger.info("Writers Room: ideation PASSED — merged concept stored, advancing to concept stage")
        return self._propose_creative_tasks(agent, "concept", config)


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
        snippet = text[:2000]
        if len(text) > 2000:
            snippet += f"\n[... truncated, {len(text)} chars total ...]"
        sources_summary += f"\n### {name} ({s.source_type})\n{snippet}\n"

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

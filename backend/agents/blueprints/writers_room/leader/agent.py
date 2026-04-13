from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import (
    EXCELLENCE_THRESHOLD,
    MAX_REVIEW_ROUNDS,
    LeaderBlueprint,
)
from agents.blueprints.writers_room.leader.commands import check_progress, plan_room
from projects.models import Document

logger = logging.getLogger(__name__)

# ── Stage pipeline ──────────────────────────────────────────────────────────

STAGES = ["pitch", "expose", "treatment", "first_draft"]

# ── Depth matrix: which FEEDBACK agents run at which stage ──────────────────

FEEDBACK_MATRIX: dict[str, list[tuple[str, str]]] = {
    "pitch": [
        ("market_analyst", "full"),
        ("structure_analyst", "lite"),
        ("character_analyst", "lite"),
    ],
    "expose": [
        ("market_analyst", "full"),
        ("structure_analyst", "full"),
        ("character_analyst", "lite"),
        ("production_analyst", "lite"),
    ],
    "treatment": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("production_analyst", "full"),
        ("market_analyst", "lite"),
    ],
    "concept": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("market_analyst", "full"),
        ("production_analyst", "full"),
    ],
    "first_draft": [
        ("structure_analyst", "full"),
        ("character_analyst", "full"),
        ("dialogue_analyst", "full"),
        ("format_analyst", "full"),
        ("production_analyst", "lite"),
        ("market_analyst", "lite"),
    ],
}

# ── Creative matrix: which CREATIVE agents write at which stage ─────────────

CREATIVE_MATRIX: dict[str, list[str]] = {
    "pitch": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "expose": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "treatment": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "concept": ["story_researcher", "story_architect", "character_designer", "dialog_writer"],
    "first_draft": ["story_architect", "character_designer", "dialog_writer"],
}

# ── Story Bible schema (structured output for canon tracking) ─────────────

STORY_BIBLE_SCHEMA = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "status": {"type": "string"},
                    "key_decisions": {"type": "array", "items": {"type": "string"}},
                    "relationships": {"type": "array", "items": {"type": "string"}},
                    "voice_directives": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "when": {"type": "string"},
                    "what": {"type": "string"},
                    "source": {"type": "string"},
                    "status": {"type": "string", "enum": ["established", "tbd"]},
                },
            },
        },
        "canon_facts": {"type": "array", "items": {"type": "string"}},
        "world_rules": {"type": "array", "items": {"type": "string"}},
        "changelog": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transition": {"type": "string"},
                    "added": {"type": "array", "items": {"type": "string"}},
                    "changed": {"type": "array", "items": {"type": "string"}},
                    "dropped": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


class WritersRoomLeaderBlueprint(LeaderBlueprint):
    name = "Writers Room Showrunner"
    slug = "leader"
    description = "Writers Room showrunner — orchestrates creative/feedback ping-pong loop across stages from pitch to first draft"
    tags = ["leadership", "writers-room", "orchestration", "screenplay", "novel", "creative-writing"]
    config_schema = {}

    def get_volume_threshold(self, agent) -> int:
        from agents.blueprints.writers_room.workforce.base import _get_writers_room_volume_threshold

        return _get_writers_room_volume_threshold(agent)

    @property
    def system_prompt(self) -> str:
        return """You are the Showrunner of a professional writers room. You orchestrate a creative team, a lead writer, and a feedback team in a disciplined loop.

CREATIVE TEAM (they generate raw material):
- story_researcher: market research, comps, world-building research, fact-checking
- story_architect: story structure, beats, act breaks, narrative architecture
- character_designer: character arcs, relationships, ensemble design, voices
- dialog_writer: dialogue, scenes, voice work, tonal samples

LEAD WRITER (synthesizer):
- lead_writer: takes ALL creative agents' output and synthesizes it into a single cohesive stage deliverable. The lead writer does NOT invent new elements — they weave the creative team's work into one document.

FEEDBACK TEAM (they analyze — mirrors professional script coverage):
- market_analyst: market fit, comps, platform alignment, zeitgeist
- structure_analyst: framework-based structural analysis (Save the Cat, McKee, etc.)
- character_analyst: character consistency, arcs, motivation, relationships
- dialogue_analyst: voice, subtext, scene construction, exposition
- format_analyst: craft conventions, formatting, pacing
- production_analyst: budget, cast-ability, feasibility, IP potential

CREATIVE REVIEWER (quality gate):
- creative_reviewer: consolidates all feedback, scores dimensions, issues verdict

THE LOOP (each stage):
1. Assign creative agents to write raw material for the current stage
2. When creative writing is done, assign the lead_writer to synthesize a deliverable
3. Lead writer's output becomes the Stage Deliverable document; creative agents' raw output becomes Research & Notes
4. Assign feedback agents to analyze the deliverable (per depth matrix)
5. When feedback is done, assign creative_reviewer to consolidate and score
6. Score >= 9.5/10 → advance. Score >= 9.0 after 3 polish attempts → accept (diminishing returns).
7. On rejection: create a Critique document, then loop back to step 1 with all creative agents re-writing
8. On acceptance: create a Critique document, advance to next stage
9. Repeat until terminal stage is reached with passing scores

THREE DOCUMENTS PER ROUND:
- Stage Deliverable: the lead writer's synthesized output (the "official" document for this stage)
- Research & Notes: raw creative agents' output preserved for reference
- Critique: feedback agents' analysis + creative reviewer's verdict (created after review)

FORMAT DETECTION:
On first invocation, the system detects whether the project is standalone (movie, book, play) or series (TV, web series). For series, the "treatment" stage position is occupied by "concept" (series bible). The terminal stage comes from format detection.

STAGE PIPELINE: pitch -> expose -> treatment/concept -> first_draft

LOCALE: All agents output in the configured locale. This is non-negotiable."""

    # ── Register commands ────────────────────────────────────────────────
    plan_room = plan_room
    check_progress = check_progress

    def get_context(self, agent):
        ctx = super().get_context(agent)
        # Leader doesn't need sibling reports or own task history in task context —
        # its orchestration runs through generate_task_proposal which builds its own prompt
        ctx["sibling_agents"] = ""
        ctx["own_recent_tasks"] = ""
        return ctx

    # ── Task execution (uses base class delegation with stage context) ──

    def _get_delegation_context(self, agent):
        sprint = self._get_current_sprint(agent)
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        stage_status = dept_state.get("stage_status", {})
        current_stage = dept_state.get("current_stage", STAGES[0])

        context = (
            f"# Current Stage: {current_stage}\n"
            f"# Stage Status: {json.dumps(stage_status, indent=2)}\n"
            f"# Quality: Excellence threshold {EXCELLENCE_THRESHOLD}/10 (average dimension score)"
        )

        # Inject story bible if one exists
        sprint = self._get_current_sprint(agent)
        if sprint:
            from projects.models import Output

            bible_output = Output.objects.filter(
                sprint=sprint,
                department=agent.department,
                label="story_bible",
            ).first()
            if bible_output and bible_output.content:
                context += f"\n\n## Story Bible (CANON — do not contradict)\n" f"{bible_output.content}"

        return context

    # ── Helper methods ──────────────────────────────────────────────────

    def _get_effective_stage(self, agent, current_stage: str, sprint=None) -> str:
        """For series at treatment position, return 'concept' for matrix lookups."""
        if sprint is None:
            sprint = self._get_current_sprint(agent)
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        format_type = dept_state.get("format_type", "standalone")
        if current_stage == "treatment" and format_type == "series":
            return "concept"
        return current_stage

    def _get_current_sprint(self, agent):
        from projects.models import Sprint

        return (
            Sprint.objects.filter(
                departments=agent.department,
                status=Sprint.Status.RUNNING,
            )
            .order_by("updated_at")
            .first()
        )

    def _render_story_bible(self, data: dict) -> str:
        """Render structured bible JSON to markdown."""
        sections = []

        # Characters
        characters = data.get("characters", [])
        if characters:
            lines = ["## Characters\n"]
            for char in characters:
                lines.append(f"### {char.get('name', 'Unknown')}")
                if char.get("role"):
                    lines.append(f"- **Role:** {char['role']}")
                if char.get("status"):
                    lines.append(f"- **Status:** {char['status']}")
                decisions = char.get("key_decisions", [])
                if decisions:
                    lines.append("- **Key Decisions:**")
                    for d in decisions:
                        lines.append(f"  - {d}")
                relationships = char.get("relationships", [])
                if relationships:
                    lines.append("- **Relationships:**")
                    for r in relationships:
                        lines.append(f"  - {r}")
                directives = char.get("voice_directives", [])
                if directives:
                    lines.append("- **Voice Directives:**")
                    for v in directives:
                        lines.append(f"  - {v}")
                lines.append("")
            sections.append("\n".join(lines))

        # Timeline
        timeline = data.get("timeline", [])
        if timeline:
            lines = ["## Timeline\n"]
            lines.append("| When | What | Source | Status |")
            lines.append("|------|------|--------|--------|")
            for entry in timeline:
                status_tag = "[ESTABLISHED]" if entry.get("status") == "established" else "[TBD]"
                lines.append(
                    f"| {entry.get('when', '')} | {entry.get('what', '')} "
                    f"| {entry.get('source', '')} | {status_tag} |"
                )
            lines.append("")
            sections.append("\n".join(lines))

        # Canon Facts
        canon_facts = data.get("canon_facts", [])
        if canon_facts:
            lines = ["## Established Facts (Canon)\n"]
            for fact in canon_facts:
                lines.append(f"- {fact}")
            lines.append("")
            sections.append("\n".join(lines))

        # World Rules
        world_rules = data.get("world_rules", [])
        if world_rules:
            lines = ["## World Rules\n"]
            for rule in world_rules:
                lines.append(f"- {rule}")
            lines.append("")
            sections.append("\n".join(lines))

        # Changelog
        changelog = data.get("changelog", [])
        if changelog:
            lines = ["## Stage Changelog\n"]
            for entry in changelog:
                lines.append(f"### {entry.get('transition', 'Unknown')}")
                added = entry.get("added", [])
                if added:
                    lines.append("- **Added:**")
                    for a in added:
                        lines.append(f"  - {a}")
                changed = entry.get("changed", [])
                if changed:
                    lines.append("- **Changed:**")
                    for c in changed:
                        lines.append(f"  - {c}")
                dropped = entry.get("dropped", [])
                if dropped:
                    lines.append("- **Dropped:**")
                    for d in dropped:
                        lines.append(f"  - {d}")
                lines.append("")
            sections.append("\n".join(lines))

        return "# Story Bible\n\n" + "\n".join(sections) if sections else "# Story Bible\n\n(No content yet)"

    def _update_story_bible(self, agent, sprint, stage: str):
        """Generate or update the story bible after a stage passes."""
        from agents.ai.claude_client import call_claude_structured
        from projects.models import Output

        effective_stage = self._get_effective_stage(agent, stage, sprint=sprint)

        deliverable_doc = (
            Document.objects.filter(
                department=agent.department,
                doc_type="stage_deliverable",
                is_archived=False,
            )
            .order_by("-created_at")
            .first()
        )
        deliverable_text = deliverable_doc.content if deliverable_doc else ""

        if not deliverable_text:
            logger.warning("Story Bible: no deliverable found for stage '%s' — skipping", stage)
            return

        existing_bible = Output.objects.filter(
            sprint=sprint,
            department=agent.department,
            label="story_bible",
        ).first()
        previous_bible = existing_bible.content if existing_bible else ""

        voice_doc = (
            Document.objects.filter(
                department=agent.department,
                doc_type="voice_profile",
                is_archived=False,
            )
            .order_by("-created_at")
            .first()
        )
        voice_text = voice_doc.content if voice_doc else ""

        user_parts = [f"## Stage: {effective_stage}\n"]
        if previous_bible:
            user_parts.append(f"## Previous Story Bible\n{previous_bible}\n")
        user_parts.append(f"## Stage Deliverable\n{deliverable_text}\n")
        if voice_text:
            user_parts.append(f"## Voice Profile\n{voice_text}\n")
        user_message = "\n".join(user_parts)

        system_prompt = (
            "You are extracting and updating a story bible from creative writing deliverables.\n\n"
            "Extract every fact, character decision, relationship, and world rule. "
            "Be exhaustive — anything not in the bible does not exist for future stages.\n\n"
            "Mark items as 'established' (dramatized in a deliverable) or 'tbd' "
            "(mentioned but not yet dramatized).\n\n"
            "EXTRACTION RULES:\n"
            "- Extract new facts established in this deliverable\n"
            "- Identify what changed from the previous bible\n"
            "- Flag anything dropped (present in prior bible but contradicted or absent)\n"
            "- Populate the changelog with added/changed/dropped\n"
            "- Flip 'tbd' items to 'established' when dramatized in the deliverable\n"
            "- Flag 'tbd' items that should have been resolved by this stage but weren't\n"
            "- Incorporate voice directives from the voice profile for each character\n\n"
            "Be specific and concrete. Names, places, decisions — not summaries."
        )

        bible_data, usage = call_claude_structured(
            system_prompt=system_prompt,
            user_message=user_message,
            output_schema=STORY_BIBLE_SCHEMA,
            tool_name="update_story_bible",
            tool_description="Submit the updated story bible with all extracted facts",
            max_tokens=8192,
        )

        bible_markdown = self._render_story_bible(bible_data)

        Output.objects.update_or_create(
            sprint=sprint,
            department=agent.department,
            label="story_bible",
            defaults={
                "title": "Story Bible",
                "output_type": "markdown",
                "content": bible_markdown,
            },
        )
        logger.info("Story Bible: updated for stage '%s' (sprint %s)", stage, sprint.id)

    # ── Revision application ───────────────────────────────────────────

    def _apply_revisions(self, document_content: str, revisions: list[dict]) -> tuple[str, list[dict]]:
        """Apply structured edits to a document.

        Returns (revised_content, failed_edits).
        Failed edits are skipped — the quality loop handles retry.
        """
        result = document_content
        failed = []

        for rev in revisions:
            rev_type = rev.get("type", "replace")

            if rev_type == "replace":
                old = rev.get("old_text", "")
                new = rev.get("new_text", "")
                if not old:
                    continue
                count = result.count(old)
                if count == 1:
                    result = result.replace(old, new, 1)
                elif count == 0:
                    failed.append({"text": old[:80], "reason": "not_found"})
                else:
                    failed.append({"text": old[:80], "reason": f"ambiguous ({count} matches)"})

            elif rev_type == "replace_section":
                header = rev.get("section", "")
                new_content = rev.get("new_content", "")
                result, ok = self._replace_section(result, header, new_content)
                if not ok:
                    failed.append({"text": header, "reason": "section_not_found"})

            elif rev_type == "replace_between":
                start = rev.get("start", "")
                end = rev.get("end", "")
                new_content = rev.get("new_content", "")
                result, ok = self._replace_between(result, start, end, new_content)
                if not ok:
                    failed.append({"text": f"{start[:40]}...{end[:40]}", "reason": "anchors_not_found"})

        return result, failed

    @staticmethod
    def _replace_section(content: str, header: str, new_content: str) -> tuple[str, bool]:
        """Replace content under a markdown header until the next same-level header."""
        if header not in content:
            return content, False

        level = len(header) - len(header.lstrip("#"))
        if level == 0:
            return content, False

        start_idx = content.index(header)
        after_header = start_idx + len(header)

        # Find next header of same or higher level
        end_offset = len(content)
        remaining = content[after_header:]
        search_pos = 0
        for line in remaining.split("\n"):
            line_start = after_header + search_pos
            stripped = line.lstrip()
            if stripped.startswith("#") and search_pos > 0:
                line_level = len(stripped) - len(stripped.lstrip("#"))
                if line_level <= level and line_level > 0:
                    end_offset = line_start
                    break
            search_pos += len(line) + 1

        result = content[:start_idx] + header + "\n\n" + new_content + "\n\n" + content[end_offset:]
        return result, True

    @staticmethod
    def _replace_between(content: str, start: str, end: str, new_content: str) -> tuple[str, bool]:
        """Replace everything between two anchor texts (inclusive)."""
        if not start or not end:
            return content, False
        if content.count(start) != 1 or content.count(end) != 1:
            return content, False

        start_idx = content.index(start)
        end_idx = content.index(end, start_idx)
        end_idx += len(end)

        if start_idx >= end_idx:
            return content, False

        result = content[:start_idx] + new_content + content[end_idx:]
        return result, True

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Strip markdown code fences (```json ... ```) from LLM output."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Remove opening fence (```json, ```JSON, ``` etc.)
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        return stripped.strip()

    def _apply_revision_or_replace(self, agent, doc_type: str, new_content: str, stage: str) -> tuple[str, bool]:
        """Try to parse new_content as revision JSON and apply to existing doc.

        Returns (final_content, was_revision_applied).
        If new_content is not valid revision JSON, returns it as-is for full replacement.
        CRITICAL: never return raw revision JSON as deliverable content.
        """
        # Strip markdown code fences — LLMs routinely wrap JSON in ```json ... ```
        cleaned = self._strip_code_fences(new_content)

        data = self._try_parse_revision_json(cleaned)
        if data is not None:
            effective = self._get_effective_stage(agent, stage)
            stage_display = effective.replace("_", " ").title()
            existing_doc = Document.objects.filter(
                department=agent.department,
                doc_type=doc_type,
                is_archived=False,
                title__startswith=f"{stage_display} v",
            ).first()
            if existing_doc and existing_doc.content:
                revised, failed = self._apply_revisions(existing_doc.content, data["revisions"])
                if failed:
                    logger.warning(
                        "Writers Room: %d revision(s) failed for %s: %s",
                        len(failed),
                        doc_type,
                        failed,
                    )
                return revised, True
            # Revision JSON but no existing doc — return existing content, never raw JSON.
            logger.error(
                "Writers Room: revision JSON received for %s but no existing %s document found. "
                "Cannot apply revisions without a base document.",
                stage,
                doc_type,
            )
            if existing_doc:
                return existing_doc.content, False
            return "", False

        # _try_parse_revision_json raises ValueError if it looks like revision
        # JSON but can't be parsed. If we reach here, it's genuinely not JSON.
        return new_content, False

    @staticmethod
    def _looks_like_revision_json(text: str) -> bool:
        """Heuristic: does this text look like revision JSON that failed to parse?"""
        stripped = text.strip()
        return stripped.startswith("{") and '"revisions"' in stripped[:200]

    @staticmethod
    def _try_parse_revision_json(text: str) -> dict | None:
        """Try to parse revision JSON, repairing common LLM errors.

        LLMs writing JSON with embedded natural-language text (especially German
        dialogue with „..." quotes) routinely produce unescaped ASCII double quotes
        inside string values.  We attempt a direct parse first, then repair and
        retry so json.loads handles all unescaping (\n, \t, unicode escapes, etc.).

        CRITICAL: If the text looks like revision JSON but cannot be parsed even
        after repair, this RAISES ValueError. Silent degradation is forbidden —
        the task must fail and be retried or escalated.
        """
        is_revision_json = text.strip().startswith("{") and '"revisions"' in text[:200]

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "revisions" in data and isinstance(data["revisions"], list):
                return data
        except (ValueError, TypeError):
            pass

        if not is_revision_json:
            return None

        # Repair strategy: escape unescaped double quotes inside JSON string values.
        try:
            repaired = WritersRoomLeaderBlueprint._repair_json_quotes(text)
            data = json.loads(repaired)
            if isinstance(data, dict) and "revisions" in data and isinstance(data["revisions"], list):
                logger.info(
                    "Writers Room: repaired malformed revision JSON — %d revisions",
                    len(data["revisions"]),
                )
                return data
        except (ValueError, TypeError):
            pass
        except Exception:
            logger.exception("Writers Room: JSON repair crashed")

        # Text IS revision JSON but cannot be parsed. FAIL HARD.
        raise ValueError(
            f"Writers Room: revision JSON could not be parsed even after repair. "
            f"This means the lead writer's revisions are LOST — the deliverable "
            f"will not improve. Failing task for retry. First 300 chars: {text[:300]}"
        )

    @staticmethod
    def _repair_json_quotes(text: str) -> str:
        """Escape unescaped double quotes inside JSON string values.

        Walks the text tracking in-string state. A " inside a string is
        "structural" (ends the string) if the character after the closing "
        is one of: , : ] } or whitespace-then-structural. Otherwise it's
        a content quote that needs escaping.

        This preserves all JSON escape sequences (\\n, \\t, \\", \\\\, etc.)
        so json.loads can unescape them properly.
        """
        chars = list(text)
        result = []
        i = 0
        in_string = False

        while i < len(chars):
            c = chars[i]

            if not in_string:
                result.append(c)
                if c == '"':
                    in_string = True
                i += 1
                continue

            # Inside a JSON string
            if c == "\\":
                # Escaped character — pass through both chars
                result.append(c)
                if i + 1 < len(chars):
                    i += 1
                    result.append(chars[i])
                i += 1
                continue

            if c == '"':
                # Is this the real end of the string, or a content quote?
                # Look ahead past whitespace for a JSON structural char.
                j = i + 1
                while j < len(chars) and chars[j] in (" ", "\t", "\r", "\n"):
                    j += 1

                is_structural = False
                if j >= len(chars) or chars[j] in ("]", "}", ":"):
                    is_structural = True
                elif chars[j] == ",":
                    # Comma after quote — structural only if followed by
                    # whitespace + quote (next JSON key/value) or whitespace + }]
                    # NOT structural if followed by a regular word like
                    # „SpreeTerrassen", Container-Büro
                    k = j + 1
                    while k < len(chars) and chars[k] in (" ", "\t", "\r", "\n"):
                        k += 1
                    if k < len(chars) and chars[k] in ('"', "]", "}", "{", "["):
                        is_structural = True
                    # else: comma followed by a regular word = content

                if is_structural:
                    result.append(c)
                    in_string = False
                else:
                    # Content quote — escape it
                    result.append("\\")
                    result.append('"')
                i += 1
                continue

            result.append(c)
            i += 1

        return "".join(result)

    # ── Task proposal (called by beat/continuous mode) ───────────────────

    def generate_task_proposal(self, agent: Agent) -> dict | None:
        """
        Core orchestration: determine what needs to happen next in the
        ping-pong loop and propose the appropriate task(s).
        """
        from agents.models import AgentTask
        from projects.models import Sprint

        # Gate on running sprints — no sprints, no work
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

        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)

        # Initialize: format detection on first invocation
        current_stage = dept_state.get("current_stage")
        if not current_stage:
            if not dept_state.get("entry_detected"):
                detection = _run_format_detection(agent, sprint)
                dept_state = sprint.get_department_state(dept_id)  # re-read after save
                entry_stage = detection.get("entry_stage", "pitch")
            else:
                entry_stage = STAGES[0]

            current_stage = entry_stage
            dept_state["current_stage"] = current_stage
            dept_state["stage_status"] = {}
            dept_state["current_iteration"] = 0
            sprint.set_department_state(dept_id, dept_state)

        stage_status = dept_state.get("stage_status", {})
        current_info = stage_status.get(current_stage, {})
        terminal_stage = dept_state.get("terminal_stage", "treatment")
        format_type = dept_state.get("format_type", "standalone")  # noqa: F841

        # Check if current stage passed — advance
        if current_info.get("status") == "passed":
            next_stg = _next_stage(current_stage)
            # For series at treatment position, check if terminal is "concept"
            effective_terminal = terminal_stage
            if effective_terminal == "concept":
                effective_terminal = "treatment"  # concept occupies treatment's slot
            if not next_stg or STAGES.index(current_stage) >= STAGES.index(effective_terminal):
                logger.info("Writers Room: target stage '%s' reached — done", terminal_stage)
                return None
            current_stage = next_stg
            dept_state["current_stage"] = current_stage
            dept_state["current_iteration"] = 0
            current_info = stage_status.get(current_stage, {})
            sprint.set_department_state(dept_id, dept_state)

        # Check for active tasks in the department
        active_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                status__in=[
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.QUEUED,
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

        # NOTE: max review rounds cap is checked AFTER the creative reviewer scores,
        # not here. This ensures every round completes with deliverable + critique.

        effective_stage = self._get_effective_stage(agent, current_stage, sprint=sprint)
        config = _get_merged_config(agent)

        # ── State machine ───────────────────────────────────────────────

        if status == "not_started":
            # Step 1: Assign creative agents to write
            return _tag_sprint(self._propose_creative_tasks(agent, effective_stage, config, sprint=sprint))

        if status == "voice_profiling":
            # Voice profiling done → now dispatch the real creative agents
            logger.info(
                "Writers Room: stage '%s' voice profiling complete — dispatching creative agents",
                current_stage,
            )
            stage_status[current_stage]["status"] = "not_started"
            dept_state["stage_status"] = stage_status
            sprint.set_department_state(dept_id, dept_state)
            return _tag_sprint(self._propose_creative_tasks(agent, effective_stage, config, sprint=sprint))

        if status == "creative_writing":
            # Creative agents done → dispatch lead writer to synthesize
            logger.info(
                "Writers Room: stage '%s' creative writing complete — dispatching lead writer",
                current_stage,
            )
            stage_status[current_stage]["status"] = "lead_writing_pending"
            dept_state["stage_status"] = stage_status
            sprint.set_department_state(dept_id, dept_state)
            return _tag_sprint(self._propose_lead_writer_task(agent, current_stage, config, sprint=sprint))

        if status == "lead_writing_pending":
            # Lead writer dispatch retry
            return _tag_sprint(self._propose_lead_writer_task(agent, current_stage, config, sprint=sprint))

        if status == "lead_writing":
            # Verify lead_writer actually completed before proceeding
            lead_writer_done = AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type="lead_writer",
                status=AgentTask.Status.DONE,
            ).exists()
            if not lead_writer_done:
                logger.warning(
                    "Writers Room: stage '%s' status is 'lead_writing' but no completed "
                    "lead_writer task found — waiting",
                    current_stage,
                )
                return None

            # Lead writer done → create docs, dispatch deliverable gate
            logger.info(
                "Writers Room: stage '%s' lead writing complete — dispatching deliverable gate",
                current_stage,
            )
            self._create_deliverable_and_research_docs(agent, current_stage, sprint)
            stage_status[current_stage]["status"] = "deliverable_gate"
            dept_state["stage_status"] = stage_status
            sprint.set_department_state(dept_id, dept_state)
            return _tag_sprint(self._propose_deliverable_gate_task(agent, current_stage, config))

        if status == "deliverable_gate":
            # Deliverable gate done → dispatch feedback agents
            logger.info(
                "Writers Room: stage '%s' deliverable gate passed — dispatching feedback",
                current_stage,
            )
            stage_status[current_stage]["status"] = "deliverable_gate_done"
            dept_state["stage_status"] = stage_status
            sprint.set_department_state(dept_id, dept_state)
            return _tag_sprint(self._propose_feedback_tasks(agent, effective_stage, config, sprint=sprint))

        if status == "deliverable_gate_done":
            # Feedback dispatch retry
            return _tag_sprint(self._propose_feedback_tasks(agent, effective_stage, config, sprint=sprint))

        if status == "feedback":
            # Feedback done → dispatch creative_reviewer
            logger.info(
                "Writers Room: stage '%s' feedback complete — dispatching review",
                current_stage,
            )
            stage_status[current_stage]["status"] = "feedback_done"
            dept_state["stage_status"] = stage_status
            sprint.set_department_state(dept_id, dept_state)
            return _tag_sprint(self._propose_review_task(agent, effective_stage, config, sprint=sprint))

        if status == "feedback_done":
            return _tag_sprint(self._propose_review_task(agent, effective_stage, config, sprint=sprint))

        if status == "review":
            # creative_reviewer completed — check verdict before advancing
            review_task = (
                AgentTask.objects.filter(
                    agent__department=agent.department,
                    agent__agent_type="creative_reviewer",
                    status=AgentTask.Status.DONE,
                )
                .order_by("-completed_at")
                .first()
            )
            if review_task and review_task.review_score is not None:
                stage_key = f"wr_{current_stage}"
                accepted, polish_count, round_num = self._apply_quality_gate(
                    agent,
                    sprint,
                    review_task.review_score,
                    stage_key,
                )
                if not accepted:
                    # Max rounds cap — fire AFTER review so deliverable + critique exist
                    if iteration >= MAX_REVIEW_ROUNDS:
                        logger.warning(
                            "Writers Room: stage '%s' hit max rounds (%d), score %.1f — completing sprint",
                            current_stage,
                            MAX_REVIEW_ROUNDS,
                            review_task.review_score,
                        )
                        self._create_critique_doc(agent, current_stage, sprint)
                        from django.utils import timezone as tz

                        from projects.views.sprint_view import _broadcast_sprint

                        sprint.status = Sprint.Status.DONE
                        sprint.completion_summary = (
                            f"Stage '{current_stage}' completed after {iteration} rounds "
                            f"(score {review_task.review_score:.1f}). "
                            f"Deliverable and critique preserved in documents."
                        )
                        sprint.completed_at = tz.now()
                        sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])
                        _broadcast_sprint(sprint, "sprint.updated")
                        return None

                    logger.info(
                        "Writers Room: stage '%s' review score %.1f — looping back (round %d)",
                        current_stage,
                        review_task.review_score,
                        round_num,
                    )
                    # Increment round tracking
                    review_rounds = dept_state.get("review_rounds", {})
                    review_rounds[stage_key] = round_num + 1
                    dept_state["review_rounds"] = review_rounds
                    dept_state["active_review_key"] = stage_key
                    sprint.set_department_state(dept_id, dept_state)
                    return _tag_sprint(
                        self._propose_fix_task(agent, review_task, review_task.review_score, round_num, polish_count)
                    )

            self._create_critique_doc(agent, current_stage, sprint)
            self._update_story_bible(agent, sprint, current_stage)
            current_info["status"] = "passed"
            stage_status[current_stage] = current_info
            dept_state["stage_status"] = stage_status

            next_stg = _next_stage(current_stage)
            effective_terminal = terminal_stage
            if effective_terminal == "concept":
                effective_terminal = "treatment"
            if next_stg and STAGES.index(current_stage) < STAGES.index(effective_terminal):
                dept_state["current_stage"] = next_stg
                dept_state["current_iteration"] = 0
                logger.info(
                    "Writers Room: stage '%s' PASSED — advancing to '%s'",
                    current_stage,
                    next_stg,
                )
                sprint.set_department_state(dept_id, dept_state)
                next_effective = self._get_effective_stage(agent, next_stg, sprint=sprint)
                return _tag_sprint(self._propose_creative_tasks(agent, next_effective, config, sprint=sprint))

            logger.info("Writers Room: target stage '%s' PASSED — sprint complete", current_stage)
            sprint.set_department_state(dept_id, dept_state)

            # Auto-complete the sprint
            from django.utils import timezone as tz

            sprint.status = Sprint.Status.DONE
            sprint.completion_summary = (
                f"Target stage '{terminal_stage}' reached and passed review. "
                f"Writers room completed all planned stages."
            )
            sprint.completed_at = tz.now()
            sprint.save(update_fields=["status", "completion_summary", "completed_at", "updated_at"])

            from projects.views.sprint_view import _broadcast_sprint

            _broadcast_sprint(sprint, "sprint.updated")
            logger.info("Writers Room: auto-completed sprint '%s'", sprint.text[:60])

            return None

        # Fallback: if status is unknown, start fresh
        logger.warning("Writers Room: unknown status '%s' for '%s', resetting", status, current_stage)
        stage_status[current_stage] = {"status": "not_started", "iterations": 0}
        dept_state["stage_status"] = stage_status
        sprint.set_department_state(dept_id, dept_state)
        return _tag_sprint(self._propose_creative_tasks(agent, effective_stage, config, sprint=sprint))

    # ── Creative task proposal ──────────────────────────────────────────

    def _propose_creative_tasks(self, agent: Agent, stage: str, config: dict, sprint=None) -> dict:
        """Create writing tasks for the current stage's creative agents."""
        # ── Voice profiling gate ────────────────────────────────────────
        # Before any creative writing begins, ensure a Voice DNA profile exists.
        has_voice_profile = Document.objects.filter(
            department=agent.department,
            doc_type="voice_profile",
            is_archived=False,
        ).exists()

        if not has_voice_profile:
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
                # Resolve the real current_stage for _on_dispatch
                if sprint is None:
                    sprint = self._get_current_sprint(agent)
                dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
                dispatch_stage = dept_state.get("current_stage", stage)
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
                    "_on_dispatch": {"set_status": "voice_profiling", "stage": dispatch_stage},
                }

        # Filter to only active agents in this department
        active_types = set(
            agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
        )
        creative_agents = [a for a in CREATIVE_MATRIX.get(stage, []) if a in active_types]

        if not creative_agents:
            logger.warning("Writers Room: no active creative agents for stage '%s' — skipping", stage)
            if sprint is None:
                sprint = self._get_current_sprint(agent)
            dept_id = str(agent.department_id)
            dept_state = sprint.get_department_state(dept_id) if sprint else {}
            # Use current_stage (always a STAGES member), not effective stage which may be "concept"
            real_stage = dept_state.get("current_stage", stage)
            stage_status = dept_state.get("stage_status", {})
            stage_status[real_stage] = {"status": "passed", "iterations": 0}
            dept_state["stage_status"] = stage_status
            next_stg = _next_stage(real_stage)
            if next_stg:
                dept_state["current_stage"] = next_stg
            if sprint:
                sprint.set_department_state(dept_id, dept_state)
            if next_stg:
                next_effective = self._get_effective_stage(agent, next_stg, sprint=sprint)
                return self._propose_creative_tasks(agent, next_effective, config, sprint=sprint)
            return None

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
            "pitch": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Market research, comps, and positioning analysis for the pitch",
                    "step_plan": (
                        "Research the competitive landscape for this project. Analyze:\n"
                        "1. Comparable titles — what worked, what didn't, and why\n"
                        "2. Market positioning — where does this project sit? What's oversaturated vs. underserved?\n"
                        "3. Platform appetite — what are buyers commissioning right now?\n"
                        "4. Zeitgeist hooks — what cultural currents can this project ride?\n"
                        "5. Audience demographics — who is the target audience?\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "story_architect": {
                    "command_name": "develop_concept",
                    "exec_summary": "Develop the story premise, structure skeleton, and dramatic engine",
                    "step_plan": (
                        "Develop the core structural foundation for the pitch:\n"
                        "1. Dramatic premise — the core tension that drives the story\n"
                        "2. World and setting — specific, vivid, grounded\n"
                        "3. Format recommendation — length, structure, episode count if series\n"
                        "4. Tonal compass — reference works, what to emulate and avoid\n"
                        "5. Thematic spine — what is this really ABOUT beneath the plot\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Design the core ensemble — protagonist, antagonist, key relationships",
                    "step_plan": (
                        "Design the initial character ensemble for the pitch:\n"
                        "1. Protagonist sketch — who are we following, what do they want, what's in their way\n"
                        "2. Key antagonist — what they want, why they're formidable\n"
                        "3. Central relationship — the engine of the story\n"
                        "4. Supporting cast overview — functional roles, distinct voices\n"
                        "5. Character dynamics that create scenes — what happens when X meets Y\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write_content",
                    "exec_summary": "Craft the pitch hook — logline variants and tone sample",
                    "step_plan": (
                        "Write the pitch's selling language:\n"
                        "1. 3-5 logline variants — tight, hooky, sellable (each under 50 words)\n"
                        "2. Each logline must contain: protagonist + flaw, inciting incident, conflict, stakes\n"
                        "3. A short tone sample (1 page max) — a scene or moment that captures the voice\n"
                        "4. Brief rationale for each logline variant\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
            },
            "expose": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Deepen research for the expose — world-building and thematic depth",
                    "step_plan": (
                        "Deepen the research foundation for the expose:\n"
                        "1. Verify and expand world-building details — locations, institutions, power structures\n"
                        "2. Research thematic parallels — real-world events, social dynamics\n"
                        "3. Identify narrative opportunities from real research\n"
                        "4. Check character backstories against real-world plausibility\n"
                        "5. Surface details that will make the expose feel grounded\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "story_architect": {
                    "command_name": "write_structure",
                    "exec_summary": "Write the expose narrative — 3-5 page compelling overview",
                    "step_plan": (
                        "Write the expose — a 3-5 page compelling narrative summary:\n"
                        "1. Opening hook — drop us into the world and protagonist's situation\n"
                        "2. Act structure — setup, escalation, climax, resolution (broad strokes)\n"
                        "3. Character arcs — how do the main characters change?\n"
                        "4. World and tone — make the reader FEEL the show, not just understand it\n"
                        "5. The promise — why does this story sustain engagement?\n"
                        "6. Emotional throughline — what journey does the audience go on?\n\n"
                        "This is a SELLING document. Every paragraph should make the reader want the next one.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Expand character ensemble with detailed arcs and relationships",
                    "step_plan": (
                        "Expand the character ensemble for the expose:\n"
                        "1. Each major character — background, motivation, fatal flaw, arc trajectory\n"
                        "2. Relationship map — who conflicts with whom, what alliances shift\n"
                        "3. Character dynamics that generate scenes and conflict\n"
                        "4. Supporting cast — functional roles, distinct voices, potential for development\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write_content",
                    "exec_summary": "Write 2-3 proof-of-concept dialogue scenes for the expose",
                    "step_plan": (
                        "Write 2-3 short dialogue scenes (each 1-2 pages) that showcase voice:\n"
                        "1. A scene that establishes the protagonist's voice and worldview\n"
                        "2. A scene of conflict between two central characters\n"
                        "3. (Optional) A scene showing tonal range — humor within drama or vice versa\n\n"
                        "These answer: 'What does this project SOUND like?' Each character must have "
                        "a distinct speech pattern and vocabulary.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
            },
            "treatment": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Treatment-level research — episode opportunities and world texture",
                    "step_plan": (
                        "Provide treatment-level research support:\n"
                        "1. Verify all real-world references — locations, institutions, cultural details\n"
                        "2. Research episode-level story opportunities — real events, milieu specifics\n"
                        "3. Identify plot engines from real-world dynamics (legal, financial, political)\n"
                        "4. Provide texture for B-plots — subcultures, side worlds, parallel stories\n"
                        "5. Flag research gaps that would undermine credibility\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "story_architect": {
                    "command_name": "write_structure",
                    "exec_summary": "Write the treatment — detailed narrative breakdown",
                    "step_plan": (
                        "Write the treatment — a detailed narrative breakdown:\n"
                        "1. Season/story arc — the macro story from opening to finale\n"
                        "2. Episode/chapter breakdown (1-2 paragraphs each) — what happens, what changes\n"
                        "3. A/B/C plot weaving — how storylines intersect and build\n"
                        "4. Act breaks and cliffhangers — what pulls the audience forward?\n"
                        "5. Midpoint shift — what reversal redefines the story at the midpoint?\n"
                        "6. Finale setup — how does everything converge?\n\n"
                        "This must read as a story, not a list.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Map detailed character arcs across the treatment structure",
                    "step_plan": (
                        "Map each major character's arc across the treatment structure:\n"
                        "1. Per character: emotional state at opening, key turning points, state at finale\n"
                        "2. Relationship evolution — how do key dynamics shift?\n"
                        "3. Character reveals — when does the audience learn key backstory?\n"
                        "4. Internal vs. external conflict — how do they diverge and reconnect?\n"
                        "5. Supporting cast arcs — who rises, who falls, who surprises?\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write_content",
                    "exec_summary": "Write signature dialogue moments for key treatment beats",
                    "step_plan": (
                        "Write dialogue for 4-6 pivotal moments in the treatment:\n"
                        "1. The opening hook scene — first impression of protagonist and world\n"
                        "2. The central relationship's defining confrontation\n"
                        "3. The midpoint revelation — the scene where everything changes\n"
                        "4. A quiet character moment — vulnerability, humor, or intimacy\n"
                        "5-6. Key scenes showcasing tonal range and secondary characters\n\n"
                        "Each scene should be 1-3 pages. Focus on subtext.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
            },
            "concept": {
                "story_researcher": {
                    "command_name": "research",
                    "exec_summary": "Series concept research — world bible material and franchise potential",
                    "step_plan": (
                        "Research for the series concept/bible:\n"
                        "1. World-building depth — the rules, institutions, and power structures of this world\n"
                        "2. Multi-season potential — what real-world dynamics sustain long-form storytelling?\n"
                        "3. Franchise opportunities — spin-offs, expanded universe, IP potential\n"
                        "4. Comparable series analysis — how did successful series in this space structure their bibles?\n"
                        "5. Cultural specificity — details that make this world unique and authentic\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "story_architect": {
                    "command_name": "write_structure",
                    "exec_summary": "Write the series concept — multi-season architecture and bible",
                    "step_plan": (
                        "Write the series concept/bible:\n"
                        "1. Series premise — the engine that generates episodes and seasons\n"
                        "2. Season 1 arc — complete story with a satisfying conclusion that opens doors\n"
                        "3. Future seasons roadmap — 2-3 sentence hooks for seasons 2-4\n"
                        "4. Episode structure — typical episode shape, recurring elements\n"
                        "5. World rules — what the audience learns, what stays hidden, mythology\n"
                        "6. Tone document — what this show feels like, reference touchstones\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Design the series ensemble with multi-season arcs",
                    "step_plan": (
                        "Design the full series ensemble:\n"
                        "1. Core cast — detailed profiles with multi-season arc potential\n"
                        "2. Recurring characters — who appears when, what they contribute\n"
                        "3. Character web — relationships that evolve across seasons\n"
                        "4. Casting notes — age, type, cultural specificity\n"
                        "5. Character voice guides — speech patterns, vocabulary, verbal tics\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write_content",
                    "exec_summary": "Write series voice samples — pilot scenes and tonal range",
                    "step_plan": (
                        "Write voice samples for the series concept:\n"
                        "1. The cold open — the first 3-5 pages that hook the audience\n"
                        "2. A character introduction scene — meet the protagonist in their world\n"
                        "3. A conflict scene — the central dynamic in action\n"
                        "4. A tonal contrast scene — show the range (humor in drama, tension in comedy)\n\n"
                        "These scenes demonstrate what the series SOUNDS like episode to episode.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
            },
            "first_draft": {
                "story_architect": {
                    "command_name": "write_structure",
                    "exec_summary": "Write the first draft — full pilot/opening chapter/screenplay",
                    "step_plan": (
                        "Write the complete first draft:\n"
                        "1. Professional format appropriate to the medium\n"
                        "2. Follow the treatment's structure but improve where inspiration strikes\n"
                        "3. Action/prose — visual, cinematic, economical\n"
                        "4. Integrate the dialog writer's voice work into natural flow\n"
                        "5. Pacing — the read should move. Cut or compress anything slow.\n"
                        "6. Target appropriate length for the format\n\n"
                        "This is a WRITER'S draft — prioritize voice, energy, and specificity over polish.\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "character_designer": {
                    "command_name": "write_characters",
                    "exec_summary": "Review and enhance character consistency across the full draft",
                    "step_plan": (
                        "Review the draft for character integrity:\n"
                        "1. Voice audit — does each character sound distinct throughout?\n"
                        "2. Motivation check — does every character action follow from wants/needs?\n"
                        "3. Arc tracking — are the character arcs landing?\n"
                        "4. Introduction effectiveness — do characters make strong first impressions?\n"
                        "5. Write enhanced versions of any scenes where characters feel generic\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
                "dialog_writer": {
                    "command_name": "write_content",
                    "exec_summary": "Dialogue dramatization pass — sharpen every exchange",
                    "step_plan": (
                        "Do a full dialogue dramatization pass:\n"
                        "1. Cut flab — remove any line that doesn't earn its place\n"
                        "2. Sharpen wit — punch up where the tone allows\n"
                        "3. Deepen subtext — where are characters saying exactly what they mean? Fix that.\n"
                        "4. Rhythm — vary sentence length, use fragments, interruptions, overlaps\n"
                        "5. Signature lines — does this draft have 3-5 lines people would quote?\n"
                        "6. Exposition surgery — is backstory delivered naturally?\n\n"
                        "Consult department documents for the latest stage deliverable and critique."
                    ),
                },
            },
        }

        tasks = []
        previous_depends = False
        # Resolve the real current_stage for _on_dispatch
        if sprint is None:
            sprint = self._get_current_sprint(agent)
        _dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        dispatch_stage = _dept_state.get("current_stage", stage)

        current_iterations = _dept_state.get("stage_status", {}).get(dispatch_stage, {}).get("iterations", 0)
        is_revision = current_iterations > 0

        for agent_type in creative_agents:
            spec = TASK_SPECS.get(stage, {}).get(agent_type)
            if not spec:
                raise ValueError(
                    f"No TASK_SPECS entry for stage '{stage}', agent '{agent_type}'. "
                    f"Every CREATIVE_MATRIX entry must have a corresponding TASK_SPECS entry."
                )

            if is_revision:
                # REVISION ROUND: agents focus ONLY on critique-driven improvements
                step_plan = (
                    f"Locale: {locale}\n{format_context}\n"
                    f"## REVISION ROUND {current_iterations + 1}\n\n"
                    "You have three inputs:\n"
                    "1. **Your initial research** (your previous output in department documents)\n"
                    "2. **The critique** for your department (what needs to change)\n"
                    "3. **The current deliverable** (what exists now)\n\n"
                    "Your job: produce TARGETED IMPROVEMENT SUGGESTIONS based on the critique.\n\n"
                    "FORMAT — output ONLY this:\n"
                    "For each issue the critique flags in your domain:\n"
                    "  1. Quote the critique point\n"
                    "  2. Quote the relevant passage from the deliverable\n"
                    "  3. Write your specific fix/improvement (the actual replacement text)\n\n"
                    "DO NOT:\n"
                    "- Reproduce your full initial research\n"
                    "- Rewrite sections the critique praised or didn't mention\n"
                    "- Add new analysis beyond what the critique asks for\n"
                    "- Repeat market positioning, comp analysis, or zeitgeist material\n\n"
                    "ONLY address what the critique flagged. Short, precise, actionable.\n\n"
                    f"Your output must be in {locale}."
                )
            else:
                # FIRST ROUND: full creative work
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
                step_plan = (
                    f"Locale: {locale}\n{format_context}\n"
                    f"{pitch_preamble}"
                    f"{spec['step_plan']}\n\n"
                    f"FIDELITY CHECK (before submitting): Re-read the creator's pitch. "
                    f"Does your output preserve EVERY specific element they provided? "
                    f"If you introduced characters, conflicts, or structures the creator "
                    f"did NOT mention, ask yourself: did I copy this from a reference show? "
                    f"If yes, delete it and build from the creator's actual material instead.\n\n"
                    f"Your output must be in {locale}. This is non-negotiable."
                )

            task_data = {
                "target_agent_type": agent_type,
                "command_name": spec.get("command_name", ""),
                "exec_summary": spec["exec_summary"],
                "step_plan": step_plan,
                "depends_on_previous": previous_depends,
            }

            tasks.append(task_data)
            if agent_type == "story_researcher":
                previous_depends = True

        return {
            "exec_summary": f"Stage '{stage}': assign creative agents to write",
            "tasks": tasks,
            "_on_dispatch": {"set_status": "creative_writing", "stage": dispatch_stage},
        }

    # ── Authenticity gate proposals ──────────────────────────────────────

    def _propose_deliverable_gate_task(self, agent, current_stage, config):
        """Dispatch authenticity_analyst to review the lead writer's deliverable."""
        return {
            "exec_summary": f"Authenticity gate for deliverable ({current_stage})",
            "tasks": [
                {
                    "target_agent_type": "authenticity_analyst",
                    "exec_summary": f"Authenticity gate: review {current_stage} deliverable",
                    "step_plan": (
                        "Review the stage deliverable for dramatic action. "
                        "Apply the full action-first methodology: scene retelling test, "
                        "causal chain verification, line-by-line logic test. "
                        "This is the gate before feedback agents see the deliverable."
                    ),
                    "command_name": "analyze",
                }
            ],
        }

    # ── Lead Writer task proposal ──────────────────────────────────────

    def _propose_lead_writer_task(self, agent: Agent, stage: str, config: dict, sprint=None) -> dict:
        """Dispatch the lead_writer to synthesize creative fragments."""
        if sprint is None:
            sprint = self._get_current_sprint(agent)
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        format_type = dept_state.get("format_type", "standalone")
        locale = config.get("locale", "en")

        if stage == "pitch":
            command_name = "write_pitch"
        elif stage == "expose":
            command_name = "write_expose"
        elif stage == "treatment":
            command_name = "write_concept" if format_type == "series" else "write_treatment"
        elif stage == "first_draft":
            command_name = "write_first_draft"
        else:
            command_name = "write_pitch"

        stage_display = "concept" if (stage == "treatment" and format_type == "series") else stage

        iteration = dept_state.get("stage_status", {}).get(stage, {}).get("iterations", 0)

        if iteration > 0:
            # Determine available operations based on stage
            if stage == "pitch":
                ops_note = "Available operations: replace (surgical text edits)."
            elif stage == "first_draft":
                ops_note = (
                    "Available operations: replace (surgical text edits), "
                    "replace_between (replace passage between two unique anchor texts, inclusive)."
                )
            else:
                ops_note = (
                    "Available operations: replace (surgical text edits), "
                    "replace_section (replace everything under a markdown header until next same-level header)."
                )

            step_plan = (
                f"Locale: {locale}\nFormat: {format_type}\nStage: {stage_display}\n"
                f"Round: {iteration + 1} (REVISION)\n\n"
                "## REVISION MODE\n"
                "The current Stage Deliverable and the Critique are in the department documents. "
                "Your job is to REVISE the existing deliverable, NOT rewrite it.\n\n"
                "Output your changes as revision JSON.\n\n"
                "OUTPUT FORMAT — CRITICAL:\n"
                "Output ONLY the JSON revision object. No preamble, no explanation, no prose. "
                "Your response must start with `{` and end with `}`. Nothing before or after.\n\n"
                "```json\n"
                "{\n"
                '  "revisions": [\n'
                '    {"type": "replace", "old_text": "exact text from document", '
                '"new_text": "revised text"},\n'
                '    {"type": "replace_section", "section": "## Section Header", '
                '"new_content": "new section content"},\n'
                '    {"type": "replace_between", "start": "unique start anchor", '
                '"end": "unique end anchor", "new_content": "new content"}\n'
                "  ],\n"
                '  "preserved": "Brief note on what was deliberately kept and why"\n'
                "}\n"
                "```\n\n"
                f"{ops_note}\n\n"
                "RULES:\n"
                "- Quote old_text EXACTLY from the existing document — character for character\n"
                "- Quote enough context for uniqueness (if old_text matches multiple times, the edit fails)\n"
                "- For replace_section, use the exact markdown header from the document\n"
                "- For replace_between, quote unique start and end anchor passages\n"
                "- ONLY change what the Critique flagged. Everything else stays BYTE-IDENTICAL.\n"
                "- If the Critique praised a section, do NOT touch it.\n\n"
                "## USING CREATIVE AGENTS' REVISED WORK\n"
                "The Research & Notes document contains fresh output from the creative agents "
                "(story_architect, character_designer, dialog_writer, story_researcher) who revised "
                "their work based on the same Critique you are reading. USE their revised material:\n"
                "- If a character was flagged as weak, check what character_designer produced — "
                "incorporate their improvements.\n"
                "- If structure was flagged, check story_architect's revised framework.\n"
                "- If dialogue was generic, check dialog_writer's new scene work.\n"
                "The creative agents did the hard thinking. Your job is to weave their improvements "
                "into the deliverable via precise revisions.\n\n"
                "Read the Critique carefully. Address EVERY flagged issue. Preserve EVERYTHING praised.\n\n"
                f"Your output must be in {locale}."
            )
        else:
            step_plan = (
                f"Locale: {locale}\nFormat: {format_type}\nStage: {stage_display}\n\n"
                "Synthesize ALL creative agents' work from this round into a single cohesive "
                f"'{stage_display}' document. Consult department documents for all creative "
                "output and prior stage deliverables.\n\n"
                "CRITICAL: Do NOT invent new elements. Use the story_architect's structure, "
                "character_designer's ensemble, dialog_writer's voice work, and "
                "story_researcher's research exactly as provided.\n\n"
                f"Your output must be in {locale}."
            )

        return {
            "exec_summary": f"Stage '{stage_display}': Lead Writer synthesizes deliverable",
            "tasks": [
                {
                    "target_agent_type": "lead_writer",
                    "command_name": command_name,
                    "exec_summary": f"Write the {stage_display} — synthesize creative team output",
                    "step_plan": step_plan,
                    "depends_on_previous": False,
                }
            ],
            "_on_dispatch": {"set_status": "lead_writing", "stage": stage},
        }

    # ── Document creation methods ──────────────────────────────────────

    def _create_stage_documents(self, agent, stage, version, doc_types, contents, sprint=None):
        """Create stage documents, archiving prior versions if they exist."""
        # Use effective stage for display (series "treatment" → "Concept")
        effective = self._get_effective_stage(agent, stage, sprint=sprint)
        stage_display = effective.replace("_", " ").title()
        label_map = {
            "stage_deliverable": "Deliverable",
            "stage_research": "Research & Notes",
            "stage_critique": "Critique",
        }

        for doc_type in doc_types:
            content = contents.get(doc_type, "")
            if not content:
                continue

            label = label_map.get(doc_type, doc_type)
            title = f"{stage_display} v{version} — {label}"

            existing = Document.objects.filter(
                department=agent.department,
                doc_type=doc_type,
                is_archived=False,
                title__startswith=f"{stage_display} v",
            ).first()

            new_doc = Document.objects.create(
                department=agent.department,
                doc_type=doc_type,
                title=title,
                content=content,
                sprint=sprint,
                is_locked=True,
            )

            if existing:
                existing.is_locked = False
                existing.is_archived = True
                existing.consolidated_into = new_doc
                existing.save(update_fields=["is_locked", "is_archived", "consolidated_into", "updated_at"])

    def _create_deliverable_and_research_docs(self, agent, stage, sprint=None):
        """Create Deliverable and Research & Notes documents."""
        from agents.models import AgentTask

        if sprint is None:
            sprint = self._get_current_sprint(agent)
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        iteration = dept_state.get("stage_status", {}).get(stage, {}).get("iterations", 0)
        version = iteration + 1

        lead_writer_task = (
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type="lead_writer",
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")
            .first()
        )
        raw_deliverable = lead_writer_task.report if lead_writer_task else ""

        effective_stage = self._get_effective_stage(agent, stage, sprint=sprint)
        creative_types = CREATIVE_MATRIX.get(effective_stage, [])
        creative_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=creative_types,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[: len(creative_types) * 2]
            .values_list("agent__agent_type", "agent__name", "report")
        )
        research_parts = []
        for agent_type, agent_name, report in creative_tasks:
            if report:
                research_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
        research_content = "\n\n═══════════════════════════════════════\n\n".join(research_parts)

        # Deliverable: always try to detect and apply revision JSON,
        # regardless of iteration counter. The lead_writer may produce
        # revision JSON even on iteration 0 if the counter was reset.
        if raw_deliverable:
            deliverable_content, was_revision = self._apply_revision_or_replace(
                agent, "stage_deliverable", raw_deliverable, stage
            )
            if was_revision:
                logger.info(
                    "Writers Room: applied revision to stage deliverable for '%s' v%d",
                    stage,
                    version,
                )
        else:
            deliverable_content = ""

        contents = {}
        if deliverable_content:
            contents["stage_deliverable"] = deliverable_content
        if research_content:
            contents["stage_research"] = research_content

        if contents:
            self._create_stage_documents(
                agent=agent,
                stage=stage,
                version=version,
                doc_types=list(contents.keys()),
                contents=contents,
                sprint=sprint,
            )

        # Update the sprint output with the latest deliverable and research
        if sprint:
            if deliverable_content:
                self._update_sprint_output(agent, sprint, stage, deliverable_content, "deliverable")
            if research_content:
                self._update_sprint_output(agent, sprint, stage, research_content, "research")

    def _update_sprint_output(self, agent, sprint, stage: str, content: str, output_type: str = "deliverable"):
        """Update or create a sprint output record for this department.

        Label format: {effective_stage}:{output_type}
        e.g. "expose:deliverable", "expose:critique", "expose:research"
        """
        from projects.models import Output

        effective_stage = self._get_effective_stage(agent, stage, sprint=sprint)
        stage_display = effective_stage.replace("_", " ").title()
        type_display = output_type.title()
        label = f"{effective_stage}:{output_type}"

        Output.objects.update_or_create(
            sprint=sprint,
            department=agent.department,
            label=label,
            defaults={
                "title": f"{stage_display} {type_display}",
                "output_type": "markdown",
                "content": content,
            },
        )

    def _create_critique_doc(self, agent, stage, sprint=None):
        """Create Critique document from feedback and reviewer reports."""
        from agents.models import AgentTask

        if sprint is None:
            sprint = self._get_current_sprint(agent)
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        version = dept_state.get("stage_status", {}).get(stage, {}).get("iterations", 0) + 1

        effective_stage = self._get_effective_stage(agent, stage, sprint=sprint)
        feedback_types = [at for at, _ in FEEDBACK_MATRIX.get(effective_stage, [])]
        feedback_types.append("creative_reviewer")
        feedback_types.append("authenticity_analyst")  # gate report feeds into critique

        feedback_tasks = list(
            AgentTask.objects.filter(
                agent__department=agent.department,
                agent__agent_type__in=feedback_types,
                status=AgentTask.Status.DONE,
            )
            .order_by("-completed_at")[: len(feedback_types) * 2]
            .values_list("agent__agent_type", "agent__name", "report")
        )
        critique_parts = []
        for agent_type, agent_name, report in feedback_tasks:
            if report:
                critique_parts.append(f"## {agent_name} ({agent_type})\n\n{report}")
        critique_content = "\n\n═══════════════════════════════════════\n\n".join(critique_parts)

        if critique_content:
            self._create_stage_documents(
                agent=agent,
                stage=stage,
                version=version,
                doc_types=["stage_critique"],
                contents={"stage_critique": critique_content},
                sprint=sprint,
            )
            if sprint:
                self._update_sprint_output(agent, sprint, stage, critique_content, "critique")

    # ── Feedback task proposal ──────────────────────────────────────────

    def _propose_feedback_tasks(self, agent: Agent, stage: str, config: dict, sprint=None) -> dict:
        """Create feedback/analysis tasks per the depth matrix.

        Skips feedback agents that are inactive, or whose controlled creative
        agent is inactive (no point reviewing work that wasn't produced).
        """
        from agents.blueprints import get_workforce_for_department

        effective_stage = stage
        feedback_agents = FEEDBACK_MATRIX.get(effective_stage, [])
        locale = config.get("locale", "en")

        # Active agents in this department
        active_types = set(
            agent.department.agents.filter(status="active", is_leader=False).values_list("agent_type", flat=True)
        )

        # Build controls map: feedback_agent_type -> creative_agent_type it reviews
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
                    "command_name": "analyze",
                    "exec_summary": f"Analyze {effective_stage} content ({agent_type}, depth={depth})",
                    "step_plan": (
                        f"Stage: {effective_stage}\n"
                        f"Depth: {depth}\n"
                        f"Locale: {locale}\n\n"
                        f"Analyze the Lead Writer's '{effective_stage}' deliverable at {depth} depth. "
                        f"The deliverable is in the department documents as the latest "
                        f"'Stage Deliverable' document.\n\n"
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
            logger.warning(
                "Writers Room: no active feedback agents for stage '%s' — passing without review",
                effective_stage,
            )
            if sprint is None:
                sprint = self._get_current_sprint(agent)
            dept_id = str(agent.department_id)
            dept_state = sprint.get_department_state(dept_id) if sprint else {}
            stage_status = dept_state.get("stage_status", {})
            current_stage = dept_state.get("current_stage", effective_stage)
            current_info = stage_status.get(current_stage, {"iterations": 0})
            current_info["status"] = "passed"
            stage_status[current_stage] = current_info
            dept_state["stage_status"] = stage_status
            next_stg = _next_stage(current_stage)
            terminal_stage = dept_state.get("terminal_stage", "treatment")
            effective_terminal = terminal_stage
            if effective_terminal == "concept":
                effective_terminal = "treatment"
            if next_stg and STAGES.index(current_stage) < STAGES.index(effective_terminal):
                dept_state["current_stage"] = next_stg
            if sprint:
                sprint.set_department_state(dept_id, dept_state)
            if next_stg and STAGES.index(current_stage) < STAGES.index(effective_terminal):
                next_effective = self._get_effective_stage(agent, next_stg, sprint=sprint)
                return self._propose_creative_tasks(agent, next_effective, config, sprint=sprint)
            return None

        # Resolve the real current_stage for _on_dispatch
        if sprint is None:
            sprint = self._get_current_sprint(agent)
        _dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        dispatch_stage = _dept_state.get("current_stage", effective_stage)

        return {
            "exec_summary": f"Stage '{effective_stage}': assign feedback agents to analyze",
            "tasks": tasks,
            "_on_dispatch": {"set_status": "feedback", "stage": dispatch_stage},
        }

    # ── Review task proposal (dispatch creative_reviewer) ────────────

    def _propose_review_task(self, agent: Agent, stage: str, config: dict, sprint=None) -> dict:
        """Dispatch the creative_reviewer to consolidate analyst feedback."""
        if sprint is None:
            sprint = self._get_current_sprint(agent)
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

        # Inject story bible for canon verification
        bible_context = ""
        try:
            from projects.models import Output

            bible_output = Output.objects.filter(
                sprint=sprint,
                department=agent.department,
                label="story_bible",
            ).first()
            if bible_output and bible_output.content:
                bible_context = f"\n\n## Story Bible (CANON — do not contradict)\n{bible_output.content}"
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not load story bible for review context: %s", exc)

        # Resolve the real current_stage for _on_dispatch
        dept_state = sprint.get_department_state(str(agent.department_id)) if sprint else {}
        dispatch_stage = dept_state.get("current_stage", stage)

        return {
            "_on_dispatch": {"set_status": "review", "stage": dispatch_stage},
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
                        f"For CHANGES_REQUESTED: group fix instructions by creative agent.\n"
                        f"For WEAK_IDEA: explain what is fundamentally weak and why, but do not prescribe replacement."
                        f"{bible_context}"
                    ),
                    "depends_on_previous": False,
                }
            ],
        }

    # ── Fix task override (writers-room-specific routing) ──────────────

    def _propose_fix_task(
        self, agent: Agent, review_task, score: float, round_num: int, polish_count: int
    ) -> dict | None:
        """On failed review: create critique doc, reset to creative_writing.

        WEAK_IDEA verdict resets iterations to 0 (fresh ideation).
        CHANGES_REQUESTED increments iterations (revision of same material).
        """
        sprint = self._get_current_sprint(agent)
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id) if sprint else {}
        current_stage = dept_state.get("current_stage", STAGES[0])
        stage_status = dept_state.get("stage_status", {})
        current_info = stage_status.get(current_stage, {})

        self._create_critique_doc(agent, current_stage, sprint)

        verdict = getattr(review_task, "review_verdict", "CHANGES_REQUESTED")

        if verdict == "WEAK_IDEA":
            # Fresh ideation — reset iterations so agents don't get revision instructions
            current_info["iterations"] = 0
            logger.info(
                "Writers Room: WEAK_IDEA for stage '%s' — resetting to fresh ideation",
                current_stage,
            )
        else:
            current_info["iterations"] = current_info.get("iterations", 0) + 1

        current_info["status"] = "not_started"
        stage_status[current_stage] = current_info
        dept_state["stage_status"] = stage_status
        if sprint:
            sprint.set_department_state(dept_id, dept_state)

        config = _get_merged_config(agent)
        effective_stage = self._get_effective_stage(agent, current_stage, sprint=sprint)
        return self._propose_creative_tasks(agent, effective_stage, config, sprint=sprint)


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


FORMAT_DETECTION_PROMPT = """\
You are the showrunner of a professional writers room. Analyze the sprint text and project input to determine:
1. Whether this is a standalone piece or a series
2. What the terminal stage should be
3. Where the pipeline should start based on existing material

## Sprint Text
{sprint_text}

## Project Goal
{goal}

## Source Material
{sources_summary}

## Rules
- Determine format_type from the sprint text. The user says what they want: "Write a series concept", \
"Schreib mir ein Treatment", "I want a screenplay", etc. Understand ANY language.
- standalone = movie, play, book, single audio drama, short story, etc.
- series = TV series, Filmreihe, Serie, Hörspielserie, web series, etc.
- terminal_stage depends on what the user asked for:
  - If they want a pitch/logline only -> "pitch"
  - If they want an expose -> "expose"
  - If they want a treatment (standalone) -> "treatment"
  - If they want a series concept/bible/Serienkonzept -> "concept"
  - If they want a screenplay/manuscript/first draft -> "first_draft"
  - If unclear, default to the natural terminal: "concept" for series, "treatment" for standalone
- entry_stage: where to START the pipeline based on existing material:
  - If no existing material -> "pitch"
  - If a pitch/logline already exists -> "expose"
  - If an expose exists -> "treatment" (or "concept" for series)
  - If a treatment/concept exists -> "first_draft"

You MUST call the classify_sprint tool with your results."""

FORMAT_DETECTION_TOOL = {
    "name": "classify_sprint",
    "description": "Submit sprint classification results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "format_type": {
                "type": "string",
                "enum": ["standalone", "series"],
                "description": "Whether this is a standalone piece or a series.",
            },
            "terminal_stage": {
                "type": "string",
                "enum": ["pitch", "expose", "treatment", "concept", "first_draft"],
                "description": "The final stage the pipeline should reach.",
            },
            "entry_stage": {
                "type": "string",
                "enum": ["pitch", "expose", "treatment", "first_draft"],
                "description": "Where the pipeline should start based on existing material.",
            },
            "locale": {
                "type": "string",
                "description": "ISO 639-1 locale code detected from sprint text and goal (e.g. 'de', 'en', 'fr').",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of the classification.",
            },
        },
        "required": ["format_type", "terminal_stage", "entry_stage", "locale", "reasoning"],
    },
}


def _run_format_detection(agent, sprint) -> dict:
    """
    Classify the sprint to determine format type, terminal stage, and entry point.
    Returns dict with format_type, terminal_stage, entry_stage.
    """
    from agents.ai.claude_client import call_claude_with_tools

    sprint_text = sprint.text or ""
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
        sources_summary += f"\n### {name} ({s.source_type})\n{text[:2000]}\n"

    if not sources_summary:
        sources_summary = "No source material uploaded."

    prompt = FORMAT_DETECTION_PROMPT.format(
        sprint_text=sprint_text,
        goal=goal,
        sources_summary=sources_summary,
    )

    _response, data, _usage = call_claude_with_tools(
        system_prompt="You are a project classification system.",
        user_message=prompt,
        tools=[FORMAT_DETECTION_TOOL],
        force_tool="classify_sprint",
        model="claude-opus-4-6",
        max_tokens=1024,
    )

    if not data or "format_type" not in data:
        logger.warning("Format detection tool call failed, defaulting")
        return {"format_type": "standalone", "terminal_stage": "treatment", "entry_stage": "pitch"}

    result = {
        "format_type": data.get("format_type", "standalone"),
        "terminal_stage": data.get("terminal_stage", "treatment"),
        "entry_stage": data.get("entry_stage", "pitch"),
        "reasoning": data.get("reasoning", ""),
    }

    # Validate terminal_stage
    valid_terminals = {"pitch", "expose", "treatment", "concept", "first_draft"}
    if result["terminal_stage"] not in valid_terminals:
        result["terminal_stage"] = "concept" if result["format_type"] == "series" else "treatment"

    # Validate entry_stage
    if result["entry_stage"] not in STAGES:
        result["entry_stage"] = "pitch"

    # Store in sprint department_state
    dept_id = str(agent.department_id)
    dept_state = sprint.get_department_state(dept_id)
    dept_state["format_type"] = result["format_type"]
    dept_state["terminal_stage"] = result["terminal_stage"]
    dept_state["detection_reasoning"] = result["reasoning"]
    dept_state["entry_detected"] = True
    sprint.set_department_state(dept_id, dept_state)

    # Backfill locale on department if not set (catches pre-existing departments)
    detected_locale = data.get("locale")
    dept_config = agent.department.config or {}
    if detected_locale and not dept_config.get("locale"):
        dept_config["locale"] = detected_locale
        agent.department.config = dept_config
        agent.department.save(update_fields=["config"])
        logger.info("Writers Room: backfilled department locale to '%s'", detected_locale)

    logger.info(
        "Writers Room format detection: format=%s terminal=%s entry=%s reason=%s",
        result["format_type"],
        result["terminal_stage"],
        result["entry_stage"],
        result["reasoning"][:100],
    )

    return result

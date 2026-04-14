"""Shared base classes for Writers Room agents."""

import logging
import re

from agents.blueprints.base import WorkforceBlueprint

logger = logging.getLogger(__name__)

# Stages where full scripts/treatments exist — context is necessarily large.
_LATE_STAGES = {"treatment", "first_draft"}
_LATE_STAGE_THRESHOLD = 1_500_000  # ~500k tokens


def _get_writers_room_volume_threshold(agent) -> int:
    """Return volume threshold based on the writers room's current stage.

    Late stages (treatment, first_draft) produce full scripts that push context
    well beyond the default 500k char threshold. Allow 1.5M for those stages.
    """
    from projects.models import Sprint

    sprint = (
        Sprint.objects.filter(
            departments=agent.department,
            status=Sprint.Status.RUNNING,
        )
        .order_by("-created_at")
        .first()
    )
    if sprint:
        dept_state = sprint.get_department_state(str(agent.department_id))
        current_stage = dept_state.get("current_stage", "pitch")
        if current_stage in _LATE_STAGES:
            return _LATE_STAGE_THRESHOLD

    return WorkforceBlueprint.volume_threshold_chars


# The deliverable is what gets scored. Everything else is reference material.
_DELIVERABLE_DOC_TYPE = "stage_deliverable"

# Which analyst feedback is relevant to each creative agent.
# Creative agents only see critique sections from analysts that review their domain.
CRITIQUE_RELEVANCE = {
    "story_architect": ["structure_analyst", "creative_reviewer"],
    "character_designer": ["character_analyst", "creative_reviewer"],
    "dialog_writer": ["dialogue_analyst", "creative_reviewer"],
    "story_researcher": ["market_analyst", "production_analyst", "creative_reviewer"],
}


def _filter_critique(content: str, relevant_types: list[str]) -> str:
    """Extract only the sections of a critique doc relevant to an agent.

    Critique docs are structured as:
        ## Agent Name (agent_type)
        <report>
        ---
    """
    if not content or not relevant_types:
        return content

    # Split on the agent-report delimiter (═══ line), NOT on --- which appears
    # inside reports as markdown horizontal rules.
    sections = re.split(r"\n═{3,}\n", content)
    kept = []
    for section in sections:
        # Check if any relevant agent_type appears in the section header
        for at in relevant_types:
            if f"({at})" in section[:200]:
                kept.append(section.strip())
                break

    if not kept:
        return content  # fallback: return full critique if parsing fails

    return "\n\n═══════════════════════════════════════\n\n".join(kept)


class WritersRoomCreativeBlueprint(WorkforceBlueprint):
    """Base for Writers Room creative agents (story_architect, character_designer,
    dialog_writer, story_researcher).

    Default model: Sonnet. Lead writer and creative reviewer override to Opus.

    Overrides get_context() to drastically reduce context size:
    1. Department documents: only deliverable + voice profile + filtered critique
       (not research notes — those are the creative agents' own prior output).
    2. Critique is filtered to only sections relevant to this agent's domain.
    3. Sibling task reports are stripped entirely — creative agents get their
       instructions from the step_plan, not by reading every other agent's output.
    """

    default_model = "claude-sonnet-4-6"

    def get_volume_threshold(self, agent) -> int:
        return _get_writers_room_volume_threshold(agent)

    def get_context(self, agent):
        ctx = super().get_context(agent)

        department = agent.department

        # Determine if this is a revision round by checking for a critique doc
        has_critique = department.documents.filter(is_archived=False, doc_type="stage_critique").exists()

        # FIRST ROUND: keep sibling reports so sequential creative agents
        # can see each other's output and work on the SAME story.
        # The lead writer (_include_research=True) always needs sibling
        # reports to synthesize creative agents' work.
        # REVISION ROUND: strip sibling reports — agents get targeted
        # critique and the deliverable instead.
        is_lead_writer = getattr(self, "_include_research", False)
        if has_critique and not is_lead_writer:
            ctx["sibling_agents"] = ""

        # Always strip own task history — creative agents don't need it
        ctx["own_recent_tasks"] = ""

        skip_filter = getattr(self, "_skip_critique_filter", False)
        relevant_analysts = CRITIQUE_RELEVANCE.get(agent.agent_type, [])

        if has_critique and not getattr(self, "_include_research", False):
            # REVISION ROUND context for creative agents:
            # a) Their initial research (own section from Research & Notes)
            # b) Filtered critique for their department
            # c) The current deliverable
            include_types = ["stage_deliverable", "stage_critique"]
        else:
            # FIRST ROUND or LEAD WRITER: deliverable + critique + voice + research
            include_types = ["stage_deliverable", "stage_critique", "voice_profile"]
            if getattr(self, "_include_research", False):
                include_types.append("stage_research")

        docs = list(
            department.documents.filter(
                is_archived=False,
                doc_type__in=include_types,
            ).values_list("title", "content", "doc_type")
        )

        parts = []
        for title, content, doc_type in docs:
            if not content:
                continue
            if doc_type == "stage_critique" and relevant_analysts and not skip_filter:
                filtered = _filter_critique(content, relevant_analysts)
                parts.append(f"\n\n--- [{doc_type}] {title} (filtered for {agent.agent_type}) ---\n{filtered}")
            else:
                parts.append(f"\n\n--- [{doc_type}] {title} ---\n{content}")

        # On revision rounds, inject the agent's OWN initial output so it has
        # its prior work as reference for targeted improvements
        if has_critique and not getattr(self, "_include_research", False):
            own_section = self._extract_own_research_section(department, agent.agent_type)
            if own_section:
                parts.append(f"\n\n--- [initial_research] Your initial research (reference) ---\n" f"{own_section}")

        ctx["department_documents"] = "".join(parts)
        return ctx

    @staticmethod
    def _extract_own_research_section(department, agent_type: str) -> str:
        """Extract this agent's section from the Research & Notes document.

        The research doc is structured as:
            ## Agent Name (agent_type)
            <report>
            ---
        Returns only this agent's section, or empty string if not found.
        """
        from projects.models import Document

        research_doc = Document.objects.filter(
            department=department,
            doc_type="stage_research",
            is_archived=False,
        ).first()
        if not research_doc or not research_doc.content:
            return ""

        # Split on agent-report delimiter and find the section for this agent_type
        sections = re.split(r"\n═{3,}\n", research_doc.content)
        for section in sections:
            if f"({agent_type})" in section[:200]:
                return section.strip()

        return ""


class WritersRoomFeedbackBlueprint(WorkforceBlueprint):
    """Base for all Writers Room feedback/review agents.

    Default model: Sonnet. Authenticity analyst overrides to Haiku,
    creative reviewer overrides to Opus.

    Overrides get_context() to:
    1. Strip sibling task reports.
    2. Inject ONLY the stage deliverable into department_documents.
       Reference material (research briefs, character bibles, tone samples)
       is excluded entirely — feedback agents score what's in the deliverable,
       nothing else.
    """

    default_model = "claude-sonnet-4-6"

    def get_volume_threshold(self, agent) -> int:
        return _get_writers_room_volume_threshold(agent)

    def get_max_tokens(self, agent, task) -> int:
        return 12288  # Feedback agents produce detailed reviews

    # Feedback agents are NOT source_privileged — they only see essential sources
    # (e.g., series bible) via the base build_task_message. Important/regular/minor
    # sources are excluded so old research doesn't pollute the review.

    _system_prompt: str = "You are a feedback agent for the Writers Room."

    @property
    def system_prompt(self) -> str:
        """Placeholder system prompt for feedback base class. Override in concrete subclasses."""
        return self._system_prompt

    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Allow setting system_prompt for testing."""
        self._system_prompt = value

    def get_context(self, agent):
        ctx = super().get_context(agent)

        # Strip sibling task reports and own task history — feedback agents
        # score the deliverable fresh each time, they don't need prior reports
        ctx["sibling_agents"] = ""
        ctx["own_recent_tasks"] = ""

        # Only inject the stage deliverable — no reference material.
        department = agent.department
        deliverable_docs = list(
            department.documents.filter(
                is_archived=False,
                doc_type=_DELIVERABLE_DOC_TYPE,
            ).values_list("title", "content")
        )

        deliverable_text = ""
        for title, content in deliverable_docs:
            deliverable_text += f"\n\n--- {title} ---\n{content}"

        sections = []

        sections.append(
            "## ═══ STAGE DELIVERABLE — THIS IS WHAT YOU SCORE ═══\n"
            "The deliverable is the document that gets pitched, sent to buyers, or advances "
            "to the next stage. Your scores and flags apply to THIS document ONLY.\n"
            "No other material is provided. Score what is here."
        )
        sections.append(deliverable_text if deliverable_text else "\n(No deliverable yet.)")

        sections.append(
            "\n\n## REVIEW METHODOLOGY\n"
            "## CHECK 0 — ACTION TEST (MANDATORY, BEFORE ALL OTHER CHECKS)\n\n"
            "Before running any framework analysis, answer this question:\n\n"
            "Can I retell what happens in this deliverable as a sequence of concrete scenes "
            "where specific characters do specific things?\n\n"
            "Attempt the retelling now. Write it out. For each scene:\n"
            "- WHO does WHAT\n"
            "- WHAT CHANGES as a result\n\n"
            "If you cannot retell the story as scenes — if all you can produce is a summary of "
            "themes, mechanisms, or character psychology — then the deliverable has NO DRAMATIC "
            "ACTION. Score: 0/10 for all dimensions. Stop analysis. Write only:\n\n"
            '"CRITICAL FAILURE: No dramatic action. The deliverable describes a story concept '
            'but does not contain a story. Cannot retell as scenes."\n\n'
            "Do NOT proceed to framework analysis, character checks, or market assessment if "
            "Check 0 fails. A document without scenes cannot be scored on structure, character, "
            "dialogue, or any other dimension.\n\n"
            "---\n\n"
            "If Check 0 passes, proceed with your standard analysis:\n"
            "1. Score ONLY the Stage Deliverable.\n"
            "2. Review the deliverable against the CREATOR'S ORIGINAL PITCH in <project_goal>.\n"
            "3. Check for moral register drift.\n"
            "4. Check causal rigor — does every 'A causes B' have a concrete mechanism?\n"
            "5. Check substance — is every paragraph carrying real content or filler?\n"
            "6. Check voice — does the prose match the creator's pitch voice?"
        )

        ctx["department_documents"] = "\n".join(sections)

        return ctx

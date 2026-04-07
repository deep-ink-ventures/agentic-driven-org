"""Shared base class for Writers Room feedback agents."""

import logging

from agents.blueprints.base import WorkforceBlueprint

logger = logging.getLogger(__name__)

# The deliverable is what gets scored. Everything else is reference material.
_DELIVERABLE_DOC_TYPE = "stage_deliverable"


class WritersRoomFeedbackBlueprint(WorkforceBlueprint):
    """Base for all Writers Room feedback/review agents.

    Overrides get_context() to:
    1. Strip sibling task reports.
    2. Restructure department_documents into two clearly separated sections:
       - THE DELIVERABLE (score this)
       - REFERENCE MATERIAL (use to verify the deliverable, but do not score)
    """

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

        # Strip sibling task reports
        ctx["sibling_agents"] = "Sibling task reports are not available to feedback agents."

        # Separate documents into deliverable vs. reference material.
        department = agent.department
        all_docs = list(
            department.documents.filter(is_archived=False).values_list("title", "content", "doc_type", "created_at")
        )

        deliverable_text = ""
        reference_text = ""
        for title, content, doc_type, _created_at in all_docs:
            entry = f"\n\n--- [{doc_type}] {title} ---\n{content}"
            if doc_type == _DELIVERABLE_DOC_TYPE:
                deliverable_text += entry
            else:
                reference_text += entry

        # Rebuild department_documents with clear separation
        sections = []

        sections.append(
            "## ═══ STAGE DELIVERABLE — THIS IS WHAT YOU SCORE ═══\n"
            "The deliverable is the document that gets pitched, sent to buyers, or advances "
            "to the next stage. Your scores and flags apply to THIS document ONLY."
        )
        sections.append(deliverable_text if deliverable_text else "\n(No deliverable yet.)")

        sections.append(
            "\n\n## ═══ REFERENCE MATERIAL — DO NOT SCORE ═══\n"
            "The documents below are internal working products from creative agents (research "
            "briefs, character bibles, structure documents, tone samples). Use them to VERIFY "
            "whether the deliverable properly captured important content — but do NOT review "
            "or score them directly. Your scores apply to the deliverable above, not to these."
        )
        sections.append(reference_text if reference_text else "\n(No reference material.)")

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
            "1. Score ONLY the Stage Deliverable. Reference material is context, not output.\n"
            "2. Review the deliverable against the CREATOR'S ORIGINAL PITCH in <project_goal>.\n"
            "3. Check for moral register drift.\n"
            "4. Check causal rigor — does every 'A causes B' have a concrete mechanism?\n"
            "5. Check substance — is every paragraph carrying real content or filler?\n"
            "6. Check voice — does the prose match the creator's pitch voice?"
        )

        ctx["department_documents"] = "\n".join(sections)

        return ctx

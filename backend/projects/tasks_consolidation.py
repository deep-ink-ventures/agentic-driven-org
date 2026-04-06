"""Document consolidation tasks.

Three-tier consolidation:
1. Sprint-end: merge all sprint progress docs into one summary per department.
2. Monthly: merge all docs older than 30 days into topic-clustered archives.
3. Volume: emergency consolidation when a department exceeds 500k tokens.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Sum
from django.db.models.functions import Length
from django.utils import timezone

from agents.ai.claude_client import call_claude

logger = logging.getLogger(__name__)

# ~500k tokens ≈ ~1.5M characters (rough 1:3 ratio for English text)
VOLUME_THRESHOLD_CHARS = 1_500_000


def _consolidate_documents(documents, department, document_type, title_prefix, instruction):
    """Shared consolidation logic: Claude reads documents, produces a summary, archives originals."""
    if not documents:
        return None

    docs_text = ""
    for doc in documents:
        docs_text += f"\n\n--- [{doc.doc_type}] {doc.title} (created {doc.created_at.date()}) ---\n{doc.content}"

    system_prompt = (
        "You are a knowledge consolidator. Your job is to merge multiple documents into a comprehensive, "
        "well-organized summary. Preserve ALL meaningful detail — findings, decisions, artifacts, outcomes. "
        "Organize by topic. Drop only information that is clearly outdated or superseded by newer content. "
        "Write in markdown. Be thorough — this summary replaces the originals."
    )

    user_message = f"""{instruction}

## Department: {department.name}

## Documents to consolidate:
{docs_text}

Write the consolidated document now."""

    response, _usage = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=16384,
    )

    from projects.models import Document

    summary = Document.objects.create(
        title=f"{title_prefix} — {department.name} — {timezone.now().strftime('%Y-%m-%d')}",
        content=response,
        department=department,
        document_type=document_type,
        doc_type=Document.DocType.GENERAL,
    )

    for doc in documents:
        doc.is_archived = True
        doc.consolidated_into = summary
        doc.save(update_fields=["is_archived", "consolidated_into", "updated_at"])

    logger.info(
        "Consolidated %d documents into '%s' for department %s",
        len(documents),
        summary.title,
        department.name,
    )
    return summary


@shared_task
def consolidate_sprint_documents(sprint_id):
    """Merge all sprint progress documents into one summary per department."""
    from projects.models import Document, Sprint

    try:
        sprint = Sprint.objects.get(id=sprint_id)
    except Sprint.DoesNotExist:
        logger.warning("Sprint %s not found — skipping consolidation", sprint_id)
        return

    for department in sprint.departments.all():
        docs = list(
            Document.objects.filter(
                department=department,
                sprint=sprint,
                is_archived=False,
                is_locked=False,
            )
            .exclude(document_type="sprint_summary")
            .order_by("created_at")
        )

        summary = _consolidate_documents(
            documents=docs,
            department=department,
            document_type="sprint_summary",
            title_prefix=f"Sprint Summary: {sprint.text[:50]}",
            instruction=(
                f"Consolidate all progress documents from this sprint into one comprehensive summary.\n"
                f"Sprint instruction: {sprint.text}\n"
                f"Sprint status: {sprint.status}"
            ),
        )

        # Link the summary to the sprint
        if summary:
            summary.sprint = sprint
            summary.save(update_fields=["sprint", "updated_at"])


@shared_task
def consolidate_monthly_documents():
    """Monthly: merge all non-archived documents older than 30 days per department."""
    from projects.models import Department, Document

    cutoff = timezone.now() - timedelta(days=30)

    departments_with_old_docs = (
        Document.objects.filter(
            is_archived=False,
            is_locked=False,
            created_at__lt=cutoff,
        )
        .values_list("department_id", flat=True)
        .distinct()
    )

    for dept_id in departments_with_old_docs:
        department = Department.objects.get(id=dept_id)
        docs = list(
            Document.objects.filter(
                department=department,
                is_archived=False,
                is_locked=False,
                created_at__lt=cutoff,
            ).order_by("created_at")
        )

        _consolidate_documents(
            documents=docs,
            department=department,
            document_type="monthly_archive",
            title_prefix="Monthly Archive",
            instruction=(
                "Consolidate these older documents into a comprehensive archive. "
                "Drop information that is clearly outdated or no longer relevant. "
                "Organize by topic. This archive represents the department's historical knowledge."
            ),
        )


@shared_task
def consolidate_department_documents(department_id):
    """Emergency consolidation when department context exceeds volume threshold."""
    from projects.models import Department, Document

    department = Department.objects.get(id=department_id)

    active_docs = Document.objects.filter(department=department, is_archived=False, is_locked=False)
    total_chars = active_docs.aggregate(total=Sum(Length("content")))["total"] or 0

    if total_chars < VOLUME_THRESHOLD_CHARS:
        return

    logger.warning(
        "VOLUME_THRESHOLD department=%s chars=%d threshold=%d — triggering consolidation",
        department.name,
        total_chars,
        VOLUME_THRESHOLD_CHARS,
    )

    docs = list(active_docs.order_by("created_at"))

    _consolidate_documents(
        documents=docs,
        department=department,
        document_type="monthly_archive",
        title_prefix="Volume Consolidation",
        instruction=(
            "This department's context has grown too large. Consolidate ALL documents into a compact, "
            "topic-organized set. Preserve everything still relevant. Drop only clearly outdated information."
        ),
    )

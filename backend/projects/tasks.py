import json
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def bootstrap_project(self, proposal_id: str):
    """
    Analyze project sources with Claude and generate a bootstrap proposal.
    """
    from projects.models import BootstrapProposal, Source
    from projects.prompts import BOOTSTRAP_SYSTEM_PROMPT, build_bootstrap_user_message
    from agents.ai.claude_client import call_claude
    from agents.blueprints import DEPARTMENTS

    try:
        proposal = BootstrapProposal.objects.select_related("project").get(id=proposal_id)
    except BootstrapProposal.DoesNotExist:
        logger.error("BootstrapProposal %s not found", proposal_id)
        return

    project = proposal.project

    proposal.status = BootstrapProposal.Status.PROCESSING
    proposal.save(update_fields=["status", "updated_at"])
    _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Gathering sources")

    try:
        # Gather sources
        sources = Source.objects.filter(project=project)
        if not sources.exists():
            raise ValueError("No sources found for this project")

        source_data = []
        for s in sources:
            text = s.extracted_text or s.raw_content or ""
            if not text:
                continue
            name = s.original_filename or s.url or "Text input"
            source_data.append({
                "id": str(s.id),
                "name": name,
                "source_type": s.source_type,
                "text": text,
            })

        if not source_data:
            raise ValueError("No sources with extracted text found")

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Mapping your project")

        # Available departments with their workforce agents
        available_departments = []
        for dept_slug, dept_config in DEPARTMENTS.items():
            workforce = [
                {"slug": slug, "name": bp.name, "description": bp.description}
                for slug, bp in dept_config["workforce"].items()
            ]
            available_departments.append({
                "slug": dept_slug,
                "name": dept_config["name"],
                "description": dept_config["description"],
                "workforce": workforce,
            })

        # Build prompt
        user_message = build_bootstrap_user_message(
            project_name=project.name,
            project_goal=project.goal,
            sources=source_data,
            available_departments=available_departments,
        )

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Building your project structure")

        # Call Claude
        response, _usage = call_claude(
            system_prompt=BOOTSTRAP_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=8192,
        )

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Validating proposal")

        from agents.ai.claude_client import parse_json_response
        proposal_data = parse_json_response(response)
        if proposal_data is None:
            raise ValueError(f"Failed to parse Claude response as JSON: {response[:200]}")

        # Validate proposal against schema
        proposal.proposal = proposal_data
        validation_errors = proposal.validate_proposal()
        if validation_errors:
            raise ValueError(f"Invalid proposal from Claude: {'; '.join(validation_errors)}")

        _broadcast_bootstrap(project.id, proposal.id, "processing", phase="Finalizing")

        proposal.token_usage = _usage
        proposal.status = BootstrapProposal.Status.PROPOSED
        proposal.save(update_fields=["proposal", "token_usage", "status", "updated_at"])

        logger.info("Bootstrap proposal generated for project %s", project.name)
        _broadcast_bootstrap(project.id, proposal.id, "proposed")

    except Exception as e:
        logger.exception("Bootstrap failed for project %s: %s", project.name, e)
        proposal.status = BootstrapProposal.Status.FAILED
        proposal.error_message = str(e)[:1000]
        proposal.save(update_fields=["status", "error_message", "updated_at"])
        _broadcast_bootstrap(project.id, proposal.id, "failed", str(e)[:200])


@shared_task
def recover_stuck_proposals():
    """
    Self-healing: find proposals stuck in pending/processing and retry them.
    - pending for >30s: dispatch bootstrap_project
    - processing for >5min: reset to pending and dispatch (task likely crashed)
    """
    from datetime import timedelta
    from django.utils import timezone
    from projects.models import BootstrapProposal

    now = timezone.now()

    # Pending proposals that were never picked up (>30s old)
    pending = BootstrapProposal.objects.filter(
        status=BootstrapProposal.Status.PENDING,
        updated_at__lt=now - timedelta(seconds=30),
    )
    for p in pending:
        logger.info("Recovering pending proposal %s for project %s", p.id, p.project.name)
        bootstrap_project.delay(str(p.id))

    # Processing proposals stuck for >5min (task crashed)
    stuck = BootstrapProposal.objects.filter(
        status=BootstrapProposal.Status.PROCESSING,
        updated_at__lt=now - timedelta(minutes=5),
    )
    for p in stuck:
        logger.warning("Recovering stuck proposal %s for project %s", p.id, p.project.name)
        p.status = BootstrapProposal.Status.PENDING
        p.error_message = "Auto-recovered from stuck processing state"
        p.save(update_fields=["status", "error_message", "updated_at"])
        bootstrap_project.delay(str(p.id))


@shared_task
def archive_stale_documents():
    """Daily: archive research documents older than 30 days."""
    from datetime import timedelta
    from django.utils import timezone
    from projects.models import Document

    cutoff = timezone.now() - timedelta(days=30)
    count = Document.objects.filter(
        doc_type=Document.DocType.RESEARCH,
        is_archived=False,
        created_at__lt=cutoff,
    ).update(is_archived=True)

    if count:
        logger.info("Archived %d stale research documents", count)


def _broadcast_bootstrap(project_id, proposal_id, bootstrap_status, error_message="", phase=""):
    """Send bootstrap status update via WebSocket."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"bootstrap_{project_id}",
            {
                "type": "bootstrap.status",
                "status": bootstrap_status,
                "proposal_id": str(proposal_id),
                "error_message": error_message,
                "phase": phase,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast bootstrap status")

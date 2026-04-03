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
    from agents.blueprints import _REGISTRY

    try:
        proposal = BootstrapProposal.objects.select_related("project").get(id=proposal_id)
    except BootstrapProposal.DoesNotExist:
        logger.error("BootstrapProposal %s not found", proposal_id)
        return

    proposal.status = BootstrapProposal.Status.PROCESSING
    proposal.save(update_fields=["status", "updated_at"])

    project = proposal.project

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

        # Available blueprint types
        available_types = [
            {"slug": slug, "name": bp.name, "description": bp.description}
            for slug, bp in _REGISTRY.items()
        ]

        # Build prompt
        user_message = build_bootstrap_user_message(
            project_name=project.name,
            project_goal=project.goal,
            sources=source_data,
            available_types=available_types,
        )

        # Call Claude
        response = call_claude(
            system_prompt=BOOTSTRAP_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=8192,
        )

        # Parse JSON response — strip markdown fences if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        proposal_data = json.loads(cleaned)

        proposal.proposal = proposal_data
        proposal.status = BootstrapProposal.Status.PROPOSED
        proposal.save(update_fields=["proposal", "status", "updated_at"])

        logger.info("Bootstrap proposal generated for project %s", project.name)

    except Exception as e:
        logger.exception("Bootstrap failed for project %s: %s", project.name, e)
        proposal.status = BootstrapProposal.Status.FAILED
        proposal.error_message = str(e)[:1000]
        proposal.save(update_fields=["status", "error_message", "updated_at"])

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.tasks_consolidation import consolidate_sprint_documents

logger = logging.getLogger(__name__)


@receiver(post_save, sender="projects.Sprint")
def trigger_sprint_consolidation(sender, instance, created, **kwargs):
    """Trigger document consolidation when a sprint is done or paused."""
    if created:
        return

    if instance.status in ("done", "paused"):
        consolidate_sprint_documents.delay(str(instance.id))
        logger.info(
            "Sprint %s status=%s — triggered document consolidation",
            instance.id,
            instance.status,
        )

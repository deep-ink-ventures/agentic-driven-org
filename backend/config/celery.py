import os

from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("agentic_company")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_ready.connect
def recover_on_boot(**kwargs):
    """On worker start (local dev only), recover tasks and resume idle sprints."""
    from django.conf import settings

    if not settings.DEBUG:
        return

    from agents.tasks import recover_stuck_tasks, resume_idle_sprints
    from projects.tasks import recover_stuck_proposals, recover_stuck_provisioning

    recover_stuck_proposals.delay()
    recover_stuck_tasks.delay(on_boot=True)
    recover_stuck_provisioning.delay()
    resume_idle_sprints.delay()

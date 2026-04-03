import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def refill_approval_queue():
    """
    Every minute: for each active agent, if fewer than 5 tasks awaiting approval,
    ask Claude to propose the next highest-value task.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(is_active=True).select_related("department__project")

    for agent in agents:
        awaiting_count = AgentTask.objects.filter(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
        ).count()

        if awaiting_count >= 5:
            continue

        try:
            blueprint = agent.get_blueprint()
            proposal = blueprint.generate_task_proposal(agent)

            AgentTask.objects.create(
                agent=agent,
                status=AgentTask.Status.AWAITING_APPROVAL,
                auto_execute=False,
                exec_summary=proposal.get("exec_summary", "Proposed task"),
                step_plan=proposal.get("step_plan", ""),
            )
            logger.info("Proposed task for %s: %s", agent.name, proposal.get("exec_summary", "")[:80])

        except Exception as e:
            logger.exception("Failed to generate task proposal for %s: %s", agent.name, e)


@shared_task
def execute_hourly_tasks():
    """
    Every hour: for each active agent with auto_exec_hourly=True,
    create and execute a task from the hourly prompt.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(is_active=True, auto_exec_hourly=True).select_related("department__project")

    for agent in agents:
        try:
            blueprint = agent.get_blueprint()
            task = AgentTask.objects.create(
                agent=agent,
                status=AgentTask.Status.QUEUED,
                auto_execute=True,
                exec_summary=f"Hourly task: {blueprint.hourly_prompt[:100]}",
                step_plan=blueprint.hourly_prompt,
            )
            execute_agent_task.delay(str(task.id))
            logger.info("Created hourly task for %s: %s", agent.name, task.id)

        except Exception as e:
            logger.exception("Failed to create hourly task for %s: %s", agent.name, e)


@shared_task(bind=True, max_retries=0)
def execute_agent_task(self, task_id: str):
    """
    Execute a single agent task. Called when tasks are approved or auto-dispatched.
    Uses atomic guard to prevent double execution.
    """
    from agents.models import AgentTask

    # Atomic guard: only one worker can transition queued -> processing
    updated = AgentTask.objects.filter(
        id=task_id,
        status=AgentTask.Status.QUEUED,
    ).update(
        status=AgentTask.Status.PROCESSING,
        started_at=timezone.now(),
    )

    if updated == 0:
        current = AgentTask.objects.filter(id=task_id).values_list("status", flat=True).first()
        logger.warning("Task %s not queued (status=%s) — skipping", task_id, current)
        return

    task = AgentTask.objects.select_related(
        "agent__department__project",
    ).get(id=task_id)

    try:
        blueprint = task.agent.get_blueprint()
        report = blueprint.execute_task(task.agent, task)

        task.status = AgentTask.Status.DONE
        task.report = report
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "report", "completed_at", "updated_at"])

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task.status = AgentTask.Status.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

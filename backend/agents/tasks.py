import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def run_scheduled_actions(schedule: str):
    """
    Run all enabled scheduled commands for the given schedule type.
    Called by beat: hourly or daily.

    For each active agent, checks which commands with this schedule are enabled
    in auto_actions, and creates + executes tasks for them.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(is_active=True).select_related("department__project")

    for agent in agents:
        blueprint = agent.get_blueprint()
        scheduled_commands = blueprint.get_scheduled_commands(schedule)

        for cmd in scheduled_commands:
            cmd_name = cmd["name"]
            if not agent.is_action_enabled(cmd_name):
                continue

            try:
                # Run the command to get task details
                result = blueprint.run_command(cmd_name, agent)

                task = AgentTask.objects.create(
                    agent=agent,
                    status=AgentTask.Status.QUEUED,
                    auto_execute=True,
                    exec_summary=result.get("exec_summary", cmd["description"]),
                    step_plan=result.get("step_plan", ""),
                )
                execute_agent_task.delay(str(task.id))
                logger.info("Auto-executed %s for %s: %s", cmd_name, agent.name, task.id)

            except Exception as e:
                logger.exception("Failed to run scheduled command %s for %s: %s", cmd_name, agent.name, e)


@shared_task(bind=True, max_retries=0)
def execute_agent_task(self, task_id: str):
    """
    Execute a single agent task. Called when tasks are approved or auto-dispatched.
    Uses atomic guard to prevent double execution.
    Handles both immediate (QUEUED) and scheduled (PLANNED) tasks.
    """
    from agents.models import AgentTask

    updated = AgentTask.objects.filter(
        id=task_id,
        status__in=[AgentTask.Status.QUEUED, AgentTask.Status.PLANNED],
    ).update(
        status=AgentTask.Status.PROCESSING,
        started_at=timezone.now(),
    )

    if updated == 0:
        current = AgentTask.objects.filter(id=task_id).values_list("status", flat=True).first()
        logger.warning("Task %s not queued/planned (status=%s) — skipping", task_id, current)
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


@shared_task
def create_next_leader_task(leader_agent_id: str):
    """
    Self-perpetuating chain: when a leader task is approved, this creates
    the next priority task proposal. Called from AgentTask.approve().
    """
    from agents.models import Agent, AgentTask
    from agents.blueprints.base import LeaderBlueprint

    try:
        agent = Agent.objects.select_related("department__project").get(
            id=leader_agent_id,
            is_leader=True,
            is_active=True,
        )
    except Agent.DoesNotExist:
        logger.warning("Leader agent %s not found or inactive", leader_agent_id)
        return

    blueprint = agent.get_blueprint()
    if not isinstance(blueprint, LeaderBlueprint):
        logger.warning("Agent %s is not a leader blueprint", agent.name)
        return

    try:
        proposal = blueprint.generate_task_proposal(agent)

        target_type = proposal.get("target_agent_type")
        if target_type:
            target_agent = Agent.objects.filter(
                department=agent.department,
                agent_type=target_type,
                is_active=True,
                is_leader=False,
            ).first()
            if target_agent:
                AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=AgentTask.Status.AWAITING_APPROVAL,
                    auto_execute=False,
                    exec_summary=proposal.get("exec_summary", "Priority task"),
                    step_plan=proposal.get("step_plan", ""),
                )
                logger.info("Leader %s proposed task for %s: %s", agent.name, target_agent.name, proposal.get("exec_summary", "")[:80])
                return

        AgentTask.objects.create(
            agent=agent,
            status=AgentTask.Status.AWAITING_APPROVAL,
            auto_execute=False,
            exec_summary=proposal.get("exec_summary", "Leader task"),
            step_plan=proposal.get("step_plan", ""),
        )
        logger.info("Leader %s proposed own task: %s", agent.name, proposal.get("exec_summary", "")[:80])

    except Exception as e:
        logger.exception("Failed to create next leader task for %s: %s", agent.name, e)

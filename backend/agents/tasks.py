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

                if result is None:
                    logger.info("Command %s for %s returned None — skipping", cmd_name, agent.name)
                    continue

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

        _unblock_dependents(task)

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task.status = AgentTask.Status.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])


def _unblock_dependents(completed_task):
    """When a task completes, unblock any tasks waiting on it."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=completed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent")

    for dep in dependents:
        if dep.command_name and dep.agent.is_action_enabled(dep.command_name):
            dep.status = AgentTask.Status.QUEUED
            dep.save(update_fields=["status", "updated_at"])
            execute_agent_task.delay(str(dep.id))
            logger.info("Auto-unblocked and queued task %s (command: %s)", dep.id, dep.command_name)
        else:
            dep.status = AgentTask.Status.AWAITING_APPROVAL
            dep.save(update_fields=["status", "updated_at"])
            logger.info("Unblocked task %s → awaiting approval", dep.id)


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

        if proposal is None:
            logger.info("Leader %s has nothing to propose (no active workforce)", agent.name)
            return

        # Multi-task format: proposal has "tasks" list
        tasks_data = proposal.get("tasks", [])
        if tasks_data:
            workforce_agents = {
                a.agent_type: a
                for a in Agent.objects.filter(
                    department=agent.department,
                    is_active=True,
                    is_leader=False,
                )
            }
            previous_task = None
            created = 0
            for task_data in tasks_data:
                target_type = task_data.get("target_agent_type")
                target_agent = workforce_agents.get(target_type)
                if not target_agent:
                    logger.warning("Leader %s: no active agent of type %s", agent.name, target_type)
                    continue

                depends_on_previous = task_data.get("depends_on_previous", False)
                command_name = task_data.get("command_name", "")

                # Determine initial status
                if depends_on_previous and previous_task:
                    initial_status = AgentTask.Status.AWAITING_DEPENDENCIES
                    blocked_by = previous_task
                elif command_name and target_agent.is_action_enabled(command_name):
                    initial_status = AgentTask.Status.QUEUED
                    blocked_by = None
                else:
                    initial_status = AgentTask.Status.AWAITING_APPROVAL
                    blocked_by = None

                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                )

                if initial_status == AgentTask.Status.QUEUED:
                    execute_agent_task.delay(str(new_task.id))

                previous_task = new_task
                created += 1
            logger.info("Leader %s proposed %d task(s): %s", agent.name, created, proposal.get("exec_summary", "")[:80])
            return

        # Fallback: single task on the leader itself
        if proposal.get("exec_summary"):
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

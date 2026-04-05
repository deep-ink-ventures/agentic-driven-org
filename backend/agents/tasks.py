import logging

from celery import shared_task
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


def _broadcast_task(task, event_type="task.updated"):
    """Send task update via WebSocket to the project channel."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    try:
        project_id = str(task.agent.department.project_id)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"project_{project_id}",
            {
                "type": event_type.replace(".", "_"),
                "task": {
                    "id": str(task.id),
                    "agent": str(task.agent_id),
                    "agent_name": task.agent.name,
                    "agent_type": task.agent.agent_type,
                    "created_by_agent": str(task.created_by_agent_id) if task.created_by_agent_id else None,
                    "created_by_agent_name": task.created_by_agent.name if task.created_by_agent else None,
                    "status": task.status,
                    "auto_execute": task.auto_execute,
                    "command_name": task.command_name,
                    "blocked_by": str(task.blocked_by_id) if task.blocked_by_id else None,
                    "blocked_by_summary": task.blocked_by.exec_summary if task.blocked_by else None,
                    "exec_summary": task.exec_summary,
                    "step_plan": task.step_plan,
                    "report": task.report,
                    "error_message": task.error_message,
                    "proposed_exec_at": task.proposed_exec_at.isoformat() if task.proposed_exec_at else None,
                    "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "token_usage": task.token_usage,
                    "review_verdict": task.review_verdict,
                    "review_score": task.review_score,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.exception("Failed to broadcast task update")


@shared_task
def run_scheduled_actions(schedule: str):
    """
    Run all enabled scheduled commands for the given schedule type.
    Called by beat: hourly or daily.

    For each active agent, checks which commands with this schedule are enabled
    with auto_approve enabled, and creates + executes tasks for them.
    """
    from agents.models import Agent, AgentTask

    agents = Agent.objects.filter(status="active").select_related("department__project")

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
                task = AgentTask.objects.select_related(
                    "agent__department__project",
                    "blocked_by",
                    "created_by_agent",
                ).get(id=task.id)
                _broadcast_task(task, "task.created")
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
        "blocked_by",
        "created_by_agent",
    ).get(id=task_id)

    # Broadcast processing status
    _broadcast_task(task)

    try:
        blueprint = task.agent.get_blueprint()
        report = blueprint.execute_task(task.agent, task)

        task.status = AgentTask.Status.DONE
        task.report = report
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "report", "completed_at", "updated_at"])

        _broadcast_task(task)
        _unblock_dependents(task)
        _trigger_continuous_mode(task)

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        task.status = AgentTask.Status.FAILED
        task.error_message = str(e)[:500]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])

        _broadcast_task(task)


def _unblock_dependents(completed_task):
    """When a task completes, unblock any tasks waiting on it."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=completed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent", "agent__department__project", "blocked_by", "created_by_agent")

    for dep in dependents:
        if dep.command_name and dep.agent.is_action_enabled(dep.command_name):
            dep.status = AgentTask.Status.QUEUED
            dep.save(update_fields=["status", "updated_at"])
            _broadcast_task(dep)
            execute_agent_task.delay(str(dep.id))
            logger.info("Auto-unblocked and queued task %s (command: %s)", dep.id, dep.command_name)
        else:
            dep.status = AgentTask.Status.AWAITING_APPROVAL
            dep.save(update_fields=["status", "updated_at"])
            _broadcast_task(dep)
            logger.info("Unblocked task %s → awaiting approval", dep.id)


@shared_task
def recover_stuck_tasks():
    """
    Self-healing: find AgentTask records stuck in processing for >1 hour.
    Marks them failed so users can retry via the UI.
    Runs every 15 minutes via celery beat.
    """
    from datetime import timedelta

    from agents.models import AgentTask

    now = timezone.now()
    cutoff = now - timedelta(hours=1)

    stuck = (
        AgentTask.objects.filter(
            status=AgentTask.Status.PROCESSING,
        )
        .filter(
            models.Q(started_at__isnull=True) | models.Q(started_at__lt=cutoff),
        )
        .select_related("agent", "agent__department__project", "created_by_agent", "blocked_by")
    )

    for task in stuck:
        logger.warning("Recovering stuck task %s (%s): %s", task.id, task.agent.name, task.exec_summary[:80])
        task.status = AgentTask.Status.FAILED
        task.error_message = "Worker died — task was processing for over 1 hour without completing"
        task.completed_at = now
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        _broadcast_task(task)


def _trigger_continuous_mode(completed_task):
    """In continuous mode, immediately trigger leader to evaluate next work."""
    from agents.blueprints import DEPARTMENTS

    department = completed_task.agent.department
    dept_def = DEPARTMENTS.get(department.department_type, {})
    default_mode = dept_def.get("execution_mode", "scheduled")
    exec_mode = (department.config or {}).get("execution_mode", default_mode)

    if exec_mode != "continuous":
        return

    delay = (department.config or {}).get(
        "min_delay_seconds",
        dept_def.get("min_delay_seconds", 0),
    )

    leader = department.agents.filter(is_leader=True, status="active").first()
    if leader:
        create_next_leader_task.apply_async(
            args=[str(leader.id)],
            countdown=delay,
        )
        logger.info(
            "Continuous mode: triggering leader %s (delay=%ds)",
            leader.name,
            delay,
        )


@shared_task
def create_next_leader_task(leader_agent_id: str):
    """
    Self-perpetuating chain: when a leader task is approved, this creates
    the next priority task proposal. Called from AgentTask.approve().
    """
    from agents.blueprints.base import LeaderBlueprint
    from agents.models import Agent, AgentTask

    try:
        agent = Agent.objects.select_related("department__project").get(
            id=leader_agent_id,
            is_leader=True,
            status="active",
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
                    status="active",
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
                elif command_name and target_agent.is_action_enabled(command_name) or target_agent.auto_approve:
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
                # Reload with relations for broadcast
                new_task = AgentTask.objects.select_related(
                    "agent__department__project",
                    "blocked_by",
                    "created_by_agent",
                ).get(id=new_task.id)
                _broadcast_task(new_task, "task.created")

                if initial_status == AgentTask.Status.QUEUED:
                    execute_agent_task.delay(str(new_task.id))

                previous_task = new_task
                created += 1
            logger.info("Leader %s proposed %d task(s): %s", agent.name, created, proposal.get("exec_summary", "")[:80])
            return

        # Fallback: single task on the leader itself
        if proposal.get("exec_summary"):
            initial_status = AgentTask.Status.QUEUED if agent.auto_approve else AgentTask.Status.AWAITING_APPROVAL
            new_task = AgentTask.objects.create(
                agent=agent,
                status=initial_status,
                auto_execute=False,
                exec_summary=proposal.get("exec_summary", "Leader task"),
                step_plan=proposal.get("step_plan", ""),
            )
            new_task = AgentTask.objects.select_related(
                "agent__department__project",
                "blocked_by",
                "created_by_agent",
            ).get(id=new_task.id)
            _broadcast_task(new_task, "task.created")
            if initial_status == AgentTask.Status.QUEUED:
                execute_agent_task.delay(str(new_task.id))
            logger.info("Leader %s proposed own task: %s", agent.name, proposal.get("exec_summary", "")[:80])

    except Exception as e:
        logger.exception("Failed to create next leader task for %s: %s", agent.name, e)

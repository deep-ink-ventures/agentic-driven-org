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
                    "department": str(task.agent.department_id),
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
                    "sprint": str(task.sprint_id) if task.sprint_id else None,
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
    in enabled_commands, and creates + executes tasks for them.
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
                    command_name=cmd_name,
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


def _mark_task_failed(task, error_message: str):
    """Mark a task as failed, retrying with a fresh DB connection if needed.

    When PostgreSQL drops the connection (AdminShutdown, timeouts), the original
    connection is dead.  We attempt the save; on OperationalError we close stale
    connections and retry once so the task doesn't stay stuck in PROCESSING.
    """
    from django.db import OperationalError as DjangoOpError
    from django.db import close_old_connections

    def _do_save():
        task.status = task.__class__.Status.FAILED
        task.error_message = error_message
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        _broadcast_task(task)
        _fail_dependents(task)
        _trigger_next_sprint_work(task)

    try:
        _do_save()
    except DjangoOpError:
        logger.warning("DB connection dead while marking task %s failed — retrying with fresh connection", task.id)
        try:
            close_old_connections()
            _do_save()
        except Exception:
            logger.exception("Could not mark task %s as failed (DB unavailable)", task.id)


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
        _trigger_next_sprint_work(task)

        logger.info("Task %s completed: %s", task_id, task.exec_summary[:80])

    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)
        _mark_task_failed(task, str(e)[:500])


def _fail_dependents(failed_task):
    """When a task fails, cascade failure to any tasks waiting on it."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=failed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent", "agent__department__project", "blocked_by", "created_by_agent")

    for dep in dependents:
        summary = (failed_task.exec_summary or "")[:200]
        dep.status = AgentTask.Status.FAILED
        dep.error_message = f"Upstream task failed: {summary}"
        dep.completed_at = timezone.now()
        dep.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        _broadcast_task(dep)
        logger.info("Cascade-failed task %s due to upstream %s", dep.id, failed_task.id)
        # Recurse to cascade through chains (A→B→C)
        _fail_dependents(dep)


def _unblock_dependents(completed_task):
    """When a task completes, unblock any tasks waiting on it."""
    from agents.models import AgentTask

    dependents = AgentTask.objects.filter(
        blocked_by=completed_task,
        status=AgentTask.Status.AWAITING_DEPENDENCIES,
    ).select_related("agent", "agent__department__project", "blocked_by", "created_by_agent")

    for dep in dependents:
        if dep.agent.is_action_enabled(dep.command_name):
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


def _apply_on_dispatch(agent, on_dispatch, sprint_id=None):
    """Apply state transition after tasks are successfully created.

    Prevents state desync: if task creation fails (celery down, old worker, etc.),
    the leader state remains unchanged and can be retried cleanly.
    """
    from projects.models import Sprint

    set_status = on_dispatch.get("set_status")
    stage = on_dispatch.get("stage")
    if not set_status or not stage:
        return

    # Use sprint department_state if sprint is available
    sprint = None
    if sprint_id:
        sprint = Sprint.objects.filter(id=sprint_id).first()

    if sprint:
        dept_id = str(agent.department_id)
        dept_state = sprint.get_department_state(dept_id)
        stage_status = dept_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        current_info["status"] = set_status
        stage_status[stage] = current_info
        dept_state["stage_status"] = stage_status
        sprint.set_department_state(dept_id, dept_state)
    else:
        # Fallback for departments not yet migrated
        agent.refresh_from_db()
        internal_state = agent.internal_state or {}
        stage_status = internal_state.get("stage_status", {})
        current_info = stage_status.get(stage, {"iterations": 0})
        current_info["status"] = set_status
        stage_status[stage] = current_info
        internal_state["stage_status"] = stage_status
        agent.internal_state = internal_state
        agent.save(update_fields=["internal_state"])
    logger.info("Leader %s: stage '%s' → %s (on_dispatch)", agent.name, stage, set_status)


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
        _fail_dependents(task)
        _trigger_next_sprint_work(task)


def _trigger_next_sprint_work(completed_task):
    """After task completion, trigger leader if department has running sprints."""
    from projects.models import Sprint

    department = completed_task.agent.department

    has_running_sprints = Sprint.objects.filter(
        departments=department,
        status=Sprint.Status.RUNNING,
    ).exists()

    if not has_running_sprints:
        return

    leader = department.agents.filter(is_leader=True, status="active").first()
    if leader:
        create_next_leader_task.delay(str(leader.id))
        logger.info("Sprint work: triggering leader %s after task completion", leader.name)


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

        # Extract metadata from proposal (set by generate_task_proposal)
        sprint_id = proposal.pop("_sprint_id", None) if proposal else None
        on_dispatch = proposal.pop("_on_dispatch", None) if proposal else None

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

                # Validate command_name against blueprint
                bp = target_agent.get_blueprint()
                valid_commands = {c["name"] for c in bp.get_commands()} if bp else set()

                if not command_name or command_name not in valid_commands:
                    error_msg = (
                        f"Invalid command '{command_name}' for {target_type}. "
                        f"Valid commands: {sorted(valid_commands)}"
                    )
                    logger.warning("Leader %s: %s", agent.name, error_msg)
                    failed_task = AgentTask.objects.create(
                        agent=target_agent,
                        created_by_agent=agent,
                        status=AgentTask.Status.FAILED,
                        command_name=command_name or "INVALID",
                        sprint_id=sprint_id,
                        exec_summary=task_data.get("exec_summary", "Invalid task"),
                        error_message=error_msg,
                        completed_at=timezone.now(),
                    )
                    failed_task = AgentTask.objects.select_related(
                        "agent__department__project",
                        "blocked_by",
                        "created_by_agent",
                    ).get(id=failed_task.id)
                    _broadcast_task(failed_task, "task.created")
                    continue

                # Determine initial status
                if depends_on_previous and previous_task:
                    initial_status = AgentTask.Status.AWAITING_DEPENDENCIES
                    blocked_by = previous_task
                elif target_agent.is_action_enabled(command_name):
                    initial_status = AgentTask.Status.QUEUED
                    blocked_by = None
                else:
                    initial_status = AgentTask.Status.AWAITING_APPROVAL
                    blocked_by = None

                # Resolve cloned_agent FK if provided by fan-out proposals
                cloned_agent_id = task_data.get("_cloned_agent_id")
                cloned_agent = None
                if cloned_agent_id:
                    from agents.models import ClonedAgent

                    cloned_agent = ClonedAgent.objects.filter(id=cloned_agent_id).first()

                new_task = AgentTask.objects.create(
                    agent=target_agent,
                    created_by_agent=agent,
                    status=initial_status,
                    command_name=command_name,
                    blocked_by=blocked_by,
                    sprint_id=sprint_id,
                    exec_summary=task_data.get("exec_summary", "Priority task"),
                    step_plan=task_data.get("step_plan", ""),
                    cloned_agent=cloned_agent,
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
            # Apply state transition AFTER tasks are created (prevents desync if task creation fails)
            if created > 0 and on_dispatch:
                _apply_on_dispatch(agent, on_dispatch, sprint_id=sprint_id)

            logger.info("Leader %s proposed %d task(s): %s", agent.name, created, proposal.get("exec_summary", "")[:80])
            return

    except Exception as e:
        logger.exception("Failed to create next leader task for %s: %s", agent.name, e)

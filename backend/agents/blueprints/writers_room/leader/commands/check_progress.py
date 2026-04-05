"""Leader command: check progress on the writers room, update stage status, unblock stalled work."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="check-progress",
    description="Check stage progress, update status based on completed tasks, detect stalled work, report status",
    schedule="hourly",
    model="claude-haiku-4-5",
)
def check_progress(self, agent: Agent) -> dict:
    """
    Hourly progress check. Updates internal_state based on completed tasks,
    detects stalled work, and transitions stage status.
    """
    from django.utils import timezone

    from agents.models import AgentTask

    department = agent.department
    internal_state = agent.internal_state or {}
    stage_status = internal_state.get("stage_status", {})
    current_stage = internal_state.get("current_stage", "logline")
    now = timezone.now()

    issues = []

    # ── Check for stalled tasks (running > 2 hours) ────────────────────
    stalled = list(
        AgentTask.objects.filter(
            agent__department=department,
            status__in=[AgentTask.Status.PROCESSING, AgentTask.Status.PROCESSING],
        ).values_list("id", "exec_summary", "started_at", "agent__name", "agent__agent_type")
    )
    stalled_count = 0
    for task_id, es, started_at, agent_name, _agent_type in stalled:
        if started_at and (now - started_at).total_seconds() > 2 * 3600:
            stalled_count += 1
            issues.append(f"Task {task_id} ({agent_name}) stalled for >2h: {es[:100]}")

    # ── Count active, queued, completed tasks ──────────────────────────
    active_count = AgentTask.objects.filter(
        agent__department=department,
        status__in=[AgentTask.Status.PROCESSING, AgentTask.Status.PROCESSING],
    ).count()

    queued_count = AgentTask.objects.filter(
        agent__department=department,
        status__in=[AgentTask.Status.QUEUED, AgentTask.Status.AWAITING_APPROVAL],
    ).count()

    # ── Detect stage transitions ───────────────────────────────────────
    # If current stage is "writing_in_progress" and no active creative tasks -> writing_done
    current_info = stage_status.get(current_stage, {})
    status = current_info.get("status", "not_started")

    from agents.blueprints.writers_room.leader.agent import CREATIVE_MATRIX, FEEDBACK_MATRIX

    if status == "writing_in_progress":
        creative_types = CREATIVE_MATRIX.get(current_stage, [])
        active_creative = AgentTask.objects.filter(
            agent__department=department,
            agent__agent_type__in=creative_types,
            status__in=[
                AgentTask.Status.PROCESSING,
                AgentTask.Status.QUEUED,
                AgentTask.Status.PROCESSING,
                AgentTask.Status.AWAITING_APPROVAL,
            ],
        ).count()
        if active_creative == 0:
            # Check if any completed recently
            completed_creative = AgentTask.objects.filter(
                agent__department=department,
                agent__agent_type__in=creative_types,
                status=AgentTask.Status.DONE,
            ).exists()
            if completed_creative:
                current_info["status"] = "writing_done"
                stage_status[current_stage] = current_info
                logger.info("Writers Room: stage '%s' writing complete, ready for feedback", current_stage)

    elif status == "feedback_in_progress":
        feedback_types = [at for at, _ in FEEDBACK_MATRIX.get(current_stage, [])]
        active_feedback = AgentTask.objects.filter(
            agent__department=department,
            agent__agent_type__in=feedback_types,
            status__in=[
                AgentTask.Status.PROCESSING,
                AgentTask.Status.QUEUED,
                AgentTask.Status.PROCESSING,
                AgentTask.Status.AWAITING_APPROVAL,
            ],
        ).count()
        if active_feedback == 0:
            completed_feedback = AgentTask.objects.filter(
                agent__department=department,
                agent__agent_type__in=feedback_types,
                status=AgentTask.Status.DONE,
            ).exists()
            if completed_feedback:
                current_info["status"] = "feedback_done"
                stage_status[current_stage] = current_info
                logger.info("Writers Room: stage '%s' feedback complete, ready for evaluation", current_stage)

    elif status == "fix_in_progress":
        # Check if fix tasks are done
        active_fixes = AgentTask.objects.filter(
            agent__department=department,
            agent__is_leader=False,
            status__in=[
                AgentTask.Status.PROCESSING,
                AgentTask.Status.QUEUED,
                AgentTask.Status.PROCESSING,
                AgentTask.Status.AWAITING_APPROVAL,
            ],
        ).count()
        if active_fixes == 0:
            current_info["status"] = "writing_done"
            stage_status[current_stage] = current_info
            logger.info("Writers Room: stage '%s' fixes complete, re-running feedback", current_stage)

    # ── Save updated state ──────────────────────────────────────────────
    internal_state["stage_status"] = stage_status
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    # ── Build status report ─────────────────────────────────────────────
    report_lines = [
        f"Current stage: {current_stage}",
        f"Stage status: {current_info.get('status', 'not_started')}",
        f"Iterations: {current_info.get('iterations', 0)}",
    ]
    if issues:
        report_lines.append("\nISSUES:")
        report_lines.extend(f"  - {i}" for i in issues)
    report_lines.append(f"\nActive tasks: {active_count}")
    report_lines.append(f"Queued tasks: {queued_count}")
    report_lines.append(f"Stalled tasks: {stalled_count}")
    report_lines.append(f"\nFull stage status: {json.dumps(stage_status, indent=2)}")

    # If state advanced, trigger the leader chain directly instead of
    # going through Claude delegation (which can create unwanted PLANNED tasks)
    state_advanced = current_info.get("status") in ("writing_done", "feedback_done")
    if state_advanced:
        from agents.tasks import create_next_leader_task

        create_next_leader_task.delay(str(agent.id))
        logger.info("Writers Room check_progress: state advanced, triggered leader chain")

    # Return None so the base execute_task does not create follow-up tasks
    # via Claude delegation. The state machine drives the pipeline.
    return None

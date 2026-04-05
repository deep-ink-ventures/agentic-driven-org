"""Leader command: check progress on pending work, unblock stalled tasks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.models import Agent

from agents.blueprints.base import command

logger = logging.getLogger(__name__)


@command(
    name="check-progress",
    description="Check pending runs, stalled tasks, clear stale file locks, report status",
    schedule="hourly",
    model="claude-haiku-4-5",
)
def check_progress(self, agent: Agent) -> dict:
    from django.utils import timezone

    from agents.models import AgentTask

    department = agent.department
    project = department.project
    config = {**project.config, **department.config, **agent.config}
    webhook_timeout = config.get("webhook_timeout_minutes", 120)
    max_review_iterations = config.get("max_review_iterations", 10)

    internal_state = agent.internal_state or {}
    pending_runs = internal_state.get("pending_runs", {})
    files_claimed = internal_state.get("files_claimed", {})
    review_rounds = internal_state.get("review_rounds", {})

    now = timezone.now()
    issues = []
    follow_up_tasks = []

    # ── Check for timed-out webhook runs ────────────────────────────────
    stale_runs = []
    for run_id, run_info in list(pending_runs.items()):
        started = run_info.get("timestamp")
        if started:
            from django.utils.dateparse import parse_datetime

            started_dt = parse_datetime(started) if isinstance(started, str) else started
            if started_dt and (now - started_dt).total_seconds() > webhook_timeout * 60:
                stale_runs.append(run_id)
                issues.append(f"Workflow run {run_id} timed out after {webhook_timeout} min (started {started})")
                # Mark as failed
                pending_runs[run_id]["status"] = "timed_out"

    for run_id in stale_runs:
        run_info = pending_runs.pop(run_id, {})
        logger.warning("Marking stale workflow run %s as timed out", run_id)

    # ── Check for stalled tasks (running > 3 hours) ────────────────────
    stalled = list(
        AgentTask.objects.filter(
            agent__department=department,
            status__in=[AgentTask.Status.PROCESSING, AgentTask.Status.PROCESSING],
        ).values_list("id", "exec_summary", "started_at", "agent__name", "agent__agent_type")
    )
    for task_id, es, started_at, agent_name, _agent_type in stalled:
        if started_at and (now - started_at).total_seconds() > 3 * 3600:
            issues.append(f"Task {task_id} ({agent_name}) stalled for >3h: {es[:100]}")

    # ── Clear stale file locks for completed tasks ──────────────────────
    cleared_locks = []
    if files_claimed:
        active_task_ids = set(
            str(tid)
            for tid in AgentTask.objects.filter(
                agent__department=department,
                status__in=[
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.QUEUED,
                    AgentTask.Status.PROCESSING,
                    AgentTask.Status.AWAITING_APPROVAL,
                ],
            ).values_list("id", flat=True)
        )
        for filepath, lock_info in list(files_claimed.items()):
            lock_task_id = str(lock_info.get("task_id", ""))
            if lock_task_id and lock_task_id not in active_task_ids:
                cleared_locks.append(filepath)
                del files_claimed[filepath]

    if cleared_locks:
        logger.info("Cleared %d stale file locks", len(cleared_locks))

    # ── Check review iteration counts ───────────────────────────────────
    for pr_number, rounds in review_rounds.items():
        if isinstance(rounds, int) and rounds >= max_review_iterations:
            issues.append(f"PR #{pr_number} has reached {rounds} review iterations — escalating to human")
            follow_up_tasks.append(
                {
                    "target_agent_type": "leader",
                    "exec_summary": f"ESCALATION: PR #{pr_number} reached {rounds} review rounds — needs human intervention",
                    "step_plan": f"PR #{pr_number} has been through {rounds} review cycles without converging. Review the PR manually and decide next steps.",
                }
            )

    # ── Check for unblocked tasks that can now proceed ──────────────────
    awaiting = list(
        AgentTask.objects.filter(
            agent__department=department,
            status=AgentTask.Status.AWAITING_APPROVAL,
        )
        .select_related("agent")
        .order_by("created_at")[:20]
    )

    # ── Check for queued work needing assignment ────────────────────────
    queued = list(
        AgentTask.objects.filter(
            agent__department=department,
            status=AgentTask.Status.QUEUED,
        )
        .select_related("agent")
        .order_by("created_at")[:20]
    )

    # ── Save updated state ──────────────────────────────────────────────
    internal_state["pending_runs"] = pending_runs
    internal_state["files_claimed"] = files_claimed
    agent.internal_state = internal_state
    agent.save(update_fields=["internal_state"])

    # ── Build status report ─────────────────────────────────────────────
    report_lines = []
    if issues:
        report_lines.append("ISSUES:")
        report_lines.extend(f"  - {i}" for i in issues)
    if cleared_locks:
        report_lines.append(f"\nCleared {len(cleared_locks)} stale file locks: {', '.join(cleared_locks[:5])}")
    report_lines.append(f"\nPending webhook runs: {len(pending_runs)}")
    report_lines.append(
        f"Stalled tasks: {len([s for s in stalled if s[2] and (now - s[2]).total_seconds() > 3 * 3600])}"
    )
    report_lines.append(f"Queued tasks: {len(queued)}")
    report_lines.append(f"Awaiting approval: {len(awaiting)}")
    report_lines.append(f"Active file locks: {len(files_claimed)}")

    result = {
        "exec_summary": f"Progress check: {len(issues)} issues, {len(pending_runs)} pending runs, {len(queued)} queued",
        "step_plan": "\n".join(report_lines),
    }

    if follow_up_tasks:
        result["tasks"] = follow_up_tasks

    return result

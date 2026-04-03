"""Celery tasks — full implementation in Task 8."""

from celery import shared_task


@shared_task
def execute_agent_task(task_id: str):
    raise NotImplementedError("Task execution not yet implemented")


@shared_task
def refill_approval_queue():
    raise NotImplementedError("Not yet implemented")


@shared_task
def execute_hourly_tasks():
    raise NotImplementedError("Not yet implemented")

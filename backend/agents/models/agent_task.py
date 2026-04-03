import uuid

from django.db import models
from django.utils import timezone


class AgentTask(models.Model):
    class Status(models.TextChoices):
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    created_by_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_tasks",
        help_text="Set when a superior agent delegates this task",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AWAITING_APPROVAL,
        db_index=True,
    )
    auto_execute = models.BooleanField(default=False)
    exec_summary = models.TextField(blank=True, help_text="Short description of what to do")
    step_plan = models.TextField(blank=True, help_text="Detailed step-by-step plan")
    report = models.TextField(blank=True, help_text="What was actually done")
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def approve(self):
        if self.status != self.Status.AWAITING_APPROVAL:
            return False
        self.status = self.Status.QUEUED
        self.save(update_fields=["status", "updated_at"])
        from agents.tasks import execute_agent_task
        execute_agent_task.delay(str(self.id))
        return True

    def __str__(self):
        return f"[{self.get_status_display()}] {self.agent.name}: {self.exec_summary[:60]}"

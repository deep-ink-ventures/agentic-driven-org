import uuid

from django.db import models
from django.utils import timezone


class AgentTask(models.Model):
    class Status(models.TextChoices):
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        AWAITING_DEPENDENCIES = "awaiting_dependencies", "Awaiting Dependencies"
        PLANNED = "planned", "Planned"
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
        help_text="Set when the department leader delegates this task",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AWAITING_APPROVAL,
        db_index=True,
    )
    auto_execute = models.BooleanField(default=False)
    command_name = models.CharField(
        max_length=100,
        help_text="Command on the agent's blueprint this task executes. Required.",
    )
    blocked_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependents",
        help_text="This task can't run until the blocker completes.",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    exec_summary = models.TextField(blank=True, help_text="Short description of what to do")
    step_plan = models.TextField(blank=True, help_text="Detailed step-by-step plan")
    proposed_exec_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Agent-proposed optimal execution time",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Confirmed execution time (set on approval)",
    )
    report = models.TextField(blank=True, help_text="What was actually done")
    error_message = models.TextField(blank=True)
    token_usage = models.JSONField(
        null=True,
        blank=True,
        help_text="Token usage from Claude API: {model, input_tokens, output_tokens, cost_estimate}",
    )
    review_verdict = models.CharField(
        max_length=20,
        blank=True,
        help_text="Structured verdict from reviewer: APPROVED or CHANGES_REQUESTED",
    )
    review_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Review score 0.0-10.0 from structured verdict",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.command_name:
            raise ValidationError({"command_name": "command_name is required for every task."})

        bp = self.agent.get_blueprint()
        if bp:
            valid_commands = {c["name"] for c in bp.get_commands()}
            if valid_commands and self.command_name not in valid_commands:
                raise ValidationError(
                    {
                        "command_name": f"'{self.command_name}' is not a valid command for {self.agent.agent_type}. Valid: {sorted(valid_commands)}"
                    }
                )

    def approve(self):
        """Approve task: schedule or queue for execution. If leader task, auto-propose next."""
        if self.status != self.Status.AWAITING_APPROVAL:
            return False

        from agents.tasks import execute_agent_task

        if self.proposed_exec_at and self.proposed_exec_at > timezone.now():
            # Schedule for future execution
            self.status = self.Status.PLANNED
            self.scheduled_at = self.proposed_exec_at
            self.save(update_fields=["status", "scheduled_at", "updated_at"])
            execute_agent_task.apply_async(args=[str(self.id)], eta=self.scheduled_at)
        else:
            # Execute immediately
            self.status = self.Status.QUEUED
            self.save(update_fields=["status", "updated_at"])
            execute_agent_task.delay(str(self.id))

        # Self-perpetuating chain: if this is a leader task, create the next proposal
        if self.agent.is_leader:
            from agents.tasks import create_next_leader_task

            create_next_leader_task.delay(str(self.agent.id))

        return True

    def __str__(self):
        return f"[{self.get_status_display()}] {self.agent.name}: {self.exec_summary[:60]}"

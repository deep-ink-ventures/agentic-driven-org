import uuid

from django.conf import settings
from django.db import models


class Sprint(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        DONE = "done", "Done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    departments = models.ManyToManyField(
        "projects.Department",
        related_name="sprints",
    )
    text = models.TextField(help_text="The work instruction from the user")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    completion_summary = models.TextField(
        blank=True,
        help_text="Leader-provided summary when marking sprint done",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    department_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-department pipeline state keyed by department ID. Reset clears this.",
    )

    def get_department_state(self, department_id) -> dict:
        """Get pipeline state for a department in this sprint."""
        return self.department_state.get(str(department_id), {})

    def set_department_state(self, department_id, state: dict):
        """Set pipeline state for a department in this sprint."""
        self.department_state[str(department_id)] = state
        self.save(update_fields=["department_state", "updated_at"])

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status}] {self.text[:60]} — {self.project.name}"

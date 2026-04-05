import uuid

from django.conf import settings
from django.db import models


class Briefing(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="briefings",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="briefings",
        help_text="Null = project-level briefing (cascades to all departments)",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="briefings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        scope = self.department.name if self.department else "project-level"
        return f"{self.title} ({scope}) — {self.project.name}"

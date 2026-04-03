import uuid

from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department_type = models.CharField(
        max_length=50,
        default="marketing",
        help_text="Department type — must match a blueprint folder (e.g. social_media, engineering)",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "department_type")]

    @property
    def name(self):
        """Display name from blueprint registry."""
        from agents.blueprints import DEPARTMENTS
        dept = DEPARTMENTS.get(self.department_type)
        return dept["name"] if dept else self.department_type

    def __str__(self):
        return f"{self.project.name} / {self.name}"

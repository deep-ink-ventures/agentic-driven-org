import uuid

from django.db import models


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("project", "name")]

    def __str__(self):
        return f"{self.project.name} / {self.name}"

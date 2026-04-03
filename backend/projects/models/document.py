import uuid

from django.db import models


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, help_text="Document content in markdown")
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    tags = models.ManyToManyField("projects.Tag", blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

import uuid

from django.conf import settings
from django.db import models


class SprintNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="notes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sprint_notes",
    )
    text = models.TextField(help_text="The note content")
    sources = models.ManyToManyField(
        "projects.Source",
        blank=True,
        related_name="sprint_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note on {self.sprint} by {self.user.email} — {self.text[:40]}"

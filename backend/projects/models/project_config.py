import uuid

from django.db import models


class ProjectConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g. 'Hotel Berlin Google Account'")
    google_email = models.EmailField(blank=True, help_text="Gmail address agents act on behalf of")
    google_credentials = models.JSONField(
        default=dict,
        blank=True,
        help_text="OAuth tokens, refresh token, etc.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

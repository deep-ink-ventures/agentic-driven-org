import uuid

from django.conf import settings
from django.db import models


class Source(models.Model):
    class SourceType(models.TextChoices):
        FILE = "file", "File"
        URL = "url", "URL"
        TEXT = "text", "Text"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_type = models.CharField(
        max_length=10,
        choices=SourceType.choices,
        default=SourceType.FILE,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True)
    file_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="Storage path — private, never expose directly.",
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hex digest of file content.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sources",
        null=True,
        blank=True,
    )
    raw_content = models.TextField(
        blank=True,
        help_text="For text sources: the raw text. For files: unprocessed extracted text.",
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Cleaned text ready for Claude analysis.",
    )
    summary = models.TextField(
        blank=True,
        help_text="Claude-generated summary of the full source content. Used in prompts instead of truncated text.",
    )
    file_format = models.CharField(max_length=20, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    word_count = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_hash"],
                name="unique_content_per_user",
                condition=models.Q(content_hash__gt=""),
            ),
        ]

    def __str__(self):
        if self.source_type == "file":
            return f"{self.original_filename} — {self.project.name}"
        elif self.source_type == "url":
            return f"{self.url[:60]} — {self.project.name}"
        return f"Text source — {self.project.name}"

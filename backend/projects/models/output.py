import uuid

from django.db import models


class Output(models.Model):
    """
    Sprint output artifact — the deliverable a department produces.

    Each department contributes at most one output per sprint, representing
    the latest refined version. The Head Of updates it after each cycle.

    Content types:
    - markdown/plaintext: inline text in the `content` field
    - link: a URL (PR, commit, deployment) in the `url` field
    - file: a binary artifact in storage, referenced by `file_key`
    """

    class OutputType(models.TextChoices):
        MARKDOWN = "markdown", "Markdown"
        PLAINTEXT = "plaintext", "Plain Text"
        LINK = "link", "Link"
        FILE = "file", "File"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="outputs",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="outputs",
    )

    title = models.CharField(max_length=255)
    label = models.CharField(
        max_length=50,
        blank=True,
        help_text='Stage or type label, e.g. "pitch", "concept", "pr", "design"',
    )
    output_type = models.CharField(
        max_length=20,
        choices=OutputType.choices,
        default=OutputType.MARKDOWN,
    )

    # Content — exactly one of these is populated depending on output_type
    content = models.TextField(blank=True, help_text="Inline text for markdown/plaintext outputs")
    url = models.URLField(blank=True, help_text="For link outputs (PR, commit, deployment URL)")
    file_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="Storage path for binary files — private, never expose directly.",
    )

    # File metadata (only relevant for file outputs)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    file_size = models.IntegerField(default=0)

    created_by_task = models.ForeignKey(
        "agents.AgentTask",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outputs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["sprint", "department"],
                name="one_output_per_department_per_sprint",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.output_type}) — {self.sprint}"

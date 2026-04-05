import uuid

from django.db import models


class Output(models.Model):
    """
    Generic output produced by any department.
    Source = input, Output = what agents produce.
    Writers room produces scripts, legal produces contracts, etc.
    """

    class OutputType(models.TextChoices):
        MARKDOWN = "markdown", "Markdown"
        FOUNTAIN = "fountain", "Fountain"  # screenplay format
        PLAINTEXT = "plaintext", "Plain Text"
        PDF = "pdf", "PDF"
        HTML = "html", "HTML"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="outputs",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="outputs",
    )

    # What is this output?
    title = models.CharField(max_length=255)
    label = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g. "logline", "treatment", "contract_draft", "v2"',
    )
    output_type = models.CharField(
        max_length=20,
        choices=OutputType.choices,
        default=OutputType.MARKDOWN,
    )

    # Content -- inline text content (for markdown, fountain, plaintext)
    content = models.TextField(blank=True)

    # File -- for binary outputs (PDFs, etc.) -- uses same storage as Source
    file_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="Storage path -- private, never expose directly.",
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)

    # Versioning
    version = models.PositiveIntegerField(default=1)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="revisions",
    )

    # Metadata
    word_count = models.IntegerField(default=0)
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
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} v{self.version} ({self.output_type})"

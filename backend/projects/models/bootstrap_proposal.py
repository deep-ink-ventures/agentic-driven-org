import uuid

from django.db import models


class BootstrapProposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        PROPOSED = "proposed", "Proposed"
        APPROVED = "approved", "Approved"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="bootstrap_proposals",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    proposal = models.JSONField(
        null=True,
        blank=True,
        help_text="The proposed departments, agents, and documents.",
    )
    error_message = models.TextField(blank=True)
    token_usage = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] Bootstrap for {self.project.name}"

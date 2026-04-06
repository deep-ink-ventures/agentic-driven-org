import uuid

from django.db import models


class Document(models.Model):
    class DocType(models.TextChoices):
        GENERAL = "general", "General"
        RESEARCH = "research", "Research"
        BRANDING = "branding", "Branding"
        STRATEGY = "strategy", "Strategy"
        CAMPAIGN = "campaign", "Campaign"
        VOICE_PROFILE = "voice_profile", "Voice Profile"
        CONCEPT = "concept", "Concept"
        SPRINT_PROGRESS = "sprint_progress", "Sprint Progress"
        SPRINT_SUMMARY = "sprint_summary", "Sprint Summary"
        MONTHLY_ARCHIVE = "monthly_archive", "Monthly Archive"
        STAGE_DELIVERABLE = "stage_deliverable", "Stage Deliverable"
        STAGE_RESEARCH = "stage_research", "Stage Research & Notes"
        STAGE_CRITIQUE = "stage_critique", "Stage Critique"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, help_text="Document content in markdown")
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.GENERAL,
        db_index=True,
    )
    document_type = models.CharField(
        max_length=20,
        choices=[
            ("general", "General"),
            ("sprint_progress", "Sprint Progress"),
            ("sprint_summary", "Sprint Summary"),
            ("monthly_archive", "Monthly Archive"),
        ],
        default="general",
        db_index=True,
    )
    consolidated_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consolidated_from",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    is_archived = models.BooleanField(default=False)
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked documents are protected from consolidation and archiving by automated processes.",
    )
    tags = models.ManyToManyField("projects.Tag", blank=True, related_name="documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

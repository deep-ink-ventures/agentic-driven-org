import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Project(models.Model):
    class Status(models.TextChoices):
        SETUP = "setup", "Setup"
        ACTIVE = "active", "Active"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    goal = models.TextField(blank=True, help_text="Project goal in markdown")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SETUP, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_projects",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="projects",
        help_text="Users who can access this project. Owner is always a member.",
    )
    config = models.ForeignKey(
        "projects.ProjectConfig",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Shared config (Google credentials, etc.). One config can serve multiple projects.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:240]
            slug = base
            n = 1
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

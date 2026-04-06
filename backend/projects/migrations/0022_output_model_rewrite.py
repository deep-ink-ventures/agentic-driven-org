"""Rewrite Output model: sprint-scoped, no versioning, clean types."""

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agents", "0009_add_briefings"),
        ("projects", "0021_document_is_locked"),
    ]

    operations = [
        # Output was created in 0013 and deleted in 0014, so we just create fresh
        migrations.CreateModel(
            name="Output",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "label",
                    models.CharField(
                        blank=True,
                        help_text='Stage or type label, e.g. "pitch", "concept", "pr", "design"',
                        max_length=50,
                    ),
                ),
                (
                    "output_type",
                    models.CharField(
                        choices=[
                            ("markdown", "Markdown"),
                            ("plaintext", "Plain Text"),
                            ("link", "Link"),
                            ("file", "File"),
                        ],
                        default="markdown",
                        max_length=20,
                    ),
                ),
                ("content", models.TextField(blank=True, help_text="Inline text for markdown/plaintext outputs")),
                ("url", models.URLField(blank=True, help_text="For link outputs (PR, commit, deployment URL)")),
                (
                    "file_key",
                    models.CharField(
                        blank=True,
                        help_text="Storage path for binary files — private, never expose directly.",
                        max_length=500,
                    ),
                ),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=100)),
                ("file_size", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sprint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outputs",
                        to="projects.sprint",
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outputs",
                        to="projects.department",
                    ),
                ),
                (
                    "created_by_task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="outputs",
                        to="agents.agenttask",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="output",
            constraint=models.UniqueConstraint(
                fields=("sprint", "department"),
                name="one_output_per_department_per_sprint",
            ),
        ),
    ]

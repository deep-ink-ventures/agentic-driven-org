import uuid

from django.db import models
from jsonschema import ValidationError as JsonSchemaError
from jsonschema import validate

# JSON Schema for project-level config. Used for validation and frontend form generation.
PROJECT_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


class ProjectConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="e.g. 'Hotel Berlin Google Account'")
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Project-wide config — validated against PROJECT_CONFIG_SCHEMA",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "project config"
        verbose_name_plural = "project configs"

    @property
    def google_email(self):
        return self.config.get("google_email", "")

    @property
    def google_credentials(self):
        return self.config.get("google_credentials", {})

    def clean(self):
        super().clean()
        errors = self.validate_config()
        if errors:
            from django.core.exceptions import ValidationError

            raise ValidationError({"config": errors})

    def validate_config(self) -> list[str]:
        """Validate config against JSON Schema. Returns list of error strings."""
        try:
            validate(instance=self.config, schema=PROJECT_CONFIG_SCHEMA)
            return []
        except JsonSchemaError as e:
            return [e.message]

    @classmethod
    def get_schema(cls) -> dict:
        """Return the JSON Schema for frontend form generation."""
        return PROJECT_CONFIG_SCHEMA

    def __str__(self):
        return self.name

import uuid

from django.db import models


class Agent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Display name, e.g. 'Our Twitter Guy'")
    agent_type = models.CharField(
        max_length=50,
        help_text="Blueprint type — determines the agent's behavior",
    )
    department = models.ForeignKey(
        "projects.Department",
        on_delete=models.CASCADE,
        related_name="agents",
    )
    superior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        help_text="Superior agent that can delegate tasks to this agent",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Custom instructions layered on top of the blueprint prompts",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-agent config (browser cookies, API keys, etc.)",
    )
    auto_exec_hourly = models.BooleanField(
        default=False,
        help_text="Whether this agent auto-executes hourly tasks",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "name"]

    def get_blueprint(self):
        from agents.blueprints import get_blueprint
        return get_blueprint(self.agent_type)

    def __str__(self):
        return f"{self.name} ({self.agent_type})"

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
    is_leader = models.BooleanField(
        default=False,
        help_text="Leader agent for the department. Creates and delegates tasks to workforce agents.",
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
    internal_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Agent-managed state (last_tweet_at, emails_sent_today, etc.). Read/written by blueprints.",
    )
    auto_actions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Maps command names to auto-execute booleans, e.g. {\"engage-tweets\": true, \"post-content\": false}. Defaults all false.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department", "-is_leader", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department"],
                condition=models.Q(is_leader=True),
                name="unique_leader_per_department",
            ),
        ]

    def is_action_enabled(self, command_name: str) -> bool:
        """Check if a scheduled command is enabled for auto-execution."""
        return self.auto_actions.get(command_name, False)

    def get_blueprint(self):
        from agents.blueprints import get_blueprint
        return get_blueprint(self.agent_type)

    def __str__(self):
        leader_tag = " [LEADER]" if self.is_leader else ""
        return f"{self.name} ({self.agent_type}){leader_tag}"

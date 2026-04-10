import uuid

from django.db import models


class ClonedAgent(models.Model):
    """Ephemeral clone of an Agent — same blueprint, own state, scoped to one sprint."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.CASCADE,
        related_name="clones",
        help_text="The agent this clone inherits blueprint/instructions/config from",
    )
    sprint = models.ForeignKey(
        "projects.Sprint",
        on_delete=models.CASCADE,
        related_name="cloned_agents",
        help_text="Sprint this clone is scoped to — destroyed when sprint completes",
    )
    clone_index = models.IntegerField(
        help_text="0-based index for identification within a fan-out batch",
    )
    internal_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Clone-specific working state (target_count, cumulative profiles, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sprint", "parent", "clone_index"]

    def __str__(self):
        return f"Clone #{self.clone_index} of {self.parent.name} (sprint {self.sprint_id})"

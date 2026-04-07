from django.contrib import admin
from django.utils import timezone

from agents.models import AgentTask


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = (
        "short_summary",
        "agent",
        "status",
        "auto_execute",
        "review_verdict",
        "review_score",
        "proposed_exec_at",
        "created_by_agent",
        "created_at",
    )
    list_filter = ("status", "auto_execute", "agent__agent_type", "agent__department__project")
    search_fields = ("exec_summary", "agent__name")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "scheduled_at",
        "review_verdict",
        "review_score",
    )
    fieldsets = (
        (None, {"fields": ("id", "agent", "created_by_agent", "status", "auto_execute")}),
        ("Scheduling", {"fields": ("proposed_exec_at", "scheduled_at")}),
        ("Task Details", {"fields": ("exec_summary", "step_plan")}),
        ("Results", {"fields": ("report", "error_message", "review_verdict", "review_score")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "started_at", "completed_at")}),
    )
    actions = ["approve_tasks", "approve_and_auto_execute_similar", "reject_tasks"]

    @admin.display(description="Summary")
    def short_summary(self, obj):
        return obj.exec_summary[:80] if obj.exec_summary else "—"

    @admin.action(description="Approve selected tasks")
    def approve_tasks(self, request, queryset):
        approved = 0
        for task in queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL):
            task.approve()
            approved += 1
        self.message_user(request, f"{approved} task(s) approved and queued/planned.")

    @admin.action(description="Approve & auto-enable command on agent")
    def approve_and_auto_execute_similar(self, request, queryset):
        """Approve tasks and enable their command in the agent's enabled_commands."""
        approved = 0
        for task in queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL):
            task.approve()
            approved += 1
            if task.command_name and not task.agent.is_action_enabled(task.command_name):
                task.agent.enabled_commands[task.command_name] = True
                task.agent.save(update_fields=["enabled_commands"])
        self.message_user(request, f"{approved} task(s) approved and queued/planned.")

    @admin.action(description="Reject selected tasks")
    def reject_tasks(self, request, queryset):
        count = queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL).update(
            status=AgentTask.Status.FAILED,
            error_message="Rejected by admin",
            completed_at=timezone.now(),
        )
        self.message_user(request, f"{count} task(s) rejected.")

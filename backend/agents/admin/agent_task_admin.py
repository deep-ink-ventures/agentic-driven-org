from django.contrib import admin
from django.utils import timezone

from agents.models import AgentTask


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ("short_summary", "agent", "status", "auto_execute", "proposed_exec_at", "created_by_agent", "created_at")
    list_filter = ("status", "auto_execute", "agent__agent_type", "agent__department__project")
    search_fields = ("exec_summary", "agent__name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "completed_at", "scheduled_at")
    fieldsets = (
        (None, {"fields": ("id", "agent", "created_by_agent", "status", "auto_execute")}),
        ("Scheduling", {"fields": ("proposed_exec_at", "scheduled_at")}),
        ("Task Details", {"fields": ("exec_summary", "step_plan")}),
        ("Results", {"fields": ("report", "error_message")}),
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

    @admin.action(description="Approve & auto-execute similar in future")
    def approve_and_auto_execute_similar(self, request, queryset):
        """Approve tasks and enable matching auto_actions on the agent."""
        approved = 0
        for task in queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL):
            task.approve()
            approved += 1

            # Try to find a matching command on the agent's blueprint
            agent = task.agent
            blueprint = agent.get_blueprint()
            commands = blueprint.get_commands()

            # Match by exec_summary similarity — find command whose description best matches
            for cmd in commands:
                if cmd.get("schedule") and cmd["name"] not in agent.auto_actions:
                    # Check if this task looks like it came from this command
                    # Simple heuristic: command name appears in exec_summary or step_plan
                    cmd_name = cmd["name"]
                    if cmd_name.replace("-", " ") in (task.exec_summary + task.step_plan).lower():
                        agent.auto_actions[cmd_name] = True
                        agent.save(update_fields=["auto_actions"])
                        self.message_user(request, f"Enabled auto-action '{cmd_name}' for {agent.name}")

        self.message_user(request, f"{approved} task(s) approved and queued/planned.")

    @admin.action(description="Reject selected tasks")
    def reject_tasks(self, request, queryset):
        count = queryset.filter(status=AgentTask.Status.AWAITING_APPROVAL).update(
            status=AgentTask.Status.FAILED,
            error_message="Rejected by admin",
            completed_at=timezone.now(),
        )
        self.message_user(request, f"{count} task(s) rejected.")

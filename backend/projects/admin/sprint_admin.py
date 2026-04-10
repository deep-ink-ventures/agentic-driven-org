import logging

from django.contrib import admin

from projects.models import Sprint

logger = logging.getLogger(__name__)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "status", "project", "created_at")
    list_filter = ("status", "project")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at", "completed_at")
    actions = ["reset_and_restart"]

    def text_preview(self, obj):
        return obj.text[:80]

    text_preview.short_description = "Text"

    @admin.action(description="Reset and restart sprint (deletes all tasks, docs, outputs)")
    def reset_and_restart(self, request, queryset):
        from agents.models import AgentTask, ClonedAgent
        from projects.models import Document, Output

        for sprint in queryset:
            tasks_deleted = AgentTask.objects.filter(sprint=sprint).delete()[0]
            clones_deleted = ClonedAgent.objects.filter(sprint=sprint).delete()[0]
            docs_deleted = Document.objects.filter(sprint=sprint).delete()[0]
            outputs_deleted = Output.objects.filter(sprint=sprint).delete()[0]

            sprint.department_state = {}
            sprint.status = Sprint.Status.RUNNING
            sprint.completion_summary = ""
            sprint.completed_at = None
            sprint.save(
                update_fields=[
                    "department_state",
                    "status",
                    "completion_summary",
                    "completed_at",
                    "updated_at",
                ]
            )

            from agents.tasks import create_next_leader_task

            for dept in sprint.departments.all():
                leader = dept.agents.filter(is_leader=True, status="active").first()
                if leader:
                    create_next_leader_task.delay(str(leader.id))

            logger.info(
                "SPRINT_RESET sprint=%s tasks=%d clones=%d docs=%d outputs=%d",
                str(sprint.id)[:8],
                tasks_deleted,
                clones_deleted,
                docs_deleted,
                outputs_deleted,
            )

        self.message_user(
            request,
            f"Reset {queryset.count()} sprint(s). Leaders will pick up fresh.",
        )

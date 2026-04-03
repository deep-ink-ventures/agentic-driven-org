from django.contrib import admin

from agents.models import Agent, AgentTask


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    fk_name = "agent"
    extra = 0
    fields = ("status", "exec_summary", "auto_execute", "proposed_exec_at", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True
    max_num = 10


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "department", "is_leader", "auto_exec_hourly", "is_active")
    list_filter = ("agent_type", "is_active", "is_leader", "auto_exec_hourly", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "-is_leader", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "is_leader")}),
        ("Configuration", {"fields": ("instructions", "config", "auto_exec_hourly", "is_active")}),
        ("Internal State", {"fields": ("internal_state",), "classes": ("collapse",)}),
    )
    inlines = [AgentTaskInline]
    actions = ["seed_first_task"]

    @admin.action(description="Seed first leader task — kick off the chain")
    def seed_first_task(self, request, queryset):
        from agents.tasks import create_next_leader_task

        seeded = 0
        for agent in queryset.filter(is_leader=True, is_active=True):
            create_next_leader_task.delay(str(agent.id))
            seeded += 1
        self.message_user(request, f"Seeded first task for {seeded} leader(s).")

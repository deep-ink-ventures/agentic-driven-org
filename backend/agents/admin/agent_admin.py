from django.contrib import admin

from agents.models import Agent, AgentTask


class AgentTaskInline(admin.TabularInline):
    model = AgentTask
    fk_name = "agent"
    extra = 0
    fields = ("status", "exec_summary", "auto_execute", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    show_change_link = True
    max_num = 10


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "agent_type", "department", "is_leader", "auto_exec_hourly", "is_active")
    list_filter = ("agent_type", "is_active", "auto_exec_hourly", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "is_leader")}),
        ("Configuration", {"fields": ("instructions", "config", "auto_exec_hourly", "is_active")}),
    )
    inlines = [AgentTaskInline]

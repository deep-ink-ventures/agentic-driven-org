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
    list_display = ("name", "agent_type", "department", "is_leader", "status")
    list_filter = ("agent_type", "status", "is_leader", "department__project")
    search_fields = ("name", "department__name")
    ordering = ("department", "-is_leader", "name")
    fieldsets = (
        (None, {"fields": ("name", "agent_type", "department", "is_leader")}),
        ("Configuration", {"fields": ("instructions", "config", "enabled_commands", "status")}),
        ("Internal State", {"fields": ("internal_state",), "classes": ("collapse",)}),
    )
    inlines = [AgentTaskInline]

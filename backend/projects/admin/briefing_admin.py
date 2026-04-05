from django.contrib import admin

from projects.models import Briefing


@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "department", "status", "created_by", "created_at")
    list_filter = ("status", "project")
    search_fields = ("title", "content", "project__name")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

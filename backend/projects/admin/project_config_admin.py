from django.contrib import admin

from projects.models import ProjectConfig


@admin.register(ProjectConfig)
class ProjectConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "google_email", "project_count", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "name")}),
        ("Configuration", {"fields": ("config",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Google Email")
    def google_email(self, obj):
        return obj.google_email or "—"

    @admin.display(description="Projects")
    def project_count(self, obj):
        return obj.projects.count()

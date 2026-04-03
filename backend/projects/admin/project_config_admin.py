from django.contrib import admin

from projects.models import ProjectConfig


@admin.register(ProjectConfig)
class ProjectConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "google_email", "project_count", "created_at")
    search_fields = ("name", "google_email")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "name")}),
        ("Google", {"fields": ("google_email", "google_credentials")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Projects")
    def project_count(self, obj):
        return obj.projects.count()

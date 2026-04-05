from django.contrib import admin

from projects.models import Sprint


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("text_preview", "status", "project", "created_at")
    list_filter = ("status", "project")
    search_fields = ("text",)
    readonly_fields = ("created_at", "updated_at", "completed_at")

    def text_preview(self, obj):
        return obj.text[:80]

    text_preview.short_description = "Text"

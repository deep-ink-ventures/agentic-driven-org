from django.contrib import admin

from projects.models import Output


@admin.register(Output)
class OutputAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "department", "output_type", "label", "version", "word_count", "created_at"]
    list_filter = ["output_type", "label", "created_at"]
    search_fields = ["title", "label"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["project", "department", "parent", "created_by_task"]

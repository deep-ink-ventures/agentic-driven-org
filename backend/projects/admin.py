from django.contrib import admin

from projects.models import Output


@admin.register(Output)
class OutputAdmin(admin.ModelAdmin):
    list_display = ["title", "sprint", "department", "output_type", "label", "updated_at"]
    list_filter = ["output_type", "label"]
    search_fields = ["title", "label"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["sprint", "department", "created_by_task"]

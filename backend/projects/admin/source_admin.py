from django.contrib import admin

from projects.models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("source_label", "source_type", "file_format", "file_size", "word_count", "project", "created_at")
    list_filter = ("source_type", "file_format", "project")
    search_fields = ("original_filename", "url", "project__name")
    readonly_fields = ("id", "file_key", "content_hash", "extracted_text", "word_count", "file_size", "created_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "source_type", "user")}),
        ("File Source", {"fields": ("original_filename", "file_key", "file_format", "content_type", "file_size", "content_hash")}),
        ("URL Source", {"fields": ("url",)}),
        ("Text Source", {"fields": ("raw_content",)}),
        ("Extraction", {"fields": ("extracted_text", "word_count")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    @admin.display(description="Source")
    def source_label(self, obj):
        if obj.source_type == "file":
            return obj.original_filename or "—"
        elif obj.source_type == "url":
            return (obj.url or "—")[:60]
        return "Text input"

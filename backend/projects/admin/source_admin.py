from django.contrib import admin

from projects.extraction import extract_text
from projects.models import Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "source_label",
        "source_type",
        "priority",
        "file_format",
        "file_size",
        "word_count",
        "project",
        "created_at",
    )
    list_filter = ("source_type", "priority", "file_format", "project")
    search_fields = ("original_filename", "url", "project__name")
    readonly_fields = ("id", "file_key", "content_hash", "extracted_text", "word_count", "file_size", "created_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "source_type", "priority", "user")}),
        (
            "File Source",
            {"fields": ("original_filename", "file_key", "file_format", "content_type", "file_size", "content_hash")},
        ),
        ("URL Source", {"fields": ("url",)}),
        ("Text Source", {"fields": ("raw_content",)}),
        ("Extraction", {"fields": ("extracted_text", "summary", "word_count")}),
        ("Timestamps", {"fields": ("created_at",)}),
    )

    def save_model(self, request, obj, form, change):
        """Auto-extract text and compute metadata when a source is saved."""
        # Set user if not set
        if not obj.user_id:
            obj.user = request.user

        # For text sources, set extracted_text from raw_content
        if obj.source_type == "text" and obj.raw_content and not obj.extracted_text:
            obj.extracted_text = obj.raw_content
            obj.word_count = len(obj.raw_content.split())

        super().save_model(request, obj, form, change)

        # Extract text after save (for file and url sources)
        if not obj.extracted_text and obj.source_type in ("file", "url"):
            text = extract_text(obj)
            if text:
                obj.extracted_text = text
                obj.word_count = len(text.split())
                obj.save(update_fields=["extracted_text", "word_count"])

    @admin.display(description="Source")
    def source_label(self, obj):
        if obj.source_type == "file":
            return obj.original_filename or "—"
        elif obj.source_type == "url":
            return (obj.url or "—")[:60]
        return "Text input"

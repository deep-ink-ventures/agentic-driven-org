from django.contrib import admin

from projects.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "created_at")
    list_filter = ("department__project", "department", "tags")
    search_fields = ("title", "content")
    ordering = ("-updated_at",)
    filter_horizontal = ("tags",)

from django.contrib import admin

from projects.models import Department, Document


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ("title", "tags")
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "created_at")
    list_filter = ("project",)
    search_fields = ("name", "project__name")
    ordering = ("project__name", "name")
    inlines = [DocumentInline]

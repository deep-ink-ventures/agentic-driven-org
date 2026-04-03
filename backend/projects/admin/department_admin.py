from django.contrib import admin

from projects.models import Department, Document


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ("title", "tags")
    show_change_link = True


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "department_type", "project", "created_at")
    list_filter = ("department_type", "project")
    search_fields = ("department_type", "project__name")
    ordering = ("project__name", "department_type")
    inlines = [DocumentInline]

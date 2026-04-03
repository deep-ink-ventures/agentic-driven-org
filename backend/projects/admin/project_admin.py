from django.contrib import admin

from projects.models import Project, Department


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("name",)
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__email")
    ordering = ("-updated_at",)
    inlines = [DepartmentInline]

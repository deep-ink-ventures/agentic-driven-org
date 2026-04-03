from django.contrib import admin
from django.contrib import messages

from projects.models import Project, Department, Source, BootstrapProposal


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 1
    fields = ("department_type",)
    show_change_link = True


class SourceInline(admin.TabularInline):
    model = Source
    extra = 0
    fields = ("source_type", "original_filename", "url", "raw_content", "word_count", "created_at")
    readonly_fields = ("word_count", "created_at")
    show_change_link = True


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "source_count", "created_at")
    search_fields = ("name", "owner__email")
    ordering = ("-updated_at",)
    inlines = [SourceInline, DepartmentInline]
    actions = ["bootstrap_project"]

    @admin.display(description="Sources")
    def source_count(self, obj):
        return obj.sources.count()

    @admin.action(description="Bootstrap Project — analyze sources and propose setup")
    def bootstrap_project(self, request, queryset):
        from projects.tasks import bootstrap_project as bootstrap_task

        for project in queryset:
            if not project.goal:
                self.message_user(request, f"{project.name}: needs a goal before bootstrapping.", level=messages.WARNING)
                continue

            source_count = project.sources.count()
            if source_count == 0:
                self.message_user(request, f"{project.name}: needs at least one source.", level=messages.WARNING)
                continue

            proposal = BootstrapProposal.objects.create(
                project=project,
                status=BootstrapProposal.Status.PENDING,
            )
            bootstrap_task.delay(str(proposal.id))
            self.message_user(
                request,
                f"Bootstrap started for {project.name}. Check Bootstrap Proposals for results.",
                level=messages.SUCCESS,
            )

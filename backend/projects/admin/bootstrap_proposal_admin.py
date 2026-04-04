import json
import logging

from django.contrib import admin
from django.utils.html import format_html

from projects.models import BootstrapProposal, Department, Document, Tag
from agents.models import Agent
from agents.blueprints import DEPARTMENTS, get_workforce_for_department

logger = logging.getLogger(__name__)


@admin.register(BootstrapProposal)
class BootstrapProposalAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "cost_display", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("project__name",)
    readonly_fields = ("id", "project", "proposal_formatted", "token_usage", "error_message", "created_at", "updated_at")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("id", "project", "status")}),
        ("Proposal", {"fields": ("proposal_formatted",)}),
        ("Debug", {"fields": ("error_message", "token_usage")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    actions = ["approve_and_apply", "reject_proposal", "retry_now"]

    @admin.display(description="Cost")
    def cost_display(self, obj):
        if obj.token_usage and "cost_usd" in obj.token_usage:
            return f"${obj.token_usage['cost_usd']:.4f}"
        return "—"

    @admin.display(description="Proposal (formatted)")
    def proposal_formatted(self, obj):
        if not obj.proposal:
            return "—"
        return format_html("<pre style='max-height:600px;overflow:auto'>{}</pre>", json.dumps(obj.proposal, indent=2))

    @admin.action(description="Approve & Apply — create departments, agents, documents")
    def approve_and_apply(self, request, queryset):
        for proposal in queryset.filter(status=BootstrapProposal.Status.PROPOSED):
            try:
                self._apply_proposal(proposal)
                proposal.status = BootstrapProposal.Status.APPROVED
                proposal.save(update_fields=["status", "updated_at"])
                self.message_user(request, f"Applied bootstrap for {proposal.project.name}")
            except Exception as e:
                logger.exception("Failed to apply bootstrap: %s", e)
                self.message_user(request, f"Failed to apply for {proposal.project.name}: {e}", level="error")

    @admin.action(description="Reject proposal")
    def reject_proposal(self, request, queryset):
        count = queryset.filter(status=BootstrapProposal.Status.PROPOSED).update(
            status=BootstrapProposal.Status.FAILED,
            error_message="Rejected by admin",
        )
        self.message_user(request, f"{count} proposal(s) rejected.")

    @admin.action(description="Retry now — re-dispatch stuck/failed proposals")
    def retry_now(self, request, queryset):
        from projects.tasks import bootstrap_project
        retried = 0
        for proposal in queryset.filter(status__in=[
            BootstrapProposal.Status.PENDING,
            BootstrapProposal.Status.PROCESSING,
            BootstrapProposal.Status.FAILED,
        ]):
            proposal.status = BootstrapProposal.Status.PENDING
            proposal.error_message = ""
            proposal.save(update_fields=["status", "error_message", "updated_at"])
            bootstrap_project.delay(str(proposal.id))
            retried += 1
        self.message_user(request, f"{retried} proposal(s) re-dispatched.")

    def _apply_proposal(self, proposal):
        """Create departments, leader + workforce agents, and documents from the proposal JSON."""
        project = proposal.project
        data = proposal.proposal
        if not data or "departments" not in data:
            raise ValueError("Invalid proposal — missing departments")

        for dept_data in data["departments"]:
            department_type = dept_data["department_type"]
            if department_type not in DEPARTMENTS:
                logger.warning("Skipping unknown department_type '%s'", department_type)
                continue

            department, _ = Department.objects.get_or_create(
                project=project,
                department_type=department_type,
            )

            # Create documents
            for doc_data in dept_data.get("documents", []):
                doc = Document.objects.create(
                    title=doc_data["title"],
                    content=doc_data.get("content", ""),
                    department=department,
                )
                for tag_name in doc_data.get("tags", []):
                    tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                    doc.tags.add(tag)

            # Auto-create leader agent if department doesn't have one
            if not department.agents.filter(is_leader=True).exists():
                Agent.objects.create(
                    name=f"{department.name} Leader",
                    agent_type="leader",
                    department=department,
                    is_leader=True,
                    instructions=f"Lead the {department.name} department for project: {project.name}. Goal: {project.goal[:200]}",
                )

            # Create workforce agents (only valid types for this department)
            available_workforce = get_workforce_for_department(department_type)
            for agent_data in dept_data.get("agents", []):
                agent_type = agent_data["agent_type"]
                if agent_type not in available_workforce:
                    logger.warning("Skipping agent_type '%s' — not available in department '%s'", agent_type, department_type)
                    continue
                Agent.objects.create(
                    name=agent_data["name"],
                    agent_type=agent_type,
                    department=department,
                    is_leader=False,
                    instructions=agent_data.get("instructions", ""),
                )

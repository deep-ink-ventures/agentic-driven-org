import json
import logging

from django.contrib import admin
from django.utils.html import format_html

from projects.models import BootstrapProposal, Department, Document, Tag
from agents.models import Agent

logger = logging.getLogger(__name__)


@admin.register(BootstrapProposal)
class BootstrapProposalAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "created_at", "updated_at")
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
    actions = ["approve_and_apply", "reject_proposal"]

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

    def _apply_proposal(self, proposal):
        """Create departments, agents, and documents from the proposal JSON."""
        project = proposal.project
        data = proposal.proposal
        if not data or "departments" not in data:
            raise ValueError("Invalid proposal — missing departments")

        for dept_data in data["departments"]:
            department, _ = Department.objects.get_or_create(
                project=project,
                name=dept_data["name"],
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

            # Create agents
            created_agents = {}
            for agent_data in dept_data.get("agents", []):
                agent = Agent.objects.create(
                    name=agent_data["name"],
                    agent_type=agent_data["agent_type"],
                    department=department,
                    instructions=agent_data.get("instructions", ""),
                    auto_exec_hourly=agent_data.get("auto_exec_hourly", False),
                )
                created_agents[agent_data["agent_type"]] = agent

            # Wire superior relationships: campaign is superior to twitter/reddit
            campaign = created_agents.get("campaign")
            if campaign:
                for agent_type in ("twitter", "reddit"):
                    sub = created_agents.get(agent_type)
                    if sub:
                        sub.superior = campaign
                        sub.save(update_fields=["superior"])

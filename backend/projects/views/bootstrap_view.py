import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project, BootstrapProposal, Department, Document, Tag
from projects.serializers import BootstrapProposalSerializer
from projects.models.bootstrap_proposal import get_proposal_json_schema
from agents.models import Agent
from agents.blueprints import DEPARTMENTS, get_workforce_for_department

logger = logging.getLogger(__name__)


class BootstrapTriggerView(APIView):
    """POST /api/projects/{project_id}/bootstrap/ — trigger bootstrap analysis."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, owner=request.user)

        if not project.goal:
            return Response({"error": "Project needs a goal before bootstrapping."}, status=status.HTTP_400_BAD_REQUEST)

        if not project.sources.exists():
            return Response({"error": "Project needs at least one source."}, status=status.HTTP_400_BAD_REQUEST)

        proposal = BootstrapProposal.objects.create(
            project=project,
            status=BootstrapProposal.Status.PENDING,
        )

        from projects.tasks import bootstrap_project
        bootstrap_project.delay(str(proposal.id))

        return Response(BootstrapProposalSerializer(proposal).data, status=status.HTTP_202_ACCEPTED)


class BootstrapLatestView(APIView):
    """GET /api/projects/{project_id}/bootstrap/latest/ — get latest proposal."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        proposal = BootstrapProposal.objects.filter(project=project).first()
        if not proposal:
            return Response({"proposal": None})
        return Response(BootstrapProposalSerializer(proposal).data)


class BootstrapApproveView(APIView):
    """POST /api/projects/{project_id}/bootstrap/{proposal_id}/approve/ — apply proposal."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, proposal_id):
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        proposal = get_object_or_404(BootstrapProposal, id=proposal_id, project=project)

        if proposal.status != BootstrapProposal.Status.PROPOSED:
            return Response({"error": f"Proposal is {proposal.status}, not proposed."}, status=status.HTTP_400_BAD_REQUEST)

        # Allow frontend to send an edited proposal
        edited_proposal = request.data.get("proposal")
        if edited_proposal:
            proposal.proposal = edited_proposal
            errors = proposal.validate_proposal()
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self._apply_proposal(proposal)
            proposal.status = BootstrapProposal.Status.APPROVED
            proposal.save(update_fields=["status", "proposal", "updated_at"])
            return Response(BootstrapProposalSerializer(proposal).data)
        except Exception as e:
            logger.exception("Failed to apply bootstrap: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _apply_proposal(self, proposal):
        """Create departments, leader + workforce agents, and documents."""
        project = proposal.project
        data = proposal.proposal

        for dept_data in data["departments"]:
            department_type = dept_data["department_type"]
            if department_type not in DEPARTMENTS:
                continue

            department, _ = Department.objects.get_or_create(
                project=project,
                department_type=department_type,
            )

            for doc_data in dept_data.get("documents", []):
                doc = Document.objects.create(
                    title=doc_data["title"],
                    content=doc_data.get("content", ""),
                    department=department,
                )
                for tag_name in doc_data.get("tags", []):
                    tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                    doc.tags.add(tag)

            if not department.agents.filter(is_leader=True).exists():
                Agent.objects.create(
                    name=f"{department.name} Leader",
                    agent_type="leader",
                    department=department,
                    is_leader=True,
                    instructions=f"Lead the {department.name} department for project: {project.name}. Goal: {project.goal[:200]}",
                )

            available_workforce = get_workforce_for_department(department_type)
            for agent_data in dept_data.get("agents", []):
                agent_type = agent_data["agent_type"]
                if agent_type not in available_workforce:
                    continue
                Agent.objects.create(
                    name=agent_data["name"],
                    agent_type=agent_type,
                    department=department,
                    is_leader=False,
                    instructions=agent_data.get("instructions", ""),
                )


class BootstrapSchemaView(APIView):
    """GET /api/bootstrap/schema/ — return the JSON Schema for proposal validation."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_proposal_json_schema())

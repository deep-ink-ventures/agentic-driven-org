import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from agents.blueprints import DEPARTMENTS, get_workforce_for_department
from agents.models import Agent
from projects.models import BootstrapProposal, Department, Project
from projects.models.bootstrap_proposal import get_proposal_json_schema
from projects.serializers import BootstrapProposalSerializer

logger = logging.getLogger(__name__)


class BootstrapTriggerView(APIView):
    """POST /api/projects/{project_id}/bootstrap/ — trigger bootstrap analysis."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "bootstrap"

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)

        if not project.goal:
            return Response({"error": "Project needs a goal before bootstrapping."}, status=status.HTTP_400_BAD_REQUEST)

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
        project = get_object_or_404(Project, id=project_id, members=request.user)
        proposal = BootstrapProposal.objects.filter(project=project).first()
        if not proposal:
            return Response({"proposal": None})
        return Response(BootstrapProposalSerializer(proposal).data)


class BootstrapApproveView(APIView):
    """POST /api/projects/{project_id}/bootstrap/{proposal_id}/approve/ — apply proposal."""

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, proposal_id):
        project = get_object_or_404(Project, id=project_id, members=request.user)
        proposal = get_object_or_404(BootstrapProposal, id=proposal_id, project=project)

        if proposal.status != BootstrapProposal.Status.PROPOSED:
            return Response(
                {"error": f"Proposal is {proposal.status}, not proposed."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Allow frontend to send an edited proposal
        edited_proposal = request.data.get("proposal")
        if edited_proposal:
            proposal.proposal = edited_proposal
            errors = proposal.validate_proposal()
            if errors:
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.db import transaction

            with transaction.atomic():
                self._apply_proposal(proposal)
                proposal.status = BootstrapProposal.Status.APPROVED
                proposal.save(update_fields=["status", "proposal", "updated_at"])
            # Enrich the goal with context from sources — never reduce it
            if proposal.proposal and proposal.proposal.get("enriched_goal"):
                enriched = proposal.proposal["enriched_goal"]
                # Safety: only apply if enriched version is at least as long as original
                if len(enriched) >= len(project.goal or ""):
                    project.goal = enriched
            project.status = Project.Status.ACTIVE
            project.save(update_fields=["goal", "status", "updated_at"])
            return Response(BootstrapProposalSerializer(proposal).data)
        except Exception as e:
            logger.exception("Failed to apply bootstrap: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _apply_proposal(self, proposal):
        """Create departments + agents immediately, then fire configure tasks for detailed instructions + docs."""
        project = proposal.project
        data = proposal.proposal

        departments_to_configure = []

        for dept_data in data["departments"]:
            department_type = dept_data["department_type"]
            if department_type not in DEPARTMENTS:
                continue

            department, _ = Department.objects.get_or_create(
                project=project,
                department_type=department_type,
            )

            # Create leader (provisioning — configure_new_department will set real instructions)
            if not department.agents.filter(is_leader=True).exists():
                Agent.objects.create(
                    name=f"Head of {department.name}",
                    agent_type="leader",
                    department=department,
                    is_leader=True,
                    status=Agent.Status.PROVISIONING,
                    instructions="",
                )

            # Build instructions map from proposal
            instructions_by_type = {}
            names_by_type = {}
            available_workforce = get_workforce_for_department(department_type)
            selected_types = set()
            for agent_data in dept_data.get("agents", []):
                agent_type = agent_data["agent_type"]
                if agent_type in available_workforce:
                    selected_types.add(agent_type)
                    instructions_by_type[agent_type] = agent_data.get("instructions", "")
                    names_by_type[agent_type] = agent_data.get("name", "")

            # Add essential + controller agents
            from agents.blueprints import get_workforce_metadata

            metadata = get_workforce_metadata(department_type)
            for m in metadata:
                if m["essential"] and m["agent_type"] not in selected_types:
                    selected_types.add(m["agent_type"])
            for m in metadata:
                if not m["controls"]:
                    continue
                controls_list = m["controls"] if isinstance(m["controls"], list) else [m["controls"]]
                if any(c in selected_types for c in controls_list) and m["agent_type"] not in selected_types:
                    selected_types.add(m["agent_type"])

            # Create agents as provisioning — provision_single_agent will activate them
            # once real instructions are generated
            for agent_type in selected_types:
                if agent_type not in available_workforce:
                    continue
                bp = available_workforce[agent_type]
                Agent.objects.create(
                    name=names_by_type.get(agent_type) or bp.name,
                    agent_type=agent_type,
                    department=department,
                    is_leader=False,
                    status=Agent.Status.PROVISIONING,
                    instructions=instructions_by_type.get(agent_type, ""),
                )

            departments_to_configure.append(department)

        # Fire configure tasks to generate detailed instructions + documents in background
        from projects.tasks import configure_new_department

        for department in departments_to_configure:
            configure_new_department.delay(str(department.id), "")


class BootstrapSchemaView(APIView):
    """GET /api/bootstrap/schema/ — return the JSON Schema for proposal validation."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_proposal_json_schema())

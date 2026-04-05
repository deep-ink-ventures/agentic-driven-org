from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.serializers import AgentUpdateSerializer
from agents.serializers.blueprint_info_serializer import get_blueprint_info


class AgentUpdateView(UpdateAPIView):
    """PATCH /api/agents/{id}/ — update agent instructions, config, auto_approve, status."""

    serializer_class = AgentUpdateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Agent.objects.filter(department__project__members=self.request.user)


class AgentBlueprintView(APIView):
    """GET /api/agents/{id}/blueprint/ — get blueprint info (skills, commands, config_schema)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agent = get_object_or_404(Agent, pk=pk, department__project__members=request.user)
        return Response(get_blueprint_info(agent))


class AddAgentView(APIView):
    """POST /api/agents/add/ — add a single agent to an existing department."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from agents.blueprints import get_workforce_for_department
        from projects.models import Department

        department_id = request.data.get("department_id")
        agent_type = request.data.get("agent_type")

        if not department_id or not agent_type:
            return Response(
                {"error": "department_id and agent_type are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        department = get_object_or_404(
            Department.objects.select_related("project"),
            id=department_id,
            project__members=request.user,
        )

        workforce = get_workforce_for_department(department.department_type)
        if agent_type not in workforce:
            return Response(
                {"error": f"Unknown agent type '{agent_type}' for department '{department.department_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if department.agents.filter(agent_type=agent_type).exists():
            return Response(
                {"error": f"Agent '{agent_type}' already exists in this department."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bp = workforce[agent_type]
        agent = Agent.objects.create(
            name=bp.name,
            agent_type=agent_type,
            department=department,
            is_leader=False,
            status=Agent.Status.PROVISIONING,
        )

        from projects.tasks import provision_single_agent

        provision_single_agent.delay(str(agent.id))

        return Response(
            {
                "id": str(agent.id),
                "name": agent.name,
                "agent_type": agent.agent_type,
                "status": agent.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )

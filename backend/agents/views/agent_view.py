from django.shortcuts import get_object_or_404
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.serializers import AgentUpdateSerializer
from agents.serializers.blueprint_info_serializer import get_blueprint_info


class AgentUpdateView(UpdateAPIView):
    """PATCH /api/agents/{id}/ — update agent instructions, config, auto_actions, is_active."""
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

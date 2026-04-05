from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Department


class DepartmentConfigView(APIView):
    """PATCH /api/departments/{id}/config/ — update department config."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        department = get_object_or_404(
            Department.objects.select_related("project"),
            id=pk,
            project__members=request.user,
        )
        updates = request.data
        if not isinstance(updates, dict):
            return Response({"error": "Expected a JSON object."}, status=400)

        config = department.config or {}
        # Merge updates, removing keys set to None
        for key, value in updates.items():
            if value is None:
                config.pop(key, None)
            else:
                config[key] = value

        department.config = config
        department.save(update_fields=["config"])
        return Response({"config": department.config})
